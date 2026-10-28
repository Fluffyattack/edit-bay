# Stages in detail

## Contents
- 1. Brief
- 2. Footage review
- 3. Rough cut → story lock
- 4. Design pass
- 5. Preview → picture lock
- 6. Finish
- Optional: hand-off to an editing app

`S` = `SKILL_DIR/scripts`, `P` = the project folder. Commands work on Linux, macOS and Windows
(use `python` or `python3` as installed).

## 1. Brief

Clarify in conversation, not as a questionnaire:
- one message, audience, platform and aspect ratio (9:16 short, 16:9 YouTube), target length
- starting point: scripted, unscripted, or many clips (vlog, event)
- which references apply to which aspect; which `LEARNINGS.md`/playbook rules matter most here
- fixed wishes (music, call to action, overlays at specific moments)

Result: `P/brief.md`. For unscripted footage the brief may be sharpened after the review.

## 2. Footage review

```bash
python S/transcribe.py P/footage/take1.mp4 P/work/transcript-take1.json --vocabulary "names, jargon"
python S/contact_sheet.py P/footage/take1.mp4 P/work/sheets-take1
```

- `small` is a good CPU default; `medium` or `large-v3-turbo` are more accurate but slower. Transcribe many
  clips one after another in the background.
- Check words with `confidence` below 0.5 and every proper name; they end up in captions otherwise.
  Fix them directly in the transcript JSON.
- Read the contact sheets: shots, locations, gestures, screen recordings, unusable stretches.
- Scripted: compare against the script — missing lines, repeated lines, slips.
- Unscripted: pick the strongest statements and propose an order (hook → core → payoff) with reasons.
- Vlog: group the footage into scenes (place, time, content) and propose an assembly plan as a list.

## 3. Rough cut → story lock

```bash
python S/suggest_cuts.py P/work/transcript-*.json --output P/work/cut_list.json
# edit the cut list: "keep": false on retakes, reorder clips, nudge start/end
python S/check_plan.py P/work/cut_list.json
python S/render_rough_cut.py P/work/cut_list.json P/previews/rough-cut-v1.mp4
```

- `--max-pause` sets the pace: 0.25–0.35 s for snappy shorts, 0.5–0.8 s for calm vlogs.
- Clips may come from any source and be reordered freely; `start`/`end` can be nudged by hand
  (e.g. to drop a breath).
- Report length, number of cuts, which takes were dropped and why.
- The person checks content only: message, order, pace, gaps. Continue only after an explicit "locked".

## 4. Design pass

**Storyboard** (`P/storyboard.md`): one row per beat with time in the rough cut, spoken cue, picture, caption,
overlay, sound. Apply playbook rules and references concretely here. Notes on text are nearly free, so settle
as much as possible at this step.

**Prepare captions and overlays:**

```bash
python S/make_captions.py P/previews/rough-cut-v1.words.json P/work/captions.ass --max-words 3
# make graphics in P/graphics/ (guides/design-with-code.md), fill in P/work/overlays.json
python S/check_plan.py P/work/overlays.json --rough-cut P/previews/rough-cut-v1.mp4
```

**Stills** at the moments that matter (hook, every overlay, split layouts):

```bash
python S/render.py P/previews/rough-cut-v1.mp4 P/previews/stills-v1 \
  --captions P/work/captions.ass --overlays P/work/overlays.json --stills 0.8,4.2,9.5
```

Look at each still before showing it: is a face, mouth or product covered? Does text reach into the platform's
UI zones? Does it match the references? Then show them.

**Test clips** only for things that move (animations, transitions, sound timing):

```bash
python S/render.py P/previews/rough-cut-v1.mp4 P/previews/test-hook-v1.mp4 \
  --captions P/work/captions.ass --overlays P/work/overlays.json --from 0 --to 6
```

## 5. Preview → picture lock

```bash
python S/render.py P/previews/rough-cut-v1.mp4 P/previews/preview-v1.mp4 \
  --captions P/work/captions.ass --overlays P/work/overlays.json
```

- Bump the version in the file name each round; every note names its version.
- After notes, change only what is affected, and show a test clip of the spot instead of re-rendering the whole
  preview for small fixes.
- If the rough cut changes after story lock, all times shift: regenerate captions and move overlay times
  (use `clips` in `*.words.json` to map old to new times).

## 6. Finish

```bash
python S/render_rough_cut.py P/work/cut_list.json P/work/rough-cut-full.mp4 --full-resolution
python S/render.py P/work/rough-cut-full.mp4 P/final/<title>.mp4 --final --normalize-loudness \
  --captions P/work/captions.ass --overlays P/work/overlays.json
```

Verify: `ffprobe` (resolution, frame rate, duration, audio present) and two or three stills from the final file.
Captions and overlays scale automatically because they are planned in canvas pixels.
Then save learnings (SKILL.md, "Turning notes into rules").

## Optional: hand-off to an editing app

If the person wants to fine-tune by hand, the cut list can be converted for an editing app (DaVinci Resolve has
a Python API; Premiere and others import EDL/FCPXML). Not needed for the normal workflow; offer it only on request.
