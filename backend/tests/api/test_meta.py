"""Unit test for the /topics taxonomy ordering — the one non-trivial bit of API logic."""

from arxiv_digest.api.models import TopicCountOut
from arxiv_digest.api.routers import meta


class TestTopicsOrdering:
    async def test_orders_by_taxonomy_and_omits_zero_count_topics(self, monkeypatch):
        async def fake_counts():
            # Out of taxonomy order; most topics absent (i.e. zero).
            return {"NLP": 2, "LLMs": 5}

        monkeypatch.setattr(meta.db, "list_topic_counts", fake_counts)

        result = await meta.list_topics()

        # LLMs precedes NLP in the taxonomy; every absent topic is omitted.
        assert result == [
            TopicCountOut(title="LLMs", count=5),
            TopicCountOut(title="NLP", count=2),
        ]
