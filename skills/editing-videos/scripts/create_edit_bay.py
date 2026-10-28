"""Create an edit bay: the one folder every video project starts in.

Existing files are never overwritten, so running this on an existing edit bay safely adds
whatever is missing.

Usage:
    python create_edit_bay.py <folder>
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "edit-bay"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or complete an edit bay from the template.")
    parser.add_argument("folder", type=Path)
    target = parser.parse_args().folder.expanduser().resolve()

    created, kept = [], []
    for source in sorted(TEMPLATE.rglob("*")):
        relative = source.relative_to(TEMPLATE)
        destination = target / relative
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif destination.exists():
            kept.append(relative)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            created.append(relative)

    print(f"Edit bay: {target}")
    for path in created:
        print(f"  created:   {path}")
    for path in kept:
        print(f"  unchanged: {path}")


if __name__ == "__main__":
    main()
