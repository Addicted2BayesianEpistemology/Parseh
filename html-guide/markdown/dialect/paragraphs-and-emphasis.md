---
title: Paragraphs and emphasis
weight: 4
description: Lines and blank lines, bold, italic and code — and why emphasis stops at the target language.
---

## Paragraphs

Lines next to each other are **one paragraph**: the studio joins them with
a space, whatever their length. A **blank line** ends the paragraph and
starts the next.

```parseh-example
These two lines of the source
are one paragraph on the page.

A blank line starts the next one.
```

This is what lets a source line break wherever it likes: an assistant's
answer wrapped at seventy characters, or a long sentence you broke to
keep the editor tidy, is still one paragraph. Indentation at the start of
a line is dropped — it never makes a code block, and it continues nothing
except a list item or a footnote (see [Lists](lists-and-tables.md) and
[Footnotes](footnotes-and-links.md)).

Two consequences:

- **To break a line inside a paragraph, ask for it** with `⏎`, the
  return sign (the editor's **`⏎`** button types it). Two spaces at the end
  of a line, or a backslash, break nothing here.
- **Japanese and Chinese gain a space** where a source line ended, because
  the lines are joined with one and these languages put none between
  words. Keep each of their sentences on one line of the source.

```parseh-example
A line of prose,⏎and the same paragraph on a new line.
```

## Bold and italic

Two stars round a stretch of text make it **bold**, one star *italic*,
and the two nest one way: italics inside bold.

```parseh-example
Text can be **bold**, *italic*, or **bold with *italic* inside**.
```

Italics follow two rules that come from writing about languages:

- **Never inside a word.** A star right after a letter or a digit does not
  start italics, so `un*believ*able` stays as typed.
- **Never across the target language.** A star next to a word of the
  target language is left as a star — a linguist writes one before a form
  that does not exist — and a stretch of italics that would hold a target
  word is not italicised at all. The dialect has its own sign for a wrong
  form, `✗` ([Special characters](special-characters.md)).

Bold is more generous: `**کتاب**` makes the Persian word itself bold (in
the target face's bold), and bold may hold a target word among other words.

```parseh-example
**کتاب** is bold Persian, and **the word کتاب** is bold with it.
*کتاب* keeps its stars, and so does *a book, کتاب*, which holds a Persian word.
```

Two stars on one line with text between them are italics even when they
stand apart as signs: in `5 * 3 * 2` the ` 3 ` comes out in italics. Write
`×` for a multiplication, or a formula ([Mathematics](mathematics.md)). A
backslash before a star keeps it from starting italics, but the backslash
is printed too: there are no escapes in the dialect.

## Code

One backtick on each side sets a stretch in a typewriter face, for a file
name, a key to press, a thing typed rather than read.

```parseh-example
Save the picture as `starter-apple.svg`, then press `Ctrl+S`.
```

Unlike ordinary Markdown, what is inside is **still read**: `` `**b**` ``
comes out as a bold b in typewriter type, and a Persian word inside is still
set as Persian. Code is for short things; the dialect has no code blocks, and
a line of three backticks is ordinary text.

```markdown
`**still bold**` inside code, in the studio
```

## What is not there

These are ordinary Markdown elsewhere, and text here — they show as typed:

| Typed | Elsewhere | In the studio |
|---|---|---|
| `_italic_`, `__bold__` | emphasis | the underscores, as typed |
| `***both***` | bold italic | not supported, and drawn wrongly: choose bold or italic |
| `~~struck~~` | struck through | the tildes, as typed |
| `\*` | a star | a backslash and a star |
| `"quotes"`, `--`, `...` | curly quotes, a dash, an ellipsis | on the screen, exactly as typed; on paper, see below |
| two spaces, or `\`, at the end of a line | a line break | nothing: use `⏎` |

**Paper is not the screen here.** The PDF's typesetter has old habits of
its own: on paper `--` prints as an en dash –, `---` as an em dash —, and
a straight `"` or `'` as a closing curly quote ” or ’ — on *both* sides of
the word, which is wrong for the opening one. `...` stays three dots on
both. So type the real characters, “ ” ‘ ’ – — …, and the screen and the
paper agree.

```parseh-example
Pages 3–5 — “quoted”, and ‘quoted’ … the way you want them on both.
```

On paper, bold and italic are the PDF's bold and italic, and code its
typewriter face; a bold target word is set in the target face's bold and
is never broken across two lines.
