from abc import ABC, abstractmethod
from asset_pipeline.domain.job import AssetJob


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