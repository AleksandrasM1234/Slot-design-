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
    enhanced_prompt: str | None = None
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


class EnhancePromptRequest(BaseModel):
    base_prompt: str
    art_style: str
    palette: list[str]
    category: str
    is_animation: bool = False


class EnhancePromptResponse(BaseModel):
    enhanced_prompt: str