from __future__ import annotations

from typing import Any, Mapping

from .defaults import DEFAULT_ORB_LEVEL_GATE_VALUES

LEVEL_GATES: tuple[int, int, int] = (3, 6, 9)


def base_orb_level(orb: Any) -> int:
    """Return normalized base level for gate checks (awakened is ignored)."""
    try:
        level = int(getattr(orb, "level", 0))
    except Exception:
        level = 0
    return max(0, level)


def cumulative_gate_value_for_type(
    orb_type: str,
    level: int,
    gate_values: Mapping[str, Mapping[int, float]] | None = None,
) -> float:
    """Sum cumulative gate values for a type at the given base level."""
    table = gate_values or DEFAULT_ORB_LEVEL_GATE_VALUES
    per_type = table.get(str(orb_type), {})
    total = 0.0
    for gate in LEVEL_GATES:
        if level < gate:
            continue
        try:
            total += float(per_type.get(gate, 0.0))
        except Exception:
            continue
    return total


def cumulative_gate_value_for_orb(
    orb: Any,
    gate_values: Mapping[str, Mapping[int, float]] | None = None,
) -> float:
    """Sum cumulative gate values for an orb using base level only."""
    orb_type = str(getattr(orb, "type", "") or "")
    return cumulative_gate_value_for_type(
        orb_type=orb_type,
        level=base_orb_level(orb),
        gate_values=gate_values,
    )

