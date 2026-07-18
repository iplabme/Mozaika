#!/usr/bin/env python3
"""Dependency-free static audit for HTML presentation quality and safety."""
from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from state_paths import output_path

GENERIC_TITLES = {
    "agenda", "overview", "introduction", "market", "problem", "solution",
    "results", "architecture", "conclusion", "summary", "next steps",
    "questions", "questions?", "thank you", "thank you!", "q&a",
}
MOZAIKA_CORE_COLORS = {"#faf9f5", "#f0eee6", "#141413", "#5e5d59", "#388f76"}
FORBIDDEN_MOZAIKA_COLORS = {"#0f0e17", "#1a1726", "#211e30", "#c93545", "#e85d6f"}


def external_dependency_urls(text: str) -> list[str]:
    """Find network-loaded resources while allowing ordinary source hyperlinks."""

    patterns = [
        r'<(?:script|img|iframe|source|video|audio)[^>]+(?:src|poster)=["\'](https?://[^"\']+)',
        r'<link[^>]+href=["\'](https?://[^"\']+)',
        r'@import\s+(?:url\()?\s*["\']?(https?://[^\s"\')]+)',
        r'url\(\s*["\']?(https?://[^\s"\')]+)',
    ]
    values: set[str] = set()
    for pattern in patterns:
        values.update(re.findall(pattern, text, re.I))
    return sorted(values)


class DeckParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.html_attrs: dict[str, str | None] = {}
        self.sections: list[dict[str, Any]] = []
        self.stack: list[tuple[str, Any]] = []
        self.ids: list[str] = []
        self.current: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "html":
            self.html_attrs = attr
        if attr.get("id"):
            self.ids.append(str(attr["id"]))
        if tag == "section":
            self.current = {
                "attrs": attr,
                "text": [],
                "headings": [],
                "bullets": 0,
                "images": [],
            }
            self.sections.append(self.current)
            self.stack.append(("section", self.current))
        elif tag in {"h1", "h2", "h3"} and self.current is not None:
            self.stack.append((tag, []))
        elif tag == "li" and self.current is not None:
            self.current["bullets"] += 1
        elif tag == "img":
            image = {"src": attr.get("src", ""), "alt": attr.get("alt")}
            if self.current is not None:
                self.current["images"].append(image)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2", "h3"} and self.stack and self.stack[-1][0] == tag:
            _, parts = self.stack.pop()
            text = " ".join("".join(parts).split())
            if self.current is not None and text:
                self.current["headings"].append(text)
        elif tag == "section":
            for index in range(len(self.stack) - 1, -1, -1):
                if self.stack[index][0] == "section":
                    self.stack.pop(index)
                    break
            self.current = None
            for kind, value in reversed(self.stack):
                if kind == "section":
                    self.current = value
                    break

    def handle_data(self, data: str) -> None:
        if self.current is not None:
            self.current["text"].append(data)
        if self.stack and self.stack[-1][0] in {"h1", "h2", "h3"}:
            self.stack[-1][1].append(data)


def finding(
    severity: str,
    code: str,
    message: str,
    slide: int | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if slide is not None:
        value["slide"] = slide
    return value


def audit(path: Path, *, require_mozaika_brandbook: bool = False) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lower = text.lower()
    parser = DeckParser()
    parser.feed(text)
    issues: list[dict[str, Any]] = []

    if not parser.html_attrs.get("lang"):
        issues.append(finding("MEDIUM", "html-lang", "<html> has no lang attribute."))

    if require_mozaika_brandbook:
        colors = {value.lower() for value in re.findall(r"#[0-9a-fA-F]{6}\b", text)}
        missing = sorted(MOZAIKA_CORE_COLORS - colors)
        forbidden = sorted(FORBIDDEN_MOZAIKA_COLORS & colors)
        if parser.html_attrs.get("data-mozaika-brandbook") != "mozaika-brandbook/v1":
            issues.append(finding("HIGH", "mozaika-brandbook-marker", "Missing exact Mozaika brandbook marker."))
        if parser.html_attrs.get("data-mozaika-theme") != "mozaika-reference":
            issues.append(finding("HIGH", "mozaika-theme-marker", "Missing exact mozaika-reference theme marker."))
        if missing:
            issues.append(finding("HIGH", "mozaika-core-palette", "Missing Mozaika core colors: " + ", ".join(missing)))
        if forbidden:
            issues.append(finding("HIGH", "mozaika-forbidden-palette", "Forbidden renderer colors: " + ", ".join(forbidden)))
        if re.search(r"color-scheme\s*:\s*dark\b", lower):
            issues.append(finding("HIGH", "mozaika-dark-theme", "Dark color-scheme is forbidden for Mozaika."))

    if not re.search(r'<meta[^>]+name=["\']viewport["\']', text, re.I):
        issues.append(finding("HIGH", "viewport", "Missing viewport meta tag."))

    if not parser.sections:
        issues.append(finding("HIGH", "slides", "No <section> slides found."))

    duplicates = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
    if duplicates:
        issues.append(finding(
            "HIGH",
            "duplicate-id",
            "Duplicate element IDs: " + ", ".join(duplicates[:10]),
        ))

    for slide_number, slide in enumerate(parser.sections, 1):
        visible = " ".join(slide["text"])
        words = re.findall(r"\b[\w'-]+\b", visible, re.U)
        title = slide["headings"][0].strip() if slide["headings"] else ""

        if not title:
            issues.append(finding("HIGH", "heading", "Slide has no heading.", slide_number))
        elif title.lower() in GENERIC_TITLES:
            issues.append(finding(
                "MEDIUM",
                "generic-title",
                f'Generic topic-label title: “{title}”. Rewrite as an assertion.',
                slide_number,
            ))

        title_words = len(title.split())
        if title_words > 16:
            issues.append(finding(
                "MEDIUM",
                "long-title",
                f"Title has {title_words} words; simplify or split.",
                slide_number,
            ))

        if len(words) > 90:
            issues.append(finding(
                "HIGH",
                "density",
                f"{len(words)} visible words; likely too dense for one slide.",
                slide_number,
            ))
        elif len(words) > 65:
            issues.append(finding(
                "MEDIUM",
                "density",
                f"{len(words)} visible words; inspect at projector size.",
                slide_number,
            ))

        if slide["bullets"] > 6:
            issues.append(finding(
                "MEDIUM",
                "bullets",
                f'{slide["bullets"]} list items; default maximum is 6.',
                slide_number,
            ))

        for image in slide["images"]:
            if image["alt"] is None:
                issues.append(finding(
                    "HIGH", "image-alt", "Image is missing an alt attribute.", slide_number
                ))
            elif not str(image["alt"]).strip():
                issues.append(finding(
                    "LOW",
                    "image-alt-empty",
                    "Image has empty alt; confirm it is decorative.",
                    slide_number,
                ))

    if parser.sections:
        last = parser.sections[-1]
        closing = last["headings"][0].lower().strip() if last["headings"] else ""
        if closing in {"questions", "questions?", "thank you", "thank you!", "q&a"}:
            issues.append(finding(
                "MEDIUM",
                "closing",
                "Closing slide should preserve the conclusion or requested action, not only Q&A/thanks.",
                len(parser.sections),
            ))

    if "prefers-reduced-motion" not in lower:
        issues.append(finding(
            "MEDIUM", "reduced-motion", "No prefers-reduced-motion CSS found."
        ))

    if not re.search(
        r"addEventListener\s*\(\s*['\"]keydown|Reveal\.initialize",
        text,
    ):
        issues.append(finding(
            "HIGH",
            "keyboard",
            "No keyboard navigation hook or Reveal initialization found.",
        ))

    if "requestfullscreen" not in lower and "reveal.initialize" not in lower:
        issues.append(finding(
            "HIGH", "fullscreen", "No fullscreen control was found."
        ))

    if "overview" not in lower and "reveal.initialize" not in lower:
        issues.append(finding(
            "HIGH", "overview", "No slide overview mode was found."
        ))

    if "@media print" not in lower and "reveal.js" not in lower:
        issues.append(finding("LOW", "print", "No print stylesheet found."))

    if re.search(
        r"\.slide[^\{]*\{[^\}]*overflow\s*:\s*(auto|scroll)",
        text,
        re.I | re.S,
    ):
        issues.append(finding(
            "HIGH",
            "slide-scroll",
            "A slide allows internal scrolling. Split content instead.",
        ))

    if re.search(r"\b(TODO|TBD|LOREM IPSUM|PLACEHOLDER)\b", text, re.I):
        issues.append(finding(
            "MEDIUM", "placeholder", "Placeholder text remains in the deck."
        ))

    external_urls = sorted(set(re.findall(r'https?://[^\s"\')>]+', text)))
    external_dependencies = external_dependency_urls(text)
    if external_dependencies:
        issues.append(finding(
            "HIGH",
            "external-deps",
            f"{len(external_dependencies)} network-loaded dependency URL(s); inline reviewed assets for an offline deck.",
        ))

    script_urls = re.findall(r'<script[^>]+src=["\']([^"\']+)', text, re.I)
    if script_urls:
        issues.append(finding(
            "HIGH",
            "third-party-script",
            "External script tags are not self-contained: " + ", ".join(script_urls[:5]),
        ))

    weights = {"HIGH": 18, "MEDIUM": 7, "LOW": 2}
    score = max(0, 100 - sum(weights[item["severity"]] for item in issues))
    counts = {
        severity: sum(item["severity"] == severity for item in issues)
        for severity in ("HIGH", "MEDIUM", "LOW")
    }
    verdict = "PASS" if counts["HIGH"] == 0 and score >= 80 else "REVISION_NEEDED"

    return {
        "file": str(path.resolve()),
        "slides": len(parser.sections),
        "score": score,
        "verdict": verdict,
        "counts": counts,
        "issues": issues,
        "external_urls": external_urls,
        "external_dependencies": external_dependencies,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--require-mozaika-brandbook", action="store_true")
    parser.add_argument("--job-id", default="")
    parser.add_argument(
        "--report", default="audit-report.json",
        help="Relative JSON report name inside the immutable job output directory",
    )
    args = parser.parse_args()

    result = audit(Path(args.html), require_mozaika_brandbook=args.require_mozaika_brandbook)
    report = output_path(args.job_id, args.report)
    result["report"] = str(report)
    report.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"Deck: {result['file']}\n"
            f"Slides: {result['slides']}\n"
            f"Score: {result['score']}/100\n"
            f"Verdict: {result['verdict']}\n"
        )
        if not result["issues"]:
            print("No issues found.")
        for item in result["issues"]:
            where = f" slide {item['slide']}" if "slide" in item else ""
            print(f"[{item['severity']}] {item['code']}{where}: {item['message']}")

    return 1 if args.strict and result["verdict"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
