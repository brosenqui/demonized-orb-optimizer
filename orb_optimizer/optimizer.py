"""Unified optimizer for 1..N profiles (ranked-per-type normalization, BEAM-only).

Key features:
- Works for one or many profiles (PVP, PVE, etc.) with shared inventory.
- Static (baked-in) set thresholds; no external sets.json required.
- Ranked-per-type normalization to prevent cross-type value scale skew.
- Beam search only (+ optional joint refine pass).
- Performance optimizations:
  * Top-K per-category combo pruning (per-profile, configurable).
  * Shared-first exploration on shareable categories.
  * Lightweight copying of assignments for inner-loop speed.

Scoring (per profile p)
-----------------------
  set_score_p = Σ_s [ W_s * (tiers_met_p(s) ** power_p) ]

  orb_score_p = Σ_orb [
      rank_within_type(value) * orb_type_weight_p[type] +
      tiers(level) * orb_level_weight_p[type]
  ]

Objective (per profile p)
-------------------------
  if objective_p == "types-first":
      primary_p   = orb_score_p + ε_p * set_score_p
      secondary_p = set_score_p
  else ("sets-first"):
      primary_p   = set_score_p + ε_p * orb_score_p
      secondary_p = orb_score_p

Combined key across profiles
----------------------------
  primary   = Σ_p weight_p * primary_p
  secondary = Σ_p weight_p * secondary_p

Constraints
-----------
- Per-category: no duplicate orb TYPES within that category assignment (for each profile).
- Global: no orb INSTANCE is reused across the entire multi-profile assignment,
  except in shareable categories *where the instances are exactly the same* (shared).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations, product
from typing import Any, Dict, List, Tuple

from .models import Orb, Category, ProfileConfig
from .defaults import DEFAULT_SET_COUNTS


# ----------------------------- helpers -----------------------------


def _tiers_from_level(level: int) -> int:
    """Return how many level tiers are unlocked at 3, 6, 9."""
    return (
        (1 if level >= 3 else 0) + (1 if level >= 6 else 0) + (1 if level >= 9 else 0)
    )


def _orb_ids(objs: List[Orb] | Tuple[Orb, ...]) -> set[int]:
    """Python instance ids -> use as unique inventory handles."""
    return {id(o) for o in objs}

def _combo_key(combo: tuple[Orb, ...]) -> tuple[int, ...]:
    """Hashable identity for a combo: sorted object ids."""
    return tuple(sorted(id(o) for o in combo))

# --------------------------- Unified Optimizer ---------------------------


class UnifiedOptimizer:
    """Joint beam optimizer for N profiles (N≥1) with ranked-per-type normalization.

    If given one profile, behaves like a single-profile solver.
    If given multiple profiles, searches jointly with a shared inventory.

    Args:
        orbs: inventory of Orb objects.
        categories: list of Category objects (with .name and .slots).
        logger: logger for progress/debug.
        profiles: list of ProfileConfig (length >= 1).
        shareable_categories: names where identical instance combos may be shared (count once).
        topk_per_category: keep only top-K combos per profile per category during expansion.
    """

    def __init__(
        self,
        *,
        orbs: List[Orb],
        categories: List[Category],
        logger,
        profiles: List[ProfileConfig],
        shareable_categories: List[str] | None = None,
        topk_per_category: int = 12,
    ):
        if not profiles:
            raise ValueError("UnifiedOptimizer requires at least one profile.")
        self.orbs = orbs
        self.categories = categories
        self.logger = logger
        self.profiles = list(profiles)
        self.shareable = set(shareable_categories or [])
        self.topk = int(max(1, topk_per_category))

        # Precompute per-type distributions for ranked-per-type normalization
        self._type_values: Dict[str, List[float]] = {}
        buckets: Dict[str, List[float]] = defaultdict(list)
        for o in self.orbs:
            try:
                buckets[o.type].append(float(o.value))
            except Exception:
                buckets[o.type].append(0.0)
        for t, vals in buckets.items():
            vals.sort()
            self._type_values[t] = vals

        # Precompute valid combos per category (no duplicate types)
        self._valid_combos_by_cat: Dict[str, List[Tuple[Orb, ...]]] = {}
        for cat in self.categories:
            combos = [
                c
                for c in combinations(self.orbs, cat.slots)
                if len({o.type for o in c}) == len(c)
            ]
            self._valid_combos_by_cat[cat.name] = combos

        # Build per-profile Top-K combos per category (performance pruning)
        self._topk_by_profile_cat: dict[str, dict[str, list[tuple[Orb, ...]]]] = {}
        for p in self.profiles:
            per_cat: dict[str, list[tuple[Orb, ...]]] = {}
            for cat in self.categories:
                combos = self._valid_combos_by_cat[cat.name]
                scored = [(self._approx_combo_score(p, cat.name, c), c) for c in combos]
                scored.sort(key=lambda x: x[0], reverse=True)
                per_cat[cat.name] = [c for _, c in scored[: self.topk]]
            self._topk_by_profile_cat[p.name] = per_cat

        # Log basics
        names = ", ".join(
            f"{p.name}(w={p.weight:g}, obj={p.objective}, ε={p.epsilon:g}, ᵖ={p.power:g})"
            for p in self.profiles
        )
        self.logger.info(f"👥 Profiles: {names}")
        if self.shareable:
            self.logger.info(
                "🔗 Shareable categories: " + ", ".join(sorted(self.shareable))
            )
        else:
            self.logger.info("🔗 Shareable categories: (none)")
        self.logger.info(f"🎛️ Top-K per category: {self.topk}")

    # --------------------- normalization & scoring ---------------------

    def _percentile_within_type(self, t: str, v: float) -> float:
        vals = self._type_values.get(t)
        if not vals:
            return 0.0
        import bisect

        i = bisect.bisect_left(vals, v)
        j = bisect.bisect_right(vals, v)
        rank = (i + j) / 2.0
        if len(vals) == 1:
            return 1.0
        return rank / (len(vals) - 1)

    def _score_one(
        self, prof: ProfileConfig, loadout: Dict[str, List[Orb]]
    ) -> Tuple[float, float]:
        """Compute (set_score, orb_score) for a single profile."""
        chosen = [o for group in loadout.values() for o in group]

        # Set score (uses static DEFAULT_SET_THRESHOLDS)
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
            set_score += w * (tiers_met**prof.power)

        # Orb score (ranked-per-type + level tiers)
        orb_score = 0.0
        for o in chosen:
            try:
                raw = float(o.value)
            except Exception:
                raw = 0.0
            base = self._percentile_within_type(o.type, raw)
            orb_score += base * prof.orb_type_weights.get(o.type, 1.0)
            orb_score += _tiers_from_level(o.level) * prof.orb_level_weights.get(
                o.type, 0.0
            )

        return set_score, orb_score

    def _primary_secondary(
        self, prof: ProfileConfig, set_s: float, orb_s: float
    ) -> Tuple[float, float]:
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

    # --------------------- heuristics for Top-K pruning ---------------------

    def _approx_combo_score(
        self, prof: ProfileConfig, cat_name: str, combo: tuple[Orb, ...]
    ) -> float:
        """Fast local heuristic to rank combos for pruning.

        Combines a quick orb-quality estimate (ranked value + level tiers) with a
        small optimistic set hint based on the sets present in this combo.
        """
        # orb quality part
        orb_q = 0.0
        for o in combo:
            try:
                raw = float(o.value)
            except Exception:
                raw = 0.0
            base = self._percentile_within_type(o.type, raw)
            orb_q += base * prof.orb_type_weights.get(o.type, 1.0)
            orb_q += _tiers_from_level(o.level) * prof.orb_level_weights.get(
                o.type, 0.0
            )

        # optimistic set hint: light nudge toward high-priority sets
        set_hint = 0.0
        seen_sets = {o.set_name for o in combo}
        for s in seen_sets:
            set_hint += 0.25 * prof.set_priority.get(s, 0.0)  # 25% of set weight

        # combine per objective (just for ordering)
        if prof.objective == "types-first":
            score = orb_q + prof.epsilon * set_hint
        else:
            score = set_hint + prof.epsilon * orb_q
        return score

    # --------------------------- optimization ---------------------------

    def optimize(self, beam_width: int = 200) -> Dict[str, Any]:
        """Run the joint BEAM search (only mode)."""
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
        for p, cmb in zip(self.profiles, choices_per_profile):
            pmap = assign[p.name]
            new_pmap = dict(pmap)
            new_pmap[cat_name] = list(cmb)
            new_assign[p.name] = new_pmap
        return new_assign

    def _beam_search(self, beam_width: int) -> Dict[str, Any]:
        # Start state
        start_assign = {p.name: {c.name: [] for c in self.categories} for p in self.profiles}
        partials = [{"assign": start_assign, "used_ids": set(), "key": (0.0, 0.0)}]

        # Order categories by “hardness”: smallest branching first; non-shareable before shareable.
        cats = sorted(
            self.categories,
            key=lambda c: (self._branching_size(c), 1 if c.name in self.shareable else 0)
        )

        for cat in cats:
            self.logger.debug(f"Evaluating category: {cat.name}")

            def expand_with_lists(partials_in, per_prof_lists):
                out = []
                for state in partials_in:
                    used_ids = state["used_ids"]

                    # 1) Shared-first
                    if cat.name in self.shareable:
                        pool_map = {}
                        for lst in per_prof_lists:
                            for c in lst:
                                pool_map[_combo_key(c)] = c
                        shared_pool = list(pool_map.values())

                        for c in shared_pool:
                            ids = _orb_ids(c)
                            if used_ids & ids:
                                continue
                            new_assign = self._copy_assign_with(state["assign"], cat.name, [c] * len(self.profiles))
                            new_used = used_ids | ids
                            key = self._key(new_assign)
                            out.append({"assign": new_assign, "used_ids": new_used, "key": key})

                    # 2) Divergent pairs (Cartesian over lists)
                    for per_profile_choices in product(*per_prof_lists):
                        id_sets = [_orb_ids(cmb) for cmb in per_profile_choices]

                        if cat.name in self.shareable:
                            # equal-or-disjoint + no overlap with used_ids
                            valid = True
                            for s in id_sets:
                                if used_ids & s:
                                    valid = False
                                    break
                            if not valid:
                                continue
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

                        new_assign = self._copy_assign_with(state["assign"], cat.name, list(per_profile_choices))
                        key = self._key(new_assign)
                        out.append({"assign": new_assign, "used_ids": new_used, "key": key})
                return out

            # Try Top-K
            per_prof_lists_topk = [self._topk_by_profile_cat[p.name][cat.name] for p in self.profiles]
            next_states = expand_with_lists(partials, per_prof_lists_topk)

            # Fallback to FULL lists if Top-K produced nothing
            if not next_states:
                full_lists = [self._valid_combos_by_cat[cat.name] for _ in self.profiles]
                self.logger.warning(
                    f"⚠️ No candidates after Top-K for {cat.name}; retrying with full combo lists "
                    f"(Top-K={self.topk}, beam={beam_width})."
                )
                next_states = expand_with_lists(partials, full_lists)

                if not next_states:
                    total_full = len(self._valid_combos_by_cat[cat.name])
                    self.logger.error(
                        "❌ Still no feasible states after full retry. "
                        f"Category={cat.name}, combos={total_full}, shareable={cat.name in self.shareable}. "
                        "Likely every candidate collides with already-used orbs from previous categories."
                    )
                    # EARLY EXIT (prevents max([]) later)
                    raise RuntimeError(
                        f"No feasible assignments for category '{cat.name}' with current beam/inventory constraints. "
                        "Try increasing --beam or --topk, or removing this category from shareable_categories."
                    )

            next_states.sort(key=lambda s: s["key"], reverse=True)
            partials = next_states[:beam_width]
            self.logger.debug(f"Beam narrowed to {len(partials)} states for {cat.name}")

        # Finish
        best_state = max(partials, key=lambda s: s["key"])
        profiles_out: Dict[str, Any] = {}
        for p in self.profiles:
            set_s, orb_s = self._score_one(p, best_state["assign"][p.name])
            profiles_out[p.name] = {"set_score": set_s, "orb_score": orb_s, "loadout": best_state["assign"][p.name]}

        primary, _ = self._key(best_state["assign"])
        return {"combined_score": primary, "profiles": profiles_out, "assign": best_state["assign"]}

    # --------------------------- refinement ---------------------------

    def refine(
        self, assign: Dict[str, Dict[str, List[Orb]]], max_passes: int = 1
    ) -> Dict[str, Dict[str, List[Orb]]]:
        """Joint greedy refine for N profiles: try single-orb swaps profile-by-profile.

        Accept a swap if the combined key improves and all constraints remain satisfied.
        For N=1, this behaves like a single-profile refine step.
        """
        if max_passes <= 0:
            return assign

        best = {p: {k: list(v) for k, v in assign[p].items()} for p in assign}
        best_key = self._key(best)

        passes = 0
        improved = True
        while improved and passes < max_passes:
            improved = False
            passes += 1

            # Iterate profiles/categories/slots
            for pname, p_assign in list(best.items()):
                for cat in self.categories:
                    group = list(p_assign[cat.name])
                    types_in_cat = {o.type for o in group}
                    current_ids_group = _orb_ids(tuple(group))

                    for i, old in enumerate(group):
                        for new in self.orbs:
                            if id(new) in current_ids_group:
                                continue  # already in this category
                            if new.type != old.type and new.type in types_in_cat:
                                continue  # duplicate type in category

                            # Trial assignment (shallow replacement)
                            trial = {
                                pp: {k: list(v) for k, v in best[pp].items()}
                                for pp in best
                            }
                            tgroup = list(trial[pname][cat.name])
                            tgroup[i] = new
                            trial[pname][cat.name] = tgroup

                            # Check share/disjoint for this category across profiles
                            ids_per_profile = {
                                pp: _orb_ids(tuple(trial[pp][cat.name])) for pp in trial
                            }
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
                                        if (
                                            ids_per_profile[names[a]]
                                            & ids_per_profile[names[b]]
                                        ):
                                            ok = False
                                            break
                                    if not ok:
                                        break
                                if not ok:
                                    continue

                            # Global inventory uniqueness across categories:
                            # - Per profile: no reuse of the same orb across multiple categories
                            # - Across profiles:
                            #     * Non-shareable categories: disallow duplicates
                            #     * Shareable categories: allow duplicates ONLY within the same category
                            ok = True
                            per_profile_used: dict[str, set[int]] = {pp: set() for pp in trial.keys()}
                            cross_profile_used_by_cat: dict[str, set[int]] = {c2.name: set() for c2 in self.categories}

                            for pp, cats_map in trial.items():
                                used_local = per_profile_used[pp]

                                for c2 in self.categories:
                                    ids = _orb_ids(tuple(cats_map[c2.name]))

                                    # 1) Within the same profile, an orb cannot appear in two categories
                                    if used_local & ids:
                                        ok = False
                                        break
                                    used_local |= ids

                                    # 2) Across profiles
                                    if c2.name in self.shareable:
                                        # Shareable category: allow duplicates across profiles
                                        # (identical sharing is allowed). No cross-profile check.
                                        continue
                                    else:
                                        # Non-shareable category: disallow cross-profile duplicates
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
    
    def _branching_size(self, cat) -> int:
        """Approximate branching: product of Top-K per profile for this category."""
        size = 1
        for p in self.profiles:
            size *= max(1, len(self._topk_by_profile_cat[p.name][cat.name]))
        return size
