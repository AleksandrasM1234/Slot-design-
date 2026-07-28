from dataclasses import dataclass, field
from enum import Enum


class AssetCategory(Enum):
    WILD = "wild"
    SCATTER = "scatter"
    LOGO = "logo"
    LOW_TIER = "low_tier"
    HIGH_TIER = "high_tier"
    BACKGROUND = "background"
    BACKGROUND_CHARACTER = "background_character"
    UI_ELEMENT = "ui_element"
    FRAME_ANIMATION = "frame_animation"


class GenerationType(Enum):
    IMAGE = "image"
    ANIMATION = "animation"


@dataclass(frozen=True)
class GenerationSettings:
    generation_type: GenerationType = GenerationType.IMAGE
    width: int = 768
    height: int = 768
    duration_seconds: float | None = None
    num_outputs: int = 1


@dataclass(frozen=True)
class AssetSpec:
    name: str
    category: AssetCategory
    description: str
    style_keywords: tuple[str, ...] = field(default_factory=tuple)
    settings: GenerationSettings = field(default_factory=GenerationSettings)


@dataclass(frozen=True)
class Theme:
    name: str
    art_style: str
    palette: tuple[str, ...]
    assets: tuple[AssetSpec, ...]