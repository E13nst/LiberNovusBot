# project
from services.analysis.schema.structured_dream_memory_v1 import StructuredDreamMemoryV1


def build_structured_memory_from_provider_payload(payload: dict) -> StructuredDreamMemoryV1:
    """Direct stage-shaped memory validation from provider JSON payload."""
    return StructuredDreamMemoryV1.model_validate(payload)
