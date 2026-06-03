# stdlib
import hashlib
import json
import time

# project
from services.llm_providers.base import LLMProvider, ProviderRawResponse, ProviderResponseMeta

_MOCK_PROVIDER = "mock"
_MOCK_MODEL = "mock-v1"
_ARCHETYPES = ("shadow", "anima", "self", "trickster", "hero")
_SYMBOLS = ("water", "forest", "bridge", "door", "mirror")


class MockLLMProvider(LLMProvider):
    """Deterministic mock provider; no external AI calls."""

    provider_name = _MOCK_PROVIDER
    model_name = _MOCK_MODEL

    async def generate(self, prompt: str, *, prompt_version: str) -> ProviderRawResponse:
        started_at = time.perf_counter()
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        seed = int(digest[:8], 16)

        if "assistant_message" in prompt or prompt_version.startswith("dialogue"):
            dialogue_payload = {
                "assistant_message": (
                    "Спасибо, что поделились. В сне, кажется, есть сильное напряжение между уходом "
                    "и необходимостью оставаться рядом — и это может откликаться как страх потери опоры.\n\n"
                    "Я бы пока не спешил с окончательным смыслом. Важнее заметить, что именно в момент "
                    "«улучшения» или «нормальности» тревога не отпускает.\n\n"
                    "Что для вас сейчас страшнее: что опора снова исчезнет, или что вы не успеете быть рядом?"
                ),
                "focus": ["напряжение ухода", "нестабильная опора"],
                "questions": [
                    "Что вы чувствуете первым, когда состояние вдруг улучшается?",
                ],
                "background_notes": {"pace": "exploratory"},
                "emotional_intensity": round((seed % 70) / 100, 2),
                "safety_flags": [],
            }
            return ProviderRawResponse(
                raw_text=self.serialize_raw(dialogue_payload),
                meta=ProviderResponseMeta(
                    provider=self.provider_name,
                    model=self.model_name,
                    prompt_version=prompt_version,
                    latency_ms=int((time.perf_counter() - started_at) * 1000),
                ),
            )

        archetype = _ARCHETYPES[seed % len(_ARCHETYPES)]
        symbol = _SYMBOLS[seed % len(_SYMBOLS)]
        intensity = round((seed % 50) / 100, 2)

        payload = {
            "summary": "Сон может отражать переход между контролем и подавленными эмоциями.",
            "symbols": [
                {
                    "symbol": symbol,
                    "meaning": f"может указывать на внутреннее состояние, связанное с {symbol}",
                    "emotional_charge": "напряжённая",
                }
            ],
            "emotional_state": {
                "primary": "тревога",
                "secondary": "напряжение",
                "intensity": intensity,
            },
            "jungian_interpretation": {
                "archetypes": [archetype],
                "shadow_elements": ["подавленный страх"],
                "anima_animus_signals": [],
                "individuation_hint": "можно исследовать, что остаётся в тени",
            },
            "narrative_interpretation": (
                "Сон может отражать напряжение между желанием исследовать и страхом потерять контроль."
            ),
            "key_insight": "Важно заметить, что контроль может скрывать уязвимость.",
            "uncertainty_notes": [
                "Какие чувства сильнее всего остались после пробуждения?",
            ],
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
