# Phase 2 prototype plan

## Definition of done

Phase 2 prototype is complete when:

1. Ouroboros loads a reviewed and enabled `mozaika` extension.
2. The Widgets page exposes two double-width mixed-source owner launch cards: routine report and insight deck. Each has a compact file/folder drop zone and a `+` menu for URL or system file/folder selection.
3. Each card keeps an ordered typed list of URL, file, and directory sources, stores bounded uploads with directory-relative paths in private append-only run state, and queues one owner-visible foreground campaign command; no hidden pipeline starts from an HTTP route and no project-name field is required.
4. The campaign resolves four distinct logical stage-agent bindings and validates typed handoffs.
5. Every stage receives the complete ready `reporting-full` pool and a role-specific recommended subset; the parent task owns skill execution because Ouroboros subagents cannot call skill lifecycle/tools.
6. Scenario 1 routes `data → dashboard → presentation` under `fixed_storyline_contract_version`.
7. Scenario 2 routes `data → dashboard → owner choice → storyline → presentation` and preserves storyline-first order.
8. Installed payloads pass deterministic preflight, required full review, grants, enablement, and runtime widget registration.
9. The working Ouroboros system repository remains unchanged.

## Skill allocation

All roles can select any ready skill in `adaptive-full` when justified. Matching
installed `anthropic-*` skills are evaluated and fully read first; another
candidate requires a recorded incompatibility or quality advantage.

| Stage agent | Primary | Recommended helpers |
|---|---|---|
| Data | `analyze-report-data` | `huggingface-datasets`, `duckdb-analytics`, `anthropic-data-validation`, `anthropic-statistical-analysis`, `anthropic-sql-queries`, `anthropic-performance-analytics`, `anthropic-snowflake-semanticview` |
| Dashboard | `build-insight-dashboard` | `antv-g2-dashboard`, `anthropic-dashboard-architect`, `anthropic-interactive-dashboard-builder`, `anthropic-data-visualization`, `anthropic-data-validation` |
| Storyline | `design-executive-storyline` | `executive-storytelling`, `anthropic-data-validation`, `antv-g2-dashboard`, `duckduckgo` |
| Presentation | dynamic HTML renderer | `anthropic-interactive-dashboard-builder`, `anthropic-dashboard-architect`, `antv-g2-dashboard`, `unix_computer_use` |

`duckduckgo` is a current-source helper, not evidence authority. `unix_computer_use` is an owner-observed visual/UI verification fallback, not permission to deliver externally. Snowflake mutations remain `owner_choice`.

## Execution sequence

1. Normalize review documentation and mark stale phase-1 recommendations.
2. Upgrade `mozaika` from instruction-only to a reviewed extension.
3. Add two sandboxed module launch widgets and two namespaced routes; do not expose agent-callable start tools that could recursively spawn duplicate campaigns.
4. Bind all suitable installed skills to the shared pool and role recommendations.
5. Validate manifests, schemas, widget declarations, prompt construction, and script syntax.
6. Install the updated payloads into `data/skills/external`.
7. Run full skill review and dependency reconciliation; enable only executable fresh payloads with required grants.
8. Launch Ouroboros and verify the real Widgets/API surfaces.
9. Verify both live routes with non-mutating validation requests. Leave the first positive campaign launch to the owner through a widget so that no production-looking task is fabricated without real input data.
10. Record runtime evidence, remaining gaps, and the next mature-role iteration.

## Phase 2 runtime evidence

Status: **prototype milestone complete; mature role-engine pass implemented**.

- Ouroboros `6.63.0` is running locally and reports `mozaika` as reviewed, fresh, enabled, and live.
- Live routes: `/api/extensions/mozaika/scenario/routine/start` and `/api/extensions/mozaika/scenario/insight/start`.
- Widget tabs: `Mozaika · Рутинный отчёт` and `Mozaika · Инсайты`.
- Both tabs use sandboxed module entries (`routine-widget.js`, `insight-widget.js`). Version 1.0.0 keeps a compact drag-and-drop zone, the `+` source menu, URL validation, separate system file/folder pickers, a typed mixed-source list, and a prefilled manager-style task selected on first focus. The extension writes the full assignment into append-only `assignment.md`; only a short Russian command plus the file reference and SHA-256 reaches chat.
- Empty requests to both routes are rejected; therefore a scenario cannot start without at least one URL, file, or directory.
- `analyze-report-data`, `build-insight-dashboard`, `design-executive-storyline`, and `build-routine-report` are role instructions with explicit typed outputs and required engine receipts. They retain need-based access to every fresh skill in `reporting-full`.
- Data execution dynamically combines source-specific inventory/engines with the first-priority Anthropic methods for SQL, statistics, validation, visualization and applicable domain analysis. Dashboard evaluates `anthropic-interactive-dashboard-builder` and `anthropic-dashboard-architect`; presentation first evaluates the owner-designated `html-presentation-studio` and uses those Anthropic capabilities for visual support or as a recorded fallback. Storyline uses a dedicated narrative method with Anthropic evidence QA where needed.
- Normal role execution is Node/SQL/instruction based and `allow_ad_hoc_python=false` remains set for every role. Unsupported formats must use another fresh reviewed pool skill or produce a typed capability gap.
- The only Mozaika presentation format is rich, self-contained HTML with storyline-driven screens and browser QA. `anthropic-pptx` is preserved for unrelated explicit PowerPoint tasks but is excluded from Mozaika.
- Final native lifecycle status for `mozaika`, the four role skills, and the five role engines is enabled, clean, fresh, executable, and grants-usable. `mozaika` is live-loaded with both routes, both double-width widget tabs, and `validate_gate` registered.
- The extension exposes no agent-callable scenario-start tool. A widget route only validates bounded input, stores file copies under its private per-launch job directory, and injects one visible command into the owner chat; the foreground Ouroboros task retains planning, review, skill readiness, artifacts, and typed handoff control.
- `/Users/iplab/Ouroboros/repo` was not modified.

## Explicit non-goals for this milestone

- No A2A peer or allowlist guard while A2A remains disabled. The four logical roles remain independently configurable and already carry A2A-ready input/output contracts.
- No hidden scheduler or parallel memory system.
- No fabricated production data, dashboard, storyline, or presentation.
- No claim that logical stage agents are independent processes; current Ouroboros capability envelopes keep skill execution in the parent foreground task.
