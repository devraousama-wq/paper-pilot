from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from paperpilot.rag.pipeline import OllamaClient, RagPipeline, RagRequest, RagResponse

router = APIRouter(prefix="/rag", tags=["rag"])
pipeline = RagPipeline()


@router.post("/ask", response_model=RagResponse)
async def ask_question(request: RagRequest) -> RagResponse:
    return await pipeline.answer(request)


@router.post("/stream")
async def stream_answer(request: RagRequest) -> StreamingResponse:
    vector = pipeline.encoder.encode([request.question])[0]
    hits = pipeline.index.search(vector, top_k=request.top_k)
    prompt = pipeline.build_prompt(request.question, hits, request.follow_up)
    client = OllamaClient()

    async def event_stream():
        async for token in client.stream(prompt):
            yield token

    return StreamingResponse(event_stream(), media_type="text/plain")
