---
title: Recordings and frames on a card
linkTitle: Recordings and frames
weight: 8
description: How a recording rides on an Anki card without a field of its own, and how the video player captures a frame of the video for a card.
---

## A recording on an Anki card

For Anki, the clip goes on the side you picked under its player on the
card sheet (the language's side, unless you pick the other). Saving the
card **copies** it from the clip tray into the deck's `media/`, beside the
screenshots, named after the card — `20260921-142212-63ef-front-audio.mp3`
or `…-back-audio.mp3` — and the card records it as its front's or its
back's recording. The clip stays in the tray, since the same clip may go
onto an exercise card too.

**The note types do not change.** There is no audio field, and none was
added: a note type's shape must never change once notes have been studied
with it ([Note types and directions](note-types.md#two-kinds-of-card)). The
recording is written as `[sound:…]` into `FrontImage` or `BackImage`,
after the picture when there is one, because those two fields already sit
on the right side of every template — your own restyled templates too.
Anki plays a `[sound:]` wherever a card shows one, when that side is shown
(unless the deck's options in Anki tell it not to play sounds by
themselves), and with its replay button any time.

```text
FrontImage:  <img src="20260921-142212-63ef-front.jpg">[sound:20260921-142212-63ef-front-audio.mp3]
```

**preview card** plays the recording from the tray before the card is
even saved.

The package carries the recordings as it carries the screenshots, and
**the round trip keeps them**: the sync reads `[sound:]` back out of the
two fields, copies the files home, and follows what you did in Anki — a
`[sound:]` you deleted from a field there is gone from the card here after
the next sync, and a sound you replaced under its old name is copied home
anew. A deck brought in from an Anki export for the first time brings its
sounds the same way.

## A recording on an exercise card

For an exercise deck and for markdown the recording is named in the card
itself, `front-audio: audio/clock-710aea.mp3` or `back-audio:` — or, on a
jolly card, as a line in a box, `![](audio/clock-710aea.mp3)`. The deck
copies the file in from the tray when it takes the card; a studio document
does when the card is pasted into it ([The clip tray](clip-tray.md#pasting-a-card-with-its-clips)).
On the deck's study page the card plays its front's recording when it is
shown and its back's when it is turned, as Anki does.

## A frame of the video

In the video player the card sheet has a **frame** row with **📷 capture
the current frame**. It puts **the video's own frame** at the card's moment
on the card — not a screenshot of the page, but the picture of the video
alone, cropped exactly to it.

Under it, once a frame is taken, the picture, two choices of side —
**on the Persian side** or **on the English side** (the language's and
the gloss language's names), the second picked unless you pick the first —
and **remove**. On a jolly card the frame goes into a box instead, as a
line `![](images/…)`, like a recording
([Jolly cards](where-the-card-goes.md#jolly-cards)).

**How it is taken.** The picture of a YouTube video (or of a film) cannot
be read by the page directly, so the capture asks the browser to share
what is on the screen, once:

- **Chrome and Edge** ask to share **this tab**, with its sound, so that
  the same share also serves a YouTube video's recording
  ([Recording a YouTube video's sound](youtube-sound.md)): one **Allow**
  serves both. The capture is then cropped to the video element itself.
- **Firefox** shares a window or the screen: share this browser window
  (or the screen) and keep the player in view. Two coloured dots flash on
  the video's corners for an instant while the capture finds the exact
  area of the video in what was shared.

The sheet hides itself while it takes the picture, so as not to be in its
own frame. A paused video shows YouTube's controls over it, and they
linger for five seconds once it plays, so a paused video is rolled in,
muted, from about five seconds before the card's moment — the controls
have faded when the wanted frame goes by — and then frozen back on that
moment, its sound as it was.

A note under the button, shown the first time and whenever a capture
fails, says the same in short. Sharing stays on while the page is open, so
later captures are instant. The capture needs a secure page: the
toolbox's `https://` address is one, wherever you open it from — a phone
or a laptop on your network as well as the machine itself — and so is
`localhost` on the machine itself.

| It says | What to do |
|---|---|
| capture failed — capture needs a secure page — open the toolbox over its https address | the page was opened over plain `http://`: use the toolbox's `https://` address |
| capture failed — scroll the video into view first | the video is scrolled out of the window |
| capture failed — could not see the player in the shared window — keep this window visible on top, then try again | the shared window or screen (Firefox always shares one) did not show the corner dots: the browser window was covered, minimised or elsewhere. *monitor* in place of *window* means a whole screen was shared |
| capture failed — calibration failed — try again | the corner dots were found, but not where they should be: keep the player unzoomed and in view, and try again |
| capture failed — the video area fell outside the capture — retry | the shared window or screen does not show the whole video |
| capture failed — no frame arrived — try once more | the share sent no picture in time |

**Where the frame goes.** On an Anki card it is saved with the card, as a
JPEG in the deck's `media/` (`…-back.jpg`), and shown on its side; it can
be at most 8 MB. For an exercise deck or markdown it is kept in the
[clip tray](clip-tray.md) and named on the card as its `front-image` or
`back-image`, `images/clock-frame-3fa9c2.jpg`, and the deck or the
document copies it in from there.
