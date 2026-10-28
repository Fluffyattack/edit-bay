# Design with code

## Contents
- 1. Captions
- 2. Graphics and cards
- 3. B-roll and screen recordings
- 4. Sound and music
- 5. Formats and safe zones
- 6. Optional outside services

Everything on top of the rough cut is a file, assembled by `render.py`. No extra tool is required; Claude
generates graphics in code.

## 1. Captions

`make_captions.py` writes ASS subtitles from the rough cut's word timings.

| Option | Effect | Typical short | Typical vlog / YouTube |
|---|---|---|---|
| `--max-words` | words per caption (punctuation and pauses also start a new one) | 2–3 | 6–8 |
| `--size` | fraction of the short side | 0.07–0.09 | 0.045–0.055 |
| `--highlight` | colour of the spoken word, or `none` | accent colour | `none` |
| `--position`, `--bottom-margin` | placement | bottom, 0.28–0.35 | bottom, 0.06–0.1 |
| `--animation pop` | each group pops in | yes | usually `none` |
| `--uppercase`, `--font`, `--outline` | look | per reference | per reference |

Put custom fonts in `library/fonts/` and pass `--fonts-dir` when rendering; `--font` must be the font's internal
family name (Linux/macOS: `fc-scan --format "%{family}\n" file.ttf`). Save combinations that worked in
`library/caption-styles.md`. For one-off emphasis, edit the ASS file directly: override tags such as
`{\c&H00D4FF&}` (colour, written blue-green-red) or `{\fs120}` (size) apply from where they appear.

## 2. Graphics and cards

Overlays are PNGs with transparent backgrounds in `P/graphics/`. Save the code that generates each one next to it
(`graphics/price-card.py`) so changes are quick and recurring graphics can move to `library/graphics/`.

Two dependable approaches:

- **Python + Pillow** (`pip install pillow`): fast, no browser needed; good for cards, lower thirds, numbers,
  arrows. Rounded boxes: `ImageDraw.rounded_rectangle`; soft shadows: draw on a separate layer, blur it with
  `ImageFilter.GaussianBlur`, composite underneath.
- **HTML/CSS rendered in a headless browser** (e.g. Playwright: `page.screenshot(omit_background=True)`):
  best for typography and web-style layouts. Animations work too: capture frames and join them with ffmpeg into a
  video with alpha (`-c:v qtrle` in `.mov` or `-c:v png` in `.mkv`).

Positions in `overlays.json` are in canvas pixels (`canvas`, e.g. 1080×1920); `render.py` scales them for preview
and export. `fade_in`/`fade_out` are opacity fades in seconds. For motion (slide-in, zoom), render an animated
overlay or extend the filter in `render.py`.

Check before showing:
- faces, mouths, eyes and the product being shown stay visible (look at a still)
- graphics and captions don't collide
- text stays inside the safe zones (section 5)
- every overlay has a reason in what is being said (its cue in the storyboard)
- no empty boxes where symbols should be: many fonts lack glyphs such as ✓ or →; draw icons as shapes
  or pick a font that has them

## 3. B-roll and screen recordings

- **Cutaway over the voice**: clip as `"video"` with `"fullscreen": true` in `overlays.json`; the main audio
  continues.
- **Picture in picture**: `"video"` without `fullscreen`, with `width`, `x`, `y`.
- **Split screen (e.g. top/bottom)**: the screen recording on top as `"video"` with `"width": 1080, "x": 0, "y": 0`;
  move or crop the speaker beforehand (an extra ffmpeg `crop`/`pad` step on the rough cut). Show a new layout
  as a still first.
- Photos and generated images are handled like graphics.

## 4. Sound and music

- Sound effects in `sounds` with `at` (seconds) and `volume` (1.0 = original). Typical: a soft whoosh when a card
  enters, a click on a text change — subtle; speech must stay clearly intelligible.
- Music in `music` with `volume` around 0.08–0.15 under speech; it loops and fades out at the end.
- `--normalize-loudness` on export targets −14 LUFS (LUFS measures perceived loudness; −14 is common on YouTube,
  Instagram and TikTok).
- Use licensed or self-made audio only, and note source and licence in `library/sounds/LICENSES.md`.

## 5. Formats and safe zones

| Format | Export size | Notes |
|---|---|---|
| Vertical 9:16 | 1080×1920 or 2160×3840 | platform UI covers roughly the top 12 %, bottom 25 % and right 12 % |
| YouTube 16:9 | 1920×1080 or 3840×2160 | captions bottom centre; overlays in the third beside the speaker |
| Square / 4:5 | 1080×1080 / 1080×1350 | feeds and carousels |

Keep the source frame rate (usually 30 or 60 fps). Phone rotation is detected automatically.

## 6. Optional outside services

None is required; use them only if the person wants to and has access:
- cloud transcription instead of local Whisper — convert the result to the transcript format in `file-formats.md`
- image or B-roll generators for illustrations
- sound and music generators or licensed libraries
- a video-capable model to "watch" a preview and flag issues; contact sheets and stills usually suffice
