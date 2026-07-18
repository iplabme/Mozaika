"""Mozaika scenario launcher extension.

Two host-rendered widgets enqueue an owner-visible command into the main
Ouroboros chat. The extension never runs a hidden pipeline: the core agent
decides routing, creates the foreground task/project, and applies normal safety,
planning, review, budget, and skill-readiness controls.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import datetime as dt
import hashlib
import hmac
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import unicodedata
from typing import Any, Dict

from starlette.requests import Request
from starlette.responses import JSONResponse


_MAX_FIELD_CHARS = 1200
_MAX_SOURCES = 50
_MAX_FILES = 500
_MAX_URL_CHARS = 4096
_MAX_RELATIVE_PATH_CHARS = 1024
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_UNSAFE_FILENAME = re.compile(r"[^0-9A-Za-zА-Яа-яЁё._ ()\[\]-]+")
_CYRILLIC = re.compile(r"[А-Яа-яЁё]")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_MAX_GATE_PAYLOAD_BYTES = 2 * 1024 * 1024
_MAX_BRANDBOOK_GATE_PAYLOAD_BYTES = 16 * 1024 * 1024
_MOZAIKA_BRANDBOOK_VERSION = "mozaika-brandbook/v1"
_SPEAKER_TEMPLATE_SHA256 = "6d9792d14d391165db9578c1c89b2b9b67a4dc62c24dcb6588286ab0f9e2d560"
_MOZAIKA_CORE_COLORS = {"#faf9f5", "#f0eee6", "#141413", "#5e5d59", "#388f76"}
_FORBIDDEN_RENDERER_COLORS = {"#0f0e17", "#1a1726", "#211e30", "#c93545", "#e85d6f"}
_PATH_SELECTION_TOKEN = re.compile(r"^[a-f0-9]{32}$")
_PRESET_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_CHOICE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
_CHOICE_OPTION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")
_TASK_PRESETS_PATH = pathlib.Path(__file__).resolve().parent / "config" / "task-presets.json"
_SUPPORTED_SCENARIOS = {"routine_report", "insight_deck", "weekly_autopilot"}
_CHOICE_CONTRACT_VERSION = "mozaika-live-owner-choice/v1"
_CHOICE_WAIT_DEFAULT_SEC = 1700
_CHOICE_WAIT_MAX_SEC = 1700
_CHOICE_PROGRESS_INTERVAL_SEC = 240
_MAX_CHOICE_ROUTE_BYTES = 64 * 1024
_PPTX_PROFILES = {
    "routine_report": {
        "style_preset": "mozaika-weekly",
        "reference_id": "scenario-2-sprint25-review-pptx",
        "reference_sha256": "d3a650c204ee9f9ea17daf94fae97a226e57ca13ecbbf7cf19e53f3e71969265",
        "reference_usage": "fixed-template",
    },
    "weekly_autopilot": {
        "style_preset": "mozaika-weekly",
        "reference_id": "scenario-2-sprint25-review-pptx",
        "reference_sha256": "d3a650c204ee9f9ea17daf94fae97a226e57ca13ecbbf7cf19e53f3e71969265",
        "reference_usage": "fixed-template",
    },
    "insight_deck": {
        "style_preset": "mozaika-insight",
        "reference_id": "scenario-insight-ds-role-analytics-pptx",
        "reference_sha256": "66430f7a96d66546eaa6c9fd8fad971e925a40c09ce2e2ae91047f16263a6c1d",
        "reference_usage": "visual-grammar-only",
    },
}


class PayloadTooLarge(ValueError):
    """Raised before an oversized widget payload is decoded or persisted."""


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _is_sha256(value: Any) -> bool:
    return bool(_SHA256.fullmatch(str(value or "")))


def _gate_result(gate: str, errors: list[str], warnings: list[str], **metrics: Any) -> Dict[str, Any]:
    return {
        "ok": not errors,
        "gate": gate,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }


def _normalize_verbatim(value: Any) -> str:
    """Normalize only Unicode composition and line endings for exact scope checks."""

    return unicodedata.normalize("NFC", str(value or "")).replace("\r\n", "\n").replace("\r", "\n")


def _comparison_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower().replace("ё", "е")
    return " ".join(re.sub(r"[^0-9a-zа-я]+", " ", text, flags=re.IGNORECASE).split())


def _token_similarity(left: Any, right: Any) -> float:
    left_tokens = set(_comparison_text(left).split())
    right_tokens = set(_comparison_text(right).split())
    if len(left_tokens) < 4 or len(right_tokens) < 4:
        return 0.0
    union = left_tokens | right_tokens
    return len(left_tokens & right_tokens) / len(union) if union else 0.0


def _validate_brandbook_conformance_gate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Inspect the actual owner-visible HTML instead of trusting a design receipt."""

    errors: list[str] = []
    warnings: list[str] = []
    artifact_type = str(payload.get("artifact_type") or "")
    artifact_id = str(payload.get("artifact_id") or "")
    html_source = payload.get("html_source")
    if artifact_type not in {"storytelling_cards", "selected_storytelling_card", "presentation", "speaker_story_cards"}:
        errors.append("brandbook conformance supports Mozaika cards, presentation, or speaker_story_cards")
    if not artifact_id:
        errors.append("artifact_id is required")
    if not isinstance(html_source, str) or not html_source.strip():
        errors.append("html_source must contain the complete owner-visible HTML")
        html_source = ""

    source_sha256 = hashlib.sha256(html_source.encode("utf-8")).hexdigest()
    claimed_sha256 = str(payload.get("html_sha256") or "")
    if not _is_sha256(claimed_sha256) or claimed_sha256 != source_sha256:
        errors.append("html_sha256 does not match the inspected HTML source")

    artifacts_payload = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    artifact_by_id = {
        str(item.get("artifact_id") or ""): item
        for item in artifacts_payload.get("artifacts", [])
        if isinstance(item, dict)
    }
    if artifacts_payload:
        artifact = artifact_by_id.get(artifact_id)
        if not artifact or artifact.get("sha256") != source_sha256:
            errors.append("inspected HTML does not match the current immutable artifact")

    normalized = html_source.lower()
    colors = {match.lower() for match in re.findall(r"#[0-9a-fA-F]{6}\b", html_source)}
    missing_core = sorted(_MOZAIKA_CORE_COLORS - colors)
    forbidden_hits = sorted(_FORBIDDEN_RENDERER_COLORS & colors)
    brandbook_marker = 'data-mozaika-brandbook="mozaika-brandbook/v1"' in normalized
    if not brandbook_marker:
        errors.append("HTML is missing the exact Mozaika brandbook marker")
    if missing_core:
        errors.append("HTML is missing required Mozaika core colors: " + ", ".join(missing_core))
    if forbidden_hits:
        errors.append("HTML contains a forbidden renderer palette: " + ", ".join(forbidden_hits))
    if re.search(r"color-scheme\s*:\s*dark\b", normalized):
        errors.append("dark color-scheme is forbidden for Mozaika owner artifacts")

    root_blocks = re.findall(r":root\s*\{(.*?)\}", normalized, flags=re.DOTALL)
    root_css = "\n".join(root_blocks)
    warm_root = bool(re.search(r"--(?:mozaika-)?(?:bg|canvas)\s*:\s*#faf9f5\b", root_css))
    ink_root = bool(re.search(r"--(?:mozaika-)?(?:text|ink)\s*:\s*#141413\b", root_css))
    accent_root = bool(re.search(r"--(?:mozaika-)?(?:accent|focus|green-700)\s*:\s*#388f76\b", root_css))
    if not warm_root or not ink_root or not accent_root:
        errors.append("root design tokens do not resolve to the Mozaika warm canvas, ink and green accent")

    template_required = artifact_type == "speaker_story_cards"
    template_exact = True
    if artifact_type == "presentation":
        if 'data-mozaika-theme="mozaika-reference"' not in normalized:
            errors.append("presentation is missing data-mozaika-theme=mozaika-reference")
        if "prefers-reduced-motion" not in normalized:
            errors.append("presentation is missing the reduced-motion fallback")
    elif artifact_type == "speaker_story_cards":
        template_sha256 = str(payload.get("template_sha256") or "")
        template_exact = template_sha256 == _SPEAKER_TEMPLATE_SHA256
        if not template_exact:
            errors.append("speaker cards do not reference the current mandatory brandbook template")
        required_fragments = (
            'data-mozaika-surface="speaker-story-cards"',
            'data-mozaika-template="speaker-story-cards/v1"',
            'id="viewport"', 'id="prev"', 'id="next"', 'id="dots"',
            "prefers-reduced-motion", "@media print", "touchstart", "keydown",
        )
        missing_fragments = [item for item in required_fragments if item not in normalized]
        if missing_fragments:
            errors.append("speaker cards are not derived from the mandatory interaction template")

    return _gate_result(
        "brandbook_conformance",
        errors,
        warnings,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        html_sha256=source_sha256,
        source_checked=bool(html_source),
        brandbook_version=_MOZAIKA_BRANDBOOK_VERSION,
        brandbook_marker=brandbook_marker,
        core_palette_exact=not missing_core and warm_root and ink_root and accent_root,
        forbidden_color_hits=len(forbidden_hits),
        template_required=template_required,
        template_exact=template_exact,
        template_sha256=_SPEAKER_TEMPLATE_SHA256 if template_required else None,
    )


def _duplicate_copy(left: Any, right: Any) -> bool:
    first = _comparison_text(left)
    second = _comparison_text(right)
    if not first or not second:
        return False
    if first == second:
        return True
    shorter, longer = sorted((first, second), key=len)
    if len(shorter) >= 24 and shorter in longer and len(shorter) / len(longer) >= 0.72:
        return True
    return _token_similarity(first, second) >= 0.82


def _validate_research_brief_gate(payload: Dict[str, Any]) -> Dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if payload.get("contract_version") != "mozaika-research-brief/v1":
        errors.append("contract_version must be mozaika-research-brief/v1")
    if payload.get("scenario") not in _SUPPORTED_SCENARIOS:
        errors.append("scenario is invalid")
    if not str(payload.get("run_id") or "").strip():
        errors.append("run_id is required")
    if not str(payload.get("assignment_artifact_id") or "").strip() or not _is_sha256(payload.get("assignment_sha256")):
        errors.append("assignment artifact id and SHA-256 are required")
    if payload.get("comparison_normalization") != "unicode-nfc-lf-v1":
        errors.append("comparison_normalization must be unicode-nfc-lf-v1")
    requirements = payload.get("requirements")
    if not isinstance(requirements, list):
        errors.append("requirements must be an array")
        requirements = []
    if payload.get("scenario") == "insight_deck" and not requirements:
        errors.append("insight_deck requires at least one frozen requirement")
    ids: list[str] = []
    texts: list[str] = []
    data_required = constraints = 0
    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, dict):
            errors.append(f"requirements[{index}] must be an object")
            continue
        requirement_id = str(requirement.get("requirement_id") or "").strip()
        text_verbatim = _normalize_verbatim(requirement.get("text_verbatim"))
        category = requirement.get("category")
        if not re.fullmatch(r"req-[a-z0-9][a-z0-9_-]{0,63}", requirement_id):
            errors.append(f"requirements[{index}].requirement_id is invalid")
        if not text_verbatim.strip():
            errors.append(f"requirements[{index}].text_verbatim is required")
        if category not in {"research_question", "requested_slice", "requested_section", "named_output", "constraint"}:
            errors.append(f"requirements[{index}].category is invalid")
        surfaces = requirement.get("required_surfaces")
        if not isinstance(surfaces, list) or not surfaces:
            errors.append(f"requirements[{index}].required_surfaces must be non-empty")
        elif len(surfaces) != len(set(str(item) for item in surfaces)):
            errors.append(f"requirements[{index}].required_surfaces must be unique")
        if category == "constraint":
            constraints += 1
            if requirement.get("data_stage_required") is not False:
                errors.append(f"requirements[{index}] constraint must set data_stage_required=false")
        elif requirement.get("data_stage_required") is True:
            data_required += 1
        ids.append(requirement_id)
        texts.append(text_verbatim)
    if len(ids) != len(set(ids)):
        errors.append("requirement_id values must be unique")
    if len(texts) != len(set(texts)):
        errors.append("text_verbatim requirements must be unique")
    protected = payload.get("protected_verbatim")
    if not isinstance(protected, list):
        errors.append("protected_verbatim must be an array")
        protected = []
    protected_normalized = {_normalize_verbatim(item) for item in protected}
    expected_protected = set(texts)
    for field in ("research_title_verbatim", "main_question_verbatim"):
        if payload.get(field) is not None:
            expected_protected.add(_normalize_verbatim(payload.get(field)))
    missing_protected = sorted(expected_protected - protected_normalized)
    if missing_protected:
        errors.append("protected_verbatim is missing frozen owner text")
    return _gate_result(
        "research_brief",
        errors,
        warnings,
        requirement_count=len(requirements),
        data_requirement_count=data_required,
        constraint_count=constraints,
    )


def _validate_requirement_claim_map_gate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate exact traceability from frozen owner requirements to evidence-backed claims."""

    errors: list[str] = []
    warnings: list[str] = []
    mapping = payload.get("mapping") if isinstance(payload.get("mapping"), dict) else {}
    brief = payload.get("research_brief") if isinstance(payload.get("research_brief"), dict) else {}
    claims_payload = payload.get("claims") if isinstance(payload.get("claims"), dict) else {}
    artifacts_payload = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    brief_result = _validate_research_brief_gate(brief)
    errors.extend(f"research_brief: {item}" for item in brief_result["errors"])
    if mapping.get("contract_version") != "mozaika-requirement-claim-map/v1":
        errors.append("mapping contract_version is invalid")
    if not _is_sha256(mapping.get("research_brief_sha256")):
        errors.append("mapping research_brief_sha256 is invalid")
    if mapping.get("run_id") != brief.get("run_id"):
        errors.append("mapping run_id must match research brief")
    claim_ids = {
        str(item.get("claim_id") or "")
        for item in claims_payload.get("claims", [])
        if isinstance(item, dict)
    }
    artifact_ids = {
        str(item.get("artifact_id") or "")
        for item in artifacts_payload.get("artifacts", [])
        if isinstance(item, dict)
    }
    requirements = {
        str(item.get("requirement_id") or ""): item
        for item in brief.get("requirements", [])
        if isinstance(item, dict)
    }
    required_data_ids = {
        requirement_id
        for requirement_id, item in requirements.items()
        if item.get("category") != "constraint" and item.get("data_stage_required") is True
    }
    required_constraint_ids = {
        requirement_id
        for requirement_id, item in requirements.items()
        if item.get("category") == "constraint"
    }
    entries = mapping.get("entries")
    if not isinstance(entries, list):
        errors.append("mapping.entries must be an array")
        entries = []
    entry_ids: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"mapping.entries[{index}] must be an object")
            continue
        requirement_id = str(entry.get("requirement_id") or "")
        entry_ids.append(requirement_id)
        requirement = requirements.get(requirement_id)
        if not requirement or requirement_id not in required_data_ids:
            errors.append(f"mapping.entries[{index}] references a non-data requirement")
            continue
        if _normalize_verbatim(entry.get("text_verbatim")) != _normalize_verbatim(requirement.get("text_verbatim")):
            errors.append(f"mapping.entries[{index}] rewrites owner text")
        status = entry.get("status")
        if status not in {"answered", "partial", "unanswered", "not_applicable"}:
            errors.append(f"mapping.entries[{index}].status is invalid")
        entry_claims = entry.get("claim_ids")
        evidence_ids = entry.get("evidence_artifact_ids")
        if not isinstance(entry_claims, list) or set(str(item) for item in entry_claims) - claim_ids:
            errors.append(f"mapping.entries[{index}] references missing claims")
        if not isinstance(evidence_ids, list) or set(str(item) for item in evidence_ids) - artifact_ids:
            errors.append(f"mapping.entries[{index}] references missing evidence artifacts")
        if status == "answered" and (not entry_claims or not evidence_ids or entry.get("reason") is not None):
            errors.append(f"mapping.entries[{index}] answered status requires claims, evidence and null reason")
        if status in {"partial", "unanswered", "not_applicable"} and not str(entry.get("reason") or "").strip():
            errors.append(f"mapping.entries[{index}] non-answered status requires a reason")
        if status in {"partial", "unanswered"} and requirement.get("partial_answer_allowed") is not True:
            warnings.append(f"mapping.entries[{index}] could not fully answer a mandatory requirement")
    if len(entry_ids) != len(set(entry_ids)) or set(entry_ids) != required_data_ids:
        errors.append("mapping.entries must exactly cover every frozen data requirement once")
    constraints = mapping.get("global_constraints")
    if not isinstance(constraints, list):
        errors.append("mapping.global_constraints must be an array")
        constraints = []
    constraint_ids: list[str] = []
    for index, entry in enumerate(constraints):
        if not isinstance(entry, dict):
            errors.append(f"mapping.global_constraints[{index}] must be an object")
            continue
        requirement_id = str(entry.get("requirement_id") or "")
        constraint_ids.append(requirement_id)
        requirement = requirements.get(requirement_id)
        if not requirement or requirement_id not in required_constraint_ids:
            errors.append(f"mapping.global_constraints[{index}] references a non-constraint requirement")
            continue
        if _normalize_verbatim(entry.get("text_verbatim")) != _normalize_verbatim(requirement.get("text_verbatim")):
            errors.append(f"mapping.global_constraints[{index}] rewrites owner text")
        if entry.get("applied_global") is not True or not entry.get("checked_surfaces"):
            errors.append(f"mapping.global_constraints[{index}] must be applied globally")
    if len(constraint_ids) != len(set(constraint_ids)) or set(constraint_ids) != required_constraint_ids:
        errors.append("mapping.global_constraints must exactly cover every frozen constraint once")
    return _gate_result(
        "requirement_claim_map",
        errors,
        warnings,
        data_requirement_count=len(required_data_ids),
        constraint_count=len(required_constraint_ids),
        claim_count=len(claim_ids),
    )


def _validate_narrative_integrity_gate(payload: Dict[str, Any]) -> Dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    audit = payload.get("audit") if isinstance(payload.get("audit"), dict) else {}
    brief = payload.get("research_brief") if isinstance(payload.get("research_brief"), dict) else {}
    brief_result = _validate_research_brief_gate(brief)
    errors.extend(f"research_brief: {item}" for item in brief_result["errors"])
    if audit.get("contract_version") != "mozaika-narrative-integrity-audit/v1":
        errors.append("audit contract_version is invalid")
    if audit.get("algorithm") != "mozaika-narrative-integrity-v1":
        errors.append("audit algorithm is invalid")
    if audit.get("status") != "pass":
        errors.append("narrative integrity audit did not pass")
    if not _is_sha256(audit.get("artifact_sha256")) or not _is_sha256(audit.get("research_brief_sha256")):
        errors.append("audit hashes are invalid")
    checks = audit.get("checks") if isinstance(audit.get("checks"), dict) else {}
    required_checks = {
        "verbatim_scope_complete", "no_exact_duplicates", "no_high_confidence_near_duplicates",
        "claim_links_valid", "selected_story_preserved", "screen_mapping_valid",
    }
    if any(checks.get(name) is not True for name in required_checks):
        errors.append("narrative integrity checks did not all pass")
    findings = audit.get("duplicate_findings")
    if findings != []:
        errors.append("duplicate_findings must be empty for pass")
    coverage = audit.get("coverage")
    if not isinstance(coverage, list):
        errors.append("coverage must be an array")
        coverage = []
    surface_name = {
        "storytelling_cards": "cards",
        "selected_storytelling_card": "cards",
        "storyline": "storyline",
        "presentation": "presentation",
        "speaker_story_cards": "presentation",
    }.get(str(audit.get("artifact_type") or ""), "")
    required = {
        str(item.get("requirement_id") or "")
        for item in brief.get("requirements", [])
        if isinstance(item, dict) and surface_name in item.get("required_surfaces", [])
    }
    actual = {str(item.get("requirement_id") or "") for item in coverage if isinstance(item, dict)}
    if required != actual:
        errors.append("audit coverage does not exactly match required surface scope")
    return _gate_result(
        "narrative_integrity",
        errors,
        warnings,
        required_count=len(required),
        covered_count=len(actual),
        artifact_type=audit.get("artifact_type"),
    )


def _validate_owner_decision_gate(payload: Dict[str, Any]) -> Dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checkpoint = payload.get("checkpoint") if isinstance(payload.get("checkpoint"), dict) else {}
    artifacts_payload = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    expected_state = str(payload.get("expected_state") or "").strip()
    if checkpoint.get("contract_version") != "mozaika-owner-decision-checkpoint/v1":
        errors.append("checkpoint contract_version is invalid")
    state = checkpoint.get("state")
    if state not in {"pending", "selected", "superseded", "dismissed"}:
        errors.append("checkpoint state is invalid")
    if expected_state and state != expected_state:
        errors.append(f"checkpoint state must be {expected_state}")
    discovery = checkpoint.get("discovery") if isinstance(checkpoint.get("discovery"), dict) else {}
    if discovery.get("priority") != ["explicit_run_id", "single_pending_in_chat_scope", "ask_owner"]:
        errors.append("checkpoint discovery priority is invalid")
    options = checkpoint.get("candidate_options")
    if not isinstance(options, list) or not 2 <= len(options) <= 3:
        errors.append("checkpoint candidate_options must contain two or three options")
        options = []
    option_ids = [str(item.get("option_id") or "") for item in options if isinstance(item, dict)]
    if len(option_ids) != len(set(option_ids)) or any(not item for item in option_ids):
        errors.append("checkpoint option ids must be non-empty and unique")
    if state in {"selected", "superseded"} and checkpoint.get("selected_option_id") not in option_ids:
        errors.append("selected_option_id must reference a candidate option")
    if state == "pending" and any(checkpoint.get(name) is not None for name in ("selected_option_id", "selected_card_ref", "superseded_by_checkpoint_id", "dismissal_reason")):
        errors.append("pending checkpoint contains terminal fields")
    if state == "selected" and (not checkpoint.get("selected_card_ref") or not checkpoint.get("owner_message_artifact_id")):
        errors.append("selected checkpoint requires selected card and owner message")
    if state == "superseded" and not checkpoint.get("superseded_by_checkpoint_id"):
        errors.append("superseded checkpoint requires successor id")
    if state == "dismissed" and not str(checkpoint.get("dismissal_reason") or "").strip():
        errors.append("dismissed checkpoint requires a reason")
    artifact_by_id = {
        str(item.get("artifact_id") or ""): item
        for item in artifacts_payload.get("artifacts", [])
        if isinstance(item, dict)
    }
    ref_names = ["assignment_ref", "research_brief_ref", "dashboard_ref", "owner_choice_ref", "cards_ref"]
    if state in {"selected", "superseded"}:
        ref_names.append("selected_card_ref")
    for name in ref_names:
        ref = checkpoint.get(name) if isinstance(checkpoint.get(name), dict) else {}
        artifact = artifact_by_id.get(str(ref.get("artifact_id") or ""))
        if not artifact:
            errors.append(f"{name} does not resolve in artifact index")
        elif ref.get("sha256") != artifact.get("sha256") or ref.get("uri") != artifact.get("uri"):
            errors.append(f"{name} does not match durable artifact metadata")
    stale = False
    try:
        stale_after = dt.datetime.fromisoformat(str(checkpoint.get("stale_after") or "").replace("Z", "+00:00"))
        stale = dt.datetime.now(dt.timezone.utc) > stale_after.astimezone(dt.timezone.utc)
    except (TypeError, ValueError):
        errors.append("stale_after must be an ISO date-time")
    if state == "pending" and stale and payload.get("owner_reconfirmed_stale") is not True:
        warnings.append("pending checkpoint is stale and requires owner reconfirmation")
    return _gate_result(
        "owner_decision",
        errors,
        warnings,
        state=state,
        stale=stale,
        continuation_eligible=not errors and state == "selected",
        publication_eligible=not errors and state == "pending" and (not stale or payload.get("owner_reconfirmed_stale") is True),
    )


def _validate_scope_gate(payload: Dict[str, Any]) -> Dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if payload.get("contract_version") != "mozaika-scope-ledger/v1":
        errors.append("contract_version must be mozaika-scope-ledger/v1")
    source_kind = payload.get("source_kind")
    if source_kind not in {"single", "collection"}:
        errors.append("source_kind must be single or collection")
    requested_mode = payload.get("requested_mode")
    if requested_mode not in {"all", "selected"}:
        errors.append("requested_mode must be all or selected")

    items = payload.get("items")
    if not isinstance(items, list) or not items:
        errors.append("items must be a non-empty array")
        items = []
    ids: list[str] = []
    analyzed = excluded = blocked = 0
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"items[{index}] must be an object")
            continue
        source_id = str(item.get("source_id") or "").strip()
        if not source_id:
            errors.append(f"items[{index}].source_id is required")
        ids.append(source_id)
        disposition = item.get("disposition")
        if disposition == "analyzed":
            analyzed += 1
            if not item.get("artifact_ids"):
                errors.append(f"items[{index}] analyzed without artifact_ids")
        elif disposition == "owner_excluded":
            excluded += 1
            if not str(item.get("reason") or "").strip() or not str(item.get("decision_id") or "").strip():
                errors.append(f"items[{index}] owner_excluded requires reason and decision_id")
        elif disposition == "blocked":
            blocked += 1
            if not str(item.get("reason") or "").strip():
                errors.append(f"items[{index}] blocked requires reason")
        else:
            errors.append(f"items[{index}].disposition is invalid")
    if len(ids) != len(set(ids)):
        errors.append("source_id values must be unique")
    if source_kind == "collection" and not payload.get("enumeration_artifact_ids"):
        errors.append("collection scope requires enumeration_artifact_ids")

    total = len(items)
    terminal = analyzed + excluded + blocked
    all_analyzed = total > 0 and analyzed == total
    terminal_complete = total > 0 and terminal == total
    scope_change_approved = bool(payload.get("scope_change_approved"))
    solved_coverage = all_analyzed or (
        terminal_complete and blocked == 0 and excluded > 0 and scope_change_approved
    )
    declared = payload.get("coverage")
    expected = {
        "total": total,
        "analyzed": analyzed,
        "owner_excluded": excluded,
        "blocked": blocked,
        "all_analyzed": all_analyzed,
        "terminal_complete": terminal_complete,
        "solved_coverage": solved_coverage,
    }
    if declared != expected:
        errors.append("coverage does not match recomputed item dispositions")
    if requested_mode == "all" and not solved_coverage:
        warnings.append("requested all sources, but coverage is not solved")
    return _gate_result(
        "scope",
        errors,
        warnings,
        **expected,
        requested_mode=requested_mode,
        source_kind=source_kind,
    )


def _calculated_value(check: Dict[str, Any]) -> float:
    operator = check.get("operator")
    left = float(check.get("left"))
    right = float(check.get("right"))
    if operator == "ratio_pct":
        if right == 0:
            raise ValueError("ratio_pct denominator is zero")
        return left / right * 100.0
    if operator == "ratio":
        if right == 0:
            raise ValueError("ratio denominator is zero")
        return left / right
    if operator == "difference":
        return left - right
    if operator == "sum":
        return left + right
    if operator == "equals":
        return left
    raise ValueError("unsupported calculation operator")


def _validate_claim_gate(payload: Dict[str, Any]) -> Dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if payload.get("contract_version") != "mozaika-claim-registry/v1":
        errors.append("contract_version must be mozaika-claim-registry/v1")
    if not _is_sha256(payload.get("scope_ledger_sha256")):
        errors.append("scope_ledger_sha256 must be a SHA-256")
    language = str(payload.get("output_language") or "").strip()
    if not language:
        errors.append("output_language is required")

    claims = payload.get("claims")
    if not isinstance(claims, list) or not claims:
        errors.append("claims must be a non-empty array")
        claims = []
    claim_ids: list[str] = []
    invalid_claims = 0
    for index, claim in enumerate(claims):
        claim_errors: list[str] = []
        if not isinstance(claim, dict):
            errors.append(f"claims[{index}] must be an object")
            invalid_claims += 1
            continue
        claim_id = str(claim.get("claim_id") or "").strip()
        claim_ids.append(claim_id)
        if not claim_id:
            claim_errors.append("claim_id is required")
        if not str(claim.get("text") or "").strip():
            claim_errors.append("text is required")
        kind = claim.get("kind")
        if kind not in {"observed", "calculated", "inference", "hypothesis", "recommendation"}:
            claim_errors.append("kind is invalid")
        evidence_ids = claim.get("evidence_artifact_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            claim_errors.append("evidence_artifact_ids must be non-empty")
        if kind in {"inference", "hypothesis", "recommendation"} and not str(claim.get("qualifier") or "").strip():
            claim_errors.append("interpretive claims require qualifier")
        checks = claim.get("checks", [])
        quantitative = claim.get("quantitative")
        entity_sensitive = claim.get("entity_sensitive")
        if not isinstance(quantitative, bool) or not isinstance(entity_sensitive, bool):
            claim_errors.append("quantitative and entity_sensitive must be booleans")
        if (kind == "calculated" or quantitative is True) and not checks:
            claim_errors.append("calculated or quantitative claims require checks")
        if not isinstance(checks, list):
            claim_errors.append("checks must be an array")
            checks = []
        for check_index, check in enumerate(checks):
            if not isinstance(check, dict):
                claim_errors.append(f"checks[{check_index}] must be an object")
                continue
            try:
                calculated = _calculated_value(check)
                claimed = float(check.get("claimed_value"))
                tolerance = float(check.get("tolerance", 0.0))
                if tolerance < 0 or not math.isfinite(tolerance):
                    raise ValueError("invalid tolerance")
                if not math.isfinite(calculated) or not math.isfinite(claimed):
                    raise ValueError("non-finite value")
                if abs(calculated - claimed) > tolerance:
                    claim_errors.append(
                        f"checks[{check_index}] claimed_value={claimed} does not match {calculated}"
                    )
            except (TypeError, ValueError) as exc:
                claim_errors.append(f"checks[{check_index}] invalid: {exc}")
        text_checks = claim.get("text_checks", [])
        if not isinstance(text_checks, list):
            claim_errors.append("text_checks must be an array")
            text_checks = []
        if entity_sensitive is True and not text_checks:
            claim_errors.append("entity_sensitive claims require text_checks")
        for check_index, check in enumerate(text_checks):
            if not isinstance(check, dict):
                claim_errors.append(f"text_checks[{check_index}] must be an object")
                continue
            actual = str(check.get("actual") or "")
            claimed = str(check.get("claimed") or "")
            if not actual or not claimed:
                claim_errors.append(f"text_checks[{check_index}] actual and claimed are required")
                continue
            if check.get("case_sensitive") is False:
                actual = actual.casefold()
                claimed = claimed.casefold()
            if actual != claimed:
                claim_errors.append(f"text_checks[{check_index}] claimed entity does not match evidence")
        expected_status = "verified" if kind in {"observed", "calculated"} else "qualified"
        if claim.get("status") != expected_status:
            claim_errors.append(f"status must be {expected_status} for kind={kind}")
        if claim_errors:
            invalid_claims += 1
            errors.extend(f"claims[{index}]: {message}" for message in claim_errors)
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("claim_id values must be unique")
    eligible = bool(claims) and invalid_claims == 0
    return _gate_result(
        "claims",
        errors,
        warnings,
        total_claims=len(claims),
        invalid_claims=invalid_claims,
        owner_choice_eligible=eligible,
        presentation_eligible=eligible,
        output_language=language,
    )


def _validate_artifact_gate(payload: Dict[str, Any]) -> Dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if payload.get("contract_version") != "mozaika-artifact-index/v1":
        errors.append("contract_version must be mozaika-artifact-index/v1")
    policy = payload.get("policy")
    if policy != {
        "mode": "append_only",
        "preserve_user_inputs": True,
        "preserve_stage_outputs": True,
        "allow_delete": False,
    }:
        errors.append("artifact policy must be append-only and deletion-disabled")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("artifacts must be a non-empty array")
        artifacts = []
    artifact_ids: list[str] = []
    durable_count = 0
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            errors.append(f"artifacts[{index}] must be an object")
            continue
        artifact_id = str(artifact.get("artifact_id") or "").strip()
        artifact_ids.append(artifact_id)
        if not artifact_id:
            errors.append(f"artifacts[{index}].artifact_id is required")
        if not str(artifact.get("uri") or "").strip():
            errors.append(f"artifacts[{index}].uri is required")
        if not _is_sha256(artifact.get("sha256")):
            errors.append(f"artifacts[{index}].sha256 is invalid")
        if not str(artifact.get("created_at") or "").strip():
            errors.append(f"artifacts[{index}].created_at is required")
        if artifact.get("preserved") is not True or artifact.get("immutable") is not True:
            errors.append(f"artifacts[{index}] must be preserved and immutable")
        if artifact.get("durable") is True:
            durable_count += 1
        else:
            errors.append(f"artifacts[{index}] has no durable copy")
        if artifact.get("kind") == "user_input" and not str(artifact.get("original_name") or "").strip():
            errors.append(f"artifacts[{index}] user_input requires original_name")
    if len(artifact_ids) != len(set(artifact_ids)):
        errors.append("artifact_id values must be unique")
    required_ids = payload.get("required_artifact_ids", [])
    if not isinstance(required_ids, list):
        errors.append("required_artifact_ids must be an array")
        required_ids = []
    missing = sorted(set(str(item) for item in required_ids) - set(artifact_ids))
    if missing:
        errors.append("required artifacts are missing: " + ", ".join(missing))
    return _gate_result(
        "artifacts",
        errors,
        warnings,
        artifact_count=len(artifacts),
        durable_count=durable_count,
        required_count=len(required_ids),
        append_only=True,
    )


def _validate_owner_choice_gate(payload: Dict[str, Any]) -> Dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    choice = payload.get("choice") if isinstance(payload.get("choice"), dict) else {}
    claims_payload = payload.get("claims") if isinstance(payload.get("claims"), dict) else {}
    artifacts_payload = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    claims_result = _validate_claim_gate(claims_payload)
    artifacts_result = _validate_artifact_gate(artifacts_payload)
    errors.extend(f"claims: {item}" for item in claims_result["errors"])
    errors.extend(f"artifacts: {item}" for item in artifacts_result["errors"])
    if choice.get("contract_version") != "mozaika-owner-choice/v1":
        errors.append("choice.contract_version must be mozaika-owner-choice/v1")
    if choice.get("visual_preview_required") is not True:
        errors.append("visual_preview_required must be true")
    if choice.get("owner_surface_format") != "html":
        errors.append("owner_surface_format must be html")
    if choice.get("output_language") != claims_payload.get("output_language"):
        errors.append("choice output_language must match claim registry")
    options = choice.get("options")
    if not isinstance(options, list) or not 2 <= len(options) <= 3:
        errors.append("choice must contain two or three options")
        options = []
    claim_ids = {
        str(item.get("claim_id") or "")
        for item in claims_payload.get("claims", [])
        if isinstance(item, dict)
    }
    artifact_by_id = {
        str(item.get("artifact_id") or ""): item
        for item in artifacts_payload.get("artifacts", [])
        if isinstance(item, dict)
    }
    brief = payload.get("research_brief") if isinstance(payload.get("research_brief"), dict) else {}
    new_choice_mode = bool(brief) or any(
        choice.get(name) is not None
        for name in (
            "research_brief_sha256",
            "required_requirement_ids",
            "narrative_integrity_audit_artifact_id",
            "checkpoint_artifact_id",
        )
    )
    required_by_id: dict[str, Dict[str, Any]] = {}
    if new_choice_mode:
        brief_result = _validate_research_brief_gate(brief)
        errors.extend(f"research_brief: {item}" for item in brief_result["errors"])
        if not _is_sha256(choice.get("research_brief_sha256")):
            errors.append("choice.research_brief_sha256 is required for frozen-scope choice")
        required_by_id = {
            str(item.get("requirement_id") or ""): item
            for item in brief.get("requirements", [])
            if isinstance(item, dict) and "cards" in item.get("required_surfaces", [])
        }
        declared_required = choice.get("required_requirement_ids")
        if not isinstance(declared_required, list) or set(str(item) for item in declared_required) != set(required_by_id):
            errors.append("choice.required_requirement_ids must exactly match card requirements from research brief")
        for field_name in ("narrative_integrity_audit_artifact_id", "checkpoint_artifact_id"):
            artifact_id = str(choice.get(field_name) or "").strip()
            if not artifact_id or artifact_id not in artifact_by_id:
                errors.append(f"choice.{field_name} must resolve in artifact index")
        audit_payload = payload.get("narrative_integrity")
        if not isinstance(audit_payload, dict):
            errors.append("frozen-scope choice requires narrative_integrity payload")
        else:
            integrity_result = _validate_narrative_integrity_gate({
                "audit": audit_payload,
                "research_brief": brief,
            })
            errors.extend(f"narrative_integrity: {item}" for item in integrity_result["errors"])
        checkpoint_payload = payload.get("checkpoint")
        if not isinstance(checkpoint_payload, dict):
            errors.append("frozen-scope choice requires pending checkpoint payload")
        else:
            checkpoint_result = _validate_owner_decision_gate({
                "checkpoint": checkpoint_payload,
                "artifacts": artifacts_payload,
                "expected_state": "pending",
                "owner_reconfirmed_stale": payload.get("owner_reconfirmed_stale") is True,
            })
            errors.extend(f"checkpoint: {item}" for item in checkpoint_result["errors"])
    dashboard_surface_id = str(choice.get("dashboard_surface_artifact_id") or "").strip()
    dashboard_surface = artifact_by_id.get(dashboard_surface_id)
    if not dashboard_surface:
        errors.append("owner dashboard HTML artifact is missing")
    elif (
        dashboard_surface.get("kind") != "dashboard"
        or dashboard_surface.get("durable") is not True
        or dashboard_surface.get("owner_visible") is not True
        or dashboard_surface.get("media_type") != "text/html"
        or dashboard_surface.get("schema") != "dashboard-html-without-storytelling-cards/v1"
    ):
        errors.append("dashboard surface must be a durable owner-visible HTML artifact without storytelling cards")
    owner_surface_id = str(choice.get("owner_surface_artifact_id") or "").strip()
    owner_surface = artifact_by_id.get(owner_surface_id)
    if not owner_surface:
        errors.append("owner HTML surface artifact is missing")
    elif (
        owner_surface.get("kind") != "owner_choice_preview"
        or owner_surface.get("durable") is not True
        or owner_surface.get("owner_visible") is not True
        or owner_surface.get("media_type") != "text/html"
        or owner_surface.get("schema") != "owner-choice-cards-html/v1"
    ):
        errors.append("owner surface must be a durable owner-visible storytelling-cards HTML artifact")
    for index, claim in enumerate(claims_payload.get("claims", [])):
        if not isinstance(claim, dict):
            continue
        missing_evidence = sorted(
            set(str(item) for item in claim.get("evidence_artifact_ids", [])) - set(artifact_by_id)
        )
        if missing_evidence:
            errors.append(f"claims[{index}] evidence artifacts are missing: {', '.join(missing_evidence)}")
    option_ids: list[str] = []
    html_anchors: list[str] = []
    grouping_principles: list[str] = []
    governing_thoughts: list[str] = []
    for index, option in enumerate(options):
        if not isinstance(option, dict):
            errors.append(f"options[{index}] must be an object")
            continue
        option_id = str(option.get("option_id") or "").strip()
        option_ids.append(option_id)
        grouping_principles.append(str(option.get("grouping_principle") or "").strip())
        governing_thoughts.append(str(option.get("governing_thought") or "").strip())
        if not option_id:
            errors.append(f"options[{index}].option_id is required")
        used_claims = option.get("claim_ids")
        if not isinstance(used_claims, list) or not used_claims:
            errors.append(f"options[{index}].claim_ids must be non-empty")
        else:
            unknown_claims = sorted(set(str(item) for item in used_claims) - claim_ids)
            if unknown_claims:
                errors.append(f"options[{index}] references unknown claims: {', '.join(unknown_claims)}")
        card = option.get("card")
        if not isinstance(card, dict):
            errors.append(f"options[{index}].card is required")
            card = {}
        for field_name in (
            "headline",
            "core_message",
            "why_it_matters",
            "executive_takeaway",
            "visual_style",
            "preview_alt_text",
        ):
            if not str(card.get(field_name) or "").strip():
                errors.append(f"options[{index}].card.{field_name} is required")
        if card.get("language") != choice.get("output_language"):
            errors.append(f"options[{index}].card.language must match choice output_language")
        if _duplicate_copy(card.get("headline"), card.get("core_message")):
            errors.append(f"options[{index}].card headline and core_message repeat one formulation")
        beats = card.get("story_beats")
        if not isinstance(beats, list) or not 3 <= len(beats) <= 5:
            errors.append(f"options[{index}].card.story_beats must contain three to five items")
            beats = []
        sequences: list[int] = []
        option_claim_ids = set(str(item) for item in used_claims) if isinstance(used_claims, list) else set()
        for beat_index, beat in enumerate(beats):
            if not isinstance(beat, dict):
                errors.append(f"options[{index}].card.story_beats[{beat_index}] must be an object")
                continue
            sequences.append(beat.get("sequence"))
            for field_name in ("title", "message", "visual_hint"):
                if not str(beat.get(field_name) or "").strip():
                    errors.append(
                        f"options[{index}].card.story_beats[{beat_index}].{field_name} is required"
                    )
            if _duplicate_copy(beat.get("title"), beat.get("message")):
                errors.append(f"options[{index}].card.story_beats[{beat_index}] title and message repeat one formulation")
            if beat_index > 0 and isinstance(beats[beat_index - 1], dict):
                previous = beats[beat_index - 1]
                if _duplicate_copy(
                    f"{previous.get('title', '')} {previous.get('message', '')}",
                    f"{beat.get('title', '')} {beat.get('message', '')}",
                ):
                    errors.append(f"options[{index}].card.story_beats[{beat_index - 1}] and [{beat_index}] repeat one formulation")
            beat_claims = beat.get("claim_ids")
            if not isinstance(beat_claims, list) or not beat_claims:
                errors.append(
                    f"options[{index}].card.story_beats[{beat_index}].claim_ids must be non-empty"
                )
            else:
                outside_option = sorted(set(str(item) for item in beat_claims) - option_claim_ids)
                if outside_option:
                    errors.append(
                        f"options[{index}].card.story_beats[{beat_index}] references claims outside the option: "
                        + ", ".join(outside_option)
                    )
        if beats and sequences != list(range(1, len(beats) + 1)):
            errors.append(f"options[{index}].card.story_beats sequence must start at one and be contiguous")
        if new_choice_mode:
            coverage = option.get("requirements_coverage")
            if not isinstance(coverage, list):
                errors.append(f"options[{index}].requirements_coverage is required")
                coverage = []
            coverage_ids: list[str] = []
            for coverage_index, entry in enumerate(coverage):
                if not isinstance(entry, dict):
                    errors.append(f"options[{index}].requirements_coverage[{coverage_index}] must be an object")
                    continue
                requirement_id = str(entry.get("requirement_id") or "")
                coverage_ids.append(requirement_id)
                requirement = required_by_id.get(requirement_id)
                if not requirement:
                    errors.append(f"options[{index}].requirements_coverage[{coverage_index}] references unknown requirement")
                    continue
                if _normalize_verbatim(entry.get("text_verbatim")) != _normalize_verbatim(requirement.get("text_verbatim")):
                    errors.append(f"options[{index}].requirements_coverage[{coverage_index}] rewrites owner text")
                status = entry.get("status")
                if status not in {"covered", "partial", "unanswered", "applied_global"}:
                    errors.append(f"options[{index}].requirements_coverage[{coverage_index}].status is invalid")
                if requirement.get("category") == "constraint" and status != "applied_global":
                    errors.append(f"options[{index}].requirements_coverage[{coverage_index}] constraint must be applied_global")
                beat_sequences = entry.get("beat_sequences")
                if not isinstance(beat_sequences, list) or any(value not in sequences for value in beat_sequences):
                    errors.append(f"options[{index}].requirements_coverage[{coverage_index}] references unknown beat sequence")
                entry_claims = entry.get("claim_ids")
                if not isinstance(entry_claims, list):
                    errors.append(f"options[{index}].requirements_coverage[{coverage_index}].claim_ids must be an array")
                elif set(str(item) for item in entry_claims) - option_claim_ids:
                    errors.append(f"options[{index}].requirements_coverage[{coverage_index}] references claims outside option")
                if status == "covered" and requirement.get("category") != "constraint" and not entry_claims:
                    errors.append(f"options[{index}].requirements_coverage[{coverage_index}] covered status requires claims")
                intents = entry.get("planned_screen_intents")
                if not isinstance(intents, list) or not intents:
                    errors.append(f"options[{index}].requirements_coverage[{coverage_index}] requires planned screen intents")
                if not str(entry.get("framing") or "").strip():
                    errors.append(f"options[{index}].requirements_coverage[{coverage_index}] requires framing")
            if len(coverage_ids) != len(set(coverage_ids)) or set(coverage_ids) != set(required_by_id):
                errors.append(f"options[{index}].requirements_coverage must exactly cover frozen scope once")
        preview_id = str(option.get("preview_artifact_id") or "").strip()
        html_anchor = str(option.get("html_anchor") or "").strip()
        html_anchors.append(html_anchor)
        if not re.fullmatch(r"#[A-Za-z][A-Za-z0-9_-]*", html_anchor):
            errors.append(f"options[{index}].html_anchor must be a stable HTML fragment")
        if preview_id != owner_surface_id:
            errors.append(f"options[{index}] preview must reference owner_surface_artifact_id")
        preview = artifact_by_id.get(preview_id)
        if not preview:
            errors.append(f"options[{index}] preview artifact is missing")
        elif preview.get("kind") != "owner_choice_preview" or preview.get("durable") is not True:
            errors.append(f"options[{index}] preview must be a durable owner_choice_preview artifact")
        elif (
            preview.get("schema") != "owner-choice-cards-html/v1"
            or preview.get("owner_visible") is not True
            or preview.get("media_type") != "text/html"
        ):
            errors.append(f"options[{index}] preview must be the rendered owner-visible HTML storytelling-cards page")
    if len(option_ids) != len(set(option_ids)):
        errors.append("option_id values must be unique")
    if len(html_anchors) != len(set(html_anchors)):
        errors.append("html_anchor values must be unique")
    for index in range(1, len(grouping_principles)):
        if _duplicate_copy(grouping_principles[index - 1], grouping_principles[index]):
            errors.append(f"options[{index - 1}] and options[{index}] grouping principles are not materially distinct")
        if _duplicate_copy(governing_thoughts[index - 1], governing_thoughts[index]):
            errors.append(f"options[{index - 1}] and options[{index}] governing thoughts are not materially distinct")
    if str(choice.get("recommended_option_id") or "") not in option_ids:
        errors.append("recommended_option_id must reference an option")
    return _gate_result(
        "owner_choice",
        errors,
        warnings,
        option_count=len(options),
        dashboard_preview_valid=bool(dashboard_surface) and not any(
            "dashboard" in item for item in errors
        ),
        visual_previews_valid=not errors,
        owner_choice_eligible=not errors,
    )


def _validate_presentation_outline_gate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Enforce routine/insight admission and traceable slide coverage before rendering."""

    errors: list[str] = []
    warnings: list[str] = []
    outline = payload.get("outline") if isinstance(payload.get("outline"), dict) else {}
    brief = payload.get("research_brief") if isinstance(payload.get("research_brief"), dict) else {}
    claims_payload = payload.get("claims") if isinstance(payload.get("claims"), dict) else {}
    if outline.get("contract_version") != "presentation-outline/v1":
        errors.append("outline contract_version must be presentation-outline/v1")
    if outline.get("output_format") != "html" or outline.get("delivery_mode") != "self-contained-single-file":
        errors.append("outline must request one self-contained HTML presentation")
    if outline.get("renderer_skill") in {"anthropic-pptx", "presentation-skill"}:
        errors.append("PowerPoint renderers are forbidden for Mozaika")
    slides = outline.get("slides")
    if not isinstance(slides, list) or not slides:
        errors.append("outline.slides must be non-empty")
        slides = []
    content_slides = [item for item in slides if isinstance(item, dict) and item.get("type") == "content"]
    for index, slide in enumerate(content_slides):
        if not slide.get("claim_ids"):
            errors.append(f"content slide {index} has no claim_ids")
    scenario = outline.get("scenario")
    legacy = scenario is None
    if legacy:
        warnings.append("legacy outline is readable but not eligible as a new Mozaika run output")
    elif scenario in {"routine_report", "weekly_autopilot"}:
        provenance = outline.get("provenance") if isinstance(outline.get("provenance"), dict) else {}
        if outline.get("coverage_mode") != "fixed_template" or not _is_sha256(provenance.get("template_sha256")):
            errors.append(f"{scenario} outline requires fixed_template admission and template SHA-256")
        if any(provenance.get(name) is not None for name in (
            "storyline_artifact_id", "selected_checkpoint_id", "selected_card_artifact_id"
        )):
            errors.append(f"{scenario} template admission cannot claim insight storyline provenance")
        if scenario == "routine_report" and provenance.get("research_brief_sha256") is not None:
            errors.append("routine template admission cannot claim research brief provenance")
    elif scenario == "insight_deck":
        brief_result = _validate_research_brief_gate(brief)
        errors.extend(f"research_brief: {item}" for item in brief_result["errors"])
        provenance = outline.get("provenance") if isinstance(outline.get("provenance"), dict) else {}
        if outline.get("coverage_mode") != "frozen_requirements":
            errors.append("insight outline requires frozen_requirements coverage mode")
        if not _is_sha256(provenance.get("research_brief_sha256")):
            errors.append("insight outline requires research brief provenance")
        for name in ("storyline_artifact_id", "selected_checkpoint_id", "selected_card_artifact_id"):
            if not str(provenance.get(name) or "").strip():
                errors.append(f"insight outline provenance.{name} is required")
        if provenance.get("template_sha256") is not None:
            errors.append("insight outline cannot use routine template admission")
        slide_ids = [str(item.get("slide_id") or "") for item in slides if isinstance(item, dict)]
        if any(not item for item in slide_ids) or len(slide_ids) != len(set(slide_ids)):
            errors.append("every insight slide requires a unique slide_id")
        slide_by_id = {
            str(item.get("slide_id") or ""): item for item in slides if isinstance(item, dict)
        }
        claim_ids = {
            str(item.get("claim_id") or "")
            for item in claims_payload.get("claims", [])
            if isinstance(item, dict)
        }
        required = {
            str(item.get("requirement_id") or ""): item
            for item in brief.get("requirements", [])
            if isinstance(item, dict) and "presentation" in item.get("required_surfaces", [])
        }
        coverage = outline.get("research_questions_coverage")
        if not isinstance(coverage, list):
            errors.append("insight outline coverage must be an array")
            coverage = []
        coverage_ids: list[str] = []
        for index, entry in enumerate(coverage):
            if not isinstance(entry, dict):
                errors.append(f"outline coverage[{index}] must be an object")
                continue
            requirement_id = str(entry.get("requirement_id") or "")
            coverage_ids.append(requirement_id)
            requirement = required.get(requirement_id)
            if not requirement:
                errors.append(f"outline coverage[{index}] references unknown requirement")
                continue
            if _normalize_verbatim(entry.get("text_verbatim")) != _normalize_verbatim(requirement.get("text_verbatim")):
                errors.append(f"outline coverage[{index}] rewrites owner text")
            status = entry.get("status")
            if requirement.get("category") == "constraint":
                if status != "applied_global":
                    errors.append(f"outline coverage[{index}] constraint must be applied_global")
            elif status not in {"covered", "partial", "unanswered"}:
                errors.append(f"outline coverage[{index}].status is invalid")
            target_ids = entry.get("slide_ids")
            if not isinstance(target_ids, list) or not target_ids:
                errors.append(f"outline coverage[{index}] requires slide_ids")
                target_ids = []
            if set(str(item) for item in target_ids) - set(slide_by_id):
                errors.append(f"outline coverage[{index}] references missing slides")
            entry_claims = set(str(item) for item in entry.get("claim_ids", []))
            if entry_claims - claim_ids:
                errors.append(f"outline coverage[{index}] references missing claims")
            if status == "covered" and requirement.get("category") != "constraint" and not entry_claims:
                errors.append(f"outline coverage[{index}] covered status requires claims")
            for slide_id in target_ids:
                slide_claims = set(str(item) for item in slide_by_id.get(str(slide_id), {}).get("claim_ids", []))
                if entry_claims and not (entry_claims & slide_claims):
                    errors.append(f"outline coverage[{index}] has no claim-bearing target slide")
        if len(coverage_ids) != len(set(coverage_ids)) or set(coverage_ids) != set(required):
            errors.append("insight outline must cover every frozen presentation requirement exactly once")
        checkpoint = payload.get("checkpoint")
        artifacts = payload.get("artifacts")
        if isinstance(checkpoint, dict) and isinstance(artifacts, dict):
            checkpoint_result = _validate_owner_decision_gate({
                "checkpoint": checkpoint,
                "artifacts": artifacts,
                "expected_state": "selected",
                "owner_reconfirmed_stale": payload.get("owner_reconfirmed_stale") is True,
            })
            errors.extend(f"owner_decision: {item}" for item in checkpoint_result["errors"])
        else:
            errors.append("insight outline requires selected checkpoint and artifact index")
        integrity = payload.get("narrative_integrity")
        if isinstance(integrity, dict):
            integrity_result = _validate_narrative_integrity_gate({"audit": integrity, "research_brief": brief})
            errors.extend(f"narrative_integrity: {item}" for item in integrity_result["errors"])
        else:
            errors.append("insight outline requires a passing storyline integrity audit")
    else:
        errors.append("outline scenario is invalid")
    return _gate_result(
        "presentation_outline",
        errors,
        warnings,
        scenario=scenario or "legacy",
        legacy_readable=legacy,
        new_run_eligible=not legacy and not errors,
        slide_count=len(slides),
        content_slide_count=len(content_slides),
    )


def _validate_speaker_story_cards_gate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Require one evidence-linked speaker cue card for every presentation slide."""

    errors: list[str] = []
    warnings: list[str] = []
    package = payload.get("speaker_story_cards") if isinstance(payload.get("speaker_story_cards"), dict) else {}
    outline = payload.get("outline") if isinstance(payload.get("outline"), dict) else {}
    claims_payload = payload.get("claims") if isinstance(payload.get("claims"), dict) else {}
    artifacts_payload = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    if package.get("contract_version") != "mozaika-speaker-story-cards/v1":
        errors.append("speaker_story_cards contract_version is invalid")
    if package.get("scenario") != "insight_deck":
        errors.append("speaker_story_cards are admitted only for insight_deck")
    if outline.get("contract_version") != "presentation-outline/v1" or outline.get("scenario") != "insight_deck":
        errors.append("speaker_story_cards require an insight presentation-outline/v1")
    slides = outline.get("slides") if isinstance(outline.get("slides"), list) else []
    cards = package.get("cards") if isinstance(package.get("cards"), list) else []
    if len(slides) < 2 or len(cards) != len(slides):
        errors.append("speaker_story_cards must contain exactly one card for every outline slide")
    artifact_by_id = {
        str(item.get("artifact_id") or ""): item
        for item in artifacts_payload.get("artifacts", [])
        if isinstance(item, dict)
    }
    ref_pairs = (
        ("outline_artifact_id", "outline_sha256"),
        ("presentation_artifact_id", "presentation_sha256"),
        ("html_artifact_id", "html_sha256"),
    )
    for id_field, hash_field in ref_pairs:
        artifact = artifact_by_id.get(str(package.get(id_field) or ""))
        if not artifact or artifact.get("sha256") != package.get(hash_field):
            errors.append(f"speaker_story_cards {id_field} does not match a current artifact")
    template = package.get("template") if isinstance(package.get("template"), dict) else {}
    if (
        template.get("ref") != "data/brandbook/mozaika/templates/speaker-story-cards.template.html"
        or template.get("sha256") != _SPEAKER_TEMPLATE_SHA256
    ):
        errors.append("speaker_story_cards template evidence is invalid")
    provenance = outline.get("provenance") if isinstance(outline.get("provenance"), dict) else {}
    if package.get("selected_checkpoint_id") != provenance.get("selected_checkpoint_id"):
        errors.append("speaker_story_cards selected checkpoint differs from the outline")
    if package.get("selected_card_artifact_id") != provenance.get("selected_card_artifact_id"):
        errors.append("speaker_story_cards selected strategy differs from the outline")
    if package.get("research_brief_sha256") != provenance.get("research_brief_sha256"):
        errors.append("speaker_story_cards research brief differs from the outline")
    if _normalize_verbatim(package.get("deck_title")) != _normalize_verbatim(outline.get("title")):
        errors.append("speaker_story_cards deck title differs from the presentation outline")
    claim_by_id = {
        str(item.get("claim_id") or ""): item
        for item in claims_payload.get("claims", [])
        if isinstance(item, dict)
    }
    card_ids: list[str] = []
    slide_ids: list[str] = []
    spoken_lines: list[tuple[str, str]] = []
    for index, (slide, card) in enumerate(zip(slides, cards)):
        if not isinstance(slide, dict) or not isinstance(card, dict):
            errors.append(f"speaker card {index} or outline slide is invalid")
            continue
        card_id = str(card.get("card_id") or "")
        slide_id = str(card.get("slide_id") or "")
        card_ids.append(card_id)
        slide_ids.append(slide_id)
        if card.get("order") != index + 1:
            errors.append(f"speaker card {index} has a non-sequential order")
        if slide_id != str(slide.get("slide_id") or ""):
            errors.append(f"speaker card {index} is detached from its outline slide")
        if card.get("slide_type") != slide.get("type"):
            errors.append(f"speaker card {index} changes the outline slide type")
        if _normalize_verbatim(card.get("slide_title")) != _normalize_verbatim(slide.get("title")):
            errors.append(f"speaker card {index} changes the slide title")
        say_this = card.get("say_this") if isinstance(card.get("say_this"), list) else []
        if not 1 <= len(say_this) <= 4 or any(not str(item).strip() for item in say_this):
            errors.append(f"speaker card {index} requires one to four spoken prompts")
        for line_index, line in enumerate(say_this):
            spoken_lines.append((f"cards[{index}].say_this[{line_index}]", str(line)))
        for field in ("purpose", "visual_cue", "transition"):
            if not str(card.get(field) or "").strip():
                errors.append(f"speaker card {index}.{field} is required")
        timing = card.get("timing_seconds")
        if not isinstance(timing, int) or not 10 <= timing <= 300:
            errors.append(f"speaker card {index}.timing_seconds is invalid")
        cues = card.get("evidence_cues") if isinstance(card.get("evidence_cues"), list) else []
        if slide.get("type") == "content" and not cues:
            errors.append(f"content speaker card {index} requires evidence cues")
        slide_claims = {str(item) for item in slide.get("claim_ids", [])}
        for cue_index, cue in enumerate(cues):
            if not isinstance(cue, dict):
                errors.append(f"speaker card {index} evidence cue {cue_index} is invalid")
                continue
            claim_id = str(cue.get("claim_id") or "")
            claim = claim_by_id.get(claim_id)
            if not claim or claim_id not in slide_claims:
                errors.append(f"speaker card {index} evidence cue {cue_index} is not supported by its slide")
                continue
            source_ids = {str(item) for item in cue.get("source_artifact_ids", [])}
            allowed_sources = {str(item) for item in claim.get("evidence_artifact_ids", [])}
            if not source_ids or source_ids - allowed_sources or source_ids - set(artifact_by_id):
                errors.append(f"speaker card {index} evidence cue {cue_index} has invalid source provenance")
    if len(card_ids) != len(set(card_ids)) or any(not item for item in card_ids):
        errors.append("speaker card ids must be non-empty and unique")
    if len(slide_ids) != len(set(slide_ids)) or slide_ids != [str(item.get("slide_id") or "") for item in slides if isinstance(item, dict)]:
        errors.append("speaker cards must preserve the exact unique slide order")
    for left_index, (left_path, left) in enumerate(spoken_lines):
        for right_path, right in spoken_lines[left_index + 1:]:
            if _duplicate_copy(left, right):
                errors.append(f"speaker prompts repeat one formulation: {left_path} and {right_path}")
                break
        if errors and errors[-1].startswith("speaker prompts repeat"):
            break
    brandbook_result = _validate_brandbook_conformance_gate({
        "artifact_type": "speaker_story_cards",
        "artifact_id": package.get("html_artifact_id"),
        "html_sha256": package.get("html_sha256"),
        "html_source": payload.get("html_source"),
        "template_sha256": template.get("sha256"),
        "artifacts": artifacts_payload,
    })
    errors.extend(f"brandbook: {item}" for item in brandbook_result["errors"])
    return _gate_result(
        "speaker_story_cards",
        errors,
        warnings,
        slide_count=len(slides),
        card_count=len(cards),
        exact_slide_coverage=bool(slides) and len(cards) == len(slides) and not any("slide" in item for item in errors),
        brandbook_conformance=brandbook_result,
    )


def _validate_completion_gate(payload: Dict[str, Any]) -> Dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if payload.get("contract_version") != "mozaika-completion-gate/v1":
        errors.append("contract_version must be mozaika-completion-gate/v1")
    scope = _validate_scope_gate(payload.get("scope") if isinstance(payload.get("scope"), dict) else {})
    claims = _validate_claim_gate(payload.get("claims") if isinstance(payload.get("claims"), dict) else {})
    artifacts = _validate_artifact_gate(payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {})
    errors.extend(f"scope: {item}" for item in scope["errors"])
    errors.extend(f"claims: {item}" for item in claims["errors"])
    errors.extend(f"artifacts: {item}" for item in artifacts["errors"])

    runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
    solved_runtime = (
        runtime.get("execution_status") == "ok"
        and runtime.get("objective_status") in {"passed", "satisfied"}
        and runtime.get("review_status") in {"passed", "not_required"}
        and runtime.get("verification_failures") is False
    )
    if not solved_runtime:
        warnings.append("runtime outcome axes do not support solved")
    visual = payload.get("visual_qa") if isinstance(payload.get("visual_qa"), dict) else {}
    visual_required = bool(visual.get("required"))
    visual_ok = (not visual_required) or visual.get("status") == "passed"
    if visual_required and not visual_ok:
        warnings.append("required visual QA has not passed")
    conformance_receipts = payload.get("brandbook_conformance_gates")
    conformance_errors: list[str] = []
    conformance_types: set[str] = set()
    if not isinstance(conformance_receipts, list) or not conformance_receipts:
        conformance_errors.append("brandbook_conformance_gates must contain inspected HTML gate results")
        conformance_receipts = []
    artifact_items = (
        payload.get("artifacts", {}).get("artifacts", [])
        if isinstance(payload.get("artifacts"), dict) else []
    )
    completion_artifact_by_id = {
        str(item.get("artifact_id") or ""): item
        for item in artifact_items
        if isinstance(item, dict)
    }
    for index, receipt in enumerate(conformance_receipts):
        if not isinstance(receipt, dict):
            conformance_errors.append(f"brandbook_conformance_gates[{index}] must be an object")
            continue
        metrics = receipt.get("metrics") if isinstance(receipt.get("metrics"), dict) else {}
        artifact_type = str(metrics.get("artifact_type") or "")
        artifact_id = str(metrics.get("artifact_id") or "")
        artifact = completion_artifact_by_id.get(artifact_id)
        if artifact_type in {"storytelling_cards", "selected_storytelling_card", "presentation", "speaker_story_cards"}:
            conformance_types.add(artifact_type)
        else:
            conformance_errors.append(f"brandbook_conformance_gates[{index}] artifact_type is invalid")
        if (
            receipt.get("gate") != "brandbook_conformance"
            or receipt.get("ok") is not True
            or receipt.get("errors") != []
            or metrics.get("source_checked") is not True
            or metrics.get("brandbook_version") != _MOZAIKA_BRANDBOOK_VERSION
            or metrics.get("brandbook_marker") is not True
            or metrics.get("core_palette_exact") is not True
            or metrics.get("forbidden_color_hits") != 0
            or metrics.get("template_exact") is not True
            or not artifact
            or artifact.get("sha256") != metrics.get("html_sha256")
        ):
            conformance_errors.append(f"brandbook_conformance_gates[{index}] is stale, fabricated, or did not inspect the current artifact")
        if artifact_type == "speaker_story_cards" and (
            metrics.get("template_required") is not True
            or metrics.get("template_sha256") != _SPEAKER_TEMPLATE_SHA256
        ):
            conformance_errors.append(f"brandbook_conformance_gates[{index}] does not prove the current speaker-card template")
    required_conformance_types = {"presentation"}
    if payload.get("scenario") == "insight_deck":
        required_conformance_types.update({"storytelling_cards", "selected_storytelling_card", "speaker_story_cards"})
    missing_conformance_types = required_conformance_types - conformance_types
    if missing_conformance_types:
        conformance_errors.append("missing inspected brandbook gates: " + ", ".join(sorted(missing_conformance_types)))
    errors.extend(f"brandbook: {item}" for item in conformance_errors)
    brandbook_conformance_ok = not conformance_errors
    design_receipts = payload.get("design_receipts")
    design_errors: list[str] = []
    design_types: set[str] = set()
    if not isinstance(design_receipts, list) or not design_receipts:
        design_errors.append("design_receipts must contain brandbook receipts")
        design_receipts = []
    for index, receipt in enumerate(design_receipts):
        if not isinstance(receipt, dict):
            design_errors.append(f"design_receipts[{index}] must be an object")
            continue
        artifact_type = receipt.get("artifact_type")
        if artifact_type not in {"dashboard", "storytelling_cards", "selected_storytelling_card", "speaker_story_cards", "report", "presentation"}:
            design_errors.append(f"design_receipts[{index}].artifact_type is invalid")
        else:
            design_types.add(artifact_type)
        if receipt.get("contract_version") != "mozaika-design-receipt/v1":
            design_errors.append(f"design_receipts[{index}] contract_version is invalid")
        if receipt.get("instructions_passed") is not True or receipt.get("status") != "pass":
            design_errors.append(f"design_receipts[{index}] did not pass")
        brandbook = receipt.get("brandbook") if isinstance(receipt.get("brandbook"), dict) else {}
        if (
            brandbook.get("authority") != "owner_brandbook"
            or brandbook.get("manifest_path") != "data/brandbook/mozaika/manifest.json"
            or brandbook.get("tokens_path") != "data/brandbook/mozaika/tokens.css"
            or not re.fullmatch(r"[a-f0-9]{64}", str(brandbook.get("manifest_sha256") or ""))
            or not brandbook.get("reference_ids")
        ):
            design_errors.append(f"design_receipts[{index}] brandbook evidence is invalid")
        checks = receipt.get("checks") if isinstance(receipt.get("checks"), dict) else {}
        required_checks = {
            "warm_canvas", "typography_hierarchy", "artifact_pattern", "semantic_palette",
            "source_proximity", "no_forbidden_default_theme", "service_metadata_hidden", "browser_verified",
        }
        if any(checks.get(name) is not True for name in required_checks):
            design_errors.append(f"design_receipts[{index}] required checks did not pass")
        if artifact_type == "dashboard" and checks.get("dashboard_excludes_storytelling_cards") is not True:
            design_errors.append(f"design_receipts[{index}] dashboard contains or did not check storytelling cards")
        dashboard_quality_checks = {
            "aligned_grid", "charts_render_without_errors", "tables_readable", "filters_functional",
            "filter_reset_works", "table_search_functional", "table_sort_functional",
            "customization_controls_functional", "customization_reset_works",
            "responsive_no_overflow", "empty_states_clear", "console_errors_absent",
        }
        if artifact_type == "dashboard" and any(checks.get(name) is not True for name in dashboard_quality_checks):
            design_errors.append(f"design_receipts[{index}] dashboard interaction or layout checks did not pass")
        card_design_checks = {"brand_palette_exact", "no_dark_card_theme"}
        if artifact_type in {"storytelling_cards", "selected_storytelling_card", "speaker_story_cards"} and any(
            checks.get(name) is not True for name in card_design_checks
        ):
            design_errors.append(f"design_receipts[{index}] storytelling-card brand palette checks did not pass")
        presentation_checks = {"diagram_rich", "smooth_page_transitions", "reduced_motion_fallback"}
        if artifact_type == "presentation" and any(checks.get(name) is not True for name in presentation_checks):
            design_errors.append(f"design_receipts[{index}] presentation visual richness or transition checks did not pass")
    required_design_types = {"dashboard", "presentation"}
    if payload.get("scenario") == "insight_deck":
        required_design_types.add("storytelling_cards")
        required_design_types.add("selected_storytelling_card")
        required_design_types.add("speaker_story_cards")
    missing_design_types = required_design_types - design_types
    if missing_design_types:
        design_errors.append("missing design receipts: " + ", ".join(sorted(missing_design_types)))
    errors.extend(f"design: {item}" for item in design_errors)
    design_ok = not design_errors
    language_audits = payload.get("business_language_audits")
    language_errors: list[str] = []
    language_types: set[str] = set()
    if not isinstance(language_audits, list) or not language_audits:
        language_errors.append("business_language_audits must contain dashboard and presentation audits")
        language_audits = []
    language_checks = {
        "protected_extraction_complete", "protected_verbatim_unchanged",
        "meaning_recoverable", "no_material_misrepresentation",
        "no_grossly_offensive_or_hostile_tone", "no_service_metadata_leak",
        "critical_only_failures_blocked", "pass_when_uncertain",
    }
    for index, audit in enumerate(language_audits):
        if not isinstance(audit, dict):
            language_errors.append(f"business_language_audits[{index}] must be an object")
            continue
        artifact_type = audit.get("artifact_type")
        if artifact_type not in {"dashboard", "storytelling_cards", "selected_storytelling_card", "speaker_story_cards", "presentation"}:
            language_errors.append(f"business_language_audits[{index}].artifact_type is invalid")
        else:
            language_types.add(artifact_type)
        if audit.get("contract_version") != "mozaika-business-language-audit/v1" or audit.get("status") != "pass":
            language_errors.append(f"business_language_audits[{index}] did not pass the business-language contract")
        if (
            not audit.get("assignment_artifact_id")
            or not re.fullmatch(r"[a-f0-9]{64}", str(audit.get("assignment_sha256") or ""))
            or not re.fullmatch(r"[a-f0-9]{64}", str(audit.get("artifact_sha256") or ""))
        ):
            language_errors.append(f"business_language_audits[{index}] assignment or artifact evidence is invalid")
        checks = audit.get("checks") if isinstance(audit.get("checks"), dict) else {}
        if any(checks.get(name) is not True for name in language_checks):
            language_errors.append(f"business_language_audits[{index}] required language checks did not pass")
        if audit.get("issues") != []:
            language_errors.append(f"business_language_audits[{index}] contains unresolved language issues")
        passes = audit.get("passes") if isinstance(audit.get("passes"), dict) else {}
        for pass_name in ("free_headings", "body_text"):
            pass_result = passes.get(pass_name) if isinstance(passes.get(pass_name), dict) else {}
            if pass_result.get("blocking_failure_count") != 0:
                language_errors.append(
                    f"business_language_audits[{index}].passes.{pass_name} has blocking failures"
                )
        if not isinstance(audit.get("protected_verbatim"), list):
            language_errors.append(f"business_language_audits[{index}].protected_verbatim must be an array")
        protected = audit.get("protected_verbatim") if isinstance(audit.get("protected_verbatim"), list) else []
        if any(not isinstance(item, dict) or item.get("found_unchanged") is not True for item in protected):
            language_errors.append(f"business_language_audits[{index}] changed protected owner text")
    required_language_types = {"dashboard", "presentation"}
    if payload.get("scenario") == "insight_deck":
        required_language_types.update({"storytelling_cards", "selected_storytelling_card", "speaker_story_cards"})
    missing_language_types = required_language_types - language_types
    if missing_language_types:
        language_errors.append("missing business-language audits: " + ", ".join(sorted(missing_language_types)))
    errors.extend(f"language: {item}" for item in language_errors)
    language_ok = not language_errors
    layout_audits = payload.get("layout_audits")
    layout_errors: list[str] = []
    layout_types: set[str] = set()
    if not isinstance(layout_audits, list) or not layout_audits:
        layout_errors.append("layout_audits must contain dashboard and presentation audits")
        layout_audits = []
    layout_checks = {
        "all_screens_inspected", "no_unintended_overlaps", "charts_within_bounds",
        "consistent_peer_spacing", "declared_centers_are_centered",
        "no_unintended_page_overflow", "interactive_states_inspected", "console_errors_absent",
    }
    for index, audit in enumerate(layout_audits):
        if not isinstance(audit, dict):
            layout_errors.append(f"layout_audits[{index}] must be an object")
            continue
        artifact_type = audit.get("artifact_type")
        if artifact_type not in {"dashboard", "presentation", "speaker_story_cards"}:
            layout_errors.append(f"layout_audits[{index}].artifact_type is invalid")
        else:
            layout_types.add(artifact_type)
        if audit.get("contract_version") != "mozaika-visual-layout-audit/v1" or audit.get("status") != "pass":
            layout_errors.append(f"layout_audits[{index}] did not pass the visual layout contract")
        checks = audit.get("checks") if isinstance(audit.get("checks"), dict) else {}
        if any(checks.get(name) is not True for name in layout_checks):
            layout_errors.append(f"layout_audits[{index}] required geometry checks did not pass")
        if audit.get("issues") != []:
            layout_errors.append(f"layout_audits[{index}] contains unresolved layout issues")
        viewports = audit.get("viewports") if isinstance(audit.get("viewports"), list) else []
        widths: list[int] = []
        for viewport_index, viewport in enumerate(viewports):
            if not isinstance(viewport, dict):
                layout_errors.append(f"layout_audits[{index}].viewports[{viewport_index}] is invalid")
                continue
            width = viewport.get("width")
            if isinstance(width, int):
                widths.append(width)
            if (
                viewport.get("overlap_count") != 0
                or viewport.get("overflow_count") != 0
                or viewport.get("spacing_outlier_count") != 0
                or not isinstance(viewport.get("max_center_offset_px"), (int, float))
                or viewport.get("max_center_offset_px", 3) > 2
                or not viewport.get("screenshot_artifact_id")
            ):
                layout_errors.append(f"layout_audits[{index}].viewports[{viewport_index}] has geometry failures")
        if not any(width >= 1280 for width in widths) or not any(768 <= width <= 1279 for width in widths) or not any(width <= 767 for width in widths):
            layout_errors.append(f"layout_audits[{index}] must cover wide, medium, and narrow viewports")
    required_layout_types = {"dashboard", "presentation"}
    if payload.get("scenario") == "insight_deck":
        required_layout_types.add("speaker_story_cards")
    missing_layout_types = required_layout_types - layout_types
    if missing_layout_types:
        layout_errors.append("missing layout audits: " + ", ".join(sorted(missing_layout_types)))
    errors.extend(f"layout: {item}" for item in layout_errors)
    layout_ok = not layout_errors
    unresolved = payload.get("unresolved")
    if not isinstance(unresolved, list):
        errors.append("unresolved must be an array")
        unresolved = []
    scenario = payload.get("scenario")
    if scenario not in _SUPPORTED_SCENARIOS:
        errors.append("scenario is invalid")
    owner_choice_ok = scenario != "insight_deck" or payload.get("owner_choice_gate_passed") is True
    if not owner_choice_ok:
        warnings.append("insight_deck owner-choice gate has not passed")
    narrative_integrity_ok = True
    if scenario == "insight_deck":
        brief = payload.get("research_brief") if isinstance(payload.get("research_brief"), dict) else {}
        if not brief:
            errors.append("integrity: insight completion requires a frozen research brief")
            narrative_integrity_ok = False
        else:
            brief_result = _validate_research_brief_gate(brief)
            integrity_errors = [f"research_brief: {item}" for item in brief_result["errors"]]
            mapping = payload.get("requirement_claim_map")
            if isinstance(mapping, dict):
                mapping_result = _validate_requirement_claim_map_gate({
                    "mapping": mapping,
                    "research_brief": brief,
                    "claims": payload.get("claims"),
                    "artifacts": payload.get("artifacts"),
                })
                integrity_errors.extend(f"requirement_claim_map: {item}" for item in mapping_result["errors"])
            else:
                integrity_errors.append("requirement_claim_map is required")
            checkpoint = payload.get("owner_decision_checkpoint")
            if isinstance(checkpoint, dict):
                checkpoint_result = _validate_owner_decision_gate({
                    "checkpoint": checkpoint,
                    "artifacts": payload.get("artifacts"),
                    "expected_state": "selected",
                    "owner_reconfirmed_stale": payload.get("owner_reconfirmed_stale") is True,
                })
                integrity_errors.extend(f"owner_decision: {item}" for item in checkpoint_result["errors"])
            else:
                integrity_errors.append("selected owner_decision_checkpoint is required")
            audits = payload.get("narrative_integrity_audits")
            audit_types: set[str] = set()
            artifact_by_id = {
                str(item.get("artifact_id") or ""): item
                for item in (payload.get("artifacts") or {}).get("artifacts", [])
                if isinstance(item, dict)
            }
            if not isinstance(audits, list):
                integrity_errors.append("narrative_integrity_audits must be an array")
                audits = []
            for index, audit in enumerate(audits):
                if not isinstance(audit, dict):
                    integrity_errors.append(f"narrative_integrity_audits[{index}] must be an object")
                    continue
                audit_types.add(str(audit.get("artifact_type") or ""))
                audit_result = _validate_narrative_integrity_gate({"audit": audit, "research_brief": brief})
                integrity_errors.extend(
                    f"narrative_integrity_audits[{index}]: {item}" for item in audit_result["errors"]
                )
                artifact = artifact_by_id.get(str(audit.get("artifact_id") or ""))
                if not artifact or artifact.get("sha256") != audit.get("artifact_sha256"):
                    integrity_errors.append(f"narrative_integrity_audits[{index}] does not match current artifact hash")
            required_audit_types = {"storytelling_cards", "selected_storytelling_card", "storyline", "presentation", "speaker_story_cards"}
            if not required_audit_types.issubset(audit_types):
                integrity_errors.append("missing narrative integrity audits: " + ", ".join(sorted(required_audit_types - audit_types)))
            outline_receipt = payload.get("presentation_outline_gate") if isinstance(payload.get("presentation_outline_gate"), dict) else {}
            execution_receipt = payload.get("presentation_execution_receipt") if isinstance(payload.get("presentation_execution_receipt"), dict) else {}
            outline_artifact = artifact_by_id.get(str(outline_receipt.get("outline_artifact_id") or ""))
            if (
                outline_receipt.get("ok") is not True
                or not outline_artifact
                or outline_artifact.get("sha256") != outline_receipt.get("outline_sha256")
            ):
                integrity_errors.append("presentation_outline_gate does not match a current outline artifact")
            output_ids = execution_receipt.get("output_artifact_ids")
            if (
                execution_receipt.get("status") != "pass"
                or execution_receipt.get("review_status") != "fresh"
                or execution_receipt.get("outline_sha256") != outline_receipt.get("outline_sha256")
                or not isinstance(output_ids, list)
                or not output_ids
                or set(str(item) for item in output_ids) - set(artifact_by_id)
            ):
                integrity_errors.append("presentation execution receipt is stale, incomplete, or detached from the outline")
            speaker_package = payload.get("speaker_story_cards") if isinstance(payload.get("speaker_story_cards"), dict) else {}
            speaker_receipt = payload.get("speaker_story_cards_gate") if isinstance(payload.get("speaker_story_cards_gate"), dict) else {}
            speaker_contract_artifact = artifact_by_id.get(str(speaker_receipt.get("contract_artifact_id") or ""))
            speaker_html_artifact = artifact_by_id.get(str(speaker_receipt.get("html_artifact_id") or ""))
            if (
                speaker_package.get("contract_version") != "mozaika-speaker-story-cards/v1"
                or speaker_receipt.get("ok") is not True
                or not speaker_contract_artifact
                or speaker_contract_artifact.get("sha256") != speaker_receipt.get("contract_sha256")
                or not speaker_html_artifact
                or speaker_html_artifact.get("sha256") != speaker_receipt.get("html_sha256")
                or speaker_package.get("html_artifact_id") != speaker_receipt.get("html_artifact_id")
                or speaker_package.get("html_sha256") != speaker_receipt.get("html_sha256")
                or speaker_package.get("outline_sha256") != speaker_receipt.get("outline_sha256")
                or speaker_package.get("presentation_sha256") != speaker_receipt.get("presentation_sha256")
                or speaker_receipt.get("outline_sha256") != outline_receipt.get("outline_sha256")
                or speaker_package.get("presentation_artifact_id") not in (output_ids or [])
            ):
                integrity_errors.append("speaker story cards gate is stale, incomplete, or detached from the final presentation")
            errors.extend(f"integrity: {item}" for item in integrity_errors)
            narrative_integrity_ok = not integrity_errors
    pptx_ok = True
    if scenario in _PPTX_PROFILES:
        pptx_profile = _PPTX_PROFILES[scenario]
        receipt = payload.get("pptx_execution_receipt") if isinstance(payload.get("pptx_execution_receipt"), dict) else {}
        artifact_by_id = {
            str(item.get("artifact_id") or ""): item
            for item in (payload.get("artifacts") or {}).get("artifacts", [])
            if isinstance(item, dict)
        }
        output_ids = receipt.get("output_artifact_ids") if isinstance(receipt.get("output_artifact_ids"), list) else []
        qa_ids = receipt.get("rendered_slide_qa_artifact_ids") if isinstance(receipt.get("rendered_slide_qa_artifact_ids"), list) else []
        if (
            receipt.get("skill_name") != "presentation-skill"
            or receipt.get("review_status") != "fresh"
            or receipt.get("style_preset") != pptx_profile["style_preset"]
            or receipt.get("reference_id") != pptx_profile["reference_id"]
            or receipt.get("reference_sha256") != pptx_profile["reference_sha256"]
            or receipt.get("reference_usage") != pptx_profile["reference_usage"]
            or receipt.get("status") != "pass"
            or not _is_sha256(receipt.get("outline_sha256"))
            or len(output_ids) != 1
        ):
            errors.append(
                "pptx: final editable deck must have a passing fresh presentation-skill receipt "
                f"with {pptx_profile['style_preset']} and the scenario reference profile"
            )
            pptx_ok = False
        else:
            pptx_artifact = artifact_by_id.get(str(output_ids[0]))
            if (
                not pptx_artifact
                or pptx_artifact.get("kind") != "pptx"
                or pptx_artifact.get("media_type") != "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                or pptx_artifact.get("owner_visible") is not True
            ):
                errors.append("pptx: receipt output must resolve to one owner-visible editable PPTX artifact")
                pptx_ok = False
        if not qa_ids or any(artifact_by_id.get(str(item), {}).get("kind") != "qa" for item in qa_ids):
            errors.append("pptx: rendered slide QA artifacts are required")
            pptx_ok = False
    solved_possible = (
        scope["ok"]
        and bool(scope["metrics"].get("solved_coverage"))
        and claims["ok"]
        and artifacts["ok"]
        and solved_runtime
        and visual_ok
        and brandbook_conformance_ok
        and design_ok
        and language_ok
        and layout_ok
        and owner_choice_ok
        and narrative_integrity_ok
        and pptx_ok
        and not unresolved
    )
    recommended_status = "solved" if solved_possible else ("best_effort" if artifacts["metrics"].get("artifact_count", 0) else "blocked_with_evidence")
    requested_status = payload.get("requested_status")
    if requested_status not in {"solved", "best_effort", "blocked_with_evidence"}:
        errors.append("requested_status is invalid")
    elif requested_status != recommended_status:
        errors.append(f"requested_status={requested_status} but gate recommends {recommended_status}")
    return _gate_result(
        "completion",
        errors,
        warnings,
        recommended_status=recommended_status,
        solved_possible=solved_possible,
        scope_ok=scope["ok"],
        claims_ok=claims["ok"],
        artifacts_ok=artifacts["ok"],
        runtime_ok=solved_runtime,
        visual_qa_ok=visual_ok,
        brandbook_conformance_ok=brandbook_conformance_ok,
        brandbook_conformance_count=len(conformance_receipts),
        design_ok=design_ok,
        design_receipt_count=len(design_receipts),
        business_language_ok=language_ok,
        business_language_audit_count=len(language_audits),
        layout_ok=layout_ok,
        layout_audit_count=len(layout_audits),
        owner_choice_ok=owner_choice_ok,
        narrative_integrity_ok=narrative_integrity_ok,
        pptx_ok=pptx_ok,
        unresolved_count=len(unresolved),
    )


def _validate_gate_payload(gate: str = "", payload: Any = None) -> Dict[str, Any]:
    """Deterministically validate orchestration gates without reading or mutating files."""

    if gate not in {"scope", "claims", "artifacts", "research_brief", "requirement_claim_map", "narrative_integrity", "owner_decision", "owner_choice", "presentation_outline", "brandbook_conformance", "speaker_story_cards", "completion"}:
        return _gate_result(str(gate or "unknown"), ["unsupported gate"], [])
    if not isinstance(payload, dict):
        return _gate_result(gate, ["payload must be an object"], [])
    try:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError):
        return _gate_result(gate, ["payload must be JSON-serializable"], [])
    payload_limit = _MAX_BRANDBOOK_GATE_PAYLOAD_BYTES if gate == "brandbook_conformance" else _MAX_GATE_PAYLOAD_BYTES
    if len(encoded) > payload_limit:
        return _gate_result(gate, [f"payload exceeds {payload_limit // (1024 * 1024)} MiB"], [])
    validators = {
        "scope": _validate_scope_gate,
        "claims": _validate_claim_gate,
        "artifacts": _validate_artifact_gate,
        "research_brief": _validate_research_brief_gate,
        "requirement_claim_map": _validate_requirement_claim_map_gate,
        "narrative_integrity": _validate_narrative_integrity_gate,
        "owner_decision": _validate_owner_decision_gate,
        "owner_choice": _validate_owner_choice_gate,
        "presentation_outline": _validate_presentation_outline_gate,
        "brandbook_conformance": _validate_brandbook_conformance_gate,
        "speaker_story_cards": _validate_speaker_story_cards_gate,
        "completion": _validate_completion_gate,
    }
    return validators[gate](payload)


def _validate_gate(_ctx: Any, gate: str = "", payload: Any = None) -> str:
    """PluginAPI-compatible tool wrapper around the deterministic gate validator."""

    return json.dumps(_validate_gate_payload(gate, payload), ensure_ascii=False)


def _choice_text(value: Any, label: str, limit: int, *, required: bool = True) -> str:
    text = _normalize_verbatim(_CONTROL_CHARS.sub("", str(value or ""))).strip()
    if required and not text:
        raise ValueError(f"{label} is required")
    if len(text) > limit:
        raise ValueError(f"{label} exceeds {limit} characters")
    return text


def _choice_store_root(api: Any) -> pathlib.Path:
    root = pathlib.Path(api.get_state_dir()).resolve() / "live-owner-choices"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _choice_dir(api: Any, question_id: str) -> pathlib.Path:
    clean_id = _choice_text(question_id, "question_id", 96)
    if not _CHOICE_ID.fullmatch(clean_id):
        raise ValueError("question_id must be a stable ASCII identifier")
    digest = hashlib.sha256(clean_id.encode("utf-8")).hexdigest()[:32]
    path = _choice_store_root(api) / digest
    path.mkdir(parents=True, exist_ok=True)
    return path


def _canonical_json_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _write_json_once(path: pathlib.Path, payload: Dict[str, Any]) -> bool:
    """Create an immutable JSON record atomically; never replace an existing record."""

    data = _canonical_json_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        with tmp.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(tmp, path)
            return True
        except FileExistsError:
            return False
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _read_choice_json(path: pathlib.Path) -> Dict[str, Any] | None:
    try:
        if path.stat().st_size > _MAX_CHOICE_ROUTE_BYTES:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _normalize_choice_options(options: Any) -> list[Dict[str, Any]]:
    if not isinstance(options, list) or not 2 <= len(options) <= 3:
        raise ValueError("options must contain two or three cards")
    normalized: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(options):
        if not isinstance(raw, dict):
            raise ValueError(f"options[{index}] must be an object")
        option_id = _choice_text(raw.get("id"), f"options[{index}].id", 64)
        if not _CHOICE_OPTION_ID.fullmatch(option_id) or option_id in seen:
            raise ValueError(f"options[{index}].id must be a unique stable ASCII identifier")
        seen.add(option_id)
        beats_raw = raw.get("story_beats")
        if not isinstance(beats_raw, list) or not 2 <= len(beats_raw) <= 4:
            raise ValueError(f"options[{index}].story_beats must contain two to four items")
        story_beats = [
            _choice_text(item, f"options[{index}].story_beats", 180)
            for item in beats_raw
        ]
        normalized.append({
            "id": option_id,
            "headline": _choice_text(raw.get("headline"), f"options[{index}].headline", 120),
            "main_thought": _choice_text(raw.get("main_thought"), f"options[{index}].main_thought", 320),
            "story_beats": story_beats,
            "executive_implication": _choice_text(
                raw.get("executive_implication"),
                f"options[{index}].executive_implication",
                260,
            ),
        })
    return normalized


def _normalize_choice_request(
    ctx: Any,
    *,
    question_id: str,
    run_id: str,
    title: str,
    question: str,
    options: Any,
    recommended_option_id: str,
    dashboard_artifact_id: str,
    dashboard_sha256: str,
    cards_artifact_id: str,
    cards_sha256: str,
    checkpoint_artifact_id: str,
    checkpoint_sha256: str,
) -> Dict[str, Any]:
    clean_question_id = _choice_text(question_id, "question_id", 96)
    if not _CHOICE_ID.fullmatch(clean_question_id):
        raise ValueError("question_id must be a stable ASCII identifier")
    clean_options = _normalize_choice_options(options)
    recommended = _choice_text(recommended_option_id, "recommended_option_id", 64)
    if recommended not in {item["id"] for item in clean_options}:
        raise ValueError("recommended_option_id must name one of the options")
    refs = {
        "dashboard": {
            "artifact_id": _choice_text(dashboard_artifact_id, "dashboard_artifact_id", 160),
            "sha256": str(dashboard_sha256 or "").strip().lower(),
        },
        "cards": {
            "artifact_id": _choice_text(cards_artifact_id, "cards_artifact_id", 160),
            "sha256": str(cards_sha256 or "").strip().lower(),
        },
        "checkpoint": {
            "artifact_id": _choice_text(checkpoint_artifact_id, "checkpoint_artifact_id", 160),
            "sha256": str(checkpoint_sha256 or "").strip().lower(),
        },
    }
    for name, ref in refs.items():
        if not _is_sha256(ref["sha256"]):
            raise ValueError(f"{name}_sha256 must be a SHA-256 digest")
    task_id = _choice_text(getattr(ctx, "task_id", ""), "task_id", 128)
    try:
        chat_id = int(getattr(ctx, "current_chat_id", 0) or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("current task chat_id is invalid") from exc
    if chat_id <= 0:
        raise ValueError("request_owner_choice requires an owner-visible foreground task")
    return {
        "contract_version": _CHOICE_CONTRACT_VERSION,
        "question_id": clean_question_id,
        "run_id": _choice_text(run_id, "run_id", 128),
        "task_id": task_id,
        "chat_id": chat_id,
        "project_id": _choice_text(getattr(ctx, "project_id", ""), "project_id", 80, required=False),
        "title": _choice_text(title, "title", 140),
        "question": _choice_text(question, "question", 600),
        "options": clean_options,
        "recommended_option_id": recommended,
        "artifact_refs": refs,
    }


def _publish_owner_choice(api: Any, ctx: Any, **kwargs: Any) -> Dict[str, Any]:
    request_core = _normalize_choice_request(ctx, **kwargs)
    request_digest = hashlib.sha256(_canonical_json_bytes(request_core)).hexdigest()
    choice_dir = _choice_dir(api, request_core["question_id"])
    request_path = choice_dir / "request.json"
    existing = _read_choice_json(request_path)
    if existing:
        if existing.get("request_sha256") != request_digest:
            raise ValueError("question_id already belongs to a different immutable request")
        return existing
    request = {
        **request_core,
        "request_sha256": request_digest,
        "response_token": uuid.uuid4().hex + uuid.uuid4().hex,
        "created_at": _utc_now(),
    }
    if not _write_json_once(request_path, request):
        existing = _read_choice_json(request_path)
        if not existing or existing.get("request_sha256") != request_digest:
            raise RuntimeError("could not publish the immutable owner choice")
        return existing
    return request


def _choice_public_payload(request: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "contract_version": request.get("contract_version"),
        "question_id": request.get("question_id"),
        "response_token": request.get("response_token"),
        "title": request.get("title"),
        "question": request.get("question"),
        "options": request.get("options"),
        "recommended_option_id": request.get("recommended_option_id"),
        "created_at": request.get("created_at"),
    }


def _list_pending_owner_choices(api: Any) -> list[Dict[str, Any]]:
    pending: list[Dict[str, Any]] = []
    root = _choice_store_root(api)
    for request_path in root.glob("*/request.json"):
        choice_dir = request_path.parent
        if (choice_dir / "answer.json").exists():
            continue
        request = _read_choice_json(request_path)
        if not request or request.get("contract_version") != _CHOICE_CONTRACT_VERSION:
            continue
        pending.append(_choice_public_payload(request))
    pending.sort(key=lambda item: str(item.get("created_at") or ""))
    return pending[:10]


def _submit_owner_choice(api: Any, body: Dict[str, Any]) -> Dict[str, Any]:
    question_id = _choice_text(body.get("question_id"), "question_id", 96)
    if not _CHOICE_ID.fullmatch(question_id):
        raise ValueError("question_id is invalid")
    response_token = _choice_text(body.get("response_token"), "response_token", 128)
    option_id = _choice_text(body.get("option_id"), "option_id", 64)
    choice_dir = _choice_dir(api, question_id)
    request = _read_choice_json(choice_dir / "request.json")
    if not request:
        raise FileNotFoundError("owner choice not found")
    if not hmac.compare_digest(str(request.get("response_token") or ""), response_token):
        raise PermissionError("owner choice token is invalid")
    option = next((item for item in request.get("options", []) if item.get("id") == option_id), None)
    if not isinstance(option, dict):
        raise ValueError("option_id is not part of this owner choice")
    answer_path = choice_dir / "answer.json"
    existing = _read_choice_json(answer_path)
    if existing:
        if existing.get("selected_option_id") != option_id:
            raise RuntimeError("owner choice was already answered with another option")
        return existing
    answer = {
        "contract_version": _CHOICE_CONTRACT_VERSION,
        "question_id": question_id,
        "run_id": request.get("run_id"),
        "task_id": request.get("task_id"),
        "selected_option_id": option_id,
        "selected_option": option,
        "request_sha256": request.get("request_sha256"),
        "answered_at": _utc_now(),
        "source": "mozaika-insight-widget-click",
    }
    if not _write_json_once(answer_path, answer):
        existing = _read_choice_json(answer_path)
        if not existing or existing.get("selected_option_id") != option_id:
            raise RuntimeError("owner choice changed concurrently")
        return existing
    return answer


def _owner_choice_result(api: Any, request: Dict[str, Any], answer: Dict[str, Any]) -> Dict[str, Any]:
    choice_dir = _choice_dir(api, str(request.get("question_id") or ""))
    answer_sha256 = hashlib.sha256(_canonical_json_bytes(answer)).hexdigest()
    _write_json_once(choice_dir / "consumed.json", {
        "contract_version": _CHOICE_CONTRACT_VERSION,
        "question_id": request.get("question_id"),
        "task_id": request.get("task_id"),
        "answer_sha256": answer_sha256,
        "consumed_at": _utc_now(),
    })
    return {
        "ok": True,
        "status": "answered",
        "contract_version": _CHOICE_CONTRACT_VERSION,
        "question_id": request.get("question_id"),
        "run_id": request.get("run_id"),
        "selected_option_id": answer.get("selected_option_id"),
        "selected_option": answer.get("selected_option"),
        "answered_at": answer.get("answered_at"),
        "answer_sha256": answer_sha256,
        "message": "Выбор владельца получен из виджета; продолжай текущую задачу с выбранной стратегией.",
    }


def _request_owner_choice(api: Any, ctx: Any, wait_seconds: int = _CHOICE_WAIT_DEFAULT_SEC, **kwargs: Any) -> str:
    """Publish a durable widget question and return the click to the same tool call."""

    try:
        wait_for = max(1, min(int(wait_seconds or _CHOICE_WAIT_DEFAULT_SEC), _CHOICE_WAIT_MAX_SEC))
        request = _publish_owner_choice(api, ctx, **kwargs)
    except (TypeError, ValueError, RuntimeError) as exc:
        return json.dumps({"ok": False, "status": "rejected", "error": str(exc)}, ensure_ascii=False)
    choice_dir = _choice_dir(api, str(request.get("question_id") or ""))
    existing_answer = _read_choice_json(choice_dir / "answer.json")
    if existing_answer:
        return json.dumps(_owner_choice_result(api, request, existing_answer), ensure_ascii=False)

    progress = getattr(ctx, "emit_progress_fn", None)
    if callable(progress):
        progress(
            "Нужен выбор владельца: откройте Widgets → «Mozaika · Инсайты» и нажмите подходящую карточку. "
            "Текущая задача остаётся активной и продолжится после клика."
        )
    deadline = time.monotonic() + wait_for
    next_progress = time.monotonic() + _CHOICE_PROGRESS_INTERVAL_SEC
    while time.monotonic() < deadline:
        answer = _read_choice_json(choice_dir / "answer.json")
        if answer:
            return json.dumps(_owner_choice_result(api, request, answer), ensure_ascii=False)
        if time.monotonic() >= next_progress:
            if callable(progress):
                progress("Mozaika продолжает ждать выбор в виджете; контекст и артефакты сохранены.")
            next_progress = time.monotonic() + _CHOICE_PROGRESS_INTERVAL_SEC
        time.sleep(0.4)

    _write_json_once(choice_dir / f"wait-timeout-{uuid.uuid4().hex}.json", {
        "contract_version": _CHOICE_CONTRACT_VERSION,
        "question_id": request.get("question_id"),
        "task_id": request.get("task_id"),
        "timed_out_at": _utc_now(),
        "wait_seconds": wait_for,
    })
    return json.dumps({
        "ok": False,
        "status": "waiting",
        "contract_version": _CHOICE_CONTRACT_VERSION,
        "question_id": request.get("question_id"),
        "run_id": request.get("run_id"),
        "recoverable": True,
        "message": (
            "Время ожидания tool call истекло, но вопрос и будущий ответ сохранены. "
            "Не угадывай выбор: повтори request_owner_choice с тем же question_id, чтобы получить ответ."
        ),
    }, ensure_ascii=False)


def _clean(value: Any, *, required: bool = False) -> str:
    text = _CONTROL_CHARS.sub("", str(value or "")).strip()
    if len(text) > _MAX_FIELD_CHARS:
        raise ValueError(f"поле длиннее {_MAX_FIELD_CHARS} символов")
    if required and not text:
        raise ValueError("обязательное поле пусто")
    return text


def _load_task_presets(scenario: str = "insight_deck") -> Dict[str, Any]:
    """Load and strictly validate owner-editable widget task presets."""

    try:
        raw = json.loads(_TASK_PRESETS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("не удалось прочитать настройки вариантов задания") from exc
    if not isinstance(raw, dict) or raw.get("contract_version") != "mozaika-task-presets/v1":
        raise RuntimeError("неверная версия настроек вариантов задания")
    if scenario not in {"insight_deck", "weekly_autopilot"}:
        raise RuntimeError("неподдерживаемый набор вариантов задания")
    insight = raw.get(scenario)
    if not isinstance(insight, dict):
        raise RuntimeError(f"в настройках отсутствует раздел {scenario}")
    try:
        button_label = _clean(insight.get("button_label"), required=True)
        default_prefix = _clean(insight.get("default_prefix"), required=True)
        fixed_suffix = _clean(insight.get("fixed_suffix"), required=True)
    except ValueError as exc:
        raise RuntimeError("текст настроек вариантов задания некорректен") from exc
    if not fixed_suffix.startswith("Подготовь"):
        raise RuntimeError("неизменяемая часть задания должна начинаться со слова «Подготовь»")
    raw_items = insight.get("items")
    if not isinstance(raw_items, list) or not 1 <= len(raw_items) <= 20:
        raise RuntimeError("настройки должны содержать от 1 до 20 вариантов задания")
    items: list[Dict[str, str]] = []
    seen_ids: set[str] = set()
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            raise RuntimeError("каждый вариант задания должен быть объектом")
        preset_id = str(raw_item.get("id") or "").strip()
        if not _PRESET_ID.fullmatch(preset_id) or preset_id in seen_ids:
            raise RuntimeError("идентификатор варианта задания некорректен или повторяется")
        try:
            label = _clean(raw_item.get("label"), required=True)
            prefix = _clean(raw_item.get("prefix"), required=True)
        except ValueError as exc:
            raise RuntimeError("текст варианта задания некорректен") from exc
        if prefix.startswith("Подготовь") or " Подготовь" in prefix:
            raise RuntimeError("начало варианта не должно содержать неизменяемую часть «Подготовь»")
        seen_ids.add(preset_id)
        items.append({"id": preset_id, "label": label, "prefix": prefix})
    return {
        "contract_version": "mozaika-task-presets/v1",
        "button_label": button_label,
        "default_prefix": default_prefix,
        "fixed_suffix": fixed_suffix,
        "items": items,
    }


def _host_service_url() -> str:
    raw = str(os.environ.get("OUROBOROS_HOST_SERVICE_PORT") or "8767").strip()
    try:
        port = int(raw)
    except ValueError as exc:
        raise RuntimeError("некорректный порт службы Ouroboros") from exc
    if not 1 <= port <= 65535:
        raise RuntimeError("некорректный порт службы Ouroboros")
    return f"http://127.0.0.1:{port}/chat/inject"


def _scenario_prompt(scenario: str, fields: Dict[str, Any]) -> str:
    if scenario not in _SUPPORTED_SCENARIOS:
        raise ValueError("неподдерживаемый сценарий")
    assignment = fields.get("assignment_file")
    if not isinstance(assignment, dict):
        raise ValueError("не задан файл поручения")
    path = str(assignment.get("path") or "").strip()
    digest = str(assignment.get("sha256") or "").strip()
    if not path or not _is_sha256(digest):
        raise ValueError("ссылка на файл поручения некорректна")
    return (
        "Mozaika, возьми в работу поручение из локального файла:\n"
        f"`{path}`\n"
        f"SHA-256: `{digest}`\n\n"
        "Используй скилл `mozaika` и запусти видимую основную задачу. "
        "Прочитай файл целиком, проверь его хеш и исполняй поручение по его критериям. "
        "Не копируй содержимое файла в чат: кратко подтверди запуск, а дальше показывай только значимый ход работы и результаты."
    )


def _inject(api: Any, scenario: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    prompt = _scenario_prompt(scenario, fields)
    token = api.get_skill_token().use_in_request()
    body = json.dumps(
        {
            "text": prompt,
            "chat_id": 1,
            "user_id": 1,
            "sender_label": "Mozaika",
            "wait_for_response": False,
            "transport": {"kind": "owner_widget", "scenario": scenario},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        _host_service_url(),
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Skill-Token": token,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310 - fixed loopback URL
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        return {"ok": False, "error": f"Служба Ouroboros отклонила запуск ({exc.code}): {detail}"}
    except Exception as exc:
        return {"ok": False, "error": f"Не удалось поставить сценарий в очередь: {type(exc).__name__}: {exc}"}
    if not payload.get("ok"):
        return {"ok": False, "error": str(payload.get("error") or "Служба Ouroboros отклонила запуск")}
    result = {
        "ok": True,
        "status": "queued",
        "scenario": scenario,
        "message": "Поручение передано Mozaika; Ouroboros запустит его как видимую основную задачу.",
    }
    if payload.get("task_id"):
        result["task_id"] = str(payload["task_id"])
    return result


async def _read_json_body(request: Request) -> Dict[str, Any]:
    chunks = bytearray()
    async for chunk in request.stream():
        chunks.extend(chunk)
    try:
        body = json.loads(chunks.decode("utf-8")) if chunks else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("тело запроса должно быть корректным JSON") from exc
    if not isinstance(body, dict):
        raise ValueError("тело запроса должно быть объектом")
    return body


async def _read_limited_json_body(request: Request, limit: int = _MAX_CHOICE_ROUTE_BYTES) -> Dict[str, Any]:
    chunks = bytearray()
    async for chunk in request.stream():
        chunks.extend(chunk)
        if len(chunks) > limit:
            raise PayloadTooLarge(f"тело запроса превышает {limit // 1024} КБ")
    try:
        body = json.loads(chunks.decode("utf-8")) if chunks else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("тело запроса должно быть корректным JSON") from exc
    if not isinstance(body, dict):
        raise ValueError("тело запроса должно быть объектом")
    return body


def _safe_filename(value: Any, index: int) -> str:
    basename = str(value or "file").replace("\\", "/").rsplit("/", 1)[-1]
    clean = _UNSAFE_FILENAME.sub("_", _CONTROL_CHARS.sub("", basename)).strip(" .")
    if not clean or clean in {".", ".."}:
        clean = "file"
    return f"{index:02d}-{clean[:140]}"


def _safe_relative_parts(value: Any) -> list[str]:
    """Return a safe relative path while preserving a dropped folder hierarchy."""

    raw = _CONTROL_CHARS.sub("", str(value or "")).replace("\\", "/").strip()
    if not raw or len(raw) > _MAX_RELATIVE_PATH_CHARS:
        raise ValueError("относительный путь пуст или слишком длинный")
    if raw.startswith(("/", "~")) or re.match(r"^[A-Za-z]:", raw):
        raise ValueError("путь к файлу не должен быть абсолютным")
    parts: list[str] = []
    for part in raw.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            raise ValueError("путь к файлу не должен выходить в родительскую папку")
        clean = _UNSAFE_FILENAME.sub("_", part).strip(" .")
        if not clean or clean in {".", ".."}:
            raise ValueError("путь к файлу содержит некорректную часть")
        parts.append(clean[:140])
    if not parts:
        raise ValueError("путь к файлу не содержит допустимых частей")
    return parts


def _validated_url(value: Any) -> str:
    raw = _CONTROL_CHARS.sub("", str(value or "")).strip()
    if not raw or len(raw) > _MAX_URL_CHARS:
        raise ValueError("URL пуст или слишком длинный")
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL должен использовать http или https и содержать адрес сайта")
    if parsed.username or parsed.password:
        raise ValueError("URL не должен содержать логин или пароль")
    return urllib.parse.urlunsplit(
        (parsed.scheme.lower(), parsed.netloc, parsed.path or "", parsed.query or "", parsed.fragment or "")
    )


def _selection_dir(api: Any) -> pathlib.Path:
    root = pathlib.Path(api.get_state_dir()).resolve() / "path-selections"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _run_native_picker(kind: str) -> list[str]:
    """Open a bounded OS picker and return owner-selected absolute paths."""

    if kind not in {"file", "directory"}:
        raise ValueError("тип выбора должен быть file или directory")
    if sys.platform == "darwin":
        if kind == "directory":
            script = 'POSIX path of (choose folder with prompt "Выберите папку с данными")'
        else:
            script = (
                'set chosenFiles to choose file with prompt "Выберите файлы с данными" '
                "with multiple selections allowed\n"
                'set output to ""\n'
                "repeat with chosenFile in chosenFiles\n"
                "set output to output & POSIX path of chosenFile & linefeed\n"
                "end repeat\n"
                "return output"
            )
        command = ["/usr/bin/osascript", "-e", script]
    elif os.name == "nt":
        if kind == "directory":
            script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$d=New-Object System.Windows.Forms.FolderBrowserDialog; "
                "$d.Description='Выберите папку с данными'; "
                "if($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK)"
                "{ConvertTo-Json -Compress @($d.SelectedPath)}else{'[]'}"
            )
        else:
            script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$d=New-Object System.Windows.Forms.OpenFileDialog; $d.Multiselect=$true; "
                "$d.Title='Выберите файлы с данными'; "
                "if($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK)"
                "{ConvertTo-Json -Compress @($d.FileNames)}else{'[]'}"
            )
        command = ["powershell.exe", "-NoProfile", "-STA", "-Command", script]
    else:
        command = ["zenity", "--file-selection"]
        if kind == "directory":
            command.append("--directory")
        else:
            command.extend(["--multiple", "--separator", "\n"])
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=55,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("системный диалог выбора недоступен на этой платформе") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("время ожидания выбора истекло") from exc
    if completed.returncode != 0:
        message = (completed.stderr or "").strip().lower()
        if "cancel" in message or "canceled" in message or "cancelled" in message or completed.returncode == 1:
            return []
        raise RuntimeError((completed.stderr or "не удалось открыть системный диалог").strip()[:300])
    output = (completed.stdout or "").strip()
    if not output:
        return []
    if os.name == "nt":
        decoded = json.loads(output)
        values = decoded if isinstance(decoded, list) else [decoded]
    else:
        values = output.splitlines()
    paths: list[str] = []
    for value in values:
        path = pathlib.Path(str(value or "").strip()).expanduser().resolve(strict=True)
        if kind == "file" and not path.is_file():
            raise ValueError(f"выбранный путь не является файлом: {path.name}")
        if kind == "directory" and not path.is_dir():
            raise ValueError(f"выбранный путь не является папкой: {path.name}")
        paths.append(str(path))
    return paths


def _create_path_selection(api: Any, kind: str) -> Dict[str, Any]:
    paths = _run_native_picker(kind)
    if not paths:
        return {"ok": True, "cancelled": True, "sources": []}
    token = uuid.uuid4().hex
    selected = []
    for raw in paths:
        path = pathlib.Path(raw)
        selected.append(
            {
                "path": raw,
                "entry_type": "directory" if path.is_dir() else "file",
                "display_name": path.name or raw,
                "size_bytes": path.stat().st_size if path.is_file() else None,
            }
        )
    receipt = {
        "contract_version": "mozaika-path-selection/v1",
        "token": token,
        "created_at": _utc_now(),
        "consumed_at": None,
        "sources": selected,
    }
    receipt_path = _selection_dir(api) / f"{token}.json"
    with receipt_path.open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return {
        "ok": True,
        "cancelled": False,
        "sources": [{**item, "selection_token": token} for item in selected],
    }


def _validated_local_path(api: Any, item: Dict[str, Any]) -> Dict[str, Any]:
    token = str(item.get("selection_token") or "").strip().lower()
    if not _PATH_SELECTION_TOKEN.fullmatch(token):
        raise ValueError("локальный путь не подтверждён системным диалогом")
    receipt_path = (_selection_dir(api) / f"{token}.json").resolve()
    try:
        receipt_path.relative_to(_selection_dir(api))
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("подтверждение локального пути не найдено") from exc
    raw_path = str(item.get("path") or "").strip()
    selected = next(
        (entry for entry in receipt.get("sources", []) if str(entry.get("path") or "") == raw_path),
        None,
    )
    if not isinstance(selected, dict):
        raise ValueError("локальный путь не совпадает с выбором владельца")
    path = pathlib.Path(raw_path).resolve(strict=True)
    entry_type = "directory" if path.is_dir() else "file" if path.is_file() else ""
    if not entry_type or entry_type != selected.get("entry_type"):
        raise ValueError("тип локального источника изменился после выбора")
    return {
        "path": str(path),
        "entry_type": entry_type,
        "display_name": _clean(selected.get("display_name")) or path.name or str(path),
        "size_bytes": path.stat().st_size if entry_type == "file" else None,
        "selection_token": token,
        "selection_receipt": str(receipt_path),
    }


def _decode_file_payload(item: Dict[str, Any]) -> bytes:
    encoded = str(item.get("data_base64") or "")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("содержимое файла не является корректным base64") from exc
    declared_size = item.get("size")
    if declared_size not in (None, ""):
        try:
            if int(declared_size) != len(content):
                raise ValueError("указанный размер файла не совпадает с фактическим")
        except (TypeError, ValueError) as exc:
            raise ValueError("указанный размер файла не совпадает с фактическим") from exc
    return content


def _legacy_sources(body: Dict[str, Any]) -> list[Dict[str, Any]]:
    """Accept one stale widget request during a reviewed extension reload."""

    sources: list[Dict[str, Any]] = []
    files = body.get("files") or []
    if not isinstance(files, list):
        raise ValueError("список файлов должен быть массивом")
    for item in files:
        sources.append({"kind": "file", "file": item})
    hint = str(body.get("source_hint") or "").strip()
    if hint:
        sources.append({"kind": "url", "url": hint})
    return sources


def _store_sources(api: Any, launch_id: str, raw_sources: Any) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
    if not isinstance(raw_sources, list):
        raise ValueError("список источников должен быть массивом")
    if not raw_sources:
        raise ValueError("добавьте хотя бы один URL, файл или папку")
    if len(raw_sources) > _MAX_SOURCES:
        raise PayloadTooLarge(f"add no more than {_MAX_SOURCES} top-level sources")

    job_dir = api.skill_job_dir(launch_id)
    assets_dir = (job_dir / "assets").resolve()
    normalized: list[Dict[str, Any]] = []
    flattened_files: list[Dict[str, Any]] = []
    file_count = 0
    seen_urls: set[str] = set()
    seen_destinations: set[str] = set()

    def persist_file(
        file_item: Any,
        *,
        source_id: str,
        source_index: int,
        directory_name: str = "",
    ) -> Dict[str, Any]:
        nonlocal file_count
        if not isinstance(file_item, dict):
            raise ValueError("каждый файл должен быть описан объектом")
        file_count += 1
        if file_count > _MAX_FILES:
            raise PayloadTooLarge(f"select no more than {_MAX_FILES} files")
        content = _decode_file_payload(file_item)
        original_name = _clean(file_item.get("name")) or "file"
        relative_raw = file_item.get("relative_path") or original_name
        relative_parts = _safe_relative_parts(relative_raw)
        if directory_name:
            root_name = _safe_filename(directory_name, source_index)
            destination = assets_dir / root_name
            # Browsers include the selected directory as the first relative component.
            if relative_parts and relative_parts[0].casefold() == directory_name.casefold():
                relative_parts = relative_parts[1:] or [_safe_filename(original_name, file_count)]
            destination = destination.joinpath(*relative_parts)
        else:
            destination = assets_dir / _safe_filename(relative_parts[-1], source_index)
        resolved = destination.resolve()
        try:
            resolved.relative_to(assets_dir)
        except ValueError as exc:
            raise ValueError("путь файла выходит за пределы папки артефактов") from exc
        destination_key = str(resolved)
        if destination_key in seen_destinations:
            raise ValueError("два файла попадают в один и тот же путь хранения")
        seen_destinations.add(destination_key)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        with resolved.open("xb") as handle:
            handle.write(content)
        stored = {
            "source_id": source_id,
            "original_name": original_name,
            "relative_path": "/".join(relative_parts),
            "stored_path": str(resolved),
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "mime": _clean(file_item.get("mime"))[:160] or "application/octet-stream",
            "artifact_kind": "user_input",
            "preservation": "append_only",
        }
        flattened_files.append(stored)
        return stored

    for source_index, raw_source in enumerate(raw_sources, start=1):
        if not isinstance(raw_source, dict):
            raise ValueError("каждый источник должен быть описан объектом")
        source_id = f"source-{source_index:02d}"
        kind = str(raw_source.get("kind") or "").strip().lower()
        if kind == "url":
            url = _validated_url(raw_source.get("url"))
            if url in seen_urls:
                raise ValueError("один и тот же URL добавлен более одного раза")
            seen_urls.add(url)
            normalized.append(
                {
                    "source_id": source_id,
                    "kind": "url",
                    "display_name": _clean(raw_source.get("display_name")) or url,
                    "url": url,
                    "fetch_status": "pending_data_stage",
                }
            )
            continue
        if kind == "local_path":
            local = _validated_local_path(api, raw_source)
            normalized.append(
                {
                    "source_id": source_id,
                    "kind": "local_path",
                    "display_name": local["display_name"],
                    "path": local["path"],
                    "entry_type": local["entry_type"],
                    "size_bytes": local["size_bytes"],
                    "selection_token": local["selection_token"],
                    "selection_receipt": local["selection_receipt"],
                    "copy_status": "pending_data_stage",
                    "preservation": "reference_only",
                }
            )
            continue
        if kind == "file":
            item = raw_source.get("file")
            if not isinstance(item, dict):
                raise ValueError("для файлового источника нужен объект файла")
            stored = persist_file(item, source_id=source_id, source_index=source_index)
            normalized.append(
                {
                    "source_id": source_id,
                    "kind": "file",
                    "display_name": stored["original_name"],
                    "file": stored,
                }
            )
            continue
        if kind == "directory":
            directory_name = _clean(raw_source.get("name"), required=True)
            file_items = raw_source.get("files")
            if not isinstance(file_items, list) or not file_items:
                raise ValueError("папка должна содержать хотя бы один файл")
            stored_files = [
                persist_file(
                    item,
                    source_id=source_id,
                    source_index=source_index,
                    directory_name=directory_name,
                )
                for item in file_items
            ]
            normalized.append(
                {
                    "source_id": source_id,
                    "kind": "directory",
                    "display_name": directory_name,
                    "file_count": len(stored_files),
                    "size_bytes": sum(item["size_bytes"] for item in stored_files),
                    "files": stored_files,
                }
            )
            continue
        raise ValueError("тип источника должен быть URL, локальным путём, файлом или папкой")
    return normalized, flattened_files


def _write_launch_manifest(api: Any, launch_id: str, scenario: str, fields: Dict[str, Any]) -> str:
    path = api.skill_job_dir(launch_id) / "launch-manifest.json"
    manifest = {
        "contract_version": "mozaika-launch-manifest/v2",
        "launch_id": launch_id,
        "scenario": scenario,
        "created_at": _utc_now(),
        "preservation_policy": {
            "mode": "append_only",
            "preserve_user_inputs": True,
            "preserve_stage_outputs": True,
            "allow_delete": False,
        },
        "input_sources_contract": fields["input_sources_contract"],
        "input_sources": fields["input_sources"],
        "input_files": fields["input_files"],
        "local_paths": fields["local_paths"],
        "source_urls": fields["source_urls"],
        "output_language": fields["output_language"],
        "assignment_file": fields["assignment_file"],
    }
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return str(path.resolve())


def _write_weekly_autopilot_assignment(
    api: Any,
    launch_id: str,
    fields: Dict[str, Any],
) -> Dict[str, str]:
    """Write the isolated second-widget contract without changing legacy scenarios."""

    path = api.skill_job_dir(launch_id) / "assignment.md"
    source_counts = {"url": 0, "file": 0, "directory": 0, "local_file": 0, "local_directory": 0}
    for source in fields["input_sources"]:
        if source["kind"] == "local_path":
            source_counts[f"local_{source['entry_type']}"] += 1
        else:
            source_counts[source["kind"]] += 1
    text = f"""# Пятничный автопилот: обновление регулярного отчёта

## Поручение руководителя

{fields['weekly_brief']}

## Цель

Обнови известный регулярный процесс по новым данным без ручной сборки: сохрани согласованные определения показателей, структуру dashboard и порядок управленческого рассказа, но пересчитай факты, сравнения, аномалии и рекомендации. Обычные обратимые операции выполняй автономно; запроси решение только если источник неполон, схема несовместима, конфликт метрик не разрешается правилами или новые факты делают утверждённый шаблон вводящим в заблуждение.

## Материалы

- манифест запуска: `{fields['launch_manifest_path']}`;
- URL: {source_counts['url']}; загруженных файлов: {source_counts['file']}; загруженных папок: {source_counts['directory']};
- локальных файлов по ссылке: {source_counts['local_file']}; локальных папок по ссылке: {source_counts['local_directory']};
- авторитетный список источников, подтверждённые владельцем абсолютные пути и пути к локальным копиям находятся в манифесте;
- на первом этапе скопируй каждый `local_path` в append-only хранилище кампании потоковой файловой операцией, не читай большой файл целиком в контекст или память, не изменяй оригинал и проверь размер и SHA-256 копии.

## Обязательный маршрут второго сценария

1. **Данные.** Инвентаризируй все источники; проверь период, схему, полноту, типы, дубли, пропуски и пригодность для сравнения. Сохрани raw-входы, quality report, исключения и lineage.
2. **Расчёты.** Пересчитай согласованные KPI и сравнения с прошлым периодом, целью и исторической нормой. Каждый существенный вывод свяжи с проверяемым источником и вычислением.
3. **HTML-dashboard.** Обнови автономный управляемый dashboard только на основе `data/brandbook/mozaika/templates/scenario-2-dashboard.template.html`. Сохрани фильтры периода и среза, поиск и сортировку таблицы, фильтр важности, настройку плотности, скрытие второстепенного раздела и общий сброс. Не добавляй загрузчик Excel, storytelling cards или служебные данные.
4. **Аномалии и важные моменты.** После расчёта dashboard отдельно проверь отклонения относительно собственной истории объекта, целевых уровней и соседних сегментов. Покажи факт, базу сравнения, величину отклонения, уверенность и управленческое следствие; не объявляй риск только из-за экстремума.
5. **HTML-презентация.** На основе принятых фактов собери автономную богатую HTML-презентацию только по `data/brandbook/mozaika/templates/scenario-2-presentation.template.html`: контекст → KPI → динамика → срез → главная аномалия → полная таблица → действия. Обязательны содержательные диаграммы и таблица, плавные переходы, клавиатура, fullscreen, overview, печать, адаптивность и reduced motion.
6. **Редактируемый PPTX — последний производственный шаг.** Сформируй отдельный factual outline по `data/brandbook/mozaika/templates/scenario-2-presentation-skill-outline.example.json` и вызови именно установленный, включённый и свежо проверенный скилл `presentation-skill` с `--style-preset mozaika-weekly`. Не используй `pptx` или `anthropic-pptx`. PPTX не заменяет HTML, а повторяет принятые факты и управленческий ход в редактируемом формате.
7. **Сверка и доставка.** Сверь общие KPI, периоды, названия сущностей, аномалии и действия между dashboard, HTML и PPTX. Открой HTML, отрендери PPTX и проверь каждый экран/слайд на наложения, выходы за границы, читаемость, правильное центрирование и сохранение брендбука.

## Авторитетные референсы

- сценарный профиль: `data/brandbook/mozaika/references/scenario-2-weekly-autopilot.md`;
- dashboard: `data/brandbook/mozaika/templates/scenario-2-dashboard.template.html`;
- HTML-презентация: `data/brandbook/mozaika/templates/scenario-2-presentation.template.html`;
- PPTX-outline: `data/brandbook/mozaika/templates/scenario-2-presentation-skill-outline.example.json`;
- редактируемый визуальный референс: `data/brandbook/mozaika/references/scenario-2-sprint25-review-reference.pptx`;
- точные хеши и приоритет источников находятся в `data/brandbook/mozaika/manifest.json`.

При чтении через runtime-data API убирай ведущий `data/`: например, читай `brandbook/mozaika/BRANDBOOK.md`. В контрактах, квитанциях и поручении сохраняй полные канонические пути `data/brandbook/...`.

## Артефакты на выходе

- сохранённые исходники, source inventory, quality report, исключения и lineage;
- проверенный аналитический набор и реестр утверждений;
- автономный управляемый HTML-dashboard;
- журнал аномалий и важных моментов;
- автономная богатая HTML-презентация;
- редактируемый `.pptx`, созданный последним шагом через `presentation-skill`;
- design receipts, browser/layout QA для обоих HTML, отрендеренные изображения и QA PPTX, итоговая сверка чисел и короткая записка руководителю.

## Критерии приёмки

- каждый существенный вывод трассируется до источника, периода, единицы и вычисления;
- все источники и промежуточные результаты сохраняются как новые неизменяемые артефакты; ничего пользовательского не удаляется и не перезаписывается;
- dashboard и обе презентации используют точные названия исследования и пункты поручения владельца, если они заданы;
- dashboard не содержит storytelling cards ни визуально, ни скрыто, ни во встроенном payload;
- HTML не зависит от CDN, сетевых шрифтов, внешних скриптов, изображений или iframe;
- пользовательские артефакты не показывают внутренние id, хеши, пути, версии схем, номера вариантов, названия стадий или статусы проверок;
- независимый языковой проход отклоняет только бесспорные критические ошибки; пользовательские формулировки защищены дословно;
- визуальный валидатор проверяет wide, medium и narrow viewport, фильтры, таблицу, reset и отсутствие ошибок консоли; PPTX дополнительно проходит render всех слайдов и проверку геометрии;
- `presentation-skill` получает только проверенный outline, использует `mozaika-weekly`, а execution receipt связан с SHA-256 outline и итогового PPTX;
- финальный статус `solved` разрешён только когда HTML-dashboard, HTML-презентация и PPTX существуют, открываются, согласованы по фактам и прошли требуемые проверки.

## Взаимодействие с владельцем

Не создавай storytelling cards и не проси выбрать storyline: во втором сценарии процесс, dashboard-шаблон и порядок рассказа уже утверждены. Сообщай о материальной автоматической очистке один раз. Остановись с доказательством только при смысловой неоднозначности или недостающих полномочиях.

## Служебные данные

- основной скилл: `mozaika`;
- сценарий: `weekly_autopilot`;
- идентификатор запуска: `{launch_id}`;
- язык результата: `{fields['output_language']}`.
"""
    data = text.encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    with path.open("xb") as handle:
        handle.write(data)
    return {"path": str(path.resolve()), "sha256": digest, "preservation": "append_only"}


def _write_assignment_file(api: Any, launch_id: str, scenario: str, fields: Dict[str, Any]) -> Dict[str, str]:
    if scenario == "weekly_autopilot":
        return _write_weekly_autopilot_assignment(api, launch_id, fields)
    path = api.skill_job_dir(launch_id) / "assignment.md"
    if scenario == "routine_report":
        owner_request = fields["instructions"]
        agenda_protocol = ""
        assignment_title = "Актуальный отчёт для руководства"
        outcome = (
            "Подготовь по предоставленным данным актуальный отчёт для руководства. "
            "Выдели главные изменения, отклонения, риски и возможности, сохранив согласованную структуру отчёта."
        )
        outputs = (
            "- сохранённые исходники, реестр источников и отчёт о качестве данных;\n"
            "- проверенный аналитический набор с отдельно сохранёнными исключениями;\n"
            "- обновлённый управляемый дашборд: обязательные таблицы с полезной выборкой данных, связанные фильтры, поиск, сортировка, настройка видимости разделов и плотности, общий сброс и краткие выводы для руководителя;\n"
            "- итоговая богатая диаграммами интерактивная HTML-презентация в одном автономном файле "
            "с плавными переходами между страницами;\n"
            "- последним шагом — отдельный редактируемый PPTX, созданный скиллом `presentation-skill` из проверенного outline;\n"
            "- браузерные материалы визуальной и интерактивной проверки и краткая записка о результате."
        )
        choice_rule = (
            "Не запрашивай согласование обычных операций. Обратись к владельцу один раз только если "
            "данные меняют смысл согласованного отчёта или не позволяют надёжно его собрать."
        )
        card_acceptance = ""
        pptx_rule = (
            "- после приёмки HTML-презентации последним шагом создай отдельный редактируемый `.pptx` именно скиллом "
            "`presentation-skill`; не используй `pptx` или `anthropic-pptx`; сверь общие числа и отрендери все слайды для визуальной проверки;\n"
        )
    elif scenario == "insight_deck":
        owner_request = fields["executive_brief"]
        agenda_protocol = """
## Обязательная пользовательская повестка — прочитай до любых действий

- Исходное поручение выше — обязательная программа, а не справочный контекст. Перед началом и перед завершением каждого этапа заново перечитай этот `assignment.md`; не работай только по пересказу предыдущего агента.
- Сохрани отдельными пунктами и в исходном порядке каждый вопрос, элемент списка, запрошенный срез, сравнение, метрику, период, сегмент, именованный раздел, вариант подачи и ограничение. Не объединяй и не переименовывай их так, чтобы связь с поручением стала неочевидной.
- Сначала ответь на эти пункты, затем добавляй проактивные инсайты. Дополнительная находка не может вытеснить обязательный пункт; при нехватке места перенеси дополнительное в приложение.
- Каждый пункт должен иметь видимый результат и интерпретацию на требуемой поверхности. Наличие фильтра без показанного ответа не считается покрытием. Если данных не хватает, явно покажи `partial` или `unanswered` с причиной вместо молчаливого пропуска или подмены похожим показателем.
- Если руководитель уже назвал альтернативные варианты подачи или планы рассказа, сделай карточки выбора из них; не подменяй их автоматически придуманными стратегиями. Если задан порядок, сохрани его либо объясни доказательное переупорядочивание, не теряя ни одного пункта.
- В каждом внутреннем handoff начни с раздела «Покрытие поручения»: перечисли все исходные пункты по порядку, их статус и точные места в следующем артефакте. Служебную карту не показывай в пользовательском HTML, но сами ответы обязаны быть видимы в дашборде, карточках, storyline, HTML-презентации и PPTX.
- Для этого сценария обязательно прочитай `references/user-agenda-coverage.md`; сокращённый storyline, карточка или outline никогда не заменяют исходное поручение.
"""
        assignment_title = "Инсайты и презентация для руководителя"
        outcome = (
            "Изучи предоставленные данные и найди выводы, которые важны руководителю. Покажи, что изменилось, "
            "где есть риски или возможности и какие решения стоит обсудить. Отделяй доказанные факты от гипотез и рекомендаций."
        )
        outputs = (
            "- сохранённые исходники, реестр источников и отчёт о качестве данных;\n"
            "- проверенный аналитический набор, журнал аномалий и отдельно сохранённые исключения;\n"
            "- неизменяемый `research-brief.json` с дословными вопросами, срезами, названиями и ограничениями поручения, а после анализа — `requirement-claim-map.json` со статусом и доказательствами по каждому пункту;\n"
            "- управляемый дашборд с ключевыми визуализациями, обязательными таблицами с полезной выборкой данных и проверяемыми ссылками на факты;\n"
            "- дашборд не содержит карточек выбора ни внизу, ни скрыто, ни во встроенных данных; карточки существуют только отдельным HTML;\n"
            "- красивые ровные настраиваемые графики и таблицы с работающими общими фильтрами, поиском и сортировкой; владелец может скрывать и возвращать разделы, менять плотность и полностью сбрасывать настройки; обязательны empty states, адаптивная сетка и browser QA без console errors;\n"
            "- предметный профиль владельца: подтверждённые KPI, решения, периоды, сегменты, предпочитаемые срезы и обратная связь, сохранённые версионно без чувствительных догадок и без заявления о fine-tuning;\n"
            "- один автономный файл `storytelling-cards.html` с двумя или тремя визуальными карточками разных структур рассказа: "
            "с главной мыслью, 3–5 смысловыми ходами, опорным доказательством и выводом для руководителя;\n"
            "- `storytelling-cards.html` и итоговый `selected-storytelling-card.html` используют точные светлые цвета и композицию "
            "runtime-брендбука Mozaika; тёмная, серая, бордовая или встроенная тема renderer не принимается;\n"
            "- внутренний `owner-choice.json` для проверки и продолжения пайплайна; владельцу отправляется HTML, а не JSON;\n"
            "- passing narrative-integrity audit для карточек и durable pending checkpoint, созданный до вопроса владельцу;\n"
            "- в сообщении выбора обязательно выведены два открываемых артефакта: сначала HTML-дашборд, затем `storytelling-cards.html`;\n"
            "- после выбора владельца — новый `selected-storytelling-card.html` только с выбранной карточкой, затем цельная история презентации, карта доказательств и структура слайдов;\n"
            "- selected checkpoint, отдельные audits выбранной карточки, storyline и презентации, а также прошедший `presentation_outline` gate до запуска renderer;\n"
            "- итоговая богатая диаграммами интерактивная HTML-презентация в одном автономном файле "
            "с плавными переходами между страницами;\n"
            "- после готовой презентации — внутренний `speaker-story-cards.json` и отдельный открываемый `speaker-story-cards.html`: ровно одна карточка-подсказка на каждый финальный слайд в том же порядке, с короткими репликами спикера, опорными доказательствами, визуальным ориентиром, переходом к следующему слайду, важной оговоркой и временем;\n"
            "- финальные карточки спикера собраны на обязательном шаблоне `brandbook/templates/speaker-story-cards.template.html`, проверены против текущих outline и презентации и переданы владельцу вместе с презентацией;\n"
            "- последним производственным шагом — отдельный редактируемый PPTX, который повторяет принятые порядок слайдов, факты и выводы HTML-презентации и создаётся только через `presentation-skill` с профилем `mozaika-insight`;\n"
            "- браузерные материалы визуальной и интерактивной проверки и краткое резюме для руководителя."
        )
        choice_rule = (
            "Не требуй согласования обычных действий. Остановись на один содержательный выбор: сначала открой и проверь "
            "HTML-дашборд и `storytelling-cards.html` в браузере, затем в одном сообщении реально выведи владельцу оба открываемых "
            "артефакта в этом порядке. Только после их вывода попроси выбрать близкую структуру рассказа. Не задавай вопрос выбора, "
            "если вывел лишь текст, имя или путь к файлу. Не выдавай внутренний JSON или текстовый A/B/C вместо HTML-карточек. "
            "Карточки нельзя добавлять, прятать или встраивать в dashboard HTML: проверь его DOM и payload, зарегистрируй dashboard "
            "только как `dashboard-html-without-storytelling-cards/v1`, а варианты держи только в отдельном файле. "
            "После ответа создай отдельный `selected-storytelling-card.html` ровно с выбранной карточкой; storyline-агент читает его, "
            "а не страницу со всеми вариантами. Эта одиночная карточка подтверждает стратегию и не является финальными подсказками спикера. "
            "После готовой презентации создай отдельную колоду подсказок по всем её слайдам. До вопроса сохрани pending checkpoint, после ответа — selected checkpoint; "
            "ошибка steering или голый номер варианта не считаются доставленным выбором. Все исходные и промежуточные артефакты сохрани."
        )
        card_acceptance = (
            "- страница выбора, выбранная карточка и финальная колода карточек спикера проходят отдельную browser QA и имеют отдельные design receipts "
            "с точным совпадением палитры runtime-брендбука и запретом тёмной темы; перед любой выдачей каждый фактический HTML проходит "
            "`brandbook_conformance` по полному исходнику и текущему SHA-256, а финальная колода дополнительно доказывает точный текущий хеш обязательного шаблона; финальная колода содержит ровно одну подсказку на каждый слайд презентации;\n"
        )
        pptx_rule = (
            "- после приёмки HTML-презентации и финальных карточек спикера последним шагом создай отдельный редактируемый `.pptx` именно скиллом `presentation-skill` с `--style-preset mozaika-insight`; не используй `pptx` или `anthropic-pptx`;\n"
            "- используй `data/brandbook/mozaika/templates/scenario-insight-presentation-skill-outline.example.json`, `data/brandbook/mozaika/references/scenario-insight-presentation-style.md` и референс `data/brandbook/mozaika/references/scenario-insight-ds-role-analytics-reference.pptx`; из референса бери только цвета, элементы, отступы и правила расположения — не копируй его данные, темы, количество, порядок или конкретную структуру слайдов;\n"
            "- PPTX должен повторять последовательность и утверждения принятой HTML-презентации, сохранять все пользовательские пункты и проверенные числа, иметь нативные редактируемые диаграммы и таблицы; отрендери и визуально проверь каждый слайд, а в receipt зафиксируй reference_usage=`visual-grammar-only` и точный SHA-256 референса;\n"
        )
    else:
        raise ValueError("неподдерживаемый сценарий")

    source_counts = {"url": 0, "file": 0, "directory": 0, "local_file": 0, "local_directory": 0}
    for source in fields["input_sources"]:
        if source["kind"] == "local_path":
            source_counts[f"local_{source['entry_type']}"] += 1
        else:
            source_counts[source["kind"]] += 1
    manifest_path = fields["launch_manifest_path"]
    text = f"""# {assignment_title}

## Поручение руководителя

{owner_request}

{agenda_protocol}

## Ожидаемый результат

{outcome}

## Материалы

- манифест запуска: `{manifest_path}`;
- URL: {source_counts['url']}; загруженных файлов: {source_counts['file']}; загруженных папок: {source_counts['directory']};
- локальных файлов по ссылке: {source_counts['local_file']}; локальных папок по ссылке: {source_counts['local_directory']};
- авторитетный список источников, подтверждённые владельцем абсолютные пути и пути к локальным копиям находятся в манифесте;
- на первом этапе скопируй каждый источник `local_path` в рабочее хранилище кампании потоковой файловой операцией, не читай файл целиком в контекст или память, не изменяй оригинал и после копирования проверь размер и SHA-256.

## Артефакты на выходе

{outputs}

## Критерии приёмки

- каждый существенный вывод трассируется до источника и проходит арифметическую и смысловую проверку;
- сначала создай, зарегистрируй и проверь immutable `mozaika-research-brief/v1`: дословно выдели из поручения все пункты, которые руководитель просит исследовать, названия и глобальные ограничения; после анализа создай и проверь `mozaika-requirement-claim-map/v1`; каждый пункт должен получить доказательный ответ либо явный статус частичного ответа/нехватки данных, появиться в дашборде, блоке покрытия каждой карточки и быть сопоставлен с конкретными экранами итоговой презентации;
- если руководитель указал название исследования, сохрани его отдельным полем `research_title_verbatim` без перевода, сокращения или редакторского переименования; включи эту точную строку в заголовок дашборда, единый study-kicker каждой карточки варианта истории и выбранной карточки, storyline и заголовок итоговой презентации; смысловой заголовок варианта не должен дублировать название исследования;
- все пользовательские и зрительские артефакты очищены от служебной информации: не показывай номера вариантов, внутренние идентификаторы и `claim_ids`, версии схем и контрактов, хеши, файловые пути, названия стадий, статусы проверок и отладочные сведения; ссылки на источники, даты, единицы измерения, определения и полезные оговорки сохраняй; техническую трассировку держи только во внутренних реестрах, контрактах и квитанциях;
- охват сетевых коллекций не сокращается молча: все дочерние наборы перечислены или явно помечены как недоступные;
- все исходные материалы, исключённые записи и промежуточные результаты сохранены как новые неизменяемые артефакты; удалять или перезаписывать их нельзя;
- перед каждым этапом Mozaika заново сравнивает готовые внешние скиллы, сначала подходящие установленные Anthropic-скиллы, и сохраняет обоснование выбора; одноразовые непроверенные скрипты не подменяют ролевой контракт;
- презентацию создаёт роль `mozaika-presentation-agent` только как богатый автономный HTML: с экранной и клавиатурной навигацией, полноэкранным и обзорным режимами, адаптивными интерактивными графиками, доступностью, печатью и реальной проверкой в браузере;
- любое продолжение после выбора владельца остаётся этой же кампанией Mozaika: восстанови исходный `assignment.md` и selected checkpoint, заново выбери и вызови ролевые скиллы; запрещено подменять `html-presentation-studio` или шаблон карточек одноразовым `run_script`, даже если скрипт вручную подписан как Mozaika;
- перед приёмкой каждого дашборда, страницы storytelling-карточек, выбранной карточки, презентации и финальной колоды карточек спикера независимый `mozaika-business-language-validator-agent` сначала защищает дословные пользовательские заголовки и пункты поручения, затем отдельно проверяет свободные заголовки и основной текст по `references/business-language-rules.md`; действует в режиме `pass by default`, отклоняет только бесспорные критические сбои — потерю защищённого текста, невосстановимый смысл, материальное искажение данных, грубую враждебность или служебную утечку — и для каждого возвращает одну минимальную формулировку без изменения фактов, цифр и оговорок; канцелярит, слабые заголовки, длину, повторы и просто неидеальный тон пропускает без замечаний; итог требует успешных `mozaika-business-language-audit/v1` для всех поверхностей сценария;
- после успешной языковой проверки дашборда, презентации и финальных карточек спикера независимый `mozaika-visual-validator-agent` проверяет в реальном браузере все экраны и интерактивные состояния на широком, среднем и узком viewport: диаграммы и подписи не пересекаются и не выходят из контейнеров, peer-отступы не имеют сильных выбросов, заявленное центрирование геометрически точно; без трёх успешных `mozaika-visual-layout-audit/v1` для insight-сценария итог не принимается;
- итоговая HTML-презентация богата содержательными диаграммами, графиками, схемами и таблицами, которые раскрывают доказательства; переходы между страницами плавные и поддерживают ход истории, а при `prefers-reduced-motion` отключаются без потери смысла;
- insight-презентация запускается только после selected checkpoint, отдельного storyline, passing narrative-integrity audit и deterministic `presentation_outline` gate; outline содержит уникальные slide ids и точное соответствие каждого пункта поручения существующим claim-bearing экранам;
- после приёмки insight-презентации роль `mozaika-speaker-cards-agent` создаёт по обязательному шаблону брендбука ровно одну доказательную карточку-подсказку на каждый слайд; `speaker_story_cards` gate сверяет порядок, slide ids, заголовки, claims, текущие хеши презентации/outline/шаблона и только затем разрешает финальную доставку обоих HTML;
- перед каждым `send_file` для `storytelling-cards.html`, `selected-storytelling-card.html`, презентации и `speaker-story-cards.html` вызови `validate_gate(gate="brandbook_conformance", ...)` с полным неизменяемым HTML, его текущим SHA-256 и artifact index; маркеры и цвета проверяются по фактическим байтам, дизайн-квитанция или скриншот эту проверку не заменяют; Mozaika не имеет тёмного варианта брендбука;
- итоговый HTML не загружает из сети scripts, styles, fonts, images, chart libraries или iframes; проверенный сторонний runtime допустим только встроенным в автономный файл;
{card_acceptance}- для этапа презентации первым оценивается назначенный владельцем скилл `html-presentation-studio`; Anthropic HTML-скиллы используются как поддержка сложных визуализаций или как обоснованный резерв;
{pptx_rule}- скилл `pptx` не используется в сценариях Mozaika;
- все материалы для владельца и обсуждение с ним ведутся по-русски; английские технические идентификаторы сохраняются только там, где их нельзя безопасно перевести;
- финальный статус отражает фактическую полноту и качество проверки, а не только наличие файлов.

## Взаимодействие с владельцем

{choice_rule}

## Служебные данные

- основной скилл: `mozaika`;
- сценарий: `{scenario}`;
- идентификатор запуска: `{launch_id}`;
- язык результата: `{fields['output_language']}`.
"""
    data = text.encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    with path.open("xb") as handle:
        handle.write(data)
    return {"path": str(path.resolve()), "sha256": digest, "preservation": "append_only"}


def _launch_fields(api: Any, scenario: str, body: Dict[str, Any]) -> Dict[str, Any]:
    launch_id = f"mozaika-{scenario}-{uuid.uuid4().hex}"
    raw_sources = body.get("sources")
    if raw_sources is None:
        raw_sources = _legacy_sources(body)
    input_sources, stored = _store_sources(api, launch_id, raw_sources)
    source_urls = [item["url"] for item in input_sources if item["kind"] == "url"]
    local_paths = [item for item in input_sources if item["kind"] == "local_path"]
    fields: Dict[str, Any] = {
        "launch_id": launch_id,
        "input_sources_contract": "mozaika-input-sources/v2",
        "input_sources": input_sources,
        "input_files": stored,
        "local_paths": local_paths,
        "source_urls": source_urls,
        "source_hint": "\n".join(source_urls),
    }
    if scenario == "routine_report":
        fields["instructions"] = _clean(body.get("instructions"))
        language_basis = fields["instructions"]
    elif scenario == "insight_deck":
        fields["executive_brief"] = _clean(body.get("executive_brief"))
        language_basis = fields["executive_brief"]
    elif scenario == "weekly_autopilot":
        fields["weekly_brief"] = _clean(body.get("weekly_brief"), required=True)
        language_basis = fields["weekly_brief"]
    else:
        raise ValueError("неподдерживаемый сценарий")
    fields["output_language"] = "ru" if _CYRILLIC.search(language_basis + " ".join(source_urls)) else "inherit_owner"
    fields["launch_manifest_path"] = str((api.skill_job_dir(launch_id) / "launch-manifest.json").resolve())
    fields["assignment_file"] = _write_assignment_file(api, launch_id, scenario, fields)
    _write_launch_manifest(api, launch_id, scenario, fields)
    return fields


def register(api: Any) -> None:
    """Register two owner-only scenario routes and launch widgets."""

    def request_owner_choice_tool(ctx: Any, **kwargs: Any) -> str:
        return _request_owner_choice(api, ctx, **kwargs)

    api.register_tool(
        "validate_gate",
        _validate_gate,
        description=(
            "Deterministically validate Mozaika scope, claims, frozen requirements, narrative integrity, "
            "durable owner decisions, presentation admission, actual HTML brandbook conformance, "
            "append-only artifacts, speaker cards, or completion gates. "
            "Pass a contract-shaped JSON object; the tool reads no files and makes no changes."
        ),
        schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "gate": {"enum": ["scope", "claims", "artifacts", "research_brief", "requirement_claim_map", "narrative_integrity", "owner_decision", "owner_choice", "presentation_outline", "brandbook_conformance", "speaker_story_cards", "completion"]},
                "payload": {"type": "object"},
            },
            "required": ["gate", "payload"],
        },
        timeout_sec=10,
    )
    api.register_tool(
        "request_owner_choice",
        request_owner_choice_tool,
        description=(
            "After the verified Mozaika dashboard and storytelling-cards HTML have both been delivered, "
            "publish two or three narrative choices as branded cards in the Mozaika Insights widget, "
            "keep this foreground task alive, and return the owner's click to this same tool call. "
            "Use a stable question_id from the durable pending checkpoint. A repeated call with the same "
            "immutable request recovers an already saved answer; never guess on status=waiting."
        ),
        schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "question_id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$"},
                "run_id": {"type": "string", "minLength": 1, "maxLength": 128},
                "title": {"type": "string", "minLength": 1, "maxLength": 140},
                "question": {"type": "string", "minLength": 1, "maxLength": 600},
                "options": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 3,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$"},
                            "headline": {"type": "string", "minLength": 1, "maxLength": 120},
                            "main_thought": {"type": "string", "minLength": 1, "maxLength": 320},
                            "story_beats": {
                                "type": "array",
                                "minItems": 2,
                                "maxItems": 4,
                                "items": {"type": "string", "minLength": 1, "maxLength": 180},
                            },
                            "executive_implication": {"type": "string", "minLength": 1, "maxLength": 260},
                        },
                        "required": ["id", "headline", "main_thought", "story_beats", "executive_implication"],
                    },
                },
                "recommended_option_id": {"type": "string", "minLength": 1, "maxLength": 64},
                "dashboard_artifact_id": {"type": "string", "minLength": 1, "maxLength": 160},
                "dashboard_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "cards_artifact_id": {"type": "string", "minLength": 1, "maxLength": 160},
                "cards_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "checkpoint_artifact_id": {"type": "string", "minLength": 1, "maxLength": 160},
                "checkpoint_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "wait_seconds": {"type": "integer", "minimum": 1, "maximum": _CHOICE_WAIT_MAX_SEC, "default": _CHOICE_WAIT_DEFAULT_SEC},
            },
            "required": [
                "question_id", "run_id", "title", "question", "options", "recommended_option_id",
                "dashboard_artifact_id", "dashboard_sha256", "cards_artifact_id", "cards_sha256",
                "checkpoint_artifact_id", "checkpoint_sha256",
            ],
        },
        timeout_sec=1720,
    )

    async def local_picker_route(request: Request) -> JSONResponse:
        try:
            body = await _read_json_body(request)
            result = await asyncio.to_thread(_create_path_selection, api, str(body.get("kind") or ""))
            return JSONResponse(result)
        except (ValueError, TypeError) as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        except RuntimeError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=503)
        except OSError:
            api.log("error", "mozaika: native path picker failed")
            return JSONResponse({"ok": False, "error": "не удалось открыть системный выбор пути"}, status_code=500)

    async def task_presets_route(_request: Request) -> JSONResponse:
        try:
            presets = await asyncio.to_thread(_load_task_presets)
            return JSONResponse({"ok": True, "presets": presets})
        except RuntimeError as exc:
            api.log("error", f"mozaika: task presets unavailable: {exc}")
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)

    async def weekly_task_presets_route(_request: Request) -> JSONResponse:
        try:
            presets = await asyncio.to_thread(_load_task_presets, "weekly_autopilot")
            return JSONResponse({"ok": True, "presets": presets})
        except RuntimeError as exc:
            api.log("error", f"mozaika: weekly task presets unavailable: {exc}")
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)

    async def pending_choices_route(_request: Request) -> JSONResponse:
        try:
            questions = await asyncio.to_thread(_list_pending_owner_choices, api)
            return JSONResponse({"ok": True, "questions": questions}, headers={"Cache-Control": "no-store"})
        except OSError:
            api.log("error", "mozaika: could not read pending owner choices")
            return JSONResponse({"ok": False, "error": "не удалось прочитать ожидающие решения"}, status_code=500)

    async def answer_choice_route(request: Request) -> JSONResponse:
        try:
            body = await _read_limited_json_body(request)
            answer = await asyncio.to_thread(_submit_owner_choice, api, body)
            return JSONResponse({
                "ok": True,
                "status": "answered",
                "question_id": answer.get("question_id"),
                "selected_option_id": answer.get("selected_option_id"),
                "answered_at": answer.get("answered_at"),
            })
        except PayloadTooLarge as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=413)
        except FileNotFoundError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)
        except PermissionError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=403)
        except RuntimeError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=409)
        except (ValueError, TypeError) as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        except OSError:
            api.log("error", "mozaika: could not persist owner choice")
            return JSONResponse({"ok": False, "error": "не удалось сохранить выбор"}, status_code=500)

    async def routine_route(request: Request) -> JSONResponse:
        try:
            body = await _read_json_body(request)
            fields = await asyncio.to_thread(_launch_fields, api, "routine_report", body)
        except PayloadTooLarge as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=413)
        except (ValueError, TypeError) as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        except OSError:
            api.log("error", "mozaika: could not persist routine upload")
            return JSONResponse({"ok": False, "error": "не удалось сохранить выбранные файлы"}, status_code=500)
        result = await asyncio.to_thread(_inject, api, "routine_report", fields)
        if result.get("ok"):
            result["file_count"] = len(fields["input_files"]) + sum(
                item.get("entry_type") == "file" for item in fields["local_paths"]
            )
            result["source_count"] = len(fields["input_sources"])
            result["url_count"] = len(fields["source_urls"])
        return JSONResponse(result, status_code=202 if result.get("ok") else 502)

    async def insight_route(request: Request) -> JSONResponse:
        try:
            body = await _read_json_body(request)
            fields = await asyncio.to_thread(_launch_fields, api, "insight_deck", body)
        except PayloadTooLarge as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=413)
        except (ValueError, TypeError) as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        except OSError:
            api.log("error", "mozaika: could not persist insight upload")
            return JSONResponse({"ok": False, "error": "не удалось сохранить выбранные файлы"}, status_code=500)
        result = await asyncio.to_thread(_inject, api, "insight_deck", fields)
        if result.get("ok"):
            result["file_count"] = len(fields["input_files"]) + sum(
                item.get("entry_type") == "file" for item in fields["local_paths"]
            )
            result["source_count"] = len(fields["input_sources"])
            result["url_count"] = len(fields["source_urls"])
        return JSONResponse(result, status_code=202 if result.get("ok") else 502)

    async def weekly_route(request: Request) -> JSONResponse:
        try:
            body = await _read_json_body(request)
            fields = await asyncio.to_thread(_launch_fields, api, "weekly_autopilot", body)
        except PayloadTooLarge as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=413)
        except (ValueError, TypeError) as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        except OSError:
            api.log("error", "mozaika: could not persist weekly autopilot upload")
            return JSONResponse({"ok": False, "error": "не удалось сохранить выбранные файлы"}, status_code=500)
        result = await asyncio.to_thread(_inject, api, "weekly_autopilot", fields)
        if result.get("ok"):
            result["file_count"] = len(fields["input_files"]) + sum(
                item.get("entry_type") == "file" for item in fields["local_paths"]
            )
            result["source_count"] = len(fields["input_sources"])
            result["url_count"] = len(fields["source_urls"])
        return JSONResponse(result, status_code=202 if result.get("ok") else 502)

    api.register_route("scenario/task-presets", task_presets_route, methods=("GET",))
    api.register_route("scenario/weekly-task-presets", weekly_task_presets_route, methods=("GET",))
    api.register_route("scenario/local/pick", local_picker_route, methods=("POST",))
    api.register_route("scenario/choice/pending", pending_choices_route, methods=("GET",))
    api.register_route("scenario/choice/answer", answer_choice_route, methods=("POST",))
    api.register_route("scenario/routine/start", routine_route, methods=("POST",))
    api.register_route("scenario/insight/start", insight_route, methods=("POST",))
    api.register_route("scenario/weekly/start", weekly_route, methods=("POST",))

    api.register_ui_tab(
        "insights",
        "Mozaika · Инсайты",
        icon="insights",
        render={
            "kind": "module",
            "entry": "insight-widget.js",
            "span": 2,
        },
    )
    api.register_ui_tab(
        "routine",
        "Mozaika · Рутинный отчёт",
        icon="repeat",
        render={
            "kind": "module",
            "entry": "routine-widget.js",
            "span": 2,
        },
    )
    api.log("info", "mozaika: registered two scenario launch widgets")


__all__ = ["register"]
