#!/usr/bin/env python3
"""Resolve append-only skill outputs inside the Ouroboros state directory."""
from __future__ import annotations

import hashlib
import os
import re
import uuid
from pathlib import Path


def _safe_job_name(value: str) -> str:
    raw = value.strip() or f"run-{uuid.uuid4().hex[:12]}"
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", raw).strip(".-") or "run"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
    return f"{slug[:72]}-{digest}"


def state_root() -> Path:
    value = os.environ.get("OUROBOROS_SKILL_STATE_DIR", "").strip()
    if not value:
        raise SystemExit(
            "OUROBOROS_SKILL_STATE_DIR is required. Run this script through "
            "Ouroboros skill_exec or set an isolated state directory for testing."
        )
    root = Path(value).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def job_output_dir(job_id: str) -> Path:
    root = state_root()
    output = root / "jobs" / _safe_job_name(job_id) / "output"
    output.mkdir(parents=True, exist_ok=True)
    return output


def require_state_input(value: str) -> Path:
    """Allow executable QA only for files already confined to this skill state."""
    root = state_root().resolve()
    target = Path(value).expanduser().resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise SystemExit(
            "Browser QA accepts only HTML artifacts inside this skill's "
            "Ouroboros state directory. Generate or safely stage the deck first."
        ) from exc
    return target


def output_path(job_id: str, relative_name: str) -> Path:
    """Return a new file path below jobs/<job>/output; never overwrite."""
    name = Path(relative_name)
    if name.is_absolute() or ".." in name.parts or not name.name:
        raise SystemExit("Output names must be relative and stay inside the job output directory.")
    base = job_output_dir(job_id).resolve()
    target = (base / name).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise SystemExit("Output path escapes the job output directory.") from exc
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise SystemExit(
            f"Refusing to overwrite existing artifact: {target}. "
            "Use a new --job-id or output name."
        )
    return target


def output_directory(job_id: str, relative_name: str) -> Path:
    """Return a new directory below jobs/<job>/output."""
    target = output_path(job_id, relative_name)
    target.mkdir(parents=True, exist_ok=False)
    return target
