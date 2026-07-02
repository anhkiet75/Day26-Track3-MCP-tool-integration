from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

try:
    from .db import SQLiteAdapter, ValidationError
    from .init_db import DEFAULT_DB_PATH, ensure_database
except ImportError:
    from db import SQLiteAdapter, ValidationError
    from init_db import DEFAULT_DB_PATH, ensure_database

DB_PATH = Path(os.environ.get("SQLITE_LAB_DB_PATH", DEFAULT_DB_PATH))
ensure_database(DB_PATH)
adapter = SQLiteAdapter(DB_PATH)
mcp = FastMCP("SQLite Lab MCP Server")


@mcp.tool(name="search")
def search(
    table: str,
    filters: list[dict[str, Any]] | None = None,
    columns: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    """Search rows with validated filters, ordering, and pagination."""
    return adapter.search(table, columns, filters, limit, offset, order_by, descending)


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    """Insert one validated row and return the inserted payload."""
    return adapter.insert(table, values)


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: list[dict[str, Any]] | None = None,
    group_by: list[str] | None = None,
) -> dict[str, Any]:
    """Run validated count or numeric-style aggregate queries."""
    return adapter.aggregate(table, metric, column, filters, group_by)


@mcp.resource("schema://database")
def database_schema() -> dict[str, list[dict[str, Any]]]:
    """Return the full database schema grouped by table."""
    return adapter.schema_snapshot()


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> dict[str, Any]:
    """Return the schema for one validated table."""
    return {"table": table_name, "columns": adapter.get_table_schema(table_name)}


if __name__ == "__main__":
    mcp.run()
