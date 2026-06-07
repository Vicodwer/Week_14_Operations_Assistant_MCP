# Decision Log — Operations Assistant

This log records every significant choice made during the build:
what was tried, what was chosen, and what was rejected — with reasons.

---

## Architecture

### MCP transport: stdio over SSE
**Considered:** SSE (Server-Sent Events) over HTTP — runs the server as a
persistent process on a port, clients connect over HTTP.
**Chosen:** stdio — the server is a subprocess, communication over stdin/stdout.
**Reason:** stdio requires zero network configuration and runs identically on
any machine from a fresh clone. SSE requires a running HTTP server, port
management, and firewall rules — no benefit for a local laptop project.
**Trade-off:** stdio means the server starts and stops with each crew run.
For production, SSE would be better for a persistent shared server.

### MCP library: FastMCP (official SDK)
**Considered:** Building raw JSON-RPC over stdio manually.
**Chosen:** `FastMCP` from the official `mcp` SDK.
**Reason:** FastMCP handles protocol framing, tool registration, and resource
listing with decorator syntax. The manual approach would add ~200 lines of
boilerplate with no learning benefit for this project.

### CrewAI MCP bridge: MCPAdapt
**Considered:** `crewai-tools[mcp]` (MCPServerAdapter), direct tool import.
**Chosen:** `MCPAdapt + CrewAIAdapter` from the `mcpadapt` package.
**Reason:** MCPServerAdapter had import errors in the installed version.
MCPAdapt worked on first try and exposed the same interface. Direct import
bypasses the MCP protocol entirely — defeats the purpose of the assignment.

### Agent pattern: factory functions over module globals
**Considered:** Defining `researcher` and `writer` as global variables in
`agents.py`, imported by `tasks.py` and `crew_runner.py`.
**Chosen:** `make_agents(mcp_tools)` factory function called inside the
MCPAdapt context manager.
**Reason:** Globals are created at import time — before the MCP context is
open and tools exist. Factory functions ensure agents receive live, connected
tool objects. Also makes the dependency explicit rather than hidden.

### Search: keyword matching over vector/semantic search
**Considered:** `sentence-transformers` for semantic embeddings, FAISS index.
**Chosen:** Simple keyword split — `any(term in content.lower() for term in query_terms)`.
**Reason:** The corpus is 10 small documents totalling ~12 KB. Semantic search
adds a 500 MB model download and 2-3 second startup for negligible quality
improvement at this scale. Keyword search is transparent and debuggable.
**Upgrade path:** Replace with FAISS + MiniLM-L6 for corpora above ~100 documents.

---

## Agent and task design

### save_report called from crew_runner.py, not by the Writer agent

**Problem:** Every prompting technique failed to make `llama3.2:3b` reliably
call `save_report` at the end of the write task:

| Attempt | Result |
|---|---|
| Task description: "call save_report" | Model printed JSON text of the call |
| expected_output showing SUCCESS string | Model still printed JSON |
| Goal: "not done until save_report returns SUCCESS" | Model called wrong tools (read_record, search_documents) |
| Separate the save into a third task | Added complexity, same failure mode |

**Root cause:** `llama3.2:3b` (3 billion parameters) handles retrieval tool
calls reliably when the task is focused (one tool, one purpose). It fails at
multi-step orchestration (write content AND call a side-effect tool).

**Decision:** Writer produces markdown text. `crew_runner.py` saves the file
after `kickoff()` returns. The `save_report` tool still exists, is tested
directly in `test_tools.py`, and the MCP architecture requirement is met.

**Documented trade-off:** This is a model capability limitation, not an
architectural flaw. A 7B+ instruction-tuned model would handle this correctly.

### Two agents, not three
**Considered:** Researcher, Writer, Validator (checks claims against evidence).
**Chosen:** Researcher + Writer only for the core submission.
**Reason:** Time constraint. The Validator is the highest-value next step —
it would have caught the customer name hallucination (see reflection.md).

### max_iter limits
**Chosen:** `max_iter=6` for Researcher, `max_iter=4` for Writer.
**Reason:** Researcher needs up to 4 tool calls plus reasoning steps (6 is safe).
Writer produces text only — more than 4 iterations means something went wrong.
Without limits, a confused small model can loop indefinitely consuming tokens.

---

## Security decisions

### Input validation approach: fail loudly, not silently
**Considered:** Sanitise bad input and proceed (e.g. strip `..` from path and save).
**Rejected:** Silent sanitisation hides attacks. The server returned `SUCCESS`
on `save_report("../../etc/passwd", ...)` — technically safe (file stayed in
`outputs/`) but misleading. A caller has no way to know the title was mangled.
**Chosen:** Validate first, return `ERROR` on bad input, never sanitise silently.
**Evidence:** VULN-01 in `security_review.md` was caught by this principle.

### Prompt injection: data-layer defence
**Attack:** A document in the corpus contains `IGNORE ALL PREVIOUS INSTRUCTIONS`.
**Defence:** The MCP server is a Python function, not an LLM. It returns document
text as a string — it cannot execute instructions found in content. The injected
text arrives at the agent labelled as a tool result, framed as data.
**Residual risk:** The agent (LLM) may still act on injected instructions.
Mitigated by testing; not fully solvable at the server layer.

### Human approval gate: added for Stretch 2
**Reason:** Any system that writes files on behalf of an LLM should require
explicit human sign-off before doing so. A hallucinated report should not be
saved silently.
**Implementation:** `_save_report(auto_approve=False)` pauses with a preview.
Tests pass `auto_approve=True` to skip the prompt.

---

## What was tried and rejected

| Thing tried | Why rejected |
|---|---|
| MCP Inspector to test server | Could not connect on Windows with venv Python — used direct function calls in tests instead |
| Global agent/task imports | Agents created before MCP context open — no live tools |
| Asking Writer to call save_report | llama3.2:3b prints JSON instead of invoking tool |
| phi3:latest as alternative model | llama3.2:3b worked once Writer task was simplified |
| pip freeze for requirements.txt | Too many transitive packages — replaced with curated list |