#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The toolbox tests/mobile_pages.mjs drives: the REAL hub (serve.main) on a
temporary tree, with books and exercise decks to read and study in the
mobile interface (docs/mobile.md).

    python3 tests/mobile_harness.py build <tmp>
        makes <tmp>/root with the fixture editions of six languages, each
        reader built -- English narrated (tests/cardkit_harness.py's tone
        recording and its timings, and its film under youtube/videos/),
        Persian, Arabic, Japanese, Hindi and Chinese -- and the Italian one
        copied but NOT built; the book library page written into the tree; and under
        <tmp>/exercises three decks: an English one with a flashcard and
        four scored exercises, tagged (EN_TAGS), a Persian one with two
        flashcards, and an empty Italian one.  Prints one line of JSON
        saying what is where.
    python3 tests/mobile_harness.py serve <tmp> <port>
        serve.main() on 127.0.0.1:<port> over <tmp>/root -- the books, the
        studio library, the exercise decks, the Anki store and the clip tray
        all inside <tmp>, as tests/cardkit_harness.py serves it, and the
        book shelf read from the tree as well (the hub's counts, /m/books/).

Never touches the real books/, exercises/, markdown/library/ or clips/:
the library page is written into the tree by make_index with its paths
pointed there, because the server's own way of writing it -- a subprocess
of lib/make_index.py from the repository -- would write the real one.
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for folder in ("markdown/exlex", "markdown/app", "youtube/lib", "lib", "tests", "."):
    sys.path.insert(0, str(REPO / folder))

# the editions besides cardkit_harness's narrated English one: (folder, slug,
# built) -- both right-to-left scripts, Devanagari, the two with readings over
# their words, and one never built
BOOKS = [("persian", "mini-fa", True), ("arabic", "mini-ar", True), ("japanese", "mini-ja", True),
         ("hindi", "mini-hi", True), ("chinese", "mini-zh", True), ("italian", "mini-it", False)]

EN_DECK = [
    """:::exercise flashcard
card-type: vocab
target: [knight]{tl}
transliteration: naɪt
meaning: a soldier of high rank in the Middle Ages, who fought on horseback
context: [The knight rode home through the night.]{tl}
:::""",
    """:::exercise single-choice
prompt: Which article goes before [apple]{tl}?
- [ ] [a]{tl}
- [x] [an]{tl}
- [ ] [the both]{tl}
explanation-correct: [an]{tl} comes before a vowel sound.
explanation-incorrect: Before a vowel sound the article is [an]{tl}.
:::""",
    """:::exercise fill-blanks
prompt: Complete the sentence with the past of [go]{tl} and of [buy]{tl}.
text: [Yesterday I [[go]] to the market and [[buy]] two apples.]{tl}
- [go] [went]{tl}
- [buy] [bought]{tl}
- [ ] [goed]{tl}
explanation-correct: Right: [went]{tl} and [bought]{tl}.
:::""",
    """:::exercise order-sentences
prompt: Put the steps in order.
- [1] [First, wash the apple.]{tl}
- [2] [Next, cut it into four pieces.]{tl}
- [3] [Finally, eat the pieces.]{tl}
explanation-correct: [First]{tl}, [next]{tl}, [finally]{tl}.
:::""",
    """:::exercise match-translations
prompt: Match each British word with the American one.
- [flat]{tl} => [apartment]{tl}
- [lift]{tl} => [elevator]{tl}
- [biscuit]{tl} => [cookie]{tl}
:::""",
]
# the English exercises' tags, one list to an exercise: what "Select by tag"
# picks a cram from (grammar: the article and the past, two of the five)
EN_TAGS = [["words"], ["grammar"], ["grammar", "verbs"], [], ["words"]]
FA_DECK = [
    """:::exercise flashcard
card-type: vocab
target: [کتاب]{tl}
transliteration: ketāb
meaning: book
context: [این کتاب را خواندم.]{tl}
:::""",
    """:::exercise flashcard
card-type: vocab
target: [آب]{tl}
transliteration: āb
meaning: water
:::""",
]


def built_reader(book):
    """tex2html over one edition, with the reader's relative climb to lib/
    (from the tree to the repository) written as the hub's own absolute
    path, as tests/cardkit_harness.py does."""
    r = subprocess.run([sys.executable, "lib/tex2html.py", "--book", str(book)],
                       capture_output=True, text=True, cwd=str(REPO))
    if r.returncode:
        raise SystemExit(r.stderr or r.stdout)
    out = book / "reader"
    climb = os.path.relpath(str(REPO), str(out)).replace(os.sep, "/") + "/"
    for page in out.glob("*.html"):
        text = page.read_text(encoding="utf-8")
        page.write_text(text.replace(climb, "/"), encoding="utf-8")


def library_page(root):
    """books/index.html, written into the tree (see the module's docstring)."""
    import books
    import languages
    import make_index
    # a book's address under /books/ is its directory relative to books/
    # (Book.rel_from_books), asked of the module's own BOOKS_DIR
    books.BOOKS_DIR = str(root / "books")
    make_index.BOOKS_DIR = str(root / "books")
    make_index.LIB = str(root / "lib")
    make_index.all_books = lambda: books.all_books(str(root / "books"))
    languages.write_css = lambda *a, **k: None
    with contextlib.redirect_stdout(io.StringIO()):
        make_index.main()


def build(tmp):
    os.chdir(str(REPO))
    import cardkit_harness
    with contextlib.redirect_stdout(io.StringIO()) as said:
        cardkit_harness.build(tmp)
    made = json.loads(said.getvalue().strip().splitlines()[-1])
    root = tmp / "root"
    readers = {"en": made["reader"]}
    for folder, slug, build_it in BOOKS:
        book = root / "books" / folder / slug
        book.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(REPO / "tests/fixtures/books" / folder / slug, book,
                        ignore=shutil.ignore_patterns("reader"))
        if build_it:
            built_reader(book)
            readers[json.loads((book / "book.json").read_text(encoding="utf-8"))["language"]] = \
                "/books/%s/%s/reader/" % (folder, slug)
    library_page(root)

    import decks
    decks.set_dir(tmp / "exercises")
    out = {}
    for name, lang, items, tags in (("Everyday English", "en", EN_DECK, EN_TAGS),
                                    ("Persian words", "fa", FA_DECK, [None] * len(FA_DECK)),
                                    ("Nothing yet", "it", [], [])):
        d = decks.create_deck(name, lang)
        for md, tag in zip(items, tags):
            decks.add_item(d["folder"], d["slug"], md, tags=tag)
        out[lang] = {"folder": d["folder"], "slug": d["slug"], "name": name, "items": len(items)}
    print(json.dumps({"readers": readers, "unbuilt": "/books/italian/mini-it",
                      "decks": out, "video": made["video"]}, ensure_ascii=False))


def serve_it(tmp, port):
    import books
    import make_index
    here = str(tmp / "root" / "books")
    whole = books.all_books
    books.all_books = lambda root=None, language=None: whole(root or here, language)
    books.BOOKS_DIR = here                  # what a book's address is relative to
    make_index.all_books = lambda: whole(here)
    import cardkit_harness
    cardkit_harness.serve_it(tmp, port, False, "tray")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "build":
        build(Path(sys.argv[2]))
    elif len(sys.argv) >= 4 and sys.argv[1] == "serve":
        serve_it(Path(sys.argv[2]), int(sys.argv[3]))
    else:
        sys.exit(__doc__)
