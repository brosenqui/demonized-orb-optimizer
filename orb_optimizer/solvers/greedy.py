"""Greedy solver (aligned with beam solver inputs & outputs)

- Consumes the shared parsed `inputs` object prepared by the CLI:
    inputs.orbs                : List[Orb]
    inputs.categories          : List[Category]
    inputs.profiles            : List[ProfileConfig]
    inputs.shareable_categories: Optional[List[str]]

- Optimizer-specific knobs are constructor params:
    topk_per_type, alpha, beta, debug_top_n, enable_debug_breakdown

- Returns the same shape as the beam solver:
    { "combined_score": float,
      "profiles": { name: { "set_score": float, "orb_score": float, "loadout": {...} } },
      "assign": { name: { cat: [Orb, ...], ... }, ... } }
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple, Optional

from ..models import Orb, Category, ProfileConfig
from ..defaults import DEFAULT_SET_COUNTS

# Heuristic defaults
ALPHA_DEFAULT = 0.2   # progress toward next threshold
BETA_DEFAULT  = 0.1   # potential (remaining tiers after adding)
DEBUG_TOP_N_DEFAULT = 5


# ----------------------------- helpers -----------------------------

def tiers_from_level(level: int) -> int:
    """Count level tiers unlocked at 3, 6, 9."""
    return (1 if level >= 3 else 0) + (1 if level >= 6 else 0) + (1 if level >= 9 else 0)


def orb_key(o: Orb) -> tuple:
    """Stable identity for an orb across processes."""
    return (
        getattr(o, "type", None),
        getattr(o, "set_name", None),
        getattr(o, "value", None),
        getattr(o, "level", None),
    )


def _orb_ids(objs: List[Orb] | Tuple[Orb, ...]) -> set[tuple]:
    """Set of stable orb keys for fast collision checks."""
    return {orb_key(o) for o in objs}


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
    """Greedy alternative to the beam solver.

    Construct with:
        GreedyOptimizer(logger=logger, inputs=<shared parsed inputs>, topk_per_type=8, alpha=0.2, beta=0.1, ...)

    Notes
    -----
    - Enforces per-category type uniqueness (no duplicate `type` within a single category).
    - For shareable categories, the same exact orb is placed for ALL profiles (single inventory usage).
    - For non-shareable categories, inventory is exclusive across profiles/categories.
    - Uses a progress/potential-aware set heuristic and percentile-within-type orb quality.
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
        self.P = inputs  # shared parsed data prepared by the CLI/root

        if not getattr(self.P, "profiles", None):
            raise ValueError("At least one profile configuration is required")

        # Optimizer-specific knobs
        self.topk = max(1, int(topk_per_type))
        self.alpha = float(alpha)
        self.beta = float(beta)
        self.debug_top_n = int(debug_top_n)
        self.enable_debug_breakdown = bool(enable_debug_breakdown)

        # Cache common handles
        self.orbs: List[Orb] = self.P.orbs
        self.categories: List[Category] = self.P.categories
        self.profiles: List[ProfileConfig] = self.P.profiles
        self.shareable = set(getattr(self.P, "shareable_categories", None) or [])

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
            typed.sort(key=lambda o: (float(getattr(o, "value", 0.0)) + tiers_from_level(o.level)), reverse=True)
            self._candidates_by_type[t] = typed[: self.topk]

        self.logger.info(
            f"🧩 Greedy optimizer ready (Top-K={self.topk}/type, {len(self.profiles)} profiles)"
        )
        if self.shareable:
            self.logger.info("🔗 Shareable categories: " + ", ".join(sorted(self.shareable)))
        self.logger.info(f"⚙️ Heuristic coefficients: ALPHA={self.alpha:.2f}, BETA={self.beta:.2f}")

    # ---------------- Public API ----------------
    def optimize(self) -> Dict[str, Any]:
        """Run greedy construction and return beam-aligned result dict."""
        # assign[pname][cat] -> List[Orb]
        assign: Dict[str, Dict[str, List[Orb]]] = {p.name: {c.name: [] for c in self.categories} for p in self.profiles}
        set_counts = {p.name: Counter() for p in self.profiles}
        used_ids_global: set[tuple] = set()

        # Process categories: shareable first (fewer constraints), then by descending slots
        ordered = sorted(self.categories, key=lambda c: (0 if c.name in self.shareable else 1, -c.slots))

        for cat in ordered:
            if cat.name in self.shareable:
                self._fill_shared_category(cat, assign, set_counts, used_ids_global)
            else:
                self._fill_independent_category(cat, assign, set_counts, used_ids_global)

        # Build per-profile scores, match beam output keys
        profiles_out: Dict[str, Any] = {}
        for p in self.profiles:
            set_s, orb_s = self._score_one(p, assign[p.name])
            profiles_out[p.name] = {"set_score": set_s, "orb_score": orb_s, "loadout": assign[p.name]}

        primary = self._key(assign)[0]
        return {"combined_score": primary, "profiles": profiles_out, "assign": assign}

    # ---------------- Category Filling ----------------
    def _fill_shared_category(
        self, cat: Category, assign: Dict[str, Dict[str, List[Orb]]], set_counts, used_ids_global
    ):
        for slot_index in range(cat.slots):
            best_orb: Optional[Orb] = None
            best_score = -float("inf")
            candidate_debug: List[Dict[str, Any]] = []

            # Type guard: avoid duplicate types across profiles in this category
            existing_types = {o.type for p in self.profiles for o in assign[p.name][cat.name]}

            for t, pool in self._candidates_by_type.items():
                if t in existing_types:
                    continue
                for orb in pool:
                    k = orb_key(orb)
                    if k in used_ids_global:
                        continue
                    if orb.type in existing_types:
                        continue

                    # Evaluate aggregate marginal across all profiles (weighted)
                    combined = 0.0
                    per_prof_details = {}
                    for p in self.profiles:
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
                # Place the same orb in this category for ALL profiles (inventory is shared)
                for p in self.profiles:
                    assign[p.name][cat.name].append(best_orb)
                    set_counts[p.name][best_orb.set_name] += 1
                used_ids_global.add(orb_key(best_orb))

                if self.enable_debug_breakdown and candidate_debug:
                    self._log_candidate_debug(cat.name, slot_index, candidate_debug, chosen=best_orb)
            else:
                self.logger.warning(f"⚠️ No viable orb found for shared {cat.name} slot {slot_index+1}/{cat.slots}")
                break

    def _fill_independent_category(
        self, cat: Category, assign: Dict[str, Dict[str, List[Orb]]], set_counts, used_ids_global
    ):
        for p in self.profiles:
            types_in_cat = {o.type for o in assign[p.name][cat.name]}
            for slot_index in range(len(assign[p.name][cat.name]), cat.slots):
                best_orb: Optional[Orb] = None
                best_score = -float("inf")
                candidate_debug: List[Dict[str, Any]] = []
                coeffs = self._profile_coeffs(p)

                for t, pool in self._candidates_by_type.items():
                    if t in types_in_cat:
                        continue
                    for orb in pool:
                        k = orb_key(orb)
                        if k in used_ids_global:
                            continue
                        if orb.type in types_in_cat:
                            continue

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
                    assign[p.name][cat.name].append(best_orb)
                    set_counts[p.name][best_orb.set_name] += 1
                    used_ids_global.add(orb_key(best_orb))
                    types_in_cat.add(best_orb.type)

                    if self.enable_debug_breakdown and candidate_debug:
                        self._log_candidate_debug(cat.name, slot_index, candidate_debug, chosen=best_orb, profile=p.name)
                else:
                    self.logger.warning(f"⚠️ No viable orb for {p.name}:{cat.name} slot {slot_index+1}/{cat.slots}")
                    break

    # ---------------- Marginal Gain with Future Potential ----------------
    def _marginal_gain(self, prof: ProfileConfig, orb: Orb, set_count: Counter) -> Tuple[float, float]:
        """Return (d_set, d_orb) marginal contributions for placing `orb`."""
        c_before = set_count[orb.set_name]
        c_after = c_before + 1
        th = DEFAULT_SET_COUNTS.get(orb.set_name, [])
        tiers_before = sum(1 for t in th if c_before >= t)
        tiers_after  = sum(1 for t in th if c_after  >= t)
        d_tiers = max(0, tiers_after - tiers_before)
        weight = prof.set_priority.get(orb.set_name, 0.0)

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
            raw = float(orb.value)
        except Exception:
            raw = 0.0
        base = percentile_within_type(self._type_values, orb.type, raw)
        d_orb = base * prof.orb_type_weights.get(orb.type, 1.0)
        d_orb += tiers_from_level(orb.level) * prof.orb_level_weights.get(orb.type, 0.0)

        return d_set, d_orb

    # ---------------- Scoring ----------------
    def _score_one(self, prof: ProfileConfig, loadout: Dict[str, List[Orb]]) -> Tuple[float, float]:
        """Compute (set_score, orb_score) for a single profile, matching beam's scoring."""
        chosen = [o for group in loadout.values() for o in group]

        # Set score: w * tiers_met^power
        counts = Counter(o.set_name for o in chosen)
        set_score = 0.0
        for s, c in counts.items():
            th = DEFAULT_SET_COUNTS.get(s)
            if not th:
                continue
            tiers_met = sum(1 for t in th if c >= t)
            if tiers_met <= 0:
                continue
            w = prof.set_priority.get(s, 0.0)
            set_score += w * (tiers_met ** prof.power)

        # Orb score: percentile + level tiers with weights
        orb_score = 0.0
        for o in chosen:
            try:
                raw = float(o.value)
            except Exception:
                raw = 0.0
            base = percentile_within_type(self._type_values, o.type, raw)
            orb_score += base * prof.orb_type_weights.get(o.type, 1.0)
            orb_score += tiers_from_level(o.level) * prof.orb_level_weights.get(o.type, 0.0)

        return set_score, orb_score

    def _primary_secondary(self, prof: ProfileConfig, set_s: float, orb_s: float) -> Tuple[float, float]:
        """Match beam's primary/secondary composition."""
        if prof.objective == "types-first":
            return (orb_s + (prof.epsilon * set_s if prof.epsilon else 0.0), set_s)
        return (set_s + (prof.epsilon * orb_s if prof.epsilon else 0.0), orb_s)

    def _key(self, assignments: Dict[str, Dict[str, List[Orb]]]) -> Tuple[float, float]:
        """Combined key across all profiles: (primary, secondary)."""
        primary = 0.0
        secondary = 0.0
        for p in self.profiles:
            set_s, orb_s = self._score_one(p, assignments[p.name])
            p1, p2 = self._primary_secondary(p, set_s, orb_s)
            primary += p.weight * p1
            secondary += p.weight * p2
        return (primary, secondary)

    # ---------------- Coefficients for category fill heuristic ----------------
    def _profile_coeffs(self, prof: ProfileConfig) -> ScoringCoefficients:
        if prof.objective == "sets-first":
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
                f"   #{idx} {orb.type} — {orb.set_name} (lvl {orb.level}, val {orb.value}) "
                f"combined={c['combined']:.3f} :: {per_prof_str}"
            )
        self.logger.debug(
            f"   ➤ Chosen: {chosen.type} — {chosen.set_name} (lvl {chosen.level}, val {chosen.value})"
        )
        self.logger.debug(f"   (Evaluated {len(candidates)} candidates)")
