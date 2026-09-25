---
title: Reading a book nobody has glossed
linkTitle: Reading unglossed chunks
weight: 11
description: The dictionary switch and its panel — the dictionary, the machine's reading, sentences somebody translated, Load more — and the sources sidebar and Ask LLM, which put them into a gloss.
---

Between pasting a text in and finishing its glosses lie weeks, and for
those weeks every unglossed chunk is a phrase you cannot get past. Three
things help, all on this machine, and none of them is a gloss:

- **a dictionary** gives you the *words*: what each one can mean, and how the
  word on the page was reached from the headword it is a form of;
- **a translation model** reads *the sentence* your chunk sits in, and marks
  the part of its reading that seems to be your chunk's;
- **sentences somebody has already translated** — a real sentence, written
  by one person and translated by another, sharing the rare words of your
  chunk — settle which of the senses on the list is the live one.

They are installed once, with buttons, on the **reading help** page
(Settings, `/settings/reading-help/`), which the header's **reading help** link opens; the Lookup and
languages section of this guide goes through it. A reader with none of them
is exactly the reader it always was.

## The dictionary switch

Once anything is installed for the book's language, the header shows
**dictionary**. It is **off** until you turn it on — then it is remembered,
for this book, in this browser — and its tooltip says what it will do: *look
the words up, show a sentence somebody translated, translate the line —
where nothing is glossed*, or as much of that as is installed. With it off,
nothing is fetched, nothing is translated, and the page costs exactly what it
did before.

With it on, **click any chunk that has no vocabulary line** — in any mode,
hover or not — and its cloud opens with the panel in it. (In hover mode,
pointing is enough.) A chunk somebody has glossed is left alone: the panel
exists for the chunk nobody has got to yet, and a finished edition looks
exactly as it did.

**English is explained in English.** Every dictionary here is the English
Wiktionary's, which explains the words of every language in English — for
Persian a translation, but for English itself a *definition*, in the very
language you are learning. So a book in English has two more switches:
**definitions** (off until turned on) shows Wiktionary's definitions under
each word, with their labels (*transitive*, *countable*, *slang*), the
first three at once and the rest behind **N more definitions**; and, where a
translation model into the language of your glosses is installed, **in
*italian*** (named after that language) puts each definition into it,
underneath — a machine's reading of a definition, labelled so. Off, an entry
still gives the headword, how it is said, its part of speech, how it was
reached and a verb's forms.

## The panel

The panel is tinted and ruled off from the gloss, and holds up to three
blocks, each headed with what it is and ending with where it came from:

**dictionary — not a gloss.** Each word of the chunk, and under it every
entry the dictionary has: the headword and its romanisation, the part of
speech, and the senses — the likely ones first, obsolete and rare ones last.
When the word on the page is not the headword, a line says how it was
reached (*found without the marks and the case*, for instance), which is
the line that teaches. A verb carries a line of its
principal parts. A word it cannot find says what it tried: *not found
(tried …)*. At the foot, the source and its licence.

**a machine's reading of the sentence — not a gloss.** The whole sentence
the chunk sits in, translated by the model on this machine. A chunk is a
fragment by construction, and a fragment translated alone comes back as
one, so it is the sentence that is read; the words of the reading that seem
to be **your chunk's** are marked in it — in colour and bold where the
dictionary accounts for at least half of the chunk's words, with a dotted
underline where it accounts for fewer — and a line under it says what
the mark stands on, `this chunk is likely: “…” — مثل → parable · ایران → Iran`,
or *part of this chunk is likely*, or that nothing matched and nothing is
marked. The mark is a guess from meaning, never from
position: word order is exactly what a translation changes. Where the chunk
*is* the whole sentence, there is nothing to mark, and the heading is just
*a machine's reading — not a gloss*. The model and its engine are named at
the foot. There is no button to use it as a gloss, and there will not be one.

**a sentence somebody translated — not this one.** Sentences from a
translated corpus (Tatoeba) that share the rare words of your chunk: both
sides, the shared words marked on both, and *shares …* naming them.
**Load more** fetches five more, for as long as there are more. It is not
your line and never pretends to be, which is exactly its use.

A panel with nothing to say says so: *the dictionary has nothing for these
words*.

**It gets ahead of you.** While you are not asking anything, the reader
looks up the unglossed chunks of the next ten subparagraphs, and reads their
sentences with the model, so that the panel opens already filled. It waits
for a moment's quiet after your last scroll or keypress, and stands down the
moment you open a cloud yourself — and it does nothing at all while the
switch is off.

## The sources sidebar: taking it up into a gloss

The panel is for reading; nothing in it writes. Where the gloss is actually
written — the chunk sheet ([Writing a chunk](doc:Writing a chunk)) — the same
sources come with you: **⊕ sources** in the sheet's head opens a column on
the left of the fields (the picture on that page shows it). The fields do
not move; the sheet grows to the left. On a narrow screen the column goes
under the fields instead, and the sheet scrolls down to it. The column
stays open until you close it, remembered for this book.

It is offered on every chunk that has gloss slots, written or not —
correcting a line is as much of the work as writing one — and whether or
not the **dictionary** switch is on. Its four blocks, in the panel's order:

| Block | Its buttons |
|---|---|
| **dictionary** | per entry: **romanisation →** (the romanisation of the word as the chunk has it, into the transliteration), **\dw → vocabulary** (the whole entry, `\dw{word}{rom} sense`, onto the vocabulary line), **meaning →** (the sense into the meaning) |
| **a machine's reading** | **the marked words → meaning**, **the whole sentence → meaning** (just **meaning →** where nothing is marked) |
| **sentences somebody translated** | **its meaning →**, per sentence |
| **external chatbot** | **Ask LLM** and **Use translation** (below) |

Every button **appends** — a vocabulary line is built up entry by entry — and
leaves the cursor at the end of the field. **It writes into a box, never
into the book**: nothing is saved until you press **save chunk**, down the
same route, with the same checks, as anything you type.

**A verb goes in as `\vb`.** Where the dictionary's entry is a verb the
language knows how to conjugate, the row shows the line of its forms, and
the button is **\vb → vocabulary**: the verb with its principal parts, in
this language's order. Where the book has already glossed the same verb, the
row first offers **\vb as this book glosses it →**, so the twenty-first
occurrence matches the twenty before it; the dictionary's own is then
**the dictionary's \vb → vocabulary**, and is not drawn at all when the two
are the same. A `\vb` the dictionary could not complete still goes in, with
its gaps listed under the row, one to a line, headed *to fill in:* — and its
button has a dashed border. Where the verb is another verb's than the
headword (German's *stand … auf* going in as *aufstehen*, a reflexive going
in as *sich freuen*), the row says so with an arrow.

**A verb of two words.** Persian's compound verbs (*labxand zadan*, to
smile), Turkish's, Hindi's conjunct verbs and French's verbal locutions are
one vocabulary entry, not two. For them the row has a second button,
**compound verb → vocabulary** (**conjunct verb** in Hindi, **verbal
locution** in French), that puts the pair in whole; its tooltip says what it
will write.

What is always left to you: the meaning is the dictionary's *first* sense,
not necessarily the one your sentence wants; where two auxiliaries are
possible, both are printed — strike the one the sentence does not use;
every hit that could be a verb gets a `\vb`, the unlikely ones included.
A block with nothing to offer says so in its own words (*the dictionary has
nothing for these words*, *no translation model for this pair*).

## Ask LLM

The last block hands the sentence to an external chatbot — any one, in
another tab — and brings its answer back:

1. **Ask LLM** copies a prompt to the clipboard: the sentence, the three
   sentences before and after it, the dictionary's results for the chunk,
   and every translated sentence the corpus has for it (it gathers them all
   first: *Preparing Ask LLM with all Tatoeba examples…*). The machine's own
   reading is deliberately never in it. *Prompt copied. Paste it into a
   chatbot, then paste its answer below.*
2. Paste the chatbot's translation into the box, and press **Use
   translation** (or **Ctrl+↵**). *Translation ready for this whole sentence.*
3. It is drawn like the machine's reading, with this chunk's share marked
   and the same buttons: **the marked words → meaning**, **the whole sentence
   → meaning**.

The answer is kept for the sentence, so the other chunks of the same
sentence reuse it (*Reusing the translation pasted for this sentence.*) and
only the mark moves. If the clipboard cannot be reached, the block says so
and **Ask LLM** tries again.

**Ask LLM** helps you write one chunk's gloss yourself. To have an LLM write
the glosses of a whole stretch — every chunk nobody has glossed, from one
sentence to a chapter — use the header's **gloss with an LLM** instead
([Glossing a stretch with an LLM](doc:Glossing a stretch with an LLM)): its
answer goes into the book, where nothing here does, but only into chunks
that have no gloss, and only whole.

> **None of this is a gloss.** A dictionary lists everything a word can
> mean and cannot say which is meant; a translated sentence is somebody
> else's sentence; a machine's reading is nobody's judgement. So in the
> reader they are drawn apart from the gloss, labelled with what they are,
> and shown only where nobody has written a vocabulary line — and the only
> place any of them becomes part of the book is a field of the chunk sheet,
> where you correct it and save it yourself.
