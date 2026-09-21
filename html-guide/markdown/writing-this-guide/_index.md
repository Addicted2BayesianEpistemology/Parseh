---
title: Writing this guide
weight: 100
description: What a page is, where it lives, and how it becomes a web page.
---

These pages are the guide to Parseh. Each one is a Markdown file under
`html-guide/markdown/`, and `html-guide/build.py` compiles them into the web
pages you are reading. This section explains how to write one: the Markdown
it takes, how it is laid out, and how it is compiled and published.

## The short version

1. Write a page: a `.md` file anywhere under `html-guide/markdown/`. A folder
   is a section of the guide; its `_index.md` is the section's own page.
2. Give it a front matter with a `title`, and a `weight` to place it among
   its neighbours.
3. Compile. When Parseh is running, the guide's front page has a
   **Compile the guide** button whenever the pages have changed; the
   installer compiles them too, every time it runs.
4. Read it: the hub's **guide** button opens it, and so does
   `html-guide/index.html` opened straight from the disk.

```markdown
---
title: Recording a narration
weight: 3
description: One sentence under the title in the list of pages.
---

## Before you start

You need the book's **reader** built, and a recording of the book being
read aloud: see [the reading editions](../books/reading.md).
```

## What a page may hold

A page takes **all of Hugo's Markdown** (the Goldmark renderer, with the
extensions Hugo turns on by default) and **all of the Parseh studio's
dialect** — the same text a document in the studio holds, drawn the same
way. Where the two read the same text differently, the studio's reading
wins; [the table of those cases](parseh-dialect.md#where-parseh-wins) says
what each one does.

- [Pages and navigation](pages.md): the front matter, sections, the order
  of the list of pages, links between pages.
- [Hugo’s Markdown](markdown.md): headings, lists, tables, links, footnotes
  and every other construct, with what it looks like.
- [The Parseh dialect](parseh-dialect.md): target-language text, lemma
  headings, boxes, exercises and formulas, and where the dialect wins.
- [Code blocks](code-blocks.md): verbatim code with a Copy button,
  highlighting, and `parseh-example`, which shows Markdown beside what it
  becomes.
- [Pictures, recordings and videos](pictures.md): screenshots, GIFs,
  figures, players.
- [Shortcodes](shortcodes.md): Hugo's `{{< figure >}}`, `{{< details >}}`,
  `{{< ref >}}` and the rest.
- [Compiling and publishing](compiling.md): the compile, its warnings,
  GitHub Pages, and taking the guide into a project of its own.
