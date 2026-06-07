# Reflection — Operations Assistant

## Why these tools and agent roles?

`search_documents` and `read_record` map directly to how a real ops team stores
knowledge: free-text documents for policies and history, a spreadsheet for
transactional records. Separating them into two tools keeps each function small
and testable. `save_report` closes the loop — the crew produces a durable artifact,
not just a terminal printout.

Two agents with clear roles (Researcher, Writer) work better than one general agent
because the tasks require opposite behaviours: the Researcher must stay strictly
within tool output and never invent, while the Writer must synthesise and structure.
One agent trying to do both produced less grounded output in early tests.

Alternatives considered: a third Validator agent to check claims against evidence.
Rejected for time, but documented in the decision log as the most valuable next step.

## What broke first when connecting the crew to the server?

Two things broke immediately:

**1. OPENAI_API_KEY is required.**
When I refactored agents into a factory function and removed the explicit `llm=`
parameter, CrewAI defaulted to the OpenAI provider. Fix: add
`LLM(model="ollama/llama3.2:3b", base_url="http://localhost:11434")` explicitly
to every agent. Lesson: never rely on environment defaults when the LLM config
is critical to the project working at all.

**2. Model not found: llama3.2.**
The model name in `.env` was `ollama/llama3.2` but Ollama requires the full tag
`ollama/llama3.2:3b`. Fix: `ollama list` showed the exact name. Lesson: always
check `ollama list` before configuring — the tag is part of the identifier.

## One answer the crew got wrong

On the first successful ORD1005 run, the Writer agent reported the customer name
as "John Doe" even though `read_record` returned "Eva" as the customer field.

The Researcher correctly cited `orders.csv → ORD1005`. The hallucination occurred
when the Writer summarised the Researcher's output — it substituted a plausible
name rather than copying the exact value.

**Why it slipped through:** the Writer receives the Researcher's summary, not raw
tool output. A small model will paraphrase when it should copy verbatim.

**Guardrail that partially worked:** the source citation (`orders.csv → ORD1005`)
was present. A human reading the report could check the order record and catch
the wrong name.

**What would fully fix it:** pass raw tool output directly to the Writer as
structured context, and add an explicit instruction: "copy customer name exactly
from the evidence — do not paraphrase proper nouns."

## Biggest security risk and how it was reduced

**Risk: path traversal in `save_report`.**

The initial implementation sanitised the title by removing special characters.
This silently converted `"../../etc/passwd"` to `"etcpasswd.md"` and saved it
inside `outputs/` — the file stayed in the right folder, but the server returned
`SUCCESS` on a malicious input. This was caught by the prompt injection test suite.

**How it was found:** a test passed `"../../etc/passwd"` as the title and asserted
`ERROR` in the result. The assertion failed — proving the bug existed.

**Fix (two layers):**
1. Explicit check before sanitisation: if `..`, `/`, or `\` appear in the raw
   title, return `ERROR` immediately.
2. Path resolution guard: resolve the full output path and verify it starts with
   `OUTPUT_PATH.resolve()` before writing.

**What remains:** the MCP server has no authentication — any local process that
knows the command can connect. For real company data, the server would need
mutual authentication and audit logging on every tool call.

## What I would change before letting this touch real company data

1. **Replace keyword search with vector search.** Keyword matching misses synonyms
   and paraphrases. FAISS or ChromaDB with a small embedding model would
   dramatically improve recall without adding much latency.

2. **Add a Validator agent.** A third agent reads the final report, checks every
   claim against the raw tool outputs, and flags anything not directly supported
   by evidence. The hallucinated customer name would have been caught here.

3. **Require human approval for every data-changing action** — currently only
   `save_report` is gated. In a real system, any write operation (updating a
   ticket, sending an email) would need explicit human sign-off.

4. **Authenticate the MCP server.** Add mutual TLS or a shared secret so only
   authorised crew processes can connect. Log every tool call with a timestamp
   and caller identity.

5. **Upgrade the model.** `llama3.2:3b` hallucinates proper nouns and struggles
   with multi-step tool orchestration. A model with stronger instruction-following
   (or a fine-tuned tool-use model) is necessary before trusting the output
   without human review.