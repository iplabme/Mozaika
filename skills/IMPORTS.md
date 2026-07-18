# Реестр импортированных скиллов

Источник владельца — `/Users/iplab/Ouroboros/new-skills/ALL_SKILLS_BUNDLE.md`.
Из него восстановлены все 27 файлов девяти скиллов. Копии находятся в этом
репозитории и установлены в `/Users/iplab/Ouroboros/data/skills/external`.

## Идентификаторы

| Секция bundle | Установленный скилл |
|---|---|
| `dashboard-architect` | `anthropic-dashboard-architect` |
| `anthropics--data-validation` | `anthropic-data-validation` |
| `anthropics--data-visualization` | `anthropic-data-visualization` |
| `anthropics--interactive-dashboard-builder` | `anthropic-interactive-dashboard-builder` |
| `anthropics--performance-analytics` | `anthropic-performance-analytics` |
| `anthropics--pptx` | `anthropic-pptx` |
| `github--snowflake-semanticview` | `anthropic-snowflake-semanticview` |
| `anthropics--sql-queries` | `anthropic-sql-queries` |
| `anthropics--statistical-analysis` | `anthropic-statistical-analysis` |

Сохранены исходные инструкции, frontmatter, шаблон dashboard, лицензия и все
PPTX-утилиты. Runtime namespace `anthropic-*` задаётся именем каталога — именно
его Ouroboros использует для identity и state. Единственная правка bundle-файла:
невалидная однострочная YAML-строка `description` в dashboard переведена в
эквивалентный folded scalar, иначе штатный loader не мог разобрать manifest.
Старые дублирующие каталоги без префикса удалены из проекта, установленного пула
и lifecycle state.

Ouroboros определяет runtime identity по имени каталога. Markdown-only скиллы
остаются честными `instruction` payload: агент видит их metadata, а Mozaika до
применения обязана полностью прочитать `SKILL.md`. Наличие короткой инструкции
или `user-invocable: false` не снижает приоритет. Наличие утилит внутри
`anthropic-pptx` также не делает их автоматически исполняемыми через
`skill_exec`, пока manifest не объявляет `type: script` и `scripts`.

## Политика Mozaika

Перед каждым этапом сначала оцениваются подходящие установленные
`anthropic-*` скиллы. Если подходящий Anthropic-скилл есть, он используется;
отказ требует зафиксированной причины несовместимости, безопасности или
преимущества качества. `anthropic-pptx` исключён. `presentation-skill` назначен
владельцем единственным renderer последнего редактируемого PPTX-шага во всех
сценариях; основная HTML-презентация по-прежнему создаётся отдельным
HTML-рендерером. Для routine/weekly используется `mozaika-weekly`, для insight —
`mozaika-insight` и визуальная грамматика приложенного владельцем PPTX без
копирования его структуры и содержания.

Импорт не обходит trust lifecycle Ouroboros. После изменения payload его старое
ревью становится stale; перед включением нужны preflight, свежий review,
dependencies/grants при необходимости и enablement.

## HTML Presentation Studio

Источник: `/Users/iplab/Ouroboros/new-skills/html-presentation-studio-v1.0.0.zip`.
Очищенный runtime-набор установлен идентично в
`skills/html-presentation-studio` и
`data/skills/external/html-presentation-studio`. В исполняемый payload не вошли
дублирующие README, исследовательский и исторический validation-отчёты, checksum
manifest, старые результаты аудита и долгоживущий localhost-сервер.

Авторская методика презентации сохранена. Для совместимости с Ouroboros добавлены
append-only выходы в `OUROBOROS_SKILL_STATE_DIR`, запрет перезаписи и выхода за
state, browser QA без localhost и внешних URL, проверка только сгенерированного
state-confined HTML, fullscreen/overview, сохраняемые static/browser QA-отчёты и
поиск установленного Chromium/Chrome/Edge. Скилл назначен первым выбором этапа
presentation в Mozaika; Anthropic HTML-скиллы остаются поддержкой и резервом.

## Presentation Skill

Источник установленного payload: `data/skills/external/presentation-skill`.
Воспроизводимая копия без `node_modules` добавлена в `skills/presentation-skill`.
К исходной логике добавлены owner-approved пресеты `mozaika-weekly` и
`mozaika-insight`. Второй повторяет палитру, элементы и правила размещения
референса первого сценария, но не его данные, число, порядок или структуру
слайдов.
Перед runtime-использованием изменённая копия обязана пройти штатные preflight,
review, dependency reconciliation и enablement; state-файлы вручную не
подделываются.
