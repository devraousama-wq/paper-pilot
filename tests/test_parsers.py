from paperpilot.parsers.sections import extract_figure_captions, split_sections


def test_split_sections_finds_introduction() -> None:
    text = "Abstract\nSummary here\n\nIntroduction\nIntro body\n\nConclusion\nEnd"
    sections = split_sections(text)
    keys = [section.section_key for section in sections]
    assert "introduction" in keys
    assert "conclusion" in keys


def test_extract_figure_captions() -> None:
    text = "Figure 1: Example caption about results.\n\nTable 1: Benchmark scores."
    assets = extract_figure_captions(text)
    assert len(assets) >= 2
