from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sql_db.executor import DatabaseEngine
from sql_db.sqllogictest_runner import (
    DEFAULT_TEST_TIMEOUT_SECONDS,
    QueryCase,
    StatementCase,
    evaluate_case_with_timeout,
    parse_file,
)


def parse_case_range(start: int, end: int | None, total_cases: int) -> tuple[int, int]:
    actual_end = start if end is None else end
    if start < 1 or actual_end < start or actual_end > total_cases:
        raise ValueError(f"invalid case range {start}-{actual_end} for file with {total_cases} cases")
    return start, actual_end


def warm_up_state(engine: DatabaseEngine, cases: list[StatementCase | QueryCase], target_start: int) -> None:
    replayed = 0
    for case in cases[: target_start - 1]:
        if isinstance(case, StatementCase):
            engine.execute(case.sql)
            replayed += 1
            if replayed % 100 == 0:
                print(f"warmup_statements={replayed}", flush=True)


def print_case_result(case: StatementCase | QueryCase, passed: bool, detail_text: str | None) -> None:
    print(f"CASE {case.index}")
    print(case.sql)
    print(f"PASS={passed}")
    if detail_text:
        print(detail_text)
    print()


def format_detail_text(detail_expected: tuple[str, ...], detail_actual: tuple[str, ...], error: str | None) -> str:
    expected_lines = list(detail_expected) if detail_expected else ["(empty)"]
    actual_lines = list(detail_actual) if detail_actual else ["(empty)"]
    lines = ["EXPECTED:", *expected_lines, "ACTUAL:", *actual_lines]
    if error:
        lines.append(f"ERROR: {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a specific sqllogictest case range with warmup replay")
    parser.add_argument("path", help="Path to a single .test file")
    parser.add_argument("start_case", type=int, help="First case index to inspect (1-based)")
    parser.add_argument("end_case", nargs="?", type=int, help="Last case index to inspect (inclusive)")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TEST_TIMEOUT_SECONDS,
        help=f"Per-test timeout in seconds (default: {DEFAULT_TEST_TIMEOUT_SECONDS})",
    )
    args = parser.parse_args()

    path = Path(args.path)
    cases = parse_file(path)
    start_case, end_case = parse_case_range(args.start_case, args.end_case, len(cases))

    print(f"file={path}")
    print(f"range={start_case}-{end_case}")
    print(f"total_cases={len(cases)}")

    engine = DatabaseEngine()
    warm_up_state(engine, cases, start_case)

    exit_code = 0
    for case in cases[start_case - 1 : end_case]:
        try:
            passed, detail = evaluate_case_with_timeout(engine, case, args.timeout_seconds)
        except TimeoutError:
            print_case_result(case, False, "ERROR:\ncase timed out")
            exit_code = 1
            continue
        detail_text = None
        if detail is not None:
            detail_text = format_detail_text(detail.expected, detail.actual, detail.error)
            exit_code = 1
        print_case_result(case, passed, detail_text)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
