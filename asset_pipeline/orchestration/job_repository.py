import json
from abc import ABC, abstractmethod
from pathlib import Path
from asset_pipeline.domain.job import AssetJob, JobStatus


class JobRepository(ABC):

    @abstractmethod
    def save(self, job: AssetJob) -> None: ...

    @abstractmethod
    def get(self, job_id: str) -> AssetJob | None: ...

    @abstractmethod
    def list_all(self) -> list[AssetJob]: ...


class InMemoryJobRepository(JobRepository):

    def __init__(self):
        self._jobs: dict[str, AssetJob] = {}

    def save(self, job: AssetJob) -> None:
        self._jobs[job.id] = job

    def get(self, job_id: str) -> AssetJob | None:
        return self._jobs.get(job_id)

    def list_all(self) -> list[AssetJob]:
        return list(self._jobs.values())


class JsonFileJobRepository(JobRepository):

    def __init__(self, directory: str = "data/jobs"):
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, job_id: str) -> Path:
        return self._directory / f"{job_id}.json"

    def save(self, job: AssetJob) -> None:
        data = {
            "id": job.id,
            "asset_name": job.asset_name,
            "theme_name": job.theme_name,
            "status": job.status.value,
            "result_paths": job.result_paths,
            "raw_paths": job.raw_paths,
            "video_path": job.video_path,
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "cost_usd": job.cost_usd,
        }
        self._path_for(job.id).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get(self, job_id: str) -> AssetJob | None:
        path = self._path_for(job_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        job = AssetJob(asset_name=data["asset_name"], theme_name=data["theme_name"])
        job.id = data["id"]
        job.status = JobStatus(data["status"])
        job.result_paths = data["result_paths"]
        job.raw_paths = data.get("raw_paths", [])
        job.video_path = data.get("video_path")
        job.error = data.get("error")
        job.cost_usd = data.get("cost_usd")
        return job

    def list_all(self) -> list[AssetJob]:
        jobs = []
        for path in self._directory.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            job = AssetJob(asset_name=data["asset_name"], theme_name=data["theme_name"])
            job.id = data["id"]
            job.status = JobStatus(data["status"])
            job.result_paths = data["result_paths"]
            job.raw_paths = data.get("raw_paths", [])
            job.video_path = data.get("video_path")
            job.error = data.get("error")
            job.cost_usd = data.get("cost_usd")
            jobs.append(job)
        return jobs