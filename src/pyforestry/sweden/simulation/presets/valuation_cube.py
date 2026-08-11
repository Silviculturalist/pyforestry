"""Building and loading the Mellanskog-2013 valuation solution cube.

A solution cube is a precomputed bucking result for a grid of species, diameters
and heights: generating one takes minutes and writes a file, loading one is
milliseconds. Both are filesystem work, and both used to be classmethods and
methods on the Elfving 2010 pipeline -- so a class whose job is to step a stand
also owned a multi-minute build, a ``mkdir``, and a file-existence policy.

They are module-level functions here because none of them needs a pipeline. What
they need is a path and a grid, and the pipeline passes those in.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.base.pricelist.solutioncube import SolutionCube
from pyforestry.sweden.pricelist.data.mellanskog_2013 import MELLANSKOG_2013_PRICE_DATA
from pyforestry.sweden.taper.edgren_nylinder_1949 import EdgrenNylinder1949
from pyforestry.sweden.timber.swe_timber import SweTimber

__all__ = [
    "RECOMMENDED_SPECIES",
    "ensure_cube_file",
    "generate_cube",
    "load_cube",
]

#: The species the Swedish pipelines value through a cube. A cube covering only
#: these is far smaller than one covering every species in the pricelist, and
#: trees outside it fall back to direct bucking, which is correct but slower.
RECOMMENDED_SPECIES: Tuple[str, ...] = (
    TreeSpecies.Sweden.pinus_sylvestris.full_name,
    TreeSpecies.Sweden.picea_abies.full_name,
)


def generate_cube(
    *,
    workers: int = -1,
    dbh_range_cm: Tuple[float, float] = (10.0, 40.0),
    height_range_m: Tuple[float, float] = (8.0, 30.0),
    dbh_step_cm: int = 5,
    height_step_m: float = 2.0,
) -> SolutionCube:
    """Build a Mellanskog-2013 cube over the recommended species and grid.

    This is the expensive one: it buckets every (species, diameter, height) cell
    on the grid. Narrow the ranges or widen the steps to trade accuracy for time.
    """
    return SolutionCube.generate(
        pricelist_data=MELLANSKOG_2013_PRICE_DATA,
        taper_model=EdgrenNylinder1949,
        timber_class=SweTimber,
        species_list=list(RECOMMENDED_SPECIES),
        dbh_range=(float(dbh_range_cm[0]), float(dbh_range_cm[1])),
        height_range=(float(height_range_m[0]), float(height_range_m[1])),
        dbh_step=max(1, int(dbh_step_cm)),
        height_step=max(0.1, float(height_step_m)),
        workers=int(workers),
    )


def ensure_cube_file(
    *,
    path: str,
    overwrite: bool = False,
    workers: int = -1,
    dbh_range_cm: Tuple[float, float] = (10.0, 40.0),
    height_range_m: Tuple[float, float] = (8.0, 30.0),
    dbh_step_cm: int = 5,
    height_step_m: float = 2.0,
) -> str:
    """Write a cube to ``path`` unless one is already there.

    Returns the path either way, so a caller can use the result without checking
    whether it built anything.
    """
    cube_path = Path(path)
    if cube_path.exists() and not overwrite:
        return str(cube_path)

    cube_path.parent.mkdir(parents=True, exist_ok=True)
    cube = generate_cube(
        workers=workers,
        dbh_range_cm=dbh_range_cm,
        height_range_m=height_range_m,
        dbh_step_cm=dbh_step_cm,
        height_step_m=height_step_m,
    )
    cube.save(str(cube_path))
    return str(cube_path)


def load_cube(path: str) -> SolutionCube:
    """Load a cube, checking it was built against the Mellanskog 2013 pricelist.

    The check matters: a cube holds *values*, so one built from a different
    pricelist would price this pipeline's stands at another year's prices without
    anything in the numbers looking wrong.
    """
    return SolutionCube.load(path, pricelist_to_verify=MELLANSKOG_2013_PRICE_DATA)
