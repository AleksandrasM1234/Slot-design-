import os
import shutil
import zipfile
import numpy as np
import cv2
from abc import ABC, abstractmethod
from PIL import Image


class InputHandler(ABC):

    @abstractmethod
    def can_handle(self, filenames: list[str]) -> bool:
        ...

    @abstractmethod
    def extract_frames(self, filenames: list[str], out_dir: str, target_frames: int) -> None:
        ...


class ZipInputHandler(InputHandler):

    def can_handle(self, filenames: list[str]) -> bool:
        return any(f.endswith(".zip") for f in filenames)

    def extract_frames(self, filenames: list[str], out_dir: str, target_frames: int) -> None:
        zip_name = next(f for f in filenames if f.endswith(".zip"))
        os.makedirs("input", exist_ok=True)
        with zipfile.ZipFile(zip_name, "r") as z:
            z.extractall("input")

        mp4_files = [
            os.path.join(root, f)
            for root, dirs, files_list in os.walk("input")
            for f in files_list
            if (f.endswith(".mp4") or f.endswith(".mov"))
            and not f.startswith(".") and "__MACOSX" not in root
        ]

        if mp4_files:
            for mp4_path in mp4_files:
                extract_frames_from_video(mp4_path, out_dir, target_frames)
        else:
            collect_png_frames("input", out_dir, target_frames)


class VideoInputHandler(InputHandler):

    def can_handle(self, filenames: list[str]) -> bool:
        return any(f.endswith(".mp4") or f.endswith(".mov") for f in filenames)

    def extract_frames(self, filenames: list[str], out_dir: str, target_frames: int) -> None:
        video_files = [f for f in filenames if f.endswith(".mp4") or f.endswith(".mov")]
        for video_path in video_files:
            extract_frames_from_video(video_path, out_dir, target_frames)


class ImageInputHandler(InputHandler):

    def can_handle(self, filenames: list[str]) -> bool:
        return any(f.endswith(".png") for f in filenames)

    def extract_frames(self, filenames: list[str], out_dir: str, target_frames: int) -> None:
        png_files = sorted(f for f in filenames if f.endswith(".png"))
        count = min(target_frames, len(png_files))
        indices = np.linspace(0, len(png_files) - 1, count, dtype=int)
        for out_idx, frame_idx in enumerate(indices):
            shutil.copy(png_files[frame_idx], os.path.join(out_dir, f"frame_{out_idx:04d}.png"))


class InputResolver:

    def __init__(self, handlers: list[InputHandler]):
        self.handlers = handlers

    def resolve(self, filenames: list[str]) -> InputHandler:
        for handler in self.handlers:
            if handler.can_handle(filenames):
                return handler
        raise ValueError(
            "Could not recognize the uploaded file type. Supported: .zip, .mp4/.mov, .png"
        )


def extract_frames_from_video(mp4_path: str, out_dir: str, target_frames: int):
    cap = cv2.VideoCapture(mp4_path)

    reported_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if reported_total <= 1:
        actual_total = 0
        while True:
            ret, _ = cap.read()
            if not ret:
                break
            actual_total += 1
        cap.release()
        cap = cv2.VideoCapture(mp4_path)
        total_frames = actual_total
    else:
        total_frames = reported_total

    if total_frames <= 0:
        print(f"Could not determine frame count for file {mp4_path}")
        cap.release()
        return

    wanted_indices = set(np.linspace(0, total_frames - 1, min(target_frames, total_frames), dtype=int).tolist())

    frame_idx = 0
    out_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx in wanted_indices:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb).convert("RGBA")
            pil_img.save(os.path.join(out_dir, f"frame_{out_idx:04d}.png"))
            out_idx += 1
        frame_idx += 1

    cap.release()
    print(f"{mp4_path}: {frame_idx} frames read, {out_idx} saved")


def collect_png_frames(input_dir: str, out_dir: str, target_frames: int):
    all_pngs = sorted([
        os.path.join(root, f)
        for root, dirs, files_list in os.walk(input_dir)
        for f in files_list
        if f.endswith(".png") and not f.startswith(".") and "__MACOSX" not in root
    ])
    indices = np.linspace(0, len(all_pngs) - 1, target_frames, dtype=int)
    for out_idx, frame_idx in enumerate(indices):
        shutil.copy(all_pngs[frame_idx], os.path.join(out_dir, f"frame_{out_idx:04d}.png"))