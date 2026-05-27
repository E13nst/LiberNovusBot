# AI-архитектура

AI-слой в Liber Novus не является свободным генератором интерпретаций. Он работает поверх подготовленного контекста, проходит через prompt contract и возвращает структурированные данные.

## Основные компоненты

### Prompt Compiler

Prompt Compiler превращает сны, summary и metadata в валидированный prompt.

Правила:

- детерминированный порядок секций;
- явные anti-hallucination anchors;
- отсутствие hidden prompts;
- воспроизводимая сборка;
- тестируемый contract.

### Prompt Contract

Prompt Contract описывает обязательные секции, формат входных данных и ожидаемый формат ответа.

Контракт должен защищать систему от:

- неполного контекста;
- невалидных инструкций;
- provider-specific форматов;
- свободной прозы вместо JSON.

### Prompt Validation

Перед вызовом provider должен быть validation step. Он проверяет наличие обязательных секций, размер контекста, JSON-policy и safety anchors.

### Analysis Orchestrator

Analysis Orchestrator координирует многостадийное рассуждение.

Антипаттерн:

```text
prompt -> GPT -> answer
```

Целевая модель:

```text
compiled prompt
    ↓
isolated reasoning stages
    ↓
validated structured outputs
    ↓
StructuredDreamAnalysis
```

## Provider abstraction

Система не должна зависеть от одного провайдера. Возможные провайдеры:

- OpenAI;
- Anthropic;
- OpenRouter;
- локальные LLM;
- Ollama;
- LM Studio.

Provider-specific SDK, response parsing и retry policy должны быть изолированы внутри provider layer. Бизнес-логика не должна знать формат ответа конкретной модели.

## JSON-first policy

AI-сервисы возвращают machine-readable structure, а не свободный текст:

```json
{
  "motifs": [],
  "emotional_patterns": [],
  "archetypal_hypotheses": [],
  "tensions": [],
  "exploratory_questions": []
}
```

Нельзя парсить психологическую прозу как источник данных. Проза может быть presentation layer, но не canonical output backend logic.

## Anti-hallucination pipeline

- Контекст собирается из PostgreSQL и deterministic summaries.
- Prompt Compiler ограничивает материал и инструкции.
- Prompt Validation блокирует неполные или небезопасные prompts.
- Provider возвращает JSON.
- Response validation проверяет schema.
- Downstream services работают только с validated structured output.
