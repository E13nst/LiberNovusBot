# ADR-011 Prompt Registry And Assets

## Status

Accepted

## Context

Runtime prompts were split across a root `prompt.txt`, inline constants in
`prompt_contract.py`, dialogue prompt builders, and fixed response modules.
That made prompt ownership hard to audit and left ambiguity about which files
were examples and which files affected production behavior.

The system still needs deterministic prompt compilation, JSON-only output
contracts, provider-agnostic business logic, and file-backed runtime prompts.
ADR-007 keeps DB-backed prompt version integration as a later step.

## Decision

Runtime prompt text is owned by `services/prompts/assets/**`:

- long Russian prompt text lives in Markdown assets;
- strict contracts, section definitions, required anchors, forbidden phrases,
  and compiler logic live in Python under `services/prompts/`;
- `PromptRegistry` maps `PromptId(prompt_type, version, language, name)` to
  explicit Markdown assets;
- compatibility modules (`services.prompt_contract`, `services.prompt_compiler`,
  `services.prompt_validation`) remain as import-safe wrappers while call sites
  migrate.

The root `prompt.txt` is no longer a runtime source. Documentation examples
must live under `docs/examples/` and must be explicitly marked as non-runtime.

## Consequences

- Prompt ownership is inspectable from one package.
- Runtime prompts remain file-backed and deterministic.
- Prompt text can be edited as readable Russian Markdown without weakening
  contract validation.
- Admin DB prompt versions remain out of runtime until a separately tested
  integration step.
