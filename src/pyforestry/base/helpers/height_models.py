"""Height-diameter curves and pluggable height sources.

This module provides the height machinery used by height imputation and by the
configurable top-height estimators:

* :class:`NaslundHeightCurve` -- Näslund's two-parameter height-diameter curve
  ``h = 1.3 + d**p / (a + b*d)**p`` (``p = 2`` by default), fit from measured
  ``(diameter, height)`` pairs by ordinary least squares after a linearising
  transform.
* :class:`HeightSource` and its concretions -- a small abstraction that yields a
  height for a tree, and (for curve-based sources) for an arbitrary diameter.
* :func:`resolve_height_source` -- turn the user-facing ``height_source``
  argument (a string, a callable ``f(d) -> h``, a fitted curve, or a ready
  :class:`HeightSource`) into a :class:`HeightSource`.

Heights produced by a curve are *interpolated*, never measured; callers keep the
two provenances distinct (see ``Tree.predicted_height_m``).

Source:
    Näslund, M. (1936). *Skogsförsöksanstaltens gallringsförsök i tallskog.*
    Meddelanden från Statens skogsförsöksanstalt 29(1), 1-169. The height-diameter
    curve and its linearising transform are Näslund's; the least-squares fitting
    procedure and the pluggable ``HeightSource`` abstraction around it are
    pyforestry's own.
"""

import warnings
from typing import Callable, List, Optional, Sequence, Tuple, Union

__all__ = [
    "NaslundHeightCurve",
    "HeightSource",
    "MeasuredHeightSource",
    "CurveHeightSource",
    "resolve_height_source",
    "MIN_HEIGHT_ABOVE_BREAST_M",
]

BREAST_HEIGHT_M = 1.3

# Näslund's curve is linearised by dividing through by ``(h - 1.3)**(1/p)``, which
# grows without bound as a tree approaches breast height. A record only a few
# centimetres above 1.3 m carries almost no information about the curve, yet it
# would dominate the regression and can drive the fit outside its valid range
# altogether. Pairs closer to breast height than this margin are dropped.
MIN_HEIGHT_ABOVE_BREAST_M = 0.5


class NaslundHeightCurve:
    """Näslund's height-diameter curve ``h = 1.3 + d**p / (a + b*d)**p``.

    After Näslund, M. (1936), *Skogsförsöksanstaltens gallringsförsök i tallskog*,
    Meddelanden från Statens skogsförsöksanstalt 29(1).

    The two coefficients ``a`` and ``b`` are positive; ``p`` (the exponent) is
    2 for Näslund's common "minor" function and is occasionally 3, but it may
    also be fit from the data (see :meth:`fit` with ``fit_exponent=True``).
    Heights and the breast-height offset are in metres, diameters in centimetres.

    Parameters
    ----------
    a, b:
        Curve coefficients.
    exponent:
        The exponent ``p``. Defaults to 2.
    """

    __slots__ = ("a", "b", "exponent")

    def __init__(self, a: float, b: float, exponent: float = 2):
        """Store the fitted coefficients and exponent."""
        self.a = a
        self.b = b
        self.exponent = exponent

    def predict(self, diameter_cm: float) -> Optional[float]:
        """Return the curve height (m) at ``diameter_cm``, or ``None`` if undefined.

        ``None`` is returned for a non-positive diameter or if the denominator
        ``a + b*d`` is non-positive (outside the curve's valid range).
        """
        if diameter_cm is None or diameter_cm <= 0:
            return None
        denom = self.a + self.b * diameter_cm
        if denom <= 0:
            return None
        return BREAST_HEIGHT_M + diameter_cm**self.exponent / denom**self.exponent

    @classmethod
    def fit(
        cls,
        diameters_cm: Sequence[float],
        heights_m: Sequence[float],
        exponent: float = 2,
        *,
        fit_exponent: bool = False,
        exponent_bounds: Tuple[float, float] = (1.0, 5.0),
        min_height_above_breast_m: float = MIN_HEIGHT_ABOVE_BREAST_M,
    ) -> Optional["NaslundHeightCurve"]:
        """Fit the curve from measured ``(diameter, height)`` pairs.

        For a fixed exponent ``p`` the fit is ordinary least squares after
        Näslund's linearising transform: with ``y = d / (h - 1.3)**(1/p)`` and
        ``x = d``, ``h = 1.3 + d**p/(a + b*d)**p`` becomes ``y = a + b*x``. Only
        pairs with ``d > 0`` and ``h >= 1.3 + min_height_above_breast_m``
        contribute; see :data:`MIN_HEIGHT_ABOVE_BREAST_M`.

        When ``fit_exponent`` is ``True`` the exponent is fit as well: for each
        candidate ``p`` the coefficients ``a, b`` are obtained as above, and the
        ``p`` minimising the sum of squared *height* residuals over
        ``exponent_bounds`` is chosen (a coarse grid seed refined by
        golden-section search). The height-space criterion is used because the
        transform itself depends on ``p``, so transformed residuals are not
        comparable between candidates; ``a`` and ``b`` remain the linearised
        least-squares solution at the chosen ``p``, which is the conventional way
        the curve is fitted. Identifying the exponent needs at least three usable
        pairs; with fewer, the fixed ``exponent`` is used.

        Parameters
        ----------
        diameters_cm:
            Diameters at breast height (cm).
        heights_m:
            Corresponding measured heights (m).
        exponent:
            The Näslund exponent ``p`` to use (or fall back to). Defaults to 2.
        fit_exponent:
            When ``True``, also fit the exponent. Defaults to ``False``.
        exponent_bounds:
            Inclusive search range for a fitted exponent. Defaults to
            ``(1.0, 5.0)``.
        min_height_above_breast_m:
            Least height above breast height a pair must have to be used.
            Defaults to :data:`MIN_HEIGHT_ABOVE_BREAST_M`.

        Returns
        -------
        NaslundHeightCurve | None
            The fitted curve, or ``None`` if it could not be fit (fewer than two
            usable pairs, or a degenerate design).
        """
        pairs: List[Tuple[float, float]] = []
        near_breast_height = 0
        minimum_height = BREAST_HEIGHT_M + max(0.0, float(min_height_above_breast_m))
        for d, h in zip(diameters_cm, heights_m, strict=False):
            if d is None or h is None:
                continue
            d = float(d)
            h = float(h)
            if d <= 0:
                continue
            if h < minimum_height:
                if h > BREAST_HEIGHT_M:
                    near_breast_height += 1
                continue
            pairs.append((d, h))
        if near_breast_height:
            warnings.warn(
                f"{near_breast_height} height-diameter pair(s) sit within "
                f"{minimum_height - BREAST_HEIGHT_M:.2f} m of breast height and were "
                "excluded from the Näslund fit; they carry almost no curve information "
                "but dominate the linearising transform.",
                stacklevel=2,
            )
        if len(pairs) < 2:
            return None

        if fit_exponent and len(pairs) >= 3:
            fitted = cls._fit_with_exponent(pairs, exponent_bounds)
            if fitted is not None:
                return fitted
        return cls._fit_ab(pairs, exponent)

    @classmethod
    def _fit_ab(
        cls, pairs: Sequence[Tuple[float, float]], exponent: float
    ) -> Optional["NaslundHeightCurve"]:
        """Least-squares fit of ``a, b`` for a fixed exponent (linearised).

        Uses Näslund's own linearisation, ``d / (h - 1.3)**(1/p) = a + b*d``,
        regressing on the diameter itself. Dividing through by ``d`` instead
        (regressing ``1/(h - 1.3)**(1/p)`` on ``1/d``) describes the same line but
        is not the same least-squares problem: it scales every residual by
        ``1/d``, so the fit is pulled towards the smallest trees -- precisely the
        ones that matter least for top height and volume.
        """
        inv_p = 1.0 / exponent
        xs = [d for d, _ in pairs]
        ys = [d * (h - BREAST_HEIGHT_M) ** (-inv_p) for d, h in pairs]
        n = len(xs)
        sum_x = sum(xs)
        sum_y = sum(ys)
        sum_xx = sum(x * x for x in xs)
        sum_xy = sum(x * y for x, y in zip(xs, ys, strict=False))
        denom = n * sum_xx - sum_x * sum_x
        if denom == 0:
            return None
        # intercept -> a, slope -> b in y = a + b*x
        b = (n * sum_xy - sum_x * sum_y) / denom
        a = (sum_y - b * sum_x) / n
        if a <= 0 or b <= 0:
            # A non-positive coefficient is not a usable (monotone) Näslund curve.
            return None
        return cls(a=a, b=b, exponent=exponent)

    @staticmethod
    def _height_sse(curve: "NaslundHeightCurve", pairs: Sequence[Tuple[float, float]]) -> float:
        """Sum of squared height residuals of ``curve`` over ``pairs``."""
        total = 0.0
        for d, h in pairs:
            predicted = curve.predict(d)
            if predicted is None:
                return float("inf")
            total += (h - predicted) ** 2
        return total

    @classmethod
    def _fit_with_exponent(
        cls, pairs: Sequence[Tuple[float, float]], bounds: Tuple[float, float]
    ) -> Optional["NaslundHeightCurve"]:
        """Pick the exponent minimising height residuals, then fit ``a, b``."""
        lo, hi = bounds
        if not hi > lo > 0:
            return None

        def sse_of(p: float) -> float:
            """Height-space SSE of the best ``a, b`` fit at exponent ``p``."""
            curve = cls._fit_ab(pairs, p)
            return float("inf") if curve is None else cls._height_sse(curve, pairs)

        # Coarse grid to bracket the minimum, then golden-section refinement.
        steps = 16
        grid = [lo + (hi - lo) * i / steps for i in range(steps + 1)]
        best_p = min(grid, key=sse_of)
        if sse_of(best_p) == float("inf"):
            return None
        span = (hi - lo) / steps
        left = max(lo, best_p - span)
        right = min(hi, best_p + span)
        inv_phi = (5.0**0.5 - 1.0) / 2.0
        c = right - inv_phi * (right - left)
        d = left + inv_phi * (right - left)
        fc, fd = sse_of(c), sse_of(d)
        for _ in range(40):
            if fc < fd:
                right, d, fd = d, c, fc
                c = right - inv_phi * (right - left)
                fc = sse_of(c)
            else:
                left, c, fc = c, d, fd
                d = left + inv_phi * (right - left)
                fd = sse_of(d)
        return cls._fit_ab(pairs, (left + right) / 2.0)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """Return a readable representation of the curve."""
        return f"NaslundHeightCurve(a={self.a:.5g}, b={self.b:.5g}, exponent={self.exponent})"


class HeightSource:
    """Interface for objects that supply tree heights.

    A height source answers two questions: the height of a given tree
    (:meth:`height_for`) and, when it is curve-based (:attr:`is_curve`), the
    height at an arbitrary diameter (:meth:`height_at_diameter`).
    """

    is_curve: bool = False

    def height_for(self, tree) -> Optional[float]:  # noqa: ANN001
        """Return a height (m) for ``tree``, or ``None`` if unavailable."""
        raise NotImplementedError

    def height_at_diameter(self, diameter_cm: float) -> Optional[float]:
        """Return a height (m) at ``diameter_cm`` (curve sources only)."""
        raise TypeError(
            "this height source cannot evaluate a height at an arbitrary "
            "diameter; supply a curve height source (Näslund or a callable)"
        )


class MeasuredHeightSource(HeightSource):
    """Use each tree's measured ``height_m`` (optionally a predicted fallback).

    Parameters
    ----------
    use_predicted_fallback:
        When ``True`` and a tree has no measured ``height_m``, fall back to its
        ``predicted_height_m`` (an interpolated value). Defaults to ``False``,
        i.e. measured heights only.
    """

    is_curve = False

    def __init__(self, use_predicted_fallback: bool = False):
        """Store whether a predicted-height fallback is allowed."""
        self.use_predicted_fallback = use_predicted_fallback

    def height_for(self, tree) -> Optional[float]:  # noqa: ANN001
        """Return the tree's measured height, or predicted height if allowed."""
        height = getattr(tree, "height_m", None)
        if height is None and self.use_predicted_fallback:
            height = getattr(tree, "predicted_height_m", None)
        return None if height is None else float(height)


class CurveHeightSource(HeightSource):
    """Wrap a diameter-to-height callable (e.g. a fitted Näslund curve).

    Parameters
    ----------
    curve:
        A callable ``f(diameter_cm) -> height_m | None``.
    """

    is_curve = True

    def __init__(self, curve: Callable[[float], Optional[float]]):
        """Store the underlying diameter-to-height callable."""
        self._curve = curve

    def height_for(self, tree) -> Optional[float]:  # noqa: ANN001
        """Return the curve height for the tree's diameter."""
        diameter = getattr(tree, "diameter_cm", None)
        if diameter is None:
            return None
        return self.height_at_diameter(float(diameter))

    def height_at_diameter(self, diameter_cm: float) -> Optional[float]:
        """Return the curve height (m) at ``diameter_cm``."""
        result = self._curve(diameter_cm)
        return None if result is None else float(result)


HeightSourceSpec = Union[str, Callable[[float], Optional[float]], HeightSource, NaslundHeightCurve]


def resolve_height_source(
    source: HeightSourceSpec,
    fit_trees: Optional[Sequence] = None,
    *,
    naslund_exponent: Union[int, float, str] = 2,
) -> Optional[HeightSource]:
    """Turn a ``height_source`` argument into a :class:`HeightSource`.

    Parameters
    ----------
    source:
        One of:

        * ``"measured"`` -- measured heights only;
        * ``"measured+predicted"`` -- measured, falling back to predicted;
        * ``"naslund"`` -- fit a :class:`NaslundHeightCurve` from ``fit_trees``;
        * a callable ``f(diameter_cm) -> height_m``;
        * a :class:`NaslundHeightCurve`; or
        * a ready :class:`HeightSource`.
    fit_trees:
        Trees whose measured ``(diameter, height)`` pairs fit the ``"naslund"``
        curve. Ignored otherwise.
    naslund_exponent:
        Exponent for the ``"naslund"`` fit: a number to fix it, or ``"auto"`` to
        fit the exponent from the data as well. Defaults to 2.

    Returns
    -------
    HeightSource | None
        The resolved source, or ``None`` if ``"naslund"`` could not be fit.
    """
    if isinstance(source, HeightSource):
        return source
    if isinstance(source, NaslundHeightCurve):
        return CurveHeightSource(source.predict)
    if callable(source):
        return CurveHeightSource(source)
    if isinstance(source, str):
        key = source.lower()
        if key == "measured":
            return MeasuredHeightSource()
        if key in ("measured+predicted", "measured_predicted"):
            return MeasuredHeightSource(use_predicted_fallback=True)
        if key in ("naslund", "näslund"):
            diameters = [getattr(t, "diameter_cm", None) for t in (fit_trees or [])]
            heights = [getattr(t, "height_m", None) for t in (fit_trees or [])]
            if isinstance(naslund_exponent, str) and naslund_exponent.lower() == "auto":
                curve = NaslundHeightCurve.fit(diameters, heights, fit_exponent=True)
            else:
                curve = NaslundHeightCurve.fit(diameters, heights, exponent=naslund_exponent)
            return None if curve is None else CurveHeightSource(curve.predict)
        raise ValueError(f"Unknown height source {source!r}.")
    raise TypeError(f"Unsupported height source of type {type(source).__name__}.")
