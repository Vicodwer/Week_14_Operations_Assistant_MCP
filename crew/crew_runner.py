"""
crew/crew_runner.py

Stretch 2 — Human Approval Gate:
    _save_report() pauses and asks for confirmation before writing any file.
    Pass auto_approve=True in tests to skip the prompt.

Stretch 3 — Observability:
    Every run saves an enhanced JSON trace to traces/ containing duration,
    tool inventory, section count, token estimate, and approval outcome.

Usage:
    python -m crew.crew_runner              # default: ORD1005, asks for approval
    python -m crew.crew_runner ORD1008      # any order ID
"""

import json
import pathlib
import re
import sys
from datetime import datetime

from dotenv import load_dotenv
from crewai import Crew, Process
from mcpadapt.core import MCPAdapt
from mcpadapt.crewai_adapter import CrewAIAdapter
from mcp import StdioServerParameters

from crew.agents import make_agents
from crew.tasks  import make_tasks

load_dotenv()

# ── paths ──────────────────────────────────────────────────────────────────────
ROOT       = pathlib.Path(__file__).resolve().parent.parent
PYTHON_EXE = ROOT / "venv" / "Scripts" / "python.exe"
SERVER_PY  = ROOT / "mcp_server" / "server.py"
TRACES_DIR = ROOT / "traces"
OUTPUT_DIR = ROOT / "outputs"
TRACES_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

if not PYTHON_EXE.exists():
    PYTHON_EXE = pathlib.Path(sys.executable)


# ══════════════════════════════════════════════════════════════════════════════
# STRETCH 3 — Observability helpers
# ══════════════════════════════════════════════════════════════════════════════

def _count_sections(markdown: str) -> int:
    """Count ## headings in a markdown report."""
    return sum(1 for line in markdown.splitlines() if line.startswith("## "))


def _count_cited_docs(markdown: str) -> list[str]:
    """Return list of .txt filenames cited anywhere in the report."""
    return re.findall(r'[\w_]+\.txt', markdown)


def _estimate_tokens(text: str) -> int:
    """
    Rough token estimate: ~4 characters per token (GPT-style).
    Not exact — used for observability only, not billing.
    """
    return max(1, len(text) // 4)


# ══════════════════════════════════════════════════════════════════════════════
# STRETCH 2 — Human Approval Gate
# ══════════════════════════════════════════════════════════════════════════════

def _save_report(title: str, content: str, auto_approve: bool = False) -> str:
    """
    Write the finished report to output/.

    Stretch 2: Pauses for human approval before writing unless
    auto_approve=True (used in automated tests).

    Why here instead of inside the agent:
      llama3.2:3b reliably produces markdown but fails at multi-step
      tool orchestration. Saving here is more reliable.
      Documented in decision_log.md.
    """
    safe_name   = re.sub(r'[^\w\s-]', '', title)
    safe_name   = re.sub(r'\s+', '_', safe_name).lower().strip('_-') or "report"
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename    = f"{safe_name}_{timestamp}.md"
    output_path = OUTPUT_DIR / filename

    # ── human approval gate (Stretch 2) ───────────────────────────────────
    if not auto_approve:
        print(f"\n{'─' * 60}")
        print("⚠️   APPROVAL REQUIRED before saving report")
        print(f"     Title   : {title}")
        print(f"     File    : {filename}")
        print(f"     Size    : {len(content):,} characters")
        print(f"     Sections: {_count_sections(content)}")
        print(f"\n     Preview :\n")
        # show first 300 chars of the report
        for line in content[:300].splitlines():
            print(f"       {line}")
        print(f"\n{'─' * 60}")

        answer = input("Save this report? [yes/no]: ").strip().lower()

        if answer not in ("yes", "y"):
            print("❌  Save cancelled.")
            return "CANCELLED: Report not saved — human approval denied."

        print("✅  Approved.")

    output_path.write_text(content, encoding="utf-8")
    return (
        f"SUCCESS: Report saved.\n"
        f"  File : {output_path}\n"
        f"  Size : {len(content):,} characters"
    )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_crew(order_id: str = "ORD1005", auto_approve: bool = False) -> str:
    """
    Connect to MCP server, run the crew, get human approval,
    save the report, and write an enhanced trace.
    """
    server_params = StdioServerParameters(
        command=str(PYTHON_EXE),
        args=[str(SERVER_PY)],
    )

    print(f"\n🔌  Connecting to MCP server...")

    with MCPAdapt(server_params, CrewAIAdapter()) as mcp_tools:

        discovered = [t.name for t in mcp_tools]
        print(f"✅  Connected — tools: {discovered}\n")

        researcher, writer = make_agents(mcp_tools)
        research_task, write_task = make_tasks(researcher, writer, order_id)

        crew = Crew(
            agents=[researcher, writer],
            tasks=[research_task, write_task],
            process=Process.sequential,
            verbose=True,
        )

        # ── run ───────────────────────────────────────────────────────────
        start  = datetime.now()
        result = crew.kickoff()
        finish = datetime.now()
        duration = round((finish - start).total_seconds(), 2)

    # ── save with human approval (Stretch 2) ──────────────────────────────
    report_content = str(result)
    save_msg = _save_report(
        title        = f"{order_id} Delay Investigation",
        content      = report_content,
        auto_approve = auto_approve,
    )
    print(f"\n{save_msg}")

    # ── enhanced trace (Stretch 3) ────────────────────────────────────────
    cited_docs = _count_cited_docs(report_content)
    trace = {
        "schema_version"   : "2.0",
        "order_id"         : order_id,
        "started_at"       : start.isoformat(),
        "finished_at"      : finish.isoformat(),
        "duration_seconds" : duration,

        # tool inventory
        "tools_discovered" : discovered,
        "tools_count"      : len(discovered),

        # report quality metrics
        "report_chars"     : len(report_content),
        "report_sections"  : _count_sections(report_content),
        "cited_documents"  : list(set(cited_docs)),
        "cited_doc_count"  : len(set(cited_docs)),

        # token estimates (rough: ~4 chars per token)
        "estimated_input_tokens"  : _estimate_tokens(report_content) * 3,
        "estimated_output_tokens" : _estimate_tokens(report_content),

        # approval outcome (Stretch 2)
        "human_approval"   : "auto" if auto_approve else (
            "approved" if "SUCCESS" in save_msg else "denied"
        ),

        "save_result"      : save_msg,
        "report_preview"   : report_content[:500],
    }

    trace_path = TRACES_DIR / f"trace_{start.strftime('%Y%m%d_%H%M%S')}.json"
    trace_path.write_text(json.dumps(trace, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    print(f"📝  Trace saved → {trace_path}")

    # ── print trace summary (Stretch 3) ──────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"  RUN SUMMARY")
    print(f"{'─' * 60}")
    print(f"  Order ID         : {order_id}")
    print(f"  Duration         : {duration}s")
    print(f"  Tools available  : {', '.join(discovered)}")
    print(f"  Report sections  : {trace['report_sections']}")
    print(f"  Documents cited  : {', '.join(trace['cited_documents']) or 'none detected'}")
    print(f"  Est. tokens used : ~{trace['estimated_input_tokens'] + trace['estimated_output_tokens']:,}")
    print(f"  Approval         : {trace['human_approval']}")
    print(f"{'═' * 60}\n")

    return report_content


if __name__ == "__main__":
    order       = sys.argv[1] if len(sys.argv) > 1 else "ORD1005"
    run_crew(order_id=order, auto_approve=False)