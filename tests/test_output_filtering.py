"""Tests for output filtering helpers.

Covers:
- _strip_cli_artifacts() in aqm/runtime/claude.py
- _extract_report() in aqm/core/context_file.py
"""

from __future__ import annotations

import pytest

from aqm.core.context_file import ContextFile
from aqm.runtime.claude import _strip_cli_artifacts


# ── _strip_cli_artifacts ──────────────────────────────────────────────


class TestStripCliArtifacts:
    def test_clean_text_unchanged(self):
        text = "This is a normal response.\nNo tool indicators here."
        assert _strip_cli_artifacts(text) == text

    def test_strips_arrow_tool_lines(self):
        text = "▶ Read(file.py)\nActual response text."
        result = _strip_cli_artifacts(text)
        assert "▶" not in result
        assert "Actual response text." in result

    def test_strips_result_indicator_lines(self):
        text = "⎿  result line\nActual response text."
        result = _strip_cli_artifacts(text)
        assert "⎿" not in result
        assert "Actual response text." in result

    def test_strips_checkmark_lines(self):
        text = "✓ Done\nActual response text."
        result = _strip_cli_artifacts(text)
        assert "✓" not in result
        assert "Actual response text." in result

    def test_strips_cross_lines(self):
        text = "✗ Failed\nActual response text."
        result = _strip_cli_artifacts(text)
        assert "✗" not in result
        assert "Actual response text." in result

    def test_strips_multiple_tool_lines_interspersed(self):
        text = (
            "▶ Read(aqm/core/pipeline.py)\n"
            "Now let me look at the code.\n"
            "▶ Bash(pytest tests/)\n"
            "IMPACT REPORT\n"
            "=============\n"
            "Feature: X\n"
        )
        result = _strip_cli_artifacts(text)
        assert "▶" not in result
        assert "IMPACT REPORT" in result
        assert "Now let me look at the code." in result

    def test_collapses_extra_blank_lines(self):
        text = "▶ Read\n\n▶ Bash\n\nActual content."
        result = _strip_cli_artifacts(text)
        # Should not have consecutive blank lines
        assert "\n\n\n" not in result
        assert "Actual content." in result

    def test_empty_string(self):
        assert _strip_cli_artifacts("") == ""

    def test_whitespace_only(self):
        assert _strip_cli_artifacts("   \n\n  ") == ""

    def test_all_artifact_lines(self):
        text = "▶ Read\n▶ Bash\n⎿  result\n✓ ok\n✗ fail"
        result = _strip_cli_artifacts(text)
        assert result == ""

    def test_indented_artifact_lines_stripped(self):
        # Indented lines with tool indicators should also be stripped
        text = "  ▶ Read(file.py)\nActual content."
        result = _strip_cli_artifacts(text)
        assert "▶" not in result
        assert "Actual content." in result

    def test_arrow_in_middle_of_line_preserved(self):
        # '▶' not at the start of a line should NOT be stripped
        text = "The flow is: A ▶ B ▶ C\nActual content."
        result = _strip_cli_artifacts(text)
        assert "A ▶ B ▶ C" in result

    def test_returns_stripped_result(self):
        text = "▶ Read\n\nActual content.\n\n"
        result = _strip_cli_artifacts(text)
        assert not result.startswith("\n")
        assert not result.endswith("\n")


# ── ContextFile._extract_report ───────────────────────────────────────


class TestExtractReport:
    def test_no_fenced_block_returns_original(self):
        text = "Plain text output with no code blocks."
        assert ContextFile._extract_report(text) == text

    def test_extracts_single_fenced_block(self):
        text = (
            "Let me analyze the codebase...\n"
            "```\n"
            "IMPACT REPORT\n"
            "=============\n"
            "Feature: X\n"
            "```\n"
        )
        result = ContextFile._extract_report(text)
        assert "IMPACT REPORT" in result
        assert "Let me analyze" not in result

    def test_extracts_multiple_fenced_blocks(self):
        text = (
            "Some narration.\n"
            "```\nBLOCK ONE\n```\n"
            "More narration.\n"
            "```\nBLOCK TWO\n```\n"
        )
        result = ContextFile._extract_report(text)
        assert "BLOCK ONE" in result
        assert "BLOCK TWO" in result
        assert "narration" not in result

    def test_fenced_block_with_language_hint(self):
        text = (
            "Prose text.\n"
            "```yaml\n"
            "key: value\n"
            "```\n"
        )
        result = ContextFile._extract_report(text)
        assert "key: value" in result
        assert "Prose text." not in result

    def test_empty_fenced_block_skipped(self):
        text = "Prose.\n```\n```\nMore prose."
        # Empty block → falls back to original
        result = ContextFile._extract_report(text)
        assert result == text

    def test_empty_string(self):
        assert ContextFile._extract_report("") == ""

    def test_structured_test_report_extracted(self):
        text = (
            "Let me run pytest now...\n"
            "Running tests...\n"
            "```\n"
            "TEST REPORT\n"
            "===========\n"
            "Status: PASS\n"
            "Pytest Exit Code: 0\n"
            "Regression: 42 passed, 0 failed\n"
            "```\n"
        )
        result = ContextFile._extract_report(text)
        assert "TEST REPORT" in result
        assert "Status: PASS" in result
        assert "Let me run pytest" not in result

    def test_structured_code_review_extracted(self):
        text = (
            "I'll review the git diff...\n"
            "▶ Bash(git diff main)\n"
            "Running tests...\n"
            "```\n"
            "CODE REVIEW\n"
            "===========\n"
            "Verdict: APPROVED\n"
            "```\n"
        )
        result = ContextFile._extract_report(text)
        assert "CODE REVIEW" in result
        assert "Verdict: APPROVED" in result
        assert "▶ Bash" not in result


# ── append_agent_context stores cleaned output ────────────────────────


class TestAppendAgentContextCleaning:
    def test_stores_extracted_report(self, tmp_path):
        cf = ContextFile(tmp_path / "task-1")
        raw_output = (
            "Now I will analyze the codebase.\n"
            "▶ Read(file.py)\n"
            "```\n"
            "IMPACT REPORT\n"
            "Feature: X\n"
            "```\n"
        )
        cf.append_agent_context(
            agent_id="impact_analyzer",
            stage_number=1,
            input_text="Add feature X",
            output_text=raw_output,
        )
        stored = cf.read_agent_context("impact_analyzer")
        assert "IMPACT REPORT" in stored
        assert "Now I will analyze" not in stored
        assert "▶ Read" not in stored

    def test_stores_plain_output_unchanged(self, tmp_path):
        cf = ContextFile(tmp_path / "task-1")
        plain_output = "- modified aqm/core/agent.py\n- added tests/test_x.py"
        cf.append_agent_context(
            agent_id="implementer",
            stage_number=2,
            input_text="Implement feature X",
            output_text=plain_output,
        )
        stored = cf.read_agent_context("implementer")
        assert "modified aqm/core/agent.py" in stored
        assert "added tests/test_x.py" in stored

    def test_context_md_stores_full_output(self, tmp_path):
        """context.md (shared) should still store the full output, not the cleaned version."""
        cf = ContextFile(tmp_path / "task-1")
        raw_output = (
            "Analyzing...\n"
            "```\nIMPACT REPORT\n```\n"
        )
        cf.append_stage(
            stage_number=1,
            agent_id="impact_analyzer",
            task_name="test",
            status="completed",
            input_text="request",
            output_text=raw_output,
        )
        shared = cf.read()
        # Full output including narration is in context.md
        assert "Analyzing..." in shared
        assert "IMPACT REPORT" in shared
