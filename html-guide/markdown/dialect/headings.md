---
title: Headings and vocabulary entries
linkTitle: Headings and vocabulary
weight: 5
description: Numbered sections, subsections, and the lemma heading that sets a word large with its transliteration, origin and meaning.
---

## Three levels

A heading is one to three `#` signs, a space, and its text, on a line of
its own:

| You write | You get |
|---|---|
| `# Title` | the document's title, when the front matter has none; otherwise nothing ([Front matter](front-matter.md#title)) |
| `## Section` | a **numbered section**: 1, 2, 3… in the order they come |
| `### Subsection` | an unnumbered subsection inside it |

```parseh-example
## Nouns

### The plural

### The ezafe

## 7. Verbs
```

The studio **numbers the sections itself**, so a number typed in front of
a `##` heading — `7.` or `7)` — is taken off, or it would come out twice.
A `###` heading keeps whatever it says. Both kinds, and the vocabulary
entries below, are listed in the reading view's **☰ Contents**, and each
is a heading of the PDF.

A few things are **not** headings here:

- `####` and deeper: the line is text, signs and all.
- A heading underlined with `===` or `---`: the words are a paragraph,
  and the underline is either more of it (`===`) or a rule, dropped
  (`---`).
- `#` signs at the end of a heading are not taken off: `## Verbs ##`
  reads *Verbs ##*.
- An ending `= *…*` on a `##` heading is taken off and lost; it means
  something only on a vocabulary entry, below.

## Vocabulary entries

A `##` heading whose parts are separated by `|` and which starts with a
word of the target language is a **vocabulary entry** — the studio calls
it a *lemma*. The word is set large in the target language's face, and
beside it, in a column of their own, its transliteration and where it
comes from:

```parseh-example
## کتاب | ketāb | from Arabic *kitāb* | = *book*

The entry itself follows as ordinary paragraphs and lists.
```

Its parts, in order:

1. **The headword**, in the target language.
2. **The transliteration** — how it is said.
3. **The origin**, or any short remark: it takes italics, colours and
   words of the target language like any line of prose.
4. **The meaning**, as `= *…*`. It is printed nowhere — the entry below
   says it — and exists to put the word into the document's glossary
   (**⇄ Glosses**), where the button **Lemmas only** narrows the list to
   the words that head an entry.

Only the headword and one more part are needed. A part may be left empty
between its bars, and the meaning may be left out:

```parseh-example
## آب | āb | = *water*

## خانه | | Middle Persian *xānag*
```

### The meaning, two ways

The meaning may be its own last part, after a bar — there the italics are
optional, since the bar says where it starts — or hung off the end of the
origin, where the italics are **required**:

```markdown
## تند | tond | mp. tund | = *fast, sharp*
## تند | tond | mp. tund | = fast, sharp
## تند | tond | mp. tund = *fast, sharp*
```

The first two give the meaning a part of its own, with and without
italics; the third hangs it off the origin. The three read the same. Without italics and without the bar, an `=` in
the origin is part of the origin — which is why an etymology may say
`'x = y'` without losing half of itself to the glossary.

### A coloured headword

The headword may wear a colour — one of the five names or a `#` and six
hexadecimal digits ([Colours](colours-and-pronunciation.md#colours)) — and
its transliteration may ride in the same braces, leaving its own part
empty:

```parseh-example
## [کتاب]{teal} | ketāb | from Arabic *kitāb* | = *book*

## [خانه]{#8E2B34 translit:xāne} | | mp. *xānag* | = *house*
```

A transliteration written in the heading's own part wins over one in the
braces. The braces may also hold `{tl}` or the language's own code
(`{fa}`), which colour nothing, or a `translit:` (and, in Japanese, a
`kana:`) with no colour at all: `## [کتاب]{translit:ketāb} | | …`. A
colour name the studio does not know leaves the headword black.

You rarely type the colour: point at the headword in the reading view or
the preview, and the cloud that opens is the colour cloud of any word
([Colours](colours-and-pronunciation.md#colours)) — a click on a swatch
writes `## [کتاب]{teal} | …` into the heading, and **✕** takes the colour
off again. That cloud holds **only the colours** for a headword: it never
shows or edits its transliteration or its reading, which are written in
the heading's own parts and shown in the entry itself.

### What makes a heading an entry

The studio decides by the **first part**:

- **For a language with its own script** — Persian, Arabic, Hindi,
  Japanese, Chinese — the first part must *start* with a character of that
  script, or be one mark, `[…]{…}`, whose words start with it
  (`## [حرکت آهسته]{teal} | …` is an entry). So a heading that
  starts with the script and holds a `|` is always an entry; a section
  title that must hold a `|` starts with a word of the prose instead.
- **For a Latin-script target** — Italian, French, German, Turkish,
  English, Spanish — nothing tells a word of the language from a word of
  the prose, so **any** `##` heading with two or more parts is an entry.
  A section title there cannot hold a `|` at all.

```parseh-example
---
target: it
---
## pesca | pèsca | Latin *persica* | = *peach*

## [casa]{teal} | càṡa | = *house*
```

The headword is set exactly as typed, one word or a few: nothing inside
it is read as Markdown. A heading whose first part starts with the script
and then holds a mark further on (`## کتاب و [قلم]{teal} | …`) is an entry
whose headword shows the brackets as typed; one whose first part is two
marks with words between them is not an entry at all, but a numbered
section with its marks drawn.

### Japanese: the reading comes first

A language with a **reading** — Japanese is the one — has one part more:
the reading in kana comes **second**, before the rōmaji. The kana is shown
above the rōmaji.

```parseh-example
---
target: ja
---
## 日本語 | にほんご | nihongo | 日本 *Japan* + 語 *language* | = *Japanese*

## [猫]{teal translit:neko} | ねこ | = *cat*
```

In Japanese the second part is **always** the reading: `## 猫 | neko`
shows *neko* where the kana goes. To give the rōmaji without the kana,
leave the reading empty, `## 猫 | | neko`. The braces of the headword may
carry the reading too, `{kana:ねこ translit:neko}`, for the parts left
empty.

Chinese has no reading part: the pinyin is its transliteration, second as
in Persian.

```parseh-example
---
target: zh
---
## 学习 | xuéxí | = *to study, to learn*
```

### On the page and on paper

In the reading view an entry is a band across the page between a rule
above and a thinner one below: the headword on the left, in the target
face, as large as the typography bar's **Lemma** slider says; on the
right the reading in grey, the transliteration in italics in the accent
colour, and the origin small and grey under it. Each entry is listed in
**☰ Contents** with its transliteration. Point at the headword and the
cloud that opens offers only the colours: the transliteration and the
reading are shown in the entry, and edited in the heading's own parts.

In the PDF the headword is set in 38-point type (larger in large print)
in a column six tenths as wide as the text, and scaled down if it is
wider than that column; the reading, the transliteration in the accent
colour, and the origin stand in the narrower column beside it.
