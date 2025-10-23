# apps/api/schemas.py
from __future__ import annotations

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ---------- Core-shaped inputs (mirror your JSON files) ----------
class OrbIn(BaseModel):
    type: str
    set: str = Field(alias="set")
    rarity: str
    value: float
    level: int


class OptimizeProfileIn(BaseModel):
    # Mirrors one entry from profiles.json, but embeds weight maps (no file paths)
    name: str
    weight: float = 1.0
    objective: Literal["sets-first", "types-first"] = "sets-first"
    power: float = 2.0
    epsilon: float = 0.02

    # Inline maps (instead of file refs)
    set_priority: Dict[str, float]
    orb_weights: Dict[str, float]
    orb_level_weights: Dict[str, float]


class OptimizeRequest(BaseModel):
    # What used to be orbs.json and slots.json:
    orbs: List[OrbIn]
    slots: Dict[str, int]  # category -> count
    # What used to be profiles.json content (embedded):
    profiles: List[OptimizeProfileIn]
    shareable_categories: Optional[List[str]] = None

    # Algorithm & knobs (CLI flags)
    algorithm: Literal["beam", "greedy"] = "beam"
    topk: int = 20              # beam helper
    beam: int = 200             # beam width
    refine_passes: int = 2
    refine_report: bool = False


# ---------- Response models ----------
class OptimizeResult(BaseModel):
    # This is a flexible envelope; we’ll pack a normalized view of your solver output.
    # You can tighten this later if you have a fixed result dataclass.
    summary: dict
    raw: dict  # low-friction full dump (for debugging / UI iteration)


class OptimizeResponse(BaseModel):
    ok: bool
    result: OptimizeResult
