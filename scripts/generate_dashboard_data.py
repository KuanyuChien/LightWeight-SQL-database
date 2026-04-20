from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sql_db import DatabaseEngine

TASKS_PATH = REPO_ROOT / "TASKS.md"
PROGRESS_PATH = REPO_ROOT / "PROGRESS.md"
BUG_REPORT_PATH = REPO_ROOT / "BUG_REPORT.md"
README_PATH = REPO_ROOT / "README.md"
STAGE_FILE_PATH = REPO_ROOT / "tests" / "sqllogictest" / "current_stage.txt"
SQLLOGICTEST_DIR = REPO_ROOT / "tests" / "sqllogictest"
OUTPUT_PATH = REPO_ROOT / "dashboard" / "data.js"
EM_DASH = " \u2014 "

PROJECT_TITLE = "Lightweight In-Memory SQL Database"
PROJECT_DESCRIPTION = (
    "A from-scratch Python SQL engine that tokenizes, parses, stores rows in memory, "
    "and executes relational queries against a staged sqllogictest corpus."
)
AGENT_WORKFLOW_DESCRIPTION = (
    "An agent loop ships one database capability at a time, reruns correctness and performance checks, "
    "and records the resulting milestones in the repo."
)
DEVELOPMENT_STORY = (
    "The project started from a minimal SQL pipeline, expanded step-by-step through parser and executor features, "
    "then shifted into performance work once multi-table joins began timing out."
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_progress_rows(progress_text: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    in_table = False
    for line in progress_text.splitlines():
        if line.startswith("| Iteration |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            break
        if line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 6:
            continue
        rows.append(
            {
                "iteration": int(cells[0]),
                "date": cells[1],
                "passed": int(cells[2]),
                "total": int(cells[3]),
                "delta": cells[4],
                "notes": cells[5],
            }
        )
    if not rows:
        raise ValueError("Could not parse progress table from PROGRESS.md")
    return rows


def parse_done_milestones(tasks_text: str) -> list[dict[str, object]]:
    milestones: list[dict[str, object]] = []
    in_done = False
    for raw_line in tasks_text.splitlines():
        line = raw_line.strip()
        if line == "## Done":
            in_done = True
            continue
        if in_done and line.startswith("## "):
            break
        if not in_done or not line.startswith("- [x] "):
            continue
        payload = line[len("- [x] ") :]
        parts = payload.split(EM_DASH)
        if len(parts) < 3:
            continue
        title, date, summary = parts[0], parts[1], EM_DASH.join(parts[2:])
        tests_passing = None
        fraction_match = re.search(r"(\d+)/(\d+)", summary)
        tests_match = re.search(r"(\d+) tests passing", summary)
        if fraction_match:
            tests_passing = int(fraction_match.group(1))
        elif tests_match:
            tests_passing = int(tests_match.group(1))
        milestones.append(
            {
                "title": title,
                "date": date,
                "summary": summary,
                "testsPassing": tests_passing,
            }
        )
    if not milestones:
        raise ValueError("Could not parse completed milestones from TASKS.md")
    return list(reversed(milestones))


def find_last_line(progress_text: str, marker: str) -> str:
    for line in reversed(progress_text.splitlines()):
        if marker in line:
            return line.strip()
    raise ValueError(f"Could not find line containing {marker!r} in PROGRESS.md")


def parse_validation_snapshot(progress_text: str) -> dict[str, object]:
    line = find_last_line(progress_text, "Validation after the optimization:")
    match = re.search(r"passed `(\d+)/(\d+)` with `timed_out=(\d+)`, but total runtime improved from `([\d.]+)s` to `([\d.]+)s`", line)
    if not match:
        raise ValueError("Could not parse validation snapshot from PROGRESS.md")
    return {
        "passed": int(match.group(1)),
        "total": int(match.group(2)),
        "timedOut": int(match.group(3)),
        "previousRuntimeSeconds": float(match.group(4)),
        "runtimeSeconds": float(match.group(5)),
    }


def parse_file_timings(line: str) -> list[tuple[str, float]]:
    return [(name, float(value)) for name, value in re.findall(r"`([^`]+)` `([\d.]+)s`", line)]


def parse_backtick_pairs(line: str, suffix: str) -> list[tuple[str, float]]:
    pattern = rf"`([^`]+)` `([\d.]+) {re.escape(suffix)}`"
    return [(name, float(value)) for name, value in re.findall(pattern, line)]


def parse_bug_summary(bug_report_text: str) -> dict[str, str]:
    latest_root_cause = ""
    latest_fix = ""
    latest_result = ""
    for line in bug_report_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- Root cause:"):
            latest_root_cause = stripped[len("- Root cause:") :].strip()
        elif stripped.startswith("- Fix:"):
            latest_fix = stripped[len("- Fix:") :].strip()
        elif stripped.startswith("- Result:"):
            latest_result = stripped[len("- Result:") :].strip()
    if not latest_root_cause or not latest_fix or not latest_result:
        raise ValueError("Could not parse latest bug summary from BUG_REPORT.md")
    return {
        "rootCause": latest_root_cause,
        "fix": latest_fix,
        "result": latest_result,
    }


def select_major_milestones(milestones: list[dict[str, object]]) -> list[dict[str, object]]:
    title_prefixes = [
        "Scaffold module structure + sqllogictest runner",
        "Tokenizer + basic pipeline:",
        "Tokenizer + parser + executor: expression SELECTs",
        "Parser + executor: `IN (...)`",
        "Stage 4 readiness:",
        "Stage 5 readiness:",
        "Benchmarking:",
        "Executor optimization:",
        "Demo dashboard:",
    ]
    selected: list[dict[str, object]] = []
    for prefix in title_prefixes:
        for milestone in milestones:
            if str(milestone["title"]).startswith(prefix):
                selected.append(milestone)
                break
    return selected


def parse_scope(stage_file_path: Path, sqllogictest_dir: Path) -> dict[str, object]:
    staged_files = [
        line.strip()
        for line in read_text(stage_file_path).splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    local_files = sorted(path.name for path in sqllogictest_dir.glob("*.test"))
    staged_names = [Path(path).name for path in staged_files]
    staged_covers_local = staged_names == local_files
    return {
        "localFiles": local_files,
        "stageFiles": staged_names,
        "stagedCoversLocal": staged_covers_local,
        "summary": (
            "Current staged coverage matches every local sqllogictest file checked into the repo."
            if staged_covers_local
            else "Current staged coverage does not yet include every local sqllogictest file."
        ),
        "externalNote": "Any broader external sqllogictest corpus that is not checked into this repo remains untested.",
    }


def build_example_queries() -> list[dict[str, object]]:
    engine = DatabaseEngine()
    setup_statements = [
        "CREATE TABLE students(id INTEGER, name VARCHAR(20), cohort INTEGER)",
        "CREATE TABLE projects(student_id INTEGER, title VARCHAR(30))",
        "INSERT INTO students VALUES(1, 'Ada', 2026)",
        "INSERT INTO students VALUES(2, 'Linus', 2025)",
        "INSERT INTO students VALUES(3, 'Grace', 2026)",
        "INSERT INTO projects VALUES(1, 'optimizer')",
        "INSERT INTO projects VALUES(1, 'runner')",
        "INSERT INTO projects VALUES(3, 'dashboard')",
    ]
    for sql in setup_statements:
        result = engine.execute(sql)
        if not result.success:
            raise RuntimeError(f"Example setup failed for {sql!r}: {result.error}")

    filter_sql = "SELECT id, name FROM students WHERE cohort = 2026 ORDER BY id"
    join_sql = (
        "SELECT students.name, projects.title FROM students, projects "
        "WHERE students.id = projects.student_id ORDER BY 1, 2"
    )
    aggregate_sql = "SELECT count(*) FROM projects"

    filter_result = engine.execute(filter_sql)
    join_result = engine.execute(join_sql)
    aggregate_result = engine.execute(aggregate_sql)
    for label, result in (("filter", filter_result), ("join", join_result), ("aggregate", aggregate_result)):
        if not result.success:
            raise RuntimeError(f"Example {label} query failed: {result.error}")

    return [
        {
            "label": "Table creation",
            "kind": "setup",
            "sql": "CREATE TABLE students(id INTEGER, name VARCHAR(20), cohort INTEGER);",
            "note": "Defines a simple in-memory relation with typed columns.",
        },
        {
            "label": "Insert rows",
            "kind": "setup",
            "sql": "INSERT INTO students VALUES(1, 'Ada', 2026);\nINSERT INTO students VALUES(2, 'Linus', 2025);\nINSERT INTO students VALUES(3, 'Grace', 2026);",
            "note": "The engine stores rows immediately, so follow-up queries can read them without any external database service.",
        },
        {
            "label": "Select with filter",
            "kind": "result",
            "sql": f"{filter_sql};",
            "columns": ["id", "name"],
            "rows": [list(row) for row in filter_result.rows],
        },
        {
            "label": "Join",
            "kind": "result",
            "sql": f"{join_sql};",
            "columns": ["name", "title"],
            "rows": [list(row) for row in join_result.rows],
        },
        {
            "label": "Aggregate",
            "kind": "result",
            "sql": f"{aggregate_sql};",
            "columns": ["count(*)"],
            "rows": [list(row) for row in aggregate_result.rows],
        },
    ]


def build_story_cards(progress_rows: list[dict[str, object]], validation_snapshot: dict[str, object], benchmarks: list[tuple[str, float]]) -> list[dict[str, str]]:
    first = progress_rows[0]
    latest = progress_rows[-1]
    benchmark_lookup = {name: value for name, value in benchmarks}
    return [
        {
            "label": "Start",
            "value": f"{first['passed']}/{first['total']}",
            "detail": "Initial scaffold ran without crashing, creating a clean baseline for the agent loop.",
        },
        {
            "label": "Coverage",
            "value": f"{latest['passed']}/{latest['total']}",
            "detail": "The local staged sqllogictest corpus now passes end-to-end with no timed-out cases.",
        },
        {
            "label": "Runtime",
            "value": f"{validation_snapshot['runtimeSeconds']:.3f}s",
            "detail": "The tracked full staged validation time fell after join predicate reuse stopped redundant WHERE checks.",
        },
        {
            "label": "Three-way join",
            "value": f"{benchmark_lookup['three_way_join']:.3f} ms/run",
            "detail": "Representative join-heavy benchmarks now land below the tracked 30 ms/run target.",
        },
    ]


def main() -> int:
    tasks_text = read_text(TASKS_PATH)
    progress_text = read_text(PROGRESS_PATH)
    bug_report_text = read_text(BUG_REPORT_PATH)
    read_text(README_PATH)

    progress_rows = parse_progress_rows(progress_text)
    milestones = select_major_milestones(parse_done_milestones(tasks_text))
    validation_snapshot = parse_validation_snapshot(progress_text)
    per_file_line = find_last_line(progress_text, "Updated per-file timings:")
    benchmark_line = find_last_line(progress_text, "Updated benchmark results")
    hotspot_line = find_last_line(progress_text, "Updated hotspot cases:")
    bug_summary = parse_bug_summary(bug_report_text)

    file_timings = [
        {"name": name, "seconds": seconds}
        for name, seconds in parse_file_timings(per_file_line)
    ]
    benchmarks = parse_backtick_pairs(benchmark_line, "ms/run")
    benchmark_metrics = [
        {"name": name, "label": name.replace("_", " "), "avgMsPerRun": value}
        for name, value in benchmarks
    ]

    latest_progress = progress_rows[-1]
    scope = parse_scope(STAGE_FILE_PATH, SQLLOGICTEST_DIR)
    examples = build_example_queries()

    data = {
        "generatedFrom": {
            "tasks": TASKS_PATH.name,
            "progress": PROGRESS_PATH.name,
            "readme": README_PATH.name,
            "stageFile": str(STAGE_FILE_PATH.relative_to(REPO_ROOT)),
        },
        "project": {
            "title": PROJECT_TITLE,
            "description": PROJECT_DESCRIPTION,
            "agentWorkflow": AGENT_WORKFLOW_DESCRIPTION,
            "story": DEVELOPMENT_STORY,
        },
        "testSnapshot": {
            "passed": validation_snapshot["passed"],
            "total": validation_snapshot["total"],
            "timedOut": validation_snapshot["timedOut"],
            "coveragePercent": round((validation_snapshot["passed"] / validation_snapshot["total"]) * 100, 1),
            "runtimeSeconds": validation_snapshot["runtimeSeconds"],
            "previousRuntimeSeconds": validation_snapshot["previousRuntimeSeconds"],
            "knownScope": scope["summary"],
            "externalScopeNote": scope["externalNote"],
            "localFiles": scope["localFiles"],
            "stageFiles": scope["stageFiles"],
            "fileTimings": file_timings,
            "hotspots": hotspot_line.replace("- Updated hotspot cases: ", ""),
            "bugSummary": bug_summary,
            "latestIteration": latest_progress["iteration"],
            "latestNotes": latest_progress["notes"],
        },
        "benchmarkSnapshot": {
            "rowCount": 5000,
            "metrics": benchmark_metrics,
            "targetMs": 30.0,
        },
        "milestones": milestones,
        "progressSeries": progress_rows,
        "storyCards": build_story_cards(progress_rows, validation_snapshot, benchmarks),
        "examples": examples,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = "window.DASHBOARD_DATA = " + json.dumps(data, indent=2, ensure_ascii=True) + ";\n"
    OUTPUT_PATH.write_text(payload, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
