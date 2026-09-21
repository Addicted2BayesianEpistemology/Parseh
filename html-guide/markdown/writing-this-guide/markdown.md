---
title: Hugo’s Markdown
linkTitle: Hugo’s Markdown
weight: 2
description: Every construct of Hugo's Markdown the guide takes, with what it becomes.
---

The guide reads the Markdown Hugo reads — CommonMark, with the extensions
Hugo's Goldmark renderer turns on by default: tables, strikethrough, task
lists, bare links, footnotes, definition lists, the typographer, heading
ids and attributes. Each construct below is shown as it is written and as
it comes out. A few read differently here, because the Parseh dialect has a
meaning of its own for the same text: the
[table of those](parseh-dialect.md#where-parseh-wins) lists them all.

## Headings

```markdown
# A level-one heading
## A section, numbered as the studio numbers it
### A subsection
#### Level four ####
##### Level five
###### Level six

Setext, level one
=================

Setext, level two
-----------------

### A heading with its own address {#my-address .highlighted}
```

A `##` heading is a numbered section, as in the studio, and a number typed
by hand in front of it (`## 3. Tables`) is taken off so that it does not
come out twice. Levels two and three make the page's contents, **On this
page**. Every heading gets the address Hugo would give it — the words in
lower case joined by `-` — shown by the # beside it when you point at it;
`{#my-address}` at its end gives it another, and `{.class}` a class.

A `# heading` on the first line of a page with no `title:` is the page's
title; one that only repeats the title is not drawn twice.

## Paragraphs and line breaks

Lines next to each other are one paragraph; a blank line starts the next.
A line that ends in two spaces, or in a backslash, breaks there:

```markdown
The first line,  
the second, after two spaces;\
the third, after a backslash.
```

The first line,  
the second, after two spaces;\
the third, after a backslash.

## Emphasis

```markdown
*italic* and _italic_, **bold** and __bold__, ***both at once***,
~~struck through~~, and `code`.
```

*italic* and _italic_, **bold** and __bold__, ***both at once***,
~~struck through~~, and `code`.

An underscore inside a word is a letter (`snake_case_name` stays as it
is), and so is a star: the studio never sets italics inside a word.

## Lists

```markdown
- a bullet
- another, with a list inside it:
  1. numbered
  2. and nested
     - as deep as you like
- [ ] a task still to do
- [x] a task done

7. an ordered list may start anywhere
8. and goes on from there
```

- a bullet
- another, with a list inside it:
  1. numbered
  2. and nested
     - as deep as you like
- [ ] a task still to do
- [x] a task done

7. an ordered list may start anywhere
8. and goes on from there

An item holds everything indented to where its text starts: more
paragraphs, a code block, another list. A line right under an item carries
its text on only when it is indented (two spaces are enough); a line at the
margin ends the list and starts a paragraph, as in the studio. A blank line
between the items of a list spaces them out (a *loose* list, in Markdown's
words) and the numbers count on — Hugo's reading, kept here although the
studio would start a new list there ([the table](parseh-dialect.md#where-parseh-wins)
says why).

A bullet list whose every item opens with a **bold label** is the studio's
description list, drawn as it is in the studio:

```markdown
- **target** the language being learned
- **lang** the language the prose is written in
```

- **target** the language being learned
- **lang** the language the prose is written in

## Definition lists

```markdown
Front matter
: The block of settings at the top of a page.

Section
: A folder of pages.
: Its `_index.md` is its own page.
```

Front matter
: The block of settings at the top of a page.

Section
: A folder of pages.
: Its `_index.md` is its own page.

## Tables

```markdown
| Key       | Read by   | Default |
|:----------|:---------:|--------:|
| `target`  | the studio|      fa |
| `lang`    | the guide |      en |
| `a \| b`  | —         |      -- |
```

| Key       | Read by   | Default |
|:----------|:---------:|--------:|
| `target`  | the studio|      fa |
| `lang`    | the guide |      en |
| `a \| b`  | —         |      -- |

The colons set each column's alignment; `\|` is a pipe inside a cell; a
cell holding only `—`, `--` or `-` is an empty one, as in the studio. A
table with four or more columns is set smaller, with six or more smaller
still.

## Links

```markdown
[A page of this guide](pages.md), [with a heading](pages.md#front-matter),
[a site](https://gohugo.io "Hugo's own site"), <https://commonmark.org>,
a bare https://github.com, [a reference link][hugo], [hugo][] and [hugo].

[hugo]: https://gohugo.io/content-management/formats/ "Content formats"
```

[A page of this guide](pages.md), [with a heading](pages.md#front-matter),
[a site](https://gohugo.io "Hugo's own site"), <https://commonmark.org>,
a bare https://github.com, [a reference link][hugo], [hugo][] and [hugo].

[hugo]: https://gohugo.io/content-management/formats/ "Content formats"

A link to another site opens in a new tab and carries a small ↗; a link to
a page of the guide stays in this one. [Links between pages](pages.md#links-between-pages)
says how a page is named.

## Footnotes

```markdown
A claim that needs a source.[^source] And one that carries its note
with it.^[Written right where it belongs.]

[^source]: The note, written anywhere in the page.
```

A claim that needs a source.[^source] And one that carries its note
with it.^[Written right where it belongs.]

[^source]: The note, written anywhere in the page.

Point at a number to read the note; they are all listed again at the end
of the page. The studio's rules hold: every reference is a new note, so a
note meant twice is written twice; a note is one paragraph, its later lines
indented by two spaces.

## Quotation marks and dashes

The typographer turns typewriter marks into printer's ones:

```markdown
"Double" and 'single' quotes, it's, -- and ---, three dots..., <<and>>.
```

"Double" and 'single' quotes, it's, -- and ---, three dots..., <<and>>.

A dash that points, `->`, is the studio's arrow instead: a -> b.

## Escapes and entities

```markdown
\*not italic\*, \_not either\_, \[not a link\](x), \# not a heading,
&copy; &mdash; &#x2192;
```

\*not italic\*, \_not either\_, \[not a link\](x), \# not a heading,
&copy; &mdash; &#x2192;

## Rules

A line of three or more `-`, `*` or `_` draws a rule:

---

## Attributes

A line holding only `{…}` right after a block gives it an id, classes or
other attributes, Hugo's block attributes:

```markdown
A paragraph with a class of its own.
{.lead #opening}
```

## HTML

HTML written into a page is not passed through — Hugo leaves it out, and
the studio shows it as text; the guide shows it, as the studio does:
<b>this is not bold</b>. What a page needs HTML for, a shortcode does: a
figure, a collapsible block, a video ([Shortcodes](shortcodes.md)).
An HTML comment is left out altogether, which makes it the way to leave a
note for whoever edits the page next:

```markdown
<!-- TODO: a screenshot of the new toolbar -->
```

<!-- TODO: a screenshot of the new toolbar -->

## What is not there

- **Indented code blocks.** In the studio's dialect indentation is never
  code, and a page is often indented; code is always fenced
  ([Code blocks](code-blocks.md)).
- **`$…$` maths.** Hugo does not read it either, by default; the dialect's
  `[…]{math}` and `:::math` do ([The Parseh dialect](parseh-dialect.md#formulas)).
- **Emoji codes** like `:smile:`, off by default in Hugo too. Type the
  emoji itself.
- **Hugo's optional extras** (`==mark==`, `^sup^`, `~sub~`), off by default
  in Hugo and not read here.
