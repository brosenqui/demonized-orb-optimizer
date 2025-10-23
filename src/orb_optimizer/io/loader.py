# orb_optimizer/io/loader.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple, Union, TYPE_CHECKING

from .sources import FileSource, DictSource
from . import parsers
from ..models import Category, Orb, ProfileConfig
from ..defaults import (
    DEFAULT_SET_COUNTS,
    DEFAULT_ORB_LEVEL_WEIGHTS,
    DEFAULT_ORB_TYPE_WEIGHTS,
    DEFAULT_SET_PRIORITY_WEIGHTS,
)
from ..utils import parse_value  # exported for completeness

if TYPE_CHECKING:
    from logging import Logger

SourceLike = Union[str, FileSource, DictSource]


class Loader:
    """
    Unified loader that works with both file paths and in-memory JSON.

    - Equivalent to your old DataLoader for CLI file paths.
    - Also accepts DictSource for FastAPI (request.body).
    - Resolves relative profile asset files (set_priority/orb_weights/orb_level_weights)
      when a base directory is known (e.g., from FileSource).
    """

    def __init__(self, logger: "Logger | None" = None):
        self.logger = logger

    # ---------- Public API ----------
    def load_json(self, file_path: str | Path) -> Any:
        """Compat: used by build_profiles_from_json() in utils."""
        fs = FileSource(file_path)
        data = fs.load_json()
        self._debug(f"📘 Loaded file: {file_path}")
        return data

    def load_orbs(self, source: SourceLike) -> List[Orb]:
        data, _ = self._coerce_to_data_and_base(source)
        out = parsers.parse_orbs(data, self.logger)
        self._info(f"✅ Loaded {len(out)} orbs.")
        return out

    def load_categories(self, source: SourceLike) -> List[Category]:
        data, _ = self._coerce_to_data_and_base(source)
        cats = parsers.parse_categories(data)
        self._info(f"✅ Loaded {len(cats)} categories.")
        return cats

    def load_set_thresholds(self) -> Dict[str, List[int]]:
        """Expose default set piece thresholds (used by scoring)."""
        return DEFAULT_SET_COUNTS.copy()

    # ---- Optional data with defaults (kept 1:1 with your DataLoader) ----
    def load_set_priority_or_default(self, file_path: str | Path | None) -> dict[str, float]:
        return self._load_weights_or_default(file_path, DEFAULT_SET_PRIORITY_WEIGHTS, "set priorities")

    def load_orb_type_weights_or_default(self, file_path: str | Path | None) -> dict[str, float]:
        return self._load_weights_or_default(file_path, DEFAULT_ORB_TYPE_WEIGHTS, "orb-types")

    def load_orb_level_weights_or_default(self, file_path: str | Path | None) -> dict[str, float]:
        return self._load_weights_or_default(file_path, DEFAULT_ORB_LEVEL_WEIGHTS, "orb-levels")

    # ---- Profiles (two modes) ----
    def load_profiles(
        self,
        source: SourceLike,
        *,
        inflate_assets: bool = True,
    ) -> Tuple[List[ProfileConfig], List[str]]:
        """
        Load profiles either from file path (string/FileSource) or in-memory dict (DictSource).

        If inflate_assets=True and a base_dir is known, resolve any string fields:
          - set_priority -> dict loaded from file
          - orb_weights -> dict loaded from file
          - orb_level_weights -> dict loaded from file

        Returns: (profiles, shareable_categories)
        """
        data, base_dir = self._coerce_to_data_and_base(source)
        profiles_raw, shareable = parsers.parse_profiles_header(data)
        out: List[ProfileConfig] = []

        for pj in profiles_raw:
            name = pj["name"]
            # Resolve asset references:
            set_priority = pj.get("set_priority")
            orb_weights = pj.get("orb_weights")
            orb_level_weights = pj.get("orb_level_weights")

            if inflate_assets and base_dir is not None:
                set_priority = self._maybe_load_relative(base_dir, set_priority, DEFAULT_SET_PRIORITY_WEIGHTS, "set priorities")
                orb_weights = self._maybe_load_relative(base_dir, orb_weights, DEFAULT_ORB_TYPE_WEIGHTS, "orb-types")
                orb_level_weights = self._maybe_load_relative(base_dir, orb_level_weights, DEFAULT_ORB_LEVEL_WEIGHTS, "orb-levels")
            else:
                # Fall back to the public helpers (string path or None)
                set_priority = self.load_set_priority_or_default(set_priority)
                orb_weights = self.load_orb_type_weights_or_default(orb_weights)
                orb_level_weights = self.load_orb_level_weights_or_default(orb_level_weights)

            out.append(
                ProfileConfig(
                    name=name,
                    set_priority=set_priority,
                    orb_type_weights=orb_weights,
                    orb_level_weights=orb_level_weights,
                    power=float(pj.get("power", 2.0)),
                    epsilon=float(pj.get("epsilon", 0.02)),
                    objective=str(pj.get("objective", "sets-first")),
                    weight=float(pj.get("weight", 1.0)),
                )
            )

        return out, list(shareable or [])

    # ---------- Helpers ----------
    def _coerce_to_data_and_base(self, source: SourceLike) -> tuple[Any, Path | None]:
        if isinstance(source, str):
            fs = FileSource(source)
            return fs.load_json(), fs.base_dir()
        if isinstance(source, FileSource):
            return source.load_json(), source.base_dir()
        if isinstance(source, DictSource):
            return source.load_json(), source.base_dir()
        # raw dict/list fallback
        return source, None

    def _maybe_load_relative(
        self,
        base_dir: Path,
        ref: Any,
        fallback: dict[str, float],
        name: str,
    ) -> dict[str, float]:
        """If ref is a string path, load JSON relative to base_dir; else use defaults helper."""
        if isinstance(ref, str):
            p = (base_dir / ref).resolve()
            try:
                raw = FileSource(p).load_json()
            except FileNotFoundError:
                self._warn(f"⚠️ {name} file not found at {p} — using defaults.")
                return fallback.copy()
            if not isinstance(raw, dict):
                self._warn(f"⚠️ {name} file must be an object — using defaults.")
                return fallback.copy()
            out: dict[str, float] = {}
            for k, v in raw.items():
                try:
                    out[str(k)] = float(v)
                except (TypeError, ValueError):
                    self._warn(f"⚠️ Invalid {name} for {k!r}: {v!r} (skipped)")
            return out or fallback.copy()
        # Non-string → delegate to the public helper paths
        return self._weights_from_maybe_dict(ref, fallback, name)

    def _weights_from_maybe_dict(
        self,
        ref: Any,
        fallback: dict[str, float],
        name: str,
    ) -> dict[str, float]:
        """Accept an inline dict (e.g., from API JSON) or fall back to defaults."""
        if isinstance(ref, dict):
            out: dict[str, float] = {}
            for k, v in ref.items():
                try:
                    out[str(k)] = float(v)
                except (TypeError, ValueError):
                    self._warn(f"⚠️ Invalid {name} for {k!r}: {v!r} (skipped)")
            return out or fallback.copy()
        if ref is None:
            self._info(f"ℹ️ No {name} provided — using built-in defaults.")
            return fallback.copy()
        # If it's some other type, try to coerce via the generic helper:
        return fallback.copy()

    def _load_weights_or_default(
        self,
        file_path: str | Path | None,
        default_weights: dict[str, float],
        name: str,
    ) -> dict[str, float]:
        """Generic loader for weight dicts with default fallback (file path or None)."""
        if not file_path:
            self._info(f"ℹ️ No {name} file — using built-in defaults.")
            return default_weights.copy()

        p = Path(file_path)
        if not p.exists():
            self._warn(f"⚠️ {name} file not found at {file_path} — using defaults.")
            return default_weights.copy()

        raw = self.load_json(p)
        if not isinstance(raw, dict):
            self._warn(f"⚠️ {name} file must be an object — using defaults.")
            return default_weights.copy()

        out: dict[str, float] = {}
        for k, v in raw.items():
            try:
                out[str(k)] = float(v)
            except (TypeError, ValueError):
                self._warn(f"⚠️ Invalid {name} for {k!r}: {v!r} (skipped)")
        self._info(f"✅ Loaded {len(out)} {name} from {file_path}.")
        return out or default_weights.copy()

    # ---------- Logging wrappers ----------
    def _debug(self, msg: str) -> None:
        if self.logger:
            try:
                self.logger.debug(msg)
            except Exception:
                pass

    def _info(self, msg: str) -> None:
        if self.logger:
            try:
                self.logger.info(msg)
            except Exception:
                pass

    def _warn(self, msg: str) -> None:
        if self.logger:
            try:
                self.logger.warning(msg)
            except Exception:
                pass
