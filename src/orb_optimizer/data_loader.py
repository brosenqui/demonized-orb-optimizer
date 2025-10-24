"""Data loading utilities for the Orb Optimizer.

Required inputs:
  - orbs.json     : list of orb records
  - slots.json    : category -> slots (int)

Optional (with built-in defaults):
  - set_priority.json      : set -> priority weight (bigger = more important)
  - orb_weights.json       : orb type -> multiplier
  - orb_levels.json        : { "max_levels_by_rarity": { "Legendary": 9, ... } }
  - orb_level_weights.json : orb type -> additive points per tier (3/6/9)

Notes:
Paths are provided by CLI. Optional files fall back to defaults.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

from .models import Orb, Category
from .utils import parse_value
from .defaults import (
    DEFAULT_LEVEL_CAPS,
    DEFAULT_ORB_LEVEL_WEIGHTS,
    DEFAULT_ORB_TYPE_WEIGHTS,
    DEFAULT_SET_COUNTS,
    DEFAULT_SET_PRIORITY_WEIGHTS,
)

if TYPE_CHECKING:
    from logging import Logger


class DataLoader:
    """Handles loading and normalization of game data files (thresholds-only)."""

    def __init__(self, logger):
        self.logger: Logger = logger

    # -------- Generic JSON --------
    def load_json(self, file_path: str | Path) -> Any:
        path = Path(file_path)
        if not path.exists():
            self.logger.error(f"❌ File not found: {file_path}")
            raise FileNotFoundError(file_path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.logger.debug(f"📘 Loaded file: {file_path}")
        return data

    # -------- Core required data --------
    def load_orbs(self, file_path: str | Path) -> list[Orb]:
        """Load orbs and clip their levels per rarity caps."""
        raw = self.load_json(file_path)
        out: list[Orb] = []
        for item in raw:
            raw_level = item.get("level", 0)
            try:
                lvl = int(raw_level) if raw_level is not None else 0
            except Exception:
                lvl = 0

            rarity = item["rarity"]
            max_lvl = DEFAULT_LEVEL_CAPS.get(rarity, 0)
            if lvl > max_lvl:
                self.logger.warning(
                    f"⚠️ Orb level {lvl} exceeds cap {max_lvl} for rarity {rarity}; clipping."
                )
                lvl = max_lvl

            try:
                out.append(
                    Orb(
                        type=item["type"],
                        set=item["set"],
                        rarity=rarity,
                        value=parse_value(item["value"]),
                        level=lvl,
                    )
                )
            except KeyError as e:
                self.logger.warning(f"⚠️ Missing key {e} in orb entry: {item}")
        self.logger.info(f"✅ Loaded {len(out)} orbs.")
        return out

    def load_categories(self, file_path: str | Path) -> list[Category]:
        """Load categories (name -> slots) and return Category objects."""
        raw = self.load_json(file_path)
        if not isinstance(raw, dict):
            raise ValueError("slots.json must be an object mapping category -> slots (int).")
        cats: list[Category] = []
        for name, slots in raw.items():
            try:
                cats.append(Category(name=str(name), slots=int(slots)))
            except (TypeError, ValueError):
                self.logger.warning(
                    f"⚠️ Invalid slots value for {name!r}: {slots!r} (skipped)"
                )
        self.logger.info(f"✅ Loaded {len(cats)} categories.")
        return cats

    # -------- Thresholds (required for scoring) --------
    def _as_sorted_ints(self, seq: Any) -> list[int]:
        return sorted({int(x) for x in seq})

    def load_set_thresholds(self) -> dict[str, list[int]]:
        return DEFAULT_SET_COUNTS.copy()

    # -------- Optional data with defaults --------
    def _load_weights_or_default(
        self,
        file_path: str | Path | None,
        default_weights: dict[str, float],
        name: str,
    ) -> dict[str, float]:
        """Generic loader for weight dictionaries with default fallback."""
        if not file_path:
            self.logger.info(f"ℹ️ No {name} file — using built-in defaults.")
            return default_weights.copy()

        p = Path(file_path)
        if not p.exists():
            self.logger.warning(
                f"⚠️ {name} file not found at {file_path} — using defaults."
            )
            return default_weights.copy()

        raw = self.load_json(p)
        if not isinstance(raw, dict):
            self.logger.warning(f"⚠️ {name} file must be an object — using defaults.")
            return default_weights.copy()

        out: dict[str, float] = {}
        for k, v in raw.items():
            try:
                out[str(k)] = float(v)
            except (TypeError, ValueError):
                self.logger.warning(f"⚠️ Invalid {name} for {k!r}: {v!r} (skipped)")

        self.logger.info(f"✅ Loaded {len(out)} {name} from {file_path}.")
        return out or default_weights.copy()

    def load_set_priority_or_default(
        self, file_path: str | Path | None
    ) -> dict[str, float]:
        return self._load_weights_or_default(
            file_path, DEFAULT_SET_PRIORITY_WEIGHTS, "set priorities"
        )

    def load_orb_type_weights_or_default(
        self, file_path: str | Path | None
    ) -> dict[str, float]:
        return self._load_weights_or_default(
            file_path, DEFAULT_ORB_TYPE_WEIGHTS, "orb-types"
        )

    def load_orb_level_weights_or_default(
        self, file_path: str | Path | None
    ) -> dict[str, float]:
        return self._load_weights_or_default(
            file_path, DEFAULT_ORB_LEVEL_WEIGHTS, "orb-levels"
        )
