#!/usr/bin/env python3
"""Generate a responsive HTML presentation scaffold from a simple Markdown outline."""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

from state_paths import output_path

THEMES = {
    "mozaika-reference": {
        "bg": "#faf9f5", "surface": "#f0eee6", "text": "#141413", "muted": "#5e5d59",
        "accent": "#388f76", "accent2": "#d787a3",
        "title_font": 'Inter, "Helvetica Neue", Arial, sans-serif',
        "body_font": 'Georgia, "Times New Roman", serif',
    },
    "signal": {
        "bg": "#0b0d12", "surface": "#171b24", "text": "#f7f4ed", "muted": "#aeb5c2",
        "accent": "#ff6a3d", "accent2": "#78dce8",
        "title_font": '"Arial Black", "Helvetica Neue", Arial, sans-serif',
        "body_font": '"Helvetica Neue", Arial, sans-serif',
    },
    "editorial": {
        "bg": "#f2eadc", "surface": "#fffaf1", "text": "#211d19", "muted": "#73695f",
        "accent": "#9f2d2d", "accent2": "#9a7b43",
        "title_font": 'Georgia, "Times New Roman", serif',
        "body_font": '"Helvetica Neue", Arial, sans-serif',
    },
    "swiss": {
        "bg": "#f7f7f3", "surface": "#ffffff", "text": "#111111", "muted": "#666666",
        "accent": "#e32727", "accent2": "#1f5cff",
        "title_font": '"Arial Black", Arial, sans-serif',
        "body_font": 'Arial, Helvetica, sans-serif',
    },
    "botanical": {
        "bg": "#101814", "surface": "#1b2821", "text": "#f4eddf", "muted": "#b4b8aa",
        "accent": "#d77b61", "accent2": "#c8a968",
        "title_font": 'Georgia, "Times New Roman", serif',
        "body_font": '"Helvetica Neue", Arial, sans-serif',
    },
    "terminal": {
        "bg": "#0d1117", "surface": "#161b22", "text": "#e6edf3", "muted": "#8b949e",
        "accent": "#3fb950", "accent2": "#58a6ff",
        "title_font": '"Courier New", monospace',
        "body_font": '"Helvetica Neue", Arial, sans-serif',
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outline", required=True, help="Markdown outline; slides separated by ---")
    parser.add_argument("--brief", default="", help="Optional JSON brief")
    parser.add_argument(
        "--output", default="presentation.html",
        help="Relative output name inside the immutable Ouroboros job directory",
    )
    parser.add_argument(
        "--job-id", default="",
        help="Stable run identifier; a unique identifier is generated when omitted",
    )
    parser.add_argument("--engine", choices=["vanilla", "reveal"], default="vanilla")
    parser.add_argument("--theme", choices=sorted(THEMES), default="mozaika-reference")
    parser.add_argument("--title", default="", help="Override document title")
    return parser.parse_args()


def load_brief(path: str) -> dict[str, Any]:
    if not path:
        return {}
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("brief JSON root must be an object")
    return value


def split_slides(text: str) -> list[str]:
    return [
        block.strip()
        for block in re.split(r"(?m)^\s*---\s*$", text)
        if block.strip()
    ]


def inline_markup(value: str) -> str:
    escaped = html.escape(value.strip())
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
    return escaped


def safe_image_source(value: str) -> str:
    source = value.strip()
    if source.startswith("data:image/"):
        return source
    path = Path(source)
    if (
        not source
        or path.is_absolute()
        or ".." in path.parts
        or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", source)
    ):
        raise SystemExit(
            "IMAGE sources must be embedded data:image URLs or safe relative "
            "paths inside the immutable job output. Remote, absolute, file, "
            "and parent-traversal sources are not allowed."
        )
    return source


def parse_slide(block: str, index: int) -> dict[str, Any]:
    slide: dict[str, Any] = {
        "title": "", "subtitle": "", "items": [], "notes": [],
        "kind": "title" if index == 1 else "content",
    }
    for raw in block.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# ") and not slide["title"]:
            slide["title"] = line[2:].strip()
        elif line.startswith("## ") and not slide["subtitle"]:
            slide["subtitle"] = line[3:].strip()
        elif line.startswith("NOTE:"):
            slide["notes"].append(line[5:].strip())
        elif line.startswith("METRIC:"):
            value, sep, label = line[7:].strip().partition("|")
            slide["items"].append(("metric", value.strip(), label.strip() if sep else ""))
        elif line.startswith("IMAGE:"):
            src, sep, alt = line[6:].strip().partition("|")
            slide["items"].append(("image", src.strip(), alt.strip() if sep else ""))
        elif line.startswith(">"):
            slide["items"].append(("quote", line[1:].strip()))
        elif re.match(r"^[-*]\s+", line):
            slide["items"].append(("bullet", re.sub(r"^[-*]\s+", "", line)))
        elif re.match(r"^\d+[.)]\s+", line):
            slide["items"].append(("step", re.sub(r"^\d+[.)]\s+", "", line)))
        else:
            slide["items"].append(("paragraph", line))
    slide["title"] = slide["title"] or f"Slide {index}"
    return slide


def render_items(items: list[tuple]) -> str:
    parts: list[str] = []
    bullets = [item for item in items if item[0] == "bullet"]
    steps = [item for item in items if item[0] == "step"]
    if bullets:
        parts.append(
            '<ul class="points">'
            + "".join(f"<li>{inline_markup(item[1])}</li>" for item in bullets)
            + "</ul>"
        )
    if steps:
        parts.append(
            '<ol class="steps">'
            + "".join(f"<li><span>{inline_markup(item[1])}</span></li>" for item in steps)
            + "</ol>"
        )
    for item in items:
        kind = item[0]
        if kind in {"bullet", "step"}:
            continue
        if kind == "metric":
            parts.append(
                f'<div class="metric"><strong>{inline_markup(item[1])}</strong>'
                f'<span>{inline_markup(item[2])}</span></div>'
            )
        elif kind == "image":
            src = html.escape(safe_image_source(item[1]), quote=True)
            alt = html.escape(item[2], quote=True)
            parts.append(
                f'<figure><img src="{src}" alt="{alt}">'
                f'<figcaption>{inline_markup(item[2])}</figcaption></figure>'
            )
        elif kind == "quote":
            parts.append(f"<blockquote>{inline_markup(item[1])}</blockquote>")
        else:
            parts.append(f"<p>{inline_markup(item[1])}</p>")
    return "\n".join(parts)


def common_css(theme: dict[str, str]) -> str:
    return f"""
:root {{
  --bg:{theme['bg']}; --surface:{theme['surface']}; --text:{theme['text']};
  --muted:{theme['muted']}; --accent:{theme['accent']}; --accent-2:{theme['accent2']};
  --title-font:{theme['title_font']}; --body-font:{theme['body_font']};
  --display:clamp(2.5rem,7vw,6.5rem); --h1:clamp(1.8rem,4.7vw,4.5rem);
  --h2:clamp(1.2rem,2.6vw,2.2rem); --body:clamp(1rem,1.65vw,1.45rem);
  --small:clamp(.72rem,1vw,.95rem); --pad:clamp(1.25rem,4.5vw,5rem);
}}
* {{ box-sizing:border-box; }}
html,body {{
  margin:0; min-height:100%; background:var(--bg); color:var(--text);
  font-family:var(--body-font);
}}
body {{ overflow-x:hidden; }}
.slide,.reveal .slides section {{
  position:relative; padding:var(--pad); text-align:left;
}}
.slide {{
  width:100vw; height:100vh; height:100dvh; overflow:hidden;
  display:flex; flex-direction:column; justify-content:center;
}}
h1,h2,h3 {{
  font-family:var(--title-font); margin:0; line-height:.98;
  letter-spacing:-.035em; text-wrap:balance;
}}
h1 {{ font-size:var(--h1); max-width:18ch; }}
.title h1 {{ font-size:var(--display); max-width:12ch; }}
h2 {{
  font-size:var(--h2); color:var(--muted); font-weight:500;
  margin-top:1.2rem; max-width:38ch;
}}
p,li,blockquote {{ font-size:var(--body); line-height:1.38; }}
.content {{
  margin-top:clamp(1.1rem,3vh,2.6rem);
  max-width:min(92vw,1100px);
}}
.points {{
  list-style:none; padding:0; display:grid;
  gap:clamp(.55rem,1.3vh,1.1rem); max-width:42ch;
}}
.points li {{ position:relative; padding-left:1.35em; }}
.points li::before {{
  content:""; width:.48em; height:.48em; background:var(--accent);
  position:absolute; left:0; top:.45em;
}}
.steps {{
  list-style:none; padding:0; counter-reset:step; display:grid;
  grid-template-columns:repeat(auto-fit,minmax(min(100%,190px),1fr));
  gap:clamp(.7rem,1.5vw,1.3rem);
}}
.steps li {{
  counter-increment:step; min-height:9rem; background:var(--surface);
  border-top:4px solid var(--accent); padding:1.1rem;
  display:flex; flex-direction:column; gap:.7rem;
}}
.steps li::before {{
  content:counter(step,decimal-leading-zero); color:var(--accent);
  font-weight:800; font-size:var(--small); letter-spacing:.12em;
}}
.metric {{
  display:inline-flex; flex-direction:column; margin:1rem 1rem 0 0;
  padding:1rem 1.25rem; border-left:5px solid var(--accent);
  background:var(--surface); min-width:min(80vw,260px);
}}
.metric strong {{
  font-family:var(--title-font); font-size:clamp(2.3rem,6vw,5.8rem);
  line-height:.9; color:var(--accent);
}}
.metric span {{ margin-top:.55rem; color:var(--muted); font-size:var(--small); }}
blockquote {{
  margin:1.2rem 0; padding:1rem 1.2rem;
  border-left:4px solid var(--accent-2);
  max-width:38ch; background:var(--surface);
}}
figure {{ margin:1rem 0; max-width:min(90vw,1100px); }}
figure img {{
  display:block; max-width:100%; max-height:52vh; object-fit:contain;
}}
figcaption,.source,.eyebrow {{ color:var(--muted); font-size:var(--small); }}
.eyebrow {{
  position:absolute; top:clamp(.8rem,2vw,1.6rem); left:var(--pad);
  text-transform:uppercase; letter-spacing:.16em;
}}
.progress {{
  position:fixed; z-index:20; left:0; bottom:0; height:5px; width:0;
  background:var(--accent); transition:width .25s ease;
}}
.deck-controls {{
  position:fixed; z-index:30; right:clamp(.7rem,2vw,1.4rem); top:clamp(.7rem,2vw,1.4rem);
  display:flex; gap:.45rem;
}}
.deck-controls button {{
  border:1px solid color-mix(in srgb,var(--muted) 45%,transparent);
  background:color-mix(in srgb,var(--bg) 86%,transparent); color:var(--text);
  border-radius:999px; padding:.5rem .72rem; font:600 var(--small)/1 var(--body-font);
  cursor:pointer; backdrop-filter:blur(12px);
}}
.deck-controls button:focus-visible {{ outline:3px solid var(--accent-2); outline-offset:2px; }}
body.overview {{ overflow:auto; padding:clamp(1rem,3vw,2.4rem); }}
body.overview main {{
  display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));
  gap:clamp(.8rem,2vw,1.4rem);
}}
body.overview .slide {{
  width:100%; height:auto; min-height:220px; aspect-ratio:16/9; padding:clamp(.8rem,2vw,1.5rem);
  border:1px solid color-mix(in srgb,var(--muted) 35%,transparent);
  box-shadow:0 18px 50px color-mix(in srgb,#000 22%,transparent); cursor:pointer;
}}
body.overview .slide h1 {{ font-size:clamp(1.15rem,2.2vw,2rem); }}
body.overview .slide h2,body.overview .slide p,body.overview .slide li {{ font-size:clamp(.68rem,1vw,.9rem); }}
body.overview .slide .metric strong {{ font-size:clamp(1.4rem,3vw,2.5rem); }}
body.overview .progress {{ display:none; }}
.slide-number {{
  position:absolute; right:var(--pad); bottom:clamp(.8rem,2vw,1.5rem);
  color:var(--muted); font-size:var(--small);
}}
code {{
  font-family:"Courier New",monospace;
  background:var(--surface); padding:.08em .28em;
}}
@media (max-height:650px) {{
  :root {{
    --pad:clamp(.8rem,3vw,2.3rem);
    --body:clamp(.88rem,1.35vw,1.15rem);
  }}
  .steps li {{ min-height:6.5rem; }}
}}
@media (max-height:500px) {{
  :root {{
    --pad:clamp(.65rem,2.2vw,1.25rem);
    --h1:clamp(1.4rem,4vw,2rem);
    --h2:clamp(.9rem,2.4vw,1.25rem);
    --body:clamp(.72rem,1.35vw,.88rem);
    --small:clamp(.62rem,.9vw,.75rem);
  }}
  .slide {{ justify-content:flex-start; }}
  .eyebrow,.slide-number {{ display:none; }}
  .content {{ margin-top:clamp(.35rem,1.2vh,.65rem); }}
  .points {{ gap:clamp(.18rem,.65vh,.4rem); margin:.25rem 0; }}
  .metric {{ margin:.35rem .5rem 0 0; padding:.45rem .75rem; }}
  .metric strong {{ font-size:clamp(1.8rem,5vw,2.8rem); }}
  .metric span {{ margin-top:.25rem; }}
  blockquote {{ margin:.4rem 0; padding:.5rem .75rem; }}
  .steps {{ gap:.5rem; }}
  .steps li {{ min-height:5.2rem; padding:.65rem; }}
}}
@media (max-width:600px) {{
  .steps {{ grid-template-columns:1fr 1fr; }}
  .metric strong {{ font-size:clamp(2rem,14vw,4rem); }}
}}
@media (prefers-reduced-motion:reduce) {{
  *,*::before,*::after {{
    animation-duration:.01ms!important;
    animation-iteration-count:1!important;
    transition-duration:.01ms!important;
    scroll-behavior:auto!important;
  }}
}}
@media print {{
  .slide {{ break-after:page; width:100%; height:100vh; }}
  .progress,.deck-controls {{ display:none; }}
}}
"""


def vanilla_html(
    slides: list[dict[str, Any]],
    brief: dict[str, Any],
    theme: dict[str, str],
    document_title: str,
    theme_name: str,
) -> str:
    rendered: list[str] = []
    total = len(slides)
    organization = html.escape(str(brief.get("organization") or "HTML presentation"))
    for index, slide in enumerate(slides, 1):
        notes = html.escape(" ".join(slide["notes"]), quote=True)
        css_class = "slide title" if slide["kind"] == "title" else "slide"
        subtitle = (
            f'<h2>{inline_markup(slide["subtitle"])}</h2>'
            if slide["subtitle"] else ""
        )
        rendered.append(f"""
<section class="{css_class}" id="slide-{index}"
         aria-labelledby="slide-{index}-title" data-notes="{notes}">
  <div class="eyebrow">{organization}</div>
  <h1 id="slide-{index}-title">{inline_markup(slide["title"])}</h1>
  {subtitle}
  <div class="content">{render_items(slide["items"])}</div>
  <div class="slide-number" aria-hidden="true">{index:02d} / {total:02d}</div>
</section>
""")
    css = common_css(theme)
    lang = html.escape(str(brief.get("language") or "en"))
    description = html.escape(
        str(brief.get("one_takeaway") or document_title), quote=True
    )
    mozaika_marker = (
        ' data-mozaika-brandbook="mozaika-brandbook/v1" data-mozaika-theme="mozaika-reference"'
        if theme_name == "mozaika-reference" else ""
    )
    return f"""<!doctype html>
<html lang="{lang}"{mozaika_marker}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="{description}">
<title>{html.escape(document_title)}</title>
<style>
{css}
html {{ scroll-snap-type:y mandatory; scroll-behavior:smooth; }}
.slide {{ scroll-snap-align:start; }}
</style>
</head>
<body data-presentation-theme="{html.escape(theme_name, quote=True)}">
<a href="#slide-1" class="source" style="position:absolute;left:-9999px">
  Skip to presentation
</a>
<main aria-label="Presentation">
{''.join(rendered)}
</main>
<nav class="deck-controls" aria-label="Presentation controls">
  <button type="button" id="overview-toggle" aria-pressed="false" title="Overview (O)">Обзор</button>
  <button type="button" id="fullscreen-toggle" title="Fullscreen (F)">На весь экран</button>
</nav>
<div class="progress" id="progress" aria-hidden="true"></div>
<script>
(() => {{
  const slides = [...document.querySelectorAll('.slide')];
  let current = 0;
  let wheelLocked = false;
  let touchY = null;
  const clamp = n => Math.max(0, Math.min(slides.length - 1, n));
  const overviewButton = document.getElementById('overview-toggle');
  const fullscreenButton = document.getElementById('fullscreen-toggle');
  function toggleOverview(force) {{
    const next = typeof force === 'boolean' ? force : !document.body.classList.contains('overview');
    document.body.classList.toggle('overview', next);
    overviewButton.setAttribute('aria-pressed', String(next));
    if (!next) go(current);
  }}
  async function toggleFullscreen() {{
    if (!document.fullscreenElement) await document.documentElement.requestFullscreen?.();
    else await document.exitFullscreen?.();
  }}
  function go(n) {{
    current = clamp(n);
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    slides[current].scrollIntoView({{behavior: reduced ? 'auto' : 'smooth'}});
    update();
  }}
  function update() {{
    document.getElementById('progress').style.width =
      ((current + 1) / slides.length * 100) + '%';
    history.replaceState(null, '', '#' + slides[current].id);
  }}
  addEventListener('keydown', event => {{
    if (event.key.toLowerCase() === 'o') {{
      event.preventDefault(); toggleOverview(); return;
    }} else if (event.key.toLowerCase() === 'f') {{
      event.preventDefault(); toggleFullscreen(); return;
    }} else if (event.key === 'Escape' && document.body.classList.contains('overview')) {{
      event.preventDefault(); toggleOverview(false); return;
    }}
    if (document.body.classList.contains('overview')) return;
    if (['ArrowRight','ArrowDown','PageDown',' '].includes(event.key)) {{
      event.preventDefault(); go(current + 1);
    }} else if (['ArrowLeft','ArrowUp','PageUp'].includes(event.key)) {{
      event.preventDefault(); go(current - 1);
    }} else if (event.key === 'Home') {{
      event.preventDefault(); go(0);
    }} else if (event.key === 'End') {{
      event.preventDefault(); go(slides.length - 1);
    }}
  }});
  overviewButton.addEventListener('click', () => toggleOverview());
  fullscreenButton.addEventListener('click', () => toggleFullscreen());
  slides.forEach((slide, index) => slide.addEventListener('click', () => {{
    if (!document.body.classList.contains('overview')) return;
    current = index; toggleOverview(false);
  }}));
  addEventListener('wheel', event => {{
    if (wheelLocked || Math.abs(event.deltaY) < 18) return;
    wheelLocked = true;
    go(current + (event.deltaY > 0 ? 1 : -1));
    setTimeout(() => wheelLocked = false, 450);
  }}, {{passive:true}});
  addEventListener('touchstart', event => {{
    touchY = event.changedTouches[0].clientY;
  }}, {{passive:true}});
  addEventListener('touchend', event => {{
    if (touchY === null) return;
    const delta = touchY - event.changedTouches[0].clientY;
    if (Math.abs(delta) > 45) go(current + (delta > 0 ? 1 : -1));
    touchY = null;
  }}, {{passive:true}});
  const observer = new IntersectionObserver(entries => entries.forEach(entry => {{
    if (entry.isIntersecting && entry.intersectionRatio > .55) {{
      current = slides.indexOf(entry.target);
      update();
    }}
  }}), {{threshold:[.55]}});
  slides.forEach(slide => observer.observe(slide));
  const hashSlide = location.hash && document.querySelector(location.hash);
  if (hashSlide) current = Math.max(0, slides.indexOf(hashSlide));
  update();
}})();
</script>
</body>
</html>
"""


def reveal_html(
    slides: list[dict[str, Any]],
    brief: dict[str, Any],
    theme: dict[str, str],
    document_title: str,
) -> str:
    rendered: list[str] = []
    for index, slide in enumerate(slides, 1):
        css_class = ' class="title"' if slide["kind"] == "title" else ""
        subtitle = (
            f'<h2>{inline_markup(slide["subtitle"])}</h2>'
            if slide["subtitle"] else ""
        )
        notes = " ".join(slide["notes"])
        note_html = (
            f'<aside class="notes">{inline_markup(notes)}</aside>'
            if notes else ""
        )
        rendered.append(f"""
<section id="slide-{index}"{css_class} aria-labelledby="slide-{index}-title">
  <h1 id="slide-{index}-title">{inline_markup(slide["title"])}</h1>
  {subtitle}
  <div class="content">{render_items(slide["items"])}</div>
  {note_html}
</section>
""")
    css = common_css(theme)
    lang = html.escape(str(brief.get("language") or "en"))
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(document_title)}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.css">
<style>
{css}
.reveal {{
  font-family:var(--body-font); color:var(--text); background:var(--bg);
}}
.reveal .slides {{ text-align:left; }}
.reveal .slides section {{ height:100%; overflow:hidden; }}
.reveal h1,.reveal h2 {{ text-transform:none; color:inherit; }}
.reveal h1 {{ font-size:var(--h1); }}
.reveal .title h1 {{ font-size:var(--display); }}
.reveal p,.reveal li,.reveal blockquote {{ font-size:var(--body); }}
</style>
</head>
<body>
<div class="reveal"><div class="slides">{''.join(rendered)}</div></div>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.js"></script>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5/plugin/notes/notes.js"></script>
<script>
Reveal.initialize({{
  hash:true,
  slideNumber:'c/t',
  progress:true,
  controls:true,
  center:false,
  transition:'fade',
  backgroundTransition:'fade',
  pdfMaxPagesPerSlide:1,
  pdfSeparateFragments:false,
  plugins:[RevealNotes]
}});
</script>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    brief = load_brief(args.brief)
    outline = Path(args.outline).read_text(encoding="utf-8")
    slides = [
        parse_slide(block, index)
        for index, block in enumerate(split_slides(outline), 1)
    ]
    if not slides:
        raise SystemExit("outline contains no slides")
    document_title = args.title or str(
        brief.get("title") or slides[0]["title"]
    )
    output = output_path(args.job_id, args.output)
    if args.engine == "vanilla":
        content = vanilla_html(slides, brief, THEMES[args.theme], document_title, args.theme)
    else:
        content = reveal_html(slides, brief, THEMES[args.theme], document_title)
    output.write_text(content, encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "output": str(output.resolve()),
        "engine": args.engine,
        "theme": args.theme,
        "slides": len(slides),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
