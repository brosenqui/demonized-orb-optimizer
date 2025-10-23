# apps/cli/main.py
"""Command-line interface for orb optimizer"""

from __future__ import annotations

from typing import Any, Dict

import click

from orb_optimizer.io.loader import Loader as DataLoader

from orb_optimizer.solvers.beam import UnifiedOptimizer
from orb_optimizer.solvers.greedy import GreedyOptimizer
from orb_optimizer.models import Inputs
from orb_optimizer.reporter import OptimizationReporter
from orb_optimizer.utils import setup_logger, build_default_profile, build_profiles_from_json


# ---------- Root group: loads everything once ----------
@click.group()
@click.option(
    "--orbs",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=str),
    required=True,
    help="Path to orbs.json (REQUIRED).",
)
@click.option(
    "--slots",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=str),
    required=True,
    help="Path to slots.json (REQUIRED).",
)
# Optional weights (used when profiles.json is NOT provided)
@click.option(
    "--set-priority",
    type=click.Path(dir_okay=False, readable=True, path_type=str),
    default=None,
    show_default=True,
    help="Optional JSON mapping set -> priority weight (default profile only).",
)
@click.option(
    "--orb-weights",
    type=click.Path(dir_okay=False, readable=True, path_type=str),
    default=None,
    show_default=True,
    help="Optional orb-type weights JSON (default profile only).",
)
@click.option(
    "--orb-level-weights",
    type=click.Path(dir_okay=False, readable=True, path_type=str),
    default=None,
    show_default=True,
    help="Optional per-type orb-level weights (tier 3/6/9) (default profile only).",
)
# Default-profile knobs (ignored if profiles.json is provided)
@click.option(
    "--objective",
    type=click.Choice(["sets-first", "types-first"]),
    default="sets-first",
    show_default=True,
    help="Objective for default profile.",
)
@click.option(
    "--power",
    type=float,
    default=2.0,
    show_default=True,
    help="Exponent applied to tiers_met to reward completion/concentration (default profile).",
)
@click.option(
    "--epsilon",
    type=float,
    default=0.02,
    show_default=True,
    help="Blend factor (keep small, e.g., 0.01–0.05) (default profile).",
)
# Multi-profile config (optional)
@click.option(
    "--profiles",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=str),
    default=None,
    show_default=True,
    help="Optional profiles.json enabling multiple profiles.",
)
@click.option("--verbose", is_flag=True, help="Enable detailed debug logs.")
@click.pass_context
def cli(
    ctx: click.Context,
    orbs: str,
    slots: str,
    set_priority: str | None,
    orb_weights: str | None,
    orb_level_weights: str | None,
    objective: str,
    power: float,
    epsilon: float,
    profiles: str | None,
    verbose: bool,
):
    """🧮 The Demonized Orb Optimizer"""
    logger = setup_logger(verbose)
    loader = DataLoader(logger)

    logger.info("🚀 Loading input data...")
    orb_data = loader.load_orbs(orbs)       # accepts path or Source object
    cat_data = loader.load_categories(slots)

    # Build profile(s)
    if profiles:
        # Keeps your existing helper intact
        profile_list, shareable = build_profiles_from_json(loader, profiles)
    else:
        profile_list = [build_default_profile(
            loader,
            set_priority_path=set_priority,
            orb_weights_path=orb_weights,
            orb_level_weights_path=orb_level_weights,
            objective=objective,
            power=power,
            epsilon=epsilon,
        )]
        shareable = None

    # Stash normalized inputs for all subcommands
    ctx.obj = {
        "logger": logger,
        "loader": loader,
        "inputs": Inputs(
            orbs=orb_data,
            categories=cat_data,
            profiles=profile_list,
            shareable_categories=shareable,
        ),
    }


# ---------- Subcommand: beam/heuristic optimizer (current default) ----------
@cli.command("beam")
@click.option("--topk", type=int, default=20, show_default=True,
              help="Per-profile Top-K combos kept per category (prunes candidate pairs).")
@click.option("--beam", type=int, default=200, show_default=True, help="Beam width.")
@click.option(
    "--refine-passes",
    type=int,
    default=2,
    show_default=True,
    help="Number of greedy local-improvement passes after search (0 to disable).",
)
@click.option(
    "--refine-report",
    is_flag=True,
    help="Show before/after combined scores if refinement changed result.",
)
@click.pass_obj
def cmd_optimize(shared: Dict[str, Any], topk: int, beam: int, refine_passes: int, refine_report: bool):
    """Optimize via beam search + optional refine."""
    logger = shared["logger"]
    inputs = shared["inputs"]

    uopt = UnifiedOptimizer(
        inputs=inputs,
        logger=logger,
        topk_per_category=topk,
    )

    result = uopt.optimize(beam_width=beam)

    OptimizationReporter().emit(
        result=result,
        profiles=inputs.profiles,
        categories=inputs.categories
    )


# ---------- Greedy (placeholder / alt solver) ----------
@cli.command("greedy")
@click.pass_obj
def test(shared: Dict[str, Any]):
    """placeholder for alternative optimization methods"""
    logger = shared["logger"]
    inputs = shared["inputs"]
    greedy = GreedyOptimizer(inputs=inputs, logger=logger)

    result = greedy.optimize()

    OptimizationReporter().emit(
        result=result,
        profiles=inputs.profiles,
        categories=inputs.categories
    )


def main() -> None:
    cli(prog_name="orb-optimize")


if __name__ == "__main__":
    main()
