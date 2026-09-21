# Hindi — the annotation conventions

How a Hindi sentence becomes a glossed line: what goes into each field and
how it is written. These rules bind both the reading editions and the video
captions; they are embedded whole into every prompt that asks for Hindi
annotation, so they are written as instructions to the annotator.

Two of the field names are languages, and neither is a claim about one: `fa`
is the text in the target language — Hindi here — and `en` is the gloss
beside it. They are the names Persian and English left behind from the days
when they were the only two languages the toolbox had, and they are the same
two keys in every book and every video. Which language the gloss is written
in is the book's or the video's own choice, `"gloss"` in `book.json` /
`video.json`, and English when the key is absent. This file is about Hindi
as the language being **taught**: the examples below gloss into English
because they must gloss into something, and every rule that turns on the
gloss language says so.

## The text field

`fa` reproduces the source **verbatim**: same spelling, same punctuation, the
source's own oddities included. Chunks split only at spaces, and joined back
they must reproduce the sentence exactly — a machine checks that. **Never
correct the text in `fa`**; the correction goes in `note` (videos) or in the
vocabulary line (books).

Devanagari writes its vowels, so a reading edition adds **nothing** to the
text a caption has: there is no layer of marks here as there is in Persian
and Arabic, and no third pass, because a bare Hindi sentence is the sentence.
Everything below is therefore about leaving the source alone.

Four things a source decides and this file does not:

| the source writes | keep it | never |
|---|---|---|
| **nukta**: क़ ख़ ग़ ज़ फ़ ड़ ढ़ | exactly as printed | add one the text does not have, or drop one it does |
| **ं anusvāra** vs **ँ candrabindu** | whichever is printed | normalise one to the other |
| **danda** । and ॥ | as printed | replace with a full stop |
| a compound written **solid** or with a space (`रेलगाड़ी`, `रेल गाड़ी`) | as printed | join or split it |

The nukta is the one that costs a reader something. `ज़` and `ज` are two
sounds, and a great many printings write both as `ज` — so the transliteration
line, not the text, is where the difference is recovered: see below. The
same for `क़/क` and `ख़/ख`.

A **ZWNJ** (U+200C) or **ZWJ** (U+200D) in the source is a shaping
instruction — it says whether a virāma makes a conjunct or a half-form — and
it stays in `fa`, inside the word, never at a chunk boundary. It has no
counterpart in `tr`.

## Reading

This language has no reading field: the `kana` key is ignored where it
appears, and nothing asks for one.

## Transliteration

`tr` is the transliteration of what is actually **said**, not of the letters
one at a time, and not of the dictionary form.

Vowels: **a ā i ī u ū e ai o au**. Consonants by row —
**k kh g gh ṅ** · **c ch j jh ñ** · **ṭ ṭh ḍ ḍh ṇ** · **t th d dh n** ·
**p ph b bh m** · **y r l v** · **ś s h**. The nukta letters are
**q x ġ z f** (क़ ख़ ग़ ज़ फ़) and **ṛ ṛh** (ड़ ढ़).

Four decisions this scheme makes, and keeps:

- **ष is ś, like श.** Hindi says one sound for both; flattening them is the
  same choice `docs/lang/fa.md` makes for the Arabic emphatics, and for the
  same reason — the transliteration is a pronunciation, and the script is
  what a word is looked up by.
- **ऋ is `ri`**, because that is what Hindi says (`ऋषि` *rishi*). This frees
  **ṛ** for ड़, which is a sound Hindi actually has, and no line in this
  series ever uses ṛ for two things.
- **The nukta is transliterated when it is written and not when it is
  not.** `ज़रूर` is *zarūr* and `जरूर` is *jarūr*: the nukta on the page is
  the source's own claim about the sound, and this line reports the page.
  Never restore one silently.
- **Nasalisation.** Before a stop, the homorganic nasal is written out:
  `हिंदी` *hindī*, `अंत` *ant*, `अंग` *aṅg*, `पंच` *pañc*. Everywhere else —
  and for every candrabindu — the mark is **ṁ** on the vowel it nasalises:
  `नहीं` *nahīṁ*, `हूँ` *hūṁ*, `माँ` *māṁ*, `गाँव` *gāṁv*.

**The schwa is the whole difficulty, and this line is where it is solved.**
The inherent *a* of a consonant is written in Devanagari and very often not
said. Report the speech:

| written | *not* | but |
|---|---|---|
| कमल | *kamala* | **kamal** — a final schwa is never pronounced |
| समझना | *samajhanā* | **samajhnā** — the medial schwa drops |
| नमकीन | *namakīn* | **namkīn** |
| दिल्ली | *dillī* | **dillī** (already; the geminate stays double) |
| सुबह | *subaha* | **subah** |

The rule of thumb: a schwa between two consonants that are themselves
followed by a vowel is dropped (V-C-**a**-C-V → V-C-C-V), and a word-final
schwa always is. It survives where dropping it would leave an unsayable
cluster (`प्रेम` *prem*, but `धरम` *dharam*). Where a word is commonly said
both ways, write the way the speaker on the recording says it.

Long vowels are always marked, geminates always doubled (`सच्चा` *saccā*,
`पत्ता` *pattā*), and the visarga `ः` — rare, and only in Sanskrit
borrowings — is **ḥ** (`दुःख` *duḥkh*).

Hindi keeps its grammatical words apart on the page, so this line carries
almost no hyphens: the postpositions (`ने को से में पर का के की`), `ही`,
`भी`, `तो` and `न` are separate words and are written separate. Hyphenate
only where one word contains two: the honorific enclitic **-jī**
(`रामजी` *rām-jī*), an echo pair (`चाय-वाय` *cāy-vāy*), and a solid Sanskrit
compound whose parts are separately meaningful (`राष्ट्रपति`
*rāṣṭra-pati*) — that last one being the only case where the hyphen teaches
rather than reports.

The scheme does not follow the gloss language: **ś** is ś and **x** is x in a
book glossed in Italian or in French as much as in one glossed in English. It
transliterates the Hindi rather than respelling it in somebody's orthography,
and every edition of this series must be readable by a reader who has learnt
it once.

## Vocabulary

`voc` is written in the voice of the books' gloss blocks: headword +
transliteration + meaning. Name what was stripped from the form in the text.
One equivalent in the gloss language rather than a string of synonyms, and
**an empty `voc` is the right answer** for a chunk that needs nothing.

In a **video** the line is plain text: a verb as `करना karnā · stem कर kar ·
perf. किया kiyā · to do (+ ने)` — the book's `\vb` read out, which is where
the space after the `+` comes from — and a form of it in the chunk first with
that entry in brackets after it (`किया kiyā did (करना karnā · stem कर kar ·
…)`).
In a **book** it uses four macros and nothing else: `\dw{fa}{rom} gloss` ·
`\vb{inf}{rom}{stem}{rom}{perf}{rom}{meaning}` · `\bw{base}{rom}{meaning}` ·
`\pw{fa}` — plus `\textit`, `\emph`, `\nobreak`.

**Every noun is given with its gender**, `m.` or `f.`, without exception.
Hindi agreement runs off the gender of a noun the reader cannot see it in:
`किताब kitāb f. book`, `मकान makān m. house`, `बात bāt f. thing said`. A
noun whose gender is not given has not been glossed.

**Every verb gets a `\vb`**, in the order the page prints it: the infinitive,
then the **stem**, then the **perfective**, masculine singular.

```
\vb{करना}{karnā}{कर}{kar}{किया}{kiyā}{to do (+\pw{ने})}
\vb{जाना}{jānā}{जा}{jā}{गया}{gayā}{to go}
\vb{होना}{honā}{हो}{ho}{हुआ}{huā}{to be, to happen}
```

The stem is the infinitive minus *-nā* and is almost never worth a second
look; the **perfective is why the entry exists**, because that is where the
handful of irregulars live — करना/किया, जाना/गया, होना/हुआ, देना/दिया,
लेना/लिया. Give a regular perfective anyway: a reader who has met three
irregulars does not yet know which verbs are regular.

What the three forms hide is **whether the subject takes ने in the
perfective** — `लड़का गया` but `लड़के ने किताब पढ़ी`, where the verb agrees
with the book and not with the boy. It is the one thing a reader needs to
build a past sentence, and it goes in **one parenthesis after the meaning**,
the only extra Hindi has, written exactly so:

- `(+\pw{ने})` for a verb whose subject takes ने (करना, देना, लेना, कहना,
  पढ़ना, रखना, उठाना, दिखाना — the transitive ones, broadly);
- `(±\pw{ने})` for one that goes either way (समझना, बदलना, नहाना, हारना);
- **nothing** for one that never does (जाना, आना, होना, मिलना, हँसना) —
  and nothing is not an omission: it says so.

A few common verbs break the transitivity rule — `लाना` and `भूलना` take an
object and never ने, `छींकना` and `खाँसना` take none and do — which is why
the mark is decided from a short hand-kept list first
(`lib/lang/hi.verbs.json`) and from the dictionary only after it: on 152
common verbs the dictionary's transitivity agreed with ने for 110,
contradicted it for 9 (`लिखना` and `सुनना` coded intransitive, `लाना` and
`बनना` transitive) and said nothing for 33, `करना`, `जाना`, `आना`, `लेना`,
`खाना` and `पीना` among them. When you know better than both, you are right;
say so in the line.

Two things Hindi does that a gloss must not flatten:

- **The transitive/intransitive pair.** `खुलना khulnā to open (of itself)`
  and `खोलना kholnā to open (something)` are two verbs, not one verb in two
  uses; likewise टूटना/तोड़ना, बनना/बनाना, दिखना/दिखाना. Gloss the one that
  is in the text, and name its partner where the difference is the point of
  the sentence.
- **The conjunct and the compound.** In a conjunct verb (`काम करना` *kām
  karnā*, `याद आना` *yād ānā*) the light verb carries no meaning of its own:
  give the `\vb` for the light verb with **no meaning in its seventh
  argument** and a `\bw` for the word it carries — the rule `docs/lang/fa.md`
  states for Persian, and the two languages do the same thing. The ने mark
  stays, because the conjunct takes ने exactly when its light verb does:
  `\vb{करना}{karnā}{कर}{kar}{किया}{kiyā}{(+\pw{ने})}\bw{काम}{kām}{m. work}`,
  and for `याद आना` the seventh argument is simply empty. The exceptions are
  the conjuncts with a subject in को — `दिखाई देना`, `सुनाई देना` take no ने
  though `देना` does — and the list names them. In a compound verb
  (`कर लिया` *kar liyā*, `चला गया` *calā gayā*) the second verb is an aspect
  and not an action: say what it adds (completion, suddenness, doing-for-
  oneself) and never gloss its dictionary meaning.

Name the language a loanword came **from**, which has nothing to do with the
language the gloss is written in: `कमरा kamrā m. room — Port. câmara`,
`किताब kitāb f. book — Ar.`, `दोस्त dost m. friend — Pers.`,
`स्टेशन sṭeśan m. station — Eng.`. Hindi's vocabulary comes in four layers
(tadbhava, Sanskrit tatsama, Perso-Arabic, English) and a reader who is told
which layer a word is in learns the next word of that layer free.

What was stripped from the form in the text is named: the oblique (`लड़के`
*laṛke* ← `लड़का` *laṛkā*), the oblique plural (`लड़कों` *laṛkoṁ*), the
feminine plural (`लड़कियाँ` *laṛkiyāṁ*), and the postposition when it has
fused with a pronoun (`मुझे` *mujhe* = `मुझ` + `को`, `इसे` *ise* = `इस` +
`को`).

The gloss editor's sources sidebar, in the reader and in the player, now
proposes the `\vb` from the dictionary for a verb it recognises — the stem,
the perfective and the ने mark, each with its transliteration. The forms are
the dictionary's conjugation table and the sounds are its romanisation of
each form, respelt into this scheme (its tilde is ṁ, its `ŕ` is *ri*, its
`ṣ` is *ś*), so the schwa is right form by form — *samajhnā* but *samjhā*.
It is still a **draft for you to correct**: the ने mark is a proposal and
never a fact, and the meaning is the dictionary's first sense rather than
the text's (`रखना` comes as *to keep* where the text may mean *to put*).
The chunk decides two things. In a conjunct the light verb comes with no
meaning and the row names the `\bw` still to write; the second verb of a
compound, the `रहा` of the progressive and the `था` or `है` after a
participle get no `\vb` at all, only the `\dw` they always had, because what
they add is yours to say.

A conjunct also gets a **button of its own**, headed *conjunct verb* — the
word this file uses, so that it is never confused with the compound, which
gets no `\vb` — and it puts the pair in as the one entry it is:
`\vb{करना}{karnā}{कर}{kar}{किया}{kiyā}{(+\pw{ने})}\bw{काम}{kām}{to work}`,
the `\bw` run straight onto the `\vb`, and in a video the conjunct whole,
`काम करना kām karnā to work (करना karnā · stem कर kar · perf. किया kiyā)`.
The noun's romanisation is the head of the conjunct's own (*kām karnā* gives
*kām*), and its gloss is the **conjunct's** meaning, the one the row names;
the noun's own gender and sense (`m. work`, as above) are yours to put in
its place, as every draft here is yours to correct. Where the dictionary could not fill a slot — a
verb with no table has no perfective, a rare verb has no ने mark — the
button says which. Correct it before it is saved.

The meaning is what the gloss language is for; the labels around it — *stem*,
*perf.*, *m.*, *f.*, `+ने` and `±ने`, the ones the edition prints from the
registry included — are not, and stay as this file writes them whatever the
glosses are in.

Which words the reader already owns turns on the gloss language. A book
glossed in **Urdu** is read by somebody who has the same language in another
script and needs nothing but the Devanagari; one glossed in **Persian** or
**Arabic** is read by somebody who already owns the Perso-Arabic layer
whole — `किताब`, `दोस्त`, `वक़्त`, `ज़रूर` — and what those words need from
the line is not a meaning but the shift, where there is one (`हालत` is a
*condition* and not a state of affairs; `बात` has drifted a long way from
Sanskrit `वार्ता`). To a reader of English or Italian the same words are
simply new, and take the ordinary entry.

The repetition rule is Frank's own: a full entry the **first time** a word
appears, briefer or none on later appearances.

## Never gloss

These ~50 function words, already in dictionary form, never get a vocabulary
entry:

```
में से को का के की ने पर तक और या कि तो ही भी नहीं न यह वह ये वे इस उस
मैं मुझ तू तुम आप हम कोई कुछ सब हर अगर लेकिन मगर क्योंकि जब तब अब फिर
बहुत बस क्या कौन कहाँ कैसे क्यों जो
```

## Chunking

A chunk is a sense group of roughly **2–6 words** — a verb with its object, a
noun with what qualifies it, a postpositional phrase: something a reader
hovers and that *means* something on its own. A very short sentence is one
chunk; that is normal and not a fault.

Runs of Hindi are found by their script, so nothing is marked by hand.

Never split:

- a **noun from its postposition** (`राम ने`, `घर में`, `मेरे लिए`) — the
  postposition is the case, and a chunk that ends before it ends mid-word in
  every language but this one's spelling;
- a **genitive from its head** (`राम का घर`), because `का` agrees with the
  head and a reader who cannot see the head cannot see why it is `का`;
- a **conjunct or compound verb** (`काम करना`, `कर लिया`, `चला गया`);
- a **verb from its negation** (`नहीं आया`), nor from the auxiliary that
  carries its tense (`आ रहा है`, `गया था`) — the auxiliary is where the
  sentence says *when*.
