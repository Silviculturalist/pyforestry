"""Runtime bindings for Swedish equations — glue, not science.

An adapter's job is to make published equations runnable: read what a model
needs off a :class:`~pyforestry.base.helpers.stand.Stand`, call the equation
kernels that live in the domain packages (``sweden/growth``, ``sweden/height``,
``sweden/volume``, ``sweden/regeneration``, …), and write the results back
through the simulation contract. That is the whole remit.

The line this package draws is enforceable rather than aspirational: **an
adapter carries no scientific coefficient literals.** If a number here has more
than a couple of decimals and is not a unit factor, it is a fitted coefficient
that has escaped its publication, and ``AL001`` in
``scripts/check_architecture_lint.py`` will say so. Whole published growth-and-
yield systems, which do own their coefficients, live one directory over in
:mod:`pyforestry.sweden.systems`.

So: to check a number against a paper, open ``systems/`` or a domain package.
To check how a model is driven, open this one.
"""

from pyforestry.sweden.mortality.naslund_1986 import Naslund1986DamageModel

from .elfving_1982 import (
    HuginCropTreeProbability,
    HuginMeanHeightModel,
    NfiRegion,
    NyskogReconstruction,
    NyskogReconstructionSummary,
    RegenerationType,
)
from .elfving_2010 import Elfving2010Config, Elfving2010Inputs, Elfving2010Model
from .soderberg_1986_growth import Soderberg1986Config, Soderberg1986Model

__all__ = [
    "Elfving2010Config",
    "Elfving2010Inputs",
    "Elfving2010Model",
    "HuginCropTreeProbability",
    "HuginMeanHeightModel",
    "Naslund1986DamageModel",
    "NfiRegion",
    "NyskogReconstruction",
    "NyskogReconstructionSummary",
    "RegenerationType",
    "Soderberg1986Config",
    "Soderberg1986Model",
]
