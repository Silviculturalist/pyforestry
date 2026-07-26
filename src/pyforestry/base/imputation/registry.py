"""Which imputers are available for which attribute.

Keeps the mapping from an attribute name to the imputers that can produce it, so
``stand.impute("height_m")`` finds one without the caller naming a class. New
imputers register themselves here; a caller can always bypass the registry by
passing an imputer instance or a plain callable.
"""

from typing import Any, Callable, Dict, List, Optional, Union

from .height import NaslundHeightImputer
from .imputer import CallableImputer, Imputer

__all__ = [
    "ImputerSpec",
    "available_attributes",
    "imputers_for",
    "register_imputer",
    "resolve_imputer",
]

#: What :func:`resolve_imputer` accepts: a registered name, an imputer instance,
#: or a bare callable ``f(tree) -> value | None``.
ImputerSpec = Union[str, Imputer, Callable[[Any], Optional[float]], None]

_REGISTRY: Dict[str, Dict[str, Callable[[], Imputer]]] = {}

# Names that are recognised but cannot impute, with the reason. These exist so a
# caller who reaches for a related-but-wrong concept gets an explanation instead
# of "unknown name" -- "measured" is a valid height *source* but cannot fill in a
# value that was never measured.
_REJECTED: Dict[str, Dict[str, str]] = {}


def register_imputer(
    attribute: str,
    name: str,
    factory: Callable[[], Imputer],
    *,
    default: bool = False,
    rejects: Optional[Dict[str, str]] = None,
) -> None:
    """Register an imputer factory under an attribute.

    Args:
        attribute: The attribute produced, e.g. ``"height_m"``.
        name: Short name callers pass to ``stand.impute``, e.g. ``"naslund"``.
        factory: Zero-argument callable returning a fresh imputer.
        default: Whether this becomes the attribute's default, used when the
            caller asks for the attribute without naming an imputer. The first
            imputer registered for an attribute becomes its default whether or
            not this is set, so a lone registration never leaves the attribute
            without one.
        rejects: Names that are recognised but invalid for imputation, mapped to
            the reason. Requesting one raises :class:`ValueError` with that
            reason rather than an unhelpful "unknown name".
    """
    slot = _REGISTRY.setdefault(attribute, {})
    slot[name] = factory
    if default or "__default__" not in slot:
        slot["__default__"] = factory
    if rejects:
        _REJECTED.setdefault(attribute, {}).update(rejects)


def imputers_for(attribute: str) -> List[str]:
    """Return the registered imputer names for ``attribute``."""
    return sorted(n for n in _REGISTRY.get(attribute, {}) if n != "__default__")


def available_attributes() -> List[str]:
    """Return every attribute with at least one registered imputer."""
    return sorted(_REGISTRY)


def resolve_imputer(attribute: str, spec: ImputerSpec = None) -> Imputer:
    """Turn a user-facing spec into an imputer.

    Args:
        attribute: The attribute to impute.
        spec: A registered name, an imputer instance, a bare callable, or
            ``None``/``"auto"`` for the attribute's default.

    Returns:
        An imputer for ``attribute``.

    Raises:
        KeyError: If no imputer is registered for the attribute, or the named one
            is unknown.
        ValueError: If an imputer instance produces a different attribute, or the
            name is recognised but cannot impute (e.g. ``"measured"``).
    """
    if spec is None or spec == "auto":
        slot = _REGISTRY.get(attribute)
        if not slot:
            raise KeyError(
                f"No imputer registered for {attribute!r}. Registered attributes: "
                f"{available_attributes()}. Pass an imputer or a callable instead."
            )
        return slot["__default__"]()

    if isinstance(spec, str):
        reason = _REJECTED.get(attribute, {}).get(spec)
        if reason is not None:
            raise ValueError(reason)
        slot = _REGISTRY.get(attribute, {})
        if spec not in slot:
            raise KeyError(
                f"Unknown imputer {spec!r} for {attribute!r}. "
                f"Registered: {imputers_for(attribute)}."
            )
        return slot[spec]()

    if hasattr(spec, "impute") and hasattr(spec, "attribute"):
        if spec.attribute != attribute:  # type: ignore[union-attr]
            raise ValueError(
                f"Imputer {spec!r} produces {spec.attribute!r}, not {attribute!r}."  # type: ignore[union-attr]
            )
        return spec  # type: ignore[return-value]

    if callable(spec):
        return CallableImputer(attribute=attribute, function=spec)

    raise ValueError(f"Cannot use {spec!r} as an imputer for {attribute!r}.")


# A Näslund curve fitted from the stand's own measured pairs is the default way
# to fill in a missing height; it is also the only imputer shipped, since no
# other attribute has a published model in this repository yet.
register_imputer(
    "height_m",
    "naslund",
    NaslundHeightImputer,
    default=True,
    rejects={
        name: (
            "Height imputation requires a curve height source (Näslund or a "
            f"callable), not measured heights; {name!r} reads heights that are "
            "already there and so cannot fill in one that is missing."
        )
        for name in ("measured", "measured+imputed")
    },
)
