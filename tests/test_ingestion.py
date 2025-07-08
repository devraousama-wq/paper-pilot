from paperpilot.ingestion.sources import parse_arxiv_id, parse_doi


def test_parse_arxiv_id() -> None:
    assert parse_arxiv_id("2301.00001") == "2301.00001"
    assert parse_arxiv_id("arxiv:2301.00001") == "2301.00001"


def test_parse_doi() -> None:
    assert parse_doi("10.1234/example.doi") == "10.1234/example.doi"
