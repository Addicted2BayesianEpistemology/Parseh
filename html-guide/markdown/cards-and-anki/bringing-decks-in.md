---
title: Bringing decks in
weight: 11
description: A deck the store has never held, a package built by another copy of Parseh, and the two things the sync refuses.
---

The sync updates decks the store already holds. Two other roads bring a
deck **into** the store, both from the same **Sync with Anki** page: a
deck that lives only in Anki, and a package built by Parseh — yours from
another computer, or someone else's.

## A deck the store has never held

Once a deck is imported into Anki and lived in, the live copy is the one
inside Anki: renamed perhaps, reorganised, reviewed for months. If the
store is ever lost or reset — a fresh copy of the toolbox, a new computer —
while Anki still has the deck, bring it back from an Anki export.

Export it from Anki as for a sync, drop it on the page, and press
**Preview the changes**. A deck of the export the store does not hold is
named in the report — *Persian CI::Old flashcards is not in the store yet
(312 notes). Syncing only updates decks the store already holds.* — with
a button of its own, **Bring this deck in for the first time**, which
names that one deck and no other. When several are new at once (a fresh
copy meeting a whole collection) **Bring all 4 decks in (1210 notes)**
brings them together.

What it does:

- **Every note of one of Parseh's note types** — any language's pair —
  becomes a card file under `anki/<language>/<slug>/cards/`, keeping the
  note's **guid exactly** and the deck's **name and Anki id exactly**, all
  taken straight from the export. The guid is what lets the next build
  update the very same notes instead of making copies; the name is what
  lets it land in the very same deck, since Anki files a package's cards
  by the deck's name. The id lets the sync recognise the deck even after
  you rename it in Anki — though its packages go on carrying the name it
  came in with, so rename it in both places all the same
  ([Renaming a deck](editing-in-anki.md#renaming-a-deck)).
- The deck is filed under the language of the note type most of its notes
  use; each card keeps its own language.
- **Every picture and recording** a card names is copied out of the
  export into the deck's `media/`, the recordings read back out of the
  `[sound:]` in its picture fields.
- A card sitting in a **filtered deck** is filed under its home deck.
- **A note carrying formatting the store cannot hold** (HTML typed inside
  Anki) comes in as an Anki-owned mirror, exactly as the sync would treat
  it, so a rebuild never flattens it.
- **A note of any other type** (a stock *Basic* card, say) is left out:
  guessing at an unfamiliar layout would write nonsense. Bring those over
  by hand.

While it works, the **Working…** indicator says *Bringing decks in from
the Anki export*. The button then says what came in — *Brought in:
Persian CI::Old flashcards (312 cards). 48 images or recordings copied.*
— names any
picture or recording the export did not carry (export again with
**Include media** ticked), counts the notes kept in Anki for their
formatting, and ends *Preview again to sync it from now on.* The styling of
your note types is learnt at the same time, as a sync learns it.

Every shape of export is read: Anki's newest compressed one, Anki 2.1's,
and the oldest.

## A package built by Parseh

The `.apkg` the build button makes is the only thing that has to travel
between two copies of Parseh: its notes carry the right note types and
fields, its pictures and recordings ride along, and the deck's name and
id are inside. Drop it on the **Sync with Anki** page like any export,
from your other computer or from someone who made the cards with Parseh.

Every package Parseh builds is **stamped**, and the page recognises the
stamp at **Preview the changes**:

*A package built by Parseh (deck persian-market), not an export from
Anki. It says nothing about what Anki holds, so there is nothing to sync —
but it can be brought in:*

| The deck in it | What the page offers |
|---|---|
| not in the store yet | **Bring this deck in** — the deck is made under the package's own deck id and name, with every card and every picture and recording (**Bring all 3 decks in (…)** for several) |
| already in the store | **Add the 5 new cards** — only the cards it lacks, matched by guid, so nothing of yours is overwritten; or *nothing in it is new here* |
| none of Parseh's cards | *No cards of this toolbox's note types in it.* |

Steps 4 and 5 stay shut — there is nothing to apply — until the deck is
brought in: then step 5 opens with its download. **Build it, import that
into Anki**, and from then on export from Anki and sync as usual.

Its cards are filed as `pkg-<guid>.json`. Unlike `apkg-<guid>.json`, that
name is **not** taken as Anki's word that the note exists — the package
came from Parseh, not from your Anki — so if a later genuine export lacks
some of them, they read as *Here, not in Anki yet*, never as deleted.

## Two things the sync refuses

Both would teach the store something false about your collection, so the
page stops rather than guess.

**The `.apkg` Parseh built.** It is a perfectly good package, sitting in
the same downloads folder as a real export — it is the very file step 5
gives you. Synced, it would mark every card in it as confirmed by Anki,
including cards no import has ever carried; the next genuine export,
lacking them, would then look like a mass deletion. So the stamp stops the
sync and offers to bring the package in instead, as above.

**Bringing in a deck the store already holds.** That would write a second
file for every note. The page offers to bring a deck in only when the
sync could not match it, and the bootstrap itself leaves alone a deck
whose id the store already holds, across the whole store; that deck's
notes come home through the sync.

What the bootstrap cannot see is a deck the store holds **under another
id**. A deck brought in from an Anki export has Anki's id, so it is
recognised even after a rename in Anki. A deck made on the pages has an id
of Parseh's own that Anki never kept, so it is recognised by its name
alone: rename it in Anki only, or let Anki merge two languages' decks of
one name, and the page names it as a deck the store does not hold. Do not
bring it in then. Give a renamed deck back its name, or rename it in the
store too ([Renaming a deck](editing-in-anki.md#renaming-a-deck)); keep two
languages' decks apart by name
([A deck belongs to a language](card-store.md#a-deck-belongs-to-a-language)).

{{< details summary="For the command line" >}}
From the `youtube/` folder:

```bash
python3 lib/import_apkg.py "../Persian CI.apkg"          # decks the store does not hold yet
python3 lib/import_apkg.py "shared.apkg" --merge         # and the new cards of decks it holds
```

It prints what it brought in, the notes of other types it skipped, and a
deck it left alone because the store already holds it (*use
lib/sync_apkg.py*). `lib/sync_apkg.py` on a package Parseh built prints
the same offer the page makes, with the command to run.
{{< /details >}}
