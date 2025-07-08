from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np

from paperpilot.rag.pipeline import OllamaClient


@dataclass
class TopicCluster:
    cluster_id: int
    label: str
    paper_ids: list[int]
    size: int


class TopicClusterer:
    def __init__(self) -> None:
        self.llm = OllamaClient()

    def cluster(self, vectors: np.ndarray, paper_ids: list[int], min_cluster_size: int = 2) -> list[TopicCluster]:
        try:
            import hdbscan
        except ImportError:
            return [TopicCluster(cluster_id=0, label="general", paper_ids=paper_ids, size=len(paper_ids))]
        clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric="euclidean")
        labels = clusterer.fit_predict(vectors)
        grouped: dict[int, list[int]] = defaultdict(list)
        for paper_id, label in zip(paper_ids, labels, strict=False):
            grouped[int(label)].append(paper_id)
        clusters: list[TopicCluster] = []
        for cluster_id, members in grouped.items():
            clusters.append(
                TopicCluster(
                    cluster_id=cluster_id,
                    label=f"topic-{cluster_id}",
                    paper_ids=members,
                    size=len(members),
                )
            )
        return clusters

    async def label_cluster(self, cluster: TopicCluster, snippets: list[str]) -> str:
        prompt = (
            "Provide a short topic label for this paper cluster.\n\n"
            + "\n".join(snippets[:8])
            + "\n\nLabel:"
        )
        label = await self.llm.generate(prompt)
        return label.split("\n", 1)[0][:80]

    def timeline(self, paper_ids: list[int], years: dict[int, int]) -> dict[int, int]:
        counter: Counter[int] = Counter()
        for paper_id in paper_ids:
            year = years.get(paper_id)
            if year:
                counter[year] += 1
        return dict(sorted(counter.items()))

    def emerging_topics(self, timeline: dict[int, int], window: int = 2) -> list[int]:
        if len(timeline) < window + 1:
            return []
        years = sorted(timeline)
        recent = years[-window:]
        previous = years[-window * 2 : -window]
        recent_total = sum(timeline[year] for year in recent)
        previous_total = sum(timeline.get(year, 0) for year in previous) or 1
        if recent_total / previous_total >= 1.5:
            return recent
        return []
