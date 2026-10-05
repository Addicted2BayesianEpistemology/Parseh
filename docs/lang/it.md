# Italian — the annotation conventions

{{?new}}How an Italian sentence becomes a glossed line: what goes into each field
and how it is written. These rules bind both the reading editions and the
video captions; they are embedded into every prompt that asks for Italian
annotation, so they are written as instructions to the annotator.

Two of the field names are languages, and neither is a claim about one:
`fa` is the text in the target language — Italian here — and `en` is the
gloss beside it. They are the names Persian and English left behind from
the days when they were the only two languages the toolbox had, and they
are the same two keys in every book and every video. Which language the
gloss is written in is the book's or the video's own choice, `"gloss"` in
`book.json` / `video.json`, and English when the key is absent. This file
is about Italian as the language being **taught**: the examples below gloss
into English because they must gloss into something, and every rule that
turns on the gloss language says so.{{/new}}

## The text field

`fa` reproduces the source **verbatim**: same spelling, same accents, same
apostrophes and elisions (`l'uomo`, `un'ora`, `po'`), same punctuation, the
source's own oddities included — a regional form, an old spelling, an ASR
slip in a caption. Chunks split only at spaces; joined back with single
spaces they must reproduce the sentence exactly, and a machine checks
that. **Never correct the text in `fa`**{{?new}} — the correction goes in
{{?video}}`note`{{/video}}{{?book}}the vocabulary line{{/book}}{{/new}}.

Italian is plain text: there are no marks to add and none to strip. The
written accents are part of the spelling (`è`, `perché`, `città`) and stay
exactly as the source has them; do not add a stress accent to a word the
source writes without one — stress, when it helps, is shown in `tr` and
nowhere else.{{?book}} There is one pass with help and one with the chunks; there is
no "bare" pass, because the text is already bare.{{/book}}

{{?studio}}Italian has no character range of its own in the registry and could not be
given one: it is written in the alphabet the toolbox's own prose is written
in. So nothing detects a run of Italian — and where the glosses are in
another Latin-script language, English or French or Turkish, nothing tells
the two apart by eye either. Wherever the format asks you to mark the
target text (a studio document's `[…]{tl}` mark), mark every Italian run;
in a book chunk or a video chunk `fa` is Italian by definition and needs no
mark.{{/studio}}

## Reading

This language has no reading field.

## Transliteration

{{?classic}}`tr` is an **IPA-lite pronunciation aid, only where it helps**, and it may
be omitted — most chunks need none. Use it for what the spelling does not
show:

- the **open and closed e and o**: `è` for /ɛ/ and `é` for /e/, `ò` for
  /ɔ/ and `ó` for /o/ (`pèsca` peach, `pésca` fishing; `bótte` barrel,
  `bòtte` blows);
- the **stress**, when it falls anywhere but the penultimate syllable or is
  ambiguous, marked on the stressed vowel as the dictionary marks it — a
  grave on `à`, `ì`, `ù` and on an open `è`, `ò`, an acute on a closed `é`,
  `ó` (`àncora` anchor, `ancóra` still; `tàvolo`, `telèfono`, `capìscono`);
- the voiced and voiceless **s** and **z** where they matter (`s` = /s/,
  `ṡ` = /z/; `z` = /ts/, `ż` = /dz/): `caṡa`, `ròṡa`, `żèro`, `pizza`;
- the sounds a reader coming from any other language misreads: `gli` as `ʎ`
  (`famiʎʎa`), `gn` as `ɲ` (`gnòcchi` → `ɲòkki`), `sc` before e/i as `ʃ`
  (`pésce` → `péʃʃe`), doubled consonants written double — and `gli` and
  `sc` are always long between vowels, so they are written double too. Only
  `gn` is spelt the same elsewhere (a French reader has it already); `gli`
  and `sc` are Italian's alone, so these stay whatever the glosses are
  written in.

Write the whole chunk in `tr` when you give one, not a single word out of
it. Never write `tr` for a word whose pronunciation is regular and
unambiguous.{{/classic}}{{?ipa}}`tr` is written in **IPA**: broad (phonemic), for standard
Italian, with no slashes and no square brackets round it. It is **only where
it helps**, and it may be omitted — most chunks need none, because the spelling
nearly says the sound. Give one for what the spelling does not show:

- the **stress**, when it falls anywhere but the penultimate syllable or is
  ambiguous, with `ˈ` before the stressed syllable (`ˈankora` anchor, `anˈkora`
  still; `ˈtavolo`, `teˈlɛfono`, `kaˈpiskono`);
- the **open and closed e and o**, which the spelling never shows: `ɛ` and
  `e`, `ɔ` and `o` (`ˈpɛska` peach, `ˈpeska` fishing; `ˈbotte` barrel, `ˈbɔtte`
  blows);
- the voiced and voiceless **s** and **z**: `s` is /s/ and `z` /z/ (`ˈkaza`,
  `ˈrɔza`), and the affricates are `ts` and `dz` (`ˈpittsa`, `ˈdzɛro`), with
  `tʃ` and `dʒ` for *c* and *g* before e or i (`ˈtʃena`, `ˈdʒiro`);
- the sounds a reader coming from any other language misreads: `ʎ` for *gli*,
  `ɲ` for *gn*, `ʃ` for *sc* before e or i (`faˈmiʎʎa`, `ˈɲɔkki`, `ˈpeʃʃe`).
  Doubled consonants are written double (`ˈfatto`), and the three above are
  always long between vowels, so they are written double too.

Write the whole chunk in `tr` when you give one, not a single word out of
it. Never write `tr` for a word whose pronunciation is regular and
unambiguous.{{/ipa}}

## Vocabulary

`voc` is written in the voice of the books' gloss blocks: headword +
meaning, with the grammar a learner needs to recognise the form.

- A **verb** is given as the infinitive, the first person present and the
  past participle, and its auxiliary when that is *essere*, as a `\vb` prints
  it: `andare · pres. vado · p.p. andato · to go (aux. essere)`. No
  conjugation class: the infinitive's own ending and the first person
  (`finisco`, `dormo`) already say it. Whatever form the text has, the entry
  is the verb's, under its infinitive: `vado`, `fatto` and `andrò` all get the
  `\vb` of `andare`.
- A **noun** carries its **gender** and, when it is not regular, its
  plural: `\dw{mano}{} hand, f., pl. \pw{le mani}`; `\dw{problema}{} problem,
  m., pl. \pw{i problemi}`; `\dw{uovo}{} egg, m., pl. \pw{le uova}`.
- An **adjective** is given in the masculine singular; a form that changes
  (`bello / bel / bell'`, `buono / buon`) is named.
- A **clitic** combination is spelled out the first time (`\dw{glielo}{} gli +
  lo`); a **preposition + article** contraction is named (`\dw{nel}{} in +
  il`).
- Name what was stripped: the plural, the feminine, the diminutive
  (`-ino`, `-etto`), the superlative (`-issimo`), the adverb ending
  (`-mente`).
- The line uses the four macros `\dw` `\vb` `\bw` `\pw` (plus `\textit`,
  `\emph`, `\nobreak`), as the Persian editions do, and its entries are
  parted by `; `: `\vb` for every verb, `\dw` for every other headword. The
  seven slots of `\vb` are, in this order,
  **infinitive, first person present, past participle**, each with its
  pronunciation, then the meaning; the edition prints *pres.* and *p.p.*
  before the second and third forms, so never put another form into those
  slots. {{?classic}}A form's pronunciation is its **stress, and only where it is not on
  the next-to-last syllable** — the form with the stressed vowel marked
  (`prèndere`, `àbito`, `telèfono`, `andàrsene`), empty for `parlare`,
  `vedere`, `prendo`: an open or closed `e` or `o` is left to the chunk's
  own `tr`.{{/classic}}{{?ipa}}A form's pronunciation is given **only where the stress is
  not on the next-to-last syllable** — the form in IPA, with `ˈ` before the
  stressed syllable (`ˈprɛndere`, `ˈabito`, `teˈlɛfono`, `anˈdarsene`), empty
  for `parlare`, `vedere`, `prendo`: an open or closed `e` or `o` is left to
  the chunk's own `tr`.{{/ipa}} A pronominal verb is the infinitive with its clitic and the
  present with its own (`alzarsi`, `mi alzo`; `andarsene`, `me ne vado`),
  and the participle bare (`alzato`, `andato`). A verb used only in the
  third person (`accadere`, `nevicare`) has no first person to give, and is
  given by its third, as the dictionary gives it:
  `\vb{accadere}{}{accade}{}{accaduto}{}{to happen (aux. \pw{essere}; p.r.
  \pw{accadde})}`.
- What those three cannot say goes in **one parenthesis after the meaning**,
  items parted by `; `, each only where it is not the ordinary case — and
  written exactly so:
  - `aux. \pw{essere}` where the perfect is made with *essere* (every
    pronominal verb, `andare`, `venire`, `piacere`, `essere` itself), and
    `aux. \pw{avere}/\pw{essere}` where it takes both (`finire`, `correre`,
    `cominciare`). *avere* alone is the default and is **never** printed.
  - `p.r. \pw{venni}`: the first person of the passato remoto, **only where
    it is irregular** — `venni`, `feci`, `dissi`, `presi`, `vidi`, `ebbi`,
    `fui`. It is the past a story is told in, and these cannot be walked back
    to their infinitives. Regular is `-ai` for an -are verb, `-ei` or `-etti`
    for an -ere verb (`credei`, `dovetti`), `-ii` for an -ire verb; a
    pronominal verb's keeps its pronoun, as the present does (`p.r.
    \pw{mi accorsi}`).

  `\vb{andare}{}{vado}{}{andato}{}{to go (aux. \pw{essere})}`,
  {{?classic}}`\vb{prendere}{prèndere}{prendo}{}{preso}{}{to take (p.r. \pw{presi})}`{{/classic}}{{?ipa}}`\vb{prendere}{ˈprɛndere}{prendo}{}{preso}{}{to take (p.r. \pw{presi})}`{{/ipa}},
  `\vb{venire}{}{vengo}{}{venuto}{}{to come (aux. \pw{essere}; p.r.
  \pw{venni})}`, `\vb{parlare}{}{parlo}{}{parlato}{}{to speak}` — the last
  with nothing in brackets, because nothing about it is out of the ordinary.
- A form in the text that is none of the three the `\vb` prints, nor one its
  parenthesis names — a tense or a person the entry does not show — is named
  after the entry, outside it, with what it is:
  `\vb{andare}{}{vado}{}{andato}{}{to go (aux. \pw{essere})}; here \pw{andrò}, fut.`,
  `\vb{parlare}{}{parlo}{}{parlato}{}{to speak}; here \pw{parlavo}, 1sg imperfect`.

One equivalent in the gloss language rather than a string of synonyms; no
etymologies; **an empty `voc` is the right answer** for a chunk needing
nothing. The repetition rule is Frank's own: a full entry the **first
time** a word appears, briefer or none on later appearances.

The meaning is what the gloss language is for; the labels around it are
not. *pres.* and *p.p.* are printed by the edition itself — the same two
words in every Italian book, out of the registry — so leave them, and
`aux.`, `p.r.`, the `f.` and the `pl.`, as they are written above whatever
the glosses are in: a line that translated the labels and not the
forms would be reading in two conventions at once. Where the gloss language
is Italian, the meaning is a **definition** and not a translation:
commoner words than the headword, and never the headword's own relatives.
`docs/lang/en.md` sets that case out in full; it belongs to no one
language.

Which words the reader already owns turns on the gloss language, and the
judgement is yours: a word transparent from the reader's own language earns
a shorter entry or none. `importante`, `nazione` and `possibile` say
themselves to a reader of English, French or Spanish and need no meaning,
only what the form is doing; to a reader of Persian, Turkish or Japanese
they say nothing at all.
Judge from the gloss language, never from English — and beware the ones
that only look transparent (`morbido` is soft, not morbid; `parenti` are
relatives, not parents; `libreria` is a bookshop), which are worth a full
entry precisely because the reader will not stop for them.

## Never gloss

The articles, the simple prepositions and their contractions, and the
clitic pronouns never get a vocabulary entry:

```
il lo la i gli le l' un uno una un'
di a da in con su per tra fra
del dello della dei degli delle al allo alla ai agli alle dal dallo dalla
dai dagli dalle nel nello nella nei negli nelle sul sullo sulla sui sugli
sulle
mi ti ci vi si lo la li le gli ne
io tu lui lei noi voi loro
e ed o ma se che non
```

## Chunking

A chunk is a sense group of roughly **2–6 words** — a verb with its
object, a noun with its adjective, a preposition with its noun: something
a reader hovers and that *means* something on its own. Never split an
**article from its noun** (`la casa`), a **clitic from its verb**
(`lo vedo`, `dimmelo`), a **preposition from its article** and both from
their noun (`nella casa`, `a Roma`), a **negation from its verb** (`non
so`), or an auxiliary from its participle (`ho visto`, `è andata`). A very
short sentence (`Sì.`, `Vieni!`) is one chunk; that is normal and not a
fault.

## Example

One sentence of Italian, answered: its chunks as they stand in the list of your
answer. The `en` of each chunk says only what that chunk says, in the order of
the Italian.

```json
{"chunks": [
  {"fa": "Mi piace molto", "tr": "{{?classic}}mi piace mòlto{{/classic}}{{?ipa}}mi ˈpjatʃe ˈmɔlto{{/ipa}}", "voc": "\\vb{piacere}{}{piaccio}{}{piaciuto}{}{to be pleasing (aux. \\pw{essere}; p.r. \\pw{piacqui})}; here \\pw{piace}, 3sg pres.", "en": "I like very much"},
  {"fa": "questa canzone,", "voc": "\\dw{canzone}{} song, f.", "en": "this song,"},
  {"fa": "ma non so cantarla.", "tr": "{{?classic}}ma non sò cantarla{{/classic}}{{?ipa}}ma non ˈsɔ kanˈtarla{{/ipa}}", "voc": "\\vb{sapere}{}{so}{}{saputo}{}{to know, to know how to (p.r. \\pw{seppi})}; \\vb{cantare}{}{canto}{}{cantato}{}{to sing}; here \\pw{cantarla} = \\pw{cantare} + \\pw{la}", "en": "but I do not know how to sing it."}
]}
```

Notice: the read-in-a-row `en` is stiff English (*I like very much | this song*)
and right, because the Italian puts the subject after the verb; `piace` is none
of the three forms the `\vb` prints, so it is named after the entry, outside it;
the sound slots stay empty because every verb here is stressed on its
next-to-last syllable; the second chunk has no `tr`, its spelling saying all
there is to say; and the clitic `-la` stays in its verb's chunk, spelled out
after the entry.
