from paperpilot.rag.pipeline import RagPipeline


def test_build_prompt_includes_question() -> None:
    pipeline = RagPipeline()
    prompt = pipeline.build_prompt(
        "what is contrastive learning?",
        [({"paper_id": 1, "section_key": "intro", "chunk_id": "1:intro:0", "text": "contrastive loss"}, 0.9)],
        None,
    )
    assert "contrastive learning" in prompt
    assert "Paper [1, intro]" in prompt
