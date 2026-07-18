# Использование оригинальных Anthropic-скиллов в Mozaika

## Содержание

- Статус и общее правило
- Карта по этапам Mozaika
- Подробное описание девяти скиллов
- Рекомендуемые связки для анализа данных
- Артефакты и receipts
- Антипаттерны

## Статус и общее правило

Девять `anthropic-*` каталогов восстановлены из
`new-skills/ALL_SKILLS_BUNDLE.md`; исходные инструкции, шаблоны, лицензия и
утилиты сохранены. Изменено имя каталога; в dashboard только исправлена
структурно невалидная YAML-запись description без изменения текста. Ouroboros определяет runtime identity по имени
каталога, а в контекст агента автоматически передаёт лишь metadata — не всё тело
`SKILL.md`. Поэтому Mozaika обязана открыть и полностью прочитать файл выбранного
скилла до применения. Markdown-only payload каталогизируется как `instruction`;
короткое тело или `user-invocable: false` не отменяет его приоритет как метода.

Отсюда следуют четыре правила:

1. Выбирать Anthropic-скилл как метод этапа, только если он точно соответствует
   данным и ожидаемому артефакту.
2. Отдельно выбирать исполняющий инструмент, когда метод требует SQL, Python,
   Chart.js или другой runtime. Не считать пример кода доказательством исполнения.
3. Сохранять отдельно `instruction receipt` применения метода и `execution
   receipt` фактического исполнения/рендера. Оба должны ссылаться на итоговые
   артефакты.
4. Если подходящий `anthropic-*` существует, использовать его; отказ разрешён
   только с записанной причиной несовместимости, безопасности или качества.
   Короткая инструкция не считается несовместимостью.

Для нетривиального data-этапа обычно достаточно одного основного аналитического
метода и одного-двух вспомогательных. Не запускать все девять автоматически.

## Карта по этапам Mozaika

| Этап | Приоритетный Anthropic-скилл | Роль | Когда действительно нужен |
|---|---|---|---|
| Инвентаризация и scope | Нет прямого Anthropic-скилла | Использовать специализированный inventory skill | URL-коллекции, директории, множество датасетов; сначала доказать полноту охвата. |
| Профилирование и подготовка запросов | `anthropic-sql-queries` | Метод проектирования SQL | Реляционные/табличные данные, joins, cohorts, funnels, deduplication, window calculations. |
| Распределения, тренды и выбросы | `anthropic-statistical-analysis` | Основной аналитический метод | Числовые метрики, временные ряды, сравнение сегментов, гипотезы, аномалии. |
| Контроль качества анализа | `anthropic-data-validation` | Независимый QA-слой | После профиля, после значимых преобразований и обязательно перед handoff руководителю. |
| Аналитические графики | `anthropic-data-visualization` | Метод выбора и проверки визуального кодирования | Когда claim уже рассчитан и нужно выбрать честный, доступный график. |
| Маркетинговый анализ | `anthropic-performance-analytics` | Предметный аналитический слой | Только email, social, paid, SEO, campaign/channel performance. |
| Дашборд | `anthropic-interactive-dashboard-builder`, затем `anthropic-dashboard-architect` | HTML UX, визуальная архитектура и интерактивность | После claim gate: автономный dashboard, фильтры, attention cards, Chart.js, профессиональная подача. |
| Snowflake semantic layer | `anthropic-snowflake-semanticview` | DDL и CLI-валидация semantic view | Только при явной Snowflake-задаче, настроенном соединении и подтверждённом внешнем полномочии. |
| Storyline | Обычно ни один как основной | Использовать специализированный storytelling skill | Anthropic data skills могут проверять evidence, но не выбирают управленческий сюжет. |
| Финальная HTML-презентация | `html-presentation-studio` — назначенный рендерер; `anthropic-interactive-dashboard-builder` и `anthropic-dashboard-architect` — поддержка/резерв | Presentation method, HTML interaction/design support | Сначала проверить назначенный рендерер; Anthropic применять для сложных графиков или при зафиксированной несовместимости. |
| PowerPoint | `presentation-skill` | Финальный редактируемый PPTX во всех сценариях | `mozaika-weekly` после HTML в routine/weekly; `mozaika-insight` после HTML и speaker cards в insight. Всегда сверять факты и выполнять render QA. `anthropic-pptx` запрещён. |

## `anthropic-data-validation`

### Что даёт

Метод независимого QA анализа перед показом заинтересованным лицам:

- проверка методологии и соответствия вопросу;
- проверка точности вычислений и логики агрегаций;
- поиск survivorship bias и других систематических смещений;
- проверка воспроизводимости и достаточности документации;
- отделение подтверждённых фактов от интерпретаций.

Оригинальная инструкция короткая и не содержит вычислительного движка. Это
review method, а не замена профилированию, SQL или статистике.

### Где использовать

На data-этапе применять три контрольные точки:

1. После инвентаризации: соответствует ли фактический scope обещанному.
2. После очистки/агрегаций: не изменили ли преобразования смысл, знаменатель,
   популяцию или распределение.
3. Перед handoff: воспроизводимы ли claims, раскрыты ли ограничения и bias.

Повторно применять перед публикацией дашборда, если визуальная агрегация или
фильтры могут изменить интерпретацию.

### Требуемые входы

- вопрос владельца и критерии успеха;
- scope ledger и source manifest;
- профиль качества и журнал преобразований;
- определения KPI и версии запросов;
- claim registry с evidence ids;
- список исключений и sensitivity comparison.

### Ожидаемый выход

`validation-report.json` или эквивалент с полями: проверка, статус, severity,
доказательство, затронутые claim ids, требуемое исправление и остаточный риск.
Не принимать общий текст «всё проверено» без проверок, связанных с артефактами.

## `anthropic-statistical-analysis`

### Что даёт

Самый полезный из семи скиллов для общего анализа данных. Он покрывает:

- центр распределения: mean, median и их расхождение;
- spread: standard deviation, IQR, coefficient of variation, range;
- percentiles p1/p5/p25/p50/p75/p90/p95/p99;
- форму распределения, границы и heavy tails;
- moving averages, WoW/MoM/YoY и сезонность;
- простые forecasts с обязательным диапазоном неопределённости;
- z-score, IQR и percentile approaches для поиска выбросов;
- point anomalies и sustained change points во временных рядах;
- t-test, proportion z-test, paired test, ANOVA, Mann–Whitney и chi-square;
- effect size, confidence interval, statistical и practical significance;
- multiple comparisons, Simpson's paradox, survivorship bias, ecological
  fallacy и ложную точность.

### Где использовать

Выбирать основным методом data-этапа, когда запрос требует найти инсайты, а в
данных есть числовые признаки, временные ряды, сегменты или экспериментальные
группы. Применять после проверки scope и базового data profile, но до фиксации
insight candidates.

Особенно полезен для:

- проверки, не скрывает ли среднее перекошенное распределение;
- сравнения сегментов и периодов;
- отличия шума от устойчивого изменения;
- обоснования уведомления об исключении выбросов;
- проверки, имеет ли различие деловой смысл, а не только маленький p-value;
- выявления mix shift и Simpson's paradox до управленческого вывода.

### Ограничения

- Не удалять выбросы автоматически. Сначала классифицировать: ошибка данных,
  реальный экстремум или отдельная популяция.
- Не использовать z-score без проверки близости к нормальному распределению.
- Не объявлять causal effect по корреляции.
- Не выдавать point forecast без диапазона и допущений.
- Не применять тест без зафиксированных H0/H1, alpha, размера выборки и причины
  выбора теста.
- Python-фрагменты в инструкции являются примерами. Для исполнения требуется
  отдельно выбранный готовый runtime/skill и его receipt.

### Ожидаемый выход

`statistical-findings.json` или эквивалент:

- population и grain;
- method и assumptions;
- sample size и missing-data treatment;
- estimate, uncertainty/effect size и practical impact;
- counterevidence и segment stability;
- outlier sensitivity: with/without flagged rows;
- claim id, evidence artifact ids и честная квалификация вывода.

## `anthropic-sql-queries`

### Что даёт

Подробный справочник по PostgreSQL, Snowflake, BigQuery, Redshift и Databricks,
а также общие шаблоны:

- date/time, strings, JSON, arrays и semi-structured data;
- window functions, ranks, lag/lead, running totals и moving averages;
- читаемые многошаговые CTE;
- cohort retention и funnel analysis;
- deduplication через `ROW_NUMBER`;
- безопасное деление, explicit casts и квалифицированные join columns;
- диалектные performance practices и отладку типовых ошибок.

### Где использовать

Выбирать на data-этапе как метод проектирования запроса, когда факты должны быть
получены из SQL-совместимых таблиц или локального аналитического движка. Особенно
важен до cohort/funnel/rank/share расчётов и при переносе между диалектами.

Скилл должен был бы предотвратить ошибки последнего запуска: window expression
в `WHERE`, ссылки на отсутствующие `score`/`r`, неявные типы и несовместимые
диалектные функции выявляются до исполнения через schema-aware design.

### Обязательная последовательность

1. Зафиксировать engine и точный SQL dialect.
2. Прочитать schema: таблицы, колонки, типы, grain, keys и nullable fields.
3. Сформулировать ожидаемый результат и ручной sanity example.
4. Построить запрос CTE-ступенями; window results фильтровать во внешнем CTE.
5. Выполнить dry run/`EXPLAIN` или bounded sample выбранным engine.
6. Сверить row counts, duplicates, joins и denominators.
7. Только затем запускать полный запрос и регистрировать результат.

### Ограничения

Это instruction skill, а не SQL engine. Он не подтверждает, что запрос
выполнился, не предоставляет доступ к Snowflake/BigQuery и не разрешает внешние
чтения. Выполнение и external authority оформляются отдельно.

### Ожидаемый выход

`query-catalog.json` или эквивалент: dialect, engine, schema fingerprint,
parameter values, SQL text/hash, expected grain, dry-run evidence, execution
receipt, output row count, checks и связанные claim ids. Каждая исправленная
версия получает новый id; не перезаписывать неудачный запрос.

## `anthropic-data-visualization`

### Что даёт

Метод выбора графика по типу отношения в данных и правила честного дизайна:

- trend → line; category comparison/rank → bar/dot;
- distribution → histogram/box/violin;
- correlation → scatter/heatmap;
- composition → stacked forms с ограничениями;
- flow → Sankey/funnel; multiple KPIs → small multiples/dashboard;
- bar axis starts at zero, consistent panel scales, uncertainty is visible;
- insight-led title, readable units, source/date range and meaningful sort;
- color-blind safe palette, labels/patterns beyond color, alt text and table
  alternative.

Он также содержит Python patterns для matplotlib/seaborn/plotly, formatting
helpers и accessibility checklist.

### Где использовать

- На data-этапе — после расчёта claims для exploratory visual checks:
  распределения, сегменты, тренды, outlier sensitivity.
- На dashboard-этапе — как основной design review выбранного renderer.
- На presentation-этапе — для проверки честности графиков внутри HTML screens.

### Ограничения

- Не использовать график для доказательства ещё не рассчитанного claim.
- Не создавать смысловую стратегию: визуализация показывает evidence, а не
  выбирает executive storyline.
- Избегать 3D, лишних pie/donut, misleading dual axes и визуального декора без
  информационной функции.
- Python examples не дают установленного matplotlib/seaborn/plotly. Если
  runtime недоступен, перенести принципы на готовый Chart.js/G2 renderer, а не
  устанавливать глобальные пакеты молча.

### Ожидаемый выход

`chart-intents.json`: claim id, question, relationship, selected chart,
alternatives rejected with reason, axes/units, uncertainty, highlights,
accessibility description, data-table fallback и renderer target.

## `anthropic-performance-analytics`

### Что даёт

Предметный метод анализа marketing performance: ключевые метрики, тренды,
сравнение каналов и кампаний, выявление работающих/неработающих элементов и
optimization recommendations. Оригинальная инструкция не содержит готовой
таксономии KPI или вычислительного кода.

### Где использовать

Только когда scope явно связан с email, social, paid, SEO, campaign или channel
performance. На data-этапе использовать после определения KPI и периода; на
dashboard-этапе — для группировки фактов по channel/campaign/funnel; на
storyline-этапе — только как предметную проверку рекомендаций.

### Требуемые уточнения до анализа

- бизнес-цель кампании и primary KPI;
- spend, attribution model/window и currency;
- exposure/opportunity denominator;
- target/baseline и сравниваемый период;
- различие observed conversions и attributed conversions;
- ограничения tracking и неполные каналы.

Без этих определений не рассчитывать ROAS/CAC/CTR/CVR и не ранжировать каналы.
Рекомендация должна ссылаться на проверенный эффект и ожидаемое влияние, а не
только на корреляцию.

## `anthropic-interactive-dashboard-builder`

### Что даёт

Краткое, но точное требование к результату: профессиональный self-contained
interactive HTML dashboard с Chart.js, dropdown filters и возможностью открыть
и передать файл без сервера.

### Где использовать

- Основной кандидат метода dashboard-этапа после validation/claim gates.
- Кандидат presentation-этапа, если выбранный исполнитель расширяет dashboard
  до последовательности HTML screens и выполняет весь presentation contract.
- Не использовать на раннем data-этапе вместо инвентаризации, расчётов или QA.

### Ограничения и усиление Mozaika

Оригинальная инструкция не задаёт скрипт, schema, offline dependency packaging,
browser QA или доступность. Поэтому Mozaika добавляет обязательные требования:

- inline/local assets без сетевой зависимости для основной функциональности;
- claim-to-chart mapping и одинаковые значения во всех представлениях;
- клавиатурное управление фильтрами и графиками;
- accessible labels и data-table/static fallback;
- desktop/compact viewport QA;
- для презентации дополнительно slide navigation, fullscreen, overview,
  reduced motion и print styles.

## `anthropic-dashboard-architect`

### Что даёт

Полный дизайн-процесс premium single-file HTML dashboard: адаптация плотности
под аудиторию, поиск anomalies/trends/concentration/bottlenecks/target gaps,
выбор честного типа графика, KPI tiles, heatmaps, funnels и фирменные карточки
«требуют внимания». В bundle сохранён `scripts/template.html` с двумя темами и
готовыми паттернами компонентов.

### Где использовать

- Главный Anthropic-кандидат dashboard-этапа, когда важны executive polish,
  attention cards, композиция и сильная визуальная иерархия.
- Кандидат presentation-этапа вместе с
  `anthropic-interactive-dashboard-builder`, если исполнитель способен превратить
  dashboard-компоненты в storyline-driven экраны и выполнить HTML-контракт.
- После data validation: скилл не заменяет инвентаризацию, расчёты и evidence.

### Усиление Mozaika

Не повторять интервью, если audience и вопросы уже переданы handoff. Исходный
шаблон использует CDN Chart.js, поэтому для требования автономности необходимо
встроить или локально упаковать runtime. Перед handoff обязательны claim mapping,
keyboard/accessibility fallback, desktop/compact browser QA и проверка всех
чисел по claim registry.

## `anthropic-snowflake-semanticview`

### Что даёт

Процесс создания и диагностики Snowflake semantic views: проверка star schema,
DDL, обязательные synonyms/comments, временное имя для валидации, исполнение
через `snow sql`, sample query и очистка временного объекта.

### Где использовать

- Data-этап для явной задачи построения или исправления semantic layer в
  Snowflake.
- Не использовать для обычных локальных CSV/Parquet или как общий SQL-скилл;
  там первым кандидатом остаётся `anthropic-sql-queries`.

### Gate внешнего действия

Наличие скилла не даёт доступ к Snowflake. До первого `snow` вызова нужны
подтверждённые database/schema/role/warehouse/connection и полномочие владельца.
Создание, изменение и удаление объектов — `owner_choice`; DDL и CLI output
сохраняются как versioned artifacts, а временный объект удаляется только после
проверки финального результата.

## `anthropic-pptx`

### Что даёт

Полный PowerPoint workflow: чтение через MarkItDown, thumbnail overview,
unpack/edit/clean/pack, создание через PptxGenJS, дизайн-паттерны, зависимости
LibreOffice/Poppler и обязательный render–inspect–fix–verify цикл.

### Политика Mozaika

Не использовать ни на одном этапе Mozaika. Владелец назначил отдельный
`presentation-skill`: он создаёт финальный редактируемый PPTX после принятого
HTML, а в `insight_deck` — после карточек спикера, с отдельным
`mozaika-insight` профилем. `anthropic-pptx` дополнительно требует
Python/npm/system dependencies и не объявляет их как Ouroboros executable
entries в сохранённом оригинале.

Скилл остаётся доступным для отдельных задач Ouroboros, где пользователь прямо
просит прочитать, изменить или создать `.pptx`. Его дизайн-советы нельзя
подмешивать как скрытую причину выбора PowerPoint в HTML-кампании.

## Рекомендуемые связки для анализа данных

### Универсальный табличный анализ

1. Специализированный inventory skill доказывает scope и сохраняет raw sources.
2. `anthropic-sql-queries` проектирует schema-aware вычисления; отдельный engine
   выполняет и возвращает receipt.
3. `anthropic-statistical-analysis` описывает распределения, сегменты, тренды,
   выбросы и uncertainty.
4. `anthropic-data-validation` независимо проверяет scope, transformations,
   denominators, bias и claims.
5. `anthropic-data-visualization` формирует chart intents только для прошедших
   проверку claims.

Не обязательно применять SQL, если источник не табличный или расчёты уже
воспроизводимо выполнены другим engine. Validation обязателен как метод QA для
нетривиального анализа; при неготовности этого скилла выбрать эквивалентный
проверенный QA method.

### Анализ временного ряда

Использовать `anthropic-statistical-analysis` как основной метод: raw series,
moving averages, same-period comparisons, seasonality, point anomalies и change
points. Затем `anthropic-data-validation` проверяет календарь, timezone,
неполные периоды и изменение определения метрики. `anthropic-data-visualization`
задаёт честный line/small-multiple chart с диапазоном неопределённости.

### Выбросы и очистка

Статистический скилл предлагает candidates, но решение принимает data-role:

1. проверить распределение и выбрать уместный method;
2. классифицировать каждую группу выбросов;
3. сохранить flagged/excluded rows;
4. рассчитать результат with/without;
5. применить `anthropic-data-validation` к смыслу и bias;
6. уведомить владельца об обратимом исключении или запросить выбор, если смысл
   меняется.

### Маркетинговые данные

Добавить `anthropic-performance-analytics` к универсальной связке только после
фиксации attribution/KPI contract. SQL отвечает за reproducible metrics,
statistics — за устойчивость различий, performance analytics — за предметную
интерпретацию, validation — за финальную проверку, visualization — за подачу.

### Анализ без числовой статистики

Для текстов, диалогов, изображений или иных неструктурированных данных эти
скиллы не являются автоматически достаточными. Сначала выбрать профильный skill
из полного пула. Anthropic validation может проверить методологию и bias, а
statistics — только результаты корректно определённого кодирования/разметки.

## Артефакты и receipts

Для каждого применённого instruction skill сохранить:

- `skill_name`, content hash и fresh review fingerprint;
- роль: `primary_method`, `supporting_method` или `qa_method`;
- входные artifact ids и точный вопрос к методу;
- применённые правила/разделы инструкции;
- созданные output artifact ids;
- ограничения и то, что скилл намеренно не делал.

Если метод потребовал исполнения, отдельный receipt должен назвать engine,
версию input specification, exact entry/command, exit status, stdout/stderr
artifact refs и фактический output hash. Instruction receipt не заменяет
execution evidence.

## Антипаттерны

- Выбирать все `anthropic-*` только из-за приоритета источника.
- Называть Python или SQL пример выполненным анализом без execution receipt.
- Использовать `anthropic-data-validation` как декларативную печать качества.
- Автоматически удалять строки, найденные статистическим правилом.
- Подменять causal claim корреляцией или p-value.
- Сначала рисовать график, затем подгонять под него claim.
- Использовать marketing skill для любого набора KPI вне маркетинга.
- Считать одностраничный dashboard полноценной HTML-презентацией без
  storyline-driven screens и presentation QA.
- Выбирать `anthropic-pptx` внутри Mozaika.
