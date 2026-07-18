---
name: antv-g2-dashboard
description: >
  Build a self-contained executive HTML dashboard from a typed JSON
  specification with AntV G2, inlined data and inlined runtime. Produces KPI
  tiles, decision-focused charts, filterable and sortable evidence tables,
  shared data filters, owner view customization, evidence references, and anomaly notes
  without Python or a web server. For insight work, renders storytelling cards
  only into a physically separate HTML file and guarantees that the dashboard
  cannot contain them.
version: 1.1.0
type: script
runtime: node
scripts:
  - name: build_dashboard.js
    description: Render a mozaika-dashboard-spec/v1 JSON file into an append-only standalone HTML dashboard and, for insight work, a separate storytelling-cards HTML page.
permissions: [fs]
install:
  - kind: npm
    package: "@antv/g2"
    expected_version: "5.4.8"
when_to_use: Use as the executable visualization engine for the Mozaika dashboard role after data claims have been validated.
timeout_sec: 180
license: MIT adaptations; see ATTRIBUTION.md
---

# AntV G2 Dashboard

The dashboard role chooses claims, visual encodings, and narrative alternatives.
This skill deterministically renders the approved specification.

```bash
node scripts/build_dashboard.js \
  --spec /absolute/job/dashboard-spec.json \
  --output jobs/run-001/output/dashboard.html \
  --cards-output jobs/run-001/output/storytelling-cards.html
```

The spec uses `mozaika-dashboard-spec/v1`, declares
`surface_policy=separate-dashboard-and-storytelling-cards`, and contains:

- Russian `title`, `subtitle`, and visible labels by default;
- `kpis` with `label`, `value`, optional `delta`, `status`, and `claim_ids`;
- `research_title_verbatim` and `research_questions`: preserve every explicitly
  named research point from the owner task and show its evidence-backed result;
- at least one `filter` whose field exists in a chart or table dataset;
- `charts` with stable `id`, decision-focused `title`, inline `data`, G2
  `type` (`interval`, `line`, `point`, `area`, or `pie`), and `encode`;
- at least one `table` with searchable rows, sortable typed columns, safe
  horizontal overflow, page size, empty state, and claim mapping;
- `customization` with section visibility, comfortable/compact density and a
  complete reset. These controls must change the rendered data or view; decorative controls are forbidden;
- `insights` and caveats;
- two or three `storytelling_cards` whose beats and claim ids match
  `mozaika-owner-choice/v1`;
- an option-specific `requirements_coverage` map for every explicitly requested
  research point. Legacy v1 specs without the map remain renderable, but the
  renderer exposes every `research_question` on every card so no point can
  disappear silently;
- `owner_question` and `recommended_option_id` whenever storytelling cards are present.

When `storytelling_cards` are present, `--cards-output` is mandatory. The renderer strips card data, owner question, recommendation, card DOM, and card scripts from `--output`; it writes them only to `--cards-output`. It refuses to save a dashboard containing known card markers. Register the dashboard with schema `dashboard-html-without-storytelling-cards/v1` and the separate cards page as a durable owner-visible `owner_choice_preview` with media type `text/html` and schema `owner-choice-cards-html/v1`. Inspect both in a real browser before requesting a choice.

The cards renderer uses the exact light Mozaika brandbook tokens (`#FAF9F5`,
`#141413`, `#5E5D59`, `#F0EEE6`, `#388F76`, `#59B295`) and open editorial
columns from `anthropic-transparency-hub-cards`. It rejects its former dark
green theme. Preserve the same palette when creating the later standalone
`selected-storytelling-card.html`; that derived artifact needs its own browser
QA and `selected_storytelling_card` design receipt.

Keep a story beat title short and make its message add evidence, meaning, or a
consequence. The renderer rejects exact and high-confidence near duplicates in
`headline/core_message`, `title/message`, adjacent beats, and adjacent option
headlines. It renders the title and message as separate elements and shows the
research title as a shared study kicker rather than repeating it inside the
narrative headline. Do not weaken or bypass this deterministic content check.

On each option show a compact, keyboard-accessible «Как вариант раскроет ваш
запрос» section. List the owner's research points verbatim with status and
option-specific framing; keep claim ids and requirement ids internal.

Keep service metadata out of both rendered pages. Claim ids, option ids,
renderer ids, contract versions, hashes, paths, and choice numbers remain in the
internal spec and evidence registry but are stripped from owner-visible HTML.
Show source links and useful dates, units, definitions, or caveats. The owner
chooses a storyline by its meaningful headline, not by an option code or number.

Never append cards below charts, hide them with CSS, place them in a collapsed dashboard section, or link them as an embedded iframe. Separation means two autonomous files: `dashboard.html` contains only analytical evidence; `storytelling-cards.html` contains only the narrative-choice surface.

The renderer derives filter values from chart and table rows, applies each
filter to every compatible dataset, rerenders charts, supports per-table search
and sorting, and lets the owner hide or show analytical sections and change data
density. KPI values intentionally stay fixed and the UI says so, preventing a
filter from silently changing their meaning. Use another reviewed renderer only
when the task requires capabilities beyond this contract, such as editing chart
definitions or saving personalized layouts across sessions.

If the incoming assignment names research questions, reproduce every question
verbatim in `research_questions` and include its supported result in the
dashboard. If the assignment supplies a research title, set
`research_title_verbatim`, include it unchanged in the dashboard title and in
every storytelling-card headline. The renderer rejects a spec that loses or
rewrites that title. The presentation outline must carry the same exact title
and a coverage map for all questions.

The spec must be a durable file under the Ouroboros data root. The output path
is confined to this skill's state directory and is create-only. The result
embeds the reviewed G2 runtime. The role must
still open the result on a real browser surface, inspect labels, clipping,
legibility, and numerical consistency, then register the screenshot or capture
as a separate QA artifact.

Do not use the renderer to invent a metric or select an executive strategy.
Every chart and card must map to validated claim ids supplied by the data
package; keep that mapping internal and expose understandable source references
instead of technical ids.
