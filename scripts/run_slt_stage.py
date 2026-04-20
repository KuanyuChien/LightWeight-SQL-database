from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sql_db.sqllogictest_runner import (
    DEFAULT_SUITE_TIMEOUT_SECONDS,
    DEFAULT_TEST_TIMEOUT_SECONDS,
    collect_test_paths,
    run_suite_detailed,
)


DEFAULT_STAGE_FILE = Path("tests/sqllogictest/current_stage.txt")


def load_stage_paths(stage_file: Path) -> list[str]:
    if not stage_file.is_file():
        raise ValueError(f"stage file does not exist: {stage_file}")

    paths: list[str] = []
    for line in stage_file.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        paths.append(stripped)

    if not paths:
        raise ValueError(f"stage file is empty: {stage_file}")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Run only the current staged sqllogictest files")
    parser.add_argument(
        "--stage-file",
        default=str(DEFAULT_STAGE_FILE),
        help=f"Text file listing allowed .test files (default: {DEFAULT_STAGE_FILE})",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TEST_TIMEOUT_SECONDS,
        help=f"Per-test timeout in seconds (default: {DEFAULT_TEST_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--suite-timeout-seconds",
        type=int,
        default=DEFAULT_SUITE_TIMEOUT_SECONDS,
        help=f"Total suite timeout in seconds (default: {DEFAULT_SUITE_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--show-file-times",
        action="store_true",
        help="Print per-file pass counts and elapsed seconds for the staged files",
    )
    parser.add_argument(
        "--show-slowest-cases",
        type=int,
        default=0,
        help="Print the N slowest individual staged cases (default: 0)",
    )
    args = parser.parse_args()

    try:
        requested_paths = load_stage_paths(Path(args.stage_file))
        paths = collect_test_paths(requested_paths, allow_directory=False)
    except ValueError as exc:
        parser.error(str(exc))

    result = run_suite_detailed(
        paths,
        timeout_seconds=args.timeout_seconds,
        suite_timeout_seconds=args.suite_timeout_seconds,
        collect_case_timings=args.show_slowest_cases > 0,
    )
    print(f"stage_file={args.stage_file}")
    print(f"passed={result.passed}")
    print(f"total={result.total}")
    print(f"failed={result.total - result.passed}")
    print(f"timed_out={result.timed_out}")
    print(f"elapsed_seconds={result.elapsed_seconds:.3f}")
    if args.show_file_times:
        print("file_times=")
        for file_timing in result.file_timings:
            print(
                f"{file_timing.path}: passed={file_timing.passed} total={file_timing.total} "
                f"timed_out={file_timing.timed_out} elapsed_seconds={file_timing.seconds:.3f}"
            )
    if args.show_slowest_cases > 0:
        print("slowest_cases=")
        for case_timing in sorted(result.case_timings, key=lambda timing: timing.seconds, reverse=True)[: args.show_slowest_cases]:
            sql_preview = " ".join(case_timing.sql.split())
            if len(sql_preview) > 120:
                sql_preview = f"{sql_preview[:117]}..."
            print(
                f"{case_timing.path.name}:{case_timing.index} passed={case_timing.passed} "
                f"timed_out={case_timing.timed_out} elapsed_seconds={case_timing.seconds:.3f}"
            )
            print(f"SQL: {sql_preview}")
    if result.failures:
        print("sample_failures=")
        for failure in result.failures:
            print(failure)
    if result.failure_details:
        print("failure_details=")
        for detail in result.failure_details:
            print(f"[{detail.path.name}:{detail.index}]")
            print("SQL:")
            print(detail.sql)
            print("EXPECTED:")
            for value in detail.expected or ("(empty)",):
                print(value)
            print("ACTUAL:")
            for value in detail.actual or ("(empty)",):
                print(value)
            if detail.error:
                print(f"ERROR: {detail.error}")
    if result.suite_timed_out:
        print("suite_timeout_reached=true")
    return 0 if result.passed == result.total and result.timed_out == 0 and not result.suite_timed_out else 1


if __name__ == "__main__":
    raise SystemExit(main())
