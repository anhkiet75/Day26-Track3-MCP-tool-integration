from __future__ import annotations

from implementation.db import SQLiteAdapter, ValidationError
from implementation.init_db import create_database


def make_adapter(tmp_path):
    db_path = tmp_path / "test.db"
    create_database(db_path)
    return SQLiteAdapter(db_path)


def test_search_with_filters_and_ordering(tmp_path):
    adapter = make_adapter(tmp_path)
    result = adapter.search(
        "students",
        filters=[{"column": "cohort", "operator": "eq", "value": "A1"}],
        order_by="name",
    )
    assert result["count"] == 3
    assert [row["name"] for row in result["rows"]] == ["Alice Nguyen", "Bao Tran", "Chi Le"]


def test_insert_returns_generated_id(tmp_path):
    adapter = make_adapter(tmp_path)
    result = adapter.insert("students", {"name": "Lan Bui", "cohort": "C3", "email": "lan@example.com"})
    assert result["row"]["id"] > 0
    rows = adapter.search("students", filters=[{"column": "email", "operator": "eq", "value": "lan@example.com"}])
    assert rows["count"] == 1


def test_aggregate_supports_group_by(tmp_path):
    adapter = make_adapter(tmp_path)
    result = adapter.aggregate("enrollments", "avg", column="score", group_by=["cohort"])
    averages = {row["cohort"]: row["value"] for row in result["rows"]}
    assert round(averages["A1"], 2) == 86.6
    assert round(averages["B2"], 2) == 82.25


def test_invalid_requests_raise_validation_errors(tmp_path):
    adapter = make_adapter(tmp_path)
    invalid_cases = [
        lambda: adapter.search("missing"),
        lambda: adapter.search("students", filters=[{"column": "missing", "operator": "eq", "value": "A1"}]),
        lambda: adapter.search("students", filters=[{"column": "cohort", "operator": "bad", "value": "A1"}]),
        lambda: adapter.insert("students", {}),
        lambda: adapter.aggregate("students", "median"),
    ]
    for action in invalid_cases:
        try:
            action()
        except ValidationError:
            continue
        raise AssertionError("Expected ValidationError")
