---
title: Boxes and Latin blocks
weight: 8
description: The > box that holds anything, and the [...]{la} block that sets prose apart — aligned, tinted, narrowed and shifted like a picture.
---

## Boxes

A line that starts with `>` goes into a **box**: a tinted panel across the
page. Every following line that starts with `>` goes into the same box.
It is not a quotation, as it is in other Markdown: it is the studio's way
of setting something apart — a rule to remember, a table of endings, an
aside.

```parseh-example
> **The six vowels.** Persian writes its three long vowels with letters
> and usually leaves the three short ones out.
>
> - long ā, i, u: آب *āb* water, سیب *sib* apple, روز *ruz* day
> - short a, e, o: شب *šab* night, کتاب *ketāb* book, گل *gol* flower
```

**A box holds anything a document holds**: paragraphs, lists, tables,
headings, pictures and recordings, formulas, exercises — and another box,
written with a second `>`. What is inside is read exactly as a document
is, after the `> ` at the start of each line is taken off.

```parseh-example
> ### Endings
>
> | Person | Ending |
> |---|---|
> | I | -am |
> | you | -i |
>
> > A box in a box: [تو]{teal} *to* is the familiar you.
```

A few rules follow from that:

- **Every line needs its `>`**, the blank ones inside the box too (a lone
  `>`). A line without one ends the box; it is not carried in, as some
  Markdown would.
- A `##` heading in a box is a numbered section like any other, and
  listed in the contents; a `#` heading in a box is dropped.
- A box that starts with `> ---` takes the lines down to the next `> ---`
  for a front matter of its own, and drops them. Start a box with
  something else.
- A footnote defined inside a box is one of the document's notes, and may
  be cited from anywhere.

On paper a box is a tinted panel a little narrower than the text; in a
PDF printed **Black and white**, a white one in a thin black frame.

## Latin blocks

A paragraph written entirely as `[…]{la}` is a **Latin block**: prose set
apart as a block of its own, that can be aligned, tinted, and narrowed and
moved sideways like a picture. It is the mirror of `[…]{tl}`: where that
one sets a stretch of the target language apart, this one sets apart the
prose — the translation under a poem, the English beside a Persian
passage, a note in the margin.

```parseh-example
[*The children of Adam are limbs of one body, for in their creation they
share one essence.* — Saadi, *Golestan*]{la align=center bg=sand width=80}

[A narrower block, 70% of the column wide and 10% in from its left edge:
room for a note beside the Persian.]{la width=70 offset=10 bg=lilac}
```

Unlike a `{tl}` stretch, **the inside is ordinary Markdown**: italics,
bold, a word of the target language, a colour, a gloss, a link, a
footnote all work in it. It may hold marks one level deep — `[…]{teal}`
inside is fine, a mark inside a mark inside it is not.

`{ltr}` is another name for `{la}`, for the same block:

```parseh-example
[The same block, written with **ltr**: a note set apart, tinted rose.]{ltr bg=rose width=80 offset=10}
```

### Its options

| Option | What it does | Default |
|---|---|---|
| `align=left`, `center`, `right` | aligns the **text** inside the block | `left` |
| `bg=quote`, `sand`, `rose`, `sage`, `lilac` | tints the block, as a `{tl}` block's tints | none |
| `width=` 10 to 100 | the block's width, in percent of the column | `100` |
| `offset=` −100 to 100 | moves the block's left edge, in percent of the column | `0` |

`align` places the text inside the block; `offset` places the block.
A width under 10, or over 100, is taken as 10 or 100, and an offset
beyond −100 or 100 as −100 or 100; whatever the numbers, the block's left
edge stops a quarter of the column beyond either edge of it.

```parseh-example
[This text is set to the right of a full-width block.]{la align=right}

[A block half the column wide, pushed to the middle, its text centred.]{la width=50 offset=25 align=center bg=rose}
```

### Its rules

- **It must be the whole paragraph.** `[…]{la}` inside a sentence is not
  read: the brackets and the braces show as typed. (Inside a line the
  prose is Latin already.)
- **It may run over several lines**, like the long form of `{tl}`: the
  opening `[` may stand on a line of its own and the closing `]{la}` on
  another, as long as no blank line and no line that starts a block of its
  own comes between them.
- In the reading view and the editor's preview, **a click on a Latin
  block** opens the layout panel pictures have — width, shift, alignment
  and tint — and writes what you choose into the braces. The editor's
  **block** button wraps the selected text in `[…]{la}` (the long form
  when it spans lines).

On paper a Latin block is set at the same place as on the screen, tinted
where it is tinted — the two renderers compute its place alike.
