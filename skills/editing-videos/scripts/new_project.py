"""Create a project folder inside the edit bay for one new video.

Usage:
    python new_project.py <edit-bay-folder> "Morning routine reel" [--date 2026-01-31]

Creates projects/2026-01-31-morning-routine-reel/ with brief.md, storyboard.md, notes.md,
work/overlays.json and the folders footage/, work/, graphics/, previews/, final/.
"""

from __future__ import annotations

import argparse
import datetime
import re
import shutil
import unicodedata
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "project"
FOLDERS = ["footage", "work", "graphics", "previews", "final"]


def slugify(title: str) -> str:
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")[:60] or "project"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a project folder for one video.")
    parser.add_argument("edit_bay", type=Path)
    parser.add_argument("title")
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    args = parser.parse_args()

    project = args.edit_bay.expanduser().resolve() / "projects" / f"{args.date}-{slugify(args.title)}"
    if project.exists():
        print(f"Already exists, nothing changed: {project}")
        return
    for name in FOLDERS:
        (project / name).mkdir(parents=True)
    for template in TEMPLATE.glob("*.md"):
        text = template.read_text(encoding="utf-8").replace("{{TITLE}}", args.title).replace("{{DATE}}", args.date)
        (project / template.name).write_text(text, encoding="utf-8")
    shutil.copy2(TEMPLATE / "overlays.json", project / "work" / "overlays.json")
    print(f"New project: {project}")


if __name__ == "__main__":
    main()
