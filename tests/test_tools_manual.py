from mcp_server.server import (
    search_documents,
    read_record,
    save_report
)

print("=" * 50)

print(search_documents("delay"))

print("=" * 50)

print(read_record("ORD1005"))

print("=" * 50)

print(save_report(
    "test_report",
    "This is a test report"
))