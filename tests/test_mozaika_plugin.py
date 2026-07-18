from __future__ import annotations

import importlib.util
import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "skills" / "mozaika" / "plugin.py"
OUROBOROS_REPO = ROOT.parent / "repo"
if OUROBOROS_REPO.is_dir():
    sys.path.insert(0, str(OUROBOROS_REPO))


def load_plugin():
    spec = importlib.util.spec_from_file_location("mozaika_plugin", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _Token:
    def use_in_request(self):
        return "test-token"


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return b'{"ok": true, "status": "queued", "task_id": "task-123"}'


class _Api:
    def __init__(self, state_dir=None):
        self.tools = []
        self.routes = []
        self.tabs = []
        self.state_dir = Path(state_dir or tempfile.mkdtemp())

    def register_tool(self, name, handler, **kwargs):
        self.tools.append((name, handler, kwargs))

    def register_route(self, path, handler, **kwargs):
        self.routes.append((path, handler, kwargs))

    def register_ui_tab(self, tab_id, title, **kwargs):
        from ouroboros.extension_ui_validation import validate_ui_render

        validate_ui_render(kwargs["render"])
        self.tabs.append((tab_id, title, kwargs))

    def get_skill_token(self):
        return _Token()

    def skill_job_dir(self, job_id):
        root = self.state_dir / "jobs" / job_id
        for child in ("assets", "output", "tmp"):
            (root / child).mkdir(parents=True, exist_ok=True)
        return root

    def get_state_dir(self):
        return str(self.state_dir)

    def log(self, *_args, **_kwargs):
        return None


class MozaikaPluginTests(unittest.TestCase):
    def test_registers_two_widgets_validation_and_live_owner_choice(self):
        plugin = load_plugin()
        api = _Api()
        plugin.register(api)
        self.assertEqual([item[0] for item in api.tools], ["validate_gate", "request_owner_choice"])
        tool_result = api.tools[0][1](object(), gate="scope", payload={})
        self.assertIsInstance(tool_result, str)
        self.assertEqual(json.loads(tool_result)["gate"], "scope")
        choice_schema = api.tools[1][2]["schema"]
        self.assertEqual(choice_schema["properties"]["options"]["minItems"], 2)
        self.assertEqual(choice_schema["properties"]["options"]["maxItems"], 3)
        self.assertEqual(
            [item[0] for item in api.routes],
            [
                "scenario/task-presets",
                "scenario/weekly-task-presets",
                "scenario/local/pick",
                "scenario/choice/pending",
                "scenario/choice/answer",
                "scenario/routine/start",
                "scenario/insight/start",
                "scenario/weekly/start",
            ],
        )
        self.assertEqual([item[0] for item in api.tabs], ["insights", "routine"])
        self.assertEqual([item[1] for item in api.tabs], ["Mozaika · Инсайты", "Mozaika · Рутинный отчёт"])
        self.assertEqual(
            [item[2]["render"]["entry"] for item in api.tabs],
            ["insight-widget.js", "routine-widget.js"],
        )
        self.assertEqual([item[2]["render"]["span"] for item in api.tabs], [2, 2])
        for widget_name in ("routine-widget.js", "insight-widget.js"):
            source = (PLUGIN.parent / widget_name).read_text(encoding="utf-8")
            self.assertIn("Перетащите файлы или папку сюда", source)
            self.assertIn("Файл или папка", source)
            self.assertIn("Добавить URL", source)
            self.assertIn("webkitdirectory", source)
            self.assertIn("scenario/local/pick", source)
            self.assertIn("chooseLocalPaths('directory')", source)
            self.assertIn("chooseLocalPaths('file')", source)
            self.assertIn("kind: 'local_path'", source)
            self.assertIn("selection_token", source)
            self.assertNotIn("typeof window.showDirectoryPicker", source)
            self.assertNotIn("closeDialog(localDialog); folderInput.click()", source)
            self.assertNotIn("До 500 файлов", source)
            self.assertNotIn("storyline", source)
            self.assertNotIn("MAX_FILE_BYTES", source)
            self.assertNotIn("MAX_TOTAL_BYTES", source)
            self.assertNotIn("файл больше 25 МБ", source)
            self.assertIn("display: inline-flex; align-items: center; justify-content: center", source)
            self.assertIn("height: 78px; min-height: 78px; max-height: 78px", source)
        insight_source = (PLUGIN.parent / "insight-widget.js").read_text(encoding="utf-8")
        self.assertIn("scenario/task-presets", insight_source)
        self.assertIn("scenario/insight/start", insight_source)
        self.assertIn("scenario/choice/pending", insight_source)
        self.assertIn("scenario/choice/answer", insight_source)
        self.assertIn("Данные для поиска инсайтов", insight_source)
        self.assertIn("taskField: 'executive_brief'", insight_source)
        self.assertIn("class=\"presets-pill\"", insight_source)
        self.assertIn("taskPresets.fixed_suffix", insight_source)
        self.assertIn("startsWith('Подготовь')", insight_source)
        self.assertIn("bottom: calc(100% + 12px)", insight_source)
        self.assertIn("z-index: 100", insight_source)
        self.assertIn("box-shadow: 0 0 0 2px #14141338", insight_source)
        self.assertNotIn(".presets-pill:hover, .presets-pill:focus-visible", insight_source)
        routine_source = (PLUGIN.parent / "routine-widget.js").read_text(encoding="utf-8")
        self.assertIn("scenario/weekly-task-presets", routine_source)
        self.assertIn("scenario/weekly/start", routine_source)
        self.assertIn("Данные для рутинного отчёта", routine_source)
        self.assertIn("taskField: 'weekly_brief'", routine_source)
        self.assertIn("class=\"presets-pill\"", routine_source)
        self.assertNotIn("scenario/choice/pending", routine_source)
        self.assertNotIn("scenario/choice/answer", routine_source)
        plugin_source = PLUGIN.read_text(encoding="utf-8")
        self.assertNotIn("_MAX_FILE_BYTES", plugin_source)
        self.assertNotIn("_MAX_TOTAL_FILE_BYTES", plugin_source)
        self.assertNotIn("_MAX_REQUEST_BYTES", plugin_source)
        self.assertNotIn("превышает 25 МБ", plugin_source)
        self.assertIn("_create_path_selection", plugin_source)
        self.assertIn("_validated_local_path", plugin_source)
        self.assertIn('command.extend(["--multiple", "--separator", "\\n"])', plugin_source)
        self.assertIn("presets = await asyncio.to_thread(_load_task_presets)", plugin_source)
        self.assertIn('await asyncio.to_thread(_launch_fields, api, "routine_report", body)', plugin_source)
        self.assertIn('await asyncio.to_thread(_launch_fields, api, "insight_deck", body)', plugin_source)

    def test_insight_task_presets_are_loaded_from_json_with_one_fixed_suffix(self):
        plugin = load_plugin()
        presets = plugin._load_task_presets()
        self.assertEqual(presets["contract_version"], "mozaika-task-presets/v1")
        self.assertEqual(presets["button_label"], "варианты задания")
        self.assertTrue(presets["fixed_suffix"].startswith("Подготовь"))
        self.assertEqual(len(presets["items"]), 4)
        self.assertEqual(
            [item["label"] for item in presets["items"]],
            [
                "Отчёт по метрикам качества производства",
                "Отчёт по моделям и CDS блоков",
                "Отчёт по AI-инициативам Банка для Президента",
                "Отчёт по AI-решениям Блока",
            ],
        )
        self.assertTrue(all("Подготовь" not in item["prefix"] for item in presets["items"]))

    def test_owner_selected_local_path_is_referenced_without_reading_or_base64(self):
        plugin = load_plugin()
        with tempfile.TemporaryDirectory() as tmp:
            api = _Api(tmp)
            source = Path(tmp) / "large.csv"
            source.write_bytes(b"a,b\n1,2\n")
            with mock.patch.object(plugin, "_run_native_picker", return_value=[str(source)]):
                picker = plugin._create_path_selection(api, "file")
            self.assertTrue(picker["ok"])
            self.assertFalse(picker["cancelled"])
            fields = plugin._launch_fields(
                api,
                "insight_deck",
                {
                    "sources": [{"kind": "local_path", **picker["sources"][0]}],
                    "executive_brief": "Найди инсайты",
                },
            )
            self.assertEqual(fields["input_files"], [])
            self.assertEqual(len(fields["local_paths"]), 1)
            local = fields["local_paths"][0]
            self.assertEqual(local["path"], str(source.resolve()))
            self.assertEqual(local["entry_type"], "file")
            self.assertEqual(local["size_bytes"], source.stat().st_size)
            self.assertEqual(local["copy_status"], "pending_data_stage")
            self.assertEqual(local["preservation"], "reference_only")
            manifest = json.loads(Path(fields["launch_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["local_paths"][0]["path"], str(source.resolve()))
            assignment = Path(fields["assignment_file"]["path"]).read_text(encoding="utf-8")
            self.assertIn("потоковой файловой операцией", assignment)
            self.assertIn("не изменяй оригинал", assignment)

    def test_inject_uses_fixed_loopback_and_owner_visible_chat(self):
        plugin = load_plugin()
        seen = {}

        def fake_urlopen(request, timeout):
            seen["url"] = request.full_url
            seen["timeout"] = timeout
            seen["token"] = request.headers.get("X-skill-token")
            seen["body"] = json.loads(request.data.decode("utf-8"))
            return _Response()

        fields = {
            "launch_id": "test-launch",
            "input_sources_contract": "mozaika-input-sources/v2",
            "input_sources": [{"source_id": "source-01", "kind": "file"}],
            "input_files": [{"original_name": "daily.csv", "stored_path": "/tmp/daily.csv"}],
            "source_urls": [],
            "source_hint": "",
            "instructions": "Refresh KPIs",
            "assignment_file": {
                "path": "/tmp/mozaika/assignment.md",
                "sha256": "a" * 64,
                "preservation": "append_only",
            },
        }
        with mock.patch.object(plugin.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = plugin._inject(_Api(), "routine_report", fields)

        self.assertTrue(result["ok"])
        self.assertEqual(result["task_id"], "task-123")
        self.assertEqual(seen["url"], "http://127.0.0.1:8767/chat/inject")
        self.assertEqual(seen["timeout"], 5)
        self.assertEqual(seen["token"], "test-token")
        self.assertEqual(seen["body"]["chat_id"], 1)
        self.assertEqual(seen["body"]["user_id"], 1)
        self.assertFalse(seen["body"]["wait_for_response"])
        self.assertEqual(seen["body"]["sender_label"], "Mozaika")
        self.assertIn("/tmp/mozaika/assignment.md", seen["body"]["text"])
        self.assertIn("a" * 64, seen["body"]["text"])
        self.assertIn("скилл `mozaika`", seen["body"]["text"])
        self.assertNotIn("input_sources", seen["body"]["text"])
        self.assertNotIn("Refresh KPIs", seen["body"]["text"])
        self.assertNotIn("DeepSeek-only fallback", seen["body"]["text"])
        self.assertLess(len(seen["body"]["text"]), 900)

    def test_mixed_launch_preserves_url_file_and_directory(self):
        plugin = load_plugin()
        with tempfile.TemporaryDirectory() as tmp:
            api = _Api(tmp)
            fields = plugin._launch_fields(
                api,
                "routine_report",
                {
                    "sources": [
                        {
                            "kind": "url",
                            "url": "https://huggingface.co/datasets/example/data/tree/main",
                        },
                        {
                            "kind": "file",
                            "file": {
                                "name": "daily report.csv",
                                "mime": "text/csv",
                                "size": 8,
                                "data_base64": base64.b64encode(b"a,b\n1,2\n").decode("ascii"),
                            },
                        },
                        {
                            "kind": "directory",
                            "name": "quarter",
                            "files": [
                                {
                                    "name": "north.csv",
                                    "relative_path": "quarter/region/north.csv",
                                    "mime": "text/csv",
                                    "size": 3,
                                    "data_base64": base64.b64encode(b"x\n1").decode("ascii"),
                                },
                                {
                                    "name": "south.csv",
                                    "relative_path": "quarter/region/south.csv",
                                    "mime": "text/csv",
                                    "size": 3,
                                    "data_base64": base64.b64encode(b"x\n2").decode("ascii"),
                                },
                            ],
                        },
                    ],
                    "instructions": "Refresh KPIs",
                },
            )
            self.assertEqual([item["kind"] for item in fields["input_sources"]], ["url", "file", "directory"])
            self.assertEqual(fields["source_urls"], ["https://huggingface.co/datasets/example/data/tree/main"])
            self.assertEqual(len(fields["input_files"]), 3)
            stored = fields["input_files"][0]
            path = Path(stored["stored_path"])
            self.assertTrue(path.is_file())
            self.assertEqual(path.read_bytes(), b"a,b\n1,2\n")
            self.assertEqual(stored["original_name"], "daily report.csv")
            directory = fields["input_sources"][2]
            self.assertEqual(directory["file_count"], 2)
            self.assertEqual(
                [item["relative_path"] for item in directory["files"]],
                ["region/north.csv", "region/south.csv"],
            )
            self.assertTrue(all(Path(item["stored_path"]).is_file() for item in directory["files"]))
            self.assertEqual(fields["instructions"], "Refresh KPIs")
            self.assertEqual(
                stored["sha256"],
                "492d5ea496056f1a6a6592241032fab764c321596317930b4fa0e1e8bc3b7470",
            )
            self.assertEqual(stored["preservation"], "append_only")
            manifest_path = Path(fields["launch_manifest_path"])
            self.assertTrue(manifest_path.is_file())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertFalse(manifest["preservation_policy"]["allow_delete"])
            self.assertEqual(manifest["contract_version"], "mozaika-launch-manifest/v2")
            self.assertEqual(manifest["input_sources_contract"], "mozaika-input-sources/v2")
            self.assertEqual([item["kind"] for item in manifest["input_sources"]], ["url", "file", "directory"])
            self.assertEqual(manifest["assignment_file"], fields["assignment_file"])
            assignment_path = Path(fields["assignment_file"]["path"])
            self.assertTrue(assignment_path.is_file())
            assignment_bytes = assignment_path.read_bytes()
            self.assertEqual(plugin.hashlib.sha256(assignment_bytes).hexdigest(), fields["assignment_file"]["sha256"])
            assignment = assignment_bytes.decode("utf-8")
            self.assertIn("Поручение руководителя", assignment)
            self.assertIn("Артефакты на выходе", assignment)
            self.assertIn("богатый автономный HTML", assignment)
            self.assertIn("богата содержательными диаграммами", assignment)
            self.assertIn("переходы между страницами плавные", assignment)
            self.assertIn("обязательные таблицы с полезной выборкой данных", assignment)
            self.assertIn("research_title_verbatim", assignment)
            self.assertIn("все пункты, которые руководитель просит исследовать", assignment)
            self.assertIn("очищены от служебной информации", assignment)
            self.assertIn("номера вариантов, внутренние идентификаторы", assignment)
            self.assertNotIn("обе страницы storytelling-карточек", assignment)
            self.assertIn("установленные Anthropic-скиллы", assignment)
            self.assertIn("отдельный редактируемый PPTX", assignment)
            self.assertIn("`presentation-skill`", assignment)
            self.assertIn("не используй `pptx` или `anthropic-pptx`", assignment)
            self.assertIn("Refresh KPIs", assignment)
            self.assertNotIn("DeepSeek-only fallback", assignment)
            self.assertNotIn("Обязательная пользовательская повестка", assignment)

            insight_fields = plugin._launch_fields(
                api,
                "insight_deck",
                {
                    "sources": [{"kind": "url", "url": "https://example.com/data"}],
                    "executive_brief": "Найди важные для руководителя инсайты",
                },
            )
            insight_assignment = Path(insight_fields["assignment_file"]["path"]).read_text(encoding="utf-8")
            self.assertIn("Обязательная пользовательская повестка — прочитай до любых действий", insight_assignment)
            self.assertIn("Сначала ответь на эти пункты, затем добавляй проактивные инсайты", insight_assignment)
            self.assertIn("Наличие фильтра без показанного ответа не считается покрытием", insight_assignment)
            self.assertIn("сделай карточки выбора из них", insight_assignment)
            self.assertIn("references/user-agenda-coverage.md", insight_assignment)
            self.assertIn("`storytelling-cards.html`", insight_assignment)
            self.assertIn("владельцу отправляется HTML, а не JSON", insight_assignment)
            self.assertIn("Не выдавай внутренний JSON", insight_assignment)
            self.assertIn("сначала HTML-дашборд, затем `storytelling-cards.html`", insight_assignment)
            self.assertIn("Только после их вывода попроси выбрать", insight_assignment)
            self.assertIn("`selected-storytelling-card.html`", insight_assignment)
            self.assertIn("storyline-агент читает его", insight_assignment)
            self.assertIn("Карточки нельзя добавлять, прятать или встраивать", insight_assignment)
            self.assertIn("`dashboard-html-without-storytelling-cards/v1`", insight_assignment)
            self.assertIn("красивые ровные настраиваемые графики и таблицы", insight_assignment)
            self.assertIn("поиском и сортировкой", insight_assignment)
            self.assertIn("скрывать и возвращать разделы", insight_assignment)
            self.assertIn("предметный профиль владельца", insight_assignment)
            self.assertIn("точные светлые цвета и композицию", insight_assignment)
            self.assertIn("финальная колода карточек спикера", insight_assignment)
            self.assertIn("`speaker-story-cards.json`", insight_assignment)
            self.assertIn("`speaker-story-cards.html`", insight_assignment)
            self.assertIn("ровно одна карточка-подсказка на каждый финальный слайд", insight_assignment)
            self.assertIn("`presentation-skill` с `--style-preset mozaika-insight`", insight_assignment)
            self.assertIn("scenario-insight-presentation-style.md", insight_assignment)
            self.assertIn("не копируй его данные, темы, количество, порядок", insight_assignment)
            self.assertIn("reference_usage=`visual-grammar-only`", insight_assignment)

            weekly_fields = plugin._launch_fields(
                api,
                "weekly_autopilot",
                {
                    "sources": [{"kind": "url", "url": "https://example.com/weekly.xlsx"}],
                    "weekly_brief": "Обнови пятничный отчёт по свежим данным команды",
                },
            )
            weekly_assignment = Path(weekly_fields["assignment_file"]["path"]).read_text(encoding="utf-8")
            self.assertIn("Пятничный автопилот", weekly_assignment)
            self.assertIn("scenario-2-dashboard.template.html", weekly_assignment)
            self.assertIn("scenario-2-presentation.template.html", weekly_assignment)
            self.assertIn("Аномалии и важные моменты", weekly_assignment)
            self.assertIn("`presentation-skill`", weekly_assignment)
            self.assertIn("`mozaika-weekly`", weekly_assignment)
            self.assertNotIn("storytelling-cards.html", weekly_assignment)
            self.assertNotIn("попроси выбрать", weekly_assignment)

        with self.assertRaisesRegex(ValueError, "добавьте хотя бы один"):
            plugin._launch_fields(_Api(), "insight_deck", {})
        with self.assertRaises(ValueError):
            plugin._clean("x" * 1201)

    def test_mixed_sources_reject_unsafe_url_and_directory_traversal(self):
        plugin = load_plugin()
        with self.assertRaisesRegex(ValueError, "http или https"):
            plugin._launch_fields(_Api(), "insight_deck", {"sources": [{"kind": "url", "url": "file:///tmp/data.csv"}]})
        bad_file = {
            "name": "secret.csv",
            "relative_path": "folder/../../secret.csv",
            "mime": "text/csv",
            "size": 1,
            "data_base64": base64.b64encode(b"x").decode("ascii"),
        }
        with self.assertRaisesRegex(ValueError, "родительскую папку"):
            plugin._launch_fields(_Api(), "routine_report", {"sources": [{"kind": "directory", "name": "folder", "files": [bad_file]}]})

    def test_scope_and_claim_gates_recompute_instead_of_trusting_prose(self):
        plugin = load_plugin()
        scope = {
            "contract_version": "mozaika-scope-ledger/v1",
            "run_id": "run-1",
            "source_kind": "collection",
            "requested_mode": "all",
            "enumeration_artifact_ids": ["source-list"],
            "scope_change_approved": False,
            "items": [
                {"source_id": "a", "uri": "artifact:a", "disposition": "analyzed", "artifact_ids": ["a-data"]},
                {"source_id": "b", "uri": "artifact:b", "disposition": "analyzed", "artifact_ids": ["b-data"]},
            ],
            "coverage": {
                "total": 2,
                "analyzed": 2,
                "owner_excluded": 0,
                "blocked": 0,
                "all_analyzed": True,
                "terminal_complete": True,
                "solved_coverage": True,
            },
        }
        self.assertTrue(plugin._validate_gate_payload("scope", scope)["ok"])
        scope["coverage"]["analyzed"] = 1
        self.assertFalse(plugin._validate_gate_payload("scope", scope)["ok"])

        claims = {
            "contract_version": "mozaika-claim-registry/v1",
            "run_id": "run-1",
            "scope_ledger_sha256": "a" * 64,
            "output_language": "ru",
            "claims": [
                {
                    "claim_id": "category-share",
                    "text": "24 из 29 — это 82,8%",
                    "kind": "calculated",
                    "status": "verified",
                    "quantitative": True,
                    "entity_sensitive": False,
                    "evidence_artifact_ids": ["category-table"],
                    "checks": [
                        {"operator": "ratio_pct", "left": 24, "right": 29, "claimed_value": 82.8, "tolerance": 0.1}
                    ],
                    "text_checks": [],
                }
            ],
        }
        self.assertTrue(plugin._validate_gate_payload("claims", claims)["ok"])
        claims["claims"][0]["checks"][0]["left"] = 27
        result = plugin._validate_gate_payload("claims", claims)
        self.assertFalse(result["ok"])
        self.assertTrue(any("does not match" in item for item in result["errors"]))

        claims["claims"][0]["checks"][0]["left"] = 24
        claims["claims"][0]["entity_sensitive"] = True
        claims["claims"][0]["text_checks"] = [
            {"actual": "gpt-5.6-sol-xhigh", "claimed": "gpt-5.5-high", "case_sensitive": False}
        ]
        result = plugin._validate_gate_payload("claims", claims)
        self.assertFalse(result["ok"])
        self.assertTrue(any("claimed entity" in item for item in result["errors"]))

    def test_upload_storage_refuses_to_overwrite_existing_artifact(self):
        plugin = load_plugin()
        item = {
            "name": "source.csv",
            "mime": "text/csv",
            "size": 3,
            "data_base64": base64.b64encode(b"a\n1").decode("ascii"),
        }
        with tempfile.TemporaryDirectory() as tmp:
            api = _Api(tmp)
            _, first = plugin._store_sources(api, "fixed-launch", [{"kind": "file", "file": item}])
            path = Path(first[0]["stored_path"])
            self.assertEqual(path.read_bytes(), b"a\n1")
            with self.assertRaises(FileExistsError):
                plugin._store_sources(api, "fixed-launch", [{"kind": "file", "file": item}])
            self.assertEqual(path.read_bytes(), b"a\n1")

    def test_artifact_and_completion_gates_prevent_false_solved(self):
        plugin = load_plugin()
        artifact_index = {
            "contract_version": "mozaika-artifact-index/v1",
            "run_id": "run-1",
            "policy": {
                "mode": "append_only",
                "preserve_user_inputs": True,
                "preserve_stage_outputs": True,
                "allow_delete": False,
            },
            "required_artifact_ids": ["input-1"],
            "artifacts": [
                {
                    "artifact_id": "input-1",
                    "kind": "user_input",
                    "original_name": "data.csv",
                    "uri": "artifact:input-1",
                    "sha256": "b" * 64,
                    "media_type": "text/csv",
                    "schema": "raw/v1",
                    "size_bytes": 10,
                    "created_at": "2026-07-13T00:00:00Z",
                    "source_task_id": "task-1",
                    "source_stage_id": "data",
                    "preserved": True,
                    "immutable": True,
                    "durable": True,
                    "owner_visible": True,
                }
            ],
        }
        self.assertTrue(plugin._validate_gate_payload("artifacts", artifact_index)["ok"])

        scope = {
            "contract_version": "mozaika-scope-ledger/v1",
            "run_id": "run-1",
            "source_kind": "single",
            "requested_mode": "all",
            "enumeration_artifact_ids": [],
            "scope_change_approved": False,
            "items": [{"source_id": "a", "uri": "artifact:a", "disposition": "analyzed", "artifact_ids": ["input-1"]}],
            "coverage": {"total": 1, "analyzed": 1, "owner_excluded": 0, "blocked": 0, "all_analyzed": True, "terminal_complete": True, "solved_coverage": True},
        }
        claims = {
            "contract_version": "mozaika-claim-registry/v1",
            "run_id": "run-1",
            "scope_ledger_sha256": "c" * 64,
            "output_language": "ru",
            "claims": [{"claim_id": "observed", "text": "Факт", "kind": "observed", "status": "verified", "quantitative": False, "entity_sensitive": False, "evidence_artifact_ids": ["input-1"], "checks": [], "text_checks": []}],
        }
        completion = {
            "contract_version": "mozaika-completion-gate/v1",
            "run_id": "run-1",
            "scenario": "routine_report",
            "owner_choice_gate_passed": False,
            "requested_status": "solved",
            "scope": scope,
            "claims": claims,
            "artifacts": artifact_index,
            "runtime": {"execution_status": "degraded", "objective_status": "not_evaluated", "review_status": "skipped", "verification_failures": True},
            "visual_qa": {"required": True, "status": "unavailable", "artifact_ids": []},
            "design_receipts": [],
            "business_language_audits": [],
            "layout_audits": [],
            "unresolved": ["visual QA unavailable"],
        }
        result = plugin._validate_gate_payload("completion", completion)
        self.assertFalse(result["ok"])
        self.assertEqual(result["metrics"]["recommended_status"], "best_effort")
        self.assertFalse(result["metrics"]["business_language_ok"])
        self.assertFalse(result["metrics"]["layout_ok"])

    def test_frozen_research_brief_and_requirement_claim_map_are_exact(self):
        plugin = load_plugin()
        brief = {
            "contract_version": "mozaika-research-brief/v1",
            "run_id": "run-brief",
            "scenario": "insight_deck",
            "assignment_artifact_id": "assignment",
            "assignment_sha256": "a" * 64,
            "output_language": "ru",
            "research_title_verbatim": "Исследование качества моделей",
            "main_question_verbatim": "Какие изменения важны руководителю?",
            "comparison_normalization": "unicode-nfc-lf-v1",
            "requirements": [
                {
                    "requirement_id": "req-quality",
                    "text_verbatim": "Сравни качество по моделям\r\nи блокам",
                    "category": "requested_slice",
                    "labels": ["model", "block"],
                    "required_surfaces": ["data", "dashboard", "cards", "storyline", "presentation"],
                    "partial_answer_allowed": False,
                    "data_stage_required": True,
                },
                {
                    "requirement_id": "req-language",
                    "text_verbatim": "Все выводы — на русском языке",
                    "category": "constraint",
                    "labels": ["language"],
                    "required_surfaces": ["dashboard", "cards", "storyline", "presentation", "delivery"],
                    "partial_answer_allowed": False,
                    "data_stage_required": False,
                },
            ],
            "protected_verbatim": [
                "Исследование качества моделей",
                "Какие изменения важны руководителю?",
                "Сравни качество по моделям\nи блокам",
                "Все выводы — на русском языке",
            ],
        }
        self.assertTrue(plugin._validate_gate_payload("research_brief", brief)["ok"])
        broken_brief = json.loads(json.dumps(brief, ensure_ascii=False))
        broken_brief["requirements"][1]["requirement_id"] = "req-quality"
        self.assertFalse(plugin._validate_gate_payload("research_brief", broken_brief)["ok"])

        claims = {
            "contract_version": "mozaika-claim-registry/v1",
            "run_id": "run-brief",
            "scope_ledger_sha256": "b" * 64,
            "output_language": "ru",
            "claims": [{
                "claim_id": "claim-quality",
                "text": "Качество различается между моделями и блоками.",
                "kind": "observed",
                "status": "verified",
                "quantitative": False,
                "entity_sensitive": False,
                "evidence_artifact_ids": ["analysis-table"],
                "checks": [],
                "text_checks": [],
            }],
        }
        artifacts = {
            "contract_version": "mozaika-artifact-index/v1",
            "run_id": "run-brief",
            "policy": {"mode": "append_only", "preserve_user_inputs": True, "preserve_stage_outputs": True, "allow_delete": False},
            "required_artifact_ids": ["analysis-table"],
            "artifacts": [{
                "artifact_id": "analysis-table", "kind": "analysis", "uri": "artifact:analysis-table",
                "sha256": "c" * 64, "media_type": "application/json", "schema": "analysis/v1",
                "size_bytes": 1, "created_at": "2026-07-16T00:00:00Z", "source_task_id": "task-1",
                "source_stage_id": "data", "preserved": True, "immutable": True, "durable": True,
                "owner_visible": False,
            }],
        }
        mapping = {
            "contract_version": "mozaika-requirement-claim-map/v1",
            "run_id": "run-brief",
            "research_brief_sha256": "d" * 64,
            "entries": [{
                "requirement_id": "req-quality",
                "text_verbatim": "Сравни качество по моделям\nи блокам",
                "status": "answered",
                "claim_ids": ["claim-quality"],
                "evidence_artifact_ids": ["analysis-table"],
                "available_dimensions": ["model", "block"],
                "reason": None,
            }],
            "global_constraints": [{
                "requirement_id": "req-language",
                "text_verbatim": "Все выводы — на русском языке",
                "applied_global": True,
                "checked_surfaces": ["dashboard", "cards", "storyline", "presentation", "delivery"],
            }],
        }
        payload = {"mapping": mapping, "research_brief": brief, "claims": claims, "artifacts": artifacts}
        self.assertTrue(plugin._validate_gate_payload("requirement_claim_map", payload)["ok"])
        payload["mapping"]["entries"][0]["text_verbatim"] = "Переформулированный срез"
        self.assertFalse(plugin._validate_gate_payload("requirement_claim_map", payload)["ok"])

    def test_narrative_audit_and_owner_checkpoint_are_deterministic(self):
        plugin = load_plugin()
        brief = {
            "contract_version": "mozaika-research-brief/v1", "run_id": "run-1", "scenario": "insight_deck",
            "assignment_artifact_id": "assignment", "assignment_sha256": "a" * 64, "output_language": "ru",
            "research_title_verbatim": "Исследование", "main_question_verbatim": "Что важно?",
            "comparison_normalization": "unicode-nfc-lf-v1",
            "requirements": [{
                "requirement_id": "req-one", "text_verbatim": "Покажи срез по модели",
                "category": "requested_slice", "labels": ["model"],
                "required_surfaces": ["cards", "storyline", "presentation"],
                "partial_answer_allowed": False, "data_stage_required": False,
            }],
            "protected_verbatim": ["Исследование", "Что важно?", "Покажи срез по модели"],
        }
        audit = {
            "contract_version": "mozaika-narrative-integrity-audit/v1", "run_id": "run-1",
            "artifact_id": "cards", "artifact_sha256": "b" * 64, "artifact_type": "storytelling_cards",
            "research_brief_sha256": "c" * 64, "algorithm": "mozaika-narrative-integrity-v1", "status": "pass",
            "checks": {"verbatim_scope_complete": True, "no_exact_duplicates": True,
                       "no_high_confidence_near_duplicates": True, "claim_links_valid": True,
                       "selected_story_preserved": True, "screen_mapping_valid": True},
            "duplicate_findings": [],
            "coverage": [{"requirement_id": "req-one", "text_verbatim": "Покажи срез по модели",
                          "status": "covered", "target_ids": ["option-a"], "claim_ids": ["claim-a"]}],
        }
        self.assertTrue(plugin._validate_gate_payload("narrative_integrity", {"audit": audit, "research_brief": brief})["ok"])
        audit["coverage"] = []
        self.assertFalse(plugin._validate_gate_payload("narrative_integrity", {"audit": audit, "research_brief": brief})["ok"])

        def artifact(artifact_id, sha):
            return {
                "artifact_id": artifact_id, "kind": "analysis", "uri": f"artifact:{artifact_id}", "sha256": sha,
                "media_type": "application/json", "schema": "test/v1", "size_bytes": 1,
                "created_at": "2026-07-16T00:00:00Z", "source_task_id": "task-1", "source_stage_id": "cards",
                "preserved": True, "immutable": True, "durable": True, "owner_visible": False,
            }

        artifacts_list = [artifact(name, character * 64) for name, character in (
            ("assignment", "1"), ("brief", "2"), ("dashboard", "3"), ("choice", "4"), ("cards", "5")
        )]
        artifacts = {
            "contract_version": "mozaika-artifact-index/v1", "run_id": "run-1",
            "policy": {"mode": "append_only", "preserve_user_inputs": True, "preserve_stage_outputs": True, "allow_delete": False},
            "required_artifact_ids": [item["artifact_id"] for item in artifacts_list], "artifacts": artifacts_list,
        }
        checkpoint = {
            "contract_version": "mozaika-owner-decision-checkpoint/v1", "checkpoint_id": "checkpoint-1",
            "run_id": "run-1", "decision_id": "story", "chat_scope_id": "chat-1", "scenario": "insight_deck",
            "state": "pending", "created_at": "2026-07-16T00:00:00Z", "stale_after": "2099-07-16T00:00:00Z",
            "previous_checkpoint_id": None,
            "discovery": {"lookup_key": "chat-1:insight_deck:run-1", "visible_run_id": "run-1",
                          "priority": ["explicit_run_id", "single_pending_in_chat_scope", "ask_owner"]},
            "assignment_ref": {"artifact_id": "assignment", "uri": "artifact:assignment", "sha256": "1" * 64},
            "research_brief_ref": {"artifact_id": "brief", "uri": "artifact:brief", "sha256": "2" * 64},
            "dashboard_ref": {"artifact_id": "dashboard", "uri": "artifact:dashboard", "sha256": "3" * 64},
            "owner_choice_ref": {"artifact_id": "choice", "uri": "artifact:choice", "sha256": "4" * 64},
            "cards_ref": {"artifact_id": "cards", "uri": "artifact:cards", "sha256": "5" * 64},
            "candidate_options": [{"option_id": "a", "headline": "Вариант A", "html_anchor": "#option-a"},
                                  {"option_id": "b", "headline": "Вариант B", "html_anchor": "#option-b"}],
        }
        result = plugin._validate_gate_payload("owner_decision", {"checkpoint": checkpoint, "artifacts": artifacts, "expected_state": "pending"})
        self.assertTrue(result["ok"])
        self.assertTrue(result["metrics"]["publication_eligible"])
        checkpoint["selected_option_id"] = "a"
        self.assertFalse(plugin._validate_gate_payload("owner_decision", {"checkpoint": checkpoint, "artifacts": artifacts, "expected_state": "pending"})["ok"])

    def test_presentation_outline_gate_separates_routine_and_insight_admission(self):
        plugin = load_plugin()
        routine = {
            "contract_version": "presentation-outline/v1",
            "scenario": "routine_report",
            "coverage_mode": "fixed_template",
            "provenance": {
                "research_brief_sha256": None,
                "storyline_artifact_id": None,
                "selected_checkpoint_id": None,
                "selected_card_artifact_id": None,
                "template_sha256": "a" * 64,
            },
            "output_format": "html",
            "delivery_mode": "self-contained-single-file",
            "renderer_skill": "html-presentation-studio",
            "slides": [{"type": "content", "title": "Качество улучшилось", "claim_ids": ["claim-a"]}],
        }
        result = plugin._validate_gate_payload("presentation_outline", {"outline": routine})
        self.assertTrue(result["ok"])
        self.assertTrue(result["metrics"]["new_run_eligible"])
        routine["provenance"]["template_sha256"] = None
        self.assertFalse(plugin._validate_gate_payload("presentation_outline", {"outline": routine})["ok"])

        legacy = {
            "contract_version": "presentation-outline/v1",
            "output_format": "html", "delivery_mode": "self-contained-single-file",
            "renderer_skill": "html-presentation-studio",
            "slides": [{"type": "content", "title": "Исторический слайд", "claim_ids": ["claim-a"]}],
        }
        result = plugin._validate_gate_payload("presentation_outline", {"outline": legacy})
        self.assertTrue(result["ok"])
        self.assertTrue(result["metrics"]["legacy_readable"])
        self.assertFalse(result["metrics"]["new_run_eligible"])

        insight = json.loads(json.dumps(legacy))
        insight.update({
            "scenario": "insight_deck",
            "coverage_mode": "frozen_requirements",
            "provenance": {
                "research_brief_sha256": "b" * 64,
                "storyline_artifact_id": "storyline",
                "selected_checkpoint_id": "checkpoint",
                "selected_card_artifact_id": "selected-card",
                "template_sha256": None,
            },
        })
        insight["slides"][0]["slide_id"] = "slide-result"
        result = plugin._validate_gate_payload("presentation_outline", {"outline": insight})
        self.assertFalse(result["ok"])
        self.assertTrue(any("research_brief" in item or "checkpoint" in item for item in result["errors"]))

    def test_speaker_story_cards_gate_matches_every_final_slide_and_claim(self):
        plugin = load_plugin()
        speaker_html = '''<!doctype html><html lang="ru" data-mozaika-brandbook="mozaika-brandbook/v1"><head><style>
        :root{--canvas:#FAF9F5;--warm:#F0EEE6;--ink:#141413;--muted:#5E5D59;--focus:#388F76}
        @media print{body{display:block}}@media(prefers-reduced-motion:reduce){*{animation:none}}
        </style></head><body data-mozaika-surface="speaker-story-cards" data-mozaika-template="speaker-story-cards/v1">
        <div id="viewport"></div><button id="prev"></button><button id="next"></button><div id="dots"></div>
        <script>document.addEventListener('keydown',()=>{});document.addEventListener('touchstart',()=>{});</script></body></html>'''
        speaker_html_sha256 = hashlib.sha256(speaker_html.encode("utf-8")).hexdigest()
        outline = {
            "contract_version": "presentation-outline/v1",
            "scenario": "insight_deck",
            "title": "Исследование качества",
            "provenance": {
                "research_brief_sha256": "1" * 64,
                "selected_checkpoint_id": "checkpoint-1",
                "selected_card_artifact_id": "selected-card",
            },
            "slides": [
                {"slide_id": "slide-opening", "type": "title", "title": "Исследование качества", "claim_ids": []},
                {"slide_id": "slide-quality", "type": "content", "title": "Качество требует внимания", "claim_ids": ["claim-quality"]},
            ],
        }
        artifacts = {
            "artifacts": [
                {"artifact_id": "outline", "sha256": "2" * 64},
                {"artifact_id": "presentation", "sha256": "3" * 64},
                {"artifact_id": "speaker-html", "sha256": speaker_html_sha256},
                {"artifact_id": "source-data", "sha256": "5" * 64},
            ]
        }
        claims = {
            "claims": [{"claim_id": "claim-quality", "evidence_artifact_ids": ["source-data"]}]
        }
        speaker_story_cards = {
            "contract_version": "mozaika-speaker-story-cards/v1",
            "run_id": "run-1",
            "scenario": "insight_deck",
            "output_language": "ru",
            "deck_title": "Исследование качества",
            "research_brief_sha256": "1" * 64,
            "selected_checkpoint_id": "checkpoint-1",
            "selected_card_artifact_id": "selected-card",
            "outline_artifact_id": "outline",
            "outline_sha256": "2" * 64,
            "presentation_artifact_id": "presentation",
            "presentation_sha256": "3" * 64,
            "html_artifact_id": "speaker-html",
            "html_sha256": speaker_html_sha256,
            "template": {
                "ref": "data/brandbook/mozaika/templates/speaker-story-cards.template.html",
                "sha256": plugin._SPEAKER_TEMPLATE_SHA256,
            },
            "cards": [
                {
                    "card_id": "speaker-card-opening", "order": 1, "slide_id": "slide-opening", "slide_type": "title",
                    "slide_title": "Исследование качества", "purpose": "Открыть тему и задать вопрос",
                    "say_this": ["Сегодня покажу, где качество требует управленческого решения."],
                    "evidence_cues": [], "visual_cue": "Укажите на главный вопрос на обложке.",
                    "transition": "Начнём с основного сигнала.", "timing_seconds": 25,
                },
                {
                    "card_id": "speaker-card-quality", "order": 2, "slide_id": "slide-quality", "slide_type": "content",
                    "slide_title": "Качество требует внимания", "purpose": "Объяснить основной риск",
                    "say_this": ["Главный сигнал — устойчивое отклонение качества от целевого уровня."],
                    "evidence_cues": [{"claim_id": "claim-quality", "spoken_fact": "Отклонение подтверждено исходными данными.", "source_artifact_ids": ["source-data"]}],
                    "visual_cue": "Покажите разрыв между фактом и целью.",
                    "transition": "Далее перейдём к действиям.", "timing_seconds": 45,
                },
            ],
        }
        payload = {"speaker_story_cards": speaker_story_cards, "outline": outline, "claims": claims, "artifacts": artifacts, "html_source": speaker_html}
        result = plugin._validate_gate_payload("speaker_story_cards", payload)
        self.assertTrue(result["ok"], result["errors"])
        self.assertTrue(result["metrics"]["exact_slide_coverage"])
        speaker_story_cards["cards"].pop()
        self.assertFalse(plugin._validate_gate_payload("speaker_story_cards", payload)["ok"])

    def test_brandbook_conformance_inspects_html_and_rejects_dark_renderer_palette(self):
        plugin = load_plugin()
        bad_html = '''<!doctype html><html lang="ru"><head><style>:root{
        --bg:#0f0e17;--surface:#1a1726;--card:#211e30;--primary:#c93545;
        --accent:#e85d6f;--text:#fffffe}</style></head><body></body></html>'''
        bad_sha = hashlib.sha256(bad_html.encode("utf-8")).hexdigest()
        bad = plugin._validate_gate_payload("brandbook_conformance", {
            "artifact_type": "presentation", "artifact_id": "deck",
            "html_sha256": bad_sha, "html_source": bad_html,
            "artifacts": {"artifacts": [{"artifact_id": "deck", "sha256": bad_sha}]},
        })
        self.assertFalse(bad["ok"])
        self.assertGreater(bad["metrics"]["forbidden_color_hits"], 0)

        good_html = '''<!doctype html><html lang="ru" data-mozaika-brandbook="mozaika-brandbook/v1" data-mozaika-theme="mozaika-reference"><head><style>
        :root{--bg:#FAF9F5;--surface:#F0EEE6;--text:#141413;--muted:#5E5D59;--accent:#388F76}
        @media(prefers-reduced-motion:reduce){*{animation:none}}</style></head><body><section><h1>Вывод</h1></section></body></html>'''
        good_sha = hashlib.sha256(good_html.encode("utf-8")).hexdigest()
        good = plugin._validate_gate_payload("brandbook_conformance", {
            "artifact_type": "presentation", "artifact_id": "deck",
            "html_sha256": good_sha, "html_source": good_html,
            "artifacts": {"artifacts": [{"artifact_id": "deck", "sha256": good_sha}]},
        })
        self.assertTrue(good["ok"], good["errors"])

        rich_html = good_html + (" " * (plugin._MAX_GATE_PAYLOAD_BYTES + 1024))
        rich_sha = hashlib.sha256(rich_html.encode("utf-8")).hexdigest()
        rich = plugin._validate_gate_payload("brandbook_conformance", {
            "artifact_type": "presentation", "artifact_id": "rich-deck",
            "html_sha256": rich_sha, "html_source": rich_html,
        })
        self.assertTrue(rich["ok"], rich["errors"])

    def test_owner_choice_gate_requires_real_visual_preview_artifacts(self):
        plugin = load_plugin()
        claims = {
            "contract_version": "mozaika-claim-registry/v1",
            "run_id": "run-1",
            "scope_ledger_sha256": "d" * 64,
            "output_language": "ru",
            "claims": [
                {"claim_id": "claim-a", "text": "Факт A", "kind": "observed", "status": "verified", "quantitative": False, "entity_sensitive": False, "evidence_artifact_ids": ["data"], "checks": [], "text_checks": []},
                {"claim_id": "claim-b", "text": "Факт B", "kind": "observed", "status": "verified", "quantitative": False, "entity_sensitive": False, "evidence_artifact_ids": ["data"], "checks": [], "text_checks": []},
            ],
        }
        base_artifact = {
            "media_type": "text/html",
            "schema": "owner-choice-cards-html/v1",
            "size_bytes": 100,
            "created_at": "2026-07-13T00:00:00Z",
            "source_task_id": "task-1",
            "source_stage_id": "dashboard",
            "preserved": True,
            "immutable": True,
            "durable": True,
            "owner_visible": True,
        }
        artifacts = {
            "contract_version": "mozaika-artifact-index/v1",
            "run_id": "run-1",
            "policy": {"mode": "append_only", "preserve_user_inputs": True, "preserve_stage_outputs": True, "allow_delete": False},
            "required_artifact_ids": ["dashboard", "storytelling-cards"],
            "artifacts": [
                {**base_artifact, "artifact_id": "data", "kind": "analysis", "uri": "artifact:data", "sha256": "1" * 64, "media_type": "application/json", "schema": "analysis/v1"},
                {**base_artifact, "artifact_id": "dashboard", "kind": "dashboard", "uri": "artifact:dashboard", "sha256": "2" * 64, "schema": "dashboard-html-without-storytelling-cards/v1"},
                {**base_artifact, "artifact_id": "storytelling-cards", "kind": "owner_choice_preview", "uri": "artifact:storytelling-cards", "sha256": "e" * 64},
            ],
        }
        choice = {
            "contract_version": "mozaika-owner-choice/v1",
            "run_id": "run-1",
            "decision_id": "story",
            "question": "Какой вариант ближе?",
            "recommended_option_id": "a",
            "blocking_stage": "storyline",
            "output_language": "ru",
            "scope_ledger_sha256": "d" * 64,
            "claim_registry_sha256": "a" * 64,
            "visual_preview_required": True,
            "owner_surface_format": "html",
            "dashboard_surface_artifact_id": "dashboard",
            "owner_surface_artifact_id": "storytelling-cards",
            "options": [
                {
                    "option_id": "a", "label": "A", "grouping_principle": "A", "governing_thought": "A", "consequences": "A", "claim_ids": ["claim-a"], "preview_artifact_id": "storytelling-cards", "html_anchor": "#option-a",
                    "card": {
                        "headline": "Вариант через факт A", "core_message": "Главная мысль этого варианта опирается на факт A.",
                        "why_it_matters": "Руководителю важно увидеть последствия факта A.",
                        "story_beats": [
                            {"sequence": 1, "title": "Контекст", "message": "Задаём контекст через факт A.", "claim_ids": ["claim-a"], "visual_hint": "Крупная цифра"},
                            {"sequence": 2, "title": "Наблюдение", "message": "Раскрываем значение факта A.", "claim_ids": ["claim-a"], "visual_hint": "Диаграмма"},
                            {"sequence": 3, "title": "Решение", "message": "Связываем факт A с решением.", "claim_ids": ["claim-a"], "visual_hint": "Стрелка к выводу"},
                        ],
                        "executive_takeaway": "Руководителю стоит обсудить решение по факту A.",
                        "visual_style": "Светлая деловая карточка", "preview_alt_text": "Карточка с тремя ходами и опорным фактом A.", "language": "ru",
                    },
                },
                {
                    "option_id": "b", "label": "B", "grouping_principle": "B", "governing_thought": "B", "consequences": "B", "claim_ids": ["claim-b"], "preview_artifact_id": "storytelling-cards", "html_anchor": "#option-b",
                    "card": {
                        "headline": "Вариант через факт B", "core_message": "Главная мысль этого варианта опирается на факт B.",
                        "why_it_matters": "Руководителю важно увидеть последствия факта B.",
                        "story_beats": [
                            {"sequence": 1, "title": "Контекст", "message": "Задаём контекст через факт B.", "claim_ids": ["claim-b"], "visual_hint": "Крупная цифра"},
                            {"sequence": 2, "title": "Наблюдение", "message": "Раскрываем значение факта B.", "claim_ids": ["claim-b"], "visual_hint": "Диаграмма"},
                            {"sequence": 3, "title": "Решение", "message": "Связываем факт B с решением.", "claim_ids": ["claim-b"], "visual_hint": "Стрелка к выводу"},
                        ],
                        "executive_takeaway": "Руководителю стоит обсудить решение по факту B.",
                        "visual_style": "Тёмная деловая карточка", "preview_alt_text": "Карточка с тремя ходами и опорным фактом B.", "language": "ru",
                    },
                },
            ],
        }
        payload = {"choice": choice, "claims": claims, "artifacts": artifacts}
        self.assertTrue(plugin._validate_gate_payload("owner_choice", payload)["ok"])
        payload["artifacts"]["artifacts"][1]["schema"] = "dashboard-html/v1"
        self.assertFalse(plugin._validate_gate_payload("owner_choice", payload)["ok"])
        payload["artifacts"]["artifacts"][1]["schema"] = "dashboard-html-without-storytelling-cards/v1"
        payload["choice"]["options"][1]["html_anchor"] = "#option-a"
        self.assertFalse(plugin._validate_gate_payload("owner_choice", payload)["ok"])
        payload["choice"]["options"][1]["html_anchor"] = "#option-b"
        payload["artifacts"]["artifacts"][2]["media_type"] = "image/png"
        self.assertFalse(plugin._validate_gate_payload("owner_choice", payload)["ok"])

        payload["artifacts"]["artifacts"][2]["media_type"] = "text/html"
        payload["artifacts"]["artifacts"][1]["owner_visible"] = False
        self.assertFalse(plugin._validate_gate_payload("owner_choice", payload)["ok"])


if __name__ == "__main__":
    unittest.main()
