# Hindi — the annotation conventions

{{?new}}How a Hindi sentence becomes a glossed line: what goes into each field and
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
gloss language says so.{{/new}}

## The text field

`fa` reproduces the source **verbatim**: same spelling, same punctuation, the
source's own oddities included. Chunks split only at spaces, and joined back
they must reproduce the sentence exactly — a machine checks that. **Never
correct the text in `fa`**{{?new}}; the correction goes in {{?video}}`note`{{/video}}{{?book}}the
vocabulary line{{/book}}{{/new}}.

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

{{?classic}}`tr` is the transliteration of what is actually **said**, not of the letters
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
it once.{{/classic}}{{?ipa}}`tr` is the pronunciation of what is actually **said**, written in **IPA**: the broad (phonemic)
IPA of standard Hindi, with no slashes and no square brackets, and one scheme from the first chunk to the
last — not the letters one at a time, and not the dictionary form.

Vowels: **ə aː ɪ iː ʊ uː eː ɛː oː ɔː**, and a nasalised vowel carries the tilde (**ɛ̃ː**, **ãː**, **ĩː**), for
the anusvāra and the candrabindu alike; before a stop the homorganic nasal is written out as a consonant
instead (`हिंदी` *ɦɪndiː*, `पंच` *pəɲtʃ*, `अंग` *əŋɡ*). Consonants by row: **k kʰ ɡ ɡʱ ŋ** · **tʃ tʃʰ dʒ dʒʱ ɲ** ·
**ʈ ʈʰ ɖ ɖʱ ɳ** · **t tʰ d dʱ n** · **p pʰ b bʱ m** · **j ɾ l ʋ** · **ʃ s ɦ**: ष is **ʃ** like श, and ह is
**ɦ**. The nukta letters are **q x ɣ z f** (क़ ख़ ग़ ज़ फ़) and **ɽ ɽʱ** (ड़ ढ़); ऋ is **ɾɪ**, because that is what
Hindi says (`ऋषि` *ɾɪʃɪ*). The nukta is written when the page has it and not when it has not: never restore one
silently.

**The schwa is the whole difficulty, and this line is where it is solved**: report the speech. A final schwa is
never said (`कमल` *kəməl*) and a schwa between two consonants that are themselves followed by a vowel drops
(`समझना` *səmədʒʱnaː*), while it survives where dropping it would leave an unsayable cluster (`प्रेम` *pɾeːm*, but
`धरम` *dʱəɾəm*); where a word is commonly said both ways, write the way the speaker says it. A geminate is
written long (`सच्चा` *sətʃːaː*, `पत्ता` *pətːaː*) and the visarga is **h** (`दुःख` *dʊhkʰ*). No stress is written.
The postpositions and the other grammatical words are written apart, as the page has them: hyphenate only where
one word contains two — the honorific **-dʒiː** (`रामजी` *raːm-dʒiː*), an echo pair (`चाय-वाय` *tʃaːj-ʋaːj*) and
a solid Sanskrit compound whose parts are separately meaningful (`राष्ट्रपति` *raːʃʈɾə-pəti*).

IPA does not follow the gloss language: it is the same in a book glossed in Italian or in French as in one
glossed in English, and every edition of this series must be readable by a reader who has learnt it once.{{/ipa}}

## Vocabulary

`voc` is written in the voice of the books' gloss blocks: headword +
{{?classic}}transliteration{{/classic}}{{?ipa}}IPA{{/ipa}} + meaning. Name what was stripped from the form in the text.
One equivalent in the gloss language rather than a string of synonyms, and
**an empty `voc` is the right answer** for a chunk that needs nothing.

The line uses four macros and nothing else: `\dw{fa}{rom} gloss` ·
`\vb{inf}{rom}{stem}{rom}{perf}{rom}{meaning}` · `\bw{base}{rom}{meaning}` ·
`\pw{fa}` — plus `\textit`, `\emph`, `\nobreak` — and its entries are parted
by `; `.

{{?video}}What a video adds is the form its chunk has, where it is none of the three
the `\vb` prints, nor one its parenthesis names: it is named after the entry,
outside it, with its sound,
{{?classic}}`\vb{करना}{karnā}{कर}{kar}{किया}{kiyā}{to do (+\pw{ने})}; here \pw{करेगा}
\textit{karegā}, future`{{/classic}}{{?ipa}}`\vb{करना}{kəɾnaː}{कर}{kəɾ}{किया}{kɪjaː}{to do (+\pw{ने})}; here \pw{करेगा}
\textit{kəɾeːɡaː}, future`{{/ipa}}.
{{/video}}

**Every noun is given with its gender**, `m.` or `f.`, without exception.
Hindi agreement runs off the gender of a noun the reader cannot see it in:
{{?classic}}`किताब kitāb f. book`, `मकान makān m. house`, `बात bāt f. thing said`{{/classic}}{{?ipa}}`किताब kɪtaːb f. book`, `मकान məkaːn m. house`, `बात baːt f. thing said`{{/ipa}}. A
noun whose gender is not given has not been glossed.

**Every verb gets a `\vb`**, in the order the page prints it: the infinitive,
then the **stem**, then the **perfective**, masculine singular.

{{?classic}}```
\vb{करना}{karnā}{कर}{kar}{किया}{kiyā}{to do (+\pw{ने})}
\vb{जाना}{jānā}{जा}{jā}{गया}{gayā}{to go}
\vb{होना}{honā}{हो}{ho}{हुआ}{huā}{to be, to happen}
```{{/classic}}{{?ipa}}```
\vb{करना}{kəɾnaː}{कर}{kəɾ}{किया}{kɪjaː}{to do (+\pw{ने})}
\vb{जाना}{dʒaːnaː}{जा}{dʒaː}{गया}{ɡəjaː}{to go}
\vb{होना}{ɦoːnaː}{हो}{ɦoː}{हुआ}{ɦʊaː}{to be, to happen}
```{{/ipa}}

The stem is the infinitive minus {{?classic}}*-nā*{{/classic}}{{?ipa}}*-naː*{{/ipa}} and is almost never worth a second
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

- **The transitive/intransitive pair.** {{?classic}}`खुलना khulnā to open (of itself)`
  and `खोलना kholnā to open (something)`{{/classic}}{{?ipa}}`खुलना kʰʊlnaː to open (of itself)`
  and `खोलना kʰoːlnaː to open (something)`{{/ipa}} are two verbs, not one verb in two
  uses; likewise टूटना/तोड़ना, बनना/बनाना, दिखना/दिखाना. Gloss the one that
  is in the text, and name its partner where the difference is the point of
  the sentence.
- **The conjunct and the compound.** In a conjunct verb ({{?classic}}`काम करना` *kām
  karnā*, `याद आना` *yād ānā*{{/classic}}{{?ipa}}`काम करना` *kaːm kəɾnaː*, `याद आना` *jaːd aːnaː*{{/ipa}}) the light verb carries no meaning of its own:
  give the `\vb` for the light verb with **no meaning in its seventh
  argument** and a `\bw` for the word it carries — the rule `docs/lang/fa.md`
  states for Persian, and the two languages do the same thing — the `\bw` run
  straight onto the `\vb`, with no `; ` between them, which is what makes the
  pair one entry in the line. The ने mark
  stays, because the conjunct takes ने exactly when its light verb does:
  {{?classic}}`\vb{करना}{karnā}{कर}{kar}{किया}{kiyā}{(+\pw{ने})}\bw{काम}{kām}{m. work}`{{/classic}}{{?ipa}}`\vb{करना}{kəɾnaː}{कर}{kəɾ}{किया}{kɪjaː}{(+\pw{ने})}\bw{काम}{kaːm}{m. work}`{{/ipa}},
  and for `याद आना` the seventh argument is simply empty. The exceptions are
  the conjuncts with a subject in को — `दिखाई देना`, `सुनाई देना` take no ने
  though `देना` does — and the list names them. In a compound verb
  ({{?classic}}`कर लिया` *kar liyā*, `चला गया` *calā gayā*{{/classic}}{{?ipa}}`कर लिया` *kəɾ lɪjaː*, `चला गया` *tʃəlaː ɡəjaː*{{/ipa}}) the second verb is an aspect
  and not an action: say what it adds (completion, suddenness, doing-for-
  oneself) and never gloss its dictionary meaning.

Name the language a loanword came **from**, which has nothing to do with the
language the gloss is written in: {{?classic}}`कमरा kamrā m. room — Port. câmara`,
`किताब kitāb f. book — Ar.`, `दोस्त dost m. friend — Pers.`,
`स्टेशन sṭeśan m. station — Eng.`{{/classic}}{{?ipa}}`कमरा kəmɾaː m. room — Port. câmara`,
`किताब kɪtaːb f. book — Ar.`, `दोस्त doːst m. friend — Pers.`,
`स्टेशन sʈeːʃən m. station — Eng.`{{/ipa}}. Hindi's vocabulary comes in four layers
(tadbhava, Sanskrit tatsama, Perso-Arabic, English) and a reader who is told
which layer a word is in learns the next word of that layer free.

What was stripped from the form in the text is named: the oblique ({{?classic}}`लड़के`
*laṛke* ← `लड़का` *laṛkā*{{/classic}}{{?ipa}}`लड़के` *ləɽkeː* ← `लड़का` *ləɽkaː*{{/ipa}}), the oblique plural ({{?classic}}`लड़कों` *laṛkoṁ*{{/classic}}{{?ipa}}`लड़कों` *ləɽkõː*{{/ipa}}), the
feminine plural ({{?classic}}`लड़कियाँ` *laṛkiyāṁ*{{/classic}}{{?ipa}}`लड़कियाँ` *ləɽkɪjãː*{{/ipa}}), and the postposition when it has
fused with a pronoun ({{?classic}}`मुझे` *mujhe* = `मुझ` + `को`, `इसे` *ise* = `इस` +
`को`{{/classic}}{{?ipa}}`मुझे` *mʊdʒʱeː* = `मुझ` + `को`, `इसे` *ɪseː* = `इस` +
`को`{{/ipa}}).

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

## Example

{{?note}}No speaker has reviewed this example yet: a Hindi reader should read the chunks, the transliteration and
the IPA before the prompt is trusted.{{/note}}Three chunks of one sentence, as an answer writes them: the same shape in every prompt. The
meanings here are written in English because an example has to be written in something; yours are written in
the gloss language of this prompt.

{{?classic}}```json
{"chunks": [
  {"fa": "मैंने कल", "tr": "maiṁne kal", "voc": "\\dw{कल}{kal} yesterday (or tomorrow: the tense of the verb says which)", "en": "I yesterday"},
  {"fa": "एक नई किताब", "tr": "ek naī kitāb", "voc": "\\dw{नया}{nayā} new, f. \\pw{नई} \\textit{naī}; \\dw{किताब}{kitāb} f. book — Ar.", "en": "a new book"},
  {"fa": "पढ़ी", "tr": "paṛhī", "voc": "\\vb{पढ़ना}{paṛhnā}{पढ़}{paṛh}{पढ़ा}{paṛhā}{to read (+\\pw{ने})}", "en": "read"}
]}
```{{/classic}}{{?ipa}}```json
{"chunks": [
  {"fa": "मैंने कल", "tr": "mɛ̃ːneː kəl", "voc": "\\dw{कल}{kəl} yesterday (or tomorrow: the tense of the verb says which)", "en": "I yesterday"},
  {"fa": "एक नई किताब", "tr": "eːk nəiː kɪtaːb", "voc": "\\dw{नया}{nəjaː} new, f. \\pw{नई} \\textit{nəiː}; \\dw{किताब}{kɪtaːb} f. book — Ar.", "en": "a new book"},
  {"fa": "पढ़ी", "tr": "pəɽʱiː", "voc": "\\vb{पढ़ना}{pəɽʱnaː}{पढ़}{pəɽʱ}{पढ़ा}{pəɽʱaː}{to read (+\\pw{ने})}", "en": "read"}
]}
```{{/ipa}}

What to notice: the sentence keeps Hindi's order, the verb last, so the `en` lines read stiffly (*I yesterday* | *a new
book* | *read*) and that is meant; the case marker is left to `voc` and `en` carries no bracket for it; the verb's
`\vb` gives the masculine perfective and the ने mark, while the chunk shows the feminine `पढ़ी`, which agrees with
the book; every noun has its gender; `मैं` is never glossed.
