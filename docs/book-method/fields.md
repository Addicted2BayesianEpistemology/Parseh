## The chunk and what you write in it

A paragraph is divided into sentences and a sentence into chunks. A sentence ends where the text ends it (a full stop, a question or exclamation mark, or the language's own marks); it is a subparagraph, one `\begin{frank}` each, and its label is in {{LANG_NAME}}'s digits (`\parnum{{{LANG_LABEL_EXAMPLE}}}`: paragraph.subparagraph -- `assemble.py` writes it).

### The fields of a chunk

- **`fa`** is the chunk's text in {{LANG_NAME}}. The key is named after Persian, the toolbox's first language, and is kept because every tool and every stored file uses it; read it as "the foreign text". The chunks' `fa`, joined with the language's word separator (a space, or nothing for a language such as Japanese that writes none), must equal the paragraph {{STRIP_NOTE}}.
- **`tr`** is its {{TR_LABEL}} (some languages leave it out where the conventions say so).
- **`en`** is its meaning **in {{GLOSS_NAME}}**, of that chunk's own words only and in the order of the text: **The meaning of a chunk** is the rule.
- **`voc`** is the vocabulary line, also in {{GLOSS_NAME}}, apart from the {{LANG_NAME}} words it quotes.{{KANA_RULE}}

{{?marks}}**`fa` carries the short vowels in this book.** Write them on every word, by the conventions of {{LANG_NAME}}. The fidelity check strips the marks from both sides, so a mark can never make a chunk fail, and that is why a wrong one goes unseen: the marks exist to agree with the transliteration printed beside them, and where they disagree the mark is what misleads. {{/marks}}{{?nomarks}}**`fa` carries no short vowels of your making in this book.** Copy it as the source has it: a mark the source itself carries stays, and none is added. {{/nomarks}}

### The vocabulary line

It uses only `\dw \vb \bw \pw \textit \nobreak \emph`: `\dw{word}{sound} meaning` (a word: its {{LANG_NAME}} form, its {{TR_LABEL}} where the conventions give one, then the meaning); `\vb{...}` with seven groups (below); `\bw{base}{sound}{meaning}` (the base word of a compound verb, run straight after the light verb's `\vb`); `\pw{word}` (a word of {{LANG_NAME}} put inside a meaning); `\textit{...}` and `\emph{...}`; `\nobreak`. Every verb gets a `\vb`. Name what was stripped (an article, a plural, an enclitic, a particle), in {{GLOSS_NAME}}; give one {{GLOSS_NAME}} equivalent, not a string of synonyms; an empty `voc` is the right answer for a chunk that needs nothing. `\pw{...}` puts a word of {{LANG_NAME}} inside the {{GLOSS_NAME}} text and is what keeps it the right way round on the page; it cannot break across a line, so keep it short (twenty characters is a lot). What is never glossed is in the conventions. Entries are parted by `; `. In the JSON every backslash is written twice: `"\\dw{...}{...} ..."`.

The repetition rule is Frank's: a full entry the first time a word, a name or a construction appears, briefer afterwards. Briefer, not absent: a one-word gloss repeated is already as brief as it gets, and what must not come again is an explanation (who a character is, what a convention means) already given.

**The `\vb` is {{LANG_NAME}}'s own**, and the conventions are where its shape is: which three forms fill `\vb{form}{sound}{form}{sound}{form}{sound}{meaning}`, in the order the edition labels them, and which verbs get one at all. The same seven arguments in every language, and three rules that hold in every language: a **pair whose form is left empty is not printed** -- neither the form nor its label -- so leave one empty only where the conventions say that verb has no such form, never to save room and never by repeating another form in it; **what the three forms cannot say** (an auxiliary, a verb class, a governed case or preposition, an irregular participle or future) goes in **one parenthesis after the meaning**, items parted by `; `, in the conventions' exact words and **only where it is not the ordinary case** -- `to drive (er fährt; aux. sein)` is German's, `to have (fut. \pw{tendré})` Spanish's; and a verb the conventions do not give a `\vb` stays a `\dw` -- Chinese gives one only to a separable verb (`split`) or a verb with a complement (`can't`), English none to a modal. The form of the verb in the chunk, when it is none of the three, is named after the entry as the conventions show.

### What a chunk is

A chunk is a phrase: the smallest span that still means something on its own and that a gloss can translate as one thing. **Cut at the edges of phrases, never inside one**, and aim for the range the conventions give for the language (**2-5 words** where they give none). The average falls where it falls -- about two and a half to three source words a chunk on the editions measured, lower where a language packs a clause into a word -- and chasing a number is how a book ends up with one word per chunk: chase the sense group and keep what the conventions say stays together.

**Keep together, always** -- an **adposition with its noun** (`in the house`), which alone cannot be glossed at all; a **noun with everything that modifies it** (articles, demonstratives, numerals, adjectives, possessives, and whatever the language uses to link a noun to its modifiers); a **verb with everything that makes its tense** -- auxiliaries, negation, a separable prefix, the light verb of a compound: **the unit is the verb group, not the verb**, and a verb group cut in half is two halves that mean nothing; a **word with its particles and clitics**; and a **fixed expression or idiom even where that breaks the syntax**, because the meaning is not in the pieces and showing the pieces teaches something untrue. That last one is the most valuable chunk in the book and the one only a reader of the language can find.

**Cut, always** -- at a **clause boundary**, with the conjunction or relativiser **opening** the chunk it introduces; and between **two content words with nothing binding them**.

An **adverb joins the verb it modifies when it stands next to it**; a **sentence adverb** (`yesterday`) modifies the whole clause and stands alone. An **infinitive or verbal noun used as a noun** goes with its noun phrase, not with the verbs.

**What a chunk must not be**: not **one word per word** -- that is a dictionary with the text interleaved, and the reader never learns how the language phrases anything; and not **a whole sentence** -- past about six words the reader stops mapping and starts reading the translation, which is the one thing this method exists to prevent. A one-word chunk is right only where the word is the whole utterance or nothing may attach to it. **A mark is never a chunk of its own**: a dash or a quotation mark that opens speech stays with the first chunk of the speech, and a line made of marks alone (a dash and dots for a silence) is one chunk, whose `en` says what the silence is.

### The per-paragraph JSON

One file for each paragraph, `annot/chN_pNN.json`, in this shape (the same for every language and every gloss, the `fa` field holding the {{LANG_NAME}} text and `en` the {{GLOSS_NAME}}):

```json
{"idx": 11, "ch": 2,
 "ann": {"sentences": [
   {"chunks": [
     {"fa": "the first chunk, exactly as the source has it", "tr": "its transliteration", "voc": "\\dw{word}{sound} meaning", "en": "its meaning"},
     {"fa": "the last chunk of the sentence.", "tr": "its transliteration", "voc": "", "en": "its meaning."}
   ]}
 ]}}
```
{{KANA_EXAMPLE}}
`idx` is the paragraph's 0-based index in its chapter (the `NN` of its file), `ch` the chapter. One sentence is one entry of `sentences`. A filled chunk of {{LANG_NAME}} -- its `tr`, its `voc` and an `en` aligned to it -- is in the Example of **The conventions of {{LANG_NAME}}**: it is the model for yours.
