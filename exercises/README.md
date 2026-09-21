# exercises/

The decks of the Exercises door: studio exercises studied like Anki cards.
Everything here except this file is personal study state and is not
committed.

    <language folder>/<deck slug>/
        deck.json            name, language, the options you changed
        items/<id>.json      one exercise: its `:::exercise` markdown, tags,
                             footnotes, and the document, book or video it
                             was made from
        schedule/<id>.json   when it is due next, and every answer given
                             (no file: not studied yet)
        images/              flashcard pictures (a PDF has a .pdf.svg twin)
        audio/               recordings the exercises play
    .trash/                  deleted and replaced decks, never read again

An exercise brings its pictures and recordings with it: copied from a studio
document with **+ Deck**, uploaded from the exercise form, or taken from the
clip tray (`clips/`) when a card cut in a book or a video names them. It goes
back the same way: the studio editor's **Exercises ▾ → Load from a deck…**
copies one into a document, its files into that document's own `images/` and
`audio/`, and leaves the deck untouched.

A deck travels as a zip, not as a copied directory: **Export** on the deck's
page (with or without the scheduling) and **Import deck…** on the Exercises
page. The zip holds `parseh-exercise-deck.json` (format
`parseh-exercise-deck/1`), `items/`, the pictures and recordings the
exercises name under `images/` and `audio/` and, with scheduling,
`schedule/`. The store itself is `markdown/app/decks.py`.

## The whole shelf, out and back

**Backup** on the decks page gives every deck here as one zip; **Load from
backup** puts one back. It is not the per-deck **Export**, and the three
differences are the reasons it exists:

* `deck.json` travels whole, so the **id** every deck is matched on, its
  settings and its created date come back as they were. An export rebuilds
  the deck from a manifest, under a new id where the id is taken — right for
  a deck you send somebody, wrong for one you are putting back.
* **every** picture and recording travels, named by an exercise or not. An
  export carries only what its exercises mention; a file nothing mentions
  today is one somebody unlinked yesterday, and a backup that dropped it
  would destroy it.
* the **scheduling always travels**. An export offers to leave it behind
  because a deck you share should start the other person new. Months of
  answers cannot be worked out again from anything, so a backup that reset
  them would not be one.

A deck already here is **kept** and named in the answer; replacing it is
offered only then. `.trash/` and a half-finished import are left where they
are.

    exercises-backup-YYYYmmdd-HHMM.zip
        parseh-exercise-shelf.json          {"format", "kind", "decks": [...]}
        <language folder>/<deck slug>/      deck.json, items/, schedule/,
                                            images/, audio/ — as on disk
