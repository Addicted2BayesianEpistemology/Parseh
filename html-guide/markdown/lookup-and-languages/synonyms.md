---
title: Synonyms for the machine's reading
linkTitle: Synonyms
weight: 6
description: The last section of the reading-help page — a table of English synonyms from WordNet that helps the machine's reading mark the right words.
---

The last section of the [reading-help page](reading-help.md) is headed
**Which words of a reading are the chunk's**, and it is a small refinement
of [the translation model's](translation-model.md) mark.

## What it fixes

The model gives a translation and no word alignment, so the reader guesses
which words of the machine's reading are your chunk's from what the
**dictionary** says the chunk's words mean. That works when the model chose
the dictionary's word. When it chose **another word for the same idea** —
*begin* where the dictionary says *start*, *aid* where it says *help*,
*master* where it says *lord* — nothing in the reading matched, and the
guess used to mark nothing at all.

The synonym table closes that gap: a list of which English words are
synonyms of which, taken from [WordNet 3.1](https://wordnet.princeton.edu/)
(Princeton University), a dictionary of English whose lexicographers grouped
words that are interchangeable in one sense.

## Getting it

It is **one row**, named **synonyms**, with no language and no picker —
the table is about English words, not about any language you read. Press
**get it**; it is about a megabyte, fetched once, and kept as
`mt/synonyms.en.json`. Installed, the row says how many words it holds, its
size, its source and licence (*WordNet 3.1 (Princeton University) · WordNet
3.0 licence (free redistribution and modification)*) and when it was built,
with **remove** (after a confirmation: *Remove the synonym table?*) and
**rebuild**.

There is nothing to switch on. A reader loads the table the moment it
learns that a model exists for its pair — well before you open a cloud —
and uses it from then on. Without it, or with no model, everything works
as before.

## How careful it is

A synonym is real evidence, but weaker evidence than the word itself, and
the table is used with that in mind:

- **The word itself always wins.** Where both are in the reading, an exact
  word (or one of its inflected forms) outscores a synonym of it.
- **Only a word's first, most common sense counts.** Two words are
  synonyms here only where that shared sense is the *first* sense of both.
  WordNet also groups *heap*, *mountain* and *batch* as "a large quantity";
  allowing that would have made *mountain*, the land mass, a synonym of
  *heap* — so it is not allowed.
- **A synonym on its own stands only for a first sense.** With nothing
  else in the reading to back it up, a synonym is a mark only when it is a
  synonym of the *first* sense the dictionary gives the chunk's word: صاحب
  reaches *lord* because its first sense is *owner; master* — never through
  a stray sense further down the entry.
- **A synonym never joins a neighbour into a longer mark.** A garbled
  reading that repeats a word therefore cannot chain itself into a mark
  covering the whole line.
- **It is English.** The machine's reading is matched against what the
  dictionary says, and the dictionaries' senses are English, so the table
  helps where the reading is English — a book or a video glossed in
  English.

It still misses two unrelated words for one idea that WordNet does not call
synonyms — *want* and *like*, *piece* and *chunk* — and now and then it can
borrow the wrong sense of an ambiguous English word. Measured on the test
fixtures and a sample of Tatoeba, it changed the mark on three chunks in
five hundred, most of them for the better: a small, honest gain, which is
why it is a separate megabyte you may simply not bother with.

{{< details summary="For the command line" >}}
```bash
python3 lib/getsyn.py              # get it (or say it is already there)
python3 lib/getsyn.py --rebuild    # fetch WordNet again and build afresh
python3 lib/getsyn.py --remove     # take it off the disk
```
{{< /details >}}
