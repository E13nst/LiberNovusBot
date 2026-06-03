# Analysis Pipeline

Analysis Pipeline должен быть многостадийным. Каждая стадия решает отдельную задачу и возвращает структурированный результат, пригодный для валидации и сохранения.

## Sync dialogue vs async memory

| Path | When | Output |
|------|------|--------|
| Dialogue ingress | Each user message (after Policy) | `DialogueTurnV1` → user sees `assistant_message` |
| Background memory | After `ROUTE_NEW_DREAM` (and optional re-enrich) | `StructuredDreamMemoryV1` in `dream_memories` |

The user must not wait for the full multi-stage pipeline to receive a companion reply. Stages run in the background worker unless explicitly invoked for debug.

## Целевая последовательность

```text
Compiled Prompt
       ↓
Motif Extraction
       ↓
Emotional Field Analysis
       ↓
Archetypal Hypothesis Generation
       ↓
Compensation Analysis
       ↓
Question Generation
       ↓
StructuredDreamAnalysis
```

## Стадии

### Motif Extraction

Выделяет повторяющиеся образы, действия, места, персонажей и символические мотивы. Стадия не должна делать финальные выводы.

### Emotional Field Analysis

Описывает эмоциональную тональность материала: напряжение, страх, стыд, интерес, притяжение, избегание, неопределенность. Результат остается гипотезой, а не диагнозом.

### Archetypal Hypothesis Generation

Формирует осторожные архетипические гипотезы. Нельзя превращать архетип в ярлык пользователя или утверждать, что образ "точно означает" конкретную фигуру.

### Compensation Analysis

Проверяет, может ли сон компенсировать односторонность сознательной позиции. Эта стадия должна использовать язык возможностей: "может указывать", "может быть связано", "возможно отражает".

### Question Generation

Генерирует открытые вопросы для самостоятельного размышления. Вопросы важнее окончательных ответов.

## Structured analysis object

Каноническая форма должна быть serializable и provider-independent:

```python
class StructuredDreamAnalysis:
    motifs: list[str]
    emotional_patterns: list[str]
    archetypal_hypotheses: list[str]
    tensions: list[str]
    exploratory_questions: list[str]
```

## Stage isolation

Каждая стадия должна иметь:

- явный input contract;
- явный output schema;
- validation;
- тесты;
- возможность аудита.

Если стадия получает невалидный input, она должна завершиться контролируемой ошибкой, а не достраивать контекст фантазией.
