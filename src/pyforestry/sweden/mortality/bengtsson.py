"""Bengtsson (1978) low-density stand mortality functions."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ._common import (
    calibration_group,
    clamp_probability,
    normalize_part_of_sweden,
    scale_probability_from_5_years,
    species_mortality_fraction_from_tree_probabilities,
)
from .types import MortalityContext


def _adjusted_bald(mean_age_years: float) -> float:
    """Return Bengtsson adjusted age term."""
    if mean_age_years < 100.0:
        return mean_age_years / 10.0 + 1.0
    return min(((mean_age_years - 100.0) / 20.0) * 2.0 + 12.0, 17.0)


def calibrate_bengtsson(
    *,
    context: MortalityContext,
    tree_probabilities: Sequence[float],
    period_years: float = 5.0,
    default_stems_per_tree: float = 1.0,
) -> tuple[list[float], dict[str, float], dict[str, float], dict[str, Any]]:
    """Calibrate tree probabilities to Bengtsson species mortality levels.

    Reference:
        Bengtsson, G. (1978). Beräkning av den naturliga avgången i
        avverkningsberäkningarna för 1973 års skogsutrednings slutbetänkande.
        In: Skog för framtid, SOU 1978:7, bilaga 6.

        Predicts natural mortality in stands of lower (non-self-thinning)
        density; in Elfving's (2010) established-stand mortality model this is
        combined as a density-weighted average with Söderberg (1986)
        self-thinning mortality (see Elfving 2010, "Growth modelling in the
        Heureka system").

    Args:
        context: Unified mortality context.
        tree_probabilities: Base tree probabilities before calibration.
        period_years: Prediction period in years.
        default_stems_per_tree: Fallback represented stems per tree record.

    Returns:
        A tuple with calibrated probabilities, target species fractions,
        correction factors, and diagnostics.
    """
    trees = context.trees
    stand_conditions = context.stand
    site_conditions = context.site

    if len(trees) != len(tree_probabilities):
        raise ValueError("context.trees and tree_probabilities must have equal length.")
    if not trees:
        return [], {}, {}, {}

    region = normalize_part_of_sweden(site_conditions.part_of_sweden)
    south = region == "south"
    mean_age_years = (
        stand_conditions.mean_age_excl_overstorey_years
        if stand_conditions.mean_age_excl_overstorey_years is not None
        else stand_conditions.mean_age_total_years
    )
    if mean_age_years is None:
        raise ValueError("mean_age_excl_overstorey_years or mean_age_total_years is required.")
    adjusted_bald = _adjusted_bald(float(mean_age_years))

    groups_present = {calibration_group(tree.species) for tree in trees}
    target_fractions_5_year: dict[str, float] = {}
    for group in groups_present:
        if group == "pine":
            a2 = 0.38 if south else 0.14
        elif group == "spruce":
            a2 = 0.36 if south else (-0.000236 + 0.0250275 * adjusted_bald)
        elif group == "birch":
            a2 = 0.46 if south else 0.78
        else:
            a2 = 0.46 if south else 0.35
        target_fractions_5_year[group] = clamp_probability(a2 / 20.0)
    target_fractions = {
        group: scale_probability_from_5_years(probability_5, period_years)
        for group, probability_5 in target_fractions_5_year.items()
    }

    current_fractions = species_mortality_fraction_from_tree_probabilities(
        trees=trees,
        tree_probabilities=tree_probabilities,
        default_stems_per_tree=default_stems_per_tree,
        use_calibration_groups=True,
    )
    correction_factors: dict[str, float] = {}
    for group in groups_present:
        current = current_fractions.get(group, 0.0)
        target = target_fractions.get(group, 0.0)
        correction_factors[group] = target / current if current > 0.0 else 1.0

    calibrated_probabilities = [
        clamp_probability(
            probability * correction_factors.get(calibration_group(tree.species), 1.0)
        )
        for tree, probability in zip(trees, tree_probabilities, strict=True)
    ]
    diagnostics = {
        "part_of_sweden": region,
        "adjusted_bald": adjusted_bald,
        "current_fractions": current_fractions,
    }
    return calibrated_probabilities, target_fractions, correction_factors, diagnostics


__all__ = ["calibrate_bengtsson"]


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


class _Descriptor:
    """FormulaModuleDescriptor for Bengtsson (1978) low-density mortality functions."""

    @property
    def component_id(self):
        return "bengtsson_mortality_calibration"

    @property
    def source(self):
        from pyforestry.base.contracts import SourceReference

        return SourceReference(
            author="Bengtsson, G.",
            year=1978,
            title=(
                "Beräkning av den naturliga avgången i avverkningsberäkningarna "
                "för 1973 års skogsutrednings slutbetänkande"
            ),
            note=(
                "In: Skog för framtid, SOU 1978:7, bilaga 6. Low-density stand "
                "mortality; combined with Söderberg (1986) self-thinning mortality "
                "in Elfving's (2010) established-stand mortality model."
            ),
        )

    @property
    def species_groups(self):
        return {}

    @property
    def units(self):
        return {}

    @property
    def kernel_names(self):
        return ["calibrate_bengtsson"]


DESCRIPTOR = _Descriptor()
