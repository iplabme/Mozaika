# Execution, model compatibility, and artifact preservation

## Contents

- Runtime profile and DeepSeek-only fallback
- Dynamic reviewed role skills
- Allowed roots and cross-task handoff
- Append-only artifact policy
- Bounded planning and review context

## Runtime profile and DeepSeek-only fallback

Read the effective provider and model from live task/runtime facts before choosing a structured-output protocol. Normalize the provider/model string to lowercase.

- When it does not contain `deepseek`, use the normal Ouroboros/model protocol. Do not pre-emptively downgrade structured output, tool use, planning, or review.
- When it contains `deepseek`, still use the normal protocol first. Apply fallback only after the exact capability error `Thinking mode does not support this tool_choice`.
- On that exact error, retry once without forced `tool_choice`: request one plain JSON text object, parse it, and pass it through `validate_gate` or the relevant local JSON Schema.
- Do not apply this fallback to unrelated HTTP 400 responses, malformed tool arguments, safety refusals, timeouts, or dependency errors.
- Never change the model, disable thinking globally, weaken safety, widen authority, or loop retries. Record that the protocol fallback was used.

Ouroboros core owns context compaction. This skill cannot suppress a core compaction request. The rule above governs model-mediated Mozaika structured artifacts and provides the same safe text-then-validate behavior when the acting task controls the request.

## Dynamic reviewed role skills

Before every stage, read `external-skill-catalog.md`, refresh the live inventory,
filter by the stage contract, and preserve `mozaika-skill-selection/v1`. Consider
the installed owner-provided Anthropic group first, then compare the rest of the
ready external pool. A skill is preferred because it is both suitable and
Anthropic; provenance never excuses a weaker contract, missing QA, unavailable
runtime, or stale review.

Each role result must contain the immutable selection receipt plus execution or
method receipts with fresh review fingerprint, exact entry, and output artifact
ids. Validate arguments and schemas before execution. Do not replace a missing
or failed reviewed skill with an unreviewed one-off script, notebook, or global
package installation. A structural failure triggers contract correction and
then reselection; an unchanged retry is reserved for one plausible transient
failure. If no reviewed skill preserves the contract, report the capability gap
with evidence and request one owner decision for any proposed installation.

Use only the roots exposed by the current task. A project state directory is not a shell working directory. Do not probe blocked paths repeatedly. Dependencies declared by a skill are resolved only through Ouroboros review/install lifecycle into that skill's isolated environment.

## Allowed roots and cross-task handoff

A continuation receives prior work through `handoff-envelope.schema.json`, never by traversing another task's drive. Every cross-task reference must include an accessible durable URI, SHA-256, schema, media type, source task/stage, timestamp, and append-only preservation fields.

At the start of a campaign, copy every uploaded user file from extension job state into the current artifact store without modifying the original. Verify the copy hash against the launch manifest. Use the durable copy for all later handoffs.

When an artifact is unavailable through its declared URI, report a contract failure. Do not search arbitrary runtime paths, use `..`, or reinterpret `user_files` as access to Ouroboros runtime state.

For an owner choice, prefer the live widget path while the foreground task is still active: after both HTML surfaces and the pending checkpoint exist, call `request_owner_choice` with a stable checkpoint-derived `question_id`. The immutable widget answer returns to the same tool call. If it returns `status=waiting`, repeat the exact request under the same id; a late click remains saved and a conflicting payload is rejected. For continuation in another task, discover state in this order: an answered live-choice record for an explicit question id; explicit `run_id` in the authenticated owner message; the only `pending` checkpoint for the current chat/session scope and scenario; otherwise ask one bounded clarifying question. Validate every ref and SHA-256 before applying the response. Persist `selected`, `superseded`, or `dismissed` as a new immutable checkpoint artifact; never mutate the prior JSON. An old pending checkpoint may become stale but is never silently expired or guessed. A failed steering attempt is not evidence that the choice was delivered.

## Append-only artifact policy

Maintain one `mozaika-artifact-index/v1` per run. Register:

- every uploaded user input and fetched source snapshot;
- source inventories and scope ledgers;
- frozen research briefs and requirement-to-claim maps;
- clean datasets, excluded-row sets, profiles, and claim registries;
- dashboard source, rendered owner-visible HTML dashboard and its browser-QA capture, internal owner-choice contract, owner-visible `storytelling-cards.html` and its browser-QA capture, then the immutable single-option `selected-storytelling-card.html` created after the owner chooses;
- pending/selected/superseded/dismissed owner-decision checkpoints and selected-card artifacts;
- storyline, evidence map, slide intents, narrative-integrity audits, and outline;
- rich HTML presentation, current-hash narrative audit, browser QA captures, and renderer receipt;
- internal `speaker-story-cards.json`, final owner-visible `speaker-story-cards.html`, mandatory template reference/hash, speaker-card gate receipt, current-hash narrative/language/design/layout audits, and browser QA captures;
- run note and final verification receipts.

## Чистота пользовательских артефактов

Разделяй доказательную трассировку и видимую публикацию. Во внутренних JSON,
реестрах, handoff и receipts сохраняй ID, `claim_ids`, хеши, версии контрактов,
пути и статусы проверок. В дашборде, storytelling-карточках выбора, финальных карточках спикера, отчёте и
презентации не показывай номера вариантов, внутренние идентификаторы, версии
схем, технические пути, названия стадий, отладочные сообщения и прочую
служебную информацию, если владелец явно не запросил техническое приложение.
Ссылки на источники, даты, периоды, единицы, определения, методологию и полезные
оговорки оставляй: они помогают аудитории понимать и проверять материал.

Never delete, truncate, replace, or reuse the URI of a registered artifact. A revision gets a new `artifact_id`, URI, hash, and optional `predecessor_artifact_id`. Temporary caches and scripts are not user artifacts unless declared as an output, but the Mozaika workflow itself does not delete them.

Before every handoff and completion claim, call `validate_gate(gate="artifacts", ...)`. A private extension job path alone is not a durable campaign artifact.

## Bounded planning and review context

Use `plan_task` with minimal context for data/report campaigns. Give reviewers only:

- the owner objective and success criteria;
- source/scope inventory, not raw datasets;
- relevant contract versions;
- claim table and identified contradictions;
- named changed files or failed checks.

Do not send whole logs, full data, full skill payloads, or prior conversation transcripts to every reviewer. Expand context only when a concrete unresolved risk requires it. A reviewer may challenge a plan or selection, but cannot choose from a stale repository impression; the parent must verify live readiness through `list_skills` first.
