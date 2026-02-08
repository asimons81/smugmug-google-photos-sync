from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Segment(BaseModel):
    start: float
    end: float
    text: str


class JobError(BaseModel):
    code: str
    message: str


class Job(BaseModel):
    id: str
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    file_name: str = ""
    file_size: int = 0
    model: str = "base"
    language: str = "auto"
    detected_language: str | None = None
    progress: int = 0
    duration_seconds: float | None = None
    segments: list[Segment] | None = None
    error: JobError | None = None


ALLOWED_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-matroska",
}

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}

ALLOWED_MODELS = {"tiny", "base", "small"}
