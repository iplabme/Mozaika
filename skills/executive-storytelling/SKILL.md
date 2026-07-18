---
name: executive-storytelling
description: >
  Build a decision-ready executive narrative before slides: governing thought,
  context and tension, ordered evidence, the Three Things status model, metric
  hierarchy, bad-news framing, caveats, asks, and slide intents. Use for board,
  jury, top-management, QBR, investor, and leadership communication after the
  evidence and narrative strategy are fixed, and use again after the final
  presentation to derive concise speaker cue cards for every slide.
version: 1.2.0
type: instruction
when_to_use: Use inside Mozaika's storyline role after strategy selection and inside its speaker-card role after the final HTML presentation is accepted.
permissions: []
license: MIT adaptation; see ATTRIBUTION.md
---

# Executive Storytelling

Build the argument first. Slide geometry comes later.

## Inputs that must already exist

- audience, desired decision, and delivery context;
- selected storytelling card with three to five ordered beats;
- selected durable owner-decision checkpoint and the immutable single-card HTML it references;
- frozen research brief and requirement-to-claim map;
- solved scope ledger and validated claim registry;
- dashboard package, claim-to-chart map, caveats, and counterevidence;
- output language and constraints.

If the selected story cannot be supported, stop with the exact evidence gap.
Do not quietly switch to a more convenient story.

## Narrative architecture

1. **Promise to the audience.** State what the audience will understand or be
   able to decide by the end.
2. **Governing thought.** Write one complete sentence that combines the main
   evidence and its consequence. It must be no stronger than the claims.
3. **Context.** Establish only the baseline facts needed to interpret the
   change, comparison, or decision.
4. **Tension.** Name the meaningful gap, change, risk, opportunity, or
   contradiction. Avoid artificial drama.
5. **Ordered proof.** Each section answers one executive question and earns the
   next section. Evidence precedes implication; implication precedes action.
6. **Decision or action.** End with a bounded recommendation, owner, timing,
   and decision needed. If evidence supports no action, say what should be
   monitored instead.

## The Three Things status model

For a status, board, or recurring report, force the core story to answer:

1. What is working, and what evidence proves it?
2. What is not working or remains uncertain, and how material is it?
3. What are we doing next, and what decision or support is required?

Do not spread these answers across unrelated slides. A leader should be able to
repeat all three after one reading.

## Four-tier metric hierarchy

Use metrics according to their decision role:

1. **Outcome:** the business or mission result.
2. **Driver:** the few variables that explain movement in the outcome.
3. **Operating:** process health and execution signals.
4. **Diagnostic:** detail needed to investigate, usually appendix material.

Lead with outcomes and drivers. Keep operating and diagnostic metrics out of
the main story unless they change the decision.

## Evidence discipline

- Every assertion carries validated `claim_ids` and source artifact ids.
- Separate observation, calculation, inference, hypothesis, and
  recommendation in visible language.
- Preserve counterevidence and methodological limitations near the claim they
  qualify, not in a hidden final footnote.
- For bad news, use: fact → impact → cause confidence → action → owner → timing
  → residual risk. Do not bury the fact or overstate knowledge of the cause.
- For actual-versus-plan, show the same period, definition, unit, and scope.
- Never manufacture a trend from two incomparable points or imply causality
  from correlation.

## Slide-intent rules

Each intended slide has exactly one message and these fields:

- stable unique `slide_id`;
- frozen `requirement_id` values answered by this slide;
- executive question answered;
- message headline written as a conclusion;
- purpose in the argument;
- claim ids and evidence artifacts;
- appropriate visual or table;
- caveat/counterevidence;
- transition to the next beat.

The title alone should tell the story when all slide titles are read in order.
Move detail that does not advance the argument to an appendix.

## Review before handoff

Read only the sequence of headlines. Then read only governing thought, caveats,
and asks. Reject the storyline if you find an unsupported jump, duplicated
message, contradictory number, hidden limitation, ambiguous decision, or slide
that exists merely because data was available.

Return `storyline.md`, `evidence-map.json`, `slide-intents.json`, a passing
`mozaika-narrative-integrity-audit/v1`, and a schema-valid, deterministic-gate-passed
`presentation-outline/v1`. For insight work use `scenario=insight_deck`,
`coverage_mode=frozen_requirements`, a single provenance block and exact
requirement-to-slide mapping. All owner-visible material is Russian
unless another language was explicitly requested. These are new append-only
artifacts; never overwrite the selected card or upstream evidence.

## Build the final speaker-card deck

After the presentation passes its deterministic outline gate and browser QA, reuse this methodology to create `speaker-story-cards.json` and the owner-visible `speaker-story-cards.html` from the accepted outline and presentation.

- Preserve the exact slide order and create exactly one cue card for every `slide_id`.
- Treat the selected single strategy card as provenance, not as the final speaker deliverable.
- Give each slide a purpose, one to four short spoken prompts, evidence cues tied to that slide's validated claims, a visual reading cue, a transition, an optional caution or answer-if-asked, and realistic timing.
- Write prompts as natural speech that connects evidence to implication. Do not duplicate the slide, narrate every label, invent a fact, expose service metadata, or create a teleprompter paragraph.
- Render with `data/brandbook/mozaika/templates/speaker-story-cards.template.html`; do not replace its Mozaika tokens with a built-in theme.
- Validate against `mozaika-speaker-story-cards/v1`, then call `validate_gate(gate="speaker_story_cards", ...)` with the accepted outline, claim registry and current artifact index.
- Run narrative-integrity, critical-only language, design and visual-layout audits on all cards and navigation states before delivery.

Deliver the final presentation and speaker-card HTML together. Keep the internal JSON for traceability and never substitute the single selected-strategy card for this per-slide deck.
