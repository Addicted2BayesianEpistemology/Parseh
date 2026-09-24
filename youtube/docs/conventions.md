# Annotation conventions

How a caption becomes a glossed line in the player. These rules are the
same for every video in every language; what a language decides for
itself — its transliteration scheme, what its vowelled and bare forms
are, what never to gloss, whether it has a reading — is in that
language's own conventions file, `docs/lang/<code>.md` at the root of the
toolbox (`fa.md` for Persian, and `ar.md`, `hi.md`, `ja.md`, `zh.md`,
`it.md`, `fr.md`, `de.md`, `tr.md`, `en.md`, `es.md` — one for every
language in `lib/languages.json`), which the prompt includes after this
one. The per-video word lists live beside this file.

*The Persian transliteration scheme and the Persian examples that used to
stand here are now `docs/lang/fa.md`.*

## The unit

A chunk is a **phrase**: the smallest span that still means something on its
own and that a gloss can translate as one thing. **Cut at the edges of
phrases, never inside one.** Aim for **two to five words** — for a language
written without spaces, a content word with the particles that follow it
(the Japanese bunsetsu).

**Keep together, always:**

- **an adposition with its noun** — `in the house`, `به خانه`, `家に`. Alone,
  neither half can be glossed at all. This is the rule that comes up most.
- **a noun with everything that modifies it** — articles, demonstratives,
  numerals, adjectives, possessives, the Persian ezafe chain, the Japanese
  `の`. A noun and its adjectives are one thing to a reader and should be one
  chunk, on whichever side the language puts them.
- **a verb with everything that makes its tense** — auxiliaries, negation, a
  separable prefix, and the light verb of a compound (`فکر کردن`,
  `勉強する`). **The unit is the verb group, not the verb.** `می‌خواهم بروم`
  and `食べている` are one verb each in two pieces; cut between them and both
  halves mean nothing.
- **a word with its particles and clitics.**
- **a fixed expression or an idiom, even where that breaks the syntax.** The
  meaning is not in the pieces, and showing the pieces teaches the reader
  something untrue. This is the most valuable chunk there is, and the one
  nothing mechanical can find — it is the reason a person or a model does
  this and not a rule.

**Cut, always:**

- **at a clause boundary.** A conjunction or a relativiser **opens** the
  chunk it introduces rather than closing the one before it.
- **between two content words with nothing binding them** — a subject and its
  verb, a verb and a new object.

**An adverb joins the verb it modifies when it stands next to it** (`quickly
ran`, `تند دوید`); a **sentence adverb** (`yesterday`, `فردا`, `もちろん`)
modifies the whole clause, glosses perfectly well alone, and stands on its
own. An **infinitive or verbal noun used as a noun** belongs to its noun
phrase, not to the verbs.

**What a chunk must not be.** Not **one word per word**: that is a dictionary
with the text interleaved, and the reader never learns how the language
phrases anything. Not **a whole clause or a whole sentence**: past about six
words the reader stops mapping and starts reading the translation, which is
the one thing this method exists to prevent. A one-word chunk is right only
when the word is the whole utterance (`Yes`, `بله`, `はい`) or when nothing
may attach to it.

Very short captions (a number, a single word, an exclamation) are one chunk.
That is normal in these videos and is not a fault.

## The fields

- **`fa`** — the caption's own words, **verbatim**: same spelling, same
  punctuation, same joiners (ZWNJ), ASR mistakes included. The key is
  named `fa` after Persian, the toolbox's first language: it holds the
  caption's text in the target language, whatever that language is.
  Chunks split only at the language's word separator (a space; for
  Japanese, anywhere between two characters); joined back with that
  separator they must reproduce the caption exactly
  (`lib/check_part.py` enforces this). **Never correct the caption in
  `fa`** — the correction goes in `note`.
- **`kana`** — only for a language with a reading (Japanese): the
  reading of the **whole chunk** in kana, never a per-character
  alignment (`漢字を書く` → `かんじをかく`). Required on every chunk of
  the target language there; not written for the other languages.
- **`tr`** — transliteration of what is actually said, colloquial forms
  as heard, in the language's scheme (its conventions file gives it,
  and how to hyphenate transparent morphology). Required on every chunk
  of the target language for Persian, Arabic, Japanese, Hindi and Chinese
  (for Chinese it is the pinyin); optional for Italian, French, German,
  Turkish, English and Spanish, where it is a pronunciation hint — for
  the odd word in Italian, for most of them in French. The language's
  file says which.
- **`voc`** — the vocabulary line, in the voice of the books' gloss
  blocks: headword + transliteration + meaning; verbs with their stems
  or forms as the language's file shows; colloquial ↔ written pairs
  spelled out; loanwords flagged. Target-script text inside `voc` is
  fine — the player isolates it. **Optional.**
- **`en`** — the short meaning of the chunk as spoken, written in the
  video's gloss language (`video.json`'s `"gloss"`; English when it says
  none — the prompt names it), lower-case, like the books' third line
  ("there are wounds", "in solitude"). The key is named `en` after the
  first gloss language, whatever the gloss is written in. Keep the reading
  order of the caption: if a caption's sense runs across the next one, end
  with `…` and pick it up.
- **`note`** — optional, sparingly: ASR slips, garbled words, culture
  notes, sounds (`[laughter]`). The caption stays wrong in `fa`; the
  note is where the truth goes.

## The repetition rule (Frank's own)

A full `voc` entry the **first time** a word appears, briefer or none on
later appearances. These teaching videos repeat one word dozens of
times: gloss it properly once, then leave it bare. By the end of a
video the common words should carry no `voc` at all — a wall of repeated
glosses is worse than none.

Use the per-video word list beside this file for the words that recur:
gloss them the first time **in the whole video** (batch 1 usually), and
after that only when the form itself is new (a new tense, a new clitic).

## Plain captions, and another language inside a caption

For a language written in its own script (Persian, Arabic, Hindi,
Japanese, Chinese) a caption with **not one character of that script** —
the framing these teaching videos open with, usually in English — is
*plain*: the pipeline fills it in from the transcript and it is not in
your batch at all. A run with no
target script *inside* a caption (`welcome to a new session of`) is one
chunk with **only `fa`** — no `tr`, no `en`. The player shows it as plain
text and never offers it as a card.

For a Latin-script language (Italian, French, German, Turkish, English,
Spanish) the software cannot tell an aside in another language from the
target by its letters, so **every caption wants glossing**, and such an
aside — a
whole caption of it, or a run inside one — is a chunk carrying
`"plain": true` beside its `fa`, and nothing else. Only there may an
annotator write `plain`; for a script language it exists solely for
imports from the older format. A chunk left with no gloss is not plain:
it is a chunk still to be glossed, and the software counts it as one —
so gloss every chunk that is not plain.

## The output

*This is the shape of a batch file, `parts/NN.json`, for a video written
by hand from `youtube/PROMPT.md`. The add page's prompt asks for a shape
of its own — one JSON object holding `video` and `captions`, each caption
with its `i` — and shows it after these conventions: answering that
prompt, follow that one.*

A part file is a JSON **array**, one entry per caption, in order:

```json
[ {"start": 27, "chunks": [ {"fa": "…", "tr": "…", "voc": "…", "en": "…"} ]} ]
```

with `"kana": "…"` on every chunk when the language has a reading:

```json
[ {"start": 27, "chunks": [ {"fa": "…", "kana": "…", "tr": "…", "voc": "…", "en": "…"} ]} ]
```

Nothing else: no `text`, no `plain` on a caption, no `chapter` —
`merge_parts.py` fills those from `transcript.txt`.

## The colour mark

A chunk in a finished `annotations.json` may also carry **`col`** —
`"red"`, `"blue"`, `"orange"` or `"green"`, and nothing else. It is the
*reader's* own mark on a phrase, the same four colours the reading
editions under `../books/` pass as the first argument of `\ch`: a word to
come back to, a construction not learnt yet, a mistake made twice. Absent
or empty means unmarked. No tool reads any meaning into it, and it does
not travel into the Anki card the chunk makes — a coloured chunk in a
book makes an ordinary card too.

**It is never written in a part file, and never by an annotator.** A
colour is added later, from the player, by whoever is reading;
`merge_parts.py` copies no such key, and nobody writing a gloss can guess
which phrases a stranger will want to mark. It is set down here because
it appears in a finished file, and someone editing that file by hand —
find-and-replace, a real editor — should know what the key is and that a
fifth colour is an error `check_annotations.py` will stop on.

## The mark that frees a caption from the transcript

A chunk in a finished `annotations.json` may also carry **`free`** — the
value `true`, or the key is not written at all. It says: *this phrase is
the annotator's, not YouTube's.*

The pasted `transcript.txt` is what YouTube heard, and it is sometimes
wrong — a name misheard, a particle dropped, a homophone. Two checks
normally hold the file to it: every chunk of a caption joined must give
the caption's `text` back, and that `text` must equal the transcript's
line. That is what stops a model, or a careless find-and-replace, from
quietly rewriting the video. But it also means a wrong transcript cannot
be corrected at all, which is the wrong answer for the one case where the
annotator is right and YouTube is not.

Marked, the caption is taken out of the second check only: the caption is
reported as *not checked against `transcript.txt`* — a warning naming how
many captions were skipped, not an error — and its `text` is written from
its own chunks. The first check still holds: the chunks must still
reproduce the text they now make, so the file stays true to itself.

It is asked of the CAPTION and answered by any of its chunks, because the
comparison is of the whole caption: one phrase departing takes its
caption with it. The reading editions under `../books/` keep the same
rule one door over, per paragraph, in `reading.json` (`lib/reading.py`).

**Never written in a part file, and never by a draft.** Like `col` it is
set later, from the player: the editor's `the transcript` box, *this
phrase need not reproduce `transcript.txt`*, sent with the edit it
permits. `annwrite.py` refuses an edit that departs from the transcript
without it, and refuses taking it off a caption whose text has departed —
put the words back and clear the box in the same save.
