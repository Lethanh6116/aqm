"""Resource availability and permission validation for agents.yaml.

Provides checks that go beyond JSON Schema validation:
- Runtime CLI availability (claude, gemini, codex)
- MCP server command availability
- Environment variable existence
- Filesystem path accessibility
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from typing import Any, NamedTuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Warning data structure
# ---------------------------------------------------------------------------


class ValidationWarning(NamedTuple):
    """A non-fatal validation warning."""

    level: str  # "warning" or "error" (when --strict)
    path: str  # dot-path in the YAML structure
    message: str
    fix: str


# ---------------------------------------------------------------------------
# Environment variable reference pattern
# ---------------------------------------------------------------------------

_ENV_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")


def _extract_env_refs(value: str) -> list[str]:
    """Extract environment variable names referenced in *value*.

    Supports both ``$VAR`` and ``${VAR}`` syntax.  Returns an empty list
    if the value doesn't reference any environment variables.
    """
    refs: list[str] = []
    for m in _ENV_VAR_RE.finditer(value):
        refs.append(m.group(1) or m.group(2))
    return refs


# ---------------------------------------------------------------------------
# Resource availability checks
# ---------------------------------------------------------------------------


def check_resource_availability(data: dict[str, Any]) -> list[ValidationWarning]:
    """Check that runtime CLIs and MCP commands referenced in *data* exist.

    Parameters
    ----------
    data:
        Parsed agents.yaml content (a dict).

    Returns
    -------
    list[ValidationWarning]
        Warnings for missing resources.
    """
    warnings: list[ValidationWarning] = []
    agents = data.get("agents", [])

    for i, agent in enumerate(agents):
        if not isinstance(agent, dict):
            continue

        agent_id = agent.get("id", f"#{i}")
        agent_type = agent.get("type", "agent")
        prefix = f"agents[{i}]({agent_id})"

        # --- Runtime CLI check ---
        runtime = agent.get("runtime")
        if runtime and agent_type != "session":
            if shutil.which(runtime) is None:
                warnings.append(
                    ValidationWarning(
                        level="warning",
                        path=f"{prefix}.runtime",
                        message=f"Runtime CLI '{runtime}' not found in PATH",
                        fix=f"Install the '{runtime}' CLI or ensure it is on your PATH.",
                    )
                )

        # --- MCP server command check ---
        mcp_list = agent.get("mcp", [])
        for j, mcp in enumerate(mcp_list if isinstance(mcp_list, list) else []):
            if not isinstance(mcp, dict):
                continue

            server_name = mcp.get("server", "")
            mcp_prefix = f"{prefix}.mcp[{j}]({server_name})"
            command = mcp.get("command")

            # If no command specified, default is "npx" for most MCP servers
            effective_command = command if command else "npx"

            if shutil.which(effective_command) is None:
                warnings.append(
                    ValidationWarning(
                        level="warning",
                        path=f"{mcp_prefix}.command",
                        message=f"MCP command '{effective_command}' not found in PATH",
                        fix=f"Install '{effective_command}' or set the correct 'command' field.",
                    )
                )

    return warnings


# ---------------------------------------------------------------------------
# Permission / environment checks
# ---------------------------------------------------------------------------


def check_permissions(data: dict[str, Any]) -> list[ValidationWarning]:
    """Check environment variables and filesystem paths referenced in *data*.

    Parameters
    ----------
    data:
        Parsed agents.yaml content (a dict).

    Returns
    -------
    list[ValidationWarning]
        Warnings for missing env vars or inaccessible paths.
    """
    warnings: list[ValidationWarning] = []
    agents = data.get("agents", [])

    for i, agent in enumerate(agents):
        if not isinstance(agent, dict):
            continue

        agent_id = agent.get("id", f"#{i}")
        prefix = f"agents[{i}]({agent_id})"

        mcp_list = agent.get("mcp", [])
        for j, mcp in enumerate(mcp_list if isinstance(mcp_list, list) else []):
            if not isinstance(mcp, dict):
                continue

            server_name = mcp.get("server", "")
            mcp_prefix = f"{prefix}.mcp[{j}]({server_name})"

            # --- Environment variable check ---
            env = mcp.get("env")
            if isinstance(env, dict):
                for key, value in env.items():
                    if not isinstance(value, str):
                        continue
                    env_refs = _extract_env_refs(value)
                    for var_name in env_refs:
                        if var_name not in os.environ:
                            warnings.append(
                                ValidationWarning(
                                    level="warning",
                                    path=f"{mcp_prefix}.env.{key}",
                                    message=f"Environment variable '{var_name}' is not set",
                                    fix=f"Set the environment variable: export {var_name}=<value>",
                                )
                            )

            # --- Filesystem path check ---
            if server_name == "filesystem":
                args = mcp.get("args", [])
                if isinstance(args, list):
                    # filesystem server typically has paths as trailing args
                    # after the server package name, e.g.:
                    #   args: ["-y", "@modelcontextprotocol/server-filesystem", "/path1", "/path2"]
                    for k, arg in enumerate(args):
                        if not isinstance(arg, str):
                            continue
                        # Skip flags and package names
                        if arg.startswith("-") or arg.startswith("@"):
                            continue
                        # Treat remaining args as filesystem paths
                        if arg.startswith("/") or arg.startswith("~"):
                            expanded = os.path.expanduser(arg)
                            if not os.path.exists(expanded):
                                warnings.append(
                                    ValidationWarning(
                                        level="warning",
                                        path=f"{mcp_prefix}.args[{k}]",
                                        message=f"Path does not exist: {arg}",
                                        fix=f"Create the directory or update the path.",
                                    )
                                )
                            elif not os.access(expanded, os.R_OK):
                                warnings.append(
                                    ValidationWarning(
                                        level="warning",
                                        path=f"{mcp_prefix}.args[{k}]",
                                        message=f"Path is not readable: {arg}",
                                        fix=f"Check file permissions: chmod +r {arg}",
                                    )
                                )

    return warnings


# ---------------------------------------------------------------------------
# Combined check
# ---------------------------------------------------------------------------


def run_all_checks(data: dict[str, Any]) -> list[ValidationWarning]:
    """Run all resource and permission checks.

    Parameters
    ----------
    data:
        Parsed agents.yaml content (a dict).

    Returns
    -------
    list[ValidationWarning]
        Combined list of warnings from all checks.
    """
    warnings: list[ValidationWarning] = []
    warnings.extend(check_resource_availability(data))
    warnings.extend(check_permissions(data))
    return warnings
