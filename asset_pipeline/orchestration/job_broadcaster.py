from collections import defaultdict
from fastapi import WebSocket
from asset_pipeline.domain.job import AssetJob


class JobEventBroadcaster:

    def __init__(self):
        self._subscribers: dict[str, list[WebSocket]] = defaultdict(list)

    def subscribe(self, job_id: str, ws: WebSocket) -> None:
        self._subscribers[job_id].append(ws)

    def unsubscribe(self, job_id: str, ws: WebSocket) -> None:
        self._subscribers[job_id].remove(ws)

    async def notify(self, job: AssetJob) -> None:
        payload = {
            "id": job.id,
            "status": job.status.value,
            "result_paths": job.result_paths,
            "video_path": job.video_path,
            "error": job.error,
        }
        for ws in list(self._subscribers.get(job.id, [])):
            await ws.send_json(payload)