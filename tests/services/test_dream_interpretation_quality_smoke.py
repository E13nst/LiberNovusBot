# stdlib
import json

# project
from services.analysis_contract import validate_analysis_output
from services.jungian_prompt_builder import build_jungian_prompt
from services.llm_providers.mock_provider import MockLLMProvider
from services.prompt_contract import FIXED_OUTPUT_FORMAT
from tests.services.test_jungian_prompt_builder import _build_prompt


async def test_mock_output_contains_required_interpretation_fields():
    provider = MockLLMProvider()
    payload = await provider.generate("quality smoke prompt", prompt_version="v1")
    validated = validate_analysis_output(json.loads(payload.raw_text))

    assert validated.symbols
    assert validated.jungian_interpretation.archetypes
    assert validated.key_insight


def test_prompt_contract_requires_dream_v1_output_keys():
    output_format = "\n".join(FIXED_OUTPUT_FORMAT)
    assert "Режим анализа сновидения" in output_format
    assert '"symbols"' in output_format
    assert '"key_insight"' in output_format
    assert '"jungian_interpretation"' in output_format


def test_prompt_builder_includes_dream_interpretation_mode():
    prompt = _build_prompt()
    assert "Режим анализа сновидения" in prompt
    assert build_jungian_prompt.__name__
