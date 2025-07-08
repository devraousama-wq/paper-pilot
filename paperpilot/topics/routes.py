from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from paperpilot.embeddings.indexer import EmbeddingEncoder
from paperpilot.topics.clustering import TopicCluster, TopicClusterer

router = APIRouter(prefix="/topics", tags=["topics"])
clusterer = TopicClusterer()
encoder = EmbeddingEncoder()


class ClusterRequest(BaseModel):
    paper_ids: list[int]
    snippets: list[str]
    years: dict[int, int] = {}


class ClusterResponse(BaseModel):
    cluster_id: int
    label: str
    paper_ids: list[int]
    size: int


@router.post("/cluster", response_model=list[ClusterResponse])
async def build_clusters(request: ClusterRequest) -> list[ClusterResponse]:
    vectors = encoder.encode(request.snippets) if request.snippets else encoder.encode(["empty"])
    clusters: list[TopicCluster] = clusterer.cluster(vectors, request.paper_ids)
    labeled: list[ClusterResponse] = []
    for cluster in clusters:
        label = await clusterer.label_cluster(cluster, request.snippets)
        labeled.append(
            ClusterResponse(
                cluster_id=cluster.cluster_id,
                label=label,
                paper_ids=cluster.paper_ids,
                size=cluster.size,
            )
        )
    return labeled


@router.post("/timeline")
async def topic_timeline(request: ClusterRequest) -> dict[str, dict[int, int] | list[int]]:
    timeline = clusterer.timeline(request.paper_ids, request.years)
    emerging = clusterer.emerging_topics(timeline)
    return {"timeline": timeline, "emerging_years": emerging}
