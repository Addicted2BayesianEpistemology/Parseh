---
title: From a deck back into a document
linkTitle: Back into a document
weight: 3
description: The editor's Load from a deck… — an exercise of a deck put into a document at the cursor, with its pictures, recordings and footnotes.
---

**+ Deck** copies an exercise from a document into a deck. The way back is
in the studio's editor: **Exercises ▾ → Load from a deck…**. It is how an
exercise you wrote straight into a deck, or one a card sheet made while you
were reading, ends up in a lesson — or how a deck's exercise is mended where
mending is easiest.

## Loading an exercise

1. Open the document in the editor and put the cursor where the exercise
   should go.
2. **Exercises ▾ → Load from a deck…** opens *Load an exercise from a deck*.
3. **Deck** lists your decks in the document's language, the one you used
   last already chosen. There is no **+ New deck…** here: a deck that does
   not exist yet has nothing to give.
4. Under it, every exercise of that deck, one row each: what kind it is
   (*Choose one answer*, *Flashcard*…) and its opening words. Click the one
   you want.
5. **Insert** puts it into the document at the cursor, exactly as the deck
   holds it, and says *Exercise inserted*.

The status line under the list keeps you informed: how many exercises the
deck has, *That deck is empty.*, or — when you have no deck at all in the
page's language — *No Persian deck yet — make one with “+ Deck” on a page.*

## It arrives whole

An exercise in a deck may carry pictures, recordings and footnotes, and they
all come with it:

- **Pictures and recordings** are copied into this document's own `images/`
  and `audio/` before the exercise goes in. A file whose name is already
  taken in the document **by a different file** is stored as `cat-2.png`
  (then `-3`, …) and the inserted exercise names it where it landed; the same
  file already in the document is not copied twice. A picture the deck
  itself has lost keeps its path, and the message after **Insert** says
  which.
- **Footnotes** the exercise calls come with it and are placed among the
  document's own, in the order the reader meets them. A note whose name the
  document already uses for something else is renamed — `n1` becomes
  `n1-2` — in the inserted exercise and in its own definition, so neither
  note is lost. The same note with the same words is simply shared.

The deck is left exactly as it was: this copies **out** of a deck, it moves
nothing. The exercise keeps its schedule there, and the one in the document
is a new, independent copy.

## Before you start

- **Save the document once.** Its pictures and recordings are copied into
  the document's own folder, and an unsaved document has none yet; the menu
  item says so (*Save the document first*) instead of opening.
- **An exercise that needs attention is still offered**, its kind followed
  by *· needs attention*, with the reasons when you point at it. A deck's exercise can stop
  working when it was edited by hand, or when it came from an older Parseh;
  a document, with its editor and its live preview, is the easiest place to
  put it right.
- **Only the decks of the page's language** are offered, since every
  exercise of a deck is in the deck's language.

**Notes** opened beside a book or a video have the same menu item: the
exercise goes into that note, and its files into the note's own folder.
