from dataclasses import dataclass
from asset_pipeline.domain.theme import GenerationType


@dataclass(frozen=True)
class ModelOption:
    display_name: str
    model_id: str
    provider: str
    generation_type: GenerationType


IMAGE_MODELS = (
    ModelOption("Flux", "flux-dev", "leonardo", GenerationType.IMAGE),
    ModelOption("GPT Image 2", "gpt-image-2", "leonardo", GenerationType.IMAGE),
    ModelOption("Nano Banana 2", "nano-banana-2", "leonardo", GenerationType.IMAGE),
)

ANIMATION_MODELS = (
    ModelOption("Kling 3", "kling-v3", "leonardo", GenerationType.ANIMATION),
    ModelOption("Hailuo 2.3", "hailuo-2-3", "leonardo", GenerationType.ANIMATION),
    ModelOption("Seedance 2", "seedance-2", "leonardo", GenerationType.ANIMATION),
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