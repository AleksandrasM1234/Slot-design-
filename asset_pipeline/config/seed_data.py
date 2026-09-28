import shutil
from pathlib import Path

from asset_pipeline.config.paths import CUSTOM_FRAMEWORKS_DIR, THEMES_DIR

SEED_DIR = Path("seed_data")

SEED_TARGETS = {
    "custom_frameworks": Path(CUSTOM_FRAMEWORKS_DIR),
    "themes": Path(THEMES_DIR),
}


def seed_defaults() -> None:
    for folder_name, target_dir in SEED_TARGETS.items():
        source_dir = SEED_DIR / folder_name
        if not source_dir.is_dir():
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        for source_file in source_dir.glob("*.json"):
            destination = target_dir / source_file.name
            if not destination.exists():
                shutil.copyfile(source_file, destination)