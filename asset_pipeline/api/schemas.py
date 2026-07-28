from pydantic import BaseModel


class GenerationSettingsRequest(BaseModel):
    generation_type: str = "image"
    width: int = 768
    height: int = 768
    duration_seconds: float | None = None
    num_outputs: int = 1


class AssetRequest(BaseModel):
    name: str
    category: str
    description: str
    style_keywords: list[str] = []
    settings: GenerationSettingsRequest = GenerationSettingsRequest()


class ThemeRequest(BaseModel):
    name: str
    art_style: str
    palette: list[str]
    assets: list[AssetRequest]


class CreateAssetRequest(BaseModel):
    theme: ThemeRequest
    asset_name: str
    model_id: str


class SaveThemeRequest(BaseModel):
    theme: ThemeRequest