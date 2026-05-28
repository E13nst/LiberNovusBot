# stdlib
import hashlib
import json
import time

# project
from services.llm_providers.base import LLMProvider, ProviderRawResponse, ProviderResponseMeta

_MOCK_PROVIDER = "mock"
_MOCK_MODEL = "mock-v1"
_ARCHETYPES = ("Shadow", "Anima", "Self", "Trickster", "Hero")


class MockLLMProvider(LLMProvider):
    """Deterministic mock provider; no external AI calls."""

    provider_name = _MOCK_PROVIDER
    model_name = _MOCK_MODEL

    async def generate(self, prompt: str, *, prompt_version: str) -> ProviderRawResponse:
        started_at = time.perf_counter()
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        seed = int(digest[:8], 16)

        archetype_name = _ARCHETYPES[seed % len(_ARCHETYPES)]
        confidence = round(0.5 + (seed % 50) / 100, 2)
        theme_a = "transition" if seed % 2 == 0 else "escape"
        theme_b = "constraint" if seed % 3 == 0 else "exploration"

        payload = {
            "archetypes": [
                {
                    "name": archetype_name,
                    "confidence": confidence,
                    "evidence": ["dark spaces", "blocked passage"],
                }
            ],
            "themes": [theme_a, theme_b],
            "psychodynamic_tension": "desire for exploration vs structural constraint",
            "compensatory_function": "movement vs stagnation balance",
            "interpretation": "mock interpretation based on structured input only",
            "questions_for_user": [
                "What feels like a 'blocked passage' in your current life?",
            ],
            "_mock_meta": {
                "prompt_hash": digest[:16],
                "provider": self.provider_name,
                "model": self.model_name,
            },
        }
        return ProviderRawResponse(
            raw_text=self.serialize_raw(payload),
            meta=ProviderResponseMeta(
                provider=self.provider_name,
                model=self.model_name,
                prompt_version=prompt_version,
                latency_ms=int((time.perf_counter() - started_at) * 1000),
            ),
        )

    def serialize_raw(self, payload: dict) -> str:
        return json.dumps(payload, ensure_ascii=False)
