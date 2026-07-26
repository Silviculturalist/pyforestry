"""Elfving (2009) continuous thinning-response function for Sweden.

The thinning response is a multiplier applied to the stand basal-area growth that
would be expected under unmanaged conditions. It replaces the discrete
``thinned_0_10`` / ``thinned_10_30`` indicator variables of the stand growth
function when a thinning has actually been simulated.

Reference:
    Elfving, B. (2009). Thinning response function, based on the Swedish
    thinning-fertilisation ("GG") trials; documented as an appendix of Elfving,
    B. (2010) "Growth modelling in the Heureka system", SLU, Faculty of Forestry.

    The response ``THRESP = ln(iG_thinned) - ln(iG_unthinned)`` is modelled from
    the proportion of basal area removed at the last thinning (``THPROP``), the
    time from that thinning to the mid-point of the growth period (``TATH``), the
    residual release effect of earlier thinnings (``RRE``), a newly-thinned
    indicator (``NEWTH``, TATH < 4 yr) and a thinning-from-above indicator
    (``THFA``). Separate coefficients apply to pine- and spruce-dominated stands.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Sequence

from pyforestry.base.contracts import FormulaDescriptor, SourceReference

# Residual release effect decays linearly to zero over this many years.
_RRE_DECAY_PER_YEAR = 0.0333
_RRE_MAX_YEARS = 30.0

# The growth period mid-point offset added to "years since thinning" to get TATH.
_MID_PERIOD_YEARS = 2.5

# Newly-thinned threshold (years) for the pine NEWTH indicator.
_NEWLY_THINNED_YEARS = 4.0


@dataclass(frozen=True)
class ThinningEvent:
    """A single past thinning used by the Elfving (2009) thinning-response model.

    Attributes:
        years_since_thinning: Whole years from the thinning to the start of the
            current 5-year growth period. ``TATH`` is this value plus the
            2.5-year mid-period offset.
        proportion_basal_area_removed: ``THPROP`` -- the proportion (0-1) of stand
            basal area removed at this thinning.
        thinned_from_above: ``THFA`` indicator in [0, 1]; 0 = thinning from below,
            1 = thinning from above. Only used for pine-dominated stands and only
            when ``ignore_thinning_form`` is ``False``.
    """

    years_since_thinning: float
    proportion_basal_area_removed: float
    thinned_from_above: float = 0.0

    @property
    def years_to_mid_period(self) -> float:
        """Return ``TATH`` -- years from the thinning to the growth-period mid-point."""
        return float(self.years_since_thinning) + _MID_PERIOD_YEARS


def residual_release_effect(
    *,
    last_thinning: ThinningEvent,
    earlier_thinnings: Sequence[ThinningEvent],
) -> float:
    """Return ``RRE`` -- the residual release effect of thinnings before the last.

    Each earlier thinning contributes ``THPROP * (1 - 0.0333 * TATH)``. Following
    Elfving (2009), the walk back through history stops once a reference
    thinning is older than 30 years (its own contribution having been counted).

    Args:
        last_thinning: The most recent thinning (its ``THPROP`` is applied
            directly by the response function, not here).
        earlier_thinnings: Thinnings performed *before* ``last_thinning``, ordered
            most-recent first.

    Returns:
        The residual release effect (dimensionless).
    """
    release = 0.0
    reference_tath = last_thinning.years_to_mid_period
    for event in earlier_thinnings:
        # Once a reference thinning falls outside the 30-year window, no older
        # thinning still contributes.
        if reference_tath > _RRE_MAX_YEARS:
            break
        tath = event.years_to_mid_period
        release += event.proportion_basal_area_removed * (1.0 - _RRE_DECAY_PER_YEAR * tath)
        reference_tath = tath
    return release


def elfving_2009_thinning_response_factor(
    *,
    last_thinning: ThinningEvent | None,
    earlier_thinnings: Sequence[ThinningEvent] = (),
    spruce_basal_area_share: float,
    ignore_thinning_form: bool = True,
) -> float:
    """Return the multiplicative thinning-response factor on stand basal-area growth.

    Args:
        last_thinning: The most recent thinning, or ``None`` if the stand has never
            been thinned (in which case the factor is 1.0).
        earlier_thinnings: Thinnings before ``last_thinning`` (most-recent first),
            used for the residual release effect.
        spruce_basal_area_share: Spruce proportion of stand basal area; the
            spruce-dominated function is used when this is >= 0.5.
        ignore_thinning_form: When ``True`` (the default), the thinning-from-above
            term is disabled. It is off by default because the high-thinning
            indicator can be misleading in stands with abundant understorey.

    Returns:
        ``exp(max(0, effect))`` -- a factor >= 1.0 applied to unmanaged stand
        basal-area growth. Returns 1.0 when ``last_thinning`` is ``None``.
    """
    if last_thinning is None:
        return 1.0

    thinning_proportion = float(last_thinning.proportion_basal_area_removed)  # THPROP
    time_after_thinning = last_thinning.years_to_mid_period  # TATH
    residual_release = residual_release_effect(  # RRE
        last_thinning=last_thinning, earlier_thinnings=earlier_thinnings
    )

    # Elfving (2009), Table 1 -- equations written out term-by-term (each coefficient
    # inline next to its variable) to keep them checkable against the published table.
    if float(spruce_basal_area_share) >= 0.5:
        effect = (
            0.0589
            + 0.8478 * thinning_proportion
            + 0.4821 * residual_release
            - 0.0333 * thinning_proportion * time_after_thinning
        )
    else:
        newly_thinned = 1.0 if time_after_thinning < _NEWLY_THINNED_YEARS else 0.0  # NEWTH
        thinned_from_above = (  # THFA * THPROP (0 unless thinning form is used)
            0.0
            if ignore_thinning_form
            else float(last_thinning.thinned_from_above) * thinning_proportion
        )
        effect = (
            0.0585
            + 0.4617 * thinning_proportion
            + 0.2843 * residual_release
            - 0.01832 * thinning_proportion * time_after_thinning
            - 0.0943 * newly_thinned
            + 0.1172 * thinned_from_above
        )

    return exp(max(0.0, effect))


__all__ = [
    "ThinningEvent",
    "residual_release_effect",
    "elfving_2009_thinning_response_factor",
]


DESCRIPTOR = FormulaDescriptor(
    component_id="elfving_2009_thinning_response",
    source=SourceReference(
        author="Elfving, B.",
        year=2009,
        title="Thinning response function based on the Swedish thinning-fertilisation (GG) trials",
        note=(
            "Documented as an appendix of Elfving, B. (2010) 'Growth modelling in the "
            "Heureka system', Sveriges lantbruksuniversitet, Faculty of Forestry. The "
            "work is dated 2009; the containing report is 2010."
        ),
    ),
    kind="formula",
    domain="growth",
    composes=(),
    kernel_names=("elfving_2009_thinning_response_factor",),
)
