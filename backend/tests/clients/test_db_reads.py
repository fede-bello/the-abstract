"""Unit tests for the API read functions in clients/db.py.

These never touch Postgres: a fake pool/connection captures the SQL + bind args the function
issues and returns canned rows, so we test the query builder and row->object mapping in
isolation. (The live round-trips live in test_db.py behind the `integration` marker.)
"""

from datetime import UTC, date, datetime

import pytest

from arxiv_digest.clients import db
from arxiv_digest.clients.arxiv import Author, Summary
from arxiv_digest.clients.db import WeekSummary

_DT = datetime(2026, 6, 3, tzinfo=UTC)


class FakeConn:
    """Records every fetch/fetchrow call and replays canned results in order."""

    def __init__(self, *, fetch_results=None, fetchrow_results=None):
        self._fetch = list(fetch_results or [])
        self._fetchrow = list(fetchrow_results or [])
        self.calls = []

    async def fetch(self, sql, *args):
        self.calls.append(("fetch", sql, args))
        return self._fetch.pop(0) if self._fetch else []

    async def fetchrow(self, sql, *args):
        self.calls.append(("fetchrow", sql, args))
        return self._fetchrow.pop(0) if self._fetchrow else None


class _Acquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *_exc):
        return False


class FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return _Acquire(self._conn)


@pytest.fixture
def fake_db(monkeypatch):
    """Install a fake pool returning the given connection; yields the connection for assertions."""

    def _install(conn):
        pool = FakePool(conn)

        async def _get_pool():
            return pool

        monkeypatch.setattr(db, "_get_pool", _get_pool)
        return conn

    return _install


def _paper_row(**overrides):
    base = {
        "arxiv_id": "2606.00001",
        "entry_id": "http://arxiv.org/abs/2606.00001",
        "title": "A Paper",
        "abstract": "An abstract.",
        "authors": [{"name": "Ada", "affiliation": None}],
        "primary_category": "cs.LG",
        "categories": ["cs.LG", "stat.ML"],
        "comment": None,
        "journal_ref": None,
        "doi": None,
        "published": _DT,
        "updated": _DT,
        "pdf_url": "http://arxiv.org/pdf/2606.00001",
        "topics": ["LLMs"],
        "classification_rationale": None,
        "summary_short": None,
        "summary_long": None,
        "summary_conclusions": None,
    }
    return base | overrides


def _week_row(**overrides):
    base = {
        "week_key": "2026-W23",
        "label": "Week of Jun 1, 2026",
        "count": 3,
        "start": date(2026, 6, 1),
        "end": date(2026, 6, 7),
    }
    return base | overrides


class TestListPapersQuery:
    async def test_no_filters_orders_newest_first_with_no_where(self, fake_db):
        conn = fake_db(FakeConn(fetch_results=[[]]))
        await db.list_papers()
        _, sql, args = conn.calls[0]
        assert "where" not in sql
        assert sql.endswith("order by published desc")
        assert args == ()

    async def test_topic_filter_uses_array_overlap(self, fake_db):
        conn = fake_db(FakeConn(fetch_results=[[]]))
        await db.list_papers(topics=["LLMs", "NLP"])
        _, sql, args = conn.calls[0]
        assert "topics && $1::text[]" in sql
        assert args == (["LLMs", "NLP"],)

    async def test_keyword_searches_title_abstract_and_authors(self, fake_db):
        conn = fake_db(FakeConn(fetch_results=[[]]))
        await db.list_papers(q="transformer")
        _, sql, args = conn.calls[0]
        assert "title ilike $1" in sql
        assert "abstract ilike $1" in sql
        assert "authors::text ilike $1" in sql
        assert args == ("%transformer%",)

    async def test_date_range_is_inclusive_on_both_ends(self, fake_db):
        conn = fake_db(FakeConn(fetch_results=[[]]))
        await db.list_papers(date_from="2026-06-01", date_to="2026-06-07")
        _, sql, args = conn.calls[0]
        assert "published >= $1::date" in sql
        assert "published < $2::date + 1" in sql
        assert args == (date(2026, 6, 1), date(2026, 6, 7))

    async def test_combined_filters_bind_in_declared_order(self, fake_db):
        conn = fake_db(FakeConn(fetch_results=[[]]))
        await db.list_papers(
            topics=["LLMs"],
            categories=["cs.LG"],
            date_from="2026-06-01",
            date_to="2026-06-07",
            q="x",
        )
        _, sql, args = conn.calls[0]
        assert "topics && $1::text[]" in sql
        assert "categories && $2::text[]" in sql
        assert "published >= $3::date" in sql
        assert "published < $4::date + 1" in sql
        assert "title ilike $5" in sql
        assert args == (["LLMs"], ["cs.LG"], date(2026, 6, 1), date(2026, 6, 7), "%x%")


class TestRowToPaper:
    async def test_list_omits_full_text(self, fake_db):
        fake_db(FakeConn(fetch_results=[[_paper_row()]]))
        [paper] = await db.list_papers()
        assert paper.full_text is None
        assert paper.authors == [Author(name="Ada", affiliation=None)]
        assert paper.topics == ["LLMs"]

    async def test_get_paper_includes_full_text_and_summary(self, fake_db):
        row = _paper_row(
            full_text="BODY", summary_short="s", summary_long="l", summary_conclusions="c"
        )
        fake_db(FakeConn(fetchrow_results=[row]))
        paper = await db.get_paper("2606.00001")
        assert paper is not None
        assert paper.full_text == "BODY"
        assert paper.summary == Summary(short="s", long="l", conclusions="c")

    async def test_get_paper_summary_is_none_when_unsummarized(self, fake_db):
        fake_db(FakeConn(fetchrow_results=[_paper_row(full_text="BODY")]))
        paper = await db.get_paper("2606.00001")
        assert paper is not None
        assert paper.summary is None

    async def test_get_paper_returns_none_when_absent(self, fake_db):
        fake_db(FakeConn(fetchrow_results=[None]))
        assert await db.get_paper("missing") is None


class TestTopicsAndCategories:
    async def test_topic_counts_maps_title_to_count(self, fake_db):
        rows = [{"topic": "LLMs", "count": 3}, {"topic": "NLP", "count": 1}]
        fake_db(FakeConn(fetch_results=[rows]))
        assert await db.list_topic_counts() == {"LLMs": 3, "NLP": 1}

    async def test_categories_returns_codes(self, fake_db):
        rows = [{"category": "cs.CL"}, {"category": "cs.LG"}]
        fake_db(FakeConn(fetch_results=[rows]))
        assert await db.list_categories() == ["cs.CL", "cs.LG"]


class TestWeekDerivation:
    async def test_list_week_summaries_maps_rows(self, fake_db):
        fake_db(FakeConn(fetch_results=[[_week_row()]]))
        result = await db.list_week_summaries()
        assert result == [
            WeekSummary(
                week_key="2026-W23",
                label="Week of Jun 1, 2026",
                count=3,
                start=date(2026, 6, 1),
                end=date(2026, 6, 7),
            )
        ]

    async def test_get_week_assembles_summary_and_papers(self, fake_db):
        fake_db(FakeConn(fetchrow_results=[_week_row(count=1)], fetch_results=[[_paper_row()]]))
        issue = await db.get_week("2026-W23")
        assert issue is not None
        assert issue.week.week_key == "2026-W23"
        assert len(issue.papers) == 1
        assert issue.papers[0].full_text is None

    async def test_get_week_returns_none_when_no_papers(self, fake_db):
        fake_db(FakeConn(fetchrow_results=[None]))
        assert await db.get_week("2099-W01") is None

    async def test_get_latest_week_follows_the_key(self, fake_db):
        fake_db(
            FakeConn(
                fetchrow_results=[{"week_key": "2026-W23"}, _week_row(count=1)],
                fetch_results=[[_paper_row()]],
            )
        )
        issue = await db.get_latest_week()
        assert issue is not None
        assert issue.week.week_key == "2026-W23"

    async def test_get_latest_week_none_when_empty(self, fake_db):
        fake_db(FakeConn(fetchrow_results=[{"week_key": None}]))
        assert await db.get_latest_week() is None
