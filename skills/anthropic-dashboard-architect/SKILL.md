---
name: dashboard-architect
description: >-
  Build premium, self-contained HTML dashboards in the "Enterprise ML Portfolio"
  design language (warm-neutral + Sberbank-style themes, Chart.js, donuts,
  heatmaps, funnels, KPI tiles, anomaly callouts, artifact timelines). Use when
  the user provides data and wants a polished analytical dashboard. The skill
  first INTERVIEWS the user (audience + key questions), then ANALYZES the data
  for anomalies and recommends which analytics to show, then RENDERS a single
  shareable HTML file. Triggers: "сделай дашборд", "build a dashboard",
  "визуализируй эти данные", "portfolio dashboard".
argument-hint: [optional: path to data file or short data description]
---

# Dashboard Architect 🎨📊

Build **premium, single-file HTML dashboards** that look like an enterprise BI product
(reference: ML Portfolio dashboard — warm neutral palette, Sberbank operational sweep,
heatmaps, funnels, "требуют внимания" anomaly cards, artifact timelines).

This is NOT a dumb chart dumper. The agent acts as a **data analyst + designer**:
it interviews the user, hunts for anomalies, and decides what's worth showing.

---

## ⚙️ THE WORKFLOW — always follow these 3 phases in order

### PHASE 1 — INTERVIEW (do this BEFORE building anything)
Ask the user these questions in ONE concise message (don't interrogate one by one).
If the answer is obvious from context, assume it and state your assumption instead of asking.

Ask:
1. **Для кого дашборд?** (audience) — exec / руководитель, аналитик, команда, клиент?
   → drives density, jargon level, and how much drill-down detail to include.
2. **На какие 3–5 ключевых вопросов он должен отвечать?**
   → e.g. "Где у нас узкие места по T2V?", "Какие модели в риске?", "Выполняем ли цель?"
   → these questions become the SECTIONS of the dashboard.
3. **Период / срез данных?** (если не ясно из данных)
4. **Есть ли цели / таргеты** для метрик? (нужно, чтобы рисовать "факт vs цель" бары)

Audience → layout heuristic:
- **Executive** → big KPI tiles up top, donuts, 1 hero chart, "требуют внимания" card, minimal tables.
- **Analyst** → dense tables, heatmaps, distributions, funnels, raw drill-down.
- **Team/ops** → status breakdowns, per-team leaderboards, queues, "что делать сейчас".
- **Client** → clean, fewer numbers, strong narrative titles, lots of whitespace.

### PHASE 2 — ANALYZE (find the story, don't just plot)
Before rendering, run a quick analysis pass over the data and surface:
- **Anomalies / outliers**: values far from median (>1.5×IQR), sudden drops/spikes, items breaching targets.
- **Trends**: is the key metric improving or degrading over time? By how much vs prior period?
- **Concentration**: Pareto — do a few categories dominate? (e.g. 38% Credit Scoring)
- **Bottlenecks**: in any funnel/pipeline, where is the biggest drop-off?
- **Target gaps**: which metrics miss their goal, and by how much.

Then DECIDE what to show. Recommend chart types using this map:
| Question type | Best visual |
|---|---|
| Состав / часть-целое | Donut (≤6 slices) or 100% stacked bar |
| Тренд по времени | Line + median dashed line |
| Сравнение категорий | Horizontal bars, sorted by value |
| Ранжирование / топ-N | Horizontal bar leaderboard |
| Воронка / pipeline | Funnel (stacked horizontal bars, descending) |
| 2 измерения × значение | Heatmap (color = intensity) |
| Факт vs цель | Bullet bar (bar + target tick) |
| Аномалии / алерты | "Требуют внимания" cards with severity badges |
| Один важный KPI | Big number tile + sparkline + delta badge |

**Surface the anomalies as "ТРЕБУЮТ ВНИМАНИЯ" cards** — this is the signature element.
Each card: icon + headline (e.g. "87 моделей с отклонениями +12 за квартал") + sub-line +
severity badge (Срочно / Важно / Gap / Рекомендация / Выполнено).

Tell the user, in chat, the 2–3 most important findings you discovered BEFORE/with the dashboard.
The dashboard should answer the questions from Phase 1 — verify each one is addressed.

### PHASE 3 — RENDER (one self-contained .html file)
- Use `scripts/template.html` as the structural starting point.
- Inline ALL CSS + JS. Chart.js via CDN (`https://cdn.jsdelivr.net/npm/chart.js@4.4.0`).
- Write to a file, then `upload_file` and give the user the link.
- Verify it opens / structure is valid before declaring done.

---

## 🎨 DESIGN SYSTEM (match the reference exactly)

Two theme variants — pick based on audience/brand (ask if unsure):

### Theme A — "Warm Neutral" (executive summary, page 1 of ref)
```
--bg:        #ECE7DC;   /* warm sand canvas */
--panel:     #FBF9F4;   /* cream panels */
--panel-2:   #F4F1E8;   /* inset panels */
--border:    #C9A86A;   /* gold panel border (2px) */
--ink:       #4A4A42;   /* warm dark text */
--muted:     #9A9486;   /* muted labels */
--accent:    #8FB48A;   /* sage green (primary series) */
--accent-2:  #D9C28A;   /* warm gold (secondary series) */
--good:      #7FA874;   --warn: #E0B450;   --bad: #D08770;
```
Panels: `border-radius:14px; border:2px solid var(--border); background:var(--panel);`
Section titles: UPPERCASE, 11px, letter-spacing .5px, color var(--muted).

### Theme B — "Operational / Sberbank" (pages 2–3 of ref)
```
--bg:        #EEF1F4;   /* cool light grey */
--panel:     #FFFFFF;
--border:    #E3E8EE;   /* hairline border (1px) */
--ink:       #1F2A37;   /* near-navy text */
--muted:     #7B8794;
--accent:    #2E7D5B;   /* Sber green */
--accent-2:  #3B82C4;   /* blue */
--good:      #2E9E6B;   --warn: #E0A82E;   --bad: #E5484D;
--severity-urgent:#FCE8E8; --severity-important:#FFF6E5; --severity-gap:#EEF2F7; --severity-ok:#E8F6EE;
```
Panels: `border-radius:16px; border:1px solid var(--border); box-shadow:0 1px 3px rgba(0,0,0,.04);`

### Shared component patterns (see template.html)
- **KPI tile**: big number (32–40px, 800), label above (uppercase 11px muted), delta badge (▲ +8% green / ▼ red), optional sparkline canvas below.
- **Donut**: Chart.js doughnut, `cutout:'72%'`, center label absolutely positioned, ONE color family — not rainbow.
- **Bar leaderboard**: horizontal bars sorted desc, value label at end, single accent color.
- **Funnel**: descending horizontal bars, % retained labels, "ключевая потеря" callout.
- **Heatmap**: CSS grid of cells, background opacity ∝ value, number centered, legend.
- **Bullet / факт-vs-цель**: thin track + filled bar + target tick (▏) + "Факт X% / Цель Y%".
- **Attention card**: left icon, headline + subline, right severity pill.
- **Section title bar**: small uppercase heading, optional right-aligned filter pill.

### Color discipline (critical — this is what makes it look pro)
- ONE data series = ONE color. Never per-bar rainbow.
- Color carries meaning only: green=good/on-target, amber=warning, red=critical/breach.
- Neutral surfaces dominate; accent used sparingly for the focal metric.
- Numbers stay in --ink; labels in --muted. Don't tint every row differently.

---

## 📐 LAYOUT RECIPES by dashboard type
- **Portfolio / Summary** (page 1–2): 3-column grid. Left = status breakdowns + significance bars.
  Middle = KPI tiles + hero trend + funnel. Right = donuts (среды реализации) + attention cards + automation gauges.
- **Operational deep-dive** (page 3): full-width metrics table (blocks × KPIs, conditional-colored cells)
  + heatmap (модели × блоки × статус) + "AutoML vs ручная" comparison tiles + attention list.
- **Initiative explorer** (page 4): left filter sidebar + selectable initiative cards; right = detail with
  model rows (status/significance badges), tabs (Модели / Сквозная цепочка / Признаки).
- **Artifact timeline** (page 5): vertical timeline, icon nodes, grouped fact rows (Инициатива→КЭ→Модели→Версии→Jira→Среды).

---

## ✅ QUALITY CHECKLIST before sending
- [ ] Every Phase-1 question is visibly answered by a section.
- [ ] Anomalies surfaced as attention cards with correct severity colors.
- [ ] One color per series; semantic colors only; no rainbow bars.
- [ ] Real numbers from user data (never leave lorem placeholders).
- [ ] Title states the insight + subtitle has period/source.
- [ ] Responsive-ish (grid collapses), no horizontal scroll on desktop.
- [ ] File uploaded, link shared, key findings summarized in chat.

## Notes
- If the user gives no data yet, build with their numbers once provided; don't invent fake data silently — if you must demo, label it "пример".
- Pair with sibling skills: `statistical-analysis` (rigorous outlier/trend math), `data-validation` (QA before sharing), `sql-queries` (if data is in a warehouse).
