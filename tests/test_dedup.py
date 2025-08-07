from paperpilot.ingestion.dedup import normalize_authors, normalize_title


def test_normalize_authors_sorts_names() -> None:
    assert normalize_authors("Bob, Alice") == "alice|bob"


def test_normalize_title_strips_punctuation() -> None:
    assert normalize_title("Hello: World") == "hello world"
