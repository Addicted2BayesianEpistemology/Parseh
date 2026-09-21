# Make an Ilya Frank reading edition of {{TITLE_LATIN}} ({{TITLE}}) by {{AUTHOR_LATIN}}, in {{LANG_NAME}}, glossed in {{GLOSS_NAME}}

You are Claude Code, working in `{{FOLDER}}` — a folder made for this one
book. It holds the tools of a toolbox called Parseh and **one finished
edition to learn from**; nothing else. Read this whole prompt, then read
`books/{{REF_PATH}}/NOTES.md` from beginning to end, before touching
anything. Those notes are the accumulated experience of the first edition
— every rule in them exists because something went wrong once — and the
new edition must follow the same approach, batch by batch, paragraph by
paragraph, with the same checks.{{REF_NOTE}}

The new book is in **{{LANG_NAME}}** ({{LANG_NATIVE}}, registry code `{{LANG}}`).
The toolbox teaches several languages with one method; what changes per
language — what the text field carries, the transliteration scheme, the
vowelling or reading, what never to gloss — is the language's conventions
block below, and the tools read the language from the book's `book.json`.

**Write every gloss in {{GLOSS_NAME}} ({{GLOSS_NATIVE}}).** That is the
book's second language and it is not the same question as the first:
{{LANG_NAME}} is what the reader is learning, {{GLOSS_NAME}} is what this
edition talks to them in, and `book.json` says `"gloss": "{{GLOSS}}"` beside
`"language": "{{LANG}}"`. It reaches every word you write that is not the
text itself — the `en` field, the meanings inside a `voc` line, anything you
add to explain a form. The field is still *called* `en`, after the days when
English was the only gloss there was, exactly as the text field is called
`fa` after the toolbox's first language; read it as "the meaning".{{GLOSS_NOTE}}

## What is in the folder

```
lib/                     the tools (Python 3; run them inside the conda env below)
lib/lang/                one LaTeX file per language; {{LANG}}.tex is this book's
build.sh                 typesets a book: ./build.sh <slug>, ./build.sh --draft chNx
environment.yml          the conda environment:  conda env create -f environment.yml
docs/                    audio-sync-prompt.md (only if a narration exists); lang/{{LANG}}.md, the conventions
books/{{REF_PATH}}/      THE REFERENCE ({{REF_LANG_NAME}}): {{REF_STATS}}
   NOTES.md              read first: source recovery, conventions, error classes, the recipe
   book.json, main.tex   what a book declares, and how the batch files are \input
   ch*.tex               what your output must look like — one file per batch
   source/clean.txt      one paragraph per line, the recovered text
   source/paras/         one file per paragraph: chN_pNN.txt (N from 1, NN from 00)
{{WORKDIR_LINES}}books/{{LANG_FOLDER}}/{{SLUG}}/   THE NEW BOOK: a book.json and a main.tex skeleton; source/ empty
others/{{SOURCE_FILE}}   the original text of the new book
```

Books live under `books/<language folder>/<slug>/` — the folder is the
language's (`{{LANG_FOLDER}}` for {{LANG_NAME}}), and `book.json` says
`"language": "{{LANG}}"`; the two must agree. The tools find a book from the
directory they are run in, or from `--book books/{{LANG_FOLDER}}/{{SLUG}}` /
`$FRANK_BOOK`; nothing about any one book is written into them. Run
everything with the environment active:

```bash
conda env create -f environment.yml    # once
conda activate ilya-frank
python3 lib/books.py                   # lists the books it can see: the reference and {{SLUG}}, with their languages
```

## The goal

`books/{{LANG_FOLDER}}/{{SLUG}}/` finished the way `books/{{REF_PATH}}/` is finished:

- `source/clean.txt` and `source/paras/chN_pNN.txt` — the text, recovered and divided;
- `source/src_chN.json` — the chapter lists (`lib/chapter_src.py` makes them);
- `annot/chN_pNN.json` and `annot/chN_batchX.json` — the annotation, the **ground truth**;
- `ch1.tex`, `ch1b.tex`, … — one file per batch, all built by `lib/assemble.py`, never by hand;
- `main.tex` \input-ing them in order, `book.json` describing the book;
- `NOTES.md` in the shape of the reference's: what the source needed, the decisions taken, what remains open;
- `./build.sh {{SLUG}}` producing a PDF with 0 errors and `./build.sh --html` a reader,
  and `lib/verify_book.py` proving every paragraph reproduces its source.

Every chunk of {{LANG_NAME}} in the edition must reproduce the source
**character for character {{STRIP_NOTE}}**. The tools refuse anything else,
and so must you: the source is never "corrected" (NOTES §2), its oddities
are reproduced and, where they would mislead, explained in a gloss.

## The rules the reference settled (non-negotiable, whatever the language)

1. **The JSON is the ground truth, the `.tex` is build output.** Corrections go into the JSON; the `.tex` is regenerated. Never hand-edit a `.tex`.
2. **One file per batch; a batch never rewrites one already checked.** The first batch of chapter N is `chN.tex`, the next `chNb.tex`, `chNc.tex` … Every batch but the chapter's last is assembled with `--partial`; every batch but the chapter's first with `--no-open`.
3. **Ten paragraphs per batch**, in the source's order, never a paragraph twice, never a gap. A paragraph of 500+ words is a batch member like any other, but gets an annotator of its own.
4. **Every paragraph passes `lib/check_batch.py` with 0 errors before anything else happens**, and every warning it prints is judged explicitly — fixed, or defensible in one sentence.
5. **The `fa` field is the chunk's text in {{LANG_NAME}}.** The key is named after Persian, the toolbox's first language, and is kept because every tool and every stored file uses it; read it as "the foreign text". `tr` is its {{TR_LABEL}}, `en` its meaning **in {{GLOSS_NAME}}**, `voc` the vocabulary line — also in {{GLOSS_NAME}}, apart from the {{LANG_NAME}} words it quotes.{{KANA_RULE}}
6. **The vocabulary line uses only** `\dw \vb \bw \pw \textit \nobreak \emph`. Every verb gets a `\vb`; name what was stripped (an article, a plural, an enclitic, a particle), in {{GLOSS_NAME}}; one {{GLOSS_NAME}} equivalent, not a string of synonyms; an empty `voc` is the right answer for a chunk that needs nothing. `\pw{…}` is a {{LANG_NAME}} word standing inside the {{GLOSS_NAME}}, and is what keeps it the right way round on the page. What is never glossed is in the conventions block.

   **The `\vb` is {{LANG_NAME}}'s own**, and the conventions block below is where its shape is: which three forms fill `\vb{form}{sound}{form}{sound}{form}{sound}{meaning}`, in the order the edition labels them, and which verbs get one at all. The same seven arguments in every language, and three rules that hold in every language: a **pair whose form is left empty is not printed** — neither the form nor its label — so leave one empty only where the block says that verb has no such form, never to save room and never by repeating another form in it; **what the three forms cannot say** (an auxiliary, a verb class, a governed case or preposition, an irregular participle or future) goes in **one parenthesis after the meaning**, items parted by `; `, in the block's exact words and **only where it is not the ordinary case** — `to drive (er fährt; aux. sein)` is German's, `to have (fut. \pw{tendré})` Spanish's; and a verb the block does not give a `\vb` stays a `\dw` — Chinese gives one only to a separable verb (`split`) or a verb with a complement (`can't`), English none to a modal. The form of the verb in the chunk, when it is none of the three, is named after the entry as the block shows.
7. **Read across every chunk seam** for the errors no check can find: a connective, particle or case ending dropped at a seam (NOTES §5.1 is Persian's ezafe — the shape of the error is the same in every language), a misparsed idiom (§5.2), and `fa` and `tr` agreeing on the *wrong* reading (§5.3b). A proof-reader is spent on exactly those three things and nothing else.
8. **Never apply an unconfirmed finding** (NOTES §6). A sceptic re-reads the file and rejects taste, rejects anything that would change the source's own spelling, and rejects a "fix" that the conventions below say is deliberate.
9. **A chunk is a phrase**: the smallest span that still means something on its own and that a gloss can translate as one thing. **Cut at the edges of phrases, never inside one**, and aim for **2–5 words** (the reference edition averages 2.9 source words per chunk).

   **Keep together, always** — an **adposition with its noun** (`به خانه`, `in the house`), which alone cannot be glossed at all; a **noun with everything that modifies it** (articles, demonstratives, numerals, adjectives, possessives, the {{LANG_NAME}} equivalent of the ezafe chain); a **verb with everything that makes its tense** — auxiliaries, negation, a separable prefix, the light verb of a compound (`فکر کردن`): **the unit is the verb group, not the verb**, and `می‌خواهم بروم` cut in half is two halves that mean nothing; a **word with its particles and clitics**; and a **fixed expression or idiom even where that breaks the syntax**, because the meaning is not in the pieces and showing the pieces teaches something untrue. That last one is the most valuable chunk in the book and the one only a reader of the language can find.

   **Cut, always** — at a **clause boundary**, with the conjunction or relativiser **opening** the chunk it introduces; and between **two content words with nothing binding them**.

   An **adverb joins the verb it modifies when it stands next to it**; a **sentence adverb** (`دیروز`, `yesterday`) modifies the whole clause and stands alone. An **infinitive or verbal noun used as a noun** goes with its noun phrase, not with the verbs.

   **What a chunk must not be**: not **one word per word** — that is a dictionary with the text interleaved, and the reader never learns how the language phrases anything; and not **a whole sentence** — past about six words the reader stops mapping and starts reading the translation, which is the one thing this method exists to prevent. A one-word chunk is right only where the word is the whole utterance or nothing may attach to it.

   A sentence is a subparagraph, one `\begin{frank}` each; labels are in {{LANG_NAME}}'s digits (`\parnum{{{LANG_LABEL_EXAMPLE}}}`: paragraph.subparagraph — `assemble.py` writes them).

## The conventions of {{LANG_NAME}} (`docs/lang/{{LANG}}.md`)

These are binding for every chunk of this book; where they and the
reference's NOTES.md differ, these win.

{{LANG_CONVENTIONS}}

## The reference edition's Persian rules

The rules below are **Persian's**: they are what the reference's NOTES.md
means by harakat, ezafe and the never-gloss list. They apply to a Persian
book; for {{LANG_NAME}} they are **replaced by the conventions block
above**, and they are kept here only so that the reference's notes read
correctly.

- **The harakat exist to agree with the romanisation** (NOTES §4): kasra+ya for /ey/, fatha+vav for /ow/, no sukun ever, every short vowel marked, the ezafe as a kasra on the governing word. `lib/normalize_batch.py` enforces the settled spellings; do not fight it. (Its Persian spellings run only for a Persian book; for the others it runs the generic checks.)
- Compound verbs get a `\vb` with an empty meaning plus a `\bw`; a Persian `\vb` is infinitive, present stem, past stem, with `(pres. without mi-)` after داشتن's meaning and nothing after any other; name what was stripped (indefinite *-i*, plurals, enclitics, ezafe); never gloss the ~45 function words on the never-gloss list.
- The dropped ezafe at a chunk seam (NOTES §5.1) is the one error no check can find; a sceptic remembers that /ey/ is deliberately kasra.

## Step 1 — the source text, once and carefully

If `others/{{SOURCE_FILE}}` is a PDF with a text layer:

```bash
python3 lib/extract_pdf.py "others/{{SOURCE_FILE}}" {{PAGE_ARGS}} --lang {{LANG}} \
    --out books/{{LANG_FOLDER}}/{{SLUG}}/source/clean.txt \
    --paras books/{{LANG_FOLDER}}/{{SLUG}}/source/paras --tag ch1
```

Look at what came out the way NOTES §1–2 look at the reference's: bidi
controls, presentation forms, private-use marks, a running header to
`--drop`, marks orphaned across a space, words split by a real space, and
whatever the script of {{LANG_NAME}} is prone to (the conventions block
says). Run the orphan scan from NOTES §2 on the result where it applies.
If the original is an epub or plain text, recover `clean.txt` yourself to
the same shape — one paragraph per line, the edition's own spelling kept.

Then decide the **chapter structure** from the source itself (the reference
found its chapters as `☼` marks and had to drop a digitiser's colophon at
both ends — expect something of the kind), write the paragraph files
`source/paras/chN_pNN.txt` for every chapter, and make the chapter lists:

```bash
python3 lib/chapter_src.py --book books/{{LANG_FOLDER}}/{{SLUG}} --all
```

Record the structure — a table of chapters, paragraphs and words, and every
oddity the text has — as §1–2 of `books/{{LANG_FOLDER}}/{{SLUG}}/NOTES.md`.
**Then stop and show me that table before annotating anything.** The
paragraph division is the one thing worth agreeing on first; everything
after it is mechanical to redo, this is not.

## Step 2 — annotate, ten paragraphs at a time

For chapter N, paragraphs a … a+9 (0-based, as the files are numbered):

a. **Pre-check the source range** (NOTES §8.1): unexpected characters,
   marks beside a space, run-together words, whatever the conventions block
   lists for {{LANG_NAME}}. Write the oddities into the annotators' brief so
   they are preserved on purpose.

b. **One annotator per paragraph**, in parallel — sub-agents, one paragraph
   each; group the short paragraphs under a shared annotator, give a long one
   its own. Each gets the conventions block above, writes
   `books/{{LANG_FOLDER}}/{{SLUG}}/annot/chN_pNN.json` in the schema below
{{WORDS_STEP}}   and iterates against

   ```bash
   python3 lib/check_batch.py books/{{LANG_FOLDER}}/{{SLUG}}/annot/chN_pNN.json --book books/{{LANG_FOLDER}}/{{SLUG}}
   ```

   until it prints **0 errors**, then answers every warning. This is the
   irreducible cost; do not skimp on it.

c. **One proof-reader per paragraph**, with only the three lenses of rule 7,
   reporting findings as
   `{"idx": NN, "chunk_fa": "…", "field": "fa|tr|voc|en", "proposed": "…", "why": "…"}`.

d. **One sceptic for the batch** confirms or rejects each finding, re-reading
   the JSON rather than trusting the finding's own quotation. Only confirmed
   findings go into `fixes.json`.

e. Merge, normalise, assemble:

   ```bash
   python3 lib/merge_batch.py     --book books/{{LANG_FOLDER}}/{{SLUG}} books/{{LANG_FOLDER}}/{{SLUG}}/annot/chN_batchX.json fixes.json books/{{LANG_FOLDER}}/{{SLUG}}/annot/chN_p*.json   # this batch's ten
   python3 lib/normalize_batch.py --book books/{{LANG_FOLDER}}/{{SLUG}} books/{{LANG_FOLDER}}/{{SLUG}}/annot/chN_batchX.json books/{{LANG_FOLDER}}/{{SLUG}}/annot/chN_batchX.norm.json
   python3 lib/assemble.py        --book books/{{LANG_FOLDER}}/{{SLUG}} books/{{LANG_FOLDER}}/{{SLUG}}/annot/chN_batchX.norm.json books/{{LANG_FOLDER}}/{{SLUG}}/source/src_chN.json "{{LANG_DIGIT_EXAMPLE}}" books/{{LANG_FOLDER}}/{{SLUG}}/chNx.tex --partial --no-open
   ```

   The three tools, like every tool of the pipeline, take the book from
   `--book` (or `$FRANK_BOOK`, or the directory they are run in): run from
   the root, they need it said.

   The third argument of `assemble.py` is the chapter's label **in
   {{LANG_NAME}}'s digits** (`{{LANG_DIGIT_EXAMPLE}}` is 3); `--partial`
   unless this batch closes the chapter, `--no-open` unless it opens it.
   `assemble.py` refuses a batch that does not reproduce the source; it must
   end with `ALL PARAGRAPHS CLEAN`.

f. `\input{chNx.tex}` in `main.tex`, in order, with a comment naming the
   paragraphs — as the reference's `main.tex` does.

g. **Look at it**: `./build.sh --draft chNx` typesets just that file in
   seconds. Open the PDF's text (`pymupdf`) and confirm a chunk row shows the
   {{LANG_NAME}} *and then* its {{TR_LABEL}} — the romanisation alone means
   the Lua side failed (NOTES §9).

h. `FRANK_BOOK=books/{{LANG_FOLDER}}/{{SLUG}} python3 lib/verify_book.py` — every built
   paragraph reproduces its source.

i. Keep the per-paragraph JSON and the batch JSON under `annot/` forever;
   append what the batch taught you to `NOTES.md`.

Then the next ten. A confirmed fix to a batch already built goes into its
JSON, and that one batch is re-assembled (e–h) — nothing else is touched.

### The per-paragraph JSON

The reference's shape (Persian glossed in English; the same shape for every
language and every gloss, the `fa` field holding the {{LANG_NAME}} text and
`en` the {{GLOSS_NAME}}):

```json
{"idx": 11, "ch": 2,
 "ann": {"sentences": [
   {"chunks": [
     {"fa": "پایِ بَساطِ تَریاک", "tr": "pā-ye basāt-e taryāk",
      "voc": "\\dw{پای}{pāy} foot, + ezafe; \\dw{بساط}{basāt} pedlar's spread, + ezafe; \\dw{تریاک}{taryāk} opium",
      "en": "beside the opium spread"},
     {"fa": "پَراکَندِه کَردَم.", "tr": "parākande kardam",
      "voc": "\\vb{کردن}{kardan}{کن}{kon}{کرد}{kard}{}\\bw{پراکنده}{parākande}{scattered}",
      "en": "I scattered."}
   ]}
 ]}}
```
{{KANA_EXAMPLE}}
`idx` is the paragraph's 0-based index in its chapter (the `NN` of its
file), `ch` the chapter. One sentence = one subparagraph = one
`\begin{frank}`; the chunks' `fa`, joined with the language's word separator
(a space; nothing for Japanese), must equal the paragraph {{STRIP_NOTE}}.
{{JSON_EXAMPLES}}

## Step 3 — the whole book, and the hand-back

When every chapter is closed: `./build.sh {{SLUG}}` (the full PDF, twice
through LaTeX, minutes), `./build.sh --html` (the reader), `verify_book.py`
clean, 0 overfull boxes worth worrying about. Report the totals — chapters,
paragraphs, subparagraphs, chunks — and the open questions in `NOTES.md`
§10.

The finished `books/{{LANG_FOLDER}}/{{SLUG}}/` directory is copied back into
the toolbox that will serve it; nothing outside it is needed except the
original under `others/`. If I give you a narration later,
`docs/audio-sync-prompt.md` and `lib/timestamp.py --book {{LANG_FOLDER}}/{{SLUG}}`
align it; do not plan for it now.

## How to work with me

After Step 1: the chapter table, and any doubt about the division. After
each batch: which paragraphs, the check results, the sceptic's tally, the
decisions added to NOTES. Ask me only when the source itself is ambiguous —
a paragraph boundary, a chapter boundary, a defect that might be the
edition's own. Never ask whether to follow the rules above; never annotate
the same paragraph twice; never regenerate a batch that was not asked for.
