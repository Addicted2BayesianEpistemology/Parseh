# Where the fixtures come from

What the tests read and build, and whose it is. Everything here that was
written for the tests is Parseh's, under its licence (`GPL-3.0-or-later`,
`LICENSE` at the top). What was not is listed with its source and its own
licence. A fixture added later says where it comes from here, or beside
itself, as `verbs/README.md` and `align/cases.json` do.

## Books: `books/<language>/mini-<code>/`

Two paragraphs each, chunked and glossed. Each `book.json` says in its
`blurb` what the fixture is for.

| Fixture | Title | The text |
|---|---|---|
| `mini-en` | *The Clock and the Wind* | written for the tests |
| `mini-fr` | *Le vieil homme et l'arbre* | written for the tests |
| `mini-de` | *Der Schuster in der Straße* | written for the tests |
| `mini-es` | *El panadero y la niña* | written for the tests |
| `mini-tr` | *Yağmurlu bir kış* | written for the tests |
| `mini-hi` | *किसान की अँगूठी* | written for the tests |
| `mini-zh` | *山下的村子* | written for the tests |
| `mini-ar` | *الثعلب والعنب* | Aesop's fox and the grapes, retold for the tests |
| `mini-ja` | *桃太郎* | the opening of Momotaro, a folk tale, in the words it is always told in |
| `mini-it` | *Il pezzo di legno* | the first two sentences are the opening of Carlo Collodi's *Le avventure di Pinocchio* (1883), word for word; the second paragraph retells what follows, in simpler words. Collodi died in 1890: public domain. |
| `mini-fa` | *فارسی شکر است* | the first two paragraphs, about 1,050 words, of Mohammad-Ali Jamalzadeh's story *Farsi shekar ast* (*Persian is sugar*), from *Yeki bud, yeki nabud* (Berlin, 1921) — taken from the edition that used to sit at `books/persian/farsi-shakar-ast` |

**`mini-fa` is not free everywhere.** It was published in 1921, so it is in
the public domain in the United States. Jamalzadeh died in 1997, so it is
still protected until the end of 2067 wherever a work is protected for
seventy years after its author's death, as in the European Union. It is the
one text here that is neither written for the tests nor free everywhere.

## Videos: `videos/<language>/<id>/`

Eleven short dialogues for beginners, one per language — at the market, at
the café, in a bookshop — written for the tests. So are their annotations.
The channel, *Fixture Channel*, and the eleven-character ids are made up:
no address here is a real video.

## Anki decks: `anki/<language>/parseh-test-<code>/`

Two cards per language, made up for the tests. Each `deck.json` says what
it is in its `_comment`.

## Studio documents: `studio/`

- `feature-test/`, `exercises/`, `audio/`: written for the tests of the
  studio's Markdown dialect — every construct, every kind of exercise, and
  recordings on the page and on cards. Their pictures (`swatch.png`,
  `pattern.png`), the recording (`greeting.mp3`) and `formulae-sample.pdf`
  are small test files; where each was made is not recorded.
- `persiano/`: a studio note in Italian on four Persian words for slow and
  fast. Where it was written is not recorded.

## Cases: `verbs/`, `align/`, `wordline.json`

- `verbs/<code>.json`: conjugation rows cut from Wiktionary, through the
  kaikki.org extracts. **CC BY-SA 4.0**, as Wiktionary's text is;
  `verbs/README.md` says how they were cut.
- `align/cases.json`: machine translations by Mozilla's Firefox
  Translations models of the fixture books' and videos' sentences, and of
  sentences from Tatoeba (**CC BY 2.0 FR**), with dictionary lookups from
  Wiktionary (**CC BY-SA 4.0**). Its `_source` key says so.
- `wordline.json`: cases of the word line's grammar, written for the tests.
