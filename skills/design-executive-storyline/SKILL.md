---
name: design-executive-storyline
description: >
  Act as the dedicated storyline agent for Mozaika executive-deck workflows:
  transform a validated dashboard package and selected narrative strategy into
  a governing thought, ordered evidence-backed argument, caveat map, slide
  intents, and presentation-ready outline.json. Use after dashboard exploration
  and owner strategy selection, before any presentation rendering. Do not alter
  analytical evidence or build the final HTML presentation.
version: 1.2.0
type: instruction
when_to_use: Use for storyline-first executive communication after the narrative strategy is fixed.
permissions: []
---

# Design Executive Storyline

Accept one `mozaika-dashboard-package/v1` handoff plus the selected strategy and return one `mozaika-storyline-package/v1` result. Build the story before slides. The only valid strategy input is a browser-verified immutable `selected-storytelling-card.html` referenced by a schema-valid `mozaika-owner-decision-checkpoint/v1` in `selected` state. Never infer a choice from a bare number, a stale task message, or the all-options page.

## Produce the storyline package

1. Validate the selected checkpoint and all artifact hashes, then confirm the audience, desired decision, complete selected storytelling card, frozen research brief, requirement-to-claim map, output language, solved scope, validated claim registry, constraints, strongest evidence, and immutable Mozaika brandbook refs. Reject a selection that lacks its three to five story beats, references claims outside the validated option, is stale without explicit owner reconfirmation, or does not preserve every required card item.
2. Read Mozaika's external-skill catalog, inspect live readiness, evaluate matching `anthropic-*` support first, and save `skill-selection.json`. The installed Anthropic bundle has no dedicated executive-storyline method, so use an appropriate reviewed narrative skill while applying `anthropic-data-validation` to evidence integrity when needed. Preserve candidate decisions, applied instructions, payload fingerprints, and resulting storyline artifacts in receipts.
3. State one governing thought that the evidence can support.
4. Establish the opening context or tension.
5. Order claims so each claim earns the next and culminates in implications or action. For status work, explicitly answer what works, what does not, and what happens next; lead with outcome and driver metrics rather than diagnostic detail.
6. Map evidence, caveats, counterevidence, source artifacts, and claim ids to every major claim. Label inference, hypothesis, and recommendation visibly; never promote them to observed fact.
7. Separate the core executive story from appendix detail.
8. Define one message and purpose for each intended slide, assign a stable unique `slide_id`, then attach the relevant brandbook pattern and reference id without turning the storyline stage into visual rendering. Add concise speaker intent to each slide: the natural opening line, visual reading cue, transition, caveat and expected timing that a later speaker-card role can use without copying the slide. Map every research-brief requirement required on `storyline` or `presentation` to target slide ids and claims; constraints use `applied_global`.
9. Review for unsupported jumps, repetition, contradiction, weak relevance, narrative drift, uncomputed trends, causal overreach, speculative forecasts, hidden bad news, ambiguous asks, and rank/value mismatches.
10. Re-run the claim gate. Every content slide must reference validated claim ids and inherit the run's output language.
11. Produce a passing `mozaika-narrative-integrity-audit/v1` for `storyline.md`. It must prove exact frozen-scope coverage, no exact/high-confidence repetitions, valid claim links, preservation of the selected story and valid slide mapping.
12. Select the owner-designated `html-presentation-studio` when it is ready and compatible, otherwise record the precise fallback reason, then produce `outline.json` that validates against `presentation-outline/v1`: set `scenario=insight_deck`, `coverage_mode=frozen_requirements`, complete the single `provenance` block, assign every slide a unique `slide_id`, map every presentation requirement with exact verbatim text to existing `slide_ids` and claim ids, set `output_format=html`, `delivery_mode=self-contained-single-file`, and include the brandbook and HTML requirements. Do not render it in this role.
13. Call `validate_gate(gate="presentation_outline", ...)` with the outline, brief, claims, selected checkpoint, artifact index and passing storyline audit. A schema-valid outline is not renderable until this deterministic gate passes.
14. Register storyline, evidence map, slide intents, audit and outline as new immutable artifacts; never delete or overwrite upstream or prior-version artifacts.
15. Return `storyline.md`, `evidence-map.json`, `slide-intents.json`, `outline.json`, the narrative-integrity audit, gate receipt, hashes, and the structured result envelope with fresh selection and methodology receipts. Make the per-slide intent sufficient for the post-presentation role to build one evidence-linked speaker cue card per slide, but do not render those cards here.

Do not change data values, hide caveats, substitute a new strategy, translate into a different language, optimize slide aesthetics, or use an ad-hoc Python script as a substitute for narrative reasoning. Escalate only if the selected strategy cannot be supported by the evidence.

## Use the shared skill pool

Keep ownership of the argument and slide intent while reconsidering the complete ready external pool. Supporting skills may validate evidence, strengthen executive narrative, or test HTML feasibility, but must not rewrite the selected strategy or evidence. `anthropic-pptx` and `presentation-skill` are forbidden for Mozaika. Record candidates, why the winner best fits this story, payload fingerprints, applied method, and output artifacts.
