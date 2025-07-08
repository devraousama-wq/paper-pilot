from paperpilot.search.hybrid import BM25Index


def test_bm25_scores_matching_document_higher() -> None:
    index = BM25Index()
    index.add_document(1, "Contrastive Learning", "contrastive learning on medical images", "Doe", 2024)
    index.add_document(2, "Graph Theory", "network flows and cuts", "Smith", 2020)
    score_one = index.score("contrastive learning medical", 1)
    score_two = index.score("contrastive learning medical", 2)
    assert score_one > score_two
