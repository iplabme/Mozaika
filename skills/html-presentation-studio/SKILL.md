---
name: html-presentation-studio
description: Build excellent HTML presentations with strong narrative, distinctive art direction, responsive layouts, source discipline, and automated quality gates. Use for pitch decks, keynotes, technical talks, teaching decks, reports, product demos, or redesigning an existing HTML deck.
version: 1.3.0
type: script
runtime: python3
os: any
requires: [python3]
permissions: [subprocess]
install:
  - kind: pip
    package: playwright
timeout_sec: 300
scripts:
  - name: scaffold.py
    description: Generate a responsive vanilla-HTML or reveal.js deck from a brief and outline.
  - name: audit.py
    description: Run dependency-free static quality checks.
  - name: browser_audit.py
    description: Run real-browser overflow and console checks using Playwright without opening a local server.
when_to_use: User asks to create, redesign, review, convert, or improve a presentation, deck, keynote, pitch, workshop, lecture, or slide-based story in HTML.
---

# HTML Presentation Studio

Create HTML decks that work **on stage**, scan clearly **at a glance**, and remain technically reliable. A deck is not a webpage divided into screens; it is a timed sequence of audience realizations and decisions.

## Default deliverables

- `presentation.html`
- `sources.md` with every material claim, quote, number, and external asset
- `audit-report.txt` or JSON
- optional `assets/` only when local media are needed

All generated files belong under the append-only Ouroboros skill state. Invoke
scripts through `skill_exec`, pass a campaign-specific `--job-id`, and use only
relative output names. The scripts return absolute artifact paths in JSON. They
refuse absolute output paths, directory escapes, and overwriting an existing
artifact. Inputs may be immutable absolute artifact paths from a Mozaika handoff.

Read before building:

1. `references/METHODOLOGY.md`
2. `references/DESIGN_SYSTEM.md`
3. `references/QUALITY_RUBRIC.md`
4. `references/FRAMEWORK_GUIDE.md`
5. `references/ACCESSIBILITY.md`

For a Mozaika run, also read the immutable runtime brandbook refs named in the
handoff under the canonical contract prefix `data/brandbook/mozaika/`. With
Ouroboros file tools, `root="runtime_data"` already resolves `data/`, so remove
that one leading prefix and read `brandbook/mozaika/...`; never request
`data/brandbook/mozaika/...` from that root. Preserve the full canonical path in
handoffs and design receipts. The brandbook, manifest, tokens, and
artifact-specific screenshot are mandatory and override built-in visual themes.

## Hard gates

A deck is unfinished while any item is false:

1. Audience, setting, requested action, and one-sentence takeaway are explicit.
2. Slide titles alone form a coherent abstract of the presentation.
3. Content-slide titles state conclusions rather than labels such as “Market” or “Results”.
4. Every slide fits one viewport without internal scrolling.
5. Body text remains readable at 1280×720 and projector distance.
6. No invented metrics, quotes, customers, logos, citations, screenshots, or evidence.
7. One intentional visual system is used; avoid generic AI-startup gradients and card walls.
8. Keyboard navigation, semantic structure, alt text, contrast, and reduced motion are supported.
9. `scripts/audit.py` has no HIGH findings.
10. Every slide is inspected in a browser; use `scripts/browser_audit.py` when Playwright is available.
11. Evidence-bearing charts, diagrams, schemes, or tables dominate the deck where the data supports them; prose and decorative card walls do not count as visual richness.
12. Page-to-page transitions are smooth, restrained, and consistent with the narrative; `prefers-reduced-motion` removes them without hiding or reordering content.
13. Audience-visible slides contain no internal ids, claim ids, option numbers, schema versions, hashes, filesystem paths, pipeline labels, review status, debug metadata, or other service information. Keep source links, dates, units, definitions, methodology, and useful caveats.
14. For Mozaika insight work, every rendered screen corresponds to a unique `slide_id` in the deterministic-gate-passed outline; no screen is invented, dropped, reordered, or detached from its frozen requirement and claim mapping.
15. The delivered HTML contains no network-loaded script, stylesheet, font, image, chart library or iframe. Inlined third-party runtime is allowed when reviewed and recorded; a remote URL dependency is a blocking failure.

## Workflow

### 1. Read the communication job

Infer safe details and ask at most one blocking question. Establish:

- audience and prior knowledge
- live talk, self-guided link, embedded page, or exported PDF
- desired decision/action
- one-sentence takeaway
- duration and target slide count
- ground-truth sources
- brand, confidentiality, offline, and asset constraints

Declare the design read in one sentence:

> Reading this as a 12-minute executive decision deck: evidence-first, restrained, and built around the conclusion that process latency—not headcount—is the bottleneck.

### 2. Build a source ledger

Create `sources.md` before slides:

| Claim or asset | Source | Confidence | Slide |
|---|---|---:|---:|
| Activation rose from 31% to 44% | analytics export, 2026-06-30 | confirmed | 6 |

Label assumptions and modeled estimates. Omit unverifiable claims or mark them visibly.

### 3. Write the narrative spine

Choose an arc:

- **Decision:** decision → stakes → evidence → options → recommendation → owner/action
- **Pitch:** change → pain → insight → mechanism → proof → business → ask
- **Technical:** problem → constraints → failed attempt → architecture → demo → trade-offs → lesson
- **Teaching:** question → mental model → example → misconception → practice → synthesis
- **Research:** question → method → result → interpretation → limits → implication

Write all slide titles first. If titles do not tell the story, the deck is not ready for design.

### 4. Choose a visual direction

Pick and adapt one direction from `DESIGN_SYSTEM.md`. Declare:

- typography pair
- background, surface, text, and accent tokens
- chart and image treatment
- motion behavior
- recurring compositional motif

Do not mix unrelated visual metaphors.

For Mozaika, do not choose among generic directions: implement the supplied
Mozaika brandbook. An explicit owner override must be recorded; renderer taste
is not an override.

### 5. Scaffold

Use `templates/outline.example.md`, then run:

```bash
python scripts/scaffold.py \
  --brief templates/brief.example.json \
  --outline templates/outline.example.md \
  --job-id campaign-stage-attempt \
  --output presentation.html \
  --engine vanilla \
  --theme mozaika-reference
```

For reveal.js (only when a remote CDN is explicitly acceptable):

```bash
python scripts/scaffold.py \
  --outline outline.md \
  --job-id campaign-stage-attempt \
  --output presentation.html \
  --engine reveal \
  --theme editorial
```

The vanilla engine is the default for Mozaika because it is self-contained.
The scaffold is only a starting point. Replace generic composition with
content-specific inline HTML/CSS/SVG charts, diagrams, screenshots, comparisons,
timelines, or demonstrations. Never claim `interactive_charts=true` merely because
navigation is interactive: every data-bearing visual must be genuinely rendered
from the validated values in the outline or linked evidence.

### 6. Compose slide by slide

Match visual form to reasoning:

- magnitude → large metric with baseline and period
- trend → chart with an annotated change
- process → directed flow
- alternatives → aligned comparison
- mechanism → labeled diagram or staged reveal
- product claim → real screenshot/demo state
- code → only the lines that support the spoken point

Avoid consecutive slides with identical layouts. Vary scale and rhythm while preserving the same design system.

### 7. Static QA

```bash
python scripts/audit.py /absolute/immutable/presentation.html \
  --job-id campaign-stage-attempt \
  --report audit-report.json \
  --require-mozaika-brandbook \
  --strict
```

Fix every HIGH issue and review every MEDIUM warning.

### 8. Browser QA

```bash
python scripts/browser_audit.py /absolute/immutable/presentation.html \
  --job-id campaign-stage-attempt \
  --screenshots-dir audit-screenshots \
  --report browser-audit.json \
  --capture-all
```

Test at least:

- 1920×1080
- 1280×720
- 768×1024
- 375×667
- 667×375

Inspect every slide for clipping, wrapping, contrast, missing assets, weak balance, and animation problems.

### 9. Presenter readiness

Confirm:

- Arrow keys, PageUp/PageDown, Home/End, wheel, and touch work
- O/button overview and F/button fullscreen work
- progress/slide number is correct
- useful speaker notes exist
- the last slide preserves the conclusion/action, not only “Questions?”
- print/PDF mode preserves backgrounds and one-page-per-slide
- external assets resolve from the intended host
- confidential/offline decks do not depend on remote resources

## Density defaults

| Slide type | Default maximum |
|---|---|
| Title | heading + subtitle + optional context line |
| Content | one assertion + 4–6 short bullets or two short paragraphs |
| Comparison | 2–4 aligned alternatives |
| Grid | 6 items, preferably 3–4 |
| Code | 8–12 visible lines |
| Quote | one short quote + attribution |
| Chart | one main chart + one takeaway annotation |
| Image | one hero image or purposeful before/after pair |

Never shrink type merely to force content onto one slide.

## Security

- Never execute JavaScript copied from an untrusted deck.
- Do not embed trackers, analytics, invisible pixels, or unknown scripts.
- Prefer local assets for confidential work.
- Record external libraries, fonts, images, and licenses.
- Never expose secrets in HTML, notes, URLs, or source maps.
- This skill must not modify its own files.
- Do not start a localhost server. Browser QA uses `file://` and an inline-content
  fallback so the executable skill does not require a network permission.
- Run browser QA only on a generated/staged HTML artifact inside this skill's
  state directory. The browser auditor refuses arbitrary paths plus `http(s)` and
  `file://` dependencies before launching Chromium.
- Never delete or overwrite prior job output. A revision uses a new `--job-id` or
  output name and remains traceable in the Mozaika artifact index.

## Mozaika presentation role

For the `presentation` stage this is the owner-designated first-choice renderer.
Consume a schema-valid and `presentation_outline`-gate-passed `presentation-outline/v1`, preserve its storyline, claim
IDs, language, caveats, and design constraints internally, and return one rich self-contained
HTML deck plus source ledger, static audit, browser audit, and QA captures. Use the
vanilla engine or a bespoke self-contained implementation based on this skill's
methodology. `anthropic-interactive-dashboard-builder` and
`anthropic-dashboard-architect` remain useful supporting/fallback capabilities for
complex data visuals, but they do not replace this renderer unless it is not ready
or cannot satisfy a specific input contract. Never use a PowerPoint renderer for a
Mozaika final presentation. Read the Mozaika runtime brandbook before composing,
pass its exact source-of-truth instruction to every supporting visual skill, use
`mozaika-reference` instead of `editorial` or `signal`, and return a browser-
verified `design-receipt.json` conforming to `mozaika-design-receipt/v1`.
The actual `<html>` element must contain
`data-mozaika-brandbook="mozaika-brandbook/v1"` and
`data-mozaika-theme="mozaika-reference"`; bespoke renderers must add the same
markers and the exact warm-canvas/ink/green core tokens. Run the static audit
with `--require-mozaika-brandbook`, then have the parent call Mozaika
`validate_gate(gate="brandbook_conformance", ...)` with the complete immutable
HTML and its SHA-256. Do not deliver or describe the deck as Mozaika when either
check fails.
For this role the receipt must additionally prove `diagram_rich=true`,
`smooth_page_transitions=true`, and `reduced_motion_fallback=true` after browser
inspection; navigation animation alone does not satisfy `diagram_rich`.
The deck must also pass `service_metadata_hidden=true`: use internal claim and
artifact ids for traceability, but never print them on audience-facing slides.
Return an immutable execution receipt bound to the exact outline SHA-256,
fresh skill-review fingerprint and produced artifact ids. Produce a passing
`mozaika-narrative-integrity-audit/v1` for the final presentation and verify that
every `slide_id`, requirement, claim and selected-story beat remains present.
Keep stable slide ids, visible slide titles, claim links, visual intent and a
natural outgoing transition available in the immutable outline/result metadata.
The later `speaker_cards` role uses this exact mapping to create one speaking cue
per final slide; this renderer must not generate those cards itself or collapse
multiple final slides behind one id.
An ad-hoc renderer, a changed outline, or a merely existing HTML file cannot be
reported as a solved Mozaika presentation.

## Completion report

Report:

- output path and engine
- visual direction
- slide count and intended duration
- source/assumption status
- static-audit score and browser-audit status
- external dependencies/offline limitations
- the single highest-leverage remaining improvement
- Mozaika brandbook manifest hash, reference ids, and design-receipt path when applicable
