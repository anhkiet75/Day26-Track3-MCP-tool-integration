from __future__ import annotations

import asyncio

from fastmcp import Client

from db import ValidationError
from init_db import create_database
from mcp_server import DB_PATH, adapter, mcp


def show(title: str, payload: object) -> None:
    print(f"\n=== {title} ===")
    print(payload)


async def main() -> None:
    create_database(DB_PATH)
    async with Client(mcp) as client:
        show("tools", [tool.name for tool in await client.list_tools()])
        show("resources", [str(resource.uri) for resource in await client.list_resources()])
        show(
            "resource templates",
            [template.uriTemplate for template in await client.list_resource_templates()],
        )
        show(
            "search cohort A1",
            (await client.call_tool(
                "search",
                {"table": "students", "filters": [{"column": "cohort", "operator": "eq", "value": "A1"}]},
            )).data,
        )
        show(
            "insert student",
            (await client.call_tool(
                "insert",
                {"table": "students", "values": {"name": "Lan Bui", "cohort": "C3", "email": "lan@example.com"}},
            )).data,
        )
        show(
            "average score by cohort",
            (await client.call_tool(
                "aggregate",
                {"table": "enrollments", "metric": "avg", "column": "score", "group_by": ["cohort"]},
            )).data,
        )
        show("schema database", (await client.read_resource("schema://database"))[0].text)
        show("schema students", (await client.read_resource("schema://table/students"))[0].text)
        try:
            adapter.search("missing_table")
        except ValidationError as error:
            show("invalid request", {"error": str(error)})


if __name__ == "__main__":
    asyncio.run(main())
