from __future__ import annotations

import json
from typing import AsyncGenerator

import httpx
import structlog
from pydantic import BaseModel

from paperpilot.core.config import settings
from paperpilot.embeddings.indexer import EmbeddingEncoder, FaissIndexStore

logger = structlog.get_logger()


class CitationSpan(BaseModel):
    paper_id: int
    section_key: str
    chunk_id: str


class RagRequest(BaseModel):
    question: str
    top_k: int = 6
    follow_up: str | None = None


class RagResponse(BaseModel):
    answer: str
    citations: list[CitationSpan]


class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str = "llama3.2") -> None:
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.model = model

    async def generate(self, prompt: str) -> str:
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
        return str(data.get("response", "")).strip()

    async def stream(self, prompt: str) -> AsyncGenerator[str, None]:
        payload = {"model": self.model, "prompt": prompt, "stream": True}
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("response")
                    if token:
                        yield str(token)


class RagPipeline:
    def __init__(self) -> None:
        self.encoder = EmbeddingEncoder()
        self.index = FaissIndexStore()
        self.llm = OllamaClient()

    def build_prompt(self, question: str, contexts: list[tuple[dict[str, str | int], float]], follow_up: str | None) -> str:
        blocks = []
        for meta, score in contexts:
            label = f"Paper [{meta['paper_id']}, {meta['section_key']}]"
            blocks.append(f"{label}\n{meta['text']}\n(score={score:.3f})")
        context_text = "\n\n".join(blocks)
        follow = f"\nFollow-up context: {follow_up}" if follow_up else ""
        return (
            "Answer the research question using only the provided paper excerpts. "
            "Include inline citations like Paper [id, section].\n\n"
            f"Question: {question}{follow}\n\n"
            f"Sources:\n{context_text}\n\nAnswer:"
        )

    async def answer(self, request: RagRequest) -> RagResponse:
        vector = self.encoder.encode([request.question])[0]
        hits = self.index.search(vector, top_k=request.top_k)
        prompt = self.build_prompt(request.question, hits, request.follow_up)
        answer = await self.llm.generate(prompt)
        citations = [
            CitationSpan(
                paper_id=int(meta["paper_id"]),
                section_key=str(meta["section_key"]),
                chunk_id=str(meta["chunk_id"]),
            )
            for meta, _ in hits
        ]
        return RagResponse(answer=answer, citations=citations)
