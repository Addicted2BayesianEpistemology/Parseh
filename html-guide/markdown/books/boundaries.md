---
title: Cutting and joining chunks
weight: 9
description: Moving the boundary between two chunks — where a chunk may be cut, what becomes of its gloss, and what the sheet refuses.
---

Everything in the chunk sheet changes what a chunk *says*. These three
buttons change where it *stops*. A chunk is a sense group, and where the
sense groups fall is a judgement somebody makes while reading — which means
the division an LLM, or a first pass of your own, produced is exactly the
thing a person who knows the language wants to move.

They are at the foot of the chunk sheet ([Writing a chunk](doc:Writing a chunk)),
in the row **where it ends**:

- **cut this chunk in two…**
- **join it to the next…**
- **join the previous to it…** — the same join, asked of the chunk before
  (not offered on the very first chunk of the book).

Each opens a sheet of its own over the chunk sheet that shows what it
proposes, field by field, and writes nothing until you press its button.

A `\chp` — a chunk with no gloss slots at all — can be cut in two, and
joined to another `\chp`; it cannot be joined to a chunk with gloss slots
(the refusal is below).

## Cutting a chunk in two

The sheet shows the chunk's text with a pair of scissors, **✂**, at every
place it may be cut. Pick one, and two columns appear — **first chunk** and
**second chunk** — each with its text and boxes for its reading, its
transliteration, its vocabulary and its meaning, holding what the sheet
proposes. Type over any of them; then **divide**.

**Where a chunk may be cut: at a space, and nowhere else** — in a language
whose words are separated by one. The reason is the fidelity check, not
taste: the chunks of a paragraph joined back with the language's separator
have to *be* the paragraph again, and `wo rd` is not `word`. Japanese and
Chinese, which write no separator, divide between any two characters. So
the sheet offers those places and no others. A gap that is not the
separator itself — a tab, a non-breaking space — is not offered either,
because the halves would be rejoined with an ordinary space and that
character would go missing. A chunk of a single word says so instead (*This
chunk is one word … Join it to its neighbour first, or leave it*).

A cut **divides**; it does not rewrite. The two halves must be the chunk's
own text, character for character. Change a letter in the chunk sheet,
before or after.

### What becomes of the gloss

Dividing the text is arithmetic. Dividing the gloss is not: nothing in the
data says which half of a meaning belongs to which half of a phrase. So the
sheet **proposes**, in boxes you type over:

| Field | What is proposed |
|---|---|
| the text | the cut itself — the only one that is not a guess |
| the transliteration | cut at the same word, when it has exactly as many words as the text; otherwise all of it to the first half |
| the vocabulary | entry by entry: each entry follows its headword to the half whose text holds it, and an entry with no headword of its own (a verb's second line, a note) stays with the one before it. The entries are drawn as chips, each with an arrow — **→** or **←** — that sends it to the other half. |
| the meaning | all to the first half, so the second is visibly unwritten and gets written — unless the meaning has exactly one comma, the one place a division is already marked |
| the kana | all to the first half, unless the reading opens with the first half's own characters, which is what happens when a Japanese phrase is parted at a particle |
| the words | Japanese and Chinese: divided where the text is; a word cut through keeps its reading on the first half |
| the colour | both halves keep it: it marked the phrase, and the phrase is still there in two pieces |

A chunk nobody has glossed divides into two chunks nobody has glossed. In
Japanese and Chinese, where such a chunk carries the reading proposed from
its words, each half is given the reading of its own words instead — the
whole reading on the first half would make it look written.

**What the halves may be.** Glossed, blank, or glossed in part: a cut
refuses nothing for a box left empty. The second half of a glossed chunk
usually comes out with its meaning still to write — the proposal leaves it
empty on purpose — and it is saved so; the checker lists it until it is
written ([Writing a chunk](doc:Writing a chunk)). A join is the same.

## Joining two chunks

The sheet shows the two texts side by side, and one column — **the one chunk
they become** — with every field already joined, for you to correct; then
**join**. The texts go end to end with the language's word separator, so
the paragraph is reproduced character for character and no check *can*
fail; the transliteration and the meaning with a space; the vocabulary with
its own separator. What could not simply be run together is said in a note
under the boxes: two colours (the first one's stands), two meanings written
to be read apart.

## What it refuses

| It says | Which means |
|---|---|
| *they are in different subparagraphs* | a subparagraph is a unit of the text, not of the gloss: two chunks under different subparagraph labels are not a pair the page may join |
| *there is something between them in the file* | a comment — a narration's `% @par` line, say — lies between the two chunks in the chapter file, and joining them would swallow it |
| *one is \chp and the other \ch …* (or `\chr` and `\ch`) | a chunk with a reading, one with no gloss slots (`\chp`) and an ordinary one are not the same kind of thing. A word line makes no difference: `\ch` joins `\chw`, and `\chr` joins `\chrw` |
| *something else is on the line with this chunk* | the checker reads one chunk per line; a chapter that puts two on one line is left for a hand to lay out |
| *these two texts are not this chunk divided in two* | a letter was changed in one of the halves |
| *the page is showing the first chunk as … and the file has …* | the page is out of date — something changed the book since it was drawn. Every cut and join sends the text it is looking at, and the server compares it with the file before it writes. Reload. |

## Afterwards

Every chunk after the change has a new number, so the sheet does not simply
close: it says what was done — *The chunk is two chunks now, in ch1.tex* —
with the paragraph's check against its source, and ends *Every chunk after
this one has a new number, so this page is out of date until it is
reloaded*, with one button, **reload the reader**, which brings you back to
the same place. The PDF is behind the text until its next build. A page left
open is safe as well as stale: the next cut or join from it is refused by
name rather than made to the wrong chunk.
