"""Greedy solver (multi-profile, shared pool; shareables + type-unique per category).

Rules:
  • Inventory is global and exclusive: each physical orb can be used once overall.
  • Shareable categories place one physical orb into all eligible profiles for the slot.
  • Type-uniqueness per category per profile.
  • Per-profile set caps: a set cannot exceed max(DEFAULT_SET_COUNTS[set]).

This module also provides bounded multi-start search for better-quality greedy solutions.
"""

from __future__ import annotations

import bisect
import random
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import permutations
from typing import Any, Dict, List, Optional, Set, Tuple

from ..defaults import DEFAULT_SET_COUNTS
from ..models import AssignedOrb, MultiProfileResult, Orb, ProfileConfig, ProfileResult

# Heuristic defaults
TOPK_DEFAULT = 16
RESTARTS_DEFAULT = 6
MAX_TIME_MS_DEFAULT = 1500
ALPHA_DEFAULT = 0.2  # progress toward next threshold
BETA_DEFAULT = 0.1   # potential (remaining tiers after adding)
DEBUG_TOP_N_DEFAULT = 5
MAX_DETERMINISTIC_PERMUTATIONS = 24

SET_MAX_COUNTS: dict[str, int] = {
    set_name: max(thresholds)
    for set_name, thresholds in DEFAULT_SET_COUNTS.items()
    if thresholds
}


# ----------------------------- helpers -----------------------------

def tiers_from_level(level: int) -> int:
    """Count level tiers unlocked at 3, 6, 9."""
    return (1 if level >= 3 else 0) + (1 if level >= 6 else 0) + (1 if level >= 9 else 0)


def get_set(o: Orb) -> str:
    """Robust accessor for set name."""
    return getattr(o, "set", None) or getattr(o, "set", "") or ""


def awakened_levels(o: Any) -> int:
    try:
        value = int(getattr(o, "awakened", 0))
    except Exception:
        value = 0
    return max(0, value)


def effective_level(o: Any) -> int:
    try:
        base_level = int(getattr(o, "level", 0))
    except Exception:
        base_level = 0
    return max(0, base_level) + awakened_levels(o)


def strong_orb_key(o: Orb) -> tuple:
    """Strong identity that supports true duplicates by stable id/index when available."""
    stable_id = getattr(o, "id", None)
    if stable_id is None:
        stable_id = getattr(o, "_idx", None)
    if stable_id is None:
        stable_id = id(o)
    return (
        stable_id,
        getattr(o, "type", None),
        get_set(o),
        getattr(o, "rarity", None),
        getattr(o, "level", None),
        getattr(o, "value", None),
        awakened_levels(o),
    )


def percentile_within_type(type_values: Dict[str, List[float]], t: str, v: float) -> float:
    """Percentile rank of value v within its type t using mid-rank."""
    vals = type_values.get(t)
    if not vals:
        return 0.0
    i = bisect.bisect_left(vals, v)
    j = bisect.bisect_right(vals, v)
    rank = (i + j) / 2.0
    if len(vals) == 1:
        return 1.0
    return rank / (len(vals) - 1)


@dataclass(slots=True)
class ScoringCoefficients:
    set_primary: float
    orb_primary: float


# --------------------------- Greedy Optimizer ---------------------------

class GreedyOptimizer:
    """Greedy assignment across all profiles with bounded multi-start optimization."""

    def __init__(
        self,
        *,
        logger,
        inputs: Any,
        topk_per_type: int = TOPK_DEFAULT,
        restarts: int = RESTARTS_DEFAULT,
        seed: int | None = None,
        max_time_ms: int = MAX_TIME_MS_DEFAULT,
        alpha: float = ALPHA_DEFAULT,
        beta: float = BETA_DEFAULT,
        debug_top_n: int = DEBUG_TOP_N_DEFAULT,
        enable_debug_breakdown: bool = False,
    ) -> None:
        self.logger = logger
        self.P = inputs

        if not getattr(self.P, "profiles", None):
            raise ValueError("At least one profile configuration is required")

        self.topk = max(1, int(topk_per_type))
        self.restarts = max(0, int(restarts))
        self.seed = seed
        self.max_time_ms = max(1, int(max_time_ms))
        self.alpha = float(alpha)
        self.beta = float(beta)
        self.debug_top_n = int(debug_top_n)
        self.enable_debug_breakdown = bool(enable_debug_breakdown)

        self.orbs: List[Orb] = list(self.P.orbs)
        self.profiles: List[ProfileConfig] = list(self.P.profiles)
        self.shareable: Set[str] = set(getattr(self.P, "shareable_categories", None) or [])

        self._slots: Dict[str, Dict[str, int]] = {}
        for p in self.profiles:
            cats = getattr(p, "categories", None) or []
            self._slots[p.name] = {c.name: max(0, int(c.slots)) for c in cats}

        self._all_cats: Set[str] = set()
        for slot_map in self._slots.values():
            self._all_cats.update(slot_map.keys())

        self._requested_slots_by_profile: Dict[str, int] = {
            p.name: sum(self._slots[p.name].values()) for p in self.profiles
        }

        self._type_values: Dict[str, List[float]] = defaultdict(list)
        self._orbs_by_type_sorted: Dict[str, List[Orb]] = defaultdict(list)
        for orb in self.orbs:
            try:
                self._type_values[orb.type].append(float(orb.value))
            except Exception:
                self._type_values[orb.type].append(0.0)
            self._orbs_by_type_sorted[orb.type].append(orb)

        for orb_type in self._type_values:
            self._type_values[orb_type].sort()
        for orb_type, typed in self._orbs_by_type_sorted.items():
            typed.sort(
                key=lambda orb: float(getattr(orb, "value", 0.0)) + tiers_from_level(effective_level(orb)),
                reverse=True,
            )
            self._orbs_by_type_sorted[orb_type] = typed

        self._candidates_by_type = self._build_candidates_by_type(self.topk)

        self.logger.info(
            "🧩 Greedy optimizer ready "
            f"(Top-K={self.topk}/type, restarts={self.restarts}, time_budget={self.max_time_ms}ms, "
            f"{len(self.profiles)} profiles)"
        )
        if self.shareable:
            self.logger.info("🔗 Shareable categories: " + ", ".join(sorted(self.shareable)))
        else:
            self.logger.info("🔗 Shareable categories: (none)")
        self.logger.info(f"⚙️ Heuristic coefficients: ALPHA={self.alpha:.2f}, BETA={self.beta:.2f}")

    # ---------------- Public API ----------------
    def optimize(self) -> MultiProfileResult:
        """Run deterministic + randomized starts and return the best greedy result found."""
        started = time.perf_counter()

        deterministic_orders = self._deterministic_profile_orders()
        rng = random.Random(self.seed if self.seed is not None else 0)

        best: MultiProfileResult | None = None
        runs = 0

        for order in deterministic_orders:
            result = self._solve_once(order)
            best = self._pick_better(best, result)
            runs += 1
            if self._time_budget_exceeded(started):
                break

        for _ in range(self.restarts):
            if self._time_budget_exceeded(started):
                break
            shuffled = list(self.profiles)
            rng.shuffle(shuffled)
            result = self._solve_once(shuffled)
            best = self._pick_better(best, result)
            runs += 1

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        self.logger.info(
            f"✅ Greedy completed in {elapsed_ms}ms across {runs} start(s). "
            f"Best score={best.combined_score:.6f} "
            f"(filled {best.filled_slots}/{best.requested_slots} slots)."
        )
        return best

    # ---------------- core solve (single start) ----------------
    def _solve_once(self, profile_order: List[ProfileConfig]) -> MultiProfileResult:
        assign: Dict[str, Dict[str, List[AssignedOrb]]] = {
            p.name: {cat: [] for cat in self._slots[p.name].keys()} for p in self.profiles
        }
        set_counts = {p.name: Counter() for p in self.profiles}
        used_ids_global: set[tuple] = set()

        # -------- Fill shareable categories --------
        for cat in sorted(self._all_cats):
            if cat not in self.shareable:
                continue
            max_slots = max(self._slots[p.name].get(cat, 0) for p in self.profiles)
            if max_slots <= 0:
                continue

            existing_types_per_prof: Dict[str, Set[str]] = {
                p.name: {ao.type for ao in assign[p.name][cat]} for p in self.profiles
            }

            for slot_index in range(max_slots):
                eligible_profiles = [p for p in self.profiles if slot_index < self._slots[p.name].get(cat, 0)]
                if not eligible_profiles:
                    break

                best_orb: Optional[Orb] = None
                best_score = -float("inf")
                candidate_debug: List[Dict[str, Any]] = []

                union_types: Set[str] = set()
                for p in eligible_profiles:
                    union_types |= existing_types_per_prof[p.name]

                for orb_type, pool in self._candidates_by_type.items():
                    if orb_type in union_types:
                        continue
                    for orb in pool:
                        orb_id = strong_orb_key(orb)
                        if orb_id in used_ids_global:
                            continue

                        if any(orb.type in existing_types_per_prof[p.name] for p in eligible_profiles):
                            continue
                        if not self._can_assign_to_profiles(orb, eligible_profiles, set_counts):
                            continue

                        combined = 0.0
                        per_prof_details: Dict[str, Dict[str, float]] = {}
                        for p in eligible_profiles:
                            d_set, d_orb = self._marginal_gain(p, orb, set_counts[p.name])
                            coeffs = self._profile_coeffs(p)
                            prof_score = coeffs.set_primary * d_set + coeffs.orb_primary * d_orb
                            combined += p.weight * prof_score
                            per_prof_details[p.name] = {
                                "d_set": d_set,
                                "d_orb": d_orb,
                                "score": prof_score,
                            }

                        tie_break = sum(v["d_set"] + v["d_orb"] for v in per_prof_details.values()) * 1e-6
                        total_score = combined + tie_break
                        if total_score > best_score:
                            best_score = total_score
                            best_orb = orb

                        if self.enable_debug_breakdown:
                            candidate_debug.append(
                                {"orb": orb, "combined": combined, "per_profile": per_prof_details}
                            )

                if best_orb is None:
                    continue

                for p in eligible_profiles:
                    assigned = AssignedOrb(
                        type=getattr(best_orb, "type", ""),
                        set=get_set(best_orb),
                        rarity=getattr(best_orb, "rarity", "Rare"),
                        level=int(getattr(best_orb, "level", 0)),
                        value=float(getattr(best_orb, "value", 0.0)),
                        awakened=awakened_levels(best_orb),
                        slot_index=slot_index,
                    )
                    assign[p.name][cat].append(assigned)
                    set_counts[p.name][assigned.set] += 1
                    existing_types_per_prof[p.name].add(assigned.type)

                used_ids_global.add(strong_orb_key(best_orb))

                if self.enable_debug_breakdown and candidate_debug:
                    self._log_candidate_debug(cat, slot_index, candidate_debug, chosen=best_orb)

        # -------- Fill non-shareable categories (profile order matters) --------
        for prof in profile_order:
            cats_sorted = sorted(
                (cat for cat, slots in self._slots[prof.name].items() if cat not in self.shareable and slots > 0),
                key=lambda cat_name: -self._slots[prof.name][cat_name],
            )
            for cat in cats_sorted:
                slots_needed = self._slots[prof.name][cat]
                types_in_cat = {ao.type for ao in assign[prof.name][cat]}

                for slot_index in range(len(assign[prof.name][cat]), slots_needed):
                    best_orb: Optional[Orb] = None
                    best_score = -float("inf")
                    candidate_debug: List[Dict[str, Any]] = []
                    coeffs = self._profile_coeffs(prof)

                    for orb_type, pool in self._candidates_by_type.items():
                        if orb_type in types_in_cat:
                            continue

                        for orb in pool:
                            orb_id = strong_orb_key(orb)
                            if orb_id in used_ids_global:
                                continue
                            if orb.type in types_in_cat:
                                continue
                            if not self._can_assign_set(prof, orb, set_counts[prof.name]):
                                continue

                            d_set, d_orb = self._marginal_gain(prof, orb, set_counts[prof.name])
                            score = coeffs.set_primary * d_set + coeffs.orb_primary * d_orb
                            tie_break = (d_set + d_orb) * 1e-6
                            total_score = score + tie_break
                            if total_score > best_score:
                                best_score = total_score
                                best_orb = orb

                            if self.enable_debug_breakdown:
                                candidate_debug.append(
                                    {
                                        "orb": orb,
                                        "combined": score,
                                        "per_profile": {
                                            prof.name: {"d_set": d_set, "d_orb": d_orb, "score": score}
                                        },
                                    }
                                )

                    if best_orb is None:
                        self.logger.debug(
                            f"ℹ️ No viable orb for {prof.name}:{cat} slot {slot_index + 1}/{slots_needed}"
                        )
                        break

                    assigned = AssignedOrb(
                        type=getattr(best_orb, "type", ""),
                        set=get_set(best_orb),
                        rarity=getattr(best_orb, "rarity", "Rare"),
                        level=int(getattr(best_orb, "level", 0)),
                        value=float(getattr(best_orb, "value", 0.0)),
                        awakened=awakened_levels(best_orb),
                        slot_index=slot_index,
                    )
                    assign[prof.name][cat].append(assigned)
                    set_counts[prof.name][assigned.set] += 1
                    used_ids_global.add(strong_orb_key(best_orb))
                    types_in_cat.add(assigned.type)

                    if self.enable_debug_breakdown and candidate_debug:
                        self._log_candidate_debug(cat, slot_index, candidate_debug, chosen=best_orb, profile=prof.name)

        # -------- Final scoring + coverage --------
        per_profile: Dict[str, ProfileResult] = {}
        combined_primary = 0.0
        total_requested = 0
        total_filled = 0

        for p in self.profiles:
            set_s, orb_s = self._score_one(p, assign[p.name])
            primary_score, _ = self._primary_secondary(p, set_s, orb_s)
            combined_primary += float(getattr(p, "weight", 1.0) or 1.0) * primary_score

            requested_slots = self._requested_slots_by_profile[p.name]
            filled_slots = sum(len(group) for group in assign[p.name].values())
            is_partial = filled_slots < requested_slots

            total_requested += requested_slots
            total_filled += filled_slots

            per_profile[p.name] = ProfileResult(
                name=p.name,
                set_score=set_s,
                orb_score=orb_s,
                loadout=assign[p.name],
                requested_slots=requested_slots,
                filled_slots=filled_slots,
                is_partial=is_partial,
            )

        return MultiProfileResult(
            profiles=per_profile,
            combined_score=combined_primary,
            requested_slots=total_requested,
            filled_slots=total_filled,
            is_partial=total_filled < total_requested,
        )

    # ---------------- Marginal Gain ----------------
    def _marginal_gain(self, prof: ProfileConfig, orb: Orb, set_count: Counter) -> Tuple[float, float]:
        """Return (d_set, d_orb) marginal contributions for placing `orb`."""
        set_name = get_set(orb)
        c_before = set_count[set_name]
        c_after = c_before + 1
        thresholds = DEFAULT_SET_COUNTS.get(set_name, [])
        tiers_before = sum(1 for t in thresholds if c_before >= t)
        tiers_after = sum(1 for t in thresholds if c_after >= t)
        weight = prof.set_priority.get(set_name, 0.0)
        power = float(getattr(prof, "power", 1.0))

        # Power-aware objective-aligned marginal delta
        d_set = weight * ((tiers_after ** power) - (tiers_before ** power))

        # Progress toward next threshold
        next_threshold = next((t for t in thresholds if t > c_before), None)
        if next_threshold is not None and weight > 0:
            progress = c_after / next_threshold
            d_set += self.alpha * weight * progress

        # Potential term: remaining tier fraction after this addition
        max_tiers = len(thresholds)
        if max_tiers > 0 and weight > 0:
            remaining = max_tiers - tiers_after
            if remaining > 0:
                d_set += self.beta * weight * (remaining / max_tiers)

        try:
            raw = float(getattr(orb, "value", 0.0))
        except Exception:
            raw = 0.0
        base = percentile_within_type(self._type_values, getattr(orb, "type", ""), raw)
        d_orb = base * prof.orb_type_weights.get(getattr(orb, "type", ""), 1.0)

        orb_level = effective_level(orb)
        lvl_tiers = tiers_from_level(orb_level)
        d_orb += prof.orb_level_weights.get(str(orb_level), 0.0)
        d_orb += lvl_tiers * prof.orb_level_weights.get(getattr(orb, "type", ""), 0.0)
        return d_set, d_orb

    # ---------------- Scoring ----------------
    def _score_one(self, prof: ProfileConfig, loadout: Dict[str, List[AssignedOrb]]) -> Tuple[float, float]:
        """Compute (set_score, orb_score) for a single profile."""
        chosen = [ao for group in loadout.values() for ao in group]

        counts = Counter(ao.set for ao in chosen)
        set_score = 0.0
        power = float(getattr(prof, "power", 1.0))
        for set_name, count in counts.items():
            thresholds = DEFAULT_SET_COUNTS.get(set_name)
            if not thresholds:
                continue
            tiers_met = sum(1 for t in thresholds if count >= t)
            if tiers_met <= 0:
                continue
            weight = prof.set_priority.get(set_name, 0.0)
            set_score += weight * (tiers_met ** power)

        orb_score = 0.0
        for ao in chosen:
            try:
                raw = float(getattr(ao, "value", 0.0))
            except Exception:
                raw = 0.0
            base = percentile_within_type(self._type_values, getattr(ao, "type", ""), raw)
            orb_score += base * prof.orb_type_weights.get(getattr(ao, "type", ""), 1.0)

            orb_level = effective_level(ao)
            lvl_tiers = tiers_from_level(orb_level)
            orb_score += prof.orb_level_weights.get(str(orb_level), 0.0)
            orb_score += lvl_tiers * prof.orb_level_weights.get(getattr(ao, "type", ""), 0.0)
        return set_score, orb_score

    def _primary_secondary(self, prof: ProfileConfig, set_s: float, orb_s: float) -> Tuple[float, float]:
        eps = float(getattr(prof, "epsilon", 0.0) or 0.0)
        if getattr(prof, "objective", "sets-first") == "types-first":
            return (orb_s + (eps * set_s if eps else 0.0), set_s)
        return (set_s + (eps * orb_s if eps else 0.0), orb_s)

    def _profile_coeffs(self, prof: ProfileConfig) -> ScoringCoefficients:
        if getattr(prof, "objective", "sets-first") == "sets-first":
            return ScoringCoefficients(set_primary=1.0, orb_primary=0.1)
        return ScoringCoefficients(set_primary=0.1, orb_primary=1.0)

    # ---------------- Constraints ----------------
    def _set_cap(self, set_name: str) -> Optional[int]:
        return SET_MAX_COUNTS.get(set_name)

    def _can_assign_set(self, prof: ProfileConfig, orb: Orb, set_count: Counter) -> bool:
        set_name = get_set(orb)
        cap = self._set_cap(set_name)
        if cap is None:
            return True
        return set_count[set_name] < cap

    def _can_assign_to_profiles(
        self,
        orb: Orb,
        profiles: List[ProfileConfig],
        set_counts: Dict[str, Counter],
    ) -> bool:
        return all(self._can_assign_set(profile, orb, set_counts[profile.name]) for profile in profiles)

    # ---------------- Multi-start helpers ----------------
    def _build_candidates_by_type(self, topk: int) -> Dict[str, List[Orb]]:
        out: Dict[str, List[Orb]] = {}
        for orb_type, typed in self._orbs_by_type_sorted.items():
            out[orb_type] = typed[:topk]
        return out

    def _deterministic_profile_orders(self) -> List[List[ProfileConfig]]:
        """Return a small deterministic set of profile orders for multi-start."""
        if not self.profiles:
            return [[]]

        unique_orders: List[List[ProfileConfig]] = []
        seen: Set[Tuple[str, ...]] = set()

        def push(order: List[ProfileConfig]) -> None:
            key = tuple(p.name for p in order)
            if key in seen:
                return
            seen.add(key)
            unique_orders.append(order)

        push(list(self.profiles))
        push(list(reversed(self.profiles)))
        push(sorted(self.profiles, key=lambda p: float(getattr(p, "weight", 1.0)), reverse=True))
        push(sorted(self.profiles, key=lambda p: float(getattr(p, "weight", 1.0))))

        if len(self.profiles) <= 4:
            for perm in permutations(self.profiles):
                push(list(perm))
                if len(unique_orders) >= MAX_DETERMINISTIC_PERMUTATIONS:
                    break

        return unique_orders

    def _time_budget_exceeded(self, started: float) -> bool:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return elapsed_ms >= float(self.max_time_ms)

    def _pick_better(
        self,
        current: MultiProfileResult | None,
        candidate: MultiProfileResult,
    ) -> MultiProfileResult:
        if current is None:
            return candidate

        current_key = (current.combined_score, current.filled_slots, -int(current.is_partial))
        candidate_key = (candidate.combined_score, candidate.filled_slots, -int(candidate.is_partial))
        return candidate if candidate_key > current_key else current

    # ---------------- Debug Logging ----------------
    def _log_candidate_debug(
        self,
        cat_name: str,
        slot_index: int,
        candidates: List[Dict[str, Any]],
        chosen: Orb,
        profile: str | None = None,
    ) -> None:
        if not candidates:
            return
        sorted_cands = sorted(candidates, key=lambda c: c["combined"], reverse=True)
        top = sorted_cands[: self.debug_top_n]
        header = (
            f"🔍 [{cat_name} slot {slot_index + 1}] Candidate breakdown"
            + (f" ({profile})" if profile else " (shared)")
        )
        self.logger.debug(header)
        for idx, cand in enumerate(top, 1):
            orb = cand["orb"]
            per_prof_parts = []
            for pname, det in cand["per_profile"].items():
                per_prof_parts.append(
                    f"{pname}:d_set={det['d_set']:.3f},d_orb={det['d_orb']:.3f},score={det['score']:.3f}"
                )
            per_prof_str = " | ".join(per_prof_parts)
            self.logger.debug(
                f"   #{idx} {getattr(orb, 'type', '')} — {get_set(orb)} "
                f"(lvl {getattr(orb, 'level', 0)}, val {getattr(orb, 'value', 0.0)}) "
                f"combined={cand['combined']:.3f} :: {per_prof_str}"
            )
        self.logger.debug(
            f"   ➤ Chosen: {getattr(chosen, 'type', '')} — {get_set(chosen)} "
            f"(lvl {getattr(chosen, 'level', 0)}, val {getattr(chosen, 'value', 0.0)})"
        )
        self.logger.debug(f"   (Evaluated {len(candidates)} candidates)")
