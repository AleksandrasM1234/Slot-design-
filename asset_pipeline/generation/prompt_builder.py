from abc import ABC, abstractmethod
from asset_pipeline.domain.theme import Theme, AssetSpec
from asset_pipeline.generation.base import GenerationRequest


class PromptBuilder(ABC):

    @abstractmethod
    def build(self, theme: Theme, asset: AssetSpec) -> GenerationRequest:
        ...


class LeonardoPromptBuilder(PromptBuilder):

    def build(self, theme: Theme, asset: AssetSpec) -> GenerationRequest:
        base = asset.enhanced_prompt if asset.enhanced_prompt else self._assemble_prompt(theme, asset)
        prompt = f"{asset.role_constant} {base}" if asset.role_constant else base
        negative = "blurry, watermark, text, extra limbs, cropped"

        return GenerationRequest(
            prompt=prompt,
            generation_type=asset.settings.generation_type,
            negative_prompt=negative,
            width=asset.settings.width,
            height=asset.settings.height,
            duration_seconds=asset.settings.duration_seconds,
            num_outputs=asset.settings.num_outputs,
            reference_image_path=asset.reference_image_path,
            reference_strength=asset.reference_strength,
        )

    @staticmethod
    def _assemble_prompt(theme: Theme, asset: AssetSpec) -> str:
        style = ", ".join(theme.palette)
        keywords = ", ".join(asset.style_keywords)
        return (
            f"{asset.description}, {theme.art_style}, "
            f"color palette: {style}, {keywords}, "
            f"solid flat background, centered composition, "
            f"game asset, high detail, studio lighting"
        )