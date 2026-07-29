from asset_pipeline.domain.theme import (
    Theme, AssetSpec, AssetCategory, GenerationSettings, GenerationType
)


def theme_to_dict(theme: Theme) -> dict:
    return {
        "name": theme.name,
        "art_style": theme.art_style,
        "palette": list(theme.palette),
        "assets": [
            {
                "name": a.name,
                "category": a.category.value,
                "description": a.description,
                "style_keywords": list(a.style_keywords),
                "enhanced_prompt": a.enhanced_prompt,
                "role_constant": a.role_constant,
                "reference_image_path": a.reference_image_path,
                "settings": {
                    "generation_type": a.settings.generation_type.value,
                    "width": a.settings.width,
                    "height": a.settings.height,
                    "duration_seconds": a.settings.duration_seconds,
                    "num_outputs": a.settings.num_outputs,
                },
            }
            for a in theme.assets
        ],
    }


def theme_from_dict(data: dict) -> Theme:
    assets = tuple(
        AssetSpec(
            name=a["name"],
            category=AssetCategory(a["category"]),
            description=a["description"],
            style_keywords=tuple(a.get("style_keywords", [])),
            enhanced_prompt=a.get("enhanced_prompt"),
            role_constant=a.get("role_constant"),
            reference_image_path=a.get("reference_image_path"),
            settings=GenerationSettings(
                generation_type=GenerationType(a["settings"]["generation_type"]),
                width=a["settings"]["width"],
                height=a["settings"]["height"],
                duration_seconds=a["settings"].get("duration_seconds"),
                num_outputs=a["settings"].get("num_outputs", 1),
            ),
        )
        for a in data["assets"]
    )
    return Theme(
        name=data["name"],
        art_style=data["art_style"],
        palette=tuple(data["palette"]),
        assets=assets,
    )