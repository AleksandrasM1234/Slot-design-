from importlib.resources import path
import json
import re
from abc import ABC, abstractmethod
from pathlib import Path

from asset_pipeline.domain.framework_preset import FrameworkPreset


class FrameworkRepository(ABC):

    @abstractmethod
    def save(self, preset: FrameworkPreset) -> None: ...

    @abstractmethod
    def list_all(self) -> list[FrameworkPreset]: ...

    @abstractmethod
    def delete(self, key: str) -> bool: ...


class JsonFileFrameworkRepository(FrameworkRepository):

    def __init__(self, directory: str = "data/custom_frameworks"):
        self._directory = Path(directory)
        self._directory.mkdir(exist_ok=True)

    def _path_for(self, key: str) -> Path:
        safe_key = re.sub(r"[^a-zA-Z0-9_-]", "_", key.strip().lower())
        return self._directory / f"{safe_key}.json"

    def save(self, preset: FrameworkPreset) -> None:
        path = self._path_for(preset.key)
        data = {
            "key": preset.key,
            "display_name": preset.display_name,
            "description": preset.description,
            "blueprint_keys": list(preset.blueprint_keys),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def list_all(self) -> list[FrameworkPreset]:
        presets = []
        for p in sorted(self._directory.glob("*.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            presets.append(FrameworkPreset(
                key=data["key"],
                display_name=data["display_name"],
                description=data["description"],
                blueprint_keys=tuple(data["blueprint_keys"]),
            ))
        return presets

    def delete(self, key: str) -> bool:
        path = self._path_for(key)
        if path.exists():
            path.unlink()
            return True
        return False