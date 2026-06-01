## Active

- [ ] #001 Схема таблицы tokens
- [ ] #002 Middleware верификации [depends: #001]

## Done

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
