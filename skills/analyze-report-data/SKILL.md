---
name: analyze-report-data
description: >
  Act as the dedicated data agent for Mozaika reporting workflows: inventory and
  fingerprint sources, preserve raw data, profile quality, apply reversible
  cleaning, calculate declared KPIs, and produce evidence-linked insight
  candidates. Use when preparing spreadsheet, export, dialogue, or tabular data
  for a downstream dashboard. Do not design dashboards, choose executive
  storylines, or build presentations.
version: 1.1.0
type: instruction
when_to_use: Use for the data stage of a configured report or executive-insight pipeline.
permissions: []
---

# Analyze Report Data

Accept one bounded handoff request and return one `mozaika-data-package/v1` result. Keep raw evidence immutable and make every transformation reproducible. When launch input uses `mozaika-input-sources/v2`, process its ordered mixed list without flattening away source kinds: validate and fetch each URL, preserve every file, and preserve directory grouping plus each child's `relative_path`.

For `insight_deck`, the handoff must also contain an immutable schema-valid `mozaika-research-brief/v1` plus its registered hash. Treat it as frozen owner scope, not as editable prose. Never infer a shorter substitute from `assignment.md`, silently merge two requested slices, rewrite a supplied research title, or drop a point because the available data cannot answer it.

## Produce the data package

1. Read the requested scope literally. Validate `research-brief.json` with `validate_gate(gate="research_brief", ...)` before analyzing an insight run. Inventory every `input_sources` entry by `source_id` and `kind`; reject an inaccessible or malformed item explicitly. For a collection URL or “all datasets”, enumerate every child source and create `mozaika-scope-ledger/v1` before analysis. A directory is one owner-selected source containing an explicit child-file inventory; a URL remains incomplete until its network children have been enumerated.
2. Before execution, read Mozaika's external-skill catalog, `mozaika/references/anthropic-skill-routing.md`, and `mozaika/references/owner-domain-profile.md`. Load the matching schema-valid `mozaika-owner-domain-<slug>` profile when available, inspect live skill readiness, and save `skill-selection.json`. Evaluate every matching installed `anthropic-*` skill first and read each serious candidate's complete `SKILL.md`. Use the suitable Anthropic method even when its instruction is short; choose another skill only when `skill-selection.json` records a concrete source, contract, reproducibility, safety, or quality incompatibility. For a collection URL, select an inventory capability that proves complete child coverage; none of the original Anthropic skills replaces source inventory.
3. Copy every user input and fetched source snapshot into durable storage, verify SHA-256, and register it in `mozaika-artifact-index/v1`. Never delete or overwrite an indexed artifact.
4. Build a schema-valid request for the selected analysis skill from the registered local sources. Read the skill's exact invocation contract first; preserve the request version, result, and receipt.
5. Inspect types, missingness, duplicates, join coverage, ranges, categories, sampling limitations, and sensitive fields with the selected reproducible method.
6. Normalize only through explicit transformations.
7. Exclude likely duplicates, technical noise, or outliers only when reversible; record rows, rule, count, and sensitivity impact.
8. Calculate KPIs only from supplied definitions. Mark missing definitions instead of inventing them.
9. Generate candidate insights with evidence strength, business relevance, counterexamples, and alternative explanations. Use confirmed profile questions, KPI and preferred slices to rank relevance, but also test unexpected dimensions so personalization does not hide strong contrary evidence. Mark which recommendations were profile-influenced and why. Register every owner-facing fact in `mozaika-claim-registry/v1` as observed, calculated, inference, hypothesis, or recommendation.
10. Build `requirement-claim-map.json` conforming to `mozaika-requirement-claim-map/v1`. Include every frozen non-constraint requirement with its exact `text_verbatim`, status, claim ids, evidence artifacts and available dimensions exactly once. Use `partial`, `unanswered`, or `not_applicable` with a concrete evidence gap instead of omission. Put every `constraint` only in `global_constraints` with `applied_global=true`; it does not need a fabricated data-stage answer.
11. Run deterministic scope, claim and `requirement_claim_map` gates. Do not describe a pilot subset as full-collection analysis and do not hand off inconsistent percentages, ranks, totals, labels or incomplete requirement coverage.
12. Verify artifact hashes and return the structured result envelope with fresh engine receipts for this instruction skill and every executed engine.

Required outputs are `scope-ledger.json`, `source-manifest.json`, preserved raw-source references, a clean analysis dataset, `data-profile.json`, `anomaly-log.json`, `claim-registry.json`, optional `kpi-table.json`, `insight-candidates.json`, and `requirement-claim-map.json` for insight work. Register the research brief and requirement map as separate immutable artifacts.

Do not replace a reviewed skill with an unreviewed ad-hoc script. If a format is unsupported, reselect an appropriate freshly reviewed pool skill or report the exact capability gap. Keep the output language inherited from the owner in all labels and notes.

Classify routine normalization as silent, reversible cleaning as notify, and meaning-changing source conflicts or KPI ambiguity as owner choice. Do not select the narrative or create slides.

## Use the shared skill pool

Keep ownership of the data contract, but reconsider the complete ready external pool for this exact input. Use `anthropic-sql-queries` to design schema-aware queries, `anthropic-statistical-analysis` for distributions/trends/outliers/tests, `anthropic-data-validation` as the independent QA method for every non-trivial analysis, `anthropic-data-visualization` only after claims are computed, and `anthropic-performance-analytics` only for marketing data. Use `anthropic-snowflake-semanticview` for an explicit Snowflake semantic-layer task after the owner-authority gate. These are instruction methods: SQL/Python/HTML execution requires a separately selected ready engine and execution receipt. A second or third skill is justified only by a distinct needed capability. Record candidates, selection rationale, review fingerprints, applied SKILL.md sections, exact entry points, outputs, and why each selected skill was needed or rejected.
