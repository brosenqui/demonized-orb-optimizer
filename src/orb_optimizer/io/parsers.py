# orb_optimizer/io/parsers.py
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple, TYPE_CHECKING

from ..models import Orb, Category
from ..utils import parse_value
from ..defaults import (
    DEFAULT_LEVEL_CAPS,
)

if TYPE_CHECKING:
    from logging import Logger


def _require_keys(d: Dict[str, Any], keys: Iterable[str], where: str) -> None:
    missing = [k for k in keys if k not in d]
    if missing:
        raise ValueError(f"Missing keys {missing} in {where}")


def parse_orbs(data: Any, logger: "Logger | None" = None) -> List[Orb]:
    """Validate and convert a list of orb dicts -> List[Orb] with level clipping."""
    if not isinstance(data, list):
        raise TypeError("orbs payload must be a list")
    out: List[Orb] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise TypeError(f"orbs[{i}] must be an object")
        _require_keys(item, ["type", "set", "rarity", "value", "level"], f"orbs[{i}]")

        # clip level by rarity caps
        raw_level = item.get("level", 0)
        try:
            lvl = int(raw_level) if raw_level is not None else 0
        except Exception:
            lvl = 0
        rarity = item["rarity"]
        max_lvl = DEFAULT_LEVEL_CAPS.get(rarity, 0)
        if lvl > max_lvl and logger:
            logger.warning(
                f"⚠️ Orb level {lvl} exceeds cap {max_lvl} for rarity {rarity}; clipping."
            )
        lvl = min(lvl, max_lvl)

        out.append(
            Orb(
                type=str(item["type"]),
                set_name=str(item["set"]),
                rarity=str(item["rarity"]),
                value=parse_value(item["value"]),
                level=lvl,
            )
        )
    return out


def parse_categories(data: Any) -> List[Category]:
    """Validate and convert mapping category->slots -> List[Category]."""
    if not isinstance(data, dict):
        raise TypeError("slots/categories payload must be an object mapping category -> slots (int).")
    cats: List[Category] = []
    for name, slots in data.items():
        cats.append(Category(name=str(name), slots=int(slots)))
    return cats


def parse_profiles_header(data: Any) -> Tuple[List[dict], List[str] | None]:
    """Light validation for profiles payload; returns (profiles_list, shareable?)."""
    if isinstance(data, dict) and "profiles" in data:
        profiles = data["profiles"]
        shareable = data.get("shareable_categories")
    else:
        profiles = data
        shareable = None

    if not isinstance(profiles, list):
        raise TypeError("profiles must be a list")
    for i, p in enumerate(profiles):
        if not isinstance(p, dict):
            raise TypeError(f"profiles[{i}] must be an object")
    if shareable is not None:
        if not isinstance(shareable, list) or not all(isinstance(s, str) for s in shareable):
            raise TypeError("shareable_categories must be a list of strings")
    return profiles, shareable
