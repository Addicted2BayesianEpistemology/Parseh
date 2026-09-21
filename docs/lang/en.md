# English — the annotation conventions

How an English sentence becomes a glossed line: what goes into each field and
how it is written. These rules bind both the reading editions and the video
captions; they are embedded whole into every prompt that asks for English
annotation, so they are written as instructions to the annotator.

Two of the field names are languages, and neither is a claim about one: `fa`
is the text in the target language — English here — and `en` is the gloss
beside it. They are the names Persian and English left behind from the days
when they were the only two languages the toolbox had, and they are the same
two keys in every book and every video. Which language the gloss is written
in is the book's or the video's own choice, `"gloss"` in `book.json` /
`video.json`, and English when the key is absent.

An English edition therefore comes in two shapes, and it is worth knowing
which one you are writing before the first chunk. Glossed **in English** —
the default, and what an absent `"gloss"` means — it is a monolingual
edition: `en` is a definition rather than a translation, and `voc` is a
dictionary's work of saying a word in commoner words. Glossed in **anything
else** it is an ordinary edition of this series, and `en` is a translation
like every other book's. Neither shape is English's privilege or English's
burden: any language may be glossed in itself, and a Persian book glossed in
Persian is the same monolingual thing.

What is English's own, and holds in both shapes, is what most of this file is
about. Its spelling hides its sound, so the pronunciation line earns its keep
on every chunk and this file requires one where the machinery does not. Its
verbs have three principal parts and no way to guess them. And it welds a
verb to a particle it need not stand next to, which is a fact about the
language and not about the reader.

## The text field

`fa` reproduces the source **verbatim**: same spelling, same apostrophes, same
hyphens, same capitals, same punctuation, the source's own oddities included —
an older spelling, a dialect form, an ASR slip in a caption. Chunks split only
at spaces; joined back with single spaces they must reproduce the sentence
exactly, and a machine checks that. **Never correct the text in `fa`** — the
correction goes in `note` (videos) or in the vocabulary line (books).

English is plain text: nothing is written in for the first pass and nothing
comes off for a bare one, so there is no third pass. Keep, exactly as the
source has them:

- the **national spelling** the source uses, whichever it is (`colour` /
  `color`, `realise` / `realize`, `travelled` / `traveled`, `centre` /
  `center`, `defence` / `defense`) — never move a text from one side of the
  Atlantic to the other, and never mix the two within one book;
- the **apostrophes**, and the character the source uses for them, `'` or `’`
  (`don't`, `it's`, `o'clock`, `the boys' room`, `'tis`, `rock 'n' roll`): the
  fidelity check compares character for character, so do not normalise one
  into the other, and do not expand a contraction;
- the **hyphens** of compounds (`well-known`, `mother-in-law`, `twenty-one`,
  `re-form` against `reform`) and the dashes the source sets, em or en;
- the **capitals**, including a sentence a source begins in lower case and a
  word it capitalises for emphasis;
- **numerals** as figures where the source has figures and as words where it
  has words (`1914` stays `1914`, `nineteen fourteen` stays spelled out).

English has no character range of its own in the registry and could not be
given one, so nothing detects a run of English. Where the glosses are English
too, nothing tells the two apart at all — not even, as with French or Turkish
inside English prose, an accent or a letter the prose does not use; where
they are in another Latin-script language it is no better. Wherever the
format asks you to mark the target text (a studio document's `[…]{tl}` mark),
mark every run; in a book chunk or a video chunk `fa` is the text being
taught by definition and needs no mark.

In a **video**, `"plain": true` means a chunk that is not part of the passage
being taught: a sponsor read, a "like and subscribe", a title card read aloud.
For a language written in its own script the key usually carries an aside in
some other language, and the checker recognises one by the script it has not
got; here there is no script to go by and nothing is ever plain by itself, so
the key is yours alone to write — use it sparingly and never to excuse a
chunk you did not want to gloss.

## Reading

This language has no reading field: the `kana` key is ignored where it
appears, and nothing asks for one.

## Transliteration

`tr` is how the chunk is **said**, and in English it is written for every
chunk that has a word in it. The machinery makes the field optional
(`require_tr` is false, as for the other Latin-script languages) and this
file takes that licence back: English spelling records a pronunciation the
language left behind in the fifteenth century and never returned to, and it
is not merely irregular but irregular in both directions — `through`,
`though`, `thought` and `tough` share five letters and no vowel
(`θru`, `ðoʊ`, `θɔt`, `tʌf`), and there is no rule that would have told you.
A chunk without a `tr` is a chunk the reader cannot read. That is a fact
about the spelling and not about the reader, so it holds whatever the
glosses are written in — and in a monolingual edition it holds twice over,
the pronunciation being then the only line on the page carrying something the
reader could not have got from the text itself.

It is written in **IPA**, not in respelled English. That is a decision about
this language and not a taste: a respelling is made of English letters, and
English letters next to English words are read as English words, so `buhtur`
would be taken for a misspelling of `butter` where `ˈbʌtər` cannot be. It has
a second benefit that no other language here gets, and one that survives the
gloss language whole: a learner's dictionary of English prints these same
symbols in Milan and in Tokyo as much as in Oxford, so the reader who learns
this line can open any of them. A respelling built out of the gloss
language's spelling — `bater` for an Italian reader, `bataa` for a Japanese
one — would be readable by that one reader and by nobody else, and would
teach a sound English does not have.

The accent is **General American**, one accent throughout a book, and every
written `r` is sounded. A reader with a non-rhotic accent drops the `r`s
before a consonant and at the end of a word; that rule runs one way only,
which is why this is the direction to write in.

Two departures from strict IPA, both for legibility and both consistent:
`g` is the ordinary letter and not `ɡ`, and `r` is the ordinary letter and not
`ɹ`. Length is not marked: `i` and `ɪ`, `u` and `ʊ` differ in quality and the
mark would add nothing. Syllables are not divided.

**Consonants**

| written | the sound | example |
|---|---|---|
| `p` | as in *pen* | `pen` → `pɛn` |
| `b` | as in *bed* | `bed` → `bɛd` |
| `t` | as in *ten* | `ten` → `tɛn` |
| `d` | as in *day* | `day` → `deɪ` |
| `k` | as in *cat* | `cat` → `kæt` |
| `g` | always hard | `go` → `goʊ` |
| `f` | as in *fish* | `fish` → `fɪʃ` |
| `v` | as in *very* | `very` → `ˈvɛri` |
| `θ` | the voiceless *th* | `thin` → `θɪn` |
| `ð` | the voiced *th* | `this` → `ðɪs` |
| `s` | always hissed | `see` → `si` |
| `z` | as in *zoo* | `zoo` → `zu` |
| `ʃ` | what *sh* spells | `ship` → `ʃɪp` |
| `ʒ` | the middle of *measure* | `measure` → `ˈmɛʒər` |
| `h` | as in *hat* | `hat` → `hæt` |
| `tʃ` | what *ch* spells | `church` → `tʃərtʃ` |
| `dʒ` | what *j* spells | `jam` → `dʒæm` |
| `m` | as in *man* | `man` → `mæn` |
| `n` | as in *no* | `no` → `noʊ` |
| `ŋ` | the end of *sing* | `sing` → `sɪŋ` |
| `l` | as in *leg* | `leg` → `lɛg` |
| `r` | the American r | `red` → `rɛd` |
| `w` | as in *wet* | `wet` → `wɛt` |
| `j` | the *y* of *yes*, never the *j* of *jam* | `yes` → `jɛs` |

**Vowels**

| written | the sound | example |
|---|---|---|
| `ɪ` | the vowel of *sit* | `sit` → `sɪt` |
| `i` | the vowel of *see* | `see` → `si` |
| `ɛ` | the vowel of *bed* | `bed` → `bɛd` |
| `æ` | the vowel of *cat* | `cat` → `kæt` |
| `ɑ` | the vowel of *hot* and of *father* | `hot` → `hɑt`, `father` → `ˈfɑðər` |
| `ɔ` | the vowel of *caught* | `caught` → `kɔt` |
| `ʊ` | the vowel of *book* | `book` → `bʊk` |
| `u` | the vowel of *too* | `too` → `tu` |
| `ʌ` | the vowel of *cup* | `cup` → `kʌp` |
| `ə` | the vowel of every unstressed syllable | `about` → `əˈbaʊt`, `taken` → `ˈteɪkən`, `lemon` → `ˈlɛmən` |

Many speakers have lost the difference between `ɑ` and `ɔ` and say `kɑt` for
`caught`. Write them apart anyway: before `r` the two stay apart for everyone
(`far` `fɑr` against `for` `fɔr`), so a book that merged them would have to
un-merge them there.

**Diphthongs**

| written | the sound | example |
|---|---|---|
| `eɪ` | as in *day* | `day` → `deɪ` |
| `aɪ` | as in *my* | `my` → `maɪ` |
| `ɔɪ` | as in *boy* | `boy` → `bɔɪ` |
| `oʊ` | as in *go* | `go` → `goʊ` |
| `aʊ` | as in *now* | `now` → `naʊ` |

**A vowel and an r** are written as the vowel then `r`, and there are six:
`ɑr` (`car` → `kɑr`), `ɔr` (`for` → `fɔr`), `ɛr` (`hair` → `hɛr`), `ɪr`
(`here` → `hɪr`), `ʊr` (`tour` → `tʊr`), and `ər`, which is both the stressed
vowel of `bird` → `bərd` and the unstressed ending of `butter` → `ˈbʌtər` —
one symbol, the stress mark saying which.

**Marks**

| written | what it means | example |
|---|---|---|
| `ˈ` | primary stress, before the syllable that carries it | `about` → `əˈbaʊt` |
| `ˌ` | secondary stress, where a long word or a compound carries one | `understand` → `ˌʌndərˈstænd`, `information` → `ˌɪnfərˈmeɪʃən`, `outside` → `ˌaʊtˈsaɪd` |

No other symbol appears in a `tr`. The rules the symbols are used by:

1. **Every word of more than one syllable carries a stress mark**, and it is
   the most valuable thing on the line: stress is what English does not write
   and what makes a word unrecognisable when it is wrong — `ˈrɛkərd` the
   thing against `rəˈkɔrd` the act, `ˈprɛzənt` the gift against `prəˈzɛnt` to
   give it.
2. **A silent letter is not written.** `knee` → `ni`, `write` → `raɪt`,
   `comb` → `koʊm`, `island` → `ˈaɪlənd`, `listen` → `ˈlɪsən`, `honest` →
   `ˈɑnəst`.
3. **A function word is written weak**, because that is how it is said in a
   sentence: `the` → `ðə` (and `ði` before a vowel), `a` → `ə`, `to` → `tə`,
   `of` → `əv`, `and` → `ən`, `for` → `fər`, `was` → `wəz`, `are` → `ər`,
   `can` → `kən`, `you` → `jə`. Write it strong only where the chunk itself
   stresses it (`I ˈkæn` answering a doubt, against `aɪ kən ˈsi`). This one
   rule teaches more about how English sounds than the rest of the line put
   together.
4. **A contraction is one word** and keeps no apostrophe: `don't` → `doʊnt`,
   `I'll` → `aɪl`, `it's` → `ɪts`, `they've` → `ðeɪv`, `we're` → `wɪr`,
   `o'clock` → `əˈklɑk`.
5. **The endings are written as they are said**, never as they are spelled.
   Past `-ed` is `t`, `d` or `ɪd` (`helped` → `hɛlpt`, `played` → `pleɪd`,
   `wanted` → `ˈwɑntɪd`); plural and third-person `-s` is `s`, `z` or `ɪz`
   (`cats` → `kæts`, `beds` → `bɛdz`, `boxes` → `ˈbɑksɪz`).
6. **The flapped t is written `t`.** Between two vowels an American mouth
   makes `better` sound like `ˈbɛdər`; it is the same word with the same
   spelling and no exception anywhere, so a symbol for it would only be one
   more thing to learn.
7. Words are spaced as the chunk spaces them, and nothing is run together
   across a space even where the speech runs it together.
8. The line is **lower case throughout**, including a proper noun and the
   first word of a sentence (`London` → `ˈlʌndən`), and carries **no
   punctuation**.

## Vocabulary

`voc` is written in the voice of the books' gloss blocks: headword +
pronunciation + meaning. One sense — the one the text uses — rather than a
string of synonyms, no etymologies, and **an empty `voc` is the right
answer** for a chunk needing nothing.

Where the gloss language is **English**, the meaning is a definition and not
a translation, and the work is a monolingual dictionary's: say what the word
means in words simpler and commoner than the word itself, and never define a
word with itself or with its own relatives (`generous` is not "having
generosity"). Two things follow that a translating edition never has to
think about. The words a definition is built from must be words the reader
already has, so one drawn from the same shelf as the headword teaches nobody
anything — `arduous` is not "onerous". And a definition is longer than the
word it defines, always, so it has to be held to the one sense in front of
you or it will not fit the line.

Where the gloss language is **anything else**, the meaning is a translation
like every other book's in this series, and the entry is shorter for it: one
word of that language does the work a sentence of definition had to do.
Nothing on either side of the meaning moves with it — the pronunciation, the
three principal parts, the phrasal verb kept whole, and the labels *past*
and *p.p.*, which the edition prints itself, the same two words in every
English book, out of the registry.

Which words the reader already owns moves with it too, and only there. A
reader of Italian, French or Spanish gets the Latinate half of the
vocabulary free — `nation`, `important`, `possible` need the form named and
no meaning at all — and is walked straight into the words that only look
free: `eventually` is *in the end*, `actually` is *in fact*, `sensible` is
*reasonable*, a `library` is not a bookshop. Those earn a full entry
precisely because that reader will not stop for them. A reader of Persian,
Turkish or Japanese was never tempted and meets them as ordinary new words.
In a monolingual edition the question does not arise: there is no second
language to be helped or misled by, only the test of whether the definition
is built from commoner words than the headword.

- A **verb** is given as **plain form, past, past participle**, in that order,
  each with its sound. The edition prints *past* and *p.p.* before the second
  and the third, so no other form may go in those slots. A regular verb gets
  all three anyway, so that the slots always mean the same thing:
  `\vb{go}{goʊ}{went}{wɛnt}{gone}{gɔn}{to move from here to there}`,
  `\vb{help}{hɛlp}{helped}{hɛlpt}{helped}{hɛlpt}{to do part of someone's work for them}`.
- Four verbs have a **present** nobody could build from the plain form, and
  only those four carry it, in **one parenthesis after the meaning** — the
  one extra English has, a closed list, written exactly so:
  `\vb{be}{bi}{was, were}{wʌz, wər}{been}{bɪn}{to exist (pres. \pw{am},
  \pw{is}, \pw{are})}`; `have` `(pres. \pw{has})`; `do` `(pres. \pw{does}
  \textit{dʌz})`; `say` `(pres. \pw{says} \textit{sɛz})` — the last two for
  a vowel the spelling does not promise. No other verb gets a parenthesis:
  the rest of the present is the plain form and an `-s`.
- A **modal** (`can`, `could`, `will`, `would`, `shall`, `should`, `may`,
  `might`, `must`, `ought`) has no principal parts and never gets a `\vb`: it
  is a `\dw`, and its past form, where it has one, is named in the meaning —
  `\dw{could}{kʊd}` the past of *can*, and also a softer *can*. A `\vb` for
  one would print a *p.p.* that does not exist.
- A **phrasal verb** — a verb welded to a particle whose meaning is not the
  sum of the two (`give up`, `look after`, `put off`, `come across`) — is
  glossed **whole**, as one headword, however far the sentence has carried the
  particle from the verb (`give it up`, `put the meeting off`). Give the
  particle its own line only when it is a plain preposition doing plain work.
  A translating edition takes one word of the gloss language for the whole
  (`give up` is *rinunciare*, never *dare* + *su*) and a monolingual one
  takes one definition; neither ever glosses the two halves apart.
- A **noun** is given with an irregular plural where it has one (`child, pl.
  children`; `foot, pl. feet`; `mouse, pl. mice`) and with a note when it is
  uncountable and the reader might expect otherwise (`information`, `advice`,
  `news` — singular).
- An **adjective** is given with an irregular comparative (`good, better,
  best`; `bad, worse, worst`) and otherwise plain.
- A **homograph** — a word spelled one way and said two — is the English case
  that most needs the vocabulary line, and the entry must say which one is on
  the page, with its sound: `read` `rɛd` here the past, not `rid`; `lead`
  `lɛd` the metal, not `lid` to go in front; `live` `laɪv` the adjective, not
  `lɪv` the verb; `wind` `waɪnd` to turn, not `wɪnd` the air; `tear` `tɛr` to
  rip, not `tɪr` from the eye.
- Name what was stripped from the form in the text: the plural or third-person
  `-s`, the past `-ed`, the `-ing`, the comparative `-er` and superlative
  `-est`, the adverb's `-ly`, and the word a contraction is hiding (`'d` for
  *had* or *would*, `'s` for *is* or *has* or the possessive) — the last of
  these the first time it appears and not again.

In a **video** the line is plain text: `go goʊ · past went wɛnt · p.p. gone
gɔn · to move from here to there`, and a form of the verb in the chunk first
with that entry in brackets after it (`went wɛnt moved (go goʊ · past went
wɛnt · …)`); a noun as `child tʃaɪld a young person, pl. children`; entries
separated by `;`. In a **book** the line uses four macros
and nothing else: `\dw{fa}{sound} gloss` ·
`\vb{plain}{sound}{past}{sound}{p.p.}{sound}{meaning}` ·
`\bw{base}{sound}{meaning}` · `\pw{fa}` — plus `\textit`, `\emph`,
`\nobreak`. **Every** verb but a modal gets a `\vb`, no exceptions. `\pw`
quotes a word of the text inside the meaning — it is what `\dw`, `\vb` and
`\bw` set their headwords with — and how much it does depends on the gloss
language: in a book glossed in another language it is what tells the English
word from the prose around it, while in a monolingual one the two are one
language in one face and the mark says only "this is a word of the text".

The gloss editor's sources sidebar, in the reader and in the player, now
proposes the `\vb` from the dictionary for a verb it recognises — the three
principal parts with their sounds, and the present of the four above — and
never offers one for a modal, nor for the particle of a phrasal verb (the
`down` of `put it down` is not the verb *to down*). Where the dictionary
lists two pasts it takes the one the chunk has, and otherwise the first
listed, which is the American one (`dreamed`, `learned`). A phrasal verb is
proposed whole when its particle ends the chunk (`came in`, `put it down`,
`what he was waiting for`); one with words after its particle (`gave up
smoking`) is proposed as the plain verb, for you to lengthen. The sound of a
regular past is worked out by rule 5 above; an irregular one is the
dictionary's own transcription of that form, and a phrasal verb with none of
its own is said as its verb and its particle (`give up` `gɪv ʌp`). It is a
**draft for you to correct**: the dictionary's transcription of many a word
is British only (`stop` `/stɒp/`, `wrote` `/ɹəʊt/`, and `was` and `were`
have no American one at all), and such a slot is left empty rather than
converted from one accent into the other; and its meaning is the
dictionary's first sense, which is not always the one in the text, nor
built of words commoner than the headword. Correct it before it is saved;
where it could not fill a slot, the button says which.

The repetition rule is Frank's own: a full entry the **first time** a word
appears, briefer or none on later appearances.

## Never gloss

These function words are already in dictionary form and never get a
vocabulary entry:

```
the a an this that these those
I you he she it we they me him her us them
my your his its our their mine yours hers ours theirs
of to in on at by for with from as into onto about over under
after before between through during against without within
and or but so if because than then when while where how why
what who whom which whose there here now
not no nor never very too also just only still again always
```

The auxiliaries and the modals are **not** on this list. `be`, `have` and `do`
are the three most irregular verbs in the language and a reader meeting `was`,
`been`, `does` or `did` needs to be told once which verb it is; a modal needs
the entry described above. The one thing you may add to a word on the list is
a pointer saying which word a contraction is hiding, and only the first time
it appears.

The list is English's own and does not move with the gloss language. One
addition does: a word on it that the reader's language has nothing like is
worth one naming, the first time it appears and never again. The articles
are the case that matters — `a` and `the` are the hardest words in the
language for a reader of Persian, Turkish, Japanese or Arabic, none of which
has both — so a book glossed in one of those may say once what they do. A
book glossed in Italian or French says nothing at all: its reader has
articles already and is learning only where English puts them.

## Chunking

A chunk is a sense group of roughly **2–6 words** — a verb with its object, a
noun with what qualifies it, a preposition with its noun: something a reader
hovers and that *means* something on its own. A very short sentence (`Yes.`,
`Come in!`) is one chunk; that is normal and not a fault. Chunks split at
spaces only, so a contraction (`don't`, `I'll`, `o'clock`) and a hyphenated
compound (`well-known`, `mother-in-law`) are each one token and cannot be cut
in two.

Never split:

- an **article or determiner from its noun**: `the house`, `a long day`, `my
  father`, `those books`;
- a **preposition from its noun**: `in the morning`, `after him`, `at home`;
- `to` **from its infinitive**: `to go`, `to have seen`;
- an **auxiliary from its verb**, however many auxiliaries there are: `has
  gone`, `is going`, `will have been waiting`, `did not know`;
- a **negation from what it negates**: `did not know`, `never came`, `no
  longer here`;
- a **subject pronoun from its verb**: `he said`, `they were`, `there is`;
- the two halves of a **comparison**: `more difficult`, `as big as`, `the
  same as`;
- a **fixed phrase**: `of course`, `a lot of`, `used to`, `as well as`, `in
  order to`, `at all`, `by the way`;
- and the one that is English's own, a **phrasal verb from its particle**,
  including when the object has been pushed between them: `give up`, `give it
  up`, `take the coat off`, `look after her` are each one chunk. The particle
  is half of the word; a chunk that ends before it would give the reader a
  verb that means something else.
