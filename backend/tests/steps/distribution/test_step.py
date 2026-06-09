"""Unit tests for the distribution step (DB, LLM, and email boundaries mocked)."""

import pytest
from _builders import make_paper

from arxiv_digest.clients.arxiv import Paper, Summary
from arxiv_digest.clients.db import Subscriber
from arxiv_digest.clients.email import EmailError
from arxiv_digest.clients.llm import LLMError
from arxiv_digest.steps.distribution import step as dist_step


def _paper(arxiv_id: str, title: str, topics: list[str]) -> Paper:
    return make_paper(
        arxiv_id=arxiv_id,
        title=title,
        topics=topics,
        summary=Summary(short=f"short-{arxiv_id}", long="long", conclusions="impact"),
    )


@pytest.fixture
def sent(monkeypatch):
    """Capture every email send_digest would send; stub the weekly-insight LLM call."""
    calls: list[dict[str, str]] = []

    async def fake_send_email(*, to: str, subject: str, html: str) -> None:
        calls.append({"to": to, "subject": subject, "html": html})

    async def fake_insight(system, user, schema, **kwargs):
        return schema(paragraph="weekly insight")

    monkeypatch.setattr(dist_step, "send_email", fake_send_email)
    monkeypatch.setattr(dist_step, "complete_structured", fake_insight)
    return calls


def _with_subscribers(monkeypatch, subscribers: list[Subscriber]) -> None:
    async def fake_get() -> list[Subscriber]:
        return subscribers

    monkeypatch.setattr(dist_step, "get_active_subscribers", fake_get)


async def test_filters_papers_to_each_subscribers_interests(sent, monkeypatch):
    papers = [_paper("u1", "On LLMs", ["LLMs"]), _paper("u2", "On RL", ["Reinforcement Learning"])]
    _with_subscribers(
        monkeypatch,
        [
            Subscriber(email="all@x.com", interests=[], unsubscribe_token="tok-all"),
            Subscriber(email="llm@x.com", interests=["LLMs"], unsubscribe_token="tok-llm"),
        ],
    )

    await dist_step.send_digest(papers)

    html_by_to = {call["to"]: call["html"] for call in sent}
    assert "On LLMs" in html_by_to["all@x.com"]
    assert "On RL" in html_by_to["all@x.com"]
    assert "On LLMs" in html_by_to["llm@x.com"]
    assert "On RL" not in html_by_to["llm@x.com"]


async def test_skips_subscriber_with_no_matching_papers(sent, monkeypatch):
    _with_subscribers(
        monkeypatch,
        [Subscriber(email="cv@x.com", interests=["Computer Vision"], unsubscribe_token="tok-cv")],
    )

    await dist_step.send_digest([_paper("u1", "On LLMs", ["LLMs"])])

    assert sent == []


async def test_no_papers_sends_nothing(sent, monkeypatch):
    _with_subscribers(
        monkeypatch, [Subscriber(email="all@x.com", interests=[], unsubscribe_token="tok-all")]
    )

    await dist_step.send_digest([])

    assert sent == []


async def test_no_subscribers_sends_nothing(sent, monkeypatch):
    _with_subscribers(monkeypatch, [])

    await dist_step.send_digest([_paper("u1", "On LLMs", ["LLMs"])])

    assert sent == []


async def test_one_failed_email_does_not_block_others(monkeypatch):
    delivered: list[str] = []

    async def flaky_send_email(*, to: str, subject: str, html: str) -> None:
        if to == "bad@x.com":
            msg = "smtp down"
            raise EmailError(msg)
        delivered.append(to)

    async def fake_insight(system, user, schema, **kwargs):
        return schema(paragraph="insight")

    monkeypatch.setattr(dist_step, "send_email", flaky_send_email)
    monkeypatch.setattr(dist_step, "complete_structured", fake_insight)
    _with_subscribers(
        monkeypatch,
        [
            Subscriber(email="bad@x.com", interests=[], unsubscribe_token="tok-bad"),
            Subscriber(email="good@x.com", interests=[], unsubscribe_token="tok-good"),
        ],
    )

    await dist_step.send_digest([_paper("u1", "On LLMs", ["LLMs"])])

    assert delivered == ["good@x.com"]


async def test_sends_digest_without_insight_when_llm_fails(sent, monkeypatch):
    async def failing_insight(system, user, schema, **kwargs):
        msg = "no backend"
        raise LLMError(msg)

    monkeypatch.setattr(dist_step, "complete_structured", failing_insight)
    _with_subscribers(
        monkeypatch, [Subscriber(email="all@x.com", interests=[], unsubscribe_token="tok-all")]
    )

    await dist_step.send_digest([_paper("u1", "On LLMs", ["LLMs"])])

    assert len(sent) == 1
    assert "weekly insight" not in sent[0]["html"]
    assert "On LLMs" in sent[0]["html"]
