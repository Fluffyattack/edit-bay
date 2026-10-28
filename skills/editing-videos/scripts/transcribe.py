"""Transcribe footage locally with a timestamp for every word (faster-whisper).

Word timings drive everything downstream: cutting on word boundaries, removing pauses,
and word-by-word captions.

Usage:
    python transcribe.py <video-or-audio> <transcript.json> [--model small] [--language en]
                         [--vocabulary "Product names, people, jargon"]

Writes:
    transcript.json  segments and words with start/end in seconds (see guides/file-formats.md)
    transcript.txt   readable version with timecodes for planning the story

Requires: pip install faster-whisper
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_utils import timecode, write_json  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe with per-word timestamps (faster-whisper).")
    parser.add_argument("input", type=Path, help="video or audio file")
    parser.add_argument("output", type=Path, help="target file, e.g. work/transcript-take1.json")
    parser.add_argument("--model", default="small",
                        help="tiny, base, small, medium, large-v3 or large-v3-turbo (default: small). "
                             "Larger is more accurate but slower.")
    parser.add_argument("--language", default=None, help="language code such as en or de; default: auto-detect")
    parser.add_argument("--vocabulary", default="",
                        help="names and terms spoken in the video, so they are spelled correctly")
    parser.add_argument("--threads", type=int, default=os.cpu_count() or 4, help="CPU threads to use")
    args = parser.parse_args()

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper is not installed. Run: pip install faster-whisper")
    if not args.input.exists():
        sys.exit(f"File not found: {args.input}")

    started = time.time()
    # int8 keeps memory low on CPUs; "auto" uses a CUDA GPU when one is available.
    model = WhisperModel(args.model, device="auto", compute_type="int8", cpu_threads=args.threads)
    segments, info = model.transcribe(
        str(args.input),
        language=args.language,
        word_timestamps=True,
        vad_filter=True,                   # skip long silences (voice activity detection)
        initial_prompt=args.vocabulary or None,
        condition_on_previous_text=False,  # stops one misheard phrase from repeating through long takes
    )

    collected, readable = [], []
    for segment in segments:
        words = [{"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word.strip(),
                  "confidence": round(w.probability, 3)}
                 for w in (segment.words or []) if w.word.strip()]
        collected.append({"start": round(segment.start, 3), "end": round(segment.end, 3),
                          "text": segment.text.strip(), "words": words})
        readable.append(f"[{timecode(segment.start)} – {timecode(segment.end)}] {segment.text.strip()}")
        print(readable[-1], flush=True)

    write_json(args.output, {"source": str(args.input), "duration": round(info.duration, 3),
                             "language": info.language, "model": args.model, "segments": collected})
    args.output.with_suffix(".txt").write_text("\n".join(readable) + "\n", encoding="utf-8")
    word_count = sum(len(s["words"]) for s in collected)
    low_confidence = sum(1 for s in collected for w in s["words"] if w["confidence"] < 0.5)
    print(f"\n{len(collected)} segments, {word_count} words ({low_confidence} with confidence < 0.5), "
          f"{info.duration:.0f} s of audio in {time.time() - started:.0f} s → {args.output}")


if __name__ == "__main__":
    main()
