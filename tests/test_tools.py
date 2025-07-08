from paperpilot.ingestion.bibtex import parse_bibtex
from paperpilot.ingestion.dedup import normalize_title


def test_parse_bibtex_extracts_title() -> None:
    content = '@article{sample2024,\n  title={Sample Paper},\n  author={Alice and Bob},\n  year={2024}\n}'
    entries = parse_bibtex(content)
    assert entries[0].title == "Sample Paper"


def test_normalize_title() -> None:
    assert normalize_title("Hello, World!") == "hello world"
