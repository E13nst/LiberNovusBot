# Backend-архитектура

Backend владеет бизнес-логикой, жизненным циклом данных и persistent state. Клиенты и AI-провайдеры не должны напрямую управлять доменными сущностями.

## Доменные сущности

### Dreams

`dreams` хранит исходный текст сновидения.

Правила:

- оригинальный текст сна неизменяем;
- сохраняются timestamps;
- каждый сон связан с сессией;
- производные данные хранятся отдельно от raw text.

### Dream Sessions

`dream_sessions` представляет непрерывный аналитический контекст.

Lifecycle:

- active;
- paused;
- closed.

Правила:

- у пользователя может быть только одна активная сессия;
- сессия сохраняет символическую и эмоциональную непрерывность;
- inactive session автоматически закрывается после 72 часов;
- клиенты не вычисляют session lifecycle самостоятельно.

### Session Summary

`session_summaries` является детерминированным агрегатом сессионного материала.

Текущие поля:

- `dream_count`;
- `key_symbols`;
- `recurring_words`;
- `raw_text_sample`.

Правила:

- summary не использует AI;
- rebuild должен быть идемпотентным;
- output должен быть воспроизводимым;
- summary служит входом для prompt compilation и будущего reasoning layer.

## Session-centric design

Аналитика должна быть session-aware. Изолированный сон можно анализировать только если это явно заданный пользовательский сценарий. По умолчанию смысл рождается из последовательности, повторения и контекста.

## Структура ответственности

```text
routers/
  HTTP contracts, validation, dependency wiring

services/
  domain logic, lifecycle, orchestration

db/
  models, sessions, persistence primitives

schemas/
  typed request/response contracts

tests/
  regression and service-level behavior
```

Роутеры не должны содержать бизнес-логику. Services не должны зависеть от Telegram. Bot и Mini App не должны обращаться к базе напрямую.

## PostgreSQL как source of truth

Нельзя полагаться на Redis, in-memory state, состояние bot framework или frontend storage как на источник истины. Все доменные состояния должны быть восстановимы из PostgreSQL.
