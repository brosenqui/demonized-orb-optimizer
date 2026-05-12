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
    awakened: int = 0

class OrbOut(BaseModel):
    type: str
    set: str
    rarity: Rarity
    value: float
    level: int
    awakened: int = 0
    slot_index: Optional[int] = None  # allowed but optional

class SharedSlotProfileImpactOut(BaseModel):
    profile: str
    selected_score: float = 0.0
    solo_best_score: float = 0.0
    compromise_loss: float = 0.0
    selected_d_set: float = 0.0
    selected_d_orb: float = 0.0
    solo_best_d_set: float = 0.0
    solo_best_d_orb: float = 0.0
    cap_limited: bool = False

class SharedSlotAssignmentOut(BaseModel):
    category: str
    slot_index: int
    profiles: List[str] = Field(default_factory=list)
    is_uniform: bool = False
    orb: Optional[OrbOut] = None
    profile_orbs: Dict[str, Optional[OrbOut]] = Field(default_factory=dict)
    profile_impacts: List[SharedSlotProfileImpactOut] = Field(default_factory=list)

class SharedSummaryOut(BaseModel):
    requested_slots: int = 0
    filled_slots: int = 0
    is_partial: bool = False
    requested_positions: int = 0
    filled_positions: int = 0
    active_sets: Dict[str, int] = Field(default_factory=dict)
    totals_by_type: Dict[str, float] = Field(default_factory=dict)
    compromise_loss_total: float = 0.0
    compromise_loss_by_profile: Dict[str, float] = Field(default_factory=dict)
    cap_limited_slots_by_profile: Dict[str, int] = Field(default_factory=dict)
    slots: List[SharedSlotAssignmentOut] = Field(default_factory=list)

class ProfileRaw(BaseModel):
    name: str
    score: Optional[float] = None
    set_score: Optional[float] = None
    orb_score: Optional[float] = None
    requested_slots: int = 0
    filled_slots: int = 0
    is_partial: bool = False
    assignments: Dict[str, List[OrbOut]] = Field(default_factory=dict)

class RawPayload(BaseModel):
    combined_score: Optional[float] = None
    requested_slots: int = 0
    filled_slots: int = 0
    is_partial: bool = False
    shared_summary: Optional[SharedSummaryOut] = None
    profiles: List[ProfileRaw] = Field(default_factory=list)

class SummaryProfile(BaseModel):
    name: str
    score: Optional[float] = None
    set_score: Optional[float] = None
    orb_score: Optional[float] = None
    requested_slots: int = 0
    filled_slots: int = 0
    is_partial: bool = False

class SummaryPayload(BaseModel):
    combined_score: Optional[float] = None
    requested_slots: int = 0
    filled_slots: int = 0
    is_partial: bool = False
    shared_summary: Optional[SharedSummaryOut] = None
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
