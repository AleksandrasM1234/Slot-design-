import asyncio
import os
import shutil
import traceback
from asset_pipeline.domain import job
from asset_pipeline.domain.job import AssetJob, JobStatus
from asset_pipeline.domain.theme import Theme, AssetSpec
from asset_pipeline.orchestration.asset_pipeline import AssetGenerationPipeline
from asset_pipeline.orchestration.job_repository import JobRepository
from asset_pipeline.orchestration.job_broadcaster import JobEventBroadcaster


class AssetJobRunner:

    def __init__(self, pipeline: AssetGenerationPipeline,
             repository: JobRepository, broadcaster: JobEventBroadcaster,
             output_dir: str = "data/output"):
        self._pipeline = pipeline
        self._repository = repository
        self._broadcaster = broadcaster
        self._output_dir = output_dir

    async def run(self, job: AssetJob, theme: Theme, asset: AssetSpec) -> None:
        loop = asyncio.get_running_loop()

        async def notify(status_str: str):
            job.status = JobStatus(status_str)
            self._repository.save(job)
            await self._broadcaster.notify(job)

        def on_status(status_str: str):
            asyncio.run_coroutine_threadsafe(notify(status_str), loop)

        try:
            result = await asyncio.to_thread(self._pipeline.produce, theme, asset, on_status)

            raw_paths = []
            processed_paths = []
            for idx, (raw_img, proc_img) in enumerate(zip(result.raw_images, result.processed_images)):
                raw_path = f"{self._output_dir}/{job.id}_raw_{idx}.png"
                raw_img.save(raw_path)
                raw_paths.append(raw_path)

                proc_path = f"{self._output_dir}/{job.id}_{idx}.png"
                proc_img.save(proc_path)
                processed_paths.append(proc_path)

            video_path = None
            if result.video_path:
                video_path = f"{self._output_dir}/{job.id}.mp4"
                shutil.copyfile(result.video_path, video_path)
                os.remove(result.video_path)

            job.status = JobStatus.DONE
            job.result_paths = processed_paths
            job.raw_paths = raw_paths
            job.video_path = video_path
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = str(exc)
            print(f"[job {job.id}] FAILED: {exc}")
            traceback.print_exc()
        finally:
            self._repository.save(job)
            await self._broadcaster.notify(job)