from __future__ import annotations

import asyncio
import importlib

from fastmcp import Client

from implementation.init_db import create_database


def load_server(tmp_path, monkeypatch):
    db_path = tmp_path / "mcp.db"
    create_database(db_path)
    monkeypatch.setenv("SQLITE_LAB_DB_PATH", str(db_path))
    import implementation.mcp_server as server
    return importlib.reload(server)


def test_mcp_discovery_and_happy_path(tmp_path, monkeypatch):
    server = load_server(tmp_path, monkeypatch)
    
    async def run_test():
        async with Client(server.mcp) as client:
            tools = await client.list_tools()
            assert [tool.name for tool in tools] == ["search", "insert", "aggregate"]

            resources = await client.list_resources()
            assert [str(resource.uri) for resource in resources] == ["schema://database"]

            templates = await client.list_resource_templates()
            assert [template.uriTemplate for template in templates] == ["schema://table/{table_name}"]

            search_result = await client.call_tool("search", {"table": "students"})
            assert search_result.data["count"] == 6

            aggregate_result = await client.call_tool(
                "aggregate",
                {"table": "enrollments", "metric": "avg", "column": "score", "group_by": ["cohort"]},
            )
            assert aggregate_result.data["rows"]

            schema = await client.read_resource("schema://table/students")
            assert "students" in schema[0].text

    asyncio.run(run_test())


def test_mcp_invalid_request_returns_error(tmp_path, monkeypatch):
    server = load_server(tmp_path, monkeypatch)

    async def run_test():
        async with Client(server.mcp) as client:
            result = await client.call_tool(
                "search",
                {"table": "students", "filters": [{"column": "bad", "operator": "eq", "value": 1}]},
                raise_on_error=False,
            )
            assert result.is_error is True
            assert "Unknown column 'bad'" in result.content[0].text

    asyncio.run(run_test())
