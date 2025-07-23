from math import isclose

import pytest

from pyforestry.base.helpers.primitives import Age
from pyforestry.sweden.siteindex.elfving_kiviste_1997 import (
    elfving_kiviste_1997_height_trajectory_sweden_pine,
)
from pyforestry.sweden.siteindex.eriksson_1997 import (
    eriksson_1997_height_trajectory_sweden_birch,
)
from pyforestry.sweden.siteindex.hagglund_remrod_1977 import (
    hagglund_remrod_1977_height_trajectories_lodgepole_pine,
)
from pyforestry.sweden.siteindex.johansson_1996 import (
    johansson_1996_height_trajectory_sweden_aspen,
)
from pyforestry.sweden.siteindex.johansson_1999 import (
    johansson_1999_height_trajectory_sweden_alnus_glutinosa,
    johansson_1999_height_trajectory_sweden_alnus_incana,
)
from pyforestry.sweden.siteindex.johansson_2011 import (
    johansson_2011_height_trajectory_sweden_poplar,
)
from pyforestry.sweden.siteindex.johansson_2013 import (
    johansson_2013_height_trajectory_sweden_beech,
    johansson_2013_height_trajectory_sweden_hybrid_aspen,
    johansson_2013_height_trajectory_sweden_larch,
    johansson_2013_height_trajectory_sweden_oak,
)


@pytest.mark.parametrize(
    "fn, args, expected",
    [
        (
            elfving_kiviste_1997_height_trajectory_sweden_pine,
            (15.0, Age.TOTAL(20), Age.TOTAL(40)),
            27.8387463,
        ),
        (
            eriksson_1997_height_trajectory_sweden_birch,
            (18.0, Age.DBH(40), Age.DBH(60)),
            21.8470492,
        ),
        (
            hagglund_remrod_1977_height_trajectories_lodgepole_pine,
            (15.0, Age.DBH(20), Age.DBH(40)),
            24.2168160,
        ),
        (johansson_1996_height_trajectory_sweden_aspen, (15.0, 20.0, 40.0), 26.0672042),
        (johansson_1999_height_trajectory_sweden_alnus_glutinosa, (15.0, 20.0, 40.0), 22.1336124),
        (johansson_1999_height_trajectory_sweden_alnus_incana, (15.0, 20.0, 40.0), 20.7304417),
        (johansson_2011_height_trajectory_sweden_poplar, (15.0, 20.0, 40.0), 22.1061066),
        (johansson_2013_height_trajectory_sweden_beech, (20.0, 40.0, 80.0), 31.1822067),
        (johansson_2013_height_trajectory_sweden_hybrid_aspen, (15.0, 20.0, 40.0), 23.5521170),
        (johansson_2013_height_trajectory_sweden_larch, (15.0, 20.0, 40.0), 25.1774356),
        (johansson_2013_height_trajectory_sweden_oak, (15.0, 40.0, 80.0), 23.3363153),
    ],
)
def test_site_index_functions(fn, args, expected):
    res = fn(*args)
    assert isclose(float(res), expected, rel_tol=1e-6)
    assert res > 0
