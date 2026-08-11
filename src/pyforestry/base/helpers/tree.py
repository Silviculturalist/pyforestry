"""Classes for representing individual and aggregated tree records."""

from itertools import count
from typing import Any, Dict, Optional, Union

from pyforestry.base.contracts import ImputedValue, SourceReference

from .primitives import Age, Diameter_cm, Position
from .tree_species import TreeName, parse_tree_species

#: Type of a :attr:`Tree.uid`. Callers may supply their own inventory keys, so an
#: identifier is whatever they use; the automatic ones are strings.
TreeUid = Union[int, str]

# Serial number behind the automatic ``uid``. Rendered with a ``"t"`` prefix so an
# auto-assigned identifier cannot collide with a caller's own integer keys, and so
# it reads as an identifier rather than a measurement in a repr.
_UID_COUNTER = count(1)


def _next_uid() -> str:
    """Return the next automatic tree identifier, e.g. ``"t42"``."""
    return f"t{next(_UID_COUNTER)}"


class Tree:
    """
    A spatially explicit single tree: (x, y, [z]) in a coordinate system + attributes.

    Attributes:
    -----------
    position : Position | tuple[float,float] | tuple[float,float,float] | None
        The location of the tree in some coordinate system.
    species : TreeName | str | None
        The species of the tree (or a string name to be parsed).
    age : Age | float | None
        The age of the tree. If an Age enum is used, it wraps the value in AgeMeasurement.
    diameter_cm : Diameter_cm | float | None
        The diameter (cm) if known. If a float is passed, it can be coerced to a Diameter_cm.
    height_m : float | None
        The *measured* height (m) of the tree if known. This is authoritative and
        is never overwritten by a modelled value.
    imputed : dict[str, ImputedValue]
        Modelled stand-ins for attributes that were never measured, keyed by
        attribute name. Plain attributes are measurements; a modelled value lives
        here with the imputer and citation that produced it. Read both together
        with :meth:`value_of`. Written by
        :meth:`~pyforestry.base.helpers.stand.Stand.impute`.
    weight_n : float
        Number of trees represented by Tree object. Defaults to 1.0.
    is_overstorey : bool | None
        Optional flag indicating overstorey status. If None, overstorey
        classification is left to downstream models.
    mortality : float | None
        Optional mortality fraction (0-1) applied to the tree record.
    crown_radius_m : float | None
        Optional horizontal crown (or influence-zone) radius in metres. Used by
        the influence-zone overlap competition indices; see
        :mod:`pyforestry.base.competition`. Left ``None`` unless measured or
        supplied by a crown model.
    uid : int | str
        Stable identifier for this record. Supply your own to carry an inventory's
        keys through; otherwise one is assigned automatically (``"t1"``, ``"t2"``,
        …), so every tree can always be tracked across a simulation step, a
        checkpoint or a serialisation round trip without falling back to
        :func:`id`, which means nothing outside one process. A copied tree keeps
        its uid: it is the same tree, in a later state.
    """

    def __init__(
        self,
        position: Optional[Union[Position, tuple, None]] = None,
        species: Optional[Union[TreeName, str]] = None,
        age: Optional[Union[Age, float]] = None,
        diameter_cm: Optional[Union[Diameter_cm, float]] = None,
        height_m: Optional[float] = None,
        weight_n: Optional[float] = 1.0,
        is_overstorey: Optional[bool] = None,
        mortality: Optional[float] = None,
        uid: Optional[Union[int, str]] = None,
        crown_radius_m: Optional[float] = None,
        imputed: Optional[Dict[str, ImputedValue]] = None,
    ):
        """Create a Tree instance with optional attributes.

        Parameters
        ----------
        position : Position | tuple | None, optional
            Tree location in a coordinate system.
        species : TreeName | str | None, optional
            Species identifier or name string.
        age : Age | float | None, optional
            Age value or ``Age`` enumeration.
        diameter_cm : Diameter_cm | float | None, optional
            Diameter at breast height in centimetres.
        height_m : float | None, optional
            Tree height in metres.
        weight_n : float
            Number of trees represented by Tree object. Defaults to 1.0.
        is_overstorey : bool | None, optional
            Optional flag indicating overstorey status.
        mortality : float | None, optional
            Optional mortality fraction (0-1) for this tree record.
        uid : int | str | None, optional
            Stable identifier for this record. Defaults to an automatically
            assigned ``"t<n>"``; pass your own to carry an inventory's keys
            through.
        imputed : dict[str, ImputedValue] | None, optional
            Pre-existing modelled values keyed by attribute name.
        crown_radius_m : float | None, optional
            Optional crown/influence-zone radius (m) for the influence-zone
            competition indices.
        """
        self.position = Position._set_position(position)

        # Convert string species → TreeSpecies if parseable
        if isinstance(species, str):
            self.species = parse_tree_species(species)
        else:
            self.species = species

        # `age` and `diameter_cm` are stored as given, and both stay that way on
        # purpose. This used to carry two shipped TODO comments suggesting they be
        # coerced to `AgeMeasurement` and `Diameter_cm`; neither is right.
        #
        # A bare age is ambiguous between total age and age at breast height, and
        # those differ by the years the tree took to reach 1.3 m -- which is why
        # `AgeMeasurement` exists. Coercing would pick one silently, and a wrong
        # guess propagates into every site-index and growth function that reads it.
        #
        # A bare diameter could be wrapped in `Diameter_cm` -- it is a float
        # subclass, so nothing numeric would change -- but its defaults assert
        # `over_bark=True` at `measurement_height_m=1.3`. That is the usual
        # convention, not a stated one, and a measurement convention this package
        # invented is worse than a plain number the caller supplied. Pass a real
        # `Diameter_cm` when the convention is known.
        #
        # What the TODOs were reaching for -- that a caller can rely on the value
        # -- is served by validating it instead.
        if diameter_cm is not None and float(diameter_cm) < 0.0:
            raise ValueError(f"diameter_cm must not be negative; got {diameter_cm!r}.")
        if height_m is not None and float(height_m) < 0.0:
            raise ValueError(f"height_m must not be negative; got {height_m!r}.")

        self.age = age
        self.diameter_cm = diameter_cm
        self.height_m = height_m
        self.imputed: Dict[str, ImputedValue] = dict(imputed) if imputed else {}
        self.uid: TreeUid = _next_uid() if uid is None else uid
        self.weight_n = weight_n
        self.is_overstorey = is_overstorey
        self.mortality = mortality
        self.crown_radius_m = crown_radius_m

    def value_of(self, attribute: str, prefer: str = "measured") -> Optional[float]:
        """Return a usable value for ``attribute``, measured or imputed.

        Plain attributes on a tree are measurements; modelled stand-ins live in
        :attr:`imputed`. This reads both, so callers do not have to.

        Parameters
        ----------
        attribute:
            Attribute name, e.g. ``"height_m"``. Need not be one the class
            declares -- ``"crown_base_height_m"`` resolves from :attr:`imputed`
            just as well.
        prefer:
            ``"measured"`` (default) returns the measurement, falling back to an
            imputed value; ``"imputed"`` reverses the order;
            ``"measured_only"`` / ``"imputed_only"`` return just that source
            (or ``None``).

        Returns
        -------
        float | None
            The value, or ``None`` if neither source has one.

        Raises
        ------
        ValueError
            If ``prefer`` is not one of the four accepted values.
        """
        measured = getattr(self, attribute, None)
        measured = None if measured is None else float(measured)
        entry = self.imputed.get(attribute)
        modelled = None if entry is None else float(entry.value)

        if prefer == "measured":
            return measured if measured is not None else modelled
        if prefer == "imputed":
            return modelled if modelled is not None else measured
        if prefer == "measured_only":
            return measured
        if prefer == "imputed_only":
            return modelled
        raise ValueError(f"Unknown prefer={prefer!r}")

    def provenance(self, attribute: str) -> Optional[str]:
        """Return ``"measured"``, ``"imputed"`` or ``None`` for ``attribute``.

        A measurement always takes precedence over a modelled value.
        """
        if getattr(self, attribute, None) is not None:
            return "measured"
        if attribute in self.imputed:
            return "imputed"
        return None

    def imputed_source(self, attribute: str) -> Optional[SourceReference]:
        """Return the citation behind an imputed ``attribute``, if it has one.

        Returns ``None`` when the attribute was measured or is absent. For a
        caller-supplied callable the reference is the ``"(none)"``/year-0
        sentinel rather than a publication.
        """
        entry = self.imputed.get(attribute)
        return None if entry is None else entry.source

    def set_imputed(self, attribute: str, value: float, imputer: Any) -> ImputedValue:
        """Record a modelled value for ``attribute``.

        Parameters
        ----------
        attribute:
            Attribute name the value stands in for.
        value:
            The modelled value, in the attribute's own units.
        imputer:
            The imputer that produced it; its ``component_id`` and ``source`` are
            stored alongside the value.

        Returns
        -------
        ImputedValue
            The stored entry.
        """
        entry = ImputedValue(
            attribute=attribute,
            value=float(value),
            imputer_id=str(imputer.component_id),
            source=imputer.source,
        )
        self.imputed[attribute] = entry
        return entry

    def __repr__(self):
        """Return ``repr(self)`` including main attribute values."""
        return (
            f"Tree(species={self.species!r}, age={self.age}, "
            f"diameter_cm={self.diameter_cm}, height_m={self.height_m}, "
            f"imputed={sorted(self.imputed)}, "
            f"position={self.position}, weight_n={self.weight_n}, "
            f"is_overstorey={self.is_overstorey}, mortality={self.mortality}, "
            f"uid={self.uid})"
        )
