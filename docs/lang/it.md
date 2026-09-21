# Italian — the annotation conventions

How an Italian sentence becomes a glossed line: what goes into each field
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
turns on the gloss language says so.

## The text field

`fa` reproduces the source **verbatim**: same spelling, same accents, same
apostrophes and elisions (`l'uomo`, `un'ora`, `po'`), same punctuation, the
source's own oddities included — a regional form, an old spelling, an ASR
slip in a caption. Chunks split only at spaces; joined back with single
spaces they must reproduce the sentence exactly, and a machine checks
that. **Never correct the text in `fa`** — the correction goes in `note`
(videos) or in the vocabulary line (books).

Italian is plain text: there are no marks to add and none to strip. The
written accents are part of the spelling (`è`, `perché`, `città`) and stay
exactly as the source has them; do not add a stress accent to a word the
source writes without one — stress, when it helps, is shown in `tr` and
nowhere else. There is one pass with help and one with the chunks; there is
no "bare" pass, because the text is already bare.

Italian has no character range of its own in the registry and could not be
given one: it is written in the alphabet the toolbox's own prose is written
in. So nothing detects a run of Italian — and where the glosses are in
another Latin-script language, English or French or Turkish, nothing tells
the two apart by eye either. Wherever the format asks you to mark the
target text (a studio document's `[…]{tl}` mark), mark every Italian run;
in a book chunk or a video chunk `fa` is Italian by definition and needs no
mark.

## Reading

This language has no reading field.

## Transliteration

`tr` is an **IPA-lite pronunciation aid, only where it helps**, and it may
be omitted — most chunks need none. Use it for what the spelling does not
show:

- the **open and closed e and o**: `è` for /ɛ/ and `é` for /e/, `ò` for
  /ɔ/ and `ó` for /o/ (`pésca` peach, `pèsca` fishing; `bótte` barrel,
  `bòtte` blows);
- the **stress**, when it falls anywhere but the penultimate syllable or is
  ambiguous, marked on the stressed vowel as the dictionary marks it — a
  grave on `à`, `ì`, `ù` and on an open `è`, `ò`, an acute on a closed `é`,
  `ó` (`àncora` anchor, `ancóra` still; `tàvolo`, `telèfono`, `capìscono`);
- the voiced and voiceless **s** and **z** where they matter (`s` = /s/,
  `ṡ` = /z/; `z` = /ts/, `ż` = /dz/): `càṡa`, `ròṡa`, `żèro`, `pizza`;
- the sounds a reader coming from any other language misreads: `gli` as `ʎ`
  (`fàmiʎa`), `gn` as `ɲ` (`gnòcchi` → `ɲòkki`), `sc` before e/i as `ʃ`
  (`pésce` → `péʃe`), doubled consonants written double. Only `gn` is
  spelt the same elsewhere (a French reader has it already); `gli` and `sc`
  are Italian's alone, so these stay whatever the glosses are written in.

Write the whole chunk in `tr` when you give one, not a single word out of
it. Never write `tr` for a word whose pronunciation is regular and
unambiguous.

## Vocabulary

`voc` is written in the voice of the books' gloss blocks: headword +
meaning, with the grammar a learner needs to recognise the form.

- A **verb** is given as the infinitive, the first person present and the
  past participle, and its auxiliary when that is *essere*: `andare · pres.
  vado · p.p. andato · to go (aux. essere)`. No conjugation class: the
  infinitive's own ending and the first person (`finisco`, `dormo`) already
  say it. An **irregular form** in the text is tied to its infinitive:
  `vado · andare, 1sg pres.`; `fatto · fare, past participle`; `andrò ·
  andare, fut.`.
- A **noun** carries its **gender** and, when it is not regular, its
  plural: `la mano (f., pl. le mani) · hand`; `il problema (m., pl. i
  problemi) · problem`; `l'uovo (m., pl. le uova) · egg`.
- An **adjective** is given in the masculine singular; a form that changes
  (`bello / bel / bell'`, `buono / buon`) is named.
- A **clitic** combination is spelled out the first time (`glielo = gli +
  lo`); a **preposition + article** contraction is named (`nel = in + il`).
- Name what was stripped: the plural, the feminine, the diminutive
  (`-ino`, `-etto`), the superlative (`-issimo`), the adverb ending
  (`-mente`).
- In a video the line is plain text, the verb as `venire · pres. vengo ·
  p.p. venuto · to come (aux. essere; p.r. venni)` and a form of it in the
  chunk first, with the entry in brackets after it: `vado I go (andare ·
  pres. vado · p.p. andato · to go (aux. essere))`. In a book the line uses
  the four macros `\dw` `\vb` `\bw` `\pw` (plus `\textit`, `\emph`,
  `\nobreak`), as the Persian editions do: `\vb` for every verb, `\dw` for
  every other headword. The seven slots of `\vb` are, in this order,
  **infinitive, first person present, past participle**, each with its
  pronunciation, then the meaning; the edition prints *pres.* and *p.p.*
  before the second and third forms, so never put another form into those
  slots. A form's pronunciation is its **stress, and only where it is not on
  the next-to-last syllable** — the form with the stressed vowel marked
  (`prèndere`, `àbito`, `telèfono`, `andàrsene`), empty for `parlare`,
  `vedere`, `prendo`: an open or closed `e` or `o` is left to the chunk's
  own `tr`. A pronominal verb is the infinitive with its clitic and the
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
  `\vb{prendere}{prèndere}{prendo}{}{preso}{}{to take (p.r. \pw{presi})}`,
  `\vb{venire}{}{vengo}{}{venuto}{}{to come (aux. \pw{essere}; p.r.
  \pw{venni})}`, `\vb{parlare}{}{parlo}{}{parlato}{}{to speak}` — the last
  with nothing in brackets, because nothing about it is out of the ordinary.
- The gloss editor's sources sidebar, in the reader and in the player, now
  proposes this entry from the dictionary for a verb it recognises, the
  auxiliary and an irregular passato remoto included, and for a form the
  dictionary only knows as a compound (`alzandosi`, `dimmelo`, `farlo`) the
  entry of the verb it is a form of. It is a **draft for you to correct**:
  its meaning is the dictionary's first sense cut to one equivalent, which
  is often not the one the chunk needs (`dovere` comes as "to owe"). Where a
  reflexive pronoun stands before the word and the dictionary lists the two
  together as a form of the pronominal verb (`si alzò`, `mi alzo`, `me ne
  vado`, `si è alzato`), it proposes the pronominal verb (`alzarsi`,
  `andarsene`) — but with `si` it cannot know a reflexive from an impersonal
  or passive one (`si dice`, `si vendono case` are `dire`, `vendere`), and
  the button says so. The auxiliary is the one the dictionary's head line
  gives, and that is sometimes wider than usage: `sapere` and `usare` come
  with *avere/essere*, the *essere* for a sense this text will hardly have
  (to taste of, to be in fashion) — trim it to what the chunk uses. Correct
  the draft before it is saved; where it could not fill a slot, the button
  says which.

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
