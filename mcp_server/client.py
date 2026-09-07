import asyncio

from fastmcp import Client
from fastmcp.client.transports import SSETransport


SERVER_URL = "http://127.0.0.1:8000/sse"


async def main():
    # Connect to the FastMCP SSE server
    transport = SSETransport(url=SERVER_URL)
    client = Client(transport)

    async with client:
        print("Connected to MCP server!")

        # List available tools
        tools = await client.list_tools()

        print("\nAvailable tools:")
        for tool in tools:
            print(f"- {tool.name}")

        # Ask for an order ID
        record_id = input("\nEnter order record ID: ").strip()

        # Call your MCP tool
        result = await client.call_tool(
            "check_order_status",
            {
                "record_id": record_id
            }
        )

        print("\nResult:")
        print(result)


if __name__ == "__main__":
    asyncio.run(main())