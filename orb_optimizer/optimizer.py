"""Core optimization logic (thresholds-only set scoring) with ranked-per-type normalization
and an optional local refinement pass.

Primary objective (choose with --objective):
  - sets-first (default):
      primary   = set_priority_score + ε * orb_quality_score
      secondary = orb_quality_score
  - types-first:
      primary   = orb_quality_score + ε * set_priority_score
      secondary = set_priority_score

Definitions:
  set_priority_score = Σ_s W_s * (tiers_met(s) ** power)
    • W_s: set priority weight
    • tiers_met(s): number of thresholds reached for set s (from sets.json)

  orb_quality_score  = Σ_orb [
      rank_within_type(value) * orb_type_weight[type]       # rank ∈ [0,1], best in type ≈ 1
    + tiers(level) * orb_level_weight[type]                 # tiers at 3/6/9
  ]

Constraints:
  • Unique orb TYPES within each category (no duplicate types in a single category)
  • Unique orb INSTANCES across all categories (each inventory orb can be used once)

Notes:
  • We ignore raw % magnitude differences across types by using per-type percentile rank.
  • This ensures “best Steel” can compete fairly with “best Flame”, etc.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations, product
from typing import Any, TYPE_CHECKING

from .models import Orb, Category

if TYPE_CHECKING:
    from logging import Logger


def tiers_from_level(level: int) -> int:
    """Return how many level tiers are unlocked at 3, 6, 9."""
    return (
        (1 if level >= 3 else 0) + (1 if level >= 6 else 0) + (1 if level >= 9 else 0)
    )


def _orb_ids(objs: list[Orb] | tuple[Orb, ...]) -> set[int]:
    """Return a set of Python object ids for given orbs (to enforce uniqueness across categories)."""
    return {id(o) for o in objs}


class LoadoutOptimizer:
    """Beam/full search optimizer with thresholds-only set scoring and local refine.

    Parameters:
        orbs: All available orbs from orbs.json.
        categories: Categories with slot counts.
        logger: Logger instance.
        set_thresholds: Mapping set -> sorted list of threshold counts.
        set_priority: Mapping set -> priority weight (bigger = more important).
        orb_type_weights: Mapping orb type -> multiplier (bias types, e.g., Steel).
        orb_level_weights: Mapping orb type -> additive per level tier (3/6/9).
        power: Exponent applied to tiers_met to reward completion/concentration.
        epsilon: Blend factor for secondary score in the primary term.
        objective: "sets-first" or "types-first".
    """

    def __init__(
        self,
        *,
        orbs: list[Orb],
        categories: list[Category],
        logger: Logger,
        set_thresholds: dict[str, list[int]],
        set_priority: dict[str, float],
        orb_type_weights: dict[str, float],
        orb_level_weights: dict[str, float],
        power: float = 2.0,
        epsilon: float = 0.0,
        objective: str = "sets-first",
    ):
        self.orbs = orbs
        self.categories = categories
        self.logger = logger

        self.set_thresholds = set_thresholds
        self.set_priority = set_priority
        self.power = float(power)

        self.orb_type_weights = orb_type_weights
        self.orb_level_weights = orb_level_weights

        self.epsilon = float(epsilon)
        self.objective = objective

        # Precompute per-type value distributions for percentile ranks
        self._prepare_value_normalizer()

        # Logging
        self.logger.info(
            "🏷️ Set priorities: "
            + ", ".join(f"{k}={v:g}" for k, v in sorted(self.set_priority.items()))
        )
        self.logger.info(f"ᵖ Power (set concentration exponent): {self.power:g}")
        self.logger.info(
            "🗂️  Sets with thresholds: " + ", ".join(sorted(self.set_thresholds.keys()))
        )
        if self.orb_type_weights:
            self.logger.info(
                "🎚️ Orb-type weights: "
                + ", ".join(
                    f"{k}={v:g}" for k, v in sorted(self.orb_type_weights.items())
                )
            )
        if self.orb_level_weights:
            self.logger.info(
                "📈 Orb-level weights: "
                + ", ".join(
                    f"{k}={v:g}" for k, v in sorted(self.orb_level_weights.items())
                )
            )
        self.logger.info(f"ε Epsilon blend: {self.epsilon:g}")
        self.logger.info(f"🎯 Objective: {self.objective}")
        self.logger.info("📏 Value normalization: ranked-per-type (0..1)")

    # ---- Value normalization (ranked per type) ----
    def _prepare_value_normalizer(self) -> None:
        """Build per-type sorted value lists for percentile ranking."""
        self._type_values: dict[str, list[float]] = {}
        buckets: dict[str, list[float]] = defaultdict(list)
        for o in self.orbs:
            try:
                buckets[o.type].append(float(o.value))
            except Exception:
                buckets[o.type].append(0.0)
        for t, vals in buckets.items():
            vals.sort()
            self._type_values[t] = vals

    def _percentile_within_type(self, t: str, v: float) -> float:
        """Return percentile rank of value v within its type t in [0, 1]."""
        vals = self._type_values.get(t)
        if not vals:
            return 0.0
        # binary search rank
        import bisect

        i = bisect.bisect_left(vals, v)
        j = bisect.bisect_right(vals, v)
        rank = (i + j) / 2.0
        if len(vals) == 1:
            return 1.0
        return rank / (len(vals) - 1)

    # ---- Scoring ----
    def _score_breakdown(
        self, loadout: dict[str, list[Orb]]
    ) -> tuple[float, float, dict[str, Any]]:
        chosen = [orb for group in loadout.values() for orb in group]

        # Set priority score (thresholds-only)
        counts = Counter(o.set_name for o in chosen)
        set_score = 0.0
        active_sets: dict[str, Any] = {}
        for s, c in counts.items():
            thresholds = self.set_thresholds.get(s)
            if not thresholds:
                continue  # strict thresholds-only: sets without thresholds = no contribution
            tiers_met = sum(1 for t in thresholds if c >= t)
            if tiers_met <= 0:
                continue
            w = self.set_priority.get(s, 0.0)
            contribution = w * (tiers_met**self.power)
            set_score += contribution
            active_sets[s] = {
                "count": c,
                "priority": w,
                "tiers_met": tiers_met,
                "contribution": contribution,
            }

        # Orb quality score (ranked-per-type normalization)
        orb_score = 0.0
        for o in chosen:
            try:
                raw = float(o.value)
            except Exception:
                raw = 0.0
            base = self._percentile_within_type(o.type, raw)  # 0..1 within that type
            orb_score += base * self.orb_type_weights.get(o.type, 1.0)
            orb_score += tiers_from_level(o.level) * self.orb_level_weights.get(
                o.type, 0.0
            )

        return set_score, orb_score, {"sets": active_sets}

    def _score_key(self, loadout: dict[str, list[Orb]]) -> tuple[float, float]:
        set_score, orb_score, _ = self._score_breakdown(loadout)

        if self.objective == "types-first":
            primary = orb_score + (self.epsilon * set_score if self.epsilon else 0.0)
            secondary = set_score
        else:
            primary = set_score + (self.epsilon * orb_score if self.epsilon else 0.0)
            secondary = orb_score

        return (primary, secondary)

    # ---- Search ----
    def optimize(self, mode: str = "beam", beam_width: int = 400) -> dict[str, Any]:
        self.logger.info(f"⚙️ Starting optimization in {mode.upper()} mode...")
        if mode == "full":
            return self._full_search()
        return self._beam_search(beam_width)

    def _beam_search(self, beam_width: int) -> dict[str, Any]:
        """Beam search with:
        - unique orb TYPES within each category
        - unique orb INSTANCES across all categories
        """
        partials = [
            {
                "assign": {c.name: [] for c in self.categories},
                "used_ids": set(),
                "key": (0.0, 0.0),
            }
        ]

        for cat in self.categories:
            next_states = []
            self.logger.debug(f"Evaluating category: {cat.name}")

            for state in partials:
                assign = state["assign"]
                used_ids = state["used_ids"]

                for combo in combinations(self.orbs, cat.slots):
                    # Unique orb TYPES within this category
                    if len({o.type for o in combo}) < len(combo):
                        continue

                    # Unique orb INSTANCES across all categories
                    combo_ids = _orb_ids(combo)
                    if used_ids & combo_ids:
                        continue

                    new_assign = {k: list(v) for k, v in assign.items()}
                    new_assign[cat.name] = list(combo)
                    new_used = used_ids | combo_ids
                    key = self._score_key(new_assign)

                    next_states.append(
                        {"assign": new_assign, "used_ids": new_used, "key": key}
                    )

            next_states.sort(key=lambda s: s["key"], reverse=True)
            partials = next_states[:beam_width]
            self.logger.debug(f"Beam narrowed to {len(partials)} states for {cat.name}")

        best_state = max(partials, key=lambda s: s["key"])
        set_score, orb_score, details = self._score_breakdown(best_state["assign"])
        total = set_score + orb_score
        details["set_priority_score"] = set_score
        details["orb_quality_score"] = orb_score
        return {"score": total, "loadout": best_state["assign"], "details": details}

    def _full_search(self) -> dict[str, Any]:
        """Full search with instance/type uniqueness constraints."""
        self.logger.info("🧮 Performing full search — this may take a while...")
        best_key = (float("-inf"), float("-inf"))
        best_loadout: dict[str, list[Orb]] = {}

        # Precompute valid combos per category (respecting type-uniqueness per category)
        all_combos: list[list[tuple[Orb, ...]]] = []
        for cat in self.categories:
            valid = [
                c
                for c in combinations(self.orbs, cat.slots)
                if len({o.type for o in c}) == len(c)
            ]
            all_combos.append(valid)

        for combo_set in product(*all_combos):
            # Enforce global instance uniqueness across categories
            used_ids: set[int] = set()
            ok = True
            for combo in combo_set:
                ids = _orb_ids(combo)
                if used_ids & ids:
                    ok = False
                    break
                used_ids |= ids
            if not ok:
                continue

            loadout = {
                cat.name: list(combo_set[i]) for i, cat in enumerate(self.categories)
            }
            key = self._score_key(loadout)
            if key > best_key:
                best_key = key
                best_loadout = loadout

        set_score, orb_score, details = self._score_breakdown(best_loadout)
        total = set_score + orb_score
        details["set_priority_score"] = set_score
        details["orb_quality_score"] = orb_score
        return {"score": total, "loadout": best_loadout, "details": details}

    # ---- Refinement (local greedy improve) ----
    def refine_loadout(
        self, loadout: dict[str, list[Orb]], max_passes: int = 1
    ) -> dict[str, list[Orb]]:
        """Greedy local improvement around a finished loadout.

        Tries single-orb swaps using any currently unused orb (respecting constraints).
        Accepts a swap if the score key improves (primary term, then secondary).
        Runs up to `max_passes` passes, or stops early if no improvement.

        Args:
            loadout: Completed loadout mapping category -> list[Orb].
            max_passes: Number of improvement passes (1-2 is usually plenty).

        Returns:
            The improved loadout (or the original if no improvements were found).
        """
        if max_passes <= 0:
            return loadout

        best_ld = {k: list(v) for k, v in loadout.items()}
        best_key = self._score_key(best_ld)

        def current_unused() -> list[Orb]:
            used = {id(o) for g in best_ld.values() for o in g}
            return [o for o in self.orbs if id(o) not in used]

        passes = 0
        improved_any = True

        while improved_any and passes < max_passes:
            improved_any = False
            passes += 1
            unused = current_unused()

            for cat_name, group in list(best_ld.items()):
                types_in_cat = {o.type for o in group}

                for i, old in enumerate(list(group)):
                    for new in list(unused):
                        if new.type != old.type and new.type in types_in_cat:
                            continue

                        # Trial swap
                        trial = {k: list(v) for k, v in best_ld.items()}
                        tgroup = list(trial[cat_name])
                        tgroup[i] = new
                        trial[cat_name] = tgroup

                        # Enforce unique instances globally
                        seen: set[int] = set()
                        ok = True
                        for g in trial.values():
                            for o in g:
                                oid = id(o)
                                if oid in seen:
                                    ok = False
                                    break
                                seen.add(oid)
                            if not ok:
                                break
                        if not ok:
                            continue

                        k = self._score_key(trial)
                        if k > best_key:
                            best_ld = trial
                            best_key = k
                            improved_any = True
                            # maintain unused pool
                            unused.remove(new)
                            unused.append(old)
                            types_in_cat = {o.type for o in best_ld[cat_name]}
                            break
                    if improved_any:
                        break
                if improved_any:
                    break

        return best_ld
