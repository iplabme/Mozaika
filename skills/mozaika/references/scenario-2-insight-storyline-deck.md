# Scenario 2: Insight Discovery → Strategy Choice → Storyline → Executive Deck

## Contents

- Purpose and owner experience
- Variable contract and skill composition
- End-to-end flow
- Acceptance criteria
- Demo/video plan

## Purpose

Turn exploratory data—such as Anthropic dialogue data—into an executive presentation where the central value is not slide production but choosing and constructing the right story. Preserve autonomy through analysis while reserving one high-value checkpoint for the owner to choose how the insights should be framed.

Before starting and before every role handoff, read `user-agenda-coverage.md` and reread the original immutable `assignment.md`. The owner's questions, slices, lists, named alternatives and requested order are the mandatory agenda. Complete them before adding autonomous findings; never let an attractive generic storyline replace them.

## Owner experience

The owner provides data and asks for a presentation for leadership with insights.

The agent should first analyze and prepare the evidence, then respond approximately like this:

> Я проверил данные, исключил 27 записей как вероятный технический шум и сохранил их отдельно. Остальные инсайты можно подать двумя сильными способами. Вариант A группирует их по этапам пользовательского пути и лучше отвечает на вопрос «где теряем качество». Вариант B группирует по типам поведения и сильнее показывает продуктовые возможности. Ниже два варианта дашборда/визуального превью. Я рекомендую A для операционного руководителя. Какой подход ближе?

The two examples at this checkpoint are dashboard/story previews, not two finished presentations. After the owner chooses, the agent builds the full storyline and only then the final rich HTML presentation.

## Variable contract

- Audience and decision to influence must be discovered or confirmed.
- Insight grouping is not predetermined.
- The governing thought and recommendation emerge from evidence.
- Several valid narrative strategies may exist.
- Visual exploration should help the owner understand the strategic difference before choosing.

## Skill composition

1. **Data intake and profiling** — preserve raw evidence and document quality.
2. **Exploratory analysis** — identify patterns, segments, anomalies, contradictions, and candidate insights.
3. **Dashboard exploration** — make the evidence inspectable and test alternative groupings.
4. **Narrative strategy generation** — produce two or three materially distinct ways to answer the executive question.
5. **Decision checkpoint** — show visual previews, trade-offs, and a recommendation; ask one bounded question.
6. **Storyline construction** — build the complete argument after the strategy is selected.
7. **Presentation rendering** — translate the storyline into slides and brand/template form.
8. **Speaker-card rendering** — derive one concise speaking cue from every final presentation slide.
9. **Editable PPTX rendering** — mirror the accepted HTML slide order and facts through `presentation-skill` with the insight visual grammar.
10. **Verification and delivery** — validate claims, evidence, narrative continuity, both rendered formats, and slide-to-cue coverage.

## End-to-end flow

### 1. Frame the executive decision

Infer from the request and available context: who will see the deck, what decision or understanding it should create, what constraints exist, and what would count as a useful insight. Immediately after `assignment.md`, extract every explicitly named question, slice, section, output title and global constraint into immutable `research-brief.json` conforming to `mozaika-research-brief/v1`. Preserve user wording with `unicode-nfc-lf-v1`, register the artifact and validate the `research_brief` gate before analysis. Never overwrite it; a correction creates a successor artifact. Load the matching `mozaika-owner-domain-profile/v1` and reuse confirmed KPI, periods, segments and past corrections only when the current subject area matches. Ask early only if the audience or decision is unknowable and materially changes the entire analysis. Record new evidence-backed preferences as a new profile version after feedback; do not claim model fine-tuning.

### 2. Prepare evidence autonomously

Create the scope ledger first. A collection URL or “all datasets” request requires enumeration and terminal disposition for every child source; a pilot may inform method choice but cannot satisfy full scope. Fingerprint and preserve raw data in the append-only artifact index. Profile schemas, missingness, duplication, sampling bias, representativeness, and sensitive fields. Clean only through explicit reversible transformations.

Likely noise may be excluded without prior approval when raw rows, rationale, counts, and sensitivity impact are preserved. Notify the owner at the strategy checkpoint.

### 3. Discover and challenge insights

Generate candidate insights from distributions, trends, segments, sequences, correlations, qualitative themes, and counterexamples. For every candidate, record evidence strength, business relevance, alternative explanation, claim kind, evidence artifact ids, and whether it changes a leadership decision. Validate all calculations and repeated metrics in the claim registry.

Discard technically interesting but decision-irrelevant findings. Keep contradictions visible instead of forcing a clean story.

Create `requirement-claim-map.json` after the claim registry. Every non-constraint requirement must appear exactly once with its original text, status, claims, evidence and available dimensions. A missing answer stays visible as `partial`, `unanswered` or `not_applicable` with a reason. Global constraints appear separately with `applied_global=true`. Validate this map before dashboard dispatch.

Preserve the order of the owner's list in the research brief and in every handoff coverage summary. Do not merge neighboring points unless the same visible evidence actually answers both and the resulting section names both. Treat a filter as an interaction, not as an answer: each requested slice also needs a visible result and interpretation.

### 4. Build an exploratory dashboard

Create a dashboard that exposes the strongest findings and lets the owner and agent test grouping principles. It is an analytical surface, not yet the presentation. Every chart must support a claim or discriminate between narrative strategies. Use beautiful level panels, configurable charts, useful filterable/sortable tables and explicit filters based on the available dimensions plus confirmed owner-profile slices. Test reset, empty states, responsive layouts, filtered totals and browser console according to `dashboard-quality.md`; do not accept visual glitches or static controls that only look interactive.

Freeze every explicitly requested research point from the assignment verbatim before analysis. The dashboard must show each point, its evidence-backed answer and its status; the presentation outline must map the same points to named screens. If the owner supplied a research title, preserve the exact string in the dashboard title, every option-card headline, the selected card, storyline and final presentation title.

### 5. Generate narrative strategies

Produce two or at most three genuinely different strategies. Examples include:

- journey/stage framing: where the experience succeeds or breaks;
- behavior/segment framing: which user or dialogue patterns create value or risk;
- problem → evidence → opportunity framing: what leadership should change;
- tension framing: expected behavior versus observed reality.

For each option provide the executive question answered, governing thought, grouping principle, likely slide sequence, strengths, risks, and the decision it encourages. Recommend one based on the stated audience.

If the owner explicitly supplied alternative framings, named report variants or a requested choice, build the cards from those alternatives first and preserve their wording. Do not replace them with the generic examples above. Every option must still show how all mandatory research points will be covered; differences between options concern framing and order, not whether an owner point survives.

### 6. Ask one bounded owner question

Show the already browser-verified HTML dashboard and the options page together, in that order. Build one dedicated self-contained `storytelling-cards.html` conforming to `mozaika-owner-choice/v1` and `references/storytelling-cards.md`. Render both the all-options page and the later selected-card page with the exact runtime Mozaika color tokens and `anthropic-transparency-hub-cards` composition; a dark, gray, burgundy, or renderer-default palette fails the design gate. Never append, hide or embed the cards page or its data in the dashboard: they are two physically separate owner surfaces. Give each option a stable HTML anchor so the owner can compare the headline, main thought, three to five story beats, supporting evidence, and executive implication visually rather than read labels or raw JSON. Use Russian for owner-visible text unless another language was explicitly requested. Validate scope and claims first, inspect both pages in a real browser and inspect dashboard DOM/source for forbidden card content, register the dashboard as `dashboard-html-without-storytelling-cards/v1`, register both as owner-visible artifacts, and actually expose both HTML files in the same owner response. Only then call `request_owner_choice` so the same options appear as clickable branded cards in `Mozaika · Инсайты` and the click returns to the current foreground task. If either page was not surfaced, stop and deliver it instead of publishing the widget question. Batch any remaining meaning-changing choices into this checkpoint.

Do not ask about chart colors, slide counts, routine cleaning, or technical implementation unless they alter meaning or require new authority.

Before asking, create an immutable pending `mozaika-owner-decision-checkpoint/v1`. Use its stable run/decision identity as the widget `question_id` and pass its artifact id and current SHA-256 to `request_owner_choice`. The tool result with `status=answered` identifies the selected option without a separate chat turn. Its recovery order remains fixed: an answered immutable live-choice record for the explicit question id; otherwise an explicit `run_id` from a later authenticated owner message; otherwise the single pending checkpoint for the same chat/session scope and scenario; otherwise one clarifying question. Zero or multiple candidates never trigger an inferred choice. The stale timestamp never silently discards the choice: require explicit reconfirmation, dismissal or a successor checkpoint. If the tool wait expires, repeat it with the same immutable request; if a completed task cannot be recovered, continue in a new task from durable refs. Never acknowledge delivery until the pending checkpoint and both surfaced HTML artifacts exist.

### 7. Build the storyline first

After selection, preserve the all-options page and create a new browser-verified `selected-storytelling-card.html` containing exactly the chosen card and its evidence references. Make this single-card HTML the authoritative strategy input; do not have the storyline agent reread all unselected alternatives. Then produce a standalone storyline containing:

- audience and desired decision;
- governing thought in one sentence;
- opening tension/context;
- ordered claims where each claim earns the next;
- evidence mapped to every claim;
- implications and recommended actions;
- section and slide intents;
- appendix boundary for supporting detail.

Review the storyline for gaps, unsupported jumps, repetition, contradictory claims, and executive relevance. Do not start slide production until it is coherent.

The owner answer creates a new selected checkpoint and an immutable selected-card artifact; a later changed choice creates a successor and marks the prior checkpoint superseded without rewriting history. Run `mozaika-narrative-integrity-audit/v1` on the selected card and storyline. It must prove exact requirement coverage, distinct text, valid claims and preservation of the selected story.

### 8. Build the deck from the storyline

Translate each storyline beat into one presentation screen with one message, a stable unique slide id, validated claim ids, supporting evidence, inherited output language, and the appropriate interactive or static visual. Validate `outline.json` against `presentation-outline/v1` and the deterministic `presentation_outline` gate. Insight admission requires `scenario=insight_deck`, `coverage_mode=frozen_requirements`, selected-checkpoint/card/storyline provenance, and exact requirement-to-slide mapping. Evaluate the owner-designated `html-presentation-studio` first and use it when ready and compatible, then create and visually inspect one self-contained rich HTML presentation. It must be rich in evidence-bearing charts, diagrams, schemes, and tables rather than prose or decorative card walls. Use smooth page-to-page transitions that support the story and provide a `prefers-reduced-motion` fallback with no loss of content. Anthropic HTML skills may support complex data visuals or serve as a recorded fallback. Require slide and keyboard navigation, fullscreen, overview, responsive layout, accessible semantics, reduced motion, print styles, and offline opening. Remote CDN/script/font/image dependencies are blocking; reviewed code inlined into the single HTML is allowed. Rendering may compress or split screens for legibility but must not silently change the argument.

Immediately before rendering, reread `assignment.md` rather than trusting the shortened storyline. Confirm that every user item maps to a visible slide and that owner-named sections and titles remain recognizable. Put additional discoveries after this mandatory coverage or in an appendix.

### 9. Build final speaker story cards from the finished deck

The single `selected-storytelling-card.html` remains an immutable strategy receipt and storyline input; it is not the final speaker aid. After the final presentation exists, create internal `speaker-story-cards.json` conforming to `mozaika-speaker-story-cards/v1` and a separate owner-visible `speaker-story-cards.html` using `brandbook/templates/speaker-story-cards.template.html` as the mandatory visual base.

Create exactly one cue card for every presentation slide, in the same order and with the same stable slide id and visible slide title. Each card must help the speaker explain that slide rather than copy its prose: include the slide purpose, one to four short speaking prompts, evidence cues linked to the slide's validated claims, the visual element to point at, a natural transition to the next slide, optional caveat or answer to an expected question, and indicative timing. Do not expose claim ids, hashes, schema versions, option numbers, or file paths in visible HTML. Preserve them only in the adjacent internal JSON.

Open the whole speaker-card deck in a real browser and check navigation, touch/keyboard behavior, print mode, narrow viewport, overflow, palette, repeated wording, and exact slide coverage. Run current-hash narrative-integrity, business-language, design, and visual-layout audits, then validate `speaker_story_cards` against the final outline, presentation, claim registry, artifact index, selected checkpoint, and brandbook template hash.

Run `brandbook_conformance` on the actual immutable HTML bytes of the all-options cards, selected card, presentation and final speaker-card deck before any `send_file`. A continuation task after the owner's choice remains inside Mozaika: it must recover the campaign contracts and use `html-presentation-studio` plus the speaker-card template rather than generating owner artifacts with an ad-hoc Python script. Pass all four successful current-hash gate results into completion.

### 10. Build the final editable PPTX

After the HTML presentation and its speaker-card deck have passed their gates,
create a separate factual outline that mirrors the accepted HTML slide order,
titles, claims, numbers, caveats and sources. Invoke exactly `presentation-skill`
with `--style-preset mozaika-insight`. Use
`brandbook/templates/scenario-insight-presentation-skill-outline.example.json`
as the renderer-input pattern and
`brandbook/references/scenario-insight-presentation-style.md` as the visual
source of truth.

The owner-provided DS-role PPTX contributes only colors, elements, spacing and
placement rules. Do not copy its sample content, slide count, slide order or
specific sequence of layouts. Choose each PowerPoint composition from the
current storyline and evidence. Keep charts and tables native and editable,
render every produced slide, reject overlaps/clipping and preserve a fresh
execution receipt with the exact reference hash and `reference_usage` set to
`visual-grammar-only`. Never substitute `pptx` or `anthropic-pptx`.

### 11. Verify and deliver

Return the standalone storyline, final HTML presentation, final `speaker-story-cards.html`, and editable PPTX. Preserve every input and declared stage artifact without deletion or overwrite. Before each owner-facing surface is accepted, run the business-language validator on free headings and body text while protecting owner-supplied titles and prompt points verbatim; use `pass by default`, reject only certain critical failures and return minimal meaning-preserving rewrites. Do not report or reject merely weak style. Run visual QA after the accepted wording. Verify data lineage, claim-evidence mapping, dashboard/deck consistency, caveats, recommendation support, output language, visual hierarchy, rendered slide quality, exact presentation-slide-to-speaker-card coverage, and cross-format equality of shared claims. Run current-hash narrative-integrity audits on the final HTML presentation and speaker cards and preserve renderer receipts tied to the exact HTML and PPTX outlines and output hashes. Then run the completion gate; insight `solved` additionally requires the fresh `presentation-skill` PPTX receipt with `mozaika-insight`, the owner-reference hash and rendered-slide QA. When language audit, visual QA or requested scope is incomplete, return `best_effort` rather than `solved`.

## Acceptance criteria

- The owner intervenes at one meaningful strategy checkpoint, not at every stage.
- Strategy options differ in executive meaning, not merely visual style.
- Preview artifacts at the checkpoint are dashboard/story views, not prematurely finished decks.
- The selected storyline exists independently before slide production.
- Every explicit owner list item, requested slice, named alternative and requested section remains traceable in its original order and is visible on every required output surface.
- Proactive findings supplement the owner's agenda and never replace it.
- Every major deck claim maps to reproducible evidence and acknowledged caveats.
- Every requested collection member is represented in the validated scope ledger.
- Reversible cleaning is disclosed and recoverable.
- Every owner-choice option is present at a unique anchor in the delivered, browser-verified `storytelling-cards.html` artifact; internal JSON is not substituted for it.
- The checkpoint response visibly delivers both the owner-visible HTML dashboard and `storytelling-cards.html` before asking for a choice.
- The dashboard contains no storytelling cards or card data in visible, hidden, embedded, collapsed, iframe, template, script, or JSON form; all options exist only in the separate cards HTML.
- After the choice, `selected-storytelling-card.html` contains only the selected option and is the only choice surface read by the storyline agent; the original alternatives remain preserved.
- The final HTML presentation follows the selected strategy without narrative drift.
- The final HTML presentation is rich in evidence-bearing diagrams and uses smooth page transitions with a verified reduced-motion fallback.
- `speaker-story-cards.html` contains exactly one concise speaking cue for every final slide, in presentation order, and uses the mandatory Mozaika speaker-card template.
- The final speaker cards explain how to speak through the deck; they do not duplicate the strategy-choice page or merely copy slide text.
- The final editable PPTX is generated last through `presentation-skill`, follows the accepted HTML sequence and facts, uses `mozaika-insight`, and derives only visual grammar from the owner reference.
- The PPTX reference never dictates the new deck's number, order, topics or concrete slide structures.
- All user inputs and stage outputs remain in the append-only artifact index.
- The delivered result includes data-quality notes, dashboard, storyline, HTML presentation, final speaker story cards, and editable PPTX.

## Demo/video plan

1. Show a short request plus an unfamiliar dialogue dataset.
2. Condense autonomous cleaning, exploration, and insight discovery.
3. Show the proactive message about removed noise and two visual strategy previews.
4. Show the owner selecting one strategy in a single response.
5. Reveal the generated storyline before showing the slides.
6. Show the finished deck and trace one claim back to dashboard and data.
7. Optionally contrast a cheap-model tuning run with the final expensive-model run, keeping the same artifacts and evaluation criteria.

This demonstrates classification of decision importance, proactive analysis, controlled autonomy, storyline-first construction, skill orchestration, and result quality.
