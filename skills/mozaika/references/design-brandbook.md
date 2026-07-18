# Обязательный брендбук Mozaika

Канонический runtime-источник правды для дизайна находится вне payload скилла, чтобы бинарные референсы не блокировали text-only review Ouroboros:

- `data/brandbook/mozaika/BRANDBOOK.md`
- `data/brandbook/mozaika/manifest.json`
- `data/brandbook/mozaika/tokens.css`
- `data/brandbook/mozaika/references/`
- `data/brandbook/mozaika/templates/speaker-story-cards.template.html`
- `data/brandbook/mozaika/templates/scenario-2-dashboard.template.html`
- `data/brandbook/mozaika/templates/scenario-2-presentation.template.html`
- `data/brandbook/mozaika/templates/scenario-2-presentation-skill-outline.example.json`

Эти значения — **канонические пути для контрактов, handoff и design-receipt**, а не готовые аргументы файловых инструментов. `runtime_data` уже указывает на каталог `data/`, поэтому при чтении через Ouroboros убирай ровно начальный префикс `data/`:

- каталог: `list_files(root="runtime_data", path="brandbook/mozaika")`
- брендбук: `read_file(root="runtime_data", path="brandbook/mozaika/BRANDBOOK.md")`
- манифест: `read_file(root="runtime_data", path="brandbook/mozaika/manifest.json")`
- токены: `read_file(root="runtime_data", path="brandbook/mozaika/tokens.css")`
- референсы: `list_files(root="runtime_data", path="brandbook/mozaika/references")`
- шаблон карточек спикера: `read_file(root="runtime_data", path="brandbook/mozaika/templates/speaker-story-cards.template.html")`

Никогда не вызывай `root="runtime_data"` с `path="data/brandbook/..."`: это разрешается как `data/data/brandbook/...` и гарантированно ведёт не туда. В JSON-контрактах, конфигурации пула и квитанциях, напротив, сохраняй полный канонический путь `data/brandbook/...`; не заменяй его укороченной tool-relative формой.

Проектная копия для разработки находится в `Mozaika/brandbook/`.

Перед этапом `dashboard`, созданием `storytelling-cards.html`, отчётом, `presentation` или финальным `speaker-story-cards.html`:

1. Прочитай `BRANDBOOK.md`, `manifest.json` и `tokens.css`; выбери референс нужного типа.
2. Проверь SHA-256 манифеста и выбранных референсов. Передай immutable artifact refs в handoff.
3. Добавь выбранному renderer-скиллу точную инструкцию: **«Брендбук Mozaika — источник правды для дизайна. Реализуй именно его композицию, токены и паттерны для данного типа артефакта. Встроенные темы renderer запрещены, если владелец явно не переопределил брендбук».**
4. После реальной браузерной проверки сохрани `design-receipt.json` по `mozaika-design-receipt/v1` и зарегистрируй его как новый immutable QA-артефакт.
5. Не заявляй `solved`, пока все обязательные визуальные этапы не имеют валидной квитанции со статусом `pass`.

Для `weekly_autopilot` дополнительно прочитай tool-relative
`brandbook/mozaika/references/scenario-2-weekly-autopilot.md` и используй точные
scenario-2 шаблоны из списка выше. После принятого HTML последний PPTX создаёт
только `presentation-skill` с пресетом `mozaika-weekly`; `pptx` и
`anthropic-pptx` запрещены. Отрендери все слайды и сохрани отдельную execution
receipt, связанную с текущими outline и PPTX SHA-256.

Для `insight_deck` дополнительно прочитай tool-relative
`brandbook/mozaika/references/scenario-insight-presentation-style.md` и используй
`brandbook/mozaika/templates/scenario-insight-presentation-skill-outline.example.json`.
Последний PPTX создаёт только `presentation-skill` с `mozaika-insight` после
HTML и карточек спикера. Owner-reference задаёт визуальные токены и грамматику
размещения, но не число, порядок, темы или конкретную структуру слайдов.

Для `speaker-story-cards.html` шаблон обязателен: renderer заменяет только содержимое карточек, сохраняет его светлую портретную композицию, навигацию, клавиатуру, свайп, печать и reduced-motion. Машинные `slide_id`, `claim_id`, хеши и статусы остаются только во внутреннем `speaker-story-cards.json`, а не в видимом HTML.

Явное указание владельца для конкретного запуска может переопределить брендбук. Такое отклонение должно иметь `owner_override_id`. Если брендбук недоступен и переопределения нет, останови только генеративный этап с доказательством; не выбирай молча `editorial`, тёмно-красную, серую или любую другую встроенную тему.
