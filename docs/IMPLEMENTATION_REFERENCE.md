# Технический справочник Mozaika

Документ фиксирует проверяемые детали текущей реализации. Концептуальная схема находится в [ARCHITECTURE.md](../ARCHITECTURE.md).

## 1. Версии и состав

| Компонент | Версия или количество |
|---|---:|
| Ouroboros | `6.71.0`, commit `50756ed` |
| Mozaika extension | `1.4.4` |
| PluginAPI | `1.3` |
| Виджеты | 2 |
| Инструменты расширения | 2 |
| HTTP-маршруты расширения | 8 |
| Логические агентные роли | 9 |
| Конвейеры | 3 |
| JSON Schema | 23 |
| Поставляемые skill-пакеты | 20, включая `mozaika` |
| Автоматические тесты | 36 тестов, 112 подтестов |

## 2. Пакет расширения

Манифест находится в frontmatter `skills/mozaika/SKILL.md`:

```yaml
name: mozaika
version: 1.4.4
type: extension
runtime: python3
entry: plugin.py
permissions: [net, fs, subprocess, route, widget, inject_chat, tool]
```

`plugin.py` не получает произвольный внутренний объект сервера. Он регистрируется через зафиксированный `PluginAPI` Ouroboros.

## 3. Поверхность PluginAPI

### Инструменты

| Имя | Назначение |
|---|---|
| `validate_gate` | Детерминированно проверяет переданный payload одного из предметных шлюзов; не читает и не меняет файлы |
| `request_owner_choice` | Публикует 2–3 карточки в первом виджете, удерживает foreground task и возвращает сохранённый клик владельца |

### Маршруты

Префикс задаёт Ouroboros: `/api/extensions/mozaika/`.

| Относительный маршрут | Метод | Назначение |
|---|---|---|
| `scenario/task-presets` | GET | Варианты поручения для поиска инсайтов |
| `scenario/weekly-task-presets` | GET | Варианты поручения для регулярного отчёта |
| `scenario/local/pick` | POST | Системный выбор файла или папки |
| `scenario/choice/pending` | GET | Ожидающие решения владельца |
| `scenario/choice/answer` | POST | Сохранение клика по карточке |
| `scenario/routine/start` | POST | Запуск внутреннего `routine_report` |
| `scenario/insight/start` | POST | Запуск `insight_deck` |
| `scenario/weekly/start` | POST | Запуск `weekly_autopilot` |

### Вкладки

- `insights` → `insight-widget.js`;
- `routine` → `routine-widget.js`.

## 4. Ограничения входного API

Ограничения защищают интерфейс и метаданные, но не устанавливают лимит размера системно выбранного файла:

- не более 50 верхнеуровневых источников;
- не более 500 файлов внутри добавленных источников;
- URL — до 4 096 символов;
- относительный путь — до 1 024 символов;
- редактируемое поле поручения — до 1 200 символов;
- обычный payload gate — до 2 МБ;
- brandbook conformance payload — до 16 МБ;
- ожидание owner choice — до 1 700 секунд на один tool call.

Системный picker передаёт путь и метаданные, не Base64. Browser-drop сохраняет файл, поэтому его практический предел зависит от памяти браузерного процесса и транспортной поверхности.

## 5. Конвейеры

```json
{
  "routine_report": ["data", "dashboard", "presentation", "pptx"],
  "insight_deck": ["data", "dashboard", "storyline", "presentation", "speaker_cards", "pptx"],
  "weekly_autopilot": ["data", "dashboard", "anomaly_analysis", "presentation", "pptx"]
}
```

Языковой и визуальный валидаторы вызываются как независимые контрольные роли вокруг owner-facing артефактов, а не являются линейными элементами каждого массива pipeline.

## 6. Роли

Все роли включены, используют `transport=local_task_skill` и пул `adaptive-full`.

| Ключ | Agent ID | Model lane | Выходной контракт |
|---|---|---|---|
| `data` | `mozaika-data-agent` | `heavy` | `mozaika-data-package/v1` |
| `dashboard` | `mozaika-dashboard-agent` | `heavy` | `mozaika-dashboard-package/v1` |
| `anomaly_analysis` | `mozaika-anomaly-analysis-agent` | `heavy` | `mozaika-anomaly-package/v1` |
| `storyline` | `mozaika-storyline-agent` | `heavy` | `mozaika-storyline-package/v1` |
| `presentation` | `mozaika-presentation-agent` | `heavy` | `mozaika-presentation-package/v1` |
| `speaker_cards` | `mozaika-speaker-cards-agent` | `heavy` | `mozaika-speaker-story-cards/v1` |
| `pptx` | `mozaika-pptx-agent` | `heavy` | `mozaika-editable-pptx-package/v1` |
| `business_language_validator` | `mozaika-business-language-validator-agent` | `review` | `mozaika-business-language-audit/v1` |
| `visual_validator` | `mozaika-visual-validator-agent` | `review` | `mozaika-visual-layout-audit/v1` |

Это логические владельцы этапов. Subagent Ouroboros не получает право сам выполнять skill lifecycle; родительская задача владеет `skill_exec`, состоянием и итоговым решением.

## 7. Политика выбора скилла

Режим — `evaluate_before_each_stage`. Решение сохраняется в `mozaika-skill-selection/v1`.

Порядок источников:

1. owner-designated installed reviewed;
2. installed Anthropic reviewed;
3. installed reviewed;
4. Anthropic official discoverable;
5. OuroborosHub official;
6. other reviewed.

Кандидаты ранжируются по:

- соответствию контракту;
- качеству результата;
- силе проверки;
- официальному происхождению;
- совместимости среды;
- свежести ревью;
- стоимости зависимостей.

Разрешены обнаружение и загрузка в staging. Постоянная установка требует provenance, preflight, skill review, разрешений владельца и enablement.

`anthropic-pptx` находится в поставке, но исключён из `adaptive-full`. HTML начинает оценку с `html-presentation-studio`; редактируемый PPTX должен создавать `presentation-skill`.

### `presentation-skill`

Установленный пакет `skills/presentation-skill/` имеет версию `0.1.0` и использует `pptxgenjs ^4.0.1`:

- `scripts/build_deck.js` — входная точка сборки PPTX из декларативной спецификации;
- `templates/presets.js` — профили оформления, включая профили Mozaika;
- `templates/slides.js` — библиотека компоновок и элементов слайдов;
- `SKILL.md` — формат входа, запуск, проверка рендера и ограничения.

Это назначенный владельцем renderer последнего этапа. Он наследует утверждённые факты и порядок из принятой HTML-презентации, а визуальные правила — из брендбука Mozaika; содержимое референсного PPTX не копируется как структура новой презентации.

## 8. Контракты

| Файл | Назначение |
|---|---|
| `agent-pool.schema.json` | конфигурация ролей, транспорта и политик |
| `input-sources.schema.json` | смешанный упорядоченный вход |
| `research-brief.schema.json` | замороженная пользовательская повестка |
| `scope-ledger.schema.json` | область коллекций и обработанных элементов |
| `owner-domain-profile.schema.json` | подтверждённые предметные предпочтения |
| `claim-registry.schema.json` | утверждения, формулы, допуски и доказательства |
| `requirement-claim-map.schema.json` | связь поручения с утверждениями и артефактами |
| `handoff-envelope.schema.json` | передача между ролями |
| `skill-selection.schema.json` | решение о скилле перед этапом |
| `artifact-index.schema.json` | неизменяемый реестр входов и выходов |
| `duckdb-request.schema.json` | запрос к аналитическому движку |
| `huggingface-inventory.schema.json` | инвентаризация Hugging Face коллекции |
| `dashboard-spec.schema.json` | структура dashboard и запрет карточек внутри него |
| `owner-choice.schema.json` | 2–3 стратегии истории |
| `owner-decision-checkpoint.schema.json` | durable pending/selected choice |
| `presentation-outline.schema.json` | структура экранов и admission rules |
| `speaker-story-cards.schema.json` | карточка на каждый финальный слайд |
| `design-receipt.schema.json` | применённый брендбук и хэши |
| `business-language-audit.schema.json` | критические текстовые нарушения |
| `visual-layout-audit.schema.json` | геометрия и состояния реального рендера |
| `narrative-integrity-audit.schema.json` | сохранение выбранной истории и повестки |
| `routine-learning.schema.json` | проверяемые знания регулярного отчёта |
| `completion-gate.schema.json` | итоговая допустимость завершения |

Для `insight_deck` связка `research-brief.json` и `requirement-claim-map.json` является текущим coverage-паспортом между ролями. `agent-contracts.md` требует включать их неизменяемые ссылки в каждый handoff и повторно сверять с `assignment.md`. Это пока инструкционное требование: `handoff-envelope.schema.json` допускает эти ссылки во входах и контексте, но не имеет отдельного обязательного поля coverage passport.

## 9. Gate API

`validate_gate` принимает один из gate names:

- `scope`;
- `claims`;
- `artifacts`;
- `research_brief`;
- `requirement_claim_map`;
- `narrative_integrity`;
- `owner_decision`;
- `owner_choice`;
- `presentation_outline`;
- `brandbook_conformance`;
- `speaker_story_cards`;
- `completion`.

Проверка повторно вычисляет ключевые ограничения и не доверяет полю `passed`, созданному моделью. Однако tool не открывает файлы: вызывающая задача обязана передать полное содержимое и правильный SHA-256.

## 10. Артефактная политика

Конфигурация:

```json
{
  "mode": "append_only",
  "preserve_user_inputs": true,
  "preserve_stage_outputs": true,
  "allow_delete": false,
  "index_contract": "mozaika-artifact-index/v1"
}
```

Исправление создаёт новый артефакт. Зарегистрированный вход или этапный результат не должен удаляться либо перезаписываться.

## 11. Брендбук

Authority — `owner_brandbook`. Канонические рабочие пути:

- `data/brandbook/mozaika/BRANDBOOK.md`;
- `data/brandbook/mozaika/manifest.json`;
- `data/brandbook/mozaika/tokens.css`;
- `data/brandbook/mozaika/references/`.

Проектные шаблоны:

| Файл | Назначение |
|---|---|
| `scenario-2-dashboard.template.html` | визуальная грамматика дэшборда регулярного отчёта |
| `scenario-2-presentation.template.html` | HTML-презентация регулярного отчёта |
| `scenario-2-presentation-skill-outline.example.json` | пример спецификации PPTX регулярного отчёта |
| `scenario-insight-presentation-skill-outline.example.json` | пример спецификации PPTX для поиска инсайтов |
| `speaker-story-cards.template.html` | обязательная композиция финальных карточек спикера |

Встроенные renderer defaults запрещены. Визуальный этап должен вернуть `mozaika-design-receipt/v1` с актуальными хэшами.

На момент аудита проектный референс `scenario-insight-ds-role-analytics-reference.pptx` имеет SHA-256 `4e0176…c7fa4`, а рабочая копия — `66430f…a6c1d`. Это известный deployment drift; до следующего производственного запуска требуется синхронизация и новое ревью.

## 12. Model fallback

По умолчанию используется нативный структурированный протокол без fallback. Только для модели, имя которой содержит `deepseek`, и только для ошибки `Thinking mode does not support this tool_choice` разрешён один повтор в режиме `plain_json_then_validate`.

Fallback не меняет модель, безопасность, источники или артефактную политику.

## 13. A2A

Текущая конфигурация: `enabled=false`. Все роли используют локальный transport. A2A-материалы в `references/a2a-audit.md` являются проектом будущего расширения, а не исполняемой production-функцией.

## 14. Source/runtime layout

| Назначение | Проект | Рабочая среда Ouroboros |
|---|---|---|
| Mozaika | `skills/mozaika` | `data/skills/external/mozaika` |
| Внешний скилл | `skills/<name>` | `data/skills/external/<name>` |
| Состояние скилла | не хранится в пакете | `data/state/skills/<name>` |
| Брендбук | `brandbook` | `data/brandbook/mozaika` |

При использовании file tools с `root=runtime_data` ведущий сегмент `data/` снимается. Например, канонический контракт `data/brandbook/mozaika/manifest.json` читается как `brandbook/mozaika/manifest.json`.

## 15. Проверка

```bash
python3 -m pytest -q
```

Проверенный результат текущего снимка:

```text
36 passed, 112 subtests passed
```

Тесты не заменяют production E2E и визуальный рендер, но фиксируют стабильность API и контрактов.

## 16. Рабочее состояние расширения

Постоянное и временное состояние расширения отделено от устанавливаемого пакета и находится в `data/state/skills/mozaika/`:

| Каталог | Назначение | Политика |
|---|---|---|
| `live-owner-choices/<sha256[:32]>/` | неизменяемые запросы выбора и сохранённые ответы владельца | сохраняется для восстановления того же `question_id` |
| `path-selections/` | подтверждённые системным диалогом локальные пути | служебное состояние выбора источников |
| `jobs/<safe-job-id>-<digest>/` | изолированные `assets/`, `output/` и `tmp/` задания расширения | создаётся через `PluginAPI.skill_job_dir` |
| `__extension_imports/<pid>-<uuid>/` | временная staged-копия пакета для безопасной загрузки расширения | очищается Ouroboros после выгрузки или как осиротевшая копия |

`__extension_imports` не является пользовательским хранилищем. Пользовательские входы и итоговые артефакты должны находиться в каталогах кампании и реестре артефактов; обновление или переустановка скилла не должно удалять `live-owner-choices`, задания либо пользовательские результаты.
