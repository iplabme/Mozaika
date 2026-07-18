# Framework selection guide

## Vanilla single-file HTML

Choose when:

- one portable file is desired;
- bespoke visual design matters;
- offline use is important;
- plugin-heavy presentation mechanics are unnecessary;
- navigation and print behavior can be tested.

Advantages: full control, no build step, easy hosting, small supply-chain surface.

Costs: speaker view, overview, notes, export, and edge cases are your responsibility.

## Reveal.js

Choose when:

- speaker notes/presenter view matter;
- horizontal and vertical navigation is useful;
- fragments or Auto-Animate are needed;
- code, math, overview, plugins, and mature PDF export matter;
- CDN or a local reveal.js bundle is acceptable.

For confidential/offline use, vendor reveal.js locally.

## Slidev

Choose when:

- the author prefers Markdown;
- Vue components, Monaco, Mermaid, UnoCSS, live code, themes, or recording are valuable;
- a Node/Vite project is acceptable.

Do not choose Slidev merely because the topic is technical; choose it for authoring/runtime capabilities.

## Marp

Choose when:

- speed and Markdown simplicity dominate;
- PDF/PPTX export matters;
- layouts are conventional;
- a modest theme is sufficient.

Do not choose it for bespoke responsive art direction or complex interaction.

## Quarto reveal.js

Choose when:

- slides live beside research/documentation;
- executable code, citations, bibliography, equations, or publishing pipelines are central;
- Quarto is already part of the project.

## Decision table

| Requirement | Vanilla | Reveal.js | Slidev | Marp |
|---|---:|---:|---:|---:|
| one portable file | excellent | possible | weak | moderate |
| bespoke CSS | excellent | excellent | excellent | limited |
| speaker view/notes | custom | excellent | excellent | moderate |
| code-heavy | good | excellent | excellent | good |
| live Vue | custom | possible | excellent | no |
| no build | excellent | excellent | no | CLI/editor |
| Markdown speed | moderate | good | excellent | excellent |
| mature PDF | custom | excellent | excellent | excellent |
| minimal dependencies | excellent | good | weak | good |

## Export

Reveal.js supports Chromium print/PDF mode and documents DeckTape. Slidev provides `slidev export`; Marp provides CLI/editor export. Always inspect exported output because fonts, backgrounds, fragments, and page size can differ from live mode.
