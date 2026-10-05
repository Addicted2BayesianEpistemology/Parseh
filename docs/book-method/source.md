## The source text

Everything after this step is checked against the paragraph files you make here, and the checks compare your annotation with them, not with the original: a recovery that lost or changed something passes every later check. So this is the step to be slow in, and the paragraph division is the one thing worth agreeing on first, because everything after it is mechanical to redo and this is not.

### 1. Recover it

Parseh's own tool reads a PDF with a text layer, an epub and a plain text file alike (the original is part 1; later parts go the same way, see **The text in parts**):

```bash
{{PYTHON}} {{LIB}}/sourcetext.py "{{ORIGINAL}}" {{PAGE_ARGS}} --lang {{LANG}} --out {{BOOK_DIR}}/source/clean.txt --paras {{BOOK_DIR}}/source/paras --tag ch1
```

It writes `source/clean.txt` (one paragraph a line) and one file a paragraph, `source/paras/ch1_pNN.txt`, all in chapter 1 for now, and says what it found: an epub's headings, pages where the paragraph breaks may be wrong, a PDF with no text layer.

**A PDF with no text layer is a scan, and you stop there.** Do not read it with an OCR of your own and annotate the result: OCR confuses letters in systematic ways, and in a learning edition every such error is a word the learner memorises that does not exist. Tell the person and ask for a text version: an epub, a plain text, or a PDF with a text layer.

### 2. Read what came out against the original

Open the original at its beginning, its end and one place in the middle (for a PDF: its first page, its last and one between), and read them beside `clean.txt`: the opening, the ending, a stretch of running text, a stretch of whatever the book has in quantity (speech, verse, a list). Count what can be counted -- the turns of speech, the verses -- in the original and in `clean.txt`. A text whose speech sits in another kind of line than its narration can come out as narration alone, fluent and wrong, and nothing is malformed to give it away.

Then read the recovered text with a script of your own (in `scratch/`) that prints, and read what it prints before you act on it: invisible characters and bidi marks, the kinds of apostrophe, quotation mark and dash and how many of each, double spaces, a space before a stop, lines made of marks alone, characters outside the language's own alphabet, and whatever else **The conventions of {{LANG_NAME}}** say its script is prone to. Never "tidy" a character with a tool that smartens or folds it (a quotation mark, an apostrophe that is part of the word, a capital the language does not fold as English does): the book reproduces the source's own.

### 3. What is the text, and what is the recovery's

Sort every oddity into one of three, and write the sort in `NOTES.md`:

- **The edition's own**: an old or irregular spelling, two spellings of one word, a space where the modern text has none, a word joined that is usually apart, odd punctuation. It is the text: keep it in `fa`, name it in the vocabulary line where it would mislead a learner, never correct it.
- **A recovery artefact you can repair with certainty**: a mark left apart from its letter, a word cut by a space the page does not have, a paragraph repeated with one glyph different, a running header, a page number. Repair it in `source/clean.txt` and in the paragraph file together, write the before and the after in `NOTES.md`, and make the chapter lists again. The original decides which of the two an oddity is: what you can see in it, a space between two letters of a word included, is the edition's even where the same word is written whole elsewhere. Where you cannot tell, keep it as it stands, note it, and ask. A word the edition itself splits by a real space is one chunk, never two (a boundary between the halves would insert a space the source has), and its transliteration is that of the one word it is.
- **An artefact you cannot repair with certainty** (punctuation put in the wrong order by a right-to-left layer, say): reproduce it as it stands, do not explain it in a gloss, and list it in `NOTES.md` so the person can decide.

Look at both ends of the text. A digitiser's title page, edition note, website address, a colophon, "the end": not the author's text, and when the same line wraps the text at both ends it is certainly a colophon. Leave such lines out and say so in `NOTES.md`; when you cannot tell, ask.

### 4. Paragraphs and chapters

A paragraph is the source's own, a line of `clean.txt`. Divide the chapters where the source does -- its headings, numerals and ornaments, not the page numbers of its running heads -- by renaming the files: the paragraph that opens chapter 2 becomes `ch2_p00`, the next `ch2_p01`, each chapter numbered from 00 without a gap; `clean.txt` stays as it is. A source with no divisions is one chapter. Then make the chapter lists, which `assemble.py` checks every batch against:

```bash
{{PYTHON}} {{LIB}}/chapter_src.py --book {{BOOK_DIR}} --all
```

Make them again whenever a paragraph file changes: a batch built on a corrected source fails against a stale list, which is the check doing its work.

**Never merge or split a source paragraph silently.** Count: the paragraph files of all the chapters are as many as the lines of `clean.txt`, unless you decided otherwise and wrote why. An edition once shipped a paragraph file that held a long run of speech turns: nothing failed, and its contents list showed one entry for pages and pages of text.

### 5. Record it, and show it

Write in `NOTES.md` the table (chapters, paragraphs, words) and every oddity, put the table in `making.json` (`chapters`, `stage`: `chapters`) and show it to the person in your own chat. If the person answers, follow the answer; if nobody can be asked, go on and say in `NOTES.md` that the table was not confirmed.
