---
title: Editing inside Anki
weight: 12
description: Which edits in Anki are always safe, the Reverse and ReverseOnly gates in practice, splitting a card's directions, and what hands a note to Anki for good.
---

Anki is a full editor, and it will happily let you do things the card
store cannot represent. None of them is forbidden — several are genuinely
useful — but each has a right way to do it, and the store is built to
notice and cope rather than to stop you. This is the page to reread.

## The mental model: who owns what

Think of every note as owned by one side or the other.

- **The store owns a note** while the note uses one of Parseh's note types
  — the pair of the card's language ([Note types and directions](note-types.md))
  — and says only what the store can hold: plain text in the fields, line
  breaks, the pictures and recordings it knows, its tags. These notes are
  rebuilt from the store every time, so a change made in Anki must be
  **synced home**, or the next import reverts it.
- **Anki owns a note** once you take it somewhere the store cannot follow:
  a different note type, or formatting the store cannot reproduce. The
  sync notices, keeps a mirror of the note for the record, and **leaves it
  out of every future package**. From then on the note lives in Anki alone,
  and nothing here can ever overwrite it.

That second state is not a failure. It is the way out: how you take a card
into your own hands, for good and safely. And it can be undone — put the
note back on a Parseh note type with plain fields, and the next sync
**reclaims** it.

## Edits that are always safe

Do these freely; just sync before you next build.

- Correcting or rewriting any field's text.
- Adding, removing or renaming tags.
- Filling or clearing `Reverse` and `ReverseOnly` (below).
- Adding a new note with one of Parseh's note types, the pair of its
  language: the sync adopts it into the store.
- Moving a note to another deck **the store holds**: the sync reports it
  as a move and updates it where its file lives. Export **All Decks** for
  that sync, so the export shows where the note went ([below](#moving-a-note-to-another-deck)).
- Restyling the cards, or editing their templates ([below](#styling-and-templates)).
- Deleting a note ([Deletions](round-trip.md#deletions)).
- Suspending, burying, flagging, rescheduling: Parseh never reads or
  writes scheduling at all.
- Replacing a picture or a sound in a field, or deleting its `[sound:]`.

Two edits that look just as harmless are **not** on this list: renaming a
deck, and moving a note into a deck the store does not hold. Each has its
own section below.

## Renaming a deck

Anki knows a deck by its **name**, and so does the store for a deck made
on the pages ([The card store](card-store.md#one-card-one-file) explains
the id it keeps as well). Rename such a deck in Anki alone and the link
between the two breaks:

- the next sync reports the renamed deck as **not in the store yet**, and
  updates nothing in it — do not take its offer to bring the deck in,
  which would write a second file for every note;
- the next build still carries the old name, so importing it makes a
  **twin deck** under the old name and files the new cards there, while
  the notes Anki already had stay in the renamed one.

A deck that came in from an Anki export is recognised by the sync after a
rename, by its id, but its packages carry the old name all the same: the
new cards land in a twin just the same.

The pages cannot rename a deck yet. To rename one safely, change its name
**in both places, the same way**:

1. In Anki, rename the deck.
2. In the store, open the deck's `deck.json` (in its folder under
   `youtube/anki/`) with any text editor, and write the same name after
   `"name":`, `::` and all. Change nothing else in it.
3. Reload the card sheet: the deck is listed under its new name. Export,
   sync and build as usual.

Renaming a parent deck in Anki renames every deck nested in it too —
*Persian* → *Farsi* turns `Persian::Market` into `Farsi::Market` — so each
of those needs its new name written in its own `deck.json`.

If a twin has already appeared, move its cards into the renamed deck in
Anki (**Change Deck** in the browser), delete the empty twin, and rename
in both places as above.

## Moving a note to another deck

A note moved inside Anki is found by its identifier wherever it goes — but
only in the decks the sync reads:

- **Into another deck the store holds**: the sync reports it under
  **Moved to another deck in Anki** and updates it in the store deck
  whose folder holds its file. Its card file does not move, and the next
  import leaves the note where you put it in Anki.
- **Into a deck the store does not hold** (a deck of your own, the parent
  of a nested deck): the note is neither synced nor deleted. Its edits in
  Anki are not brought home, so **the next rebuild overwrites them**; and
  bringing that deck in writes a second file for the same note. Move it
  back into a deck the store holds before you sync.
- **Export All Decks** after moving notes. An export of one deck does not
  carry a note moved out of it, and a note Anki has held before that is
  missing from the export reads as **Deleted inside Anki**
  ([Deletions](round-trip.md#deletions)): untick the box, or export again
  with *All Decks*.

## Reverse and ReverseOnly in practice

[Note types and directions](note-types.md#direction-which-cards-a-note-makes)
has the table; here is what to type. Both fields are **gates**: any text at
all turns one on. The card sheet writes a single `y`, but Anki's templates
only ask whether the field is empty, so `yes` works as well — and the sync
reads it the way Anki does.

| To | Do this |
|---|---|
| drop the reverse card | clear `Reverse`: the meaning → word card is no longer asked |
| drop the forward card | put `y` in `ReverseOnly`, **and make sure `Reverse` is set too** |
| have both again | `Reverse` set, `ReverseOnly` empty |

An opposites note has only `Reverse`.

> **A card you switch off is not deleted at once.** It becomes an **empty
> card**: Anki keeps it, with its review history, and no longer shows it.
> Set the gate again before you sweep, and the same card comes back with
> its history. Only **Tools → Empty Cards** ([below](#tools--empty-cards))
> deletes it, and its scheduling with it; setting the gate after that
> makes a *new* card, at day zero. So sweeping is cheap on a young card and
> costly on one you have studied for months.

## A worked example: one meaning, two words

تن *tan* and بدن *badan* both mean *body*. Asking *body* → Persian is fair
only if either word may be the answer; but asking تن → English and بدن →
English should each be a question of its own. That is three cards from
two words, and it is exactly what `ReverseOnly` is for:

| `Persian` | `Reverse` | `ReverseOnly` | The card it makes |
|---|---|---|---|
| تن | (empty) | (empty) | تن → body |
| بدن | (empty) | (empty) | بدن → body |
| تن / بدن, on two lines | `y` | `y` | body → تن / بدن |

The third note's forward card is switched off, so it never asks a question
the first two already ask better. Make it from the card sheet with
**← English → Persian only**, or in Anki by setting both gates by hand.

## Tools → Empty Cards

When a gate goes empty, the card it controlled becomes an **empty card**,
which Anki keeps until you sweep it up. **Tools → Empty Cards** finds them,
lists them, and deletes them when you say so.

- **Read the list before you confirm.** It is the honest answer to “what
  did my edit actually do?”. If it names more cards than you expected,
  something else changed too — a field you cleared, a template you edited.
- It is safe for the store: it removes **cards**, never notes, and the
  store does not keep scheduling. Your card files are untouched.
- You do not have to run it. An empty card is harmless clutter; the reason
  to sweep is to keep Anki's counts honest.

> There is no undo for the review history of a card deleted this way. When
> in doubt, leave the empty cards alone — they cost nothing — and decide
> later.

## Duplicating a note: Notes → Create Copy

This is the tool for *two cards that say different things*, when the gates
are not enough because the two directions need different **content**.

In Anki's browser (**B**), select the note, then **Notes → Create Copy**.
You now have two identical notes, each making whatever cards its fields
say — and the copy has **an identifier of its own**, so the two are
independent from that moment on.

Two ways to use it:

- **Staying with Parseh.** Edit each copy's fields and set its gates so
  that between them they ask what you want. Both remain ordinary notes of
  Parseh's type; the sync adopts the copy as a new card and manages both.
  This is the lighter way, and usually the right one.
- **Leaving Parseh behind.** When the two directions must differ entirely
  — different wording, formatting, layout — convert each copy with
  **Notes → Change Note Type** (below), mapping the fields so that each
  direction's content lands in its own *Front* and *Back*. After the next
  sync both are Anki's, and nothing here will ever touch or bring them
  back.

## Change Note Type, and being taken over

Converting a note to another note type — *Basic*, say — hands it to Anki
for good. The next sync reports it as **Taken over by Anki (note type
changed there)**: the store keeps a mirror of it (its guid, the note
type's name, its raw fields, where it was made) for the record only, marks
it as Anki's, and leaves it out of every package from then on. Since an
import never deletes a note, it simply stays in your collection,
untouched, for ever. That is the point.

> **To take a note back**, change it back to the vocabulary or opposites
> type **of its language** — **Frank YouTube Persian** or **Frank Persian
> Opposites** for a Persian card, **Frank Japanese** or **Frank Japanese
> Opposites** for a Japanese one, and so on — map the fields sensibly, and
> strip any formatting. The next sync **reclaims** it. The language's own
> pair matters: a Japanese word put on the Persian type would be filed as a
> Persian card, with no `Reading` field for its kana.

## Formatting: bold, colour, and why it is kept in Anki

The store holds plain text with line breaks. Make a field **bold** in Anki,
colour a word, or paste HTML into a field, and a rebuild could not
reproduce it: it would flatten it.

Rather than let that happen, the sync treats such a note like a takeover:
it reports it as **Kept in Anki (formatting the store cannot hold)** and
stops putting it in packages. Your formatting is safe in Anki, and no
rebuild can touch it. Would you rather have the note managed again, remove
the formatting inside Anki: the next sync reclaims it by itself. A new
field's worth of HTML, or a note with more fields than its type, counts
the same way.

## Styling and templates

The CSS your cards wear and the card templates belong to the **note
type**, not to any note — so no card file can hold them. They are learnt
instead, from your exports, into the store's `notetypes.json`, one entry
per note type, and every build and every **preview card** uses them in
place of the factory ones.

1. Change the styling or the templates in Anki (**Cards…** on any note of
   that type). A note type you rename in Anki keeps its new name too.
2. **Export and sync.** The report shows **Card appearance** for that note
   type, naming what changed — the styling, the templates — and the store
   learns it.
3. Every later build reproduces it, and the card sheet's **preview card**
   shows your styling rather than the factory one.

Styling is learnt per note type: restyling the opposites cards leaves the
vocabulary cards alone.

> **The export is the source of truth for the look too.** Restyle in Anki
> and then sync an export taken *before* that change, and the old look is
> what is learnt — and the next rebuild pushes it back. **Always export
> again after changing a note type.**

## Adding or removing a field

This is the one change that needs code, and it travels one way only:
**change it in Anki first, then export, then teach the exporter.**

Anki migrates its own collection safely when a note type gains a field;
Parseh cannot guess what the new field means or where its value comes
from. So the order is: add the field in Anki, export, and have the
exporter (`youtube/lib/anki_export.py`) taught the new shape. Until it is,
**the build refuses to run**, naming the difference
([When the build refuses](building-a-deck.md#when-the-build-refuses)).
The same holds for a card template added or removed.

That refusal protects you. A note's values are written by position, and
Anki recognises a note type by its id: a package whose note type disagreed
with your collection would either scramble every note or make Anki fork a
second note type beside the first, orphaning the reviews of everything
already studied. The `ReverseOnly` field travelled exactly this road.

## Things that will make a mess

1. **Building and importing without syncing first.** The likeliest way to
   lose work: everything you edited in Anki since the last import is
   reverted. When in doubt, run the page's **Preview the changes** — it
   writes nothing and tells you exactly what differs.
2. **Editing a card's `guid`, or copying a card file to make another
   card.** Two files with one guid are the one state the store cannot
   reason about. Make the new card from the page.
3. **Deleting a card file to get rid of a note.** It leaves future builds,
   but Anki still has the note, and the next export makes the store think
   you deleted it there. Delete it in Anki and let the sync retire it.
4. **Renaming a deck in Anki alone.** The store and the build go on using
   the old name: the sync stops updating a deck made on the pages, and the
   next import files the new cards of any deck in a twin under the old
   name. Rename in both places the same way
   ([Renaming a deck](#renaming-a-deck)). Renaming a deck's **folder**
   under `anki/` renames nothing, on the other hand: the name is the one
   in its `deck.json`, and only the package's file name changes.
5. **Moving a note into a deck the store does not hold**, or exporting a
   single deck after moving notes out of it. The first loses the note's
   Anki edits at the next rebuild; the second makes moved notes look
   deleted ([Moving a note to another deck](#moving-a-note-to-another-deck)).
