# {{NAME}} — the annotation conventions

How a {{NAME}} sentence becomes a glossed line: what goes into each field and
how it is written. These rules bind both the reading editions and the video
captions; they are embedded whole into every prompt that asks for {{NAME}}
annotation, so they are written as instructions to the annotator.

Two of the field names are languages, and neither is a claim about one: `fa`
is the text in the target language — {{NAME}} here — and `en` is the gloss
beside it. They are the names Persian and English left behind from the days
when they were the only two languages the toolbox had, and they are the same
two keys in every book and every video. Which language the gloss is written
in is the book's or the video's own choice, `"gloss"` in `book.json` /
`video.json`, and English when the key is absent. This file is about {{NAME}}
as the language being **taught**: the examples below gloss into English
because they must gloss into something, and every rule that turns on the
gloss language says so.

<!-- Scaffolded from docs/lang/_template.md by lib/newlang.py.  The six
     sections below are the six that docs/lang/fa.md has and that every prompt
     expects; keep all six, including the ones that only say the language has
     no such thing.  Replace every TODO.  The model is docs/lang/fa.md for a
     language with marks, docs/lang/it.md for a Latin one, docs/lang/ja.md for
     one with a reading.
     A rule about the RELATIONSHIP between this language and the one the
     glosses are written in -- which words the reader already knows, what a
     respelling would be read as -- must name the gloss language and not
     English, which is only the commonest one: docs/lang/it.md's false friends
     and docs/lang/en.md's two shapes are the models. A transliteration scheme
     is the other kind: it belongs to this language and does not move. -->

## The text field

`fa` reproduces the source **verbatim**: same spelling, same punctuation, the
source's own oddities included. Chunks split only at {{CHUNK_WORDS_SEAM}}, and
joined back they must reproduce the sentence exactly — a machine checks that.
**Never correct the text in `fa`**; the correction goes in `note` (videos) or
in the vocabulary line (books).

TODO: what else the text field carries in {{NAME}} — the marks a reading
edition writes in and a caption does not, the spellings the source is allowed
to keep, and any mark that is an error rather than extra precision. Be exact:
this section is what the fidelity checks are measured against.

## Reading

{{READING}}

## Transliteration

`tr` is the {{TR_LABEL}} of what is actually said or printed, not of the
dictionary form.

TODO: the scheme, letter by letter — every mark used, what it stands for, and
what is hyphenated. An annotator who has only this file must be able to write
a line that another one would write the same way.

## Vocabulary

`voc` is written in the voice of the books' gloss blocks: headword +
{{TR_LABEL}} + meaning. Name what was stripped from the form in the text. One
equivalent in the gloss language rather than a string of synonyms, and **an
empty `voc` is the right answer** for a chunk that needs nothing. The meaning
is what the gloss language is for; the labels around it — the ones the
edition prints from the registry included — are not, and stay as this file
writes them whatever the glosses are in.

In a **video** the line is plain text. In a **book** it uses four macros and
nothing else: `\dw{fa}{rom} gloss` · `\vb{form}{rom}{form}{rom}{form}{rom}{meaning}` ·
`\bw{base}{rom}{meaning}` · `\pw{fa}` — plus `\textit`, `\emph`, `\nobreak`.

**Every verb gets a `\vb`.** Its seven slots are, in this order, the
**{{VB_FORM1}}**, the **{{VB_FORM2}}** and the **{{VB_FORM3}}**, each with its
{{TR_LABEL}}, then the meaning. The edition prints *{{VB_PRES}}* and
*{{VB_PAST}}* before the second and the third (lib/lang/{{CODE}}.tex's
`\FrankVbPres` and `\FrankVbPast`, the registry's `vb_labels`), so never
put another form into those slots. A pair whose form is left blank is not
printed at all, label and all: leave one blank only where the language has
no such form for that verb, never to save space. What the three forms cannot
say goes in **one parenthesis after the meaning**, items parted by `; `, each
only where it is not the ordinary case — `\vb{fahren}{}{fuhr}{}{gefahren}{}{to
drive (er fährt; aux. sein)}` is German's shape.

TODO: why these three forms, with an example of each; which extras this
language has, if any, in their exact wording; and which verbs do NOT get a
`\vb` (docs/lang/en.md's modals, docs/lang/zh.md's rule). Then: what a noun
is given with, and what an annotator must name when a form in the text is not
the dictionary form.

In a **video** the same entry is plain text, `form rom · {{VB_PRES}} form rom ·
{{VB_PAST}} form rom · meaning (extras)`, and a form of it in the chunk is given
first with the entry in brackets after it. The gloss editor's sources sidebar
proposes these entries from the dictionary, for a verb it recognises; read
what it proposes and correct it before it is saved — it is a draft, and where
it could not fill a slot it says which.

The repetition rule is Frank's own: a full entry the **first time** a word
appears, briefer or none on later appearances.

## Never gloss

TODO: the function words that are already dictionary form and never get an
entry — the article, the common prepositions, the pronouns, the conjunctions.
List them, do not describe them: this list is read by an annotator mid-batch.

```
TODO
```

## Chunking

A chunk is a sense group of {{CHUNK_WORDS}}: something a reader hovers and
that *means* something on its own. A very short sentence is one chunk; that is
normal and not a fault.

{{MARKED}}

TODO: what must never be split in {{NAME}} — the pairs a chunk boundary would
cut through (a verb from its negation, a compound from its parts, a noun from
what governs it).
