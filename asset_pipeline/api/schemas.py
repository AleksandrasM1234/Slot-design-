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
    reference_strength: str = "Mid"
    chroma_color: str = "green"
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
    role_constant: str | None = None
    has_reference_image: bool = False

class EnhanceMasterPromptRequest(BaseModel):
    base_prompt: str
    art_style: str
    palette: list[str]

class EnhancePromptResponse(BaseModel):
    enhanced_prompt: str
    chroma_color: str = "green"


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

class ReprocessRequest(BaseModel):
    index: int = 0
    commit: bool = False
    edge_tolerance: int = 45
    interior_tolerance: int = 32
    soft_edge_margin: int = 18
    feather_radius: float = 1.0
    chroma: str = "green"
    removal_mode: str = "color"
    ml_model: str = "isnet-general-use"
    upscale_strategy: str = "lanczos"
    scale_factor: int = 4