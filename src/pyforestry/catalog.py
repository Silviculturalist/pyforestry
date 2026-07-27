"""Discover and search pyforestry's scientific formula models.

Most formula modules publish a module-level ``DESCRIPTOR`` (see
:class:`pyforestry.base.contracts.FormulaModuleDescriptor`) describing the
model's identity, citation, species applicability, and units. This module
aggregates those descriptors so a model can be found without already knowing its
import path::

    >>> from pyforestry import catalog
    >>> catalog.find(domain="volume")                 # all volume models
    >>> catalog.find(domain="growth", species="pinus")  # best-effort species filter
    >>> catalog.search("bark")                         # by id / module / citation
    >>> entry = catalog.describe("soderberg_1992_bark")
    >>> entry.source.title

Discovery covers ``pyforestry.base`` as well as the regions, so region-independent
models are findable too::

    >>> catalog.find(region="base")                    # Näslund, García, Bitterlich, Näsberg

Discovery currently covers modules that expose a ``DESCRIPTOR``; the set grows as
more modules adopt the convention.
"""

from __future__ import annotations

import importlib
import pkgutil
import warnings
from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Optional

from pyforestry.base.contracts import SourceReference

# Packages scanned for DESCRIPTOR-bearing formula modules. ``base`` is scanned
# alongside the regions because it holds region-independent science (Näslund's
# height curve, García's top-height estimator, Bitterlich angle-count sampling,
# Näsberg's bucking optimiser); those entries report ``region="base"``.
_MODEL_ROOTS = ("pyforestry.base", "pyforestry.sweden", "pyforestry.norway")

# Subpackage names that hold data, geometry, or runtime glue rather than
# scientific descriptors. Skipped to keep discovery fast and focused. ``adapters``
# and ``systems`` are intentionally *not* skipped: their model bindings publish
# ``kind="model"`` descriptors that the catalog surfaces alongside formulas.
# Neither are ``geo`` (Odin 1983, Eriksson 1986) or ``helpers`` (the base science
# listed above) — both carry published models, so both are scanned.
_SKIP_SEGMENTS = frozenset({"simulation", "pricelist", "timber", "site", "misc"})

#: The full :class:`~pyforestry.base.contracts.FormulaModuleDescriptor` contract.
#: This list is what discovery tests a candidate ``DESCRIPTOR`` against, so it and
#: the Protocol have to name the same members -- they did not, and the three the
#: Protocol omitted (``kind``, ``domain``, ``composes``) were the ones read below
#: with ``getattr`` defaults.
_DESCRIPTOR_ATTRS = (
    "component_id",
    "source",
    "species_groups",
    "units",
    "kernel_names",
    "kind",
    "domain",
    "composes",
)


@dataclass(frozen=True)
class ModelEntry:
    """A discoverable formula model and its introspection metadata."""

    component_id: str
    module: str
    region: str
    domain: str
    source: SourceReference
    species_groups: Mapping[str, frozenset[str]]
    units: Mapping[str, str]
    kernel_names: tuple[str, ...]
    kind: str = "formula"
    composes: tuple[str, ...] = ()

    @property
    def species(self) -> frozenset[str]:
        """Flattened set of species identifiers this model applies to."""
        names: set[str] = set()
        for group in self.species_groups.values():
            names.update(group)
        return frozenset(names)

    def __str__(self) -> str:
        """One-line human-readable summary."""
        cite = f"{self.source.author} {self.source.year}" if self.source else ""
        return f"{self.component_id}  [{self.kind}: {self.region}/{self.domain}]  {cite}".rstrip()


_CACHE: Optional[list[ModelEntry]] = None

#: Modules that could not be imported during the last discovery pass, as
#: ``{module_name: exception}``. Populated by :func:`_discover`; read it with
#: :func:`discovery_errors`.
_ERRORS: dict[str, BaseException] = {}


def _record_failure(module_name: str, exc: BaseException) -> None:
    """Remember an import failure and warn once, rather than losing the model.

    A model whose module raises on import used to disappear from
    :func:`list_models`, :func:`find` and :func:`search` with no diagnostic at
    all -- the failure mode was a model that "does not exist", which is
    indistinguishable from one that was never written and sends you looking in
    the wrong place. Discovery still continues past the failure, because one
    broken module should not hide the other eighty.
    """
    _ERRORS[module_name] = exc
    warnings.warn(
        f"pyforestry.catalog could not import {module_name!r}, so any model it "
        f"defines is missing from the catalog: {type(exc).__name__}: {exc}. "
        f"See pyforestry.catalog.discovery_errors().",
        stacklevel=2,
    )


def _iter_module_names(root_name: str) -> Iterator[str]:
    """Yield dotted names of candidate formula modules under ``root_name``."""
    try:
        root = importlib.import_module(root_name)
    except Exception as exc:
        _record_failure(root_name, exc)
        return
    stack = [root]
    while stack:
        pkg = stack.pop()
        if not hasattr(pkg, "__path__"):
            continue
        for info in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
            short = info.name.rsplit(".", 1)[-1]
            if short in _SKIP_SEGMENTS or short.startswith("_"):
                continue
            # Both leaf modules and package __init__ files may carry a DESCRIPTOR
            # (e.g. growth/elfving_2010/__init__.py), so yield every candidate.
            yield info.name
            if info.ispkg:
                try:
                    stack.append(importlib.import_module(info.name))
                except Exception as exc:
                    _record_failure(info.name, exc)
                    continue


def _looks_like_descriptor(obj: Any) -> bool:
    """Return ``True`` if ``obj`` satisfies the FormulaModuleDescriptor protocol."""
    return all(hasattr(obj, attr) for attr in _DESCRIPTOR_ATTRS)


def _entry_from_module(module_name: str) -> Optional[ModelEntry]:
    """Build a :class:`ModelEntry` from a module's ``DESCRIPTOR``, or ``None``."""
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        _record_failure(module_name, exc)
        return None
    descriptor = getattr(module, "DESCRIPTOR", None)
    if descriptor is None or not _looks_like_descriptor(descriptor):
        return None
    parts = module_name.split(".")
    region = parts[1] if len(parts) > 1 else ""
    path_domain = parts[2] if len(parts) > 2 else ""
    return ModelEntry(
        component_id=str(descriptor.component_id),
        module=module_name,
        region=region,
        # A "model" descriptor lives under adapters/ or systems/ but may declare
        # its scientific domain (e.g. "growth"); fall back to the path segment.
        domain=str(descriptor.domain or path_domain),
        source=descriptor.source,
        species_groups={k: frozenset(v) for k, v in dict(descriptor.species_groups).items()},
        units=dict(descriptor.units),
        kernel_names=tuple(descriptor.kernel_names),
        kind=str(descriptor.kind),
        composes=tuple(descriptor.composes or ()),
    )


def _discover() -> list[ModelEntry]:
    """Discover all ``DESCRIPTOR``-bearing models (result is cached)."""
    global _CACHE
    if _CACHE is None:
        _ERRORS.clear()
        entries: dict[str, ModelEntry] = {}
        for root in _MODEL_ROOTS:
            for name in _iter_module_names(root):
                entry = _entry_from_module(name)
                if entry is not None:
                    entries[entry.component_id] = entry
        _CACHE = sorted(entries.values(), key=lambda e: (e.region, e.domain, e.component_id))
    return _CACHE


def refresh() -> None:
    """Clear the discovery cache (e.g. after importing new model modules)."""
    global _CACHE
    _CACHE = None
    _ERRORS.clear()


def discovery_errors() -> dict[str, BaseException]:
    """Return the modules the last discovery pass could not import.

    Empty when everything imported. A non-empty result means the catalog is
    incomplete and says exactly which modules are missing and why -- which is
    what "this model does not exist" used to look like.
    """
    _discover()
    return dict(_ERRORS)


def list_models() -> list[ModelEntry]:
    """Return every discoverable model entry."""
    return list(_discover())


def domains() -> list[str]:
    """Return the sorted set of model domains (e.g. ``volume``, ``mortality``)."""
    return sorted({e.domain for e in _discover() if e.domain})


def regions() -> list[str]:
    """Return the sorted set of regions that publish discoverable models."""
    return sorted({e.region for e in _discover() if e.region})


def _matches_species(entry: ModelEntry, query: str) -> bool:
    """Return ``True`` if ``query`` appears in any species identifier."""
    q = query.lower()
    return any(q in s.lower() for s in entry.species)


def _matches_units(entry: ModelEntry, query: str) -> bool:
    """Return ``True`` if ``query`` appears in the model's unit names or values."""
    q = query.lower()
    return any(q in k.lower() or q in str(v).lower() for k, v in entry.units.items())


def find(
    *,
    region: Optional[str] = None,
    domain: Optional[str] = None,
    species: Optional[str] = None,
    units: Optional[str] = None,
    kind: Optional[str] = None,
) -> list[ModelEntry]:
    """Return models matching every supplied filter (case-insensitive).

    Args:
        region: Region name, e.g. ``"sweden"``.
        domain: Domain name, e.g. ``"volume"``. Returns both formula kernels and
            composed models for that domain unless ``kind`` is also given.
        species: Substring matched against each model's species identifiers.
            Best-effort, since identifiers are stored as ``TreeName`` strings.
        units: Substring matched against the model's unit names or values.
        kind: ``"formula"`` (equation kernels) or ``"model"`` (composed,
            runnable model adapters).

    Returns:
        Matching :class:`ModelEntry` objects, ordered by region/domain/id.
    """
    results: list[ModelEntry] = []
    for entry in _discover():
        if region and entry.region != region.lower():
            continue
        if domain and entry.domain != domain.lower():
            continue
        if kind and entry.kind != kind.lower():
            continue
        if species and not _matches_species(entry, species):
            continue
        if units and not _matches_units(entry, units):
            continue
        results.append(entry)
    return results


def search(query: str) -> list[ModelEntry]:
    """Return models whose id, module, domain, or citation contains ``query``."""
    q = query.lower()
    out: list[ModelEntry] = []
    for entry in _discover():
        src = entry.source
        fields = [entry.component_id, entry.module, entry.domain]
        if src:
            fields += [src.author, str(src.year), src.title]
        if q in " ".join(fields).lower():
            out.append(entry)
    return out


def describe(identifier: str) -> ModelEntry:
    """Return the model matching ``identifier`` (component id or module path).

    Falls back to a unique case-insensitive substring match on the component id.

    Raises:
        KeyError: if no model, or more than one, matches ``identifier``.
    """
    for entry in _discover():
        if identifier in (entry.component_id, entry.module):
            return entry
    matches = [e for e in _discover() if identifier.lower() in e.component_id.lower()]
    if len(matches) == 1:
        return matches[0]
    raise KeyError(f"No unique model matches {identifier!r} ({len(matches)} candidates).")


__all__ = [
    "ModelEntry",
    "discovery_errors",
    "find",
    "search",
    "describe",
    "list_models",
    "domains",
    "regions",
    "refresh",
]
