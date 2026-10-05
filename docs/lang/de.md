# German — the annotation conventions

{{?new}}How a German sentence becomes a glossed line: what goes into each field and
how it is written. These rules bind both the reading editions and the video
captions; they are embedded whole into every prompt that asks for German
annotation, so they are written as instructions to the annotator.

Two of the field names are languages, and neither is a claim about one: `fa`
is the text in the target language — German here — and `en` is the gloss
beside it. They are the names Persian and English left behind from the days
when they were the only two languages the toolbox had, and they are the same
two keys in every book and every video. Which language the gloss is written
in is the book's or the video's own choice, `"gloss"` in `book.json` /
`video.json`, and English when the key is absent. This file is about German
as the language being **taught**: the examples below gloss into English
because they must gloss into something, and every rule that turns on the
gloss language says so.{{/new}}

## The text field

`fa` reproduces the source **verbatim**: same spelling, same capitals, same
ß, same punctuation, the source's own oddities included — a pre-1996
spelling, a Swiss one, a dialect form, an ASR slip in a caption. Chunks split
only at spaces; joined back with single spaces they must reproduce the
sentence exactly, and a machine checks that. **Never correct the text in
`fa`**{{?new}} — the correction goes in {{?video}}`note`{{/video}}{{?book}}the vocabulary
line{{/book}}{{/new}}.

German takes no marks: there are no vowel marks to write in, and so nothing to
take off again{{?book}}, which is why German has two passes and not three{{/book}}.
**A mark you add is an error, not extra precision**: no
stress marks, no length marks, no hyphen slipped into a compound to show its
parts (that belongs in `voc`), no `ae oe ue` for the umlauts, and no umlauts
put back into a source that writes `ae oe ue`.

**Capitals are spelling.** Every noun is written with one, and so is every
word used as a noun (`das Essen`, `etwas Neues`, `beim Schwimmen`, `das Für
und Wider`); the polite `Sie`, `Ihnen`, `Ihr` are capitalised and `du`,
`dich`, `dein` are not, unless the source is a letter that capitalises them.
Never lower-case a noun, and never capitalise a word the source writes small.
A capital is not emphasis, not a proper name and not a sign that the word
matters: it is how the word is spelt.

**ß and ss are spelling too.** The reformed orthography — babel's `ngerman`,
which the editions are set with — writes ß after a long vowel or a diphthong
(`Straße`, `heißen`, `groß`, `weiß`) and ss after a short one (`dass`,
`muss`, `Fluss`, `wissen`). Reproduce what is in front of you: a book printed
before 1996 has `daß`, `muß`, `Fluß`; a Swiss source has no ß at all
(`Strasse`, `heissen`); a line set in capitals has `STRASSE`. Never normalise
in either direction — the modern spelling, where it is worth knowing, is said
in {{?video}}`note` or in {{/video}}the vocabulary line.

Everything else the source prints stays as printed: the German quotation
marks (`„…“`, `»…«`), the comma before a subordinate clause, the hyphen of
`Kfz-Werkstatt`, the apostrophe of `geht's`, the space inside `z. B.`, the
decimal comma of `3,5` and the full stop of `1.000`.

{{?studio}}German has no character range of its own in the registry and could not be
given one: it is written in the alphabet the toolbox's own prose is written
in. So nothing detects a run of German — and where the glosses are in
another Latin-script language, a capitalised German noun standing in a
sentence of English or Italian or Turkish reads as a proper name rather than
as a foreign word. Wherever the format asks you to mark the target text (a
studio document's `[…]{tl}` mark), mark every German run; in a book chunk or
a video chunk `fa` is German by definition and needs no mark.{{/studio}}

## Reading

This language has no reading field.

## Transliteration

{{?classic}}`tr` is a **pronunciation line, given only where the spelling misleads**, and
it may be omitted — most chunks need none. German says most of what it
writes; what it does not show is how long a vowel is, which of the two *ch*
sounds is meant, where the stress falls, and that a final *-er* is a vowel.

When you give a line, respell the **whole chunk**, never one word out of it,
in **small letters** — the line is sound and not spelling, and a capital in
it would be read as stress. Every letter not in the lists below keeps its
ordinary German value.

It is one scheme for every German edition whatever the glosses are written
in: it is built on German's own letters, and the English words a symbol is
explained by below (*sofa*, *measure*) are there to fix a sound, not to say
who is reading. Never respell the line in the gloss language's orthography.

The two marks:

| mark | means | example |
|---|---|---|
| `:` after a vowel | the vowel is long | `schta:t` *Staat* against `schtat` *Stadt*; `'o:fen` *Ofen* against `'ofen` *offen* |
| `'` before a syllable | the stress falls there | `be'zu:xen` *besuchen*, `ü:ba'zetsen` *übersetzen* |

The letters that change:

- **`ch`** is **`x`** after a, o, u, au (`bax` *Bach*, `bu:x` *Buch*,
  `'koxen` *kochen*, `raux` *Rauch*) and **`ç`** everywhere else — after e,
  i, ä, ö, ü, ei, eu, after a consonant, and always in `-chen` (`iç` *ich*,
  `milç` *Milch*, `'mä:tçen` *Mädchen*, `'bü:ça` *Bücher*). A real German x
  is written `ks` (`'taksi` *Taxi*), so an `x` in the line is always the
  *Bach* sound. Final `-ig` is `iç`: `'kö:niç` *König*, `'riçtiç` *richtig*.
- A **doubled consonant is written single** (`'ofen` *offen*, `'vasa`
  *Wasser*, `'häte` *hätte*): the doubling in German spelling is there to say
  the vowel before it is short, and the line says that already by leaving the
  colon off — `'ofen` *offen* against `'o:fen` *Ofen*.
- **`v`** is `f` (`'fa:ta` *Vater*, `fi:l` *viel*), except in loanwords where
  it stays `v` (`'va:ze` *Vase*, `no'vemba` *November*); **`w`** is `v`
  (`'vasa` *Wasser*); **`z`** and **`tz`** are `ts` (`tsait` *Zeit*,
  `'zetsen` *setzen*).
- **`s`** before a vowel is voiced and written `z` (`'zone` *Sonne*,
  `'ze:en` *sehen*); `s`, `ss` and `ß` elsewhere are `s` (`'schtra:se`
  *Straße*, `haus` *Haus*). The line does not keep the ß; `fa` always does.
- **`st`** and **`sp`** at the start of a word or of a stem are `scht` and
  `schp` (`schta:t` *Staat*, `'schpi:len` *spielen*, `fa'schte:en`
  *verstehen*); `sch` stays `sch`; **`ž`** is the *s* of *measure*, for the
  words German took from French (`ga'ra:že` *Garage*, `žurna'list`
  *Journalist*).
- A final **`b`, `d`, `g`** hardens to `p`, `t`, `k`: `ta:k` *Tag*, `ba:t`
  *Bad*, `gelp` *gelb*, `unt` *und* — which is why *Rad* and *Rat* are both
  `ra:t`.
- A final **`-er`** is the dark vowel of English *sofa* and is written `a`:
  `'fa:ta` *Vater*, `'kinda` *Kinder*, `'a:ba` *aber*; the prefix `ver-` is
  `fa` (`fa'schte:en`). A final `-e` stays `e` (`'blu:me` *Blume*).
- **`ei`** is `ai` (`tsait` *Zeit*), **`ie`** is `i:` (`'li:ben` *lieben*),
  **`eu`** and **`äu`** are `oy` (`'hoyte` *heute*, `'boyme` *Bäume*); an
  **`h`** after a vowel is silent and only says the vowel is long (`tsa:n`
  *Zahn*, `'ge:en` *gehen*); **`ng`** is one sound with no g after it
  (`'zingen` *singen*).{{/classic}}{{?ipa}}`tr` is the pronunciation in **IPA**: broad (phonemic), for standard
German, with no slashes and no square brackets round it, and **given only where
the spelling misleads**; it may be omitted — most chunks need none. German says
most of what it writes; what it does not show is how long a vowel is, which of
the two *ch* sounds is meant, where the stress falls, and that a final *-er* is a
vowel.

When you give a line, write the **whole chunk**, never one word out of it, in
small letters — a capital would be read as a symbol. It is one scheme for every
German edition whatever the glosses are written in. `ː` after a vowel says it is
long (`ʃtaːt` *Staat* against `ʃtat` *Stadt*; `ˈoːfən` *Ofen* against `ˈɔfən`
*offen*), and `ˈ` before a syllable says the stress falls there (`bəˈzuːxən`
*besuchen*, `yːbɐˈzɛtsən` *übersetzen*); a word of one syllable carries no stress
mark. The letters and the sounds the spelling hides:

- **`ch`** is `x` after a, o, u, au (`bax` *Bach*, `buːx` *Buch*, `ˈkɔxən`
  *kochen*, `ʁaʊx` *Rauch*) and `ç` everywhere else — after e, i, ä, ö, ü, ei,
  eu, after a consonant, and always in `-chen` (`ɪç` *ich*, `mɪlç` *Milch*,
  `ˈmɛːtçən` *Mädchen*, `ˈbyːçɐ` *Bücher*). A real German x is `ks` (`ˈtaksi`
  *Taxi*). Final `-ig` is `ɪç`: `ˈkøːnɪç` *König*, `ˈʁɪçtɪç` *richtig*.
- A **doubled consonant is written single** (`ˈɔfən` *offen*, `ˈvasɐ`
  *Wasser*): the doubling in German spelling is there to say the vowel before it
  is short, and the line says that already by leaving the length mark off.
- **`v`** is `f` (`ˈfaːtɐ` *Vater*, `fiːl` *viel*), except in loanwords where it
  stays `v` (`ˈvaːzə` *Vase*); **`w`** is `v` (`ˈvasɐ` *Wasser*); **`z`** and
  **`tz`** are `ts` (`tsaɪt` *Zeit*, `ˈzɛtsən` *setzen*).
- **`s`** before a vowel is voiced and written `z` (`ˈzɔnə` *Sonne*, `ˈzeːən`
  *sehen*); `s`, `ss` and `ß` elsewhere are `s` (`ˈʃtʁaːsə` *Straße*, `haʊs`
  *Haus*). The line does not keep the ß; `fa` always does.
- **`st`** and **`sp`** at the start of a word or of a stem are `ʃt` and `ʃp`
  (`ʃtaːt` *Staat*, `ˈʃpiːlən` *spielen*, `fɛɐˈʃteːən` *verstehen*); `sch` is
  `ʃ`; **`ʒ`** is the *s* of *measure*, for the words German took from French
  (`gaˈʁaːʒə` *Garage*, `ʒʊʁnaˈlɪst` *Journalist*).
- A final **`b`, `d`, `g`** hardens to `p`, `t`, `k`: `taːk` *Tag*, `baːt` *Bad*,
  `gɛlp` *gelb*, `ʊnt` *und* — which is why *Rad* and *Rat* are both `ʁaːt`.
- **`r`** is `ʁ` before a vowel and `ɐ` after a vowel or at the end of a word,
  and a final **`-er`** is `ɐ`: `ˈfaːtɐ` *Vater*, `ˈkɪndɐ` *Kinder*, `ˈaːbɐ`
  *aber*, `uːɐ` *Uhr*; the prefix `ver-` is `fɛɐ` (`fɛɐˈʃteːən`). A final `-e` is
  `ə` (`ˈbluːmə` *Blume*), and so is the vowel of `-en` (`ˈmaxən` *machen*).
- **`ei`** is `aɪ` (`tsaɪt` *Zeit*), **`ie`** is `iː` (`ˈliːbən` *lieben*),
  **`eu`** and **`äu`** are `ɔʏ` (`ˈhɔʏtə` *heute*, `ˈbɔʏmə` *Bäume*); an **`h`**
  after a vowel is silent and only says the vowel is long (`tsaːn` *Zahn*,
  `ˈgeːən` *gehen*); **`ng`** is one sound, `ŋ`, with no g after it (`ˈzɪŋən`
  *singen*).{{/ipa}}

**Give a line** for: a vowel length the sense turns on (*Stadt* / *Staat*,
*Ofen* / *offen*); any word with a `ch` — *ich* and *nicht* included, the
line being where the reader is told which of the two sounds it is, and the
digraph `sch` not being one; a stress that is not on the first syllable
({{?classic}}`bäke'rai` *Bäckerei*, `ja:r'hundat` *Jahrhundert*, `univerzi'tä:t`
*Universität*{{/classic}}{{?ipa}}`bɛkəˈʁaɪ` *Bäckerei*, `jaːɐˈhʊndɐt` *Jahrhundert*,
`univɛʁziˈtɛːt` *Universität*{{/ipa}}); **every verb with a prefix, the first time it
appears**, because the stress is the whole difference between the two kinds
({{?classic}}`'umfa:ren` *umfahren*, to run over, against `um'fa:ren`, to drive
round{{/classic}}{{?ipa}}`ˈʊmfaːʁən` *umfahren*, to run over, against `ʊmˈfaːʁən`, to drive
round{{/ipa}}); the `-tion` ending ({{?classic}}`na'tsio:n`{{/classic}}{{?ipa}}`naˈtsjoːn`{{/ipa}} *Nation*); and a
loanword that keeps a foreign sound ({{?classic}}`schef` *Chef*, `kom'pju:ta`
*Computer*{{/classic}}{{?ipa}}`ʃɛf` *Chef*, `kɔmˈpjuːtɐ` *Computer*{{/ipa}}).

**Leave it empty** for a chunk whose spelling already says it — `der Mann`,
`im Garten`, `und dann` — which is most chunks. A chunk holding a `ch` is
never one of them, common as the word may be: `ich habe` earns
{{?classic}}`iç 'ha:be`{{/classic}}{{?ipa}}`ɪç ˈhaːbə`{{/ipa}}. A line given for one word and half a chunk is worse than none.

How much a spelling "already says" depends a little on who is reading it. A
book glossed in Japanese, Persian or Arabic is read by somebody with no
habits at all in this alphabet, and may reasonably give a line where a book
glossed in English or Italian would leave it empty. The scheme, the
whole-chunk rule and the list of things that always earn a line do not move
with the gloss language; only that margin does.

## Vocabulary

`voc` is written in the voice of the books' gloss blocks: headword + meaning,
with the grammar a learner needs to recognise the form. The pronunciation
slots of the macros are filled only where a pronunciation line would be given
at all; elsewhere they are left empty.

- A **verb** is given by its three principal parts — **infinitive,
  preterite, past participle**, in that order — because every other form is
  built from them: `geben`, `gab`, `gegeben`. The edition prints *pret.* and
  *p.p.* before the second and third, so never put another form into those
  slots. Weak verbs are regular and still get all three (`machen`, `machte`,
  `gemacht`): **every** verb gets a `\vb`, no exceptions.
- What the three do not show goes in **one parenthesis after the meaning**,
  items parted by `; `, in this order and these words, each **only where it
  is not the ordinary case**:
  - the **third person singular present**, where it is not the stem plus
    `-t` or `-et` — the vowel change of a strong verb: `er gibt`, `er nimmt`,
    `er fährt`; a separable verb's whole, `er fährt ab`. A modal changes it
    through the whole singular, so the first person goes there instead: `ich
    kann` (and so does *wissen*: `ich weiß`). Nothing for `er macht`, `er
    arbeitet`.
  - **`aux. sein`** where the perfect is made with *sein* (`ist gegangen`,
    `ist gefahren`), **`aux. haben/sein`** where it takes both; *haben* alone
    is the default and is never named.
  - the **case or the preposition** a verb governs, which is not guessable
    either: `+ dat.` (`helfen`), `auf + acc.` (`warten`), `über + acc.`
    (`sich freuen`). A plain accusative object is never named.

  `\vb{geben}{}{gab}{}{gegeben}{}{to give (er gibt)}`,
  `\vb{fahren}{}{fuhr}{}{gefahren}{}{to drive (er fährt; aux. sein)}`,
  `\vb{können}{}{konnte}{}{gekonnt}{}{to be able (ich kann)}`,
  `\vb{helfen}{}{half}{}{geholfen}{}{to help (er hilft; + dat.)}`.
- A **reflexive** verb carries its `sich` in the first slot and nowhere else:
  `\vb{sich freuen}{}{freute}{}{gefreut}{}{to be glad (über + acc.)}`.
- A **separable-prefix verb** is given whole, with the preterite as it stands
  in a clause: `\vb{aufstehen}{}{stand auf}{}{aufgestanden}{}{to get up (aux.
  sein)}`. An **inseparable** prefix (`be-`, `emp-`, `ent-`, `er-`, `ge-`,
  `miss-`, `ver-`, `zer-`) never separates and takes no *ge-* in the
  participle: `\vb{verstehen}{}{verstand}{}{verstanden}{}{to understand}`.
  What to do when the sentence has pulled a separable verb apart is under
  **Chunking**, and it matters more than anything else on this page.
- A **noun** is given in the nominative singular, **with its article and its
  plural**, the article and the plural inside the headword slot: `\dw{der Tisch,
  -e}{} table`; `\dw{die Frau, -en}{} woman`; `\dw{das Fenster, -}{} window`.
  Write the plural out in full where it takes an umlaut (`das Buch, Bücher`;
  `die Mutter, Mütter`). A weak masculine takes `-n` in every case but the
  nominative singular, and that is worth saying: `\dw{der Student, -en}{}
  student; here \pw{den Studenten}, weak masculine`.
- **Case** is carried by the article and the endings, and the line always
  shows the nominative singular whatever case the text has. Where the form in
  the text is not that, name the case and what put it there, after the entry:
  `\dw{der Mann, Männer}{} man; here \pw{dem Mann}, dat. after \pw{mit}`;
  `\dw{das Haus, Häuser}{} house; here \pw{des Hauses}, gen.`. An adjective
  ending is a case mark and not part of the word, so the headword is the bare
  adjective: `\dw{groß}{} big; here \pw{großen}`.
- A **preposition** that is not on the *Never gloss* list below is glossed with
  the case it takes: `\dw{wegen}{} because of (+ gen.)`, `\dw{trotz}{} despite
  (+ gen.)`, `\dw{außer}{} except (+ dat.)`. One that is on the list gets no
  entry of its own: the noun it governs says the case and what put it there
  (the bullet above) and, for the nine that take either case, which one:
  `\dw{der Garten, Gärten}{} garden; here \pw{im Garten} = \pw{in dem}, dat.
  after \pw{in}, where it is a place` (acc. where it is motion into). A
  contraction is spelled out the same way: `zum = zu dem`, `ins = in das`.
- A **compound** is broken into the words it is made of, because a dictionary
  may not have the compound itself: `\dw{die Geschwindigkeitsbegrenzung,
  -en}{} speed limit \bw{Geschwindigkeit}{}{speed}
  \bw{Begrenzung}{}{limit}`. The linking `-s-` is named as a link, never as a
  genitive.
- A **modal particle** — `doch`, `mal`, `ja`, `eben`, `halt`, `wohl`,
  `schon` — is glossed by what it is doing and not by a dictionary word:
  `\dw{doch}{} particle, contradicts what was just said`; `\dw{mal}{}
  particle, softens an order`.
- Name what was stripped or added: the plural, the diminutive `-chen` /
  `-lein` (with the umlaut and the neuter gender it brings: `das Brötchen`
  from `das Brot`), the comparative `-er` and superlative `-st` (`\dw{groß}{}
  big; here \pw{größer}, comparative`), the `zu` of an infinitive, the adverb
  that is simply the bare adjective (`schnell`).
- The line uses the four macros `\dw` `\vb` `\bw` `\pw` (plus `\textit`,
  `\emph`, `\nobreak`), as the Persian editions do, and its entries are
  parted by `; `: `\vb` for every verb, `\dw` for every other headword — the
  article and the plural go inside the headword slot (`\dw{der Tisch, -e}{}
  table`) — `\bw` for the parts of a compound, and `\pw` for a German word
  quoted inside a remark in the gloss language (`\pw{auf} at the end of the
  clause`).
- A form in the text that is none of the three the `\vb` prints, nor one its
  parenthesis names, is named after the entry, outside it, with what it is:
  `\vb{geben}{}{gab}{}{gegeben}{}{to give (er gibt)}; here \pw{gaben}, pret. plural`.

One equivalent in the gloss language rather than a string of synonyms; no
etymologies; **an empty `voc` is the right answer** for a chunk needing
nothing. The repetition rule is Frank's own: a full entry the **first time**
a word appears, briefer or none on later appearances.

The meaning is what the gloss language is for; the labels around it are not.
*pret.* and *p.p.* are printed by the edition itself — the same two words in
every German book, out of the registry — so leave them, and `aux. sein`,
`+ dat.`, `+ acc.`, `+ gen.`, the article and the plural, as they are
written above whatever the glosses are in: they name German's own cases in
the abbreviations every grammar of German uses, and a line that translated
them would be a convention of its own book. Where the
gloss language is German, the meaning is a **definition** and not a
translation: commoner words than the headword, and never one of its own
compounds — which in German is the trap, since the language will always
offer you one. `docs/lang/en.md` sets that case out in full; it belongs to
no one language.

Which words the reader already owns turns on the gloss language as well, and
German's case is the one to be careful with: a reader of English or Dutch
gets `Haus`, `Wasser`, `trinken`, `Hand` free, and is walked straight into
the ones that only look free — `bekommen` is *to get*, `Gift` is *poison*,
`also` is *so*, `bald` is *soon*, `Rat` is *advice*. Those earn a full entry
precisely because that reader will not stop for them, and are ordinary
vocabulary for a reader of Turkish or Japanese, who was never tempted.

## Never gloss

These function words, already in dictionary form, never get a vocabulary
entry:

```
der die das den dem des ein eine einen einem einer eines kein keine
ich du er sie es wir ihr mich dich uns euch mir dir ihm ihnen sich
mein dein sein unser euer
in an auf aus bei mit nach von zu vor über unter neben zwischen hinter
für ohne um durch gegen seit
im am zum zur ins ans vom beim
und oder aber denn sondern dass weil wenn als ob wie
nicht nein auch nur noch sehr hier dort jetzt dann so
```

The verbs `sein`, `haben` and `werden` are deliberately **not** on the list —
the `sein` above is the possessive *his* — because `ist`, `war`, `hat`,
`hatte`, `wird`, `wurde` are irregular enough to be worth one naming (`wurde ·
werden, pret.`), after which the repetition rule takes over. A word from the
list doing something other than its usual work is named once too: `zu` before
an infinitive, `als` meaning *than*, `sie` where it is the polite `Sie` and
not *she* or *they*.

## Chunking

A chunk is a sense group of roughly **2–6 words** — a verb with its object,
a noun with what qualifies it, a preposition with its noun: something a
reader hovers and that *means* something on its own. Never split an
**article from its noun**, nor the adjectives standing between them (`der
alte Mann`, `ein schönes Haus`); a **preposition from the noun phrase it
governs**, contraction included (`mit dem Fahrrad`, `zum Bahnhof`); a
**negation from what it negates** (`nicht gesehen`, `kein Geld`); a
**reflexive pronoun from its verb** (`freut sich`); or `zu` **from its
infinitive** (`zu gehen`). A compound is one word in German and stays one
(`Straßenbahn`). A very short sentence (`Ja.`, `Komm!`) is one chunk; that is
normal and not a fault. The comma before a subordinate clause is the best
boundary German gives you, and the verb that ends such a clause closes its
chunk: break after `…, weil er müde war`, never before `war`.

German's own difficulty is that it **splits a verb in two and puts the halves
at opposite ends of the clause**: `steht … auf`, `hat … gesehen`, `will …
mitkommen`. No chunking can hold those together, so the gloss has to, and a
chunk boundary must never be allowed to hide the connection. The rule is the
same in both directions — the full entry goes with the half that carries the
meaning, the other half gets a pointer to it:

- **A separable prefix.** The meaning is settled by the prefix, but the
  reader meets the finite verb first, so the entry goes there and says what
  is still to come: at `steht`, `\vb{aufstehen}{}{stand auf}{}{aufgestanden}{}{to
  get up (aux. sein)}, \pw{auf} at the end of the clause`. At the `auf`
  itself, a pointer and not a second entry: `\pw{auf} — the second half of
  \pw{aufstehen}, above`. **Never** gloss a stranded prefix as the
  preposition (`auf` as *on*, `an` as *at*, `aus` as *out of*): that is the
  one mistake that leaves a learner reading a sentence that cannot mean
  anything.
- **A perfect or a modal.** Here the meaning is at the end, in the participle
  or the infinitive, so the entry goes there — `gesehen`:
  `\vb{sehen}{}{sah}{}{gesehen}{}{to see}` — and the auxiliary is named where
  it stands: `\dw{hat}{} \pw{haben}, makes the perfect with \pw{gesehen} below`.

## Example

One sentence of German, answered: its chunks as they stand in the list of your
answer. The `en` of each chunk says only what that chunk says, in the order of
the German.

```json
{"chunks": [
  {"fa": "Wir sind", "voc": "\\dw{sind}{} \\pw{sein}, makes the perfect with \\pw{gefahren} below", "en": "we are"},
  {"fa": "mit dem Zug", "voc": "\\dw{der Zug, Züge}{} train; here \\pw{dem Zug}, dat. after \\pw{mit}", "en": "with the train"},
  {"fa": "nach München", "tr": "{{?classic}}nax 'münçen{{/classic}}{{?ipa}}nax ˈmʏnçən{{/ipa}}", "en": "to Munich"},
  {"fa": "gefahren.", "voc": "\\vb{fahren}{}{fuhr}{}{gefahren}{}{to drive, to travel (er fährt; aux. sein)}", "en": "travelled."}
]}
```

Notice: read in a row the `en` lines keep the German order — *we are | with the
train | to Munich | travelled* — stiff, and right: the verb's two halves stand where
German puts them, the full entry goes with the participle that carries the
meaning, and the auxiliary is only named where it stands. `mit dem Zug` names the
case and what put it there; the sound slots of the `\vb` stay empty; and only
the third chunk has a `tr`, for its `ch`, the spelling saying all there is to say
in the others.

{{?note}}No speaker has reviewed this example yet.{{/note}}
