"""Unit tests for the LLM client's model/provider helpers (pure functions)."""

import pytest

from arxiv_digest.clients.llm import _bare_model, _is_anthropic_model


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("anthropic/claude-haiku-4-5-20251001", "claude-haiku-4-5-20251001"),
        ("openai/gpt-4o-mini", "gpt-4o-mini"),
        ("claude-sonnet-4-6", "claude-sonnet-4-6"),  # already bare
    ],
)
def test_bare_model_strips_provider_prefix(model, expected):
    assert _bare_model(model) == expected


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("anthropic/claude-haiku-4-5-20251001", True),
        ("claude-sonnet-4-6", True),  # bare name assumed Anthropic
        ("openai/gpt-4o-mini", False),
        ("gemini/gemini-2.0-flash", False),
    ],
)
def test_is_anthropic_model(model, expected):
    assert _is_anthropic_model(model) is expected
