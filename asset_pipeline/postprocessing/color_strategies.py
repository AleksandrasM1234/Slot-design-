import numpy as np
import cv2
from abc import ABC, abstractmethod


class ColorStrategy(ABC):

    @abstractmethod
    def matches_array(self, rgb: np.ndarray, tolerance: int) -> np.ndarray:
        ...

    @abstractmethod
    def alpha_array(self, rgb: np.ndarray, tolerance: int, soft_margin: int) -> np.ndarray:
        ...


class FixedColorStrategy(ColorStrategy):

    def __init__(self, target_color: tuple[int, int, int]):
        self.target_color = np.array(target_color, dtype=np.int16)

    def _distance(self, rgb: np.ndarray) -> np.ndarray:
        diff = np.abs(rgb.astype(np.int16) - self.target_color)
        return diff.max(axis=-1)

    def matches_array(self, rgb, tolerance):
        return self._distance(rgb) <= tolerance

    def alpha_array(self, rgb, tolerance, soft_margin):
        d = self._distance(rgb).astype(np.float32)
        fraction = np.clip((d - tolerance) / max(soft_margin, 1), 0.0, 1.0)
        return (fraction * 255).astype(np.uint8)


class HueBasedGreenScreenStrategy(ColorStrategy):

    def __init__(self, target_hue_degrees: float = 120.0, min_saturation: float = 0.15):
        self.target_hue = target_hue_degrees / 360.0
        self.min_saturation = min_saturation

    def _hue_diff_and_sat(self, rgb: np.ndarray):
        hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
        h = hsv[:, :, 0] / 179.0
        s = hsv[:, :, 1] / 255.0
        diff = np.abs(h - self.target_hue)
        diff = np.minimum(diff, 1.0 - diff)
        return diff, s

    def matches_array(self, rgb, tolerance):
        hue_diff, s = self._hue_diff_and_sat(rgb)
        return (s >= self.min_saturation) & (hue_diff <= tolerance / 360.0)

    def alpha_array(self, rgb, tolerance, soft_margin):
        hue_diff, s = self._hue_diff_and_sat(rgb)
        tol = tolerance / 360.0
        margin = max(soft_margin, 1) / 360.0
        fraction = np.clip((hue_diff - tol) / margin, 0.0, 1.0)
        alpha = (fraction * 255).astype(np.uint8)
        alpha[s < self.min_saturation] = 255
        return alpha


class GreenResidueStrategy(ColorStrategy):

    def __init__(self, target_hue_degrees: float = 120.0,
                 min_saturation: float = 0.12, min_value: float = 0.25):
        self.target_hue = target_hue_degrees / 360.0
        self.min_saturation = min_saturation
        self.min_value = min_value

    def _hsv(self, rgb: np.ndarray):
        hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
        h = hsv[:, :, 0] / 179.0
        s = hsv[:, :, 1] / 255.0
        v = hsv[:, :, 2] / 255.0
        diff = np.abs(h - self.target_hue)
        diff = np.minimum(diff, 1.0 - diff)
        return diff, s, v

    def matches_array(self, rgb, tolerance):
        hue_diff, s, v = self._hsv(rgb)
        return (s >= self.min_saturation) & (v >= self.min_value) & (hue_diff <= tolerance / 360.0)

    def alpha_array(self, rgb, tolerance, soft_margin):
        hue_diff, s, v = self._hsv(rgb)
        tol = tolerance / 360.0
        margin = max(soft_margin, 1) / 360.0
        fraction = np.clip((hue_diff - tol) / margin, 0.0, 1.0)
        alpha = (fraction * 255).astype(np.uint8)
        alpha[(s < self.min_saturation) | (v < self.min_value)] = 255
        return alpha


def build_color_strategy(chroma_name: str) -> ColorStrategy:
    hue_map = {"green": 120.0, "magenta": 300.0}
    if chroma_name == "white":
        return FixedColorStrategy((255, 255, 255))
    if chroma_name not in hue_map:
        raise ValueError(f"Unknown chroma value: {chroma_name}")
    return HueBasedGreenScreenStrategy(target_hue_degrees=hue_map[chroma_name])