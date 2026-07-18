---
name: duckdb-analytics
description: >
  Profile and query CSV, TSV, JSON, JSONL, and Parquet sources with the official
  DuckDB Node API. Produces append-only JSON evidence without pandas, notebooks,
  task-local Python, or global package installation. Use as the executable data
  engine behind Mozaika's analyze-report-data role.
version: 1.0.0
type: script
runtime: node
scripts:
  - name: analyze.js
    description: Profile registered sources and execute bounded read-only analytical SELECT queries.
permissions: [fs, net]
install:
  - kind: npm
    package: "@duckdb/node-api"
    expected_version: "1.5.4-r.1"
when_to_use: Use for reproducible profiling and read-only aggregation over local files or inventoried Hugging Face Parquet URLs.
timeout_sec: 300
license: MIT adaptation notes in ATTRIBUTION.md
---

# DuckDB Analytics

This is the executable analytical engine for the Mozaika data role. The role
still owns scope, cleaning decisions, claims, anomalies, and handoff contracts;
this skill owns deterministic reads, profiles, and SQL result materialization.

```bash
node scripts/analyze.js --request /absolute/job/data-request.json
```

The request must use `mozaika-duckdb-request/v1`:

```json
{
  "contract_version": "mozaika-duckdb-request/v1",
  "output": "jobs/run-001/output/duckdb-analysis.json",
  "sources": [
    {"source_id": "ratings", "location": "/absolute/input/ratings.parquet", "format": "parquet"}
  ],
  "queries": [
    {"query_id": "top_models", "sql": "SELECT model, AVG(rating) AS rating FROM ratings GROUP BY model ORDER BY rating DESC LIMIT 20"}
  ]
}
```

Safety and evidence rules:

- Sources are registered under their `source_id`; analytical SQL may read only
  those views.
- Only one read-only `SELECT`/`WITH` statement per query is accepted. DDL, DML,
  PRAGMA, extension loading, direct file readers, comments, and multiple
  statements are rejected.
- Remote reads are limited to HTTPS URLs on official Hugging Face hosts.
- The output is create-only. Existing files and every source remain untouched.
- Request and local sources must already be durable files under the Ouroboros
  data root. Output is confined to this skill's state directory; relative
  output names resolve from `OUROBOROS_SKILL_STATE_DIR`.
- SQL results are evidence, not automatically owner-facing claims. The data
  role must register claim ids, calculation rules, caveats, and source lineage.
- Spreadsheet formats outside the declared set must be routed to a reviewed
  spreadsheet skill, never converted by an improvised Python script.
