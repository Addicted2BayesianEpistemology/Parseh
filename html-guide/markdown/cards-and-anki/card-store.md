---
title: The card store
weight: 1
description: Where Parseh keeps your Anki cards — one file each, filed by language — and why a card's identifier never changes.
---

The book reader and the video player write their Anki cards into one
place, the **card store**, in the folder `youtube/anki/` of your toolbox.
It is one collection whatever the card came from: a deck may hold cards
made from books and cards made from videos side by side, and each card
remembers which it was.

The store is yours, like your books and your videos: it is never part of
the repository, and nothing in Parseh moves or renames what is in it
behind your back.

## One card, one file

A deck is a folder, and **each card is one small JSON file** in it. That
file is the ground truth: the deck package you import into Anki is built
from the files, never the other way round.

```text
youtube/anki/
  persian/                              a language's folder
    persian-market/                     one deck: its slug
      deck.json                         its name, its language, its deck id
      cards/20260921-142212-63ef.json   one card per file
      media/                            the screenshots and recordings its cards show
      deleted/                          cards retired because you deleted them in Anki
  japanese/
    …
  notetypes.json                        what your note types look like in Anki
  seen.json                             every note Anki has ever shown the store
  inbox/                                the .apkg files dropped on the Sync with Anki page
  build/                                the packages the build writes
```

`deck.json` holds the deck's **name** — nested with `::` as in Anki
(`Persian::Market`) — its **language**, and a **deck id**.

**Anki knows a deck by its name.** Importing a package files its cards
into the deck that has the package's deck name, made if need be; the id
the package carries is not kept, and Anki gives a new deck an id of its
own. So what makes a rebuilt package land back in the deck you study,
instead of a twin beside it, is that the two still have the same name.

The id is for the sync, which looks for an exported deck by its id first
and by its name after that:

- A deck **made on the pages** gets an id of Parseh's own making when its
  first card is saved. Anki never uses it, so the sync always finds such
  a deck **by its name** — as long as no other deck in the store, of any
  language, has that name too ([below](#a-deck-belongs-to-a-language)).
- A deck **brought in from an Anki export**
  ([Bringing decks in](bringing-decks-in.md#a-deck-the-store-has-never-held))
  keeps the id Anki gave it, so the sync still finds it after you rename
  it inside Anki.

Either way the store keeps the name and the folder the deck was first
given, and every package it builds carries that name. So **do not rename
a deck in Anki alone**: see
[Renaming a deck](editing-in-anki.md#renaming-a-deck) for what happens,
and how to rename one safely.

The four entries directly under `anki/` belong to the whole collection,
not to a deck, because in Anki they are collection-wide too: a note type
is shared by every deck, and a note's identifier is unique across the
collection.

- `notetypes.json` — the styling and the card templates of your note
  types, learnt from your Anki exports ([Editing inside Anki](editing-in-anki.md#styling-and-templates)).
- `seen.json` — which notes Anki has confirmed it holds. This is how a
  card you deleted in Anki is told apart from a card Anki has simply not
  been given yet ([The round trip](round-trip.md#deletions)).
- `inbox/` — where an export you drop on the **Sync with Anki** page is
  saved.
- `build/` — where the packages go when a deck is built.

## A deck belongs to a language

A deck lives under its language's folder (`persian/`, `japanese/`,
`hindi/` — the folder names Parseh's language registry gives), as every
kind of content in the toolbox does. The store lets two languages hold a
deck of the same name: `persian/videos/` and `japanese/videos/` are two
folders, and their cards never mix here.

**In Anki they would.** Anki knows a deck by its name, so both packages
land in **one** Anki deck called *Videos*. The sync then cannot tell which
of the two store decks that Anki deck is, and it updates neither: it
reports the deck as one the store does not hold. (Do not take the page's
offer to bring it in: that would write a second file for every note.) So
give each language's decks names of their own. Nesting them under the
language is the easy way, and the one the card sheet suggests:
`Persian::Videos` and `Japanese::Videos`.

**A card goes to the deck of its own language.** The card sheet lists
the decks of the book's or the video's language first, under that
language's heading, and the decks of the other languages after them, each
under its own heading marked *(another language)*, so that an existing
deck is never hidden. You may pick one of those — but the card still
lands in the deck of **its own** language that has that name, made if
need be, and the sheet says so when the card is saved:

```text
saved ✓ — “Videos” (Japanese) now has 12 cards — filed under Japanese -- a Japanese card goes to the Japanese deck of that name
```

The card's language is what picks its note type when the deck is built,
so a card in the wrong language's deck would be built wrong; that is why
the store refiles it rather than obey. It is also how two decks of one
name come about, which Anki would merge (above): rather than pick another
language's deck, pick or make one of the card's own language.

A deck lying **directly under `anki/`**, the layout from before Parseh had
languages, still works everywhere — it is listed, built, synced and filled —
and is read as Persian, as everything written before languages were
declared is. Nothing moves it: move it yourself when you like.

## What a card file holds

You never need to open one, but it helps to know what is there.

| Key | What it is |
|---|---|
| `id` | the file's name: when the card was made and four random characters |
| `guid` | the note's identifier in Anki, made once and **never changed** (below) |
| `lang` | the card's language, a code of the registry (`fa`, `ja`, `hi`…) |
| `kind` | `vocab` or `opposites` — which of the two note types it uses |
| `fa` | the word in the target language, **whatever the language** (the key is named after Persian, the toolbox's first language) |
| `kana` | its reading, for a language that has one (Japanese) |
| `tr` | its transliteration |
| `en` | its meaning, in the language the book or video is glossed in |
| `context`, `notes` | the sentence it came from; the notes |
| `opp`, `opp_kana`, `opp_tr` | the opposite, on an opposites card |
| `bidirectional`, `reverse_only` | its direction ([Note types and directions](note-types.md#direction-which-cards-a-note-makes)) |
| `tags`, `source` | its tags, and the label and link back to where it was made |
| `img_front`, `img_back` | a screenshot on either side: a file in `media/` |
| `snd_front`, `snd_back` | a recording on either side: a file in `media/` |
| `video` or `book`, `time` | where it was made — kept for you, never sent to Anki |

A tag with spaces in it is saved with `_` in their place (Anki's tags are
separated by spaces), and a card keeps at most sixteen tags.

## Why a card's identifier matters

Every card carries a **guid**, made once when the card is saved and never
made again. Anki matches notes by it when a package is imported: import a
rebuilt deck, and Anki **updates** the notes it already has instead of
adding copies — their review history, their due dates and their ease all
stay as they were, and only the cards that are new arrive as new.

That is what makes the whole round trip possible, and also what makes it
fragile in two ways worth knowing:

> **Never edit a card's `guid`, and never copy a card file to make a
> similar card.** Two files with one guid are one note the store cannot
> reason about. Make the second card from the page instead.

> **Deleting a card's file does not delete the note in Anki.** It only
> leaves the card out of future builds; an import never deletes a note.
> Delete the note in Anki and let the next sync retire the file
> ([Deletions](round-trip.md#deletions)).

## What the store can refuse

The card sheet checks a card before it sends it (see
[Making a card](making-a-card.md#saving-it)); the store checks it again,
and nothing is written when it says no. What you may meet on the sheet:

| It says | Why, and what to do |
|---|---|
| the recording … is no longer in the clip tray | the clip was deleted from the tray (on the tray's page, or from a studio document's **Recordings…**) between the cut and the save: cut it again |
| the recording could not be copied: … | the clip could not be copied into the deck's `media/` (a full disk, a folder you may not write): the reason follows the colon |
| screenshot too large | a captured frame over 8 MB |
