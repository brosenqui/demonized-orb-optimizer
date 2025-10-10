"""Unified optimizer"""

from __future__ import annotations

import bisect
from collections import Counter, defaultdict
from itertools import combinations, product
from typing import Any, Dict, List, Tuple

from .models import Orb, Category, ProfileConfig
from .defaults import DEFAULT_SET_COUNTS

import weakref
from .memory_utils import monitor_memory, get_memory_usage_mb

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
        memory_limit_mb: Memory limit in MB before forcing cleanup (default: 1024).
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
        memory_limit_mb: int = 1024,
    ):
        if not profiles:
            raise ValueError("At least one profile configuration is required")

        # Validate shareable categories exist
        if shareable_categories:
            cat_names = {c.name for c in categories}
            invalid = set(shareable_categories) - cat_names
            if invalid:
                raise ValueError(f"Unknown shareable categories: {invalid}")

        self.memory_limit_mb = memory_limit_mb
        self._score_cache = weakref.WeakKeyDictionary()
        self.orbs = orbs
        self.categories = categories
        self.logger = logger
        self.profiles = list(profiles)
        self.shareable = set(shareable_categories or [])
        self.topk = int(max(1, topk_per_category))

        # Initialize score caches
        self._orb_base_scores = {}
        self._orb_level_scores = {}
        self._type_values = {}

        # Precompute per-type distributions for ranked-per-type normalization
        buckets: Dict[str, List[float]] = defaultdict(list)
        for o in self.orbs:
            try:
                buckets[o.type].append(float(o.value))
            except Exception:
                buckets[o.type].append(0.0)
        for t, vals in buckets.items():
            vals.sort()
            self._type_values[t] = vals

        # Now precompute orb scores using the type values
        self._precompute_orb_scores()
        
        # Reserve orbs for non-shareable categories
        self.reserved_orbs = self._calculate_reserved_orbs()

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

        def get_slots_needed(cat: Category) -> int:
            """Calculate actual slots needed considering shareability."""
            return cat.slots if cat.name in self.shareable else cat.slots * len(self.profiles)
        
        # Log combo statistics per category
        self.logger.info("📊 Category Analysis:")
        for cat in self.categories:
            total_combos = len(self._valid_combos_by_cat[cat.name])
            slots_needed = get_slots_needed(cat)
            self.logger.info(
                f"   • {cat.name}: {total_combos:,} combos, "
                f"{slots_needed} slots needed, "
                f"{total_combos/slots_needed:.1f} combos/slot"
                f"{' (Shareable)' if cat.name in self.shareable else ''}"
            )

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

    def _precompute_orb_scores(self):
        """Precompute and cache base scores for all orbs."""
        self.logger.info("🔄 Precomputing orb scores...")
        
        # Precompute base scores (percentiles)
        for orb in self.orbs:
            try:
                raw = float(orb.value)
            except Exception:
                raw = 0.0
            self._orb_base_scores[id(orb)] = self._percentile_within_type(orb.type, raw)
            # Cache level scores
            self._orb_level_scores[id(orb)] = _tiers_from_level(orb.level)
            
        self.logger.info("✓ Finished precomputing scores for %d orbs", len(self.orbs))

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

        # Orb score (using cached scores)
        orb_score = 0.0
        for o in chosen:
            base = self._orb_base_scores[id(o)]
            level_score = self._orb_level_scores[id(o)]
            orb_score += base * prof.orb_type_weights.get(o.type, 1.0)
            orb_score += level_score * prof.orb_level_weights.get(o.type, 0.0)

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
        self, prof: ProfileConfig, cat_name: str, combo: tuple[Orb, ...], 
        remaining_cats: List[Category] | None = None
    ) -> float:
        """Score a combo considering both immediate value and future flexibility.
        
        Args:
            prof: Profile configuration
            cat_name: Category name
            combo: Tuple of orbs to evaluate
            remaining_cats: List of categories that still need to be processed
        """
        # Base score from orb quality (using cached scores)
        orb_q = 0.0
        for o in combo:
            base = self._orb_base_scores[id(o)]
            level_score = self._orb_level_scores[id(o)]
            orb_q += base * prof.orb_type_weights.get(o.type, 1.0)
            orb_q += level_score * prof.orb_level_weights.get(o.type, 0.0)
            
        # Add flexibility score if we have remaining categories
        flexibility_score = 0.0
        if remaining_cats:
            used_orbs = set(id(o) for o in combo)
            available_orbs = set(id(o) for o in self.orbs) - used_orbs
            
            # Check how many valid combinations remain for each category
            for future_cat in remaining_cats:
                valid_future_count = sum(
                    1 for c in self._valid_combos_by_cat[future_cat.name]
                    if not (used_orbs & set(id(o) for o in c))
                )
                total_combos = len(self._valid_combos_by_cat[future_cat.name])
                if total_combos > 0:
                    flexibility_score += valid_future_count / total_combos
                    
            # Normalize by number of remaining categories
            flexibility_score /= len(remaining_cats)

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

    @monitor_memory()
    def optimize(self, beam_width: int = 200) -> Dict[str, Dict[str, Any]]:
        """Run the joint BEAM search optimization.

        Args:
            beam_width: Width of the beam search (default: 200)

        Returns:
            Dict containing:
                - combined_score: float, The final combined score across all profiles
                - profiles: Dict[str, Dict[str, Any]], Per-profile results and scores
                - assign: Dict[str, Dict[str, List[Orb]]], Final assignments per profile
        """
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

    @monitor_memory()
    def _beam_search(self, beam_width: int) -> Dict[str, Any]:
        # Start state
        start_assign = {
            p.name: {c.name: [] for c in self.categories} for p in self.profiles
        }
        partials = [{"assign": start_assign, "used_ids": set(), "key": (0.0, 0.0)}]

        # Log initial memory usage
        self.logger.debug(f"Initial memory usage: {get_memory_usage_mb():.1f} MB")

        # sort categories by “hardness”: shareable first, then smallest branching
        cats = sorted(self.categories, key=self._category_sort_key)
        self.logger.info(
            f"Category processing order: {', '.join(c.name for c in cats)}"
        )

        for cat_idx, cat in enumerate(cats):
            # Calculate adaptive parameters
            adaptive_beam = self._get_adaptive_beam_width(cat_idx, len(cats), beam_width)
            adaptive_topk = self._get_adaptive_topk(cat.name)
            self.logger.debug(f"Evaluating category: {cat.name}")

            def expand_with_lists(partials_in, per_prof_lists):
                out = []
                shared_attempts = 0
                divergent_attempts = 0
                shared_valid = 0
                divergent_valid = 0
                max_attempts_per_state = 1000  # Configurable limit

                # Filter and prioritize lists based on reservation
                self.logger.info(f"📋 Filtering combinations based on reservations...")
                filtered_lists = []
                for prof_idx, prof_list in enumerate(per_prof_lists):
                    self.logger.info(
                        f"   • Processing profile {prof_idx + 1}/{len(per_prof_lists)} "
                        f"({len(prof_list)} combinations)"
                    )
                    # For non-shareable categories, prioritize combos using reserved orbs
                    if cat.name not in self.shareable:
                        reserved_combos = [
                            combo for combo in prof_list
                            if all(self._can_use_orb(orb, cat) for orb in combo)
                            and any(orb in self.reserved_orbs.get(cat.name, {}).get(orb.type, []) 
                                  for orb in combo)
                        ]
                        other_combos = [
                            combo for combo in prof_list
                            if all(self._can_use_orb(orb, cat) for orb in combo)
                            and combo not in reserved_combos
                        ]
                        filtered = reserved_combos + other_combos
                    else:
                        filtered = [
                            combo for combo in prof_list 
                            if all(self._can_use_orb(orb, cat) for orb in combo)
                        ]
                    filtered_lists.append(filtered)
                
                # Use filtered lists instead of original
                per_prof_lists = filtered_lists

                for state_idx, state in enumerate(partials_in):
                    attempts_this_state = 0
                    used_ids = state["used_ids"]

                    # 1) Shared-first
                    if cat.name in self.shareable:
                        self.logger.info("🔄 Trying shared combinations...")
                        pool_map = {}
                        for lst in per_prof_lists:
                            for c in lst:
                                pool_map[_combo_key(c)] = c
                        shared_pool = list(pool_map.values())
                        self.logger.info(
                            f"   • Found {len(shared_pool)} unique combinations "
                            f"to try across profiles"
                        )

                        for c in shared_pool:
                            shared_attempts += 1
                            ids = _orb_ids(c)
                            if used_ids & ids:
                                continue
                            new_assign = self._copy_assign_with(
                                state["assign"], cat.name, [c] * len(self.profiles)
                            )
                            new_used = used_ids | ids
                            key = self._key(new_assign)
                            out.append(
                                {"assign": new_assign, "used_ids": new_used, "key": key}
                            )
                            shared_valid += 1

                    # 2) Divergent pairs (Cartesian over lists)
                    total_possible = 1
                    for lst in per_prof_lists:
                        total_possible *= len(lst)
                    self.logger.info(
                        f"   • Evaluating state {state_idx + 1}/{len(partials_in)} "
                        f"(max {min(total_possible, max_attempts_per_state)} attempts)"
                    )
                    
                    attempts_logged = 0
                    for per_profile_choices in product(*per_prof_lists):
                        attempts_this_state += 1
                        if attempts_this_state % 1000 == 0:  # Log progress every 1000 attempts
                            self.logger.info(
                                f"     ↳ Processed {attempts_this_state} combinations, "
                                f"found {divergent_valid} valid"
                            )
                            attempts_logged = attempts_this_state
                            
                        if attempts_this_state > max_attempts_per_state:
                            if attempts_this_state > attempts_logged:
                                self.logger.info(
                                    f"     ↳ Reached attempt limit ({max_attempts_per_state}). "
                                    f"Found {divergent_valid} valid combinations"
                                )
                            break  # Early exit if we've tried too many combinations

                        divergent_attempts += 1
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
                                    if id_sets[i] != id_sets[j] and (
                                        id_sets[i] & id_sets[j]
                                    ):
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

                        new_assign = self._copy_assign_with(
                            state["assign"], cat.name, list(per_profile_choices)
                        )
                        key = self._key(new_assign)
                        out.append(
                            {"assign": new_assign, "used_ids": new_used, "key": key}
                        )
                        divergent_valid += 1

                # Log detailed statistics for this expansion
                if cat.name in self.shareable:
                    self.logger.info(
                        f"🔗 {cat.name} (Shareable) - "
                        f"Shared attempts: {shared_attempts}, Valid: {shared_valid} "
                        f"({shared_valid/max(1,shared_attempts)*100:.1f}%) | "
                        f"Divergent attempts: {divergent_attempts}, Valid: {divergent_valid} "
                        f"({divergent_valid/max(1,divergent_attempts)*100:.1f}%)"
                    )
                else:
                    self.logger.info(
                        f"📦 {cat.name} (Non-shareable) - "
                        f"Attempts: {divergent_attempts}, Valid: {divergent_valid} "
                        f"({divergent_valid/max(1,divergent_attempts)*100:.1f}%)"
                    )
                return out

            # Get remaining categories for lookahead
            remaining_cats = cats[cat_idx + 1:]
            
            # Score and filter combinations considering future impact in parallel
            import concurrent.futures
            from concurrent.futures import ThreadPoolExecutor
            import math

            def score_combo_batch(batch, profile=None):
                """Score a batch of combinations for a profile or all profiles if shared."""
                scored = []
                for combo in batch:
                    if profile:
                        # Non-shared: score for specific profile
                        score = self._approx_combo_score(profile, cat.name, combo, remaining_cats)
                    else:
                        # Shared: weighted average across all profiles
                        total_score = 0
                        total_weight = 0
                        for p in self.profiles:
                            total_score += p.weight * self._approx_combo_score(p, cat.name, combo, remaining_cats)
                            total_weight += p.weight
                        score = total_score / total_weight if total_weight > 0 else 0
                    scored.append((score, combo))
                return scored

            scored_combos = []
            combos = self._valid_combos_by_cat[cat.name]
            total_combos = len(combos)
            batch_size = 1000  # Process combos in batches of 1000
            num_threads = min(8, math.ceil(total_combos / batch_size))  # Cap at 8 threads
            
            # Split combinations into batches
            batches = [
                combos[i:i + batch_size] 
                for i in range(0, len(combos), batch_size)
            ]
            
            # For shared categories, score only once using all profiles' weights
            if cat.name in self.shareable:
                self.logger.info(
                    f"⏳ Scoring combinations for shared category {cat.name} "
                    f"using {num_threads} threads"
                )
                
                scored = []
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    future_to_batch = {
                        executor.submit(score_combo_batch, batch): i 
                        for i, batch in enumerate(batches)
                    }
                    
                    completed = 0
                    for future in concurrent.futures.as_completed(future_to_batch):
                        batch_idx = future_to_batch[future]
                        batch_results = future.result()
                        scored.extend(batch_results)
                        
                        completed += len(batches[batch_idx])
                        self.logger.info(
                            f"   • Evaluated {completed}/{total_combos} combinations "
                            f"({completed/total_combos*100:.1f}%)"
                        )
                
                scored.sort(key=lambda x: x[0], reverse=True)
                self.logger.info(f"   ✓ Finished scoring {total_combos} combinations")
                # For shared categories, use the same scored list for all profiles
                min_required = max(adaptive_topk, int(len(combos) * 0.1))  # At least 10% of combos
                top_combos = [c for _, c in scored[:min_required]]
                scored_combos.extend([top_combos] * len(self.profiles))
            else:
                # For non-shared categories, score separately for each profile
                for p_idx, p in enumerate(self.profiles):
                    self.logger.info(
                        f"⏳ Scoring combinations for profile {p.name} "
                        f"({p_idx + 1}/{len(self.profiles)}) using {num_threads} threads"
                    )
                    
                    scored = []
                    with ThreadPoolExecutor(max_workers=num_threads) as executor:
                        future_to_batch = {
                            executor.submit(score_combo_batch, batch, p): i 
                            for i, batch in enumerate(batches)
                        }
                        
                        completed = 0
                        for future in concurrent.futures.as_completed(future_to_batch):
                            batch_idx = future_to_batch[future]
                            batch_results = future.result()
                            scored.extend(batch_results)
                            
                            completed += len(batches[batch_idx])
                            self.logger.info(
                                f"   • Evaluated {completed}/{total_combos} combinations "
                                f"({completed/total_combos*100:.1f}%)"
                            )
                    
                    scored.sort(key=lambda x: x[0], reverse=True)
                    self.logger.info(f"   ✓ Finished scoring {total_combos} combinations")
                    # Take top K but ensure we have enough variety
                    min_required = max(adaptive_topk, 
                                     int(len(combos) * 0.1))  # At least 10% of combos
                    scored_combos.append([c for _, c in scored[:min_required]])
            
            self.logger.info(
                f"\n📊 Category {cat.name} - Stats:"
                f"\n   • Base beam width: {beam_width}"
                f"\n   • Adaptive beam width: {adaptive_beam}"
                f"\n   • Available combos: {len(self._valid_combos_by_cat[cat.name])}"
                f"\n   • Selected combos per profile: {[len(l) for l in scored_combos]}"
                f"\n   • Partial solutions: {len(partials)}"
                f"\n   • Remaining categories: {[c.name for c in remaining_cats]}"
            )
            next_states = expand_with_lists(partials, scored_combos)

            # Fallback to FULL lists if Top-K produced nothing
            if not next_states:
                full_lists = [
                    self._valid_combos_by_cat[cat.name] for _ in self.profiles
                ]
                self.logger.warning(
                    f"⚠️ No candidates after Top-K for {cat.name}; retrying with full combo lists"
                    f"\n   • Top-K: {self.topk}"
                    f"\n   • Beam width: {beam_width}"
                    f"\n   • Full combos per profile: {[len(l) for l in full_lists]}"
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
            partials = next_states[:adaptive_beam]
            
            # Log beam state after narrowing
            self.logger.info(
                f"🔍 Beam state for {cat.name}:"
                f"\n   • Valid states found: {len(next_states)}"
                f"\n   • After beam narrowing: {len(partials)}"
                f"\n   • Top score: {partials[0]['key'][0] if partials else 'N/A'}"
                f"\n   • Score range: {partials[-1]['key'][0] if partials else 'N/A'} - {partials[0]['key'][0] if partials else 'N/A'}"
            )

        # Finish
        best_state = max(partials, key=lambda s: s["key"])
        profiles_out: Dict[str, Any] = {}
        for p in self.profiles:
            set_s, orb_s = self._score_one(p, best_state["assign"][p.name])
            profiles_out[p.name] = {
                "set_score": set_s,
                "orb_score": orb_s,
                "loadout": best_state["assign"][p.name],
            }

        primary, _ = self._key(best_state["assign"])
        return {
            "combined_score": primary,
            "profiles": profiles_out,
            "assign": best_state["assign"],
        }

    # --------------------------- refinement ---------------------------

    def refine(
        self, assign: Dict[str, Dict[str, List[Orb]]], max_passes: int = 1
    ) -> Dict[str, Dict[str, List[Orb]]]:
        """Joint greedy refine for N profiles: try single-orb swaps profile-by-profile.

        Args:
            assign: Current assignment of orbs to categories per profile
            max_passes: Maximum number of refinement passes

        Returns:
            Refined assignment with potentially improved scores

        Notes:
            Accepts a swap if it improves the combined key while maintaining all constraints:
            - Within profile: no duplicate types in category, no orb reuse across categories
            - Across profiles:
                * Non-shareable categories: no duplicates allowed
                * Shareable categories: duplicates allowed ONLY within same category
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
                            per_profile_used: dict[str, set[int]] = {
                                pp: set() for pp in trial.keys()
                            }
                            cross_profile_used_by_cat: dict[str, set[int]] = {
                                c2.name: set() for c2 in self.categories
                            }

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

    def _get_adaptive_topk(self, cat_name: str) -> int:
        """Calculate adaptive TopK based on category size."""
        total_combos = len(self._valid_combos_by_cat[cat_name])
        # Square root scaling with upper bound
        return min(self.topk, max(10, int(total_combos ** 0.5)))

    def _get_adaptive_beam_width(self, cat_idx: int, total_cats: int, base_width: int) -> int:
        """Reduce beam width progressively as we process more categories."""
        progress = cat_idx / total_cats
        return max(20, int(base_width * (1.0 - (progress * 0.5))))  # Reduce up to 50%

    def _branching_size(self, cat) -> int:
        """Approximate branching size based on total valid combinations."""
        total_combos = len(self._valid_combos_by_cat[cat.name])
        if cat.name in self.shareable:
            # For shareable categories, we can reuse combinations
            return total_combos
        # For non-shareable, need separate combinations per profile
        return total_combos * len(self.profiles)

    def _calculate_reserved_orbs(self) -> Dict[str, Dict[str, List[Orb]]]:
        """Reserve top orbs for non-shareable categories with smarter allocation."""
        reserved = {}
        non_shareable_cats = [c for c in self.categories if c.name not in self.shareable]
        
        if not non_shareable_cats:
            return reserved

        # Group orbs by type
        orbs_by_type = defaultdict(list)
        for orb in self.orbs:
            orbs_by_type[orb.type].append(orb)
            
        def get_slots_needed(cat: Category) -> int:
            """Calculate actual slots needed considering shareability."""
            return cat.slots if cat.name in self.shareable else cat.slots * len(self.profiles)

        # Calculate total resource needs
        total_slots = sum(get_slots_needed(c) for c in non_shareable_cats)
        shareable_slots = sum(get_slots_needed(c) for c in self.categories 
                            if c.name in self.shareable)
        
        # Adjust reservation ratio based on total needs
        reserve_ratio = min(0.5, total_slots / (total_slots + shareable_slots))
        
        # Sort each type's orbs by value
        sorted_by_type = {
            t: sorted(orbs, key=lambda o: float(o.value), reverse=True)
            for t, orbs in orbs_by_type.items()
        }
        
        # First pass: reserve minimum needed orbs per category
        orbs_taken = defaultdict(set)
        for cat in non_shareable_cats:
            cat_reserved = defaultdict(list)
            min_slots_needed = cat.slots  # Non-shareable categories already filtered
            
            for orb_type, sorted_orbs in sorted_by_type.items():
                available = [o for o in sorted_orbs if id(o) not in orbs_taken[orb_type]]
                # For non-shareable categories, we need separate orbs for each profile
                min_reserve = min(len(available), min_slots_needed * len(self.profiles))
                reserved_orbs = available[:min_reserve]
                cat_reserved[orb_type].extend(reserved_orbs)
                orbs_taken[orb_type].update(id(o) for o in reserved_orbs)
            
            reserved[cat.name] = cat_reserved
        
        # Second pass: distribute remaining high-value orbs
        for orb_type, sorted_orbs in sorted_by_type.items():
            available = [o for o in sorted_orbs if id(o) not in orbs_taken[orb_type]]
            extra_reserve = int(len(available) * reserve_ratio)
            if extra_reserve > 0:
                # Distribute extra orbs proportionally to slot count
                weights = {c.name: c.slots for c in non_shareable_cats}
                total_weight = sum(weights.values())
                for cat_name, weight in weights.items():
                    share = int((weight / total_weight) * extra_reserve)
                    if share > 0:
                        cat_orbs = available[:share]
                        reserved[cat_name][orb_type].extend(cat_orbs)
                        orbs_taken[orb_type].update(id(o) for o in cat_orbs)
                        available = available[share:]
    
        return reserved

    def _can_use_orb(self, orb: Orb, category: Category) -> bool:
        """Check if an orb can be used in this category."""
        if category.name in self.shareable:
            # For shareable categories, check if orb is reserved by any non-shareable category
            for cat_name, cat_reserves in self.reserved_orbs.items():
                if orb in cat_reserves.get(orb.type, []):
                    return False
            return True
        else:
            # For non-shareable categories, prefer their reserved orbs first
            # but allow other orbs if needed
            reserved_for_cat = self.reserved_orbs.get(category.name, {}).get(orb.type, [])
            if orb in reserved_for_cat:
                return True
            # If it's reserved for another non-shareable category, don't use it
            for cat_name, cat_reserves in self.reserved_orbs.items():
                if cat_name != category.name and orb in cat_reserves.get(orb.type, []):
                    return False
            return True

    def _category_sort_key(self, cat: Category) -> tuple[int, int, int]:
        """Sort key for categories prioritizing shareable categories with least constraints first.
        
        Returns tuple of:
        - is_non_shareable (0=shareable, 1=non-shareable)
        - combo_constraint_score (lower=fewer constraints)
        - slot_demand (higher=more slots needed)
        """
        is_non_shareable = 0 if cat.name in self.shareable else 1
        
        # Calculate how constrained this category is based on valid combos
        total_combos = len(self._valid_combos_by_cat[cat.name])
        max_combos = max(len(combos) for combos in self._valid_combos_by_cat.values())
        combo_constraint_score = 1.0 - (total_combos / max_combos)
        
        # Calculate actual slot demand considering shareability
        slot_demand = cat.slots if cat.name in self.shareable else cat.slots * len(self.profiles)
        
        # For shareable categories:
        # - Process less constrained categories first (more likely to find valid combinations)
        # - Within same constraint level, prefer higher slot demand
        if cat.name in self.shareable:
            return (is_non_shareable, int(combo_constraint_score * 1000), -slot_demand)
        
        # For non-shareable categories:
        # - Process after shareable
        # - Process higher slot demands first
        return (is_non_shareable, -slot_demand, int(combo_constraint_score * 1000))
