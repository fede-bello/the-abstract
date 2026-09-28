from datetime import UTC, datetime

import pytest
from _builders import make_paper

from arxiv_digest.clients.arxiv import (
    ArxivError,
    Author,
    OaiPage,
    Paper,
    parse_list_records,
    select_recent,
)

_ENVELOPE = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  {body}
</OAI-PMH>"""

_RECORD = """
<record>
  <header><identifier>oai:arXiv.org:2609.22043</identifier></header>
  <metadata>
    <arXivRaw xmlns="http://arxiv.org/OAI/arXivRaw/">
      <id>2609.22043</id>
      <version version="v1"><date>Fri, 18 Sep 2026 17:34:13 GMT</date></version>
      <version version="v2"><date>Mon, 21 Sep 2026 09:00:00 GMT</date></version>
      <title>An Interpretable Memory
  Decision Controller</title>
      <authors>Yiming Zhang (Univ X, Lab Y), Jinghong Zhang and Haoran Zhao</authors>
      <categories>cs.CL cs.LG</categories>
      <comments>17 pages</comments>
      <abstract>  Memory systems matter.
</abstract>
    </arXivRaw>
  </metadata>
</record>"""


def _list_records(records: str, token: str = "") -> bytes:
    body = f"<ListRecords>{records}<resumptionToken>{token}</resumptionToken></ListRecords>"
    return _ENVELOPE.format(body=body).encode()


class TestParseListRecords:
    def test_maps_arxiv_raw_record_to_paper(self):
        page = parse_list_records(_list_records(_RECORD))

        assert page.papers == [
            Paper(
                arxiv_id="2609.22043v2",
                entry_id="http://arxiv.org/abs/2609.22043v2",
                title="An Interpretable Memory Decision Controller",
                abstract="Memory systems matter.",
                authors=[
                    Author(name="Yiming Zhang", affiliation="Univ X, Lab Y"),
                    Author(name="Jinghong Zhang"),
                    Author(name="Haoran Zhao"),
                ],
                primary_category="cs.CL",
                categories=["cs.CL", "cs.LG"],
                comment="17 pages",
                published=datetime(2026, 9, 18, 17, 34, 13, tzinfo=UTC),
                updated=datetime(2026, 9, 21, 9, 0, tzinfo=UTC),
                pdf_url="https://arxiv.org/pdf/2609.22043v2",
            )
        ]

    def test_returns_resumption_token_when_more_pages(self):
        next_page = "abc|1001"

        page = parse_list_records(_list_records(_RECORD, token=next_page))

        assert page.resumption_token == next_page

    def test_empty_resumption_token_means_last_page(self):
        page = parse_list_records(_list_records(_RECORD))

        assert page.resumption_token is None

    def test_skips_deleted_records(self):
        deleted = '<record><header status="deleted"><identifier>x</identifier></header></record>'

        page = parse_list_records(_list_records(deleted))

        assert page.papers == []

    def test_no_records_match_is_an_empty_page(self):
        body = '<error code="noRecordsMatch">No records</error>'

        page = parse_list_records(_ENVELOPE.format(body=body).encode())

        assert page == OaiPage(papers=[])

    def test_raises_on_other_oai_errors(self):
        body = '<error code="badResumptionToken">expired</error>'

        with pytest.raises(ArxivError, match=r"badResumptionToken: expired"):
            parse_list_records(_ENVELOPE.format(body=body).encode())


class TestSelectRecent:
    _SINCE = datetime(2026, 9, 21, tzinfo=UTC)

    def test_drops_papers_first_submitted_before_window(self):
        old = make_paper(arxiv_id="old", published=datetime(2026, 9, 20, tzinfo=UTC))
        new = make_paper(arxiv_id="new", published=datetime(2026, 9, 22, tzinfo=UTC))

        assert select_recent([old, new], self._SINCE, max_results=10) == [new]

    def test_orders_newest_first_and_caps(self):
        papers = [
            make_paper(arxiv_id=str(day), published=datetime(2026, 9, day, tzinfo=UTC))
            for day in (22, 25, 23)
        ]

        selected = select_recent(papers, self._SINCE, max_results=2)

        assert [paper.arxiv_id for paper in selected] == ["25", "23"]

    def test_deduplicates_cross_listed_papers(self):
        paper = make_paper(arxiv_id="dup", published=datetime(2026, 9, 22, tzinfo=UTC))

        assert select_recent([paper, paper], self._SINCE, max_results=10) == [paper]
