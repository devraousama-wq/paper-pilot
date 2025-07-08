from paperpilot.citations.graph import CitationGraph, parse_reference_line


def test_parse_reference_line_extracts_year() -> None:
    ref = parse_reference_line("Smith et al. Deep models. 2021.")
    assert ref.year == 2021


def test_citation_graph_metrics() -> None:
    graph = CitationGraph()
    graph.add_paper(1, "A")
    graph.add_paper(2, "B")
    graph.add_citation(1, 2)
    metrics = graph.metrics(1)
    assert metrics["pagerank"] >= 0.0
