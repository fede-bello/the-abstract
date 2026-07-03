"""Unit tests for the best-effort usage recorder (DB + litellm mocked at the boundary)."""

import sys
import types
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from arxiv_digest.clients import usage
from arxiv_digest.clients.db import DBError, UsageEvent
from arxiv_digest.config import settings

_DB_URL = SecretStr("postgres://user:pass@localhost/db")


@pytest.fixture
def captured_events(monkeypatch):
    """Patch the DB writer to capture recorded events instead of hitting Postgres."""
    events: list[UsageEvent] = []

    async def fake_record(event: UsageEvent) -> None:
        events.append(event)

    monkeypatch.setattr("arxiv_digest.clients.db.record_usage_event", fake_record)
    return events


def _fake_litellm(monkeypatch, completion_cost) -> None:
    """Inject a fake ``litellm`` module so the real (heavy) package isn't imported."""
    module = types.ModuleType("litellm")
    module.completion_cost = completion_cost  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "litellm", module)


def _response(prompt_tokens: int, completion_tokens: int) -> SimpleNamespace:
    usage_ns = SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return SimpleNamespace(usage=usage_ns)


async def test_records_tokens_and_cost(monkeypatch, captured_events):
    monkeypatch.setattr(settings, "supabase_db_url", _DB_URL)
    _fake_litellm(monkeypatch, lambda completion_response: 0.05)

    await usage.record_litellm_usage(
        stage="classification", model="claude-haiku", response=_response(200, 40)
    )

    assert captured_events == [
        UsageEvent(
            kind="llm",
            stage="classification",
            model="claude-haiku",
            input_tokens=200,
            output_tokens=40,
            cost_usd=0.05,
        )
    ]


async def test_records_none_tokens_when_response_has_no_usage(monkeypatch, captured_events):
    monkeypatch.setattr(settings, "supabase_db_url", _DB_URL)
    _fake_litellm(monkeypatch, lambda completion_response: 0.0)

    await usage.record_litellm_usage(stage="summarization", model="m", response=SimpleNamespace())

    assert captured_events == [
        UsageEvent(kind="llm", stage="summarization", model="m", cost_usd=0.0)
    ]


async def test_records_zero_cost_when_pricing_unknown(monkeypatch, captured_events):
    monkeypatch.setattr(settings, "supabase_db_url", _DB_URL)

    def unpriced(completion_response):
        msg = "no pricing for model"
        raise RuntimeError(msg)

    _fake_litellm(monkeypatch, unpriced)

    await usage.record_litellm_usage(stage="classification", model="m", response=_response(1, 1))

    assert captured_events[0].cost_usd == 0.0


async def test_record_litellm_usage_skips_when_db_unconfigured(monkeypatch, captured_events):
    monkeypatch.setattr(settings, "supabase_db_url", SecretStr(""))

    await usage.record_litellm_usage(stage="classification", model="m", response=SimpleNamespace())

    assert captured_events == []


async def test_record_litellm_usage_swallows_db_error(monkeypatch, caplog):
    monkeypatch.setattr(settings, "supabase_db_url", _DB_URL)
    _fake_litellm(monkeypatch, lambda completion_response: 0.0)

    async def failing_record(event: UsageEvent) -> None:
        msg = "write failed"
        raise DBError(msg)

    monkeypatch.setattr("arxiv_digest.clients.db.record_usage_event", failing_record)

    await usage.record_litellm_usage(stage="summarization", model="m", response=_response(1, 1))

    assert "failed to record LLM usage" in caplog.text


async def test_record_parse_usage_records_pages(monkeypatch, captured_events):
    monkeypatch.setattr(settings, "supabase_db_url", _DB_URL)

    await usage.record_parse_usage(pages=10)

    # LiteParse is local, so parse rows track pages only — no tier, no cost.
    assert captured_events == [UsageEvent(kind="parse", stage="parsing", pages=10)]


async def test_record_parse_usage_skips_when_db_unconfigured(monkeypatch, captured_events):
    monkeypatch.setattr(settings, "supabase_db_url", SecretStr(""))

    await usage.record_parse_usage(pages=10)

    assert captured_events == []
