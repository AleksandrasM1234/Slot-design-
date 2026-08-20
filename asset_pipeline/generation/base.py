from abc import ABC, abstractmethod
from dataclasses import dataclass
from asset_pipeline.domain.theme import GenerationType


@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    generation_type: GenerationType = GenerationType.IMAGE
    width: int = 768
    height: int = 768
    negative_prompt: str | None = None
    duration_seconds: float | None = None
    num_outputs: int = 1
    reference_image_path: str | None = None
    reference_strength: str = "Mid"


@dataclass(frozen=True)
class GenerationResult:
    asset_urls: tuple[str, ...]
    provider_name: str
    raw_response: dict
    is_video: bool = False
    cost_usd: float | None = None


class ImageGenerationProvider(ABC):

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        ...