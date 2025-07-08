from __future__ import annotations

from dataclasses import dataclass

from paperpilot.citations.graph import CitationGraph
from paperpilot.embeddings.indexer import EmbeddingEncoder, FaissIndexStore


@dataclass
class RelatedPaper:
    paper_id: int
    title: str
    score: float
    reasons: list[str]


class RelatedWorkEngine:
    def __init__(self) -> None:
        self.encoder = EmbeddingEncoder()
        self.index = FaissIndexStore()
        self.graph = CitationGraph()
        self.library: dict[int, dict[str, str | int | None]] = {}

    def register_paper(self, paper_id: int, title: str, authors: str, text: str) -> None:
        self.library[paper_id] = {"title": title, "authors": authors, "text": text}
        self.graph.add_paper(paper_id, title)

    def suggest(self, paper_id: int, top_k: int = 8) -> list[RelatedPaper]:
        meta = self.library.get(paper_id)
        if not meta:
            return []
        query = f"{meta['title']} {meta['text']}"
        vector = self.encoder.encode([str(query)])[0]
        hits = self.index.search(vector, top_k=top_k + 3)
        source_authors = {part.strip().lower() for part in str(meta["authors"]).split(",") if part.strip()}
        neighborhood = self.graph.neighborhood(paper_id)
        related_ids = set(neighborhood["incoming"] + neighborhood["outgoing"])
        suggestions: list[RelatedPaper] = []
        for chunk_meta, score in hits:
            candidate_id = int(chunk_meta["paper_id"])
            if candidate_id == paper_id:
                continue
            reasons = ["embedding similarity"]
            candidate = self.library.get(candidate_id, {})
            candidate_authors = {
                part.strip().lower() for part in str(candidate.get("authors", "")).split(",") if part.strip()
            }
            if source_authors & candidate_authors:
                reasons.append("author overlap")
            if candidate_id in related_ids:
                reasons.append("citation overlap")
            suggestions.append(
                RelatedPaper(
                    paper_id=candidate_id,
                    title=str(candidate.get("title", f"Paper {candidate_id}")),
                    score=score,
                    reasons=reasons,
                )
            )
        suggestions.sort(key=lambda item: item.score, reverse=True)
        return suggestions[:top_k]
