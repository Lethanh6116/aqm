"""Tests for aqm.core.validate — resource availability & permission checks."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from aqm.core.validate import (
    ValidationWarning,
    _extract_env_refs,
    check_permissions,
    check_resource_availability,
    run_all_checks,
)


# ---------------------------------------------------------------------------
# _extract_env_refs
# ---------------------------------------------------------------------------


class TestExtractEnvRefs:

    def test_dollar_var(self):
        assert _extract_env_refs("$MY_TOKEN") == ["MY_TOKEN"]

    def test_braced_var(self):
        assert _extract_env_refs("${MY_TOKEN}") == ["MY_TOKEN"]

    def test_mixed_vars(self):
        refs = _extract_env_refs("prefix_${FOO}_$BAR_end")
        assert "FOO" in refs
        assert "BAR_end" in refs or "BAR" in refs

    def test_no_vars(self):
        assert _extract_env_refs("literal_value") == []

    def test_empty_string(self):
        assert _extract_env_refs("") == []


# ---------------------------------------------------------------------------
# check_resource_availability
# ---------------------------------------------------------------------------


class TestCheckResourceAvailability:

    def test_runtime_found(self):
        """No warning when runtime CLI exists."""
        data = {"agents": [{"id": "a", "runtime": "python", "type": "agent"}]}
        with patch("aqm.core.validate.shutil.which", return_value="/usr/bin/python"):
            warnings = check_resource_availability(data)
        assert warnings == []

    def test_runtime_not_found(self):
        """Warning when runtime CLI is missing from PATH."""
        data = {"agents": [{"id": "a", "runtime": "claude", "type": "agent"}]}
        with patch("aqm.core.validate.shutil.which", return_value=None):
            warnings = check_resource_availability(data)
        assert len(warnings) == 1
        assert "claude" in warnings[0].message
        assert "not found" in warnings[0].message

    def test_session_type_skipped(self):
        """Session agents should not trigger runtime warnings."""
        data = {"agents": [{"id": "s", "type": "session", "runtime": "claude"}]}
        with patch("aqm.core.validate.shutil.which", return_value=None):
            warnings = check_resource_availability(data)
        assert warnings == []

    def test_no_runtime_no_warning(self):
        """Agent without runtime field does not trigger warning."""
        data = {"agents": [{"id": "a", "type": "agent"}]}
        warnings = check_resource_availability(data)
        assert warnings == []

    def test_mcp_command_found(self):
        """No warning when MCP command exists."""
        data = {
            "agents": [
                {
                    "id": "a",
                    "runtime": "claude",
                    "mcp": [{"server": "github", "command": "npx"}],
                }
            ]
        }
        with patch("aqm.core.validate.shutil.which", return_value="/usr/bin/npx"):
            warnings = check_resource_availability(data)
        assert warnings == []

    def test_mcp_command_not_found(self):
        """Warning when MCP command is missing."""
        data = {
            "agents": [
                {
                    "id": "a",
                    "runtime": "claude",
                    "mcp": [{"server": "github", "command": "missing-cmd"}],
                }
            ]
        }
        with patch("aqm.core.validate.shutil.which", return_value=None):
            warnings = check_resource_availability(data)
        # One for runtime, one for MCP command
        mcp_warnings = [w for w in warnings if "MCP" in w.message]
        assert len(mcp_warnings) == 1
        assert "missing-cmd" in mcp_warnings[0].message

    def test_mcp_default_command_npx(self):
        """When no command specified, checks for 'npx' as default."""
        data = {
            "agents": [
                {
                    "id": "a",
                    "runtime": "claude",
                    "mcp": [{"server": "github"}],
                }
            ]
        }

        def which_side_effect(cmd):
            return "/usr/bin/claude" if cmd == "claude" else None

        with patch("aqm.core.validate.shutil.which", side_effect=which_side_effect):
            warnings = check_resource_availability(data)
        mcp_warnings = [w for w in warnings if "npx" in w.message]
        assert len(mcp_warnings) == 1

    def test_empty_agents(self):
        """No warnings for empty agents list."""
        assert check_resource_availability({"agents": []}) == []

    def test_no_agents_key(self):
        """No crash when agents key missing."""
        assert check_resource_availability({}) == []

    def test_multiple_agents(self):
        """Warnings generated for each agent independently."""
        data = {
            "agents": [
                {"id": "a", "runtime": "claude"},
                {"id": "b", "runtime": "gemini"},
            ]
        }
        with patch("aqm.core.validate.shutil.which", return_value=None):
            warnings = check_resource_availability(data)
        runtime_warnings = [w for w in warnings if "Runtime" in w.message]
        assert len(runtime_warnings) == 2


# ---------------------------------------------------------------------------
# check_permissions
# ---------------------------------------------------------------------------


class TestCheckPermissions:

    def test_env_var_set(self):
        """No warning when referenced env var exists."""
        data = {
            "agents": [
                {
                    "id": "a",
                    "mcp": [{"server": "github", "env": {"TOKEN": "$GITHUB_TOKEN"}}],
                }
            ]
        }
        with patch.dict(os.environ, {"GITHUB_TOKEN": "abc123"}):
            warnings = check_permissions(data)
        assert warnings == []

    def test_env_var_missing(self):
        """Warning when referenced env var is not set."""
        data = {
            "agents": [
                {
                    "id": "a",
                    "mcp": [
                        {"server": "github", "env": {"TOKEN": "$MISSING_VAR"}}
                    ],
                }
            ]
        }
        with patch.dict(os.environ, {}, clear=True):
            warnings = check_permissions(data)
        assert len(warnings) == 1
        assert "MISSING_VAR" in warnings[0].message

    def test_env_var_braced_syntax(self):
        """Handles ${VAR} syntax."""
        data = {
            "agents": [
                {
                    "id": "a",
                    "mcp": [
                        {"server": "github", "env": {"KEY": "${MY_SECRET}"}}
                    ],
                }
            ]
        }
        with patch.dict(os.environ, {}, clear=True):
            warnings = check_permissions(data)
        assert len(warnings) == 1
        assert "MY_SECRET" in warnings[0].message

    def test_env_literal_no_warning(self):
        """Literal values (no $ prefix) should not trigger warnings."""
        data = {
            "agents": [
                {
                    "id": "a",
                    "mcp": [
                        {"server": "github", "env": {"KEY": "literal_value"}}
                    ],
                }
            ]
        }
        warnings = check_permissions(data)
        assert warnings == []

    def test_filesystem_path_exists(self):
        """No warning when filesystem path exists and is readable."""
        data = {
            "agents": [
                {
                    "id": "a",
                    "mcp": [
                        {
                            "server": "filesystem",
                            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                        }
                    ],
                }
            ]
        }
        with patch("os.path.exists", return_value=True), patch(
            "os.access", return_value=True
        ):
            warnings = check_permissions(data)
        assert warnings == []

    def test_filesystem_path_not_exists(self):
        """Warning when filesystem path does not exist."""
        data = {
            "agents": [
                {
                    "id": "a",
                    "mcp": [
                        {
                            "server": "filesystem",
                            "args": [
                                "-y",
                                "@modelcontextprotocol/server-filesystem",
                                "/nonexistent/path",
                            ],
                        }
                    ],
                }
            ]
        }
        with patch("os.path.exists", return_value=False):
            warnings = check_permissions(data)
        assert len(warnings) == 1
        assert "does not exist" in warnings[0].message

    def test_filesystem_path_not_readable(self):
        """Warning when filesystem path exists but is not readable."""
        data = {
            "agents": [
                {
                    "id": "a",
                    "mcp": [
                        {
                            "server": "filesystem",
                            "args": [
                                "-y",
                                "@modelcontextprotocol/server-filesystem",
                                "/restricted/path",
                            ],
                        }
                    ],
                }
            ]
        }
        with patch("os.path.exists", return_value=True), patch(
            "os.access", return_value=False
        ):
            warnings = check_permissions(data)
        assert len(warnings) == 1
        assert "not readable" in warnings[0].message

    def test_non_filesystem_server_skips_path_check(self):
        """Non-filesystem servers should not trigger path checks."""
        data = {
            "agents": [
                {
                    "id": "a",
                    "mcp": [
                        {
                            "server": "github",
                            "args": ["-y", "@modelcontextprotocol/server-github"],
                        }
                    ],
                }
            ]
        }
        warnings = check_permissions(data)
        assert warnings == []

    def test_no_mcp_no_warnings(self):
        """Agents without MCP produce no permission warnings."""
        data = {"agents": [{"id": "a", "runtime": "claude"}]}
        warnings = check_permissions(data)
        assert warnings == []

    def test_multiple_env_refs_in_value(self):
        """Multiple env var refs in a single value are each checked."""
        data = {
            "agents": [
                {
                    "id": "a",
                    "mcp": [
                        {
                            "server": "custom",
                            "env": {"URL": "https://$HOST:$PORT/api"},
                        }
                    ],
                }
            ]
        }
        with patch.dict(os.environ, {}, clear=True):
            warnings = check_permissions(data)
        names = {w.message.split("'")[1] for w in warnings}
        assert "HOST" in names
        assert "PORT" in names


# ---------------------------------------------------------------------------
# run_all_checks
# ---------------------------------------------------------------------------


class TestRunAllChecks:

    def test_combines_resource_and_permission_warnings(self):
        """run_all_checks returns warnings from both check types."""
        data = {
            "agents": [
                {
                    "id": "a",
                    "runtime": "claude",
                    "mcp": [
                        {
                            "server": "github",
                            "env": {"TOKEN": "$MISSING_TOKEN"},
                        }
                    ],
                }
            ]
        }
        with patch("aqm.core.validate.shutil.which", return_value=None), patch.dict(
            os.environ, {}, clear=True
        ):
            warnings = run_all_checks(data)
        # At least one resource warning (runtime) and one permission warning (env)
        messages = " ".join(w.message for w in warnings)
        assert "not found" in messages
        assert "not set" in messages

    def test_empty_data(self):
        """No crash on empty dict."""
        assert run_all_checks({}) == []


# ---------------------------------------------------------------------------
# ValidationWarning structure
# ---------------------------------------------------------------------------


class TestValidationWarning:

    def test_named_tuple_fields(self):
        w = ValidationWarning(
            level="warning",
            path="agents[0].runtime",
            message="test msg",
            fix="test fix",
        )
        assert w.level == "warning"
        assert w.path == "agents[0].runtime"
        assert w.message == "test msg"
        assert w.fix == "test fix"
