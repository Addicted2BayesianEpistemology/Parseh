## The batch recipe

A batch is {{BATCH}} paragraphs of one chapter, in the source's order (the last batch of a chapter has what is left: a chapter of three paragraphs is one batch of three). The first batch of chapter N is `chN.tex` (its batch JSON `chN_batchA.json`), the next `chNb.tex` (`chN_batchB.json`), then `chNc.tex` ... Every batch but the chapter's last is assembled with `--partial`; every batch but the chapter's first with `--no-open`.

### Who does what

Three jobs, each done by someone who did not do the one before it:

- **The annotator** writes `annot/chN_pNN.json` for a paragraph (short paragraphs may be grouped; one of 500 words or more gets an annotator of its own), runs `check_batch.py` until it says 0 errors, and answers every warning and note. This is the irreducible cost: do not skimp on it, because what comes after is meant for what the tools cannot see.
- **The proof-reader** reads one paragraph's JSON, never one it wrote, for the first three errors of **The errors no tool finds** and nothing else, and reports each finding as `{"idx": NN, "chunk_fa": "...", "field": "fa|tr|voc|en", "proposed": "...", "why": "..."}`. Do not spend a reader on what `check_batch.py` already says (the conventions, the never-gloss list, repeated entries): a reader sent to check conventions re-derives the checker's output.
- **The sceptic** reads the findings of the whole batch once, re-reads the JSON itself rather than trusting a finding's own quotation of it, and confirms or rejects each. It rejects taste, rejects anything that would change the source's own spelling, and rejects a "fix" that the conventions say is deliberate. About a third of what readers raise is rejected, which is why this job stays.

If you can start helpers (sub-agents), give each annotator its paragraphs and each proof-reader its paragraph, run them in parallel, and take the sceptic's job yourself or give it to one more helper: two helpers on every paragraph and one sceptic a batch is what the method settled on, and four on every paragraph cost three times as much for the same findings. If you cannot, do the paragraphs one after another and the proof-reading as a pass of its own, after the batch is annotated, reading the JSON alone with fresh eyes: not in the same breath as writing it.

**The brief a helper needs**, because it has read nothing: this file's path and which parts to read (**The chunk and what you write in it**, **The meaning of a chunk**, **The conventions of {{LANG_NAME}}**); its paragraphs' file names, with the paragraph before and the first sentence after (a chunk read alone is where the worst errors come from); the oddities you found in the pre-check, to be kept on purpose; the "Decisions" and "Introduced so far" of `NOTES.md` -- helpers working at the same moment cannot see each other, and each would otherwise explain the same character again and assume another introduced the same word; the command to run, by its full path; and that it writes only its own JSON, inside this folder.

### The steps of a batch

For chapter N, paragraphs a ... a+{{BATCH_LAST}} (0-based, as the files are numbered):

1. **Read again** `ASKS.md`, `making.json` (a part may have come: **The text in parts**) and the "Decisions" of `NOTES.md`.
2. **Pre-check the source range**: read the paragraphs yourself and run your census on them (**The source text**): unexpected characters, marks beside a space, run-together words, whatever the conventions list for {{LANG_NAME}}. Write the oddities into `NOTES.md` (Kept on purpose) so they are preserved on purpose and not by luck.
3. **Annotate each paragraph**: write `{{BOOK_DIR}}/annot/chN_pNN.json` in the shape of **The chunk and what you write in it**. {{WORDS_STEP}}Iterate against

   ```bash
   {{PYTHON}} {{LIB}}/check_batch.py {{BOOK_DIR}}/annot/chN_pNN.json --book {{BOOK_DIR}}
   ```

   until it prints **0 errors**, then answer every warning and every note: fix it, or be able to say in a sentence why it is right. A note is the checker saying what it did not check; what it does not check for {{LANG_NAME}} is yours (**How to check**).
4. **Proof-read** each paragraph, as above.
5. **Confirm or reject** each finding, as above. Only confirmed findings go into a `fixes.json` you write in `annot/`; with none, give `-` to `merge_batch.py` in its place. An empty list from a helper that failed is not a clean bill of health: check that every proof-reader and the sceptic really ran.
6. **Merge, normalise, assemble**:

   ```bash
   {{PYTHON}} {{LIB}}/merge_batch.py --book {{BOOK_DIR}} {{BOOK_DIR}}/annot/chN_batchX.json {{BOOK_DIR}}/annot/fixes.json {{BOOK_DIR}}/annot/chN_pNN.json ...      # this batch's paragraphs, each named
   {{PYTHON}} {{LIB}}/normalize_batch.py --book {{BOOK_DIR}} {{BOOK_DIR}}/annot/chN_batchX.json {{BOOK_DIR}}/annot/chN_batchX.norm.json
   {{PYTHON}} {{LIB}}/assemble.py --book {{BOOK_DIR}} {{BOOK_DIR}}/annot/chN_batchX.norm.json {{BOOK_DIR}}/source/src_chN.json "{{LANG_DIGIT_EXAMPLE}}" {{BOOK_DIR}}/chNx.tex --partial --no-open
   ```

   The third argument of `assemble.py` is the chapter's label **in {{LANG_NAME}}'s digits** (chapter 3 is written `{{LANG_DIGIT_EXAMPLE}}`); `--partial` unless this batch closes the chapter, `--no-open` unless it opens it (a chapter of one batch takes neither). `X` is the batch's capital letter (A, B, C ...) and `chNx.tex` is `chN.tex` for A, `chNb.tex` for B, `chNc.tex` for C ... `assemble.py` refuses a batch that does not reproduce the source; it must end with `ALL PARAGRAPHS CLEAN`, and a `.tex` it wrote on problems is not to be used. Give `merge_batch.py` only the paragraphs of THIS batch, by name: a glob that also catches an older batch's paragraphs merges them twice. A fix must match exactly one chunk, and the tool refuses one that does not: where a chunk's text stands twice in a paragraph, make that fix in the paragraph's own JSON and merge again.
7. **Sweep** the batch against the ones before it, now, while it is one batch and not the whole book (**How to check**).
8. `\input{chNx.tex}` in `main.tex`, in order, with a comment naming the paragraphs.
9. **Look at it** (where typesetting works): `sh {{ROOT}}/build.sh {{BOOK_REL}} --draft chNx` typesets just that file in seconds, and `frankdraft.log` beside it says what LaTeX thought: no overfull boxes. Read a page of the PDF's text after the front matter (Parseh's Python has PyMuPDF: `{{PYTHON}} -c "import pymupdf; print(pymupdf.open(r'{{BOOK_DIR}}/frankdraft.pdf')[N].get_text()[:600])"`) and confirm a chunk row shows the {{LANG_NAME}} *and then*, where the chunk has one, its {{TR_LABEL}}: a row with the transliteration but without the {{LANG_NAME}} means the text never reached the page, whatever the log said.
10. `{{PYTHON}} {{LIB}}/verify_book.py --book {{BOOK_DIR}}` -- every built paragraph reproduces its source.
11. **Record it**: keep the per-paragraph JSON and the batch JSON under `annot/` for ever; append what the batch taught you to `NOTES.md` (what was kept on purpose, the decisions, what is now introduced, the guesses, the table); write `making.json` (`stage`: `batch`, `batches`, `checks`, `on`, `asks_read`).

Then the next batch, after reading `ASKS.md` again. A confirmed fix to a batch already built goes into its JSON, and that one batch is assembled again (6 to 10) -- nothing else is touched.
