---
title: Cards and Anki
weight: 70
description: Making flashcards out of a book or a video, giving them their sound, and keeping them in step with Anki.
---

Every word you meet in a book or a video can become a card. You pick it
where you read it, the card sheet opens already filled in, and the card
goes where you send it: to **Anki**, as a note in one of your decks; to an
**exercise deck** of this toolbox; or onto the clipboard as **markdown**,
for a studio document. It can carry the word's own sound, cut out of the
book's narration or the film, and — from a video — a frame of the picture.

The Anki side is a round trip. Parseh keeps every Anki card as a small file
of its own, builds a deck package (`.apkg`) from those files, and you import
that package into Anki. Once you have studied and edited the cards inside
Anki, a sync brings those edits home before the next build, so that nothing
you changed in Anki is ever overwritten.

## The loop, in short

1. **Make cards** while you read or watch: modifier-click a word
   (**Alt**, **Ctrl** or **Cmd**) and press **save card**.
2. **Build the deck**: **build .apkg** on the card sheet, and import the
   file into Anki (**File → Import…**).
3. **Study in Anki**, and edit there as you like.
4. **Before the next build, sync**: export the deck from Anki, drop the
   file on the **Sync with Anki** page, preview, apply — then rebuild and
   import again.

Steps 1 and 2 are all there is until you edit a card inside Anki. From
then on, step 4 comes before every build.

## Where it all is

| On the page | What it opens |
|---|---|
| a modifier-click on a word, or **+ card** in a gloss cloud | the card sheet, in the book reader and in the video player |
| **🔊 cut the audio…** on the card sheet | the cut editor, which cuts the word's sound into the clip tray |
| **⇆ Anki** on the hub | the **Sync with Anki** page (`/anki/sync/`) |
| **⇆ Sync with Anki** on the videos page | the same page |
| **⇆ synced lately?** beside a video's **build .apkg** | the same page, in a new tab |
| **✂ The clip tray** on the hub | the clip tray's own page (`/clips/`) |

The hub's **⇆ Anki** door counts the cards and the decks in the store, and
**✂ The clip tray** says how many clips wait in the tray. Both doors, like
the rest of what edits, are on the hub's **Browser** layout only: the
**Mobile** layout is made for reading and studying, so switch back to
**Browser** in the hub's top bar to reach them.

## The pages of this section

They follow the life of a card: where it is kept and what it is made of,
making it and giving it its sound, building the deck, and the round trip
with Anki once you study and edit it there.
