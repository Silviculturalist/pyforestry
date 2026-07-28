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

from pyforestry.base.helpers.primitives import Age, StandBasalArea, Stems
from pyforestry.base.helpers.stand import Stand
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.base.simulation.core import SimulationContext
from pyforestry.norway.adapters.kuehne_2022 import (
    KuehnePineAdapterConfig,
    KuehnePineGrowthModel,
)
from pyforestry.norway.growth.kuehne_2022 import kuehne_2022_stand_volume
from pyforestry.norway.simulation.presets import ScenarioConfig, build_baseline_scenario_config
from pyforestry.simulation.forcing import ForcingSet
from pyforestry.simulation.scenario import ScenarioRunResult, StandUnit, run_scenario

__all__ = ["build_kuehne_stands", "kuehne_stand_volume", "run_norway_scenario"]


def kuehne_stand_volume(ctx: SimulationContext) -> float:
    """Return the stand's volume now, from Kuehne (2022) Eq. 10.

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
    disturbance_rate_per_year: float = 0.0,
    thin_at_years: Sequence[float] = (),
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
        disturbance_rate_per_year=disturbance_rate_per_year,
        thin_at_years=thin_at_years,
        start_year=start_year,
        forcings=forcings,
    )
