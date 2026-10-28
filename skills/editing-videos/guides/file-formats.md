# File formats

## Contents
- transcript.json
- cut_list.json
- rough_cut.words.json
- overlays.json

All times are seconds (decimal point). All paths are relative to the file they appear in.
Run `check_plan.py` on a cut list or overlays plan after editing it.

## transcript.json (from `transcribe.py`)

```json
{
  "source": "footage/take1.mp4",
  "duration": 312.4,
  "language": "en",
  "model": "small",
  "segments": [
    {"start": 0.52, "end": 3.9, "text": "This desk took me three years to get right.",
     "words": [{"start": 0.52, "end": 0.71, "word": "This", "confidence": 0.98}]}
  ]
}
```

Transcripts from other services can be converted to this format; required are `source`, `duration` and, per word,
`start`, `end`, `word`.

## cut_list.json (from `suggest_cuts.py`, then edited)

```json
{
  "transcripts": {"../footage/take1.mp4": "transcript-take1.json"},
  "clips": [
    {"id": 1, "keep": false, "source": "../footage/take1.mp4", "start": 0.44, "end": 2.9,
     "text": "This desk took me", "note": "Possible retake: clip 2 starts the same way."},
    {"id": 2, "keep": true, "source": "../footage/take1.mp4", "start": 3.6, "end": 6.85,
     "text": "This desk took me three years to get right."}
  ]
}
```

- List order is playback order. `id` is only for finding clips again.
- `transcripts` maps each source to its transcript; sources without an entry get no captions.

## rough_cut.words.json (from `render_rough_cut.py`)

```json
{
  "video": "rough-cut-v1.mp4", "width": 720, "height": 1280, "frame_rate": "30/1", "duration": 41.3,
  "words": [{"start": 0.08, "end": 0.27, "word": "This"}],
  "clips": [{"id": 2, "source": "../footage/take1.mp4", "source_start": 3.6, "source_end": 6.833,
             "timeline_start": 0.0, "timeline_end": 3.233}]
}
```

`words` are on the rough-cut timeline (input for captions); `clips` maps timecodes between rough cut and source.

## overlays.json (written by Claude, read by `render.py`)

```json
{
  "canvas": {"width": 1080, "height": 1920},
  "overlays": [
    {"image": "../graphics/price-card.png", "start": 3.2, "end": 6.0, "x": "center", "y": 260, "width": 820,
     "fade_in": 0.15, "fade_out": 0.15},
    {"video": "../footage/screen.mp4", "start": 8.0, "end": 12.5, "fullscreen": true, "fade_in": 0.1, "fade_out": 0.1}
  ],
  "sounds": [{"file": "../../../library/sounds/whoosh.wav", "at": 3.1, "volume": 0.6}],
  "music": {"file": "../../../library/music/calm.mp3", "volume": 0.1, "fade_in": 1.0, "fade_out": 2.0}
}
```

| Field | Meaning |
|---|---|
| `canvas` | resolution that `x`, `y`, `width` refer to (usually the export size) |
| `image` / `video` | PNG with transparency, or a video clip; a clip starts from its first frame at `start` |
| `start`, `end` | visible from–to on the rough-cut timeline |
| `x`, `y` | top-left corner in canvas pixels, or `"center"` |
| `width` | width in canvas pixels; height follows the aspect ratio |
| `fullscreen` | fills the frame (cutaway/B-roll); `x`, `y`, `width` are ignored |
| `fade_in`, `fade_out` | fade durations in seconds |
| `sounds[].at` | start time of the sound effect |
| `music` | looped, trimmed to the video length, faded in and out; `null` = no music |

Overlays stack in list order (later ones on top); captions are always on top.
