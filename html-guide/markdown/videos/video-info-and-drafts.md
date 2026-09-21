---
title: Video info and drafts
weight: 11
description: The video info sheet — title, channel, level, blurb, the kanbun checkbox — and what the draft flag means for a video being written.
---

## Video info {#video-info}

Everything on the [editing page](editing-a-phrase.md) is one phrase of one
caption. **video info**, in the player's bar, is the video itself: the
fields of its `video.json` that YouTube's lookup or an LLM's answer can get
wrong — a mistitled video, a channel name YouTube would not give — and that
had no other way to be mended than editing the file.

| Field | Is |
|---|---|
| **title** | the title in Latin letters, shown on the card and in the bar; it may not be blank |
| the language's name (**Persian**, **Japanese**…) | the title in the video's own language and script, `title_native` |
| **channel** | the channel it is filed under — change it and the video moves to that channel's page |
| **level** | **unset**, **beginner**, **lower-intermediate**, **intermediate**, **upper-intermediate** or **advanced** |
| **blurb** | the sentence on the card |
| **order** (Japanese, Chinese) | **read out of its written order (kanbun)** — below |

**save** (or **Ctrl+↵**) writes `video.json`, says *saved ✓* and reloads
the page, since the title and the channel are shown in several places at
once; **nothing to change** is all it says when nothing changed. **✕**, Esc
or a click beside the sheet close it. The video pauses while the sheet is
open and plays on after, if it was playing. There is nothing to rebuild:
the player reads `video.json` on every visit.

What it refuses: *title may not be blank*, and a field holding a control
character — *… carries U+0007 at character 3, which is not text* — which a
paste from a strange source can carry. The server answer, if the server is
not there: *the server did not answer (…) — nothing was written*.

### Kanbun

A Japanese or Chinese phrase carries its words with their readings, and
normally those readings run together are the phrase's own reading — so the
word strip warns when they disagree. A text **read out of its written
order** — classical Chinese read as Japanese, *kanbun* — rightly disagrees
everywhere. Tick **read out of its written order (kanbun)**: it writes
`"reorders": true` into `video.json`, and the readings are no longer
compared with the words. Untick it and the key is taken out again. The
reading editions' **book info** sheet has the same checkbox for a book.

## Drafts {#drafts}

A video [started empty](adding-a-video.md#start-it-empty) is a **draft**:
its `video.json` says `"draft": true`. It means *this is being written*,
and it shows:

- a **draft** badge beside the title in the player's bar (its tooltip: a
  phrase nobody has glossed yet is still yours to fill in, and the checker
  forgives it);
- a **draft** tag on the video's card, and *1 in draft* on its channel's
  card;
- phrases counted as phrases — *12 of 40 chunks glossed* — rather than
  captions, since a draft has a phrase under every caption and nothing
  written in them.

In the player every phrase of a draft is a phrase — hoverable, with a cloud
that says *nothing glossed yet* and a ✎ — even with nothing written on it,
because that blank phrase is exactly what you opened the page to fill in.

### What the flag relaxes

Exactly one thing, in the checker:

- a phrase with **nothing** written in it — no transliteration, no
  vocabulary, no meaning, no kana — is passed over instead of being an
  error;
- a phrase **half** written — the meaning typed, the transliteration still
  to come — is **said** (*missing 'tr' -- still a draft*) rather than
  refused. That is what the middle of the work looks like: the meanings of
  a caption typed in one pass, the transliterations in the next.

Nothing else softens: the text, the colours, the words and the phrases
reproducing their caption are checked in a draft exactly as anywhere else.

The player's own editor does not lean on the flag: a save is refused only
for an error it **brings in**, so typing the meaning into a blank phrase is
always accepted, draft or not. The flag is what lets such a half-written
video pass the checker as a whole — which it must, for instance, to come
back through the [bundle door](downloads-and-backups.md) it went out of.

### Finishing a draft

Take the flag out when the last phrase is glossed: every gap is then an
error again, which is the whole of what the flag means. There is no button
for it — **video info** does not show the flag. Open the video's
`video.json` (`youtube/videos/<language>/<id>/video.json`) in a text editor
and delete the line `"draft": true,`. Nothing else changes, and the badge
and the tag go at the next reload.

> **For the command line.** `python3 youtube/lib/check_annotations.py
> youtube/videos/<language>/<id>` says what is still missing before you take
> the flag out: with it, the half-written phrases are warnings; without it,
> they are the errors a finished video may not have.
