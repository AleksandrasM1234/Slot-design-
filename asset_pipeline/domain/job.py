import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "queued"
    GENERATING = "generating"
    POSTPROCESSING = "postprocessing"
    DONE = "done"
    FAILED = "failed"


@dataclass
class AssetJob:
    asset_name: str
    theme_name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.QUEUED
    result_paths: list[str] = field(default_factory=list)
    raw_paths: list[str] = field(default_factory=list)
    video_path: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    cost_usd: float | None = None