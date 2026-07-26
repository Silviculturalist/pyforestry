"""Filling in tree attributes a record does not carry, with provenance.

Models keep needing attributes a :class:`~pyforestry.base.helpers.tree.Tree` was
not measured for: the influence-zone competition indices need
``crown_radius_m``, Marklund (1988) T12/T15/T16 need ``crown_base_height_m``,
and height is missing on most inventory trees. This package supplies one
mechanism for all of them.

The rule is that **plain attributes are measurements**. A modelled value never
overwrites one; it goes in ``Tree.imputed`` as an
:class:`~pyforestry.base.contracts.ImputedValue` carrying the imputer
that produced it and that imputer's citation, and
:meth:`~pyforestry.base.helpers.tree.Tree.value_of` resolves the two::

    >>> stand.impute("height_m")                  # Naslund curve, fitted to the stand
    >>> tree.height_m                             # None -- never measured
    >>> tree.value_of("height_m")                 # 13.28
    >>> tree.provenance("height_m")               # 'imputed'
    >>> tree.imputed_source("height_m").author    # 'Näslund, M.'

Attributes with no published model are supplied by the caller, and are recorded
as uncited rather than silently unattributed::

    >>> stand.impute("crown_radius_m", lambda t: 0.15 * t.diameter_cm)
    >>> tree.imputed["crown_radius_m"].is_cited   # False

This package holds no science of its own: it is plumbing plus one adapter over
the Näslund curve that already lives in
:mod:`pyforestry.base.helpers.height_models`.
"""

from pyforestry.base.contracts import FormulaDescriptor, ImputedValue, SourceReference

from .height import NaslundHeightImputer
from .imputer import UNCITED, CallableImputer, Imputer, uncited_source
from .registry import (
    ImputerSpec,
    available_attributes,
    imputers_for,
    register_imputer,
    resolve_imputer,
)

__all__ = [
    "UNCITED",
    "CallableImputer",
    "ImputedValue",
    "Imputer",
    "ImputerSpec",
    "NaslundHeightImputer",
    "available_attributes",
    "imputers_for",
    "register_imputer",
    "resolve_imputer",
    "uncited_source",
]

DESCRIPTOR = FormulaDescriptor(
    component_id="tree_attribute_imputation",
    source=SourceReference(
        author="(none)",
        year=0,
        title="Tree attribute imputation (pyforestry mechanism)",
        note=(
            "No primary publication, and none is possible: this package is the "
            "mechanism for recording modelled tree attributes with their provenance, "
            "not a model. year=0 is a sentinel for 'not applicable', not a citation "
            "date. Each registered imputer carries its own citation on `.source`; the "
            "only one shipped wraps Näslund (1936). Imputer component_ids are listed "
            "by `imputers_for(attribute)`; `composes` names the catalogued models "
            "behind them."
        ),
    ),
    species_groups={},
    units={"height_m": "m", "crown_radius_m": "m"},
    kernel_names=("resolve_imputer", "register_imputer"),
    composes=("naslund_1936_height_curve",),
    domain="imputation",
)
