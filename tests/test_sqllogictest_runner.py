from pathlib import Path

import pytest

from sql_db.sqllogictest_runner import collect_test_paths, run_suite, run_suite_detailed


def test_collect_test_paths_accepts_single_file() -> None:
    paths = collect_test_paths(["tests/sqllogictest/select1.test"], allow_directory=False)
    assert paths == [Path("tests/sqllogictest/select1.test")]


def test_collect_test_paths_rejects_directory_without_opt_in() -> None:
    with pytest.raises(ValueError, match="refusing to run directory"):
        collect_test_paths(["tests/sqllogictest"], allow_directory=False)


def test_collect_test_paths_expands_directory_with_opt_in() -> None:
    paths = collect_test_paths(["tests/sqllogictest"], allow_directory=True)
    assert paths
    assert all(path.suffix == ".test" for path in paths)


def test_run_suite_executes_single_file(tmp_path: Path) -> None:
    test_file = tmp_path / "single.test"
    test_file.write_text(
        "\n".join(
            [
                "statement ok",
                "CREATE TABLE t(a INTEGER);",
                "",
                "statement ok",
                "INSERT INTO t VALUES(1);",
                "",
                "query I nosort",
                "SELECT a FROM t;",
                "----",
                "1",
                "",
            ]
        )
    )

    passed, total, timed_out, failures, failure_details, suite_timed_out = run_suite(
        [test_file],
        timeout_seconds=1,
        suite_timeout_seconds=5,
    )

    assert passed == 3
    assert total == 3
    assert timed_out == 0
    assert failures == []
    assert failure_details == []
    assert suite_timed_out is False


def test_run_suite_detailed_collects_file_and_case_timings(tmp_path: Path) -> None:
    test_file = tmp_path / "single.test"
    test_file.write_text(
        "\n".join(
            [
                "statement ok",
                "CREATE TABLE t(a INTEGER);",
                "",
                "statement ok",
                "INSERT INTO t VALUES(1);",
                "",
                "query I nosort",
                "SELECT a FROM t;",
                "----",
                "1",
                "",
            ]
        )
    )

    result = run_suite_detailed(
        [test_file],
        timeout_seconds=1,
        suite_timeout_seconds=5,
        collect_case_timings=True,
    )

    assert result.passed == 3
    assert result.total == 3
    assert result.timed_out == 0
    assert result.failures == ()
    assert result.failure_details == ()
    assert result.suite_timed_out is False
    assert result.elapsed_seconds >= 0
    assert len(result.file_timings) == 1
    assert result.file_timings[0].path == test_file
    assert result.file_timings[0].passed == 3
    assert result.file_timings[0].total == 3
    assert result.file_timings[0].timed_out == 0
    assert result.file_timings[0].seconds >= 0
    assert len(result.case_timings) == 3
    assert all(case_timing.path == test_file for case_timing in result.case_timings)
    assert all(case_timing.seconds >= 0 for case_timing in result.case_timings)
