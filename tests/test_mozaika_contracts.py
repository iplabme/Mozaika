from __future__ import annotations

import json
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "mozaika"
CONTRACTS = SKILL / "contracts"


class MozaikaContractTests(unittest.TestCase):
    def test_widget_prompt_limit_is_8000_in_browser_and_backend(self):
        plugin_path = SKILL / "plugin.py"
        spec = importlib.util.spec_from_file_location("mozaika_plugin_prompt_limit", plugin_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertEqual(module._MAX_PROMPT_CHARS, 8000)
        self.assertEqual(
            module._clean("я" * 8000, max_chars=module._MAX_PROMPT_CHARS),
            "я" * 8000,
        )
        with self.assertRaisesRegex(ValueError, "8000"):
            module._clean("я" * 8001, max_chars=module._MAX_PROMPT_CHARS)

        for widget_name in ("insight-widget.js", "routine-widget.js"):
            widget = (SKILL / widget_name).read_text(encoding="utf-8")
            self.assertIn("const MAX_PROMPT_CHARS = 8000;", widget)
            self.assertIn('maxlength="${MAX_PROMPT_CHARS}"', widget)

    def test_every_contract_is_valid_draft_2020_12_schema(self):
        for path in sorted(CONTRACTS.glob("*.schema.json")):
            with self.subTest(path=path.name):
                schema = json.loads(path.read_text(encoding="utf-8"))
                Draft202012Validator.check_schema(schema)

    def test_bootstrap_pool_matches_version_1_3_adaptive_schema(self):
        schema = json.loads((CONTRACTS / "agent-pool.schema.json").read_text(encoding="utf-8"))
        config = json.loads((SKILL / "config" / "agent-pool.example.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(config)
        self.assertEqual(config["contract_version"], "1.3")
        self.assertEqual(config["runtime_compatibility"]["default"]["structured_protocol"], "native")
        self.assertEqual(
            config["runtime_compatibility"]["deepseek"]["fallback_errors"],
            ["Thinking mode does not support this tool_choice"],
        )
        self.assertFalse(config["artifact_policy"]["allow_delete"])
        design = config["design_system"]
        self.assertEqual(design["authority"], "owner_brandbook")
        self.assertEqual(design["runtime_path"], "data/brandbook/mozaika/BRANDBOOK.md")
        self.assertFalse(design["renderer_defaults_allowed"])
        self.assertEqual(design["receipt_contract"], "mozaika-design-receipt/v1")
        selection = config["skill_selection"]
        self.assertEqual(selection["mode"], "evaluate_before_each_stage")
        self.assertEqual(selection["source_priority"][0], "owner_designated_installed_reviewed")
        self.assertEqual(len(selection["installed_anthropic_skills"]), 9)
        self.assertEqual(selection["external_catalog"], "references/external-skill-catalog.md")
        self.assertEqual(selection["excluded_skills"], ["anthropic-pptx"])
        self.assertEqual(selection["owner_designated_presentation_skill"], "html-presentation-studio")
        self.assertEqual(selection["presentation_candidate_hints"][0], "html-presentation-studio")
        self.assertTrue(all(name.startswith("anthropic-") for name in selection["installed_anthropic_skills"]))
        self.assertTrue(config["skill_pools"]["adaptive-full"]["required_selection_receipts"])
        presentation = config["agents"]["presentation"]
        self.assertEqual(presentation["options"]["output_format"], "html")
        self.assertEqual(presentation["options"]["delivery_mode"], "self-contained-single-file")
        self.assertEqual(presentation["options"]["preferred_renderer_skill"], "html-presentation-studio")
        self.assertTrue(presentation["options"]["require_keyboard_navigation"])
        self.assertTrue(presentation["options"]["require_fullscreen"])
        self.assertTrue(presentation["options"]["require_overview"])
        self.assertTrue(presentation["options"]["require_evidence_rich_diagrams"])
        self.assertTrue(presentation["options"]["require_smooth_page_transitions"])
        self.assertEqual(presentation["options"]["brandbook_theme"], "mozaika-reference")
        self.assertTrue(presentation["options"]["design_receipt_required"])
        self.assertEqual(presentation["options"]["agenda_reference"], "references/user-agenda-coverage.md")
        self.assertTrue(presentation["options"]["reread_assignment_before_render"])
        self.assertTrue(config["agents"]["data"]["options"]["owner_items_first"])
        self.assertTrue(config["agents"]["dashboard"]["options"]["filter_alone_is_not_coverage"])
        self.assertTrue(config["agents"]["dashboard"]["options"]["owner_named_choices_take_priority"])
        self.assertTrue(config["agents"]["storyline"]["options"]["proactive_insights_after_owner_items"])
        self.assertTrue(config["agents"]["pptx"]["options"]["preserve_html_owner_agenda_coverage"])
        self.assertTrue((ROOT / "skills" / "mozaika" / "references" / "user-agenda-coverage.md").is_file())
        self.assertTrue(config["agents"]["dashboard"]["options"]["brandbook_required"])
        self.assertTrue(config["agents"]["storyline"]["options"]["brandbook_ref_required"])
        self.assertEqual(config["pipelines"]["routine_report"], ["data", "dashboard", "presentation", "pptx"])
        self.assertEqual(config["pipelines"]["insight_deck"][-2:], ["speaker_cards", "pptx"])
        self.assertEqual(
            config["pipelines"]["weekly_autopilot"],
            ["data", "dashboard", "anomaly_analysis", "presentation", "pptx"],
        )
        self.assertEqual(config["agents"]["anomaly_analysis"]["agent_id"], "mozaika-anomaly-analysis-agent")
        pptx = config["agents"]["pptx"]
        self.assertEqual(pptx["agent_id"], "mozaika-pptx-agent")
        self.assertEqual(pptx["options"]["required_renderer_skill"], "presentation-skill")
        self.assertEqual(pptx["options"]["style_preset_by_scenario"]["insight_deck"], "mozaika-insight")
        self.assertEqual(pptx["options"]["reference_usage_by_scenario"]["insight_deck"], "visual-grammar-only")
        self.assertEqual(pptx["options"]["forbidden_renderer_skills"], ["pptx", "anthropic-pptx"])
        speaker = config["agents"]["speaker_cards"]
        self.assertEqual(speaker["agent_id"], "mozaika-speaker-cards-agent")
        self.assertEqual(speaker["output_contract"], "mozaika-speaker-story-cards/v1")
        self.assertTrue(speaker["options"]["one_card_per_slide"])
        self.assertEqual(speaker["options"]["template_path"], "data/brandbook/mozaika/templates/speaker-story-cards.template.html")
        validator = config["agents"]["visual_validator"]
        self.assertEqual(validator["agent_id"], "mozaika-visual-validator-agent")
        self.assertEqual(validator["options"]["invocations"], ["after_dashboard_language_pass", "after_presentation_language_pass", "after_speaker_story_cards_language_pass"])
        self.assertEqual(validator["options"]["max_center_offset_px"], 2)
        language_validator = config["agents"]["business_language_validator"]
        self.assertEqual(language_validator["agent_id"], "mozaika-business-language-validator-agent")
        self.assertEqual(language_validator["options"]["separate_passes"], ["free_headings", "body_text"])
        self.assertEqual(language_validator["options"]["baseline_method"], "mozaika-business-language-rules")
        self.assertTrue(language_validator["options"]["supporting_skill_optional"])
        self.assertTrue(language_validator["options"]["block_only_critical_failures"])
        self.assertEqual(language_validator["options"]["block_threshold"], "critical_only")
        self.assertTrue(language_validator["options"]["pass_when_uncertain"])
        self.assertFalse(language_validator["options"]["flag_style_preferences"])
        self.assertIn("explicit_prompt_point", language_validator["options"]["protected_verbatim_sources"])
        self.assertEqual(config["learning"]["owner_domain_profile_contract"], "mozaika-owner-domain-profile/v1")
        self.assertFalse(config["learning"]["sensitive_inference_allowed"])
        self.assertEqual(config["learning"]["training_mode"], "profile_memory_not_model_weights")
        for agent in config["agents"].values():
            self.assertNotIn("primary_skill", agent)
            self.assertNotIn("recommended_skills", agent)

    def test_brandbook_guidance_separates_contract_and_runtime_data_paths(self):
        guidance = (SKILL / "references" / "design-brandbook.md").read_text(encoding="utf-8")
        skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn('list_files(root="runtime_data", path="brandbook/mozaika")', guidance)
        self.assertIn('read_file(root="runtime_data", path="brandbook/mozaika/BRANDBOOK.md")', guidance)
        self.assertIn('Никогда не вызывай `root="runtime_data"` с `path="data/brandbook/..."`', guidance)
        self.assertIn("Keep the full `data/brandbook/...` form in contracts and receipts", skill_text)

    def test_owner_domain_profile_is_evidence_backed_and_not_model_training(self):
        schema = json.loads((CONTRACTS / "owner-domain-profile.schema.json").read_text(encoding="utf-8"))
        profile = {
            "contract_version": "mozaika-owner-domain-profile/v1",
            "profile_id": "economic-index",
            "knowledge_key": "mozaika-owner-domain-economic-index",
            "domain": {
                "name": "AI и рынок труда",
                "glossary": ["экспозиция"],
                "entity_hierarchies": ["страна → регион"],
                "time_grains": ["месяц"],
                "priority_kpis": ["AI-экспозиция"],
            },
            "decision_context": {
                "audiences": ["руководитель"],
                "recurring_decisions": ["выбор приоритетного рынка"],
                "priority_questions": ["где изменение существенно"],
            },
            "analysis_preferences": {
                "preferred_dimensions": ["страна"],
                "preferred_slices": ["малые развитые экономики"],
                "comparison_baselines": ["предыдущий месяц"],
                "evidence_threshold": "decision-grade",
                "recommendation_style": "кратко с рисками",
            },
            "learned_signals": [{
                "signal_id": "slice-country",
                "category": "slice",
                "value": "страна",
                "provenance": "explicit_statement",
                "evidence_refs": ["task:example"],
                "confidence": 1,
                "status": "confirmed",
                "first_seen_at": "2026-07-15T00:00:00Z",
                "last_seen_at": "2026-07-15T00:00:00Z",
            }],
            "feedback_history": [],
            "governance": {
                "owner_visible_and_editable": True,
                "versioned_not_overwritten": True,
                "no_sensitive_inference": True,
                "training_mode": "profile_memory_not_model_weights",
                "material_profile_changes_require_confirmation": True,
                "provisional_signals_cannot_drive_material_recommendations": True,
            },
            "predecessor_sha256": None,
            "updated_at": "2026-07-15T00:00:00Z",
        }
        Draft202012Validator(schema).validate(profile)

    def test_role_engines_and_all_bundle_skills_are_present(self):
        skills_root = ROOT / "skills"
        for name in ["huggingface-datasets", "duckdb-analytics", "antv-g2-dashboard", "executive-storytelling"]:
            with self.subTest(skill=name):
                self.assertTrue((skills_root / name / "SKILL.md").is_file())
        anthropic = {
            "anthropic-dashboard-architect": "dashboard-architect",
            "anthropic-data-validation": "data-validation",
            "anthropic-data-visualization": "data-visualization",
            "anthropic-interactive-dashboard-builder": "interactive-dashboard-builder",
            "anthropic-performance-analytics": "performance-analytics",
            "anthropic-pptx": "pptx",
            "anthropic-snowflake-semanticview": "snowflake-semanticview",
            "anthropic-sql-queries": "sql-queries",
            "anthropic-statistical-analysis": "statistical-analysis",
        }
        for name, source_name in anthropic.items():
            with self.subTest(anthropic_skill=name):
                manifest = (skills_root / name / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn(f"name: {source_name}", manifest)
        for legacy in {
            "dashboard-architect", "data-validation", "data-visualization",
            "interactive-dashboard-builder", "performance-analytics", "pptx",
            "snowflake-semanticview", "sql-queries", "statistical-analysis",
        }:
            with self.subTest(removed_legacy_skill=legacy):
                self.assertFalse((skills_root / legacy).exists())
        self.assertTrue((skills_root / "anthropic-dashboard-architect" / "scripts" / "template.html").is_file())
        self.assertTrue((skills_root / "anthropic-pptx" / "LICENSE.txt").is_file())
        self.assertTrue((skills_root / "anthropic-pptx" / "scripts" / "office" / "validate.py").is_file())
        self.assertTrue((skills_root / "html-presentation-studio" / "scripts" / "scaffold.py").is_file())
        self.assertTrue((skills_root / "html-presentation-studio" / "scripts" / "browser_audit.py").is_file())
        self.assertTrue((skills_root / "presentation-skill" / "scripts" / "build_deck.js").is_file())
        presentation_skill = (skills_root / "presentation-skill" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("mozaika-weekly", presentation_skill)
        self.assertIn("mozaika-insight", presentation_skill)
        presets = (skills_root / "presentation-skill" / "templates" / "presets.js").read_text(encoding="utf-8")
        self.assertIn("'mozaika-insight'", presets)
        for name, entry in [
            ("huggingface-datasets", "scripts/inventory.js"),
            ("duckdb-analytics", "scripts/analyze.js"),
            ("antv-g2-dashboard", "scripts/build_dashboard.js"),
        ]:
            source = (skills_root / name / entry).read_text(encoding="utf-8")
            self.assertIn("OUROBOROS_SKILL_STATE_DIR", source)

    def test_brandbook_is_complete_and_dark_red_is_not_the_mozaika_default(self):
        brandbook = ROOT / "brandbook"
        for relative in [
            "BRANDBOOK.md", "SOURCES.md", "tokens.css", "manifest.json",
            "references/anthropic-economic-index-dashboard.png",
            "references/anthropic-transparency-hub-cards.png",
            "references/anthropic-economic-index-report.png",
            "templates/speaker-story-cards.template.html",
            "references/scenario-2-weekly-autopilot.md",
            "references/scenario-2-sprint25-review-reference.pptx",
            "templates/scenario-2-dashboard.template.html",
            "templates/scenario-2-presentation.template.html",
            "templates/scenario-2-presentation-skill-outline.example.json",
            "references/scenario-insight-presentation-style.md",
            "references/scenario-insight-ds-role-analytics-reference.pptx",
            "templates/scenario-insight-presentation-skill-outline.example.json",
        ]:
            with self.subTest(relative=relative):
                self.assertTrue((brandbook / relative).is_file())
        scaffold = (ROOT / "skills" / "html-presentation-studio" / "scripts" / "scaffold.py").read_text(encoding="utf-8")
        self.assertIn('default="mozaika-reference"', scaffold)
        self.assertIn('"mozaika-reference"', scaffold)
        guide = (SKILL / "references" / "design-brandbook.md").read_text(encoding="utf-8")
        self.assertIn("источник правды", guide)
        self.assertIn("design-receipt.json", guide)
        manifest = json.loads((brandbook / "manifest.json").read_text(encoding="utf-8"))
        for item in [*manifest["references"], *manifest["templates"]]:
            asset = brandbook / item["file"]
            with self.subTest(manifest_asset=item["file"]):
                self.assertTrue(asset.is_file())
                self.assertEqual(item["sha256"], __import__("hashlib").sha256(asset.read_bytes()).hexdigest())
        template = brandbook / manifest["templates"][0]["file"]
        self.assertEqual(manifest["templates"][0]["artifact_type"], "speaker_story_cards")
        template_html = template.read_text(encoding="utf-8")
        self.assertNotIn("fonts.googleapis.com", template_html)
        self.assertIn("Что сказать", template_html)
        self.assertIn("Как перейти дальше", template_html)

    def test_scenario_2_html_templates_are_self_contained_and_executable(self):
        templates = ROOT / "brandbook" / "templates"
        for name in ["scenario-2-dashboard.template.html", "scenario-2-presentation.template.html"]:
            source = (templates / name).read_text(encoding="utf-8")
            with self.subTest(template=name):
                self.assertNotRegex(source, r"<(?:script|link|img)[^>]+(?:src|href)=[\"']https?://")
                self.assertIn("data-mozaika-brandbook=\"mozaika-brandbook/v1\"", source)
                scripts = [
                    body
                    for attrs, body in re.findall(r"<script([^>]*)>(.*?)</script>", source, flags=re.I | re.S)
                    if "application/json" not in attrs.lower()
                ]
                self.assertTrue(scripts)
                with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8") as handle:
                    handle.write("\n".join(scripts))
                    handle.flush()
                    result = subprocess.run(
                        ["node", "--check", handle.name],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_speaker_story_cards_contract_requires_one_evidence_linked_cue_per_slide(self):
        schema = json.loads((CONTRACTS / "speaker-story-cards.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["title"], "mozaika-speaker-story-cards/v1")
        self.assertEqual(schema["properties"]["scenario"]["const"], "insight_deck")
        self.assertEqual(schema["properties"]["cards"]["minItems"], 2)
        card = schema["$defs"]["card"]
        self.assertIn("say_this", card["required"])
        self.assertIn("visual_cue", card["required"])
        self.assertIn("transition", card["required"])
        self.assertEqual(card["properties"]["say_this"]["maxItems"], 4)

    def test_handoff_result_requires_fresh_engine_receipts(self):
        schema = json.loads((CONTRACTS / "handoff-envelope.schema.json").read_text(encoding="utf-8"))
        result = schema["$defs"]["result"]
        self.assertIn("engine_receipts", result["required"])
        receipt = schema["$defs"]["engine_receipt"]
        self.assertEqual(receipt["properties"]["review_status"]["const"], "fresh")
        self.assertEqual(receipt["properties"]["python_used"]["type"], "boolean")

    def test_skill_selection_requires_anthropic_priority_audit(self):
        schema = json.loads((CONTRACTS / "skill-selection.schema.json").read_text(encoding="utf-8"))
        self.assertIn("anthropic_priority", schema["required"])
        priority = schema["properties"]["anthropic_priority"]
        self.assertEqual(
            set(priority["required"]),
            {"matching_candidates", "selected_anthropic", "override_reason"},
        )
        candidate_sources = schema["properties"]["candidates"]["items"]["properties"]["source"]["enum"]
        self.assertIn("owner_anthropic_bundle", candidate_sources)
        self.assertIn("owner_designated", candidate_sources)

    def test_owner_choice_requires_visual_previews_and_claim_ids(self):
        schema = json.loads((CONTRACTS / "owner-choice.schema.json").read_text(encoding="utf-8"))
        option_required = set(schema["properties"]["options"]["items"]["required"])
        self.assertIn("claim_ids", option_required)
        self.assertIn("preview_artifact_id", option_required)
        self.assertIn("html_anchor", option_required)
        self.assertIn("card", option_required)
        card = schema["$defs"]["storytelling_card"]
        self.assertEqual(card["properties"]["story_beats"]["minItems"], 3)
        self.assertEqual(card["properties"]["story_beats"]["maxItems"], 5)
        self.assertEqual(schema["properties"]["visual_preview_required"]["const"], True)
        self.assertEqual(schema["properties"]["owner_surface_format"]["const"], "html")
        self.assertIn("dashboard_surface_artifact_id", schema["required"])
        self.assertIn("owner_surface_artifact_id", schema["required"])

    def test_dashboard_spec_requires_physically_separate_storytelling_cards(self):
        schema = json.loads((CONTRACTS / "dashboard-spec.schema.json").read_text(encoding="utf-8"))
        self.assertIn("surface_policy", schema["required"])
        self.assertEqual(
            schema["properties"]["surface_policy"]["const"],
            "separate-dashboard-and-storytelling-cards",
        )
        self.assertIn("owner_question", schema["properties"])
        self.assertIn("recommended_option_id", schema["properties"])
        self.assertIn("filters", schema["required"])
        self.assertIn("tables", schema["required"])
        self.assertIn("customization", schema["required"])
        self.assertIn("research_title_verbatim", schema["required"])
        self.assertIn("research_questions", schema["required"])
        then_required = set(schema["allOf"][0]["then"]["required"])
        self.assertEqual(then_required, {"owner_question", "recommended_option_id"})
        renderer = (ROOT / "skills" / "antv-g2-dashboard" / "scripts" / "build_dashboard.js").read_text(encoding="utf-8")
        self.assertIn("--cards-output", renderer)
        self.assertIn("buildStoryCardsHtml", renderer)
        self.assertIn("storytelling_cards.length && !args.cardsOutput", renderer)
        self.assertIn("assertSeparatedSurfaces", renderer)
        self.assertIn("dashboard-html-without-storytelling-cards/v1", renderer)

    def test_dashboard_audits_require_data_backed_interactivity(self):
        interaction_checks = {
            "filter_options_backed_by_data",
            "filter_targets_recomputed",
            "cross_filter_consistent",
            "no_decorative_controls",
        }
        design_schema = json.loads((CONTRACTS / "design-receipt.schema.json").read_text(encoding="utf-8"))
        design_dashboard_required = set(design_schema["allOf"][1]["then"]["properties"]["checks"]["required"])
        self.assertTrue(interaction_checks <= design_dashboard_required)

        layout_schema = json.loads((CONTRACTS / "visual-layout-audit.schema.json").read_text(encoding="utf-8"))
        layout_dashboard_required = set(layout_schema["allOf"][0]["then"]["properties"]["checks"]["required"])
        self.assertEqual(interaction_checks, layout_dashboard_required)

    def test_dashboard_renderer_never_embeds_storytelling_cards(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / "data"
            state = data / "state" / "skills" / "antv-g2-dashboard"
            output = state / "output" / "dashboard.html"
            cards_output = state / "output" / "storytelling-cards.html"
            spec = data / "dashboard-spec.json"
            state.mkdir(parents=True)
            spec.write_bytes((ROOT / "tests" / "fixtures" / "dashboard-spec-with-cards.json").read_bytes())

            fake_package = root / "node_modules" / "@antv" / "g2"
            (fake_package / "dist").mkdir(parents=True)
            (fake_package / "package.json").write_text('{"name":"@antv/g2","version":"0.0.0-test","main":"dist/g2.min.js"}', encoding="utf-8")
            (fake_package / "dist" / "g2.min.js").write_text("window.G2={Chart:class{options(){} render(){return Promise.resolve()}}};", encoding="utf-8")

            environment = os.environ.copy()
            environment["OUROBOROS_SKILL_STATE_DIR"] = str(state)
            environment["NODE_PATH"] = str(root / "node_modules")
            result = subprocess.run(
                [
                    node,
                    str(ROOT / "skills" / "antv-g2-dashboard" / "scripts" / "build_dashboard.js"),
                    "--spec", str(spec),
                    "--output", str(output),
                    "--cards-output", str(cards_output),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )
            receipt = json.loads(result.stdout)
            dashboard_html = output.read_text(encoding="utf-8")
            cards_html = cards_output.read_text(encoding="utf-8")
            self.assertEqual(receipt["schema"], "dashboard-html-without-storytelling-cards/v1")
            self.assertIn('data-mozaika-surface="dashboard-only"', dashboard_html)
            self.assertIn("Данные в таблицах", dashboard_html)
            self.assertIn("Управление данными", dashboard_html)
            self.assertIn("Настроить вид", dashboard_html)
            self.assertIn("Поиск по таблице", dashboard_html)
            self.assertIn("research_questions", dashboard_html)
            self.assertNotIn("Сфокусироваться на лидере", dashboard_html)
            self.assertNotIn('"storytelling_cards":', dashboard_html)
            self.assertNotIn('id="stories"', dashboard_html)
            self.assertIn('data-mozaika-surface="storytelling-cards-only"', cards_html)
            self.assertIn('data-mozaika-brandbook="mozaika-brandbook/v1"', cards_html)
            self.assertIn('--mozaika-canvas:#faf9f5', cards_html)
            self.assertIn('--mozaika-green-700:#388f76', cards_html)
            self.assertNotIn('#101512', cards_html.lower())
            self.assertNotIn('#18201b', cards_html.lower())
            self.assertIn("Сфокусироваться на лидере", cards_html)
            self.assertIn("Как вариант раскроет ваш запрос", cards_html)
            self.assertIn("Как распределяется показатель между вариантами?", cards_html)
            self.assertIn("beat-title", cards_html)
            self.assertIn("beat-message", cards_html)
            self.assertNotIn("Масштаб — Начать с доли лидера", cards_html)
            self.assertNotIn('"claim_ids":', dashboard_html)
            self.assertNotIn('"claim_ids":', cards_html)
            self.assertNotIn('"option_id":', cards_html)
            self.assertNotIn('"recommended_option_id":', cards_html)
            self.assertNotIn("claim-share", dashboard_html)
            self.assertNotIn("claim-share", cards_html)
            self.assertNotIn(">1. focus<", cards_html)

    def test_dashboard_renderer_rejects_duplicate_storytelling_copy(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / "data"
            state = data / "state" / "skills" / "antv-g2-dashboard"
            output = state / "output" / "dashboard.html"
            cards_output = state / "output" / "storytelling-cards.html"
            spec = data / "dashboard-spec.json"
            state.mkdir(parents=True)
            payload = json.loads((ROOT / "tests" / "fixtures" / "dashboard-spec-with-cards.json").read_text(encoding="utf-8"))
            payload["storytelling_cards"][0]["story_beats"][0]["message"] = "Масштаб"
            spec.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            fake_package = root / "node_modules" / "@antv" / "g2"
            (fake_package / "dist").mkdir(parents=True)
            (fake_package / "package.json").write_text('{"name":"@antv/g2","version":"0.0.0-test","main":"dist/g2.min.js"}', encoding="utf-8")
            (fake_package / "dist" / "g2.min.js").write_text("window.G2={Chart:class{options(){} render(){return Promise.resolve()}}};", encoding="utf-8")

            environment = os.environ.copy()
            environment["OUROBOROS_SKILL_STATE_DIR"] = str(state)
            environment["NODE_PATH"] = str(root / "node_modules")
            result = subprocess.run(
                [
                    node,
                    str(ROOT / "skills" / "antv-g2-dashboard" / "scripts" / "build_dashboard.js"),
                    "--spec", str(spec),
                    "--output", str(output),
                    "--cards-output", str(cards_output),
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("повторяют одну формулировку", result.stderr)
            self.assertFalse(output.exists())
            self.assertFalse(cards_output.exists())

    def test_html_presentation_audit_blocks_remote_assets_but_allows_source_links(self):
        scripts = ROOT / "skills" / "html-presentation-studio" / "scripts"
        spec = importlib.util.spec_from_file_location("mozaika_html_audit", scripts / "audit.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.path.insert(0, str(scripts))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.pop(0)
        with tempfile.TemporaryDirectory() as temporary:
            html = Path(temporary) / "presentation.html"
            html.write_text(
                "<html lang='ru'><head><meta name='viewport' content='width=device-width'></head>"
                "<body><section><h1>Вывод подтверждён данными</h1>"
                "<a href='https://example.com/source'>Источник</a>"
                "<img src='https://cdn.example.com/chart.png' alt='График'>"
                "</section><script>document.addEventListener('keydown',()=>{});function overview(){};"
                "function f(){document.body.requestFullscreen()}</script>"
                "<style>@media print{}@media (prefers-reduced-motion:reduce){*{animation:none}}</style>"
                "</body></html>",
                encoding="utf-8",
            )
            result = module.audit(html)
            self.assertEqual(result["external_dependencies"], ["https://cdn.example.com/chart.png"])
            self.assertTrue(any(item["code"] == "external-deps" and item["severity"] == "HIGH" for item in result["issues"]))
            html.write_text(html.read_text(encoding="utf-8").replace("<img src='https://cdn.example.com/chart.png' alt='График'>", ""), encoding="utf-8")
            result = module.audit(html)
            self.assertEqual(result["external_dependencies"], [])
            self.assertIn("https://example.com/source", result["external_urls"])

    def test_input_sources_contract_keeps_url_local_path_file_and_directory_typed(self):
        schema = json.loads((CONTRACTS / "input-sources.schema.json").read_text(encoding="utf-8"))
        stored = {
            "source_id": "source-02",
            "original_name": "data.csv",
            "relative_path": "data.csv",
            "stored_path": "/durable/data.csv",
            "size_bytes": 1,
            "sha256": "a" * 64,
            "mime": "text/csv",
            "artifact_kind": "user_input",
            "preservation": "append_only",
        }
        payload = {
            "contract_version": "mozaika-input-sources/v2",
            "sources": [
                {"source_id": "source-01", "kind": "url", "display_name": "Dataset", "url": "https://example.com/data", "fetch_status": "pending_data_stage"},
                {"source_id": "source-02", "kind": "file", "display_name": "data.csv", "file": stored},
                {"source_id": "source-03", "kind": "directory", "display_name": "folder", "file_count": 1, "size_bytes": 1, "files": [{**stored, "source_id": "source-03", "relative_path": "nested/data.csv"}]},
                {
                    "source_id": "source-04",
                    "kind": "local_path",
                    "display_name": "large.csv",
                    "path": "/Users/owner/large.csv",
                    "entry_type": "file",
                    "size_bytes": 999999999,
                    "selection_token": "b" * 32,
                    "selection_receipt": "/state/path-selections/receipt.json",
                    "copy_status": "pending_data_stage",
                    "preservation": "reference_only",
                },
            ],
        }
        Draft202012Validator(schema).validate(payload)

    def test_content_slides_require_claim_ids_and_language(self):
        schema = json.loads((CONTRACTS / "presentation-outline.schema.json").read_text(encoding="utf-8"))
        self.assertIn("output_language", schema["required"])
        self.assertIn("renderer_skill", schema["required"])
        self.assertIn("output_format", schema["required"])
        self.assertIn("design_system", schema["required"])
        self.assertIn("html_requirements", schema["required"])
        self.assertEqual(schema["properties"]["output_format"]["const"], "html")
        self.assertEqual(schema["properties"]["delivery_mode"]["const"], "self-contained-single-file")
        self.assertEqual(
            schema["properties"]["renderer_skill"]["not"]["enum"],
            ["anthropic-pptx", "presentation-skill"],
        )
        content_requirements = schema["$defs"]["content_slide"]["allOf"][1]["required"]
        self.assertIn("claim_ids", content_requirements)

    def test_external_skill_catalog_covers_the_installed_pool(self):
        catalog = (SKILL / "references" / "external-skill-catalog.md").read_text(encoding="utf-8")
        installed = sorted(path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md"))
        expected = {
            "analyze-report-data", "antv-g2-dashboard", "build-insight-dashboard",
            "build-routine-report", "anthropic-dashboard-architect", "anthropic-data-validation",
            "anthropic-data-visualization", "design-executive-storyline", "duckdb-analytics",
            "executive-storytelling", "huggingface-datasets", "anthropic-interactive-dashboard-builder",
            "html-presentation-studio", "mozaika", "anthropic-performance-analytics", "anthropic-pptx",
            "anthropic-snowflake-semanticview", "anthropic-sql-queries", "anthropic-statistical-analysis",
        }
        self.assertTrue(expected.issubset(set(installed)))
        for name in expected:
            with self.subTest(skill=name):
                self.assertIn(f"`{name}`", catalog)

    def test_anthropic_routing_guide_covers_all_original_skills(self):
        guide = (SKILL / "references" / "anthropic-skill-routing.md").read_text(encoding="utf-8")
        manifest = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        catalog = (SKILL / "references" / "external-skill-catalog.md").read_text(encoding="utf-8")
        names = {
            "anthropic-data-validation", "anthropic-data-visualization",
            "anthropic-dashboard-architect",
            "anthropic-interactive-dashboard-builder", "anthropic-performance-analytics",
            "anthropic-pptx", "anthropic-snowflake-semanticview",
            "anthropic-sql-queries", "anthropic-statistical-analysis",
        }
        for name in names:
            with self.subTest(skill=name):
                self.assertIn(f"`{name}`", guide)
        self.assertIn("instruction receipt", guide)
        self.assertIn("execution receipt", guide)
        self.assertIn("anthropic-skill-routing.md", manifest)
        self.assertIn("`presentation-skill`", catalog)
        for name in {
            "anthropic-data-validation", "anthropic-data-visualization",
            "anthropic-dashboard-architect",
            "anthropic-interactive-dashboard-builder", "anthropic-performance-analytics",
            "anthropic-pptx", "anthropic-snowflake-semanticview",
            "anthropic-sql-queries", "anthropic-statistical-analysis",
        }:
            with self.subTest(original_anthropic_skill=name):
                self.assertIn(f"`{name}`", catalog)

    def test_completion_schema_resolves_and_validates_all_gate_contracts(self):
        schemas = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in CONTRACTS.glob("*.schema.json")
        ]
        registry = Registry().with_resources(
            (schema["$id"], Resource.from_contents(schema))
            for schema in schemas
            if "$id" in schema
        )
        completion = next(schema for schema in schemas if schema.get("title") == "mozaika-completion-gate/v1")
        payload = {
            "contract_version": "mozaika-completion-gate/v1",
            "run_id": "run-1",
            "scenario": "routine_report",
            "owner_choice_gate_passed": False,
            "requested_status": "solved",
            "scope": {
                "contract_version": "mozaika-scope-ledger/v1",
                "run_id": "run-1",
                "source_kind": "single",
                "requested_mode": "all",
                "enumeration_artifact_ids": [],
                "scope_change_approved": False,
                "items": [{"source_id": "source", "uri": "artifact:data", "disposition": "analyzed", "artifact_ids": ["data"]}],
                "coverage": {"total": 1, "analyzed": 1, "owner_excluded": 0, "blocked": 0, "all_analyzed": True, "terminal_complete": True, "solved_coverage": True},
            },
            "claims": {
                "contract_version": "mozaika-claim-registry/v1",
                "run_id": "run-1",
                "scope_ledger_sha256": "a" * 64,
                "output_language": "ru",
                "claims": [{"claim_id": "fact", "text": "Факт", "kind": "observed", "status": "verified", "quantitative": False, "entity_sensitive": False, "evidence_artifact_ids": ["data"], "checks": [], "text_checks": []}],
            },
            "artifacts": {
                "contract_version": "mozaika-artifact-index/v1",
                "run_id": "run-1",
                "policy": {"mode": "append_only", "preserve_user_inputs": True, "preserve_stage_outputs": True, "allow_delete": False},
                "required_artifact_ids": ["data", "pptx", "pptx-qa"],
                "artifacts": [
                    {"artifact_id": "data", "kind": "user_input", "original_name": "data.csv", "uri": "artifact:data", "sha256": "b" * 64, "media_type": "text/csv", "schema": "raw/v1", "size_bytes": 1, "created_at": "2026-07-13T00:00:00Z", "source_task_id": "task-1", "source_stage_id": "data", "preserved": True, "immutable": True, "durable": True, "owner_visible": True},
                    {"artifact_id": "pptx", "kind": "pptx", "original_name": "report.pptx", "uri": "artifact:pptx", "sha256": "c" * 64, "media_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation", "schema": "editable-pptx/v1", "size_bytes": 2, "created_at": "2026-07-13T00:00:01Z", "source_task_id": "task-1", "source_stage_id": "pptx", "preserved": True, "immutable": True, "durable": True, "owner_visible": True},
                    {"artifact_id": "pptx-qa", "kind": "qa", "original_name": "pptx-montage.png", "uri": "artifact:pptx-qa", "sha256": "d" * 64, "media_type": "image/png", "schema": "rendered-slide-qa/v1", "size_bytes": 3, "created_at": "2026-07-13T00:00:02Z", "source_task_id": "task-1", "source_stage_id": "pptx", "preserved": True, "immutable": True, "durable": True, "owner_visible": True},
                ],
            },
            "runtime": {"execution_status": "ok", "objective_status": "passed", "review_status": "not_required", "verification_failures": False},
            "visual_qa": {"required": False, "status": "not_required", "artifact_ids": []},
            "brandbook_conformance_gates": [
                {
                    "ok": True, "gate": "brandbook_conformance", "errors": [], "warnings": [],
                    "metrics": {
                        "artifact_type": "presentation", "artifact_id": "presentation",
                        "html_sha256": "2" * 64, "source_checked": True,
                        "brandbook_version": "mozaika-brandbook/v1", "brandbook_marker": True,
                        "core_palette_exact": True, "forbidden_color_hits": 0,
                        "template_required": False, "template_exact": True, "template_sha256": None,
                    },
                }
            ],
            "design_receipts": [
                {
                    "contract_version": "mozaika-design-receipt/v1", "run_id": "run-1",
                    "stage_id": "dashboard", "artifact_type": "dashboard", "artifact_id": "dashboard",
                    "brandbook": {"authority": "owner_brandbook", "manifest_path": "data/brandbook/mozaika/manifest.json", "manifest_sha256": "d" * 64, "tokens_path": "data/brandbook/mozaika/tokens.css", "reference_ids": ["anthropic-economic-index-dashboard"]},
                    "instructions_passed": True,
                    "checks": {"warm_canvas": True, "typography_hierarchy": True, "artifact_pattern": True, "semantic_palette": True, "source_proximity": True, "no_forbidden_default_theme": True, "service_metadata_hidden": True, "dashboard_excludes_storytelling_cards": True, "aligned_grid": True, "charts_render_without_errors": True, "tables_readable": True, "filters_functional": True, "filter_options_backed_by_data": True, "filter_targets_recomputed": True, "cross_filter_consistent": True, "no_decorative_controls": True, "filter_reset_works": True, "table_search_functional": True, "table_sort_functional": True, "customization_controls_functional": True, "customization_reset_works": True, "responsive_no_overflow": True, "empty_states_clear": True, "console_errors_absent": True, "browser_verified": True},
                    "deviations": [], "owner_override_id": None, "status": "pass",
                },
                {
                    "contract_version": "mozaika-design-receipt/v1", "run_id": "run-1",
                    "stage_id": "presentation", "artifact_type": "presentation", "artifact_id": "presentation",
                    "brandbook": {"authority": "owner_brandbook", "manifest_path": "data/brandbook/mozaika/manifest.json", "manifest_sha256": "d" * 64, "tokens_path": "data/brandbook/mozaika/tokens.css", "reference_ids": ["anthropic-economic-index-report"]},
                    "instructions_passed": True,
                    "checks": {"warm_canvas": True, "typography_hierarchy": True, "artifact_pattern": True, "semantic_palette": True, "source_proximity": True, "no_forbidden_default_theme": True, "service_metadata_hidden": True, "diagram_rich": True, "smooth_page_transitions": True, "reduced_motion_fallback": True, "browser_verified": True},
                    "deviations": [], "owner_override_id": None, "status": "pass",
                },
            ],
            "business_language_audits": [
                {
                    "contract_version": "mozaika-business-language-audit/v1", "run_id": "run-1",
                    "audit_id": "language-dashboard", "artifact_type": "dashboard", "artifact_id": "dashboard",
                    "artifact_sha256": "1" * 64, "assignment_artifact_id": "assignment", "assignment_sha256": "3" * 64,
                    "output_language": "ru", "protected_verbatim": [],
                    "passes": {
                        "free_headings": {"items_checked": 4, "protected_items_skipped": 0, "blocking_failure_count": 0},
                        "body_text": {"items_checked": 8, "protected_items_skipped": 0, "blocking_failure_count": 0},
                    },
                    "checks": {"protected_extraction_complete": True, "protected_verbatim_unchanged": True, "meaning_recoverable": True, "no_material_misrepresentation": True, "no_grossly_offensive_or_hostile_tone": True, "no_service_metadata_leak": True, "critical_only_failures_blocked": True, "pass_when_uncertain": True},
                    "issues": [], "status": "pass",
                },
                {
                    "contract_version": "mozaika-business-language-audit/v1", "run_id": "run-1",
                    "audit_id": "language-presentation", "artifact_type": "presentation", "artifact_id": "presentation",
                    "artifact_sha256": "2" * 64, "assignment_artifact_id": "assignment", "assignment_sha256": "3" * 64,
                    "output_language": "ru",
                    "protected_verbatim": [{"kind": "owner_supplied_title", "text": "Отчёт по качеству", "source_ref": "assignment.md#title", "found_unchanged": True}],
                    "passes": {
                        "free_headings": {"items_checked": 5, "protected_items_skipped": 1, "blocking_failure_count": 0},
                        "body_text": {"items_checked": 10, "protected_items_skipped": 0, "blocking_failure_count": 0},
                    },
                    "checks": {"protected_extraction_complete": True, "protected_verbatim_unchanged": True, "meaning_recoverable": True, "no_material_misrepresentation": True, "no_grossly_offensive_or_hostile_tone": True, "no_service_metadata_leak": True, "critical_only_failures_blocked": True, "pass_when_uncertain": True},
                    "issues": [], "status": "pass",
                },
            ],
            "layout_audits": [
                {
                    "contract_version": "mozaika-visual-layout-audit/v1", "run_id": "run-1",
                    "audit_id": "layout-dashboard", "artifact_type": "dashboard", "artifact_id": "dashboard", "artifact_sha256": "e" * 64,
                    "viewports": [
                        {"width": 1440, "height": 1000, "screenshot_artifact_id": "dashboard-wide", "overlap_count": 0, "overflow_count": 0, "spacing_outlier_count": 0, "max_center_offset_px": 0.5},
                        {"width": 1024, "height": 768, "screenshot_artifact_id": "dashboard-medium", "overlap_count": 0, "overflow_count": 0, "spacing_outlier_count": 0, "max_center_offset_px": 1},
                        {"width": 390, "height": 844, "screenshot_artifact_id": "dashboard-narrow", "overlap_count": 0, "overflow_count": 0, "spacing_outlier_count": 0, "max_center_offset_px": 1.5}
                    ],
                    "checks": {"all_screens_inspected": True, "no_unintended_overlaps": True, "charts_within_bounds": True, "consistent_peer_spacing": True, "declared_centers_are_centered": True, "no_unintended_page_overflow": True, "interactive_states_inspected": True, "filter_options_backed_by_data": True, "filter_targets_recomputed": True, "cross_filter_consistent": True, "no_decorative_controls": True, "console_errors_absent": True},
                    "issues": [], "status": "pass"
                },
                {
                    "contract_version": "mozaika-visual-layout-audit/v1", "run_id": "run-1",
                    "audit_id": "layout-presentation", "artifact_type": "presentation", "artifact_id": "presentation", "artifact_sha256": "f" * 64,
                    "viewports": [
                        {"width": 1440, "height": 1000, "screenshot_artifact_id": "presentation-wide", "overlap_count": 0, "overflow_count": 0, "spacing_outlier_count": 0, "max_center_offset_px": 0.5},
                        {"width": 1024, "height": 768, "screenshot_artifact_id": "presentation-medium", "overlap_count": 0, "overflow_count": 0, "spacing_outlier_count": 0, "max_center_offset_px": 1},
                        {"width": 390, "height": 844, "screenshot_artifact_id": "presentation-narrow", "overlap_count": 0, "overflow_count": 0, "spacing_outlier_count": 0, "max_center_offset_px": 1.5}
                    ],
                    "checks": {"all_screens_inspected": True, "no_unintended_overlaps": True, "charts_within_bounds": True, "consistent_peer_spacing": True, "declared_centers_are_centered": True, "no_unintended_page_overflow": True, "interactive_states_inspected": True, "console_errors_absent": True},
                    "issues": [], "status": "pass"
                }
            ],
            "pptx_execution_receipt": {
                "skill_name": "presentation-skill",
                "review_status": "fresh",
                "style_preset": "mozaika-weekly",
                "reference_id": "scenario-2-sprint25-review-pptx",
                "reference_sha256": "d3a650c204ee9f9ea17daf94fae97a226e57ca13ecbbf7cf19e53f3e71969265",
                "reference_usage": "fixed-template",
                "outline_sha256": "9" * 64,
                "output_artifact_ids": ["pptx"],
                "rendered_slide_qa_artifact_ids": ["pptx-qa"],
                "status": "pass",
            },
            "unresolved": [],
        }
        validator = Draft202012Validator(completion, registry=registry)
        validator.validate(payload)

        del payload["layout_audits"][0]["checks"]["no_decorative_controls"]
        errors = list(validator.iter_errors(payload))
        self.assertTrue(errors, "dashboard audit without no_decorative_controls must fail")


if __name__ == "__main__":
    unittest.main()
