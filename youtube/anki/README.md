# Anki decks

Every deck the card dashboards write lives here, **filed under its
language** — one folder per language, as everything else in the toolbox is
(`docs/languages.md` sections 2 and 4). BOTH dashboards — the video
player's (`/youtube/`) and the book reader's (`/books/`), served together
by Parseh — share this store: one collection, whatever the card came from.
A card carries its provenance (`video` or `book`), and one deck mixes those freely:

```
anki/<folder>/<slug>/deck.json        the deck's name, language and fixed Anki id
anki/<folder>/<slug>/cards/<id>.json  one card per file — the ground truth
anki/<folder>/<slug>/media/           the screenshots and recordings those cards reference
anki/<folder>/<slug>/deleted/         cards retired by a sync (see below)
anki/notetypes.json                   what the live collection's note types look like
anki/seen.json                        every note guid an export has shown us
anki/inbox/                           .apkg files dropped on the sync wizard
anki/build/<folder>-<slug>.apkg       built packages (derived; not versioned)
```

`<folder>` is the registry's folder name — the `folder` field of the
language's entry in `../../lib/languages.json`; the registry is the list of
languages, and nothing here keeps a second one. The four collection-level
entries sit directly under `anki/` because they are collection-wide in Anki
too — a note type, the record of what Anki has seen, one inbox, one build
directory.

**A deck's language.** `deck.json` carries `"lang": "<code>"`; absent, the
deck is of its folder's language, and a deck lying **directly under
`anki/`** — the layout from before languages — is read as Persian, like
every other piece of content written before languages were declared. Such
a deck still works everywhere: it is listed, built, synced and imported
into. It is *reported* once on stderr, saying where it belongs, and
**nothing here ever moves it**: this is your store, and a tool that
rehomed a studied deck behind your back would break every path you have
written down. Move it yourself when you like.

**Two languages may hold a deck of the same name**, and so of the same
slug — `anki/persian/videos/` and `anki/japanese/videos/` are two decks,
and nothing addresses a deck by slug alone any more. The store's own
handle is the deck's `path` (`japanese/videos`), and the build URL is
`/anki/build/<folder>/<slug>.apkg`. The one-level `/anki/build/<slug>.apkg`
still answers while the slug names exactly one deck, and otherwise says
which two it could mean. The built package is named
`<folder>-<slug>.apkg` for the same reason: two languages' decks of one
name must not overwrite each other in `build/`.

**A card goes to the deck of its own language.** The dashboards offer
this page's language's decks first (the others are still listed, under
their language's heading), but the card's `lang` decides where it is
filed: post a Japanese card to a deck the Persian side named, and it
lands in the Japanese deck of that name — the answer says so and the
dashboard tells you. A deck name already used *in that language* reuses
its directory, including a legacy one directly under `anki/`.

A card records its **language** (`lang`, a code of the registry
`../../lib/languages.json`; absent means Persian, which every card written
before languages existed is) and its text under `fa` — the key is named
after Persian, the toolbox's first language, and holds the target-language
text whatever the language. A card of a **reading language** (Japanese)
carries the kana reading beside the transliteration: `kana` next to `tr`,
and `opp_kana` next to `opp_tr` on an opposites card. A card's `lang`
agrees with the folder its deck is in, because the store put it there;
`lang` is also what picks its note type at build, so a wrong one is
refused rather than guessed. Deck *names* are yours — the dashboards
suggest the language's own nesting (`Japanese::Videos`) — and the tag is
`<tag>-youtube` / `<tag>-book` with the language's registry tag
(`farsi-youtube` stays exactly what it was; `arabic-book`,
`japanese-youtube`).

There are two **kinds** of note type, chosen by the card's `kind`, and
**one pair of them per language**:

- **`vocab`** (the default): the target word on one side, the meaning on
  the other. Its **direction** is a three-way choice: *both* (two cards),
  *target → English only*, or *English → target only* (`reverse_only`,
  via the `ReverseOnly` field — non-empty suppresses the forward card).
  The third one exists for a meaning whose target side lists several
  words — e.g. *body* → تن / بدن: one reverse-only note shows both words
  as the answer, while each word has its own forward-only note asking it
  alone; three cards, no overlap.
- **`opposites`**: the card asks *"what is the opposite of X?"* and the
  answer is the opposite word (fields `opp` / `opp_tr`, plus `opp_kana`
  for Japanese); bidirectional asks it the other way round too. Both
  dashboards have a **type** toggle that switches the form — the opposite
  itself is always written by hand.

The **Persian pair is the original one** and keeps its ids, names, fields
and templates byte for byte: `1724563200001` *Frank YouTube Persian*
(`Persian, Transliteration, English, Context, Notes, FrontImage,
BackImage, Source, Reverse, ReverseOnly`) and `1724563200002` *Frank
Persian Opposites* (`Persian, Transliteration, Opposite, OppositeTr,
Notes, FrontImage, BackImage, Source, Reverse`). Every other language gets
a pair of its own, with the ids and names the registry's `anki` record
gives (`anki.vocab_model` / `anki.opposites_model`, minted ten apart on
the `1724563200000 + 10n` grid, so the second language holds
`…011`/`…012`), the first field named after the language (`anki.field`),
and — for a reading language only — a `Reading` field after it in the
vocab type and a `Reading` plus an `OppositeReading` in the opposites
type. Their templates are the Persian ones with the field renamed, a
reading line under the text where there is one, and the CSS `direction`
set from the language.
Different languages are different note types for the same reason
opposites are: a note type's shape can never change once notes have been
studied with it, so the Persian one could not grow a field.

**A recording on a card, with no note-type change.** The card sheet's
*cut the audio…* button cuts the word or the sentence out of the book's
narration or the film into the clip tray (`clips/`, see
`../../clips/README.md`), and the card is sent with
`"clip": {"side": "front"|"back", "name": "<tray name>"}`. The store copies
the clip to `media/<id>-<side>-audio.<ext>` and records it on the card as
`snd_front` / `snd_back` (a file name in `media/`, or null), beside
`img_front` / `img_back`. There is no audio field: the export writes
`[sound:<file>]` into `FrontImage` / `BackImage`, after the picture when
there is one, because those two fields already sit on the right side of
every template — the captured ones too — and a note type's shape can
never change (below). Anki plays a `[sound:]` wherever a card shows it,
and the package's deck options autoplay it. The package carries the
recordings like the screenshots; `import_apkg.py` and `sync_apkg.py` read
`[sound:]` back out of the two fields into `snd_front` / `snd_back` and
copy the files out. The dashboard's preview plays the clip from the tray.

Build a deck into an importable package with the dashboard's
**build .apkg** button, or by hand:

```
python3 lib/anki_export.py anki/<folder>/<slug>
```

which writes `anki/build/<folder>-<slug>.apkg`.

The card JSONs are the source of truth: edit one and rebuild, and the
re-imported note updates in place (its GUID is minted once, at save).
Studying is never disturbed by a re-import — Anki keeps the scheduling of
existing cards and only adds the new ones. Deleting a card's JSON removes
it from future builds, but Anki never deletes notes on import; prune those
in Anki itself.

The note types' identities are one table, `anki_export.MODELS`, keyed by
model id → `{lang, kind, fields, name}` and built from the registry;
`import_apkg`, `sync_apkg`, `notetypes` and `check_shape` all read it and
none holds a second list. A note's GUID (with the field lists) alone
identifies it — if a note type's shape ever changes, Anki will refuse to
update the notes already studied with it. That is exactly why the
opposites are a SEPARATE note type instead of extra fields on the first
one, and why each language has note types of its own. The one shape
change ever made — the `ReverseOnly` field appended to the vocab type —
was made *inside Anki first* (Anki migrates its own collection safely)
and then mirrored here field-for-field and template-for-template from the
collection's export, so the two sides agree byte for byte. Any future
shape change must travel the same road: change it in Anki, export, and
teach the exporter to match — never the other way round.
A .apkg carries only the note types its deck actually uses, and only the
**media** its languages need: the first web face the registry names for a
language (`fonts.web_files`) rides along — Vazirmatn for Persian, Noto
Naskh Arabic for Arabic — and a language that names none relies on the
device's own fonts, so nothing is added for it.

## Bringing a deck the other way — Anki back into this store

The one-way flow above (JSON → `.apkg` → import into Anki) is only half
the story: once a deck is imported and lived in, the *live* copy is the
one inside Anki — renamed, maybe reorganised, maybe reviewed for months.
If this `anki/` directory is ever reset (a fresh checkout, a wiped
folder) while Anki itself still has the deck, drop the current export
from Anki (*Export → Anki Deck Package*, include scheduling is fine, it
is ignored) into this directory and run:

```
python3 lib/import_apkg.py "anki/Persian CI.apkg"
```

It reads the package (modern zstd-compressed export, Anki 2.1's plain
`collection.anki21`, or the older `collection.anki2`), and for every
note that uses one of this project's own note types (any language's pair,
recognised by the model ids in `MODELS`), writes a card
JSON under `anki/<folder>/<slug>/cards/` — the folder being the language
of the note type most of that deck's notes use (`anki_export.MODELS` is
the one table saying which language a note type belongs to) — **preserving
the exact GUID and the exact Anki deck id and name**, both taken straight
from the package —
and copies every image and recording a card names out of it. A card sitting in a
filtered deck is filed under its home deck. A note carrying formatting
the store cannot hold (HTML typed inside Anki) comes in as an anki-owned
mirror, exactly as the sync would treat it (see *Keeping edits made
inside Anki*), so a rebuild never flattens it. That is what lets a future rebuild land back in the
very same deck on re-import (Anki matches by id, falling back to name)
instead of spawning a disconnected sibling, and lets an existing note be
updated in place rather than duplicated. A note of any *other* note type
(a stock Basic card, say) is reported and skipped rather than guessed
at — bring those over by hand.

`Persian CI.apkg` is exactly this: the deck built here as
`Farsi::Old flashcards` (see below), imported into Anki, and renamed
`Persian CI::Old flashcards` there. `lib/import_apkg.py` was run once to
bring that live state back into `anki/persian/persian-ci-old-flashcards/`,
which is what both dashboards' deck picker now offers under *Persian*.

## How the cards LOOK — styling and templates

A note type carries more than its fields: it carries the CSS the cards
wear and the card templates that decide what each side asks. Those live
in the **note type**, not in any note — so nothing under
`anki/<folder>/<deck>/cards/` can hold them, and a rebuild used to re-assert the
styling hard-coded in `lib/anki_export.py` over whatever had been set
inside Anki.

A sync (or a bootstrap import) now snapshots every one of this project's
note types the export carries — name, field names, CSS, and each
template's `name`/`qfmt`/`afmt`, per language — into one collection-level
file:

```
anki/notetypes.json
```

Note types are collection-global, so this sits directly under `anki/`,
beside the language folders rather than inside a deck. `seen.json` is
collection-level for the same reason: an Anki guid is collection-wide, so
a note moved between two decks — or between two languages — is still the
same note. `anki_export.py` **prefers** what is captured there over
its own constants when building a package and when rendering the
dashboard preview; the constants remain the fallback for a store that has
never seen an export. So: restyle a card inside Anki, export, sync — and
every future rebuild reproduces that styling instead of overwriting it.
Styling is captured **per note type**, so changing the opposites cards
leaves the vocabulary cards alone.

**The export is the source of truth.** If you change styling in Anki and
then sync an export taken *before* that change, the old styling is what
gets captured — and the next rebuild would push it back. Always
re-export after changing a note type, then sync.

### A shape change stops the build

If the captured field list disagrees with the one `MODELS` gives for that
model id, or the captured template count is not 2, `build_deck`
**refuses to build** and names the difference. This is
deliberate: a note's values are written positionally and Anki matches a
note type by id, so emitting a mismatched model would either scramble
every note or make Anki fork a second note type and orphan the review
history of everything already studied. Teach the exporter the new shape
first — the road the `ReverseOnly` field travelled.

## Keeping edits made inside Anki — sync before you export

Importing a rebuilt `.apkg` stamps every note "modified now", so for any
guid the deck already holds, **the import overwrites whatever was edited
inside Anki** since the last one. If the deck has been touched in Anki —
fields corrected, tags changed, a reverse card removed — pull those edits
home *first*, then rebuild:

```
# in Anki:  File → Export → Anki Deck Package (media too, if images changed)
python3 lib/sync_apkg.py "path/to/Persian CI.apkg" --dry-run   # look first
python3 lib/sync_apkg.py "path/to/Persian CI.apkg"             # then merge
python3 lib/anki_export.py anki/persian/persian-ci-old-flashcards   # rebuild
# import the rebuilt .apkg into Anki: only genuinely new cards change it
```

The sync matches notes to card files **by guid**, whatever the files are
named, and Anki's version wins for every note Anki knows — that is the
point. What one run does:

- **fields edited in Anki** → the store card is updated in place (same
  file, same id, same provenance) — including a note moved to a
  different deck (it is updated in the deck where the store holds it,
  and the move is reported) and an image whose bytes were edited under
  its old filename;
- **a note created inside Anki** with one of this project's note types →
  added to the store as a normal card;
- **a note whose type was changed inside Anki** (*Change Note Type →
  Basic*, say) → the store card becomes an **anki-owned mirror**: guid
  kept, the note's model name and raw fields recorded, and
  `build_deck` **excludes it from every future `.apkg`**. Since imports
  never delete notes, that note now lives in Anki alone, permanently out
  of this pipeline's reach — edits to it can never clash again;
- **a new note of a foreign type** → added as an anki-owned mirror too;
- **a project note carrying formatting the store cannot hold** (bold,
  colours, extra HTML typed into a field inside Anki) → also anki-owned,
  reported as *kept in Anki* — a normal update would flatten the
  formatting on the next export. Strip the formatting inside Anki and
  the next sync reclaims the card automatically;
- **a card in the store the export doesn't carry** → split into two very
  different cases, because only one of them is a deletion:
  - **deleted inside Anki** — the collection has held this note before
    and no longer does. With deletions turned on (the wizard's checkbox,
    or `--delete-missing`) the card is **retired**: stamped with when and
    why, then *moved* to `anki/<folder>/<deck>/deleted/` rather than
    unlinked.
    `build_deck` reads only `cards/`, so it stops being exported at once,
    and moving the file back is a complete undo. Deleting the note in
    Anki is Anki's business; this only stops re-asserting it.
  - **here but not in Anki yet** — made on the websites since the last
    import, so Anki has never seen it and its absence means nothing.
    Never touched; the next import is what gives it to Anki.

- **a retired card whose note is back in Anki** → **un-retired**: its own
  file comes back out of `deleted/`, keeping its id and provenance,
  rather than a second file being minted for the same note.

  The two are told apart by whether Anki has ever *confirmed* the note:
  its guid appears in `anki/seen.json` (written on every real sync with
  every guid the export carried), or its file is `apkg-<guid>.json`,
  which is only ever written from an export. A card with neither witness
  has only ever existed here and is never removed. Both witnesses are
  weighed across *every* file carrying that guid, not just the one the
  index happens to hold. Losing `seen.json` is not catastrophic but is
  not a no-op either: cards whose only witness was that file stop looking
  known and are never proposed for removal, while `apkg-*` cards still
  are, on their filename alone.

  A note absent from the deck being synced but present *anywhere else in
  the package* is a **move**, never a deletion — the parent of a nested
  deck is the ordinary case.

  Two things the sync refuses outright, because each would teach the
  store a falsehood about what Anki holds:

  - **the `.apkg` this tool built.** `build_deck` stamps its output and
    the sync stops on that stamp. It is a valid package sitting in the
    same downloads folder as a real export, and syncing it would mark
    every card in it as confirmed by Anki — after which the next genuine
    export, lacking the ones never imported, would look like a mass
    deletion. It is not a dead end, though: see *A package built by
    Parseh* below.
  - **bootstrapping a deck the store already holds** from an export.
    `import_apkg.py` matches on the Anki deck *id* across the whole store
    (so a deck renamed inside Anki is still recognised) and skips it; the
    wizard's per-deck button now names the one deck it means.

## A package built by Parseh — someone else's cards, or your own from another computer

The `.apkg` the build button makes is the only thing that needs to travel
between two copies of Parseh: its notes carry the right note types and
fields, its media rides along, and the deck id is in it. Drop it on the
sync wizard like any export, or on the command line:

```
python3 lib/import_apkg.py "shared.apkg"            # decks the store does not hold yet
python3 lib/import_apkg.py "shared.apkg" --merge    # also add the new cards of decks it holds
```

The stamp is recognised and the package is **brought in, never synced**:
a deck the store lacks is created under the package's own deck id and
name, a deck already held is given only the cards it lacks (matched by
guid, so nothing here is overwritten), and every image a card names is
copied out of the package. Its cards are filed as `pkg-<guid>.json` —
unlike `apkg-<guid>.json`, that name is *not* taken as Anki's word that
the note exists, so a later genuine export that lacks them reads as
*here, not in Anki yet*, never as a deletion. Then build the deck, import
that into Anki, and from there on export from Anki and sync as usual.

Run it twice and the second run reports everything unchanged: the sync
is idempotent.

### Splitting a card's two directions apart

Two roads, by weight:

- **Just killing the reverse**: empty the note's `Reverse` field inside
  Anki (the reverse template is gated on it). The sync brings that home
  as `bidirectional: false`; the card stays a normal project card.
- **Making the directions say different things** (e.g. a word with two
  translations, wanting one forward card showing both and two separate
  reverse cards): do it entirely inside Anki — duplicate the note
  (*Browse → Notes → Create Copy*), then *Change Note Type → Basic* on
  each copy with the field mapping putting each direction's content into
  its own Front/Back — and then run the sync. Both notes come back as
  anki-owned mirrors, the exporter steps back from them for good, and
  from then on they are ordinary Basic notes you edit in Anki alone.
  Nothing here will ever overwrite or resurrect them.

## The old Obsidian flashcards

Delete the section, or mark it as history: the Obsidian import was a one-off whose script is no longer in the repository.
`extract` parses every vault file's spaced-repetition card blocks;
curation (done once, by hand/agents) keeps only the ones that expand
vocabulary — no grammar, no usage explanations, opposites pairs kept as
`kind: "opposites"`; `write` turns the curated list into cards here, one
JSON per card, exactly the shape the dashboards save. Re-running `write`
is a no-op for cards already on disk (it seeds its dedupe from the
existing deck), so it is safe to run again after adding more files to
curate.
