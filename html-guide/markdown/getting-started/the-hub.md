---
title: The hub
weight: 5
description: Parseh's first page — its top bar, the language chips, the doors and what their counts say, and the three themes of the ◐ button.
---

The hub is the page at the root of Parseh's address, `https://localhost:7654/`,
and the one the home link in the top-left corner of Parseh's pages leads
back to — a **پ**, the first letter of the toolbox's Persian name, on most
of them. It shows what there is and lets you pick where to go.

![The hub in the browser interface: three books, a video, four studio documents and a deck of exercises](shots/hub.png){width=100 align=center}

It is made afresh each time you open it, so its counts are always today's:
come back to it, or reload it, after adding something.

## The top bar

From the left:

| In the bar | What it is |
|---|---|
| **پ Parseh** | this page |
| *the hub* | where you are |
| **Browser** **Mobile** | the two interfaces: which one Parseh is in, and the switch between them ([Browser and Mobile](mobile-mode.md)) |
| **guide** | this guide ([This guide](this-guide.md)) |
| **◐** | the theme, below |
| **⏻ stop** | stops the server, after asking ([Starting and stopping](starting-and-stopping.md#stopping-it)) |

On a phone the bar sheds words to stay on one row — *the hub* and the
*stop* after ⏻ go first, then the name beside پ — and keeps every button. A
screen reader still hears *Parseh* and *stop*; *the hub* is dropped
altogether, since the name under the bar says it.

## The language chips

Under the name, one chip for each language you have something in — its
name in its own script, فارسی, 日本語, italiano, with how many books,
videos, documents and decks it has — and **all** for everything.

Picking a chip does two things:

- The doors' counts follow it: with فارسی picked, the Books door says
  how many Persian books there are, the Videos door how many Persian
  videos, and so on — 0 for a door with nothing in Persian;
- It is remembered, by this browser, for the whole toolbox: the books,
  the videos, the studio's library and the exercise decks each have the
  same row of chips, and they open showing the language you picked last,
  whichever page you picked it on.

A language only has a chip on a page while there is something of it
there. A page with nothing in the language you picked — the video index,
when all your videos are in other languages — shows everything, and the
choice goes back to **all**.

## The doors

Four large doors, one for each part of the toolbox, each with its name in
Persian above it — the toolbox's own language, whatever you are learning:

| Door | Leads to | What its count says |
|---|---|---|
| **Books** | the library of reading editions, `/books/` | how many books |
| **Videos** | the index of videos, `/youtube/` | how many videos, and how many channels they come from |
| **Studio** | the studio's library of documents, `/studio/` | how many documents |
| **Exercises** | the exercise decks, `/exercises/` | how many decks, and how many exercises are due today |

and four wide ones under them, for the work around the four:

| Door | Leads to | What it says |
|---|---|---|
| **⇆ Anki** | the card store and its sync with Anki, `/anki/sync/` | how many cards and decks the store holds — one store for every language |
| **✂ The clip tray** | the recordings and pictures cut for cards, `/clips/` | how many clips wait there, or *the tray is empty* |
| **🔍 Reading what nobody has glossed** | the dictionaries and the rest, in Settings, `/settings/reading-help/` | how many languages have a dictionary, and which, or *no dictionary yet* |
| **⚙ Settings** | what this Parseh is set to, `/settings/`: which version it is, **Reading help**, **Network** and **Updating Parseh** ([Updating Parseh](updating.md)) | who may reach it — this computer, a VPN, the Wi-Fi ([From a phone or another computer](other-devices.md)) |

A door that says 0, or *no dictionary yet*, is doing its job: it tells you
there is something there you have not started using.

## The foot

At the bottom of the hub:

- **Reachable at**, and every address the server can be reached at — the
  ones to type on a phone — followed by who may reach it and a link that
  changes that ([From a phone or another computer](other-devices.md));
- a reminder that every browser warns once about the certificate, which is
  Parseh's own;
- that the **⏻ stop** button stops the server, that a book is built from
  its card on the books' library page and a video added from the video
  index — and that **the guide** has the rest;
- which version of Parseh this is, and that it is free software, with a
  link to its **licences** ([Licences and credits](../reference/licences.md)).
  The mobile hub says the same in two lines at its very foot, the version
  on the second. [What's new](../reference/whats-new.md) says what each
  version brought.

## The theme

The **◐** button, at the top of the hub and of most pages, changes the
colours of the whole toolbox. Each click goes on to the next of three
palettes:

| Palette | The button shows | What it is |
|---|---|---|
| light | ○ | dark ink on a pale ground |
| dark | ● | pale ink on a dark ground |
| sepia | ◐ | the warm paper the studio has always read on |

Until you first click it, Parseh follows the computer's own setting —
light or dark — and the button's tooltip says *following the system*. From
the first click the choice is yours, and it holds everywhere: every page
with the button — the books and their reader, the videos and their player,
the Anki page, the clip tray, the dictionaries' page —, the studio's and
the exercises' pages, which have no button of their own and follow it, and
this guide when Parseh serves it. Like the language, it is remembered by
each browser for itself.

**The studio has a theme of its own, for when you want one.** A document's
**Aa** settings have a theme too — **Paper**, **Sepia** or **Dark** — and
until you pick one there, it simply follows ◐. Once you do, the choice is
not that document's alone: the whole studio — every document, the
library, the prompt page — and the exercise decks keep that theme from
then on, and ◐ goes on changing only the rest of the toolbox. **Reset**,
in the same settings, puts back Paper, not ◐.

The **Working…** panel appears at the top of the hub, above its name,
whenever the server is busy — [The Working… indicator](working-indicator.md)
says what it shows.
