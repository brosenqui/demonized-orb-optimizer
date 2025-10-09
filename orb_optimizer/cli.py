"""Command-line interface for orb optimizer"""

from __future__ import annotations
from collections import Counter

import click

from .data_loader import DataLoader
from .optimizer import LoadoutOptimizer
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
    default="data/orb_level_weights.json",
    show_default=True,
    help="Optional per-type orb-level additive weights JSON (per +3/6/9) upgrades.",
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
    help="Small blend of secondary score into the primary score (try 0.01–0.05).",
)
@click.option(
    "--objective",
    type=click.Choice(["sets-first", "types-first"]),
    default="sets-first",
    show_default=True,
    help="Choose which score is primary: set completion or orb type/level quality.",
)
# Refinement
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
    help="Print a compact before/after summary if refinement improves the result.",
)
# Search & verbosity
@click.option(
    "--mode",
    type=click.Choice(["beam", "full"]),
    default="beam",
    show_default=True,
    help="Search strategy.",
)
@click.option(
    "--beam",
    type=int,
    default=100,
    show_default=True,
    help="Beam width (beam mode only).",
)
@click.option("--verbose", is_flag=True, help="Enable detailed debug logs.")
def optimize(
    orbs,
    slots,
    set_priority,
    orb_weights,
    orb_level_weights,
    power,
    epsilon,
    objective,
    refine_passes,
    refine_report,
    mode,
    beam,
    verbose,
):
    """Optimize your orb configuration with thresholds-first scoring, then refine with quick local swaps."""
    logger = setup_logger(verbose)
    loader = DataLoader(logger)

    logger.info("🚀 Loading input data...")

    # Required data
    orb_data = loader.load_orbs(orbs)
    cat_data = loader.load_categories(slots)
    set_thresholds = loader.load_set_thresholds()

    # Optional weights with defaults
    set_priority_w = loader.load_set_priority_or_default(set_priority)
    orb_type_w = loader.load_orb_type_weights_or_default(orb_weights)
    level_w = loader.load_orb_level_weights_or_default(orb_level_weights)

    optimizer = LoadoutOptimizer(
        orbs=orb_data,
        categories=cat_data,
        logger=logger,
        set_thresholds=set_thresholds,
        set_priority=set_priority_w,
        orb_type_weights=orb_type_w,
        orb_level_weights=level_w,
        power=power,
        epsilon=epsilon,
        objective=objective,
    )

    # Do the thing
    logger.info("🏃‍♂️ Optimizing...")
    search_result = optimizer.optimize(mode=mode, beam_width=beam)

    base_loadout = search_result["loadout"]
    base_set, base_orb, _ = optimizer._score_breakdown(base_loadout)
    refined = (
        optimizer.refine_loadout(base_loadout, max_passes=refine_passes)
        if refine_passes > 0
        else base_loadout
    )
    ref_set, ref_orb, details = optimizer._score_breakdown(refined)
    total = ref_set + ref_orb
    details["set_priority_score"] = ref_set
    details["orb_quality_score"] = ref_orb

    # Reporting
    click.echo("\n✅ Optimization Complete!\n")
    click.secho(f"🏆 Total Score: {total:.2f}", fg="green", bold=True)
    click.echo(f"   • Set priority score: {details['set_priority_score']:.2f}")
    click.echo(f"   • Orb quality score : {details['orb_quality_score']:.2f}")
    click.echo(f"   • Epsilon           : {epsilon:.3g}")
    if refine_passes > 0 and refine_report:
        base_total = base_set + base_orb
        delta = total - base_total
        click.secho("\n🧽 Refine summary:", fg="yellow")
        click.echo(f"   • Passes: {refine_passes}")
        click.echo(
            f"   • Before: total={base_total:.2f} (sets={base_set:.2f}, orbs={base_orb:.2f})"
        )
        click.echo(
            f"   • After : total={total:.2f} (sets={ref_set:.2f}, orbs={ref_orb:.2f})"
        )
        sign = "+" if delta >= 0 else ""
        click.echo(f"   • Δ Score: {sign}{delta:.2f}")

    click.echo("\nLoadout:\n")
    for cat, orbs_list in refined.items():
        click.secho(f"[{cat}]", fg="blue")
        for orb in orbs_list:
            click.echo(
                f"  • {orb.type} — {orb.set_name} ({orb.rarity}) +{orb.value}% (lvl {orb.level})"
            )
        click.echo()

    click.secho("Active Sets (tiers met):", fg="yellow")
    for sname, info in sorted(
        details["sets"].items(), key=lambda kv: (-kv[1]["contribution"], kv[0])
    ):
        click.echo(
            f"  • {sname}: pieces {info['count']}  "
            f"tiers={info['tiers_met']}  W={info['priority']}  "
            f"contrib={info['contribution']:.2f}"
        )

    click.secho("Orb Type Summary:", fg="yellow")
    type_counts, type_bonus = Counter(), Counter()
    for cat, orbs_list in refined.items():
        for orb in orbs_list:
            type_counts[orb.type] += 1
            type_bonus[orb.type] += orb.value

    for t in sorted(type_counts):
        click.echo(
            f"  • {t}: pieces={type_counts[t]} " f"total bonus={type_bonus[t]:.2f}"
        )


def main() -> None:
    cli(prog_name="orb-optimize")


if __name__ == "__main__":
    main()
