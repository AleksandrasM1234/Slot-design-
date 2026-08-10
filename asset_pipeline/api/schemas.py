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
    role_constant: str | None = None
    reference_image_path: str | None = None
    settings: GenerationSettingsRequest = GenerationSettingsRequest()


class ThemeRequest(BaseModel):
    name: str
    art_style: str
    palette: list[str]
    assets: list[AssetRequest]
    master_prompt: str = ""
    master_prompt_enhanced: str | None = None


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
    master_context: str | None = None

class EnhanceMasterPromptRequest(BaseModel):
    base_prompt: str
    art_style: str
    palette: list[str]

class EnhancePromptResponse(BaseModel):
    enhanced_prompt: str


class SaveFrameworkRequest(BaseModel):
    key: str
    display_name: str
    description: str = ""
    blueprint_keys: list[str]

class GenerateFromWorldRequest(BaseModel):
    role_display_name: str
    category: str
    is_animation: bool = False
    art_style: str
    palette: list[str]
    master_context: str

class ExportZipRequest(BaseModel):
    job_ids: list[str]