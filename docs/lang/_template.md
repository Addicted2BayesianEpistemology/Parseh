# {{NAME}} — the annotation conventions

{{?new}}How a {{NAME}} sentence becomes a glossed line: what goes into each field and
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
gloss language says so.{{/new}}

{{?note}}<!-- Scaffolded from docs/lang/_template.md by lib/newlang.py.  The seven
     sections below are the seven that docs/lang/fa.md has and that every prompt
     expects (the last, Example, is a worked answer); keep all seven, including
     the ones that only say the language has no such thing.  Replace every TODO.
     The model is docs/lang/fa.md for a language with marks, docs/lang/it.md for
     a Latin one, docs/lang/ja.md for one with a reading.
     A rule about the RELATIONSHIP between this language and the one the
     glosses are written in -- which words the reader already knows, what a
     respelling would be read as -- must name the gloss language and not
     English, which is only the commonest one: docs/lang/it.md's false friends
     and docs/lang/en.md's two shapes are the models. A transliteration scheme
     is the other kind: it belongs to this language and does not move.
     The file is cut per prompt and its flagged blocks are resolved by
     lib/promptkit.py (docs/prompt-kit.md): what belongs to a book only or a
     video only, to a prompt from scratch only, and a note to whoever keeps the
     file that no prompt carries, each have a flag.  Every sound the file shows
     is written twice, one block for the usual scheme and one for IPA, so that a
     prompt that asks for IPA never shows the other (docs/lang/fa.md is the
     model).  A language with short vowels to mark (`strip` in its registry row)
     also writes its marks paragraphs twice, one block for the prompt that asks
     for the marks and one for the prompt that leaves the text as it is
     (docs/lang/fa.md and ar.md); a language without them writes neither. -->{{/note}}

## The text field

`fa` reproduces the source **verbatim**: same spelling, same punctuation, the
source's own oddities included. Chunks split only at {{CHUNK_WORDS_SEAM}}, and
joined back they must reproduce the sentence exactly — a machine checks that.
**Never correct the text in `fa`**{{?new}}; the correction goes in {{?video}}`note`{{/video}}{{?book}}the
vocabulary line{{/book}}{{/new}}.

TODO: what else the text field carries in {{NAME}} — the marks a reading
edition writes in and a caption does not, the spellings the source is allowed
to keep, and any mark that is an error rather than extra precision. Be exact:
this section is what the fidelity checks are measured against.

## Reading

{{READING}}

## Transliteration

{{?classic}}`tr` is the {{TR_LABEL}} of what is actually said or printed, not of the
dictionary form.

TODO: the scheme, letter by letter — every mark used, what it stands for, and
what is hyphenated. An annotator who has only this file must be able to write
a line that another one would write the same way.{{/classic}}{{?ipa}}`tr` is the pronunciation of what is actually said or printed,
written in **IPA**: the broad (phonemic) IPA of {{NAME}}, with no slashes and no
square brackets, the stress mark ˈ and the length mark ː where {{NAME}} has
them, and one scheme from the first chunk to the last — not the dictionary form.

TODO: which IPA — the variety of {{NAME}} that is transcribed, and every sign
this language needs for its own sounds, letter by letter, with what each stands
for; and what is hyphenated, which the usual scheme's hyphens say. IPA does not
follow the gloss language: it is the same in a book glossed in any language.{{/ipa}}

## Vocabulary

`voc` is written in the voice of the books' gloss blocks: headword +
{{?classic}}{{TR_LABEL}}{{/classic}}{{?ipa}}IPA{{/ipa}} + meaning. Name what was stripped from the form in the text. One
equivalent in the gloss language rather than a string of synonyms, and **an
empty `voc` is the right answer** for a chunk that needs nothing. The meaning
is what the gloss language is for; the labels around it — the ones the
edition prints from the registry included — are not, and stay as this file
writes them whatever the glosses are in.

The line uses four macros and nothing else: `\dw{fa}{rom} gloss` ·
`\vb{form}{rom}{form}{rom}{form}{rom}{meaning}` · `\bw{base}{rom}{meaning}` ·
`\pw{fa}` — plus `\textit`, `\emph`, `\nobreak` — and its entries are parted by
`; `.

**Every verb gets a `\vb`.** Its seven slots are, in this order, the
**{{VB_FORM1}}**, the **{{VB_FORM2}}** and the **{{VB_FORM3}}**, each with its
{{?classic}}{{TR_LABEL}}{{/classic}}{{?ipa}}IPA{{/ipa}}, then the meaning. The edition prints *{{VB_PRES}}* and
*{{VB_PAST}}* before the second and the third (lib/lang/{{CODE}}.tex's
`\FrankVbPres` and `\FrankVbPast`, the registry's `vb_labels`), so never
put another form into those slots. A pair whose form is left blank is not
printed at all, label and all: leave one blank only where the language has
no such form for that verb, never to save space. What the three forms cannot
say goes in **one parenthesis after the meaning**, items parted by `; `, each
only where it is not the ordinary case — `\vb{fahren}{}{fuhr}{}{gefahren}{}{to
drive (er fährt; aux. sein)}` is German's shape.

TODO: why these three forms, with an example of each, written twice
(once for the usual scheme, once for IPA) wherever it shows a sound; which extras this
language has, if any, in their exact wording; and which verbs do NOT get a
`\vb` (docs/lang/en.md's modals, docs/lang/zh.md's rule). Then: what a noun
is given with, and what an annotator must name when a form in the text is not
the dictionary form.

{{?video}}What a video adds is the form its chunk has, where it is none of the three
the `\vb` prints, nor one its parenthesis names: it is named after the entry,
outside it, with its sound,
`\vb{form}{rom}{form}{rom}{form}{rom}{meaning}; here \pw{form} \textit{rom}, what it is`
(TODO: what else a video says, if anything, goes in the parenthesis after the
meaning: the colloquial forms of speech).
{{/video}}The repetition rule is Frank's own: a full entry the **first time** a word
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

## Example

{{?note}}TODO, and no speaker has reviewed it yet: until a speaker of {{NAME}} has read the chunks, the
transliteration and the IPA, this line says so (a line of this kind, in a block of this name, is never sent).{{/note}}TODO: three
chunks of one sentence of {{NAME}}, as an answer writes them — cut the way Chunking above cuts a sentence, `fa`
in the language's own script, the `tr` in its scheme, `voc` in the one convention above (a book's macros,
entries parted by `; `, a chunk that needs nothing with none) and an `en` that is **aligned**: each chunk's `en`
renders that chunk's own words and only those, in the text's order, so that read in a row it may not be good
English. The key of the text is `fa` in every language; a language with a reading also carries `kana`, and one
whose chunks carry words also `words`. Then one line saying what to notice. Write the block twice, the second
with every sound in IPA, so that an IPA prompt never shows the usual scheme, and run each `voc` line through the
checkers (`youtube/lib/check_annotations.py`, `lib/texwrite.py`). The meanings are written in English because
an example has to be written in something; the prompt's own gloss language is named elsewhere in it.

{{?classic}}```json
{"chunks": [
  {"fa": "TODO", "tr": "TODO", "voc": "TODO", "en": "TODO"}
]}
```{{/classic}}{{?ipa}}```json
{"chunks": [
  {"fa": "TODO", "tr": "TODO in IPA", "voc": "TODO", "en": "TODO"}
]}
```{{/ipa}}

What to notice: TODO.
