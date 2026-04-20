# sql-db

A lightweight in-memory SQL database built from scratch in Python.

This project parses SQL text, stores tables in memory, and executes a subset of relational queries without relying on an external database engine. It was built as a course project to explore how SQL systems work end-to-end, from tokenization and parsing to execution and testing with `sqllogictest`.

## Features

- In-memory table storage
- SQL tokenization and parsing
- `CREATE TABLE`, `INSERT`, and `SELECT` support
- Filtering, projection, ordering, and compound queries
- Aggregate functions such as `COUNT`, `SUM`, `MIN`, `MAX`, and `AVG`
- A small command-line REPL interface
- A staged `sqllogictest` runner for correctness checks
- A lightweight dashboard generator for project/demo data

## Tech Stack

- Python 3.13+
- `pytest` for tests
- Custom parser, executor, and storage layers in pure Python

## Project Structure

```text
sql_db/                 Core database engine
tests/                  Unit tests and sqllogictest inputs
scripts/                Helper scripts for staged runs and dashboard data
dashboard/              Static demo dashboard
pyproject.toml          Project metadata and CLI entry points
```

## Getting Started

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd final-project-u1470293
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install the project

```bash
pip install -e .
```

## Usage

### Run a single SQL statement

```bash
sqldb-repl "SELECT 1"
```

You can also pipe SQL into the CLI:

```bash
echo "SELECT 1" | sqldb-repl
```

### Python API

```python
from sql_db import DatabaseEngine

engine = DatabaseEngine()
engine.execute("CREATE TABLE students(id INTEGER, name VARCHAR(20))")
engine.execute("INSERT INTO students VALUES(1, 'Ada')")
result = engine.execute("SELECT * FROM students")

print(result.rows)
```

### Run the staged sqllogictest suite

```bash
python3 scripts/run_slt_stage.py
```

### Generate dashboard data

```bash
python3 scripts/generate_dashboard_data.py
```

To view the dashboard locally:

```bash
python3 -m http.server 8000 --directory dashboard
```

Then open `http://localhost:8000`.

## Testing

Run the full test suite with:

```bash
python3 -m pytest -q
```

Current local status: `15 passed`.

## Example Workflow

```sql
CREATE TABLE students(id INTEGER, name VARCHAR(20));
INSERT INTO students VALUES(1, 'Ada');
SELECT * FROM students;
```

## Goals

- Understand the core pieces of a SQL engine
- Practice building a non-trivial systems project from scratch
- Measure progress with repeatable automated tests
- Improve correctness and performance through iterative development

## Limitations

This is an educational in-memory database, not a production database system. SQL support is intentionally partial, performance is limited compared with real engines, and data does not persist across runs.

## License

This repository does not currently define a license.
