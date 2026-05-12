"""Unified report/print helper for all solvers.

Usage from CLI:
    from .reporter import OptimizationReporter, ReportOptions

    reporter = OptimizationReporter()
    reporter.emit(
        result=uopt_result,                 # {'combined_score', 'profiles', 'assign'}
        profiles=profile_list,              # List[ProfileConfig]
        categories=cat_data,                # List[Category]
        options=ReportOptions(
            show_refine=True,
            refine_passes=refine_passes,
            base_result=base_result,        # optional: pre-refine
            show_active_sets=True,
            show_orb_type_summary=True,
        ),
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
from typing import Any, Dict, List, Optional

try:
    import click  # type: ignore
except Exception:  # pragma: no cover
    click = None  # Fallback for non-CLI test contexts

from .models import Orb, Category, ProfileConfig, MultiProfileResult, AssignedOrb
from .defaults import DEFAULT_SET_COUNTS


# ------------------------------- options -------------------------------

@dataclass
class ReportOptions:
    show_refine: bool = False
    refine_passes: int = 0
    base_result: Optional[Dict[str, Any]] = None  # same shape as 'result'
    show_active_sets: bool = True
    show_orb_type_summary: bool = True
    # Limit the amount of output for large datasets
    max_sets_to_show: int = 999999
    max_categories_to_show: int = 999999


# ----------------------------- reporter -----------------------------

class OptimizationReporter:
    """Uniform report printer for beam/greedy (or any future) solvers.

    Expects `result` to have:
      - result['combined_score']: float
      - result['assign']: Dict[pname][cat] -> List[Orb]
      - result['profiles'][pname]: { 'set_score': float, 'orb_score': float, 'loadout': Dict[cat] -> List[Orb] }
    """

    def __init__(self, *, use_colors: bool = True):
        self.use_colors = use_colors and (click is not None)

    # ---- public ----
    def emit(
        self,
        *,
        result: MultiProfileResult,
        profiles: List[ProfileConfig],
        options: Optional[ReportOptions] = None,
    ) -> None:
        opts = options or ReportOptions()

        self._print_header("✅ Optimization Complete!", color="green", bold=True)
        self._print_kv("🏆 Combined Score (primary)", f"{result.combined_score:.2f}", strong=True)
        self._print_kv(
            "📦 Coverage",
            f"{result.filled_slots}/{result.requested_slots} "
            f"({'partial' if result.is_partial else 'complete'})",
        )
        self._println("")

        if opts.show_refine and opts.base_result is not None:
            self._emit_refine_summary(opts.base_result, result, passes=opts.refine_passes)

        # Per-profile sections
        for p in profiles:
            pdata = result.profiles[p.name]
            loadout = pdata.loadout
            set_s = pdata.set_score
            orb_s = pdata.orb_score

            self._print_header(f"[{p.name}] Loadout", color="blue", bold=True)
            self._print_kv("• Set score", f"{set_s:.2f}")
            self._print_kv("• Orb score", f"{orb_s:.2f}")
            self._print_kv(
                "• Coverage",
                f"{pdata.filled_slots}/{pdata.requested_slots} "
                f"({'partial' if pdata.is_partial else 'complete'})",
            )
            self._println("")

            # Loadout details by category
            for i, cat in enumerate(p.categories):
                self._print_line(cat.name, color="blue")
                for orb in loadout[cat.name]:
                    self._println(
                        f"  • {orb.type} — {orb.set} ({orb.rarity}) "
                        f"+{orb.value}% (lvl {getattr(orb, 'level', 0)})"
                    )
                self._println("")

            # Optional extras
            if opts.show_active_sets:
                self._emit_active_sets(loadout, p, max_rows=opts.max_sets_to_show)

            if opts.show_orb_type_summary:
                self._emit_orb_type_summary(loadout)

    # ---- sections ----
    def _emit_refine_summary(self, base: Any, refined: MultiProfileResult, *, passes: int) -> None:
        before_raw = base.get("combined_score", 0.0) if isinstance(base, dict) else getattr(base, "combined_score", 0.0)
        before = float(before_raw)
        after = float(getattr(refined, "combined_score", 0.0))
        delta = after - before
        self._print_header("🧽 Refine", color="yellow")
        self._print_kv("• Passes", str(passes))
        self._print_kv("• Before", f"{before:.2f}")
        self._print_kv("• After", f"{after:.2f}")
        sign = "+" if delta >= 0 else ""
        self._print_kv("• Δ", f"{sign}{delta:.2f}")
        self._println("")

    def _emit_active_sets(self, loadout: Dict[str, List[Orb]], prof: ProfileConfig, *, max_rows: int) -> None:
        rows = self._active_sets_table(loadout, prof)
        self._print_header("Active Sets (tiers met):", color="yellow")
        for i, r in enumerate(rows):
            if i >= max_rows:
                self._println(f"... ({len(rows)-i} more sets not shown)")
                break
            self._println(
                f"  • {r['set']}: pieces {r['pieces']}  "
                f"tiers={r['tiers']}  W={r['weight']}  "
                f"contrib={r['contrib']:.2f}"
            )
        self._println("")

    def _emit_orb_type_summary(self, loadout: Dict[str, List[Orb]]) -> None:
        type_counts, type_bonus = Counter(), Counter()
        for orbs_list in loadout.values():
            for orb in orbs_list:
                type_counts[orb.type] += 1
                # value is already normalized/parsed upstream
                try:
                    type_bonus[orb.type] += float(orb.value)
                except Exception:
                    pass

        self._print_header("Orb Type Summary:", color="yellow")
        for t in sorted(type_counts):
            self._println(
                f"  • {t}: pieces={type_counts[t]} total bonus={type_bonus[t]:.2f}"
            )
        self._println("")

    # ---- helpers ----
    def _active_sets_table(self, loadout: Dict[str, List[AssignedOrb]], prof: ProfileConfig) -> List[Dict[str, Any]]:
        counts = Counter(o.set for group in loadout.values() for o in group)
        rows: List[Dict[str, Any]] = []
        for sname, c in counts.items():
            th = DEFAULT_SET_COUNTS.get(sname, [])
            tiers = sum(1 for t in th if c >= t)
            if tiers <= 0:
                continue
            w = prof.set_priority.get(sname, 0.0)
            contrib = w * tiers
            rows.append(
                {
                    "set": sname,
                    "pieces": c,
                    "tiers": tiers,
                    "weight": w,
                    "contrib": contrib,
                }
            )
        rows.sort(key=lambda r: (-r["contrib"], -r["tiers"], -r["pieces"], r["set"]))
        return rows

    # ---- printing primitives ----
    def _print_header(self, text: str, *, color: Optional[str] = None, bold: bool = False) -> None:
        if self.use_colors and color:
            click.secho(text, fg=color, bold=bold)
        else:  # pragma: no cover
            self._println(text)

    def _print_kv(self, k: str, v: str, *, strong: bool = False) -> None:
        line = f"{k}: {v}"
        if self.use_colors and strong:
            click.secho(line, fg="green", bold=True)
        else:  # pragma: no cover
            self._println(line)

    def _print_line(self, text: str, *, color: Optional[str] = None) -> None:
        if self.use_colors and color:
            click.secho(text, fg=color)
        else:  # pragma: no cover
            self._println(text)

    def _println(self, text: str = "") -> None:  # pragma: no cover
        print(text)
