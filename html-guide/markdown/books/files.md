---
title: What a book is made of
linkTitle: The files of a book
weight: 14
description: book.json, a chapter .tex argument by argument, the chunk macros and the vocabulary line, the source paragraphs, reading.json and the draft flag — for reading or writing the files directly.
---

Everything the pages do, they do to a handful of plain files. You never
need to open them — but they are written to be read, and a text editor can
do some things a page cannot ([Taking a book away](doc:Taking a book away)).
The files are the truth: the reader and the PDF are both built from them.

## book.json

The book's facts, one JSON object:

```json
{
  "slug": "mini-fa",
  "language": "fa",
  "gloss": "en",
  "title": "فارسی شکر است",
  "title_latin": "Farsi shekar ast",
  "title_en": "Persian is Sugar",
  "author": "محمدعلی جمال‌زاده",
  "author_latin": "Mohammad-Ali Jamalzadeh",
  "year": "1921",
  "blurb": "One sentence for the library card.",
  "main": "main.tex",
  "audio": "audio/narration.mp3",
  "transcript": "audio/transcript.txt"
}
```

| Key | |
|---|---|
| `slug` | the folder's name |
| `language` | the language the book teaches, a code of the toolbox's registry (`fa`, `ar`, `it`, `ja`, `fr`, `de`, `tr`, `en`, `hi`, `es`, `zh`). The folder the book sits in (`books/persian/`) must agree; if it does not, the file wins. No page says so: the warning (*!! mini-en is filed under books/french/ but book.json says language en (books/english/)*) is printed only in the server's own output — the window Parseh runs in, when it starts — and among the lines of each build, which a page shows one at a time while the build runs. |
| `gloss` | the language the glosses are written in; English when absent |
| `title`, `title_latin`, `title_en`, `author`, `author_latin`, `year`, `blurb` | what **book info** edits |
| `main` | the file that includes the chapters |
| `audio`, `transcript` | the recording and its transcript, for a book with one; `null` for none |
| `narrations` | a book recorded in parts: one record per recording — its id, file, transcript, and the first and last subparagraph it covers |
| `draft` | `true` while the book is being written ([Adding a book](doc:Adding a book)) |
| `reorders` | `true` for a text read out of its written order (kanbun): **book info**'s **order** checkbox |

## A chapter, argument by argument

`main.tex` is the frame — the language, the title page, and one `\input`
line per chapter file, which is where the order of the chapters is written
down. A chapter file reads like this (from the English fixture, cut short):

```latex
\chapopen{1}            % the chapter's number
\chapname{The clock}    % optional: its name

\parstart{1.1}{The old man wound the clock}
\parnum{1.1}            % paragraph.subparagraph
\begin{frank}
\ch{}{The old man}{ðə oʊld mæn}
    {\dw{old}{oʊld} having lived a long time}{the old man}
\ch{}{wound the clock}{waʊnd ðə klɑk}
    {\dw{clock}{klɑk} the thing that tells the time}
    {turned the key of the clock}
\end{frank}

\parnum{1.2}
\begin{frank}
...
\end{frank}

\parend                 % the end of a paragraph

\secmark{The child}     % optional: a section starts below

\parstart{1.2}{A child came in and asked}
...
\chapend                % the end of the chapter
```

**The scaffolding is not decoration.** `\parstart` puts the paragraph in the
contents and the PDF's outline: *chapter.paragraph*, in the language's own
digits (۱.۱ in Persian), then the paragraph's opening words. `\parnum` labels
a subparagraph *paragraph.subparagraph*. One `frank` block is one
subparagraph, and is what makes the passes: its chunks are read once to fill
pass 1 before the chunks are set. `\chapname` and `\secmark` are what the
**chapters and sections** sheet writes ([Contents, sections and
folding](doc:Contents, sections and folding)).

A chunk may be broken over several lines wherever one brace group ends and
the next begins — which is how a long vocabulary line is kept readable — but
it may not contain a **blank** line: to LaTeX that ends a paragraph, and the
build stops with an error naming neither the chapter nor the chunk.

## The chunk macros

| Macro | Groups | Is |
|---|---|---|
| `\ch{col}{text}{tr}{voc}{meaning}` | 5 | the ordinary chunk |
| `\chr{col}{text}{kana}{tr}{voc}{meaning}` | 6 | a chunk with a reading: Japanese |
| `\chw{col}{text}{tr}{voc}{meaning}{words}` | 6 | the ordinary chunk with its word line: Chinese |
| `\chrw{col}{text}{kana}{tr}{voc}{meaning}{words}` | 7 | the Japanese chunk with its word line |
| `\chp{col}{text}` | 2 | a chunk that needs no gloss |

**The number of groups is in the name** and is never guessed: the reader and
the PDF cut a call into the same pieces, so one group too few or too many
breaks both. The **first** group is the colour — `\Cred`, `\Cblue`,
`\Corange`, `\Cgreen`, or empty. The **second** is the text, and it is the
group every check against the source reads. The **word line** is the words
parted by spaces, each followed by its reading in brackets:
`山(やま) へ 柴刈り(しばかり) に 、`.

**The vocabulary line** is LaTeX, and only this much of it: entries divided
by `;`, the four gloss macros — `\dw{word}{sound} meaning`, `\pw{word}`,
`\bw{base}{sound}{the phrase}` and `\vb` with its seven groups ([Writing a
chunk](doc:Writing a chunk) has them all) — and `\textit`, `\emph`, `\nobreak`
(and a thin space, `\,`). None of `$ % & # _ ^ ~` and no `\\`, raw or
escaped. Every other field — the text, the reading, the transliteration,
the meaning — is plain text, and none of `\ { } $ % & # _ ^ ~` may go into
it at all.

## The source paragraphs, and fidelity

Every paragraph has a plain-text file of its own under `source/`, the
original as it was divided:

```text
source/paras/ch1_p00.txt    chapter 1, paragraph 1   (the number counts from 0)
source/paras/ch1_p01.txt    chapter 1, paragraph 2
source/src_ch1.json         the same paragraphs, as one list
```

Every chunk of a paragraph, joined with the language's word separator (a
space; nothing for Japanese and Chinese), with the vowel marks taken off and
the whitespace tidied, must give exactly the source paragraph. That is why
changing a word is refused and vowelling one is not, and why chunks can be
cut and joined freely ([Writing a chunk](doc:Writing a chunk) explains, and
shows how to take a paragraph out of the check). A paragraph with no source
file is not checked at all, and the chunk sheet's answer to a save says so:
*not checked: no source paragraph at source/paras/ch1_p04.txt*.

## The comments

A chapter's comments are yours, and nothing touches them — with one
exception. Aligning a narration writes a `% @par` line above each `frank`
block, holding that subparagraph's start and end in the recording; it is
where the reader reads its times from. They belong to the block on the next
line: do not move them, and do not put anything between a comment and its
block. (A build writes them back from `timings.json` when they are
missing.)

A `%` inside a chunk is the one thing that makes the reader and LaTeX
disagree about where the chunk ends, so the chunk sheet refuses to edit such
a chunk at all: nothing the toolbox writes contains one, and a chapter that
does wants mending by hand.

## reading.json

The two decisions about the edition that are not in its text: the runs of
paragraphs **folded** away, and the paragraphs taken out of the source check
(**this paragraph need not reproduce `source/paras/`**). Written by the
reader, kept beside the book, carried in its download:

```json
{"collapsed": [["1:3", "1:8"]], "free": ["2:13"]}
```

A paragraph is named *chapter:paragraph*, by the chapter file's number and
the paragraph's place in it.

## The draft flag

`"draft": true` in `book.json` relaxes one rule: a chunk with nothing written
in it at all is passed over instead of being an error. One field written
makes it a chunk somebody is working on, and every field its language
requires is required again. The library card and the reader show **draft**
while it is there. When the last gloss is written, delete the line, and
press **rebuild the reader** ([Adding a book](doc:Adding a book)).
