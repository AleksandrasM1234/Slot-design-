import os
import numpy as np
import cv2
from abc import ABC, abstractmethod
from PIL import Image, ImageFilter

from asset_pipeline.postprocessing.color_strategies import (
    ColorStrategy, GreenResidueStrategy, build_color_strategy
)
from asset_pipeline.postprocessing.config import PostProcessingConfig


class BackgroundRemovalStage(ABC):

    @abstractmethod
    def process(self, img: Image.Image) -> Image.Image:
        ...


class ColorKeyRemovalStage(BackgroundRemovalStage):

    def __init__(self, color_strategy: ColorStrategy, edge_tol: int,
                 interior_tol: int, soft_margin: int, feather_radius: float):
        self.color_strategy = color_strategy
        self.edge_tol = edge_tol
        self.interior_tol = interior_tol
        self.soft_margin = soft_margin
        self.feather_radius = feather_radius

    def process(self, img: Image.Image) -> Image.Image:
        arr = np.array(img.convert("RGBA"))
        rgb = arr[:, :, :3]

        mask = self.color_strategy.matches_array(rgb, self.edge_tol).astype(np.uint8)
        num_labels, labels = cv2.connectedComponents(mask, connectivity=4)
        border_labels = set(labels[0, :].tolist()) | set(labels[-1, :].tolist()) \
                       | set(labels[:, 0].tolist()) | set(labels[:, -1].tolist())
        border_labels.discard(0)
        connected_bg = np.isin(labels, list(border_labels)) if border_labels else np.zeros(labels.shape, dtype=bool)

        alpha_candidate = self.color_strategy.alpha_array(rgb, self.edge_tol, self.soft_margin)
        arr[:, :, 3] = np.where(connected_bg, np.minimum(arr[:, :, 3], alpha_candidate), arr[:, :, 3])

        already_transparent = arr[:, :, 3] == 0
        interior_mask = self.color_strategy.matches_array(rgb, self.interior_tol) & ~already_transparent
        alpha_candidate_interior = self.color_strategy.alpha_array(rgb, self.interior_tol, self.soft_margin)
        arr[:, :, 3] = np.where(interior_mask, np.minimum(arr[:, :, 3], alpha_candidate_interior), arr[:, :, 3])

        alpha_channel = arr[:, :, 3]
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        closed_alpha = cv2.morphologyEx(alpha_channel, cv2.MORPH_CLOSE, kernel)
        is_inner_hole = (alpha_channel < 255) & (closed_alpha == 255) & ~connected_bg
        arr[is_inner_hole, 3] = 255

        img = Image.fromarray(arr, mode="RGBA")

        r, g, b, a = img.split()
        a_arr = np.array(a)

        if self.feather_radius <= 0:
            return img

        kernel_size = max(3, int(self.feather_radius // 2) * 2 + 1)
        edge_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        dilated = cv2.dilate(a_arr, edge_kernel, iterations=1)
        eroded = cv2.erode(a_arr, edge_kernel, iterations=1)
        edge_mask = (dilated > 0) & (eroded < 255)

        if not edge_mask.any():
            return img

        img_arr = np.array(img)
        r_chan = img_arr[:, :, 0]
        g_chan = img_arr[:, :, 1]
        b_chan = img_arr[:, :, 2]

        green_spill_mask = edge_mask & (g_chan > r_chan) & (g_chan > b_chan)
        if green_spill_mask.any():
            avg_red_blue = (r_chan.astype(np.uint16) + b_chan.astype(np.uint16)) // 2
            g_chan[green_spill_mask] = np.minimum(
                g_chan[green_spill_mask], avg_red_blue[green_spill_mask]
            ).astype(np.uint8)
            img_arr[:, :, 1] = g_chan
            img = Image.fromarray(img_arr, mode="RGBA")
            r, g, b, a = img.split()

        blurred_alpha = a.filter(ImageFilter.GaussianBlur(radius=self.feather_radius / 3.0))
        blurred_arr = np.array(blurred_alpha)

        edge_pixels = blurred_arr.astype(np.float32)
        edge_pixels = (edge_pixels - 127.5) * 1.4 + 127.5
        edge_pixels = np.clip(edge_pixels, 0, 255).astype(np.uint8)

        a_arr = np.where(edge_mask, edge_pixels, a_arr).astype(np.uint8)
        a = Image.fromarray(a_arr, mode="L")
        return Image.merge("RGBA", (r, g, b, a))


class MLSegmentationRemovalStage(BackgroundRemovalStage):

    def __init__(self, model_name: str):
        try:
            from rembg import new_session, remove
        except ImportError:
            os.system("pip install rembg onnxruntime -q")
            from rembg import new_session, remove
        self._remove = remove
        self.session = new_session(model_name)

    def process(self, img: Image.Image) -> Image.Image:
        rgba = img.convert("RGBA")
        result = self._remove(rgba, session=self.session)
        return result


class ResidualChromaCleanupStage(BackgroundRemovalStage):

    def __init__(self, hue_degrees: float = 120.0, tolerance: int = 40,
                 min_saturation: float = 0.15, min_value: float = 0.25,
                 max_patch_area: int = 1600):
        self.color_strategy = GreenResidueStrategy(
            target_hue_degrees=hue_degrees, min_saturation=min_saturation, min_value=min_value
        )
        self.tolerance = tolerance
        self.max_patch_area = max_patch_area

    def process(self, img: Image.Image) -> Image.Image:
        arr = np.array(img.convert("RGBA"))
        rgb = arr[:, :, :3]
        alpha = arr[:, :, 3]

        suspect = (self.color_strategy.matches_array(rgb, self.tolerance) & (alpha > 0)).astype(np.uint8)
        if not suspect.any():
            return img

        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(suspect, connectivity=8)

        removal_mask = np.zeros(suspect.shape, dtype=bool)
        for label in range(1, num_labels):
            area = stats[label, cv2.CC_STAT_AREA]
            if area <= self.max_patch_area:
                removal_mask |= (labels == label)

        alpha[removal_mask] = 0
        arr[:, :, 3] = alpha
        return Image.fromarray(arr, mode="RGBA")


class StrictChromaPocketStage(BackgroundRemovalStage):

    def __init__(self, hue_degrees: float = 120.0, tolerance: int = 12,
                 min_saturation: float = 0.55, min_value: float = 0.25):
        self.color_strategy = GreenResidueStrategy(
            target_hue_degrees=hue_degrees, min_saturation=min_saturation, min_value=min_value
        )
        self.tolerance = tolerance

    def process(self, img: Image.Image) -> Image.Image:
        arr = np.array(img.convert("RGBA"))
        rgb = arr[:, :, :3]
        alpha = arr[:, :, 3]

        strict_match = self.color_strategy.matches_array(rgb, self.tolerance) & (alpha > 0)
        if not strict_match.any():
            return img

        alpha[strict_match] = 0
        arr[:, :, 3] = alpha
        return Image.fromarray(arr, mode="RGBA")


class PaddedRemovalStage(BackgroundRemovalStage):

    def __init__(self, wrapped: BackgroundRemovalStage, padding: int = 40):
        self.wrapped = wrapped
        self.padding = padding

    def process(self, img: Image.Image) -> Image.Image:
        img = img.convert("RGBA")
        w, h = img.size
        p = self.padding

        padded = Image.new("RGBA", (w + 2 * p, h + 2 * p), (0, 0, 0, 0))
        padded.paste(img, (p, p))

        result = self.wrapped.process(padded)
        return result.crop((p, p, p + w, p + h))


class CompositeRemovalStage(BackgroundRemovalStage):

    def __init__(self, stages: list[BackgroundRemovalStage]):
        self.stages = stages

    def process(self, img: Image.Image) -> Image.Image:
        for stage in self.stages:
            img = stage.process(img)
        return img


class EnclosedHoleFillStage(BackgroundRemovalStage):

    def __init__(self, original_source: Image.Image = None):
        self.original_source = original_source

    def process(self, img: Image.Image) -> Image.Image:
        arr = np.array(img.convert("RGBA"))
        alpha = arr[:, :, 3]

        transparent = (alpha == 0).astype(np.uint8)
        h, w = transparent.shape

        flood_mask = np.zeros((h + 2, w + 2), np.uint8)
        fill_src = transparent.copy()
        cv2.floodFill(fill_src, flood_mask, (0, 0), 2)

        erroneous_holes = (fill_src == 1)
        if not erroneous_holes.any():
            return img

        source_arr = np.array(self.original_source.convert("RGBA")) if self.original_source else arr

        arr[erroneous_holes, :3] = source_arr[erroneous_holes, :3]
        arr[erroneous_holes, 3] = 255
        return Image.fromarray(arr, mode="RGBA")


class HoleFillCompositeStage(BackgroundRemovalStage):

    def __init__(self, ml_stage: BackgroundRemovalStage, cleanup_stages: list[BackgroundRemovalStage]):
        self.ml_stage = ml_stage
        self.cleanup_stages = cleanup_stages

    def process(self, img: Image.Image) -> Image.Image:
        original = img.convert("RGBA")
        result = self.ml_stage.process(original)
        for stage in self.cleanup_stages:
            result = stage.process(result)
        return EnclosedHoleFillStage(original_source=original).process(result)


def build_removal_stage(config: PostProcessingConfig) -> BackgroundRemovalStage:
    if config.removal_mode == "color":
        return ColorKeyRemovalStage(
            build_color_strategy(config.chroma), config.edge_tolerance,
            config.interior_tolerance, config.soft_edge_margin, config.feather_radius,
        )
    if config.removal_mode == "ml":
        ml_stage = MLSegmentationRemovalStage(config.ml_model)
        return PaddedRemovalStage(
            CompositeRemovalStage([
                ml_stage,
                StrictChromaPocketStage(
                    hue_degrees=config.strict_chroma_hue,
                    tolerance=config.strict_chroma_tolerance,
                    min_saturation=config.strict_chroma_min_saturation,
                    min_value=config.strict_chroma_min_value,
                ),
                ResidualChromaCleanupStage(
                    hue_degrees=config.residual_chroma_hue,
                    tolerance=config.residual_chroma_tolerance,
                    min_saturation=config.residual_chroma_min_saturation,
                    min_value=config.residual_chroma_min_value,
                    max_patch_area=config.residual_chroma_max_patch_area,
                ),
            ]),
            padding=config.ml_padding,
        )
    raise ValueError(f"Unknown removal_mode: {config.removal_mode}")