"""
crew/tasks.py
"""
from crewai import Task


def make_tasks(researcher, writer, order_id: str = "ORD1005"):

    research_task = Task(
        description=f"""
Investigate order {order_id} for NovaTech Supplies.

Call these tools IN THIS ORDER:

1. read_record
   order_id = "{order_id}"

2. search_documents
   query = "{order_id}"

3. search_documents
   query = "delay inventory shortage"

4. search_documents
   query = "shipping policy"

Based ONLY on tool outputs, determine:
- Current order status
- Whether there is an inventory issue
- The cause of any delay
- All supporting evidence (name the source for every fact)

Never use outside knowledge. Never invent facts.
""",
        expected_output=(
            "A structured evidence report containing:\n"
            "• Order status (from orders record)\n"
            "• Inventory issue: yes/no and reason\n"
            "• Cause of delay (from ticket or policy doc)\n"
            "• Evidence list: every document name and order ID cited"
        ),
        agent=researcher,
    )

    # ── Writer task: produce markdown text ONLY ───────────────────────────
    # We do NOT ask the small model to call save_report here.
    # llama3.2:3b reliably produces text but mixes up tool calls when
    # asked to write + call a tool in one step.
    # crew_runner.py saves the output after kickoff() — see decision log.
    write_task = Task(
        description=f"""
Using ONLY the research findings from the previous task, write a markdown report.

The report MUST contain ALL of these sections with real content:

# {order_id} — Investigation Report

## Executive Summary
One paragraph summarising the finding.

## Order Status
State the order status and customer name from the order record.

## Cause of Delay
Explain the delay using evidence from the documents.

## Relevant Policy
Quote the relevant shipping or inventory policy that applies.

## Evidence Used
List every document name and order ID that was cited. Example:
- orders.csv → {order_id}
- support_ticket_1.txt
- shipping_policy.txt
- inventory_policy.txt

## Conclusion
One paragraph conclusion with next steps.

Write the complete markdown. Every claim must name its source document.
Do not call any tools. Just write the report text.
""",
        expected_output=(
            "A complete markdown report with all 6 sections filled in. "
            "Every factual claim cites a document name or order ID."
        ),
        agent=writer,
        context=[research_task],
    )

    return research_task, write_task