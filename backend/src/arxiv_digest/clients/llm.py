"""LLM client: structured completions via the Claude Code SDK or LiteLLM.

Backend selection (``settings.llm_backend``):
- ``claude_code`` — the Claude Code SDK (``claude-agent-sdk``), using the local CLI
  subscription auth (no API key).
- ``litellm`` — LiteLLM with an API key; provider-swappable by changing the model
  string.
- ``auto`` — prefer the Claude Code SDK, fall back to LiteLLM.

Heavy backend libraries are imported lazily inside their functions so that callers
that never classify (e.g. ingestion-only runs) don't pay their import cost.
"""

import asyncio
import importlib.util
import logging
import shutil
from typing import TypeVar

from pydantic import BaseModel

from arxiv_digest.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_MAX_OUTPUT_TOKENS = 1024


class LLMError(RuntimeError):
    """Raised when no usable LLM backend is available or a completion fails."""


def _json_instruction(schema: type[BaseModel]) -> str:
    """Instruction for backends without native structured output (Claude Code SDK)."""
    import json

    return (
        "Respond with ONLY a JSON object matching this schema — no markdown, no prose:\n"
        + json.dumps(schema.model_json_schema())
    )


def _parse_json(text: str, schema: type[T]) -> T:
    """Extract and validate the JSON object embedded in model output."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        msg = f"no JSON object found in model output: {text!r}"
        raise LLMError(msg)
    return schema.model_validate_json(text[start : end + 1])


def _claude_code_available() -> bool:
    """True if the Claude Code SDK is importable and its CLI is on PATH."""
    if importlib.util.find_spec("claude_agent_sdk") is None:
        return False
    return shutil.which("claude") is not None


def backend_available() -> bool:
    """True if some LLM backend is usable, given the configured ``llm_backend``."""
    has_key = bool(settings.anthropic_api_key.get_secret_value())
    if settings.llm_backend == "litellm":
        return has_key
    if settings.llm_backend == "claude_code":
        return _claude_code_available()
    return _claude_code_available() or has_key


async def _complete_claude_code(system: str, user: str, schema: type[T], model: str) -> T:
    """Single-turn completion via the Claude Code SDK (subscription auth, no API key).

    The SDK exposes no max-output-tokens knob, so a caller's ``max_tokens`` only bounds
    the LiteLLM path; here output is left to the model's own limit.
    """
    from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

    options = ClaudeAgentOptions(
        model=model,
        system_prompt=system,
        allowed_tools=[],  # plain LLM call — no tools
        max_turns=1,
    )
    prompt = f"{user}\n\n{_json_instruction(schema)}"

    async def _run() -> str:
        # The SDK exposes no native timeout; wrap the whole exchange in wait_for below.
        chunks: list[str] = []
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                chunks.extend(b.text for b in message.content if isinstance(b, TextBlock))
        return "".join(chunks)

    text = await asyncio.wait_for(_run(), timeout=settings.llm_timeout_seconds)
    return _parse_json(text, schema)


async def _complete_litellm(  # noqa: PLR0913 — independent passthrough args, not a god-function
    system: str, user: str, schema: type[T], model: str, max_tokens: int, label: str | None
) -> T:
    """Single-turn completion via LiteLLM (API key; provider-swappable by model string)."""
    from litellm import acompletion

    from arxiv_digest.clients.usage import record_litellm_usage

    response = await acompletion(
        model=f"anthropic/{model}",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format=schema,
        api_key=settings.anthropic_api_key.get_secret_value() or None,
        max_tokens=max_tokens,
        timeout=settings.llm_timeout_seconds,
        num_retries=2,
    )
    await record_litellm_usage(stage=label, model=model, response=response)
    return _parse_json(response.choices[0].message.content or "", schema)


async def complete_structured(  # noqa: PLR0913 — keyword-only options, not a god-function
    system: str,
    user: str,
    schema: type[T],
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    label: str | None = None,
) -> T:
    """Return a structured completion, honoring ``settings.llm_backend`` with auto-fallback.

    ``model`` and ``max_tokens`` default to the classification model and limit; pass them
    to override per call (e.g. a stronger model with more headroom for summarization).
    ``label`` names the calling pipeline stage; it tags the recorded usage row (LiteLLM path
    only — Claude Code subscription calls aren't billed and aren't recorded).
    """
    model = model or settings.classification_model
    max_tokens = max_tokens or _MAX_OUTPUT_TOKENS
    if settings.llm_backend == "claude_code":
        return await _complete_claude_code(system, user, schema, model)
    if settings.llm_backend == "litellm":
        return await _complete_litellm(system, user, schema, model, max_tokens, label)

    # auto: prefer the Claude Code SDK, fall back to LiteLLM on any failure.
    if _claude_code_available():
        try:
            return await _complete_claude_code(system, user, schema, model)
        except Exception:  # noqa: BLE001 — any SDK/auth failure should fall back to LiteLLM
            logger.warning("Claude Code SDK failed; falling back to LiteLLM", exc_info=True)
    return await _complete_litellm(system, user, schema, model, max_tokens, label)
