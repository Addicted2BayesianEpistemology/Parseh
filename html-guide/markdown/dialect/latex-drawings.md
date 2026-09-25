---
title: LaTeX drawings
weight: 13
description: Chemistry, drawings, plots and units drawn by LaTeX itself, in a ::::latex block beside the formulas MathJax draws — with named themes, made in Settings, and a drawing that travels to paper, to a web page and onto a phone.
---

A formula is written with `[…]{math}` or `:::math`, and MathJax draws it
([Mathematics](mathematics.md)). That is still **the ordinary way to write
mathematics**: nothing to install, drawn in the page, on a phone and
offline. What MathJax cannot draw — a chemical reaction written with
`mhchem`, a molecule with `chemfig`, a drawing or a plot with TikZ, units
with `siunitx` — LaTeX itself can, and a **latex block** asks it to.

A latex block is **optional**. It needs TeX on the computer Parseh runs on
(TeX Live or MiKTeX): a document without one is read exactly as before.

## Writing one

Between a line `::::latex` and a line `::::` — **four colons**, one more
than a formula's fence, so that a block may also stand in a Jolly card's
field, where a line of three colons ends the exercise:

```markdown
::::latex chemistry {width=45 align=center}
\ce{2H2 + O2 -> 2H2O}
::::
```

![The reaction, as LaTeX draws it](images/latex-reaction.svg){width=45 align=center}

- **The word after `latex`** names a [theme](#themes): the packages the
  drawing is compiled with. No word, the default theme.
- **The braces** are a figure's own: `width`, a percentage of the column
  from 5 to 100; `align`, `left`, `center` or `right`; `offset`, a
  sideways shift, as for a picture. With **no width** a drawing is at its
  natural size, measured against the text round it: it reads at the size
  of the words beside it and grows with them. With **no align** it is
  centred, as a formula is. On a card there is no offset.
- **The body** is LaTeX, exactly as it would stand between
  `\begin{document}` and `\end{document}`.

```markdown
::::latex chemistry
\chemfig{H-[:30]O-[:-30]H}
::::
```

![Water, drawn with chemfig](images/latex-water.svg)

```markdown
::::latex drawing {width=50}
\begin{tikzpicture}
\draw[->] (0,0) -- (2,0) node[right] {$x$};
\draw[->] (0,0) -- (0,1.5) node[above] {$y$};
\draw[thick,domain=0:1.8] plot (\x,{0.4*\x*\x});
\end{tikzpicture}
::::
```

![A parabola, drawn with TikZ](images/latex-tikz.svg){width=50 align=center}

In the editor, **LaTeX drawing** opens a sheet: the theme, the LaTeX, the
drawing as the computer makes it while you type, and its size and side. In
the preview, **✎** on a drawing opens it again. In the exercise form,
**LaTeX drawing…** puts one in the field of a Jolly card you were last in.

## Where it goes

Wherever a `:::math` formula may go — a document, a box, a note in a book
or a video — and in the four fields of a Jolly card, in a document and in a
deck. Not in an exercise's other fields, which are lines of prose.

## Drawn once, the same everywhere

A block is compiled **on its own**, in a document of its own with its
theme's preamble, and becomes a picture. So its packages can never change
an ordinary formula, and the screen and paper show **the same drawing**:
the page shows it as a vector picture, the PDF includes it, an [HTML
export](../studio/web-page.md) carries it inside the file, and a page kept
on a phone keeps it. In the PDF it is a picture, not text you can select,
and it is set in LaTeX's own face.

It is made **once** and kept (`markdown/latex/`), and made again only when
something that decides what it looks like changes: the block, its theme's
packages, preamble or compiler, the TeX installation, or Parseh's way of
drawing. Renaming a theme redraws nothing.

## When it cannot be drawn

A block that cannot be drawn shows **its source**, in a frame, and **one
line saying why**, in plain words and with the line of the block where
LaTeX says one: a command a package would give (*\ce is not a command the
theme "default" knows… tick mhchem*), a brace missing, a package not
installed, a theme this Parseh does not have, a compiler this computer
lacks, a drawing that took too long. The rest of the page is drawn. On the
computer the frame has the button that mends it — the theme, **Install…**,
or **Import a theme…** and **Make a theme called …** for a theme that is
not here. In the PDF and in an export the frame stands where the drawing
would, and the PDF's badge says how many could not be made.

## Themes {#themes}

**Settings → LaTeX drawings** holds the themes, as many as you like, each
with a name of one word:

- **Packages** as checkboxes, each with a line and an example: `amsmath`,
  `amssymb`, `amsfonts`, `mathtools`, `bm`, `xcolor`, `siunitx`,
  `physics`, and `mathrsfs`, `dsfont`, `esvect`, `stmaryrd`, `wasysym`,
  `marvosym`, `cancel`, `slashed`, `relsize`, `amsthm`, `tikz`, `tikz-cd`,
  `bayesnet`, `pgfplots`, `circuitikz`, `mhchem`, `chemfig`, `listings`,
  `algorithm2e`.
- **Text in the languages Parseh teaches**: each language's face, as
  `\textfa{…}`, `\textja{…}`, `\texthi{…}` and so on, right to left
  where it is written so.
- **A font** of this computer's for the drawing.
- **A preamble of its own**, after the packages.
- **The compiler**: xelatex (a new theme's), pdflatex or lualatex.

A fresh Parseh has three: **default**, which a block naming no theme is
drawn with, **chemistry** and **drawing**. **Make it the default** gives
another theme that part. **Export** saves a theme as a file to send to
somebody; **Import a theme…** reads one, and shows its whole preamble before
it is kept, under a name no other theme has. **Rename…** says first how
many blocks name the theme, and where — *3 documents, 1 exercise deck, 2
notes* — then rewrites the name in every one of them; if one of them cannot
be written (a deck taken out on a phone), nothing is renamed.

The same page says which of the three compilers this computer has, gets
the **TeX packages** a theme needs into Parseh's own folder `texmf/` — what
it costs said first, then its progress, and **Stop** — with each package's
licence, and sets **how long a drawing may take** (30 seconds to begin
with). **Forget drawings nothing uses** frees the space of the drawings no
block asks for; a drawing nothing has asked for in 30 days goes by itself.

Everything on the page is changed on the computer Parseh runs on: a phone
sees it all, with its locks, and may export a theme.

## Going back to an older Parseh

A version before a0.4.0 does not know a latex block: it shows its lines as
text. Going back from **Settings → Updating Parseh** says so first, under
*What may not survive going back*, and asks *I understand*. Nothing is
deleted, and when you come forward again every drawing is there.
