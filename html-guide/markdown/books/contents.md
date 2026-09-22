---
title: Contents, sections and folding
linkTitle: Contents and folding
weight: 4
description: The contents as a tree, naming chapters and sections, and folding a run of paragraphs out of the way.
---

A long book needs a way about it, and a way to put parts of it out of the
way. Three tools in the reader's header do that: the contents, the chapters
and sections sheet, and folding.

## The contents

**contents** in the header, or **C** anywhere on the page, opens the table
of contents: one row per paragraph, with its number and its opening words,
grouped under its chapter and, where the book has them, its sections.

- **Type to filter.** The box at the top (*filter by number or opening
  words*) keeps only the paragraphs that match. You need not type the vowel
  marks of Persian or Arabic, nor mind the case: the filter ignores both.
  **Enter** jumps to the first match; **↓** and **↑** walk the matches.
- **Click a row** to jump there. The panel closes and the page scrolls to the
  paragraph — fetching its chapter first, if it has not arrived yet, and
  opening it if it is folded away (below). *nothing matches* says so when the
  filter finds nothing.
- **It is a tree.** Each chapter and each section has a **▾** that folds it
  shut and opens it again. **fold all** leaves the chapter names alone, to
  walk the book at that depth; **open all** opens everything. Nothing is
  folded when the page loads. What you fold stays folded when you close the
  contents and open them again, until you open it (or press **open all**) or
  reload the page. Typing in the filter opens everything, so a match is
  never left hidden inside something folded — and what it opened stays open
  when you empty the box again.
- **×**, **Esc** or a click outside close it.

A row is an ordinary link, so the paragraph's address goes into the address
bar — [The reader](doc:The reader) says what that is good for.

## Picking a part of the book

Three sheets name a part of the book: what is folded away, where a section
opens, and what a recording covers ([Adding a narration](doc:Adding a narration)).
All three show the book the same way, as an outline. Its rows are the
chapters, each with its name and how many paragraphs it has. A chapter opens
(**▸**) on its sections and its paragraphs, each paragraph by its number and
its first words, in the book's own script. For a recording, a paragraph opens
on its subparagraphs too.

- **A click takes a whole thing**: a chapter, a section or a paragraph.
  Click what is picked again to open it and go finer.
- **Shift-click** another row to take everything from the first to it. On a
  phone, or without Shift, press **stretch it to…** and then pick where it
  ends.
- What is picked is tinted, its two ends say *from* and *to*, and the line
  under the outline says it in words: *chapter 2 · The Wind · 14
  paragraphs*, *chapters 2–4 · 38 paragraphs*, *chapter 2, ¶ 3 → chapter 3,
  ¶ 1 · 5 paragraphs*.
- The box above the outline finds a paragraph by its number or by its
  words, and shows it where it is, under its chapter and its section.
  **open all** and **close all** open and close every chapter and section.
- From the keyboard, the arrows walk the rows, and **→** and **←** open and
  close them. **Enter** or **Space** picks, and with **Shift** they stretch.
  **Esc** lets a half-made stretch go, or empties the box, before it closes
  the sheet.

## Chapters and sections

**sections…** at the top of the contents — or the **✎** beside a chapter
or a section in the tree — opens the **chapters and sections** sheet. Its
first line counts what the book has (*1 chapter, no sections in this book*).
Below it is the book as an outline (above): pick what you want to name. The
sheet opens on the paragraph you are reading, or on what the **✎** stood
beside.

**A chapter's name.** Pick the chapter, type what it is called, and press
**name it** (or **Enter**). The name is shown under the chapter's number in
the text and beside it in the contents. Leave the box empty and press the
button to take the name away: the chapter is called by its number alone
again.

**A section.** A section marks a place between two paragraphs: pick the
paragraph it starts at, type its title, and press **start a section here**.
It has no number of its own and changes no paragraph's number — it is a
heading in the text and a row in the contents, nothing more. A section
already in the book is a row of the outline, **§** and its title. Picking it
picks the paragraph it opens at, and offers **rename this section** and
**remove this section**.

Both are written into the chapter's own `.tex` file (as `\chapname` and
`\secmark`), so they travel with the book when you download it. The reader
is rebuilt at once; the heading and the rows of the contents are written at
build time, so the answer says *— reload to see it in the book* and offers
**reload the reader**. A refusal is shown whole, in the sheet, in its own
words; from a page opened off the disk, nothing is written and the sheet
says so.

Chapters and sections also matter to the narration: **stop at a change**
holds the playing at the start of each new chapter or section
([Playing and listening](doc:Playing and listening)).

## Folding a run of paragraphs away

**fold** in the header opens the **folded away** sheet, on the paragraph
you are reading. Pick a run of paragraphs in the outline — a paragraph, a
section, a chapter, or a stretch of them ([Picking a part of the
book](#picking-a-part-of-the-book)) — and **fold these away** folds it:

- their text is not shown; one bar stands in its place, saying how many
  paragraphs are folded (*6 paragraphs folded away*). Click it to **show them
  here** — the book keeps them folded, and the bar then says **fold them
  away again**;
- reading walks past a folded run. With a narration the playing jumps from
  the subparagraph before the run to the first one after; with no
  narration the **→** and **←** keys do the same. **listen** does it the other
  way round: it stops at the run, and the next press goes on after it
  ([Playing and listening](doc:Playing and listening));
- the sheet lists every run already folded, in words (*chapter 2, ¶ 2 →
  chapter 3, ¶ 1 · 2 paragraphs*; click it to see it in the outline), each
  with **unfold**. In the outline, a folded paragraph says *folded*. Two runs
  that meet become one.

Nothing is deleted, and the build knows nothing of it: the runs are kept in
`reading.json` beside the book, which travels in its download, so it is the
*edition* that is folded, not one machine's view of it. A front matter, a
dedication, an apparatus, a chapter you have read and do not want again —
they go out of the way without a byte of the text being lost.

The sheet answers *folded away* or *unfolded*. The page folds at once,
without a reload; the server also rebuilds the reader so that the next
visit agrees, and if that rebuild fails the answer says so.

A reading place saved inside a run you have since folded is not a reason to
unfold it: opening the book again goes to the bar standing where your place
is.

**An older book** built before folding existed has no **fold** button: press
**rebuild the reader** (or **rebuild** on its card) and it has one. The folds
were never in the page anyway — they live in `reading.json` — so nothing is
lost by rebuilding.
