from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from .models import (
    AssignedOrb,
    ProfileConfig,
    SharedSlotAssignment,
    SharedSlotProfileImpact,
    SharedSummary,
)

MarginalGainFn = Callable[[ProfileConfig, Any, Counter], Tuple[float, float]]
PrimaryCoeffFn = Callable[[ProfileConfig], Tuple[float, float]]
SetCapFn = Callable[[str], Optional[int]]


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _orb_set(orb: Any) -> str:
    return str(getattr(orb, "set", None) or getattr(orb, "set_name", None) or "")


def _orb_type(orb: Any) -> str:
    return str(getattr(orb, "type", "") or "")


def _orb_signature(orb: Any) -> tuple:
    return (
        _orb_type(orb),
        _orb_set(orb),
        str(getattr(orb, "rarity", "") or ""),
        _safe_float(getattr(orb, "value", 0.0)),
        _safe_int(getattr(orb, "level", 0)),
        max(0, _safe_int(getattr(orb, "awakened", 0))),
    )


def _to_assigned(orb: Any, slot_index: int) -> AssignedOrb:
    return AssignedOrb(
        type=_orb_type(orb),
        set=_orb_set(orb),
        rarity=str(getattr(orb, "rarity", "Rare") or "Rare"),
        level=max(0, _safe_int(getattr(orb, "level", 0))),
        value=_safe_float(getattr(orb, "value", 0.0)),
        awakened=max(0, _safe_int(getattr(orb, "awakened", 0))),
        slot_index=slot_index,
    )


def build_shared_summary(
    *,
    profiles: Sequence[ProfileConfig],
    assignments: Dict[str, Dict[str, List[Any]]],
    slots_by_profile: Dict[str, Dict[str, int]],
    shareable_categories: Set[str],
    candidate_orbs: Sequence[Any],
    marginal_gain_fn: MarginalGainFn,
    primary_coeff_fn: PrimaryCoeffFn,
    set_cap_fn: SetCapFn,
) -> SharedSummary:
    if not shareable_categories:
        return SharedSummary()

    requested_slots = 0
    filled_slots = 0
    requested_positions = 0
    filled_positions = 0

    active_sets: Counter[str] = Counter()
    totals_by_type: defaultdict[str, float] = defaultdict(float)
    compromise_loss_by_profile: defaultdict[str, float] = defaultdict(float)
    cap_limited_slots_by_profile: defaultdict[str, int] = defaultdict(int)
    slot_rows: List[SharedSlotAssignment] = []

    for category in sorted(shareable_categories):
        max_slots = max((slots_by_profile.get(p.name, {}).get(category, 0) for p in profiles), default=0)
        if max_slots <= 0:
            continue

        for slot_index in range(max_slots):
            eligible_profiles = [
                p for p in profiles if slot_index < slots_by_profile.get(p.name, {}).get(category, 0)
            ]
            if not eligible_profiles:
                continue

            requested_slots += 1
            requested_positions += len(eligible_profiles)

            selected_by_profile: Dict[str, Optional[Any]] = {}
            for profile in eligible_profiles:
                loadout = assignments.get(profile.name, {})
                cat_orbs = loadout.get(category, [])
                selected_by_profile[profile.name] = (
                    cat_orbs[slot_index] if slot_index < len(cat_orbs) else None
                )

            selected_non_null = [orb for orb in selected_by_profile.values() if orb is not None]
            if selected_non_null and len(selected_non_null) == len(eligible_profiles):
                filled_slots += 1
            filled_positions += len(selected_non_null)

            signatures = {_orb_signature(orb) for orb in selected_non_null}
            is_uniform = len(signatures) == 1 and len(selected_non_null) == len(eligible_profiles)
            uniform_orb = selected_non_null[0] if is_uniform else None

            profile_orbs: Dict[str, Optional[AssignedOrb]] = {}
            impacts: List[SharedSlotProfileImpact] = []

            for profile in eligible_profiles:
                selected_orb = selected_by_profile[profile.name]
                profile_orbs[profile.name] = (
                    _to_assigned(selected_orb, slot_index) if selected_orb is not None else None
                )

                baseline_counts = Counter()
                used_types_same_cat: Set[str] = set()
                cat_orbs = assignments.get(profile.name, {}).get(category, [])
                for cat_name, orb_list in assignments.get(profile.name, {}).items():
                    for idx, orb in enumerate(orb_list):
                        if cat_name == category and idx == slot_index:
                            continue
                        baseline_counts[_orb_set(orb)] += 1
                        if cat_name == category:
                            used_types_same_cat.add(_orb_type(orb))

                coeff_set, coeff_orb = primary_coeff_fn(profile)

                if selected_orb is not None:
                    selected_d_set, selected_d_orb = marginal_gain_fn(profile, selected_orb, baseline_counts)
                    selected_score = (coeff_set * selected_d_set) + (coeff_orb * selected_d_orb)
                else:
                    selected_d_set = 0.0
                    selected_d_orb = 0.0
                    selected_score = 0.0

                best_c_score = selected_score
                best_c_d_set = selected_d_set
                best_c_d_orb = selected_d_orb
                best_u_score = selected_score
                best_u_d_set = selected_d_set
                best_u_d_orb = selected_d_orb
                best_u_orb: Optional[Any] = selected_orb

                for candidate in candidate_orbs:
                    candidate_type = _orb_type(candidate)
                    if candidate_type in used_types_same_cat:
                        continue

                    c_set = _orb_set(candidate)
                    cap = set_cap_fn(c_set)
                    violates_cap = cap is not None and baseline_counts[c_set] >= cap

                    d_set, d_orb = marginal_gain_fn(profile, candidate, baseline_counts)
                    candidate_score = (coeff_set * d_set) + (coeff_orb * d_orb)

                    if not violates_cap and candidate_score > best_c_score:
                        best_c_score = candidate_score
                        best_c_d_set = d_set
                        best_c_d_orb = d_orb

                    if candidate_score > best_u_score:
                        best_u_score = candidate_score
                        best_u_d_set = d_set
                        best_u_d_orb = d_orb
                        best_u_orb = candidate

                cap_limited = False
                if best_u_orb is not None:
                    best_u_set = _orb_set(best_u_orb)
                    cap = set_cap_fn(best_u_set)
                    cap_limited = (
                        cap is not None
                        and baseline_counts[best_u_set] >= cap
                        and best_u_score > best_c_score
                    )
                if cap_limited:
                    cap_limited_slots_by_profile[profile.name] += 1

                compromise_loss = max(0.0, best_c_score - selected_score)
                compromise_loss_by_profile[profile.name] += compromise_loss

                impacts.append(
                    SharedSlotProfileImpact(
                        profile=profile.name,
                        selected_score=selected_score,
                        solo_best_score=best_c_score,
                        compromise_loss=compromise_loss,
                        selected_d_set=selected_d_set,
                        selected_d_orb=selected_d_orb,
                        solo_best_d_set=best_c_d_set,
                        solo_best_d_orb=best_c_d_orb,
                        cap_limited=cap_limited,
                    )
                )

                if selected_orb is not None:
                    active_sets[_orb_set(selected_orb)] += 1
                    totals_by_type[_orb_type(selected_orb)] += _safe_float(getattr(selected_orb, "value", 0.0))

            slot_rows.append(
                SharedSlotAssignment(
                    category=category,
                    slot_index=slot_index,
                    profiles=[p.name for p in eligible_profiles],
                    is_uniform=is_uniform,
                    orb=_to_assigned(uniform_orb, slot_index) if uniform_orb is not None else None,
                    profile_orbs=profile_orbs,
                    profile_impacts=impacts,
                )
            )

    compromise_loss_total = sum(compromise_loss_by_profile.values())

    return SharedSummary(
        requested_slots=requested_slots,
        filled_slots=filled_slots,
        is_partial=filled_slots < requested_slots,
        requested_positions=requested_positions,
        filled_positions=filled_positions,
        active_sets=dict(sorted(active_sets.items(), key=lambda item: (-item[1], item[0]))),
        totals_by_type=dict(
            sorted(totals_by_type.items(), key=lambda item: (-item[1], item[0]))
        ),
        compromise_loss_total=compromise_loss_total,
        compromise_loss_by_profile=dict(sorted(compromise_loss_by_profile.items())),
        cap_limited_slots_by_profile=dict(sorted(cap_limited_slots_by_profile.items())),
        slots=slot_rows,
    )


def shared_summary_to_dict(shared_summary: Optional[SharedSummary]) -> Optional[Dict[str, Any]]:
    if shared_summary is None:
        return None
    return asdict(shared_summary)
