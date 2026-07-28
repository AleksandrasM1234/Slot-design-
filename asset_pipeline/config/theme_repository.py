import json
import re
from abc import ABC, abstractmethod
from pathlib import Path

from asset_pipeline.domain.theme import Theme
from asset_pipeline.domain.theme_serializer import theme_to_dict, theme_from_dict


class ThemeRepository(ABC):

    @abstractmethod
    def save(self, theme: Theme) -> None: ...

    @abstractmethod
    def load(self, name: str) -> Theme: ...

    @abstractmethod
    def list_names(self) -> list[str]: ...


class JsonFileThemeRepository(ThemeRepository):

    def __init__(self, directory: str = "themes"):
        self._directory = Path(directory)
        self._directory.mkdir(exist_ok=True)

    def _path_for(self, name: str) -> Path:
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name.strip().lower())
        return self._directory / f"{safe_name}.json"

    def save(self, theme: Theme) -> None:
        path = self._path_for(theme.name)
        path.write_text(json.dumps(theme_to_dict(theme), indent=2), encoding="utf-8")

    def load(self, name: str) -> Theme:
        path = self._path_for(name)
        if not path.exists():
            raise ValueError(f"No saved theme named '{name}'")
        data = json.loads(path.read_text(encoding="utf-8"))
        return theme_from_dict(data)

    def list_names(self) -> list[str]:
        return sorted(p.stem for p in self._directory.glob("*.json"))