# Annotate a YouTube video for the Frank-method player

*(Copy everything below into a Claude session opened in the project root,
then paste the video URL, its language, and the timed transcript after it.
The short way, for any LLM without the project, is the **Add a video** page
at `https://localhost:7654/youtube/add/` — it uses `docs/chat-prompt.md`,
the same conventions, and checks the answer with the same tools.)*

---

You are annotating a YouTube video for the Frank-method video player in
`youtube/`. I will give you a YouTube URL, the language the video teaches
(a code of `lib/languages.json` — that registry is the list of languages and
no file outside it holds one, so read the entry for the code, its folder and
what the language asks of a chunk) and a timed transcript (copied from
YouTube's "Show transcript" panel). Produce the files that make the video
playable at `https://localhost:7654/youtube/v/<id>/`. Do not modify the
player, the server, other videos' directories, or anything outside
`youtube/videos/<folder>/<id>/` (plus a word list under `youtube/docs/`,
if the video needs one).

**I will also give you the GLOSS LANGUAGE — the language everything you
write *for the reader* is written in.** It is a second, independent choice:
an Italian learning English wants the meanings in Italian, so the video's
language is `en` and its gloss language is `it`. Every `en` field, every
meaning inside a `voc`, every `note` and the `blurb` are written in it, and
nothing else is: the `fa` is the caption's own words and the `tr` is the
romanisation its conventions prescribe. If I do not name one, it is
**English**, which is what every video in the player today is glossed in.

Read `youtube/docs/conventions.md` first — it is the binding specification
for chunking, the fields, the repetition rule and plain captions, the same
for every language — and then the language's own conventions,
`docs/lang/<code>.md` at the project root: the transliteration scheme, the
reading rule, what never to gloss. This file only says what to produce and
in what order.

## Files to produce, all under `youtube/videos/<folder>/<id>/`

`<folder>` is the language's folder from the registry — the `folder` field
of its entry, which is the English name in lower case (`fa` → `persian`);
`<id>` is the YouTube video id (the `v=` parameter of the URL). Every tool
below is run from `youtube/` and takes that path.

### 1. `transcript.txt`
The pasted transcript, **verbatim** — timestamp lines, the human duration
lines if present ("1 minuto e 6 secondi"), any chapter lines
("Capitolo 3: …", "第3章：…", "3. Bölüm: …"), and the caption text lines
exactly as given, in order. This file is the single source of truth: the
pipeline reads every caption's text, timestamp, chapter heading and plain
mark from it, so a typo here is a typo everywhere — copy, never retype
from memory.

### 2. `video.json`
```json
{
  "id":           "<the 11-char YouTube id>",
  "url":          "https://www.youtube.com/watch?v=<id>",
  "title":        "<the real YouTube title — fetch https://www.youtube.com/oembed?url=<url>&format=json>",
  "title_native": "<a short display title in the video's language, for the index card>",
  "channel":      "<channel name, from the same oEmbed answer>",
  "language":     "<the language's code in lib/languages.json>",
  "gloss":        "<the code the meanings are written in; leave it out for English>",
  "level":        "beginner | lower-intermediate | intermediate | upper-intermediate | advanced",
  "duration":     "<mm:ss, roughly the last caption's timestamp>",
  "added":        "<today, YYYY-MM-DD>",
  "blurb":        "<one sentence, in the gloss language, on what the video is>"
}
```

(`language` is what the video TEACHES and `gloss` what its meanings are
WRITTEN in; the two are never the same field. A gloss may be written in any
of the languages the registry holds and in a handful of prose ones it does
not teach — `pt`, `nl`, `ca`, `ro`, `pl`, `ru`, `en-gb`, `en-us` — and
`check_annotations.py` refuses anything else. Absent means English.)

(`title_fa` is the older name of `title_native`; the Persian videos still
carry it and every reader accepts it. Write `title_native`.)

### 3. `parts/*.json`, then `annotations.json`

See how the video divides up:

```bash
python3 lib/slice_part.py videos/<folder>/<id>
```

Work in batches of **20–30 captions** (fewer when the speech is fast and the
captions are long). Each batch is one part file — `parts/01.json`,
`parts/02.json`, … — merged in filename order. Get a batch's captions,
authoritative, from the transcript itself:

```bash
python3 lib/slice_part.py videos/<folder>/<id> 0 25     # captions 0..24
```

and write them as a JSON **array**, one entry per caption, in order. Each
chunk carries `fa` (the caption's text in the target language — the key is
named after Persian, the toolbox's first language), `tr`, `voc`, `en` (the
meaning, written in the gloss language — that key is named after English for
the same historical reason `fa` is named after Persian, and says nothing
about what goes in it), and `kana` when the language has a reading:

```json
[
 {"start": 27,
  "chunks": [
   {"fa": "احساس می‌کنم", "tr": "ehsās mi-konam",
    "voc": "احساس ehsās feeling (Ar.); احساس کردن ehsās kardan to feel",
    "en": "I feel"},
   {"fa": "یه چیزی در مورد شما هست", "tr": "ye čiz-i dar mored-e šomā hast",
    "en": "there is something about you"}
  ]}
]
```

and, for Japanese, with the chunk's words and the reading of the whole chunk:

```json
[
 {"start": 14,
  "chunks": [
   {"fa": "私は", "words": "私(わたし) は", "kana": "わたしは", "tr": "watashi wa", "voc": "私 わたし watashi I", "en": "I"},
   {"fa": "毎朝コーヒーを飲みます", "words": "毎朝(まいあさ) コーヒー を 飲みます(のみます)",
    "kana": "まいあさコーヒーをのみます", "tr": "maiasa kōhī o nomimasu",
    "en": "drink coffee every morning"}
  ]}
]
```

Never put the caption text, a `plain` flag or a `chapter` on a caption in
a part — `merge_parts.py` fills those from `transcript.txt`, and it
refuses to merge if your starts skip or double a caption.

**Captions that are entirely in another language** (the framing many
teaching videos open with, usually English) are, for a language written in
its own script, not annotated at all: `slice_part.py` leaves them out of the
numbering and the pipeline fills them in, to be shown as they stand. Such a
run *inside* such a caption is one chunk carrying only `fa`. For a
Latin-script language — which cannot be told from English by its letters,
and which English itself now is — nothing is plain by itself: every caption
is in your batch, and an aside in a language that is not the one being
taught is a chunk with `fa` and `"plain": true`. The test is the language
the video TEACHES, never the gloss language. A chunk marked `plain` for a
script language exists only for imports from the older format — never write
one there; a chunk of the target language always gets its gloss.

### 4. A word list, when the video earns one
If the video has a vocabulary of its own — a story world, a technical
subject — write `docs/glossary-<slug>.md` the way the existing ones are
written, and gloss those words identically everywhere. This is what keeps a
long video from reading as if several people wrote it (they did).

## The pipeline (run from `youtube/`)

```bash
python3 ../lib/fill_words.py --lang ja --json videos/<folder>/<id>/parts/01.json   # Japanese, Chinese: the words first
python3 lib/check_part.py videos/<folder>/<id> parts/01.json   # after each batch
python3 lib/merge_parts.py videos/<folder>/<id>                # parts -> annotations.json
python3 lib/check_annotations.py videos/<folder>/<id>          # must end:  0 error(s)
rm -r videos/<folder>/<id>/parts                              # the batches have done their job
```

`parts/` lives only while a video is being added. Once `merge_parts.py` has
folded the batches into `annotations.json` and the checker has passed on it,
delete them: `annotations.json` is the video's only annotation from then on,
the player writes it, and a folder left behind is a second, older copy that
a merge run again would quietly put back. The add page does this for you.
`merge_parts.py` will not rebuild over an `annotations.json` newer than the
batches — it says which captions and which fields that would have lost.

`check_part.py` checks one batch on its own, before the rest of the video
exists — run it after every batch and fix until it prints `0 error(s)`, while
the words are still in front of you. The checks take the language from
`video.json` and ask of each chunk what the language requires (the meaning;
the transliteration where the language wants one; the kana where it has a
reading). The fidelity test strips the language's marks (harakat) from both
sides, so it cannot see a vocalisation mistake: reread your own batch once
after the mechanical checks pass. Then reload (nothing to restart: pages are
assembled per request) and confirm `https://localhost:7654/youtube/v/<id>/`
renders and the captions highlight in time with the video.

## What good looks like

The finished page should read like a page of the printed editions: the
text carries the reader, the cloud answers the question the reader was
about to ask, and nothing more. The meaning lines should join up into
continuous prose down the page, in the gloss language. When the transcript's ASR garbles a word,
the gloss quietly says what was really said. When a word has appeared five
times, its cloud has grown short.
