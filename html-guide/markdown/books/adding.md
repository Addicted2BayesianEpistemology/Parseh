---
title: Adding a book
weight: 2
description: Three ways to begin a book — by hand, onto a book already here, or with an LLM outside — and a book whose glosses are still to write.
---

A reading edition is not one answer from a model. It is made paragraph by
paragraph, with a checker after every batch — days of work. The **＋ Add a
book** card on the library opens `/books/add/`, which asks one question,
**What are you doing?**, and then shows only what the answer needs. Three
cards answer it:

| Card | What it does | It needs |
|---|---|---|
| **Write it here, by hand** | cuts a chapter you paste into paragraphs and sentences, with every gloss left blank, and opens the reader on it | the book's facts, and a chapter |
| **Add to a book already here** | puts more text onto the end of a book on the shelf; nothing already written is touched or re-cut | a book, and the text |
| **Let an LLM do it outside** | gives you three things to copy: a script that builds a working folder, the prompt, and a script that brings the finished book back | the facts, the original file, a folder — and a terminal |

The first two write to the shelf the moment you press their button; the
third only hands you things to copy. The second card is not offered while
the shelf is empty. A book you exported earlier, a `<slug>-book.zip`, is
not added here at all: bring it back from the library page's **⇩ Bring a
book back** panel ([The library](doc:The library)).

The page remembers what you typed, in this browser, and which way you chose
(the address says so too: `/books/add/?path=new`, `?path=extend`,
`?path=llm`), so a reload loses nothing. Each numbered step turns into a
tick once what it asks for is there. While a book is being written, the
**Working…** indicator says so on every page.

## Write it here, by hand

This is the way for somebody who knows the language: the toolbox does the
mechanical part — dividing the text — and you write every gloss yourself,
in the reader.

**1. The book.** The facts the book is filed under:

| Field | What it is |
|---|---|
| **Language** | the language the book teaches. It sets the folder the book is filed under, the fonts it is set in and the conventions it is annotated by. It starts on the language picked in the chips of the toolbox's index pages. |
| **Glosses in** | the language the meanings are written *in* — an Italian learning Persian wants them in Italian. English unless you choose otherwise. The list has two groups: *taught here* and *written in, not taught*. A right-to-left gloss of a left-to-right text (Persian or Arabic meanings for a German book, say) is greyed out, because its vocabulary lines could not be set in order. The note under the select says what your pair means. |
| **Slug (directory name, ascii)** | the name of the book's folder. Left empty it is made from the transliterated title (or the title). |
| **Year** | kept in `book.json`, and editable later in the reader's **book info**. Nothing prints it yet: neither the title page nor the library card shows it, whatever the box's tooltip says. |
| **Title, *in the language*** and **Title, transliterated** | the title in its own script, and its Latin spelling. The title page sets both: the title large, and the transliteration under it **as you type it** — capitalise it yourself if you want it in capitals. (The note under the box says *in capitals*; that is true only of the **Let an LLM do it outside** way, whose `main.tex` the page writes in capitals.) |
| **Title, in *the gloss language*** | the title as the gloss language says it — kept in `book.json`, and shown as the **English** row of **book info**; neither the library card nor the PDF prints it |
| **Author, *in the language*** and **Author, transliterated** | the same for the author; the transliteration is the byline under the transliterated title |
| **One-sentence blurb** | the line under the title on the library card |

The title and author boxes take the book's script and direction as soon as
the language is chosen: Persian and Arabic type right to left.

**2. The chapter.** Paste the first chapter into **The chapter, in
*language*** — a blank line between paragraphs, or one paragraph to a line
(the way a chapter copied out of an epub usually arrives). Then choose how
the text is cut, under **Cut the text into**:

- **one chunk per sentence** — the default. Every sentence arrives whole,
  and every boundary inside it is yours to draw. Where a sentence breaks into
  phrases is the whole of the Frank method, the judgement the person doing
  this work is there to make; a machine's guess would hand you somebody
  else's reading to undo before you could begin your own.
- **sense groups (the dictionary reads the parts of speech)** — a first pass,
  for when one is worth more than a blank. It cuts at the edges of phrases
  (a preposition with its noun, a noun with its adjectives, a verb with its
  auxiliaries), reading the punctuation, the language's own list of function
  words and, where one is installed, its dictionary: the better equipped the
  language, the finer the cut, and a language with none of them is cut only
  at its punctuation. Japanese and Chinese are cut by their word analyser
  where it is installed; where it is not, Japanese is cut after its
  particles and Chinese at its punctuation.

Either way, any chunk can be re-cut later in the reader
([Cutting and joining chunks](doc:Cutting and joining chunks)).

**3. Make it.** **Make the draft** stays disabled until there is a title and
a chapter, and says why (*the title comes first*, *paste the chapter
first*). Pressed, it says *drafting…*, and then:

> **Drafted.** 2 paragraphs, 3 sentences, 3 blank chunks, in
> `books/spanish/el-reloj-y-el-viento/`. **Open the reader →**

— and the page goes straight to the reader, where the glossing is done. The
card is already on the library page. The PDF is not built yet: build it
with **build PDF** in the reader, or **rebuild** on its card — the reader
is built already, so the card offers **rebuild**
([The printed edition](doc:The printed edition)). The answer carries a
**build the PDF now** button too, but you will only have time to press it
if the reader could not be built — then the page stays where it is, and
says why under the answer.

What it writes is `book.json`, `main.tex`, `ch1.tex`, and the source files
the fidelity checks read (`source/paras/ch1_p00.txt` and so on, and
`source/src_ch1.json`). For Japanese and Chinese the toolbox also proposes
each chunk's **word line** — the division into words that the readings
stand over — for you to correct in the words strip ([Writing a
chunk](doc:Writing a chunk)); every other line is blank.

### What it refuses

| It says | Which means |
|---|---|
| *a book needs a title in Persian* | the title box is empty |
| *no directory name could be made from '…'* | the title is all in its own script and leaves no ASCII letters for a folder name: give a slug, or a transliterated title |
| *the text is empty: there is nothing to draft* | the chapter box is empty |
| *paragraph 3 of chapter 1 carries '%', which LaTeX reads as an instruction …* | the text holds one of `\ { } $ % & # _ ^ ~`. Take it out, or spell it in words: escaping it would make the text disagree with its source |
| *paragraph 0 of chapter 1 carries U+0007 at character 12, which is not text …* | an invisible control character came in with the paste; the message shows where it is, so you can take it out |
| *book.json already exists in … — draft into a new name, or move that one out of the way* | a book (built or not) already has that folder; choose another slug |

## Add to a book already here

The same text box and the same way of cutting, pointed at a book that
exists and added to its end.

1. **Which book** — **Add to** lists every book on the shelf, built or not.
   Its language, its glosses and its title are the book's already and are
   not asked again; the text box takes the book's own script and direction.
2. **Where it goes** — **A new chapter** (its own opening and its own line in
   `main.tex`: another story, another lesson), or **More of the last
   chapter** (it continues it, the new paragraphs numbered on from the ones
   already there; the chapter's `\chapend` moves to the end of the new text
   and `source/src_chN.json` is merged). The note under it calls this the
   only thing on the page that edits a file that already exists; it is the
   only choice that changes a *chapter* already written — **A new chapter**
   edits one existing file too, `main.tex`, adding its `\input` line after
   the others.
3. **The text** — pasted as above, with **Cut the text into**.
4. **Add it** — *adding…*, then *Added. 1 paragraphs, 1 sentences, 1 blank
   chunks, as chapter 2* (or *onto the end of chapter 1*), with *the PDF is
   out of date until the next build* under it, and three buttons: **Open
   the reader →**, **Add another chapter** (empties the box for the next
   one — this way's rhythm is repeated appends, so the page does not jump to
   the reader) and **build the PDF now**.

Nothing written before is touched or re-cut: the old chapters are read only
to be numbered on from. The reader is rebuilt at once. The new chunks
arrive blank, for you to fill, in a book finished or not: a blank gloss is
legal anywhere (below).

## Let an LLM do it outside

The third way is the method the first editions were made with: an AI coding
assistant (Claude Code, as the page is written) working in a folder of its
own **outside** the toolbox, with the tools, one finished edition to learn
from, and a prompt that sets it to work ten paragraphs at a time, with a
checker after every batch. It is the one way into Parseh that needs a
terminal, and its card says so before you have filled in anything. Nothing
on this page is sent anywhere: the three scripts are yours to copy and run.

**1. The book.** The same facts as above, and four more in a box marked
*only for the outside folder*:

- **Learn from** — a finished, built edition whose method and notes are
  copied beside your book. The page picks one in the same language where
  there is one, else the Persian one — the method is the same and the
  conventions differ, and the prompt carries your language's own
  conventions (`docs/lang/<code>.md`) in place of the Persian rules.
- **The original** — the path of the book to annotate: a PDF with a text
  layer, an epub or a text file. Until it is named, the page warns **Name
  the original first** and the copy buttons stay disabled: the scripts would
  otherwise hold a placeholder path.
- **PDF pages, first–last** — optional, 0-based, written `13-21`.
- **Working folder** — where the LLM works; `$HOME/frank-<slug>` unless you
  say otherwise.

**2. Set the folder up.** **copy the setup script** copies a script to run
once in a terminal. It makes the folder and copies into it the tools
(`lib/`, `build.sh`, `environment.yml`, `docs/`), the reference edition with
its notes and its annotation files, your original, a `book.json` and a
`main.tex` skeleton, and the prompt as `PROMPT.md`.

**3. Set Claude Code to work.** Go into the folder, start the assistant and
paste the prompt (**copy the prompt**; the page shows how many characters it
is, and it is also in the folder as `PROMPT.md`). The prompt prescribes the
whole method: the source recovered and divided first, the chapter table
shown to you before anything is annotated, then ten paragraphs a batch with
a checker run until it reports no errors, a proof-reader, a sceptic before
any fix, and a draft PDF. Between batches, read a paragraph or two of the
draft PDF yourself: the tools prove the text is faithful, but they cannot
judge a gloss.

**4. Bring it back.** When every chapter is done and the book's checker is
clean, **copy the return script** copies the script that copies the finished
book into `books/<language>/<slug>/` in the toolbox, builds its PDF and its
reader, and checks it once more. The book then appears on the library page.

The prompt lives in `docs/new-book-prompt.md`; the page only fills in its
blanks, so an edit to that file changes what the page gives.

## Glosses still to write

A book made by hand starts with every gloss blank, and may stay partly
blank for as long as the work takes: **a chunk nobody has glossed is legal
in every book**. Nothing marks the book as unfinished, and nothing needs
taking off when it is done — the glosses are simply written, a few at a
time or many at once:

- a chunk at a time, in the reader's chunk sheet
  ([Writing a chunk](doc:Writing a chunk)), filling one box at a time if
  you like: a meaning typed before its transliteration is saved;
- a stretch at a time, by an LLM, from the reader's **gloss with an LLM**
  ([Glossing a stretch with an LLM](doc:Glossing a stretch with an LLM)),
  which fills only the chunks nobody has glossed.

What the book's checker makes of it: a chunk with **nothing** written in it
is counted, once per paragraph — *3 of 12 chunks have no gloss yet* — and
asked for nothing else. A chunk **half** glossed — a meaning with no
transliteration beside it, in a language that romanises every chunk — is
an error, because that is exactly the half-done work the checks exist to
catch: the chunk sheet lets you save it on your way, and the checker keeps
the list of what is still to finish. A book made by an older Parseh, whose
`book.json` still says `"draft": true`, is read as if it did not: the line
does nothing, and may stay or go.

> **What a drafted book looks like.** The text is given; the translation,
> the transliteration and the vocabulary are not, and nothing invents them.
> In Japanese and Chinese each chunk's reading starts as its words' readings
> run together — a proposal from the word line, which counts as nobody's
> writing until something else in the chunk is written. A blank line ends a
> paragraph, a sentence becomes a
> subparagraph, and a chunk is a whole sentence (or a sense group, if you
> asked for them). A sentence boundary the splitter got wrong — after *Mr.*,
> say — still reproduces the text exactly, so nothing breaks. The page joins
> chunks only inside one subparagraph, so two subparagraphs are put back
> together by hand, in the chapter file: the second one's chunk lines move
> into the first one's `frank` block, and its own `\parnum` and block go
> ([What a book is made of](doc:What a book is made of) shows the shape).
