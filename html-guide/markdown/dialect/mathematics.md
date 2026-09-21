---
title: Mathematics
weight: 12
description: Formulas in LaTeX notation, in the line with [...]{math} or on their own between :::math and :::, drawn on the screen and set by TeX on paper.
---

A formula is written in **LaTeX notation** — the notation of every
mathematics paper — in one of two ways.

**In the line**, as a mark: the formula in square brackets, `{math}`
after it.

```parseh-example
Persian has 32 letters, [28 + 4 = 32]{math}: the 28 of the Arabic alphabet
and four of its own. The area of a circle is [\pi r^2]{math}.
```

**On its own**, between a line `:::math` and a line `:::` — the fence an
exercise has, one word shorter:

```parseh-example
Ten new words a day for a month:

:::math
\sum_{d=1}^{30} 10 = 10 \times 30 = 300 \text{ words}
:::
```

## The rules

- **Neither `$` nor `\[` is a marker.** `$` is a character somebody
  writing about money types by accident — *it cost $4 billion* stays a
  sentence — and `\(…\)`, `\[…\]` and `$$…$$` are shown as typed. The
  square brackets and `{math}` are what every other mark of the dialect
  looks like.
- **The formula may hold brackets.** `[x \in [0,1]]{math}` and
  `[\sqrt[3]{x}]{math}` are ordinary mathematics: the formula runs to the
  `]{math}` that ends it, and no formula holds that. Spaces inside the
  braces are fine, `{ math }`.
- **A formula on its own may take several lines**; they are one formula.
  Break it the way LaTeX breaks one — `\\`, an `aligned` environment —
  not with blank lines. `:::MATH` is read like `:::math`.
- **A formula is left to right**, whatever the line around it: in a
  Persian or Arabic paragraph it stands as its own left-to-right island.
- **It goes wherever a line of prose goes**: a paragraph, a list item, a
  table cell, a footnote, a box, an exercise. It may not go inside the
  blank of a fill-in exercise.

```parseh-example
- the interval [x \in [0,1]]{math}
- a cube root, [\sqrt[3]{27} = 3]{math}

| Word | Letters |
|---|---|
| کتاب | [4]{math} |
```

```parseh-example
:::math
\begin{aligned}
(a+b)^2 &= a^2 + 2ab + b^2 \\
(a-b)^2 &= a^2 - 2ab + b^2
\end{aligned}
:::
```

## On the screen and on paper

**On the screen** a formula is drawn by MathJax, which comes with the
toolbox and is fetched only by a page that has a formula on it. Bad
notation is not hidden: MathJax draws what it can and marks the fault,
and the page keeps the notation as you wrote it. A page whose script does
not run — a page printed from the browser, a document opened from the
disk — still shows the notation itself.

**On paper** there is nothing to draw: the PDF is made with LaTeX, so the
notation goes through exactly as written and TeX sets it.

## In the editor

- **math** wraps the selected text in `[…]{math}`, brackets inside it
  kept, or puts an empty one at the cursor.
- **∑ Maths** opens a sheet: a box for the notation, the formula drawn
  under it as you type — with what is wrong said in MathJax's own words,
  *Missing close brace* — and the choice **in the line** or **on its
  own**. In the preview, pointing at a formula offers **✎** to open it in
  the same sheet again.

## Two rough edges

- **A formula after a bracket that is only prose.** A formula starts at
  its own square bracket, and a coloured word, a transliterated word, a
  link or a blank before it in the same paragraph stays what it is:
  `[تند]{teal} and [x^2]{math}` is a coloured word and a formula. A
  formula may hold brackets of its own (`\sqrt[3]{x}`, an interval such
  as `[0,1)` or `]0,1[`), so a bracket that is only prose — `[sic]`,
  `[1]` — earlier in the same paragraph cannot be told from one, and is
  taken into the formula. Put the formula first, or in a paragraph, an
  item or a cell of its own, or on its own lines with `:::math`.
- **A `:::math` must be closed.** Without its closing `:::` it takes the
  rest of the document into the formula.

```markdown
[sic] and its square [x^2]{math}                 <- one broken formula
Its square [x^2]{math}, and [sic]                <- both as meant
[تند]{teal} fast, and its square [x^2]{math}     <- both as meant
```
