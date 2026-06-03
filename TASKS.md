## Active

- [ ] #025.1 Prompt Alignment V2 (full Russian contract-owned reflection instructions + validation updates)
- [ ] #017 Async OpenAI Runtime Smoke
- [ ] #001 Схема таблицы tokens
- [ ] #002 Middleware верификации [depends: #001]

## Done

- [x] #030 Prompt System Refactor (file-backed prompt assets + registry/compiler compatibility layer)
- [x] #029 Dialogue Tone And Name Variant Prompt (friendly tone, Russian name variants, short greeting rule)
- [x] #028 Telegram Name Addressing (transient profile in dialogue prompt only; no post-LLM name injection; language_code + temporal context)
- [x] #027 Dialogue-First Memory Refactor (DialogueTurnV1, conversation_turns, Policy routes v2, dream_memories, journal API) [depends: #024, #025]
- [x] #026.1 Admin UI Clarity Pass (readable session cards, policy trace narrative, timeline labels, status badges)
- [x] #026 Admin Debug Console MVP (ADMIN_TOKEN-protected admin API, session timeline projection, policy trace persistence, DB-backed prompt versions, minimal Next.js admin UI)
- [x] #025 Dialogue Policy Integration Layer (ingress policy gate + route-aware runtime execution; stateless non-reflection paths) [depends: #024]
- [x] #024 Dialogue Policy Engine (domain contract + pure deterministic router + unit tests)
- [x] #020a Dream Intake → Job Wiring (atomic dream + analysis_job enqueue per accepted message) [depends: #020]
- [x] #022 Real OpenAI E2E Smoke (synthetic Telegram webhook -> intake -> worker -> real OpenAI -> fake delivery)
- [x] #021 Dream Interpretation Contract Layer (DreamAnalysisV1 canonical model + legacy presentation mapper) [depends: #020]
- [x] #020 Delivery Idempotency Layer (Redis side-effect guard + Telegram delivery hook) [depends: #019]
- [x] #019 Execution Traceability Layer (Job → Result Binding) [depends: #018]
- [x] #018 Runtime Concurrency + Multi-Worker Safety [depends: #013]
- [x] #016 First Real Dream Analysis Smoke (OpenAI opt-in orchestrator path)
- [x] #015 First Real LLM Execution (OpenAI Wiring)
- [x] #014 Config Separation + ENV_MODE + Runtime Safety
- [x] #013 Async Analysis Runtime Layer [depends: #012]
- [x] #011 Real LLM Provider Layer [depends: #010]
- [x] #010 Analysis State Machine + Threads + Continuation [depends: #009]
- [x] #009 Analysis Orchestrator (Mock LLM Layer) [depends: #007]
- [x] #008 Project memory system: progress + ADR + operating process [depends: #007]
- [x] #007 Jungian Prompt Builder Layer [depends: #006]
- [x] #000 Инициализация проекта
- [x] #003 Telegram bot + POST /dreams + persistence + PUBLIC/AUTH split
- [x] #004 Session lifecycle: session_service + dream_intake + dream routing [depends: #003]
- [x] #005 Session inactivity lifecycle: last_activity_at + auto-close after 72h + migration [depends: #004]
- [x] #006 Session Summary Layer [depends: #004]
