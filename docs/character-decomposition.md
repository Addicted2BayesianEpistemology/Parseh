# Character decomposition

Install component packs from **Settings → Reading help**, on the Japanese or
Chinese card's *Character components* row (`/settings/reading-help/#character-components`;
the old `/lookup/#character-components` redirects there, fragment kept), beside the
dictionary, corpus and translation installers; CJKVI-IDS is on the card shared by
every language. The reader button also links there if nothing is installed.

- **KanjiVG** is the preferred Japanese pack.
- **Make Me a Hanzi** is the preferred Chinese pack.
- **CJKVI-IDS** is a separate, optional fallback for both languages.

In a book or video, choose **Decompose Kanji** or **Decompose Hanzi**, then
click/tap an outlined character. Kana and punctuation are excluded. Keyboard
users can Tab to a character and press Enter or Space. The modal shows connected
components and their meanings from the dictionary already installed for that
language. Missing dictionary entries say “Meaning unavailable”; decomposition
itself does not require a dictionary.

Select a component to explore it, then use **Back** or **Return to**. Closing the
modal leaves selection mode active for another character. **Escape** closes the
modal first and leaves the mode on a second press. **Done** or the original
button also leaves the mode. Opening a tree pauses playback; resume playback
with the reader's normal controls. Normal word, copy, Anki and playback clicks
are suppressed while a character is being selected.

After updating a running installation, restart the Parseh server and rebuild
existing book readers with the usual build command so their generated HTML links
the new viewer assets. Video pages use the new assets when reloaded.

## Local data and provenance

Installation downloads a pinned source revision, checks its SHA-256, converts
only component structure, and atomically publishes `components/<source>.db`.
A failed rebuild keeps the previous pack. No dataset is installed by default or
committed to this repository. Remove/rebuild buttons are on the same setup page.
The installer uses Python's standard library and requires no extra runtime package.

| Source | Structure imported | Licence / upstream notice |
| --- | --- | --- |
| [KanjiVG](https://github.com/KanjiVG/kanjivg) | Named SVG component groups | [CC BY-SA 3.0; Ulrich Apel and contributors](https://github.com/KanjiVG/kanjivg/blob/master/COPYING) |
| [Make Me a Hanzi](https://github.com/skishore/makemeahanzi) | Only `character` and `decomposition` from `dictionary.txt` | [LGPL 3.0 or later](https://github.com/skishore/makemeahanzi/blob/master/COPYING) |
| [CJKVI-IDS](https://github.com/cjkvi/cjkvi-ids) | `ids.txt`, selecting language-appropriate variants | [GPLv2 / CHISE provenance](https://github.com/cjkvi/cjkvi-ids#licenses) |

Each pack remains separate and retains its own licence, attribution, upstream
revision, source URL, checksum, notices and description of the conversion in its
SQLite `meta` table (`manifest` entry). These source licences continue to apply to
the converted data; the application's licence does not replace them. Keep these
notices and consult the upstream terms if redistributing a pack. The viewer
credits every source actually used, including fallback nodes.

No SVG artwork, path coordinates, definitions, pronunciations, readings or
etymologies are imported. Make Me a Hanzi's graphics/font data is not downloaded.
Inspection calls only the local Parseh server, which reads SQLite and the
existing local dictionary. It makes no external request.

Command-line alternatives, using the application's Python environment:

```sh
python3 lib/getdecomposition.py kanjivg
python3 lib/getdecomposition.py makemeahanzi
python3 lib/getdecomposition.py cjkvi
```

For offline installation, pass `--input`: a KanjiVG repository ZIP containing
`kanji/*.svg`, Make Me a Hanzi's `dictionary.txt`, or CJKVI's `ids.txt`.
Keep upstream notices beside local text files (`COPYING` and `LGPL` for Make Me a
Hanzi, `README.md` for CJKVI); KanjiVG's `COPYING` is read from its archive.
Custom local revisions are labelled “local import” and retain their checksum.

## Implementation

- `lib/decomposition_sources.py` contains the source-specific importers and strict
  IDS parser. All standard enclosure, binary and ternary operators are handled,
  together with reflection, rotation and subtraction operators. Unknown/unencoded
  components remain explicit leaves rather than invented characters.
- `lib/decomposition.py` supplies the shared domain model, pack status, recursive
  local lookup, source preference, and the adapter to the existing dictionary.
- `lib/getdecomposition.py` owns download, verification and atomic installation.
- `lib/decomposition.js` and `.css` provide the shared mode and accessible native
  dialog; the two readers supply their language, text scope and playback hooks.
- `serve.py` exposes `/lookup/api/decompositions`, `decompose`, `getdecomposition`
  and `dropdecomposition`. Installation runs in a background job with progress,
  with concurrent rebuild/removal guarded per source.

A normalized node has optional `character`, `operator`, `children`, and `source`.
Additional fields describe unknown components (`kind`), contextual variants
(`variantOf`, `partial`), stopping state (`status`), and bounded expansion
(`truncated`). Dictionary meanings are returned separately, never stored in the
component packs. Structural nodes render as descriptive layout labels, not raw
IDS expressions.

KanjiVG anonymous graphical wrappers are flattened, duplicate stroke-order parts
are coalesced, and paths are excluded. The original named hierarchy is kept.
Some familiar components such as 木, 目 and 心 stop automatic expansion to keep
trees readable; selecting one as the root can reveal its finer source structure.
Expansion is bounded and detects cycles. Missing data and source-defined atomic
components have distinct messages. An ideographic variation selector is retained
in the displayed character; when its base entry is used, the viewer says so.

The UI uses Unicode-aware graphemes and ideographs, including supplementary
planes. It wraps eligible text temporarily, excludes ruby readings and controls,
and removes its wrappers when the mode ends. The original ruby/word containers
remain intact. Dynamically redrawn video text is handled while the mode is active.

## Checks

```sh
python3 -m unittest discover -s tests -p test_decomposition.py
python3 tests/smoke.py --only js,books,videos,server
CHROME_BIN=/path/to/chrome PARSEH_PYTHON=python3 \
  deno run --allow-all tests/decomposition.mjs
```

Browser checks use Playwright Core through Deno and intercept all requests. They
cover books and videos, touch input, keyboard navigation, Unicode, unchanged ruby
text, suppression of normal reader actions, missing data, retries, optional setup,
and language gating. `PARSEH_TEST_ARTIFACTS` can set the screenshot output folder.
