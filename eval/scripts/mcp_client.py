import asyncio
import json
from pathlib import Path
from datetime import datetime

from fastmcp import Client
from fastmcp.client.transports import SSETransport


# --------------------------------------------------
# Configuration
# --------------------------------------------------

SERVER_URL = "http://127.0.0.1:8000/sse"

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR /"golden"/"record_ids.json"
RESULTS_FILE = BASE_DIR /"results"/"mcp_results.json"
DEMO_FILE = BASE_DIR /"insights"/"mcp_demonstration.txt"


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def load_record_ids():
    """Load record IDs from JSON file."""

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    record_ids = data.get("record_ids", [])

    if not record_ids:
        raise ValueError("No record_ids found in the JSON file.")

    return record_ids


def make_json_serializable(result):
    """Convert MCP result into JSON-serializable data."""

    # FastMCP/Pydantic objects
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")

    # Regular dictionaries/lists
    if isinstance(result, dict):
        return result

    if isinstance(result, list):
        return result

    # Fallback
    return str(result)


# --------------------------------------------------
# Main MCP client
# --------------------------------------------------

async def main():

    record_ids = load_record_ids()

    print("=" * 60)
    print("CARTMIND E-COMMERCE SUPPORT - MCP CLIENT")
    print("=" * 60)

    print(f"\nServer: {SERVER_URL}")
    print(f"Input file: {INPUT_FILE}")
    print(f"Record IDs: {record_ids}")

    # Create SSE transport
    transport = SSETransport(url=SERVER_URL)

    # Create MCP client
    client = Client(transport)

    all_results = []

    async with client:

        print("\n[1] Connected to MCP server successfully.")

        # ------------------------------------------
        # Discover available tools
        # ------------------------------------------

        tools = await client.list_tools()

        print("\n[2] Available MCP tools:")

        for tool in tools:
            print(f"    - {tool.name}")

        # ------------------------------------------
        # Process each record ID
        # ------------------------------------------

        print("\n[3] Calling check_order_status...")
        print("-" * 60)

        for record_id in record_ids:

            print(f"\nProcessing record: {record_id}")

            try:

                result = await client.call_tool(
                    "check_order_status",
                    {
                        "record_id": record_id
                    }
                )

                serialized_result = make_json_serializable(result)

                response = {
                    "record_id": record_id,
                    "success": True,
                    "server_response": serialized_result
                }

                all_results.append(response)

                print("Server response:")
                print(json.dumps(
                    serialized_result,
                    indent=4,
                    ensure_ascii=False
                ))

            except Exception as error:

                response = {
                    "record_id": record_id,
                    "success": False,
                    "error": str(error)
                }

                all_results.append(response)

                print(f"ERROR: {error}")

    # --------------------------------------------------
    # Save results
    # --------------------------------------------------

    output_data = {
        "project": "CartMind Agentic E-Commerce Support",
        "server_url": SERVER_URL,
        "processed_records": len(record_ids),
        "results": all_results
    }

    with open(
        RESULTS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output_data,
            file,
            indent=4,
            ensure_ascii=False
        )

    # --------------------------------------------------
    # Create demonstration report
    # --------------------------------------------------

    demo_lines = []

    demo_lines.append("=" * 70)
    demo_lines.append("CARTMIND AGENTIC E-COMMERCE SUPPORT")
    demo_lines.append("MCP SERVER DEMONSTRATION")
    demo_lines.append("=" * 70)

    demo_lines.append("")
    demo_lines.append(
        f"Execution time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    demo_lines.append("")
    demo_lines.append("ARCHITECTURE")
    demo_lines.append("-" * 70)
    demo_lines.append("1. JSON file contains customer/order record IDs")
    demo_lines.append("2. MCP client reads the record IDs")
    demo_lines.append("3. Client connects to FastMCP server using SSE")
    demo_lines.append("4. Client discovers available MCP tools")
    demo_lines.append("5. Client calls check_order_status for each record")
    demo_lines.append("6. MCP server queries the SQLite database")
    demo_lines.append("7. Server calculates the escalation score")
    demo_lines.append("8. Client receives and saves the server response")

    demo_lines.append("")
    demo_lines.append("SERVER")
    demo_lines.append("-" * 70)
    demo_lines.append(f"URL: {SERVER_URL}")

    demo_lines.append("")
    demo_lines.append("INPUT RECORDS")
    demo_lines.append("-" * 70)

    for record_id in record_ids:
        demo_lines.append(f"- {record_id}")

    demo_lines.append("")
    demo_lines.append("SERVER OUTPUT")
    demo_lines.append("-" * 70)

    for item in all_results:

        demo_lines.append("")
        demo_lines.append(
            f"Record ID: {item['record_id']}"
        )

        if item["success"]:

            demo_lines.append(
                json.dumps(
                    item["server_response"],
                    indent=4,
                    ensure_ascii=False
                )
            )

        else:

            demo_lines.append(
                f"ERROR: {item['error']}"
            )

    demo_lines.append("")
    demo_lines.append("=" * 70)
    demo_lines.append("DEMONSTRATION COMPLETE")
    demo_lines.append("=" * 70)

    with open(
        DEMO_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write("\n".join(demo_lines))

    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)

    print(f"\nResults saved to:")
    print(RESULTS_FILE)

    print(f"\nDemonstration saved to:")
    print(DEMO_FILE)


if __name__ == "__main__":
    asyncio.run(main())