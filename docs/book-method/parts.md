## The text in parts

The person may give the text a bit at a time, from any device, as files or pasted. The original is **part 1**; every part is an entry of `parts` in `making.json` (Parseh writes it, with `more_coming`: never you): its `n`, its `file` in `original/`, its PDF `pages`, its `label`, and where it goes -- `chapter` is `new` (a chapter of its own), `last` (more of the last chapter) or `auto` (you decide from the text), and `join` is `paragraph` when the part was cut in the middle of a paragraph and its first paragraph goes on the last one of the part before.

**Before every batch**, with `ASKS.md` (a new part is noted there too), read `making.json` again and take, in order, every part whose `n` is not in `sources.done`:

1. Look at it first -- `--look` writes nothing, and `--book` lets the tool number the paragraphs on from what the book holds:

   ```bash
   {{PYTHON}} {{LIB}}/sourcetext.py "{{BOOK_DIR}}/original/part-002-name.pdf" --lang {{LANG}} --from A --to B --book {{BOOK_DIR}} --look
   ```

   (`--from`/`--to` only for a PDF with `pages`.) It says how many paragraphs there are and what to look at: an epub's headings, a text that starts in lower case, a book whose last paragraph ends without a full stop. Hold the part to the care the original had, as **The source text** says: read what came out against the part's own pages, count what can be counted, sort its oddities, and stop at a scan.
2. Decide what `auto` leaves to you: a heading opens a new chapter; a start in the middle of a sentence is a part cut in the middle of a paragraph. A part may hold several chapters: split it where the source does. Write what you decided, part by part, in `NOTES.md`.
3. Recover it: the same command without `--look`, with `--chapter new`, `last` or a chapter's number. It writes `source/paras/chN_pNN.txt` and adds to `source/clean.txt`. Run it once: run again, it would put the part in twice. For a part cut in the middle of a paragraph, join its first paragraph to the last one of the part before (the file and `clean.txt`) and annotate THAT paragraph again: its source changed, so its batch is redone (merged, normalised, assembled and verified again, as **The batch recipe** says).
4. Make the chapter lists again (`chapter_src.py --book {{BOOK_DIR}} --all`), bring the chapter table in `NOTES.md` and `making.json` (`chapters`; `batches.of` grows) up to date and show it to the person in your own chat, as after the first step.
5. Write `sources`, which is yours alone: `{"done": [1, 2], "of": 3, "decided": {"2": "a new chapter: it opens with a heading"}}`.

Then the batches of the new paragraphs, as the batch recipe says; a part never changes the numbering of what is already annotated. When every part is in `sources.done` and every batch is in: with `more_coming` false, write `stage`: `done`, say **the text is complete** and stop (Finish is the person's); with it true, write `stage`: `waiting`, say you are waiting for the next part, and read `making.json` again when you are told one has come.
