import os
import numpy as np
from abc import ABC, abstractmethod
from PIL import Image, ImageFilter


class UpscaleStrategy(ABC):

    @abstractmethod
    def upscale(self, image: Image.Image, scale_factor: int) -> Image.Image:
        ...


class LanczosUpscaleStrategy(UpscaleStrategy):

    def upscale(self, image, scale_factor):
        w, h = image.size
        return image.resize((w * scale_factor, h * scale_factor), Image.LANCZOS)


class LanczosWithEdgeSmoothingStrategy(UpscaleStrategy):

    def __init__(self, smoothing_radius: float = 1.5):
        self.smoothing_radius = smoothing_radius

    def upscale(self, image, scale_factor):
        w, h = image.size
        upscaled = image.resize((w * scale_factor, h * scale_factor), Image.LANCZOS)
        if upscaled.mode != "RGBA":
            upscaled = upscaled.convert("RGBA")
        r, g, b, a = upscaled.split()
        a = a.filter(ImageFilter.GaussianBlur(radius=self.smoothing_radius))
        r = r.filter(ImageFilter.GaussianBlur(radius=self.smoothing_radius * 0.5))
        g = g.filter(ImageFilter.GaussianBlur(radius=self.smoothing_radius * 0.5))
        b = b.filter(ImageFilter.GaussianBlur(radius=self.smoothing_radius * 0.5))
        return Image.merge("RGBA", (r, g, b, a))


class RealESRGANUpscaleStrategy(UpscaleStrategy):

    def __init__(self):
        try:
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet
        except ImportError:
            os.system("pip install realesrgan basicsr -q")
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet

        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                         num_block=23, num_grow_ch=32, scale=4)
        self.upsampler = RealESRGANer(
            scale=4,
            model_path="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
            model=model, tile=0, half=True,
        )

    def upscale(self, image, scale_factor):
        rgb_image = image.convert("RGB")
        alpha = image.split()[3] if image.mode == "RGBA" else None
        img_array = np.array(rgb_image)
        output, _ = self.upsampler.enhance(img_array, outscale=scale_factor)
        result = Image.fromarray(output).convert("RGBA")
        if alpha is not None:
            w, h = result.size
            alpha_resized = alpha.resize((w, h), Image.LANCZOS)
            result.putalpha(alpha_resized)
        return result


def build_upscale_strategy(strategy_name: str) -> UpscaleStrategy:
    strategies = {
        "lanczos": LanczosUpscaleStrategy,
        "lanczos_smooth": LanczosWithEdgeSmoothingStrategy,
        "realesrgan": RealESRGANUpscaleStrategy,
    }
    if strategy_name not in strategies:
        raise ValueError(f"Unknown upscale_strategy: {strategy_name}")
    return strategies[strategy_name]()