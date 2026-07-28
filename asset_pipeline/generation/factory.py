from asset_pipeline.generation.base import ImageGenerationProvider
from asset_pipeline.generation.leonardo_provider import LeonardoProvider


class GenerationProviderFactory:

    _registry = {
        "leonardo": LeonardoProvider,
    }

    @classmethod
    def create(cls, provider_name: str, **kwargs) -> ImageGenerationProvider:
        try:
            provider_cls = cls._registry[provider_name]
        except KeyError:
            raise ValueError(f"Unknown provider: {provider_name}")
        return provider_cls(**kwargs)

    @classmethod
    def register(cls, name: str, provider_cls: type[ImageGenerationProvider]):
        cls._registry[name] = provider_cls