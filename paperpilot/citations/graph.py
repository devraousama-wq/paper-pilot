from __future__ import annotations

import re
from dataclasses import dataclass

import networkx as nx


@dataclass
class ParsedReference:
    raw: str
    title: str | None = None
    authors: list[str] | None = None
    year: int | None = None
    doi: str | None = None


REFERENCE_SPLIT = re.compile(r"\[\d+\]|\n\d+\.\s+")


def parse_reference_line(line: str) -> ParsedReference:
    cleaned = line.strip()
    doi_match = re.search(r"(10\.\d{4,9}/\S+)", cleaned)
    year_match = re.search(r"\b(19|20)\d{2}\b", cleaned)
    title = cleaned
    if "." in cleaned:
        title = cleaned.split(".", 1)[0]
    return ParsedReference(
        raw=cleaned,
        title=title[:160],
        year=int(year_match.group(0)) if year_match else None,
        doi=doi_match.group(1).rstrip(".,") if doi_match else None,
    )


def parse_references(text: str) -> list[ParsedReference]:
    chunks = [part.strip() for part in REFERENCE_SPLIT.split(text) if part.strip()]
    return [parse_reference_line(chunk) for chunk in chunks]


class CitationGraph:
    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def add_paper(self, paper_id: int, title: str) -> None:
        self.graph.add_node(paper_id, title=title)

    def add_citation(self, source_id: int, target_id: int) -> None:
        self.graph.add_edge(source_id, target_id)

    def resolve_references(self, paper_id: int, references: list[ParsedReference], library: dict[str, int]) -> list[int]:
        resolved: list[int] = []
        for ref in references:
            key = ref.doi or (ref.title or "").lower()
            target = library.get(key)
            if target is not None:
                self.add_citation(paper_id, target)
                resolved.append(target)
        return resolved

    def metrics(self, paper_id: int) -> dict[str, float]:
        if paper_id not in self.graph:
            return {"pagerank": 0.0, "betweenness": 0.0}
        pagerank = nx.pagerank(self.graph).get(paper_id, 0.0)
        betweenness = nx.betweenness_centrality(self.graph).get(paper_id, 0.0)
        return {"pagerank": float(pagerank), "betweenness": float(betweenness)}

    def neighborhood(self, paper_id: int, depth: int = 1) -> dict[str, list[int]]:
        if paper_id not in self.graph:
            return {"incoming": [], "outgoing": []}
        incoming = list(self.graph.predecessors(paper_id))
        outgoing = list(self.graph.successors(paper_id))
        if depth > 1:
            for node in list(outgoing):
                outgoing.extend(list(self.graph.successors(node)))
            for node in list(incoming):
                incoming.extend(list(self.graph.predecessors(node)))
        return {
            "incoming": sorted(set(incoming)),
            "outgoing": sorted(set(outgoing)),
        }

    def export_edges(self) -> list[dict[str, int]]:
        return [{"source": source, "target": target} for source, target in self.graph.edges]
