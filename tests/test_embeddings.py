from paperpilot.embeddings.indexer import chunk_text


def test_chunk_text_overlap() -> None:
    text = "a" * 600
    chunks = chunk_text(1, "body", text, chunk_size=200, overlap=40)
    assert len(chunks) >= 3
    assert chunks[0].paper_id == 1
