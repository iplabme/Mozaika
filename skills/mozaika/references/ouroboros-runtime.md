# Ouroboros Runtime Contract

Use this reference to map autonomous intent onto existing Ouroboros capabilities. Prefer live tool schemas and runtime facts when they differ from this summary.

## Conversation and tasks

- Keep simple answers in chat.
- Use `promote_chat_to_task` for tool-using or multi-step work so the owner receives one live task card.
- Use `steer_task` only when a new message clearly targets a running task.
- Use `route_to_project` when a message clearly continues an existing project.
- Use `ensure_project_scope` when work already in progress must become a named project.
- Keep one owner-visible outcome per message; do not answer and spawn duplicate work for the same deliverable.

## Planning and evidence

- Use `plan_task` before non-trivial design, build, edit, or self-modification work.
- Use `read_file`, `list_files`, `search_code`, and `query_code` for authoritative repository evidence.
- Use `run_command`, `run_script`, and services only when their effect is necessary and within the active capability envelope.
- Send every tool invocation through the native structured tool-call field. Never expose XML-like `<tool_call>`, `<arg_key>`, or `<arg_value>` wrappers in progress or final text. If a provider returns textual pseudo-tool markup, do not execute or repeat it; allow the runtime recovery guard to retry once and otherwise report a compact failure.
- Write Russian and other non-ASCII text as literal UTF-8. Do not manually assemble `\uXXXX` sequences or decode content with `unicode_escape`. Keep large structured payloads in campaign files and pass file references through the selected reviewed skill instead of embedding a regenerated program in chat.
- Use `verify_and_record` before declaring a real artifact or deliverable complete.
- Use `task_acceptance_review` for independent outcome critique, then record whether its advice was accepted, rejected, partial, or deferred when the surface supports it.

## Projects and continuity

- Treat a project as a focused room of one Ouroboros identity, not a separate agent.
- Use project journal milestones for `start`, `checkpoint`, `blocked`, `done`, and important notes.
- Keep active project state in workpad and reusable project facts in scoped knowledge.
- Respect the one-writer-per-project lease. Parallelize between projects or through a task's bounded subagent swarm.
- Use `recent_tasks` to recover prior execution evidence that is not present in the current turn.

## Delegation

- Use `schedule_subagent` for focused independent work, not to postpone parent judgment.
- Always provide a concrete `objective` and `expected_output`.
- Use read-only children for investigation and adversarial checks.
- Request a declared `write_surface` only when an acting child is necessary and the live runtime permits it.
- For integrating children, publish ownership, interfaces, formats, integration order, and open questions with `tree_note` before fan-out.
- Read results with `get_task_result`, `wait_task`, or `wait_tasks`; never assume completion.
- Integrate or reject acting-child patches in the parent. Children do not commit or run review gates.

## Memory and reflection

- Use `update_identity`, `update_scratchpad`, and `knowledge_write`; do not edit protected cognitive files with generic file tools.
- Read current memory before writing.
- Preserve reusable process lessons, not task trivia.
- Treat the improvement backlog as durable advice, not an executable queue.
- Preserve provenance: distinguish observed, inferred, stale, and missing facts.

## Skills: discovery, selection and execution

- Ouroboros discovers `SKILL.md` or `skill.json` under `data/skills/*/<folder>`
  and an optional external checkout, at most one grouping level deep. Runtime,
  state and tool identity are derived from the sanitized directory basename;
  frontmatter `name` is display metadata. Duplicate directory identities fail
  closed with a collision error.
- `SKILL.md` wins over `skill.json` when both exist. Missing frontmatter creates
  a body-only `instruction` skill; missing `type` also defaults to
  `instruction`. Valid types are `instruction`, `script` and `extension`.
- The normal agent context receives only metadata for enabled, freshly reviewed
  skills: name, type, version, description, `when_to_use` and registered tool
  surfaces. The `SKILL.md` body is untrusted payload and is not injected. A role
  that selects an instruction skill must explicitly read the full file before
  applying it.
- `instruction` skills are catalogued and reviewable but never run through
  `skill_exec`. A `script` must declare an allowlisted runtime and every runnable
  file in `scripts`; undeclared files cannot execute. An `extension` declares
  `plugin.py` (or another confined entry) and registers namespaced tools, routes,
  WebSocket handlers and widgets through `PluginAPI`.
- Every runtime-reachable text file in a skill payload is hashed and reviewed.
  An edit makes the previous verdict stale. Sensitive-shaped files, unreadable
  files, escaping symlinks and opaque binary payloads fail closed. Preflight
  checks manifest, entry/script paths, Python/Node/Bash syntax, permissions and
  widget schemas before the tri-model review.
- Lifecycle is `install → preflight → review → dependencies → grants → enable →
  execute/load`. Review and enable state lives under
  `data/state/skills/<directory-identity>`. External skills are disabled by
  default; owner attestation can skip only the expensive LLM phase for eligible
  owner-trusted payloads and never skips deterministic preflight.
- `skill_exec` rechecks enabled state, fresh content hash, executable review,
  isolated dependencies, owner grants, runtime availability, declared script
  path and a second TOCTOU hash immediately before spawn. It runs with
  `cwd=skill_dir`, scrubbed environment, bounded output and timeout, and exposes
  `OUROBOROS_SKILL_NAME` plus `OUROBOROS_SKILL_STATE_DIR`.
- Mozaika therefore treats short Anthropic instruction skills as first-class
  methods, records the exact sections applied, and keeps a separate execution
  receipt for the engine that actually reads data, executes SQL or renders HTML.

## Background consciousness

Background consciousness may inspect, reflect, maintain memory, groom knowledge, and message the owner sparingly. It may not run shell/code, schedule children, commit, perform review, toggle evolution, or execute structural work. Convert executable ideas into a visible foreground task or evolution candidate.

## Outcome protocol

Track the three independent axes used by Ouroboros: objective outcome, process quality, and system health. The owner-facing task outcome must remain one of:

- `solved`
- `best_effort`
- `blocked_with_evidence`

Do not hide partial completion behind optimistic prose.
