import io
from typing import Callable
import requests
from PIL import Image

from asset_pipeline.domain.theme import Theme, AssetSpec
from asset_pipeline.generation.base import ImageGenerationProvider
from asset_pipeline.generation.prompt_builder import PromptBuilder
from asset_pipeline.postprocessing.frame_pipeline import FramePipeline


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
                on_status: Callable[[str], None] | None = None) -> list[Image.Image]:
        notify = on_status or (lambda _: None)

        notify("generating")
        request = self._prompt_builder.build(theme, asset)
        result = self._provider.generate(request)

        notify("postprocessing")
        images = [self._download(url) for url in result.asset_urls]
        return [self._frame_pipeline.run(image) for image in images]

    def produce_batch(self, theme: Theme) -> dict[str, list[Image.Image]]:
        return {asset.name: self.produce(theme, asset) for asset in theme.assets}

    @staticmethod
    def _download(url: str) -> Image.Image:
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGBA")