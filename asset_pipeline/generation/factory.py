from asset_pipeline.generation.base import ImageGenerationProvider
from asset_pipeline.generation.leonardo_provider import LeonardoProvider
from asset_pipeline.generation.model_catalog import ModelOption


class GenerationProviderFactory:

    _registry = {
        "leonardo": LeonardoProvider,
    }

    @classmethod
    def create(cls, provider_name: str, api_key: str, model: ModelOption) -> ImageGenerationProvider:
        try:
            provider_cls = cls._registry[provider_name]
        except KeyError:
            raise ValueError(f"Unknown provider: {provider_name}")
        return provider_cls(api_key=api_key, model=model)

    @classmethod
    def register(cls, name: str, provider_cls: type[ImageGenerationProvider]):
        cls._registry[name] = provider_cls