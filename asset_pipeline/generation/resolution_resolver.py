from asset_pipeline.generation.model_catalog import ModelOption


def resolve_generation_size(target_width: int, target_height: int,
                             model: ModelOption) -> tuple[int, int, str]:
    if model.resolution_mode == "enumerated":
        target_ratio = target_width / target_height
        best = min(
            model.valid_resolutions,
            key=lambda entry: abs((entry[0] / entry[1]) - target_ratio),
        )
    return best[0], best[1], best[2]

    width = max(model.min_width, min(target_width, model.max_width))
    height = max(model.min_height, min(target_height, model.max_height))
    width = round(width / model.step) * model.step
    height = round(height / model.step) * model.step
    return width, height, ""