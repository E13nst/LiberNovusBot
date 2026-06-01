# project
from services.config.runtime_config import RuntimeConfig, get_runtime_config
from services.llm_providers.openai_compatible_provider import OpenAICompatibleLLMProvider


class OpenAILLMProvider(OpenAICompatibleLLMProvider):
    """Reference OpenAI provider built on OpenAI-compatible transport."""

    def __init__(self, config: RuntimeConfig | None = None) -> None:
        resolved = config or get_runtime_config()
        super().__init__(
            model_name=resolved.default_model,
            base_url=resolved.openai_base_url,
            api_key=resolved.openai_api_key or "",
            provider_name="openai",
        )
