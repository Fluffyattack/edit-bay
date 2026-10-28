"""Shared helpers for the editing-videos scripts: probing media with ffprobe, running ffmpeg,
time formatting and JSON I/O. Every other script imports from here."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

# Consoles with a legacy encoding (Windows cp1252, Latin-1 locales) cannot print arrows or warning
# signs; replace such characters instead of crashing.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(errors="replace")

# Frame rates that cameras and phones actually record at. Phones often record a slightly variable
# rate (e.g. 29.98 fps); snapping to the nearest standard rate keeps cuts and audio in sync.
STANDARD_FRAME_RATES = ["24000/1001", "24/1", "25/1", "30000/1001", "30/1", "50/1", "60000/1001", "60/1", "120/1"]
# A measured rate within 1 % of a standard rate is treated as that standard rate.
FRAME_RATE_SNAP_TOLERANCE = 0.01


def require_program(name: str) -> None:
    if shutil.which(name) is None:
        sys.exit(f"'{name}' was not found on PATH. Install ffmpeg first "
                 f"(macOS: 'brew install ffmpeg', Debian/Ubuntu: 'sudo apt install ffmpeg', "
                 f"Windows: 'winget install ffmpeg').")


def run_command(command: list[str], working_directory: Path | None = None) -> None:
    """Run ffmpeg/ffprobe; on failure exit with the command and the tail of ffmpeg's error output."""
    result = subprocess.run(command, cwd=working_directory, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-25:])
        sys.exit(f"Command failed:\n  {' '.join(command)}\n\nffmpeg said:\n{tail}")


@dataclass
class VideoInfo:
    width: int          # displayed width in pixels (phone rotation already applied)
    height: int         # displayed height in pixels
    frame_rate: str     # frames per second as a fraction string, e.g. "30/1" or "30000/1001"
    duration: float     # seconds
    has_audio: bool

    @property
    def frame_rate_value(self) -> float:
        return float(Fraction(self.frame_rate))


def nominal_frame_rate(declared: str | None, average: str | None) -> str:
    candidates = []
    for value in (declared, average):
        if value and value not in ("0/0", "0/1") and 1 <= float(Fraction(value)) <= 240:
            candidates.append(value)
    if not candidates:
        return "30/1"
    measured = float(Fraction(candidates[0]))
    nearest = min(STANDARD_FRAME_RATES, key=lambda rate: abs(float(Fraction(rate)) - measured))
    if abs(float(Fraction(nearest)) - measured) / measured < FRAME_RATE_SNAP_TOLERANCE:
        return nearest
    return candidates[0]


def probe_video(path: Path) -> VideoInfo:
    require_program("ffprobe")
    if not Path(path).exists():
        sys.exit(f"File not found: {path}")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        sys.exit(f"ffprobe could not read '{path}':\n{result.stderr.strip()}")
    data = json.loads(result.stdout)
    video_streams = [s for s in data["streams"] if s.get("codec_type") == "video"
                     and not s.get("disposition", {}).get("attached_pic")]
    if not video_streams:
        sys.exit(f"'{path}' has no video stream.")
    stream = video_streams[0]
    width, height = int(stream["width"]), int(stream["height"])

    # Phones often store landscape pixels plus a 90° rotation flag; report what the viewer sees.
    rotation = 0
    for side_data in stream.get("side_data_list", []) or []:
        if "rotation" in side_data:
            rotation = int(float(side_data["rotation"]))
    rotation = int(stream.get("tags", {}).get("rotate", rotation))
    if abs(rotation) % 180 == 90:
        width, height = height, width

    frame_rate = nominal_frame_rate(stream.get("r_frame_rate"), stream.get("avg_frame_rate"))
    duration = float(data.get("format", {}).get("duration") or stream.get("duration") or 0)
    has_audio = any(s.get("codec_type") == "audio" for s in data["streams"])
    return VideoInfo(width, height, frame_rate, duration, has_audio)


def size_for_short_side(width: int, height: int, short_side: int | None) -> tuple[int, int]:
    """Scale so the shorter side is `short_side` pixels; never upscale; keep even numbers for H.264."""
    if not short_side or min(width, height) <= short_side:
        return width - width % 2, height - height % 2
    factor = short_side / min(width, height)
    return int(round(width * factor / 2)) * 2, int(round(height * factor / 2)) * 2


def timecode(seconds: float) -> str:
    """Format seconds as M:SS.s (or H:MM:SS.s) — the format people use when giving notes."""
    tenths = int(round(seconds * 10))
    whole, tenth = divmod(tenths, 10)
    hours, rest = divmod(whole, 3600)
    minutes, secs = divmod(rest, 60)
    text = f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"
    return f"{text}.{tenth}"


def read_json(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"File not found: {path}")
    except json.JSONDecodeError as error:
        sys.exit(f"{path} is not valid JSON: {error}")


def write_json(path: Path, data: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def filter_path(path: Path) -> str:
    """Escape a path for use inside an ffmpeg filter argument (works on Windows drive letters too)."""
    text = str(path).replace("\\", "/")
    return text.replace(":", "\\:").replace("'", "\\'")
