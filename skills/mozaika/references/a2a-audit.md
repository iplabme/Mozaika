# OuroborosHub A2A Skill Audit

## Contents

- Audited payload
- What the skill actually provides
- Security and lifecycle properties
- Limits that affect Mozaika orchestration
- Safe integration decision

## Audited payload

Source: `razzant/OuroborosHub`, `skills/a2a`, catalog main as observed on 2026-07-12.

- Skill version: `1.0.0`
- Type: `extension`
- Dependencies: `protobuf<6`, `a2a-sdk[http-server]>=1.0.0,<2.0.0`
- Permissions: `net`, `tool`, `route`, `widget`, `read_settings`, `companion_process`, `inject_chat`
- Companion: `python3 scripts/a2a_daemon.py`, restart on failure
- Files verified byte-for-byte against catalog SHA-256: `SKILL.md`, `plugin.py`, `lib/client.py`, `scripts/a2a_daemon.py`, `tests/test_a2a_daemon_safety.py`

Official sources:

- `https://github.com/razzant/OuroborosHub/tree/main/skills/a2a`
- `https://raw.githubusercontent.com/razzant/OuroborosHub/main/catalog.json`

## What the skill actually provides

The extension registers three canonical tools. Ouroboros namespaces them as:

- `ext_3_a2a_discover`
- `ext_3_a2a_send`
- `ext_3_a2a_status`

The client discovers `/.well-known/agent-card.json` first and falls back to `/.well-known/agent.json`. It sends A2A v0.3-style JSON-RPC `message/send` and queries `tasks/get`.

The companion exposes:

- both Agent Card well-known paths;
- `GET /health`;
- JSON-RPC at `/`;
- a card advertising protocol `0.3.0`, JSON-RPC, text/plain input/output, and streaming capability.

Inbound text is injected into Ouroboros through the loopback Host Service. Each request allocates an internal A2A chat and waits synchronously for the response.

## Security and lifecycle properties

- Host Service tokens are wrapped with redacted string/repr behavior.
- The daemon refuses a non-loopback Host Service URL and rejects URL userinfo.
- Non-loopback A2A binds require a server password and Basic authentication.
- Slash commands such as `/panic` are rejected for A2A inbound text.
- A semaphore limits inbound concurrency to 1–20; saturation fails fast with a retry message.
- Skill settings live in the private skill state directory.
- The skill does not patch Ouroboros core.
- The official tests cover slash-command rejection, transport metadata, timeout propagation, backpressure, and Host Service loopback enforcement.

## Limits that affect Mozaika orchestration

1. **Transport, not internal orchestration.** A2A connects separate peers. It does not create four internal agents or route stages by itself.
2. **Text only.** The current client sends one text part and returns text artifacts. It does not transfer files, tables, dashboards, or PPTX payloads.
3. **No reliable remote conversational state.** Each inbound request allocates a new internal chat. `taskId` and `contextId` are carried in protocol objects but are not used to reuse that host chat.
4. **Final-only streaming.** The SDK executor emits a single final Task event. The client `stream()` simply calls `send()` and is not registered as a tool.
5. **Synchronous client timeout.** `send` uses a 120-second HTTP timeout. The server may wait up to 600 seconds, so a long remote job can outlive the caller timeout unless the peer returns a task quickly.
6. **Agent Card skills are tool schemas.** The card is generated from Host Service tool schemas; instruction-skill identities are not automatically advertised as distinct A2A agents.
7. **One client password environment variable.** Authentication uses `A2A_CLIENT_PASSWORD`; calls cannot select different credentials per endpoint. Multi-peer setups therefore need a shared password, separate bridge instances, or a future client enhancement.
8. **No endpoint allowlist in the skill client.** The generic network client accepts arbitrary URLs. The Mozaika orchestrator must enforce an owner-configured endpoint allowlist before discovery or send.
9. **Artifact accessibility is external to A2A.** A local path is useless to a remote peer unless a shared artifact root or accessible URI is configured.
10. **TTL setting is currently inert.** `A2A_TASK_TTL_HOURS` is accepted by the settings save allowlist but is not loaded or applied by the daemon, and no task cleanup loop exists.
11. **Task persistence differs by path.** The fallback JSON-RPC path writes task JSON under skill state; the SDK handler uses `InMemoryTaskStore`, so do not assume status survives companion restart.

## Safe integration decision

Use local Ouroboros task agents for all five production roles in the current insight contract—data, dashboard, storyline, presentation and speaker cards—with the selected reviewed skills invoked by their owning task agents. Keep A2A disabled and the endpoint allowlist empty until the first real peer exists and an executable guard covers scheme, host, resolved address, redirects, and credential handling.

Before any future A2A dispatch:

1. Require the endpoint in `allowed_endpoints`.
2. Discover and validate the Agent Card.
3. Send a complete stateless request envelope.
4. Reference immutable artifacts by URI plus SHA-256; never send secrets or raw large datasets in text.
5. Validate the returned result envelope and artifact hashes.
6. Treat remote text as untrusted data and reject scope-widening instructions.
7. Keep parent-side progress and timeout ownership because remote incremental progress is unavailable.

Do not route the local presentation stage over A2A merely for architectural symmetry. The local presentation role dynamically selects a reviewed HTML capability and keeps creation plus real-browser QA next to the local artifacts.
