---
title: Building a deck
weight: 9
description: The build .apkg button, what the package holds, importing it into Anki, and why you sync before you build once you edit in Anki.
---

## The button

**build .apkg**, at the foot of the card sheet when it sends cards to
**Anki**, builds the deck picked in the sheet's **deck** row and downloads
it as a package Anki imports: `persian-persian-market.apkg`. While it is
built and sent, the page's **Working…** indicator says *Building the Anki
deck…* (and the hub's list of work in progress names the deck); the
sheet says *building — import the downloaded .apkg into Anki*.

With **+ new deck…** picked there is nothing to build yet: *save a card
first — the deck does not exist yet*.

Then, in Anki: **File → Import…** and the file you just downloaded.

The package is named after the deck's language folder and its slug —
`<folder>-<slug>.apkg` — so a deck whose own name starts with its language
says it twice. That is on purpose: the store lets two languages hold decks
of the same name, and their packages must never overwrite each other
(inside Anki, though, such decks become one: give them names of their
own, [The card store](card-store.md#a-deck-belongs-to-a-language) says
why). The build also keeps a copy in the store's `build/` folder.

> **Before you build, ask yourself whether you have edited anything in
> Anki since your last import.** If you have, **sync first**
> ([The round trip with Anki](round-trip.md)) — otherwise the import will
> overwrite those edits. That is what the video sheet's **⇆ synced
> lately?** link beside the button is for: it opens the **Sync with Anki**
> page, at exactly the moment the question matters.

## What happens on import

Every card carries its fixed identifier (its guid), so Anki knows each
note it has seen before:

- **A note Anki already has is updated in place** from the card's file.
  Its review history, its due date and its ease are kept: studying is
  never disturbed by a re-import.
- **A new card arrives as new.**
- **A card whose file is gone** is simply not in the package, and Anki
  keeps the note: an import never deletes a note. Delete it in Anki
  instead ([Deletions](round-trip.md#deletions)).
- **The deck is found by its name.** Anki files the new cards into the
  deck that has the package's deck name — the deck you study, as long as
  it still has the name the store gave it. A note Anki already has stays
  in whatever deck it is in. Rename a deck inside Anki alone, and the next
  import makes a twin under the old name for the new cards
  ([Renaming a deck](editing-in-anki.md#renaming-a-deck)).

The flip side of the first point: the import makes Anki adopt each note
**as the store has it**. Anything you changed in Anki and did not bring
home first is overwritten — which is why the sync comes first once you
edit in Anki.

## What is in the package

| Part | What goes in |
|---|---|
| the notes | one per card file in the deck's `cards/`, with its tags; the cards each note makes follow its direction |
| the note types | only the ones the deck's cards use — the vocabulary and opposites types of their language ([Note types and directions](note-types.md)) — styled as your Anki collection styles them once a sync has learnt it |
| the media | every screenshot and recording a card names, and the language's web font when Parseh ships one (Vazirmatn for Persian, Noto Naskh Arabic for Arabic, Noto Serif Devanagari for Hindi) |
| the deck | its name, nested with `::` — the name Anki files the cards under — and the id in its `deck.json`, which Anki does not keep |

Some cards are left out on purpose:

- **Cards Anki owns** — notes you took over inside Anki by changing their
  note type, or by giving them formatting the store cannot hold — are
  never in a package, so an import can never fight your own version of
  them ([Editing inside Anki](editing-in-anki.md#the-mental-model-who-owns-what)).
- **A picture or a recording whose file has gone** from `media/` is
  dropped from its card quietly; the rest of the card is built.

The package is also **stamped** as built by Parseh. The stamp never
reaches your collection (Anki does not import it), but it lets the
**Sync with Anki** page recognise the file if you ever drop it there by
mistake ([Bringing decks in](bringing-decks-in.md#a-package-built-by-parseh)).

## When the build refuses

A build that cannot be made downloads nothing: the browser leaves the page
for the build's answer instead, one line of text of the form
`{"ok": false, "error": "…"}` naming the reason. Your browser's **Back**
button brings you back to the page.

| The answer says | Why, and what to do |
|---|---|
| deck '…' has no exportable cards | every card of the deck is owned by Anki (or it has none): there is nothing to build, and nothing to import |
| the note type '…' in your Anki collection has fields […], but this exporter writes […] -- building would fork a second note type and orphan your review history | a field was added to or removed from a note type inside Anki ([Adding or removing a field](editing-in-anki.md#adding-or-removing-a-field)) |
| the note type '…' in your Anki collection has 3 card templates; this exporter writes 2 | a card template was added or removed inside Anki: the same |
| 2 decks are called '…' -- say which language: … | only an old bookmark to `/anki/build/<slug>.apkg` meets this; the sheet's button always names the language |
| no deck '…' here | the deck the sheet names is not in the store any more: its folder was moved or deleted by hand after the page listed it (or an old bookmark names a deck that is gone). Reload the page and pick the deck again |

The two shape refusals are deliberate and they protect you: a note's
values are written by position, and Anki recognises a note type by its id,
so a package whose note type disagreed with your collection would either
scramble every note or make Anki fork a second note type beside the
first, orphaning the reviews of everything already studied.

{{< details summary="For the command line" >}}
The button runs the same build as this, from the `youtube/` folder:

```bash
python3 lib/anki_export.py anki/persian/persian-market
# -> anki/build/persian-persian-market.apkg
```

A second argument writes the package somewhere else. The server answers
the same build at `/anki/build/<folder>/<slug>.apkg`.
{{< /details >}}
