# SQL Database Agent — DASHBOARD_PROMPT.md

You are an autonomous coding agent building a simple demo dashboard for a class project video.

The goal is not to build a full product UI. The goal is to create a clean, clear, lightweight dashboard that helps explain the project visually.

Work autonomously. Do not ask the user questions. Do not pause for confirmation. If something is unclear, make a reasonable decision, document it in `TASKS.md`, and continue.

Use the existing `TASKS.md`, `PROGRESS.md`, `BUG_REPORT.md`, `README.md`, and benchmark/test tooling as project context. Do not replace those files. Read them and use them as the source of truth for progress and results.

## Main Goal

Build a small dashboard that is good for a recorded demo video.

The dashboard should communicate:

1. what the project is
2. how much sqllogictest coverage is passing
3. what performance or benchmark progress has been made
4. a few example SQL capabilities
5. the overall development story

## Dashboard Requirements

The dashboard should be simple, polished, and easy to understand in under one minute of viewing.

Include these sections:

### 1. Project Overview

- project title
- one short description of the SQL database project
- one short description of the agent-driven workflow

### 2. Test Progress

Show clearly:

- current passing tests
- total tests
- whether timeouts are present
- current known tested scope

Use real numbers from the repo, not invented placeholders.

### 3. Benchmark Snapshot

Show the current benchmark values from the repo workflow, such as:

- filtered scan
- equality join
- three-way join
- total sqllogictest runtime if available

### 4. Milestones Or Timeline

Summarize the major progress milestones from `PROGRESS.md` in a visually clear way.

### 5. Example Queries

Show a few example SQL statements that demonstrate the project, such as:

- table creation
- insert
- select with filter
- join or aggregate

If possible, show the SQL and a simple result view.

## Design Guidance

Keep it lightweight and demo-friendly.

- Make it visually clean and modern.
- Prefer one page.
- Use strong hierarchy and readable typography.
- Use cards, small charts, or progress indicators where helpful.
- Do not build unnecessary authentication, forms, or backend services.
- Do not overcomplicate the app.

This is a demo dashboard, not a production admin panel.

## Technical Guidance

- Prefer the simplest approach that fits the current repo.
- If the repo already has a frontend structure, use it.
- If there is no frontend structure, create the smallest reasonable dashboard setup.
- Prefer static or local data derived from repo files rather than complex live data plumbing.
- If needed, hardcode current metrics from the repo into a single dashboard page, but keep the values aligned with the latest tracked results.

## Workflow

Follow this order:

1. Inspect the repo for any existing frontend or app structure.
2. Inspect `PROGRESS.md`, `TASKS.md`, `BUG_REPORT.md`, and relevant scripts to gather current metrics.
3. Build the dashboard UI.
4. Make sure it runs locally.
5. Keep the implementation small and easy to demo.

## Constraints

- Do not break the SQL engine or test tooling.
- Do not rewrite unrelated parts of the project.
- Do not spend time on features that do not help the demo.
- Do not build a giant dashboard system.

## Success Standard

The work is successful if:

- the dashboard runs locally
- the dashboard is visually clear in a video
- the dashboard shows real project progress and benchmark data
- the dashboard makes the project easier to explain

## Deliverable

Produce the dashboard code, wire it into the repo in a simple way, and leave brief notes in the tracking files about what was added for the demo.
