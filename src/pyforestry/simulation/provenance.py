"""Collecting the citations behind a run.

One traversal, used by :func:`pyforestry.project` and by the scenario runner, so
a run manifest and a ``ProjectionResult`` report the same papers for the same
models. The scenario runbook used to walk ``components`` itself with a second,
laxer copy that fell back to ``{"class": type(c).__name__}`` for anything that
did not describe itself -- a class name in a provenance record, where a citation
should be.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from pyforestry.base.contracts import SourceReference

__all__ = ["as_manifest_entries", "as_manifest_source", "collect_provenance"]


def as_manifest_source(source: Optional[SourceReference]) -> Optional[dict[str, Any]]:
    """Render one citation as a manifest record, or ``None`` for no citation.

    The single spelling of a citation in a run manifest. There were two -- this
    module's, and a private one in :mod:`pyforestry.simulation.forcing` -- and a
    third was about to be written for the discount rate. Several conventions for
    one value is no convention.
    """
    if source is None:
        return None
    return {
        "author": source.author,
        "year": source.year,
        "title": source.title,
        "note": source.note,
    }


def collect_provenance(component: Any) -> Dict[str, SourceReference]:
    """Return every citation ``component`` and its components carry, by id.

    ``components`` is ``Sequence[Describable]``: each entry declares its own
    ``component_id`` and ``source``, and each is descended into, so a composition
    of compositions reports the papers at the bottom.

    Raises:
        TypeError: If an entry of ``components`` does not describe itself.
            Skipping them is how seven mortality citations once went missing
            without a word.
    """
    found: Dict[str, SourceReference] = {}
    _collect(component, found, seen=set())
    return found


def _collect(component: Any, into: Dict[str, SourceReference], seen: set[int]) -> None:
    """Add ``component``'s citation to ``into``, then recurse into what it composes."""
    if id(component) in seen:
        return
    seen.add(id(component))

    component_id = getattr(component, "component_id", None)
    source = getattr(component, "source", None)
    if component_id is not None and source is not None:
        into[str(component_id)] = source

    for child in getattr(component, "components", ()) or ():
        if getattr(child, "component_id", None) is None or getattr(child, "source", None) is None:
            raise TypeError(
                f"{type(component).__name__}.components must yield Describable objects "
                f"(each with component_id and source), but one entry is "
                f"{child!r}. Returning ids alone loses the citations they stand for."
            )
        _collect(child, into, seen)


def as_manifest_entries(provenance: Mapping[str, SourceReference]) -> list[dict[str, Any]]:
    """Render collected citations as JSON-serialisable manifest entries."""
    return [
        {"component_id": component_id, **(as_manifest_source(source) or {})}
        for component_id, source in sorted(provenance.items())
    ]
