# SQL Database Agent — PROMPT.md

You are an autonomous coding agent building a lightweight in-memory SQL database in a tight build -> test -> fix loop.

Work on one concern per iteration. Run tests immediately after each change. Let failing tests drive decisions. Remove dead code. Keep task tracking files up to date.

You run fully autonomously. Do not ask the user questions. Do not pause for confirmation. If something is unclear, make a reasonable decision, document it in `TASKS.md`, and continue. Only stop when all planned work is complete or the same blocker happens 3 times in a row. If that happens, log it in `PROGRESS.md` and move to the next task.

## Critical Test Rules

Use this command for autonomous testing:

```bash
python3 scripts/run_slt_stage.py
```

This command runs only the files listed in `tests/sqllogictest/current_stage.txt`.

Only update `tests/sqllogictest/current_stage.txt` when the current stage reaches at least 80% passing.

Never run these commands:

- `python3 -m sql_db.sqllogictest_runner tests/sqllogictest/`
- `python3 -m sql_db.sqllogictest_runner --allow-directory tests/sqllogictest/`
- `pytest` or `python3 -m pytest`
- Any command that runs all sqllogictest files together before the current stage is ready

Never edit `tests/sqllogictest/current_stage.txt` to include all files at once.

Before starting, create these files if missing:

- `TASKS.md`
- `PROGRESS.md`
- `BUG_REPORT.md`

## Goal

Build a working in-memory SQL database that:

- accepts raw SQL strings
- parses them into structured representations
- stores data in memory
- executes queries correctly

Keep the system modular with these files:

- `tokenizer` — lex SQL into tokens
- `parser` — build an AST
- `storage` — hold tables and rows in memory
- `executor` — execute statements and queries
- `repl` — accept SQL input and return results

## sqllogictest Workflow

Use the official sqllogictest corpus from SQLite:

`https://www.sqlite.org/sqllogictest/dir?ci=trunk`

Use `select1.test` through `select5.test` in `tests/sqllogictest/`.

Do not run all files at once. Progress in stages by editing `current_stage.txt`.

| Stage | `current_stage.txt` contents | Advance when |
|---|---|---|
| 1 | `select1.test` | at least 80% passing |
| 2 | `select1.test`, `select2.test` | at least 80% passing |
| 3 | add `select3.test` | at least 80% passing |
| 4 | add `select4.test` | at least 80% passing |
| 5 | add `select5.test` | final target |

Full-suite runs are final evaluation only. Do not use the entire sqllogictest corpus as the normal development loop.

## Current Task

Your current task is to follow this order before doing broad optimization:

1. Confirm the runner is truly distinguishing staged files correctly.
2. Work on correctness bugs in the current staged file or files.
3. Advance `current_stage.txt` gradually only after the current stage is strong enough.
4. Treat performance work as secondary unless a staged run times out or clearly makes the machine struggle.

Do not assume the computer is too weak. First prove whether the issue is incorrect test scope, a correctness bug, or a real slow query.

When you need actual failure details for a large file, do not write long inline Python heredocs that replay thousands of cases blindly.
Use the existing tools first:

- `python3 scripts/run_slt_stage.py` for normal staged runs
- `python3 scripts/inspect_slt_cases.py <file> <start_case> [end_case]` for targeted case inspection

## Development Strategy

- Use staged `select` files to build correctness and momentum.
- Expand coverage gradually in small batches.
- Keep daily development on `python3 scripts/run_slt_stage.py`.
- If needed later, create separate stage files for broader checkpoints such as core queries, joins, or aggregates.
- Run broader suites only occasionally and with strict timeouts.
- Reserve the biggest runs for the end of the project or for a stronger machine if one is available.

## Iteration Loop

Follow this loop every time:

1. Pick the highest-signal failing behavior.
2. Change only the module most responsible for that failure.
3. Remove dead code or abandoned paths in the edited file.
4. Run `python3 scripts/run_slt_stage.py`.
5. Update `PROGRESS.md`, `TASKS.md`, and `BUG_REPORT.md`.
6. If progress increases, continue. If not, try a different fix.

## Priorities

Fix issues in this order:

1. Crashes and exceptions
2. Parser failures on valid SQL
3. Wrong row counts
4. Wrong values
5. Formatting or ordering mismatches
6. Performance issues that cause timeouts

## Performance Guardrails

- Do not increase test scope just to get a bigger number.
- Do not run the full sqllogictest directory during normal development.
- If a staged test times out, treat it as a real bug.
- Prefer correctness first, then optimize only when a specific staged test is too slow.
- Do not assume the machine is the problem until a small staged run is actually timing out.

## Correctness Vs Performance

- If a small staged run finishes quickly but fails assertions, that is a correctness problem. Fix logic first.
- If a staged run times out, hangs, or makes the machine noticeably lag even with a small stage, that is a performance problem. Then optimize.
- The wrong strategy is "optimize everything now because the full suite will be large."
- Do not rerun the same slow stage unchanged over and over. Inspect the failing range, fix the likely slow path, then rerun.

## Code Rules

- One focused change per iteration
- No speculative features
- No dead code
- No leftover `TODO` or `FIXME` comments
- Keep modules separated and simple
- Use failing tests to choose the next task

## Tracking Files

Keep these updated every iteration:

- `TASKS.md` — current task, done items, backlog
- `PROGRESS.md` — pass counts and notes for each iteration
- `BUG_REPORT.md` — failing SQL, expected output, actual output, root cause, and fix
