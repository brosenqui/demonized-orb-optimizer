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
from .shareability import enabled_profiles_by_category

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
    shareability_matrix: Dict[str, Dict[str, bool]] | None,
    candidate_orbs: Sequence[Any],
    marginal_gain_fn: MarginalGainFn,
    primary_coeff_fn: PrimaryCoeffFn,
    set_cap_fn: SetCapFn,
) -> SharedSummary:
    enabled_by_category = enabled_profiles_by_category(shareability_matrix)
    if not enabled_by_category:
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

    for category, enabled_profiles in sorted(enabled_by_category.items()):
        if len(enabled_profiles) < 2:
            continue
        max_slots = max((slots_by_profile.get(p.name, {}).get(category, 0) for p in profiles), default=0)
        if max_slots <= 0:
            continue

        for slot_index in range(max_slots):
            sharing_profiles = [
                p
                for p in profiles
                if (
                    slot_index < slots_by_profile.get(p.name, {}).get(category, 0)
                    and p.name in enabled_profiles
                )
            ]
            if len(sharing_profiles) < 2:
                continue

            selected_by_profile: Dict[str, Optional[Any]] = {}
            for profile in sharing_profiles:
                loadout = assignments.get(profile.name, {})
                cat_orbs = loadout.get(category, [])
                selected_by_profile[profile.name] = (
                    cat_orbs[slot_index] if slot_index < len(cat_orbs) else None
                )

            selected_non_null = [orb for orb in selected_by_profile.values() if orb is not None]
            if len(selected_non_null) < 2:
                continue

            grouped_orbs: defaultdict[tuple, List[Any]] = defaultdict(list)
            for orb in selected_non_null:
                grouped_orbs[_orb_signature(orb)].append(orb)
            shared_signatures = {
                signature: orb_group
                for signature, orb_group in grouped_orbs.items()
                if len(orb_group) >= 2
            }
            if not shared_signatures:
                continue

            requested_slots += 1
            filled_slots += 1
            requested_positions += len(sharing_profiles)
            filled_positions += sum(len(group) for group in shared_signatures.values())

            is_uniform = len(shared_signatures) == 1 and len(selected_non_null) == len(sharing_profiles)
            uniform_orb = (
                next(iter(shared_signatures.values()))[0]
                if is_uniform
                else None
            )

            profile_orbs: Dict[str, Optional[AssignedOrb]] = {}
            impacts: List[SharedSlotProfileImpact] = []

            for profile in sharing_profiles:
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

            slot_rows.append(
                SharedSlotAssignment(
                    category=category,
                    slot_index=slot_index,
                    profiles=[p.name for p in sharing_profiles],
                    is_uniform=is_uniform,
                    orb=_to_assigned(uniform_orb, slot_index) if uniform_orb is not None else None,
                    profile_orbs=profile_orbs,
                    profile_impacts=impacts,
                )
            )

            unique_shared_orbs: Dict[tuple, Any] = {
                signature: orb_group[0]
                for signature, orb_group in shared_signatures.items()
            }
            for orb in unique_shared_orbs.values():
                active_sets[_orb_set(orb)] += 1
                totals_by_type[_orb_type(orb)] += _safe_float(getattr(orb, "value", 0.0))

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
