"""End-to-end smoke test for the editing-videos scripts.

Builds synthetic footage (test pattern + tone) with a hand-written transcript, so no speech model
is needed, then runs the whole pipeline: edit bay → cut list → plan check → rough cut → captions →
stills → test clip → preview → contact sheet → final export.

Usage:
    python tests/smoke_test.py [--keep]     (--keep leaves the temporary folder for inspection)

Requires Python 3.10+ and ffmpeg with libass and libx264.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):      # don't crash on consoles without UTF-8
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(errors="replace")

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "editing-videos" / "scripts"
PYTHON = sys.executable

# Fixture: (start, end, word). A retake ("This desk took me" twice), a filler ("um") and pauses.
FIXTURE_WORDS = [
    (0.50, 0.70, "This"), (0.72, 0.95, "desk"), (0.97, 1.20, "took"), (1.22, 1.40, "me"),
    (2.60, 2.80, "This"), (2.82, 3.05, "desk"), (3.07, 3.30, "took"), (3.32, 3.50, "me"),
    (3.52, 3.80, "three"), (3.82, 4.10, "years."),
    (5.20, 5.40, "um"),
    (6.10, 6.40, "Here's"), (6.42, 6.60, "what"), (6.62, 7.00, "changed."),
]
FOOTAGE_SECONDS = 8.0


def run(*command: str, expect_failure: bool = False) -> str:
    environment = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run([PYTHON, *command], capture_output=True, text=True, encoding="utf-8",
                            errors="replace", env=environment)
    failed = result.returncode != 0
    if failed != expect_failure:
        print(result.stdout, result.stderr)
        raise SystemExit(f"FAIL: {' '.join(command)} (exit {result.returncode})")
    return result.stdout


def ffmpeg(*arguments: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *arguments], check=True)


def duration_of(path: Path) -> float:
    output = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                             str(path)], capture_output=True, text=True, check=True).stdout
    return float(output.strip())


def check(condition: bool, message: str) -> None:
    print(("PASS " if condition else "FAIL ") + message)
    if not condition:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    for program in ("ffmpeg", "ffprobe"):
        if shutil.which(program) is None:
            raise SystemExit(f"{program} not found on PATH")

    root = Path(tempfile.mkdtemp(prefix="editing-videos-smoke-"))
    try:
        bay = root / "bay"
        run(str(SCRIPTS / "create_edit_bay.py"), str(bay))
        run(str(SCRIPTS / "new_project.py"), str(bay), "Smoke test", "--date", "2026-01-01")
        project = bay / "projects" / "2026-01-01-smoke-test"
        check((bay / "LEARNINGS.md").exists() and (project / "brief.md").exists(), "edit bay and project created")

        footage = project / "footage" / "take1.mp4"
        ffmpeg("-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=30", "-f", "lavfi", "-i", "sine=frequency=330",
               "-t", str(FOOTAGE_SECONDS), "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", str(footage))
        transcript = project / "work" / "transcript-take1.json"
        transcript.write_text(json.dumps({
            "source": str(footage), "duration": FOOTAGE_SECONDS, "language": "en", "model": "fixture",
            "segments": [{"start": FIXTURE_WORDS[0][0], "end": FIXTURE_WORDS[-1][1], "text": "",
                          "words": [{"start": s, "end": e, "word": w, "confidence": 1.0} for s, e, w in FIXTURE_WORDS]}],
        }), encoding="utf-8")

        cut_list = project / "work" / "cut_list.json"
        run(str(SCRIPTS / "suggest_cuts.py"), str(transcript), "--output", str(cut_list), "--max-pause", "0.4")
        plan = json.loads(cut_list.read_text(encoding="utf-8"))
        texts = [c["text"] for c in plan["clips"]]
        check(not any("um" == t.split()[0] for t in texts), "filler word removed")
        check("note" in plan["clips"][0] and "retake" in plan["clips"][0]["note"].lower(), "retake flagged")
        plan["clips"][0]["keep"] = False
        cut_list.write_text(json.dumps(plan), encoding="utf-8")
        check(run(str(SCRIPTS / "check_plan.py"), str(cut_list)).strip().endswith("OK"), "cut list validates")

        rough = project / "previews" / "rough-cut-v1.mp4"
        run(str(SCRIPTS / "render_rough_cut.py"), str(cut_list), str(rough))
        kept = sum(c["end"] - c["start"] for c in plan["clips"] if c["keep"])
        check(abs(duration_of(rough) - kept) < 0.1, f"rough cut length {duration_of(rough):.2f} s ~ kept {kept:.2f} s")
        words = json.loads(rough.with_suffix(".words.json").read_text(encoding="utf-8"))
        check(len(words["words"]) == 9 and words["width"] == 720, "words re-timed (6 + 3 kept words) at 720 px preview width")

        captions = project / "work" / "captions.ass"
        run(str(SCRIPTS / "make_captions.py"), str(rough.with_suffix(".words.json")), str(captions))
        check(captions.read_text(encoding="utf-8").count("Dialogue:") == 9, "one caption event per word")

        card = project / "graphics" / "card.png"
        ffmpeg("-f", "lavfi", "-i", "color=c=white@0.9:s=800x240,format=rgba", "-frames:v", "1", str(card))
        overlays = project / "work" / "overlays.json"
        overlays.write_text(json.dumps({"canvas": {"width": 1080, "height": 1920},
                                        "overlays": [{"image": "../graphics/card.png", "start": 0.8, "end": 2.4,
                                                      "x": "center", "y": 260, "width": 800}],
                                        "sounds": [], "music": None}), encoding="utf-8")
        check(run(str(SCRIPTS / "check_plan.py"), str(overlays), "--rough-cut", str(rough)).strip().endswith("OK"),
              "overlays plan validates")
        broken = project / "work" / "overlays-broken.json"
        broken.write_text(json.dumps({"canvas": {"width": 1080, "height": 1920},
                                      "overlays": [{"image": "../graphics/missing.png", "start": 2, "end": 99}]}),
                          encoding="utf-8")
        run(str(SCRIPTS / "check_plan.py"), str(broken), "--rough-cut", str(rough), expect_failure=True)
        check(True, "broken overlays plan is rejected")

        common = ["--captions", str(captions), "--overlays", str(overlays)]
        stills = project / "previews" / "stills-v1"
        run(str(SCRIPTS / "render.py"), str(rough), str(stills), *common, "--stills", "0.5,2.0")
        check(len(list(stills.glob("still-*.png"))) == 2, "two stills rendered")
        test_clip = project / "previews" / "test-v1.mp4"
        run(str(SCRIPTS / "render.py"), str(rough), str(test_clip), *common, "--from", "0.5", "--to", "2.5")
        check(abs(duration_of(test_clip) - 2.0) < 0.15, "test clip is 2 s long")
        preview = project / "previews" / "preview-v1.mp4"
        run(str(SCRIPTS / "render.py"), str(rough), str(preview), *common)
        check(abs(duration_of(preview) - duration_of(rough)) < 0.1, "preview matches rough cut length")
        run(str(SCRIPTS / "contact_sheet.py"), str(preview), str(project / "work" / "sheets"), "--every", "1")
        check(any((project / "work" / "sheets").glob("contact-sheet-*.jpg")), "contact sheet rendered")

        full = project / "work" / "rough-cut-full.mp4"
        run(str(SCRIPTS / "render_rough_cut.py"), str(cut_list), str(full), "--full-resolution")
        final = project / "final" / "smoke-test.mp4"
        run(str(SCRIPTS / "render.py"), str(full), str(final), *common, "--final", "--normalize-loudness")
        size = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                               "stream=width,height", "-of", "csv=p=0", str(final)],
                              capture_output=True, text=True, check=True).stdout.strip()
        check(size == "1080,1920", f"final export at full resolution ({size})")
        print("\nAll checks passed.")
    finally:
        if args.keep:
            print(f"Kept: {root}")
        else:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
