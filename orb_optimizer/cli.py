"""Command-line interface for orb optimizer"""

from __future__ import annotations

import json
import click

from .data_loader import DataLoader
from .optimizer import UnifiedOptimizer, ProfileConfig
from .utils import setup_logger


@click.group()
def cli():
    """🧮 The Demonized Orb Optimizer"""


@cli.command()
@click.option(
    "--orbs",
    type=click.Path(exists=True),
    default="data/orbs.json",
    show_default=True,
    help="Path to orbs.json (required).",
)
@click.option(
    "--slots",
    type=click.Path(exists=True),
    default="data/slots.json",
    show_default=True,
    help="Path to slots.json (required).",
)
# Set priorities (ranking)
@click.option(
    "--set-priority",
    type=click.Path(),
    default="data/set_priority.json",
    show_default=True,
    help="Optional JSON mapping set -> priority weight (bigger = more important).",
)
# Orb weighting & levels
@click.option(
    "--orb-weights",
    type=click.Path(),
    default="data/orb_weights.json",
    show_default=True,
    help="Optional orb-type weights JSON.",
)
@click.option(
    "--orb-level-weights",
    type=click.Path(),
    default=None,
    show_default=True,
    help="Optional per-type orb-level weights JSON (per tier 3/6/9) for default profile.",
)
@click.option(
    "--objective",
    type=click.Choice(["sets-first", "types-first"]),
    default="sets-first",
    show_default=True,
    help="Objective for default profile.",
)
# Threshold shaping / blending
@click.option(
    "--power",
    type=float,
    default=2.0,
    show_default=True,
    help="Exponent applied to tiers_met to reward completion/concentration.",
)
@click.option(
    "--epsilon",
    type=float,
    default=0.02,
    show_default=True,
    help="Blend factor for default profile (keep small, e.g., 0.01–0.05).",
)
# Multi-profile config (optional)
@click.option(
    "--profiles",
    type=click.Path(),
    default=None,
    show_default=True,
    help="Optional profiles.json enabling multiple profiles.",
)
# Performance knobs
@click.option(
    "--topk",
    type=int,
    default=20,
    show_default=True,
    help="Per-profile Top-K combos kept per category (prunes candidate pairs).",
)
# Search / refine / verbosity
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
@click.option("--verbose", is_flag=True, help="Enable detailed debug logs.")
def optimize(
    orbs,
    slots,
    set_priority,
    orb_weights,
    orb_level_weights,
    objective,
    power,
    epsilon,
    profiles,
    topk,
    beam,
    refine_passes,
    refine_report,
    verbose,
):
    """Optimize your orb configuration with thresholds-first scoring, then refine with quick local swaps."""
    logger = setup_logger(verbose)
    loader = DataLoader(logger)

    logger.info("🚀 Loading input data...")

    # Required data
    orb_data = loader.load_orbs(orbs)
    cat_data = loader.load_categories(slots)

    profile_list: list[ProfileConfig] = []
    shareable_categories: list[str] = []

    if profiles:
        with open(profiles, "r") as f:
            cfg = json.load(f)

        for pj in cfg["profiles"]:
            name = pj["name"]
            set_prio = loader.load_set_priority_or_default(pj.get("set_priority"))
            type_w = loader.load_orb_type_weights_or_default(pj.get("orb_weights"))
            lvl_w = loader.load_orb_level_weights_or_default(
                pj.get("orb_level_weights")
            )
            profile_list.append(
                ProfileConfig(
                    name=name,
                    set_priority=set_prio,
                    orb_type_weights=type_w,
                    orb_level_weights=lvl_w,
                    power=float(pj.get("power", 2.0)),
                    epsilon=float(pj.get("epsilon", 0.0)),
                    objective=pj.get("objective", "sets-first"),
                    weight=float(pj.get("weight", 1.0)),
                )
            )
        shareable_categories = list(cfg.get("shareable_categories", []))

    else:
        # Synthesize a single default profile from CLI knobs
        set_prio = loader.load_set_priority_or_default(set_priority)
        type_w = loader.load_orb_type_weights_or_default(orb_weights)
        lvl_w = loader.load_orb_level_weights_or_default(orb_level_weights)
        profile_list = [
            ProfileConfig(
                name="DEFAULT",
                set_priority=set_prio,
                orb_type_weights=type_w,
                orb_level_weights=lvl_w,
                power=power,
                epsilon=epsilon,
                objective=objective,
                weight=1.0,
            )
        ]
        shareable_categories = None

    # Build unified optimizer
    uopt = UnifiedOptimizer(
        orbs=orb_data,
        categories=cat_data,
        logger=logger,
        profiles=profile_list,
        shareable_categories=shareable_categories,
        topk_per_category=topk,
    )

    result = uopt.optimize(beam_width=beam)

    base_assign = result["assign"]
    base_primary, _ = uopt._key(base_assign)  # combined primary for report

    refined_assign = (
        uopt.refine(base_assign, max_passes=refine_passes)
        if refine_passes > 0
        else base_assign
    )
    refined_primary, _ = uopt._key(refined_assign)

    click.echo("\n✅ Optimization Complete!\n")
    click.secho(
        f"🏆 Combined Score (primary): {refined_primary:.2f}", fg="green", bold=True
    )
    if refine_passes > 0 and refine_report:
        delta = refined_primary - base_primary
        click.secho("🧽 Refine:", fg="yellow")
        click.echo(f"   • Passes: {refine_passes}")
        click.echo(f"   • Before: {base_primary:.2f}")
        click.echo(f"   • After : {refined_primary:.2f}")
        click.echo(f"   • Δ      {('+' if delta >= 0 else '')}{delta:.2f}")

    # Print per-profile reports
    for p in profile_list:
        set_s, orb_s = uopt._score_one(p, refined_assign[p.name])
        click.secho(f"\n[{p.name}] Loadout", fg="blue", bold=True)
        click.echo(f"   • Set score: {set_s:.2f}")
        click.echo(f"   • Orb score: {orb_s:.2f}\n")
        for cat in cat_data:
            click.secho(f"{cat.name}", fg="blue")
            for orb in refined_assign[p.name][cat.name]:
                click.echo(
                    f"  • {orb.type} — {orb.set_name} ({orb.rarity}) +{orb.value}% (lvl {orb.level})"
                )
            click.echo()


def main() -> None:
    cli(prog_name="orb-optimize")


if __name__ == "__main__":
    main()
