from crewai.tools import tool
from mcp_server.server import (
    search_documents,
    read_record,
    save_report
)


@tool("Search Documents")
def search_docs_tool(query: str) -> str:
    """Search company documents."""
    return search_documents(query)


@tool("Read Order Record")
def read_order_tool(order_id: str) -> str:
    """Read order information."""
    return read_record(order_id)


@tool("Save Report")
def save_report_tool(title: str, content: str) -> str:
    """Save report to output folder."""
    return save_report(title, content)
