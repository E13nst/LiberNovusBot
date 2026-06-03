# project
from services.analysis.schema.structured_dream_memory_v1 import StructuredDreamMemoryV1
from services.memory.dream_memory_service import dream_analysis_v1_to_memory


def build_structured_memory_from_provider_payload(payload: dict) -> StructuredDreamMemoryV1:
    """Stage-shaped memory builder (v1: single-pass bridge from analysis JSON)."""
    memory = dream_analysis_v1_to_memory(payload)
    return memory.model_validate(memory.model_dump())
