"""Greedy solver (multi-profile, shared pool; shareables + type-unique per category)

- Inputs:
    inputs.orbs                  : List[Orb]
    inputs.profiles              : List[ProfileConfig]  (EACH profile has .categories: List[Category])
    inputs.shareable_categories  : Optional[List[str]]  # categories where the same orb can be shared across profiles

- Rules:
    • Inventory is global and exclusive: each physical orb (by strong identity) can be used only once overall.
    • For shareable categories, the SAME orb (single inventory item) is placed into all eligible profiles for that category slot,
      then consumed. (So that orb can’t be used again elsewhere.)
    • In ALL categories (shared or not), enforce "no duplicate TYPES within a category" per profile.

- Returns a dataclass result (for API's _dc_to_dict):
    MultiProfileResult(
      profiles = { name: ProfileResult(set_score, orb_score, loadout) },
      combined_score = float
    )
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple, Optional, Set

from ..models import (
    Orb,
    Category,
    ProfileConfig,
    AssignedOrb,
    ProfileResult,
    MultiProfileResult,
)
from ..defaults import DEFAULT_SET_COUNTS

# Heuristic defaults
ALPHA_DEFAULT = 0.2   # progress toward next threshold
BETA_DEFAULT  = 0.1   # potential (remaining tiers after adding)
DEBUG_TOP_N_DEFAULT = 5


# ----------------------------- helpers -----------------------------

def tiers_from_level(level: int) -> int:
    """Count level tiers unlocked at 3, 6, 9."""
    return (1 if level >= 3 else 0) + (1 if level >= 6 else 0) + (1 if level >= 9 else 0)


def get_set(o: Orb) -> str:
    """Robust accessor for set name, accepting either .set or .set."""
    return getattr(o, "set", None) or getattr(o, "set", "") or ""


def strong_orb_key(o: Orb) -> tuple:
    """Strong identity to prevent accidental reuse AND allow true duplicates.

    Priority:
      1) explicit `id` field if present (stable across loads)
      2) synthetic `_idx` field if loader attached one
      3) Python object id as last resort (process-unique)
    """
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
    """Greedy assignment across ALL profiles in one pass (shared pool).

    Key rules:
      - Global exclusive inventory (one physical orb cannot be reused elsewhere).
      - Shareable categories: same chosen orb placed to all eligible profiles for that slot, then consumed.
      - Type-uniqueness per category per profile (no duplicate types in a category), for both shareable & non-shareable.
    """

    def __init__(
        self,
        *,
        logger,
        inputs: Any,
        topk_per_type: int = 8,
        alpha: float = ALPHA_DEFAULT,
        beta: float = BETA_DEFAULT,
        debug_top_n: int = DEBUG_TOP_N_DEFAULT,
        enable_debug_breakdown: bool = True,
    ) -> None:
        self.logger = logger
        self.P = inputs  # shared parsed data prepared by the CLI/API

        if not getattr(self.P, "profiles", None):
            raise ValueError("At least one profile configuration is required")

        # Optimizer-specific knobs
        self.topk = max(1, int(topk_per_type))
        self.alpha = float(alpha)
        self.beta = float(beta)
        self.debug_top_n = int(debug_top_n)
        self.enable_debug_breakdown = bool(enable_debug_breakdown)

        # Cache common handles
        self.orbs: List[Orb] = list(self.P.orbs)
        self.profiles: List[ProfileConfig] = list(self.P.profiles)
        self.shareable: Set[str] = set(getattr(self.P, "shareable_categories", None) or [])

        # Per-profile category -> slots map (must exist; otherwise no assignment)
        self._slots: Dict[str, Dict[str, int]] = {}
        for p in self.profiles:
            cats = getattr(p, "categories", None) or []
            self._slots[p.name] = {c.name: int(c.slots) for c in cats}

        # Set of all categories present across profiles
        self._all_cats: Set[str] = set()
        for slot_map in self._slots.values():
            self._all_cats.update(slot_map.keys())

        # Precompute per-type distributions for percentile ranks
        self._type_values: Dict[str, List[float]] = defaultdict(list)
        for o in self.orbs:
            try:
                self._type_values[o.type].append(float(o.value))
            except Exception:
                self._type_values[o.type].append(0.0)
        for t in self._type_values:
            self._type_values[t].sort()

        # Candidate pruning: keep top-K per type by (value + level tiers)
        self._candidates_by_type: Dict[str, List[Orb]] = defaultdict(list)
        by_type: Dict[str, List[Orb]] = defaultdict(list)
        for o in self.orbs:
            by_type[o.type].append(o)
        for t, typed in by_type.items():
            typed.sort(key=lambda o: (float(getattr(o, "value", 0.0)) + tiers_from_level(getattr(o, "level", 0))), reverse=True)
            self._candidates_by_type[t] = typed[: self.topk]

        self.logger.info(
            f"🧩 Greedy optimizer ready (Top-K={self.topk}/type, {len(self.profiles)} profiles)"
        )
        if self.shareable:
            self.logger.info("🔗 Shareable categories: " + ", ".join(sorted(self.shareable)))
        else:
            self.logger.info("🔗 Shareable categories: (none)")
        self.logger.info(f"⚙️ Heuristic coefficients: ALPHA={self.alpha:.2f}, BETA={self.beta:.2f}")

    # ---------------- Public API ----------------
    def optimize(self) -> MultiProfileResult:
        """Run greedy construction and return a dataclass result."""
        # assign[pname][cat] -> List[AssignedOrb]
        assign: Dict[str, Dict[str, List[AssignedOrb]]] = {
            p.name: {cat: [] for cat in self._slots[p.name].keys()} for p in self.profiles
        }
        set_counts = {p.name: Counter() for p in self.profiles}
        used_ids_global: set[tuple] = set()  # exclusive inventory across profiles/categories

        # -------- Fill shareable categories (same orb to all eligible profiles) --------
        for cat in sorted(self._all_cats):
            if cat not in self.shareable:
                continue
            max_slots = max(self._slots[p.name].get(cat, 0) for p in self.profiles)
            if max_slots <= 0:
                continue

            # track types already used in this category per profile
            existing_types_per_prof: Dict[str, Set[str]] = {
                p.name: {ao.type for ao in assign[p.name][cat]} for p in self.profiles
            }

            for slot_index in range(max_slots):
                # Profiles that still have capacity in this category at this slot index
                eligible_profiles = [p for p in self.profiles if slot_index < self._slots[p.name].get(cat, 0)]
                if not eligible_profiles:
                    break

                best_orb: Optional[Orb] = None
                best_score = -float("inf")
                candidate_debug: List[Dict[str, Any]] = []

                # Union of types already used in this category across eligible profiles
                union_types = set()
                for p in eligible_profiles:
                    union_types |= existing_types_per_prof[p.name]

                for t, pool in self._candidates_by_type.items():
                    if t in union_types:
                        continue  # enforce type uniqueness across this shared slot
                    for orb in pool:
                        k = strong_orb_key(orb)
                        if k in used_ids_global:
                            continue  # orb already consumed elsewhere

                        # also ensure no eligible profile already has this type in the category
                        if any(orb.type in existing_types_per_prof[p.name] for p in eligible_profiles):
                            continue

                        # Evaluate aggregate marginal across eligible profiles (weighted)
                        combined = 0.0
                        per_prof_details = {}
                        for p in eligible_profiles:
                            d_set, d_orb = self._marginal_gain(p, orb, set_counts[p.name])
                            coeffs = self._profile_coeffs(p)
                            prof_score = coeffs.set_primary * d_set + coeffs.orb_primary * d_orb
                            combined += p.weight * prof_score
                            per_prof_details[p.name] = {"d_set": d_set, "d_orb": d_orb, "score": prof_score}

                        # Tiny tiebreak toward higher raw marginal
                        tie_break = sum(v["d_set"] + v["d_orb"] for v in per_prof_details.values()) * 1e-6
                        total_score = combined + tie_break

                        if total_score > best_score:
                            best_score = total_score
                            best_orb = orb

                        if self.enable_debug_breakdown:
                            candidate_debug.append({"orb": orb, "combined": combined, "per_profile": per_prof_details})

                if best_orb:
                    # Place the SAME orb into all eligible profiles; then consume it globally
                    for p in eligible_profiles:
                        assigned = AssignedOrb(
                            type=getattr(best_orb, "type", ""),
                            set=get_set(best_orb),
                            rarity=getattr(best_orb, "rarity", "Rare"),
                            level=int(getattr(best_orb, "level", 0)),
                            value=float(getattr(best_orb, "value", 0.0)),
                            slot_index=slot_index,
                        )
                        assign[p.name][cat].append(assigned)
                        set_counts[p.name][assigned.set] += 1
                        # Enforce type-uniqueness in this category for each profile
                        existing_types_per_prof[p.name].add(assigned.type)

                    used_ids_global.add(strong_orb_key(best_orb))

                    if self.enable_debug_breakdown and candidate_debug:
                        self._log_candidate_debug(cat, slot_index, candidate_debug, chosen=best_orb)
                else:
                    # nothing viable for this shared slot; move to the next slot (there might be a fit later)
                    continue

        # -------- Fill non-shareable categories (exclusive inventory per profile) --------
        for p in self.profiles:
            cats_sorted = sorted(
                (cat for cat, s in self._slots[p.name].items() if cat not in self.shareable and s > 0),
                key=lambda c: -self._slots[p.name][c],
            )
            for cat in cats_sorted:
                slots_needed = self._slots[p.name][cat]
                types_in_cat = {ao.type for ao in assign[p.name][cat]}  # type-uniqueness

                for slot_index in range(len(assign[p.name][cat]), slots_needed):
                    best_orb: Optional[Orb] = None
                    best_score = -float("inf")
                    candidate_debug: List[Dict[str, Any]] = []
                    coeffs = self._profile_coeffs(p)

                    for t, pool in self._candidates_by_type.items():
                        if t in types_in_cat:
                            continue
                        for orb in pool:
                            k = strong_orb_key(orb)
                            if k in used_ids_global:
                                continue  # inventory already consumed elsewhere
                            if orb.type in types_in_cat:
                                continue  # enforce type uniqueness

                            d_set, d_orb = self._marginal_gain(p, orb, set_counts[p.name])
                            score = coeffs.set_primary * d_set + coeffs.orb_primary * d_orb
                            tie_break = (d_set + d_orb) * 1e-6
                            total_score = score + tie_break

                            if total_score > best_score:
                                best_score = total_score
                                best_orb = orb

                            if self.enable_debug_breakdown:
                                candidate_debug.append(
                                    {"orb": orb, "combined": score, "per_profile": {p.name: {"d_set": d_set, "d_orb": d_orb, "score": score}}}
                                )

                    if best_orb:
                        assigned = AssignedOrb(
                            type=getattr(best_orb, "type", ""),
                            set=get_set(best_orb),
                            rarity=getattr(best_orb, "rarity", "Rare"),
                            level=int(getattr(best_orb, "level", 0)),
                            value=float(getattr(best_orb, "value", 0.0)),
                            slot_index=slot_index,
                        )
                        assign[p.name][cat].append(assigned)
                        set_counts[p.name][assigned.set] += 1
                        used_ids_global.add(strong_orb_key(best_orb))
                        types_in_cat.add(assigned.type)

                        if self.enable_debug_breakdown and candidate_debug:
                            self._log_candidate_debug(cat, slot_index, candidate_debug, chosen=best_orb, profile=p.name)
                    else:
                        self.logger.debug(f"ℹ️ No viable orb for {p.name}:{cat} slot {slot_index+1}/{slots_needed}")
                        break

        # -------- Compute per-profile scores & dataclass result --------
        per_profile: Dict[str, ProfileResult] = {}
        combined_primary = 0.0
        for p in self.profiles:
            set_s, orb_s = self._score_one(p, assign[p.name])
            p1, _ = self._primary_secondary(p, set_s, orb_s)
            combined_primary += float(getattr(p, "weight", 1.0) or 1.0) * p1
            per_profile[p.name] = ProfileResult(
                name=p.name,
                set_score=set_s,
                orb_score=orb_s,
                loadout=assign[p.name],
            )

        return MultiProfileResult(
            profiles=per_profile,
            combined_score=combined_primary,
        )

    # ---------------- Marginal Gain with Future Potential ----------------
    def _marginal_gain(self, prof: ProfileConfig, orb: Orb, set_count: Counter) -> Tuple[float, float]:
        """Return (d_set, d_orb) marginal contributions for placing `orb`."""
        set = get_set(orb)
        c_before = set_count[set]
        c_after = c_before + 1
        th = DEFAULT_SET_COUNTS.get(set, [])
        tiers_before = sum(1 for t in th if c_before >= t)
        tiers_after  = sum(1 for t in th if c_after  >= t)
        d_tiers = max(0, tiers_after - tiers_before)
        weight = prof.set_priority.get(set, 0.0)

        # Base marginal set gain (threshold crossing)
        d_set = d_tiers * weight

        # Progress term toward next threshold
        next_th = next((t for t in th if t > c_before), None)
        if next_th is not None and weight > 0:
            progress = c_after / next_th  # (0,1]
            d_set += self.alpha * weight * progress

        # Potential term: fraction of tiers remaining AFTER this addition
        max_tiers = len(th) if th else 0
        if max_tiers > 0 and weight > 0:
            remaining = max_tiers - tiers_after
            if remaining > 0:
                d_set += self.beta * weight * (remaining / max_tiers)

        # Orb quality term (percentile within type + level tiers)
        try:
            raw = float(getattr(orb, "value", 0.0))
        except Exception:
            raw = 0.0
        base = percentile_within_type(self._type_values, getattr(orb, "type", ""), raw)
        d_orb = base * prof.orb_type_weights.get(getattr(orb, "type", ""), 1.0)

        # Optional: level-based component (adjust to match your CLI’s exact convention)
        lvl_tiers = tiers_from_level(getattr(orb, "level", 0))
        d_orb += prof.orb_level_weights.get(str(getattr(orb, "level", 0)), 0.0) * 1.0
        d_orb += lvl_tiers * prof.orb_level_weights.get(getattr(orb, "type", ""), 0.0)

        return d_set, d_orb

    # ---------------- Scoring ----------------
    def _score_one(self, prof: ProfileConfig, loadout: Dict[str, List[AssignedOrb]]) -> Tuple[float, float]:
        """Compute (set_score, orb_score) for a single profile."""
        chosen = [ao for group in loadout.values() for ao in group]

        # Set score: w * tiers_met^power
        counts = Counter(ao.set for ao in chosen)
        set_score = 0.0
        for s, c in counts.items():
            th = DEFAULT_SET_COUNTS.get(s)
            if not th:
                continue
            tiers_met = sum(1 for t in th if c >= t)
            if tiers_met <= 0:
                continue
            w = prof.set_priority.get(s, 0.0)
            set_score += w * (tiers_met ** float(getattr(prof, "power", 1.0)))

        # Orb score: percentile + level tiers with weights
        orb_score = 0.0
        for ao in chosen:
            try:
                raw = float(getattr(ao, "value", 0.0))
            except Exception:
                raw = 0.0
            base = percentile_within_type(self._type_values, getattr(ao, "type", ""), raw)
            orb_score += base * prof.orb_type_weights.get(getattr(ao, "type", ""), 1.0)

            lvl_tiers = tiers_from_level(getattr(ao, "level", 0))
            orb_score += prof.orb_level_weights.get(str(getattr(ao, "level", 0)), 0.0) * 1.0
            orb_score += lvl_tiers * prof.orb_level_weights.get(getattr(ao, "type", ""), 0.0)

        return set_score, orb_score

    def _primary_secondary(self, prof: ProfileConfig, set_s: float, orb_s: float) -> Tuple[float, float]:
        """Primary/secondary composition to mirror beam blending."""
        eps = float(getattr(prof, "epsilon", 0.0) or 0.0)
        if getattr(prof, "objective", "sets-first") == "types-first":
            return (orb_s + (eps * set_s if eps else 0.0), set_s)
        return (set_s + (eps * orb_s if eps else 0.0), orb_s)

    # ---------------- Coefficients for category fill heuristic ----------------
    def _profile_coeffs(self, prof: ProfileConfig) -> ScoringCoefficients:
        if getattr(prof, "objective", "sets-first") == "sets-first":
            return ScoringCoefficients(set_primary=1.0, orb_primary=0.1)
        return ScoringCoefficients(set_primary=0.1, orb_primary=1.0)

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
        header = f"🔍 [{cat_name} slot {slot_index+1}] Candidate breakdown" + (f" ({profile})" if profile else " (shared)")
        self.logger.debug(header)
        for idx, c in enumerate(top, 1):
            orb = c["orb"]
            per_prof_parts = []
            for pname, det in c["per_profile"].items():
                per_prof_parts.append(
                    f"{pname}:d_set={det['d_set']:.3f},d_orb={det['d_orb']:.3f},score={det['score']:.3f}"
                )
            per_prof_str = " | ".join(per_prof_parts)
            self.logger.debug(
                f"   #{idx} {getattr(orb, 'type', '')} — {get_set(orb)} "
                f"(lvl {getattr(orb, 'level', 0)}, val {getattr(orb, 'value', 0.0)}) "
                f"combined={c['combined']:.3f} :: {per_prof_str}"
            )
        self.logger.debug(
            f"   ➤ Chosen: {getattr(chosen, 'type', '')} — {get_set(chosen)} "
            f"(lvl {getattr(chosen, 'level', 0)}, val {getattr(chosen, 'value', 0.0)})"
        )
        self.logger.debug(f"   (Evaluated {len(candidates)} candidates)")
