"""Unified optimizer (consumes shared parsed Inputs; optimizer-specific knobs
   are constructor params)"""

from __future__ import annotations

import bisect
import math
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor
from collections import Counter, defaultdict
from dataclasses import asdict
from itertools import combinations, product
from typing import Any, Dict, List, Tuple, Optional

from ..models import Orb, Category, ProfileConfig
from ..defaults import DEFAULT_SET_COUNTS


# ----------------------------- helpers -----------------------------

def _tiers_from_level(level: int) -> int:
    """Return how many level tiers are unlocked at 3, 6, 9."""
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


def _combo_key(combo: tuple[Orb, ...]) -> tuple:
    """Hashable identity for a combo: sorted stable keys."""
    return tuple(sorted(orb_key(o) for o in combo))


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
                total = len(valid_combos_by_cat[future_cat])
                if total == 0:
                    continue
                free = sum(
                    1 for c in valid_combos_by_cat[future_cat]
                    if not (used & {orb_key(o) for o in c})
                )
                flex_sum += (free / total)
            flex = flex_sum / len(remaining_names)

        # Soft set hint
        set_hint = 0.0
        for s in {o.set_name for o in combo}:
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
    """Joint beam optimizer for N profiles (N≥1) with ranked-per-type normalization.

    Construct with:
        UnifiedOptimizer(logger=logger, inputs=<shared parsed inputs>, topk_per_category=12)

    The `inputs` object is expected to expose:
      - inputs.orbs: List[Orb]
      - inputs.categories: List[Category]
      - inputs.profiles: List[ProfileConfig]
      - inputs.shareable_categories: Optional[List[str]]
    (Duck-typed; no hard import from the CLI module.)
    """

    def __init__(self, *, logger, inputs: Any, topk_per_category: int = 12):
        self.logger = logger
        self.P = inputs  # shared parsed data prepared by the CLI/root
        if not getattr(self.P, "profiles", None):
            raise ValueError("At least one profile configuration is required")

        # Optimizer-specific knobs
        self.topk = int(max(1, topk_per_category))
        self.shareable = set(getattr(self.P, "shareable_categories", None) or [])

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
        for cat in self.P.categories:
            combos = [c for c in combinations(self.P.orbs, cat.slots)
                      if len({o.type for o in c}) == len(c)]
            self._valid_combos_by_cat[cat.name] = combos

        # Reservations (for non-shareable categories)
        self.reserved_orbs = self._calculate_reserved_orbs()

        # Logs
        self.logger.info("📊 Category Analysis:")
        for cat in self.P.categories:
            total = len(self._valid_combos_by_cat[cat.name])
            slots_needed = cat.slots if cat.name in self.shareable else cat.slots * len(self.P.profiles)
            combos_per_slot = (total / slots_needed) if slots_needed else 0.0
            self.logger.info(
                f"   • {cat.name}: {total:,} combos, {slots_needed} slots needed, "
                f"{combos_per_slot:.1f} combos/slot"
                f"{' (Shareable)' if cat.name in self.shareable else ''}"
            )
        names = ", ".join(
            f"{p.name}(w={p.weight:g}, obj={p.objective}, ε={p.epsilon:g}, ᵖ={p.power:g})"
            for p in self.P.profiles
        )
        self.logger.info(f"👥 Profiles: {names}")
        self.logger.info(
            "🔗 Shareable categories: " + (", ".join(sorted(self.shareable)) if self.shareable else "(none)")
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
            self._orb_level_scores[k] = _tiers_from_level(orb.level)
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

    # --------------------------- optimization ---------------------------

    def optimize(self, beam_width: int = 200) -> Dict[str, Dict[str, Any]]:
        """Run the joint BEAM search optimization."""
        self.logger.info("⚙️ Starting optimization in BEAM mode...")
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

    def _beam_search(self, beam_width: int) -> Dict[str, Any]:
        start_assign = {p.name: {c.name: [] for c in self.P.categories} for p in self.P.profiles}
        partials = [{"assign": start_assign, "used_ids": set(), "key": (0.0, 0.0)}]

        # Order categories (smallest spaces first)
        cats_info = []
        for cat in self.P.categories:
            total_combos = len(self._valid_combos_by_cat[cat.name])
            slot_demand = cat.slots if cat.name in self.shareable else cat.slots * len(self.P.profiles)
            combo_size_score = math.log10(total_combos) if total_combos > 0 else 0.0
            cats_info.append((cat, total_combos, combo_size_score, slot_demand))

        cats_info.sort(key=lambda x: (int(x[2] * 100), 0 if x[0].name in self.shareable else 1, -x[3]))
        self.logger.info("📊 Category processing order (from smallest to largest search space):")
        for i, (cat, total_combos, score, slots) in enumerate(cats_info, 1):
            self.logger.info(
                f"   {i}. {cat.name:<6} - {total_combos:,} combinations"
                f" (log10 score: {score:.1f}) | {slots} {'shared ' if cat.name in self.shareable else ''}slots"
            )
        cats = [c[0] for c in cats_info]

        for cat_idx, cat in enumerate(cats):
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
            batch_size = 1000
            num_procs = min(8, max(1, math.ceil(total_combos / max(1, batch_size))))
            batches = [combos[i:i + batch_size] for i in range(0, total_combos, batch_size)]

            scored_combos: List[List[tuple[Orb, ...]]] = []

            def _score_all_batches(profile_dict: Optional[Dict[str, Any]]) -> List[tuple[float, tuple[Orb, ...]]]:
                if total_combos == 0:
                    return []
                ctx = dict(mp_base_ctx)
                ctx["profile_dict"] = profile_dict
                scored: List[tuple[float, tuple[Orb, ...]]] = []
                with ProcessPoolExecutor(max_workers=num_procs) as executor:
                    future_to_batch = {executor.submit(_score_combo_batch, batch, ctx): i for i, batch in enumerate(batches)}
                    completed = 0
                    for fut in concurrent.futures.as_completed(future_to_batch):
                        batch_idx = future_to_batch[fut]
                        scored.extend(fut.result())
                        completed += len(batches[batch_idx])
                        self.logger.info(
                            f"   • Evaluated {completed}/{total_combos} combinations "
                            f"({(completed/total_combos*100 if total_combos else 100):.1f}%)"
                        )
                scored.sort(key=lambda x: x[0], reverse=True)
                return scored

            if cat.name in self.shareable:
                self.logger.info(f"⏳ Scoring combinations for shared category {cat.name} using {num_procs} processes")
                scored = _score_all_batches(profile_dict=None)
                min_required = max(adaptive_topk, int(total_combos * 0.1))
                top = [c for _, c in scored[:min_required]]
                scored_combos.extend([top] * len(self.P.profiles))
            else:
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
                    self.logger.error(
                        "❌ Still no feasible states after full retry. "
                        f"Category={cat.name}, combos={total_full}, shareable={cat.name in self.shareable}. "
                        "Likely every candidate collides with already-used orbs from previous categories."
                    )
                    raise RuntimeError(
                        f"No feasible assignments for category '{cat.name}' with current beam/inventory constraints. "
                        "Try increasing --beam or --topk, or removing this category from shareable_categories."
                    )

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

        # Finish
        best_state = max(partials, key=lambda s: s["key"])
        profiles_out: Dict[str, Any] = {}
        for p in self.P.profiles:
            set_s, orb_s = self._score_one(p, best_state["assign"][p.name])
            profiles_out[p.name] = {"set_score": set_s, "orb_score": orb_s, "loadout": best_state["assign"][p.name]}
        primary, _ = self._key(best_state["assign"])
        return {"combined_score": primary, "profiles": profiles_out, "assign": best_state["assign"]}

    # --------------------------- expansion helper ---------------------------

    def _expand_with_lists(
        self,
        partials_in: List[Dict[str, Any]],
        per_prof_lists: List[List[tuple[Orb, ...]]],
        cat: Category,
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        shared_attempts = divergent_attempts = 0
        shared_valid = divergent_valid = 0
        max_attempts_per_state = 1000  # safety

        # Filter/prioritize based on reservations
        filtered_lists: List[List[tuple[Orb, ...]]] = []
        for prof_list in per_prof_lists:
            if cat.name not in self.shareable:
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

            # 1) Shared-first
            if cat.name in self.shareable:
                pool_map: Dict[tuple, tuple[Orb, ...]] = {}
                for lst in per_prof_lists:
                    for c in lst:
                        pool_map[_combo_key(c)] = c
                for c in pool_map.values():
                    shared_attempts += 1
                    ids = _orb_ids(c)
                    if used_ids & ids:
                        continue
                    new_assign = self._copy_assign_with(state["assign"], cat.name, [c] * len(self.P.profiles))
                    new_used = used_ids | ids
                    key = self._key(new_assign)
                    out.append({"assign": new_assign, "used_ids": new_used, "key": key})
                    shared_valid += 1

            # 2) Divergent (Cartesian)
            attempts_this_state = 0
            for choices in product(*per_prof_lists):
                attempts_this_state += 1
                if attempts_this_state > max_attempts_per_state:
                    break

                divergent_attempts += 1
                id_sets = [_orb_ids(cmb) for cmb in choices]

                if cat.name in self.shareable:
                    # equal-or-disjoint + no overlap with used_ids
                    if any(used_ids & s for s in id_sets):
                        continue
                    valid = True
                    for i in range(len(id_sets)):
                        for j in range(i + 1, len(id_sets)):
                            if id_sets[i] != id_sets[j] and (id_sets[i] & id_sets[j]):
                                valid = False
                                break
                        if not valid:
                            break
                    if not valid:
                        continue
                    new_used = set(used_ids)
                    for s in id_sets:
                        new_used |= s
                else:
                    # Non-shareable: pairwise disjoint and disjoint from used_ids
                    new_used = set(used_ids)
                    valid = True
                    for s in id_sets:
                        if new_used & s:
                            valid = False
                            break
                        new_used |= s
                    if not valid:
                        continue
                    for i in range(len(id_sets)):
                        for j in range(i + 1, len(id_sets)):
                            if id_sets[i] & id_sets[j]:
                                valid = False
                                break
                        if not valid:
                            break
                    if not valid:
                        continue

                new_assign = self._copy_assign_with(state["assign"], cat.name, list(choices))
                key = self._key(new_assign)
                out.append({"assign": new_assign, "used_ids": new_used, "key": key})
                divergent_valid += 1

        # Logs
        if cat.name in self.shareable:
            self.logger.info(
                f"🔗 {cat.name} (Shareable) - Shared attempts: {shared_attempts}, Valid: {shared_valid} "
                f"({shared_valid/max(1,shared_attempts)*100:.1f}%) | Divergent attempts: {divergent_attempts}, "
                f"Valid: {divergent_valid} ({divergent_valid/max(1,divergent_attempts)*100:.1f}%)"
            )
        else:
            self.logger.info(
                f"📦 {cat.name} (Non-shareable) - Attempts: {divergent_attempts}, Valid: {divergent_valid} "
                f"({divergent_valid/max(1,divergent_attempts)*100:.1f}%)"
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
                for cat in self.P.categories:
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

                            # Category-level sharing/disjoint
                            ids_per_profile = {pp: _orb_ids(tuple(trial[pp][cat.name])) for pp in trial}
                            if cat.name in self.shareable:
                                ok = True
                                names = list(trial.keys())
                                for a in range(len(names)):
                                    for b in range(a + 1, len(names)):
                                        A = ids_per_profile[names[a]]
                                        B = ids_per_profile[names[b]]
                                        if A != B and (A & B):
                                            ok = False
                                            break
                                    if not ok:
                                        break
                                if not ok:
                                    continue
                            else:
                                ok = True
                                names = list(trial.keys())
                                for a in range(len(names)):
                                    for b in range(a + 1, len(names)):
                                        if ids_per_profile[names[a]] & ids_per_profile[names[b]]:
                                            ok = False
                                            break
                                    if not ok:
                                        break
                                if not ok:
                                    continue

                            # Global inventory uniqueness constraints
                            ok = True
                            per_profile_used: dict[str, set[tuple]] = {pp: set() for pp in trial.keys()}
                            cross_profile_used_by_cat: dict[str, set[tuple]] = {c2.name: set() for c2 in self.P.categories}

                            for pp, cats_map in trial.items():
                                used_local = per_profile_used[pp]
                                for c2 in self.P.categories:
                                    ids = _orb_ids(tuple(cats_map[c2.name]))
                                    if used_local & ids:
                                        ok = False
                                        break
                                    used_local |= ids
                                    if c2.name in self.shareable:
                                        continue
                                    if cross_profile_used_by_cat[c2.name] & ids:
                                        ok = False
                                        break
                                    cross_profile_used_by_cat[c2.name] |= ids
                                if not ok:
                                    break
                            if not ok:
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
        non_shareable_cats = [c for c in self.P.categories if c.name not in self.shareable]
        if not non_shareable_cats:
            return reserved

        # Group orbs by type
        orbs_by_type: Dict[str, List[Orb]] = defaultdict(list)
        for orb in self.P.orbs:
            orbs_by_type[orb.type].append(orb)

        def slots_needed(cat: Category) -> int:
            return cat.slots if cat.name in self.shareable else cat.slots * len(self.P.profiles)

        total_slots = sum(slots_needed(c) for c in non_shareable_cats)
        shareable_slots = sum(slots_needed(c) for c in self.P.categories if c.name in self.shareable)
        reserve_ratio = (
            min(0.5, total_slots / (total_slots + shareable_slots))
            if (total_slots + shareable_slots)
            else 0.0
        )

        sorted_by_type = {t: sorted(orbs, key=lambda o: float(o.value), reverse=True) for t, orbs in orbs_by_type.items()}

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
        if category.name in self.shareable:
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
        if cat.name in self.shareable:
            return total
        return total * len(self.P.profiles)
