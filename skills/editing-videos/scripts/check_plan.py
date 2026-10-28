"""Validate a cut list or an overlays plan before rendering — rendering is the expensive step,
so mistakes should be caught here, with messages that say exactly what to fix.

Usage:
    python check_plan.py work/cut_list.json
    python check_plan.py work/overlays.json --rough-cut previews/rough-cut-v1.mp4

Prints "OK" and exits 0 when the plan is valid; otherwise lists every problem and exits 1.
Warnings (printed with "warning:") do not fail the check.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_utils import probe_video, read_json, timecode  # noqa: E402

IMAGE_EXTENSIONS = {".png", ".webp", ".jpg", ".jpeg"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
# Clips shorter than this are usually accidental and produce a visible flash.
MIN_CLIP_SECONDS = 0.2


def check_cut_list(plan: dict, base: Path, errors: list[str], warnings: list[str]) -> None:
    clips = plan.get("clips")
    if not isinstance(clips, list) or not clips:
        errors.append('"clips" must be a non-empty list.')
        return
    durations: dict[str, float] = {}
    kept = 0
    for index, clip in enumerate(clips):
        label = f"clips[{index}] (id {clip.get('id', '?')})"
        for field in ("source", "start", "end"):
            if field not in clip:
                errors.append(f"{label}: missing \"{field}\".")
        if any(field not in clip for field in ("source", "start", "end")):
            continue
        source = base / clip["source"]
        if not source.exists():
            errors.append(f"{label}: source not found: {source}")
            continue
        if clip["source"] not in durations:
            durations[clip["source"]] = probe_video(source).duration
        if clip["start"] < 0 or clip["end"] <= clip["start"]:
            errors.append(f"{label}: end ({clip['end']}) must be after start ({clip['start']}) and start >= 0.")
        elif clip["end"] > durations[clip["source"]] + 0.05:
            errors.append(f"{label}: end {timecode(clip['end'])} is past the source's length "
                          f"{timecode(durations[clip['source']])}.")
        elif clip["end"] - clip["start"] < MIN_CLIP_SECONDS and clip.get("keep", True):
            warnings.append(f"{label}: only {clip['end'] - clip['start']:.2f} s long — intended?")
        kept += 1 if clip.get("keep", True) else 0
    if kept == 0:
        errors.append('No clip has "keep": true — the rough cut would be empty.')
    for source, transcript in plan.get("transcripts", {}).items():
        if not (base / transcript).exists():
            errors.append(f'transcripts["{source}"]: transcript not found: {base / transcript}')
    used_sources = {c.get("source") for c in clips if c.get("keep", True)}
    for source in used_sources - set(plan.get("transcripts", {})):
        warnings.append(f"{source} has no transcript entry, so its words get no captions.")


def check_overlays(plan: dict, base: Path, rough_cut: Path | None, errors: list[str], warnings: list[str]) -> None:
    canvas = plan.get("canvas")
    if not (isinstance(canvas, dict) and canvas.get("width") and canvas.get("height")):
        errors.append('"canvas" must be {"width": ..., "height": ...} (the resolution x/y/width refer to).')
        canvas = {"width": 1, "height": 1}
    duration = probe_video(rough_cut).duration if rough_cut else None
    if rough_cut:
        info = probe_video(rough_cut)
        if abs(info.width / info.height - canvas["width"] / canvas["height"]) > 0.01:
            warnings.append(f"canvas {canvas['width']}×{canvas['height']} has a different aspect ratio than the "
                            f"rough cut {info.width}×{info.height}; positions will be off.")

    for index, overlay in enumerate(plan.get("overlays", [])):
        label = f"overlays[{index}]"
        media_name = overlay.get("image") or overlay.get("video")
        if not media_name:
            errors.append(f'{label}: needs "image" or "video".')
            continue
        media = base / media_name
        if not media.exists():
            errors.append(f"{label}: file not found: {media}")
        elif media.suffix.lower() not in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS:
            errors.append(f"{label}: unsupported file type {media.suffix} (use PNG/WebP/JPG or MP4/MOV/MKV/WebM).")
        elif media.suffix.lower() in {".jpg", ".jpeg"} and not overlay.get("fullscreen"):
            warnings.append(f"{label}: JPEG has no transparency; use PNG for cards and graphics.")
        start, end = overlay.get("start"), overlay.get("end")
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or end <= start:
            errors.append(f'{label}: "start" and "end" must be numbers with end > start.')
            continue
        if duration is not None and end > duration + 0.05:
            errors.append(f"{label}: ends at {timecode(end)}, but the rough cut is only {timecode(duration)} long.")
        fades = float(overlay.get("fade_in", 0.15)) + float(overlay.get("fade_out", 0.15))
        if fades > end - start:
            errors.append(f"{label}: fade_in + fade_out ({fades:.2f} s) is longer than the overlay ({end - start:.2f} s).")
        if not overlay.get("fullscreen"):
            width = float(overlay.get("width", canvas["width"] * 0.8))
            x, y = overlay.get("x"), overlay.get("y")
            if isinstance(x, (int, float)) and (x < 0 or x + width > canvas["width"]):
                warnings.append(f"{label}: x={x} with width={width:g} reaches outside the {canvas['width']} px canvas.")
            if isinstance(y, (int, float)) and not 0 <= y < canvas["height"]:
                errors.append(f"{label}: y={y} is outside the {canvas['height']} px canvas.")
            for name, value in (("x", x), ("y", y)):
                if value is not None and value != "center" and not isinstance(value, (int, float)):
                    errors.append(f'{label}: "{name}" must be a number or "center", not {value!r}.')

    for index, sound in enumerate(plan.get("sounds", [])):
        if not (base / sound.get("file", "")).is_file():
            errors.append(f"sounds[{index}]: file not found: {base / sound.get('file', '')}")
        if duration is not None and float(sound.get("at", 0)) > duration:
            errors.append(f"sounds[{index}]: at {timecode(float(sound['at']))} is after the end of the rough cut.")
        if not 0 <= float(sound.get("volume", 0.8)) <= 2:
            warnings.append(f"sounds[{index}]: volume {sound.get('volume')} is unusual (1.0 = original level).")
    music = plan.get("music")
    if music:
        if not (base / music.get("file", "")).is_file():
            errors.append(f"music: file not found: {base / music.get('file', '')}")
        if float(music.get("volume", 0.12)) > 0.4:
            warnings.append(f"music: volume {music['volume']} may drown out speech (0.08–0.15 is typical).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate cut_list.json or overlays.json before rendering.")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--rough-cut", type=Path, help="rough cut video, to check overlay times against its length")
    args = parser.parse_args()

    plan = read_json(args.plan)
    base = args.plan.resolve().parent
    errors: list[str] = []
    warnings: list[str] = []
    if "clips" in plan:
        check_cut_list(plan, base, errors, warnings)
    elif "overlays" in plan or "canvas" in plan:
        check_overlays(plan, base, args.rough_cut, errors, warnings)
    else:
        sys.exit(f'{args.plan}: not a cut list ("clips") or overlays plan ("overlays"/"canvas").')

    for warning in warnings:
        print(f"warning: {warning}")
    if errors:
        print(f"{len(errors)} problem(s) in {args.plan}:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
