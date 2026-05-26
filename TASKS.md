## Active

- [ ] #001 Схема таблицы tokens
- [ ] #002 Middleware верификации [depends: #001]

## Done

- [x] #000 Инициализация проекта
- [x] #003 Telegram bot + POST /dreams + persistence + PUBLIC/AUTH split
- [x] #004 Session lifecycle: session_service + dream_intake + dream routing [depends: #003]
- [x] #005 Session inactivity lifecycle: last_activity_at + auto-close after 72h + migration [depends: #004]
- [x] #006 Session Summary Layer [depends: #004]
