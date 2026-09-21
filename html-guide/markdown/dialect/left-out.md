---
title: What the studio leaves out
linkTitle: What is left out
weight: 14
description: The Markdown the studio does not read, what it drops without a word, what swallows the rest of a document, and a few rough edges to step round.
---

The dialect is small on purpose, and it does not complain: what it does
not read, it shows as you typed it, or drops. This page lists all of it,
so that a document never surprises you. The examples are source only —
this guide's own pages read several of them the other way.

## Shown as typed

These are Markdown in other places, and plain characters here:

| You type | Elsewhere | In the studio you see |
|---|---|---|
| `#### Heading`, and deeper | a heading | the line, `####` and all |
| a heading underlined with `===` | a heading | the words and the `===`, as one paragraph |
| `## Heading {#id}`, `{.class}` | an address or a class | the braces, in the heading |
| a fence of three backticks, code, and another fence | a code block | the lines joined into one paragraph, the backticks mangled |
| a line indented four spaces | a code block | the line, its indentation dropped |
| `_x_`, `__x__` | italic, bold | the underscores |
| `~~x~~` | struck through | the tildes |
| `\*`, `\_`, `\[` | the character | the backslash and the character |
| `&amp;`, `&copy;` | `&`, `©` | the entity as typed |
| `<b>html</b>` | bold | the tags, as text |
| `<!-- a comment -->` | nothing | the comment as text — and the `->` of its `-->` read as an arrow |
| `<https://…>`, a bare `https://…` | a link | the address, as text |
| `[text][ref]` and `[ref]: https://…` | a link | both lines, as text |
| `![a map](images/map.png)` inside a sentence | a picture | `!a map`: the caption, after an exclamation mark |
| `- [ ] a task` | a checkbox | `[ ] a task` |
| `Term` and `: its definition` under it | a definition list | `Term : its definition` |
| `$x^2$`, `\(x\)`, `$$…$$` | a formula, on some sites | the characters — write `[x^2]{math}` |
| `:::note` … `:::` | a note box, on some sites | the lines, as a paragraph — only `:::exercise` and `:::math` are fences |
| `{{< figure … >}}` | a Hugo shortcode | the braces, as text |
| `:smile:` | an emoji | the word between colons — type the emoji |
| `"quotes"`, `--`, `...` | curly quotes, a dash, an ellipsis | on the screen, as typed; on paper `--` and `---` become – and —, and `"` prints as ” on both sides ([Paragraphs](paragraphs-and-emphasis.md#what-is-not-there)) |
| `[word]{red}`, any name not among the five colours | — | the brackets and the braces, as typed |
| `[bello]{it}` in a Persian document | — | as typed: only the document's own code marks its language |
| `[…]{la}` inside a sentence | — | as typed: a Latin block is a whole paragraph |
| `[[name]]` outside a fill-in exercise | — | as typed |

## Dropped without a word

- **Front matter keys** other than `title`, `subtitle`, `note`, `lang`
  and `target` ([Front matter](front-matter.md)).
- **Rules**: a line of `---`, `***` or `___`. The sections give a document
  its shape.
- **A `#` heading** when the front matter has a title, and every `#`
  heading after the first when it has none.
- **A subtitle and a note** when there is no title.
- **The ending `= *…*` of a `##` section title** that is not a vocabulary
  entry.
- **Options a mark does not take**: `font=` for a language without that
  face, `vertical` and `height=` for Persian, Arabic, Hindi and the
  Latin-script languages, or inside a line; any word in the braces the
  mark does not know (`{tl bogus=1}`); a `bg=` that is not one of the
  five tints.
- **The kana of a language without a reading**: kept in the file, shown
  nowhere.
- **`start=` and `end=` on a picture**, which has no stretch to play.
- **The cells of a table row beyond the header's number.**
- **A second paragraph of a footnote**: the note stops at the blank line,
  and the next paragraph is one of the document's.

## Read differently

- **A `>` line is a box**, not a quotation, and a line without `>` ends
  it ([Boxes](boxes-and-latin-blocks.md)).
- **Lists**: one level of nesting (every deeper item is on that level,
  and a nested item is always a bullet); the numbers of a numbered list
  are the studio's, from 1; a blank line between items makes two lists;
  a list takes the kind of its first marker
  ([Lists](lists-and-tables.md)).
- **A `[^name]` cited twice** is two notes, not one note cited twice
  ([Footnotes](footnotes-and-links.md#how-notes-are-numbered)).
- **Lines are joined with a space**, which Japanese and Chinese do not
  want: keep each sentence of theirs on one line.
- **A code span is still read**: `` `**b**` `` is a bold b in typewriter
  type.

## What swallows the rest

Three openings run to their closing line, and without one they take
everything after them:

| Opening | Closed by | Unclosed |
|---|---|---|
| the front matter's `---` | `---` | the whole document is taken into the front matter, and nothing is drawn |
| `:::math` | `:::` | the rest of the document becomes one formula |
| `:::exercise` | `:::` | the rest of the document becomes the exercise, which says *exercise is missing its closing ::: line* |

A box that starts with `> ---` does the same inside the box: it reads
the lines to the next `> ---` as a front matter of its own, and drops
them.

## Rough edges

A few things do not work as they should yet. Each has a way round:

| What happens | The way round |
|---|---|
| a straight `"` prints as ” on both sides of a word in the PDF, and `--`, `---` as – and — (on the screen all show as typed) | type “ ” – — yourself |
| a formula after a bracket that is only prose — `[sic]`, `[1]` — in the same paragraph takes the prose into itself ([Mathematics](mathematics.md#two-rough-edges)) | put the formula first, or on its own |
| `✗` before a word with letters beyond the Western European accents (`✗gelmiş`) reddens only its first letters | mark the form: `✗[gelmiş]{tl}` in a Latin-script target |
| `[](https://…)`, a web link with no text, is invisible | give every web link its words |
| `***both***` draws its bold and italics wrongly nested | choose bold or italic |
| the notes of one paragraph are numbered with the ones written in place first | keep the two kinds of note in separate paragraphs |

A few words the studio shows are Italian, where English would be
expected: a wrong picture path's *immagine non valida*, a wrong video
address's *video non valido*, *dal* and *fino a* (*from*, *until*) on a
recording's card on paper, the heading *Note* over the list of notes at
the end, and the small grey *Nota tecnica* that ends every document,
naming the faces it is set in.
