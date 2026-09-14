import io
import tempfile
from dataclasses import dataclass
from typing import Callable
from unittest import result
import requests
import cv2
import numpy as np
from PIL import Image

from asset_pipeline.domain.theme import Theme, AssetSpec, GenerationType
from asset_pipeline.generation.base import ImageGenerationProvider
from asset_pipeline.generation.prompt_builder import PromptBuilder
from asset_pipeline.postprocessing.frame_pipeline import FramePipeline


@dataclass
class ProductionResult:
    video_path: str | None
    raw_images: list[Image.Image]
    processed_images: list[Image.Image]
    cost_usd: float | None = None
    audio_url: str | None = None


class AssetGenerationPipeline:

    def __init__(
        self,
        prompt_builder: PromptBuilder,
        provider: ImageGenerationProvider,
        frame_pipeline: FramePipeline,
    ):
        self._prompt_builder = prompt_builder
        self._provider = provider
        self._frame_pipeline = frame_pipeline

    def produce(self, theme: Theme, asset: AssetSpec,
                on_status: Callable[[str], None] | None = None) -> ProductionResult:
        notify = on_status or (lambda _: None)

        notify("generating")
        request = self._prompt_builder.build(theme, asset)
        result = self._provider.generate(request)

        notify("postprocessing")

        notify("postprocessing")

        if asset.settings.generation_type == GenerationType.SOUND:
            return ProductionResult(
                video_path=None, raw_images=[], processed_images=[],
                cost_usd=result.cost_usd, audio_url=result.asset_urls[0],
            )

        if result.is_video:
            video_path, raw_frames = self._download_and_extract_frames(result.asset_urls[0])
            processed = [self._frame_pipeline.run(f) for f in raw_frames]
            return ProductionResult(
                video_path=video_path, raw_images=raw_frames, processed_images=processed,
                cost_usd=result.cost_usd,
            )

        raw_images = [self._download(url) for url in result.asset_urls]
        processed = [self._frame_pipeline.run(img) for img in raw_images]
        return ProductionResult(
            video_path=None, raw_images=raw_images, processed_images=processed,
            cost_usd=result.cost_usd,
        )

    @staticmethod
    def _download(url: str) -> Image.Image:
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGBA")

    @staticmethod
    def _download_and_extract_frames(video_url: str, target_frames: int = 30):
        response = requests.get(video_url, stream=True)
        response.raise_for_status()

        tmp_video = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        with open(tmp_video.name, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        cap = cv2.VideoCapture(tmp_video.name)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            total = 1
        wanted = set(np.linspace(0, max(total - 1, 0), min(target_frames, max(total, 1)), dtype=int).tolist())

        frames = []
        idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if idx in wanted:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(Image.fromarray(rgb).convert("RGBA"))
            idx += 1
        cap.release()

        return tmp_video.name, frames