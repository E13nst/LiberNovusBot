# project
import settings
from services.llm_providers.openai_compatible_provider import OpenAICompatibleLLMProvider


class OpenAILLMProvider(OpenAICompatibleLLMProvider):
    """Reference OpenAI provider built on OpenAI-compatible transport."""

    def __init__(self) -> None:
        super().__init__(
            model_name=settings.DEFAULT_MODEL,
            base_url=settings.OPENAI_BASE_URL,
            api_key=settings.OPENAI_API_KEY,
            provider_name="openai",
        )
