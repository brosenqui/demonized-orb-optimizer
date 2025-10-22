"""Models for the Orb Optimizer.

This module defines dataclasses that represent the main entities in the orb optimization system
"""

from typing import Dict
from dataclasses import dataclass


@dataclass(slots=True)
class Orb:
    """Represents a single orb item.

    Attributes:
        type: The orb type (e.g., 'Steel', 'Flame', 'Wind').
        set_name: The set this orb belongs to (e.g., 'Leviathan').
        rarity: The rarity tier of the orb (e.g., 'Rare', 'Legendary').
        value: The numeric value representing this orb's stat bonus.
        level: The orb's current upgrade level (default 0).
    """

    type: str
    set_name: str
    rarity: str
    value: float
    level: int = 0

    def __repr__(self) -> str:
        return (
            f"Orb(type='{self.type}', set='{self.set_name}', "
            f"rarity='{self.rarity}', value={self.value}, level={self.level})"
        )


@dataclass(slots=True)
class SetBonus:
    """Represents a set bonus configuration.

    Attributes:
        name: The name of the set.
        thresholds: Mapping of piece count to bonus value.
        preference: Multiplier representing player preference for this set.
    """

    name: str
    thresholds: dict[int, float]
    preference: float = 1.0

    def get_bonus(self, count: int) -> float:
        """Get the highest non-stacking bonus available for a given count.

        Args:
            count: Number of equipped pieces from this set.

        Returns:
            The highest bonus threshold achieved.
        """
        applicable = [bonus for c, bonus in self.thresholds.items() if count >= c]
        return max(applicable, default=0.0)


@dataclass(slots=True)
class Category:
    """Represents an orb category, such as Soul or Wings.

    Attributes:
        name: The name of the category.
        slots: Number of orb slots available in this category.
    """

    name: str
    slots: int

    def __repr__(self) -> str:
        return f"Category(name='{self.name}', slots={self.slots})"


# ========= Orb level tiers (per TYPE) =========


@dataclass(slots=True)
class OrbLevelTier:
    """Single level tier that applies to an orb TYPE.

    Attributes:
        level: Threshold level at which this tier activates (e.g., 3, 6, 9).
        mode: 'add' to add to the orb's base value; 'mul' to multiply it.
        value: The additive amount or multiplicative factor.
    """

    level: int
    mode: str  # "add" or "mul"
    value: float


@dataclass(slots=True)
class OrbLevelSpec:
    """Collection of level tiers for one orb TYPE.

    Attributes:
        type_name: Orb type name this spec applies to (e.g., 'Steel').
        tiers: Sorted list of OrbLevelTier, ascending by 'level'.
    """

    type_name: str
    tiers: list[OrbLevelTier]

    def apply_to(self, base: float, level: int) -> float:
        """Apply all tiers <= 'level' to 'base' and return adjusted value.

        The combination rule is:
            adjusted = base * (product of all 'mul' factors) + (sum of all 'add' amounts)
        """
        add_sum = 0.0
        mul_prod = 1.0
        for t in self.tiers:
            if level >= t.level:
                if t.mode == "add":
                    add_sum += t.value
                elif t.mode == "mul":
                    mul_prod *= t.value
        return base * mul_prod + add_sum


@dataclass(slots=True, frozen=True)
class ProfileConfig:
    """Configuration for a single profile (e.g., PVP or PVE)."""

    name: str
    set_priority: Dict[str, float]
    orb_type_weights: Dict[str, float]
    orb_level_weights: Dict[str, float]
    power: float = 2.0
    epsilon: float = 0.0
    objective: str = "sets-first"  # "sets-first" | "types-first"
    weight: float = 1.0  # contribution to combined objective
