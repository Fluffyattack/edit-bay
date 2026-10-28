"""Rough cut, step 2: turn the cut list into a video.

Every kept clip is cut frame-accurately, gets a tiny audio fade (prevents clicks at the joins)
and is appended in list order. Alongside the video, a words file is written with every word
re-timed to the new timeline — captions are generated from it.

Usage:
    python render_rough_cut.py <cut_list.json> <output.mp4> [--short-side 720] [--full-resolution]

    --short-side 720     (default) fast review copy; the shorter side of the frame is 720 px
    --full-resolution    source resolution, for the final export

Writes:
    output.mp4           the rough cut
    output.words.json    words on the rough-cut timeline + mapping between rough cut and source
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_utils import (VideoInfo, probe_video, read_json, require_program, run_command,  # noqa: E402
                         size_for_short_side, timecode, write_json)

# 12 ms is long enough to remove the click of a hard audio cut and too short to hear as a fade.
AUDIO_FADE_SECONDS = 0.012
# Words may end slightly after a clip's padded end; this tolerance keeps them in the captions.
WORD_END_TOLERANCE = 0.05


def snap_to_frame(seconds: float, frame_rate: float) -> float:
    """Cut on whole frames so picture and sound stay in sync across many cuts."""
    return round(seconds * frame_rate) / frame_rate


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a rough cut from a cut list.")
    parser.add_argument("cut_list", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--short-side", type=int, default=720)
    parser.add_argument("--full-resolution", action="store_true")
    args = parser.parse_args()
    require_program("ffmpeg")

    plan = read_json(args.cut_list)
    base = args.cut_list.resolve().parent
    clips = [c for c in plan.get("clips", []) if c.get("keep", True)]
    if not clips:
        sys.exit('The cut list has no clip with "keep": true.')

    sources: dict[str, VideoInfo] = {}
    for clip in clips:
        if clip["source"] not in sources:
            sources[clip["source"]] = probe_video(base / clip["source"])

    # Frame size and rate follow the first clip's source; other sources are fitted (letterboxed).
    first = sources[clips[0]["source"]]
    width, height = size_for_short_side(first.width, first.height,
                                        None if args.full_resolution else args.short_side)
    rate_text, rate = first.frame_rate, first.frame_rate_value
    quality = ["-preset", "medium", "-crf", "17"] if args.full_resolution else ["-preset", "veryfast", "-crf", "24"]

    words_by_source = {}
    for source, transcript_path in plan.get("transcripts", {}).items():
        transcript = read_json(base / transcript_path)
        words_by_source[source] = [w for s in transcript["segments"] for w in s["words"]]

    temp = Path(tempfile.mkdtemp(prefix="rough-cut-"))
    try:
        parts, timeline_words, mapping = [], [], []
        position = 0.0
        for index, clip in enumerate(clips, start=1):
            start = snap_to_frame(clip["start"], rate)
            end = snap_to_frame(clip["end"], rate)
            length = end - start
            if length <= 0:
                print(f"Skipping clip {clip.get('id')}: end is not after start.")
                continue
            # MOV parts with uncompressed audio: no AAC gaps at the joins and frame-exact timestamps.
            part = temp / f"part_{index:04d}.mov"
            video_filter = (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={rate_text},format=yuv420p")
            audio_filter = (f"aresample=48000,afade=t=in:d={AUDIO_FADE_SECONDS},"
                            f"afade=t=out:st={max(0.0, length - AUDIO_FADE_SECONDS):.3f}:d={AUDIO_FADE_SECONDS}")
            command = ["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{length:.3f}",
                       "-i", str(base / clip["source"])]
            if sources[clip["source"]].has_audio:
                audio_input = "0:a:0"
            else:
                command += ["-f", "lavfi", "-t", f"{length:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
                audio_input = "1:a"
            command += ["-map", "0:v:0", "-map", audio_input, "-vf", video_filter, "-af", audio_filter,
                        "-ac", "2", "-c:v", "libx264", *quality, "-c:a", "pcm_s16le", "-t", f"{length:.3f}", str(part)]
            run_command(command)
            parts.append(part)

            for word in words_by_source.get(clip["source"], []):
                if word["start"] >= start - 0.01 and word["end"] <= end + WORD_END_TOLERANCE:
                    timeline_words.append({"start": round(max(0.0, word["start"] - start) + position, 3),
                                           "end": round(min(length, word["end"] - start) + position, 3),
                                           "word": word["word"]})
            mapping.append({"id": clip.get("id"), "source": clip["source"],
                            "source_start": round(start, 3), "source_end": round(end, 3),
                            "timeline_start": round(position, 3), "timeline_end": round(position + length, 3)})
            position += length
            print(f"clip {clip.get('id')}: {timecode(start)}–{timecode(end)} → at {timecode(position - length)}",
                  flush=True)

        concat_list = temp / "parts.txt"
        concat_list.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        run_command(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", concat_list.name,
                     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                     str(args.output.resolve())], working_directory=temp)
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    words_path = args.output.with_suffix(".words.json")
    write_json(words_path, {"video": args.output.name, "width": width, "height": height,
                            "frame_rate": rate_text, "duration": round(position, 3),
                            "words": timeline_words, "clips": mapping})
    print(f"\nRough cut {timecode(position)} ({width}×{height}) → {args.output}\nWords → {words_path}")


if __name__ == "__main__":
    main()
