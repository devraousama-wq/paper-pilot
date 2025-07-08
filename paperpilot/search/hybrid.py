from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from paperpilot.embeddings.indexer import EmbeddingEncoder, FaissIndexStore


@dataclass
class SearchFilters:
    year: int | None = None
    author: str | None = None
    venue: str | None = None


@dataclass
class RankedDocument:
    paper_id: int
    title: str
    snippet: str
    score: float
    authors: str
    year: int | None = None


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25Index:
    def __init__(self) -> None:
        self.documents: dict[int, dict[str, str | int | None]] = {}
        self.term_freqs: dict[int, Counter[str]] = {}
        self.doc_lengths: dict[int, int] = {}
        self.avg_doc_length = 0.0
        self.df: Counter[str] = Counter()

    def add_document(self, paper_id: int, title: str, text: str, authors: str, year: int | None) -> None:
        tokens = tokenize(f"{title} {text}")
        self.documents[paper_id] = {
            "title": title,
            "authors": authors,
            "year": year,
            "text": text,
        }
        counts = Counter(tokens)
        self.term_freqs[paper_id] = counts
        self.doc_lengths[paper_id] = len(tokens)
        for term in counts:
            self.df[term] += 1
        total = sum(self.doc_lengths.values())
        self.avg_doc_length = total / max(len(self.doc_lengths), 1)

    def score(self, query: str, paper_id: int, k1: float = 1.5, b: float = 0.75) -> float:
        tokens = tokenize(query)
        if paper_id not in self.term_freqs:
            return 0.0
        score = 0.0
        doc_len = self.doc_lengths[paper_id]
        freqs = self.term_freqs[paper_id]
        total_docs = max(len(self.documents), 1)
        for term in tokens:
            if term not in freqs:
                continue
            df = self.df[term]
            idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
            tf = freqs[term]
            denom = tf + k1 * (1 - b + b * doc_len / max(self.avg_doc_length, 1))
            score += idf * (tf * (k1 + 1)) / max(denom, 1)
        return score


class HybridSearchEngine:
    def __init__(self) -> None:
        self.bm25 = BM25Index()
        self.encoder = EmbeddingEncoder()
        self.faiss = FaissIndexStore()

    def register_document(
        self,
        paper_id: int,
        title: str,
        text: str,
        authors: str,
        year: int | None,
    ) -> None:
        self.bm25.add_document(paper_id, title, text, authors, year)

    def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        top_k: int = 10,
        alpha: float = 0.55,
    ) -> list[RankedDocument]:
        filters = filters or SearchFilters()
        vector = self.encoder.encode([query])[0]
        vector_hits = {int(item[0]["paper_id"]): item[1] for item in self.faiss.search(vector, top_k=50)}
        combined: dict[int, float] = defaultdict(float)
        for paper_id in self.bm25.documents:
            meta = self.bm25.documents[paper_id]
            if filters.year and meta.get("year") != filters.year:
                continue
            if filters.author and filters.author.lower() not in str(meta.get("authors", "")).lower():
                continue
            if filters.venue and filters.venue.lower() not in str(meta.get("title", "")).lower():
                continue
            lexical = self.bm25.score(query, paper_id)
            semantic = vector_hits.get(paper_id, 0.0)
            combined[paper_id] = alpha * semantic + (1 - alpha) * lexical
        ranked = sorted(combined.items(), key=lambda item: item[1], reverse=True)[:top_k]
        results: list[RankedDocument] = []
        for paper_id, score in ranked:
            meta = self.bm25.documents[paper_id]
            text = str(meta["text"])
            snippet = text[:240] + ("..." if len(text) > 240 else "")
            results.append(
                RankedDocument(
                    paper_id=paper_id,
                    title=str(meta["title"]),
                    snippet=snippet,
                    score=score,
                    authors=str(meta["authors"]),
                    year=meta.get("year"),  # type: ignore[arg-type]
                )
            )
        return results
