# Task list

## In progress
- [ ] None

## Done
- [x] Demo dashboard: add a lightweight one-page class video view backed by tracked repo metrics — 2026-04-17 — added `dashboard/` plus `scripts/generate_dashboard_data.py` so the demo page shows project overview, sqllogictest status, benchmarks, milestones, and example SQL results
- [x] Executor optimization: stop re-evaluating `WHERE` terms already enforced by candidate pruning or indexed join lookups — 2026-04-17 — full local staged scope still passes `10706/10706`, `three_way_join` improved from `33.649 ms/run` to `29.270 ms/run`, and `select4.test` runtime dropped from `18.292s` to `10.694s`
- [x] Audit local sqllogictest corpus and confirm staged coverage matches the full local suite — 2026-04-17 — only `select1.test` through `select5.test` exist locally, and `current_stage.txt` already covers all 10706 local cases
- [x] Runner tooling: total runtime, per-file timing, and slowest-case reporting for controlled sqllogictest runs — 2026-04-17 — `run_slt_stage.py --show-file-times --show-slowest-cases N` now reports measured hotspots without changing SQL behavior
- [x] Benchmarking: add a lightweight representative-query benchmark script — 2026-04-17 — `scripts/benchmark_queries.py` covers filtered scans, selective joins, and three-way joins
- [x] Stage 5 readiness: advance staged runner to `select5.test` and validate the final staged target — 2026-04-16 — 10706 tests passing
- [x] Parser + executor: multi-table `FROM t1, t2` cartesian scans with WHERE filtering — 2026-04-16 — 10706 tests passing
- [x] Stage 4 readiness: advance staged runner to `select4.test` and fix the first failing correctness bug it exposes — 2026-04-16 — 9270 tests passing
- [x] Parser + executor: `IN (...)`, `UNION`, `UNION ALL`, `EXCEPT`, and `INTERSECT` — 2026-04-09 — 8160 tests passing
- [x] Parser + executor: accept `CREATE INDEX` as a no-op setup statement — 2026-04-09 — 7160 tests passing
- [x] Executor: scalar NULL helpers and `coalesce(...)` — 2026-04-09 — 7144 tests passing
- [x] Executor: correlated subquery alias scoping and qualified column resolution — 2026-04-09 — 7036 tests passing
- [x] Tokenizer + parser + executor: expression SELECTs, WHERE predicates, CASE, subqueries, and basic aggregates — 2026-04-09 — 5569 tests passing
- [x] Runner isolation per sqllogictest file — 2026-04-09 — 1854 tests passing
- [x] Tokenizer + basic pipeline: CREATE TABLE, INSERT, SELECT *, projections, ORDER BY — 2026-04-09 — 1603 tests passing
- [x] Scaffold module structure + sqllogictest runner — 2026-04-09 — 0 tests passing

## Backlog (prioritized)
- [ ] Storage: NULL handling
- [ ] Executor: SQL NULL truth-table edge cases
- [ ] Executor: aggregate functions beyond whole-query mode
- [ ] Parser + executor: broader sqllogictest checkpoints beyond `select1.test`-`select5.test` if more corpus files are added locally
