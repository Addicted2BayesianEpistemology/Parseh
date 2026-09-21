# Turkish — the annotation conventions

How a Turkish sentence becomes a glossed line: what goes into each field and
how it is written. These rules bind both the reading editions and the video
captions; they are embedded whole into every prompt that asks for Turkish
annotation, so they are written as instructions to the annotator.

Two of the field names are languages, and neither is a claim about one: `fa`
is the text in the target language — Turkish here — and `en` is the gloss
beside it. They are the names Persian and English left behind from the days
when they were the only two languages the toolbox had, and they are the same
two keys in every book and every video. Which language the gloss is written
in is the book's or the video's own choice, `"gloss"` in `book.json` /
`video.json`, and English when the key is absent. This file is about Turkish
as the language being **taught**: the examples below gloss into English
because they must gloss into something, and every rule that turns on the
gloss language says so.

## The text field

`fa` reproduces the source **verbatim**: same spelling, same punctuation, the
source's own oddities included — a dialect form, an Ottoman spelling, an ASR
slip in a caption. Chunks split only at spaces; joined back with single spaces
they must reproduce the sentence exactly, and a machine checks that. **Never
correct the text in `fa`** — the correction goes in `note` (videos) or in the
vocabulary line (books).

Turkish is plain text: there is nothing to write in and nothing to strip. One
pass gives the sentence, one gives the chunks, and there is no bare pass
because the text is already bare.

**The dotted and the dotless i are different letters.** `i`/`İ` and `ı`/`I`
are four letters, not two, and they tell words apart: `ılık` lukewarm against
`ilik` marrow, `sıkı` tight against `siki`. Copy them exactly, and **never
case-fold Turkish**: `i` uppercases to `İ` and `I` lowercases to `ı`, so
anything that turns `için` into `IÇIN` has changed the word. The same care
goes to `ç ğ ş ö ü` and to the circumflex — write `kâğıt` where the source
writes `kâğıt` and `kagit` where it writes `kagit`.

A caption stripped of its Turkish letters (`Turkce ogrenmek cok guzel`) is
**kept as it is** and reported in `note`; do not put the diacritics back in
`fa`. So are:

- the apostrophe a proper noun takes before its ending: `İstanbul'da`,
  `Ankara'ya`, `Atatürk'ün`, `2020'de`;
- the circumflex where the source writes it and only there: `hâlâ`, `kâr`,
  `millî`;
- Turkish's own figures — the ordinal dot (`3. bölüm`), the decimal comma
  (`3,5`), the thousands dot (`1.000`);
- a particle written apart because Turkish writes it apart, however it is
  said: `gidiyor mu`, `ben de`, `yapabilir misin`.

## Reading

This language has no reading field: the `kana` key is ignored where it
appears, and nothing asks for one.

## Transliteration

`tr` is a **pronunciation aid, given only where it helps**, and it may be left
empty — most chunks need none, and `require_tr` is false for Turkish. The
spelling is phonemic: one letter, one sound. **Never respell the alphabet.**
`c` is the *j* of *jam*, `ç` the *ch* of *church*, `ş` the *sh* of *ship*, `j`
the *s* of *measure*, `ı` the back unrounded vowel English has no letter for
(roughly the second vowel of *open*), `ö` and `ü` the German ones; and a final
`b d c g` is already written `p t ç k` where it is said so (`kitap`, `ağaç`).
A reader learns that once, and a `tr` that writes it out again is noise. The
English and German words those letters are named by are there to fix a sound
for whoever is writing the line; the letters themselves are Turkish and the
scheme below is the same in every Turkish edition, whatever the glosses are
written in.

There are three cases, and only three. When one of them fires, write the
**whole chunk**, not the one word in it:

1. **`ğ`**, which is never a consonant. After `a ı o u` it dissolves and
   lengthens the vowel: `dağ` → *dā*, `yağmur` → *yāmur*, `oğlu` → *ōlu*,
   `sağ` → *sā*. After `e i` it is a `y`: `değil` → *deyil*, `eğer` →
   *eyer*, `iğne` → *iyne*. After `ö ü` it lengthens again: `öğle` → *ȫle*,
   `düğün` → *dǖn* — which is what the mark is for, since `dün` is
   *yesterday*.
2. **A long vowel the spelling does not show**, which means an Arabic or
   Persian loan. The circumflex marks it where the source writes one, and
   modern Turkish often writes none: `kâr` → *kār* profit against `kar`
   snow, `hâlâ` → *hālā* still against `hala` aunt, `âdet` → *ādet* custom
   against `adet` number, `millî` → *millī*, `usûl` → *usūl*. After `k`, `g`
   or `l` that long vowel also softens the consonant — the *k* of *cure*, not
   of *car* — and the macron is the only mark given for it.
3. **Stress that is not on the last syllable.** Turkish stresses the last
   syllable and marks nothing; where it does not, `ˈ` goes immediately before
   the stressed syllable.
   - The negative `-ma/-me` and the impotential `-ama/-eme` throw the stress
     back onto the syllable in front of them: `ˈgelme` do not come against
     `gelˈme` coming; `ˈgelmiyor`, `yaˈpamam`.
   - `-ken`, `-ce/-ca`, `-le/-la`, `-ki`, and the separately written
     `mi/mı/mu/mü` and `de/da`, never take it: `geˈlirken`, `gelˈdi mi`,
     `ˈben de`.
   - Place names, and a short closed list of adverbs, are stressed early:
     `ˈAnkara`, `İsˈtanbul`, `ˈBodrum`, `ˈyalnız`, `ˈşimdi`, `ˈönce`,
     `ˈsonra`, `ˈçünkü`, `ˈbelki`, `ˈnasıl`, `ˈbazen`.

Every symbol the scheme uses, and there are no others:

| written | is |
|---|---|
| `ā ē ī ō ū`, and `ȫ ǖ` | a long vowel |
| `ä` | the open `e` of `gel`, `ben` — the `e` before a syllable-final `l m n r` |
| `ˈ` | immediately before the stressed syllable (U+02C8, **not** an apostrophe) |

`ä` is never on its own a reason to write a `tr`: every Turkish speaker opens
that `e` and no learner is misled by it. Write it wherever it falls inside a
chunk you are giving a `tr` for anyway, and nowhere else. Capitals stay as the
text has them and the orthographic apostrophe is dropped: `İstanbul'da` is
*İsˈtanbulda*.

## Vocabulary

`voc` is written in the voice of the books' gloss blocks: headword +
segmentation + meaning. **For Turkish the middle slot is a segmentation, not a
pronunciation.** The spelling already says how a word sounds; what a reader
cannot do is find the seams in a word that is a whole clause. Anything about
sound belongs in `tr` and nowhere else.

### How a word is broken up

The separator is the **hyphen**, and the rule is absolute: **push the pieces
together with nothing between them and you have the word exactly as the text
spells it.** A segmentation that does not join back is wrong.

```
evlerimizden        ev-ler-imiz-den
bahçedeki           bahçe-de-ki
okuyordu            oku-yor-du
gidebileceğimizi    gid-e-bil-eceğ-imiz-i
```

- **The harmony vowel belongs to the suffix that carries it.** A suffix is
  written in the shape it actually has, never in a citation shape and never
  with a capital archiphoneme: `ev-ler` but `kız-lar`; `ev-de`, `okul-da`,
  `kitap-ta`; `ev-i`, `kız-ı`, `göz-ü`, `okul-u`.
- **A buffer letter travels with the suffix it introduces**, so that every
  piece is one morpheme and not a fragment: `kapı-yı` (not `kapı-y-ı`),
  `araba-sı`, `su-yu`, `alt-ı-nda`, `el-i-nde-ki`.
- **A compound written solid is cut at its seam** as well: `buz-dolab-ı`,
  `hanım-el-i`. Nothing else is cut — never at a mere syllable boundary.
- **A proper noun's apostrophe is already the seam**: `İstanbul'da` gets no
  hyphen in front of `da`, and the rest is segmented as usual —
  `İstanbul'da-ki`.
- **Words written apart stay apart**: `mi/mı/mu/mü`, `de/da`, `ile`, `bile`
  are their own words and never join a segmentation.

### What the meaning says

After the segmentation, name the pieces **in the same order and the same
number the hyphens gave them**, joined by `+`. The stem's meaning comes first,
and the dictionary form in front of it whenever the stem changed shape:

```
evlerimizden   ev-ler-imiz-den   house + plural + our + from
bahçedeki      bahçe-de-ki       garden + in + which is
ağacın         ağac-ın           ağaç tree + of
altında        alt-ı-nda         alt underside + its + in
kitabını       kitab-ı-nı        kitap book + his + object
```

Use the gloss language's own word where a suffix has one and the plain
grammatical name where it has not — the everyday word, never the
grammarian's, in whatever language that is (*object*, not *accusative*;
*oggetto*, not *accusativo*). The table below names them in English because
this file glosses into English; the ones that recur:

| suffix | named |
|---|---|
| `-ler/-lar` | plural |
| `-i/-ı/-u/-ü` | object *(say object, not accusative)* |
| `-e/-a` · `-de/-da/-te/-ta` · `-den/-dan/-ten/-tan` · `-in/-ın/-un/-ün` | to · in · from · of |
| `-im -in -i -imiz -iniz -leri` | my, your, his, our, your, their |
| `-le/-la` · `-li` · `-siz` · `-lik` · `-ci` · `-ce` | with · with · without · -ness · one who · in the manner of |
| `-ki` | which is |
| `-me/-ma` the negative · `-ebil/-abil` | not · can |
| `-yor` · `-di/-dı` · `-miş/-mış` · `-ecek/-acak` · `-ir/-ar` · `-se/-sa` | -ing · past · past, reported · will · aorist · if |
| `-im -sin -iz -siniz -ler` on a verb | I, you, we, you, they |
| `-mek/-mak` · `-me/-ma` the verbal noun | to … · …ing |

The two `-me/-ma` are homographs and are told apart by the stress, which is
the pair the how-to page shows: `ˈgelme` do not come, `gelˈme` coming.

**Naming a suffix in words** — as opposed to writing it inside a segmentation
— give **all its written shapes, slash-separated, the first time it appears**
in a book or a video, and the shape in the word ever after:
`-den/-dan/-ten/-tan from`, then simply `from`. That is the toolbox's
repetition rule applied to morphology, and in Turkish it is where the rule
earns most.

**A stem that changed shape is always followed by its dictionary form**,
because that is the one thing a learner cannot look up:

- final `p t ç k` voices before a vowel — `kitap` → `kitab-ı`, `ağaç` →
  `ağac-ın`, `renk` → `reng-i`, `bebek` → `bebeğ-i`, `git-` → `gid-er`;
- a two-syllable stem with `ı i u ü` in its second syllable drops it —
  `burun` → `burn-u`, `ağız` → `ağz-ı`, `şehir` → `şehr-i`, `isim` →
  `ism-i`, `oğul` → `oğl-u`;
- `su` and `ne` take a `y` — `su-yu`, `ne-yi`;
- the verbs `de-` and `ye-` become `di-` and `yi-` before `-yor` and
  `-ecek` — `di-yor`, `yi-yecek`.

### Verbs

**Every verb gets a `\vb`, no exceptions.** Its seven slots are, in this
order, **infinitive, present in *-iyor*, aorist**, each with its sound slot,
then the meaning. The three sound slots stay **empty**: the spelling says how
each form is said. The edition prints *pres.* and *aor.* before the second
and the third, so never put another form (a past, a bare stem) into those
slots.

```
\vb{gelmek}{}{geliyor}{}{gelir}{}{to come}
\vb{gitmek}{}{gidiyor}{}{gider}{}{to go}
\vb{demek}{}{diyor}{}{der}{}{to say (-e)}
\vb{bakmak}{}{bakıyor}{}{bakar}{}{to look at (-e)}
```

The infinitive is the `-mek/-mak` dictionary form. The other two are both the
**bare third person singular**. The present in *-iyor* is the form a reader
meets most and the one where a verb is hardest to see through — `demek` is
`diyor`, `yemek` `yiyor`, `aramak` `arıyor`, `oynamak` `oynuyor`,
`gülümsemek` `gülümsüyor`, and a final `t` voices in it (`gidiyor`,
`ediyor`). The aorist is there because its vowel is the one thing the
infinitive does not predict (`gelir` but `bakar`, `alır` but `olur`, `kalır`
but `yapar`).

**The second slot used to be the stem**, written in the shape it takes before
a vowel (`gid-`, `ed-`). It is gone, because that shape is wrong before a
consonant — `gitti`, `gitmiş`, the imperative `git!` — so a reader told
"stem gid-" built *gidti*; and in every other verb it was the infinitive less
`-mek`, which the page already prints. An entry still written that way is
a finding, and is corrected like any other.

**Government** is the one thing a Turkish verb carries that no form shows:
the case its complement takes, which is what a reader needs to parse the
clause. It goes in **one parenthesis after the meaning**, as the suffix in
its front-vowel shape — `(-e)`, `(-i)`, `(-den)`, `(-de)`, `(ile)` — and only
where it is not the plain object the gloss-language verb already leads the
reader to expect: always for `-e`, `-den`, `-de` and `ile`, and for `-i` only
where the gloss-language verb takes a preposition (`to wait for (-i)`, `to
look for (-i)`). `bakmak (-e)` is what separates `pencereye bakar`, *looks at
the window*, from `penceresinden bakar`, *looks out of his window*. The
dictionary knows one compound whose complement is a possessor, `farkında
olmak` *to be aware of*, and writes it `(-in)`, the genitive.

```
\vb{korkmak}{}{korkuyor}{}{korkar}{}{to be afraid of (-den)}
\vb{beklemek}{}{bekliyor}{}{bekler}{}{to wait for (-i)}
```

**The form the text actually has** is segmented at the end of the meaning
slot, after that parenthesis and a semicolon, in `\textit`, whenever it
carries more than one ending:

```
\vb{okumak}{}{okuyor}{}{okur}{}{to read; \textit{oku-yor-du} she was reading}
```

**A compound verb** — `etmek`, `olmak`, `yapmak`, `vermek` welded to a bare
noun — follows the Persian editions exactly: a `\vb` for the light verb with
an **empty seventh argument**, then a `\bw` for the word it carries, and the
government goes on the `\bw`, since it is the compound's. Never gloss the
light verb's own meaning.

```
\vb{etmek}{}{ediyor}{}{eder}{}{}\bw{teşekkür}{}{thanks (-e)}
\vb{olmak}{}{oluyor}{}{olur}{}{}\bw{mutlu}{}{happy}
```

The gloss editor's sources sidebar, in the reader and in the player, now
proposes this entry from the dictionary for a verb it recognises: the
aorist from the dictionary's head line, the present from its conjugation
table, the first equivalent of its first sense, and the government where the
dictionary tags that sense — which is seldom, 78 verbs in 2 559 (`bakmak`
-e, `korkmak` -den, `evlenmek` ile), so most of it is yours to add, and
`beklemek`'s `(-i)` always is. It stops there: the segmented form the text
has (`; \textit{…}`) is yours as well. It is a **draft for you to correct**:

- a homograph comes as two entries, each with its own forms — `yenmek` *to
  defeat*, `yener`, and `yenmek` *to be eaten*, `yenir` — and you keep the
  one the text means;
- the meaning is a dictionary's first sense, not the text's;
- for a compound it proposes the light verb's `\vb` with the empty meaning,
  and the row names the `\bw` still to add, with the compound's own
  meaning and government (*bw for teşekkür after it: to thank (-e)*). A
  **button of its own**, headed *compound verb*, puts the pair in as the one
  entry it is —
  `\vb{etmek}{}{ediyor}{}{eder}{}{}\bw{teşekkür}{}{to thank (-e)}`, the `\bw`
  run straight onto the `\vb` — and says in so many words that teşekkür
  etmek is one verb written in two words and not two entries; a video gets
  the compound whole, `teşekkür etmek to thank (-e) (etmek · pres. ediyor ·
  aor. eder)`. What it writes in the `\bw` is the **compound's** meaning,
  which is the one the dictionary's entry is for; an edition that would
  rather gloss the noun itself (`thanks (-e)`, as above) trims it there, as
  it trims every other draft this sidebar proposes. Nothing is romanised:
  both sound slots stay empty, and the segmentation is yours. It
  finds the compound only where the noun stands right before the verb in the
  same chunk, which is where the chunking rules put it;
- a derived verb the dictionary has only as a note on its base (`yapılmak`,
  *passive of yapmak*) comes as its infinitive alone, the forms and the
  meaning left to you — never with `yapar` under it;
- about one verb in twelve has no conjugation table in the dictionary
  (`ilerlemek`, `incelemek`, `hedeflemek`) and comes without its present,
  or without both forms.

Correct it before it is saved; where it could not fill a slot, the button
says which, and why where the dictionary contradicts itself (`hafifletmek`:
its head says `hafifletir`, its table `hafiflediyor`).

### Everything else

A **noun** is the dictionary form and one word of the gloss language; Turkish
has no gender, no article and one plural, so there is nothing else to carry.
A **postposition** is named with the case it governs: `göre · according to,
after -e`; `gibi · like, after the bare form`. An **adjective** is given as it
stands. A **proper noun** gets a line saying what it is: `Beyoğlu · a district
of İstanbul`. A **loanword the reader already owns** needs no more than one
naming — but which words those are is the gloss language's business, not
English's. `otobüs`, `tren` and `telefon` say themselves to a reader of
English, French or Italian; a Persian reader has the Arabic half of the
vocabulary instead (`kitap`, `hayat`, `insan`, `zaman`), which an English
reader has no way into at all, and a Japanese reader has neither. Gloss what
this book's reader cannot get, and let the rest go.

In a **video** the line is plain text and reads the way the book prints it:
`evlerimizden ev-ler-imiz-den ev house + plural + our + from`, a verb as
`bakmak · pres. bakıyor · aor. bakar · to look at (-e)`. In a **book** it uses
four macros and nothing else: `\dw{fa}{segmentation} gloss` ·
`\vb{inf}{}{pres}{}{aorist}{}{meaning}` · `\bw{base}{segmentation}{meaning}` ·
`\pw{fa}` — plus `\textit`, `\emph`, `\nobreak`.

One equivalent in the gloss language rather than a string of synonyms; no
etymologies; **an empty `voc` is the right answer** for a chunk needing
nothing. The repetition rule is Frank's own: a full entry the **first time** a
word appears, briefer or none on later appearances.

The meaning is what the gloss language is for; the labels around it are not.
*pres.* and *aor.* are printed by the edition itself — the same two words in
every Turkish book, out of the registry — so leave them, and the government
in brackets, as they are written above whatever the glosses are in. The
segmentation is not a meaning at all and never moves: the hyphens are
Turkish's own seams, and only the words naming the pieces after them are
written in the gloss language. Where that language is Turkish, the meaning
is a **definition** and not a translation: commoner words than the headword,
and never the headword with another suffix on it. `docs/lang/en.md` sets
that case out in full; it belongs to no one language.

## Never gloss

These function words, already in dictionary form, never get a vocabulary
entry:

```
ve ile ama fakat ancak veya ya hem
ki çünkü eğer ise de da mi mı mu mü
ben sen o biz siz onlar kendi bu şu
bir her hiç bazı bütün tüm
çok az daha en pek
için gibi kadar göre karşı doğru sonra önce
değil evet hayır
```

No **suffix** is on this list. A suffix is named inside the word it sits on,
every time that word is glossed, however often it has been met before.

## Chunking

A chunk is a sense group of roughly **2–5 words** — Turkish words are long,
and four of them can be a whole clause: something a reader hovers and that
*means* something on its own. The verb comes last, so a sentence usually ends
on its heaviest chunk. **End a chunk at a case-marked noun, at a converb
(`-ip`, `-erek`, `-ince`, `-dikten sonra`) or at the verb** — that is where
Turkish breathes.

Never split:

- **a word**, however long: `gidebileceğimizi` is a chunk on its own, and a
  one-word chunk is normal, not a fault;
- **a noun from the postposition that follows it**: `benim için`, `senin
  gibi`, `saat beşe kadar`, `ona göre`;
- **a genitive from what it possesses**: `ağacın altında`, `evin kapısı`,
  `Türkiye'nin başkenti` — two words, one construction;
- **an adjective, a number or `bir` from its noun**: `küçük bir kız`, `üç
  gün`, `bu ev`;
- **a participle or a relative clause from the noun it modifies**, where the
  two are adjacent and short: `bahçedeki ağaç`, `okuduğum kitap`, `gelen
  adam`;
- **a verb from what closes it**: the negation is inside the word, but the
  question particle, `değil`, `de/da`, an auxiliary and the noun of a
  compound are written apart and still belong to it — `gitti mi`, `güzel
  değil`, `gelmiş olabilir`, `yapmak istiyor`, `teşekkür ederim`.

A very short sentence (`Evet.`, `Gel!`, `Bilmiyorum.`) is one chunk; that is
normal.

Runs of Turkish are **marked** in the studio (`[word]{tl}`): Turkish has no
character range of its own in the registry — it is written in the alphabet
the toolbox's own prose is written in — so nothing detects a run of it, and
`ı ğ ş` aside, nothing tells it from Latin-script prose by eye either.
