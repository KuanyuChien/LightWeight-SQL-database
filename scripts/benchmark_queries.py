from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sql_db.executor import DatabaseEngine
from sql_db.storage import InMemoryStorage


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    description: str
    default_repeats: int
    query_sql: str


def build_filtered_scan_storage(row_count: int) -> InMemoryStorage:
    storage = InMemoryStorage()
    storage.create_table("items", ("id", "bucket", "payload"))
    for row_id in range(row_count):
        storage.insert_row("items", (row_id, row_id % 100, f"value_{row_id}"))
    return storage


def build_equality_join_storage(row_count: int) -> InMemoryStorage:
    storage = InMemoryStorage()
    storage.create_table("left_t", ("id", "bucket", "payload"))
    storage.create_table("right_t", ("bucket", "tag"))
    for row_id in range(row_count):
        storage.insert_row("left_t", (row_id, row_id % 100, f"left_{row_id}"))
    for bucket in range(100):
        storage.insert_row("right_t", (bucket, f"tag_{bucket}"))
    return storage


def build_three_way_join_storage(row_count: int) -> InMemoryStorage:
    storage = InMemoryStorage()
    storage.create_table("a", ("id", "bucket"))
    storage.create_table("b", ("bucket", "flag"))
    storage.create_table("c", ("bucket", "weight"))
    for row_id in range(row_count):
        storage.insert_row("a", (row_id, row_id % 100))
    for bucket in range(100):
        storage.insert_row("b", (bucket, bucket % 2))
        storage.insert_row("c", (bucket, bucket * 10))
    return storage


BENCHMARK_BUILDERS = {
    "filtered_scan": build_filtered_scan_storage,
    "equality_join": build_equality_join_storage,
    "three_way_join": build_three_way_join_storage,
}

BENCHMARK_CASES = (
    BenchmarkCase(
        name="filtered_scan",
        description="Single-table equality filter with ORDER BY over a seeded table",
        default_repeats=30,
        query_sql="SELECT id, payload FROM items WHERE bucket = 42 ORDER BY id;",
    ),
    BenchmarkCase(
        name="equality_join",
        description="Two-table equality join with a selective predicate",
        default_repeats=20,
        query_sql=(
            "SELECT left_t.id, right_t.tag FROM left_t, right_t "
            "WHERE left_t.bucket = right_t.bucket AND right_t.bucket = 42 ORDER BY left_t.id;"
        ),
    ),
    BenchmarkCase(
        name="three_way_join",
        description="Three-table join that exercises the executor's join pruning",
        default_repeats=10,
        query_sql=(
            "SELECT a.id, c.weight FROM a, b, c "
            "WHERE a.bucket = b.bucket AND b.bucket = c.bucket AND b.flag = 1 ORDER BY a.id;"
        ),
    ),
)


def run_benchmark_case(case: BenchmarkCase, row_count: int, repeats: int) -> tuple[float, int]:
    builder = BENCHMARK_BUILDERS[case.name]
    engine = DatabaseEngine(builder(row_count))
    total_rows = 0
    start = time.perf_counter()
    for _ in range(repeats):
        result = engine.execute(case.query_sql)
        if not result.success:
            raise RuntimeError(f"benchmark {case.name!r} failed: {result.error}")
        total_rows += len(result.rows)
    elapsed_seconds = time.perf_counter() - start
    return elapsed_seconds, total_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Run lightweight SQL engine benchmarks")
    parser.add_argument(
        "--rows",
        type=int,
        default=5000,
        help="Number of fact-table rows to seed for each benchmark (default: 5000)",
    )
    parser.add_argument(
        "--repeat-scale",
        type=float,
        default=1.0,
        help="Multiply each benchmark's default repeat count by this scale (default: 1.0)",
    )
    parser.add_argument(
        "--only",
        choices=[case.name for case in BENCHMARK_CASES],
        help="Run only a single benchmark case",
    )
    args = parser.parse_args()

    selected_cases = [case for case in BENCHMARK_CASES if args.only in {None, case.name}]
    total_seconds = 0.0
    print(f"rows={args.rows}")
    for case in selected_cases:
        repeats = max(1, int(round(case.default_repeats * args.repeat_scale)))
        elapsed_seconds, total_rows = run_benchmark_case(case, args.rows, repeats)
        total_seconds += elapsed_seconds
        print(f"benchmark={case.name}")
        print(f"description={case.description}")
        print(f"repeats={repeats}")
        print(f"rows_returned={total_rows}")
        print(f"elapsed_seconds={elapsed_seconds:.3f}")
        print(f"avg_ms_per_run={(elapsed_seconds / repeats) * 1000:.3f}")
    print(f"total_elapsed_seconds={total_seconds:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
