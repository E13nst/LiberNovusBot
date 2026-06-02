CLARIFICATION_RESPONSE_RU = (
    "Похоже, это пока короткий фрагмент. "
    "Если хотите, опишите сон чуть подробнее: образы, эмоции и чем он закончился."
)

SESSION_CONTINUE_RESPONSE_RU = (
    "Принял продолжение. Добавьте, пожалуйста, детали сна, которые сейчас кажутся ключевыми."
)


def build_clarification_response() -> str:
    return CLARIFICATION_RESPONSE_RU


def build_session_continue_response() -> str:
    return SESSION_CONTINUE_RESPONSE_RU

