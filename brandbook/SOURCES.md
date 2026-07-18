# Источники визуальных референсов

Снимки сделаны 2026-07-14 с официальных публичных страниц Anthropic. Они сохраняют композиционные принципы для внутреннего применения Mozaika; это не копия официального бренд-гайда и не разрешение использовать фирменные активы.

## Дэшборд

- Официальный источник: [Anthropic Economic Index](https://www.anthropic.com/economic-index)
- Локальный снимок: [references/anthropic-economic-index-dashboard.png](references/anthropic-economic-index-dashboard.png)
- Заимствуемые принципы: тёплый светлый холст, постоянная секционная навигация, KPI рядом с бенчмарком, прямой рейтинг и крупный treemap с мягкой категориальной палитрой.

## Карточки и модульный отчётный хаб

- Официальный источник: [Anthropic Transparency Hub](https://www.anthropic.com/transparency)
- Локальный снимок: [references/anthropic-transparency-hub-cards.png](references/anthropic-transparency-hub-cards.png)
- Заимствуемые принципы: крупный заголовок, три пронумерованных модуля, открытые колонки, редакционный ритм, минимальная декоративность.

## Длинный исследовательский отчёт

- Официальный источник: [Anthropic Economic Index report, June 2026](https://www.anthropic.com/research/economic-index-june-2026-report)
- Локальный снимок: [references/anthropic-economic-index-report.png](references/anthropic-economic-index-report.png)
- Заимствуемые принципы: короткая категория, крупный вывод, дата и действие, большие спокойные цветовые поля, ясная последовательность чтения.

## Карточки-подсказки спикера

- Источник владельца: `LLM_Story_Cards_2026_FINAL.html`, предоставлен в задаче 2026-07-16.
- Очищенный локальный шаблон: [templates/speaker-story-cards.template.html](templates/speaker-story-cards.template.html).
- Заимствуемые принципы: портретная колода, обложка, последовательные карточки, акцентная линия, сильная типографическая иерархия, ключевой факт, стрелки, точки, клавиатура, свайп и мягкая смена карточек.
- Адаптация Mozaika: конкретные LLM-данные и редакторский код удалены; внешние Google Fonts исключены; палитра заменена точными токенами Mozaika; содержимое преобразовано из мини-презентации в подсказки спикеру, связанные со слайдами итоговой презентации.

## Второй сценарий: еженедельный автопилот

- Источник владельца: `e17881152_dashboard.html`, предоставлен 2026-07-17.
- Производный шаблон: [templates/scenario-2-dashboard.template.html](templates/scenario-2-dashboard.template.html).
- Заимствуемые принципы: тёплый светлый холст, пастельная категориальная палитра, KPI перед деталями, отдельный блок аномалий, динамика, сравнение сегментов и детальная таблица.
- Адаптация Mozaika: удалён встроенный загрузчик Excel, исключены CDN-зависимости, конкретные данные заменены контрактными placeholder-полями, добавлены поиск, сортировка, фильтр важности, настройка плотности и сброс.

- Источник владельца: `presentation.html`, предоставлен 2026-07-17.
- Производный шаблон: [templates/scenario-2-presentation.template.html](templates/scenario-2-presentation.template.html).
- Заимствуемые принципы: восемь последовательных экранов, один вывод на экран, кульминация на аномалии, доказательная таблица и завершение действиями.
- Адаптация Mozaika: удалена служебная подпись renderer, исключён внешний Chart.js, добавлены автономная навигация, overview, fullscreen, печать, адаптивность и reduced motion.

- PPTX-референс владельца: [references/scenario-2-sprint25-review-reference.pptx](references/scenario-2-sprint25-review-reference.pptx), 8 слайдов, 2 редактируемые диаграммы и 1 таблица.
- Исходный Excel использован только для понимания схемы: `Issues`, `Weekly_Summary`, `Anomalies_GT`; конкретные записи не являются частью шаблонов.
- Полный сценарный контракт и контрольные хеши: [references/scenario-2-weekly-autopilot.md](references/scenario-2-weekly-autopilot.md).

## PPTX для сценария поиска инсайтов

- Источник владельца: `14c0d21d8_ds_role_analytics.pptx`, предоставлен
  2026-07-17.
- Неизменённая локальная копия:
  [references/scenario-insight-ds-role-analytics-reference.pptx](references/scenario-insight-ds-role-analytics-reference.pptx).
- Производный визуальный профиль:
  [references/scenario-insight-presentation-style.md](references/scenario-insight-presentation-style.md).
- Заимствуемые принципы: чернильно-синяя и тёплая светлая база, спокойные
  зелёные/синие/горчичные/лавандовые/коралловые акценты, узкие заголовки,
  верхние линии, широкая доказательная зона, узкая колонка интерпретации,
  нативные диаграммы, семантические таблицы и выровненные блоки решений.
- Не заимствуются: данные и формулировки примера, количество и порядок слайдов,
  темы, выводы и конкретная последовательность композиций.

## Применение дизайн-системы

- Официальный источник: [Claude Design in Anthropic Labs](https://www.anthropic.com/news/claude-design-anthropic-labs)
- Используемый принцип: код и дизайн-файлы могут служить общей дизайн-системой, которую агент последовательно применяет к новым артефактам. В Mozaika эту роль выполняют `BRANDBOOK.md`, `manifest.json`, `tokens.css` и локальные референсы.
