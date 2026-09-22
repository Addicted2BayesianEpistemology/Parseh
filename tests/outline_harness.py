#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The toolbox tests/outline.mjs drives: the REAL server (serve.main, as
tests/mobile_harness.py runs it) over a temporary tree holding one book of
three chapters -- mini-en's one chapter three times over, as chapters 1 to 3,
so that EVERY CHAPTER HAS THE SAME LABELS, 1.1 1.2 2.1 2.2.  Each chapter is
given words of its own (a subparagraph's times are filed under its label and a
hash of its text, and copies would share them); chapters 1 and 2 are named,
chapter 1 has one section and chapter 2 two.

    python3 tests/outline_harness.py build <tmp>
        makes <tmp>/root/books/english/outline-en, its reader built, and two
        six-second tones beside the tree, <tmp>/part-a.wav and part-b.wav, to
        add as recordings.  Prints one line of JSON saying where.
    python3 tests/outline_harness.py serve <tmp> <port>
        serve.main() on 127.0.0.1:<port> over <tmp>/root.
    python3 tests/outline_harness.py relink <tmp>
        the reader built again, its climb to lib/ written as the hub's own
        path -- after a door has rebuilt it the way the real checkout wants.

Never touches the real books/, exercises/, markdown/library/ or clips/.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for folder in ("markdown/exlex", "markdown/app", "youtube/lib", "lib", "tests", "."):
    sys.path.insert(0, str(REPO / folder))

SLUG = "outline-en"


def book_dir(tmp):
    return tmp / "root" / "books" / "english" / SLUG


def make_book(d):
    """The book itself, at `d` (a books/<folder>/<slug> directory), not built:
    what tests/test_regions.py reads without a server."""
    import structure
    d = Path(d)
    shutil.copytree(REPO / "tests/fixtures/books/english/mini-en", d,
                    ignore=shutil.ignore_patterns("reader"))
    src = (d / "ch1.tex").read_text(encoding="utf-8")
    for k, word in ((2, "Then"), (3, "So")):
        (d / ("ch%d.tex" % k)).write_text(
            src.replace("\\chapopen{1}", "\\chapopen{%d}" % k)
               .replace("\\ch{}{", "\\ch{}{%s " % word), encoding="utf-8")
    main = (d / "main.tex").read_text(encoding="utf-8")
    (d / "main.tex").write_text(
        main.replace("\\input{ch1.tex}", "\\input{ch1.tex}\n\\input{ch2.tex}\n\\input{ch3.tex}")
            .replace("\\BookTitle}{The Clock and the Wind}", "\\BookTitle}{Three Clocks}"),
        encoding="utf-8")
    meta = json.loads((d / "book.json").read_text(encoding="utf-8"))
    meta.update(slug=SLUG, title="Three Clocks", title_latin="Three Clocks")
    (d / "book.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
    structure.set_chapter_name(str(d), 1, "The Clock")
    structure.set_chapter_name(str(d), 2, "The Wind")
    structure.set_section(str(d), 1, 2, "The Child")
    structure.set_section(str(d), 2, 1, "Morning")
    structure.set_section(str(d), 2, 2, "Evening")
    return d


def build(tmp):
    os.chdir(str(REPO))
    import mobile_harness
    root = tmp / "root"
    for d in (root / "youtube" / "videos", tmp / "library", tmp / "exercises",
              tmp / "anki", tmp / "tray"):
        d.mkdir(parents=True, exist_ok=True)
    os.symlink(str(REPO / "lib"), str(root / "lib"))
    os.symlink(str(REPO / "youtube" / "lib"), str(root / "youtube" / "lib"))
    d = make_book(book_dir(tmp))
    mobile_harness.built_reader(d)
    for name, hz in (("part-a.wav", 440), ("part-b.wav", 660)):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", "sine=frequency=%d:duration=6" % hz, "-ac", "1", "-ar", "8000",
                        str(tmp / name)], check=True)
    print(json.dumps({"reader": "/books/english/%s/reader/" % SLUG, "book": str(d),
                      "tones": [str(tmp / "part-a.wav"), str(tmp / "part-b.wav")]}))


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "build":
        build(Path(sys.argv[2]))
    elif len(sys.argv) >= 3 and sys.argv[1] == "relink":
        os.chdir(str(REPO))
        import mobile_harness
        mobile_harness.built_reader(book_dir(Path(sys.argv[2])))
    elif len(sys.argv) >= 4 and sys.argv[1] == "serve":
        os.chdir(str(REPO))
        import mobile_harness
        mobile_harness.serve_it(Path(sys.argv[2]), int(sys.argv[3]))
    else:
        sys.exit(__doc__)
