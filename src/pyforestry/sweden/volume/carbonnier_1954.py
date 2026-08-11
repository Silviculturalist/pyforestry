"""Larch volume functions, Carbonnier (1954).

Source:
    Carbonnier, C. (1954). *Funktioner för kubering av europeisk, sibirisk och
    japansk lärk.* Manuscript; no formal publication. Reproduced in the Heureka PM
    of 2004-01-20 by Björn Elfving.
"""

from pyforestry.base.contracts import FormulaDescriptor, SourceReference


def carbonnier_1954_volume_larch(diameter_cm, height_m):
    """
    Volume of Larch trees, from Carbonnier 1954.

    Source:
        Carbonnier, C. 1954. Funktioner för kubering av europeisk, sibirisk och japansk lärk. MS.
        PM for Heureka 2004-01-20 Björn Elfving.
        Available: https://www.heurekaslu.org/w/images/9/93/Heureka_prognossystem_(Elfving_rapportutkast).pdf

    Parameters:
        diameter_cm (float): Diameter at breast height in cm.
        height_m (float): Height of the tree in meters.

    Returns:
        float: Volume of the tree in m³.
    """
    return (
        0.04801 * (diameter_cm**2) * height_m
        + 0.08886 * (diameter_cm**2)
        - 0.01012 * (diameter_cm**3)
        - 0.08406 * diameter_cm * height_m
        + 0.1972 * height_m
    ) / 1000


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


DESCRIPTOR = FormulaDescriptor(
    component_id="carbonnier_1954_volume",
    source=SourceReference(
        author="Carbonnier, C.",
        year=1954,
        title=("Funktioner för kubering av europeisk, sibirisk och japansk lärk"),
        note=(
            "Manuscript; no formal publication. Reproduced in the Heureka PM of "
            "2004-01-20 by Björn Elfving."
        ),
    ),
    species_groups={},
    units={},
    kernel_names=("carbonnier_1954_volume_larch",),
)
