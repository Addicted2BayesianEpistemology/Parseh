# French — the annotation conventions

How a French sentence becomes a glossed line: what goes into each field and
how it is written. These rules bind both the reading editions and the video
captions; they are embedded whole into every prompt that asks for French
annotation, so they are written as instructions to the annotator.

Two of the field names are languages, and neither is a claim about one: `fa`
is the text in the target language — French here — and `en` is the gloss
beside it. They are the names Persian and English left behind from the days
when they were the only two languages the toolbox had, and they are the same
two keys in every book and every video. Which language the gloss is written
in is the book's or the video's own choice, `"gloss"` in `book.json` /
`video.json`, and English when the key is absent. This file is about French
as the language being **taught**: the examples below gloss into English
because they must gloss into something, and every rule that turns on the
gloss language says so.

## The text field

`fa` reproduces the source **verbatim**: same spelling, same accents, same
apostrophes, same punctuation, the source's own oddities included — a
nineteenth-century spelling, a reform spelling, a regionalism, an ASR slip in
a caption. Chunks split only at spaces; joined back with single spaces they
must reproduce the sentence exactly, and a machine checks that. **Never
correct the text in `fa`** — the correction goes in `note` (videos) or in the
vocabulary line (books).

French is plain text: nothing is written in for the first pass and nothing
comes off for a bare one, because every mark on the page is spelling and not
help. Keep, exactly as the source has them:

- the **accents**, including the ones that are the whole difference between
  two words (`ou` / `où`, `a` / `à`, `sur` / `sûr`, `du` / `dû`), and their
  absence on a capital where the source leaves it off (`Etat` stays `Etat`,
  `État` stays `État`);
- the **cedilla** (`ça`, `reçu`, `français`) and the ligatures `œ` and `æ`
  (`sœur`, `cœur`, `œuf`, `ex æquo`) — never respell `œ` as `oe`;
- the **apostrophe of elision**, and the character the source uses for it,
  `'` or `’` (`l'homme`, `qu'il`, `j'ai`, `aujourd'hui`, `presqu'île`): the
  fidelity check compares character for character, so do not normalise one
  into the other;
- the **hyphens** of inversion and of compounds (`est-ce que`, `dit-il`,
  `y a-t-il`, `peut-être`, `c'est-à-dire`);
- whichever spelling the source uses where two are allowed (`maître` /
  `maitre`, `coût` / `cout`, `oignon` / `ognon`).

**The space before `;` `:` `!` `?` and inside `«  »`** is French typography
and part of the text. Write the space the source has, and only that: do not
add one the source has not got, and do not close one up — `Vraiment ?` is not
`Vraiment?`. A run of whitespace is normalised before the comparison, so the
ordinary space and the no-break space a well-set source uses both pass;
deleting one does not. How wide it is printed is the edition's business, not
yours. Keep `«` and `»` themselves as well, and never swap them for `"`.

French has no character range of its own in the registry and could not be
given one: it is written in the alphabet the toolbox's own prose is written
in, and its accents are a few letters of a word rather than a script. So
nothing detects a run of French — and where the glosses are in another
Latin-script language, English or Italian or Turkish, a `é` or a `ç` is the
only thing that ever tells the two apart by eye, on the words that have one.
Wherever the format asks you to mark the target text (a studio document's
`[…]{tl}` mark), mark every French run; in a book chunk or a video chunk `fa`
is French by definition and needs no mark.

## Reading

This language has no reading field: the `kana` key is ignored where it
appears, and nothing asks for one.

## Transliteration

`tr` is how the chunk is **said**, and in French it is worth writing for
almost every chunk: the spelling records a pronunciation the language has left
behind, and a reader who has only the spelling will sound final consonants
that are silent, put an `n` after a nasal vowel, and miss every liaison. The
field is optional, and that is a licence to leave it out of a chunk where
nothing can be got wrong — a figure (`1914`), an interjection (`Ah !`), a word
the gloss language says the same way (`le film`) — not a licence to skip a
chunk because its words are common: `Oui` and `Bonjour` both need one. Write
it for the **whole chunk** or not at all, in lower case even where it has a
capital (`Paris` → `pari`), and without punctuation.

The scheme is a respelling, not IPA. Every symbol it uses is below, and it
uses no other. It is one scheme for every French edition whatever the
glosses are written in, and the English words a symbol is explained by here
(*yes*, *wet*) are there to fix the sound, not to say who the reader is.
Never respell the line in the gloss language's own orthography: `ou` stays
`ou` and does not become `u` for an Italian reader, `ʃ` stays `ʃ` and does
not become `sc` or `ş`.

**Vowels**

| written | the sound | example |
|---|---|---|
| `a` | the a of *chat* | `chat` → `ʃa` |
| `é` | the closed e | `été` → `été`, `parler` → `parlé` |
| `è` | the open e | `mère` → `mèr`, `il était` → `il étè` |
| `e` | the mute e of *le*, and never anything else | `le` → `le`, `petit` → `peti` |
| `i` | the i of *lit* | `lit` → `li` |
| `o` | the closed o | `beau` → `bo`, `hôtel` → `otèl` |
| `ò` | the open o | `botte` → `bòt`, `homme` → `òm` |
| `ou` | the ou of *tout* | `tout` → `tou`, `sourire` → `sourir` |
| `ü` | the u of *tu* | `tu` → `tü`, `plus` → `plü` |
| `eu` | the vowel of *peu*, and the opener one of *peur* | `vieux` → `vyeu`, `peur` → `peur` |
| `ã` | nasal a: *an am en em* | `grand` → `grã`, `enfant` → `ãfã` |
| `ẽ` | nasal e: *in ain ein un um* | `vin` → `vẽ`, `pain` → `pẽ`, `brun` → `brẽ` |
| `õ` | nasal o: *on om* | `bon` → `bõ`, `nom` → `nõ` |

**Glides**

| written | the sound | example |
|---|---|---|
| `y` | the y of *yes*: *-ill-*, and *i* before a vowel | `billet` → `biyè`, `bien` → `byẽ` |
| `w` | the w of *wet*: *oi*, and *ou* before a vowel | `moi` → `mwa`, `oui` → `wi` |
| `ü` before a vowel | the glide of *lui* | `lui` → `lüi`, `huit` → `üit` |

**Consonants** keep the values English and Italian alike give them —
`b d f g k l m n p s t v z`, with `g` always hard, `s` always hissed, `r`
made in the throat — plus three:

| written | the sound | example |
|---|---|---|
| `ʃ` | what *ch* spells | `chat` → `ʃa`, `chose` → `ʃoz` |
| `ʒ` | what *j*, and *g* before e or i, spell | `je` → `ʒe`, `gens` → `ʒã` |
| `ɲ` | what *gn* spells | `agneau` → `aɲo`, `montagne` → `mõtaɲ` |

`c`, `h`, `j`, `q` and `x` never appear in a `tr` — `j` least of all, since
the yod is `y` — so write the sound instead: `cinq` → `sẽk`, `six` → `sis`,
`exact` → `ègza`, `homme` → `òm`.

The rules the symbols are used by:

1. **A silent letter is not written.** `petit` → `peti`, `les livres` →
   `lé livr`, `beaucoup` → `bokou`. The `-ent` of a verb is silent (`ils
   parlent` → `il parl`); the `-ment` of an adverb is not (`lentement` →
   `lãtemã`).
2. **A liaison takes a hyphen.** A consonant that is silent alone but sounded
   before a vowel is written at the head of the word it moves to, after a
   hyphen — and the hyphen is used for nothing else: `les amis` → `lé-zami`,
   `vous avez` → `vou-zavé`, `c'est un` → `sè-tẽ`, `deux ans` → `deu-zã`,
   `est-il` → `è-til`, `un grand homme` → `ẽ grã-tòm`. Where the liaison is
   *not* made the words stay apart: after `et` (`et il` → `é il`, never
   `é-til`) and before an aspirate h (`les héros` → `lé éro`, `le hasard` →
   `le azar`).
3. **An elision makes one word**, and the apostrophe does not survive into
   `tr`: `l'homme` → `lòm`, `j'ai` → `ʒé`, `qu'il` → `kil`, `d'abord` →
   `dabòr`.
4. **A nasal vowel is one sound**: nothing is sounded after the tilde, and a
   following vowel or a doubled consonant undoes the nasal. `bon` → `bõ` but
   `bonne` → `bòn`; `an` → `ã` but `Anne` → `an`; `plein` → `plẽ` but
   `pleine` → `plèn`. `un` and `in` have fallen together for most speakers
   and are both `ẽ`.
5. **The mute e is written where it is said and left out where it is not.**
   In `petit` it is said (`peti`); in `samedi` and `maintenant` it is not
   (`samdi`, `mẽtnã`). A page read carefully keeps more of them than a speaker
   does, so a caption follows the speaker: `je ne sais pas` is `ʒe ne sè pa`
   said carefully and `ʃè pa` when that is what you hear.
6. **Nothing marks stress.** French stresses the last full syllable of the
   group and nowhere else, so — unlike the Italian line, which marks it —
   there is nothing here to mark.
7. **No letter is doubled.** French does not hold a consonant: `elle` → `èl`,
   `donner` → `dòné`, `attendre` → `atãdr`.
8. Words are spaced as the chunk spaces them, except where an elision or a
   liaison has joined two of them.

## Vocabulary

`voc` is written in the voice of the books' gloss blocks: headword +
pronunciation + meaning. Name what was stripped from the form in the text —
the plural `-s`/`-x`, the feminine `-e`, an adverb's `-ment`, the elided
article, the pronoun a hyphen carries after an inversion. One equivalent in
the gloss language rather than a string of synonyms, no etymologies, and
**an empty `voc` is the right answer** for a chunk needing nothing.

- A **verb** is given as **infinitive, first person present, past
  participle**, in that order, each with its sound, because the endings that
  carry the grammar are the ones you cannot hear. The edition prints *pres.*
  and *p.p.* before the second and the third, so no other form may go in
  those slots. No conjugation class is written: the infinitive prints its
  own ending, and `-er` is wrong for *aller* anyway. A **pronominal** verb
  carries its pronoun in the first two slots — `se lever`, `me lève`;
  `s'approcher`, `m'approche` — and its participle bare. A verb with **no
  first person** (`falloir`, `pleuvoir`, `neiger`) gives its third, with
  `il`: `\vb{falloir}{falwar}{il faut}{il fo}{fallu}{falü}{to be necessary
  (fut. \pw{il faudra} \textit{il fodra})}`.
- What the three cannot say goes in **one parenthesis after the meaning**,
  items parted by `; `, in this order and these words, each **only where it
  is not the ordinary case**:
  - `aux. être` for a verb whose perfect is made with *être* — and every
    pronominal verb — or `aux. être/avoir` for one that takes both
    (`monter`, `passer`, `sortir`). *avoir* is the default and is never
    printed.
  - `nous \pw{prenons} \textit{prenõ}`, the first person plural, where it
    is not the infinitive's stem + `-ons` — `prendre` (prenons), `boire`
    (buvons), `faire` (faisons), `écrire` (écrivons), `être` (sommes);
    nothing where it is (`parlons`, `venons`, `voulons`, `avons`), nor for
    the spelling of `commençons` and `mangeons`, nor for `finir`'s
    `finissons`. So a reader shown no *nous* form builds the plural, and the
    imperfect with it, from the infinitive — and is right.
  - `fut. \pw{irai} \textit{iré}`, the first person of the future, where it
    is not built on the infinitive (`irai`, `viendrai`, `ferai`, `pourrai`,
    `saurai`, `verrai`, `cueillerai`). An `-er` verb's future built on its
    own present counts as built on it: `lèverai`, `jetterai`, `appellerai`
    need nothing, since the second slot already shows `lève`, `jette`,
    `appelle`.

  `\vb{aller}{alé}{vais}{vè}{allé}{alé}{to go (aux. être; fut. \pw{irai}
  \textit{iré})}`, `\vb{prendre}{prãdr}{prends}{prã}{pris}{pri}{to take (nous
  \pw{prenons} \textit{prenõ})}`,
  `\vb{regarder}{regardé}{regarde}{regard}{regardé}{regardé}{to look at}` —
  the last with nothing in brackets, because nothing about it is irregular.
- A form in the text that is **none of the three** is named at the end of the
  meaning, after the parenthesis, with its sound: `\vb{venir}{venir}{viens}
  {vyẽ}{venu}{venü}{to come (aux. être; fut. \pw{viendrai} \textit{vyẽdré});
  here \pw{vint} \textit{vẽ}, past historic}`. The past historic a book
  narrates in and a subjunctive (`qu'il vienne`) both need this.
- A **verbal locution** — a verb welded to a bare noun with no article
  (`avoir peur`, `faire attention`, `prendre garde`, `rendre visite`) — is a
  `\vb` for the verb with an **empty seventh argument**, then a `\bw` for the
  noun, which carries the meaning of the whole:
  `\vb{avoir}{avwar}{ai}{é}{eu}{ü}{}\bw{peur}{peur}{to be afraid}`. The verb
  is not given a meaning of its own: it has none there.
- A **noun** carries its **gender**, every time, because nothing in the word
  shows it — and least of all where the article is elided or plural and hides
  it (`l'eau` is feminine, `l'homme` masculine, `les yeux` masculine). An
  irregular plural is given with it: `journal, pl. journaux`; `œil, pl.
  yeux`; `travail, pl. travaux`.
- An **adjective** is given in the masculine singular, with the feminine when
  it is not simply `-e` (`beau / belle`, `vieux / vieille`, `blanc /
  blanche`) and with the form it takes before a vowel (`bel homme`, `vieil
  ami`, `nouvel an`).

In a **video** the line is plain text: `venir venir · pres. viens vyẽ ·
p.p. venu venü · to come (aux. être; fut. viendrai vyẽdré)`, and a form of
the verb in the chunk first, with the entry in brackets after it — `vint vẽ
came (venir venir · pres. viens vyẽ · …)`; a noun as `livre livr book, m.`;
entries separated by `;`. French inside `voc` is fine. In a **book** the line
uses four macros and nothing else: `\dw{fa}{rom} gloss` ·
`\vb{inf}{rom}{pres}{rom}{p.p.}{rom}{meaning}` · `\bw{base}{rom}{meaning}` ·
`\pw{fa}` — plus `\textit`, `\emph`, `\nobreak`. **Every** verb gets a `\vb`,
no exceptions.

The gloss editor's sources sidebar, in the reader and in the player, now
proposes this entry from the dictionary for a verb it recognises — the
three forms with their sounds, the auxiliary, an irregular *nous* form and
an irregular future, all read from Wiktionary's conjugation table. It is a
**draft for you to correct**. Its sounds are Wiktionary's pronunciations
written into this file's scheme by rule: they follow the scheme, and they
say what Wiktionary says — where it gives `aurai` as /ɔ.ʁe/ the draft has
`òré`. Its meaning is a dictionary's first sense rather than the text's. It
takes a verb as pronominal only where the chunk shows the pronoun — `se`,
`s'`, or `me`, `te`, `nous`, `vous` agreeing with the subject (`je me lève`,
not `il me regarde`) — and then gives the pronominal verb, *aux. être* and
a reflexive sense; `il s'en va` is *s'en aller*. Where Wiktionary lists two
forms (`paye` and `paie`, `assois` and `assieds`) it offers the first. It
never writes the *here* note for a form that is none of the three: that is
yours to add. Correct it before it is saved; where it could not fill a slot,
the button says which.

**A verbal locution the chunk makes** — `j'ai peur`, `il fait attention`,
and the negation is no obstacle (`je n'ai pas peur`) — is now recognised as
the locution it is: the verb comes with its seventh argument **already
empty**, the row names the `\bw` still to add (*bw for peur after it: to be
afraid*), and a **button of its own**, headed *verbal locution*, puts the
pair in as the one entry this file asks for —
`\vb{avoir}{avwar}{ai}{é}{eu}{ü}{}\bw{peur}{peur}{to be afraid}`, the `\bw`
run straight onto the `\vb`, and in a video the locution whole, `avoir peur
avwar peur to be afraid (avoir avwar · pres. ai é · p.p. eu ü)`. The noun's
sound is the noun's own pronunciation respelt, and the whole one is the two
said in a row; where either is missing the slot stays empty. It is found
only where the noun stands right after the verb in the same chunk and the
dictionary has the pair as a verb page of its own; a locution it has not got
comes as the plain verb with its own meaning, and emptying that is yours.

The meaning is what the gloss language is for; the labels around it are not.
*pres.* and *p.p.* are printed by the edition itself — the same two words in
every French book, out of the registry — so leave them, and `aux.`, `nous`,
`fut.`, the `m.` and the `f.`, as they are written above whatever the
glosses are in. Where the gloss language is French, the meaning is a
**definition** and not a translation: commoner words than the headword, and
never a word of the headword's own family. `docs/lang/en.md` sets that case
out in full; it belongs to no one language.

A word transparent from the reader's own language earns a shorter entry or
none, and which words those are is the gloss language's business rather than
English's. `nation`, `important` and `possible` say themselves to a reader of
English or Italian; a Turkish reader knows the ones Turkish borrowed
(`istasyon`, `şoför`, `pantolon`) and nothing else; a Japanese reader knows
none of them. And a word that only looks transparent is worth the full entry
precisely because the reader will not stop for it: `actuellement` is
*currently*, `librairie` is a bookshop, `sensible` is *sensitive*.

The repetition rule is Frank's own: a full entry the **first time** a word
appears, briefer or none on later appearances.

## Never gloss

These function words are already in dictionary form and never get a
vocabulary entry:

```
le la les l' un une des du au aux de d'
à en dans sur sous pour par avec sans chez vers entre
je tu il elle on nous vous ils elles
me te se moi toi lui leur y
ce c' cet cette ces ça cela
mon ma mes ton ta tes son sa ses notre nos votre vos leurs
et ou mais donc ni car que qu' qui quoi dont où si comme quand
ne n' pas plus très aussi bien alors ici là oui non
```

The list holds for the elided shapes too — `l'`, `d'`, `j'`, `n'`, `s'`,
`c'`, `m'`, `t'`, `qu'` are those same words. The one thing you may add is a
pointer saying which word an apostrophe is hiding (`qu'` for `que`, `s'` for
`si` before `il`, `l'` for `le` or `la`), and only the first time it appears.

## Chunking

A chunk is a sense group of roughly **2–6 words** — a verb with its object, a
noun with what qualifies it, a preposition with its noun: something a reader
hovers and that *means* something on its own. A very short sentence (`Oui.`,
`Bonjour !`) is one chunk; that is normal and not a fault. Chunks split at
spaces only, so a word carrying an apostrophe or a hyphen (`l'homme`,
`aujourd'hui`, `est-ce`, `dit-il`, `y a-t-il`) is one token and cannot be cut
in two.

Never split:

- a **negation from its verb**, and never let a boundary fall between the two
  halves of `ne … pas`: `il ne sait pas` is one chunk, never `il ne sait` +
  `pas`. The same for `ne … plus`, `ne … jamais`, `ne … que`, `ne … rien`.
  Where the object is long enough to make one chunk impossible, `ne` stays
  with its verb and the second half opens the next chunk, never the reverse;
- an **article or determiner from its noun**: `la maison`, `des livres`, `mon
  père`, `ce jour-là`;
- a **preposition from its noun**, contraction and all: `au marché`, `de la
  ville`, `chez lui`;
- a **subject pronoun from its verb**, upright or inverted: `je vais`, `elle
  dit`, `dit-il`, `est-ce que`, `y a-t-il`;
- a **clitic from its verb**: `je le lui donne`, `il l'a vu`, `il
  s'approche`, `donne-le-moi`;
- an **auxiliary from its participle**: `il a fait`, `elle est venue`, `nous
  avons dit`;
- a **fixed phrase**: `il y a`, `tout à coup`, `parce que`, `bien sûr`,
  `s'il vous plaît`, `c'est-à-dire`;
- and, the one that is French's own, a **liaison pair**: never end a chunk
  between two words a liaison joins (`les amis`, `vous avez`, `c'est un`,
  `deux ans`, `grand homme`). A chunk ending in `les` would have to write a
  `z` in its pronunciation line with nowhere to put it.
