---
title: Pictograms (ARASAAC)
linkTitle: Pictograms
weight: 12
description: Settings → Pictograms (ARASAAC) (/settings/arasaac/) — some fourteen thousand pictograms and the words that name them, fetched once from ARASAAC and kept on this computer for the studio's exercises; whose pictures they are and what their licence asks of you (a credit, nothing sold, the same licence for what you share), what each choice costs, who may fetch them, and where the files are.
---

ARASAAC — the Aragonese Portal of Augmentative and Alternative Communication,
a brand of the Government of Aragón, in Spain — publishes some fourteen
thousand **pictograms**: small drawings of a house, of *to eat*, of
*nervous*, each with the words that name it in some forty languages. Parseh
can keep them on this computer, so that an exercise can carry a picture of
what it is about.

They are for the studio's exercises: a picture to put beside a word, on a
card or in a question. This page is where they are fetched, kept and taken
away; nothing else in Parseh needs them, and nothing breaks without them.

It is **optional** in every sense. Until you press a button on its page
nothing is fetched, Parseh's own installation is exactly the size it was, and
no page of Parseh asks for a pictogram. Nothing you write is sent anywhere:
the page asks two of ARASAAC's own hosts for ARASAAC's own files, and tells
them nothing of yours.

## Getting there

| From | What you press |
|---|---|
| Settings | the door **Pictograms (ARASAAC)**, beside **Reading help**, **Network**, **Updating Parseh**, **LaTeX drawings**, **Speech to text** and **Your prompts** |
| The address bar | `/settings/arasaac/` on the server |

On a phone the page opens with the phone's own bar, like its sibling Settings
pages, and does everything the computer's does.

## Whose pictures these are

The pictograms are ARASAAC's. They were drawn by **Sergio Palao** for ARASAAC
and are the property of the **Government of Aragón**, which shares them under
the **Creative Commons licence BY-NC-SA 4.0** — *attribution*,
*non-commercial*, *share-alike*. Parseh does not own them and cannot give
them another licence; it fetches them for you, and says what the licence asks
of you before you press the button. What it asks is ARASAAC's own, in the
words of its [terms of use](https://arasaac.org/terms-of-use):

- **Name them.** The author (Sergio Palao), the owner (the Government of
  Aragón), their origin (ARASAAC) and the licence (BY-NC-SA) must be cited,
  in one of the two forms the terms give: *The pictographic symbols used are
  the property of the Government of Aragón and have been created by Sergio
  Palao for ARASAAC (http://www.arasaac.org), that distributes them under
  Creative Commons License BY-NC-SA.* or *Pictograms author: Sergio Palao.
  Origin: ARASAAC (http://www.arasaac.org). License: CC (BY-NC-SA). Owner:
  Government of Aragon (Spain).*
- **Not for sale.** *The use of these resources within any product or
  publication for commercial purposes is excluded.* The licence's own
  definition of non-commercial is *not primarily intended for or directed
  towards commercial advantage or monetary compensation*: a document you
  study from, print for your own class or give to a friend is on the right
  side of it; a book you sell is not. Where money is involved in some other
  way, read the licence, or write to ARASAAC: Parseh cannot tell you where
  the line is for you.
- **Shared on the same terms.** *Any work derived from the resources … must
  be distributed with the same Creative Commons License BY-NC-SA.* So a
  document that holds pictograms goes to others — a friend, a class, a
  website — under BY-NC-SA, credit and all. What is yours in it stays yours;
  it can only be passed on on those terms.
- **The logo.** ARASAAC asks for its logo on signs, posters and plates that
  use the pictograms to mark public areas, services and shops. A page for
  studying a language is none of those.

Parseh enforces none of this and could not: the licence does. What it does is
say it here, before anything is fetched; write the credit, word for word,
into `arasaac/LICENSE-ARASAAC.txt` when a download ends; and list the
pictograms on the [Licences](../reference/licences.md) page.

## What is fetched, and from where

Two hosts, and nothing else — no account, no key, and nothing of yours sent:

- **`api.arasaac.org`** gives the **word lists**: for each language you tick,
  one list of every pictogram with the words that name it in that language.
  A list comes as 5 to 8 MB of JSON, of which Parseh keeps only a part: the
  words, and a few facts about each pictogram.
- **`static.arasaac.org`** gives the **pictures**: one PNG for each of the
  13,829 pictograms, at 300 or at 500 pixels.

What it costs was **measured on the real hosts on 2 October 2026**, and the
page says it before you press a button:

| What | Costs |
|---|---|
| The pictures at **300 pixels** | about **159 MB**: 11 kB on average, 13,829 of them |
| The pictures at **500 pixels** | about **321 MB**: 23 kB on average |
| A language's words | 5 to 8 MB to fetch (English 7.6 MB, Spanish 8.2, French 6.8, Persian 6.7, Italian and German 6.4, Chinese 5.8, Arabic 5.7, Turkish 5.2) |
| The time | about **twelve minutes** for the whole set, one picture at a time |

The pictures come **one at a time, on one connection kept open, with a short
pause between two**, and each request carries only Parseh's name and
version. A host that says it is busy is waited out for as long as it asks (two
minutes at most), and a wait that grows after any other error. ARASAAC's terms say nothing about how many
files may be fetched at once, so Parseh asks for as few things as it can: once,
politely, and again only for what has changed.

## The page, from the top

- **Whose pictures these are.** What is above, in a box that is always
  there: the credit in ARASAAC's words, what it asks of you, and links to
  the terms and the licence.
- **Languages.** One line for each language Parseh teaches, in its own
  script: how many words ARASAAC has in it, how many of the 13,829 pictograms
  those words name, and what its list costs. **English** is ticked to begin
  with: a picture is found by a word, and English names every one of the
  13,829 pictograms. Tick the languages your documents are written in as well,
  if you like.
  **Japanese** is not offered, and the line says why: ARASAAC has no words in
  it. **Hindi** is not either: its list holds one word, and that one is
  Spanish. **Turkish** is offered, and its line says honestly that its words
  name 2,656 of the 13,829.
- **Size of the pictures.** **300 pixels**, the one to start with, or **500
  pixels**, sharper on a large page, at twice the cost. All the pictures are
  of one size: changing it fetches them all again.
- **What it costs.** A line under the choices, which follows every tick and
  every size: how much will come, how long it takes, how much it keeps, and —
  where the disk has not the room — that it will not start.
- **One button, saying what it does.** **Get it** the first time; **Carry
  on** after a stop or an error; **Add the language ticked** when
  something is installed and you tick another; **Fetch again at 500
  pixels…** when you change the size, which asks first, since it replaces
  every picture.
- **Update**, beside it once everything is here. It asks ARASAAC which
  pictograms are new, changed or withdrawn since, and fetches only those: a
  picture that is here is asked for again with *If-Modified-Since*, and the
  server says *unchanged* for the many whose record changed without the
  picture changing. A pictogram ARASAAC no longer lists is let go.
- **Remove…**, which asks first. On a language's line it takes away that
  language's words and leaves the pictures; below, it takes away everything.

While it runs the page shows a **bar** — the word list in megabytes, then the
pictures by number — with the time left, and **Stop**; the choices are shut.
The same job is on the **Working** list on every page of Parseh. **Stopping is
not failing**: what came is kept, the page says so, and the button says
**Carry on**. A download that was cut by a dropped line, a closed laptop or a
Parseh that was stopped carries on the same way, and **no picture is fetched
twice**.

## Who may use it

**Any device that has been let in** may get, update, stop and remove anything
on this page: the computer, a phone on the Wi-Fi, another computer. The
door's pill says *any device let in*, and there is no lock line and no dead
button anywhere on it.

It is safe to leave open because **nothing a device sends becomes anything
that is fetched.** A language is one of the forty names ARASAAC's own API
lists, a size is one of two numbers, and a pictogram is an integer out of
the list ARASAAC gave; each picture is checked to be a whole PNG before it
is put in place. Whoever presses the button gets the same files, from the
same two hosts. Removing is refused while a download is running.

## Where the files are

`arasaac/`, beside `dict/`, `mt/` and `stt/`. It is kept by every
[update](../getting-started/updating.md), is left out of
[backups](../getting-started/backups.md) (it is somebody else's work, and
fetched again by a button), and git ignores it. Once it is here, everything
works with no connection.

| Path | What it is |
|---|---|
| `arasaac/pictograms/<number>.png` | The pictures, all at the one size the manifest says. A file is there only when it is whole. |
| `arasaac/index.<language>.json` | One language's words: the keywords of each pictogram, with their plurals and meanings. |
| `arasaac/pictograms.json` | One record per pictogram: when ARASAAC last changed it, its flags (line-drawn, skin and hair that can change colour, *violence*, *sex*) and its WordNet numbers. A record marked as still to be fetched is how a stopped download knows where it stopped. |
| `arasaac/manifest.json` | Which size, which languages, when, and whether it is whole. |
| `arasaac/LICENSE-ARASAAC.txt` | The credit and the licence, written when a download ends. |

If you share a document that holds pictograms, give the credit with it:
`LICENSE-ARASAAC.txt` has the text to use.

## If something goes wrong

- **You stopped it.** The page says so, and says what is kept. **Carry on.**
- **ARASAAC's host did not answer, or said it was busy.** Parseh waits and
  tries again, four times; then it stops and says so in a sentence, with what
  came kept. **Try again** carries on from there.
- **There is not enough room.** It does not start, and says how much it needs
  and how much is free. Make room, or choose fewer languages or the smaller
  pictures.
- **A folder made by another Parseh.** If `arasaac/` holds a manifest of a
  shape this Parseh does not know, the page says so: **Get it** makes it again,
  **Remove…** takes it away.
- **ARASAAC has no picture of some pictograms at this size.** The page says
  how many, once it is done. They are looked for again when ARASAAC changes
  their record.
