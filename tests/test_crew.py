"""
tests/test_crew.py
End-to-end test: runs the full crew on a fixed question.
auto_approve=True skips the human gate — safe for automated testing.

Run: python -m pytest tests/test_crew.py -v -s
(takes ~2 minutes — runs Ollama)
"""
import pathlib
import sys
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from crew.crew_runner import run_crew, OUTPUT_DIR


def test_crew_produces_sourced_report():
    """
    Full pipeline: crew investigates ORD1005, report saved to output/.
    Checks file created, required sections present, at least one citation.
    """
    initial_files = set(OUTPUT_DIR.glob("*.md"))

    # auto_approve=True → skips human gate in automated test
    result = run_crew("ORD1005", auto_approve=True)

    new_files = set(OUTPUT_DIR.glob("*.md")) - initial_files
    assert len(new_files) == 1, "Expected exactly one new report file"

    report = list(new_files)[0].read_text(encoding="utf-8")

    assert "## Executive Summary" in report
    assert "## Order Status"      in report
    assert "## Evidence Used"     in report
    assert "## Conclusion"        in report

    # at least one source cited
    assert any(s in report for s in (".txt", "orders.csv", "ORD1005"))

    assert "I cannot"    not in report
    assert "I don't know" not in report