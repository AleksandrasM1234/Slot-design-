import asyncio
from asset_pipeline.domain.job import AssetJob, JobStatus
from asset_pipeline.domain.theme import Theme, AssetSpec
from asset_pipeline.orchestration.asset_pipeline import AssetGenerationPipeline
from asset_pipeline.orchestration.job_repository import JobRepository
from asset_pipeline.orchestration.job_broadcaster import JobEventBroadcaster


class AssetJobRunner:

    def __init__(self, pipeline: AssetGenerationPipeline,
                 repository: JobRepository, broadcaster: JobEventBroadcaster,
                 output_dir: str = "output"):
        self._pipeline = pipeline
        self._repository = repository
        self._broadcaster = broadcaster
        self._output_dir = output_dir

    async def run(self, job: AssetJob, theme: Theme, asset: AssetSpec) -> None:
        async def notify(status_str: str):
            job.status = JobStatus(status_str)
            self._repository.save(job)
            await self._broadcaster.notify(job)

        try:
            def on_status(status_str: str):
                asyncio.create_task(notify(status_str))

            images = await asyncio.to_thread(
                self._pipeline.produce, theme, asset, on_status
            )

            paths = []
            for idx, image in enumerate(images):
                path = f"{self._output_dir}/{job.id}_{idx}.png"
                image.save(path)
                paths.append(path)

            job.status = JobStatus.DONE
            job.result_paths = paths
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = str(exc)
        finally:
            self._repository.save(job)
            await self._broadcaster.notify(job)