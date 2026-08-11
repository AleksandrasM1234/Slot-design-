from asset_pipeline.domain.theme import (
    Theme, AssetSpec, AssetCategory, GenerationSettings, GenerationType
)


def theme_from_request(theme_request) -> Theme:
    assets = tuple(
        AssetSpec(
            name=a.name,
            category=AssetCategory(a.category),
            description=a.description,
            style_keywords=tuple(a.style_keywords),
            enhanced_prompt=a.enhanced_prompt,
            role_constant=a.role_constant,
            reference_image_path=a.reference_image_path,
            reference_strength=getattr(a, "reference_strength", "Mid"),
            settings=GenerationSettings(
                generation_type=GenerationType(a.settings.generation_type),
                width=a.settings.width,
                height=a.settings.height,
                duration_seconds=a.settings.duration_seconds,
                num_outputs=a.settings.num_outputs,
            ),

        )
        for a in theme_request.assets
    )
    return Theme(
        name=theme_request.name,
        art_style=theme_request.art_style,
        palette=tuple(theme_request.palette),
        assets=assets,
        master_prompt=theme_request.master_prompt,
        master_prompt_enhanced=theme_request.master_prompt_enhanced,
    )