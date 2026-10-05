# Persian — the annotation conventions

{{?new}}How a Persian sentence becomes a glossed line: what goes into each field
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
something, and every rule that turns on the gloss language says so.{{/new}}

## The text field

`fa` reproduces the source **verbatim**: same spelling, same punctuation,
same ZWNJs, the source's own oddities included (a compound written with a
space, a 1921 printing's `ة` for the ezafe after `ه`, an ASR slip in a
caption). Chunks split only at spaces; joined back with single spaces they
must reproduce the sentence exactly, and a machine checks that. **Never
correct the text in `fa`**{{?new}} — the correction goes in {{?video}}`note`{{/video}}{{?book}}the
vocabulary line{{/book}}{{/new}}.{{?nomarks}} It carries no short vowels of your making: the
text is copied as the source has it{{?video}}, a caption as YouTube has it{{/video}}.{{/nomarks}}{{?marks}} The short
vowels are asked for in this prompt: `fa` is then the source's text WITH the
harakat added and nothing else changed — by the rules under Reading.{{/marks}}

## Reading

This language has no reading field.

{{?marks}}What stands in its place is the short vowels, which `fa` itself carries when they are
asked for: the harakat exist to agree with the `tr` printed beside them — if a
mark and `tr` disagree, the mark is what misleads.{{?video}} A caption is then
YouTube's text with the marks added and nothing else changed: not a letter, not
a space, not a ZWNJ, not a stop.{{/video}}{{?book}} A reading edition's `fa`
carries them on every word.{{/book}}

{{?classic}}| sound | written | note |
|---|---|---|
| a | fatha َ | |
| e | kasra ِ | |
| o | damma ُ | |
| **/ey/** | **kasra + ya** | `پِیدا` *peydā*, `خِیلی` *xeyli*, `بِینِ` *beyn-e* |
| **/ow/** | **fatha + vav** | `جِلَوِ` *jelow*, `رَوزَنِه` *rowzane*, `تَولید` *towlid* |
| long ā/i/u | unmarked | ا و ی carry themselves |
| sukun | **never** | not used |

`/ey/` is kasra: a fatha there tells the reader to say *paydā* where the
page prints *peydā*.{{/classic}}{{?ipa}}| sound | written | note |
|---|---|---|
| æ | fatha َ | |
| e | kasra ِ | |
| o | damma ُ | |
| **ej** | **kasra + ya** | `پِیدا` *pejdɒː*, `خِیلی` *xejli*, `بِینِ` *bejn-e* |
| **ow** | **fatha + vav** | `جِلَوِ` *dʒelow*, `رَوزَنِه` *ɾowzæne*, `تَولید` *towlid* |
| long ɒː/i/u | unmarked | ا و ی carry themselves |
| sukun | **never** | not used |

`/ej/` is kasra: a fatha there tells the reader to say *pæjdɒː* where the
page prints *pejdɒː*.{{/ipa}} `/ow/` stays fatha + vav. Every short vowel must be
marked — an unmarked consonant is a claim that no vowel is there. **A mark
on a letter carrying a long vowel is an error, not extra precision.**

Other settled points:

- final ه pronounced *-e* takes its kasra on the **preceding** consonant:
  `خانِه`, `آهِستِه`;
- conjunction و: `وَ` when read {{?classic}}*va*{{/classic}}{{?ipa}}*væ*{{/ipa}}, `وُ` when read *o*;
- `چشم` is **`چِشم` / {{?classic}}*češm*{{/classic}}{{?ipa}}*tʃeʃm*{{/ipa}}**{{?classic}} — Tehrani /tʃeʃm/{{/classic}};
- `بودن`'s present stem is **`باش`**; `هست` is the suppletive existential;
- one spelling can be two words (`دورِ` {{?classic}}*dowr-e* "around" / *dur-e* "distant"{{/classic}}{{?ipa}}*dowɾ-e* "around" / *duɾ-e* "distant"{{/ipa}}):
  refuse any form printed with two different {{?classic}}romanisations{{/classic}}{{?ipa}}transcriptions{{/ipa}}, but
  never "harmonise" two words into one.

**The ezafe** is marked as a kasra on the **governing** word, every time:
`مِثلِ خورِه`. After a final ه keep the hamza (or the ة) the text already
has. Where it is the glide {{?classic}}*-ye*{{/classic}}{{?ipa}}*-je*{{/ipa}}, the kasra goes on the ی: `دارویِ آن`,
`هیچ جایِ دُنیا`. The ezafe that is easiest to lose is the one whose
qualifier falls into the **next** chunk: the chunk looks complete, and the
kasra is dropped. Read across every seam.{{/marks}}

## Transliteration

{{?classic}}`tr` is the transliteration of what is actually said or printed:
colloquial forms as heard (`mi-kone`, not `mi-konad`, when that is what is
spoken; `umad`, not *āmad*, when the page prints `اومد`).

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
by a reader who has learnt it once.{{/classic}}{{?ipa}}`tr` is the pronunciation of what is actually said or printed,
written in **IPA**: the broad (phonemic) IPA of standard Tehrani Persian, with
no slashes and no square brackets, and one scheme from the first chunk to the
last. Colloquial forms are written as heard (`mi-kone`, not *mi-konæd*, when
that is what is spoken; `umæd`, not *ɒːmæd*, when the page prints `اومد`).

Symbols: the vowels are **i e æ o u** and **ɒː** for ā (never ɑ, and never a
plain a); **tʃ** is چ, **dʒ** is ج, **ʃ** is ش, **ʒ** is ژ, **x** is خ, **ɢ** is
both ق and غ, **ʔ** is both ع and ء, **ɾ** is ر, **ɡ** is گ, **j** is ی as a
consonant; the rest are IPA's own (p b t d k f v s z h m n l). The emphatics
are flattened as Persian flattens them (one s for س ص ث, one z for ز ذ ض ظ, one
t for ت ط, one h for ه ح). Stress: write ˈ before the stressed syllable of a
word of two or more syllables where you are sure of it — the last syllable of a
noun, an adjective or an adverb; the prefix of a verb that has mi-, ne- or
be- — and leave it out where in doubt. The hyphens that part transparent
morphology stay, because they part the word and are no sounds:
`mi-`, `nemi-`, `be-`, `na-`, ezafe `-e`/`-je`, plural `-hɒː`/colloquial
`-ɒː`, indefinite `-i`, clitic pronouns `-æm -et -eʃ -emun -etun -eʃun`, object
clitic `-o` (رو `ɾo` when a separate word). A ZWNJ inside a word becomes a hyphen
(`می‌کنه` → `mi-kone`).

IPA does not follow the gloss language: it is the same in a book glossed in
Italian or in French as in one glossed in English, and every edition of this
series must be readable by a reader who has learnt it once.{{/ipa}}

## Vocabulary

{{?classic}}`voc` is written in the voice of the books' gloss blocks: headword +
transliteration + meaning. Name what was stripped from the form in the text:
indefinite *-i*, plural *-hā*/*-ān*, enclitics *-am -at -aš …*, the ezafe,
comparative *-tar*, the attached copula (including spoken *-e*, *-in*, *-an*),
Arabic broken plurals (give singular **and** plural).
No etymologies of headwords, one equivalent in the gloss language rather
than a string of synonyms, and **an empty `voc` is the right answer** for a
chunk needing nothing.{{/classic}}{{?ipa}}`voc` is written in the voice of the books' gloss blocks: headword +
IPA + meaning. Name what was stripped from the form in the text: indefinite
*-i*, plural *-hɒː*/*-ɒn*, enclitics *-æm -æt -æʃ …*, the ezafe, comparative *-tæɾ*,
the attached copula (including spoken *-e*, *-in*, *-ɒn*), Arabic broken plurals
(give singular **and** plural). No etymologies of headwords, one equivalent in
the gloss language rather than a string of synonyms, and **an empty `voc` is
the right answer** for a chunk needing nothing.{{/ipa}}

The line uses four macros and nothing else: `\dw{fa}{rom} gloss` ·
`\vb{inf}{rom}{pres}{rom}{past}{rom}{meaning}` · `\bw{base}{rom}{meaning}` ·
`\pw{fa}` — plus `\textit`, `\emph`, `\nobreak` — and its entries are parted
by `; `. **Every** verb gets a `\vb`, no exceptions: the infinitive, the
present stem — the one nobody can guess — and the past stem, each with its
{{?classic}}romanisation{{/classic}}{{?ipa}}IPA{{/ipa}}. A compound verb (کردن/شدن/داشتن/بردن/زدن…) is a `\vb` for the
light verb with an **empty 7th argument**, then a `\bw` for the word it
carries; never gloss the light verb's own meaning:
{{?classic}}`\vb{زدن}{zadan}{زن}{zan}{زد}{zad}{}\bw{لبخند}{labxand}{to smile}`{{/classic}}{{?ipa}}`\vb{زدن}{zædæn}{زن}{zæn}{زد}{zæd}{}\bw{لبخند}{læbxænd}{to smile}`{{/ipa}},
the `\bw` run straight onto the `\vb` with no `; ` between them, which is what
makes the pair one entry in the line.

{{?video}}What a video adds is the form its chunk has, where it is none of the
three the `\vb` prints, nor one its parenthesis names: it is named after the
entry, outside it, with its sound,
{{?classic}}`\vb{بخشیدن}{baxšidan}{بخش}{baxš}{بخشید}{baxšid}{to forgive}; here \pw{ببخشید}
\textit{bebaxšid}, imperative`{{/classic}}{{?ipa}}`\vb{بخشیدن}{bæxʃidæn}{بخش}{bæxʃ}{بخشید}{bæxʃid}{to forgive}; here \pw{ببخشید}
\textit{bebæxʃid}, imperative`{{/ipa}}. Colloquial ↔ written pairs are spelled out
({{?classic}}`\dw{خونه}{xune} = \pw{خانه} \textit{xāne} house`, and after a `\vb`
`; here \pw{میاد} \textit{mi-yād} = \pw{می‌آید} \textit{mi-āyad}`{{/classic}}{{?ipa}}`\dw{خونه}{xune} = \pw{خانه} \textit{xɒːne} house`, and after a `\vb`
`; here \pw{میاد} \textit{mi-jɒːd} = \pw{می‌آید} \textit{mi-ɒːjæd}`{{/ipa}}).
{{/video}}Loanwords are flagged with the language they came **from**, which has
nothing to do with the language the gloss is written in
({{?classic}}`\dw{تکست}{tekst} — Eng. "text"`, `\dw{مرسی}{mersi} — Fr. "merci"`{{/classic}}{{?ipa}}`\dw{تکست}{tekst} — Eng. "text"`, `\dw{مرسی}{meɾsi} — Fr. "merci"`{{/ipa}}).
{{?video}}A video is spoken Tehrani, and the commonest verbs contract their
present beyond recognition ({{?classic}}گو → *mi-gam*, رو → *mi-ram*, شو → *mi-šam*,
دان → *mi-dunam*{{/classic}}{{?ipa}}گو → *mi-ɡæm*, رو → *mi-ɾæm*, شو → *mi-ʃæm*,
دان → *mi-dunæm*{{/ipa}}): where the speaker says one and the chunk does not already
show it, the entry takes the colloquial first person present as its extra, **in
videos only**, in the parenthesis after the meaning —
{{?classic}}`\vb{گفتن}{goftan}{گو}{gu}{گفت}{goft}{to say (coll. \pw{می‌گم} \textit{mi-gam})}`{{/classic}}{{?ipa}}`\vb{گفتن}{ɡoftæn}{گو}{ɡu}{گفت}{ɡoft}{to say (coll. \pw{می‌گم} \textit{mi-ɡæm})}`{{/ipa}};
a compound's light verb has no meaning, so there the parenthesis stands alone —
{{?classic}}`\vb{شدن}{šodan}{شو}{šav}{شد}{šod}{(coll. \pw{می‌شم} \textit{mi-šam})}\bw{معلوم}{ma'lum}{evident}`{{/classic}}{{?ipa}}`\vb{شدن}{ʃodæn}{شو}{ʃæv}{شد}{ʃod}{(coll. \pw{می‌شم} \textit{mi-ʃæm})}\bw{معلوم}{mæʔlum}{evident}`{{/ipa}}.

{{/video}}What the three forms cannot say goes in **one parenthesis after the
meaning**, items parted by `; `, and in Persian that is a closed list:

- **داشتن**, whose present takes no *mi-* (`دارم`, never `می‌دارم`):
  {{?classic}}`\vb{داشتن}{dāštan}{دار}{dār}{داشت}{dāšt}{to have (pres. without mi-)}`{{/classic}}{{?ipa}}`\vb{داشتن}{dɒːʃtæn}{دار}{dɒːɾ}{داشت}{dɒːʃt}{to have (pres. without mi-)}`{{/ipa}}.
  No other verb carries it; بودن keeps `باش` as its stem and `هست` its own
  `\dw`, as above.
- the colloquial present, in a video only{{?video}} (above){{/video}}{{?book}}:
  a book keeps to the written stems and never carries it{{/book}}.

A verb with a **preverb** (برگشتن, درآوردن, فراگرفتن) is hyphenated after
the preverb in all three {{?classic}}romanisations{{/classic}}{{?ipa}}transcriptions{{/ipa}}, because *mi-*, *be-* and *na-* go in
there ({{?classic}}*bar-mi-gardam*, *bar-gard*{{/classic}}{{?ipa}}*bæɾ-mi-ɡæɾdæm*, *bæɾ-ɡæɾd*{{/ipa}}):
{{?classic}}`\vb{برگشتن}{bar-gaštan}{برگرد}{bar-gard}{برگشت}{bar-gašt}{to return}`{{/classic}}{{?ipa}}`\vb{برگشتن}{bæɾ-ɡæʃtæn}{برگرد}{bæɾ-ɡæɾd}{برگشت}{bæɾ-ɡæʃt}{to return}`{{/ipa}}.
A stem already given is given the same way again — the same
spelling, the same {{?classic}}romanisation{{/classic}}{{?ipa}}transcription{{/ipa}} — whatever a dictionary offers.

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

## Example

Three chunks of one caption, as an answer writes them: the same shape in every
prompt. The meanings here are written in English because an example has to be
written in something; yours are written in the gloss language of this prompt.

{{?classic}}```json
{"chunks": [
  {"fa": "{{?marks}}چِشم،{{/marks}}{{?nomarks}}چشم،{{/nomarks}}", "tr": "češm", "voc": "\\dw{چشم}{češm} certainly, at once (lit. eye)", "en": "certainly,"},
  {"fa": "{{?marks}}چیز دیگَری{{/marks}}{{?nomarks}}چیز دیگری{{/nomarks}}", "tr": "čiz digar-i", "en": "anything else"},
  {"fa": "{{?marks}}نِمی‌خواهید{{/marks}}{{?nomarks}}نمی‌خواهید{{/nomarks}}", "tr": "nemi-xāhid", "voc": "\\vb{خواستن}{xāstan}{خواه}{xāh}{خواست}{xāst}{to want}", "en": "you do not want"}
]}
```{{/classic}}{{?ipa}}```json
{"chunks": [
  {"fa": "{{?marks}}چِشم،{{/marks}}{{?nomarks}}چشم،{{/nomarks}}", "tr": "tʃeʃm", "voc": "\\dw{چشم}{tʃeʃm} certainly, at once (lit. eye)", "en": "certainly,"},
  {"fa": "{{?marks}}چیز دیگَری{{/marks}}{{?nomarks}}چیز دیگری{{/nomarks}}", "tr": "tʃiz diɡæɾ-i", "en": "anything else"},
  {"fa": "{{?marks}}نِمی‌خواهید{{/marks}}{{?nomarks}}نمی‌خواهید{{/nomarks}}", "tr": "nemi-xɒːhid", "voc": "\\vb{خواستن}{xɒːstæn}{خواه}{xɒːh}{خواست}{xɒːst}{to want}", "en": "you do not want"}
]}
```{{/ipa}}

What to notice: the negative verb is a chunk of its own and its `en` says only
the negation and the person, while `voc` gives the verb whole; the idiom `چشم`
is glossed as the idiom (*certainly*) and not as the word *eye*; `چیز دیگری`
needs nothing (a common word, and دیگر is never glossed), so it has no `voc`; the
hyphens in `tr` part the morphemes (`nemi-`, the indefinite `-i`).
