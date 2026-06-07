from mcpadapt.core import MCPAdapt
from mcpadapt.crewai_adapter import CrewAIAdapter
from mcp import StdioServerParameters

server = StdioServerParameters(
    command=r"C:\Users\Vishal\operations-assistant\venv\Scripts\python.exe",
    args=[r"C:\Users\Vishal\operations-assistant\mcp_server\server.py"]
)

with MCPAdapt(server, CrewAIAdapter()) as tools:
    print("Connected!")
    print("Number of tools:", len(tools))

    for tool in tools:
        print(tool.name)