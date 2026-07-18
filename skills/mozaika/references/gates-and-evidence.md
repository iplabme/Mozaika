# Scope, claim, visual, and completion gates

## Contents

- Scope gate
- Claim gate
- Frozen research and requirement map gates
- Dashboard interaction-integrity gate
- Owner-choice visual gate
- Presentation and visual QA gate
- Completion gate
- Output language

## Scope gate

Create `mozaika-scope-ledger/v1` before analysis. A collection URL or a request such as “all datasets” means `requested_mode=all`. Enumerate every child source and preserve the enumeration as an artifact.

Each source ends as `analyzed`, `owner_excluded`, or `blocked`. An owner exclusion requires a decision id and reason. Recompute coverage with `validate_gate(gate="scope", ...)`. Do not describe a pilot subset as analysis of the full collection. `solved` coverage requires all sources analyzed, or terminal coverage with no blockers and an owner-approved scope change.

## Claim gate

Maintain one `mozaika-claim-registry/v1`. Classify every owner-facing claim as:

- `observed`: directly present in source evidence;
- `calculated`: derived with explicit arithmetic checks;
- `inference`: interpretation supported but not directly measured;
- `hypothesis`: plausible explanation requiring further evidence;
- `recommendation`: proposed action grounded in named claims.

Every claim carries evidence artifact ids. Mark quantitative and entity-sensitive claims explicitly. Quantitative claims carry machine-checkable operations and tolerances; entity-sensitive claims carry text equality checks for model/product/category labels. Interpretive claims carry a visible qualifier. Call `validate_gate(gate="claims", ...)` before dashboard publication, owner choice, storyline approval, HTML presentation rendering, and completion.

Never claim an uncomputed trend, causal effect, confidence probability, future outcome, architecture property, rank, percentage, or total. A metric shown in two places must point to the same claim id. Correct the registry upstream; do not patch only the slide text.

## Frozen research and requirement map gates

For every insight run, validate `mozaika-research-brief/v1` immediately after assignment intake. Preserve named research titles, questions, slices, requested sections and constraints verbatim under `unicode-nfc-lf-v1`; internal ids never replace visible wording. Validate `mozaika-requirement-claim-map/v1` after claims are computed. It must cover every data-required item exactly once and resolve every claim/evidence id; constraints are checked separately as `applied_global`.

Run `mozaika-narrative-integrity-audit/v1` independently on storytelling cards, selected card, storyline, final presentation, and final speaker-card deck. It blocks only structural meaning failures: missing frozen points, invalid claim/screen links, narrative drift, slide-to-cue mismatch, or exact/high-confidence repetition. It does not replace the deliberately permissive business-language audit or the visual-layout audit.

## Dashboard interaction-integrity gate

Before a dashboard is accepted or used by anomaly, storyline, presentation, or owner-choice stages, require complete `filter-data-coverage.json`, `interaction-qa.json`, dashboard design receipt and independent visual-layout audit. Every visible data-bound control must enumerate all offered options, backing data ref/key, aggregation and target ids. Test every option, a combination of two filters, empty state and reset; preserve input-slice and semantic target signatures.

Fail the gate when an option lacks data, the selected value is not consumed by the computation, targets remain bound to one fixed slice, only labels/styles change, targets update inconsistently, or a control is presented as analytical while it only changes layout. An event listener, `render()` call, screenshot, clean console or self-authored `filters_functional=true` is insufficient. If the source cannot support the control, remove or visibly disable it and state the limitation; never manufacture interactivity.

## Owner-choice visual gate

Insight work requires two or three materially different strategies conforming to `mozaika-owner-choice/v1`. The payload must declare `owner_surface_format=html`; every option includes claim ids, the shared HTML artifact id, and its own unique HTML anchor. A text label, JSON attachment, Markdown table, raster-only preview, or prose answer is not the owner surface.

Create one self-contained `storytelling-cards.html` that visibly demonstrates each grouping principle, governing thought, representative evidence, and consequence. It must be a separate file, never a dashboard section, hidden block, tab, iframe, template, or embedded payload. Validate the scope and claim gates before showing it. Open both the dashboard HTML and cards HTML in a real browser; inspect dashboard DOM/source to prove card texts, `storytelling_cards`, owner question, recommendation and card containers are absent. Preserve both QA captures, register the dashboard as `dashboard-html-without-storytelling-cards/v1`, register both owner-visible artifacts, and expose both to the owner in the same response before calling `request_owner_choice` with their current artifact ids/hashes and the pending-checkpoint ref. A widget question without the two surfaced HTML artifacts fails the checkpoint. Keep the schema-valid `owner-choice.json` internal unless the owner asks for it.

Call `validate_gate(gate="owner_choice", ...)` with the choice payload, claim registry, and artifact index. Do not publish the checkpoint unless every referenced claim exists, `dashboard_surface_artifact_id` resolves to a durable owner-visible HTML dashboard, and the owner-surface id resolves to a durable, owner-visible `text/html` artifact with schema `owner-choice-cards-html/v1`. After the owner chooses, create the immutable single-option `selected-storytelling-card.html`; block storyline until that artifact has been browser-checked and registered.

Persist and validate a pending `mozaika-owner-decision-checkpoint/v1` before the question. Validate a selected checkpoint before storyline dispatch. Only a selected checkpoint whose hashes resolve to the single-card artifact is continuation evidence; a task id, a bare option number, or an optimistic steering acknowledgement is not.

## Presentation and visual QA gate

Every content slide in `presentation-outline/v1` carries claim ids and inherits `output_language`. The presentation agent may change layout for legibility but cannot change claim values, rankings, caveats, or narrative order.

Routine and weekly-autopilot outlines use `coverage_mode=fixed_template` and an immutable template hash; weekly autopilot additionally follows the scenario-2 dashboard and presentation templates from the runtime brandbook. Insight outlines use `scenario=insight_deck`, `coverage_mode=frozen_requirements`, a provenance block, unique slide ids and exact requirement-to-slide mapping. Call `validate_gate(gate="presentation_outline", ...)` before renderer dispatch; legacy v1 outlines remain readable but are not eligible as new run output.

The intake gate also freezes explicitly requested research points and an optional
owner-supplied research title. Dashboard and presentation gates fail when any
verbatim point is absent from their coverage map. When a title was supplied,
dashboard, all storytelling-card headlines, selected card, storyline and final
presentation title must contain that exact string; editorial framing may be
added but the named research may not be rewritten.

Render the dashboard and deck on an available real surface. Preserve screenshots, page images, or contact sheets as QA artifacts. Inspect placeholders, clipping, overlaps, readability, chart/table consistency, language, and shared numeric claims. If a visual model or renderer is unavailable, mark visual QA `unavailable`; file existence and slide count are not visual verification.

## Final speaker-card gate

After each owner-facing card page and the final presentation become immutable, call `validate_gate(gate="brandbook_conformance", ...)` with the complete HTML source, current artifact id, current SHA-256 and artifact index. The gate reads the actual bytes and rejects missing brandbook markers, missing core tokens, forbidden dark/burgundy renderer colors and a stale speaker-card template. Self-authored design receipts do not replace this gate.

After the final presentation is immutable, create `speaker-story-cards.json` and the separate owner-visible `speaker-story-cards.html`. Validate `speaker-story-cards.json` against `mozaika-speaker-story-cards/v1`, then call `validate_gate(gate="speaker_story_cards", ...)` with the current outline, presentation, complete speaker-card HTML source, selected checkpoint/card, research brief, claim registry, artifact index, and exact current brandbook template SHA-256.

The gate requires exactly one cue card per final slide in the same order, with matching slide ids, types and titles. Content-slide evidence cues resolve only to claims already admitted on that slide. Visible prompts must be concise, distinct and useful to a speaker: what to say, what evidence to mention, what visual to point at, how to transition, and any essential caution. The selected strategy card is provenance, not a substitute for this deck.

The final HTML must derive from `brandbook/templates/speaker-story-cards.template.html`, remain self-contained, hide machine metadata, and pass browser checks for all cards, keyboard/touch navigation, print, responsive layout, reduced motion and overflow. Require current-hash design, business-language, visual-layout and narrative-integrity audits before completion.

## Completion gate

Call `validate_gate(gate="completion", ...)` immediately before the final outcome. `solved` requires:

- solved scope coverage;
- valid claims;
- a valid append-only artifact index containing all required artifacts;
- execution status `ok`;
- objective status `passed` or `satisfied`;
- review `passed` or explicitly `not_required`;
- no verification failures;
- required visual QA passed;
- passing current-hash `brandbook_conformance` gate results for the presentation and, in insight work, the all-options cards, selected card and speaker-card deck;
- passing `mozaika-business-language-audit/v1` for dashboard and presentation,
  plus storytelling cards, selected card and final speaker cards in the insight scenario;
- every owner-supplied title and explicit prompt point recorded as protected
  verbatim and found unchanged;
- no unresolved requirements.
- for every scenario, a fresh passing `pptx_execution_receipt` from exactly
  `presentation-skill`, one owner-visible editable PPTX artifact and one or more
  rendered-slide QA artifacts; require `mozaika-weekly` plus the weekly reference
  profile for routine/weekly, or `mozaika-insight` plus
  `reference_usage=visual-grammar-only` and the owner-reference hash for insight;
- for insight work, a frozen brief, requirement-to-claim map, selected checkpoint, current-hash narrative audits for cards/selected card/storyline/presentation/speaker cards, a passing outline receipt, a fresh HTML renderer receipt, a passing speaker-card receipt tied to current outline, presentation, HTML and template hashes, and the final PPTX receipt.

Otherwise return `best_effort` or `blocked_with_evidence` exactly as recommended by the gate. Never write “полностью проверено” when runtime outcome axes or the verification ledger disagree.

## Output language

Set `output_language` from the owner's request. Use it consistently for progress, dashboard labels, strategy previews, storyline, deck, run note, warnings, and final delivery. Preserve technical identifiers verbatim. Ask about language only when the audience requirement conflicts with the owner's language and materially changes the deliverable.
