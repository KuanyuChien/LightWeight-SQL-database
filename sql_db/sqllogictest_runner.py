from __future__ import annotations

import argparse
import hashlib
import re
import signal
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from .executor import DatabaseEngine


HASH_RESULT_PATTERN = re.compile(r"^(\d+) values hashing to ([0-9a-f]{32})$")
DEFAULT_TEST_TIMEOUT_SECONDS = 10
DEFAULT_SUITE_TIMEOUT_SECONDS = 300


def _normalize_sort_mode(parts: list[str]) -> tuple[str, str]:
    sort_mode = "nosort"
    label = ""
    for part in parts:
        if part in {"nosort", "rowsort", "valuesort"}:
            sort_mode = part
        else:
            label = part
    return sort_mode, label


@dataclass(frozen=True)
class StatementCase:
    path: Path
    index: int
    mode: str
    sql: str


@dataclass(frozen=True)
class QueryCase:
    path: Path
    index: int
    sql: str
    sort_mode: str
    label: str
    expected: tuple[str, ...]


class CaseTimeoutError(TimeoutError):
    """Raised when a single sqllogictest case exceeds the configured timeout."""


@dataclass(frozen=True)
class FailureDetail:
    path: Path
    index: int
    sql: str
    expected: tuple[str, ...]
    actual: tuple[str, ...]
    error: str | None = None


@dataclass(frozen=True)
class FileTiming:
    path: Path
    passed: int
    total: int
    timed_out: int
    seconds: float


@dataclass(frozen=True)
class CaseTiming:
    path: Path
    index: int
    sql: str
    passed: bool
    timed_out: bool
    seconds: float


@dataclass(frozen=True)
class SuiteRunResult:
    passed: int
    total: int
    timed_out: int
    failures: tuple[str, ...]
    failure_details: tuple[FailureDetail, ...]
    suite_timed_out: bool
    elapsed_seconds: float
    file_timings: tuple[FileTiming, ...] = ()
    case_timings: tuple[CaseTiming, ...] = ()


def parse_file(path: Path) -> list[StatementCase | QueryCase]:
    lines = path.read_text().splitlines()
    cases: list[StatementCase | QueryCase] = []
    i = 0
    case_index = 1
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#"):
            i += 1
            continue
        if (
            line.startswith("skipif")
            or line.startswith("onlyif")
            or line.startswith("hash-threshold")
            or line == "halt"
        ):
            i += 1
            continue
        if line.startswith("statement "):
            mode = line.split()[1]
            i += 1
            sql_lines: list[str] = []
            while i < len(lines) and lines[i].strip():
                sql_lines.append(lines[i])
                i += 1
            cases.append(StatementCase(path=path, index=case_index, mode=mode, sql="\n".join(sql_lines)))
            case_index += 1
            continue
        if line.startswith("query "):
            parts = line.split()
            sort_mode, label = _normalize_sort_mode(parts[2:])
            i += 1
            sql_lines: list[str] = []
            while i < len(lines) and lines[i].strip() != "----":
                sql_lines.append(lines[i])
                i += 1
            if i >= len(lines):
                raise ValueError(f"missing result separator in {path}")
            i += 1
            expected_lines: list[str] = []
            while i < len(lines) and lines[i].strip():
                expected_lines.append(lines[i])
                i += 1
            cases.append(
                QueryCase(
                    path=path,
                    index=case_index,
                    sql="\n".join(sql_lines),
                    sort_mode=sort_mode,
                    label=label,
                    expected=tuple(expected_lines),
                )
            )
            case_index += 1
            continue
        raise ValueError(f"unsupported sqllogictest directive {line!r} in {path}")
    return cases


def format_rows(rows: list[tuple[object, ...]], sort_mode: str) -> tuple[str, ...]:
    rendered_rows = [tuple(_format_value(value) for value in row) for row in rows]
    if sort_mode == "rowsort":
        rendered_rows = sorted(rendered_rows)
    rendered: list[str] = []
    if sort_mode == "valuesort":
        values = sorted(value for row in rendered_rows for value in row)
        return tuple(values)
    rendered: list[str] = []
    for row in rendered_rows:
        rendered.extend(row)
    return tuple(rendered)


def evaluate_case(engine: DatabaseEngine, case: StatementCase | QueryCase) -> tuple[bool, FailureDetail | None]:
    if isinstance(case, StatementCase):
        result = engine.execute(case.sql)
        passed = result.success if case.mode == "ok" else not result.success
        if passed:
            return True, None
        expected = (f"statement {case.mode}",)
        actual = ("statement ok",) if result.success else (f"statement error: {result.error or '(no error message)'}",)
        return False, FailureDetail(
            path=case.path,
            index=case.index,
            sql=case.sql,
            expected=expected,
            actual=actual,
            error=result.error,
        )

    result = engine.execute(case.sql)
    if not result.success:
        return False, FailureDetail(
            path=case.path,
            index=case.index,
            sql=case.sql,
            expected=case.expected,
            actual=(f"error: {result.error or '(no error message)'}",),
            error=result.error,
        )

    actual = format_rows(result.rows, case.sort_mode)
    if _is_hashed_result(case.expected):
        passed = _hash_result(actual) == case.expected[0]
        if passed:
            return True, None
        return False, FailureDetail(
            path=case.path,
            index=case.index,
            sql=case.sql,
            expected=case.expected,
            actual=(_hash_result(actual),),
        )

    passed = actual == case.expected
    if passed:
        return True, None
    return False, FailureDetail(
        path=case.path,
        index=case.index,
        sql=case.sql,
        expected=case.expected,
        actual=actual,
    )


def _format_value(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.3f}"
    text = "" if value is None else str(value)
    if not text:
        return "(empty)"
    return "".join(character if 32 <= ord(character) <= 126 else "@" for character in text)


def _is_hashed_result(expected: tuple[str, ...]) -> bool:
    return len(expected) == 1 and HASH_RESULT_PATTERN.match(expected[0]) is not None


def _hash_result(values: tuple[str, ...]) -> str:
    digest = hashlib.md5()
    for value in values:
        digest.update(value.encode())
        digest.update(b"\n")
    return f"{len(values)} values hashing to {digest.hexdigest()}"


def _format_detail_values(values: tuple[str, ...], max_items: int = 12) -> str:
    if not values:
        return "(empty)"
    if len(values) <= max_items:
        return "\n".join(values)
    preview = "\n".join(values[:max_items])
    return f"{preview}\n... ({len(values) - max_items} more values)"


def _timeout_handler(signum: int, frame: object) -> None:
    del signum, frame
    raise CaseTimeoutError("test exceeded time limit")


ResultT = TypeVar("ResultT")


def _call_with_timeout(callback: Callable[[], ResultT], timeout_seconds: int) -> ResultT:
    if timeout_seconds <= 0:
        return callback()

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(timeout_seconds)
    try:
        return callback()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)


def collect_test_paths(inputs: list[str], allow_directory: bool) -> list[Path]:
    if not inputs:
        raise ValueError("at least one .test file path is required")

    paths: list[Path] = []
    for raw_path in inputs:
        path = Path(raw_path)
        if path.is_file():
            if path.suffix != ".test":
                raise ValueError(f"expected a .test file, got {path}")
            paths.append(path)
            continue
        if path.is_dir():
            if not allow_directory:
                raise ValueError(
                    f"refusing to run directory {path}. Pass one or more explicit .test files instead, "
                    "or re-run with --allow-directory if you really want the whole folder."
                )
            directory_paths = sorted(path.glob("*.test"))
            if not directory_paths:
                raise ValueError(f"no .test files found in directory {path}")
            paths.extend(directory_paths)
            continue
        raise ValueError(f"path does not exist: {path}")

    return paths


def run_suite(
    paths: list[Path],
    timeout_seconds: int = DEFAULT_TEST_TIMEOUT_SECONDS,
    suite_timeout_seconds: int = DEFAULT_SUITE_TIMEOUT_SECONDS,
    max_failure_details: int = 3,
) -> tuple[int, int, int, list[str], list[FailureDetail], bool]:
    result = run_suite_detailed(
        paths,
        timeout_seconds=timeout_seconds,
        suite_timeout_seconds=suite_timeout_seconds,
        max_failure_details=max_failure_details,
    )
    return (
        result.passed,
        result.total,
        result.timed_out,
        list(result.failures),
        list(result.failure_details),
        result.suite_timed_out,
    )


def run_suite_detailed(
    paths: list[Path],
    timeout_seconds: int = DEFAULT_TEST_TIMEOUT_SECONDS,
    suite_timeout_seconds: int = DEFAULT_SUITE_TIMEOUT_SECONDS,
    max_failure_details: int = 3,
    collect_case_timings: bool = False,
) -> SuiteRunResult:
    passed = 0
    total = 0
    timed_out = 0
    failures: list[str] = []
    failure_details: list[FailureDetail] = []
    file_timings: list[FileTiming] = []
    case_timings: list[CaseTiming] = []
    suite_timed_out = False
    suite_start = time.perf_counter()
    deadline = time.monotonic() + suite_timeout_seconds if suite_timeout_seconds > 0 else None
    for path in paths:
        file_passed = 0
        file_total = 0
        file_timed_out = 0
        file_start = time.perf_counter()
        engine = DatabaseEngine()
        for case in parse_file(path):
            if deadline is not None and time.monotonic() >= deadline:
                suite_timed_out = True
                file_timings.append(
                    FileTiming(
                        path=path,
                        passed=file_passed,
                        total=file_total,
                        timed_out=file_timed_out,
                        seconds=time.perf_counter() - file_start,
                    )
                )
                return SuiteRunResult(
                    passed=passed,
                    total=total,
                    timed_out=timed_out,
                    failures=tuple(failures),
                    failure_details=tuple(failure_details),
                    suite_timed_out=suite_timed_out,
                    elapsed_seconds=time.perf_counter() - suite_start,
                    file_timings=tuple(file_timings),
                    case_timings=tuple(case_timings),
                )

            total += 1
            file_total += 1
            case_start = time.perf_counter()
            try:
                case_passed, detail = evaluate_case_with_timeout(engine, case, timeout_seconds)
            except CaseTimeoutError:
                case_seconds = time.perf_counter() - case_start
                timed_out += 1
                file_timed_out += 1
                if len(failures) < 10:
                    failures.append(f"TIMEOUT {path.name}:{case.index}")
                if collect_case_timings:
                    case_timings.append(
                        CaseTiming(
                            path=path,
                            index=case.index,
                            sql=case.sql,
                            passed=False,
                            timed_out=True,
                            seconds=case_seconds,
                        )
                    )
                continue
            case_seconds = time.perf_counter() - case_start
            if collect_case_timings:
                case_timings.append(
                    CaseTiming(
                        path=path,
                        index=case.index,
                        sql=case.sql,
                        passed=case_passed,
                        timed_out=False,
                        seconds=case_seconds,
                    )
                )
            if case_passed:
                passed += 1
                file_passed += 1
                continue
            if len(failures) < 10:
                failures.append(f"{path.name}:{case.index}")
            if detail is not None and len(failure_details) < max_failure_details:
                failure_details.append(detail)
        file_timings.append(
            FileTiming(
                path=path,
                passed=file_passed,
                total=file_total,
                timed_out=file_timed_out,
                seconds=time.perf_counter() - file_start,
            )
        )
    return SuiteRunResult(
        passed=passed,
        total=total,
        timed_out=timed_out,
        failures=tuple(failures),
        failure_details=tuple(failure_details),
        suite_timed_out=suite_timed_out,
        elapsed_seconds=time.perf_counter() - suite_start,
        file_timings=tuple(file_timings),
        case_timings=tuple(case_timings),
    )


def evaluate_case_with_timeout(
    engine: DatabaseEngine,
    case: StatementCase | QueryCase,
    timeout_seconds: int,
) -> tuple[bool, FailureDetail | None]:
    return _call_with_timeout(lambda: evaluate_case(engine, case), timeout_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run sqllogictest files against the in-memory SQL engine")
    parser.add_argument("paths", nargs="+", help="One or more .test files to run")
    parser.add_argument(
        "--allow-directory",
        action="store_true",
        help="Allow directory inputs and expand them to every .test file inside",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TEST_TIMEOUT_SECONDS,
        help=f"Per-test timeout in seconds (default: {DEFAULT_TEST_TIMEOUT_SECONDS}, 0 disables)",
    )
    parser.add_argument(
        "--suite-timeout-seconds",
        type=int,
        default=DEFAULT_SUITE_TIMEOUT_SECONDS,
        help=f"Total suite timeout in seconds (default: {DEFAULT_SUITE_TIMEOUT_SECONDS}, 0 disables)",
    )
    parser.add_argument(
        "--max-failure-details",
        type=int,
        default=3,
        help="Maximum number of detailed failures to print (default: 3)",
    )
    parser.add_argument(
        "--show-file-times",
        action="store_true",
        help="Print per-file pass counts and elapsed seconds",
    )
    parser.add_argument(
        "--show-slowest-cases",
        type=int,
        default=0,
        help="Print the N slowest individual cases (default: 0)",
    )
    args = parser.parse_args()

    try:
        paths = collect_test_paths(args.paths, allow_directory=args.allow_directory)
    except ValueError as exc:
        parser.error(str(exc))

    result = run_suite_detailed(
        paths,
        timeout_seconds=args.timeout_seconds,
        suite_timeout_seconds=args.suite_timeout_seconds,
        max_failure_details=args.max_failure_details,
        collect_case_timings=args.show_slowest_cases > 0,
    )
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
            print(_format_detail_values(detail.expected))
            print("ACTUAL:")
            print(_format_detail_values(detail.actual))
            if detail.error:
                print(f"ERROR: {detail.error}")
    if result.suite_timed_out:
        print("suite_timeout_reached=true")
    return 0 if result.passed == result.total and result.timed_out == 0 and not result.suite_timed_out else 1


if __name__ == "__main__":
    raise SystemExit(main())
