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
    valid_resolutions: tuple[tuple[int, int, str, str], ...] = ()
    min_width: int = 256
    min_height: int = 256
    max_width: int = 1536
    max_height: int = 1536
    step: int = 1
    min_duration: float | None = None
    max_duration: float | None = None


IMAGE_MODELS = (
    ModelOption(
        "Nano Banana 2", "nano-banana-2", "leonardo", GenerationType.IMAGE,
        api_version="v2", resolution_mode="enumerated",
        valid_resolutions=(
            (1024, 1024, "", "1:1"),
            (848, 1264, "", "2:3"),
            (1264, 848, "", "3:2"),
            (896, 1200, "", "3:4"),
            (1200, 896, "", "4:3"),
            (928, 1152, "", "4:5"),
            (1152, 928, "", "5:4"),
            (768, 1376, "", "9:16"),
            (1376, 768, "", "16:9"),
            (1584, 672, "", "21:9"),
        ),
    ),
    ModelOption(
        "FLUX.2 Pro", "flux-pro-2.0", "leonardo", GenerationType.IMAGE,
        api_version="v2", resolution_mode="enumerated",
        valid_resolutions=(
            (960, 1440, "", "2:3"),
            (1440, 1440, "", "1:1"),
            (1440, 810, "", "16:9"),
            (810, 1440, "", "9:16"),
        ),
    ),
    ModelOption(
        "GPT Image 2", "gpt-image-2", "leonardo", GenerationType.IMAGE,
        api_version="v2", resolution_mode="enumerated",
        valid_resolutions=(
            (1024, 1024, "", "1:1"),
            (848, 1264, "", "2:3"),
            (1264, 848, "", "3:2"),
            (1376, 768, "", "16:9"),
            (768, 1376, "", "9:16"),
        ),
    ),
    ModelOption(
        "FLUX Dev", "b2614463-296c-462a-9586-aafdb8f00e36", "leonardo", GenerationType.IMAGE,
        api_version="v1", resolution_mode="continuous",
        min_width=480, min_height=480, max_width=2048, max_height=2048, step=8,
    ),
)

ANIMATION_MODELS = (
    ModelOption(
        "Kling 3.0", "kling-3.0", "leonardo", GenerationType.ANIMATION,
        api_version="v2", resolution_mode="enumerated",
        valid_resolutions=(
            (1280, 720, "RESOLUTION_720", "16:9 (720p)"),
            (960, 960, "RESOLUTION_720", "1:1 (720p)"),
            (720, 1280, "RESOLUTION_720", "9:16 (720p)"),
            (1920, 1080, "RESOLUTION_1080", "16:9 (1080p)"),
            (1440, 1440, "RESOLUTION_1080", "1:1 (1080p)"),
            (1080, 1920, "RESOLUTION_1080", "9:16 (1080p)"),
        ),
        min_duration=3, max_duration=15,
    ),
    ModelOption(
        "Wan 2.7", "wan-2.7", "leonardo", GenerationType.ANIMATION,
        api_version="v2", resolution_mode="enumerated",
        valid_resolutions=(
            (1280, 720, "RESOLUTION_720", "16:9 (720p)"),
            (960, 960, "RESOLUTION_720", "1:1 (720p)"),
            (720, 1280, "RESOLUTION_720", "9:16 (720p)"),
            (1920, 1080, "RESOLUTION_1080", "16:9 (1080p)"),
            (1440, 1440, "RESOLUTION_1080", "1:1 (1080p)"),
            (1080, 1920, "RESOLUTION_1080", "9:16 (1080p)"),
        ),
        min_duration=2, max_duration=10,
    ),
    ModelOption(
        "Seedance 2.0 (resolution unverified)", "seedance-2-0", "leonardo", GenerationType.ANIMATION,
        api_version="v2", resolution_mode="continuous",
        min_width=512, min_height=512, max_width=1920, max_height=1920,
        min_duration=4, max_duration=15,
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