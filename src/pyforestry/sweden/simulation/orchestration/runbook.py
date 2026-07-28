"""Running Sweden's scenario configurations over real stands.

This module used to emit the artifact contract from a seeded random walk, with
every file stamped ``"synthetic": true`` and a warning on every call, because
nothing existed that could run a configuration for real. That is what
:func:`pyforestry.simulation.scenario.run_scenario` now does, and this is
Sweden's entry point into it: it supplies the Elfving (2010) growth model, a
Brandel (1990) volume reporter and a starting tree list, and hands everything
else to the shared runner.

The numbers it writes are a projection. Nothing is stamped synthetic because
nothing is.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from pyforestry.base.helpers.plot import CircularPlot
from pyforestry.base.helpers.stand import Stand
from pyforestry.base.helpers.tree import Tree
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies
from pyforestry.base.simulation.core import SimulationContext
from pyforestry.simulation.forcing import ForcingSet
from pyforestry.simulation.scenario import ScenarioRunResult, StandUnit, run_scenario
from pyforestry.simulation.valuation.volume import StemDimensions, ValuationSettings
from pyforestry.sweden.adapters.elfving_2010 import Elfving2010Model
from pyforestry.sweden.simulation.presets import ScenarioConfig, build_baseline_scenario_config
from pyforestry.sweden.timber import SweTimber

__all__ = [
    "brandel_stand_volume",
    "build_even_aged_stands",
    "run_sweden_scenario",
    "swedish_timber_factory",
]


def swedish_timber_factory(removal: StemDimensions) -> SweTimber:
    """Build the :class:`SweTimber` Sweden's taper functions require.

    ``EdgrenNylinder1949.validate`` rejects anything that is not a ``SweTimber``,
    so a Sweden valuation configured with the base ``Timber`` the ledger builds
    by default fails inside the bucker rather than at configuration time. Pass
    this as ``ValuationSettings(timber_factory=...)``.

    Serves either kind of removal -- an individual stem or a stand's mean tree --
    since both report a species, a diameter and a height.
    """
    return SweTimber(
        species=removal.species_name,
        diameter_cm=removal.diameter_cm,
        height_m=removal.height_m,
    )


#: The stand a Sweden scenario starts from unless the caller supplies one:
#: an even-aged Norway spruce stand at about first-thinning size.
_BASELINE_AGE_YEARS = 40.0
_BASELINE_STEMS_PER_HA = 1200.0
_BASELINE_MEAN_DBH_CM = 18.0
_BASELINE_MEAN_HEIGHT_M = 16.0
_TREES_PER_STAND = 25

#: Site facts the Elfving (2010) kernels need, which a bare synthetic stand does
#: not carry. Central Sweden, spruce site index H100 = 26 m.
_DEFAULT_ATTRS: Mapping[str, Any] = {
    "site_index_m": 26.0,
    "latitude_deg": 60.5,
    "altitude_m": 150.0,
    "temperature_sum_dd": 1100.0,
    "distance_to_coast_km": 100.0,
}


def _volume_species_name(species: TreeName | None) -> str:
    """Return the species name Brandel's dispatch expects."""
    if species is None:
        return str(TreeSpecies.Sweden.picea_abies.full_name)
    return str(getattr(species, "full_name", species))


def brandel_stand_volume(ctx: SimulationContext) -> float:
    """Return the stand's standing volume now, in m³/ha, from Brandel (1990).

    Summed over the tree list as it currently stands, so a thinning between two
    growth steps is visible immediately -- a reporter that read a value cached at
    the last model step would report every removal as zero and fold the volume it
    took back into growth.

    Trees too small for the volume functions contribute nothing rather than
    raising: a stand of saplings has a volume, and it is near enough zero.
    """
    total = 0.0
    for plot in ctx.plots:
        for tree in plot.trees:
            diameter_cm = float(tree.diameter_cm or 0.0)
            height_m = float(tree.height_m or 0.0)
            weight = float(tree.weight_n or 0.0)
            if diameter_cm <= 0.0 or height_m <= 1.3 or weight <= 0.0:
                continue
            timber = SweTimber(
                species=_volume_species_name(tree.species),
                diameter_cm=diameter_cm,
                height_m=height_m,
            )
            try:
                total += float(timber.getvolume()) * weight
            except ValueError:
                continue
    return total


def build_even_aged_stands(
    n_stands: int,
    *,
    species: TreeName | None = None,
    stems_per_ha: float = _BASELINE_STEMS_PER_HA,
    mean_dbh_cm: float = _BASELINE_MEAN_DBH_CM,
    mean_height_m: float = _BASELINE_MEAN_HEIGHT_M,
    age_years: float = _BASELINE_AGE_YEARS,
) -> list[StandUnit]:
    """Build ``n_stands`` even-aged stands as a starting inventory.

    A linear diameter spread around the mean, so the stand has a distribution for
    a single-tree model to work on rather than one repeated tree. Supply your own
    :class:`~pyforestry.simulation.scenario.StandUnit` list for real inventory.

    Raises:
        ValueError: If ``n_stands`` is not positive.
    """
    if n_stands <= 0:
        raise ValueError(f"n_stands must be > 0, got {n_stands!r}.")

    resolved_species = species or TreeSpecies.Sweden.picea_abies
    weight_per_tree = stems_per_ha / _TREES_PER_STAND
    spread = mean_dbh_cm * 0.3

    units: list[StandUnit] = []
    for stand_id in range(1, n_stands + 1):
        trees = []
        for index in range(_TREES_PER_STAND):
            offset = (index / (_TREES_PER_STAND - 1) - 0.5) * 2.0
            trees.append(
                Tree(
                    species=resolved_species,
                    diameter_cm=mean_dbh_cm + offset * spread,
                    height_m=mean_height_m + offset * spread * 0.4,
                    age=age_years,
                    weight_n=weight_per_tree,
                )
            )
        units.append(
            StandUnit(
                stand_id=stand_id,
                stand=Stand(
                    area_ha=1.0,
                    plots=[CircularPlot(id=1, area_m2=10_000.0, trees=trees)],
                ),
            )
        )
    return units


def run_sweden_scenario(
    *,
    global_seed: int,
    output_dir: Path,
    config: Optional[ScenarioConfig] = None,
    stands: Optional[Sequence[StandUnit]] = None,
    n_stands: int = 8,
    n_steps: int = 10,
    step_years: float = 5.0,
    attrs: Optional[Mapping[str, Any]] = None,
    valuation: Optional[ValuationSettings] = None,
    disturbance_rate_per_year: float = 0.0,
    thin_at_years: Sequence[float] = (),
    start_year: float = 0.0,
    forcings: Optional[ForcingSet] = None,
) -> ScenarioRunResult:
    """Run a Sweden scenario with the Elfving (2010) model and write its artifacts.

    Args:
        global_seed: The run's seed; each stand's derives from it.
        output_dir: Where the three artifacts go.
        config: The scenario configuration. Defaults to the baseline.
        stands: Stands to project. Defaults to ``n_stands`` even-aged spruce
            stands from :func:`build_even_aged_stands`.
        n_stands: How many default stands to build.
        n_steps: Number of periods.
        step_years: Period length in years.
        attrs: Site facts for the growth model, merged over the defaults.
        valuation: Price list, taper and bucking settings. Required if the
            configuration declares a ``"valuation"`` stage, which Sweden's
            baseline does.
        disturbance_rate_per_year: Annual share of the stand a scenario
            disturbance removes, before the scenario's ``disturbance_factor``.
            Supplied by the caller; this package ships no rate, because a
            disturbance rate is a finding and there is no source for one here.
            Zero, the default, makes the stage an exact no-op.
        thin_at_years: Clock times at which the management stage thins.
        start_year: Calendar year the projection begins in, which is the year
            a forcing series is read at.
        forcings: Named values the run reads per period -- a weather
            correction, a price index. This package ships none.

    Returns:
        The run result, including the written artifacts.
    """
    resolved_config = config or build_baseline_scenario_config()
    resolved_stands = list(stands) if stands is not None else build_even_aged_stands(n_stands)
    resolved_attrs = {**_DEFAULT_ATTRS, **(attrs or {})}

    return run_scenario(
        resolved_config,
        build_model=Elfving2010Model,
        stands=resolved_stands,
        volume=brandel_stand_volume,
        global_seed=global_seed,
        n_steps=n_steps,
        step_years=step_years,
        output_dir=output_dir,
        attrs=resolved_attrs,
        valuation=valuation,
        disturbance_rate_per_year=disturbance_rate_per_year,
        thin_at_years=thin_at_years,
        start_year=start_year,
        forcings=forcings,
    )
