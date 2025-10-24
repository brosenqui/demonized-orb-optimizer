"""Utility helpers for the Orb Optimizer.

Includes:
    - ANSI colorized logging setup.
    - Rarity/slot mappings.
    - Helper parsing functions.
    - Profile builders that attach per-profile categories.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, TYPE_CHECKING

from .models import ProfileConfig, Category

if TYPE_CHECKING:
    from .data_loader import DataLoader

# === Rarity mappings ===
# Category rarity → slots (for profile category selection)
CATEGORY_RARITY_SLOTS: dict[str, int] = {
    "Rare": 1,
    "Epic": 2,
    "Legendary": 3,
    "Mythic": 4,
}

# === ANSI color codes for logger ===
class ColorFormatter(logging.Formatter):
    """Custom log formatter with ANSI color codes."""

    COLORS = {
        logging.DEBUG: "\033[92m",   # Green
        logging.INFO: "\033[94m",    # Blue
        logging.WARNING: "\033[93m", # Yellow
        logging.ERROR: "\033[91m",   # Red
        logging.CRITICAL: "\033[95m" # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


def setup_logger(verbose: bool = False) -> logging.Logger:
    """Configure a colorized logger."""
    logger = logging.getLogger("orb_optimizer")
    if logger.handlers:
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        return logger
    handler = logging.StreamHandler(sys.stderr)
    formatter = ColorFormatter("%(asctime)s [%(levelname)s]\t| %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.propagate = False
    return logger


# === Helper functions ===
def parse_value(value: Any) -> float:
    """Parse a value that may be a percentage or numeric string."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        if value.endswith("%"):
            try:
                return float(value.strip("%"))
            except ValueError:
                return 0.0
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


# ---------- NEW: category helpers ----------
def _slots_from_category_rarity(cat_rarity: dict[str, str] | None) -> dict[str, int]:
    """Convert {category: rarity} -> {category: slots} using CATEGORY_RARITY_SLOTS."""
    if not cat_rarity:
        return {}
    out: dict[str, int] = {}
    for cat, rarity in cat_rarity.items():
        out[cat] = CATEGORY_RARITY_SLOTS.get(str(rarity), 0)
    return out


def _categories_from_slots(loader: "DataLoader", slots_map: dict[str, int]) -> list[Category]:
    """Build Category dataclasses from a {category: slots} map using the loader path."""
    # If your DataLoader has load_categories(DictSource(map)) keep using it.
    # Otherwise build dataclasses directly.
    try:
        from .io.sources import DictSource
        return loader.load_categories(DictSource(slots_map))
    except Exception:
        # Fallback: construct directly
        return [Category(name=k, slots=int(v)) for k, v in slots_map.items()]


# ---------- Profiles: builders that ATTACH categories ----------
def build_profiles_from_json(
    loader: "DataLoader",
    path: str,
    *,
    default_slots: dict[str, int] | None = None,
) -> tuple[list[ProfileConfig], list[str]]:
    """Read profiles.json and convert to ProfileConfig list WITH categories attached.

    Supports per-profile:
      - "slots": { "Soul": 3, ... }
      - "category_rarity": { "Soul": "Legendary", ... }  (mapped via CATEGORY_RARITY_SLOTS)

    If neither is present on a profile, falls back to `default_slots` (typically from slots.json).
    """
    cfg = loader.load_json(path)
    try:
        profiles_json = cfg["profiles"]
        if not isinstance(profiles_json, list):
            raise TypeError
    except (TypeError, KeyError):
        raise ValueError("profiles.json must contain a 'profiles' array")

    out: list[ProfileConfig] = []
    for pj in profiles_json:
        name = pj["name"]

        # core weights
        set_prio = loader.load_set_priority_or_default(pj.get("set_priority"))
        type_w = loader.load_orb_type_weights_or_default(pj.get("orb_weights"))
        lvl_w = loader.load_orb_level_weights_or_default(pj.get("orb_level_weights"))

        # per-profile categories
        slots_map: dict[str, int] | None = None
        if isinstance(pj.get("slots"), dict):
            slots_map = {str(k): int(v) for k, v in pj["slots"].items()}
        elif isinstance(pj.get("category_rarity"), dict):
            slots_map = _slots_from_category_rarity(pj["category_rarity"])
        elif default_slots:
            slots_map = dict(default_slots)
        else:
            slots_map = {}

        categories = _categories_from_slots(loader, slots_map)

        out.append(
            ProfileConfig(
                name=name,
                set_priority=set_prio,
                orb_type_weights=type_w,
                orb_level_weights=lvl_w,
                power=float(pj.get("power", 2.0)),
                epsilon=float(pj.get("epsilon", 0.02)),
                objective=pj.get("objective", "sets-first"),
                weight=float(pj.get("weight", 1.0)),
                categories=categories,  # <-- ATTACHED HERE
            )
        )

    shareable = list(cfg.get("shareable_categories", []))
    return out, shareable


def build_default_profile(
    loader: "DataLoader",
    *,
    set_priority_path: str | None,
    orb_weights_path: str | None,
    orb_level_weights_path: str | None,
    objective: str,
    power: float,
    epsilon: float,
    default_slots: dict[str, int] | None = None,  # NEW
) -> ProfileConfig:
    """Construct a single DEFAULT profile WITH categories attached from default_slots."""
    set_prio = loader.load_set_priority_or_default(set_priority_path)
    type_w = loader.load_orb_type_weights_or_default(orb_weights_path)
    lvl_w = loader.load_orb_level_weights_or_default(orb_level_weights_path)

    categories: list[Category] = []
    if default_slots:
        categories = _categories_from_slots(loader, default_slots)

    return ProfileConfig(
        name="DEFAULT",
        set_priority=set_prio,
        orb_type_weights=type_w,
        orb_level_weights=lvl_w,
        power=power,
        epsilon=epsilon,
        objective=objective,
        weight=1.0,
        categories=categories,  # <-- ATTACHED HERE
    )
