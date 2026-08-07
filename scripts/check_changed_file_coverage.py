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
            # When the package is installed normally, coverage records
            # files inside ``site-packages``. Map those paths back to the
            # ``src/`` layout used in this repository so that filenames
            # match ``git`` paths and coverage can be checked correctly.
            if not path.startswith("src/"):
                if "pyforestry" in path:
                    _, tail = path.split("pyforestry", 1)
                    path = f"src/pyforestry{tail}"
            try:
                rates[path] = float(elem.get("line-rate", "0"))
            except ValueError:
                rates[path] = 0.0
    return rates


def docstring_coverage_rates(paths: list[str]) -> dict[str, float]:
    """Return docstring coverage percentage for every path in ``paths``.

    One pass over all of them, through ``docstr_coverage``'s Python API. This
    used to shell out to ``docstr-coverage -p <path>`` once per file, which on a
    branch touching two hundred files meant two hundred interpreter startups to
    answer a question the library answers for the whole set at once -- and it was
    the reason this step dominated the CI job's runtime.

    Keys are resolved absolute paths, so a caller comparing against them does not
    have to guess whether the analyser echoed back the relative path it was given.

    Args:
        paths: Python files to measure.

    Returns:
        Resolved path to docstring coverage percentage. A file with nothing that
        needs a docstring counts as fully covered rather than as a division by
        zero.
    """
    if not paths:
        return {}

    from docstr_coverage import analyze

    results = analyze(paths)
    rates: dict[str, float] = {}
    for path, file_count in results.files():
        count = file_count.count_aggregate()
        rates[str(Path(path).resolve())] = 100.0 if count.needed == 0 else count.coverage()
    return rates


def main() -> int:
    base_ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1"
    files = list_changed_files(base_ref)
    if not files:
        print("No Python files changed")
        return 0

    rates = load_coverage_rates("coverage.xml")
    doc_rates = docstring_coverage_rates(files)

    failed = False
    for path in files:
        test_cov = rates.get(path, 0.0) * 100
        # Missing from the analyser's results means "not measured", which is
        # reported as a failure rather than passed over: a file the gate cannot
        # score is the one case where staying quiet would be worst.
        doc_cov = doc_rates.get(str(Path(path).resolve()), 0.0)
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
