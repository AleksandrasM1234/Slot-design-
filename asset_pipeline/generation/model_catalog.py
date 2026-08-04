from dataclasses import dataclass
from asset_pipeline.domain.theme import GenerationType


@dataclass(frozen=True)
class ModelOption:
    display_name: str
    model_id: str
    provider: str
    generation_type: GenerationType
    api_version: str = "v1"
    resolution_mode: str = "continuous"
    valid_resolutions: tuple[tuple[int, int], ...] = ()
    min_width: int = 256
    min_height: int = 256
    max_width: int = 1536
    max_height: int = 1536
    video_mode: str | None = None


IMAGE_MODELS = (
    ModelOption(
        "Nano Banana 2", "nano-banana-2", "leonardo", GenerationType.IMAGE,
        api_version="v2", resolution_mode="enumerated",
        valid_resolutions=(
            (1024, 1024), (848, 1264), (1264, 848), (896, 1200), (1200, 896),
            (928, 1152), (1152, 928), (768, 1376), (1376, 768), (1584, 672),
        ),
    ),
    ModelOption(
        "FLUX.2 Pro", "flux-pro-2.0", "leonardo", GenerationType.IMAGE,
        api_version="v2", resolution_mode="continuous",
        min_width=256, min_height=256, max_width=1440, max_height=1440,
    ),
    ModelOption(
        "FLUX Dev", "b2614463-296c-462a-9586-aafdb8f00e36", "leonardo", GenerationType.IMAGE,
        api_version="v1", resolution_mode="continuous",
        min_width=512, min_height=512, max_width=1536, max_height=1536,
    ),
    ModelOption(
        "GPT Image 2 (unverified)", "gpt-image-2", "leonardo", GenerationType.IMAGE,
        api_version="v2", resolution_mode="continuous",
        min_width=512, min_height=512, max_width=1536, max_height=1536,
    ),
)

ANIMATION_MODELS = (
    ModelOption(
        "Kling 3.0", "kling-3.0", "leonardo", GenerationType.ANIMATION,
        api_version="v2", resolution_mode="enumerated", video_mode="RESOLUTION_720",
        valid_resolutions=((1280, 720), (960, 960), (720, 1280)),
    ),
    ModelOption(
        "Hailuo 2.3 (unverified)", "hailuo-2-3", "leonardo", GenerationType.ANIMATION,
        api_version="v2", resolution_mode="continuous",
        min_width=512, min_height=512, max_width=1920, max_height=1920,
    ),
    ModelOption(
        "Seedance 2.0 (unverified)", "seedance-2-0", "leonardo", GenerationType.ANIMATION,
        api_version="v2", resolution_mode="continuous",
        min_width=512, min_height=512, max_width=1920, max_height=1920,
    ),
)


def all_models() -> tuple[ModelOption, ...]:
    return IMAGE_MODELS + ANIMATION_MODELS


def models_for_type(generation_type: GenerationType) -> tuple[ModelOption, ...]:
    return tuple(m for m in all_models() if m.generation_type == generation_type)


def find_model(model_id: str) -> ModelOption:
    for m in all_models():
        if m.model_id == model_id:
            return m
    raise ValueError(f"Unknown model id: {model_id}")