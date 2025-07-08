from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import structlog

from paperpilot.core.config import settings

logger = structlog.get_logger()


@dataclass
class TextChunk:
    paper_id: int
    section_key: str
    chunk_id: str
    text: str
    start_offset: int
    end_offset: int


def chunk_text(
    paper_id: int,
    section_key: str,
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[TextChunk]:
    if not text.strip():
        return []
    chunks: list[TextChunk] = []
    start = 0
    index = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(
                TextChunk(
                    paper_id=paper_id,
                    section_key=section_key,
                    chunk_id=f"{paper_id}:{section_key}:{index}",
                    text=chunk,
                    start_offset=start,
                    end_offset=end,
                )
            )
            index += 1
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


class EmbeddingEncoder:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.embedding_model
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        model = self._load_model()
        vectors = model.encode(texts, batch_size=batch_size, show_progress_bar=False)
        return np.asarray(vectors, dtype=np.float32)


class FaissIndexStore:
    def __init__(self, index_dir: Path | None = None) -> None:
        self.index_dir = index_dir or Path(settings.data_dir) / "faiss"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.index_dir / "chunks.json"
        self.index_path = self.index_dir / "index.faiss"
        self._index = None
        self._metadata: list[dict[str, str | int]] = []

    def _load_index(self):
        if self._index is None:
            import faiss

            if self.index_path.exists():
                self._index = faiss.read_index(str(self.index_path))
                if self.metadata_path.exists():
                    self._metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            else:
                self._index = None
                self._metadata = []
        return self._index

    def add(self, chunks: list[TextChunk], vectors: np.ndarray) -> None:
        import faiss

        if vectors.size == 0:
            return
        dimension = vectors.shape[1]
        index = self._load_index()
        if index is None:
            index = faiss.IndexFlatIP(dimension)
        faiss.normalize_L2(vectors)
        index.add(vectors)
        for chunk in chunks:
            self._metadata.append(
                {
                    "paper_id": chunk.paper_id,
                    "section_key": chunk.section_key,
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                }
            )
        self._index = index
        faiss.write_index(index, str(self.index_path))
        self.metadata_path.write_text(json.dumps(self._metadata), encoding="utf-8")

    def search(self, query_vector: np.ndarray, top_k: int = 10) -> list[tuple[dict[str, str | int], float]]:
        import faiss

        index = self._load_index()
        if index is None or not self._metadata:
            return []
        query = np.asarray(query_vector, dtype=np.float32).reshape(1, -1)
        faiss.normalize_L2(query)
        scores, indices = index.search(query, min(top_k, len(self._metadata)))
        results: list[tuple[dict[str, str | int], float]] = []
        for score, idx in zip(scores[0], indices[0], strict=False):
            if idx < 0:
                continue
            results.append((self._metadata[idx], float(score)))
        return results
