from mcp.server.fastmcp import FastMCP
from pathlib import Path
import pandas as pd
import re

mcp = FastMCP("OperationsAssistant")

# ── absolute project paths ────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
DOCS_PATH   = BASE_DIR / "data" / "docs"
ORDERS_CSV  = BASE_DIR / "data" / "orders.csv"
OUTPUT_PATH = BASE_DIR / "outputs"
OUTPUT_PATH.mkdir(exist_ok=True)


@mcp.tool()
def search_documents(query: str) -> str:
    """Search all documents for matching text."""

    # ── input validation ──────────────────────────────────────────────────────
    # Inputs come from an LLM — validate strictly before using them.
    if not query or not query.strip():
        return "ERROR: 'query' must be a non-empty string."
    query = query.strip()
    if len(query) < 3:
        return "ERROR: Query too short — provide at least 3 characters."
    if len(query) > 500:
        return "ERROR: Query too long — keep it under 500 characters."

    # ── search ────────────────────────────────────────────────────────────────
    results     = []
    query_terms = query.lower().split()

    for file in DOCS_PATH.glob("*.txt"):
        content = file.read_text(encoding="utf-8")
        if any(term in content.lower() for term in query_terms):
            results.append(f"\nDocument: {file.name}\n{content}")

    if not results:
        return "NO RESULTS: No documents matched your query. Try different keywords."

    return "\n".join(results)


@mcp.tool()
def read_record(order_id: str) -> str:
    """Read an order record from CSV by order ID."""

    # ── input validation ──────────────────────────────────────────────────────
    if not order_id or not order_id.strip():
        return "ERROR: 'order_id' must be a non-empty string."

    order_id = order_id.strip().upper()   # normalise: ord1005 → ORD1005

    if not re.match(r'^ORD\d{1,6}$', order_id):
        return (
            f"ERROR: Invalid format '{order_id}'. "
            "Expected ORD followed by numbers (e.g. ORD1005)."
        )

    # ── lookup ────────────────────────────────────────────────────────────────
    try:
        df    = pd.read_csv(ORDERS_CSV)
        match = df[df["order_id"].str.upper() == order_id]   # case-safe compare

        if match.empty:
            return f"NOT FOUND: No order with ID '{order_id}' in orders.csv."

        return match.to_string(index=False)

    except Exception as e:
        return f"ERROR: Could not read orders file — {e}"


@mcp.tool()
def save_report(title: str, content: str) -> str:
    """Save a markdown report to the outputs folder."""

    # ── input validation ──────────────────────────────────────────────────────
    if not title or not title.strip():
        return "ERROR: 'title' must be a non-empty string."
    if not content or not content.strip():
        return "ERROR: 'content' must be non-empty."
    title = title.strip()
    if len(title) > 100:
        return "ERROR: title too long — max 100 characters."
    if len(content) > 50_000:
        return "ERROR: content too long — max 50,000 characters."
    
    # ── reject path traversal characters in the raw title ────────────────────
    # Sanitizing silently is not enough — fail loudly so the caller knows
    # the title was rejected, not mangled.
    if any(bad in title for bad in ('..', '/', '\\')):
        return "ERROR: Title contains invalid characters ('..', '/', '\\' not allowed)."

    # ── sanitize filename (block path traversal attacks) ──────────────────────
    # An LLM could pass "../../etc/passwd" as a title.
    # Strip everything except word chars, spaces, and hyphens.
    safe_name = re.sub(r'[^\w\s-]', '', title)
    safe_name = re.sub(r'\s+', '_', safe_name).lower().strip('_-') or "report"
    filename  = f"{safe_name}.md"

    output_path = (OUTPUT_PATH / filename).resolve()

    # Final guard: resolved path must stay inside OUTPUT_PATH
    if not str(output_path).startswith(str(OUTPUT_PATH.resolve())):
        return "ERROR: Unsafe file path detected. Report not saved."

    output_path.write_text(content, encoding="utf-8")
    return (
        f"SUCCESS: Report saved.\n"
        f"  File : {output_path}\n"
        f"  Size : {len(content)} characters"
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")