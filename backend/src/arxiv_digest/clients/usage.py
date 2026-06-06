"""Usage/cost recording for paid external calls — best-effort, never fatal.

Writes one ``usage_events`` row per paid LLM completion (LiteLLM path) and per LlamaParse
job, so the week's spend can be rolled up (see ``db.fetch_weekly_usage`` and the
``arxiv-digest usage`` command). Claude Code subscription completions are not recorded: they
expose no token data and cost $0 at the margin.

Recording must never break the pipeline, so every entry point swallows its own errors (a
failed insert, an unconfigured DB) and logs a warning. Heavy imports (``db``, ``litellm``)
are deferred into the functions, matching ``clients/llm.py``'s lazy-import style.
"""

import logging

from arxiv_digest.config import ParseTier, settings

logger = logging.getLogger(__name__)


def _litellm_tokens(response: object) -> tuple[int | None, int | None]:
    """Pull (prompt, completion) token counts off a LiteLLM response, defensively."""
    usage = getattr(response, "usage", None)
    prompt = getattr(usage, "prompt_tokens", None)
    completion = getattr(usage, "completion_tokens", None)
    return prompt, completion


def _litellm_cost(response: object) -> float:
    """LiteLLM's own cost estimate for a response, or 0.0 if it can't be computed."""
    from litellm import completion_cost

    try:
        return float(completion_cost(completion_response=response))
    except Exception:  # noqa: BLE001 — cost is best-effort accounting, never worth failing a call
        logger.warning("could not compute LiteLLM cost; recording 0", exc_info=True)
        return 0.0


async def record_litellm_usage(*, stage: str | None, model: str, response: object) -> None:
    """Record a paid LiteLLM completion's tokens and cost. Best-effort; errors are swallowed."""
    if not settings.supabase_db_url.get_secret_value():
        return
    from arxiv_digest.clients.db import UsageEvent, record_usage_event

    prompt_tokens, completion_tokens = _litellm_tokens(response)
    event = UsageEvent(
        kind="llm",
        stage=stage,
        model=model,
        input_tokens=prompt_tokens,
        output_tokens=completion_tokens,
        cost_usd=_litellm_cost(response),
    )
    try:
        await record_usage_event(event)
    except Exception:  # noqa: BLE001 — usage tracking must never break the pipeline
        logger.warning("failed to record LLM usage for stage %s", stage, exc_info=True)


async def record_parse_usage(*, pages: int, tier: ParseTier) -> None:
    """Record a LlamaParse job's pages and estimated cost. Best-effort; errors are swallowed."""
    if not settings.supabase_db_url.get_secret_value():
        return
    from arxiv_digest.clients.db import UsageEvent, record_usage_event

    cost = pages * settings.parse_cost_per_page_usd.get(tier, 0.0)
    event = UsageEvent(kind="parse", stage="parsing", pages=pages, tier=tier, cost_usd=cost)
    try:
        await record_usage_event(event)
    except Exception:  # noqa: BLE001 — usage tracking must never break the pipeline
        logger.warning("failed to record parse usage (%d pages, %s)", pages, tier, exc_info=True)
