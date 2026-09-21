---
title: Books
weight: 20
description: The reading editions — the library, the reader, narrations, writing a book yourself, taking it away and bringing it back.
---

A **book** in Parseh is a *reading edition* in the Ilya Frank manner: the
text cut into small pieces — *chunks*, a phrase or a sense group each —
and every chunk glossed where it stands, with its transliteration, the
words it is made of and what it means. You read the sentence whole first,
then chunk by chunk with the help beside it, then the sentence whole again
without the help. A recording of the book can play in step with the text,
a subparagraph at a time.

The **Books** door of the hub opens the library at `/books/`. Everything in
this section is done from there and from the pages it leads to: nothing
here needs a terminal, except one way of adding a book that hands the work
to an AI coding assistant outside Parseh, and it says so.

## Where to start

Open the library ([The library](doc:The library)), pick a book, and read
([The reader](doc:The reader)). To make a book of your own, start at
[Adding a book](doc:Adding a book); to hear one, at [Adding a
narration](doc:Adding a narration). The pages of this section are listed at
the foot of this one, in the order a book is usually met: finding it,
reading it, hearing it, writing it, taking it away.

## Passes: the same text, several ways

Each subparagraph of a book is set several times over, one *pass* after the
other. Which passes there are depends on the language, and the header of
the reader has one numbered button per pass to show or hide it:

| Language | The passes, by the number on their button |
|---|---|
| Persian | 1 the vowelled attempt · 2 chunks and glosses · 3 bare naskh · 4 nastaliq |
| Arabic | 1 the vowelled attempt · 2 chunks and glosses · 3 unvowelled, as Arabic is written |
| Japanese | 1 with furigana over each word · 2 the reading alone, in kana · 3 chunks and glosses · 4 plain, as Japanese is written · 5 vertical (tategaki) |
| Chinese | 1 with pinyin over each word · 2 the reading alone, in pinyin · 3 chunks and glosses · 4 plain, as Chinese is written · 5 vertical |
| Italian, French, German, Turkish, English, Hindi, Spanish | 1 the sentence · 2 chunks and glosses |

Pass 1 is your own attempt at the sentence, before any help arrives; the
chunks-and-glosses pass is the help; the others give the sentence again — as
it is really printed, in its other face, or, in Japanese and Chinese, as it is
read aloud. The list comes from Parseh's language
registry, so a language added to the toolbox brings its own passes with it.

## Where a book lives

A book is a folder, and nothing anywhere keeps a list of books: a folder
with a `book.json` in it, under its language's folder, is on the shelf.

```text
books/
  persian/
    farsi-shakar-ast/
      book.json      the title, the author, the language
      main.tex       the frame: title page, one \input per chapter
      ch1.tex ...    the text, chunk by chunk, with the glosses
      source/        the original paragraphs, to check the text against
      reading.json   what you folded away
      markdown/      the notes in the seams
      audio/         the recordings (never committed)
      timings.json   where each subparagraph starts and ends
      main.pdf       the printed edition, once built
      reader/        the reading page, built from the .tex
```

The toolbox ships with no book: each language's folder under `books/` holds
only a `.gitkeep` until you add one, bring one back from a bundle or start
an empty one. The files themselves are described in
[What a book is made of](doc:What a book is made of).
