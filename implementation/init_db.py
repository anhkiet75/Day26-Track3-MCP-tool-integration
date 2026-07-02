from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "lab.db"

SCHEMA_SQL = """
DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);

CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL
);

CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    cohort TEXT NOT NULL,
    score REAL NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (course_id) REFERENCES courses(id)
);
"""

SEED_SQL = """
INSERT INTO students (name, cohort, email) VALUES
  ('Alice Nguyen', 'A1', 'alice@example.com'),
  ('Bao Tran', 'A1', 'bao@example.com'),
  ('Chi Le', 'A1', 'chi@example.com'),
  ('Dung Pham', 'B2', 'dung@example.com'),
  ('Ha Vo', 'B2', 'ha@example.com'),
  ('Minh Do', 'B2', 'minh@example.com');

INSERT INTO courses (code, title) VALUES
  ('MCP101', 'MCP Foundations'),
  ('SQL201', 'Applied SQLite'),
  ('PY301', 'Python Services');

INSERT INTO enrollments (student_id, course_id, cohort, score) VALUES
  (1, 1, 'A1', 91.5),
  (1, 2, 'A1', 88.0),
  (2, 1, 'A1', 76.0),
  (2, 3, 'A1', 84.5),
  (3, 2, 'A1', 93.0),
  (4, 1, 'B2', 69.5),
  (5, 2, 'B2', 82.0),
  (5, 3, 'B2', 87.5),
  (6, 3, 'B2', 90.0);
"""


def create_database(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.executescript(SCHEMA_SQL)
        connection.executescript(SEED_SQL)
        connection.commit()
    finally:
        connection.close()
    return path


def ensure_database(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    path = Path(db_path)
    if not path.exists():
        return create_database(path)
    return path


if __name__ == "__main__":
    created = create_database()
    print(f"Database initialized at {created}")
