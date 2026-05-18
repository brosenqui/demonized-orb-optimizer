"""Command-line interface for orb optimizer"""

from __future__ import annotations

from typing import Any, Dict

import click

from orb_optimizer.data_loader import DataLoader
from orb_optimizer.solvers.beam import UnifiedOptimizer
from orb_optimizer.solvers.greedy import GreedyOptimizer
from orb_optimizer.models import Inputs
from orb_optimizer.reporter import OptimizationReporter
from orb_optimizer.utils import (
    setup_logger,
    build_default_profile,
    build_profiles_from_json,
)

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
    help="Path to slots.json (REQUIRED). Used as default per-profile categories if a profile doesn't specify its own.",
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
    help="Optional per-type multipliers for level-gate bonuses (3/6/9) (default profile only).",
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
    help="Optional profiles.json enabling multiple profiles. Each profile may specify 'slots' or 'category_rarity'.",
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
    orb_data = loader.load_orbs(orbs)

    # Load default slots map from slots.json (as a dict)
    default_slots_map = loader.load_json(slots)
    if not isinstance(default_slots_map, dict):
        raise click.UsageError("slots.json must be an object mapping category -> slots")

    # Build profile(s) WITH categories
    if profiles:
        profile_list, shareability_matrix = build_profiles_from_json(
            loader, profiles, default_slots=default_slots_map
        )
    else:
        profile_list = [
            build_default_profile(
                loader,
                set_priority_path=set_priority,
                orb_weights_path=orb_weights,
                orb_level_weights_path=orb_level_weights,
                objective=objective,
                power=power,
                epsilon=epsilon,
                default_slots=default_slots_map,
            )
        ]
        shareability_matrix = None

    # Stash normalized inputs for all subcommands
    ctx.obj = {
        "logger": logger,
        "loader": loader,
        "inputs": Inputs(
            orbs=orb_data,
            profiles=profile_list,                 # <-- categories now live inside each profile
            shareability_matrix=shareability_matrix,
        ),
    }


# ---------- Subcommand: beam optimizer ----------
@cli.command("beam")
@click.option(
    "--topk-per-category",
    type=int,
    default=20,
    show_default=True,
    help="Top-K combos kept per category.",
)
@click.option("--beam-width", type=int, default=200, show_default=True, help="Beam width.")
@click.option(
    "--parallelism",
    type=click.Choice(["auto", "process", "thread", "serial"]),
    default="auto",
    show_default=True,
    help="How beam scoring parallelism is executed.",
)
@click.option(
    "--max-time-ms",
    type=int,
    default=5000,
    show_default=True,
    help="Beam time budget in milliseconds.",
)
@click.pass_obj
def cmd_optimize(
    shared: Dict[str, Any],
    topk_per_category: int,
    beam_width: int,
    parallelism: str,
    max_time_ms: int,
):
    """Optimize via beam search."""
    logger = shared["logger"]
    inputs: Inputs = shared["inputs"]

    uopt = UnifiedOptimizer(
        inputs=inputs,
        logger=logger,
        topk_per_category=topk_per_category,
        parallelism=parallelism,
        max_time_ms=max_time_ms,
    )
    result = uopt.optimize(beam_width=beam_width)

    OptimizationReporter().emit(
        result=result,
        profiles=[p for p in inputs.profiles]
    )


# ---------- Greedy (unified multi-profile) ----------
@cli.command("greedy")
@click.option(
    "--topk-per-type",
    type=int,
    default=16,
    show_default=True,
    help="Top-K candidate orbs kept per type.",
)
@click.option(
    "--restarts",
    type=int,
    default=6,
    show_default=True,
    help="Number of randomized multi-start restarts.",
)
@click.option(
    "--max-time-ms",
    type=int,
    default=1500,
    show_default=True,
    help="Greedy time budget in milliseconds.",
)
@click.option(
    "--seed",
    type=int,
    default=0,
    show_default=True,
    help="Random seed used for greedy restarts.",
)
@click.pass_obj
def cmd_greedy(
    shared: Dict[str, Any],
    topk_per_type: int,
    restarts: int,
    max_time_ms: int,
    seed: int,
):
    """Greedy optimizer with bounded multi-start search."""
    logger = shared["logger"]
    inputs: Inputs = shared["inputs"]

    greedy = GreedyOptimizer(
        inputs=inputs,
        logger=logger,
        topk_per_type=topk_per_type,
        restarts=restarts,
        max_time_ms=max_time_ms,
        seed=seed,
    )
    result = greedy.optimize()

    OptimizationReporter().emit(
        result=result,
        profiles=[p for p in inputs.profiles]
    )


def main() -> None:
    cli(prog_name="orb-optimize")


if __name__ == "__main__":
    main()
