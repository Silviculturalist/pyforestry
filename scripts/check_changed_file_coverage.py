"""Check test and docstring coverage for changed Python files.

This script compares the current branch against a base reference to
determine which ``.py`` files under ``src/`` have been added or modified.
Both test coverage (from ``coverage.xml``) and docstring coverage
(via ``docstr-coverage``) must be at least 90% for each changed file.

Usage::

    python scripts/check_changed_file_coverage.py <base-ref>

The ``base-ref`` should typically be ``$(git merge-base HEAD origin/dev)``
when running in CI.
"""

from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def list_changed_files(base_ref: str) -> list[str]:
    """Return added or modified ``.py`` files under ``src/`` since ``base_ref``."""
    result = subprocess.run(
        ["git", "diff", "--diff-filter=AM", "--name-only", base_ref],
        capture_output=True,
        text=True,
        check=True,
    )
    changed: list[str] = []
    for raw in result.stdout.splitlines():
        path = Path(raw).as_posix()
        if path.startswith("src/") and path.endswith(".py"):
            changed.append(path)
    return changed


def load_coverage_rates(xml_path: str) -> dict[str, float]:
    """Map source file paths to line coverage rates from ``coverage.xml``."""
    tree = ET.parse(xml_path)
    rates: dict[str, float] = {}
    for elem in tree.findall(".//class"):
        filename = elem.get("filename")
        if filename:
            path = Path(filename).as_posix()
            try:
                rates[path] = float(elem.get("line-rate", "0"))
            except ValueError:
                rates[path] = 0.0
    return rates


def docstring_coverage(path: str) -> float:
    """Return docstring coverage percentage for ``path``."""
    result = subprocess.run(["docstr-coverage", "-p", path], capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def main() -> int:
    base_ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1"
    files = list_changed_files(base_ref)
    if not files:
        print("No Python files changed")
        return 0

    rates = load_coverage_rates("coverage.xml")

    failed = False
    for path in files:
        test_cov = rates.get(path, 0.0) * 100
        doc_cov = docstring_coverage(path)
        if test_cov < 90 or doc_cov < 90:
            print(f"{path}: tests {test_cov:.1f}% docs {doc_cov:.1f}% (<90%)")
            failed = True

    if failed:
        print("Changed files must have at least 90% test and docstring coverage")
        return 1

    print("All changed files meet coverage requirements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
