# stdlib
import re
from dataclasses import dataclass

# project
from services.prompts.contracts import DEFAULT_PROMPT_CONTRACT, PromptContract

_FIELD_LINE = re.compile(r"^([a-z_]+): (.+)$")
_DREAM_MARKER = re.compile(r"^\[DREAM (\d+)\]$")


@dataclass(frozen=True)
class StructuralValidationError:
    code: str
    detail: str


def _extract_section_body(prompt: str, heading: str, next_heading: str | None) -> str:
    start = prompt.index(heading) + len(heading)
    if next_heading is None:
        return prompt[start:].lstrip("\n")
    end = prompt.index(next_heading, start)
    return prompt[start:end].strip("\n")


def _parse_field_lines(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in body.splitlines():
        match = _FIELD_LINE.match(line)
        if match:
            fields[match.group(1)] = match.group(2)
    return fields


def _validate_section_order(prompt: str, contract: PromptContract) -> StructuralValidationError | None:
    positions = [prompt.index(section.heading) for section in contract.sections]
    if positions != sorted(positions):
        return StructuralValidationError("section_order", "Sections are out of contract order")
    return None


def _validate_context_section(
    body: str,
    section_fields: tuple,
) -> StructuralValidationError | None:
    fields = _parse_field_lines(body)
    for spec in section_fields:
        if spec.required and spec.name not in fields:
            return StructuralValidationError(
                "missing_context_field",
                f"Missing required field: {spec.name}",
            )
    expected_order = [spec.name for spec in section_fields]
    actual_order = []
    for line in body.splitlines():
        match = _FIELD_LINE.match(line)
        if match:
            actual_order.append(match.group(1))
    if actual_order != expected_order:
        return StructuralValidationError(
            "context_field_order",
            f"Expected fields {expected_order}, got {actual_order}",
        )
    return None


def _validate_dream_section(body: str, dream_count: int) -> StructuralValidationError | None:
    if dream_count == 0:
        if body != "(no dreams provided)":
            return StructuralValidationError("dream_log_empty", "Expected empty-dream placeholder")
        return None

    blocks = [block.strip() for block in body.split("\n\n") if block.strip()]
    for index, block in enumerate(blocks, start=1):
        lines = block.splitlines()
        if len(lines) != 3:
            return StructuralValidationError("dream_entry_shape", f"Dream {index} must have 3 lines")
        marker_match = _DREAM_MARKER.match(lines[0])
        if marker_match is None or int(marker_match.group(1)) != index:
            return StructuralValidationError(
                "dream_entry_index",
                f"Expected [DREAM {index}], got {lines[0]!r}",
            )
        if not lines[1].startswith("text: "):
            return StructuralValidationError("dream_entry_text", f"Dream {index} missing text: line")
        if not lines[2].startswith("timestamp: "):
            return StructuralValidationError(
                "dream_entry_timestamp",
                f"Dream {index} missing timestamp: line",
            )
    return None


def _validate_summary_section(
    body: str,
    section_fields: tuple,
) -> StructuralValidationError | None:
    fields = _parse_field_lines(body)
    for spec in section_fields:
        if spec.required and spec.name not in fields:
            return StructuralValidationError(
                "missing_summary_field",
                f"Missing required field: {spec.name}",
            )
    expected_order = [spec.name for spec in section_fields]
    actual_order = []
    for line in body.splitlines():
        match = _FIELD_LINE.match(line)
        if match:
            actual_order.append(match.group(1))
    if actual_order != expected_order:
        return StructuralValidationError(
            "summary_field_order",
            f"Expected fields {expected_order}, got {actual_order}",
        )
    return None


def _validate_fixed_section(
    body: str,
    required_lines: tuple[str, ...],
    code: str,
) -> StructuralValidationError | None:
    for line in required_lines:
        if line not in body:
            return StructuralValidationError(code, f"Missing required line: {line!r}")
    return None


def _lexical_safety_on_controlled_text(text: str, contract: PromptContract) -> bool:
    normalized = text.lower()
    if not any(anchor in normalized for anchor in contract.required_instruction_anchors):
        return False
    for phrase in contract.forbidden_phrases:
        if phrase in normalized:
            return False
    if contract.placeholder_pattern.search(text):
        return False
    return True


def validate_prompt_structure(
    prompt: str,
    contract: PromptContract = DEFAULT_PROMPT_CONTRACT,
) -> list[StructuralValidationError]:
    """Return structural violations; empty list means the prompt matches the contract."""
    errors: list[StructuralValidationError] = []

    if not prompt.startswith(contract.prefix):
        errors.append(StructuralValidationError("prefix", "Missing or invalid prompt prefix"))
        return errors

    for heading in contract.sections:
        if heading.heading not in prompt:
            errors.append(
                StructuralValidationError("missing_section", f"Missing section: {heading.heading}")
            )
            return errors

    order_error = _validate_section_order(prompt, contract)
    if order_error is not None:
        errors.append(order_error)
        return errors

    section_headings = [section.heading for section in contract.sections]
    bodies: list[str] = []
    for index, section in enumerate(contract.sections):
        next_heading = section_headings[index + 1] if index + 1 < len(section_headings) else None
        bodies.append(_extract_section_body(prompt, section.heading, next_heading))

    context_error = _validate_context_section(bodies[0], contract.sections[0].fields)
    if context_error is not None:
        errors.append(context_error)

    context_fields = _parse_field_lines(bodies[0])
    dream_count = int(context_fields.get("dream_count", "0"))
    dream_error = _validate_dream_section(bodies[1], dream_count)
    if dream_error is not None:
        errors.append(dream_error)

    summary_error = _validate_summary_section(bodies[2], contract.sections[2].fields)
    if summary_error is not None:
        errors.append(summary_error)

    instructions_error = _validate_fixed_section(
        bodies[3],
        contract.required_instruction_lines,
        "instructions",
    )
    if instructions_error is not None:
        errors.append(instructions_error)

    framework_error = _validate_fixed_section(
        bodies[4],
        contract.required_framework_items,
        "framework",
    )
    if framework_error is not None:
        errors.append(framework_error)

    output_format_error = _validate_fixed_section(
        bodies[5],
        contract.required_output_format_lines,
        "output_format",
    )
    if output_format_error is not None:
        errors.append(output_format_error)

    return errors


def validate_prompt_safety(
    prompt: str,
    contract: PromptContract = DEFAULT_PROMPT_CONTRACT,
) -> bool:
    """Structural + lexical validation; both must pass."""
    if validate_prompt_structure(prompt, contract):
        return False

    dream_start = prompt.index(contract.sections[1].heading)
    dream_end = prompt.index(contract.sections[2].heading)
    controlled = prompt[:dream_start] + prompt[dream_end:]
    if not _lexical_safety_on_controlled_text(controlled, contract):
        return False

    return True
