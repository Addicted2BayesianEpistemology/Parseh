# exlex authoring prompt

Copy everything below the horizontal rule and paste it **before your
question** (in the same message). The model will produce a `.md` file;
download it and open it in exlex studio (*Upload .md*), or run
`exlex.py build` on it, to get the typeset, verified PDF.

The prompt is generic: the language the document is about is named by
the `target:` line of the front matter, and its value is one of the
codes in the toolbox's registry, `lib/languages.json` -- the one table
that says which languages there are. The studio's prompt page has a
select for it, states the target at the top of the copied text and
appends that language's own conventions (`docs/lang/<code>.md`: the
transliteration scheme, the reading rule, what to hyphenate, what never
to gloss).

---

You are writing a document for **exlex**, a toolchain that compiles
Markdown into a XeLaTeX PDF with the text of a **target language** (the
language being learned, set in large type in its own script and
direction) embedded in prose written in another language.

Answer the question that follows by **creating a markdown file**: an
actual `.md` file, written and saved as a file, not a fenced code block
inside your reply. Give it a short name derived from the topic. The file
must contain the document and nothing else — no preamble, no commentary
around it; anything you want to say to me goes in the chat, not in the
file. Follow the rules below exactly, and write the prose in the
language of the question.

**Before everything: the features below are tools, not tasks.** The
rules describe two different things. Some fix the *format* (front
matter, headings, how the target language must be written) — follow
those always. The others (footnotes, links, colour marks, ✗/✅, blocks
and their styling) describe *optional machinery*: reach for a feature
only when the content genuinely calls for it, exactly as you would reach
for italics — and it is completely normal for an answer to use few of
them or none. Never use a feature to demonstrate it, never construct an
example *in order to* exercise one (a sentence mixing the two languages
belongs in the document only if that mixture is what you are teaching),
and never let the set of available features shape what you say. Above
all, the document must contain **no trace of the machinery itself**:
the reader sees a typeset essay, and must find nothing about "this
document", its colours, its markup, its rendering, or what any tool
"allows us" to show. If a sentence talks about the document instead of
the subject, delete it.

**1. Front matter.** Start the file with:

```
---
title: <short title>
subtitle: <one line; may contain the target language>
note: <optional small line under the title>
lang: <ISO code of the prose language: en, it, fr, de, es …>
target: <registry code of the language the document is about>
---
```

`target:` names the language being learned; it decides the script,
the direction, the fonts and which headings are lemma entries, so set
it before anything else (omitted, the document is taken to be about
Persian). `lang:` is the language of the **prose** — it is not
decoration: it picks the hyphenation patterns the typesetter breaks
words with, and one language's patterns applied to another are worse
than none at all. Set it to the language you are actually writing the
prose in — the language of the question. If you omit it the document
is typeset as English. The two may coincide only when the prose and the
target are both Latin-script languages; then rule 4 says how the target
is told apart.

**2. Structure.** `##` for sections, `###` for subsections. Never go
deeper. No `#` heading (the title comes from front matter). Sections
are **numbered automatically by the toolchain** — never number them
yourself: write `## The four words`, not `## 2. The four words`
(a hand-typed number would come out doubled). A section title never
contains a `|`: that character makes a heading a lemma entry (rule 3).

**3. Lemma entries.** For each headword treated in depth, use a `##`
heading of the form:

```
## <headword> | <transliteration> | <short etymology note> | = *translation*
```

When the target language has a **reading** (Japanese: the kana), it is
a field of its own, **before** the transliteration:

```
## 漢字 | かんじ | kanji | <etymology> | = *translation*
```

The last field is optional and **is printed nowhere**: the heading
already carries the transliteration and the etymology, and a translation
set beside them would only repeat what the entry goes on to say. It
exists so the headword joins the document's glossary, which otherwise
sees only the words glossed in running prose. Give every lemma one, and
put in it the senses the entry actually treats:
`## تند | tond | mp. tund, 'sharp, violent' | = *sharp, spicy, fast*`.

The first field must be the headword alone, in the target language; it
is typeset very large. Everything under it until the next heading
belongs to the entry. Inside an entry, use a bullet list where
**every** item starts with a bold label — `- **Attributive** ...`,
`- **Register** ...`, in the language of the document — such lists are
rendered as definition lists.

**4. Text in the target language.** Write it inline as plain Unicode,
exactly where it belongs in the sentence, in its own script. Never
transliterate instead of writing it; never put Latin letters, Western
digits, or markdown syntax *inside* a phrase of the target language.
Use the script's own conventions (ZWNJ where Persian orthography
requires it: می‌رود, به‌آهستگی). Multi-word phrases are fine; the
toolchain keeps them together and sets them in the right direction.

How a stretch of the target language is *recognised* depends on its
script:

- **A target with its own script** is **detected**: every run of its
  script is set in the target font automatically, and nothing has to be
  marked for that.
- **A Latin-script target** — one written in the same alphabet the prose
  is — cannot be told apart from the prose, so **every run of it is
  marked**: `[bello]{tl}`, or with the language's code, `[bello]{it}`.
  Any bracket mark already carrying a transliteration or a colour counts
  as the mark too (`[bello]{translit:'bɛl.lo}`, `[bello]{teal}`): a
  bracketed word with attributes is a run of the target language.
  Glosses are then written `[bello]{tl} = *beautiful*`. A word of the
  prose language is never marked, and a marked word is never a word of
  the prose.

**Mixed-direction sequences: distinguish the direction of a run from the
direction of its container.** This distinction is mandatory for a
right-to-left target. A continuous target-language phrase or sentence is
one RTL unit: write it in normal logical/read-aloud order inside a single
`[…]{tl}` mark (or leave it as the dialect otherwise permits), and never
reverse anything inside it.

A line of LTR prose can instead contain several **separately marked RTL
components** divided by operators, punctuation, labels, numbering, or
intervening prose. This occurs in questions, answers, morphological
analyses, derivations, lists, tables, and comparisons. In that case each
marked RTL run is an indivisible visual box, while the containing
expression and separators remain LTR. Write the boxes in the Markdown in
the order they must appear **from left to right on the rendered page**.
For successive parts of an RTL word or phrase, that box order is normally
the reverse of the linguistic/read-aloud order. Reverse only the boxes;
keep the characters and punctuation inside each box in natural order.

For example, Persian *dānešgāh* is analysed from the right as `dān + -eš
+ -gāh`, but an LTR expression showing its isolated components must be
authored as:

```
[گاه]{#6B6B1A translit:-gāh} + [ش]{#C28E0E translit:-eš} + [دان]{translit:dān}
```

Do not put the read-first root *dān* in the leftmost visual box: once the
RTL runs are isolated, that displays the component sequence backwards. The
same rule applies with `→`, `=`, `/`, commas, parentheses, bullets,
numbering, or any other LTR separator or surrounding prose; it is not a
special property of `+`. Before returning a mixed-direction line, inspect
its intended visual order from left to right and then check that reading
the RTL components from right to left gives the intended linguistic order.

**Punctuation: use the Latin mark almost everywhere.** The target
language's own punctuation — the Arabic comma `،`, semicolon `؛`,
question mark `؟`; the Japanese `。`, `、` — belongs **only inside a
continuous sentence or clause of the target language of its own**
(typically inside a `[…]{tl}` block or a full display line).
Everywhere else the document is running prose in the language of the
question, and that prose takes its own Latin punctuation. It is a
common and incorrect reflex to reach for the target's mark whenever
punctuation sits next to its script; do not do this. The test is
always what the mark itself is punctuating — the sentence structure of
the target language, or that of the prose you are writing in — never
how much of the target's script sits on either side of it.

A comma that separates **items in a list**, or that punctuates the
surrounding prose sentence, is doing Latin work even when every item on
either side of it is a word or phrase of the target language — use `,`:
`کند, سریع, تند` (never `کند، سریع، تند`), and likewise `not
[کند]{translit:kond} but [تند]{translit:tond}`. The same holds for the
semicolon: `[تندرو]{translit:tond-row} = *fast-moving*, and in politics
*extremist*; [تندباد]{translit:tond-bād} = *squall*` takes the Latin
`;`, because it separates clauses of the surrounding prose sentence,
not two halves of one clause of the target language. This holds
however short the items are and however many of them there are in a
row.

The question mark is the one member of this family that does stay the
target's — but only when the whole sentence it closes is in the target
language: چرا این‌قدر یواشی؟ = *why are you so slow?* A question
*about* a word or phrase, asked in the language of the document, still
ends in the Latin `?`.

**Transliteration marks — required for lone words and short groups.**
Every time the target language stands in the prose as a **word or a
short group of two or three words** — an inline mention, the subject
of a gloss, a table cell, a fixed collocation cited as a unit (a
preposition + noun, a noun + light verb such as عجله کردن or کند شدن)
— write it as `[تند]{translit:tond}` or `[یواش برو]{translit:yavâš
borou}`. This is a format rule, not an optional tool: the mark leaves
no visible trace (the text renders exactly as if bare, on screen and
on paper), but the studio shows the transliteration when the reader
hovers it. Use the same scholarly transliteration you would put in a
lemma heading (the conventions of the target language, appended to
this prompt, give the scheme).

**The reading mark**, for a target language that has a reading
(Japanese): the kana of the whole word or group goes in the same
braces, before the transliteration — `[漢字]{kana:かんじ
translit:kanji}`, `[水の音]{kana:みずのおと translit:mizu no oto}`.
Give it wherever a transliteration is given; the kana is the reading
of the whole bracketed text, never a per-character alignment.
`reading:` is accepted as an alias of `kana:`.

Do **not** add these marks to a full **example sentence** — anything
with a subject-and-verb reading, an imperative addressed to "you", or a
question, even a short one (زود بیا, چرا این‌قدر یواشی؟) — those stay
optional, exactly like any other multi-word phrase. The line is what
the group *is*: a citation form or a fixed expression gets the mark: a
sentence demonstrating usage does not. Also skip `##` lemma headings
(they already carry a transliteration field), display lines, and
`[…]{tl}` blocks. A colour mark can share the braces:
`[تند]{teal translit:tond}`.

For a language with its own script, a paragraph containing **no Latin
letters at all** is laid out as a block of prose in that language
automatically — right-to-left for Persian and Arabic, left-to-right in
the target font for Japanese — ASCII punctuation (`!`, `.`, `…`) and
emoji included, so `درود!!! چطوری؟` reads correctly. When a sentence of
the target language must *contain* a Latin word or number, wrap the
whole stretch as `[…]{tl}` (the document's own code, `{fa}`, `{ja}`…,
is an alias; `{fa}` and `{rtl}` are the old Persian spellings and still
work):

```
[امروز یک فایل PDF فرستادم]{tl}
```

Everything inside stays one unit in the target language's direction
(the Latin word becomes an embedded left-to-right island). The content
of `[…]{tl}` is opaque: no markdown, no glosses, no footnotes inside
it. Use it only when Latin material genuinely belongs inside the
sentence — for a gloss, keep the usual pattern `<target> =
*translation*` instead. For a Latin-script target a whole paragraph
wrapped this way is a paragraph in the target language; inside prose
the same mark is simply how a run is written (above).

Newlines in the source are **ignored** (consecutive lines join into one
paragraph); to force a real line break, write the symbol `⏎` where the
break belongs. A longer `[…]{tl}` block may be written across several
lines for readability, with `⏎` closing each line that must end there:

```
[
امروز هوا آفتابی است.⏎
به پارک رفتیم
]{tl}
```

The marker accepts optional styling: `{tl font=<alternate>}` switches
to the language's alternate face where it has one (`nastaliq` for
Persian, `gothic` for Japanese), `{tl bg=quote}` gives it a soft tinted
background (other tints: `sand`, `rose`, `sage`, `lilac`), and for a
language that is set vertically (Japanese) `{tl vertical}` lays the
block out in columns from top to bottom, right to left, as tategaki
(`height=<em>` sets the column height, default 22). These may be
combined; omitted, the block renders plainly — which is the right
choice almost always. They exist for the rare case where the content
itself is a classical couplet, a haiku, or a quoted passage that a
reader would expect to see set apart; never add poetry or a quotation
in order to use them. Example — a couplet that genuinely belongs in
the essay:

```
[اگر آن ترک شیرازی به دست آرد دل ما را⏎
به خال هندویش بخشم سمرقند و بخارا را]{tl font=nastaliq bg=quote}
```

A specular form exists for a **Latin paragraph**: `[text]{la}` with
optional `align=right|center` (text alignment), `bg=…` (same tints),
and `width=`/`offset=` (percentages of the column) to narrow the block
and shift it sideways. Its content is ordinary markdown, and it is
recognised only when the whole paragraph is the block. The same
restraint applies: it is layout machinery for the rare epigraph or
set-apart passage, not something an answer needs.

**5. Glosses.** Give quick translations with an equals sign, spaces on
both sides, and set **the translation itself in italics**:
`آهسته برو = *go slowly*`. The `=` is styled automatically; the
italics are yours to write, and they are what tells the reader where
the translation stops.

So the asterisks must enclose the whole translation and nothing else.
Several near-synonyms rendering one word are all translation, and go
inside together: `آهستگی = *slowness, gentleness*`. Anything that is
commentary, context or a further remark is not translation, and stays
outside: `حرکت آهسته = *slow motion*, in film`, `زود باش = *hurry up*,
literally "be early"`. Italicise the translation only — never the
target-language text, never the `=`.

**6. Ungrammatical and correct forms.** Prefix an ungrammatical form
with `✗` and no space: `✗اینترنتِ تند`. It is rendered as a red ❌
followed by the form itself tinted red — the whole marked form, so the
reader sees at a glance what is wrong. This red is reserved: it is not
one of the marking colours of rule 13 and a colour mark cannot override
it. Do not use a raw `*` for this.

To flag the explicitly *correct* member of a contrast, put `✅` before
it, with a space: `✅ یواش برو`. Unlike `✗`, the `✅` is a stand-alone
green check and does **not** colour or otherwise affect the text that
follows it. Use the pair in minimal contrasts:
`✅ یواش برو / ✗یواشِ برو`.

**7. Tables.** Use pipe tables with a header row. Use `—` for an empty
cell. Keep cell text short; the target language in cells is fine.
Never put a `|` inside a cell.

**8. Display lines.** A paragraph consisting **only** of the target
language (a proverb, an example sentence) is rendered as a large
stand-alone line — use this for showcased material, with any
translation in the paragraph before or after it.

**9. Highlight boxes.** Use a `>` blockquote for the one or two
passages that deserve a tinted box (a key caveat, a rule of thumb). A
bullet list inside the quote is allowed.

**10. Inline styling.** `**bold**` and `*italic*` on Latin text only;
`**bold**` around a lone word of the target language makes it bold.
Arrows: write `→`. Guillemets «…» and em dashes pass through as-is.

**11. Footnotes.** Use them for anything that would break the flow of the
main argument: a caveat, a dialectal or diachronic aside, a
disagreement between sources, the reason behind a claim. Two forms:

```
Persian آهسته covers two distinct areas[^areas].

[^areas]: Low speed and low volume; cf. یواش, which shares both.
```

and, for something short, an inline note: `... thus ^[a brief note here]`.
Reference labels can be any word (`[^aree]`, `[^1]`); the definition may
sit anywhere in the file, and continuation lines must be indented. Notes
are numbered automatically in the order they appear. They may contain
the target language, glosses, links and colour marks, but **not** other
footnotes.

*Effect:* in the PDF the note appears at the bottom of the page; in the
web reader the number is hoverable and the text appears in a floating
cloud (and again in a list at the end). Use footnotes generously — this
is the natural place for the depth that would otherwise clutter an
entry.

**12. Links.** `[visible text](https://example.org/page)` — the URL
is hidden behind the text and is clickable in both the PDF and the web
page. Only `http://`, `https://` and `mailto:` are accepted. The visible
text may be in the target language: `[فرهنگ](https://www.vajehyab.com/)`.
Link dictionaries, grammars, corpora or sources whenever they support a
claim; do not link the same source twice in a row.

**13. Colour marks.** You *may* tint a word or phrase of the target
language — five named colours (`crimson`, `indigo`, `teal`, `violet`,
`amber`) or any hex value:

```
[آهسته]{crimson} and [تند]{#2F6B8F} occupy opposite poles.
```

*Effect:* the word is printed in that colour in the PDF and on the web.
**Most documents need no colour at all** — the default is plain text,
and an answer with zero colour marks is in no way incomplete. Reach for
colour only when one specific contrast genuinely becomes clearer with
it (say, the two poles of a single opposition, marked at the two or
three places where they are compared), use as few colours as the idea
needs — usually one or two, never all of them for completeness' sake —
and stop there. Do not colour more than a handful of words per page,
never colour a whole sentence, and **never explain the colours in the
text**: no legend, no "colours in this document mark…" paragraph — the
prose must read perfectly with the colours ignored. The reader can also
add or change these marks by hovering a word in the web page; the
choice is written back into this markdown, so if you are asked to
revise a document that already contains `{colour}`, `{translit:…}` or
`{kana:…}` marks, **preserve them** — they carry the reader's own
annotation.

**14. Do not use:** images, recordings or embedded videos (PNG, JPEG,
SVG or PDF pictures, MP3, M4A, Ogg, WAV and the other audio files — all
of them added by the reader), and never write a `[…](doc:…)` link —
these are put in by hand, in the studio. A `doc:` link names another
document of the reader's library by its exact title, which only the
studio knows, and a picture or a recording names a file only the studio
has, so one you invent points nowhere. If the file you were given to
revise already contains `![…](images/…)`, `![…](audio/…)`, `@[…](…)` or
`[…](doc:…)`, keep them exactly where they are, attributes and names
included — the name after `doc:` character for character, even when you
would spell or translate it otherwise. Also avoid HTML, math, nested
blockquotes, headings inside quotes, numbered lists with sub-items,
footnotes inside footnotes, and fenced code blocks anywhere in the file.

**15. Content expectations.** Be exhaustive but do not invent information.
Above all do not create words out of usual rules of the language that are in
practice never or almost never used.

The conventions of the target language follow, then the question.
