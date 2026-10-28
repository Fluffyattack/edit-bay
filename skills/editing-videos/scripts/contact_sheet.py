"""Make footage visible to Claude: a grid of frames, each labelled with its timecode.

Claude cannot play video but can read images. A contact sheet shows shots, locations, gestures,
screen recordings and reference videos at a glance.

Usage:
    python contact_sheet.py <video> <output-folder> [--every 5] [--columns 5] [--rows 6]

Writes contact-sheet-01.jpg, contact-sheet-02.jpg, … (columns × rows frames per sheet)
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_utils import probe_video, require_program, run_command  # noqa: E402

# Long videos get spread over at most this many sheets unless --every is given.
DEFAULT_MAX_SHEETS = 3


def main() -> None:
    parser = argparse.ArgumentParser(description="Contact sheet (frame grid with timecodes) from a video.")
    parser.add_argument("video", type=Path)
    parser.add_argument("output_folder", type=Path)
    parser.add_argument("--every", type=float, help="seconds between frames (default: fit into 3 sheets)")
    parser.add_argument("--columns", type=int, default=5)
    parser.add_argument("--rows", type=int, default=6)
    parser.add_argument("--frame-width", type=int, default=300, help="width of each thumbnail in pixels")
    args = parser.parse_args()
    require_program("ffmpeg")

    video = probe_video(args.video)
    per_sheet = args.columns * args.rows
    interval = args.every or max(1.0, math.ceil(video.duration / (per_sheet * DEFAULT_MAX_SHEETS)))
    args.output_folder.mkdir(parents=True, exist_ok=True)

    # select (not fps) keeps the original timestamps, so each label matches its frame exactly.
    pick = f"select='isnan(prev_selected_t)+gte(t-prev_selected_t,{interval - 0.001})'"
    label = ("drawtext=text='%{pts\\:hms}':fontsize=22:fontcolor=white:box=1:boxcolor=black@0.65:"
             "boxborderw=4:x=6:y=6")
    video_filter = (f"{pick},scale={args.frame_width}:-2,{label},"
                    f"tile={args.columns}x{args.rows}:padding=4:margin=4")
    run_command(["ffmpeg", "-y", "-v", "error", "-i", str(args.video.resolve()), "-vf", video_filter,
                 "-fps_mode", "passthrough", "-q:v", "4",
                 str(args.output_folder.resolve() / "contact-sheet-%02d.jpg")])
    count = len(list(args.output_folder.glob("contact-sheet-*.jpg")))
    print(f"{count} contact sheet(s), one frame every {interval:g} s → {args.output_folder}/")


if __name__ == "__main__":
    main()
