# Review and Evolution Contract

Read this reference before changing Ouroboros itself, authoring or repairing a skill, modifying governance/memory architecture, or starting an evolution campaign.

## Repository changes

Use the reviewed self-modification path:

1. Establish explicit success criteria and run `plan_task` with sufficient context.
2. Inspect coupled definitions, callers, contracts, prompts, docs, and tests.
3. Implement the smallest class-level fix.
4. Run focused verification before spending reviewer tokens.
5. Complete the pre-commit self-check from `docs/CHECKLISTS.md`.
6. Run `advisory_review` on the final snapshot.
7. Run `commit_reviewed` immediately without intervening mutation.
8. If blocked, inspect `review_status`, group obligations by root cause, fix the class, re-test, and re-review.
9. Restart only when required, then verify the new body and transaction state.

Never use shell git mutations to bypass the reviewed commit path. Never weaken review, safety, scope floors, protected paths, cognitive horizon, panic, or owner controls to reduce friction.

## Skill authoring and repair

An Ouroboros skill manifest uses `SKILL.md` YAML frontmatter or `skill.json`. Core fields are `name`, `description`, `version`, and `type` (`instruction`, `script`, or `extension`). Declare only permissions the payload uses.

Use this lifecycle:

1. Author user-managed skills under `data/skills/external/<name>/`.
2. For a new skill, write the manifest first.
3. Run `skill_preflight` for deterministic manifest, syntax, entry, permission, and widget checks.
4. Run `skill_review` for the full content-hash-bound reviewer pass.
5. Resolve grants and isolated dependencies.
6. Let the owner enable the reviewed skill, unless an allowed lifecycle action explicitly does so.
7. Re-review after every runtime-reachable payload change because the content hash becomes stale.

Instruction skills contain guidance only. Script skills run declared subprocesses. Extension skills use `PluginAPI` and require stricter permission, namespace, path, token, process, route, event, and widget review.

Owner attestation is owner-only. Never self-attest a skill or call the owner endpoint on Ouroboros's behalf.

## Evolution campaigns

Use evolution only for Ouroboros self-improvement, not ordinary project work. Require `advanced` or `pro` runtime mode and owner-enabled evolution controls. Never self-elevate or self-enable them.

Preserve the campaign transaction lifecycle:

- Record a base branch and head.
- Plan before implementation.
- Produce concrete verification and review evidence.
- Land change only through a reviewed commit.
- Preserve rescue references and recovery hints on interruption.
- Mark a cycle absorbed only when a concrete reviewed result landed.
- Treat repeated no-op or failed objectives as a signal to reassess, pause, or choose a different objective.
- Keep project-scoped work out of global post-task self-evolution.

Post-task reflection may nominate a durable backlog item or promotion request. The supervisor, owner settings, eligibility rules, budget, and campaign state decide whether it becomes an evolution cycle; a worker never directly enqueues or enables evolution.

## Constitutional boundaries

Preserve these non-negotiable properties:

- Agency without destroying continuity, immune integrity, or self-creation.
- Full constitutional and identity context without silent truncation.
- Durable process memory and exact review evidence.
- Class-level fixes over repetitive symptom patches.
- Owner-selected review enforcement with loud, durable advisory overrides.
- Emergency stop that cannot be delayed or circumvented.
- Protected `main`; self-modification occurs on the local evolution branch.
