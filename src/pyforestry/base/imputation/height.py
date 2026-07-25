"""Height imputation from a fitted height-diameter curve.

A thin adapter over the existing height machinery in
:mod:`pyforestry.base.helpers.height_models`: the curve, its fit and its
linearising transform all live there and are unchanged. This module only teaches
them the :class:`~pyforestry.base.imputation.imputer.Imputer` contract, so an
imputed height records that Naslund's curve produced it.

Source:
    Naslund, M. (1936). *Skogsforsoksanstaltens gallringsforsok i tallskog.*
    Meddelanden fran Statens skogsforsoksanstalt 29(1), 1-169.
"""

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence, Union

from pyforestry.base.contracts import SourceReference
from pyforestry.base.helpers.height_models import (
    HeightSource,
    HeightSourceSpec,
    resolve_height_source,
)

__all__ = ["NaslundHeightImputer"]

NASLUND_1936 = SourceReference(
    author="Näslund, M.",
    year=1936,
    title="Skogsförsöksanstaltens gallringsförsök i tallskog",
    note=(
        "Meddelanden från Statens skogsförsöksanstalt 29(1), 1-169. The "
        "height-diameter curve and its linearising transform are Näslund's; the "
        "least-squares fitting procedure around them is pyforestry's own."
    ),
)


@dataclass
class NaslundHeightImputer:
    """Impute ``height_m`` from a height-diameter curve fitted to the stand.

    The curve is fitted from the measured ``(diameter_cm, height_m)`` pairs of
    the trees it is given, so this imputer must be :meth:`fit` before use --
    :meth:`~pyforestry.base.helpers.stand.Stand.impute` does that for you.

    Attributes:
        spec: What to fit. ``"naslund"`` fits from the stand's own pairs; a
            callable ``f(diameter_cm) -> height_m`` or an already-fitted
            :class:`~pyforestry.base.helpers.height_models.NaslundHeightCurve`
            is used directly.
        naslund_exponent: Exponent for the fit, or ``"auto"`` to fit it too.
    """

    spec: HeightSourceSpec = "naslund"
    naslund_exponent: Union[int, float, str] = 2
    _source: Optional[HeightSource] = field(default=None, repr=False, compare=False)

    attribute: str = field(default="height_m", init=False)

    @property
    def component_id(self) -> str:
        """Stable identifier for this imputer."""
        return "naslund_height_imputer"

    @property
    def source(self) -> SourceReference:
        """Näslund (1936), the curve this imputer evaluates."""
        return NASLUND_1936

    def fit(
        self, trees: Sequence[Any], context: Mapping[str, Any]
    ) -> Optional["NaslundHeightImputer"]:
        """Fit the curve from ``trees``.

        Args:
            trees: Trees whose measured height-diameter pairs the curve is fitted
                from. Ignored when ``spec`` is already a curve or a callable.
            context: Unused; present for the :class:`Imputer` contract.

        Returns:
            A bound copy ready to impute, or ``None`` if the curve could not be
            fitted -- too few usable pairs, a single diameter, or a fit implying
            a non-monotone curve.

        Raises:
            ValueError: If ``spec`` resolves to measured heights, which cannot
                impute anything.
        """
        resolved = resolve_height_source(self.spec, trees, naslund_exponent=self.naslund_exponent)
        if resolved is None:
            return None
        if not resolved.is_curve:
            raise ValueError(
                "Height imputation requires a curve height source (Näslund or a "
                "callable), not measured heights."
            )
        return NaslundHeightImputer(
            spec=self.spec, naslund_exponent=self.naslund_exponent, _source=resolved
        )

    def impute(self, tree: Any, context: Mapping[str, Any]) -> Optional[float]:
        """Return the curve height for ``tree``, or ``None`` without a diameter.

        Args:
            tree: The tree to impute for; needs ``diameter_cm``.
            context: Unused; present for the :class:`Imputer` contract.

        Returns:
            The modelled height in metres, or ``None``.

        Raises:
            RuntimeError: If the imputer has not been fitted.
        """
        if self._source is None:
            raise RuntimeError(
                "NaslundHeightImputer must be fit() before use; Stand.impute() does this."
            )
        diameter = getattr(tree, "diameter_cm", None)
        if diameter is None:
            return None
        return self._source.height_at_diameter(float(diameter))
