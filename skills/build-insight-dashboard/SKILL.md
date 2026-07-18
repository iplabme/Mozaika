---
name: build-insight-dashboard
description: >
  Act as the dedicated dashboard agent for Mozaika workflows: turn a validated
  data package into stable decision-focused visuals, a chart catalog,
  claim-to-chart evidence mapping, and two or three visual narrative previews
  when executive meaning is not fixed. Use after data analysis and before
  storyline selection. Do not clean raw data, silently choose the executive
  story, or render the final presentation.
version: 1.1.0
type: instruction
when_to_use: Use for the dashboard and visual-strategy stage of a configured reporting pipeline.
permissions: []
---

# Build Insight Dashboard

Accept one `mozaika-data-package/v1` handoff and return one `mozaika-dashboard-package/v1` result. Make evidence inspectable before narrative commitment. For insight work, refuse a handoff that omits the immutable `mozaika-research-brief/v1`, its SHA-256, or a passing `mozaika-requirement-claim-map/v1` gate.

## Produce the dashboard package

1. Validate the data package, solved scope ledger, claim registry, quality notes, KPI definitions, artifact index, anomaly log, research brief and requirement-to-claim map. Stop if the dashboard would imply broader coverage than the data stage achieved or if any frozen point disappeared.
2. Select only decision-relevant claims and map each to reproducible data evidence.
3. Choose stable visual encodings that preserve comparisons and uncertainty.
4. Read Mozaika's external-skill catalog, `mozaika/references/design-brandbook.md`, `mozaika/references/dashboard-quality.md`, and `mozaika/references/owner-domain-profile.md`. Load the matching owner-domain profile, inspect live readiness, compare all capable dashboard skills, and save `skill-selection.json`. Prefer a suitable installed Anthropic skill; choose another installed skill when it materially improves contract fit, visual quality, autonomy, or QA. Require real support for configurable charts, useful filterable/sortable tables and browser-tested filters; a renderer without those capabilities is incompatible when meaningful slices exist. Pass the immutable Mozaika brandbook manifest, tokens, dashboard/card references, exact source-of-truth instruction, and confirmed profile slices to the selected renderer. Produce a validated renderer input with Russian visible labels by default, KPI claim ids, inline chart data, caveats, sources, storytelling cards, and `surface_policy=separate-dashboard-and-storytelling-cards`.
5. Record every chart, metric, filter, source reference, and supported claim in `chart-catalog.json` and `claim-chart-map.json`.
6. For insight work, read `mozaika/references/storytelling-cards.md` and create two or at most three materially different storytelling cards. Render all options into one rich, self-contained `storytelling-cards.html` page. Each card must carry a concise headline, core message, executive relevance, three to five evidence-backed story beats, takeaway, visual direction, accessibility description, supporting claim ids, and a unique HTML anchor. Each option also carries `requirements_coverage` that maps every brief item required on `cards` exactly once to beats, claims, framing and planned screen intents; constraints use `applied_global`. Display the owner's exact research title as one shared study kicker, not as the option-specific headline. Text-only A/B/C options, JSON shown to the owner, image-only previews, recolored copies, repeated headline/core message, repeated beat title/message, or options with equivalent grouping principles do not satisfy this step.
7. Re-run the claim gate before publishing the dashboard and owner choice. Every repeated metric must resolve to the same claim id. Create `mozaika-narrative-integrity-audit/v1` for the cards and call the deterministic `narrative_integrity` gate; a schema-valid page with missing coverage or high-confidence copy repetition still fails.
8. Verify labels, units, dates, filters, totals, output language, and visual legibility on a rendered surface. Test every filter, reset, relevant pair of filters, table sort/filter, empty state and responsive viewport; require a level grid, stable panel sizing, no clipping/overlap/layout jumps and no console errors. Reconcile all filtered totals with the claim/data layer. If visual inspection is unavailable, mark it unavailable rather than passed.
9. Register dashboard source, rendered output, chart catalog, maps, the internal owner-choice JSON, `storytelling-cards.html`, its narrative-integrity audit and its browser-QA capture in the append-only artifact index; never overwrite or delete an earlier version. Register the dashboard only with schema `dashboard-html-without-storytelling-cards/v1`; reject it if narrative cards, their data, their question, or an embedded cards page appear anywhere in its DOM.
10. Save browser-verified `design-receipt.json` files for the dashboard and, when present, storytelling cards; validate them against `mozaika-design-receipt/v1` and register them in the artifact index.
11. Return artifact hashes and the structured result envelope with fresh selection, execution, and design receipts.

Required outputs are `dashboard-spec.json`, a standalone dashboard HTML containing no storytelling cards, a real-browser QA capture, `chart-catalog.json`, `claim-chart-map.json`, and, when owner choice is required, internal schema-valid `owner-choice.json`, its passing narrative-integrity audit, plus a physically separate owner-visible `storytelling-cards.html` and its browser-QA capture. Deliver both HTML files separately; keep JSON internal unless explicitly requested. Hiding cards inside the dashboard does not satisfy separation.

Before the parent asks the owner, it must persist a schema-valid `mozaika-owner-decision-checkpoint/v1` in `pending` state whose refs and hashes resolve to assignment, research brief, dashboard, internal choice and cards HTML. Returning the dashboard package alone is not permission to confirm that the question was delivered.

Do not treat visual style variants as different strategies. Do not select a meaning-changing grouping on the owner's behalf. Do not render the final presentation. Do not introduce uncomputed trends, causal claims, future predictions, or model properties into dashboard prose. Do not replace a reviewed skill with an unreviewed ad-hoc renderer.

The Mozaika brandbook overrides every built-in dashboard theme. If it is unavailable and the owner has not provided an explicit override, block rendering rather than silently producing a dark-red, gray, or default-themed artifact.

## Use the shared skill pool

Keep ownership of dashboard evidence and visual exploration, and follow Mozaika's `anthropic-skill-routing.md`. First read and evaluate `anthropic-interactive-dashboard-builder` and `anthropic-dashboard-architect`; use the suitable one unless a recorded incompatibility or quality proof requires another reviewed engine such as `antv-g2-dashboard`. A short Anthropic instruction is still a valid mandatory method candidate. Use `anthropic-data-validation` for non-trivial QA without silently changing upstream data. When strategies differ materially, emit two or three options conforming to `mozaika-owner-choice/v1` on a single owner-visible HTML surface. Never select `anthropic-pptx` or `presentation-skill`. Record candidates, selection rationale, review fingerprints, applied instruction sections, entries, and output artifacts.
