"""What an imputed tree attribute is, and where it came from.

An :class:`ImputedValue` is deliberately more than a number: it names the
imputer that produced it and carries that imputer's citation, so a modelled
crown radius or height can always answer "according to whom?". A measured value
never becomes one of these -- measurements stay on the tree as plain attributes.
"""

from dataclasses import dataclass

from pyforestry.base.contracts import SourceReference

__all__ = ["ImputedValue"]


@dataclass(frozen=True)
class ImputedValue:
    """A modelled value for one tree attribute, with its provenance.

    Attributes:
        attribute: The attribute this value stands in for, e.g. ``"height_m"``.
        value: The modelled value, in the attribute's own units.
        imputer_id: ``component_id`` of the imputer that produced it.
        source: The publication behind that imputer. A user-supplied callable
            carries the ``"(none)"``/year-0 sentinel, so an uncited value is
            visibly uncited rather than silently unattributed.
    """

    attribute: str
    value: float
    imputer_id: str
    source: SourceReference

    def __post_init__(self) -> None:
        """Reject a non-finite or unnamed value."""
        if not self.attribute:
            raise ValueError("attribute must be a non-empty name.")
        if self.value != self.value or self.value in (float("inf"), float("-inf")):
            raise ValueError(f"Imputed {self.attribute} must be finite, got {self.value!r}.")

    @property
    def is_cited(self) -> bool:
        """Whether this value traces to a publication rather than a bare callable."""
        return self.source.author != "(none)"

    def __float__(self) -> float:
        """Return the value, so an ImputedValue can be used in arithmetic."""
        return float(self.value)
