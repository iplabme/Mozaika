# Scenario 1: Recurring Data → Dashboard → Template Deck

## Purpose

Turn a repetitive evening reporting process built from many Excel files or dashboard exports into a reliable autonomous run. Maximize unattended execution because the audience, KPIs, storyline pattern, template, and delivery cadence are already agreed.

## Owner experience

The owner provides the source files or points to the recurring source and says, for example: "Refresh tonight's management report."

The agent should return a finished dashboard snapshot and presentation, plus a concise operational note such as:

> Отчёт обновлён по данным на 12 июля. Исключил 14 строк с дублирующимися идентификаторами и сохранил их в журнале качества. KPI и структура презентации не менялись. Два показателя вышли за обычный диапазон — отметил их на слайдах 4 и 7.

No approval checkpoint should appear during a normal run.

## Stable contract

- Audience: known management group.
- KPI definitions: versioned and fixed for the reporting cycle.
- Storyline: a versioned fixed narrative contract compiled by the orchestrator LLM; the template renders that contract but is not its only source of truth.
- Visual and brand rules: fetched from the current approved source.
- Delivery cadence and cutoff: known.
- Baseline: previous accepted run plus configured comparison periods.

If any of these contracts is missing on the first run, establish it once and persist it for subsequent runs.

## Skill composition

1. **Source intake** — locate files/exports, verify cutoff time and expected partitions.
2. **Spreadsheet/data preparation** — profile schemas, normalize types, join sources, calculate KPIs, preserve lineage.
3. **Quality and anomaly analysis** — detect missing partitions, duplicates, impossible values, likely outliers, and deviations from baseline.
4. **Dashboard rendering** — refresh agreed views and annotate material deviations.
5. **Template-story validation** — confirm the fixed storyline still matches the evidence and no section has become misleading.
6. **HTML presentation rendering** — populate the approved template without rewriting the narrative contract.
7. **Editable PPTX rendering** — after HTML acceptance, invoke exactly `presentation-skill` as the final production stage; never use `pptx` or `anthropic-pptx`.
8. **Verification and delivery** — reopen outputs, render all PPTX slides, reconcile numbers across data/dashboard/HTML/PPTX, and record the run.

The first implementation should live in `skills/build-routine-report/` and orchestrate existing spreadsheet, visualization, presentation, and brand/template capabilities rather than reimplement them.

## End-to-end flow

### 1. Recover the run contract

Load the prior accepted run, KPI dictionary, source manifest, dashboard specification, template, brand source, delivery target, and known exception rules. Report a blocker only when a required source or contract cannot be recovered.

### 2. Ingest without destroying evidence

Enumerate the complete expected scope. Copy inputs into durable run-scoped artifacts, fingerprint them, and keep raw data immutable under the append-only artifact policy. Never delete or overwrite a user input or declared stage output. Record file names, timestamps, row counts, schemas, and extraction cutoff.

### 3. Profile and normalize

Normalize headers, types, time zones, identifiers, and categorical values. Join only through declared keys. Produce a quality report before calculating executive metrics.

### 4. Classify deviations

- Act silently on known formatting and source-location drift.
- Act and notify on reversible cleaning such as duplicates or strongly supported outlier exclusions; preserve excluded rows and the rule used.
- Pause only when data are incomplete enough to change conclusions, a KPI definition changed, sources conflict without a dominant authority, or the fixed storyline would become materially misleading.

### 5. Refresh the dashboard

Recompute the agreed views, compare current values with prior period, target, and expected range, and surface only decision-relevant deviations. Keep chart encodings stable across runs unless the template contract changed.

### 6. Compile and validate the fixed storyline

Carry `fixed_storyline_contract_version` in the run handoff. Ask the orchestrator LLM to compile current evidence into the fixed narrative schema: context, performance, drivers, exceptions, actions, and appendix—or the organization's chosen equivalent. Self-check section presence/order, evidence coverage, caveats, dashboard reconciliation, and recommendation drift. If the evidence fits, continue automatically. If it contradicts the governing message, stop once with evidence and propose a bounded template/story adjustment.

### 7. Build and verify the deck

Populate slides from the validated claim registry and verified dashboard outputs. Check totals, labels, dates, units, period comparisons, chart-data equality, output language, overflow, legibility, and template compliance. Render and inspect the actual presentation, not only its source objects.

### 8. Build the final editable PPTX

Create a factual presentation-skill outline from the accepted fixed-template claims. Invoke the installed, enabled, freshly reviewed `presentation-skill` with `--style-preset mozaika-weekly`. Register the result as a new immutable owner-visible PPTX artifact, preserve the outline and execution receipt, render every slide, and reject overlaps, clipping, illegible labels, missing charts/tables, or numeric drift. This is an additional editable format; it does not replace or weaken HTML acceptance.

### 9. Deliver and learn

Before visual QA, run the independent business-language validator on the dashboard and final presentation. Protect owner-supplied titles and prompt points verbatim; check free headings and body text separately; use `pass by default` and reject only certain critical failures, never merely weak style. Require a minimal meaning-preserving rewrite for each critical failure. Run the completion gate. Return the deck, dashboard artifact, quality/anomaly log, append-only artifact index, rendered QA evidence, and a short notification of material automatic interventions in the inherited output language. Require the dashboard quality checks for level configurable charts, filterable tables, functional filters, reset, responsive layout, empty states and a clean browser console. After acceptance, store reusable rules under an `mozaika-routine-*` knowledge key conforming to `mozaika-routine-learning/v1`. Update the matching `mozaika-owner-domain-*` profile only from explicit feedback, accepted choices or corrections, as a new evidence-backed version. Reuse only when source, schema and subject-area assumptions still match, so the next run becomes quieter without accumulating silent drift.

Before analysis, freeze every explicitly requested research point from the assignment as verbatim required scope. Show the status and evidence-backed result for each point in the dashboard and map each one to named presentation screens. If the owner supplied a research title, preserve it exactly in dashboard and presentation titles.

## Acceptance criteria

- Every executive number is traceable to source rows and a KPI definition.
- Raw inputs and excluded records remain recoverable.
- Every expected source has a terminal entry in the validated scope ledger.
- Every repeated KPI resolves to the same validated claim id.
- Dashboard, HTML and PPTX values agree exactly for shared metrics.
- The approved template and brand source are current.
- The agent makes no normal-run approval request.
- Material automatic cleaning is disclosed once in the final note.
- Meaning-changing ambiguity blocks with evidence and no fabricated completion.
- HTML and every rendered PPTX slide are suitable for delivery without manual repair.
- Completion status matches the deterministic completion gate.

## Demo/video plan

1. Show a folder with many routine Excel inputs and one short owner request.
2. Show autonomous profiling, duplicate/outlier handling, and dashboard refresh as condensed progress.
3. Show the agent notifying—not asking—about reversible cleaning.
4. Show the finished rich HTML presentation, the final editable PPTX produced by `presentation-skill`, and a number traced back through both formats to dashboard and source.
5. Show a second run becoming shorter because the accepted contract and lessons persist.

This demonstrates routine autonomy, controlled intervention, repeatability, and learning. Do not stage a fake approval dialog in the normal path.
