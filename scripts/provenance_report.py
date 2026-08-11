"""Provenance report: auto-discover and list all Describable components.

Usage:
    python scripts/provenance_report.py [--format table|json|csv]

Auto-discovers:
- All DESCRIPTOR objects in equation packages (scans for modules with DESCRIPTOR attribute).
- All GrowthModel subclasses with Describable properties (scans adapters/ and systems/).
- All preset classes/factories with Describable properties (scans simulation/presets/).

Outputs a provenance table for audit, documentation, and catalog use.
"""

from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
import sys
from pathlib import Path
from typing import Any

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"

# ---------------------------------------------------------------------------
# Auto-discovery
# ---------------------------------------------------------------------------

# Region packages to scan
_REGIONS = ["pyforestry.sweden", "pyforestry.norway"]

# Domain packages where equations live (scanned for DESCRIPTOR)
_EQUATION_PACKAGES = [
    "growth",
    "mortality",
    "siteindex",
    "volume",
    "bark",
    "biomass",
    "height",
    "ingrowth",
    "regeneration",
]

# Packages where GrowthModel subclasses live: the runtime bindings in
# ``adapters/`` and, for a self-contained published system that ships its own
# binding, ``systems/``.
_MODEL_TIERS = ["adapters", "systems"]


def _scan_package_for_descriptors(package_name: str) -> list[str]:
    """Return module paths that have a DESCRIPTOR attribute within a package."""
    try:
        pkg = importlib.import_module(package_name)
    except ImportError:
        return []
    if not hasattr(pkg, "__path__"):
        return []
    results = []
    for _importer, modname, _ispkg in pkgutil.walk_packages(
        pkg.__path__, prefix=package_name + "."
    ):
        if modname.endswith(".__init__") or "._" in modname:
            continue
        try:
            mod = importlib.import_module(modname)
            if hasattr(mod, "DESCRIPTOR"):
                results.append(modname)
        except Exception:
            pass
    return results


def _extract_descriptor(module_path: str) -> dict[str, Any] | None:
    """Load a module and extract its DESCRIPTOR metadata."""
    try:
        mod = importlib.import_module(module_path)
        desc = getattr(mod, "DESCRIPTOR", None)
        if desc is None or not hasattr(desc, "component_id"):
            return None
        src = desc.source
        return {
            "type": "equation",
            "component_id": desc.component_id,
            "author": src.author,
            "year": src.year,
            "title": src.title,
            "appendix": getattr(src, "appendix", ""),
            "note": getattr(src, "note", ""),
            "module": module_path,
            "kernels": list(desc.kernel_names) if hasattr(desc, "kernel_names") else [],
            "components": [],
        }
    except Exception as e:
        print(f"  WARN: {module_path}: {e}", file=sys.stderr)
        return None


def _extract_block(cls: type, module_path: str) -> dict[str, Any] | None:
    """Extract Describable metadata from a GrowthModel subclass."""
    try:
        instance = cls.__new__(cls)
        if not hasattr(instance, "component_id") or not hasattr(instance, "source"):
            return None
        src = instance.source
        return {
            "type": "block",
            "component_id": instance.component_id,
            "author": src.author,
            "year": src.year,
            "title": src.title,
            "appendix": getattr(src, "appendix", ""),
            "note": getattr(src, "note", ""),
            "module": f"{module_path}.{cls.__name__}",
            "kernels": [],
            "components": [],
        }
    except Exception as e:
        print(f"  WARN: {module_path}.{cls.__name__}: {e}", file=sys.stderr)
        return None


def _extract_preset(instance: object, module_path: str) -> dict[str, Any] | None:
    """Extract Describable metadata from a preset instance."""
    if not hasattr(instance, "component_id") or not hasattr(instance, "source"):
        return None
    try:
        src = instance.source
        components = []
        for c in getattr(instance, "components", ()):
            if hasattr(c, "component_id") and hasattr(c, "source"):
                components.append(
                    {
                        "component_id": c.component_id,
                        "author": c.source.author,
                        "year": c.source.year,
                    }
                )
            else:
                components.append(
                    {
                        "component_id": type(c).__name__,
                        "author": "(not yet Describable)",
                        "year": 0,
                    }
                )
        return {
            "type": "preset",
            "component_id": instance.component_id,
            "author": src.author,
            "year": src.year,
            "title": src.title,
            "appendix": getattr(src, "appendix", ""),
            "note": getattr(src, "note", ""),
            "module": module_path,
            "kernels": [],
            "components": components,
        }
    except Exception as e:
        print(f"  WARN: preset {module_path}: {e}", file=sys.stderr)
        return None


def discover_all() -> list[dict[str, Any]]:
    """Auto-discover all equations, models, and presets across all regions."""
    entries: list[dict[str, Any]] = []

    # 1. Scan equation packages for DESCRIPTOR objects
    for region in _REGIONS:
        for pkg_name in _EQUATION_PACKAGES:
            full_pkg = f"{region}.{pkg_name}"
            for module_path in _scan_package_for_descriptors(full_pkg):
                entry = _extract_descriptor(module_path)
                if entry:
                    entries.append(entry)

    # 2. Scan adapters/ and systems/ for GrowthModel subclasses
    from pyforestry.base.simulation.growth_model import GrowthModel

    for region in _REGIONS:
        for tier in _MODEL_TIERS:
            model_pkg = f"{region}.{tier}"
            try:
                pkg = importlib.import_module(model_pkg)
            except ImportError:
                continue
            for _importer, modname, _ispkg in pkgutil.walk_packages(
                pkg.__path__, prefix=model_pkg + "."
            ):
                if "._" in modname:
                    continue
                try:
                    mod = importlib.import_module(modname)
                except Exception:
                    continue
                for _name, obj in inspect.getmembers(mod, inspect.isclass):
                    if (
                        issubclass(obj, GrowthModel)
                        and obj is not GrowthModel
                        and obj.__module__ == modname
                    ):
                        entry = _extract_block(obj, modname)
                        if entry:
                            entries.append(entry)

    # 3. Scan simulation/presets/ for preset classes
    for region in _REGIONS:
        presets_pkg = f"{region}.simulation.presets"
        try:
            pkg = importlib.import_module(presets_pkg)
        except ImportError:
            continue
        for _importer, modname, _ispkg in pkgutil.walk_packages(
            pkg.__path__, prefix=presets_pkg + "."
        ):
            if "._" in modname:
                continue
            try:
                mod = importlib.import_module(modname)
            except Exception:
                continue
            for cls_name, obj in inspect.getmembers(mod):
                if not inspect.isclass(obj) or obj.__module__ != modname:
                    continue
                if not hasattr(obj, "component_id"):
                    continue
                try:
                    instance = obj()
                except Exception:
                    continue
                entry = _extract_preset(instance, f"{modname}.{cls_name}")
                if entry:
                    entries.append(entry)

    # Deduplicate by component_id
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for e in entries:
        if e["component_id"] not in seen:
            seen.add(e["component_id"])
            unique.append(e)

    return unique


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def _format_table(entries: list[dict[str, Any]]) -> str:
    """Format as aligned text table."""
    lines = ["", "PYFORESTRY PROVENANCE REPORT", "=" * 80, ""]

    equations = [e for e in entries if e["type"] == "equation"]
    blocks = [e for e in entries if e["type"] == "block"]
    presets = [e for e in entries if e["type"] == "preset"]

    if equations:
        lines.append(f"Equations ({len(equations)} modules)")
        lines.append("-" * 80)
        lines.append(f"  {'Component ID':<35s} {'Author':<25s} {'Year'}")
        lines.append(f"  {'':35s} {'Title'}")
        lines.append("-" * 80)
        for e in sorted(equations, key=lambda x: x["component_id"]):
            lines.append(f"  {e['component_id']:<35s} {e['author']:<25s} {e['year']}")
            lines.append(f"  {'':35s} {e['title']}")
            if e["note"]:
                lines.append(f"  {'':35s} ({e['note']})")
            lines.append("")

    if blocks:
        lines.append(f"Blocks ({len(blocks)} models)")
        lines.append("-" * 80)
        lines.append(f"  {'Component ID':<35s} {'Author':<25s} {'Year'}")
        lines.append(f"  {'':35s} {'Title'}")
        lines.append("-" * 80)
        for e in sorted(blocks, key=lambda x: x["component_id"]):
            lines.append(f"  {e['component_id']:<35s} {e['author']:<25s} {e['year']}")
            if e["title"]:
                lines.append(f"  {'':35s} {e['title']}")
            lines.append("")

    if presets:
        lines.append(f"Presets ({len(presets)} pipelines)")
        lines.append("-" * 80)
        for e in sorted(presets, key=lambda x: x["component_id"]):
            lines.append(f"  {e['component_id']:<35s} {e['author']:<25s} {e['year']}")
            if e["title"]:
                lines.append(f"  {'':35s} {e['title']}")
            if e.get("note"):
                lines.append(f"  {'':35s} ({e['note']})")
            for c in e.get("components", []):
                lines.append(f"  {'':35s} └─ {c['component_id']}: {c['author']} ({c['year']})")
            lines.append("")

    lines.append("=" * 80)
    lines.append(
        f"Total: {len(equations)} equations, {len(blocks)} blocks, {len(presets)} presets"
    )
    lines.append("")
    return "\n".join(lines)


def _format_json(entries: list[dict[str, Any]]) -> str:
    """Format as JSON with component chains included."""
    return json.dumps(entries, indent=2, ensure_ascii=False)


def _format_csv(entries: list[dict[str, Any]]) -> str:
    """Format as CSV."""
    lines = ["type,component_id,author,year,title,module"]
    for e in entries:
        title = e["title"].replace(",", ";")
        lines.append(
            f"{e['type']},{e['component_id']},{e['author']},{e['year']},{title},{e['module']}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """Run provenance discovery and output report."""
    # Provenance text contains non-ASCII author names (e.g. Söderberg, Ståhl); avoid
    # crashing on legacy consoles (Windows cp1252) when writing the report.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

    fmt = "table"
    if "--format" in sys.argv:
        idx = sys.argv.index("--format")
        fmt = sys.argv[idx + 1]

    entries = discover_all()

    if fmt == "json":
        print(_format_json(entries))
    elif fmt == "csv":
        print(_format_csv(entries))
    else:
        print(_format_table(entries))

    return 0


if __name__ == "__main__":
    sys.exit(main())
