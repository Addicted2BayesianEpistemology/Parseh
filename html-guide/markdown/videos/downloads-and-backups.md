---
title: Taking videos away and bringing them back
linkTitle: Downloads and backups
weight: 13
description: A video's ⤓ bundle and its size, bringing one back with its refusals, the backup of the whole shelf, and the trash.
---

A video is a folder of files, and every page that writes one writes those
files. So a video can be taken away whole — to work on it elsewhere, to
hand it to somebody, to keep a copy — and brought back, by three doors:
one video out, one video in, and the whole shelf at once.

## One video out: ⤓

The **⤓** in the player's bar downloads the video as **one zip that another
Parseh can install whole**. It holds a folder named after the video's id:

| The zip carries | |
|---|---|
| `video.json` | the title, the channel, the language… |
| `annotations.json` | every phrase and its gloss |
| `transcript.txt` | the transcript it was checked against |
| `parts/*.json` | the answer an LLM gave, on a video added before `parts/` was [retired](the-files.md#parts) |
| `markdown/**` | the [notes](notes-in-the-seam.md), with their pictures and recordings (an `.svg` figure excepted: it stays on the machine it was drawn on) |
| `waveform.json` | the picture of the sound, [where one was drawn](the-timings.md#the-picture-of-the-sound) |
| `media.<ext>` | the film, for [a film on this machine](a-film-on-this-machine.md) |

and at its root `parseh-bundle.json`, a small manifest saying what the zip
is: a video bundle, its language, the language its glosses are written in,
its id, and — for a film — whether the film is inside. It is what makes the
zip something a toolbox can reason about instead of guess at.

**The name** says what it is: `<id>-video.zip` for a YouTube video,
`<id>-video-full.zip` for a film with its film, `<id>-video-text.zip` for a
film's words alone.

**A film goes with its glosses by default** — the film is stored in the zip
as it is, not compressed again — because a video without its film is a
transcript of something the person who unpacks it cannot watch. For the
words alone, add `?media=text` to the download's address (the ⤓'s tooltip
says so; there is no button for it).

**The size** is in the ⤓'s tooltip when the zip carries a film — *download
this video as a bundle: the film itself and its glosses in one zip (about
1.9 GB), which another Parseh installs whole* — worked out from exactly the
files the zip will carry, as they will sit in it. A browser starts a
two-hour film's download without a word, so the figure is there before you
click. A YouTube video's zip is a few kilobytes and its tooltip gives no
size.

The zip is packed before the browser is told anything, so a large one takes
a moment to start. Meanwhile the **Working** pill says so on this page —
*Preparing the download…*, then *Packing the video … to download* — and the
hub lists it too; the file then appears in your browser's downloads.

**A waveform is carried whatever else is asked for.** It is derived — and
every other derived thing is left to be made again — but this one is made by
sitting through the whole video in real time, from a source no zip can
carry, so making it again on the next machine is an hour nobody should
spend twice.

## One video in: Bring a video back

At the foot of the videos page, **⇩ Bring a video back** takes such a zip
back: press **Choose the zip — or drop it here**, or drop the file on the
panel. The zip is unpacked into a hidden staging folder beside where it is
going, every check runs **there**, and the video's folder is not touched
until the staged copy has passed. Nothing that fails leaves anything
behind. A bundle of any size comes back — a large one is written to disk
as it arrives, never held in memory — and the **Working** pill shows it
going up.

A successful install says what went in — *dar-mive-forushi-a1b2c3 is in,
at youtube/videos/persian/dar-mive-forushi-a1b2c3 — a Persian video, 7
files, 339 kB.* — lists what is worth a second look (*6 captions, 12
chunks, 23 words -- Persian, glossed in English*, and any warning of the
checker's), and offers **Open the player →** and **reload the list**. The
player reads the new files at once.

What it refuses, and what each refusal means:

| It says | Which means |
|---|---|
| *that is not a Parseh bundle: it carries no parseh-bundle.json. The download button makes one; a zip of a folder is not one.* | zip it again from a bundle ⤓ gave you, keeping the manifest at the root |
| *that is a book bundle; this is where a video goes* | dropped on the wrong page: a book goes back through the books' library |
| *this bundle carries '…', which is not a path inside it -- refused whole, and nothing was unpacked* | an entry that would land outside the video's folder |
| *video.json language 'xx' is not a registry code (known: fa, ar, …)* | a language this toolbox has not got |
| *parseh-bundle.json says the language is fr and video.json says en -- they must agree* | the manifest is checked against the files, not believed |
| *check_annotations refuses this video (2 error(s)): …* | the video's own checker, in its own words — a hand-edited file, most often. A phrase **half** glossed is not one of the reasons: the video is taken in, and the answer carries a note (*2 chunks half glossed -- kept, not refused: finish them in the player*). A phrase with nothing written in it is legal anywhere |
| *… is already in the toolbox at youtube/videos/japanese/…, filed as Japanese, and this bundle is Chinese: it would go to … and leave the toolbox holding that name twice …* | the same id under another language: replacing cannot cross the two — move, rename or delete the one there first, as the sentence says |
| *… is already in the toolbox, at youtube/videos/persian/…. Ticking replace overwrites its authored files with this bundle's.* | the one refusal with a way forward: the panel offers **replace** and **leave it** |

**replace** makes the video the bundle's: its annotations, its transcript,
its parts and its notes are the bundle's afterwards — even the ones the
bundle does not carry, so a bundle made before a note was written takes
that note away. Two things of the old video are kept when the bundle has
none of its own, because they are the two that cannot be made again
cheaply: **the film** (a bundle of the words alone installs without
touching it) and **the drawn waveform**. Each is given up only to another
film, or another waveform.

## The whole shelf

Below it, **⇩ The whole shelf**:

- **Backup every video** downloads one zip, `videos-backup-<date>-<time>.zip`,
  holding **one bundle per video** — the very zips ⤓ makes, each with its
  film where it has one — so any video can be taken out of it and brought
  back on its own through the panel above. A video that cannot be packed is
  named in the backup's own manifest and the rest go in anyway: one broken
  video is no reason to have no backup of the other forty. The **Working**
  pill says *Packing the backup…* while it is made.
- **Load from backup** takes such a zip back, video by video, each through
  the same door and the same checks as above (*…this can take a while*). A
  video already on the shelf is **kept**, and the answer names them:
  **Replace them** sends the backup again and overwrites them — losing
  anything written since the backup was made — and **Keep mine** leaves
  them as they are. It ends with how many videos were put back, and a link
  to reload the page.

## Off the shelf, and the trash

The **✕** on a video's card moves the whole folder to
`youtube/videos/.trash/`, never deleting it
([The video index](finding-a-video.md#taking-a-video-off-the-shelf)); so
does a video replaced from the add page. Replacing through **Bring a video
back** does not use the trash: the old files the bundle carries are
overwritten, which is what **replace** says it does.

> **For the command line.** `python3 lib/bundle.py` packs, inspects and
> installs a bundle, with the same rules as the two panels.
