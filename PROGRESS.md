# Test progress log

| Iteration | Date | Tests passing | Tests total | Delta | Notes |
|---|---|---|---|---|---|
| 0 | 2026-04-09 | 0 | 10706 | — | Scaffold + runner execute without crashing |
| 1 | 2026-04-09 | 1603 | 10706 | +1603 | Tokenizer, parser, storage, and executor now handle CREATE TABLE, INSERT, SELECT *, simple projections, ORDER BY |
| 2 | 2026-04-09 | 1854 | 10706 | +251 | Runner now resets database state per sqllogictest file |
| 3 | 2026-04-09 | 5569 | 10706 | +3715 | Expression parser and executor now handle arithmetic, WHERE, CASE, EXISTS, scalar subqueries, and whole-query aggregates |
| 4 | 2026-04-09 | 7036 | 10706 | +1467 | Executor now resolves correlated subquery qualifiers against aliases before outer rows |
| 5 | 2026-04-09 | 7144 | 10706 | +108 | Executor now supports `coalesce(...)` for NULL-sensitive predicates in select2/select3 |
| 6 | 2026-04-09 | 8160 | 10706 | +1016 | Parser and executor now handle `IN (...)` predicates plus left-associative compound selects |
| 7 | 2026-04-16 | 2062 | 2062 | +1031 | Advanced `current_stage.txt` to `select1.test` + `select2.test`; staged runner scope is behaving correctly and both files pass cleanly |
| 8 | 2026-04-16 | 5413 | 5413 | +3351 | Advanced `current_stage.txt` to include `select3.test`; stage 3 passes cleanly with no timeouts, so the next bug is beyond `select3` |
| 9 | 2026-04-16 | 7487 | 7507 | +2074 | Advanced `current_stage.txt` to include `select4.test`; runner scope stayed correct, but 20 multi-table join queries timed out because the executor was still materializing huge comma-join intermediates |
| 10 | 2026-04-16 | 9270 | 9270 | +1783 | Executor now prunes `WHERE` conjuncts during `FROM` scans, uses indexed equality lookups, and semijoin-style candidate reduction; `select1.test` through `select4.test` pass cleanly with no timeouts |
| 11 | 2026-04-16 | 10706 | 10706 | +1436 | Advanced `current_stage.txt` to include `select5.test`; final staged target passes cleanly with no timeouts |
| 12 | 2026-04-17 | 10706 | 10706 | +0 | Audited the local sqllogictest corpus, confirmed only `select1.test` through `select5.test` exist locally, and added timing/benchmark tooling while revalidating the full local staged scope |
| 13 | 2026-04-17 | 10706 | 10706 | +0 | Executor now skips re-checking `WHERE` terms already guaranteed by per-table filtering or indexed join lookups; the full staged scope still passes, `select4.test` runtime dropped to `10.694s`, and `three_way_join` improved below the `30 ms/run` target |

## 2026-04-17 Scope Audit

- Local sqllogictest inventory: only [`tests/sqllogictest/select1.test`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/tests/sqllogictest/select1.test), [`tests/sqllogictest/select2.test`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/tests/sqllogictest/select2.test), [`tests/sqllogictest/select3.test`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/tests/sqllogictest/select3.test), [`tests/sqllogictest/select4.test`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/tests/sqllogictest/select4.test), and [`tests/sqllogictest/select5.test`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/tests/sqllogictest/select5.test) are present in the repo.
- Current staged scope: [`tests/sqllogictest/current_stage.txt`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/tests/sqllogictest/current_stage.txt) already includes all five local files, so there are no additional local sqllogictest files left untested.
- Untested scope: any broader external sqllogictest corpus not checked into this repo remains untested, so the project still cannot claim full sqllogictest coverage beyond the local five-file corpus.

## 2026-04-17 Timing Snapshot

- `python3 scripts/run_slt_stage.py --show-file-times --show-slowest-cases 5` passed `10706/10706` with `timed_out=0` in `26.986s` total.
- Per-file timings: `select1.test` `1.248s`, `select2.test` `1.070s`, `select3.test` `3.360s`, `select4.test` `18.292s`, `select5.test` `3.016s`.
- Current runtime hotspot: `select4.test` cases `2413`, `2414`, `3419`, `3810`, and `2415` are the slowest passing cases at `0.231s` to `0.345s` each.

## 2026-04-17 Benchmark Snapshot

- Added [`scripts/benchmark_queries.py`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/scripts/benchmark_queries.py) for representative query-pattern timing without running the whole sqllogictest corpus.
- `python3 scripts/benchmark_queries.py --rows 5000` measured `filtered_scan` at `5.131 ms/run`, `equality_join` at `0.651 ms/run`, and `three_way_join` at `33.649 ms/run`.

## 2026-04-17 Optimization Loop Result

- Focused optimization: [`sql_db/executor.py`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/sql_db/executor.py) now tracks which `WHERE` terms were already enforced by `_table_candidate_indexes()` or `_indexed_lookup()` and skips re-evaluating those terms during deeper join recursion.
- Validation after the optimization: `python3 scripts/run_slt_stage.py --show-file-times --show-slowest-cases 5` still passed `10706/10706` with `timed_out=0`, but total runtime improved from `26.986s` to `16.689s`.
- Updated per-file timings: `select1.test` `0.983s`, `select2.test` `0.832s`, `select3.test` `2.714s`, `select4.test` `10.694s`, `select5.test` `1.465s`.
- Updated hotspot cases: `select4.test` cases `2413`, `3419`, `3810`, `3416`, and `2414` are now the slowest passing cases at `0.127s` to `0.183s` each.
- Updated benchmark results from `python3 scripts/benchmark_queries.py --rows 5000`: `filtered_scan` `5.435 ms/run`, `equality_join` `0.627 ms/run`, and `three_way_join` `29.270 ms/run`.
- Exit criteria status: the full local staged scope still passes, `three_way_join` is now below the `30.000 ms/run` target, and the guardrails still hold for `filtered_scan` and `equality_join`.

## 2026-04-17 Demo Dashboard

- Added [`dashboard/index.html`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/dashboard/index.html), [`dashboard/app.js`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/dashboard/app.js), and [`dashboard/styles.css`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/dashboard/styles.css) as a lightweight one-page demo dashboard for the project video.
- Added [`scripts/generate_dashboard_data.py`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/scripts/generate_dashboard_data.py), which rebuilds [`dashboard/data.js`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/dashboard/data.js) from `TASKS.md`, `PROGRESS.md`, `BUG_REPORT.md`, `README.md`, [`tests/sqllogictest/current_stage.txt`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/tests/sqllogictest/current_stage.txt), and live example query outputs from the SQL engine.
- Dashboard scope: project overview, local sqllogictest pass coverage, tracked benchmark snapshot, milestone timeline, and example SQL statements with simple result views sized for a short recorded demo.
