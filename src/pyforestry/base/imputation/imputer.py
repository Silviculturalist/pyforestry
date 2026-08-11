"""The imputer contract, and a wrapper for ad-hoc callables.

An imputer produces one tree attribute from whatever the tree already carries.
Like every other model in this package it is :class:`Describable`: it declares a
``component_id`` and a :class:`SourceReference`, so the value it produces can be
traced back to a publication.

Some imputers are fitted from the stand they are applied to -- the Naslund
height curve is fitted from the stand's own measured height-diameter pairs --
which is what :meth:`Imputer.fit` is for. Stateless imputers return themselves.
"""

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence, runtime_checkable

from pyforestry.base.contracts import SourceReference

__all__ = ["CallableImputer", "Imputer", "UNCITED", "uncited_source"]

#: Author string marking a value that traces to no publication. Matches the
#: sentinel used by ``retained_trees``, the Swedish mortality engine and
#: ``base.competition``.
UNCITED = "(none)"


def uncited_source(label: str) -> SourceReference:
    """Build the not-applicable citation for an imputer with no publication.

    Args:
        label: Short description of what the callable does.

    Returns:
        A :class:`SourceReference` with author ``"(none)"`` and year 0 -- the
        sentinel for "not applicable", not a citation date.
    """
    return SourceReference(
        author=UNCITED,
        year=0,
        title=label,
        note=(
            "Caller-supplied imputer with no publication behind it. year=0 is a "
            "sentinel for 'not applicable', not a citation date."
        ),
    )


@runtime_checkable
class Imputer(Protocol):
    """Produces one tree attribute from the rest of the tree record."""

    @property
    def component_id(self) -> str:
        """Stable identifier for this imputer."""
        ...

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance for whatever this imputer computes."""
        ...

    @property
    def attribute(self) -> str:
        """Name of the tree attribute produced, e.g. ``"height_m"``."""
        ...

    def fit(self, trees: Sequence[Any], context: Mapping[str, Any]) -> Optional["Imputer"]:
        """Bind to a set of trees, returning an imputer ready to use.

        Args:
            trees: Every tree the imputer may be applied to.
            context: Stand-level values an imputer may need.

        Returns:
            An imputer bound to ``trees`` -- often ``self`` for a stateless model
            -- or ``None`` if it could not be fitted from what is available.
        """
        ...

    def impute(self, tree: Any, context: Mapping[str, Any]) -> Optional[float]:
        """Return a value for ``tree``, or ``None`` if it cannot be produced."""
        ...


@dataclass(frozen=True)
class CallableImputer:
    """Wrap a plain callable so ad-hoc imputers carry provenance too.

    The value it produces is recorded as uncited, which is the honest label: a
    lambda has no publication. That keeps caller-supplied values distinguishable
    from ones a published model produced.

    Attributes:
        attribute: The attribute produced, e.g. ``"crown_radius_m"``.
        function: ``f(tree) -> value | None``.
        label: Short description used as the citation title and, slugified, as
            the ``component_id``.
    """

    attribute: str
    function: Callable[[Any], Optional[float]]
    label: str = "caller-supplied callable"

    @property
    def component_id(self) -> str:
        """Identifier derived from the attribute and label."""
        slug = "".join(c if c.isalnum() else "_" for c in self.label.lower()).strip("_")
        return f"callable_{self.attribute}_{slug}"

    @property
    def source(self) -> SourceReference:
        """The not-applicable citation; a callable has no publication."""
        return uncited_source(self.label)

    def fit(self, trees: Sequence[Any], context: Mapping[str, Any]) -> "CallableImputer":
        """Return ``self``; a callable needs no fitting."""
        return self

    def impute(self, tree: Any, context: Mapping[str, Any]) -> Optional[float]:
        """Evaluate the callable for ``tree``."""
        value = self.function(tree)
        return None if value is None else float(value)
