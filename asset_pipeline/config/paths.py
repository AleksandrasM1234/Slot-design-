import os

DATA_DIR = "data"
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
REFERENCE_IMAGES_DIR = os.path.join(DATA_DIR, "reference_images")
CUSTOM_FRAMEWORKS_DIR = os.path.join(DATA_DIR, "custom_frameworks")
THEMES_DIR = os.path.join(DATA_DIR, "themes")


def ensure_data_dirs() -> None:
    for path in (OUTPUT_DIR, REFERENCE_IMAGES_DIR, CUSTOM_FRAMEWORKS_DIR, THEMES_DIR):
        os.makedirs(path, exist_ok=True)