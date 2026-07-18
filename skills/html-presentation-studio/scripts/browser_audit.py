#!/usr/bin/env python3
"""Audit a local HTML deck in Chromium at multiple sizes using Playwright."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path

from state_paths import output_directory, output_path, require_state_input

VIEWPORTS = [
    (1920, 1080),
    (1280, 720),
    (768, 1024),
    (375, 667),
    (667, 375),
]


def external_dependency_urls(text: str) -> list[str]:
    """Find resources the browser would fetch; plain citation links are allowed."""

    patterns = [
        r'<(?:script|img|iframe|source|video|audio)[^>]+(?:src|poster)=["\']((?:https?|file)://[^"\']+)',
        r'<link[^>]+href=["\']((?:https?|file)://[^"\']+)',
        r'@import\s+(?:url\()?\s*["\']?((?:https?|file)://[^\s"\')]+)',
        r'url\(\s*["\']?((?:https?|file)://[^\s"\')]+)',
    ]
    values: set[str] = set()
    for pattern in patterns:
        values.update(re.findall(pattern, text, re.I))
    return sorted(values)


def browser_executables() -> list[Path]:
    """Find reviewable host-installed Chromium-family executables."""
    candidates: list[Path] = []
    for name in (
        "chromium", "chromium-browser", "google-chrome",
        "google-chrome-stable", "msedge", "microsoft-edge",
    ):
        value = shutil.which(name)
        if value:
            candidates.append(Path(value))

    candidates.extend([
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
        Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
    ])

    cache_roots = [
        Path.home() / "Library" / "Caches" / "ms-playwright",
        Path.home() / ".cache" / "ms-playwright",
    ]
    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if local_app_data:
        cache_roots.append(Path(local_app_data) / "ms-playwright")
    patterns = (
        "chromium_headless_shell-*/**/chrome-headless-shell",
        "chromium-*/**/Chromium",
        "chromium-*/**/chrome",
        "chromium_headless_shell-*/**/headless_shell.exe",
        "chromium-*/**/chrome.exe",
    )
    for root in cache_roots:
        if not root.is_dir():
            continue
        for pattern in patterns:
            candidates.extend(sorted(root.glob(pattern), reverse=True))

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        key = str(resolved)
        if key not in seen and resolved.is_file():
            seen.add(key)
            unique.append(resolved)
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html")
    parser.add_argument("--job-id", default="")
    parser.add_argument("--screenshots-dir", default="browser-audit-screenshots")
    parser.add_argument("--report", default="browser-audit.json")
    parser.add_argument(
        "--capture-all", action="store_true",
        help="Capture every slide at every viewport, not only overflow findings.",
    )
    args = parser.parse_args()

    deck = require_state_input(args.html)
    screenshots = (
        output_directory(args.job_id, args.screenshots_dir)
        if args.screenshots_dir else None
    )
    report = output_path(args.job_id, args.report)

    def fail(message: str) -> int:
        result = {
            "file": str(deck),
            "verdict": "BLOCKED",
            "error": message,
            "overflow_findings": [],
            "console_errors": [],
            "report": str(report),
        }
        report.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    try:
        from playwright.sync_api import sync_playwright
    except Exception as error:
        return fail(
            "Playwright is not installed in the skill environment. "
            f"Dependency error: {error}"
        )

    if not deck.exists():
        return fail(f"File not found: {deck}")
    deck_text = deck.read_text(encoding="utf-8", errors="replace")
    external_dependencies = external_dependency_urls(deck_text)
    if external_dependencies:
        return fail(
            "Browser QA refused network-loaded or file:// dependencies: "
            + ", ".join(external_dependencies[:5])
            + ". Inline reviewed assets before executable browser inspection."
        )

    overflows: list[dict] = []
    console_errors: list[dict] = []
    navigation_modes: dict[str, str] = {}

    with sync_playwright() as playwright:
        launch_options = {"headless": True}
        launch_errors: list[str] = []
        browser = None
        for label, options in (
            ("playwright chromium", launch_options),
            ("Microsoft Edge", {**launch_options, "channel": "msedge"}),
            ("Google Chrome", {**launch_options, "channel": "chrome"}),
        ):
            try:
                browser = playwright.chromium.launch(**options)
                break
            except Exception as error:
                launch_errors.append(f"{label}: {error}")
        for executable in browser_executables():
            if browser is not None:
                break
            try:
                browser = playwright.chromium.launch(
                    **launch_options, executable_path=str(executable),
                )
            except Exception as error:
                launch_errors.append(f"{executable}: {error}")
        if browser is None:
            return fail(
                "Could not launch Chromium, Edge, or Chrome. Install a browser "
                "or run 'python -m playwright install chromium'.\n" +
                "\n".join(launch_errors)
            )
        for width, height in VIEWPORTS:
            viewport_name = f"{width}x{height}"
            page = browser.new_page(viewport={"width": width, "height": height})

            def on_console(message, viewport=viewport_name):
                if message.type == "error":
                    console_errors.append({
                        "viewport": viewport,
                        "type": message.type,
                        "text": message.text,
                    })

            def on_page_error(error, viewport=viewport_name):
                console_errors.append({
                    "viewport": viewport,
                    "type": "pageerror",
                    "text": str(error),
                })

            page.on("console", on_console)
            page.on("pageerror", on_page_error)

            try:
                page.goto(deck.as_uri(), wait_until="load")
                navigation_modes[viewport_name] = "file-url"
            except Exception as file_error:
                try:
                    page.close()
                    page = browser.new_page(viewport={"width": width, "height": height})
                    page.on("console", on_console)
                    page.on("pageerror", on_page_error)
                    page.set_content(
                        deck_text,
                        wait_until="load",
                    )
                    navigation_modes[viewport_name] = "inline-content-fallback"
                except Exception as content_error:
                    console_errors.append({
                        "viewport": viewport_name,
                        "type": "navigation",
                        "text": f"file navigation failed: {file_error}; set_content failed: {content_error}",
                    })
                    page.close()
                    continue

            selector = (
                ".slide"
                if page.locator(".slide").count()
                else ".reveal .slides section[id]"
            )
            count = page.locator(selector).count()

            for index in range(count):
                locator = page.locator(selector).nth(index)
                try:
                    locator.scroll_into_view_if_needed()
                    metrics = locator.evaluate(
                        """element => ({
                          id: element.id,
                          scrollWidth: element.scrollWidth,
                          clientWidth: element.clientWidth,
                          scrollHeight: element.scrollHeight,
                          clientHeight: element.clientHeight,
                          rect: element.getBoundingClientRect().toJSON()
                        })"""
                    )
                    overflow_x = metrics["scrollWidth"] > metrics["clientWidth"] + 2
                    overflow_y = metrics["scrollHeight"] > metrics["clientHeight"] + 2
                    if screenshots and args.capture_all:
                        target = screenshots / (
                            f"{viewport_name}-slide-{index + 1}.png"
                        )
                        try:
                            locator.screenshot(path=str(target))
                        except Exception:
                            page.screenshot(
                                path=str(target.with_name(target.stem + "-page.png")),
                                full_page=True,
                            )
                    if overflow_x or overflow_y:
                        item = {
                            "viewport": viewport_name,
                            "slide": index + 1,
                            "id": metrics["id"],
                            "overflow_x": overflow_x,
                            "overflow_y": overflow_y,
                            "metrics": metrics,
                        }
                        overflows.append(item)
                        if screenshots:
                            target = screenshots / (
                                f"{viewport_name}-slide-{index + 1}.png"
                            )
                            try:
                                locator.screenshot(path=str(target))
                            except Exception:
                                page.screenshot(
                                    path=str(target.with_name(target.stem + "-page.png")),
                                    full_page=True,
                                )
                except Exception as error:
                    overflows.append({
                        "viewport": viewport_name,
                        "slide": index + 1,
                        "error": str(error),
                    })
            page.close()
        browser.close()

    result = {
        "file": str(deck),
        "viewports": [f"{width}x{height}" for width, height in VIEWPORTS],
        "navigation_modes": navigation_modes,
        "limitations": (
            ["Inline-content fallback was used; relative media resolution was not verified."]
            if "inline-content-fallback" in navigation_modes.values() else []
        ),
        "overflow_findings": overflows,
        "console_errors": console_errors,
        "verdict": (
            "PASS"
            if not overflows and not console_errors
            else "REVISION_NEEDED"
        ),
    }
    result["report"] = str(report)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
