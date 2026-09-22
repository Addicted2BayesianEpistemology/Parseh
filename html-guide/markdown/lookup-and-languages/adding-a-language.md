---
title: Adding a language
weight: 11
description: For whoever maintains Parseh — the one command that adds a twelfth language, what it writes, what is left to write by hand, fonts, and how to check it.
---

> **An advanced page, for the command line.** Nothing here is needed to
> *use* Parseh. A new language is a change to the program itself — a row of
> its language table and two files that go with it — so it is done in
> Parseh's folder, from a terminal, by whoever maintains the toolbox, and
> then shared like any other change to the code. There is no button for it,
> on purpose: once it is done, the language is simply there in every page.

Nothing about the number eleven is special. French, German, Turkish,
Hindi, Spanish and Chinese each arrived as one run of one command — a row
of the table and the files that go with it — because every part of Parseh
reads the table rather than keeping a list of languages of its own.

## What a language is

A language is **one row of `lib/languages.json`**, the registry, plus:

- `lib/lang/<code>.tex` — what a reading edition's LaTeX needs to know about
  it;
- `docs/lang/<code>.md` — its annotation conventions;
- three content folders, `books/<folder>/`, `youtube/videos/<folder>/` and
  `markdown/library/<folder>/`, each with a `.gitkeep` so an empty one
  survives a clone.

The fields of the row that carry a decision:

| Field | What it decides |
|---|---|
| the key | the code, two or three letters (`fa`, `ja`, `nap`): `"language"` in a book or video, `target:` in a document, `data-lang` on every page |
| `name` | the English name: the folder, babel's language, the Anki field, every label that names the language |
| `native` | what the language calls itself: what its chip shows |
| `folder`, `tag` | the content folders; the stem of the Anki tags (`<tag>-book`, `<tag>-youtube`) |
| `iso3` | the ISO 639-3 code outside sources file it under — the corpus download needs it; without it the language can have no corpus |
| `dir` | `rtl` or `ltr` |
| `script`, `chars` | the kind of script, and the character ranges its text is recognised by (a regular-expression class, compiled by both Python and the browser). **`null`** means it cannot be told from English, and every run is marked by hand in the studio |
| `word_sep` | what separates words; the empty string for a language written without spaces, where a chunk counts as one word |
| `digits` | the ten figures its labels are written in |
| `strip` | the marks the bare pass takes off (the harakat). A language with no marks to strip, no reading and no word line has no bare pass, since it would only reprint pass 1; Japanese and Chinese have none to strip and still get one, which takes the readings away |
| `reading`, `reading_label` | a second reading line beside the transliteration (Japanese's **kana**): a field on the cards, a line in every gloss, ruby in pass 1, a rule the checkers enforce |
| `words` | chunks carry a word line, each word with its reading (Japanese, Chinese) — and a reading-alone pass follows pass 1 |
| `vertical` | it can be set in columns: a vertical last pass, and the studio's `vertical` |
| `require_tr`, `translit_label` | whether every chunk needs a transliteration, and what the line is called |
| `vocal_label`, `bare_label` | what pass 1 and the bare pass are called |
| `vb_forms`, `vb_labels` | what a verb entry's three forms are, and the two labels it prints ([Verb entries](language-by-language.md#verb-entries)) |
| `vb_video_bare` | a video's verb entries written without the marks (Arabic's are unvowelled); set by hand, there is no flag |
| `fonts`, `tex` | the faces on screen (the CSS stacks, and any `.woff2` that travels with Parseh) and on paper (babel's and fontspec's names, the faces to try in order, the hyphenation) |
| `passes` | the reading edition's passes, with their titles — worked out from the fields above |
| `anki` | the two note-type ids and names, and the first field's name. **The ids are what Anki matches note types by, and must be this language's alone, forever** |
| `duration_units`, `chapter_words` | the words a transcript uses for seconds, minutes, hours and chapters |

## The one command

`lib/newlang.py` writes all of it. Run from Parseh's folder:

```bash
python3 lib/newlang.py                 # what it needs, and the languages there are
python3 lib/newlang.py --check         # every language validated, every file present
python3 lib/newlang.py --help          # every flag
python3 lib/newlang.py ko --name Korean --native 한국어 --script other \
    --chars '\uAC00-\uD7AF\u1100-\u11FF' --font 'Noto Serif KR' --iso3 kor
```

It asks for nothing it can work out — the folder, the tag, babel's name,
the passes and their titles, the labels, and the next free pair of Anki
ids, checked against every id in the table and every retired one — and
works out nothing you ought to decide. The flags that carry a decision:

| Flag | |
|---|---|
| `--name`, `--native` | required: the English name and the language's own |
| `--script KIND` | the kind of script: `arabic`, `devanagari`, `latin`, `cjk` or `other` (default `latin`). It picks the direction, `chars`, `word_sep`, `digits`, `strip`, whether a transliteration is required and what the line is called |
| `--chars RANGES` | the script's ranges, as a regular-expression class (`'\uAC00-\uD7AF…'`); required with `--script other`, and the way to narrow a kind (Chinese's class is the `cjk` one without the kana) |
| `--dir rtl`, `--dir ltr` | when it is not the script's usual direction |
| `--digits`, `--word-sep`, `--strip` | to override what the script kind gave |
| `--require-tr`, `--no-require-tr` | whether every chunk needs a transliteration, when the script kind's answer is wrong (only `latin` makes it optional, since there the line is a pronunciation aid) |
| `--iso3` | the ISO 639-3 code, for the corpus download |
| `--reading`, `--reading-label` | a reading beside the transliteration, and what it is called (`kana`) |
| `--words` | chunks carry a word line (only for a language written without spaces) |
| `--vertical` | it can be set in columns |
| `--folder`, `--tag` | the content folder and the Anki tag stem, when the ones the English name gives are taken or are not a folder name — the refusal says which to give |
| `--font`, `--font-fallback` | the face on paper and on screen, and faces to try when it is missing |
| `--css-font` | the whole CSS stack, when the one built from `--font` is not right |
| `--web-font` | a face bundled in `lib/fonts/`, by its `.woff2` file name (repeatable) |
| `--alt-font`, `--alt-key` | a second face (Persian's nastaliq): the title, the chapter numbers and a pass of its own; the key is what a studio block calls it, `font=<key>` |
| `--alt-line-height` | the leading the second face needs on screen (Persian's nastaliq asks for 2.6) |
| `--translit-label`, `--vocal-label`, `--bare-label` | what the lines and passes are called |
| `--vb-forms`, `--vb-labels` | the verb entry's three forms and two labels, each comma-separated |
| `--hyphen`, `--import`, `--babel`, `--tex-language` | LaTeX's names, when the defaults are wrong |
| `--anki-field`, `--duration-units`, `--chapter-words` | the rest of the row |
| `--dry-run` | print the row that would be added, and write nothing |
| `--force` | overwrite the `.tex` and the `.md` if they are already there |

It **refuses**, and writes nothing, for a code that is taken or is not two
or three lower-case letters, a folder or a tag another language has, a
`chars` that does not compile in both Python and JavaScript, `--script
other` without `--chars`, `--reading` on a script that cannot be
recognised, `--words` on a language written with spaces, `--digits` that
are not exactly ten, and verb labels carrying a character LaTeX would read
as syntax. A font the machine does not have is only a **warning**: the row
may be written on one machine for another.

What it said for Korean:

```text
adding Korean (ko, 한국어) to Parseh

warnings (none of them stopped anything):
  - --font 'Noto Serif KR' is not on this machine.  Kept: the entry may be for another one, and \FrankPickFont falls through tex.main_fallbacks.

  lib/languages.json   entry added after zh:
      folder korean/   tag korean   dir ltr   script other   digits Latin
      passes: 1 (the sentence), 2 (chunks and glosses)
      fonts:  main Noto Serif KR, alt none, bundled none
      anki:   1724563200121 / 1724563200122 (slot 12), field Korean
  lib/lang/ko.tex      written
  docs/lang/ko.md      written
  books/korean/        made, with .gitkeep
  youtube/videos/korean/ made, with .gitkeep
  markdown/library/korean/ made, with .gitkeep
```

## What is left to write by hand

The command fills in the shape and not the prose, and it ends by listing
what is yours:

1. **`\FrankHowTo` in `lib/lang/<code>.tex`** — the “How to read this” page
   at the front of every printed book: what each pass is for, and what the
   marks of the transliteration mean. It is written with a placeholder, so
   a book builds meanwhile; `lib/lang/fa.tex` is the voice to follow. For a
   language with a reading, words or a vertical pass, the file also has
   **TODO** blocks — the ruby over a word, the reading pass, the rotated
   columns — to copy from `lib/lang/ja.tex` and `zh.tex`; copy them rather
   than writing your own, since both are tuned against real pages.
2. **`docs/lang/<code>.md`** — the conventions, in six sections (below).
3. **A fixture**, if the test suite is to cover the language: a small book
   under `tests/fixtures/books/<folder>/`, a video under
   `tests/fixtures/videos/<folder>/`, a card in `tests/fixtures/anki/`. The
   smoke test only tries a language it has a fixture for.
4. **A starter document**, `markdown/exlex/starters/<code>.md` — the page the
   studio's **+ New** opens on for this language, showing the marks it
   really uses. Until it exists the studio builds a plain one from the row.
5. **A verb recipe**, `lib/verbs/<code>.py`, which reads a dictionary entry
   and returns the language's three verb forms, with an optional table of
   exceptions in `lib/lang/<code>.verbs.json`. Without it nothing breaks:
   the editor's sources offer every verb as a plain word (`\dw`) instead of
   a whole `\vb`. Try one with `python3 lib/verbs/__init__.py <code> "<a
   sentence>"` and pin it with cases in `tests/fixtures/verbs/<code>.json`.

A language with marks to strip is also reminded that `vb_video_bare` has to
be set by hand if its videos are written without them. Other files a
language may have, read only where they exist: `lib/lang/<code>.lookup.json`
(the dictionary's rules for what is written onto a word), `<code>.ipa.json`,
`<code>.chunk.json`, and for a worded language `<code>.words.json`.

### The conventions file

`docs/lang/<code>.md` starts from `docs/lang/_template.md` with the
language's name, labels and verb forms filled in. It is **instructions to an
annotator** — and the annotator is usually a model: the video prompt and the
new-book prompt paste it in whole when that language is chosen. Keep all six
sections, even one that only says the language has no such thing:

1. **The text field** — what `fa` must reproduce, verbatim, and what it
   must never silently correct. The fidelity checks are measured against it.
2. **Reading** — the reading rule, or one line saying there is none.
3. **Transliteration** — the scheme, letter by letter, and what is
   hyphenated: an annotator with only this file must write the line another
   one would.
4. **Vocabulary** — what a gloss carries, and the three forms of a verb in
   the order `\vb` prints them.
5. **Never gloss** — the function words that never get an entry, as a list.
6. **Chunking** — how big a chunk is, and what must never be split.

`\FrankHowTo` says the same things to the reader; the two must agree. The
nearest existing file is the one to model yours on: `docs/lang/it.md` for a
Latin-script language that spells itself, `fr.md` where the spelling hides
the sound, `fa.md` or `ar.md` for an Arabic script, `ja.md` for a reading,
`zh.md` for words without a reading.

## Giving it a font

**If the device can be trusted to have the face**, name it with `--font`
and its fallbacks, and nothing else is needed: a Latin-script language
needs no face at all (it is set in the toolbox's roman), and the CJK
languages name the system's faces rather than carrying tens of megabytes.

**If it cannot**, the face travels with Parseh:

1. put the **`.woff2`** in `lib/fonts/` for the pages, and the **`.ttf`**
   or `.otf` beside it for LaTeX;
2. name the `.woff2` in the row's `fonts.web_files` — `--web-font` does
   that, and warns if the file is not in `lib/fonts/` yet;
3. declare it once with `@font-face` in `lib/parseh.css` and once in the
   studio's `markdown/app/static/app.css`, beside the four already there;
4. check its licence allows it: the four bundled faces are under the SIL
   Open Font License;
5. record the licence, so that the font travels with it: a row in
   `lib/fonts/README.md`, the font's copyright line in `lib/fonts/OFL.txt`
   (or a licence file of its own beside the font, if it is not under the
   OFL), and an entry in `FONTS` in `lib/notices.py`, which draws the
   **Licences** page. `tests/test_licences.py` fails until all three name
   it ([Licences and credits](../reference/licences.md)).

The CSS stacks themselves need no editing: the per-language stylesheet
every page links is generated from the registry when Parseh starts.

## Checking it

```bash
python3 lib/newlang.py --check       # every language: files, folders, fonts, ids, ranges
python3 tests/smoke.py               # the regression run, every renderer
python3 tests/smoke.py --pdf         # ... and the LaTeX builds (minutes)
```

`--check` walks the **whole** registry and prints a line for everything it
looked at: the `.tex` and the `.md`, that the verb labels and the passes in
the registry and the `.tex` agree, the three folders, that babel has the
locale, the fonts, the bundled files, that the Anki ids are the language's
alone, that `chars` compiles. A **MISSING** line is a fault — a missing
file, a shared Anki id, a range that does not compile, labels that
disagree — and makes it exit with a failure. A **note** is not: a folder
that does not exist yet, a font this machine lacks, a locale this TeX
installation has not got. `--strict` counts the notes as faults too.

```text
  ko  Korean (korean)
      ok       lib/lang/ko.tex (the reading editions' preamble)
      ok       docs/lang/ko.md (the annotation conventions)
      ok       vb labels 'pres.' / 'past': the registry and the .tex agree
      ok       vb forms: dictionary form / second form / third form
      ok       passes vocal/chunks: the registry and the .tex agree
      ok       books/korean/, youtube/videos/korean/, library/korean/
      ok       babel imports 'ko', which is installed
      note     tex.main 'Noto Serif KR' is not on this machine and no fallback is either
      ok       Anki ids 1724563200121 / 1724563200122 are this language's alone
      ok       chars: compiles in Python and JS

12 languages: 0 faults, 1 note.
```

## After that

Restart Parseh, and the language is everywhere a language is chosen: the
**Language** selects of **Add a book** and **Add a video**, the studio's
LLM prompt page, a new exercise deck, the gloss selects. Its chip appears
on a page as soon as that page has something in it. The
[reading-help page](reading-help.md) has a row for it in each section:
its dictionary is fetched from kaikki.org by its English name, its corpus
from Tatoeba by its `iso3`, and a translation model exists only if Mozilla
offers one between it and English. (The character components are for
Japanese and Chinese alone.)

The quickest proof that it works end to end is a video: **Add a video**,
choose the language, and the prompt it copies carries your conventions
file. The real test is a book, the one door that goes through LaTeX —
build its first chapter early, because `lib/lang/<code>.tex` is proved by
nothing until LaTeX has read it.

## Three examples

**A Latin-script language** is the easy case — six of the eleven are:

```bash
python3 lib/newlang.py sv --name Swedish --native svenska --script latin \
    --iso3 swe --hyphen swedish
```

Two passes, *the sentence* and *chunks and glosses*; an optional
*pronunciation* line; no font, no ranges, no marks to strip. What is left is
the prose: `\FrankHowTo` and the six sections.

**A right-to-left language with its own digits and a face to carry:**

```bash
python3 lib/newlang.py ur --name Urdu --native اردو --script arabic \
    --font "Noto Nastaliq Urdu" --web-font NotoNastaliqUrdu.woff2 \
    --alt-font "Noto Naskh Arabic" --alt-key naskh \
    --digits "۰۱۲۳۴۵۶۷۸۹" --iso3 urd
```

`--script arabic` gives right to left, the Arabic ranges and the harakat to
strip, so the row has a bare pass; `--alt-font` adds a fourth pass in the
second face; `--digits` puts the Persian figures in place of the Arabic
ones. Nastaliq is already in `lib/fonts/`, because Persian uses it — a face
that is not needs the four steps above.

**A script of its own:** the Korean example above — `--script other` and
the Hangul ranges. And **a language written without spaces** adds `--words`
(each chunk then carries its words and their readings, and gets a
reading-alone pass) and, if it can be set in columns, `--vertical`; the
scaffold then leaves TODO blocks in the `.tex` to copy from `ja.tex` and
`zh.tex`.

> **Never type an Anki note-type id by hand.** The command allocates the
> next free pair and checks it against every id in the table and every
> retired one, which is the whole reason to let it. An id that collides
> with another language's breaks nothing in Parseh — it breaks inside
> Anki, months later, by quietly merging two note types and the cards
> under them.
>
> **Removing a language needs one more line.** Its row takes its ids out of
> the table with it, so the grid would look free where it is not — and
> anybody who ever synced a deck of that language still has those note
> types in Anki. So when you remove one, add its two ids to
> `RETIRED_ANKI_IDS` in `lib/newlang.py`, with the language and the date
> beside them. Pali's pair (slot 9, `1724563200091` / `1724563200092`) is
> already there, which is why the Korean above got slot 12 and not slot 9.
> The command then never hands a retired pair out again, and `--check`
> calls any row that uses one a **MISSING** fault (*the Anki id … is
> already retired*).

`docs/languages.md` is the design underneath all of this.
