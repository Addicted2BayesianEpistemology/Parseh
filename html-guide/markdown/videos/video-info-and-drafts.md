---
title: Video info
weight: 12
description: The video info sheet — title, channel, level, blurb, the kanbun checkbox — and a video whose phrases are still being glossed.
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

## A video still being glossed {#drafts}

Nothing marks a video as unfinished. A video [started
empty](adding-a-video.md#start-it-empty) is an ordinary video whose phrases
have nothing written in them yet, and **a phrase nobody has glossed is
legal in every video, for as long as it stays so**. There is no flag to set
and none to take off when the last one is written — a `"draft": true` an
older Parseh left in a `video.json` is never read, and may stay or go.

Where it shows:

- on the video's card, phrases are counted rather than captions while any
  is blank — *12 of 40 chunks glossed* — since a video started empty has a
  phrase under every caption and nothing written in them
  ([The video index and channels](finding-a-video.md));
- in the player every blank phrase of the language is a phrase like any
  other — hoverable, with a cloud that says *nothing glossed yet* and a
  **✎** — because it is exactly what you opened the page to fill in
  ([The video player](the-player.md)).

It is glossed a phrase at a time in the ✎ form
([Editing a phrase](editing-a-phrase.md)), where a meaning may be saved
before its transliteration, or a run at a time by an LLM
([Glossing captions with an LLM](glossing-with-an-llm.md)), which fills only
the phrases nobody has glossed.

**What the checker makes of it.** A phrase with **nothing** written in it —
no transliteration, no vocabulary, no meaning, no kana — is counted, once
for the whole video (*note: 12 of 40 chunks have no gloss yet*), and asked
for nothing else. A phrase **half** written — the meaning typed, the
transliteration still to come — is an error to the checker, which is how
the half-done work is found; the ✎ form saves it on the way, and a
[bundle](downloads-and-backups.md) that carries one is still taken back in,
with a note saying how many.

> **For the command line.** `python3 youtube/lib/check_annotations.py
> youtube/videos/<language>/<id>` lists every phrase still half written,
> and counts the blank ones.
