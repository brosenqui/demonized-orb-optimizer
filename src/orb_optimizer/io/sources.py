# orb_optimizer/io/sources.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


class FileSource:
    """Reads JSON from a file path on disk."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load_json(self) -> Any:
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def base_dir(self) -> Path:
        return self.path.parent


class DictSource:
    """Returns JSON that is already in-memory (dict/list/etc.).

    Optionally carry a base path (used to resolve relative profile asset refs).
    """

    def __init__(self, data: Any, base: Optional[str | Path] = None):
        self.data = data
        self._base = Path(base) if base else None

    def load_json(self) -> Any:
        return self.data

    def base_dir(self) -> Path | None:
        return self._base
