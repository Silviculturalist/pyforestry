"""Generate the documentation model-index page from ``pyforestry.catalog``.

Writes ``docs/source/model_index.rst`` as a table of every discoverable model
(component id, region, domain, citation). Run as part of the docs build so the
index stays current::

    python scripts/generate_model_index.py
"""

from __future__ import annotations

from pathlib import Path

from pyforestry import catalog

OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "source" / "model_index.rst"


def _render(models: list) -> str:
    """Render the discovered models as a reStructuredText list-table."""
    header = [
        "Model index",
        "===========",
        "",
        f"Auto-generated from ``pyforestry.catalog`` ({len(models)} models). "
        "Regenerate with ``python scripts/generate_model_index.py``.",
        "",
        ".. list-table::",
        "   :header-rows: 1",
        "   :widths: 24 8 8 10 42",
        "",
        "   * - Component id",
        "     - Kind",
        "     - Region",
        "     - Domain",
        "     - Source",
    ]
    rows: list[str] = []
    for entry in models:
        src = entry.source
        citation = f"{src.author} ({src.year}) {src.title}".strip() if src else ""
        if entry.composes:
            citation = f"{citation} (composes {', '.join(entry.composes)})".strip()
        rows += [
            f"   * - ``{entry.component_id}``",
            f"     - {entry.kind}",
            f"     - {entry.region}",
            f"     - {entry.domain}",
            f"     - {citation}",
        ]
    return "\n".join(header + rows) + "\n"


def main() -> None:
    """Write the model-index page and report the model count."""
    catalog.refresh()
    models = catalog.list_models()
    OUTPUT.write_text(_render(models), encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(models)} models)")


if __name__ == "__main__":
    main()
