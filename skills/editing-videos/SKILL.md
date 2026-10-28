---
name: editing-videos
description: >-
  Edits videos end to end with ffmpeg and Python instead of an editing app: local word-level transcription,
  cut lists, frame-accurate rough cuts, word-by-word captions, overlays, B-roll, sound effects, music,
  previews and final export, in gated stages (brief, rough cut, story lock, design pass, preview,
  picture lock, finish). Keeps a persistent edit bay of reference notes, playbooks and LEARNINGS.md so every
  video applies what earlier notes taught. Use when the user wants to cut, trim, caption, subtitle, add
  graphics or B-roll to, or render a video, reel, TikTok, YouTube Short, vlog or talking-head recording;
  remove pauses, filler words or retakes; give timestamped notes on an edit; or collect style references
  for future videos.
---

# Editing videos

Claude edits by writing plans and running scripts: transcript with word timings → cut list → ffmpeg.
The person decides; Claude plans, runs the tools and checks the results. Two habits keep the results personal
instead of generic:

1. **Personal style is written down** in reference notes that say *what exactly* works in a video someone likes.
2. **Notes become rules.** Every correction that should hold in future is logged, so the next video starts ahead.

`SKILL_DIR` below means this skill's directory. Scripts need Python 3.10+ and ffmpeg (with libass and libx264);
`transcribe.py` also needs `pip install faster-whisper`, graphics usually `pip install pillow`. Check what is
missing first (`ffmpeg -version`, `python -c "import faster_whisper"`) and tell the person what to install —
don't install system packages unasked.

## The edit bay

All projects live in one folder, the edit bay. If none exists, ask where it should go, then run:

```bash
python SKILL_DIR/scripts/create_edit_bay.py ~/edit-bay
python SKILL_DIR/scripts/new_project.py ~/edit-bay "Desk setup reel"
```

If an edit bay exists, **read its `CLAUDE.md`, `LEARNINGS.md`, the matching playbook and the reference notes
named in the brief before cutting anything.** Layout, reference notes and how rules mature: [guides/edit-bay.md](guides/edit-bay.md).

## Workflow

Copy this checklist into the conversation and tick it off as you go:

```
Edit progress:
- [ ] 1. Brief agreed (brief.md)
- [ ] 2. Footage reviewed (transcripts, contact sheets)
- [ ] 3. Rough cut rendered → STORY LOCK from the person
- [ ] 4. Design pass: storyboard → stills → test clips
- [ ] 5. Preview rendered, notes applied → PICTURE LOCK from the person
- [ ] 6. Final exported and checked
- [ ] 7. Learnings proposed and saved
```

Each stage is cheaper to change than the next, so fix things early and render full resolution once.
Never skip a lock: everything later is built on it. Going back to an earlier stage is always fine.
Commands, options and checks for every stage: [guides/stages.md](guides/stages.md).

1. **Brief.** Ask before cutting: the one message, audience, platform and aspect ratio, length, which
   references apply (and for which aspect), scripted or unscripted. Write `brief.md`.
2. **Footage review.** `transcribe.py` for each recording; `contact_sheet.py` to see the picture (Claude can't
   play video but can read images). Scripted: check every line was said and find duplicate takes. Unscripted:
   find the strongest moments and propose an order. Fix misheard names in the transcript before going on.
3. **Rough cut.** `suggest_cuts.py` removes pauses and fillers and flags retakes. Decide which clips stay and in
   what order (usually the last complete take wins) and say why. `check_plan.py`, then `render_rough_cut.py`.
   The person reviews content only — message, order, pace, gaps. Story first, design later.
4. **Design pass**, in this order, each with a round of notes:
   `storyboard.md` (text only) → stills (`render.py --stills`) → short test clips (`render.py --from --to`) for
   anything that moves. Look at every still yourself before showing it. How captions, graphics, B-roll and
   sound are made: [guides/design-with-code.md](guides/design-with-code.md).
5. **Preview.** Whole video at 720p, version in the file name (`preview-v2.mp4`) so every timecode in a note is
   unambiguous. Suggest one uninterrupted viewing first, then a second pass noting timecodes.
6. **Finish.** Re-render the rough cut with `--full-resolution`, then `render.py --final` with the same captions
   and overlays. Verify with ffprobe and a few stills from the final file.
7. **Learnings.** See below.

Validate before every render: `python SKILL_DIR/scripts/check_plan.py <cut_list.json | overlays.json>`.
If it reports problems, fix the plan and run it again; render only when it prints `OK`.

## Notes that work

A useful note has three parts: **where** (version + timecode), **what you see**, **what you want** —
for example: "preview v2 at 0:12 — the price card hides the product — move it to the top-left."
When a note is vague ("make it punchier"), don't guess. Ask where, or offer two or three concrete readings
(faster cuts? punch-in zooms on key words? a sound on each card?). Log every note in the project's `notes.md`.

Timecodes refer to the named preview version; `*.words.json` → `clips` maps rough-cut time back to source time.

## Turning notes into rules

After each round of notes, sort them:

- **This video only** ("move the card at 0:12") → `notes.md`, nothing else.
- **Every video** ("cards never cover the product", "max three words per caption") → an entry in
  `LEARNINGS.md` (date, rule, why, origin); proven rules move into the matching playbook.

If it's unclear whether a note is universal, ask — a wrong rule damages every future video. Write rules so they
can be checked (numbers, positions, durations). If a new note contradicts an existing rule, ask whether the rule
should change instead of silently making an exception.

At the end of a project, list the learnings found in this chat, ask which to save, save them, and tick
"Learnings saved" in `brief.md`.

## Render budget

Rendering costs time (and, for every round, tokens). Previews at 720p, test clips instead of whole videos,
full resolution exactly once. On slow machines use the `small` Whisper model or smaller and run long jobs in the
background with progress updates; faster-whisper uses a CUDA GPU automatically when present.

## References

When someone shares a video they like, write a reference note ([guides/edit-bay.md](guides/edit-bay.md)):
download a 720p copy with `yt-dlp -f "bv*[height<=720]+ba/b[height<=720]" -o "references/<name>/video-720p.%(ext)s" <url>`,
make a contact sheet, and agree *together* on what works, area by area, with timecodes. Other people's footage
is for analysis only and never goes into the person's videos. Mix single elements from several references so the
result looks like the person, not like one particular creator.

## File formats

Transcript, cut list, words file and overlays plan are JSON: [guides/file-formats.md](guides/file-formats.md).
Read it before writing `overlays.json` or editing a cut list by hand.
