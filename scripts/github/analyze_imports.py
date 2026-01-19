#!/usr/bin/env python3
"""
Analyze import patterns in the scripts folder.
Shows which files use sys.path manipulation and their import dependencies.
"""

import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict


def analyze_imports(project_root: Path) -> Dict[str, Any]:  # noqa: C901
    """Analyze import patterns in Python files."""

    scripts_dir = project_root / "scripts"
    tests_dir = project_root / "tests"

    results: Dict[str, Any] = {
        "sys_path_files": [],
        "import_patterns": defaultdict(list),
        "total_files": 0,
        "total_lines": 0,
    }

    # Patterns to detect
    sys_path_pattern = re.compile(r"sys\.path\.insert")
    import_pattern = re.compile(r"^\s*(?:from|import)\s+(\S+)", re.MULTILINE)

    # Analyze scripts directory
    for py_file in scripts_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        results["total_files"] += 1

        try:
            content = py_file.read_text()
            line_count = len(content.splitlines())
            results["total_lines"] += line_count

            rel_path = py_file.relative_to(project_root)

            # Check for sys.path manipulation
            if sys_path_pattern.search(content):
                results["sys_path_files"].append(str(rel_path))

            # Extract imports
            imports = import_pattern.findall(content)
            for imp in imports:
                if imp.startswith("scripts"):
                    results["import_patterns"][str(rel_path)].append(imp)

        except Exception as e:
            print(f"Error reading {py_file}: {e}")

    # Analyze tests directory
    for py_file in tests_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text()
            rel_path = py_file.relative_to(project_root)

            # Check for sys.path manipulation in tests
            if sys_path_pattern.search(content):
                results["sys_path_files"].append(str(rel_path))

        except Exception as e:
            print(f"Error reading {py_file}: {e}")

    return results


def print_report(results: Dict[str, Any]) -> None:
    """Print analysis report."""

    print("=" * 80)
    print("PYTHON IMPORT ANALYSIS REPORT")
    print("=" * 80)
    print()

    print("📊 Statistics:")
    print(f"   Total Python files analyzed: {results['total_files']}")
    print(f"   Total lines of code: {results['total_lines']:,}")
    print(f"   Files using sys.path.insert: {len(results['sys_path_files'])}")
    print()

    print("=" * 80)
    print("⚠️  FILES USING sys.path.insert()")
    print("=" * 80)
    print()

    if results["sys_path_files"]:
        for i, file_path in enumerate(sorted(results["sys_path_files"]), 1):
            print(f"{i:2d}. {file_path}")
    else:
        print("✅ No files using sys.path.insert() - Good!")

    print()
    print("=" * 80)
    print("🔗 IMPORT DEPENDENCIES (scripts.* imports)")
    print("=" * 80)
    print()

    if results["import_patterns"]:
        for file_path, imports in sorted(results["import_patterns"].items()):
            print(f"📄 {file_path}")
            unique_imports = sorted(set(imports))
            for imp in unique_imports:
                print(f"   └─ {imp}")
            print()
    else:
        print("No scripts.* imports found")

    print("=" * 80)
    print("💡 RECOMMENDATIONS")
    print("=" * 80)
    print()
    print("1. Remove all sys.path.insert() statements")
    print("2. Convert scripts/ to proper package: src/photo_organizer/")
    print("3. Update imports: scripts.X → photo_organizer.X")
    print("4. Add project metadata to pyproject.toml")
    print("5. Install as editable package: pip install -e .")
    print()
    print("See docs/planning/PYTHON_APPLICATION_SETUP_PROPOSAL.md for details")
    print()


def main() -> None:
    """Main entry point."""
    # Get the actual project root (2 levels up from scripts/github/)
    project_root = Path(__file__).parent.parent.parent

    print(f"Analyzing project: {project_root}")
    print()

    results = analyze_imports(project_root)
    print_report(results)


if __name__ == "__main__":
    main()
