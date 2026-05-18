"""Unified optimizer (consumes shared parsed Inputs; optimizer-specific knobs
   are constructor params)"""

from __future__ import annotations

import bisect
import math
import concurrent.futures
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from collections import Counter, defaultdict
from dataclasses import asdict
from itertools import combinations
from typing import Any, Dict, List, Tuple, Optional

from ..models import Orb, Category, ProfileConfig, ProfileResult, MultiProfileResult
from ..defaults import DEFAULT_SET_COUNTS
from ..orb_level_bonus import base_orb_level, cumulative_gate_value_for_orb
from ..shareability import enabled_profiles_by_category, normalize_shareability_matrix
from ..shared_summary import build_shared_summary

SET_MAX_COUNTS: dict[str, int] = {
    set_name: max(thresholds)
    for set_name, thresholds in DEFAULT_SET_COUNTS.items()
    if thresholds
}
FLEX_SAMPLE_LIMIT = 250

# ----------------------------- helpers -----------------------------

def _tiers_from_level(level: int) -> int:
    """Return how many level tiers are unlocked at 3, 6, 9."""
    return (1 if level >= 3 else 0) + (1 if level >= 6 else 0) + (1 if level >= 9 else 0)

def _awakened_levels(o: Orb) -> int:
    try:
        value = int(getattr(o, "awakened", 0))
    except Exception:
        value = 0
    return max(0, value)

def orb_key(o: Orb) -> tuple:
    """Stable identity for an orb across processes and duplicate-stat inventories."""
    stable_id = getattr(o, "id", None)
    if stable_id is None:
        stable_id = getattr(o, "_idx", None)
    if stable_id is None:
        stable_id = id(o)
    return (
        stable_id,
        getattr(o, "type", None),
        getattr(o, "set", None),
        getattr(o, "value", None),
        getattr(o, "level", None),
        _awakened_levels(o),
    )


def _orb_ids(objs: List[Orb] | Tuple[Orb, ...]) -> set[tuple]:
    """Set of stable orb keys for fast collision checks."""
    return {orb_key(o) for o in objs}


# --------- Batch scoring for multiprocessing (picklable ctx) ---------

def _score_combo_batch(
    batch: List[tuple[Orb, ...]],
    mp_ctx: Dict[str, Any],
) -> List[tuple[float, tuple[Orb, ...]]]:
    """Score a batch of combinations for either a specific profile or the shared case.

    mp_ctx keys:
      - profile_dict: dict or None
      - remaining_cats_names: List[str]
      - orb_base_scores: Dict[orb_key, float]
      - orb_level_scores: Dict[orb_key, float]
      - profiles_dicts: List[dict]  (for shared averaging)
      - valid_combos_by_cat: Dict[str, List[tuple[Orb,...]]]
    """
    profile_dict = mp_ctx["profile_dict"]
    remaining_names = mp_ctx["remaining_cats_names"]
    base_scores = mp_ctx["orb_base_scores"]
    level_scores = mp_ctx["orb_level_scores"]
    profiles_dicts = mp_ctx["profiles_dicts"]
    valid_combos_by_cat = mp_ctx["valid_combos_by_cat"]

    def approx_combo_score(prof: Dict[str, Any], combo: tuple[Orb, ...]) -> float:
        # Orb quality
        orb_q = 0.0
        for o in combo:
            k = orb_key(o)
            orb_q += base_scores[k] * prof["orb_type_weights"].get(o.type, 1.0)
            orb_q += level_scores[k] * prof["orb_level_weights"].get(o.type, 0.0)

        # Lookahead: flexibility
        if not remaining_names:
            flex = 0.0
        else:
            used = {orb_key(o) for o in combo}
            flex_sum = 0.0
            for future_cat in remaining_names:
                all_combos = valid_combos_by_cat[future_cat]
                total = len(all_combos)
                if total == 0:
                    continue
                combos = all_combos[:FLEX_SAMPLE_LIMIT] if total > FLEX_SAMPLE_LIMIT else all_combos
                free = sum(
                    1 for c in combos
                    if not (used & {orb_key(o) for o in c})
                )
                flex_sum += (free / len(combos))
            flex = flex_sum / len(remaining_names)

        # Soft set hint
        set_hint = 0.0
        for s in {o.set for o in combo}:
            set_hint += 0.25 * prof["set_priority"].get(s, 0.0)

        return (
            orb_q + prof["epsilon"] * set_hint
            if prof["objective"] == "types-first"
            else set_hint + prof["epsilon"] * orb_q
        )

    scored: List[tuple[float, tuple[Orb, ...]]] = []
    if profile_dict is not None:
        for combo in batch:
            scored.append((approx_combo_score(profile_dict, combo), combo))
    else:
        for combo in batch:
            total_score = 0.0
            total_w = 0.0
            for prof in profiles_dicts:
                w = float(prof.get("weight", 1.0))
                total_score += w * approx_combo_score(prof, combo)
                total_w += w
            scored.append(((total_score / total_w) if total_w else 0.0, combo))
    return scored


# --------------------------- Unified Optimizer ---------------------------

class UnifiedOptimizer:
    """Joint beam optimizer for N profiles (N≥1) with matrix-gated strict sharing.

    Construct with:
        UnifiedOptimizer(logger=logger, inputs=<shared parsed inputs>, topk_per_category=12)

    The `inputs` object is expected to expose:
      - inputs.orbs: List[Orb]
      - inputs.profiles: List[ProfileConfig]  (categories are attached per profile)
      - inputs.shareability_matrix: Optional[Dict[str, Dict[str, bool]]]
    """

    def __init__(
        self,
        *,
        logger,
        inputs: Any,
        topk_per_category: int = 20,
        parallelism: str = "auto",
        max_time_ms: int = 5000,
    ):
        self.logger = logger
        self.P = inputs  # shared parsed data prepared by the CLI/root
        if not getattr(self.P, "profiles", None):
            raise ValueError("At least one profile configuration is required")

        # Optimizer-specific knobs
        self.topk = int(max(1, topk_per_category))
        self.parallelism = str(parallelism or "auto").lower()
        self.max_time_ms = max(1, int(max_time_ms))
        # Normalize categories from profile-attached configs (or optional top-level list if present).
        input_categories = getattr(self.P, "categories", None)
        if input_categories:
            self.categories: List[Category] = list(input_categories)
        else:
            cat_slots: Dict[str, int] = {}
            for prof in self.P.profiles:
                for cat in getattr(prof, "categories", None) or []:
                    cat_slots[cat.name] = max(cat_slots.get(cat.name, 0), int(cat.slots))
            self.categories = [Category(name=name, slots=slots) for name, slots in cat_slots.items()]
        if not self.categories:
            raise ValueError("At least one category with slots is required")

        self._slots_by_profile: Dict[str, Dict[str, int]] = {}
        for prof in self.P.profiles:
            self._slots_by_profile[prof.name] = {
                cat.name: int(cat.slots) for cat in (getattr(prof, "categories", None) or [])
            }

        self._shareability_matrix = normalize_shareability_matrix(
            categories=[category.name for category in self.categories],
            profile_names=[profile.name for profile in self.P.profiles],
            shareability_matrix=getattr(self.P, "shareability_matrix", None),
            strict=False,
        )
        self._share_enabled_by_category = enabled_profiles_by_category(self._shareability_matrix)

        # Score caches
        self._orb_base_scores: Dict[tuple, float] = {}
        self._orb_level_scores: Dict[tuple, float] = {}
        self._type_values: Dict[str, List[float]] = {}

        # Precompute distributions for percentile scoring
        buckets: Dict[str, List[float]] = defaultdict(list)
        for o in self.P.orbs:
            try:
                buckets[o.type].append(float(o.value))
            except Exception:
                buckets[o.type].append(0.0)
        for t, vals in buckets.items():
            vals.sort()
            self._type_values[t] = vals

        # Precompute scores
        self._precompute_orb_scores()

        # Precompute valid combos per category (no duplicate types)
        self._valid_combos_by_cat: Dict[str, List[Tuple[Orb, ...]]] = {}
        for cat in self.categories:
            combos = [c for c in combinations(self.P.orbs, cat.slots)
                      if len({o.type for o in c}) == len(c)]
            self._valid_combos_by_cat[cat.name] = combos

        # Reservations (for non-shareable categories)
        self.reserved_orbs = self._calculate_reserved_orbs()

        # Logs
        self.logger.info("📊 Category Analysis:")
        for cat in self.categories:
            total = len(self._valid_combos_by_cat[cat.name])
            slots_needed = cat.slots if self._category_has_sharing(cat.name) else cat.slots * len(self.P.profiles)
            combos_per_slot = (total / slots_needed) if slots_needed else 0.0
            self.logger.info(
                f"   • {cat.name}: {total:,} combos, {slots_needed} slots needed, "
                f"{combos_per_slot:.1f} combos/slot"
                f"{' (Share-enabled)' if self._category_has_sharing(cat.name) else ''}"
            )
        names = ", ".join(
            f"{p.name}(w={p.weight:g}, obj={p.objective}, ε={p.epsilon:g}, ᵖ={p.power:g})"
            for p in self.P.profiles
        )
        self.logger.info(f"👥 Profiles: {names}")
        self.logger.info(
            "🔗 Sharing-enabled categories: "
            + (
                ", ".join(sorted(category for category in self._share_enabled_by_category if self._category_has_sharing(category)))
                if self._share_enabled_by_category
                else "(none)"
            )
        )
        self.logger.info(f"🎛️ Top-K per category: {self.topk}")

    # --------------------- normalization & scoring ---------------------

    def _precompute_orb_scores(self):
        """Precompute and cache base scores for all orbs."""
        self.logger.info("🔄 Precomputing orb scores...")
        for orb in self.P.orbs:
            try:
                raw = float(orb.value)
            except Exception:
                raw = 0.0
            k = orb_key(orb)
            self._orb_base_scores[k] = self._percentile_within_type(orb.type, raw)
            self._orb_level_scores[k] = cumulative_gate_value_for_orb(orb)
        self.logger.info("✓ Finished precomputing scores for %d orbs", len(self.P.orbs))

    def _percentile_within_type(self, t: str, v: float) -> float:
        vals = self._type_values.get(t)
        if not vals:
            return 0.0
        i = bisect.bisect_left(vals, v)
        j = bisect.bisect_right(vals, v)
        rank = (i + j) / 2.0
        if len(vals) == 1:
            return 1.0
        return rank / (len(vals) - 1)

    def _score_one(self, prof: ProfileConfig, loadout: Dict[str, List[Orb]]) -> Tuple[float, float]:
        """Compute (set_score, orb_score) for a single profile."""
        chosen = [o for group in loadout.values() for o in group]

        # Set score
        counts = Counter(o.set for o in chosen)
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

        # Orb score (cached)
        orb_score = 0.0
        for o in chosen:
            k = orb_key(o)
            orb_score += self._orb_base_scores[k] * prof.orb_type_weights.get(o.type, 1.0)
            orb_score += self._orb_level_scores[k] * prof.orb_level_weights.get(o.type, 0.0)

        return set_score, orb_score

    def _primary_secondary(self, prof: ProfileConfig, set_s: float, orb_s: float) -> Tuple[float, float]:
        if prof.objective == "types-first":
            return (orb_s + (prof.epsilon * set_s if prof.epsilon else 0.0), set_s)
        return (set_s + (prof.epsilon * orb_s if prof.epsilon else 0.0), orb_s)

    def _key(self, assignments: Dict[str, Dict[str, List[Orb]]]) -> Tuple[float, float]:
        """Combined key across all profiles: (primary, secondary)."""
        primary = 0.0
        secondary = 0.0
        for p in self.P.profiles:
            set_s, orb_s = self._score_one(p, assignments[p.name])
            p1, p2 = self._primary_secondary(p, set_s, orb_s)
            primary += p.weight * p1
            secondary += p.weight * p2
        return (primary, secondary)

    def _within_set_caps(self, assignments: Dict[str, Dict[str, List[Orb]]]) -> bool:
        for prof in self.P.profiles:
            counts = Counter(o.set for group in assignments[prof.name].values() for o in group)
            for set_name, count in counts.items():
                cap = SET_MAX_COUNTS.get(set_name)
                if cap is not None and count > cap:
                    return False
        return True

    def _set_cap(self, set_name: str) -> Optional[int]:
        return SET_MAX_COUNTS.get(set_name)

    def _marginal_gain(self, prof: ProfileConfig, orb: Orb, set_count: Counter) -> Tuple[float, float]:
        set_name = getattr(orb, "set", None) or ""
        c_before = set_count[set_name]
        c_after = c_before + 1
        thresholds = DEFAULT_SET_COUNTS.get(set_name, [])
        tiers_before = sum(1 for t in thresholds if c_before >= t)
        tiers_after = sum(1 for t in thresholds if c_after >= t)
        weight = prof.set_priority.get(set_name, 0.0)
        power = float(getattr(prof, "power", 1.0))
        d_set = weight * ((tiers_after ** power) - (tiers_before ** power))

        key = orb_key(orb)
        d_orb = self._orb_base_scores[key] * prof.orb_type_weights.get(orb.type, 1.0)
        d_orb += self._orb_level_scores[key] * prof.orb_level_weights.get(orb.type, 0.0)
        return d_set, d_orb

    def _category_has_sharing(self, category_name: str) -> bool:
        return len(self._share_enabled_by_category.get(category_name, set())) >= 2

    def _profiles_can_share(self, category_name: str, left_profile: str, right_profile: str) -> bool:
        enabled = self._share_enabled_by_category.get(category_name, set())
        return left_profile in enabled and right_profile in enabled

    def _strict_sharing_satisfied(self, assignments: Dict[str, Dict[str, List[Orb]]]) -> bool:
        for cat in self.categories:
            enabled = self._share_enabled_by_category.get(cat.name, set())
            if len(enabled) < 2:
                continue
            expected_signature: tuple[tuple, ...] | None = None
            for profile in self.P.profiles:
                if profile.name not in enabled:
                    continue
                combo = assignments[profile.name][cat.name]
                signature = tuple(orb_key(orb) for orb in combo)
                if expected_signature is None:
                    expected_signature = signature
                    continue
                if signature != expected_signature:
                    return False
        return True

    # --------------------------- optimization ---------------------------

    def optimize(self, beam_width: int = 200) -> MultiProfileResult:
        """Run the joint BEAM search optimization."""
        self.logger.info("⚙️ Starting optimization in BEAM mode...")
        self._diag_time_budget_hit = False
        self._diag_candidate_evaluations = 0
        self._diag_set_cap_rejections = 0
        self._diag_categories_processed = 0
        self._diag_no_feasible_categories = 0
        self._diag_expansion_attempts = 0
        self._diag_expansion_valid = 0
        self._diag_parallel_modes: set[str] = set()
        return self._beam_search(beam_width)

    def _copy_assign_with(
        self,
        assign: Dict[str, Dict[str, List[Orb]]],
        cat_name: str,
        choices_per_profile: List[tuple[Orb, ...]],
    ) -> Dict[str, Dict[str, List[Orb]]]:
        """Shallow copy `assign`, replacing only `cat_name` per profile with the given combos."""
        new_assign: Dict[str, Dict[str, List[Orb]]] = {}
        for p, cmb in zip(self.P.profiles, choices_per_profile):
            pmap = assign[p.name]
            new_pmap = dict(pmap)
            new_pmap[cat_name] = list(cmb)
            new_assign[p.name] = new_pmap
        return new_assign

    def _beam_search(self, beam_width: int) -> MultiProfileResult:
        started = time.perf_counter()
        start_assign = {p.name: {c.name: [] for c in self.categories} for p in self.P.profiles}
        partials = [{"assign": start_assign, "used_ids": set(), "key": (0.0, 0.0)}]

        # Order categories (smallest spaces first)
        cats_info = []
        for cat in self.categories:
            total_combos = len(self._valid_combos_by_cat[cat.name])
            slot_demand = cat.slots if self._category_has_sharing(cat.name) else cat.slots * len(self.P.profiles)
            combo_size_score = math.log10(total_combos) if total_combos > 0 else 0.0
            cats_info.append((cat, total_combos, combo_size_score, slot_demand))

        cats_info.sort(
            key=lambda x: (int(x[2] * 100), 0 if self._category_has_sharing(x[0].name) else 1, -x[3])
        )
        self.logger.info("📊 Category processing order (from smallest to largest search space):")
        for i, (cat, total_combos, score, slots) in enumerate(cats_info, 1):
            self.logger.info(
                f"   {i}. {cat.name:<6} - {total_combos:,} combinations"
                f" (log10 score: {score:.1f}) | {slots} "
                f"{'share-enabled ' if self._category_has_sharing(cat.name) else ''}slots"
            )
        cats = [c[0] for c in cats_info]

        for cat_idx, cat in enumerate(cats):
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            if elapsed_ms >= float(self.max_time_ms):
                self._diag_time_budget_hit = True
                self.logger.warning(
                    f"⏱️ Beam time budget reached at {elapsed_ms:.0f}ms; returning best partial assignment."
                )
                break
            adaptive_beam = self._get_adaptive_beam_width(cat_idx, len(cats), beam_width)
            adaptive_topk = self._get_adaptive_topk(cat.name)

            # Remaining cats for lookahead
            remaining_cats = cats[cat_idx + 1:]
            remaining_names = [c.name for c in remaining_cats]

            # Build MP context
            profiles_dicts = [asdict(p) for p in self.P.profiles]
            mp_base_ctx = {
                "remaining_cats_names": remaining_names,
                "orb_base_scores": self._orb_base_scores,
                "orb_level_scores": self._orb_level_scores,
                "profiles_dicts": profiles_dicts,
                "valid_combos_by_cat": self._valid_combos_by_cat,
            }

            # Score combos
            combos = self._valid_combos_by_cat[cat.name]
            total_combos = len(combos)
            batch_size = 200
            num_procs = min(8, max(1, math.ceil(total_combos / max(1, batch_size))))
            batches = [combos[i:i + batch_size] for i in range(0, total_combos, batch_size)]

            scored_combos: List[List[tuple[Orb, ...]]] = []

            def _score_all_batches(profile_dict: Optional[Dict[str, Any]]) -> List[tuple[float, tuple[Orb, ...]]]:
                if total_combos == 0:
                    return []
                ctx = dict(mp_base_ctx)
                ctx["profile_dict"] = profile_dict
                scored: List[tuple[float, tuple[Orb, ...]]] = []

                def _run_parallel(executor_cls: Any, label: str) -> bool:
                    try:
                        with executor_cls(max_workers=num_procs) as executor:
                            future_to_batch = {
                                executor.submit(_score_combo_batch, batch, ctx): i
                                for i, batch in enumerate(batches)
                            }
                            completed = 0
                            for fut in concurrent.futures.as_completed(future_to_batch):
                                batch_idx = future_to_batch[fut]
                                scored.extend(fut.result())
                                completed += len(batches[batch_idx])
                                self._diag_candidate_evaluations += len(batches[batch_idx])
                                self.logger.info(
                                    f"   • [{label}] Evaluated {completed}/{total_combos} combinations "
                                    f"({(completed/total_combos*100 if total_combos else 100):.1f}%)"
                                )
                        self._diag_parallel_modes.add(label)
                        return True
                    except Exception as exc:
                        self.logger.warning(f"⚠️ {label} executor failed ({exc}); falling back.")
                        return False

                def _run_serial() -> None:
                    completed = 0
                    for batch in batches:
                        if ((time.perf_counter() - started) * 1000.0) >= float(self.max_time_ms):
                            self._diag_time_budget_hit = True
                            self.logger.warning(
                                "⏱️ Beam time budget reached during scoring; using partial scored batch set."
                            )
                            break
                        scored.extend(_score_combo_batch(batch, ctx))
                        completed += len(batch)
                        self._diag_candidate_evaluations += len(batch)
                        self.logger.info(
                            f"   • [serial] Evaluated {completed}/{total_combos} combinations "
                            f"({(completed/total_combos*100 if total_combos else 100):.1f}%)"
                        )
                    self._diag_parallel_modes.add("serial")

                if num_procs <= 1 or self.parallelism == "serial":
                    _run_serial()
                elif self.parallelism == "thread":
                    if not _run_parallel(ThreadPoolExecutor, "thread"):
                        _run_serial()
                elif self.parallelism == "process":
                    if not _run_parallel(ProcessPoolExecutor, "process"):
                        if not _run_parallel(ThreadPoolExecutor, "thread"):
                            _run_serial()
                else:  # auto
                    if not _run_parallel(ProcessPoolExecutor, "process"):
                        if not _run_parallel(ThreadPoolExecutor, "thread"):
                            _run_serial()

                scored.sort(key=lambda x: x[0], reverse=True)
                return scored

            for p_idx, p in enumerate(self.P.profiles):
                self.logger.info(
                    f"⏳ Scoring combinations for profile {p.name} ({p_idx + 1}/{len(self.P.profiles)}) "
                    f"using {num_procs} processes"
                )
                scored = _score_all_batches(profile_dict=asdict(p))
                min_required = max(adaptive_topk, int(total_combos * 0.1))
                top = [c for _, c in scored[:min_required]]
                scored_combos.append(top)

            # Expand beam with the chosen lists
            next_states = self._expand_with_lists(partials, scored_combos, cat)

            # Fallback if Top-K produced nothing
            if not next_states:
                full_lists = [self._valid_combos_by_cat[cat.name] for _ in self.P.profiles]
                self.logger.warning(
                    f"⚠️ No candidates after Top-K for {cat.name}; retrying with full combo lists"
                    f"\n   • Top-K: {self.topk}"
                    f"\n   • Beam width: {beam_width}"
                    f"\n   • Full combos per profile: {[len(l) for l in full_lists]}"
                )
                next_states = self._expand_with_lists(partials, full_lists, cat)
                if not next_states:
                    total_full = len(self._valid_combos_by_cat[cat.name])
                    self._diag_no_feasible_categories += 1
                    self.logger.warning(
                        "⚠️ No feasible states after full retry; returning best partial assignment so far. "
                        f"Category={cat.name}, combos={total_full}, share_enabled={self._category_has_sharing(cat.name)}."
                    )
                    break

            next_states.sort(key=lambda s: s["key"], reverse=True)
            partials = next_states[:adaptive_beam]

            self.logger.info(
                f"🔍 Beam state for {cat.name}:"
                f"\n   • Valid states found: {len(next_states)}"
                f"\n   • After beam narrowing: {len(partials)}"
                f"\n   • Top score: {partials[0]['key'][0] if partials else 'N/A'}"
                f"\n   • Score range: "
                f"{(partials[-1]['key'][0] if partials else 'N/A')} - "
                f"{(partials[0]['key'][0] if partials else 'N/A')}"
            )
            self._diag_categories_processed += 1

        # Finish (if no states survive, return best partial start state)
        best_state = max(partials, key=lambda s: s["key"])
        primary, _ = self._key(best_state["assign"])

        per_profile: Dict[str, ProfileResult] = {}
        total_requested = 0
        total_filled = 0
        for p in self.P.profiles:
            set_s, orb_s = self._score_one(p, best_state["assign"][p.name])
            requested_slots = sum(self._slots_by_profile.get(p.name, {}).values())
            filled_slots = sum(len(group) for group in best_state["assign"][p.name].values())
            total_requested += requested_slots
            total_filled += filled_slots
            per_profile[p.name] = ProfileResult(
                name=p.name,
                set_score=set_s,
                orb_score=orb_s,
                loadout=best_state["assign"][p.name],
                requested_slots=requested_slots,
                filled_slots=filled_slots,
                is_partial=filled_slots < requested_slots,
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)

        return MultiProfileResult(
            profiles=per_profile,
            combined_score=primary,
            requested_slots=total_requested,
            filled_slots=total_filled,
            is_partial=total_filled < total_requested,
            shared_summary=build_shared_summary(
                profiles=self.P.profiles,
                assignments=best_state["assign"],
                slots_by_profile=self._slots_by_profile,
                shareability_matrix=self._shareability_matrix,
                candidate_orbs=self.P.orbs,
                marginal_gain_fn=self._marginal_gain,
                primary_coeff_fn=lambda profile: (
                    1.0 if profile.objective == "sets-first" else float(getattr(profile, "epsilon", 0.0) or 0.0),
                    float(getattr(profile, "epsilon", 0.0) or 0.0) if profile.objective == "sets-first" else 1.0,
                ),
                set_cap_fn=self._set_cap,
            ),
            run_diagnostics={
                "algorithm": "beam",
                "duration_ms": elapsed_ms,
                "time_budget_ms": self.max_time_ms,
                "time_budget_hit": bool(self._diag_time_budget_hit),
                "beam_width": int(beam_width),
                "topk_per_category": int(self.topk),
                "parallelism_config": self.parallelism,
                "parallelism_used": sorted(self._diag_parallel_modes),
                "categories_total": len(cats),
                "categories_processed": int(self._diag_categories_processed),
                "candidate_evaluations": int(self._diag_candidate_evaluations),
                "set_cap_rejections": int(self._diag_set_cap_rejections),
                "expansion_attempts": int(self._diag_expansion_attempts),
                "valid_expansions": int(self._diag_expansion_valid),
                "no_feasible_categories": int(self._diag_no_feasible_categories),
            },
        )

    # --------------------------- expansion helper ---------------------------

    def _expand_with_lists(
        self,
        partials_in: List[Dict[str, Any]],
        per_prof_lists: List[List[tuple[Orb, ...]]],
        cat: Category,
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        attempts = 0
        valid_states = 0
        max_attempts_per_state = 1000  # safety
        profile_count = len(self.P.profiles)
        category_enabled = self._share_enabled_by_category.get(cat.name, set())
        sharing_enabled = len(category_enabled) >= 2

        # Filter/prioritize based on reservations
        filtered_lists: List[List[tuple[Orb, ...]]] = []
        for prof_list in per_prof_lists:
            if not sharing_enabled:
                reserved_combos = [
                    combo for combo in prof_list
                    if all(self._can_use_orb(orb, cat) for orb in combo)
                    and any(orb in self.reserved_orbs.get(cat.name, {}).get(orb.type, []) for orb in combo)
                ]
                other_combos = [
                    combo for combo in prof_list
                    if all(self._can_use_orb(orb, cat) for orb in combo) and combo not in reserved_combos
                ]
                filtered = reserved_combos + other_combos
            else:
                filtered = [combo for combo in prof_list if all(self._can_use_orb(orb, cat) for orb in combo)]
            filtered_lists.append(filtered)
        per_prof_lists = filtered_lists

        for state in partials_in:
            used_ids = state["used_ids"]
            options_with_ids: List[List[tuple[tuple[Orb, ...], set[tuple]]]] = []
            has_empty_options = False
            for combos in per_prof_lists:
                profile_options: List[tuple[tuple[Orb, ...], set[tuple]]] = []
                for combo in combos:
                    combo_ids = _orb_ids(combo)
                    if used_ids & combo_ids:
                        continue
                    profile_options.append((combo, combo_ids))
                if not profile_options:
                    has_empty_options = True
                    break
                options_with_ids.append(profile_options)
            if has_empty_options:
                continue

            enabled_indices = (
                sorted(
                    (
                        idx
                        for idx, profile in enumerate(self.P.profiles)
                        if profile.name in category_enabled
                    ),
                    key=lambda idx: len(options_with_ids[idx]),
                )
                if sharing_enabled
                else []
            )
            solo_indices = sorted(
                [idx for idx in range(profile_count) if idx not in enabled_indices],
                key=lambda idx: len(options_with_ids[idx]),
            )

            attempts_this_state = 0
            chosen: Dict[int, tuple[Orb, ...]] = {}

            def finalize_candidate(current_used: set[tuple]) -> None:
                nonlocal attempts, valid_states, attempts_this_state
                if attempts_this_state >= max_attempts_per_state:
                    return
                attempts += 1
                attempts_this_state += 1

                choices: List[tuple[Orb, ...]] = []
                for idx in range(profile_count):
                    combo = chosen.get(idx)
                    if combo is None:
                        return
                    choices.append(combo)

                new_assign = self._copy_assign_with(state["assign"], cat.name, choices)
                if not self._strict_sharing_satisfied(new_assign):
                    return
                if not self._within_set_caps(new_assign):
                    self._diag_set_cap_rejections += 1
                    return
                key = self._key(new_assign)
                out.append({"assign": new_assign, "used_ids": current_used, "key": key})
                valid_states += 1

            def expand_solo(pos: int, current_used: set[tuple]) -> None:
                if attempts_this_state >= max_attempts_per_state:
                    return
                if pos >= len(solo_indices):
                    finalize_candidate(current_used)
                    return

                idx = solo_indices[pos]
                for combo, combo_ids in options_with_ids[idx]:
                    if current_used & combo_ids:
                        continue
                    chosen[idx] = combo
                    expand_solo(pos + 1, current_used | combo_ids)
                    if attempts_this_state >= max_attempts_per_state:
                        return

            def assign_shared_enabled(current_used: set[tuple]) -> None:
                if attempts_this_state >= max_attempts_per_state:
                    return
                if not enabled_indices:
                    expand_solo(0, current_used)
                    return

                option_maps: List[Dict[tuple[tuple, ...], tuple[tuple[Orb, ...], set[tuple]]]] = []
                for idx in enabled_indices:
                    option_map: Dict[tuple[tuple, ...], tuple[tuple[Orb, ...], set[tuple]]] = {}
                    for combo, combo_ids in options_with_ids[idx]:
                        signature = tuple(orb_key(orb) for orb in combo)
                        option_map[signature] = (combo, combo_ids)
                    option_maps.append(option_map)

                shared_signatures = set(option_maps[0].keys())
                for option_map in option_maps[1:]:
                    shared_signatures &= set(option_map.keys())
                if not shared_signatures:
                    return

                ordered_shared = sorted(shared_signatures)
                for signature in ordered_shared:
                    combo, combo_ids = option_maps[0][signature]
                    if current_used & combo_ids:
                        continue
                    for map_idx, idx in enumerate(enabled_indices):
                        chosen[idx] = option_maps[map_idx][signature][0]
                    expand_solo(0, current_used | combo_ids)
                    if attempts_this_state >= max_attempts_per_state:
                        return

            if enabled_indices:
                assign_shared_enabled(set(used_ids))
            else:
                expand_solo(0, set(used_ids))

        self._diag_expansion_attempts += attempts
        self._diag_expansion_valid += valid_states

        if sharing_enabled:
            self.logger.info(
                f"🔗 {cat.name} (Share-enabled) - Attempts: {attempts}, Valid: {valid_states} "
                f"({valid_states/max(1,attempts)*100:.1f}%)"
            )
        else:
            self.logger.info(
                f"📦 {cat.name} (Solo-only) - Attempts: {attempts}, Valid: {valid_states} "
                f"({valid_states/max(1,attempts)*100:.1f}%)"
            )
        return out

    # --------------------------- refinement ---------------------------

    def refine(self, assign: Dict[str, Dict[str, List[Orb]]], max_passes: int = 1) -> Dict[str, Dict[str, List[Orb]]]:
        """Joint greedy refine for N profiles: try single-orb swaps profile-by-profile."""
        if max_passes <= 0:
            return assign

        best = {p: {k: list(v) for k, v in assign[p].items()} for p in assign}
        best_key = self._key(best)

        passes = 0
        improved = True
        while improved and passes < max_passes:
            improved = False
            passes += 1

            for pname, p_assign in list(best.items()):
                for cat in self.categories:
                    group = list(p_assign[cat.name])
                    types_in_cat = {o.type for o in group}
                    current_ids_group = _orb_ids(tuple(group))

                    for i, old in enumerate(group):
                        for new in self.P.orbs:
                            if orb_key(new) in current_ids_group:
                                continue
                            if new.type != old.type and new.type in types_in_cat:
                                continue

                            trial = {pp: {k: list(v) for k, v in best[pp].items()} for pp in best}
                            tgroup = list(trial[pname][cat.name])
                            tgroup[i] = new
                            trial[pname][cat.name] = tgroup

                            # Category-level overlap constraints for the edited category
                            ids_per_profile = {pp: _orb_ids(tuple(trial[pp][cat.name])) for pp in trial}
                            names = list(trial.keys())
                            ok = True
                            for a in range(len(names)):
                                for b in range(a + 1, len(names)):
                                    overlap = ids_per_profile[names[a]] & ids_per_profile[names[b]]
                                    if overlap and not self._profiles_can_share(cat.name, names[a], names[b]):
                                        ok = False
                                        break
                                if not ok:
                                    break
                            if not ok:
                                continue

                            # Global inventory uniqueness constraints
                            ok = True
                            per_profile_used: dict[str, set[tuple]] = {pp: set() for pp in trial.keys()}

                            for pp, cats_map in trial.items():
                                used_local = per_profile_used[pp]
                                for c2 in self.categories:
                                    ids = _orb_ids(tuple(cats_map[c2.name]))
                                    if used_local & ids:
                                        ok = False
                                        break
                                    used_local |= ids
                                if not ok:
                                    break
                            if not ok:
                                continue

                            for c2 in self.categories:
                                ids_by_name = {
                                    name: _orb_ids(tuple(trial[name][c2.name]))
                                    for name in trial.keys()
                                }
                                names = list(ids_by_name.keys())
                                for a in range(len(names)):
                                    for b in range(a + 1, len(names)):
                                        overlap = ids_by_name[names[a]] & ids_by_name[names[b]]
                                        if overlap and not self._profiles_can_share(c2.name, names[a], names[b]):
                                            ok = False
                                            break
                                    if not ok:
                                        break
                                if not ok:
                                    break
                            if not ok:
                                continue

                            if not self._strict_sharing_satisfied(trial):
                                continue

                            if not self._within_set_caps(trial):
                                continue

                            k = self._key(trial)
                            if k > best_key:
                                best = trial
                                best_key = k
                                improved = True
                                break
                        if improved:
                            break
                    if improved:
                        break
                if improved:
                    break

        return best

    # --------------------- small helpers ---------------------

    def _get_adaptive_topk(self, cat_name: str) -> int:
        total = len(self._valid_combos_by_cat[cat_name])
        return min(self.topk, max(10, int(total ** 0.5)))

    def _get_adaptive_beam_width(self, cat_idx: int, total_cats: int, base_width: int) -> int:
        progress = cat_idx / total_cats
        return max(20, int(base_width * (1.0 - (progress * 0.5))))  # Reduce up to 50%

    def _calculate_reserved_orbs(self) -> Dict[str, Dict[str, List[Orb]]]:
        """Reserve top orbs for non-shareable categories with smarter allocation."""
        reserved: Dict[str, Dict[str, List[Orb]]] = {}
        non_shareable_cats = [c for c in self.categories if not self._category_has_sharing(c.name)]
        if not non_shareable_cats:
            return reserved

        # Group orbs by type
        orbs_by_type: Dict[str, List[Orb]] = defaultdict(list)
        for orb in self.P.orbs:
            orbs_by_type[orb.type].append(orb)

        def slots_needed(cat: Category) -> int:
            return cat.slots if self._category_has_sharing(cat.name) else cat.slots * len(self.P.profiles)

        total_slots = sum(slots_needed(c) for c in non_shareable_cats)
        shareable_slots = sum(slots_needed(c) for c in self.categories if self._category_has_sharing(c.name))
        reserve_ratio = (
            min(0.5, total_slots / (total_slots + shareable_slots))
            if (total_slots + shareable_slots)
            else 0.0
        )

        sorted_by_type = {
            t: sorted(
                orbs,
                key=lambda o: float(o.value) + (_tiers_from_level(base_orb_level(o)) * 0.1),
                reverse=True,
            )
            for t, orbs in orbs_by_type.items()
        }

        # First pass: minimal reservations per non-shareable category
        orbs_taken: Dict[str, set] = defaultdict(set)
        for cat in non_shareable_cats:
            cat_reserved: Dict[str, List[Orb]] = defaultdict(list)
            min_slots = cat.slots
            for orb_type, sorted_orbs in sorted_by_type.items():
                available = [o for o in sorted_orbs if orb_key(o) not in orbs_taken[orb_type]]
                take_n = min(len(available), min_slots * len(self.P.profiles))
                take = available[:take_n]
                cat_reserved[orb_type].extend(take)
                orbs_taken[orb_type].update(orb_key(o) for o in take)
            reserved[cat.name] = cat_reserved

        # Second pass: distribute extra by slot weight
        for orb_type, sorted_orbs in sorted_by_type.items():
            available = [o for o in sorted_orbs if orb_key(o) not in orbs_taken[orb_type]]
            extra_reserve = int(len(available) * reserve_ratio)
            if extra_reserve <= 0:
                continue
            weights = {c.name: c.slots for c in non_shareable_cats}
            total_weight = sum(weights.values()) or 1
            for cat_name, weight in weights.items():
                share = int((weight / total_weight) * extra_reserve)
                if share > 0:
                    cat_orbs = available[:share]
                    reserved[cat_name][orb_type].extend(cat_orbs)
                    orbs_taken[orb_type].update(orb_key(o) for o in cat_orbs)
                    del available[:share]

        return reserved

    def _can_use_orb(self, orb: Orb, category: Category) -> bool:
        """Check if an orb can be used in this category based on reservations."""
        if self._category_has_sharing(category.name):
            for cat_name, cat_reserves in self.reserved_orbs.items():
                if orb in cat_reserves.get(orb.type, []):
                    return False
            return True
        else:
            reserved_for_cat = self.reserved_orbs.get(category.name, {}).get(orb.type, [])
            if orb in reserved_for_cat:
                return True
            for cat_name, cat_reserves in self.reserved_orbs.items():
                if cat_name != category.name and orb in cat_reserves.get(orb.type, []):
                    return False
            return True

    def _branching_size(self, cat: Category) -> int:
        total = len(self._valid_combos_by_cat[cat.name])
        if self._category_has_sharing(cat.name):
            return total
        return total * len(self.P.profiles)
