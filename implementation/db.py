from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SUPPORTED_OPERATORS = {
    "eq": "=",
    "ne": "!=",
    "lt": "<",
    "lte": "<=",
    "gt": ">",
    "gte": ">=",
    "like": "LIKE",
}
SUPPORTED_METRICS = {"count", "avg", "sum", "min", "max"}
NUMERIC_TYPES = {"INTEGER", "REAL", "NUMERIC"}
MAX_LIMIT = 100


class ValidationError(Exception):
    """Raised when a request cannot be safely executed."""


class SQLiteAdapter:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def list_tables(self) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [row["name"] for row in rows]

    def get_table_schema(self, table: str) -> list[dict[str, Any]]:
        table_name = self._validate_table(table)
        with self.connect() as connection:
            rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return [dict(row) for row in rows]

    def search(
        self,
        table: str,
        columns: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        table_name = self._validate_table(table)
        selected_columns = self._normalize_columns(table_name, columns)
        limit_value = self._validate_limit(limit)
        offset_value = self._validate_offset(offset)
        where_sql, params = self._build_filters(table_name, filters)
        order_sql = self._build_order(table_name, order_by, descending)
        sql = (
            f"SELECT {', '.join(selected_columns)} FROM {table_name}"
            f"{where_sql}{order_sql} LIMIT ? OFFSET ?"
        )
        with self.connect() as connection:
            rows = connection.execute(sql, [*params, limit_value, offset_value]).fetchall()
        return {
            "table": table_name,
            "columns": selected_columns,
            "count": len(rows),
            "limit": limit_value,
            "offset": offset_value,
            "rows": [dict(row) for row in rows],
        }

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        if not values:
            raise ValidationError("Insert values must not be empty.")
        table_name = self._validate_table(table)
        columns = self._normalize_columns(table_name, list(values))
        placeholders = ", ".join("?" for _ in columns)
        sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        params = [values[column] for column in columns]
        with self.connect() as connection:
            cursor = connection.execute(sql, params)
            connection.commit()
        row = dict(values)
        row["id"] = cursor.lastrowid
        return {"table": table_name, "row": row}

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: list[dict[str, Any]] | None = None,
        group_by: list[str] | None = None,
    ) -> dict[str, Any]:
        table_name = self._validate_table(table)
        metric_name = metric.lower()
        if metric_name not in SUPPORTED_METRICS:
            raise ValidationError(f"Unsupported metric '{metric}'.")
        if metric_name == "count" and column is None:
            aggregate_target = "*"
        else:
            aggregate_target = self._validate_column(table_name, column)
            if metric_name in {"avg", "sum"} and not self._is_numeric_column(table_name, aggregate_target):
                raise ValidationError(f"Metric '{metric_name}' requires a numeric column.")
        groups = self._normalize_columns(table_name, group_by) if group_by else []
        where_sql, params = self._build_filters(table_name, filters)
        select_parts = [*groups, f"{metric_name.upper()}({aggregate_target}) AS value"]
        group_sql = f" GROUP BY {', '.join(groups)}" if groups else ""
        sql = f"SELECT {', '.join(select_parts)} FROM {table_name}{where_sql}{group_sql}"
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return {
            "table": table_name,
            "metric": metric_name,
            "column": None if aggregate_target == "*" else aggregate_target,
            "group_by": groups,
            "rows": [dict(row) for row in rows],
        }

    def schema_snapshot(self) -> dict[str, list[dict[str, Any]]]:
        return {table: self.get_table_schema(table) for table in self.list_tables()}

    def _validate_table(self, table: str) -> str:
        if table not in self.list_tables():
            raise ValidationError(f"Unknown table '{table}'.")
        return table

    def _validate_column(self, table: str, column: str | None) -> str:
        if not column:
            raise ValidationError("Column is required for this request.")
        columns = {item["name"] for item in self.get_table_schema(table)}
        if column not in columns:
            raise ValidationError(f"Unknown column '{column}' for table '{table}'.")
        return column

    def _is_numeric_column(self, table: str, column: str) -> bool:
        for item in self.get_table_schema(table):
            if item["name"] == column:
                return str(item["type"]).upper() in NUMERIC_TYPES
        return False

    def _normalize_columns(self, table: str, columns: list[str] | None) -> list[str]:
        available = [item["name"] for item in self.get_table_schema(table)]
        if columns is None:
            return available
        if not columns:
            raise ValidationError("Columns list must not be empty.")
        return [self._validate_column(table, column) for column in columns]

    def _validate_limit(self, limit: int) -> int:
        if not isinstance(limit, int) or limit < 1 or limit > MAX_LIMIT:
            raise ValidationError(f"Limit must be an integer between 1 and {MAX_LIMIT}.")
        return limit

    def _validate_offset(self, offset: int) -> int:
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("Offset must be a non-negative integer.")
        return offset

    def _build_order(self, table: str, order_by: str | None, descending: bool) -> str:
        if order_by is None:
            return ""
        direction = "DESC" if descending else "ASC"
        return f" ORDER BY {self._validate_column(table, order_by)} {direction}"

    def _build_filters(self, table: str, filters: list[dict[str, Any]] | None) -> tuple[str, list[Any]]:
        if not filters:
            return "", []
        clauses: list[str] = []
        params: list[Any] = []
        for condition in filters:
            column = self._validate_column(table, condition.get("column"))
            operator = condition.get("operator", "eq")
            if operator == "in":
                values = condition.get("value")
                if not isinstance(values, list) or not values:
                    raise ValidationError("Operator 'in' requires a non-empty list value.")
                clauses.append(f"{column} IN ({', '.join('?' for _ in values)})")
                params.extend(values)
                continue
            if operator not in SUPPORTED_OPERATORS:
                raise ValidationError(f"Unsupported operator '{operator}'.")
            clauses.append(f"{column} {SUPPORTED_OPERATORS[operator]} ?")
            params.append(condition.get("value"))
        return f" WHERE {' AND '.join(clauses)}", params
