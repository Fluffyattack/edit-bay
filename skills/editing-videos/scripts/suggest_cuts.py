"""Rough cut, step 1: propose a cut list from one or more transcripts.

The cut list is an editable JSON file: the clips of the footage that stay in the video, in the
order they will play. This script removes pauses and filler words and flags likely retakes
(a sentence that was started more than once). Deciding which takes survive and in what order
is done afterwards by setting "keep": false or reordering clips.

Usage:
    python suggest_cuts.py <transcript.json> [<transcript2.json> ...] --output cut_list.json
        [--max-pause 0.4] [--pad-before 0.08] [--pad-after 0.15] [--keep-fillers]

Several transcripts (e.g. many clips of a vlog) are appended into one list.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_utils import read_json, timecode, write_json  # noqa: E402

# Hesitation sounds in English and German; extend for other languages.
FILLER_WORDS = {"um", "uh", "uhm", "erm", "er", "hmm", "hm", "äh", "ähm", "öhm", "äm", "ehm"}
# A retake usually restarts within the next few clips.
RETAKE_LOOKAHEAD = 4
# Number of opening words compared when looking for a restarted sentence.
RETAKE_OPENING_WORDS = 3


def normalize(word: str) -> str:
    return re.sub(r"[^\w]", "", word.lower())


def group_words(words: list[dict], duration: float, max_pause: float,
                pad_before: float, pad_after: float) -> list[dict]:
    """Merge words into clips; a gap longer than max_pause starts a new clip."""
    groups: list[list[dict]] = []
    for word in words:
        if groups and word["start"] - groups[-1][-1]["end"] <= max_pause:
            groups[-1].append(word)
        else:
            groups.append([word])

    clips = []
    for group in groups:
        start = max(0.0, group[0]["start"] - pad_before)
        end = group[-1]["end"] + pad_after
        if duration:
            end = min(duration, end)
        text = " ".join(w["word"] for w in group)
        if clips and start < clips[-1]["end"]:
            clips[-1]["end"] = round(end, 3)          # padding overlaps: merge instead of playing twice
            clips[-1]["text"] += " " + text
            continue
        clips.append({"start": round(start, 3), "end": round(end, 3), "text": text})
    return clips


def flag_retakes(clips: list[dict]) -> None:
    for index, clip in enumerate(clips):
        opening = [normalize(w) for w in clip["text"].split()[:RETAKE_OPENING_WORDS]]
        if len(opening) < 2:
            continue
        for later in clips[index + 1:index + 1 + RETAKE_LOOKAHEAD]:
            if [normalize(w) for w in later["text"].split()[:len(opening)]] == opening:
                clip["note"] = (f"Possible retake: clip {later['id']} starts the same way. "
                                f"The last complete attempt is usually the keeper.")
                break


def main() -> None:
    parser = argparse.ArgumentParser(description="Propose a cut list from transcript(s).")
    parser.add_argument("transcripts", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True, help="e.g. work/cut_list.json")
    parser.add_argument("--max-pause", type=float, default=0.4,
                        help="cut out pauses longer than this many seconds (0.25–0.35 snappy, 0.5–0.8 relaxed)")
    parser.add_argument("--pad-before", type=float, default=0.08, help="seconds kept before the first word")
    parser.add_argument("--pad-after", type=float, default=0.15, help="seconds kept after the last word")
    parser.add_argument("--keep-fillers", action="store_true", help="do not remove um/uh/erm")
    args = parser.parse_args()

    list_folder = args.output.resolve().parent
    all_clips, transcript_map = [], {}
    for transcript_path in args.transcripts:
        transcript = read_json(transcript_path)
        source = Path(transcript["source"])
        if not source.is_absolute():
            source = (Path.cwd() / source).resolve()
        source_rel = os.path.relpath(source, list_folder).replace("\\", "/")
        transcript_map[source_rel] = os.path.relpath(transcript_path.resolve(), list_folder).replace("\\", "/")

        words = [w for s in transcript["segments"] for w in s["words"]]
        if not args.keep_fillers:
            words = [w for w in words if normalize(w["word"]) not in FILLER_WORDS]
        for clip in group_words(words, transcript.get("duration", 0), args.max_pause,
                                args.pad_before, args.pad_after):
            all_clips.append({"source": source_rel, **clip})

    for number, clip in enumerate(all_clips, start=1):
        clip["id"] = number
    flag_retakes(all_clips)
    ordered = [{"id": c["id"], "keep": True, "source": c["source"], "start": c["start"], "end": c["end"],
                "text": c["text"], **({"note": c["note"]} if "note" in c else {})} for c in all_clips]
    write_json(args.output, {
        "about": ("Clips play in this order. Set \"keep\": false to drop one; reorder freely. "
                  "start/end are seconds in the source file. Paths are relative to this file."),
        "transcripts": transcript_map,
        "clips": ordered,
    })

    total = sum(c["end"] - c["start"] for c in ordered)
    print(f"{len(ordered)} clips, {timecode(total)} in total → {args.output}\n")
    for c in ordered:
        flag = f"  ⚠ {c['note']}" if "note" in c else ""
        print(f"{c['id']:>3}. {timecode(c['start'])}–{timecode(c['end'])}  {c['text'][:90]}{flag}")


if __name__ == "__main__":
    main()
