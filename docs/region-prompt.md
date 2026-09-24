# Gloss part of {{A_LANGUAGE}} {{SURFACE_NOUN}}, in {{GLOSS_LANGUAGE}}, for Parseh

You are glossing part of {{SURFACE}} the way Ilya Frank's reading editions
gloss a text: the text is already cut into chunks — short phrases — and each
chunk gets its {{FIELD_LIST}} beside it, so that a learner reads the
{{LANGUAGE}} and understands it at once, phrase by phrase. Part of this stretch may be
glossed already; {{?keep}}you fill in only what the data below marks as still
to do, and leave everything else exactly as it is{{/keep}}{{?regloss}}this time
every chunk is glossed afresh: no gloss already written is shown to you, and
yours replaces it{{/regloss}}.

You receive **one JSON document**, at the end of this message, and you answer
with **the same JSON document, filled in, and nothing else** — no word before
it or after it.

**Write every meaning in {{GLOSS_LANGUAGE}}.** It is the language this
{{SURFACE_NOUN}}'s glosses are written in: every `en`, and every meaning inside
a `voc`, is written in {{GLOSS_LANGUAGE}}{{GLOSS_NOTE}}. The key is still called
`en`, after the days when English was the only gloss there was, just as the
text is called `fa` after Persian, the toolbox's first language: read `fa` as
"the {{LANGUAGE}} text" and `en` as "the meaning".

## What you receive

{{?book}}One entry per **sentence** of the book, in reading order, under
`"sentences"`. `"at"` names it — the chapter file, a colon, and the
paragraph.sentence label the book prints (`"ch1:1.2"` is sentence 2 of
paragraph 1 in the file ch1) — and `"chunks"` are its chunks, in order.{{/book}}{{?video}}One entry per **caption** of the video, in order, under `"captions"`.
`"i"` is the caption's number and `"start"` its time in seconds; `"chunks"`
are its chunks, in order. A caption marked `"plain": true` carries its
`"text"` and no chunks: it is not {{LANGUAGE}} — the video's own framing,
usually English — and is there only so you can follow what is being said.{{/video}}

Every chunk carries `fa`, its {{LANGUAGE}} text, exactly as it stands.
{{?words}}A chunk may also carry `words`: the chunk divided into words, each
word's reading in parentheses after it. It is **read-only** here — never
change it — and it is your best guide to the reading: `{{READING_FIELD}}` must
say what the words say, the readings of the words run together (see the Words
section of the conventions below).{{/words}}

What each chunk asks of you:

{{?keep}}- `"todo": true` — **gloss this chunk**: write its {{FIELD_LIST}}.
{{?seeded}}  Such a chunk may already carry a `{{READING_FIELD}}` the software
  read off its words: it is a proposal, not somebody's writing — keep it
  where it is right and correct it where it is not.
{{/seeded}}{{?perfield}}- `"todo": ["tr", "voc"]` — a list: this chunk is glossed in part, and
  you **fill exactly the fields named**, leaving the ones it already has as
  they are. A required field in the list ({{REQUIRED}}) must be filled; an
  optional one (`voc`{{?optional_tr}}, `tr`{{/optional_tr}}) is filled
  where the conventions call for it and left out where they do not.
{{/perfield}}- no `"todo"` at all — **already glossed**: leave it exactly as it is. It is
  there so your glosses agree with it: the same transliteration for the same
  word, the same meaning where the sense is the same, and the repetition rule
  (below) counts what its `voc` already gave.
{{/keep}}{{?regloss}}- `"todo": true` on every chunk not marked plain, whether it carries a
  gloss now or none: **gloss it afresh**, its {{FIELD_LIST}}. Nothing
  already written is shown, and nothing already written survives: what you
  answer is the whole gloss of the chunk.
{{/regloss}}- `"plain": true` — text that is never glossed (a foreign word, a run of
  the {{SURFACE_NOUN}}'s own framing): leave it exactly as it is, and add no
  field to it.

## The rules — binding

1. **Keep every chunk exactly as it is divided.** Never cut a chunk in two,
   never join two, never move a word from one chunk to the next, never add or
   remove a chunk, never reorder anything. The division was made by a person
   and is kept as sent: a chunk you divide differently is thrown away, gloss
   and all.
2. **Never change `fa`**, not a letter, not a mark, not a space — the
   {{SURFACE_NOUN}}'s own oddities and mistakes included. What is wrong in
   the text is said in {{?book}}the vocabulary line{{/book}}{{?video}}the
   meaning or the vocabulary line{{/video}}, never corrected in
   `fa`.{{?video}} Where the conventions below send a correction to `note`,
   they do not apply here: this answer writes no `note` — say the
   correction in the meaning or the vocabulary line.{{/video}}{{?words}}
   Never change `words` either.{{/words}}
3. **Fill only what is to do.**{{?keep}} A chunk with no `"todo"` comes back
   exactly as you received it{{?perfield}}; a chunk whose `"todo"` is a list
   gets those fields and no others changed{{/perfield}}. Glosses already
   written are protected: a change to one is ignored, whatever it
   says.{{/keep}}{{?regloss}} Every
   chunk marked `"todo"` gets its whole gloss from you; a `"plain"` chunk gets
   nothing.{{/regloss}}
4. **A chunk you gloss is glossed completely:** {{REQUIRED}} on every one,
   written in full. A chunk that comes back with one of them missing is not
   written at all — half a gloss is worse than none.
5. **The fields:**
{{?reading}}   - `kana` — the reading of the **whole chunk**, as the conventions of
     {{LANGUAGE}} below write it; required.
{{/reading}}   - `tr` — the {{TR_LABEL}} of the chunk, in the scheme of the conventions
     below{{?require_tr}}; required{{/require_tr}}{{?optional_tr}}; optional in
     {{LANGUAGE}}: write it where the conventions call for it, leave it out
     where they do not{{/optional_tr}}.
   - `voc` — the vocabulary line: headword, {{TR_LABEL}}, meaning in
     {{GLOSS_LANGUAGE}}, as the conventions below show. **Optional**: an
     empty `voc` is the right answer for a chunk that needs nothing.
{{?book}}     In this book `voc` is **LaTeX**, and only these macros may appear in
     it: `\dw{word}{rom} meaning`, `\vb{…}` (seven arguments, as the
     conventions give them), `\bw{base}{rom}{meaning}`, `\pw{word}`,
     `\textit{…}`, `\emph{…}` and `\nobreak`. None of `$ % & # _ ^ ~` may
     appear in it, nor a double backslash, and every brace must close. In
     the JSON a backslash is written twice: `"\\dw{…}{…} …"`.
   - {{TEXT_FIELDS}} are plain text, and none of
     `\ { } $ % & # _ ^ ~` may appear in them.
{{/book}}{{?video}}     In a video `voc` is **plain text** — no LaTeX, no macros — written as
     the conventions below show for a video.
{{/video}}   - `en` — the meaning of the chunk as it is said, short, in
     {{GLOSS_LANGUAGE}}; required. Keep the reading order of the text: where
     the sense runs on into the next chunk, let it.
{{?words}}   - `{{READING_FIELD}}` agrees with `words`: the words' readings run
     together{{?reading}} (the conventions say where the two may rightly
     differ){{/reading}}.
{{/words}}6. **Frank's repetition rule.** A full `voc` entry the **first time** a word
   appears in the stretch — or in the glossed chunks around it — briefer or
   none on later appearances. A wall of repeated entries is worse than none.
7. Every value is a JSON string. Write no other key than the ones above:
   `col`, `note`, `free`, `plain` and `words` are never written from an
   answer.{{?video}} That includes the `note` the conventions below give a
   correction or a remark: a `note` you write is thrown away, so what it
   would say goes in the meaning or the vocabulary line.{{/video}}

## The conventions of {{LANGUAGE}} — binding

These rules are {{LANGUAGE}}'s own; they bind every chunk you gloss. Where
they speak of a {{OTHER_SURFACE}}, that part is not for this
{{SURFACE_NOUN}}.

{{LANG_CONVENTIONS}}

## What you answer

The JSON below, **whole**, with the chunks to do filled in: every
{{UNIT}} in the order given, with its {{ADDRESS}} unchanged, every chunk in
its place with its `fa` unchanged{{?keep}}, and every chunk not to do exactly
as it was{{/keep}}. You may keep the `"todo"` keys or drop them; they are
ignored. Put it inside **one** ```` ```json ```` fence and write nothing else
in the message.

A long stretch may not fit one message. Then stop at a {{UNIT}} boundary,
close the fence, and continue in the next message with the next {{UNIT}}, in
a new ```` ```json ```` fence holding only `"{{LIST_KEY}}"`: every block
pasted back is read, in order, and a {{UNIT}} that comes twice is taken from
the later block — which is also how a correction is sent.

## Before you answer, check

- every {{UNIT}} once, in order, its {{ADDRESS}} exactly as given;
- every chunk in its place, as many chunks as you were given, `fa` unchanged;
- {{REQUIRED}} on every chunk you glossed, in the scheme of the {{LANGUAGE}}
  conventions above;
- every meaning in {{GLOSS_LANGUAGE}};
- `voc` on first appearances only{{?book}}, and nothing in it but the macros
  allowed{{/book}};
- valid JSON, inside a single ```` ```json ```` fence, and nothing else in the
  message.

{{ABOUT}}

## The {{UNITS}}

```json
{{DATA}}
```

Answer with the JSON and nothing else.
