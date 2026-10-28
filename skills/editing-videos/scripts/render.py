"""Design pass, preview and final export: render the rough cut with everything on top.

Layers overlays (graphics, cards, B-roll), sound effects, music and captions over the rough cut.
One script, four outputs — cheapest first:

    stills        --stills 3.2,7.5,12   individual PNG frames: the cheapest way to check the design
    test clip     --from 3 --to 9        just a section, e.g. to check an animation or sound timing
    preview       (default)              whole video, short side 720 px, fast
    final         --final                source resolution, high quality

Usage:
    python render.py <rough_cut.mp4> <output.mp4 | stills-folder>
        [--captions captions.ass] [--overlays overlays.json] [--fonts-dir path]
        [--short-side 720] [--final] [--from S --to S] [--stills S,S,...] [--normalize-loudness]

Times in overlays.json always refer to the rough-cut timeline. For the final export, re-render
the rough cut with --full-resolution first. Run check_plan.py on overlays.json before rendering.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_utils import (filter_path, probe_video, read_json, require_program, run_command,  # noqa: E402
                         size_for_short_side)

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
# -14 LUFS integrated loudness is the common target on YouTube, Instagram and TikTok;
# -1.5 dBTP true peak leaves headroom for the platforms' re-encoding.
LOUDNESS_FILTER = "loudnorm=I=-14:TP=-1.5:LRA=11"


def position_expression(value, axis: str, factor: float) -> str:
    """'center' or a number in canvas pixels → ffmpeg overlay position expression."""
    if value in (None, "center"):
        return "(W-w)/2" if axis == "x" else "(H-h)/2"
    return str(int(round(float(value) * factor)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Render stills, a test clip, a preview or the final export.")
    parser.add_argument("rough_cut", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--captions", type=Path)
    parser.add_argument("--overlays", type=Path)
    parser.add_argument("--fonts-dir", type=Path, help="folder with .ttf/.otf files used by the captions")
    parser.add_argument("--short-side", type=int, default=720)
    parser.add_argument("--final", action="store_true", help="source resolution, high quality")
    parser.add_argument("--from", dest="start", type=float, help="test clip: start second")
    parser.add_argument("--to", dest="end", type=float, help="test clip: end second")
    parser.add_argument("--stills", help="comma-separated seconds, e.g. 1.5,4,9.2")
    parser.add_argument("--normalize-loudness", action="store_true", help="loudness to -14 LUFS (for publishing)")
    args = parser.parse_args()
    require_program("ffmpeg")

    video = probe_video(args.rough_cut)
    width, height = size_for_short_side(video.width, video.height, None if args.final else args.short_side)

    plan = read_json(args.overlays) if args.overlays else {}
    plan_dir = args.overlays.resolve().parent if args.overlays else Path.cwd()
    canvas = plan.get("canvas") or {"width": video.width, "height": video.height}
    factor = width / canvas["width"]

    inputs = ["-i", str(args.rough_cut.resolve())]
    graph = [f"[0:v]scale={width}:{height},setsar=1,format=yuv420p[base0]"]
    last_video = "base0"
    next_input = 1

    for number, overlay in enumerate(plan.get("overlays", []), start=1):
        media = (plan_dir / (overlay.get("image") or overlay["video"])).resolve()
        start, end = float(overlay["start"]), float(overlay["end"])
        fade_in, fade_out = float(overlay.get("fade_in", 0.15)), float(overlay.get("fade_out", 0.15))
        if media.suffix.lower() in VIDEO_EXTENSIONS:
            inputs += ["-i", str(media)]
            shift = f"setpts=PTS-STARTPTS+{start}/TB,"     # the clip starts playing at `start`
        else:
            inputs += ["-loop", "1", "-framerate", video.frame_rate, "-t", f"{video.duration:.3f}", "-i", str(media)]
            shift = ""
        if overlay.get("fullscreen"):
            sizing = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
            x_expr, y_expr = "0", "0"
        else:
            target_width = int(round(float(overlay.get("width", canvas["width"] * 0.8)) * factor / 2)) * 2
            sizing = f"scale={target_width}:-2"
            x_expr = position_expression(overlay.get("x"), "x", factor)
            y_expr = position_expression(overlay.get("y"), "y", factor)
        fades = (f"fade=t=in:st={start}:d={fade_in}:alpha=1,"
                 f"fade=t=out:st={max(start, end - fade_out)}:d={fade_out}:alpha=1")
        graph.append(f"[{next_input}:v]{shift}{sizing},format=rgba,{fades}[layer{number}]")
        graph.append(f"[{last_video}][layer{number}]overlay=x={x_expr}:y={y_expr}:"
                     f"enable='between(t,{start},{end})':eof_action=pass[base{number}]")
        last_video = f"base{number}"
        next_input += 1

    working_directory = None
    if args.captions:
        # The ass filter is fussy about paths, so run inside the captions folder and pass a bare file name.
        working_directory = args.captions.resolve().parent
        fonts = f":fontsdir={filter_path(args.fonts_dir.resolve())}" if args.fonts_dir else ""
        graph.append(f"[{last_video}]ass={filter_path(Path(args.captions.name))}{fonts}[picture]")
    else:
        graph.append(f"[{last_video}]null[picture]")

    if args.stills:
        times = [float(t) for t in args.stills.split(",") if t.strip()]
        frame = 0.999 / video.frame_rate_value
        condition = "+".join(f"between(t,{t:.3f},{t + frame:.3f})" for t in times)
        graph.append(f"[picture]select='{condition}'[out]")
        args.output.mkdir(parents=True, exist_ok=True)
        run_command(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(graph),
                     "-map", "[out]", "-fps_mode", "passthrough", str(args.output.resolve() / "still-%02d.png")],
                    working_directory)
        for index, t in enumerate(times, start=1):
            produced = args.output / f"still-{index:02d}.png"
            if produced.exists():
                produced.replace(args.output / f"still-{t:07.2f}s.png")
        print(f"{len(times)} stills → {args.output}/")
        return
    graph.append("[picture]null[out]")

    audio_inputs = ["[0:a]"] if video.has_audio else []
    for number, sound in enumerate(plan.get("sounds", []), start=1):
        inputs += ["-i", str((plan_dir / sound["file"]).resolve())]
        delay = int(round(float(sound["at"]) * 1000))
        graph.append(f"[{next_input}:a]aresample=48000,volume={sound.get('volume', 0.8)},"
                     f"adelay={delay}|{delay}[sfx{number}]")
        audio_inputs.append(f"[sfx{number}]")
        next_input += 1
    if plan.get("music"):
        music = plan["music"]
        inputs += ["-stream_loop", "-1", "-i", str((plan_dir / music["file"]).resolve())]
        fade_out = float(music.get("fade_out", 2.0))
        graph.append(f"[{next_input}:a]aresample=48000,atrim=0:{video.duration:.3f},"
                     f"volume={music.get('volume', 0.12)},afade=t=in:d={music.get('fade_in', 1.0)},"
                     f"afade=t=out:st={max(0.0, video.duration - fade_out):.3f}:d={fade_out}[music]")
        audio_inputs.append("[music]")
        next_input += 1

    audio_out = None
    if audio_inputs:
        loudness = f",{LOUDNESS_FILTER}" if args.normalize_loudness else ""
        if audio_inputs == ["[0:a]"]:
            graph.append(f"[0:a]anull{loudness}[audio]")
        else:
            # normalize=0 keeps each volume as written instead of amix dividing by the input count.
            graph.append(f"{''.join(audio_inputs)}amix=inputs={len(audio_inputs)}:duration=first:"
                         f"normalize=0{loudness}[audio]")
        audio_out = "[audio]"

    command = ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(graph), "-map", "[out]"]
    command += ["-map", audio_out] if audio_out else ["-an"]
    if args.start is not None:
        command += ["-ss", f"{args.start:.3f}"]   # output-side seek keeps overlay timing intact
    if args.end is not None:
        command += ["-to", f"{args.end:.3f}"]
    quality = (["-preset", "slow", "-crf", "17", "-b:a", "256k"] if args.final
               else ["-preset", "veryfast", "-crf", "26", "-b:a", "128k"])
    command += ["-c:v", "libx264", "-pix_fmt", "yuv420p", *quality, "-c:a", "aac", "-movflags", "+faststart",
                str(args.output.resolve())]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    run_command(command, working_directory)
    kind = "Final export" if args.final else ("Test clip" if args.start is not None else "Preview")
    print(f"{kind} ({width}×{height}) → {args.output}")


if __name__ == "__main__":
    main()
