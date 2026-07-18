# Design system for HTML decks

## Mozaika authority

When this skill runs for Mozaika, the runtime files under the canonical contract
prefix `data/brandbook/mozaika/` are the design source of truth and override
every direction below. To access them with Ouroboros file tools, use
`root="runtime_data"` and paths under `brandbook/mozaika/`; do not repeat the
root as `data/brandbook/mozaika/`, which would resolve to `data/data/...`. Keep
the full canonical prefix in handoffs and receipts. Read `BRANDBOOK.md`,
`manifest.json`, `tokens.css`, and the
artifact-specific screenshot reference; pass them into the build; use
`--theme mozaika-reference` only as the coarse scaffold fallback; then produce a
schema-valid `mozaika-design-receipt/v1`. The built-in `editorial` direction is
an optional generic theme, not the Mozaika brandbook and not an Anthropic theme.
Do not silently use its dark-red accent or any other renderer default.

## Generic core contract (for non-Mozaika work only)

The dark example below is forbidden in a Mozaika campaign. Never copy, adapt,
or describe it as a Mozaika dark theme; Mozaika has no dark brandbook variant.

Define theme tokens once:

```css
:root {
  --bg: #0b0d12;
  --surface: #151923;
  --text: #f7f4ed;
  --muted: #a8b0bf;
  --accent: #ff6a3d;
  --accent-2: #78dce8;
  --line: rgba(255,255,255,.16);
  --title-font: "Arial Black", "Helvetica Neue", sans-serif;
  --body-font: "Helvetica Neue", Arial, sans-serif;
  --slide-pad: clamp(1.25rem, 4vw, 4.5rem);
}
```

Change tokens intentionally. Do not scatter arbitrary colors, radii, and shadows.

## Five generic directions

### Signal

Best for launches, pitches, decisive strategy.

- graphite field;
- orange focal accent;
- oversized sans-serif titles;
- sharp blocks/alignment;
- restrained scale/fade;
- neutral charts with one highlighted series.

### Editorial

Best for narrative keynotes, research interpretation, premium brands.

- warm paper or near-black ink;
- expressive serif title + neutral sans body;
- fine rules, pull quotes, captions;
- asymmetrical magazine composition;
- slow/minimal motion.

### Swiss

Best for analytics, product strategy, corporate reviews.

- white/off-white;
- black type + one red/cobalt accent;
- visible grid;
- disciplined asymmetry;
- flat directly-labeled charts.

### Botanical

Best for climate, wellness, thoughtful products, premium storytelling.

- deep forest/near-black;
- ivory text + clay/blush/gold accent;
- organic atmosphere, not decoration;
- evidence/photography remains dominant;
- gentle cross-fades.

### Terminal

Best for APIs, infrastructure, CLI, security, developer tools.

- dark editor field;
- monospace labels + readable sans body;
- green/cyan accent;
- thin grid, prompt motifs, precise diagrams;
- no fake hacker noise.

## Type scale

```css
--display: clamp(2.4rem, 7vw, 6.8rem);
--h1: clamp(2rem, 5.2vw, 4.8rem);
--h2: clamp(1.5rem, 3.4vw, 3rem);
--body: clamp(1rem, 1.7vw, 1.45rem);
--small: clamp(.75rem, 1.1vw, 1rem);
```

At 1280×720, body copy usually needs roughly 22–30 CSS pixels depending on density and distance. Split content rather than shrinking.

## Layout

Use a stable grid and outer safe area.

Common compositions:

1. Hero assertion + evidence object
2. 40/60 explanation + diagram
3. Full-bleed image + scrim
4. Metric row + interpretation
5. Aligned comparison
6. Timeline with highlighted transition
7. Chart + direct annotation
8. Quote + context
9. Architecture map + staged highlight
10. Quiet synthesis sentence

Do not put every idea in a rounded card. Cards imply independent objects; arguments often require sequence or relationship.

## Color

- one dominant accent;
- optional second accent with a different semantic role;
- color is never the only state signal;
- neutral gray carries context;
- accent carries the claim;
- avoid rainbow categorical palettes unless necessary.

## Charts

- title states the finding;
- direct-label series when possible;
- annotate the important change;
- include unit, period, baseline, source;
- use honest axes;
- preserve uncertainty;
- animate reasoning, not decoration.

## Images

- prefer real evidence: screenshots, people, places, artifacts;
- do not crop away relevant evidence;
- use a scrim for readable overlay text;
- attribute/licence when needed;
- never fake testimonials, logos, screenshots, or data.

## Motion

Motion should show:

1. what appeared;
2. what changed;
3. what deserves attention;
4. how two states relate.

Typical durations:

- emphasis: 120–220 ms;
- entrance: 220–450 ms;
- state transition: 350–700 ms;
- cinematic transition: up to 900 ms, rarely.

Respect reduced motion. Avoid continuous motion behind text.

## Responsive contract

```css
.slide {
  width: 100vw;
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
}
```

Use `clamp()`, grid/flex, `minmax()`, and short-height breakpoints. Mobile may require recomposition, not simple scaling.

## Anti-patterns

- automatic purple-blue gradient;
- Inter/Roboto + rounded cards as the whole identity;
- bullet walls;
- nested cards;
- tiny essential footnotes;
- gradients on every section;
- mixed icon families;
- code screenshots when selectable code works;
- undirected process diagrams;
- animation on every element;
- decorative chrome consuming safe area;
- topic-label titles.
