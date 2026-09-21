---
title: Pages and navigation
weight: 1
description: Front matter, sections, the order of the pages, and links between them.
---

## Where a page lives

Every `.md` file under `html-guide/markdown/` is a page, and its path is its
address: `markdown/studio/exercises.md` becomes `site/studio/exercises.html`.
A folder is a **section**. Its `_index.md` — Hugo's name for it — is the
section's own page (`site/studio/index.html`), gives the section its title
and its place, and ends with the list of the pages inside it. A section
without an `_index.md` still appears in the list of pages, named after its
folder, and simply has no page of its own.

```text
html-guide/
  index.html                 the front page, written by hand (not compiled)
  markdown/
    _index.md                the guide's own front matter: its title
    showcase.md              a page:            site/showcase.html
    images/flashcard.gif     a picture, copied: site/images/flashcard.gif
    writing-this-guide/
      _index.md              the section's page: site/writing-this-guide/index.html
      pages.md               a page in it:      site/writing-this-guide/pages.html
```

Any other file under `markdown/` — a screenshot, a GIF, a PDF — is copied to
the same place under `site/`, so a page names a picture by its path from
the page: `![The editor](shots/editor.png)`.

The root's `markdown/_index.md` does not draw a page. Its `title` is the
guide's name, on every page's bar and in every tab; the front page is
`html-guide/index.html`, written by hand, because it has to work before
anything has been compiled.

## Front matter

A page starts with its front matter, in any of the three forms Hugo reads:
YAML between `---` lines, TOML between `+++` lines, or a JSON object.

```yaml
---
title: Recording a narration
linkTitle: Narration
weight: 3
description: The narration of a book, recorded and aligned.
toc: false
target: ja
lang: en
aliases: [old/narration.md]
draft: true
---
```

```toml
+++
title = "Recording a narration"
weight = 3
+++
```

```json
{
  "title": "Recording a narration",
  "weight": 3
}
```

| Key | What it does |
|---|---|
| `title` | The page's title: at the top of the page, in the list of pages, in the tab. Without one, a first line `# Title` is the title; without either, the file's name. |
| `linkTitle` | A shorter title for the list of pages and the prev/next links. |
| `description` | A sentence under the page's name in its section's list, and in the search results. |
| `weight` | The page's place among its neighbours (below). |
| `draft` | `true` leaves the page out: it is not compiled and not listed. |
| `toc` | `false` hides the page's own contents (**On this page**). |
| `aliases` | Old addresses of the page; each gets a small page that goes on to this one. |
| `target` | The language the page's target-language text is in (below). |
| `lang` | The language the page's prose is written in; English when not given. |
| `subtitle`, `note` | The studio's: a line under the title, and a small note under the rule. |
| anything else | Kept, and readable with `{{< param "key" >}}`. |

Keys are read whatever their case (`linktitle`, `linkTitle`), as Hugo reads
them.

### The target language

A page's target-language text — `[کتاب]{tl}`, an automatic Persian
paragraph, a lemma heading, an exercise — is read in the language its
`target:` names, a code from Parseh's language registry: `fa`, `ar`, `it`,
`ja`, `fr`, `de`, `tr`, `en`, `hi`, `es` or `zh`. Without a `target:` a page
is read as Persian (`fa`), exactly as a document in the studio is: Persian
text is then found and set right to left on its own, and every other
language's text needs a page, or a [`parseh-example`](code-blocks.md#showing-markdown-and-what-it-becomes)
block, that names it.

## The order of the pages

The list of pages on the left — the sidebar — is the sections and pages in
the order Hugo gives them: by `weight`, smallest first; a page with no
`weight` after every page with one; then by title. A section takes the
`weight` of its `_index.md`. **Previous** and **Next** at the foot of each
page follow the same order, a section's own page before the pages in it.

The sidebar remembers what you did with it: closed with ☰ it stays closed
on the next page, and a section opened or closed by hand stays so. The
section of the page you are reading is always open, and the page itself is
marked. On a phone the sidebar is a drawer that ☰ opens over the page.

## Links between pages

Link to another page by its file, relative to the page you are writing:

```markdown
See [pages and navigation](pages.md), [a heading on it](pages.md#front-matter),
[the section](../writing-this-guide/_index.md) or [the showcase](../showcase.md).
```

The compile turns `.md` into the page's `.html` address and checks the page
is there: a link to a page that is not is said at compile time, with its
file and line. Three other ways reach a page:

- `[label](doc:Title)` — the studio's cross-document link, here by the
  target page's **title**: [Code blocks](doc:Code blocks). Left empty,
  `[](doc:Shortcodes)` shows the page's title: [](doc:Shortcodes). A link
  to a title no page has is drawn as the studio draws a dead link, and said
  at compile time.
- `{{< ref "code-blocks.md" >}}` and `{{< relref "code-blocks.md#nested-fences" >}}` —
  Hugo's, as the address of a link: `[code]({{< ref "code-blocks.md" >}})`.
  A `ref` to a page that is not there stops the compile with an error, as
  in Hugo.
- A heading's own address, `#its-id`: every heading has one (the # beside
  it when you point at it), made the way Hugo makes it — the words in lower
  case, joined by `-`: `## Front matter` is `#front-matter`.

Every address the compile writes is relative and names its file, never a
folder, and never starts with `/`: that is what lets the same pages work
opened from the disk, served by Parseh under `/guide/`, and published on
GitHub Pages under the repository's name. Write your own links the same
way; an address starting with `/` is said at compile time.
