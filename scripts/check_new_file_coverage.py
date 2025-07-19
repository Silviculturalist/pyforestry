import subprocess
import sys
import xml.etree.ElementTree as ET


def list_new_files(base_ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--diff-filter=A", "--name-only", base_ref],
        capture_output=True,
        text=True,
        check=True,
    )
    return [f for f in result.stdout.splitlines() if f.startswith("src/") and f.endswith(".py")]


def load_coverage_rates(xml_path: str) -> dict[str, float]:
    tree = ET.parse(xml_path)
    rates = {}
    for elem in tree.findall(".//class"):
        filename = elem.get("filename")
        if filename:
            try:
                rates[filename] = float(elem.get("line-rate", "0"))
            except ValueError:
                rates[filename] = 0.0
    return rates


def docstring_coverage(file: str) -> float:
    result = subprocess.run(["docstr-coverage", "-p", file], capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def main() -> int:
    base_ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1"
    new_files = list_new_files(base_ref)
    if not new_files:
        print("No new Python files to check")
        return 0

    rates = load_coverage_rates("coverage.xml")

    failed = False
    for path in new_files:
        test_cov = rates.get(path, 0.0) * 100
        doc_cov = docstring_coverage(path)
        if test_cov < 90 or doc_cov < 90:
            print(f"{path}: tests {test_cov:.1f}% docs {doc_cov:.1f}% (<90%)")
            failed = True

    if failed:
        print("New files must have at least 90% test and docstring coverage")
        return 1
    print("All new files meet coverage requirements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
