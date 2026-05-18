# orb_optimizer/io/parsers.py
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Tuple, TYPE_CHECKING

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

def _coerce_awakened_level(value: Any) -> int:
    try:
        numeric = int(float(value))
    except Exception:
        return 0
    return max(0, numeric)


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
                set=str(item["set"]),
                rarity=str(item["rarity"]),
                value=parse_value(item["value"]),
                level=lvl,
                awakened=_coerce_awakened_level(item.get("awakened", 0)),
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


def _validate_shareability_matrix(value: Any) -> Mapping[str, Mapping[str, bool]]:
    if not isinstance(value, dict):
        raise TypeError("shareability_matrix must be an object mapping category -> profile -> boolean")
    for category, row in value.items():
        if not isinstance(category, str):
            raise TypeError("shareability_matrix category keys must be strings")
        if not isinstance(row, dict):
            raise TypeError(
                f"shareability_matrix[{category!r}] must be an object mapping profile -> boolean"
            )
        for profile_name, enabled in row.items():
            if not isinstance(profile_name, str):
                raise TypeError("shareability_matrix profile keys must be strings")
            if not isinstance(enabled, bool):
                raise TypeError(
                    f"shareability_matrix[{category!r}][{profile_name!r}] must be a boolean"
                )
    return value


def parse_profiles_header(data: Any) -> Tuple[List[dict], Mapping[str, Mapping[str, bool]] | List[str] | None]:
    """Light validation for profiles payload; returns (profiles_list, shareability payload)."""
    if isinstance(data, dict) and "profiles" in data:
        profiles = data["profiles"]
        shareability_matrix = data.get("shareability_matrix")
        legacy_shareable = data.get("shareable_categories")
    else:
        profiles = data
        shareability_matrix = None
        legacy_shareable = None

    if not isinstance(profiles, list):
        raise TypeError("profiles must be a list")
    for i, p in enumerate(profiles):
        if not isinstance(p, dict):
            raise TypeError(f"profiles[{i}] must be an object")
    if shareability_matrix is not None:
        return profiles, _validate_shareability_matrix(shareability_matrix)

    if legacy_shareable is not None:
        if not isinstance(legacy_shareable, list) or not all(isinstance(s, str) for s in legacy_shareable):
            raise TypeError("shareable_categories must be a list of strings")
        return profiles, legacy_shareable

    return profiles, None
