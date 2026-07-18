---
name: presentation-skill
description: >
  Build editable PowerPoint .pptx decks from a structured outline.json.
  Accepts 13 slide variants: title, section, content, cards, split, timeline,
  stats, kpi-hero, table, comparison, matrix, flow, image-sidebar, scientific-figure.
  Style presets include owner-approved Mozaika weekly-report and insight-deck palettes.
  Data-driven charts and tables. Adapted from siril9/presentation-skill (MIT).
version: 0.2.0
type: script
runtime: node
scripts:
  - name: build_deck.js
    description: Build a .pptx from an outline.json file.
permissions: [subprocess, fs]
when_to_use: >
  The user asks to create a PowerPoint presentation, slide deck, or .pptx file
  from structured data, an outline, or a prompt describing slides with data.
timeout_sec: 120
---

# Presentation Skill

Create editable PowerPoint decks from structured `outline.json` source files.
The agent owns narrative, evidence, and design judgment; the skill's scripts
own deterministic rendering via PptxGenJS.

## What This Skill Does

- Reads an `outline.json` file describing slides, data, charts, and tables
- Renders an editable `.pptx` using PptxGenJS (no screenshots, no Playwright)
- Supports 13 slide variants and 12 style presets
- Charts and tables are native PowerPoint objects (editable in PowerPoint/Keynote)

## Usage

```bash
node scripts/build_deck.js \
  --outline outline.json \
  --output presentation.pptx \
  --style-preset executive-clinical
```

### Style Presets

`executive-clinical` (default) | `bold-startup-narrative` | `midnight-neon` |
`data-heavy-boardroom` | `lab-report` | `editorial-minimal` | `paper-journal` |
`forest-research` | `sunset-investor` | `charcoal-safety` | `arctic-minimal` |
`lavender-ops` | `warm-terracotta` | `mozaika-weekly` | `mozaika-insight`

For Mozaika's final editable PPTX step use `mozaika-weekly`. It mirrors the
light warm canvas, pastel lavender/sage accents, restrained borders, and
editorial heading hierarchy captured in the owner-approved weekly-report
reference. The skill still receives a factual `outline.json`; it must not
invent metrics to fill a layout.

For Mozaika's insight-deck PPTX use `mozaika-insight` together with
`data/brandbook/mozaika/references/scenario-insight-presentation-style.md` and
the accepted HTML outline. The owner-provided PPTX is a visual-grammar source
only: inherit its colors, elements, spacing and placement logic, but never its
sample data, topics, slide count or slide order. Replace the example `slides`
array with the accepted storyline-derived sequence before rendering.

## Outline JSON Format

```json
{
  "title": "Q2 Business Review",
  "subtitle": "Executive summary",
  "deck_style": { "visual_density": "medium" },
  "slides": [
    { "type": "title", "title": "Q2 Review", "subtitle": "2025" },
    { "type": "section", "title": "Key Results" },
    {
      "type": "content",
      "variant": "cards-3",
      "title": "Three Priorities",
      "cards": [
        { "title": "Growth", "body": "Revenue up 14%" },
        { "title": "Margin", "body": "Improved 2.1 pts" },
        { "title": "Pipeline", "body": "22% expansion" }
      ]
    },
    {
      "type": "content",
      "variant": "chart",
      "title": "Revenue Trend",
      "assets": {
        "chart_data": {
          "type": "bar",
          "title": "Quarterly Revenue (M USD)",
          "categories": ["Q1", "Q2", "Q3", "Q4"],
          "series": [
            { "name": "2024", "labels": ["Q1","Q2","Q3","Q4"], "values": [10, 12, 15, 18] },
            { "name": "2025", "labels": ["Q1","Q2","Q3","Q4"], "values": [14, 17, 20, 24] }
          ]
        }
      }
    }
  ]
}
```

## Slide Types

| Type | Variants | Description |
|------|----------|-------------|
| `title` | — | Opening slide with title + subtitle |
| `section` | — | Section divider |
| `content` | `standard`, `cards-2`, `cards-3`, `split`, `timeline`, `stats`, `kpi-hero`, `table`, `comparison-2col`, `matrix`, `flow`, `image-sidebar`, `scientific-figure`, `generated-image`, `chart` | Content slides |

## Dependencies

This skill requires the `pptxgenjs` npm package. Install it in the skill directory:

```bash
cd data/skills/external/presentation-skill && npm install pptxgenjs
```

Or set the `PPTX_NODE_MODULES` environment variable to a directory containing pptxgenjs.

## Attribution

Adapted from [siril9/presentation-skill](https://github.com/siril9/presentation-skill) (MIT License).
The renderer, slide templates, and preset system are derived from that project.
