---
title: Sentences somebody translated
weight: 4
description: The parallel corpus — a real sentence and a person's translation of it, shown under a chunk because it shares that chunk's rare words.
---

A dictionary lists every sense a word can carry and cannot say which one
your sentence means — شیر is *lion*, *faucet*, *tiger* and *milk*. A sentence
somebody wrote and somebody else translated can: it shows the word at work.
So the panel under an unglossed chunk can also show **whole sentences that
share its rare words**, both sides of each, with the shared words named.

It is headed **a sentence somebody translated — not this one**, because
that is exactly what it is: not a translation of your line, and never
presented as one.

## Where the sentences come from

From [Tatoeba](https://tatoeba.org), a collection of sentences written and
translated by its contributors and released under **CC BY 2.0 FR**. Parseh
downloads its exports once, on this machine, and builds an index of them:
which sentences hold which word, and how many sentences hold each word —
which is what later tells a rare word from a common one.

## Getting a corpus

A corpus is a **pair** of languages: the language you read, and the one
your glosses are written in. Persian glossed in English and Persian glossed
in Italian are two different files.

1. On the [reading-help page](reading-help.md), go to **Sentences somebody
   has already translated**. Every language has a row.
2. Beside **get it** is a picker holding the other ten languages Parseh
   teaches, with **English** chosen. Pick the language your book's or
   video's glosses are written in — English, unless you chose another when
   you added it ([Target language and gloss language](target-and-gloss.md)).
3. Press **get it**.

The picker holds only the languages Parseh teaches, so a book glossed in a
language it only writes in — Portuguese, say — has no corpus to offer.

The download is three files — the sentences of each language and the links
between them — and only the sentences the links name are kept, which is why
the English export of millions of sentences does not become a corpus of
millions.

When it is done the row lists the pair on a line of its own — *glossed in
**English** · 8,454 sentence pairs · 3 MB · Tatoeba (tatoeba.org) · CC BY
2.0 FR · built …* — with **rebuild** and **remove** beside it, and the
picker stays for another pair. A language may have several pairs, each on
its line with its own buttons; the picker offers only the ones it has not
got. **rebuild** is worth pressing now and then: Tatoeba gains sentences
every week.

### What it costs, and what you get

Coverage is very uneven, and so is the size. Measured:

| Pair | Sentence pairs | Size |
|---|---|---|
| Italian–English | about 719,000 | 182 MB |
| Spanish–English | 283,123 | 83 MB |
| Persian–English | 8,454 | 3 MB |

Two orders of magnitude between the ends of that list. A thin pair simply
finds a sentence to show you less often — no error, no message, just a
panel without one, which is worth knowing before you decide something is
broken. A pair Tatoeba does not have at all fails in the row, in red,
saying so.

### Japanese and Chinese need their dictionary first

A corpus is indexed word by word, and a sentence written without spaces has
to be cut into words first — which only the dictionary's own word list can
do. So until the **Japanese** or **Chinese** dictionary is installed, their
row says *its dictionary first — Japanese is written without spaces between
its words, so a corpus of it has to be cut into words before it can be
indexed, and the dictionary's own word list is what cuts it*, and offers no
button. Install the dictionary above, reload the page, and the row offers
**get it**.

Every other language's corpus stands on its own: it needs no dictionary,
and a corpus alone is enough for the reader to show its **dictionary**
switch.

## In the reader and the player

With the **dictionary** switch on, open a chunk (a phrase, in the player)
that has no vocabulary line. The sentences come back with the dictionary's
answer, on the same request, and sit at the foot of the panel, after the
dictionary's entries and the machine's reading:

- up to **three** sentences at first, each with the original above and the
  translation below — each in its own direction, so a Persian sentence runs
  right to left over its English;
- under each, **shares …**, naming the words it has in common with your
  chunk, so you can see why it was chosen;
- the source and the licence at the foot, *Tatoeba (tatoeba.org) · CC BY
  2.0 FR*;
- **Load more**, when there are more: five more each time, until there are
  none (it says *Loading…* while it asks).

### Why that sentence and not another

A sentence is offered on the **rarest** word it shares with your chunk,
weighted by how few sentences of the corpus hold that word: sharing *and*
is worth nothing, sharing *homeland* is worth the match. The rarest shared
word must clear a bar on its own — three of the commonest words in the
language together do not add up to a reason — and the bar is a fraction of
what the rarest word in *that* corpus is worth, so a small corpus is small
rather than silently useless. Among the sentences that qualify, what all
their shared words are worth together decides which comes first.

An example worth knowing: سیگار می‌کشد, *he is smoking a cigarette*. The
dictionary reaches می‌کشد only through کشتن, *to kill*, because of how
Wiktionary files the forms. The corpus answers with سامی دارد علف می‌کشد و می‌نوشد — *Sami is
smoking weed and drinking* — sharing می‌کشد, and the smoking sense is in
front of you without anybody having glossed anything.

### In the editor

In the chunk sheet's (or the edit cloud's) **⊕ sources** column, the same
sentences appear under *sentences somebody translated*, each with **its
meaning →**, which puts the translation into the meaning box for you to
correct. As with everything in that column, nothing reaches the book or
the video until you save.

{{< details summary="For the command line" >}}
```bash
python3 lib/getcorpus.py                  # which pairs are installed
python3 lib/getcorpus.py fa               # Persian, glossed in English
python3 lib/getcorpus.py fa it            # Persian, glossed in Italian
python3 lib/getcorpus.py --all            # every language, glossed in English
python3 lib/corpus.py fa en "<a phrase>"  # what a reader would be shown
```
{{< /details >}}
