"""Running Norway's scenario configurations over real stands.

Norway had a scenario configuration, rulesets and a preset, and nothing that
executed any of them -- the whole tier was a mirror of Sweden's scaffolding,
added in the same initial commit, before either region had a runtime. Norway's
four published models were reachable through :func:`pyforestry.project` all
along; what was missing was the scenario runtime around them.

:func:`run_norway_scenario` is that. It is a thin regional entry point over
:func:`pyforestry.simulation.scenario.run_scenario`: it supplies the Kuehne
(2022) Scots-pine model, builds the stands, and hands everything else to the
shared runner, so the manifest Norway emits has the same shape and the same
guarantees as Sweden's.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from pyforestry.base.helpers.primitives import Age, AgeMeasurement, StandBasalArea, Stems
from pyforestry.base.helpers.stand import Stand
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.base.simulation.core import SimulationContext
from pyforestry.norway.adapters.kuehne_2022 import (
    KuehnePineAdapterConfig,
    KuehnePineGrowthModel,
)
from pyforestry.norway.growth.kuehne_2022 import kuehne_2022_stand_volume
from pyforestry.norway.simulation.presets import ScenarioConfig, build_baseline_scenario_config
from pyforestry.norway.volume.brantseg_1967 import brantseg_1967_volume_scots_pine_norway
from pyforestry.simulation.forcing import ForcingSet
from pyforestry.simulation.scenario import ScenarioRunResult, StandUnit, run_scenario
from pyforestry.simulation.stages import STAND_SPECIES_KEY, MeanTree
from pyforestry.simulation.valuation.volume import ValuationSettings

__all__ = [
    "build_kuehne_stands",
    "kuehne_mean_tree",
    "kuehne_stand_volume",
    "run_norway_scenario",
]


def kuehne_stand_volume(ctx: SimulationContext) -> float:
    """Return the stand's volume now, from Kuehne (2022) Eq. 8.

    Evaluated on the context's *current* basal area, dominant height and age, so
    a thinning or a disturbance between two growth steps is visible immediately.
    Reading the ``stand_volume_m3_per_ha`` the model published at its last step
    would not be: it goes stale the moment anything removes a stem, and the run's
    summary would then report the removal as zero and quietly fold the volume
    back into growth.

    Kuehne (2022) is fitted for thinned as well as unthinned stands, so
    re-evaluating it on a post-thinning basal area is within what the model was
    published to do.
    """
    return float(
        kuehne_2022_stand_volume(
            float(ctx.metrics["BasalArea"]["TOTAL"]),
            float(ctx.attrs["kuehne_dominant_height_m"]),
            Age.TOTAL(float(ctx.state.get("t", 0.0))),
        )
    )


def kuehne_mean_tree(ctx: SimulationContext, removed_fraction: float) -> MeanTree:
    """Return the stand's representative stem, so a thinning can be bucked.

    The Kuehne model steps a basal area and a stem count, so a thinning from it
    has no individual stems. It does have a quadratic mean diameter, which the
    stand derives from those two, and the stem that diameter describes is a real
    one: bucking it gives the assortment split a stand of that mean size yields.

    The height is the harder half, because Kuehne (2022) predicts only *dominant*
    height -- its height function is a dominant-height trajectory -- and a mean
    stem is shorter than a dominant one. Substituting the dominant height, which
    this did, makes the representative stem too big: on the shipped baseline it
    bucks to about 12% more wood than the model says the thinning removed, which
    is impossible for a real stem and was previously absorbed unseen into a scale
    factor.

    So the height is *implied from the model instead*. The model states how much
    volume came out and in how many stems, so the mean stem's volume is their
    quotient; :func:`brantseg_1967_volume_scots_pine_norway` gives the volume of a
    Scots pine of a given diameter and height, and this inverts it for the height
    consistent with the model's own figures at the stand's QMD. That is not a new
    height relation: Brantseg (1967) is one of the three single-tree functions
    Kuehne's own volume equation is built on, so the stem this returns is the one
    the model is already implicitly describing.

    Args:
        ctx: The run's context, read before the removal is applied.
        removed_fraction: The share of the stand being taken out.

    Returns:
        The representative stem and how many of it come out.
    """
    stems_removed = float(ctx.metrics["Stems"]["TOTAL"]) * float(removed_fraction)
    diameter_cm = float(ctx.stand.QMD)
    dominant_height_m = float(ctx.attrs["kuehne_dominant_height_m"])

    height_m = dominant_height_m
    if stems_removed > 0.0:
        # What the removal actually costs the stand, evaluated the way the run's
        # own reporter will: Kuehne's volume goes as BA^0.969, so taking a fifth
        # of the basal area does not take a fifth of the volume, and estimating it
        # as one left the implied stem a little too tall.
        basal_area = float(ctx.metrics["BasalArea"]["TOTAL"])
        age = Age.TOTAL(float(ctx.state.get("t", 0.0)))
        before = float(kuehne_2022_stand_volume(basal_area, dominant_height_m, age))
        after = float(
            kuehne_2022_stand_volume(
                basal_area * (1.0 - float(removed_fraction)), dominant_height_m, age
            )
        )
        implied = _height_for_stem_volume(diameter_cm, (before - after) / stems_removed)
        if implied is not None:
            # Never taller than the dominant height: the inversion is a mean, and a
            # mean stem does not out-top the dominant one.
            height_m = min(implied, dominant_height_m)

    return MeanTree(
        species=ctx.attrs.get(STAND_SPECIES_KEY, TreeSpecies.Sweden.pinus_sylvestris),
        diameter_cm=diameter_cm,
        height_m=height_m,
        stems_removed=stems_removed,
    )


def _height_for_stem_volume(diameter_cm: float, volume_m3: float) -> Optional[float]:
    """Return the height at which a Scots pine of ``diameter_cm`` holds ``volume_m3``.

    Brantseg (1967) is monotonic in height at a fixed diameter, so a bisection on
    ``[1.4, 50]`` m finds it. ``None`` when the target volume lies outside what a
    stem of that diameter can hold at any height in that range, which leaves the
    caller's own height in place rather than substituting a fabricated one.
    """
    target = float(volume_m3)
    if target <= 0.0 or diameter_cm <= 0.0:
        return None

    def stem_volume(height_m: float) -> float:
        # AtomicVolume, in m3 -- the function reports dm3 internally and wraps it.
        return float(brantseg_1967_volume_scots_pine_norway(height_m, diameter_cm).value)

    low, high = 1.4, 50.0
    if not (stem_volume(low) <= target <= stem_volume(high)):
        return None
    for _ in range(60):
        mid = 0.5 * (low + high)
        if stem_volume(mid) < target:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


#: The starting stand the Kuehne (2022) baseline projects from. Even-aged Scots
#: pine, at the age and density the paper's own worked example uses as its
#: starting point; a run that wants another supplies its own stands.
_BASELINE_AGE_YEARS = 40.0
_BASELINE_DOMINANT_HEIGHT_M = 12.0
_BASELINE_BASAL_AREA_M2_HA = 20.0
_BASELINE_STEMS_PER_HA = 1400.0


def build_kuehne_stands(
    n_stands: int,
    *,
    basal_area_m2_ha: float = _BASELINE_BASAL_AREA_M2_HA,
    stems_per_ha: float = _BASELINE_STEMS_PER_HA,
) -> list[StandUnit]:
    """Build ``n_stands`` identical aggregate pine stands for a scenario run.

    Identical on purpose: the Kuehne model is deterministic, so identical stands
    give identical rows, and any difference between rows in a run is the
    scenario's doing rather than the inventory's. Supply your own
    :class:`~pyforestry.simulation.scenario.StandUnit` list for real inventory.

    Args:
        n_stands: How many stands to build.
        basal_area_m2_ha: Starting basal area.
        stems_per_ha: Starting stem density.

    Returns:
        One :class:`StandUnit` per stand, ids counting from 1.

    Raises:
        ValueError: If ``n_stands`` is not positive.
    """
    if n_stands <= 0:
        raise ValueError(f"n_stands must be > 0, got {n_stands!r}.")

    species = TreeSpecies.Sweden.pinus_sylvestris
    return [
        StandUnit(
            stand_id=stand_id,
            # Declared here because a whole-stand model's metrics cannot carry it:
            # set_aggregate_metrics drops species detail, by design, on the first
            # step. Pricing a bulk removal needs to know what it was.
            species=species,
            stand=Stand.from_aggregate_metrics(
                {
                    "BasalArea": {"TOTAL": StandBasalArea(basal_area_m2_ha, species=species)},
                    "Stems": {"TOTAL": Stems(stems_per_ha, species=species)},
                },
                area_ha=1.0,
            ),
        )
        for stand_id in range(1, n_stands + 1)
    ]


def run_norway_scenario(
    *,
    global_seed: int,
    output_dir: Path,
    config: Optional[ScenarioConfig] = None,
    stands: Optional[Sequence[StandUnit]] = None,
    n_stands: int = 8,
    n_steps: int = 10,
    step_years: float = 5.0,
    valuation: Optional[ValuationSettings] = None,
    discount_rate: Optional[float] = None,
    disturbance_rate_per_year: float = 0.0,
    thin_at_age: Optional[Sequence[AgeMeasurement]] = None,
    thin_at_year: Optional[Sequence[float]] = None,
    start_age: Optional[AgeMeasurement] = None,
    time_to_breast_height: Optional[float] = None,
    start_year: float = 0.0,
    forcings: Optional[ForcingSet] = None,
) -> ScenarioRunResult:
    """Run a Norway scenario with the Kuehne (2022) pine model and write its artifacts.

    Args:
        global_seed: The run's seed; each stand's derives from it.
        output_dir: Where the three artifacts go.
        config: The scenario configuration. Defaults to the Kuehne baseline.
        stands: The stands to project. Defaults to ``n_stands`` built by
            :func:`build_kuehne_stands`.
        n_stands: How many default stands to build, if ``stands`` is not given.
        n_steps: Number of periods.
        step_years: Period length in years.
        valuation: Price list and bucking settings. **Required**, because
            Norway's scenario declares a valuation stage. This package ships
            no Norwegian price list -- a price list is regional market data,
            not science, and inventing one would put numbers under Norway's
            name with nothing behind them. Supply your own
            :class:`~pyforestry.simulation.valuation.volume.ValuationSettings`,
            and give its price list a
            :class:`~pyforestry.base.pricelist.PricelistIdentity`: since the list
            is yours, it is the only thing that can tell the manifest what
            currency the summary's money is in.
            The Kuehne model is a stand-level one, so a thinning from it has no
            individual stems -- it is bucked at the stand's mean tree instead,
            once, and scaled to the volume the model says came out. See
            :func:`kuehne_mean_tree` for what that assumes.
        discount_rate: The annual rate the summary's net present value is
            discounted at. **Required**, like ``valuation``, because Norway's
            scenario declares a valuation stage and a net present value in an
            artifact has to say what it was discounted at. ``0.0`` states no time
            preference.
        disturbance_rate_per_year: Annual share of the stand a scenario
            disturbance removes, before the scenario's ``disturbance_factor``.
            Supplied by the caller; this package ships no rate, because a
            disturbance rate is a finding and there is no source for one here.
            Zero, the default, makes the stage an exact no-op.
        thin_at_age: Stand ages at which the management stage thins, as
            ``Age.TOTAL(60)``. The one to reach for, and especially here: the
            Kuehne adapter starts its clock at the stand's total age, so the raw
            clock times this replaces meant something different in Norway than in
            Sweden under the same argument name. Defaults to the age
            :func:`build_kuehne_stands` starts its stands at.
        thin_at_year: Calendar years at which it thins instead, read against
            ``start_year``. Mutually exclusive with ``thin_at_age``.
        start_age: How old the stands are at the start. Defaults to
            :data:`_BASELINE_AGE_YEARS` as a *total* age, which is what the
            adapter is configured with; supply it when passing your own stands.
        time_to_breast_height: Years to 1.3 m, needed only to schedule in one age
            measure stands described in the other.
        start_year: Calendar year the projection begins in, which is the year
            a forcing series is read at.
        forcings: Named values the run reads per period -- a weather
            correction, a price index. This package ships none.

    Returns:
        The run result, including the written artifacts.
    """
    resolved_config = config or build_baseline_scenario_config()
    resolved_stands = list(stands) if stands is not None else build_kuehne_stands(n_stands)

    return run_scenario(
        resolved_config,
        build_model=lambda: KuehnePineGrowthModel(
            KuehnePineAdapterConfig(
                dominant_height_m=_BASELINE_DOMINANT_HEIGHT_M,
                start_total_age_years=_BASELINE_AGE_YEARS,
            )
        ),
        stands=resolved_stands,
        volume=kuehne_stand_volume,
        global_seed=global_seed,
        n_steps=n_steps,
        step_years=step_years,
        output_dir=output_dir,
        valuation=valuation,
        discount_rate=discount_rate,
        disturbance_rate_per_year=disturbance_rate_per_year,
        thin_at_age=thin_at_age,
        thin_at_year=thin_at_year,
        start_age=start_age if start_age is not None else Age.TOTAL(_BASELINE_AGE_YEARS),
        time_to_breast_height=time_to_breast_height,
        start_year=start_year,
        forcings=forcings,
        mean_tree=kuehne_mean_tree,
    )
