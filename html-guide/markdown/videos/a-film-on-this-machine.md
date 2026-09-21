---
title: A film on this machine
linkTitle: A film on this machine
weight: 6
description: A video that is a file rather than a YouTube address — its subtitles, the hardlink, playing offline, and taking it away with its film.
---

A video does not have to be on YouTube. A lesson you recorded, a film you
own, a course that came on a disk: give the add page the **path to the
file** instead of an address, and it becomes a video like any other — the
same glossing, the same clouds, the same cards — that plays with **no
internet at all**.

## Adding one

On the add page, answer **Where is the video?** with **A film already on
this machine** ([Adding a video](adding-a-video.md)). Step 1 then asks for
**The film**: the full path of the file, as your file manager shows it —
`/home/you/films/lesson-1.mp4`, `C:\Users\you\Videos\lesson 1.mp4`.
Quotes around it are ignored, and `~` means your home folder.

The page names `.mp4`, `.webm`, `.mkv`, `.mov` and `.m4v`; the server takes
`.avi`, `.ogv` and `.ogg` as well. Whether your browser can **play** the
file is another matter — `.mp4` and `.webm` play everywhere, `.mkv` and
`.avi` often do not — and the player says so if it cannot (below).

What it refuses:

| It says | Which means |
|---|---|
| *name the film on this machine* | the box is empty — said by the page itself, before anything is sent |
| *no file at /home/you/films/lesson-1.mp4* | nothing is there — a typing mistake, or a disk not mounted |
| *.flv is not a video this can play (.mp4, .m4v, .webm, .mkv, .mov, .avi, .ogv, .ogg)* | an extension outside the list |

Either answer to **Who writes the glosses?** takes a film: the prompt for an
LLM, or a video started empty to gloss in the player.

## Its transcript: a panel, or a subtitle file

The transcript box takes the same panel as for a YouTube video — or a whole
**`.srt` or `.vtt` subtitle file**, pasted as it is. It is translated into
the panel everything else here already reads — the `.srt` on the left
becomes the panel on the right:

```text
1                                      0:01.5
00:00:01,500 --> 00:00:04,000          Buongiorno, vorrei un chilo di pomodori
Buongiorno, vorrei un chilo            0:04.2
di pomodori                            Quanto costano le mele oggi

2
00:00:04,200 --> 00:00:07,000
<i>Quanto costano le mele oggi</i>
```

- the cue numbers go, and so do tags such as `<i>` and the word timings of
  YouTube's automatic captions;
- the lines of a cue become one caption, starting at the cue's own time,
  fraction and all;
- **YouTube's rolling captions are collapsed**: automatic captions repeat
  the line before with a few words added. A cue that begins with the whole
  of the caption before it keeps only what it adds, whatever the timing —
  nobody writes a subtitle that way on purpose. A cue that repeats the one
  before **exactly** is dropped when the two overlap in time, and kept when
  they do not: the same words later are somebody saying them again — a
  refrain, a correction;
- a caption that is only digits (*1979*) stays a caption;
- cues out of order are put in order.

A file with no cue it could read is refused: *that subtitle file holds no
cues this could read*.

## What happens to the film

The film goes **beside the transcript**, in the video's own folder, as
`media.mp4` (or whatever its extension is). It is **hardlinked**: a second
name for the same file, which costs no disk and no time even for a two-hour
film. Where the file system forbids a link — the film is on another disk —
it is **copied** instead, which does take time and space; on the way to
the player, a video started empty says which it was (*The film was copied
(1840 MB) — this filesystem would not take a link.*).

Either way what lands is a real file, and **the file being there is the
whole of what makes the video local**: nothing in `video.json` declares it,
so there is no field to keep true. What follows from there being no
YouTube:

- the video's **id** is made from the file's name — or, when you start it
  empty, from the title you typed — with six random hexadecimal characters
  after it (`lesson-1-3fa2c1`), so two lessons both called *lesson 1* are
  two videos;
- `video.json`'s `url` is empty: no address is invented;
- the **title** is the file's name when you give none, and the **channel**
  is **on this machine**;
- nothing is fetched from the internet, at any step.

The film is kept out of git, as a book's recordings are — hundreds of
megabytes are not what a repository is for — while the glosses beside it
are ordinary files that git keeps. The film travels by the download button
instead.

## Playing it

The player shows the browser's own video, with its own controls, where a
YouTube video's frame would be; everything else — the lit line, **follow**,
**hover ⏸**, a click to replay, the clouds — works exactly the same. The
film is served by Parseh itself, a piece at a time, which is what lets it
seek anywhere at once.

### When the film will not play {#when-the-film-will-not-play}

The place of the video says which of these went wrong, and the
transcript still works in every case:

| It says | Which means |
|---|---|
| *this browser cannot play that file* | a format the browser does not play (often `.mkv` or `.avi`): convert it, or open the page in another browser |
| *the film is there but will not decode* | the file is damaged, or only partly copied |
| *the film is not where this video says it is* | the film could not be fetched |
| *the film that belongs to this video is not here any more — put it back beside the transcript, or add the video again* | the video's folder has no `media.…` file: it was moved or deleted |

## What else a film makes possible

- **The timings** draw its waveform from the film itself, on the server,
  with nothing to record first ([The timings](the-timings.md)). This needs
  ffmpeg, as a book's narration does.
- **🔊 cut the audio…** on a card cuts the word's own sound out of the film,
  on the server — no screen sharing, any browser. (The section *Cards and
  Anki* explains the card sheet.)
- A card's link back to its source points at the player on this machine,
  at the card's moment, rather than at youtube.com.

## Taking it away with its film

The ⤓ in the player's bar hands over **the film and its glosses in one
zip**, so that the video comes out of a bundle on another machine and plays
there. Its tooltip says how big that zip is — *(about 1.9 GB)* — because a
browser starts a two-hour film's download without a word. For the words
alone there is no button: add `?media=text` to the download's address, as
the tooltip says. A book's download defaults
the other way, and the asymmetry is the point: a book without its recording
is still the book, while a video without its film is a transcript of
something nobody can watch. See
[Taking videos away and bringing them back](downloads-and-backups.md).
