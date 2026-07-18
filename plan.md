# План исправления Mozaika: карточки, выбор сюжета и соответствие презентации заданию

## 1. Цель

Исправить сквозной сценарий Mozaika `данные → дашборд → варианты истории → выбор владельца → storyline → HTML-презентация`, чтобы:

- все явно заданные пользователем вопросы, срезы и названия исследования сохранялись дословно от запуска до итоговой презентации;
- каждая storytelling-карточка показывала не только альтернативную идею рассказа, но и понятный способ раскрытия всего пользовательского задания;
- карточки не содержали смысловых и механических повторов;
- выбор владельца надёжно переживал завершение исходной задачи и продолжение в новой задаче Ouroboros;
- storyline создавался обязательно до презентации;
- презентация строилась только из проверенного outline, соответствовала выбранной карточке и покрывала каждый обязательный срез;
- техническая проверка не могла объявить результат готовым только по наличию файлов, количеству экранов или строке `Chart.js`;
- проектная копия скиллов и установленная runtime-копия в Ouroboros оставались идентичными.

План основан на диагностике запуска `d4170c3e` и продолжения `b9401fad`. Данные и дашборд в том запуске содержали шесть обязательных пунктов, но карточки не имели карты их покрытия, а презентация была собрана одноразовым Python-скриптом в обход storyline-агента и `html-presentation-studio`.

### Решения по `reviewplan.md`

Приняты безопасные рекомендации ревьюера: добавить минимальную фазу 0, описать state machine и discovery protocol для checkpoint, отделить insight admission от routine admission, различать удалённые зависимости и встроенный runtime, поддержать глобальные constraints, проверить миграцию v1 и повторно провести runtime-review после синхронизации. Существующие business-language и visual-layout audits сохраняются как два независимых контура; narrative-integrity audit становится третьим и не дублирует их.

Не считаем ранее внесённый код автоматически завершённым: чекбокс отмечается только после проверки актуального состояния, отрицательного regression-теста и положительного теста исправления. Это защищает от расхождения между ревью старого diff и текущим репозиторием.

## 2. Зафиксированные причины

### 2.1. Повторы в карточках

- В `dashboard-spec.json` поля `story_beat.title` и `story_beat.message` могли быть одинаковыми.
- Renderer `antv-g2-dashboard` без проверки соединял их в строку `title — message`.
- `headline` и `core_message` также могли повторять одну мысль почти дословно.
- JSON Schema проверяла наличие и длину полей, но не их смысловое различие.
- Ослабленный валидатор делового языка намеренно пропускает обычные повторы и не должен использоваться для контроля структурной целостности.

### 2.2. Пользовательские срезы не попали в варианты истории

- `research_questions` существовали только на уровне дашборда.
- В `storytelling_cards` не было обязательного `research_questions_coverage` или другой связи с пользовательским заданием.
- У карточек были только `claim_ids`, причём один и тот же claim мог ошибочно покрывать всю карточку.
- Ограничение `3–5 story beats` фактически конкурировало с шестью обязательными пунктами вместо того, чтобы позволить одному beat объединять несколько пунктов с явной картой покрытия.
- Пользователь не видел, как каждый вариант собирается раскрыть все заданные вопросы.

### 2.3. Выбор владельца потерял контекст

- Ответ `1` пытался направить уже завершившуюся задачу.
- Runtime сообщил, что steering невозможен, но последующее сообщение ошибочно подтвердило доставку выбора.
- Новая задача продолжения получила краткий текст без полного immutable checkpoint.
- Связь между assignment, внутренним `owner-choice.json`, выбранной карточкой и следующей стадией не была формально восстановлена.

### 2.4. Презентация отошла от задания

- Storyline-агент не запускался.
- `presentation-outline.json` и проверяемая карта покрытия не создавались.
- `html-presentation-studio` не использовался.
- Одноразовый Python-скрипт захардкодил набор слайдов и потерял часть срезов.
- Проверка презентации не сопоставляла экраны с обязательными пунктами задания и выбранной карточкой.

## 3. Архитектурные решения

### 3.1. Сделать пользовательское задание отдельным неизменяемым контрактом

Добавить контракт `mozaika-research-brief/v1`, который создаётся сразу после `assignment.md` и является источником правды для всех последующих стадий.

Предлагаемые поля:

- `contract_version`, `run_id`, `assignment_artifact_id`, `assignment_sha256`;
- `output_language`;
- `research_title_verbatim`;
- `main_question_verbatim`, если он сформулирован пользователем;
- `requirements[]`:
  - стабильный внутренний `requirement_id`;
  - `text_verbatim`;
  - основная категория: `research_question`, `requested_slice`, `requested_section`, `named_output` или `constraint`;
  - дополнительные непересекающиеся `labels[]` для расширения без изменения enum;
  - обязательные поверхности: dashboard, cards, storyline, presentation;
  - допустимость частичного ответа;
- `protected_verbatim[]` для языкового валидатора;
- ссылка на исходный prompt без копирования или редактирования его смысла.

Внутренние идентификаторы нужны только контрактам. В пользовательских HTML должны отображаться сами формулировки, а не `requirement_id`. Verbatim-текст хранится без редакторской нормализации; для сравнения применяется единый алгоритм `NFC + CRLF/CR → LF`, зафиксированный общей функцией и тестами.

### 3.2. Разделить сюжетные ходы и покрытие задания

Сохранить 3–5 `story_beats` как краткую логику конкретной истории. Не требовать превращать каждый пользовательский пункт в отдельный beat.

Рядом добавить обязательную карту покрытия:

- какой пункт задания раскрывается;
- в каких beats он развивается;
- какими claims подтверждается;
- какой акцент получает именно в этом варианте;
- какой предварительный экран или раздел презентации ему соответствует;
- статус `covered`, `partial` или `unanswered` с причиной.

На HTML-странице карточек выводить компактный блок «Как этот вариант раскроет ваш запрос» со всеми пользовательскими пунктами дословно: краткий статус и framing видны сразу, доказательства и детализация раскрываются по клавиатуре/клику. Это позволит сравнивать варианты по смыслу без перегрузки карточки.

### 3.3. Ввести отдельный контур содержательной целостности

Не усиливать обратно правила делового тона. Добавить отдельный контракт и детерминированную проверку `mozaika-narrative-integrity-audit/v1` для:

- точных и близких повторов;
- потери обязательных пунктов;
- подмены выбранной истории;
- расхождения claims между карточкой, storyline и презентацией;
- отсутствия обязательных связей между заданием и экранами.

Ослабленный business-language validator продолжает блокировать только критические языковые ошибки. Повторы и coverage контролируются новым содержательным gate. Существующие `mozaika-business-language-audit/v1` и `mozaika-visual-layout-audit/v1` остаются независимыми: первый отвечает за критические текстовые сбои, второй — за геометрию, новый audit — за смысловую целостность.

### 3.4. Продолжать после выбора только из durable checkpoint

Добавить `mozaika-owner-decision-checkpoint/v1` как JSON Schema `oneOf` для состояний `pending`, `selected`, `superseded` и `dismissed`. Он сохраняется до вопроса владельцу и содержит:

- `run_id`, `decision_id`, статус `pending`;
- ссылки и SHA-256 assignment/research brief;
- ссылку на dashboard package;
- ссылку на `owner-choice.json`;
- ссылку на показанные dashboard и `storytelling-cards.html`;
- допустимые option ids и их человекочитаемые заголовки;
- следующую стадию `storyline`;
- исходный task id только как диагностическое поле, но не как механизм продолжения.

Discovery protocol: сохранять указатель на последний pending checkpoint в append-only artifact registry по ключу `chat/session scope + scenario + run_id`; показывать короткий `run_id` в служебной run note, но не в зрительских артефактах. Новая задача сначала использует явный `run_id` из сообщения, затем единственный pending checkpoint текущего chat/session scope; при нуле или нескольких кандидатах задаёт один уточняющий вопрос и ничего не выбирает.

Если исходная задача уже завершилась, новая задача должна восстановить checkpoint по durable artifact refs, проверить hashes, применить ответ владельца и выпустить новую версию checkpoint со статусом `selected`. Повторный выбор создаёт новый checkpoint со статусом `selected`, а прежний становится `superseded`; история не переписывается. Pending checkpoint не истекает молча: после настраиваемого срока он считается stale и требует явного подтверждения владельца, а закрывается только через `dismissed` или новый выбор. Нельзя сообщать «выбор доставлен», пока selected checkpoint и `selected-storytelling-card.html` действительно не созданы.

### 3.5. Запретить презентацию без storyline и валидного outline

Presentation stage разрешается только при наличии:

- выбранной и проверенной `selected-storytelling-card.html`;
- selected decision checkpoint;
- `storyline.md`;
- `evidence-map.json`;
- `slide-intents.json`;
- schema-valid `presentation-outline/v2` для insight-сценария или совместимого routine admission из фиксированного шаблона;
- полного `research_questions_coverage`;
- execution receipt выбранного presentation skill.

Одноразовый Python/HTML renderer без зафиксированного выбора скилла и execution receipt должен завершать стадию как `best_effort` или `blocked_with_evidence`, но не `solved`.

## 4. Модификации по скиллам и файлам

### 4.1. Основной оркестратор `mozaika`

Файлы:

- `Mozaika/skills/mozaika/SKILL.md`;
- `Mozaika/skills/mozaika/plugin.py`;
- `Mozaika/skills/mozaika/references/scenario-2-insight-storyline-deck.md`;
- `Mozaika/skills/mozaika/references/agent-contracts.md`;
- `Mozaika/skills/mozaika/references/gates-and-evidence.md`;
- `Mozaika/skills/mozaika/references/storytelling-cards.md`;
- `Mozaika/skills/mozaika/references/execution-and-artifacts.md`;
- `Mozaika/skills/mozaika/references/ouroboros-runtime.md`;
- `Mozaika/skills/mozaika/config/agent-pool.example.json`.

Изменения:

1. После создания `assignment.md` выполнять отдельное извлечение research brief и сохранять его как immutable JSON.
2. Не позволять downstream-ролям заново свободно интерпретировать prompt: они получают assignment и research brief с проверенными hashes.
3. Добавить явные stage gates:
   - `research_brief_frozen`;
   - `dashboard_requirements_covered`;
   - `owner_choice_content_valid`;
   - `owner_decision_persisted`;
   - `storyline_requirements_covered`;
   - `presentation_outline_valid`;
   - `presentation_requirements_covered`;
   - `selected_story_preserved`.
4. Перед вопросом владельцу создавать durable pending checkpoint.
5. После сообщения владельца сначала восстанавливать checkpoint, затем создавать selected checkpoint и только после этого подтверждать выбор.
6. Явно запрещать оптимистичное подтверждение доставки при ошибке steering.
7. Не отправлять storyline-задачу из одного краткого текста «продолжи»; handoff обязан содержать artifact refs research brief, selected checkpoint, selected card, dashboard package и claim registry.
8. Не запускать presentation role, если storyline package отсутствует или не прошёл gates.
9. Не принимать `run_script` как скрытый presentation renderer. Любой fallback проходит обычный skill-selection lifecycle и сохраняет receipt.
10. В completion gate передавать не булевы заявления, а ссылки на прошедшие gate receipts.

Изменение assignment:

- добавить явное требование, что каждый вариант карточки визуально показывает способ покрытия всех обязательных пунктов;
- уточнить, что 3–5 сюжетных ходов не отменяют полный список пользовательских срезов;
- закрепить точное пользовательское название как отдельный kicker/контекст карточки, а не заставлять повторять длинное название внутри каждого смыслового заголовка;
- требовать отдельный content-integrity audit для карточек, selected card, storyline и презентации.

### 4.2. Data role `analyze-report-data`

Файл:

- `Mozaika/skills/analyze-report-data/SKILL.md`.

Изменения:

1. Сделать `mozaika-research-brief/v1` обязательным входом.
2. Добавить выход `requirement-claim-map.json`:
   - каждый requirement присутствует;
   - статус `answered`, `partial`, `unanswered`;
   - связанные `claim_ids`;
   - evidence artifact ids;
   - причина неполноты;
   - доступные измерения и срезы.
3. Не считать data stage решённым, если исследовательский пункт исчез из карты, даже когда общий анализ успешно завершён. Для requirement категории `constraint` использовать `applied_global=true` и проверять его на соответствующей поверхности, не требуя искусственного data claim.
4. Сохранить текущую свободу выбора аналитических skills. Импортированные `anthropic-*` skills не изменять; усиливать только входной и выходной контракт роли.

Причина включения data role: прошлый data stage сработал правильно, но его результат не был оформлен как обязательный сквозной handoff. Требуется закрепить уже найденные вопросы так, чтобы они не могли потеряться дальше.

### 4.3. Dashboard role `build-insight-dashboard`

Файл:

- `Mozaika/skills/build-insight-dashboard/SKILL.md`.

Изменения:

1. Принимать research brief и `requirement-claim-map.json` как обязательные входы.
2. Требовать `requirements_coverage` в dashboard spec и owner-choice contract.
3. Для каждой narrative option проверять полный набор обязательных пунктов.
4. Разрешить одному story beat покрывать несколько пунктов, но запретить неявное выпадение пунктов.
5. Требовать содержательное отличие вариантов:
   - разные grouping principle;
   - разные governing thought или порядок аргумента;
   - объяснённый trade-off;
   - одинаковый полный scope задания.
6. Запускать narrative-integrity audit до browser QA.
7. Не публиковать вопрос владельцу при duplicate/coverage failure.
8. В `chart-catalog.json` и `claim-chart-map.json` добавить обратную связь с requirement ids, чтобы storyline мог подобрать релевантные визуализации для каждого пользовательского среза.

### 4.4. Контракты dashboard и owner choice

Файлы:

- `Mozaika/skills/mozaika/contracts/dashboard-spec.schema.json`;
- `Mozaika/skills/mozaika/contracts/owner-choice.schema.json`;
- новый `Mozaika/skills/mozaika/contracts/research-brief.schema.json`;
- новый `Mozaika/skills/mozaika/contracts/narrative-integrity-audit.schema.json`;
- новый `Mozaika/skills/mozaika/contracts/owner-decision-checkpoint.schema.json`.
- существующие `business-language-audit.schema.json` и `visual-layout-audit.schema.json` не заменять и не объединять с новым audit.

План версий:

- для новых обязательных полей выпустить `mozaika-dashboard-spec/v2` и `mozaika-owner-choice/v2`;
- старые v1-артефакты оставить читаемыми только для аудита и миграции;
- все новые запуски создавать только v2;
- не переписывать исторические immutable artifacts.

Новые обязательные поля owner choice:

- `research_brief_sha256`;
- `research_title_verbatim`;
- `required_requirement_ids`;
- для каждой option — `requirements_coverage[]`;
- для каждой coverage entry — `requirement_id`, `text_verbatim`, `status`, `beat_sequences`, `claim_ids`, `planned_screen_intents`, `framing`;
- `content_integrity_audit_artifact_id`;
- `checkpoint_artifact_id`.

Проверки схемы и gate:

- множество `requirement_id` в каждой карточке точно равно обязательному множеству из research brief;
- `text_verbatim` совпадает побайтно после нормализации перевода строк, но без редакторского переписывания;
- все `claim_ids` существуют и согласованы с requirement-claim map;
- `beat_sequences` ссылаются на реальные beats;
- `planned_screen_intents` не пусты для covered/partial;
- `unanswered` содержит видимую причину и не может тихо считаться covered.
- checkpoint schema использует разные required fields для `pending`, `selected`, `superseded` и `dismissed`;
- legacy v1 загружается для аудита, но не проходит gate нового запуска.

### 4.5. Renderer `antv-g2-dashboard`

Файлы:

- `Mozaika/skills/antv-g2-dashboard/SKILL.md`;
- `Mozaika/skills/antv-g2-dashboard/scripts/build_dashboard.js`.

Изменения в нормализации и проверке:

1. Добавить функцию нормализации текста: Unicode NFKC, lowercase, `ё/е` только для сравнения, удаление пунктуации, схлопывание пробелов.
2. Блокировать:
   - точное совпадение `beat.title` и `beat.message`;
   - почти полное включение одного поля в другое без новой информации;
   - высокое token-overlap между `headline` и `core_message`;
   - повтор соседних beats;
   - одинаковые governing thoughts/grouping principles у разных options.
3. Для near-duplicate использовать детерминированный порог, зафиксированный тестами; результат проверки сохранять в narrative-integrity audit.
4. Не исправлять смысл автоматически и не обрезать сообщение молча. При нарушении отклонять spec с точным путём поля.

Изменения HTML:

1. Не соединять заголовок и сообщение в одну строку `title — message`.
2. Выводить title как короткий подзаголовок, message — отдельным абзацем.
3. Выводить `research_title_verbatim` в едином kicker/eyebrow каждой карточки, а не дублировать его внутри narrative headline.
4. Добавить видимый блок полного покрытия пользовательского задания.
5. Не показывать option ids, requirement ids, claim ids, номера выбора и другую служебную информацию.
6. Сохранить текущую физическую изоляцию карточек от dashboard HTML.
7. Сохранить точные токены брендбука и отдельные design receipts.

### 4.6. Storyline role `design-executive-storyline`

Файл:

- `Mozaika/skills/design-executive-storyline/SKILL.md`.

Изменения:

1. Принимать только selected decision checkpoint и `selected-storytelling-card.html`, а не исходную страницу со всеми вариантами.
2. Обязательно принимать research brief, requirement-claim map и dashboard claim-chart map.
3. До написания storyline создавать `storyline-requirements-coverage.json`.
4. Для каждого обязательного пункта указывать:
   - место в аргументе;
   - связанные claims и caveats;
   - целевой slide id;
   - подходящую диаграмму/таблицу или честную причину её отсутствия;
   - статус покрытия.
5. Сохранять выбранный grouping principle и governing thought без подмены.
6. Разрешать менять длину презентации и группировать пункты ради ясности, но не удалять обязательные вопросы.
7. Не выдавать outline при потере хотя бы одного requirement.
8. Запускать отдельный review:
   - selected-story preservation;
   - headline-sequence review;
   - duplicate message review;
   - requirements coverage review;
   - evidence/caveat review.

### 4.7. Method skill `executive-storytelling`

Файл:

- `Mozaika/skills/executive-storytelling/SKILL.md`.

Изменения:

1. Дополнить slide-intent rules полями `slide_id` и `requirement_ids`.
2. Требовать, чтобы последовательность заголовков одновременно:
   - рассказывала выбранную историю;
   - отвечала на все обязательные пункты пользователя;
   - не повторяла один и тот же вывод на нескольких экранах без нового доказательства.
3. Различать допустимое возвращение к главному тезису и недопустимый повтор содержания.
4. В review добавить матрицу «requirement → claim → slide → visual».
5. Не разрешать заменять конкретный пользовательский срез общей категорией. Например, «какие задачи выполняют специалисты» нельзя считать раскрытым общим слайдом Work/Personal/Coursework без релевантной детализации.

### 4.8. Presentation outline contract

Файл:

- `Mozaika/skills/mozaika/contracts/presentation-outline.schema.json`.

Выпустить `presentation-outline/v2` со следующими изменениями:

1. Добавить каждому экрану обязательный уникальный `slide_id`.
2. Заменить нестабильную ссылку по `slide_titles` на `slide_ids`; человекочитаемые titles оставить как проверяемое дополнение.
3. Сделать `research_questions_coverage` обязательным и непустым, когда research brief содержит требования.
4. Добавить `requirement_id` и `text_verbatim` каждой coverage entry.
5. Проверять, что каждый `slide_id` существует.
6. Проверять, что claims coverage entry входят в claims соответствующих экранов.
7. Добавить один структурированный блок `provenance` с `selected_decision_id`, `selected_card_artifact_id`, `storyline_artifact_id`, `research_brief_sha256`, не смешивая lineage с render-полями.
8. Для статуса `covered` требовать content slide с доказательным visual/table/diagram, а не только титульный или секционный экран.
9. Для `partial/unanswered` требовать видимую caveat/limitation entry; `solved` запрещать, если неполнота не вызвана реальным дефицитом данных и не показана пользователю.
10. Запретить рендереру менять `slide_id`, requirement mapping, governing thought, claim values и narrative order.
11. Для `insight_deck` требовать полный requirement mapping; для `routine_report` разрешить `coverage_mode=fixed_template` с hash утверждённого шаблона и проверкой его обязательных разделов. Routine admission не должен зависеть от owner-choice checkpoint.

### 4.9. Presentation renderer `html-presentation-studio`

Файлы:

- `Mozaika/skills/html-presentation-studio/SKILL.md`;
- `Mozaika/skills/html-presentation-studio/scripts/scaffold.py`;
- `Mozaika/skills/html-presentation-studio/scripts/audit.py`;
- `Mozaika/skills/html-presentation-studio/scripts/browser_audit.py`;
- новые скрипты проверки outline/coverage при необходимости.

Изменения:

1. Добавить обязательный Mozaika entrypoint, принимающий schema-valid `presentation-outline/v2`, а не свободный markdown outline.
2. До рендера проверять research brief, selected checkpoint и coverage map.
3. Сохранять `slide_id` как DOM id и формировать отдельный внутренний `presentation-manifest.json` с requirement/claim mapping.
4. Не выводить внутренние ids зрителю.
5. Не разрешать рендер из ad-hoc скрипта, не указанного в execution receipt.
6. Сохранять self-contained single-file HTML; любой загружаемый из сети script, style, font или chart CDN считать blocking failure. Проверенный third-party runtime, физически встроенный в итоговый HTML и отражённый в source/license ledger, разрешён.
7. Статический audit должен проверять:
   - количество и уникальность slide ids;
   - соответствие presentation manifest;
   - наличие всех обязательных требований;
   - отсутствие placeholder и служебной информации;
   - отсутствие внешних зависимостей;
   - отсутствие повторяющихся заголовков/основных сообщений.
8. Browser audit должен:
   - посетить каждый экран, а не только первый;
   - проверить все заявленные viewports;
   - активировать интерактивные графики и навигацию;
   - проверить console/page errors;
   - проверить clipping/overflow/overlap;
   - сохранить capture каждого экрана хотя бы на основном viewport и проблемных состояний на остальных;
   - сверить реально существующие DOM slide ids с outline.
9. Результатом должны быть deck, source/manifest, static audit, browser audit, screenshots и design receipt.

### 4.10. Completion и validation gates

Файлы:

- `Mozaika/skills/mozaika/contracts/completion-gate.schema.json`;
- `Mozaika/skills/mozaika/plugin.py`.

Выпустить `mozaika-completion-gate/v2` и потребовать:

- research brief artifact и hash;
- полное множество requirement ids;
- passing narrative-integrity audits для all-options cards, selected card, storyline и presentation;
- owner-choice gate receipt;
- selected decision checkpoint;
- storyline gate receipt;
- schema-valid presentation outline receipt;
- presentation skill selection и execution receipts;
- presentation coverage result;
- offline/self-contained result;
- visual QA всех экранов;
- business-language и visual-layout audits;
- отсутствие `review_status=skipped`, `objective_status=not_evaluated` и verification failures для `solved`.

Нельзя принимать в качестве доказательства:

- существование файла;
- наличие слова `Chart.js`;
- приблизительное число JSON-объектов;
- скриншот только первого экрана;
- текстовое заявление агента без gate receipt;
- булево `owner_choice_gate_passed=true` без durable checkpoint и выбранного артефакта.

### 4.11. Runtime-копии скиллов

После успешной реализации и тестов синхронизировать изменённые файлы из:

- `/Users/iplab/Ouroboros/Mozaika/skills/...`

в:

- `/Users/iplab/Ouroboros/data/skills/external/...`.

Правила:

1. Источник правды — проектная папка `Mozaika/skills`.
2. Не менять сторонние `anthropic-*` skills, если исправление относится к orchestration wrapper или contract.
3. Не трогать пользовательские runtime-логи, state и исторические artifacts.
4. После копирования проверить SHA-256 или побайтовое равенство каждой изменённой пары.
5. Перезапускать/перезагружать Ouroboros только штатным безопасным способом после прохождения тестов.
6. После изменения runtime-reachable payload проверить новый content hash: прежний review обязан стать stale. Запустить штатный re-review, не подменять его owner attestation и не включать изменённый skill до допустимого review status.

## 5. Алгоритм нового сценария

### Стадия A. Intake

1. Сохранить исходный prompt и материалы.
2. Создать `assignment.md`.
3. Извлечь `research-brief.json`.
4. Дословно показать во внутреннем run note список распознанных вопросов/срезов.
5. Если формулировка действительно неоднозначна и меняет весь анализ, задать один ранний вопрос; иначе продолжить автономно.

### Стадия B. Data

1. Проанализировать данные.
2. Создать claims и evidence.
3. Создать `requirement-claim-map.json` для каждого пункта.
4. Зафиксировать partial/unanswered без удаления пункта.

### Стадия C. Dashboard и варианты

1. Построить dashboard со всеми пользовательскими срезами.
2. Создать 2–3 действительно разные narrative options.
3. Для каждой option построить полную requirements coverage map.
4. Запустить schema, claim и narrative-integrity gates.
5. Отрендерить отдельные dashboard и cards HTML.
6. Запустить browser/language/layout QA.
7. Создать pending owner-decision checkpoint.
8. Реально показать пользователю оба HTML и только затем попросить выбор.

### Стадия D. Выбор и продолжение

1. Принять номер, заголовок или однозначную формулировку выбора.
2. Восстановить pending checkpoint даже в новой задаче.
3. Проверить допустимость выбранной option.
4. Выпустить selected checkpoint.
5. Создать новый `selected-storytelling-card.html` только с выбранной карточкой.
6. Проверить его и только затем подтвердить выбор пользователю/продолжить.

### Стадия E. Storyline

1. Storyline-агент читает selected card, а также research brief и доказательства.
2. Создаёт storyline и карту покрытия.
3. Проверяет все пункты, повторы, выбранную логику и claims.
4. Создаёт `presentation-outline/v2` с уникальными slide ids.
5. Presentation gate не открывается при любой потере обязательного пункта.

### Стадия F. Presentation

1. Выбрать skill по стандартному lifecycle; первым проверить `html-presentation-studio`.
2. Передать ему только валидный outline, brandbook и immutable refs.
3. Создать богатую автономную HTML-презентацию.
4. Проверить каждый экран, визуализации, переходы, offline-режим и coverage.
5. Исправления создавать как новые immutable revisions.

### Стадия G. Completion

1. Сверить requirement coverage на dashboard, cards, storyline и presentation.
2. Сверить выбранную карточку с governing thought и последовательностью экранов.
3. Проверить все gate receipts и runtime outcome axes.
4. Вернуть `solved` только при полном подтверждённом прохождении.

## 6. Тестовый план

### 6.1. Regression fixtures

Добавить минимизированные fixtures на основе выявленного сбоя:

- шесть пользовательских срезов;
- карточка с `title == message`;
- `headline`, повторяющий `core_message`;
- три карточки с одинаковым claim;
- отсутствующий в карточках шестой срез;
- presentation outline без «запросов пользователей»;
- ответ владельца после завершения исходной задачи;
- презентация с CDN и проверкой только первого экрана.

Не копировать в fixtures большие пользовательские данные; использовать небольшой синтетический набор с тем же классом ошибок.

### 6.2. Contract tests

В `Mozaika/tests/test_mozaika_contracts.py` добавить проверки:

- research brief требует полный дословный набор;
- каждая owner-choice option покрывает одинаковое обязательное множество;
- coverage с неизвестным requirement/claim/beat отклоняется;
- presentation coverage с неизвестным slide id отклоняется;
- все slide ids уникальны;
- старые v1 fixtures остаются читаемыми, но не принимаются как новый run output;
- completion v2 требует selected checkpoint, storyline, outline и content audits.

### 6.3. Plugin/gate tests

В `Mozaika/tests/test_mozaika_plugin.py` добавить проверки:

- owner choice fails при пропущенном срезе;
- owner choice fails при exact/near duplicate;
- owner choice fails при одном claim для всех unrelated beats;
- steering failure не превращается в подтверждённый выбор;
- новая задача успешно восстанавливает pending checkpoint;
- неверный/двусмысленный выбор не меняет checkpoint;
- completion fails при `review_status=skipped`;
- completion fails при ad-hoc renderer без receipt;
- completion fails при missing storyline/outline/coverage;
- completion fails при внешнем CDN.

### 6.4. Renderer tests

Для `antv-g2-dashboard`:

- корректные разные title/message проходят;
- одинаковые и почти одинаковые блокируются;
- все шесть пунктов видны в каждой карточке;
- служебные ids не видны;
- research title находится в kicker;
- dashboard не содержит card payload.

Для `html-presentation-studio`:

- каждый outline slide создаёт соответствующий DOM slide id;
- каждый requirement отображён хотя бы на одном content slide;
- все экраны проверяются browser audit;
- внешний URL блокирует приёмку;
- отсутствие одного требуемого экрана блокирует completion;
- выбранная история сохраняется в последовательности заголовков.

### 6.5. Сквозной тест

Прогнать синтетический сценарий:

1. Пользователь задаёт название и шесть срезов.
2. Data stage отвечает на все шесть.
3. Dashboard отображает все шесть.
4. Cards page показывает три разные стратегии и способ раскрытия всех шести.
5. Пользователь выбирает вариант после завершения первой задачи.
6. Новая задача восстанавливает checkpoint.
7. Selected card содержит одну стратегию.
8. Storyline покрывает все шесть.
9. Outline связывает их с конкретными slide ids.
10. HTML-презентация содержит релевантные данные по каждому срезу.
11. Все audits и completion gate проходят.

### 6.6. Миграция, время и поздний выбор

- Проверить, что v1-артефакт читается legacy-аудитором, но отклоняется completion gate v2 как результат нового запуска.
- Проверить единый алгоритм verbatim-нормализации на `LF`, `CRLF`, Unicode composed/decomposed и повторяющихся пробелах без изменения сохранённого оригинала.
- Проверить pending checkpoint сразу, после stale-порога, после explicit dismissal и после повторного выбора с `superseded` историей.
- Измерить время static/browser audit на 6, 14 и 30 экранах; задать разумный stage timeout и пакетировать screenshots без пропуска экранов.
- Проверить routine admission отдельно: фиксированный шаблон работает без owner-choice и полного insight mapping.

## 7. Порядок реализации

### Фаза 0. Минимальное безопасное исправление

- [x] Добавить отрицательные тесты exact/near duplicate карточек.
- [x] Исправить renderer так, чтобы title и message не склеивались и дубли блокировались.
- [x] Зафиксировать basic research brief без принудительного перевода всего pipeline на v2.
- [x] Сохранить pending checkpoint и запретить ложный ACK после неудачного steering.
- [ ] Прогнать оба текущих сценария v1, чтобы phase 0 не сломала routine и insight.

### Фаза 1. Контракты и fixtures

- [ ] Зафиксировать regression fixtures.
- [x] Добавить research brief и requirement-claim map.
- [x] Добавить обратно совместимые строгие admission-поля owner-choice/dashboard-spec и narrative-integrity audit.
- [x] Добавить decision checkpoint.
- [x] Добавить level-admission presentation outline и строгий insight completion поверх читаемого v1.
- [x] Сначала написать отрицательные tests, воспроизводящие прошлый сбой.

### Фаза 2. Карточки и dashboard gate

- [x] Обновить `build-insight-dashboard`.
- [x] Обновить `antv-g2-dashboard` validation и renderer.
- [x] Добавить полный пользовательский scope в HTML-карточки.
- [x] Добавить deterministic duplicate validation.
- [x] Проверить брендбук и отсутствие служебных полей.

### Фаза 3. Надёжный выбор и resume

- [x] Обновить Mozaika orchestration references.
- [x] Реализовать контракт, state machine и gate pending/selected/superseded/dismissed checkpoint lifecycle.
- [x] Запретить ложное подтверждение steering.
- [ ] Проверить продолжение из новой задачи по durable refs.

### Фаза 4. Storyline и outline

- [x] Обновить `design-executive-storyline`.
- [x] Обновить `executive-storytelling`.
- [x] Ввести requirement-to-slide mapping.
- [x] Добавить selected-story и duplicate review.

### Фаза 5. HTML presentation

- [x] Добавить строгий insight/routine admission entrypoint в `html-presentation-studio`.
- [x] Обновить static и browser audits.
- [x] Проверять каждый экран, coverage и offline assets.
- [x] Запретить ad-hoc renderer без lifecycle receipts.

### Фаза 6. Completion и документация скиллов

- [x] Обновить completion gate и plugin validation.
- [x] Обновить основной `SKILL.md`, scenario, contracts, gates и runtime references.
- [ ] Обновить `agents/openai.yaml`, только если metadata соответствующих скиллов реально изменилась.
- [x] Выполнить native Ouroboros manifest validation всех изменённых skill folders; Codex quick validator неприменим к расширенному Ouroboros frontmatter.

### Фаза 7. Тесты, синхронизация и повтор запуска

- [x] Запустить unit/contract/renderer/plugin tests.
- [ ] Запустить сквозной regression scenario.
- [x] Синхронизировать только проверенные project-файлы в `data/skills/external`.
- [x] Проверить побайтовое равенство project/runtime копий.
- [x] Проверить stale content hash и пройти штатный re-review изменённых runtime skills.
- [x] Перезагрузить Ouroboros.
- [ ] Повторить сценарий на реальном задании и проверить карточки/выбор/storyline/deck вручную.

## 8. Критерии готовности

Исправление считается завершённым, только если одновременно выполнено следующее:

- каждый пользовательский вопрос или срез существует в immutable research brief;
- data, dashboard, каждая карточка, storyline и presentation имеют проверяемое покрытие полного списка;
- карточка не проходит при одинаковых или почти одинаковых title/message/headline/core message;
- варианты отличаются способом аргументации, но не теряют общий пользовательский scope;
- пользователь видит в карточках, как каждый вариант раскроет заданные пункты;
- выбор после завершённой задачи восстанавливается через durable checkpoint без ложного подтверждения;
- выбранная карточка одна и именно она является входом storyline;
- presentation stage невозможно запустить без storyline и schema-valid outline;
- каждый обязательный пункт связан с существующим content slide и релевантным evidence-bearing visual/table/diagram;
- presentation renderer имеет skill-selection и execution receipts;
- HTML автономен и не использует CDN;
- browser QA проверяет все экраны, а не только титульный;
- completion gate не принимает skipped review, not evaluated objective или verification failures;
- исторические пользовательские артефакты не удалены и не перезаписаны;
- runtime-копии изменённых skills совпадают с проектными.

## 9. Что сознательно не менять

- Не возвращать жёсткую стилистическую цензуру: business-language validator остаётся ослабленным и блокирует только явные критические ошибки.
- Не модифицировать оригинальные `anthropic-*` skills ради исправления orchestration contract; приоритет и использование регулируются Mozaika wrapper и selection receipts.
- Не объединять storytelling cards обратно с dashboard.
- Не показывать внутренние ids, номера вариантов, hashes и contract metadata пользователю.
- Не переписывать исторические артефакты проблемного запуска.
- Не обещать `ouroboros://` callback, пока он не реализован в host/runtime; надёжность обеспечивается durable checkpoint и явным сообщением владельца.
