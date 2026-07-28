from dataclasses import dataclass


@dataclass(frozen=True)
class PostProcessingConfig:
    edge_tolerance: int = 45
    interior_tolerance: int = 32
    soft_edge_margin: int = 18
    feather_radius: float = 1.0
    chroma: str = "green"

    scale_factor: int = 4
    upscale_strategy: str = "lanczos"
    removal_mode: str = "color"
    ml_model: str = "isnet-general-use"

    strict_chroma_hue: float = 120.0
    strict_chroma_tolerance: int = 12
    strict_chroma_min_saturation: float = 0.55
    strict_chroma_min_value: float = 0.25

    residual_chroma_hue: float = 120.0
    residual_chroma_tolerance: int = 30
    residual_chroma_min_saturation: float = 0.28
    residual_chroma_min_value: float = 0.25
    residual_chroma_max_patch_area: int = 1600

    ml_padding: int = 40
    target_frames: int = 30