# The edit bay

## Contents
- Why one folder
- Layout
- Reference notes
- LEARNINGS.md and playbooks
- Closing a project

## Why one folder

Preferences that live only in a chat are gone when the chat ends. The edit bay is a plain folder that every new
editing session opens first: style rules, saved references and per-video working files sit side by side, so a
new session picks up where the last one stopped.

## Layout

```
edit-bay/
├── CLAUDE.md        how work is done here + house rules (channel, platforms, fonts, colours …)
├── LEARNINGS.md     log of rules that apply to every video, newest first
├── inbox/           unfiled memos, ideas, notes, raw files
├── references/      <name>/note.md + 720p copy + contact sheet / screenshots
├── playbooks/       general.md + one file per format (talking-head-short.md, vlog.md, …)
├── library/         sounds/, music/, fonts/, graphics/, caption-styles.md
└── projects/        YYYY-MM-DD-title/ per video
```

Two assets grow with every video: **references** (what the person likes) and **playbooks + library**
(how it is made). `LEARNINGS.md` is the staging area between notes and playbooks.

## Reference notes

A saved video is only as useful as the note next to it. "I like this" is not enough; the note records *which
aspect* works, as measurably as possible:

| Area | Look for |
|---|---|
| Hook | What happens in the first 1–3 s? Text, motion, a question, a sound? |
| Cutting and pace | Cuts on word boundaries? How often does something new appear? Punch-in zooms? |
| Captions | Words per caption, font, size, colour, highlight of the spoken word, position, animation |
| Overlays | Kind (card, screenshot, emoji, lower third), timing, placement, how it enters and leaves |
| Look | Colour, typography, framing, layouts such as split screen |
| Sound | Effects on cuts and overlays, music, level balance |
| Structure | Arc, payoff, call to action |

Writing a note together with the person:

1. Download a 720p copy into `references/<name>/` with yt-dlp (`pip install yt-dlp`; works for YouTube,
   Instagram, TikTok and many more).
2. Run `contact_sheet.py` and look at the sheets; transcribe if the content matters.
3. Describe what you see and ask what they like. They may add marked-up screenshots with timecodes.
4. Fill in `_reference-note-template.md`, including "Not for us".

Mix sources: captions from one reference, pacing from a second, overlays from a third. The brief of each project
names which reference applies to which aspect.

## LEARNINGS.md and playbooks

| | `projects/<p>/notes.md` | `LEARNINGS.md` | `playbooks/*.md` |
|---|---|---|---|
| Holds | every note on this video | rules for all videos, with origin | organised, proven rule set |
| Example | "move the card at 0:12" | "cards never cover the product" | section "Overlays" |
| When | immediately | as soon as it's clearly universal | once the rule has held up |

Good rules are concrete (numbers, positions, durations), give a reason (so edge cases are judged sensibly) and an
origin (so they can be checked or reverted). A playbook for a format is worth starting the second time that
format comes up: the first vlog is work, the second one starts from the vlog playbook.

## Closing a project

1. Final video in `final/`, checks done.
2. Go through the chat for learnings and propose them: "I'd add these to LEARNINGS.md: …".
3. After approval, write them, update playbooks, tick `brief.md`.
4. Large intermediates (previews, test clips) may be deleted on request. Keep the cut list, overlays plan,
   captions and graphics code — they re-render the video at any time.
