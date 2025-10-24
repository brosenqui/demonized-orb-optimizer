# apps/api/schemas.py
from __future__ import annotations
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field

Rarity = Literal["Common", "Magic", "Rare", "Epic", "Legendary", "Mythic"]

class OrbIn(BaseModel):
    type: str
    set: str
    rarity: str
    value: float
    level: int

class OrbOut(BaseModel):
    type: str
    set: str
    rarity: Rarity
    value: float
    level: int
    slot_index: Optional[int] = None  # allowed but optional

class ProfileRaw(BaseModel):
    name: str
    score: Optional[float] = None
    set_score: Optional[float] = None
    orb_score: Optional[float] = None
    assignments: Dict[str, List[OrbOut]] = Field(default_factory=dict)

class RawPayload(BaseModel):
    combined_score: Optional[float] = None
    profiles: List[ProfileRaw] = Field(default_factory=list)

class SummaryProfile(BaseModel):
    name: str
    score: Optional[float] = None
    set_score: Optional[float] = None
    orb_score: Optional[float] = None

class SummaryPayload(BaseModel):
    combined_score: Optional[float] = None
    profiles: List[SummaryProfile] = Field(default_factory=list)

class OptimizeProfileIn(BaseModel):
    name: str
    weight: float
    objective: Literal["sets-first", "types-first"]
    power: float
    epsilon: float
    set_priority: Dict[str, float]
    orb_weights: Dict[str, float]
    orb_level_weights: Dict[str, float]
    categories: Optional[Dict[str, Rarity]] = None
    slots: Optional[Dict[str, int]] = None  # direct override

class OptimizeRequest(BaseModel):
    orbs: List[OrbIn]
    profiles: List[OptimizeProfileIn]
    shareable_categories: Optional[List[str]] = None
    algorithm: Literal["greedy"] = "greedy"  # web app supports greedy only

class OptimizeResult(BaseModel):
    summary: SummaryPayload
    raw: RawPayload

class OptimizeResponse(BaseModel):
    ok: bool
    result: OptimizeResult
