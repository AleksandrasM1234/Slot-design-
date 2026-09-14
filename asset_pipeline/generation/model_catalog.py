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
    reference_cost_usd: float | None = None
    reference_note: str | None = None
    reference_width: int | None = None
    reference_height: int | None = None
    reference_duration: float | None = None


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
        reference_cost_usd=0.04, reference_note="1:1 1024×1024",
        reference_width=1024, reference_height=1024,
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
        reference_cost_usd=0.08, reference_note="1:1 1440×1440",
        reference_width=1440, reference_height=1440,
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
        reference_cost_usd=0.10, reference_note="1:1/16:9 ~1024–1376px, Medium quality",
        reference_width=1024, reference_height=1024,
    ),
    ModelOption(
        "FLUX Dev", "b2614463-296c-462a-9586-aafdb8f00e36", "leonardo", GenerationType.IMAGE,
        api_version="v1", resolution_mode="continuous",
        min_width=480, min_height=480, max_width=2048, max_height=2048, step=8,
        reference_cost_usd=0.01, reference_note="~900–1400px range",
        reference_width=1000, reference_height=1000,
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
        reference_cost_usd=0.58, reference_note="960×960 or 1280×720 HD, 3s",
        reference_width=960, reference_height=960, reference_duration=3,
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
        reference_cost_usd=0.10, reference_note="960×960 or 1280×720 HD, 2s",
        reference_width=960, reference_height=960, reference_duration=2,
    ),
    ModelOption(
        "Seedance 2.0 (resolution unverified)", "seedance-2-0", "leonardo", GenerationType.ANIMATION,
        api_version="v2", resolution_mode="continuous",
        min_width=512, min_height=512, max_width=1920, max_height=1920,
        min_duration=4, max_duration=15,
        reference_cost_usd=1.81, reference_note="960×960 or 1280×720 HD, 4s",
        reference_width=960, reference_height=960, reference_duration=4,
    ),
)

SOUND_MODELS = (
    ModelOption(
        "Sound Effects v2", "sound-effects-v2", "leonardo", GenerationType.SOUND,
        api_version="v2", resolution_mode="none",
        min_duration=1, max_duration=22,
        reference_cost_usd=None,  # unverified — check Leonardo's pricing calculator
        reference_note="Cost not yet confirmed",
    ),
)

def all_models() -> tuple[ModelOption, ...]:
    return IMAGE_MODELS + ANIMATION_MODELS + SOUND_MODELS


def models_for_type(generation_type: GenerationType) -> tuple[ModelOption, ...]:
    return tuple(m for m in all_models() if m.generation_type == generation_type)


def find_model(model_id: str) -> ModelOption:
    for m in all_models():
        if m.model_id == model_id:
            return m
    raise ValueError(f"Unknown model id: {model_id}")

def estimate_cost(model: ModelOption, width: int, height: int,
                   duration: float | None = None) -> float | None:
    if model.reference_cost_usd is None or not model.reference_width or not model.reference_height:
        return None

    area_ratio = (width * height) / (model.reference_width * model.reference_height)
    cost = model.reference_cost_usd * area_ratio

    if model.reference_duration and duration:
        cost *= duration / model.reference_duration

    return round(cost, 4)