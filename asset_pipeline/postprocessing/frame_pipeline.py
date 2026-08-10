from abc import ABC, abstractmethod
from PIL import Image

from asset_pipeline.postprocessing.config import PostProcessingConfig
from asset_pipeline.postprocessing.background_removal import BackgroundRemovalStage, build_removal_stage
from asset_pipeline.postprocessing.upscaling import UpscaleStrategy, build_upscale_strategy


class FrameStage(ABC):

    @abstractmethod
    def execute(self, image: Image.Image) -> Image.Image:
        ...


class RemovalStageAdapter(FrameStage):

    def __init__(self, stage: BackgroundRemovalStage):
        self.stage = stage

    def execute(self, image: Image.Image) -> Image.Image:
        return self.stage.process(image.convert("RGBA"))


class UpscaleStageAdapter(FrameStage):

    def __init__(self, strategy: UpscaleStrategy, scale_factor: int):
        self.strategy = strategy
        self.scale_factor = scale_factor

    def execute(self, image: Image.Image) -> Image.Image:
        return self.strategy.upscale(image.convert("RGBA"), self.scale_factor)


class FinalResizeStage(FrameStage):

    def __init__(self, target_width: int, target_height: int):
        self.target_width = target_width
        self.target_height = target_height

    def execute(self, image: Image.Image) -> Image.Image:
        return image.resize((self.target_width, self.target_height), Image.LANCZOS)


class FramePipeline:

    def __init__(self, stages: list[FrameStage]):
        self.stages = stages

    def run(self, image: Image.Image) -> Image.Image:
        img = image
        for stage in self.stages:
            img = stage.execute(img)
        return img


def build_frame_pipeline(config: PostProcessingConfig,
                          target_width: int, target_height: int) -> FramePipeline:
    removal_stage = build_removal_stage(config)
    upscale_strategy = build_upscale_strategy(config.upscale_strategy)

    if config.removal_mode == "color":
        stages = [
            UpscaleStageAdapter(upscale_strategy, config.scale_factor),
            RemovalStageAdapter(removal_stage),
        ]
    elif config.removal_mode == "ml":
        stages = [
            RemovalStageAdapter(removal_stage),
            UpscaleStageAdapter(upscale_strategy, config.scale_factor),
        ]
    else:
        raise ValueError(f"Unknown removal_mode: {config.removal_mode}")

    stages.append(FinalResizeStage(target_width, target_height))
    return FramePipeline(stages)