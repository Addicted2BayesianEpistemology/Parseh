---
title: Lists and tables
weight: 9
description: Bullet and numbered lists, one level of nesting, labelled lists, and tables with their alignment, empty cells and sizes.
---

## Lists

A line that starts with a marker and a space is a list item; the items
that follow it make the list.

| Marker | List |
|---|---|
| `- `, `* `, `+ ` | a bullet list |
| `1. `, `1) ` — any number, then a full stop or a bracket | a numbered list |

```parseh-example
- one item per line;
- a second item;
  - an item indented by two spaces sits one level down.

1. Read the new word aloud.
2. Write it once by hand.
3. Use it in a sentence of your own → now it is yours.
```

```parseh-example
* a star makes a bullet too,
* and an item goes on
  over a line indented by two spaces;

+ so does a plus.

1) A number and a bracket
2) make a numbered list.
```

The rules are few, and a little stricter than elsewhere:

- **The first item decides the kind.** A list is numbered when its first
  marker is a number, and later items join it whatever their markers.
- **The numbers count themselves**: a numbered list always starts at 1 and
  goes up by one, whatever numbers you typed — `5.`, `9.`, `1.` come out
  1, 2, 3.
- **An item goes on** over the lines under it that are indented by at
  least two spaces (or a tab). A line under an item at the margin ends the
  list and starts a paragraph.
- **A blank line ends the list.** Items with blank lines between them are
  separate lists, and a numbered one starts again at 1 after each.
- **One level of nesting.** An item indented further than the first one
  sits one level down, in a bullet list, even inside a numbered one. Deeper
  indentation does not go deeper: every indented item is on that one
  level.

What those rules make of a few lists, shown as source because this guide's
own pages read them otherwise:

```markdown
1. first
2. second

3. third             <- a new list, numbered 1 again

- bullet
    - indented        <- one level down
        - indented more   <- still one level down
  1. numbered         <- one level down, as a bullet

- [ ] a task          <- the item reads "[ ] a task": no checkbox
```

### Labelled lists

A bullet list whose **every** item starts with a bold label — two items
or more — is a **labelled list**: each label is set in bold at the head of
its line, the text running on after it.

```parseh-example
- **Script** an alphabet of 32 letters, joined as in handwriting
- **Direction** right to left
- **Vowels** the short ones are usually left unwritten
```

When a label is a longer stretch of the target language — more than ten
characters of it — the labels go on lines of their own, with the text
indented under each, which reads better for phrases:

```parseh-example
- **کتاب‌های قدیمی** old books, a plural with the ezafe left out
- **کتابخانهٔ ملی** the national library
```

A single item with a bold label, or a numbered list with them, is an
ordinary list.

## Tables

A table is a header line and a line of dashes under it, then its rows,
the cells parted by `|`:

```parseh-example
| Infinitive | Present stem | Past stem | Meaning |
|:---|:---:|:---:|---:|
| رفتن *raftan* | رو *rav* | رفت *raft* | to go |
| آمدن *āmadan* | آ *ā* | آمد *āmad* | to come |
| دیدن *didan* | بین *bin* | -- | to see |
```

- **The line of dashes** sets each column's alignment: `:---` left,
  `:---:` centred, `---:` right, and `---` alone left. One dash a cell is
  enough, as in GitHub's Markdown: `|:-:|-|` is a line of dashes too. It
  is read only on the line right under the header, so a body row of `-`
  or `--` cells is still a row (of empty cells).
- **Two columns or more.** A one-column "table" is text.
- **The pipes at the ends of a line are optional**: `a | b` over `--|--`
  is a table too.
- **The rows run** until a line with no `|` in it, or a blank line.
- **A row with fewer cells** is filled with empty ones; the cells of a
  row beyond the header's number are dropped.
- **A cell holding only `—`, `--` or `-`** is an empty one, drawn as a
  dash — the way a printed table says *nothing here*.
- **A `|` can never be in a cell**, not even in code: every one splits
  the row. (Which is also why a document's name may not hold one: a link
  to it inside a table would split the cell.)
- A cell holds what a line of prose holds: bold, italics, target-language
  words, colours, a formula, a footnote.

A table of **four columns or more** is set in a smaller size, and one of
**six or more** smaller still, so that it fits the column:

```parseh-example
| Person | Present | Past | Future | Perfect | Subjunctive |
|---|---|---|---|---|---|
| I | می‌روم | رفتم | خواهم رفت | رفته‌ام | بروم |
| you | می‌روی | رفتی | خواهی رفت | رفته‌ای | بروی |
```

A table wider than the column scrolls sideways in the reading view. On
paper it is a book-style table, header in bold between two rules; in
large print, one wider than the line is scaled down to it. Very wide
tables are still best shortened, or cut in two.
