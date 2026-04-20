# SQL Database Agent — optimization_promt.md

You are an autonomous coding agent working on the final validation and improvement phase of a lightweight in-memory SQL database.

Your goals are ordered strictly:

1. Verify whether the database passes the broader sqllogictest suite beyond `select1.test` through `select5.test`.
2. Fix correctness bugs exposed by broader validation.
3. Improve code quality: modularity, clarity, and dead code removal.
4. Add lightweight benchmarking and timing support.
5. Optimize performance only after correctness and structure are under control.

Work autonomously. Do not ask the user questions. Do not pause for confirmation. If something is unclear, make a reasonable decision, document it in `TASKS.md`, and continue.

Use the existing `TASKS.md`, `PROGRESS.md`, and `BUG_REPORT.md` files as project history and continue updating them. Do not replace them, reset them, or start new tracking files.

This phase is not complete just because the code "looks cleaner." Keep iterating until the exit criteria in this file are met or you hit the same blocker 3 times in a row.

## First Priority: Validate The Real Test Scope

Do not assume passing `select1.test` through `select5.test` means the full sqllogictest corpus is passing.

Your first task is to determine what "full suite" is actually available in this repo and test against it safely.

Rules:

- If only `select1.test` through `select5.test` are present locally, state that clearly in `PROGRESS.md`.
- If more sqllogictest files are available locally, test them in controlled batches.
- Do not invent nonexistent coverage claims.
- Do not claim "all sqllogictest passes" unless the broader local corpus has actually been run.

## Safe Test Workflow

Normal development command:

```bash
python3 scripts/run_slt_stage.py
```

Targeted debugging command:

```bash
python3 scripts/inspect_slt_cases.py <file> <start_case> [end_case]
```

Direct runner use is allowed only for controlled validation of explicit files, never for blind directory-wide development loops.

Never use these during normal work:

- `python3 -m sql_db.sqllogictest_runner tests/sqllogictest/`
- `python3 -m sql_db.sqllogictest_runner --allow-directory tests/sqllogictest/`
- any command that blindly runs the entire corpus without batching

If broader validation is needed, expand scope in small explicit groups and record the results.

## Optimization Loop

Repeat this loop:

1. Run the full local staged sqllogictest validation.
2. Run the lightweight benchmark suite.
3. Compare the results to the current targets in this file.
4. If all tests still pass and at least one benchmark target is not yet met, make one focused optimization change.
5. Rerun the same validation and benchmarks immediately.
6. Record the before/after numbers in `PROGRESS.md`.

Do not stop after a code cleanup pass if the benchmark targets are still unmet.
Do not stop after a benchmark improvement if the tests are no longer fully passing.

## Required Order Of Work

Follow this order exactly:

1. Audit the available sqllogictest files in the repo.
2. Record what subset is currently being tested and what subset is not.
3. Run broader validation in safe batches.
4. Fix correctness bugs found there.
5. Clean up code structure and remove dead code.
6. Add timing or benchmark support.
7. Optimize performance bottlenecks revealed by tests or benchmarks.

Do not start with optimization just because large suites may be slow.

## Correctness Before Optimization

Use this rule:

- If a test run finishes quickly and fails assertions, that is a correctness bug.
- If a test run times out, hangs, or becomes extremely slow, that is a performance bug.

Do not treat machine slowness as the first explanation. First determine whether the issue is:

- missing or incorrect SQL behavior
- too-broad test scope
- a specific slow query or join path

## Code Quality Pass

After correctness is stable on the broader available suite, improve code quality.

Focus on:

- modularity between `tokenizer`, `parser`, `storage`, `executor`, and `repl`
- removing dead code and unused helpers
- simplifying long functions
- improving naming and readability
- keeping comments brief and useful

Do not do large speculative rewrites. Keep behavior stable while cleaning structure.

## Benchmarking And Timing

Add lightweight measurement tools after correctness is stable.

Good ideas:

- per-file sqllogictest timing
- total suite timing
- optional per-case timing for very slow files
- a small benchmark script for representative query patterns
- logging the slowest files or slowest cases

Benchmarking should help answer:

- which file is slow
- which query pattern is slow
- whether a change improved runtime

Do not build a large benchmarking system. Keep it simple and useful.

Use these commands:

```bash
python3 scripts/run_slt_stage.py --show-file-times --show-slowest-cases 5
python3 scripts/benchmark_queries.py --rows 5000
```

Treat the current measured baseline as:

- sqllogictest full local staged scope: `10706/10706` passing, `timed_out=0`, total runtime about `26.986s`
- benchmark `filtered_scan`: about `5.131 ms/run`
- benchmark `equality_join`: about `0.651 ms/run`
- benchmark `three_way_join`: about `33.649 ms/run`

These are not success targets. They are the baseline to beat while keeping correctness intact.

## Exit Criteria

Continue the optimization loop until all of these are true at the same time:

1. `python3 scripts/run_slt_stage.py --show-file-times --show-slowest-cases 5` still reports full passing local coverage with:
   - `passed=10706`
   - `total=10706`
   - `timed_out=0`
   - no suite timeout
2. `python3 scripts/benchmark_queries.py --rows 5000` shows measurable improvement over the baseline in at least the real hotspot benchmark:
   - `three_way_join` average time is below `30.000 ms/run`
3. No benchmark regresses badly while chasing that goal:
   - `filtered_scan` should stay below `6.000 ms/run`
   - `equality_join` should stay below `1.000 ms/run`
4. The code is left cleaner than before:
   - remove dead code
   - keep module boundaries clear
   - avoid speculative rewrites

If the hotspot target is met, continue only if there is another clearly measured bottleneck worth fixing. Otherwise stop and document the achieved numbers.

## Performance Work

Only optimize after:

- broader correctness has been checked
- dead code has been removed
- basic timing exists

Focus on real bottlenecks, especially:

- joins
- cartesian products
- repeated full scans
- unnecessary intermediate results
- missing predicate pushdown

Prefer measured improvements over guesswork.

Focus first on the measured hotspots already recorded in `PROGRESS.md`:

- `select4.test` is the dominant sqllogictest runtime hotspot
- `three_way_join` is the dominant benchmark hotspot

Do not optimize random areas of the codebase without evidence from these commands.

## Tracking Requirements

Keep these updated:

- `TASKS.md` — current task, done work, next steps
- `PROGRESS.md` — what suite was actually run, pass counts, timing notes
- `BUG_REPORT.md` — concrete failing SQL, expected output, actual output, root cause, fix

When broader validation is incomplete, explicitly say what remains untested.

## Final Standard

Do not say the project passes the full sqllogictest suite unless that has been proven by actual runs.

The correct final outcome is:

- known tested scope
- known untested scope
- correctness bugs reduced
- codebase cleaner and more modular
- lightweight performance measurements in place
- optimization work guided by real evidence
- benchmark targets met without breaking the local sqllogictest pass count
