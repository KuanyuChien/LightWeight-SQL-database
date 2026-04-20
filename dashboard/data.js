window.DASHBOARD_DATA = {
  "generatedFrom": {
    "tasks": "TASKS.md",
    "progress": "PROGRESS.md",
    "readme": "README.md",
    "stageFile": "tests/sqllogictest/current_stage.txt"
  },
  "project": {
    "title": "Lightweight In-Memory SQL Database",
    "description": "A from-scratch Python SQL engine that tokenizes, parses, stores rows in memory, and executes relational queries against a staged sqllogictest corpus.",
    "agentWorkflow": "An agent loop ships one database capability at a time, reruns correctness and performance checks, and records the resulting milestones in the repo.",
    "story": "The project started from a minimal SQL pipeline, expanded step-by-step through parser and executor features, then shifted into performance work once multi-table joins began timing out."
  },
  "testSnapshot": {
    "passed": 10706,
    "total": 10706,
    "timedOut": 0,
    "coveragePercent": 100.0,
    "runtimeSeconds": 16.689,
    "previousRuntimeSeconds": 26.986,
    "knownScope": "Current staged coverage matches every local sqllogictest file checked into the repo.",
    "externalScopeNote": "Any broader external sqllogictest corpus that is not checked into this repo remains untested.",
    "localFiles": [
      "select1.test",
      "select2.test",
      "select3.test",
      "select4.test",
      "select5.test"
    ],
    "stageFiles": [
      "select1.test",
      "select2.test",
      "select3.test",
      "select4.test",
      "select5.test"
    ],
    "fileTimings": [
      {
        "name": "select1.test",
        "seconds": 0.983
      },
      {
        "name": "select2.test",
        "seconds": 0.832
      },
      {
        "name": "select3.test",
        "seconds": 2.714
      },
      {
        "name": "select4.test",
        "seconds": 10.694
      },
      {
        "name": "select5.test",
        "seconds": 1.465
      }
    ],
    "hotspots": "`select4.test` cases `2413`, `3419`, `3810`, `3416`, and `2414` are now the slowest passing cases at `0.127s` to `0.183s` each.",
    "bugSummary": {
      "rootCause": "[`sql_db/executor.py`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/sql_db/executor.py) built full cartesian products in `_source_contexts()` before applying `WHERE`, and later still scanned too many candidates when equality joins only became useful near the end of the `FROM` order.",
      "fix": "[`sql_db/executor.py`](file:///Users/qianguanyu/Desktop/CS3960/final-project-u1470293/sql_db/executor.py) now splits `AND` terms, evaluates resolvable predicates during recursive `FROM` scans, reuses per-column row indexes for equality lookups against already-bound tables, and applies semijoin-style candidate reduction across filtered equality joins before recursion starts.",
      "result": "`python3 scripts/run_slt_stage.py` passed `5413/5413` with `timed_out=0` after adding `select3.test` to `tests/sqllogictest/current_stage.txt`."
    },
    "latestIteration": 13,
    "latestNotes": "Executor now skips re-checking `WHERE` terms already guaranteed by per-table filtering or indexed join lookups; the full staged scope still passes, `select4.test` runtime dropped to `10.694s`, and `three_way_join` improved below the `30 ms/run` target"
  },
  "benchmarkSnapshot": {
    "rowCount": 5000,
    "metrics": [
      {
        "name": "filtered_scan",
        "label": "filtered scan",
        "avgMsPerRun": 5.435
      },
      {
        "name": "equality_join",
        "label": "equality join",
        "avgMsPerRun": 0.627
      },
      {
        "name": "three_way_join",
        "label": "three way join",
        "avgMsPerRun": 29.27
      }
    ],
    "targetMs": 30.0
  },
  "milestones": [
    {
      "title": "Scaffold module structure + sqllogictest runner",
      "date": "2026-04-09",
      "summary": "0 tests passing",
      "testsPassing": 0
    },
    {
      "title": "Tokenizer + basic pipeline: CREATE TABLE, INSERT, SELECT *, projections, ORDER BY",
      "date": "2026-04-09",
      "summary": "1603 tests passing",
      "testsPassing": 1603
    },
    {
      "title": "Tokenizer + parser + executor: expression SELECTs, WHERE predicates, CASE, subqueries, and basic aggregates",
      "date": "2026-04-09",
      "summary": "5569 tests passing",
      "testsPassing": 5569
    },
    {
      "title": "Parser + executor: `IN (...)`, `UNION`, `UNION ALL`, `EXCEPT`, and `INTERSECT`",
      "date": "2026-04-09",
      "summary": "8160 tests passing",
      "testsPassing": 8160
    },
    {
      "title": "Stage 4 readiness: advance staged runner to `select4.test` and fix the first failing correctness bug it exposes",
      "date": "2026-04-16",
      "summary": "9270 tests passing",
      "testsPassing": 9270
    },
    {
      "title": "Stage 5 readiness: advance staged runner to `select5.test` and validate the final staged target",
      "date": "2026-04-16",
      "summary": "10706 tests passing",
      "testsPassing": 10706
    },
    {
      "title": "Benchmarking: add a lightweight representative-query benchmark script",
      "date": "2026-04-17",
      "summary": "`scripts/benchmark_queries.py` covers filtered scans, selective joins, and three-way joins",
      "testsPassing": null
    },
    {
      "title": "Executor optimization: stop re-evaluating `WHERE` terms already enforced by candidate pruning or indexed join lookups",
      "date": "2026-04-17",
      "summary": "full local staged scope still passes `10706/10706`, `three_way_join` improved from `33.649 ms/run` to `29.270 ms/run`, and `select4.test` runtime dropped from `18.292s` to `10.694s`",
      "testsPassing": 10706
    },
    {
      "title": "Demo dashboard: add a lightweight one-page class video view backed by tracked repo metrics",
      "date": "2026-04-17",
      "summary": "added `dashboard/` plus `scripts/generate_dashboard_data.py` so the demo page shows project overview, sqllogictest status, benchmarks, milestones, and example SQL results",
      "testsPassing": null
    }
  ],
  "progressSeries": [
    {
      "iteration": 0,
      "date": "2026-04-09",
      "passed": 0,
      "total": 10706,
      "delta": "\u2014",
      "notes": "Scaffold + runner execute without crashing"
    },
    {
      "iteration": 1,
      "date": "2026-04-09",
      "passed": 1603,
      "total": 10706,
      "delta": "+1603",
      "notes": "Tokenizer, parser, storage, and executor now handle CREATE TABLE, INSERT, SELECT *, simple projections, ORDER BY"
    },
    {
      "iteration": 2,
      "date": "2026-04-09",
      "passed": 1854,
      "total": 10706,
      "delta": "+251",
      "notes": "Runner now resets database state per sqllogictest file"
    },
    {
      "iteration": 3,
      "date": "2026-04-09",
      "passed": 5569,
      "total": 10706,
      "delta": "+3715",
      "notes": "Expression parser and executor now handle arithmetic, WHERE, CASE, EXISTS, scalar subqueries, and whole-query aggregates"
    },
    {
      "iteration": 4,
      "date": "2026-04-09",
      "passed": 7036,
      "total": 10706,
      "delta": "+1467",
      "notes": "Executor now resolves correlated subquery qualifiers against aliases before outer rows"
    },
    {
      "iteration": 5,
      "date": "2026-04-09",
      "passed": 7144,
      "total": 10706,
      "delta": "+108",
      "notes": "Executor now supports `coalesce(...)` for NULL-sensitive predicates in select2/select3"
    },
    {
      "iteration": 6,
      "date": "2026-04-09",
      "passed": 8160,
      "total": 10706,
      "delta": "+1016",
      "notes": "Parser and executor now handle `IN (...)` predicates plus left-associative compound selects"
    },
    {
      "iteration": 7,
      "date": "2026-04-16",
      "passed": 2062,
      "total": 2062,
      "delta": "+1031",
      "notes": "Advanced `current_stage.txt` to `select1.test` + `select2.test`; staged runner scope is behaving correctly and both files pass cleanly"
    },
    {
      "iteration": 8,
      "date": "2026-04-16",
      "passed": 5413,
      "total": 5413,
      "delta": "+3351",
      "notes": "Advanced `current_stage.txt` to include `select3.test`; stage 3 passes cleanly with no timeouts, so the next bug is beyond `select3`"
    },
    {
      "iteration": 9,
      "date": "2026-04-16",
      "passed": 7487,
      "total": 7507,
      "delta": "+2074",
      "notes": "Advanced `current_stage.txt` to include `select4.test`; runner scope stayed correct, but 20 multi-table join queries timed out because the executor was still materializing huge comma-join intermediates"
    },
    {
      "iteration": 10,
      "date": "2026-04-16",
      "passed": 9270,
      "total": 9270,
      "delta": "+1783",
      "notes": "Executor now prunes `WHERE` conjuncts during `FROM` scans, uses indexed equality lookups, and semijoin-style candidate reduction; `select1.test` through `select4.test` pass cleanly with no timeouts"
    },
    {
      "iteration": 11,
      "date": "2026-04-16",
      "passed": 10706,
      "total": 10706,
      "delta": "+1436",
      "notes": "Advanced `current_stage.txt` to include `select5.test`; final staged target passes cleanly with no timeouts"
    },
    {
      "iteration": 12,
      "date": "2026-04-17",
      "passed": 10706,
      "total": 10706,
      "delta": "+0",
      "notes": "Audited the local sqllogictest corpus, confirmed only `select1.test` through `select5.test` exist locally, and added timing/benchmark tooling while revalidating the full local staged scope"
    },
    {
      "iteration": 13,
      "date": "2026-04-17",
      "passed": 10706,
      "total": 10706,
      "delta": "+0",
      "notes": "Executor now skips re-checking `WHERE` terms already guaranteed by per-table filtering or indexed join lookups; the full staged scope still passes, `select4.test` runtime dropped to `10.694s`, and `three_way_join` improved below the `30 ms/run` target"
    }
  ],
  "storyCards": [
    {
      "label": "Start",
      "value": "0/10706",
      "detail": "Initial scaffold ran without crashing, creating a clean baseline for the agent loop."
    },
    {
      "label": "Coverage",
      "value": "10706/10706",
      "detail": "The local staged sqllogictest corpus now passes end-to-end with no timed-out cases."
    },
    {
      "label": "Runtime",
      "value": "16.689s",
      "detail": "The tracked full staged validation time fell after join predicate reuse stopped redundant WHERE checks."
    },
    {
      "label": "Three-way join",
      "value": "29.270 ms/run",
      "detail": "Representative join-heavy benchmarks now land below the tracked 30 ms/run target."
    }
  ],
  "examples": [
    {
      "label": "Table creation",
      "kind": "setup",
      "sql": "CREATE TABLE students(id INTEGER, name VARCHAR(20), cohort INTEGER);",
      "note": "Defines a simple in-memory relation with typed columns."
    },
    {
      "label": "Insert rows",
      "kind": "setup",
      "sql": "INSERT INTO students VALUES(1, 'Ada', 2026);\nINSERT INTO students VALUES(2, 'Linus', 2025);\nINSERT INTO students VALUES(3, 'Grace', 2026);",
      "note": "The engine stores rows immediately, so follow-up queries can read them without any external database service."
    },
    {
      "label": "Select with filter",
      "kind": "result",
      "sql": "SELECT id, name FROM students WHERE cohort = 2026 ORDER BY id;",
      "columns": [
        "id",
        "name"
      ],
      "rows": [
        [
          1,
          "Ada"
        ],
        [
          3,
          "Grace"
        ]
      ]
    },
    {
      "label": "Join",
      "kind": "result",
      "sql": "SELECT students.name, projects.title FROM students, projects WHERE students.id = projects.student_id ORDER BY 1, 2;",
      "columns": [
        "name",
        "title"
      ],
      "rows": [
        [
          "Ada",
          "optimizer"
        ],
        [
          "Ada",
          "runner"
        ],
        [
          "Grace",
          "dashboard"
        ]
      ]
    },
    {
      "label": "Aggregate",
      "kind": "result",
      "sql": "SELECT count(*) FROM projects;",
      "columns": [
        "count(*)"
      ],
      "rows": [
        [
          3
        ]
      ]
    }
  ]
};
