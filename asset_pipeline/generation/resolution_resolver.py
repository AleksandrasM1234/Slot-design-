from asset_pipeline.generation.model_catalog import ModelOption


def resolve_generation_size(target_width: int, target_height: int, model: ModelOption) -> tuple[int, int]:
    if model.resolution_mode == "enumerated":
        target_ratio = target_width / target_height
        return min(
            model.valid_resolutions,
            key=lambda pair: abs((pair[0] / pair[1]) - target_ratio),
        )

    width = max(model.min_width, min(target_width, model.max_width))
    height = max(model.min_height, min(target_height, model.max_height))
    return width, height