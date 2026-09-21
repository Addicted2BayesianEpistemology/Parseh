---
title: How the studio reads a document
linkTitle: How a document is read
weight: 1
description: The order in which the studio tries each line, what of ordinary Markdown it has and has not, and how this guide differs.
---

A studio document is one text file: a short **front matter** at the top,
between two `---` lines, and then the body. The studio reads the body
from the top, one line at a time, and decides for each line what kind of
block it starts. Two renderers then draw the same blocks: one as the web
page you read and edit in the studio (the reading view, and the editor's
live preview), one as the PDF. They are written as twins, so a figure
lands in the same place on the screen and on paper, and a colour is the
same colour.

```parseh-example
---
title: Verbs of motion
subtitle: رفتن and آمدن
lang: en
target: fa
---
## Going

The verb رفتن = *to go* has the past stem رفت.

> **Remember.** The past stem is the infinitive without its *-an*.
```

## The order in which a line is tried

For every line, the studio asks these questions in this order, and the
first yes decides:

| The line is… | It becomes… | Page |
|---|---|---|
| blank | the end of the paragraph (or list, or table) above it | [Paragraphs](paragraphs-and-emphasis.md) |
| `---`, `***` or `___` alone | nothing: a rule is dropped | [Left out](left-out.md) |
| `:::exercise` and a type | an exercise, up to a line `:::` | [Writing exercises](../dialect-exercises/_index.md) |
| `:::math` | a formula, up to a line `:::` | [Mathematics](mathematics.md) |
| `[^id]: text` | a footnote's text, drawn where it is cited | [Footnotes](footnotes-and-links.md) |
| `# `, `## ` or `### ` and text | a title, a numbered section, a subsection — or a vocabulary entry | [Headings](headings.md) |
| `>` and text | a box, with every following `>` line | [Boxes](boxes-and-latin-blocks.md) |
| a line holding `\|`, over a line of dashes | a table | [Tables](lists-and-tables.md#tables) |
| `![caption](images/…)` or `![caption](audio/…)` alone | a picture, or a recording | [Media](media.md) |
| `@[caption](a YouTube address)` alone | a video | [Media](media.md) |
| `- `, `* `, `+ `, `1. ` or `1) ` | a list, with the items after it | [Lists](lists-and-tables.md) |
| anything else | a line of a paragraph | [Paragraphs](paragraphs-and-emphasis.md) |

Two consequences are worth knowing from the start:

- **An exercise and a formula are read first**, so everything between
  `:::exercise` and its closing `:::` belongs to the exercise, however
  much it looks like a list or a heading. The same holds for `:::math`.
- **A paragraph is what is left over.** Lines next to each other that are
  none of the above are one paragraph; the studio then looks at the
  paragraph *as a whole*, and a paragraph that is entirely `[…]{la}`,
  entirely `[…]{tl}`, or entirely in the target language's script becomes
  a block of its own ([Boxes and Latin blocks](boxes-and-latin-blocks.md),
  [Target-language text](target-language.md)).

## Inside a line

Within a paragraph — and a heading, a list item, a table cell, a caption, a
footnote — the studio reads the marks of the dialect. The order matters,
because it decides what may sit inside what:

1. Footnotes, both kinds, are set aside first, so a note may hold almost
   anything.
2. Stretches of the target language, `[…]{tl}`, and formulas,
   `[…]{math}`, are set aside next, **whole**: nothing inside them is read
   as Markdown. A `*` in a Persian sentence marked `{tl}` is a star.
3. Links, then colours and transliterations, are found round their text.
4. Runs of the target script — Persian words in English prose, say — are
   found and set aside: they are never read as Markdown either, and
   emphasis never crosses them.
5. What is left is ordinary prose: `**bold**`, `*italic*`, `` `code` ``,
   the arrow `→`, the line break `⏎`, the signs `✗` and `✅`.
6. Last, an `=` right after a target-language word is greyed: that is a
   gloss.

```parseh-example
A formula [a^2+b^2]{math}, a **bold** word, an *italic* one, [کتاب]{teal} in
colour, [تند]{translit:tond} with its transliteration,
[a link](https://www.youtube.com/watch?v=aqz-KE-bpKQ), and کتاب = *book*.
```

## What of ordinary Markdown is there

The dialect started from the Markdown most people know, and kept the part
a lesson needs. Much of the rest is simply not read: typed, it shows as the
characters you typed.

| Ordinary Markdown | In the studio |
|---|---|
| `#`, `##`, `###` headings | yes — `##` is numbered, `#` is the title ([Headings](headings.md)) |
| `####` and deeper, headings underlined with `===` or `---` | no: they are text |
| paragraphs, blank lines between them | yes; lines of one paragraph are joined with a space |
| a line break by two trailing spaces or a backslash | no: use `⏎` ([Special characters](special-characters.md)) |
| `**bold**`, `*italic*` | yes, never inside a word or across the target language |
| `__bold__`, `_italic_`, `***both***`, `~~struck~~` | no |
| `` `code` `` | yes, one backtick each side — but what is inside is still read |
| code blocks, fenced or indented | no: a fence is text, and indentation is dropped |
| `-`, `*`, `+` and `1.`, `1)` lists | yes, one level of nesting ([Lists](lists-and-tables.md)) |
| tables with `\|` and a row of dashes | yes, with alignment ([Tables](lists-and-tables.md#tables)) |
| `> quotation` | a tinted **box**, which can hold anything ([Boxes](boxes-and-latin-blocks.md)) |
| `[text](https://…)` | yes; `[label](doc:Name)` links another document ([Links](footnotes-and-links.md)) |
| reference links, `<https://…>`, a bare address | no: text |
| `![caption](images/x.png)` on its own line | yes, with a layout in braces ([Media](media.md)) |
| a picture inside a sentence | no (except inside an exercise) |
| footnotes `[^1]` | yes, and notes written in place, `^[…]` ([Footnotes](footnotes-and-links.md)) |
| `---` rule | dropped: sections give a document its shape |
| HTML, `<!-- comments -->` | shown as text |
| `\*` backslash escapes, `&amp;` entities | no: the backslash and the entity are shown |
| `$x$` mathematics | no: `[x]{math}` ([Mathematics](mathematics.md)) |

[What the studio leaves out](left-out.md) goes through each of these, and
says what you see when you type one.

## Why the studio's own rules

A document here is mostly prose about a language, in another language,
and the dialect is built round that. A few of its choices follow from it:

- **Lines are joined, and a break is asked for.** A source line can wrap
  wherever it likes — you may paste a paragraph an assistant wrapped at 70
  characters — and the paragraph still reads as one. The price is that
  Japanese and Chinese, which put no spaces between words, gain a space
  where a line of the source ended: keep each of their sentences on one
  line.
- **Target-language text is opaque.** A stretch of the target language
  is set aside before any Markdown is read, so it stays one unit, laid out
  in its own direction and face, and nothing can break it up — and a star
  beside it, which a linguist writes before a form that does not exist,
  stays a star instead of starting italics.
- **Every mark looks the same**: a text in square brackets and a word in
  braces after it — `[…]{tl}`, `[…]{teal}`, `[…]{translit:…}`,
  `[…]{la}`, `[…]{math}`. Once you know one, you can read them all.

## This guide is not the studio

The pages of this guide are Markdown files too, and the guide draws them
with the studio's own code — but it also reads **Hugo's** Markdown, which
the studio does not: `_italic_`, `~~struck~~`, code blocks, `####`
headings, reference links, typographic quotes and dashes. Where the two
read the same text differently, the guide takes the studio's reading;
the table [Where Parseh wins](../writing-this-guide/parseh-dialect.md#where-parseh-wins)
lists every such case, and [Hugo’s Markdown](../writing-this-guide/markdown.md)
lists what the guide adds.

So a construct that works on a page of this guide may not work in a
studio document. Everything in *this* section is the studio's: where the
guide would draw something differently, the example is given as source
only, and the text says what the studio does.
