# Configurable Agent and Handoff Contracts

## Contents

- Pool model
- Transport modes
- Common request and result envelopes
- A2A wire mapping
- Role contracts
- Rich HTML presentation contract
- Pipeline gates

## Pool model

Maintain five logical production roles: `data`, `dashboard`, `storyline`, `presentation`, and `speaker_cards`, plus independent visual and business-language validators. Each has a stable `agent_id`, role boundary, capability contract, and artifact contract. A skill name is selected anew for every stage and is never part of role identity.

Keep live configuration in the Ouroboros project workpad under `mozaika-pool/v1`, derived once from `config/agent-pool.example.json`. Validate it against `contracts/agent-pool.schema.json` before work. Do not accept file overrides next to a task and never store passwords, tokens, or API keys in the workpad value.

Every role is bound to `adaptive-full`, which exposes the complete ready external pool described in `external-skill-catalog.md` plus discoverable fallback candidates. Before each stage, filter by contract and readiness and preserve `mozaika-skill-selection/v1`. Consider suitable installed Anthropic skills first for data, dashboard, and storyline; evaluate owner-designated `html-presentation-studio` first for presentation. Skills are selected need-by-need, never all invoked automatically. Role ownership comes from the typed contract; using a supporting skill does not transfer responsibility or relax it. Do not substitute an unreviewed one-off implementation for a selected reviewed skill.

## Transport modes

- `local_task_skill`: run a bounded Ouroboros task-agent that selects the best ready skill for its current capability contract and may select a second skill only for a distinct supporting capability.

The current contract deliberately permits only local task agents. A2A remains disabled with an empty allowlist until a real peer exists and a URL/redirect guard is reviewed. The presentation task-agent owns rich HTML generation and browser QA; `html-presentation-studio` is its owner-designated first-choice renderer, with runtime readiness and contract compatibility still checked on every run.

## Common request and result envelopes

Use `contracts/handoff-envelope.schema.json` for local and A2A handoffs alike.

Every request identifies:

- contract version, run, stage, role, stable agent id, and creation time;
- one bounded objective;
- immutable input artifact references;
- constraints and decision policy;
- named expected outputs;
- only the context needed for this stage.

For every insight-stage request, include the immutable original `assignment.md`, frozen research brief, current requirement map and the instruction to read `user-agenda-coverage.md`. The receiving agent rereads the assignment at both stage boundaries. A shortened handoff summary never replaces owner text. Begin the internal result with an ordered agenda-coverage summary naming where every owner item appears in the output or why it remains partial/unanswered.

Every result identifies:

- honest status: `solved`, `best_effort`, or `blocked_with_evidence`;
- stable agent id plus start/completion timestamps and duration;
- immutable output artifact references;
- verification evidence;
- interventions classified as silent, notify, or owner choice;
- warnings and unresolved questions;
- optional stage metrics.
- a fresh selection receipt and reviewed execution receipts naming the skill,
  payload hash, exact entry or applied method, output artifact ids, and execution mode.

An artifact reference contains an id, accessible durable URI, SHA-256, media type, schema, creation time, source task/stage, and append-only preservation contract. Never delete or overwrite an artifact behind a hash-bearing reference. Cross-task continuations use these refs rather than paths into another task drive.

The intervention `tag` and `class` must match the typed mapping in the pool contract. These schemas are orchestration contracts checked by the parent task; they are not native Ouroboros runtime enforcement.

## Deferred A2A wire mapping

Do not execute this mapping in the current version. It records the intended future integration only. When the guard and a peer are approved, serialize the complete request envelope as JSON in one A2A text part. Keep it self-contained because the current Ouroboros bridge allocates a new internal chat for every inbound request.

After `ext_3_a2a_send`:

1. Parse the outer JSON-RPC response.
2. Inspect the returned task state.
3. If terminal, extract the artifact text part and parse it as the result envelope.
4. If a peer returns a non-terminal task, poll `ext_3_a2a_status` within the parent-owned deadline.
5. Validate run id, stage id, role, schema, status, artifact accessibility, and hashes before continuing.

Use `run_id + stage_id` as the semantic idempotency key even though the bridge generates a new protocol message id. Never rely on A2A `contextId` for conversational continuity. Never embed a secret, large dataset, dashboard binary, or PPTX in the text part.

## Data role

Input contract: `mozaika-handoff/request-v1`.

Insight input additionally requires immutable `mozaika-research-brief/v1`. The data role validates it before analysis and never rewrites or silently narrows its requirements.

For widget launches, the request also carries `mozaika-input-sources/v2`. Preserve array order and source kind. A `url` remains pending until the data agent validates reachability, enumerates collection children, and snapshots fetched evidence. A `file` points to one immutable stored artifact. A `directory` is one owner-selected source whose `files` retain their relative paths; inventory every child before analysis. Do not flatten a directory or URL into an ambiguous filename list.

Required responsibilities:

- inventory and fingerprint sources;
- preserve raw inputs;
- profile schemas and data quality;
- apply reversible normalization and cleaning;
- calculate declared KPIs when definitions exist;
- identify candidate insights and counterevidence;
- record excluded rows and sensitivity impact.
- select and record the best ready inventory and analysis capabilities for the
  actual sources, preferring a suitable installed Anthropic skill.
- analyze owner-requested questions and slices first, in original order; additional insights follow them and cannot replace them.

Required `mozaika-data-package/v1` outputs:

- `scope-ledger.json` conforming to `mozaika-scope-ledger/v1`;
- `source-manifest.json`;
- append-only raw-source artifact references;
- clean analysis dataset reference;
- `data-profile.json`;
- `anomaly-log.json`;
- optional `kpi-table.json`;
- `claim-registry.json` conforming to `mozaika-claim-registry/v1`;
- `insight-candidates.json`.
- `requirement-claim-map.json` conforming to `mozaika-requirement-claim-map/v1` for insight work, with exact data-requirement and global-constraint coverage.

The data role must not choose the executive narrative, design the dashboard, or create slides.
Missing format support triggers reselection or a named capability gap, not an
unreviewed ad-hoc pipeline.

## Dashboard role

Input contract: `mozaika-data-package/v1`.

Insight input must include the research brief, requirement-to-claim map and their passing deterministic gate receipts.

Required responsibilities:

- map candidate claims to visual evidence;
- choose stable chart encodings;
- build an inspectable dashboard or dashboard specification;
- surface caveats and contradictions;
- for insight work, create two or three materially different narrative previews.
- choose a reviewed HTML visualization capability and preserve a real-browser QA surface.
- reread the assignment and give every owner-requested point a visible result, interpretation and evidence-bearing dashboard location; a filter alone is not coverage.
- when the owner named narrative alternatives, use those alternatives as the strategy-card basis instead of inventing substitutes.
- bind every visible data control to complete source rows or reproducible aggregate slices and named targets; never offer values that exist only as labels.
- prove that the selected value participates in the filtering/recomputation path and that KPI, chart, table, insight, signal and caveat targets update from one consistent filtered state.
- remove or visibly disable unavailable controls instead of shipping decorative filters, selectors, switches, tabs, legends or drill-downs.

Required `mozaika-dashboard-package/v1` outputs:

- dashboard source/specification;
- rendered dashboard reference;
- `chart-catalog.json`;
- `claim-chart-map.json`;
- `filter-data-coverage.json` mapping every data-bound control and option to backing data, targets and aggregation;
- `interaction-qa.json` recording tested options/combinations, input-slice signatures, semantic target signatures and reset evidence;
- internal `owner-choice.json` when owner choice is required, plus owner-visible HTML dashboard and `storytelling-cards.html` surfaced before the question, and `selected-storytelling-card.html` containing only the selected option before storyline dispatch;
- one owner-visible self-contained `storytelling-cards.html` containing every option at a stable anchor;
- a real-browser QA capture of that HTML choice surface.
- passing narrative-integrity audit for the cards and all immutable inputs needed for the parent to create a pending owner-decision checkpoint.

The dashboard role may propose grouping strategies but must not silently select a meaning-changing storyline.
It must not bypass the reviewed selection lifecycle with one-off generated HTML.
The owner receives the HTML choice surface, not the internal JSON payload.

## Storyline role

Input contract: `mozaika-dashboard-package/v1` plus a validated selected owner-decision checkpoint and the immutable single selected-card HTML for insight work.

Required responsibilities:

- define audience and desired decision;
- preserve `research_title_verbatim` unchanged when supplied and carry every verbatim requested research question into a coverage map;
- write the governing thought;
- order claims so each earns the next;
- map evidence and caveats to every claim;
- define section and slide intents;
- produce a presentation-ready outline only after the narrative is coherent.
- select and preserve the strongest ready narrative method for this audience,
  with a receipt tied to the storyline artifacts.
- preserve the owner's ordered agenda, or document an evidence-based reordering while keeping every item visible; never optimize a point away for narrative neatness.

Required `mozaika-storyline-package/v1` outputs:

- `storyline.md`;
- `evidence-map.json`;
- `slide-intents.json`;
- `outline.json` conforming to `presentation-outline/v1`.
- `mozaika-narrative-integrity-audit/v1` for storyline and a passing `presentation_outline` gate receipt.

The outline title must contain `research_title_verbatim` exactly when it is not
null. `research_questions_coverage` must list every requested question verbatim
and name the presentation screen titles that answer it; use `partial` or
`unanswered` instead of silently dropping a question.

Every major storyline statement resolves to a validated claim id. Interpretations, hypotheses, and recommendations remain visibly qualified. The package inherits the run output language.

The storyline role must not render the presentation or change raw analytical evidence.

## Presentation role

Stable contract:

- agent id: `mozaika-presentation-agent`;
- transport: `local_task_skill`;
- input: schema-valid `outline.json` with the approved storyline;
- skill: owner-designated `html-presentation-studio` when ready and compatible, otherwise a recorded fallback from the ready external pool;
- output: one rich self-contained `.html` presentation;
- forbidden HTML renderers: `anthropic-pptx`, `presentation-skill`.

Before invocation, read the catalog and live skill state, then create a fresh
selection receipt. Evaluate `html-presentation-studio` first. The installed
`anthropic-interactive-dashboard-builder` and `anthropic-dashboard-architect`
remain supporting/fallback candidates for complex visuals or a recorded
incompatibility. Validate `outline.json`, require `output_format=html` and
`delivery_mode=self-contained-single-file`, and verify that the chosen skill can
produce a sequence of presentation screens rather than merely a scrolling
dashboard. The presentation role may compress or split a screen for legibility,
but may not alter the governing thought, claim order, KPI values, caveats, or
evidence mapping.

Before rendering, reread the original assignment and check every owner item against a visible screen. The accepted outline is not permission to omit a requirement accidentally lost upstream. Additional insights go after mandatory agenda coverage or into an appendix.

## Final editable PPTX role

Stable contract:

- agent id: `mozaika-pptx-agent`;
- scenarios: `routine_report`, `weekly_autopilot`, and `insight_deck`;
- input: accepted HTML presentation package plus the same validated claims;
- skill: exactly `presentation-skill`, with fresh review; use `mozaika-weekly`
  for routine/weekly and `mozaika-insight` for insight;
- forbidden renderers: `pptx`, `anthropic-pptx`;
- output: one immutable owner-visible editable `.pptx`, one immutable outline,
  an execution receipt, and rendered-slide QA artifacts;
- order: last production stage, after HTML acceptance; in insight work, after
  the final speaker-card deck;
- acceptance: shared claims, labels, periods and actions agree with dashboard and
  HTML, and every rendered slide is free of overlap, clipping and unreadable text.
  Insight additionally requires the exact owner-reference hash and
  `reference_usage=visual-grammar-only`; its sample structure is never copied.

The request handoff must also carry the immutable Mozaika brandbook manifest,
tokens, relevant artifact reference, and exact source-of-truth instruction from
`design-brandbook.md`. This design authority is independent of renderer
selection and overrides built-in themes. The result must include a schema-valid
`mozaika-design-receipt/v1`; a missing or inaccessible brandbook blocks visual
generation unless the owner supplied a recorded per-run override.

For insight PPTX, reread the original assignment and preserve the same user-agenda coverage as the accepted HTML. Do not treat HTML-to-PPTX conversion as permission to shorten away requested slices, sections or named outputs.

Required `mozaika-presentation-package/v1` outputs:

- source `outline.json` reference;
- one autonomous HTML reference with scripts, styles, data, fonts/icons or safe
  fallbacks packaged for offline opening;
- slide navigation plus keyboard, fullscreen, overview, responsive and print modes;
- interactive charts with accessible descriptions and usable static fallbacks;
- semantic headings, focus states, contrast, reduced-motion behavior and no
  critical interaction that depends only on hover;
- real-browser QA captures at desktop and compact viewport sizes;
- QA evidence covering navigation, placeholders, clipping, readability,
  interaction, output language, accessibility, and value consistency.

The role must visually inspect the actual browser rendering. File existence,
HTML parsing, or a screenshot of only the first screen is not sufficient. The
HTML capability does not replace storyline work.

## Speaker-cards role

Stable contract:

- agent id: `mozaika-speaker-cards-agent`;
- transport: `local_task_skill` with the adaptive pool;
- input: the final immutable `mozaika-presentation-package/v1`, passing outline receipt, claim registry, selected checkpoint/card, and Mozaika brandbook template;
- output: internal `speaker-story-cards.json` conforming to `mozaika-speaker-story-cards/v1` plus one owner-visible self-contained `speaker-story-cards.html`.

This role runs only after the final presentation has passed its own checks. It must create exactly one cue card per final slide, preserve slide order, ids and titles, and derive each cue from the slide's purpose, validated claims, visual and transition. A cue card contains one to four short spoken prompts, evidence to mention, what to point at, the transition to the next slide, optional caution or anticipated answer, and timing. It must not copy entire slide prose or expose machine metadata.

When a slide answers an explicit owner item, its speaker cue names that question or slice in audience language and explains the answer. Do not reduce such a card to a generic transition line.

Use `brandbook/templates/speaker-story-cards.template.html` as the mandatory visual and interaction base. The selected strategy card is provenance only and must not be republished as the final speaker deck. Validate the package with `speaker_story_cards`, then run independent narrative-integrity, business-language, design and visual-layout audits against current hashes. Return both final HTML artifacts—the presentation and the speaker-card deck—to the owner.

## Visual validator role

Stable contract:

- agent id: `mozaika-visual-validator-agent`;
- transport: `local_task_skill` with the adaptive pool;
- invocation: after dashboard rendering, final presentation rendering, and final speaker-card rendering;
- input: immutable HTML artifact plus renderer receipt, brandbook refs and expected interactive states;
- output: `mozaika-visual-layout-audit/v1` and three or more screenshot artifacts.

The validator is independent of the producing role. Read
`visual-layout-validation.md`, choose the strongest ready browser/layout-audit
skill available for that invocation, and inspect the real HTML at wide, medium
and narrow viewports. Check every presentation screen and required dashboard
interaction. For dashboards, inspect the payload and event path as well as the rendered DOM: enumerate all data-bound controls, verify backing data for every option, prove the selected value reaches target computation, and compare filtered input and semantic output signatures. A control that changes only its label/style or redraws one fixed slice is a blocking failure even when it has an event handler and no console error. Measure unintended overlaps, chart bounds, peer spacing outliers,
declared center offsets and page overflow after rendering and transitions. A
failed audit is a typed handoff back to the producer; only a new immutable
revision may be rechecked.

## Business-language validator role

Stable contract:

- agent id: `mozaika-business-language-validator-agent`;
- transport: `local_task_skill` with the adaptive pool;
- invocation: after each owner-facing dashboard, storytelling-cards page,
  selected card, final presentation and final speaker-card deck, before visual layout validation;
- input: immutable artifact, original assignment/prompt, claim registry and the
  complete list of user-supplied titles and prompt points;
- output: `mozaika-business-language-audit/v1`.

The validator is independent of the producing role. Read
`business-language-rules.md`; first extract protected verbatim strings, then run
separate passes over free headings and body text. Do not flag protected owner
wording, official names or direct quotes for style. Use `pass by default` and
reject only a certain critical failure class defined by the rules. Weak
headings, bureaucracy, passive voice, repetition, length, jargon and ordinary
tone roughness must pass without findings. Provide one minimal ready rewrite that
does not alter facts, numbers, qualifiers or evidence. A `revise` result returns
to the producer and creates a new immutable revision. After a language `pass`,
run the visual validator again on the accepted wording. The versioned Mozaika
rule file is the baseline method and is sufficient for the role; evaluate the
adaptive pool for a stronger ready editorial skill, but do not block merely
because no separate language skill is installed and never let a supporting
skill lower the critical-only threshold or weaken protected-text rules.

## Pipeline gates

Enforce these gates in the parent orchestrator:

1. **Pool readiness:** every selected role skill/method is freshly reviewed, enabled, dependency-ready, compatible, and accompanied by a selection receipt.
2. **Scope gate:** all requested collection members are inventoried and analyzed, or scope reduction is owner-approved and explicit.
3. **Artifact gate:** every user input and stage output has an immutable durable append-only reference; deletion is disabled.
4. **Data/claim gate:** lineage, quality report, reversible cleaning evidence, and arithmetic-valid claims exist.
5. **Dashboard gate:** every major visual maps to a validated claim and source evidence; every data-bound control has complete backing data and verified targets, all options and a two-filter combination are exercised, and no decorative or label-only interactivity remains.
6. **Owner-choice gate:** insight strategy is explicitly selected from two or three rendered visual previews when alternatives change executive meaning.
7. **Storyline gate:** governing thought, ordered claim ids, evidence map, language, and screen intents are coherent before presentation rendering.
8. **Presentation gate:** outline matches the approved storyline and the rich HTML passes interaction, responsive, accessibility, visual, language, and numeric QA.
9. **Speaker-card gate:** exactly one evidence-linked cue exists per final slide, uses the mandatory template and matches current outline/presentation hashes.
10. **Business-language gate:** protected owner text is unchanged; free headings and body text have separate passing audits, with only certain critical failures eligible to block and uncertainty resolved as `pass`.
11. **Completion gate:** runtime outcome axes, verification ledger, scope, claims, artifacts, visual QA, required brandbook design receipts, required business-language audits, and unresolved requirements support the requested outcome label.
12. **Engine gate:** every role result contains contract-valid fresh selection and execution receipts and no unreviewed ad-hoc implementation.
13. **Delivery gate:** all preserved user and final artifacts plus intervention notices are returned together, including the presentation and its speaker-card deck.
14. **Narrative-integrity gate:** frozen owner requirements are covered exactly, card/story/slide text is structurally distinct, claim links resolve, and the selected story is preserved at current artifact hashes.
15. **Durable-decision gate:** the owner question has a pending checkpoint and storyline has a selected checkpoint; failed steering or a bare option number never substitutes for persisted state.

For the routine pipeline, the approved template supplies the stable storyline contract; skip the separate storyline agent unless evidence invalidates that contract. For the insight pipeline, the storyline role is mandatory.
