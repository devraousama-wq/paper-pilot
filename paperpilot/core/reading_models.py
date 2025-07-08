from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from paperpilot.core.models import Base


class ReadingStatus(StrEnum):
    UNREAD = "unread"
    READING = "reading"
    DONE = "done"


class ReadingQueueItem(Base):
    __tablename__ = "reading_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"), index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default=ReadingStatus.UNREAD.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaperAnnotation(Base):
    __tablename__ = "paper_annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"), index=True)
    body: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[str] = mapped_column(String(256), default="")
    highlight: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
