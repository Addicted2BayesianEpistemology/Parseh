## The folder and the three files you keep

The book's folder holds, when it is finished:

```
book.json, main.tex        what the book declares, and how the batch files are \input
original/                  the source text the book is made from, and every part added later
source/clean.txt           one paragraph per line, the recovered text
source/paras/              one file per paragraph: chN_pNN.txt (N from 1, NN from 00), holding that paragraph's text alone, on one line, exactly as in clean.txt
source/src_chN.json        the chapter lists (chapter_src.py makes them)
annot/chN_pNN.json         the annotation, one file per paragraph -- THE GROUND TRUTH
annot/chN_batchA.json      a batch of ten paragraphs, merged and normalised (A for a chapter's first batch, then B, C ...)
chN.tex, chNb.tex, ...     one file per batch (the first batch is chN.tex, the second chNb.tex ...), built by assemble.py, never by hand
NOTES.md, ASKS.md, making.json     the journal, the person's asks, the record of the making
scratch/                   scripts of your own; nothing of Parseh's reads it
```

Keep the per-paragraph JSON, the batch JSON and your fix lists under `annot/` for ever: they are the only copy of the work, and the `.tex` can be built from them at any time.

### NOTES.md -- the journal

Parseh started it with one line; you keep it from then on, after every batch, because a session ends without warning and whoever reads it next has nothing else. Write it so that someone who has seen none of your work could go on from it. These headings, and others as the book asks:

- **The source**: what it is, how it was recovered, how you made sure it is whole, what you left out and why.
- **The table**: chapters, paragraphs, subparagraphs, chunks, source words, brought up to date after each batch. Every number comes from a command you ran, never from memory.
- **Kept on purpose**: each oddity of the source reproduced in `fa`, with the reason and where a gloss explains it.
- **Decisions**: every time the conventions leave room, or two ways were possible: what you chose, why, from which batch on. Read this before every batch.
- **Introduced so far**: the names, constructions and conventions already explained, each with its batch, so that no batch explains one again and none assumes another did.
- **Asks**: one line for each entry of `ASKS.md`: its heading, and what you did about it or why you did not.
- **Guesses**: every reading or meaning chosen with no authority to hand (a name, a dialect form, an archaic word): "chosen, not confirmed", the same choice everywhere, and where it recurs.
- **Open**: the questions for the person, the checks you could not run, what the next session should look at first.

### ASKS.md -- what the person asks

The person writes into it from Parseh's pages; you never do. An entry begins `## 2026-10-05 14:20 — what to change from now on` (an ask for the rest of the book) or `## 2026-10-05 14:20 — about a chunk` (then the chunk's address, the chunk quoted with `>`, and the person's line). Parseh also writes notices there, headed `a part was added`, `this is all the text`, `more text is coming`, `reopened` or `finished`: not asks, but read them, they say the text has changed. An ask for the rest of the book becomes a decision in `NOTES.md` from the next batch on. An ask about a chunk is about that chunk: if it is a fault, correct that chunk's JSON and assemble that one batch again; if it is a question, answer it in your own chat. When an ask goes against the method -- it would break a check, change the source's own spelling, or make the book disagree with itself -- say so in your chat and wait for the answer: do not quietly follow it and do not quietly ignore it.

### making.json -- the record of the making

One small object that you and Parseh keep between you; the panel on the book's card shows it. Its fields that are yours:

- `stage`: `source` (the original recovered), `chapters` (the chapter table written), `batch`, `done` (every part so far is in, and every batch), `waiting` (the same, and more text is coming).
- `on`: one line, what you are on now.
- `chapters`: `[{"chapter": 1, "paragraphs": 24, "part": 1}, ...]` (`part`, the part its first paragraphs came from, is optional).
- `batches`: `{"done": 3, "of": 12}`; `of` grows when a part is added.
- `checks`: what the tools last said, e.g. `{"check_batch": "0 errors", "assemble": "ALL PARAGRAPHS CLEAN", "verify_book": "clean"}`.
- `sources`: which parts of the text you have recovered, `{"done": [1, 2], "of": 3, "decided": {"2": "a new chapter: it opens with a heading"}}`; see **The text in parts**.
- `asks_read`: how many entries of `ASKS.md` you have read, notices included.
- `updated`: the time you wrote it, UTC (`2026-09-29T14:20:01Z`).

Parseh's, never yours: `state` (`making` or `finished`), `parseh` (the version it was made under), `started`, `finished`, `parts` (every part the person added, and where it goes), `more_coming`, and `instructions` (how these instructions were written). The person may write the instructions again, and Parseh may be updated, while you work: read the file again before you write it.
