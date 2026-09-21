# Persian — the annotation conventions

How a Persian sentence becomes a glossed line: what goes into each field
and how it is written. These rules bind both the reading editions and the
video captions; they are embedded into every prompt that asks for Persian
annotation, so they are written as instructions to the annotator.

Two of the field names are languages, and neither is a claim about one:
`fa` is the text in the target language — Persian here, which is the
language the key was named after when Persian was the only one — and `en`
is the gloss beside it. They are the same two keys in every book and every
video. Which language the gloss is written in is the book's or the video's
own choice, `"gloss"` in `book.json` / `video.json`, and English when the
key is absent. This file is about Persian as the language being **taught**:
the examples below gloss into English because they must gloss into
something, and every rule that turns on the gloss language says so.

## The text field

`fa` reproduces the source **verbatim**: same spelling, same punctuation,
same ZWNJs, the source's own oddities included (a compound written with a
space, a 1921 printing's `ة` for the ezafe after `ه`, an ASR slip in a
caption). Chunks split only at spaces; joined back with single spaces they
must reproduce the sentence exactly, and a machine checks that. **Never
correct the text in `fa`** — the correction goes in `note` (videos) or in
the vocabulary line (books).

In a reading edition `fa` carries the **harakat**, and the vowel marks exist
to agree with the romanisation printed beside them — if a mark and the
romanisation disagree, the mark is what misleads. In a video caption `fa`
carries no marks at all: the caption is copied as YouTube has it.

| sound | written | note |
|---|---|---|
| a | fatha َ | |
| e | kasra ِ | |
| o | damma ُ | |
| **/ey/** | **kasra + ya** | `پِیدا` *peydā*, `خِیلی` *xeyli*, `بِینِ` *beyn-e* |
| **/ow/** | **fatha + vav** | `جِلَوِ` *jelow*, `رَوزَنِه` *rowzane*, `تَولید` *towlid* |
| long ā/i/u | unmarked | ا و ی carry themselves |
| sukun | **never** | not used |

`/ey/` is kasra: a fatha there tells the reader to say *paydā* where the
page prints *peydā*. `/ow/` stays fatha + vav. Every short vowel must be
marked — an unmarked consonant is a claim that no vowel is there. **A mark
on a letter carrying a long vowel is an error, not extra precision.**

Other settled points:

- final ه pronounced *-e* takes its kasra on the **preceding** consonant:
  `خانِه`, `آهِستِه`;
- conjunction و: `وَ` when read *va*, `وُ` when read *o*;
- `چشم` is **`چِشم` / *češm*** — Tehrani /tʃeʃm/;
- `بودن`'s present stem is **`باش`**; `هست` is the suppletive existential;
- one spelling can be two words (`دورِ` *dowr-e* "around" / *dur-e*
  "distant"): refuse any form printed with two different romanisations, but
  never "harmonise" two words into one.

**The ezafe** is marked as a kasra on the **governing** word, every time:
`مِثلِ خورِه`. After a final ه keep the hamza (or the ة) the text already
has. Where it is the glide *-ye*, the kasra goes on the ی: `دارویِ آن`,
`هیچ جایِ دُنیا`. The ezafe that is easiest to lose is the one whose
qualifier falls into the **next** chunk: the chunk looks complete, and the
kasra is dropped. Read across every seam.

## Reading

This language has no reading field.

## Transliteration

`tr` is the transliteration of what is actually said or printed: colloquial
forms as heard (`mi-kone`, not `mi-konad`, when that is what is spoken;
`umad`, not *āmad*, when the page prints `اومد`).

Scheme: long **ā**, short a e o; **š** = ش, **č** = چ, **ž** = ژ, **x** = خ,
**q** = both ق and غ, **'** = both ع and ء; emphatics flattened
(س ص ث → s, ز ذ ض ظ → z, ت ط → t, ه ح → h). Hyphenate transparent
morphology: `mi-`, `nemi-`, `be-`, `na-`, ezafe `-e`/`-ye`, plural
`-hā`/colloquial `-ā`, indefinite `-i`, clitic pronouns `-am -et -eš -emun
-etun -ešun`, object clitic `-o` (رو `ro` when a separate word). A ZWNJ
inside a word becomes a hyphen (`می‌کنه` → `mi-kone`).

The scheme does not follow the gloss language: `š` is `š` and `x` is `x` in
a book glossed in Italian or in French as much as in one glossed in
English. It transliterates the Persian rather than respelling it in
somebody's orthography, and every edition of this series must be readable
by a reader who has learnt it once.

## Vocabulary

`voc` is written in the voice of the books' gloss blocks: headword +
transliteration + meaning. Name what was stripped from the form in the text:
indefinite *-i*, plural *-hā*/*-ān*, enclitics *-am -at -aš …*, the ezafe,
comparative *-tar*, Arabic broken plurals (give singular **and** plural).
No etymologies of headwords, one equivalent in the gloss language rather
than a string of synonyms, and **an empty `voc` is the right answer** for a
chunk needing nothing.

In a **video** the line is plain text: verbs as
`دیدن didan · pres. بین bin · past دید did · to see`, and a form of the verb
in the chunk first, with the entry in brackets after it — `ببخشید bebaxšid
excuse me (بخشیدن baxšidan · pres. بخش baxš · past بخشید baxšid · to
forgive)`; compounds as `فکر کردن fekr kardan to think`; colloquial ↔
written pairs spelled out (`میاد mi-yād = می‌آید mi-āyad`); loanwords flagged
with the language they came **from**, which has nothing to do with the
language the gloss is written in (`تکست tekst — Eng. "text"`, `مرسی mersi —
Fr. "merci"`). Persian script inside `voc` is fine — the player isolates it.
A video is spoken Tehrani, and the commonest verbs contract their present
beyond recognition (گو → *mi-gam*, رو → *mi-ram*, شو → *mi-šam*, دان →
*mi-dunam*): where the speaker says one and the chunk does not already show
it, the entry takes the colloquial first person present as its extra, **in
videos only** — `گفتن goftan · pres. گو gu · past گفت goft · to say (coll.
می‌گم mi-gam)`. A book keeps to the written stems and never carries it.

In a **book** the line uses four macros and nothing else: `\dw{fa}{rom}
gloss` · `\vb{inf}{rom}{pres}{rom}{past}{rom}{meaning}` ·
`\bw{base}{rom}{meaning}` · `\pw{fa}` — plus `\textit`, `\emph`,
`\nobreak`. **Every** verb gets a `\vb`, no exceptions: the infinitive, the
present stem — the one nobody can guess — and the past stem, each with its
romanisation. A compound verb (کردن/شدن/داشتن/بردن/زدن…) is a `\vb` for the
light verb with an **empty 7th argument**, then a `\bw` for the word it
carries; never gloss the light verb's own meaning.

What the three forms cannot say goes in **one parenthesis after the
meaning**, items parted by `; `, and in Persian that is a closed list:

- **داشتن**, whose present takes no *mi-* (`دارم`, never `می‌دارم`):
  `\vb{داشتن}{dāštan}{دار}{dār}{داشت}{dāšt}{to have (pres. without mi-)}`.
  No other verb carries it; بودن keeps `باش` as its stem and `هست` its own
  `\dw`, as above.
- the colloquial present, in a video only (above).

A verb with a **preverb** (برگشتن, درآوردن, فراگرفتن) is hyphenated after
the preverb in all three romanisations, because *mi-*, *be-* and *na-* go in
there (*bar-mi-gardam*, *bar-gard*):
`\vb{برگشتن}{bar-gaštan}{برگرد}{bar-gard}{برگشت}{bar-gašt}{to return}`.
A stem this book has already given is given the same way again — the same
spelling, the same romanisation — whatever a dictionary offers.

The gloss editor's sources sidebar, in the reader and in the player, now
proposes this entry from the dictionary for a verb it recognises — the
infinitive and the two stems with their sounds — ready to put into the line
with one click; in a book that already has a `\vb` for the same infinitive
it offers the book's own first. It is a **draft for you to correct**, not an
answer: its stems are Wiktionary's, from the literary Iranian table where
there is one, and need not be this book's (it has *dah* for دادن where this
series writes *deh*), so check them against this file; trim the meaning to
the one sense the text uses;
and fill what it could not — the button names what is missing. For a
compound the dictionary knows (فکر کردن, عوض کردن — not every one it
should), the draft is the light verb's `\vb` with the meaning already empty,
and a **button of its own** puts the whole compound in — headed *compound
verb*, and saying in so many words that لبخند زدن is one verb written in
two words and not two entries. What it writes is the entry this file asks
for and nothing else:

```
\vb{زدن}{zadan}{زن}{zan}{زد}{zad}{}\bw{لبخند}{labxand}{to smile}
```

— the `\bw` run straight onto the `\vb`, with no `; ` between them, which is
what makes the pair one entry in the line. In a **video**, where there is no
macro to say which word belongs to which, it writes the compound whole and
glossed whole, as this file's video section asks (`compounds as فکر کردن
fekr kardan to think`), with the verb that does the conjugating after it:
`لبخند زدن labxand zadan to smile (زدن zadan · pres. زن zan · past زد zad)`.
The plain `\vb` button is untouched beside it — the light verb alone, still
drawn unfinished — and the row goes on naming the `\bw` under *to fill in*,
so you see what the entry is about to become before pressing. Where the
dictionary gave no meaning the compound still goes in, with that slot empty
and the button dashed; where it does not know the compound at all (گمان
کردن, معلوم شدن), the light verb comes with its own meaning, and emptying it
is yours. It hyphenates a preverb only where the dictionary
marks one (برگشتن, برداشتن, درآوردن, فراگرفتن and a few more): برخاستن comes
as *barxāstan*, and the hyphen is yours to put in. A preverb verb the text
writes apart (`بر می‌گردم`, `در آورده`) is offered whole, as برگشتن and
درآوردن. In a video it adds the colloquial present wherever the dictionary's
colloquial Tehrani table spells it differently (18 verbs, the four above
among them); take it out where the speaker does not say it.

The meaning is what the gloss language is for; the labels around it are
not. *pres.* and *past* are printed by the edition itself — the same two
words in every Persian book, out of the registry — so leave them, and the
`pl.`, `pres. without mi-`, `coll.` and the rest, as they are written here
whatever the glosses are in: a line that translated the labels and not the
forms would be reading in two conventions at once. Where the gloss language
is Persian, the meaning is a **definition** and not a translation — commoner
words than the headword, and never the headword's own relatives.
`docs/lang/en.md` sets that case out in full; it belongs to no one language.

Which words the reader already owns turns on the gloss language as well,
and Persian's case is the strongest in the toolbox: a book glossed in
Arabic or in Turkish is read by somebody who has met a great part of the
vocabulary already (کتاب، انسان، زمان، حیات), and what those words need
from the line is not a meaning but the shift — کثیف is *dirty* in Persian
and dense in Arabic, زحمت is *trouble* and not a crowd, حوصله is
*patience* and not a bird's crop. To a reader of English or Italian the
same words are simply new, and take the ordinary entry.

The repetition rule is Frank's own: a full entry the **first time** a word
appears, briefer or none on later appearances.

## Never gloss

These ~45 function words, already in dictionary form, never get a
vocabulary entry:

```
در از با به که این آن و را تا هم یا ولی اما اگر نه هر یک من تو او ما شما
آنها خود چون زیرا پس چه خیلی فقط باز هنوز هیچ همه بی بر روی زیر جلو مثل
وقتی حالا دیگر بعد قبل
```

## Chunking

A chunk is a sense group of roughly **2–6 words** — a verb with its object,
a noun with its ezafe, a preposition with its noun: something a reader
hovers and that *means* something on its own. Never split a compound verb
(`فکر کردن`), an ezafe pair (`کوه قاف`), or a verb from its negation. A very
short sentence (`۲`, `شاه`, `می‌بینید`) is one chunk; that is normal and
not a fault.
