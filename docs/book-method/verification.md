## How to check

### What each tool proves, and what it does not

- **`check_batch.py`**, one paragraph: the chunks' `fa`, joined, reproduce the paragraph {{STRIP_NOTE}}; only characters LaTeX accepts, only the allowed macros with the right number of arguments and balanced braces; no required field empty. For Persian it also runs that edition's own conventions (the never-gloss list, verb stems, the pointing sweep, the seams worth a human read); for every other language that is all, and **"0 errors, 0 warnings" is not zero things to check**: it is as content with a book that glosses the same name five times as with one that does not. It says in a *note* what it did not check and why (a book in IPA skips the checks that read the usual transliteration): read every note.
- **`assemble.py`**, one batch: the fidelity of every paragraph again, against `source/src_chN.json`; the macro list and the TeX characters; no mark in `tr`; the paragraph numbers in a row; what a chunk of the language must carry (the reading, the word line). Its report goes to the error stream: read all of it. It ends `ALL PARAGRAPHS CLEAN` or `N PROBLEMS`.
- **`verify_book.py`**, the whole book: reads the built `.tex` files, groups the chunks by paragraph number, takes the marks off, and compares each paragraph with `source/paras/`. It finds what a later edit damaged: run it after any bulk change and at the end.
- **The draft PDF** shows a chunk row as it prints: the only check that reads the PDF.
- **None of them** compares the recovered text with the original, and none reads for the four errors of **The errors no tool finds**. That is your reading, and the proof-reader's.

For {{LANG_NAME}}, the conventions may state rules that no tool checks: a segmentation that must join back to the word it cuts, the letters and marks a transliteration may hold, a list of words never glossed. For each, write the ten lines that check it, in `scratch/`, and run them over every paragraph as you run the tool. Fold case the way the language does and never with a plain lower-casing (Turkish has two letters i and two capitals of them): a script that mangles the text it checks reports faults that are not there.

### The sweeps

Each batch was made apart from the others, so run these after every batch (step 7 of **The batch recipe**) and over the whole book at the end. They are string comparisons over the merged files, `annot/chN_batch*.json` (not the `.norm.json` ones), shaped `{"paragraphs": [{"idx": 3, "ann": {"sentences": [{"chunks": [...]}]}}]}`:

- the same headword (`\dw{head}{...}`) glossed with two different meanings, or spelt two ways (a capital that is only the sentence's, a form that differs by a mark);
- the same verb (`\vb{infinitive}...`) given two sets of forms, and a verb with no `\vb` at all;
- a `\pw{...}` argument over about twenty characters, which cannot break and runs off the column;
- the names and constructions explained in full in more than one batch (the "Introduced so far" of `NOTES.md` says where each was met).

A skeleton to start from, saved as `{{BOOK_DIR}}/scratch/sweep.py` and run with Parseh's Python:

```python
import collections, glob, json, re

FIELD = re.compile(r"\\dw\{([^{}]*)\}\{[^{}]*\}\s*([^;\\]*)")
VERB = re.compile(r"\\vb\{([^{}]*)\}((?:\{[^{}]*\}){5})\{")      # the infinitive, then forms and sounds, not the meaning
meanings, forms = collections.defaultdict(set), collections.defaultdict(set)
for path in sorted(glob.glob(r"{{BOOK_DIR}}/annot/ch*_batch*.json")):
    if path.endswith(".norm.json"):
        continue
    for para in json.load(open(path, encoding="utf-8"))["paragraphs"]:
        for sentence in para["ann"]["sentences"]:
            for chunk in sentence["chunks"]:
                voc = chunk.get("voc", "")
                for head, meaning in FIELD.findall(voc):
                    meanings[head].add(meaning.strip())
                for infinitive, rest in VERB.findall(voc):
                    forms[infinitive].add(rest)
for head, said in sorted(meanings.items()):
    if len(said) > 1:
        print("glossed more than one way:", head, sorted(said))
for infinitive, said in sorted(forms.items()):
    if len(said) > 1:
        print("two sets of forms:", infinitive, sorted(said))
```

Read what it prints. A repeated bare gloss is not a fault (the repetition rule is full the first time, briefer afterwards); a disagreement is. Settle each by the rules of **The errors no tool finds**, fix it in the JSON through the same door as any finding, and make that batch again.

### The whole book, once, before you say it is done

The proof-reading read one paragraph at a time. Before Step 3 closes, read the whole book against itself once: every `voc` and `en` of the merged batch files, chapter by chapter, for a convention applied two ways, a name explained again or not at all, a word glossed differently from the way it was met before. Expect this pass to find far more than the paragraph-level proof-reading did, because those lenses cannot see a second paragraph. Its findings go through the sceptic like any other; a fix is made in the JSON and only the batches it touches are assembled again. In a long book read each chapter as it closes and keep the sweeps for the whole.

End with `verify_book.py` clean, and write in `NOTES.md` what each pass found -- and when one found nothing, that.
