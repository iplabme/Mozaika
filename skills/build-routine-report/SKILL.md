---
name: build-routine-report
description: Autonomously refresh a recurring management report from stable spreadsheet or dashboard sources through data validation, reversible cleaning, KPI calculation, dashboard refresh, fixed-storyline validation, and rich HTML presentation generation from an approved visual system. Use for nightly, weekly, or monthly reporting where audience, metrics, structure, and brand rules are already agreed. Notify about material cleaning, but ask only when evidence invalidates the reporting contract.
version: 1.0.0
type: instruction
when_to_use: Use for repeatable data-to-dashboard-to-HTML-presentation reporting runs with a stable narrative and minimal owner intervention.
permissions: []
---

# Build Routine Report

Produce the complete recurring report without approval at each step. Load the configurable agent pool, run the `routine_report` role sequence, and treat the accepted prior run, KPI dictionary, dashboard specification, storyline template, brand source, and delivery cutoff as a versioned run contract.

## Run the workflow

1. Recover the run contract, previous accepted output, and the runtime Mozaika brandbook. Its manifest, tokens, and artifact-specific references are the design source of truth unless this run has an explicit owner override.
2. Stage and fingerprint all inputs while preserving raw data unchanged in an append-only artifact index. Never delete or overwrite user inputs or declared stage outputs.
3. Validate expected files, partitions, schemas, join keys, row counts, dates, units, and KPI definitions.
4. Create and validate the scope ledger, then dispatch the configured `data` role with a complete handoff envelope and durable immutable artifact refs.
5. Detect duplicates, impossible values, likely outliers, missing data, and material baseline deviations.
6. Dispatch the configured `dashboard` role with the validated data package plus immutable brandbook refs and the exact instruction that the brandbook overrides renderer defaults.
7. Ask the orchestrator LLM to compile the current evidence into the fixed storyline contract named by `fixed_storyline_contract_version`; do not infer the storyline from slide geometry alone.
8. Run the deterministic claim gate and a storyline self-check: every fixed section is present, section order is unchanged, every claim id is evidence-backed, caveats are preserved, values reconcile with the dashboard, and no new recommendation was introduced. If the evidence no longer fits, emit one owner-choice checkpoint instead of forcing the template.
9. Build an `outline.json` that validates against `presentation-outline/v1` and invoke `mozaika-presentation-agent` with the same immutable brandbook refs. Evaluate the owner-designated `html-presentation-studio` first and use it when it is ready and contract-compatible; fully read its instruction and references. Use suitable Anthropic capabilities only as visual support or as a recorded fallback. The result must be one self-contained HTML presentation with slide, keyboard, fullscreen and overview navigation, responsive interactive visuals, accessibility, reduced motion, print styles, and browser QA. Never use `anthropic-pptx` or `presentation-skill`.
10. Render and inspect the actual dashboard and HTML presentation in a browser; reconcile shared metrics exactly. File existence, byte size, or screen count alone is not visual QA.
11. Preserve dashboard, outline, HTML presentation, QA captures, run note, selection receipts, verification receipts, and schema-valid design receipts as new immutable artifacts.
12. Run the completion gate and deliver artifacts plus one concise run note and verification evidence in the inherited output language.
13. After owner acceptance, write only durable reusable rules to an `mozaika-routine-*` knowledge key under `mozaika-routine-learning/v1`; revalidate source and schema assumptions before later reuse.

## Control owner intervention

- Act silently on routine reversible mechanics such as formatting normalization, known source paths, and fetching the current approved brand book.
- Act and notify when excluding duplicates or strongly supported noise. Preserve excluded rows, rule, count, and sensitivity impact.
- Pause once with evidence only when a required source is missing, KPI meaning changed, sources conflict without an authority rule, or the fixed storyline would misrepresent the data.

Do not ask about ordinary chart choices, file handling, or known cleaning rules. Do not conceal a meaning-changing deviation to preserve automation.

## Preserve handoff contracts

Require each stage to save a fresh `mozaika-skill-selection/v1` decision after inspecting the complete ready external pool. Prefer installed Anthropic skills when they fit, but bind only the typed input/output contract, not a skill name. Require every routine handoff after contract recovery to carry `fixed_storyline_contract_version`. Require the presentation stage to consume a schema-valid `presentation-outline/v1` and return `mozaika-presentation-package/v1` as rich self-contained HTML without changing the fixed storyline. Every result carries fresh selection and execution receipts.

If a required specialist capability is unavailable, report the missing capability and continue any evidence preparation that remains useful. Do not invent an unreviewed substitute that weakens the result.

Do not create an unreviewed task-local implementation to bypass an unavailable role engine. Reselect a reviewed skill or report the precise capability gap.

## Verify completion

Confirm that:

- every executive number is traceable to source and KPI definition;
- raw and excluded records remain recoverable;
- data, dashboard, and HTML-presentation values agree;
- dates, units, labels, and comparison periods are correct;
- the current approved template and brand source were used;
- dashboard and presentation each have a passing `mozaika-design-receipt/v1` tied to the current manifest hash;
- rendered artifacts have no clipping, overlap, unreadable charts, or empty placeholders;
- material automatic interventions appear once in the run note.

Return `solved` only when the actual rendered artifacts pass these checks.
