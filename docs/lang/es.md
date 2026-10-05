# Spanish — the annotation conventions

{{?new}}How a Spanish sentence becomes a glossed line: what goes into each field and
how it is written. These rules bind both the reading editions and the video
captions; they are embedded whole into every prompt that asks for Spanish
annotation, so they are written as instructions to the annotator.

Two of the field names are languages, and neither is a claim about one: `fa`
is the text in the target language — Spanish here — and `en` is the gloss
beside it. They are the names Persian and English left behind from the days
when they were the only two languages the toolbox had, and they are the same
two keys in every book and every video. Which language the gloss is written
in is the book's or the video's own choice, `"gloss"` in `book.json` /
`video.json`, and English when the key is absent. This file is about Spanish
as the language being **taught**: the examples below gloss into English
because they must gloss into something, and every rule that turns on the
gloss language says so.{{/new}}

## The text field

`fa` reproduces the source **verbatim**: same spelling, same accents, same
punctuation, the source's own oddities included — a regional form, an old
spelling, an ASR slip in a caption. Chunks split only at spaces; joined back
with single spaces they must reproduce the sentence exactly, and a machine
checks that. **Never correct the text in `fa`**{{?new}} — the correction goes in
{{?video}}`note`{{/video}}{{?book}}the vocabulary line{{/book}}{{/new}}.

Spanish is plain text: there are no marks to add and none to strip{{?book}}, so the
registry's `strip` is null and there is no bare pass{{/book}}. Two things go wrong
often enough to be worth naming:

- **The written accent is spelling, not decoration.** It is what tells the
  reader where the stress is (`corazón`, `fácil`, `estábamos`) and, on the
  monosyllables, which of two words this is: `el`/`él`, `tu`/`tú`, `mi`/`mí`,
  `si`/`sí`, `mas`/`más`, `se`/`sé`, `de`/`dé`, `te`/`té`, `que`/`qué`,
  `como`/`cómo`, `donde`/`dónde`. Never add one the source does not write and
  never drop one it does. A source that still writes `sólo`, `éste` or `ésta`
  by the old rule keeps them; that is its spelling, not an error.
- **The inverted marks belong to the sentence.** `¿` and `¡` open every
  question and exclamation and are part of the text, not typography. A
  caption whose ASR has dropped one is reproduced without it, and the missing
  mark is noted {{?video}}in `note`{{/video}}{{?book}}in the vocabulary line{{/book}} if it is worth noting at all.

`ñ` is a letter of its own and not an `n` with something on it, and the `ü` of
`pingüino` and `vergüenza` is not decoration either — it is what puts the `u`
back into `gue`/`gui`. Neither may be folded away.

{{?studio}}Spanish has no character range of its own in the registry and could not be
given one: it is written in the alphabet the toolbox's own prose is written
in. So nothing detects a run of Spanish — and where the glosses are in
another Latin-script language, English or Italian or French, nothing tells
the two apart by eye either. Wherever the format asks you to mark the target
text (a studio document's `[…]{tl}` mark), mark every Spanish run; in a book
chunk or a video chunk `fa` is Spanish by definition and needs no mark.{{/studio}}

## Reading

This language has no reading field: the `kana` key is ignored where it
appears, and nothing asks for one.

## Transliteration

{{?classic}}`tr` is an **IPA-lite pronunciation aid, only where it helps**, and it may be
omitted — most Spanish chunks need none, fewer than in any other language
here. The spelling is very nearly a map of the sound, and the reader is told
so on the how-to-read page; a line that respells `la casa está en la mesa`
teaches nothing and costs a line of the page.

**Stress is never marked here**, and that is the one real difference from the
Italian line. Spanish already marks it: a word stressed anywhere but where
the default rule puts it carries a written accent, so the spelling has
answered the question before the pronunciation line is reached. Nor is vowel
quality marked. Spanish has five vowels with one value each — no open and
closed `e` and `o` to distinguish, so none of Italian's `è`/`é`, `ò`/`ó`
appears in a Spanish line.

A respelling keeps the accent the word itself carries (`corazón` →
`korasón`) and adds none. Give a `tr` for what the spelling does not show:

- **`g` before `e`/`i`, and `j`**, which are the `ch` of *loch*, written `x`:
  `gente` → `xente`, `hijo` → `ixo`, `mujer` → `muxer`, `general` →
  `xeneral`;
- **silent `h`**: `hombre` → `ombre`, `ahora` → `aora`, `hola` → `ola`;
- **`ll` and `y`**, one sound, written `ʝ`: `calle` → `kaʝe`, `yo` → `ʝo`.
  This is the sound that moves most between regions — `ʃ` or `ʒ` in the Río
  de la Plata — so write what the recording says, and let the book say once
  which Spanish it is read in;
- **`c` before `e`/`i`, and `z`**: `s` in most of the Americas and `θ` (the
  `th` of *thin*) in most of Spain. Both are correct; the recording decides.
  `cinco` is `sinko` or `θinko`, `zapato` is `sapato` or `θapato`. A book or
  a video keeps one answer throughout;
- **`qu`, `gu`, `ü`**: `qu` and `gu` before `e`/`i` are plain `k` and `g`
  (`queso` → `keso`, `guerra` → `gerra`), and `ü` is the one that puts the
  `u` back (`pingüino` → `pingwino`);
- **`r` at the beginning of a word**, which is the trill and is written `rr`
  like the doubled one: `rojo` → `rroxo`, against the single tap of `caro` →
  `karo`;
- **`ñ`** is `ɲ` — the same sign Italian's `gn` and French's `gn` take, so a
  reader who has met either already has it;
- a **borrowed or foreign word** said the way the source says it (`whisky` →
  `gwiski`, `jazz` → `ʝas`), which is the case the spelling helps least.

`b` and `v` are one sound and the letter does not say which; that is worth
knowing once and is on the how-to-read page, not repeated in every chunk.{{/classic}}{{?ipa}}`tr` is written in **IPA**: broad (phonemic), for standard Spanish, with
no slashes and no square brackets round it, and **only where it helps**; it may be
omitted — most Spanish chunks need none, fewer than in any other language here.
The spelling is very nearly a map of the sound, and a line that transcribes `la
casa está en la mesa` teaches nothing and costs a line of the page. Spanish has
five vowels with one value each, `a e i o u`, so there is no open and closed `e`
and `o` to tell apart. The stress is written with `ˈ` before the stressed
syllable of every word of more than one syllable, since IPA has no written
accent (`ˈkasa`, `muˈxeɾ`, `esˈtabamos`). Give a line for what the spelling does
not show:

- **`g` before `e`/`i`, and `j`**, which are the `ch` of *loch*, written `x`:
  `gente` → `ˈxente`, `hijo` → `ˈixo`, `mujer` → `muˈxeɾ`;
- **silent `h`**: `hombre` → `ˈombɾe`, `ahora` → `aˈoɾa`;
- **`ll` and `y`**, one sound, written `ʝ`: `calle` → `ˈkaʝe`, `yo` → `ʝo`. This
  is the sound that moves most between regions — `ʃ` or `ʒ` in the Río de la
  Plata — so write what the recording says, and let the book say once which
  Spanish it is read in;
- **`c` before `e`/`i`, and `z`**: `s` in most of the Americas and `θ` (the `th`
  of *thin*) in most of Spain. Both are correct; the recording decides. `cinco` is
  `ˈsinko` or `ˈθinko`, `zapato` is `saˈpato` or `θaˈpato`. A book or a video keeps
  one answer throughout;
- **`qu`, `gu`, `ü`**: `qu` and `gu` before `e`/`i` are plain `k` and `g` (`queso`
  → `ˈkeso`, `guerra` → `ˈgera`), and `ü` is the one that puts the `u` back
  (`pingüino` → `pinˈgwino`);
- **`ch`** is `tʃ` (`chico` → `ˈtʃiko`), and **`ñ`** is `ɲ` (`año` → `ˈaɲo`) —
  the same sign Italian's `gn` and French's `gn` take;
- **`r`**: the trill, at the beginning of a word and written `rr`, is `r`, against
  the single tap `ɾ` (`rojo` → `ˈroxo`, `carro` → `ˈkaro`, against `caro` →
  `ˈkaɾo`);
- a **borrowed or foreign word** said the way the source says it (`whisky` →
  `ˈgwiski`, `jazz` → `ˈʝas`), which is the case the spelling helps least.

`b` and `v` are one sound, written `b` (`vaca` → `ˈbaka`), and the letter does not
say which: that is worth knowing once and is on the how-to-read page.{{/ipa}}

Write the whole chunk in `tr` when you give one, not a single word out of it.
Never write `tr` for a chunk whose spelling is regular — which in Spanish is
most of them.{{?video}} In a **video** `tr` is the sound of what was **said**: where
the speaker runs words together or swallows a `d` ({{?classic}}`cansado` → `kansao`{{/classic}}{{?ipa}}`cansado` → `kanˈsao`{{/ipa}}),
that is what goes in, because the reader is listening to the same recording.{{/video}}

## Vocabulary

`voc` is written in the voice of the books' gloss blocks: headword + meaning,
with the grammar a learner needs to recognise the form. The pronunciation
slots of the macros are filled only where a pronunciation line would be given
at all; elsewhere they are left empty.

- A **verb** is given as **infinitive, first person present, third person
  preterite**, in that order. The edition prints *pres.* and *pret.* before
  the second and the third, so never put another form into those slots.
  Those two are the forms you cannot guess: the `yo` present carries both the
  odd consonant (`tengo`, `salgo`, `conozco`, `quepo`) and the stem change
  (`quiero`, `puedo`, `pido`), and is what the present subjunctive is built
  on; the `él` preterite carries a stem of its own (`tuvo`, `dijo`, `quiso`,
  `hizo`, `fue`) and the change an `-ir` verb makes only outside the `yo`
  form — `pidió`, `durmió`, `sintió`, `leyó` — which `pedí`, `dormí`,
  `sentí`, `leí` never show. It is also the person a story is told in.
  `\vb{tener}{}{tengo}{}{tuvo}{}{to have (fut. \pw{tendré})}`,
  `\vb{pedir}{}{pido}{}{pidió}{}{to ask for}`,
  `\vb{hablar}{}{hablo}{}{habló}{}{to speak}`. No class (`-ar`, `-er`,
  `-ir`) and no stem-change note (`e→i`): the infinitive and the two forms
  show both. A **regular** verb gets all three too: **every** verb gets a
  `\vb`, no exceptions.
- A **pronominal** verb is the `-se` infinitive with the clitic in both forms
  (`\vb{irse}{}{me voy}{}{se fue}{}{to leave}`), a fixed verbal phrase is
  whole (`darse cuenta`, `me doy cuenta`, `se dio cuenta`), and an
  **impersonal** verb, which has no `yo`, gives the third person in the
  second slot as well: `\vb{llover}{}{llueve}{}{llovió}{}{to rain}`,
  `\vb{haber}{}{hay}{}{hubo}{}{there to be (fut. \pw{habrá})}`.
- What the three forms cannot say goes in **one parenthesis after the
  meaning**, items parted by `; `, **only where it is irregular**, in these
  words:
  - `p.p. \pw{hecho}`: the past participle is regular (`-ado`, `-ido`) and
    so not one of the three, but a reader who meets `hecho` or `visto` will
    not find it by taking an ending off. The others worth it are `dicho`,
    `visto`, `puesto`, `escrito`, `roto`, `vuelto`, `abierto`, `muerto`,
    `cubierto`, `resuelto` and their compounds.
  - `fut. \pw{tendré}`: the first person future, where it is not the
    infinitive plus an ending — `tendré`, `pondré`, `saldré`, `vendré`,
    `podré`, `sabré`, `querré`, `haré`, `diré`, `habré`, `cabré`, `valdré`.
    The same stem makes the conditional, and `podría`, `tendría`, `diría`
    are on every page of a novel. An impersonal verb gives the third person
    here as it does in the second slot (`fut. \pw{habrá}`).

  `\vb{hacer}{}{hago}{}{hizo}{}{to do, to make (p.p. \pw{hecho}; fut.
  \pw{haré})}`, `\vb{abrir}{}{abro}{}{abrió}{}{to open (p.p. \pw{abierto})}`.
  Where the language has **two** of either and one of them is irregular,
  give both, parted by a slash, the regular one included, since both are
  written: `p.p. \pw{imprimido}/\pw{impreso}`, `p.p. \pw{freído}/\pw{frito}`,
  `fut. \pw{predeciré}/\pw{prediré}`.
- **`ser` and `estar` are both "to be", and the entry must say which and
  why** — a gloss that says only *to be* has told the reader nothing they
  did not already misunderstand. Name the division in the meaning slot, in
  these words, every time either verb is given a full entry:
  `\vb{ser}{}{soy}{}{fue}{}{to be — ser: what a thing \textit{is} (identity,
  origin, material, time, what it is like always)}`,
  `\vb{estar}{}{estoy}{}{estuvo}{}{to be — estar: where and how it is
  \textit{right now} (place, state, the result of a change)}`. Where an
  adjective changes meaning with the verb, that belongs to the adjective's
  own entry and not to the verb's: `es aburrido` is *he is boring*, `está
  aburrido` is *he is bored*; so also `listo` (clever / ready), `bueno`
  (good / tasty, well), `malo`, `vivo`, `verde`. `fui` is the preterite of
  **both `ser` and `ir`**, and the entry for it says so: `\dw{fui}{} \pw{ser}
  or \pw{ir}, 1sg pret. — the same form for both; the sentence decides`.
- **The preterite and the imperfect are not one past tense**, and neither
  survives an English gloss that says *did*. Name which one the form is, and
  let the meaning carry the difference: the preterite is one finished event
  (`habló` · *spoke, said his piece*), the imperfect is the background, the
  habit, the unfinished (`hablaba` · *was speaking, used to speak*). The
  preterite `habló` is the third form the `\vb` prints; the imperfect is named
  after the entry: `\vb{hablar}{}{hablo}{}{habló}{}{to speak}; here
  \pw{hablaba}, 1/3sg imperf.`. The handful of verbs whose **meaning** changes with the tense earn a full entry
  every time, because a reader glossing from English will get them backwards:
  `sabía` *knew* against `supo` *found out*; `conocía` *knew (a person)*
  against `conoció` *met*; `podía` *could* against `pudo` *managed to*;
  `quería` *wanted* against `quiso` *tried to* and `no quiso` *refused*;
  `tenía` *had* against `tuvo` *got*.
- **The subjunctive must be named**, always, because the gloss language
  almost certainly has no form to show it with: *quiero que vengas* comes
  into English as *I want you to come*, an infinitive, and the reader sees
  nothing at all where the Spanish has a whole mood. Write it after the
  entry: `\vb{venir}{}{vengo}{}{vino}{}{to come (fut. \pw{vendré})}; here
  \pw{vengas}, pres. subj. after \pw{querer que}`, and so `; here \pw{fuera},
  imperf. subj.` for `ser` or `ir` and `; here \pw{hubiera venido}, pluperf.
  subj.`. **Name the trigger** with it — `querer que`, `para que`, `antes de que`, `ojalá`, `no creo que`,
  `cuando` + a future, `si` + a condition contrary to fact — since the
  trigger is the whole of why the form is there. The imperfect subjunctive
  has two endings, `-ra` and `-se` (`fuera`/`fuese`, `hablara`/`hablase`);
  both are correct, they are not corrected into one another, and the entry
  names whichever the source wrote.
- A **noun** carries its **gender**, every time, because the article in the
  text may be elided into a contraction or absent altogether: `\dw{agua}{}
  water, f.` — a feminine noun that takes `el`, and the reader will read it as
  masculine unless told; `\dw{mano}{} hand, f.`; `\dw{día}{} day, m.`;
  `\dw{problema}{} problem, m.`. An irregular or shifting plural is given with
  it: `\dw{lápiz}{} pencil, m., pl. \pw{lápices}`; `\dw{inglés}{} English, m.,
  pl. \pw{ingleses}`.
- An **adjective** is given in the masculine singular; the forms that shorten
  before a masculine noun are named (`bueno / buen`, `malo / mal`, `grande /
  gran`, `primero / primer`, `ciento / cien`). Name what was stripped: the
  plural `-s`/`-es`, the feminine `-a`, the diminutive (`-ito`, `-illo`), the
  augmentative (`-ón`, `-azo`), the absolute superlative (`-ísimo`), the
  adverb's `-mente`.
- **Clitic pronouns attach to the verb, and the entry is filed under the
  verb.** Before a finite verb they stand apart and get no entry of their own
  (`me lo dijo`, `se lo di`); onto an infinitive, a gerund or an affirmative
  imperative they are written, and then the whole word is one word in the
  text: `dímelo`, `decírtelo`, `dándomelo`, `verlo`, `siéntate`. Spell it out
  under its verb, after the entry: `; here \pw{dímelo}, imperative + \pw{me} +
  \pw{lo} — say it to me`; `; here \pw{decírtelo}, infinitive + \pw{te} +
  \pw{lo} — to tell it to you`. The **accent that
  appears** when the clitics are added (`da` → `dame` → `dámelo`; `di` →
  `dime` → `dímelo`) is part of the spelling and is reproduced, never added
  or removed by you. Their **order** is fixed and is not the English one:
  `se`, then `te`/`os`, then `me`/`nos`, then `lo`/`la`/`los`/`las`. And the
  `se` of `se lo di` is **not reflexive**: it is `le`/`les` forced to change
  because `lo` follows, so it means *to him, to her, to them*, and the entry
  says so — `\dw{se}{} = \pw{le} (to him/her), before
  \pw{lo}/\pw{la}/\pw{los}/\pw{las}` — or the reader will read a reflexive that
  is not there.
- **The personal `a` is not the preposition `to`.** Spanish puts `a` before a
  direct object that is a person (`veo a María`, `busca a su hermano`,
  `conocí al médico`), and a reader glossing word by word gets *I see to
  María*. It takes no entry of its own — it is in the never-gloss list below
  — but where the chunk's gloss could be read as a preposition, say it in
  the vocabulary line once: `\dw{a}{} the personal \pw{a}: marks a person as
  the object, not "to"`.
- The line uses four macros and nothing else: `\dw{fa}{rom} gloss` ·
  `\vb{inf}{rom}{pres}{rom}{pret}{rom}{meaning}` · `\bw{base}{rom}{meaning}` ·
  `\pw{fa}` — plus `\textit`, `\emph`, `\nobreak` — and its entries are parted
  by `; `. `\vb` for every verb, `\dw` for every other headword.
- A form in the text that is none of the three the `\vb` prints, nor one its
  parenthesis names, is named after the entry, outside it, with what it is:
  `\vb{hablar}{}{hablo}{}{habló}{}{to speak}; here \pw{hablaba}, 1/3sg imperf.`.

One equivalent in the gloss language rather than a string of synonyms; no
etymologies; **an empty `voc` is the right answer** for a chunk needing
nothing. The repetition rule is Frank's own: a full entry the **first time** a
word appears, briefer or none on later appearances.

The meaning is what the gloss language is for; the labels around it are not.
*pres.* and *pret.* are printed by the edition itself — the same two words in
every Spanish book, out of the registry — so leave them, and `p.p.`, `fut.`,
the `f.`, the `pl.`, `imperf.` and `subj.`, as they are written above
whatever the glosses are in: a line that translated the labels and not the
forms would be reading in two conventions at once. Where the gloss language
is Spanish, the meaning is a **definition** and not a translation: commoner
words than the headword, and never the headword's own relatives.
`docs/lang/en.md` sets that case out in full; it belongs to no one language.

Which words the reader already owns turns on the gloss language, and the
judgement is yours: a word transparent from the reader's own language earns a
shorter entry or none. `importante`, `nación` and `posible` say themselves to
a reader of English, Italian or French and need no meaning, only what the
form is doing; to a reader of Persian, Turkish or Japanese they say nothing
at all. Judge from the gloss language, never from English — and beware the
ones that only look transparent (`embarazada` is pregnant, not embarrassed;
`éxito` is a success, not an exit; `actualmente` is currently, not actually;
`librería` is a bookshop; `carta` is a letter; `largo` is long, not large),
which are worth a full entry precisely because the reader will not stop for
them.

## Never gloss

The articles, the simple prepositions and their two contractions, the
pronouns and the commonest conjunctions never get a vocabulary entry:

```
el la los las lo un una unos unas
a de en con por para sin sobre entre hasta desde hacia según tras
al del
yo tú vos él ella usted nosotros nosotras vosotros vosotras
ellos ellas ustedes
me te se nos os le les lo la los las mí ti sí conmigo contigo
y e o u ni pero sino que si no
```

`por` and `para` are on that list as words and not as a problem: neither is
glossed on its own, and where a chunk turns on the difference the verb or the
noun that governs it carries the explanation.

## Chunking

A chunk is a sense group of roughly **2–6 words** — a verb with its object, a
noun with its adjective, a preposition with its noun: something a reader
hovers and that *means* something on its own. A very short sentence (`Sí.`,
`¡Ven!`) is one chunk; that is normal and not a fault.

Never split:

- an **article from its noun** (`la casa`), or a **contraction from what it
  governs** (`al final`, `del pueblo`) — `al` and `del` are `a`/`de` with the
  article swallowed and are half a phrase on their own;
- a **preposition from its object** (`en la mesa`, `con mi hermano`), and the
  **personal `a` from its person** (`veo a María`);
- a **proclitic pronoun from its verb** (`me lo dijo`, `se lo di`, `te
  quiero`): they are unglossable alone, and this is the one Spanish rule the
  offline chunker had to be told (`lib/lang/es.chunk.json`);
- a **negation from its verb** (`no sé`, `no me lo dijo`), including the
  second negative that Spanish keeps (`no vi nada`);
- an **auxiliary from what it carries**: `he visto`, `había llegado`, `está
  hablando`, `va a comer`, `acaba de salir`, `sigue lloviendo`;
- a **noun from the adjective after it** (`la casa grande`), which is where
  Spanish puts it, nor from the short ones that come before (`buen día`,
  `gran cosa`);
- a **fixed expression**, whatever its syntax: `tener que`, `hay que`, `darse
  cuenta de`, `echar de menos`, `por supuesto`, `sin embargo`. The meaning is
  not in the pieces, and showing the pieces teaches the reader something
  untrue.

`que` and the other relativisers open the chunk they introduce rather than
closing the one before them (`Quiero | que vengas`). Enclitics need no rule:
they are written onto the verb (`dímelo`, `decírtelo`), so there is no space
there for a cut to fall in.

## Example

One sentence of Spanish, answered: its chunks as they stand in the list of your
answer. The `en` of each chunk says only what that chunk says, in the order of
the Spanish.

```json
{"chunks": [
  {"fa": "Ayer vi", "tr": "{{?classic}}aʝer vi{{/classic}}{{?ipa}}aˈʝeɾ bi{{/ipa}}", "voc": "\\vb{ver}{}{veo}{}{vio}{}{to see (p.p. \\pw{visto})}; here \\pw{vi}, 1sg pret.", "en": "yesterday I saw"},
  {"fa": "a María", "voc": "\\dw{a}{} the personal \\pw{a}: marks a person as the object, not \"to\"", "en": "María"},
  {"fa": "en el mercado.", "voc": "\\dw{mercado}{} market, m.", "en": "in the market."}
]}
```

Notice: only the first chunk has a `tr`, for the `y` of *ayer*, the spelling
saying all there is to say in the others; `vi` is none of the three forms the
`\vb` prints, so it is named after the entry, outside it; the personal `a` is
explained once and is not rendered as *to*; and the noun carries its gender.

{{?note}}No speaker has reviewed this example yet.{{/note}}
