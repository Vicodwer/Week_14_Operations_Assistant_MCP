"""
tests/test_prompt_injection.py
Security test: a hidden malicious instruction inside a document must not
change the tool's behaviour or be executed.

This tests the 'prompt injection' threat: an attacker embeds instructions
inside content that an LLM will read, hoping the LLM treats them as commands.

Our defence: the MCP server is just a Python function. It returns document
TEXT to the agent — it does not execute instructions found in documents.
The agent sees the malicious text as data, not commands.

Run: python -m pytest tests/test_prompt_injection.py -v
"""
import sys
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcp_server.server import search_documents, save_report


class TestPromptInjection:

    def test_malicious_document_returned_as_text_not_executed(self):
        """
        The poisoned document contains 'IGNORE ALL PREVIOUS INSTRUCTIONS'.
        The tool must return it as plain text — not act on it.
        """
        result = search_documents("T003 late delivery")

        # The text is returned — good, the tool surfaced it
        assert "T003" in result or "support_ticket_3" in result

        # The system was NOT taken over — outputs/ was not deleted
        outputs = list((ROOT / "outputs").glob("*.md"))
        # (if outputs/ is empty that is fine — what matters is it was not
        #  deleted by the injected instruction)
        assert (ROOT / "outputs").exists(), \
            "SECURITY FAIL: outputs/ was deleted by injected instruction"

    def test_injected_delete_instruction_not_executed(self):
        """The tool must not delete files even if a document says to."""
        # Create a dummy file first
        dummy = ROOT / "outputs" / "dummy_injection_test.md"
        dummy.write_text("safe content", encoding="utf-8")

        search_documents("delete all files output")   # triggers the poisoned doc

        assert dummy.exists(), \
            "SECURITY FAIL: injected 'delete' instruction was executed"
        dummy.unlink()   # clean up

    def test_injected_system_prompt_leak_not_executed(self):
        """Searching the poisoned doc must return text, not expose internals."""
        result = search_documents("ignore previous instructions")
        # Result is a document listing — not a system prompt dump
        assert "system prompt" not in result.lower() or "Document:" in result
        assert "ERROR" not in result or "NO RESULTS" in result or "support_ticket_3" in result

    def test_save_report_cannot_be_triggered_by_document_content(self):
        """
        An injected instruction telling the agent to 'save_report' with
        malicious content must be blocked by save_report's own validation.
        """
        # Simulate what would happen if the LLM tried to save a report
        # triggered by an injected instruction with a path-traversal title
        result = save_report("../../etc/passwd", "injected content")
        assert "ERROR" in result, \
            "SECURITY FAIL: path traversal in save_report was not blocked"