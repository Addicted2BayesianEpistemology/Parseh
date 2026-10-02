---
title: A film on this machine
linkTitle: A film on this machine
weight: 6
description: A video that is a file rather than a YouTube address, a film or a sound alone — named by its path or sent, its subtitles, the hardlink, playing offline, and taking it away with it.
---

A video does not have to be on YouTube. A lesson you recorded, a film you
own, a course that came on a disk: give the add page the **path to the
file** instead of an address, and it becomes a video like any other — the
same glossing, the same clouds, the same cards — that plays with **no
internet at all**. The file may be a **sound** as well as a film
([below](#a-sound-instead-of-a-film)), and it may be **sent** from another
device instead of named ([below](#sending-the-file-instead-of-naming-it)).

## Adding one

On the add page, answer **Where is the video?** with **A video or a sound on
this machine** ([Adding a video](adding-a-video.md)). Step 1 then asks for
**The video or sound**: the full path of the file, as your file manager
shows it — `/home/you/films/lesson-1.mp4`, `C:\Users\you\Videos\lesson 1.mp4`.
Quotes around it are ignored, and `~` means your home folder. When you leave
the box the page says what the file is: *A video (mp4, 412 MB, 1:02:11).* or
*A sound with no picture (mp3, 4.2 MB, 3:12): the player shows a bar with its
waveform in place of a frame.*

The page names `.mp4`, `.webm`, `.mkv`, `.mov` and `.m4v`; the server takes
`.avi`, `.ogv` and `.ogg` as well, and the sounds below. Whether your
browser can **play** the file is another matter — `.mp4` and `.webm` play
everywhere, `.mkv` and `.avi` often do not — and the player says so if it
cannot (below).

What it refuses:

| It says | Which means |
|---|---|
| *name the film on this machine* | the box is empty — said by the page itself, before anything is sent |
| *no file at /home/you/films/lesson-1.mp4* | nothing is there — a typing mistake, or a disk not mounted |
| *.flv is not a video this can play, nor a sound (videos: .mp4, .m4v, …; sounds: .mp3, .m4a, …)* | an extension outside the lists |

Either answer to **Who writes the glosses?** takes a film or a sound: the
prompt for an LLM, or a video started empty to gloss in the player.

## A sound instead of a film {#a-sound-instead-of-a-film}

A recording that was never filmed is a video with no picture. Any of
`.mp3`, `.m4a`, `.aac`, `.ogg`, `.oga`, `.opus`, `.wav`, `.flac`, `.weba`,
`.wma`, `.aiff`, `.aif`, `.amr`, `.mka` and `.caf` is taken wherever a film
is: by its path, sent, started empty, glossed by an LLM, transcribed by
speech to text. What is different, and why:

- **it is decided once** whether the file is a sound. `video.json` says
  `"kind": "audio"` and nothing else needs to look (a film's `video.json`
  says nothing, as it always did). Where ffmpeg is installed it is asked what
  is *inside* the file, so an mp3 with the album's picture in it is still a
  sound; without it the extension decides;
- **the player draws a bar** where a video shows a frame: the shape of the
  sound, whole, with the playing place on it — press anywhere on it to go
  there, drag to scrub — the browser's own play controls under it, and a
  hairline at the foot where each caption starts. It is drawn by ffmpeg from
  the file; without ffmpeg the bar is a plain track and says so. The
  transcript follows the sound as it follows a film, and everything that
  worked on a film's sound — [the timings](the-timings.md), a card's recording —
  works on a sound's;
- **a card has no frame**: the sheet's *frame* row is not drawn, and the
  card takes the **recording** cut out of the sound ([Adding a video](adding-a-video.md#speech-to-text)
  says what the speech to text does with one);
- **the shelf says so**: a card of a sound carries *♪ a sound*, where a
  thumbnail would be;
- **a prompt to an LLM** names it *a recording on the reader's own machine,
  not on YouTube*.

### A sound the browser cannot play

`.wma`, `.aiff`, `.aif`, `.amr`, `.mka` and `.caf` — and a file whose sound
is in a form a browser has no player for — get a **playable copy**, made by
ffmpeg when the video is added (an mp3 where ffmpeg can write one, else an
m4a or a wav). The copy is the video's `media.mp3`; **the original is kept
beside it** as `media-orig.wma`, hard-linked where the disk allows it, so it
costs no space. The page says so when you leave the path box — *.wma is a
sound this browser cannot play as it is: a playable copy is made when the
video is added, and the original stays beside it* — and the answer says it
again when it is done. A bundle carries the copy and not the original.

Where ffmpeg is not installed the sound is added **as it is** and the page
says so, in words, before you go on: *…ffmpeg, which would make a playable
copy, is not installed on this computer: it is added as it is, and may stay
silent*. The player says *this browser cannot play that sound* if it is.
Install ffmpeg and add the sound again.

## Sending the file instead of naming it {#sending-the-file-instead-of-naming-it}

The path stays what it always was: the way to name a file that is on the
computer, hard-linked, so a two-hour film costs no copy. Under the box there
is a second way, **Choose a video or a sound…**, for a file that is on
**another device** — a phone's recording, a laptop's film — or for a person
on Windows who has no path to type:

1. choose the file. Before anything is sent the page says what it is — its
   size, whether it is a sound or a video, and **how much room this computer's
   disk has** — and refuses in words what cannot be taken: *name the file with
   its extension*, *that file is empty*, *there is no room on this computer's
   disk for it: it needs 476 MB and 120 MB is free*;
2. press **Send it**. A bar and a line say how far it has got, how fast, and
   about how long is left (*Sending lesson.mp3: 38 % of 412 MB · 12 MB/s · about
   22 seconds left*); **Stop** ends it and nothing is kept;
3. when the last byte is in, the computer looks at the file — where ffmpeg is
   installed, a file that is not a video or a sound it can read is refused
   then — and **puts its path in the box**.
   From there it is a path like any other: the prompt, speech to text, *Start
   it empty*.

There is **no limit on the size** but the disk's. A file is written whole or
not at all — to a `.part` name nothing reads as media, and renamed only when
it is all there — and what you send and never use is cleared after two days
(it waits in `youtube/videos/.incoming/`, which is never listed, served or
bundled). Adding the video links the file into the video's folder and the
waiting copy goes.

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

## Or its transcript, made by speech to text {#speech-to-text}

A film with no subtitles can have its transcript **made on this computer**
if speech to text is set up ([Speech to
text](../lookup-and-languages/speech-to-text.md), in Settings; it is
optional, and a pasted transcript or a subtitle file needs none of it). With
the film's path in step 1, the block under the transcript box offers
**Transcribe**: [Adding a
video](adding-a-video.md#speech-to-text) says what it asks and does.

For a film it is the simple case:

- **nothing is played.** The computer opens the file and listens to it
  itself, so the film's format does not matter to your browser, and neither
  does the browser: **any browser on any device that has been let in will
  do**, a phone's included;
- **the path is a path on the computer's own disk.** When you are using the
  page from another device, name the file where the computer keeps it, not
  where you are;
- **the transcript goes into the box**, timed from the film's own start,
  ready to be corrected in [the editor](mending-the-transcript.md) — and
  the film is not added until you go on;
- the film is read where it is, never copied, and the audio is processed on
  this computer;
- **no waveform is written**: as always, a film's is drawn from the film
  itself when the timings sheet wants it.

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
so there is no field to keep true. (A sound is the one thing `video.json`
does say, `"kind": "audio"`, because a file's name does not always show
whether it has a picture.) What follows from there being no YouTube:

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
YouTube video's frame would be — for a sound, [the bar above](#a-sound-instead-of-a-film) —
and everything else — the lit line, **follow**, **hover ⏸**, a click to
replay, the clouds — works exactly the same. The film is served by Parseh
itself, a piece at a time, which is what lets it seek anywhere at once. On
a phone the bar fills the same place, held upright or sideways; a sound is
never put beside the text, because there is no picture to put there.

### When the film will not play {#when-the-film-will-not-play}

The place of the video says which of these went wrong, and the
transcript still works in every case:

| It says | Which means |
|---|---|
| *this browser cannot play that file* | a format the browser does not play (often `.mkv` or `.avi`): convert it, or open the page in another browser |
| *this browser cannot play that sound — a playable copy is made where ffmpeg is installed: add it again once it is* | a sound that was added without ffmpeg ([above](#a-sound-the-browser-cannot-play)) |
| *the film is there but will not decode* | the file is damaged, or only partly copied |
| *the film is not where this video says it is* | the film could not be fetched |
| *the film (or sound) that belongs to this video is not here any more — send it again, put it back beside the transcript, or add the video again* | the video's folder has no `media.…` file: it was moved or deleted. **send the film or sound again…** under it sends one to the same video, whole, and the page opens again on it (not on a phone: nothing there writes) |

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
there — a sound as a film does, as `media.mp3` (its playable copy where one
was made; the original stays here). An older Parseh that does not know the
sound types takes the bundle all the same, leaves the sound out and says
which file it left. Its tooltip says how big that zip is — *(about 1.9 GB)* — because a
browser starts a two-hour film's download without a word. For the words
alone there is no button: add `?media=text` to the download's address, as
the tooltip says. A book's download defaults
the other way, and the asymmetry is the point: a book without its recording
is still the book, while a video without its film is a transcript of
something nobody can watch. See
[Taking videos away and bringing them back](downloads-and-backups.md).
