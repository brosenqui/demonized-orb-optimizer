"""Data loading utilities for the Orb Optimizer.

Required inputs:
  - orbs.json     : list of orb records
  - slots.json    : category -> rarity (slots inferred from rarity)

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

if TYPE_CHECKING:
    from logging import Logger

# ===== Built-in defaults (for optional knobs) =====

# Priority weights per set (bigger = more important)
DEFAULT_SET_PRIORITY_WEIGHTS: dict[str, float] = {
    "Leviathan": 8.0,
    "Beezlebub": 6.0,
    "Belphegor": 5.0,
    "Asmodeus": 3.0,
    "Mammon": 2.0,
    "Satan": 1.5,
    "Lucifer": 1.0,
}

# Orb-type multipliers, no bias
DEFAULT_ORB_TYPE_WEIGHTS: dict[str, float] = {
    "Flame": 1.0,
    "Water": 1.0,
    "Wind": 1.0,
    "Earth": 1.0,
    "Sun": 1.0,
    "Grass": 1.0,
    "Lightning": 1.0,
    "Steel": 1.0,
}

# Level caps by rarity
DEFAULT_LEVEL_CAPS: dict[str, int] = {
    "Common": 3,
    "Magic": 3,
    "Rare": 6,
    "Heroic": 6,
    "Legendary": 9,
    "Mythic": 9,
}

DEFAULT_SET_COUNTS: dict[str, list[int]] = {
    "Lucifer": [4, 5],
    "Mammon": [2, 4, 6],
    "Leviathan": [3, 5, 6],
    "Satan": [4, 5, 6],
    "Asmodeus": [2, 4],
    "Beezlebub": [1, 3, 5],
    "Belphegor": [2, 4, 6],
}

# Additive points per unlocked tier (3/6/9) by orb type
DEFAULT_ORB_LEVEL_WEIGHTS: dict[str, float] = {
    "Flame": 1.0,
    "Water": 1.0,
    "Wind": 1.0,
    "Earth": 1.0,
    "Sun": 1.0,
    "Grass": 1.0,
    "Lightning": 1.0,
    "Steel": 5.0,
}


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
        """Load orbs and clip their levels per rarity caps"""
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
                        set_name=item["set"],
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
        """Load category rarities and determine slot counts."""
        raw = self.load_json(file_path)
        cats: list[Category] = []
        for name, slots in raw.items():
            cats.append(Category(name=name, slots=slots))
        self.logger.info(f"✅ Loaded {len(cats)} categories.")
        return cats

    # -------- Thresholds (required for scoring) --------
    def _as_sorted_ints(self, seq: Any) -> list[int]:
        return sorted({int(x) for x in seq})

    def load_set_thresholds(self) -> dict[str, list[int]]:
        return DEFAULT_SET_COUNTS.copy()

    # -------- Optional data with defaults --------
    def load_set_priority_or_default(
        self, file_path: str | Path | None
    ) -> dict[str, float]:
        if not file_path:
            self.logger.info("ℹ️ No set priority file — using built-in defaults.")
            return DEFAULT_SET_PRIORITY_WEIGHTS.copy()
        p = Path(file_path)
        if not p.exists():
            self.logger.warning(
                f"⚠️ Set priority file not found at {file_path} — using defaults."
            )
            return DEFAULT_SET_PRIORITY_WEIGHTS.copy()
        raw = self.load_json(p)
        if not isinstance(raw, dict):
            self.logger.warning(
                "⚠️ Set priority file must be an object — using defaults."
            )
            return DEFAULT_SET_PRIORITY_WEIGHTS.copy()
        out: dict[str, float] = {}
        for k, v in raw.items():
            try:
                out[str(k)] = float(v)
            except (TypeError, ValueError):
                self.logger.warning(
                    f"⚠️ Invalid set priority for {k!r}: {v!r} (skipped)"
                )
        self.logger.info(f"✅ Loaded {len(out)} set priorities from {file_path}.")
        return out or DEFAULT_SET_PRIORITY_WEIGHTS.copy()

    def load_orb_type_weights_or_default(
        self, file_path: str | Path | None
    ) -> dict[str, float]:
        if not file_path:
            self.logger.info("ℹ️ No orb-type weights file — using built-in defaults.")
            return DEFAULT_ORB_TYPE_WEIGHTS.copy()
        p = Path(file_path)
        if not p.exists():
            self.logger.warning(
                f"⚠️ Orb-type weights file not found at {file_path} — using defaults."
            )
            return DEFAULT_ORB_TYPE_WEIGHTS.copy()
        raw = self.load_json(p)
        if not isinstance(raw, dict):
            self.logger.warning(
                "⚠️ Orb-type weights must be an object — using defaults."
            )
            return DEFAULT_ORB_TYPE_WEIGHTS.copy()
        out: dict[str, float] = {}
        for k, v in raw.items():
            try:
                out[str(k)] = float(v)
            except (TypeError, ValueError):
                self.logger.warning(
                    f"⚠️ Invalid orb-type weight for {k!r}: {v!r} (skipped)"
                )
        self.logger.info(f"✅ Loaded {len(out)} orb-type weights from {file_path}.")
        return out or DEFAULT_ORB_TYPE_WEIGHTS.copy()

    def load_orb_level_weights_or_default(
        self, file_path: str | Path | None
    ) -> dict[str, float]:
        if not file_path:
            self.logger.info("ℹ️ No orb-level weights file — using built-in defaults.")
            return DEFAULT_ORB_LEVEL_WEIGHTS.copy()
        p = Path(file_path)
        if not p.exists():
            self.logger.warning(
                f"⚠️ Orb-level weights file not found at {file_path} — using defaults."
            )
            return DEFAULT_ORB_LEVEL_WEIGHTS.copy()
        raw = self.load_json(p)
        if not isinstance(raw, dict):
            self.logger.warning(
                "⚠️ Orb-level weights must be an object — using defaults."
            )
            return DEFAULT_ORB_LEVEL_WEIGHTS.copy()
        out: dict[str, float] = {}
        for k, v in raw.items():
            try:
                out[str(k)] = float(v)
            except (TypeError, ValueError):
                self.logger.warning(
                    f"⚠️ Invalid orb-level weight for {k!r}: {v!r} (skipped)"
                )
        self.logger.info(f"✅ Loaded {len(out)} orb-level weights from {file_path}.")
        return out or DEFAULT_ORB_LEVEL_WEIGHTS.copy()
