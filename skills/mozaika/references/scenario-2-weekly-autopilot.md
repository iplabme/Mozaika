# Scenario 2: Weekly Autopilot

## Purpose

The second Mozaika widget runs a known reporting process on new data. It does not ask the owner to select a narrative strategy. Its stable route is:

`data → dashboard → anomaly_analysis → HTML presentation → editable PPTX`

Use the dashboard and HTML presentation templates declared in the runtime brandbook. The final editable deck is an additional format produced only after the HTML presentation is accepted.

## Fixed contract

- Scenario id: `weekly_autopilot`.
- Dashboard template: `data/brandbook/mozaika/templates/scenario-2-dashboard.template.html`.
- HTML presentation template: `data/brandbook/mozaika/templates/scenario-2-presentation.template.html`.
- PPTX outline example: `data/brandbook/mozaika/templates/scenario-2-presentation-skill-outline.example.json`.
- PPTX design reference: `data/brandbook/mozaika/references/scenario-2-sprint25-review-reference.pptx`.
- Full owner-approved design/process contract: `data/brandbook/mozaika/references/scenario-2-weekly-autopilot.md`.
- PPTX renderer: exactly `presentation-skill` with style preset `mozaika-weekly`; never `pptx` or `anthropic-pptx`.

When reading through `runtime_data`, strip the leading `data/`. Keep the full canonical path in contracts and receipts.

## Execution

1. Preserve and inventory every input. Copy local paths by streaming file operations; never load a large file into model context.
2. Validate schema, period completeness, types, duplicates, missing data, and comparison compatibility. Preserve raw and excluded records.
3. Recompute the fixed KPI contract and trace every material number to source and calculation.
4. Render the autonomous dashboard from the exact scenario template. Replace all placeholders and remove the template warning. Keep filters, searchable/sortable table, severity filtering, density control, section control, reset, responsive states, and offline operation.
5. After dashboard calculations, independently rank anomalies against own-history, target, and peer baselines. Every surfaced anomaly includes fact, baseline, deviation, confidence/caveat, and management consequence.
6. Render the autonomous HTML presentation from its exact template. Preserve the sequence context → KPI → trend → slice → main anomaly → complete table → actions. Replace all placeholders and remove the template warning.
7. Build a factual `presentation-skill` outline from accepted claims. Run `presentation-skill` with `--style-preset mozaika-weekly` as the last production stage. Register one owner-visible PPTX artifact and rendered-slide QA artifacts.
8. Reconcile dashboard, HTML and PPTX on KPI values, dates, entity names, anomaly severity and actions. A mismatch blocks `solved`.

## Intervention policy

Do not ask for approval for known formatting drift, reversible cleanup, source resolution covered by the manifest, or a normal template refresh. Notify once about material automatic cleanup. Pause only when a required source is missing, schema incompatibility changes meaning, conflicting metrics have no authority rule, or the fixed story would mislead.

## Acceptance

- No storytelling cards, owner-choice checkpoint, selected card, or speaker cards are produced in this scenario.
- No external scripts, fonts, images, iframes, or CDN dependencies remain in owner HTML.
- Dashboard and HTML pass language and wide/medium/narrow browser layout checks.
- PPTX execution receipt records `presentation-skill`, fresh review, `mozaika-weekly`, outline SHA-256, output id, and rendered-slide QA ids.
- All user inputs and stage artifacts remain immutable and recoverable.
