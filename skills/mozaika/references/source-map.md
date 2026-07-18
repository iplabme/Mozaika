# Source Map and Audit Baseline

Use this map when updating the skill for a newer Ouroboros release. Re-read changed contracts instead of assuming this baseline is current.

## Audited baseline

- Repository: `razzant/ouroboros`
- Working branch: `ouroboros`
- Version: `6.63.0`
- Commit: `e180954f150daa5298f30f484bc9985ea6225eac`
- Public `main` observed during the audit: version `6.56.0`, commit `6aeec9eb74eba969da3b88dc5fca1dd12a0f5250`

The working branch contained seventeen commits beyond the public-main merge base and was used as the richer behavior baseline. No checkout or merge was performed during the audit.

## Re-audit by concern

- Constitution and invariants: `BIBLE.md`, `prompts/SYSTEM.md`, `prompts/SAFETY.md`
- User interaction and foreground/background split: `prompts/SYSTEM.md`, `prompts/CONSCIOUSNESS.md`, `server.py`, `ouroboros/context.py`
- Task lifecycle and outcomes: `ouroboros/agent.py`, `ouroboros/loop.py`, `ouroboros/agent_task_pipeline.py`, `ouroboros/outcomes.py`, `ouroboros/task_status.py`
- Planning and task review: `ouroboros/tools/plan_review.py`, `ouroboros/tools/review.py`, `ouroboros/triad_review.py`, `ouroboros/review_substrate.py`
- Commit immune system: `ouroboros/tools/commit_gate.py`, `ouroboros/tools/claude_advisory_review.py`, `ouroboros/review.py`, `docs/CHECKLISTS.md`
- Reflection and learning: `ouroboros/reflection.py`, `ouroboros/memory.py`, `ouroboros/consolidator.py`, `ouroboros/improvement_backlog.py`
- Consciousness and deep review: `ouroboros/consciousness.py`, `ouroboros/deep_self_review.py`, `prompts/CONSCIOUSNESS.md`
- Evolution: `ouroboros/post_task_evolution.py`, `ouroboros/evolution_checkpoints.py`, `supervisor/evolution_lifecycle.py`, `supervisor/queue.py`
- Projects and delegation: `ouroboros/projects_registry.py`, `ouroboros/project_lease.py`, `ouroboros/subagents.py`, `ouroboros/task_tree_ledger.py`, `supervisor/workers.py`
- Tools and capability envelopes: `ouroboros/tools/registry.py`, `ouroboros/tool_capabilities.py`, `ouroboros/tool_policy.py`, `ouroboros/tool_access.py`
- Skills: `docs/CREATING_SKILLS.md`, `ouroboros/contracts/skill_manifest.py`, `ouroboros/skill_loader.py`, `ouroboros/skill_readiness.py`, `ouroboros/skill_review*.py`, `ouroboros/tools/skill_preflight.py`, `ouroboros/tools/skill_exec.py`, `ouroboros/extension_loader.py`
- Project-owned pool state: `ouroboros/projects_registry.py`, `ouroboros/project_facts.py`, `ouroboros/tools/project_journal.py`, and the `workpad_read` / `workpad_write` registrations in `ouroboros/tools/registry.py`
- Skill lifecycle and freshness state: `ouroboros/skill_owner_attestation.py`, `ouroboros/skill_review.py`, `ouroboros/skill_review_passes.py`, `ouroboros/skill_review_runner.py`, `ouroboros/skill_review_status.py`, `ouroboros/skill_readiness.py`
- Runtime architecture and development constraints: `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`

## Drift checks

Before releasing an update, compare:

1. Manifest fields, skill types, permissions, and lifecycle gates.
2. Canonical tool names and capability envelopes.
3. Chat-to-task and project routing behavior.
4. Outcome vocabulary and task acceptance review semantics.
5. Background-consciousness restrictions.
6. Review order, enforcement modes, and protected surfaces.
7. Evolution eligibility, transaction, cleanup, restart, and recovery rules.
8. Memory locations, provenance rules, and backlog semantics.
