# Bug report log

## 2026-04-17

- Performance hotspot validation: `python3 scripts/benchmark_queries.py --rows 5000` measured `three_way_join` at `33.649 ms/run` before the next executor change, so the project still missed the hotspot target even though correctness was stable.
- Root cause: [`sql_db/executor.py`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/sql_db/executor.py) was still re-evaluating already-satisfied `WHERE` terms at every recursion depth in `_scan_source_contexts()`, even when `_table_candidate_indexes()` or `_indexed_lookup()` had already guaranteed those predicates.
- Fix: [`sql_db/executor.py`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/sql_db/executor.py) now carries forward the set of `WHERE` terms already enforced by candidate pruning, so `_where_terms_match()` only checks the remaining unresolved predicates for each partially bound join row.
- Result: `python3 scripts/run_slt_stage.py --show-file-times --show-slowest-cases 5` still passed `10706/10706` with `timed_out=0`, total runtime improved from `26.986s` to `16.689s`, `select4.test` dropped from `18.292s` to `10.694s`, and `python3 scripts/benchmark_queries.py --rows 5000` improved `three_way_join` from `33.649 ms/run` to `29.270 ms/run` while keeping `filtered_scan` at `5.435 ms/run` and `equality_join` at `0.627 ms/run`.
- Local corpus audit: `find tests/sqllogictest -name '*.test'` found only `select1.test` through `select5.test`, so there was no broader local sqllogictest corpus to validate beyond the existing staged files.
- Full local validation: `python3 scripts/run_slt_stage.py --show-file-times --show-slowest-cases 5` passed `10706/10706` with `timed_out=0` in `26.986s`; no new correctness failures were exposed.
- Timing hotspot report: the slowest passing cases are `select4.test` cases `2413`, `2414`, `3419`, `3810`, and `2415`, each still completing under `0.35s` after the earlier join-pruning fix.
- Tooling update: [`sql_db/sqllogictest_runner.py`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/sql_db/sqllogictest_runner.py) now records total runtime, per-file timings, and optional slowest-case timings, and [`scripts/benchmark_queries.py`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/scripts/benchmark_queries.py) adds a lightweight benchmark path for filtered scans and join-heavy queries.
- Conclusion: no new concrete failing SQL was found in the full local corpus; the next performance work should start from the measured `select4.test` and `three_way_join` hotspots rather than from unproven guesses.

## 2026-04-16

- Stage 2 validation: no staged failures in `select1.test` + `select2.test`.
- Result: `python3 scripts/run_slt_stage.py` passed `2062/2062` with `timed_out=0` after adding `select2.test` to `tests/sqllogictest/current_stage.txt`.
- Conclusion: staged runner scope is honoring `current_stage.txt`; next action is to advance to `select3.test` and capture the first correctness failure there.
- Stage 3 validation: no staged failures in `select1.test` + `select2.test` + `select3.test`.
- Result: `python3 scripts/run_slt_stage.py` passed `5413/5413` with `timed_out=0` after adding `select3.test` to `tests/sqllogictest/current_stage.txt`.
- Conclusion: current staged coverage is stronger than the old progress log suggested; the next meaningful bug search moves to `select4.test`.
- Stage 4 initial failure: `python3 scripts/run_slt_stage.py` reached `7487/7507` with `timed_out=20` after adding `select4.test` to `tests/sqllogictest/current_stage.txt`.
- Failing SQL pattern: large comma joins in `select4.test` such as cases `2056-2067`, `2268-2271`, `2442`, `3030`, `3524`, `3678`, and `3844`; expected hashed row results, actual output was `error: test exceeded time limit`.
- Root cause: [`sql_db/executor.py`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/sql_db/executor.py) built full cartesian products in `_source_contexts()` before applying `WHERE`, and later still scanned too many candidates when equality joins only became useful near the end of the `FROM` order.
- Fix: [`sql_db/executor.py`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/sql_db/executor.py) now splits `AND` terms, evaluates resolvable predicates during recursive `FROM` scans, reuses per-column row indexes for equality lookups against already-bound tables, and applies semijoin-style candidate reduction across filtered equality joins before recursion starts.
- Stage 4 validation: `python3 scripts/run_slt_stage.py` passed `9270/9270` with `timed_out=0` after the multi-table scan fix.
- Stage 5 validation: `python3 scripts/run_slt_stage.py` passed `10706/10706` with `timed_out=0` after adding `select5.test` to `tests/sqllogictest/current_stage.txt`.
- Conclusion: staged runner scope is honoring `current_stage.txt`, the multi-table comma-join timeout bug is fixed, and the full staged `select1.test` through `select5.test` target now passes cleanly.
