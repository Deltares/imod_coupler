"""
Extract the release notes for a given version tag from CHANGELOG.md.

Prints the notes to stdout so they can be captured by a calling script.

Usage:
    python scripts/extract_changelog_notes.py <version>

Example:
    python scripts/extract_changelog_notes.py v1.2.0
"""

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).parent.parent / "CHANGELOG.md"


def extract_notes(text: str, version: str) -> str:
    escaped = re.escape(version)
    pattern = re.compile(
        rf"## \[{escaped}\][^\n]*\n(.*?)(?=\n## |\Z)", re.DOTALL
    )
    match = pattern.search(text)
    if not match:
        raise SystemExit(
            f"Could not find a section for [{version}] in CHANGELOG.md"
        )
    notes = match.group(1).strip()
    if not notes:
        raise SystemExit(f"The [{version}] section in CHANGELOG.md is empty")
    return notes


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: python {sys.argv[0]} <version>  (e.g. v1.2.0)")

    version = sys.argv[1]
    text = CHANGELOG.read_text(encoding="utf-8")
    print(extract_notes(text, version))


if __name__ == "__main__":
    main()
