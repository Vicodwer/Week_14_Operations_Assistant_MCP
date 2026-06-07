"""
crew/agents.py
"""
import os
from crewai import Agent, LLM
from dotenv import load_dotenv

load_dotenv()

_llm = LLM(
    model=os.getenv("OLLAMA_MODEL", "ollama/llama3.2:3b"),
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
)


def make_agents(mcp_tools: list):
    by_name = {t.name: t for t in mcp_tools}
    missing = [n for n in ("search_documents", "read_record", "save_report")
               if n not in by_name]
    if missing:
        raise RuntimeError(f"MCP server missing tools: {missing}. Found: {list(by_name)}")

    search_tool = by_name["search_documents"]
    read_tool   = by_name["read_record"]
    # save_report exists on the server and is tested directly.
    # crew_runner.py calls it after kickoff() — see decision log.

    researcher = Agent(
        role="Research Analyst",
        goal=(
            "Retrieve facts from NovaTech documents and order records. "
            "Cite every fact by its source document name or order ID. "
            "Never state anything that was not returned by a tool."
        ),
        backstory=(
            "You are a meticulous research analyst for NovaTech Supplies. "
            "You retrieve evidence from the knowledge base and report it "
            "verbatim — you never embellish or invent."
        ),
        tools=[search_tool, read_tool],
        llm=_llm,
        max_iter=6,
        verbose=True,
    )

    writer = Agent(
        role="Report Writer",
        goal=(
            "Write a clear, sourced markdown report using ONLY the research "
            "findings provided. Every claim must cite a document name or order ID."
        ),
        backstory=(
            "You write professional business reports. "
            "Every claim cites a document or order ID. "
            "You write markdown text — nothing else."
        ),
        tools=[],      # no tools: writer just produces text
        llm=_llm,
        max_iter=3,
        verbose=True,
    )

    return researcher, writer