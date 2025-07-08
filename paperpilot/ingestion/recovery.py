from __future__ import annotations

import json
from pathlib import Path

import structlog

from paperpilot.core.config import settings
from paperpilot.ingestion.jobs import IngestionJob, JobStatus, job_store, run_ingestion_job
from paperpilot.core.database import SessionLocal

logger = structlog.get_logger()


class JobRecoveryStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(settings.data_dir) / "jobs.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def persist(self) -> None:
        payload = [
            {
                "id": job.id,
                "kind": job.kind,
                "payload": job.payload,
                "status": job.status,
                "progress": job.progress,
                "message": job.message,
                "error": job.error,
                "paper_id": job.paper_id,
            }
            for job in job_store.list_jobs()
        ]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def restore(self) -> list[IngestionJob]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        restored: list[IngestionJob] = []
        for item in payload:
            job = IngestionJob(
                id=item["id"],
                kind=item["kind"],
                payload=item["payload"],
                status=JobStatus(item["status"]),
                progress=float(item["progress"]),
                message=item.get("message", ""),
                error=item.get("error"),
                paper_id=item.get("paper_id"),
            )
            job_store._jobs[job.id] = job
            restored.append(job)
        return restored


recovery_store = JobRecoveryStore()


async def retry_failed_jobs(max_attempts: int = 3) -> list[str]:
    retried: list[str] = []
    for job in job_store.list_jobs():
        if job.status != JobStatus.FAILED:
            continue
        attempts = int(getattr(job, "attempts", 0)) + 1
        if attempts > max_attempts:
            continue
        job.status = JobStatus.PENDING
        job.error = None
        job.message = "retry scheduled"
        setattr(job, "attempts", attempts)
        async with SessionLocal() as session:
            await run_ingestion_job(session, job)
        retried.append(job.id)
        logger.info("job_retry_completed", job_id=job.id, attempts=attempts)
    recovery_store.persist()
    return retried
