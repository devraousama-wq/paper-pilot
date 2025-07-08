from __future__ import annotations

from dataclasses import dataclass

from paperpilot.rag.pipeline import OllamaClient


@dataclass
class ReviewSection:
    key: str
    title: str
    content: str


REVIEW_OUTLINE = [
    ("problem", "Problem framing"),
    ("evolution", "Chronological evolution"),
    ("taxonomy", "Methodological taxonomy"),
    ("comparison", "Results comparison"),
    ("gaps", "Open challenges"),
]


class LiteratureReviewGenerator:
    def __init__(self) -> None:
        self.llm = OllamaClient()

    def build_section_prompt(self, topic: str, section_key: str, section_title: str, paper_summaries: list[str]) -> str:
        joined = "\n\n".join(paper_summaries)
        return (
            f"Write the '{section_title}' section for a literature review on '{topic}'. "
            "Use markdown, cite papers inline as [Paper id].\n\n"
            f"Selected papers:\n{joined}\n\nSection:"
        )

    async def generate(
        self,
        topic: str,
        paper_summaries: list[str],
        outline: list[tuple[str, str]] | None = None,
    ) -> list[ReviewSection]:
        outline = outline or REVIEW_OUTLINE
        sections: list[ReviewSection] = []
        for key, title in outline:
            prompt = self.build_section_prompt(topic, key, title, paper_summaries)
            content = await self.llm.generate(prompt)
            sections.append(ReviewSection(key=key, title=title, content=content))
        return sections

    async def regenerate_section(
        self,
        topic: str,
        section_key: str,
        section_title: str,
        paper_summaries: list[str],
    ) -> ReviewSection:
        prompt = self.build_section_prompt(topic, section_key, section_title, paper_summaries)
        content = await self.llm.generate(prompt)
        return ReviewSection(key=section_key, title=section_title, content=content)

    def export_markdown(self, topic: str, sections: list[ReviewSection]) -> str:
        lines = [f"# Literature review: {topic}", ""]
        for section in sections:
            lines.append(f"## {section.title}")
            lines.append(section.content)
            lines.append("")
        return "\n".join(lines)
