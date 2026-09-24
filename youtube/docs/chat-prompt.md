# Annotate a YouTube video for Parseh's Frank-method player

You are annotating the transcript of a {{LANGUAGE}} YouTube video so that
a learner can hover any phrase of it and see the reading (where the
language has one), the transliteration, the vocabulary and the meaning —
the way an Ilya Frank reading edition glosses a text, phrase by phrase.
You will receive the video's captions below, numbered and with their
start times. You answer with **one JSON document and nothing else**: the
page that reads your answer reads every ```` ```json ```` block in what is
pasted into it, in order, and merges them (several blocks, across several
messages — see the end); a caption given again in a later block replaces
the earlier one.

## The conventions — binding

{{CONVENTIONS}}

## The conventions of {{LANGUAGE}} — binding

{{LANG_CONVENTIONS}}

The `lib/…` scripts named above are the software's own checks. You cannot
run them; the page runs them on your answer and reports what failed, and you
will be asked to fix exactly those captions.

## What you receive

A numbered list, one caption per line:

```
[i] <start>s  <the caption's text, verbatim>
```
{{WORDS_RECEIVED}}
`i` counts only the captions that want glossing. Two other kinds of line
appear for context and must **not** be annotated:

- `(plain — not annotated) <start>s  <text>`: a caption with no
  {{LANGUAGE}} script at all, the video's own framing in another language,
  usually English (this line exists only for a language written in its own
  script). Read it, it
  tells you what is going on; do not put it in your answer.
- `— chapter: <title> —`: a chapter marker; a heading, not speech.

Every `[i]` line must appear in your answer exactly once, in order.

## What you answer

```json
{
  "video": {
    "title_native": "a short display title in {{LANGUAGE}}, for the index card",
    "level": "beginner | lower-intermediate | intermediate | upper-intermediate | advanced",
    "blurb": "one {{GLOSS_LANGUAGE}} sentence on what the video is",
    "title": "the real YouTube title, only if you know it",
    "channel": "the channel's name, only if you know it"
  },
  "captions": [
    {"i": 0, "start": 32, "chunks": [
      {"fa": "…", "kana": "…", "tr": "…", "voc": "…", "en": "…"},
      {"fa": "…", "kana": "…", "tr": "…", "en": "…", "note": "…"}
    ]}
  ]
}
```

- `i` and `start` are copied from the list, unchanged.
- `chunks` split the caption into the sense groups the conventions
  describe. Their `fa` — the caption's text in {{LANGUAGE}}; the key is
  named after Persian, the toolbox's first language — joined back with
  the language's word separator, must reproduce the caption
  **verbatim** — same letters, same punctuation, same joiners, the
  transcript's mistakes included. That is the one test a machine will
  run, and it is unforgiving.
- {{TR_RULE}}; `voc` on a word's **first** appearance in the video and
  rarely after; `note` only when something needs saying (an ASR slip,
  what was really said, a cultural point).
{{KANA_LINE}}{{WORDS_LINE}}- For a language written in its own script, a chunk of pure Latin
  script carries only `fa`; for a Latin-script language an aside in another
  language is a chunk with `fa` and `"plain": true`. Write `kana` only when the
  language has a reading.
- Leave out `title` and `channel` rather than guess them.

## An example, from a video already in the player

{{EXAMPLE_INTRO}}

Received:

```
{{EXAMPLE_IN}}
```

Answered (the `video` object is abbreviated):

```json
{{EXAMPLE_OUT}}
```

{{GLOSSARY}}

## Before you answer, check

- every `[i]` caption once, in order, `i` and `start` exactly as given;
- `fa` verbatim, chunks split only at the language's word separator,
  nothing corrected in `fa`;
{{WORDS_CHECK}}- {{TR_RULE}}, in the transliteration scheme of the {{LANGUAGE}}
  conventions above;
- `voc` on first appearances only — by the end of the video the common
  words carry none;
- valid JSON, inside a single ```` ```json ```` fence, and nothing else in
  the message.

A long video may not fit one message. Then stop at a caption boundary, end
the message with the fence closed, and continue in the next message with the
next `[i]`, in a new ```` ```json ```` fence holding only `"captions"`; the
page merges all the blocks you paste, in order.
