"""
tests/test_tools.py
Unit tests — call MCP tool functions directly, no protocol overhead.
Run: python -m pytest tests/test_tools.py -v
"""
import sys
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcp_server.server import search_documents, read_record, save_report


class TestSearchDocuments:

    def test_valid_query_returns_results(self):
        result = search_documents("shipping policy delay")
        assert "shipping_policy.txt" in result
        assert "ERROR" not in result

    def test_returns_document_name_in_output(self):
        result = search_documents("inventory shortage")
        assert ".txt" in result

    def test_empty_query_returns_error(self):
        assert "ERROR" in search_documents("")

    def test_whitespace_only_returns_error(self):
        assert "ERROR" in search_documents("   ")

    def test_too_short_query_returns_error(self):
        assert "ERROR" in search_documents("ab")

    def test_no_match_returns_no_results_message(self):
        result = search_documents("xyzzy irrelevant gibberish zzz")
        assert "NO RESULTS" in result or "no" in result.lower()

    def test_query_too_long_returns_error(self):
        assert "ERROR" in search_documents("x" * 501)


class TestReadRecord:

    def test_valid_order_returns_data(self):
        result = read_record("ORD1005")
        assert "ORD1005" in result
        assert "ERROR" not in result

    def test_result_contains_status(self):
        result = read_record("ORD1005")
        assert "Delayed" in result or "status" in result.lower()

    def test_wrong_format_returns_error(self):
        assert "ERROR" in read_record("INVALID-ID")

    def test_empty_string_returns_error(self):
        assert "ERROR" in read_record("")

    def test_nonexistent_order_returns_not_found(self):
        result = read_record("ORD9999")
        assert "NOT FOUND" in result

    def test_lowercase_normalised_to_uppercase(self):
        # server now normalises ord1005 → ORD1005 before lookup
        result = read_record("ord1005")
        assert "ORD1005" in result and "ERROR" not in result


class TestSaveReport:

    def test_saves_file_and_returns_success(self, tmp_path, monkeypatch):
        import mcp_server.server as srv
        monkeypatch.setattr(srv, "OUTPUT_PATH", tmp_path)  # ← OUTPUT_PATH not OUTPUT_DIR
        result = save_report("Test Report", "# Hello\nThis is a test.")
        assert "SUCCESS" in result
        assert len(list(tmp_path.glob("*.md"))) == 1

    def test_saved_file_contains_content(self, tmp_path, monkeypatch):
        import mcp_server.server as srv
        monkeypatch.setattr(srv, "OUTPUT_PATH", tmp_path)
        save_report("Content Check", "# My Report\nHello world.")
        content = list(tmp_path.glob("*.md"))[0].read_text(encoding="utf-8")
        assert "Hello world" in content

    def test_empty_title_returns_error(self):
        assert "ERROR" in save_report("", "Some content")

    def test_empty_content_returns_error(self):
        assert "ERROR" in save_report("Valid Title", "")

    def test_title_too_long_returns_error(self):
        assert "ERROR" in save_report("x" * 101, "content")

    def test_path_traversal_blocked(self, tmp_path, monkeypatch):
        import mcp_server.server as srv
        monkeypatch.setattr(srv, "OUTPUT_PATH", tmp_path)
        save_report("../../evil", "malicious content")
        # nothing written outside tmp folder
        assert not (ROOT / "evil.md").exists()