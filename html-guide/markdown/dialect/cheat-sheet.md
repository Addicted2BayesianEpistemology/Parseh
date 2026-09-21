---
title: Cheat sheet
linkTitle: Cheat sheet
weight: 2
toc: false
description: Every construct of the dialect on one page, with a link to where it is explained.
---

Every construct of the studio's dialect, each in one line. A small
document holding most of them comes first; the tables after it list
them all, with the page that explains each one. The exercises,
`:::exercise` blocks, are in a section of their own,
[Writing exercises](../dialect-exercises/_index.md).

```parseh-example
---
title: A lesson in one screen
subtitle: کتاب and its friends
lang: en
target: fa
---
## کتاب | ketāb | from Arabic *kitāb* | = *book*

The word کتاب = *book* takes the plural کتاب‌ها, and [یک PDF]{tl} is a
Persian phrase with a Latin word in it.[^1] **Bold**, *italic*, `code`,
[تند]{teal translit:tond} in colour, ✗کتابا wrong, ✅ کتاب‌ها right → done.

> **Remember:** a box holds anything, [\sqrt{16} = 4]{math} included.

- **Singular** کتاب
- **Plural** کتاب‌ها

| Form | Meaning |
|:--|--:|
| کتاب | a book |
| کتاب‌ها | books |

[The English under a Persian passage, centred and tinted.]{la align=center bg=sage width=70}

[^1]: A footnote, at the foot of the page on paper.
```

## The document

| Write | For | Page |
|---|---|---|
| `---` / `title:` `subtitle:` `note:` `lang:` `target:` / `---` | the front matter, first in the file | [Front matter](front-matter.md) |
| `# Title` | the title, when the front matter has none | [Front matter](front-matter.md#title) |
| `## Section` | a numbered section (a typed number is taken off) | [Headings](headings.md) |
| `### Subsection` | an unnumbered subsection | [Headings](headings.md) |
| `## word \| translit \| origin \| = *meaning*` | a vocabulary entry | [Headings](headings.md#vocabulary-entries) |
| `## word \| kana \| rōmaji \| origin \| = *meaning*` | a vocabulary entry in Japanese | [Headings](headings.md#japanese-the-reading-comes-first) |
| `## [word]{teal translit:…} \| \| origin` | a coloured headword, its transliteration in the braces | [Headings](headings.md#a-coloured-headword) |

## Text

| Write | For | Page |
|---|---|---|
| lines next to each other | one paragraph; a blank line starts the next | [Paragraphs](paragraphs-and-emphasis.md) |
| `**bold**`, `*italic*`, `` `code` `` | emphasis — never inside a word, never across the target language | [Paragraphs](paragraphs-and-emphasis.md#bold-and-italic) |
| `⏎` | a line break inside a paragraph | [Special characters](special-characters.md#the-line-break) |
| `✗form`, `❌form` | a wrong form, in red | [Special characters](special-characters.md#a-wrong-form) |
| `✅` | a green tick | [Special characters](special-characters.md#a-right-form) |
| `→`, `->` | an arrow, on the screen and on paper | [Special characters](special-characters.md#the-arrow) |
| the ZWNJ, `«»` | the zero-width non-joiner, guillemets | [Special characters](special-characters.md) |

## The target language

| Write | For | Page |
|---|---|---|
| کتاب, 日本語, नमस्ते in the prose | a run, found by its script | [Target language](target-language.md#words-found-by-their-script) |
| a paragraph of the script alone | a display line, set larger | [Target language](target-language.md#whole-paragraphs) |
| a paragraph with no Latin letter | a paragraph in the target language | [Target language](target-language.md#whole-paragraphs) |
| `[…]{tl}`, `[…]{fa}`, `[…]{ja}`… | a stretch marked as the target language; alone, a block | [Target language](target-language.md#marking-a-stretch-tl) |
| `[` … `]{tl}` on lines of their own | a passage of several lines | [Target language](target-language.md#several-lines-the-long-form) |
| `{tl bg=quote}` — `sand` `rose` `sage` `lilac` | a tinted block | [Target language](target-language.md#its-options) |
| `{tl font=nastaliq}`, `{tl font=gothic}` | the second face: Persian, Japanese | [Target language](target-language.md#its-options) |
| `{tl vertical height=14}` | vertical columns: Japanese, Chinese | [Target language](target-language.md#its-options) |
| `[bello]{tl}`, `[bello]{it}`, any mark | a run of a Latin-script target | [Target language](target-language.md#latin-script-targets-every-run-is-marked) |

## Marks on a word

| Write | For | Page |
|---|---|---|
| `[word]{crimson}` — `indigo` `teal` `violet` `amber` | a named colour | [Colours](colours-and-pronunciation.md#colours) |
| `[word]{#C2185B}` | any colour | [Colours](colours-and-pronunciation.md#colours) |
| `[word]{translit:…}` | its transliteration, shown on pointing | [Pronunciation](colours-and-pronunciation.md#transliteration) |
| `[word]{kana:… translit:…}`, `reading:` | its reading, in Japanese | [Pronunciation](colours-and-pronunciation.md#the-reading-kana) |
| `[word]{teal translit:…}` | colour and transliteration together, colour first | [Pronunciation](colours-and-pronunciation.md#transliteration) |
| `word = *meaning*` | a gloss, gathered into the glossary | [Glosses](colours-and-pronunciation.md#glosses) |
| `[a^2+b^2]{math}` | a formula in the line | [Mathematics](mathematics.md) |

## Blocks

| Write | For | Page |
|---|---|---|
| `> …` on every line | a box, which holds anything | [Boxes](boxes-and-latin-blocks.md#boxes) |
| `[…]{la align= bg= width= offset=}` as a paragraph | a Latin block; `{ltr}` is the same | [Latin blocks](boxes-and-latin-blocks.md#latin-blocks) |
| `- ` `* ` `+ ` / `1. ` `1) ` | a list; one level of nesting, two spaces in | [Lists](lists-and-tables.md) |
| `- **Label** text`, every item | a labelled list | [Lists](lists-and-tables.md#labelled-lists) |
| `\| a \| b \|` over `\|:--\|--:\|` | a table; `:--:` centres; `--` alone is an empty cell | [Tables](lists-and-tables.md#tables) |
| `:::math` … `:::` | a formula on its own | [Mathematics](mathematics.md) |
| `:::exercise type` … `:::` | an exercise | [Writing exercises](../dialect-exercises/_index.md) |

## Notes, links, media

| Write | For | Page |
|---|---|---|
| `text[^name]` and `[^name]: the note` | a footnote | [Footnotes](footnotes-and-links.md#footnotes) |
| `^[the note]` | a footnote written in place | [Footnotes](footnotes-and-links.md#footnotes) |
| `[words](https://…)` | a web link | [Links](footnotes-and-links.md#links-to-the-web) |
| `[](doc:Its name)`, `[words](doc:Its name)` | a link to another document, by its name | [Links](footnotes-and-links.md#links-to-other-documents) |
| `![caption](images/x.png){width=60 align=center offset=0}` | a picture, on its own line | [Media](media.md#pictures) |
| `![caption](audio/x.mp3){start=1:05.2 end=1:09}` | a recording, and the stretch it plays | [Media](media.md#recordings) |
| `@[caption](youtube address){start=90 end=150}` | a YouTube video | [Media](media.md#videos) |

## Not in the dialect

`####` headings, `===` underlines, code blocks, `_x_`, `~~x~~`, `$x$`,
HTML, escapes, reference links, bare addresses, rules (dropped): see
[What the studio leaves out](left-out.md).
