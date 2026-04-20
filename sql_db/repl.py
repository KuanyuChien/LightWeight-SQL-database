from __future__ import annotations

import argparse
import sys

from .executor import DatabaseEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the in-memory SQL database REPL")
    parser.add_argument("sql", nargs="?", help="SQL to execute")
    args = parser.parse_args()

    engine = DatabaseEngine()
    sql = args.sql if args.sql is not None else sys.stdin.read()
    result = engine.execute(sql)
    if not result.success:
        print(f"error: {result.error}")
        return 1
    for row in result.rows:
        print(" ".join("NULL" if value is None else str(value) for value in row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
