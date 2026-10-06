#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The toolbox tests/review_later.mjs drives: the REAL hub (serve.main) on a
temporary tree -- tests/mobile_harness.py's (the narrated English book, the
Persian, Arabic, Japanese, Hindi and Chinese readers, the exercise decks, the
film of tests/cardkit_harness.py) -- with what review later is driven on added:

  * a PERSIAN BOOK OF THREE CHAPTERS, `multi-fa`, whose second and third
    chapters the reader fetches when they are wanted (ten paragraphs each, of
    the same four chunks every time, so that one text is in many places and a
    flag has to be found by WHERE it is as well as by what it is: the chunks
    of chapter 1 are 0-39, of chapter 2 40-79, of chapter 3 80-119);
  * an ENGLISH BOOK OF THREE CHAPTERS, `multi-en`, the same for a language read
    left to right;
  * two VIDEOS on the film of this machine: an English one of four captions and
    a Persian one, every phrase of them glossed -- a chunk is
    [text, meaning, vocabulary, transliteration].

    python3 tests/later_harness.py build <tmp>
        mobile_harness's tree and the above; prints one line of JSON
        saying what is where.
    python3 tests/later_harness.py serve <tmp> <port>
        serve.main() on 127.0.0.1:<port> over it, with NO dictionary, corpus or
        model of this machine to look a word up with (a cloud would hold an
        entry the test does not expect).

Never touches the real books/, config/ or anki/ (tests/cardkit_harness.py's
serve_it points every store at the tree).
"""
import contextlib
import io
import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for folder in ("markdown/exlex", "markdown/app", "youtube/lib", "lib", "tests", "."):
    sys.path.insert(0, str(REPO / folder))

EN_VIDEO = "four-lines-d4e5f6"
FA_VIDEO = "persian-lines-a1b2c3"
# [text, meaning, vocabulary, transliteration]; a caption's chunks, joined with a
# space, give its text back (check_annotations)
EN_CAPTIONS = [
    {"start": 0, "text": "Good morning, friends.", "plain": True, "chunks": []},
    {"start": 2, "text": "The market opens early.", "chunks": [
        ["The market", "the place of the stalls", "market: where things are sold", ""],
        ["opens early.", "starts soon", "", ""]]},
    {"start": 4, "text": "Bring a bag today.", "chunks": [
        ["Bring a bag", "come with something to carry", "bag: a soft carrier", ""],
        ["today.", "this day", "", ""]]},
    {"start": 6, "text": "We buy fresh bread.", "chunks": [
        ["We buy", "we pay for", "", ""], ["fresh bread.", "bread just baked", "", ""]]},
]
FA_CAPTIONS = [
    {"start": 0, "text": "هیچ جایِ دُنیا تَروُ خُشک را", "chunks": [
        ["هیچ جایِ دُنیا", "nowhere in the world", "جا jā place", "hič jā-ye donyā"],
        ["تَروُ خُشک را", "the wet and the dry", "", "tar-o xošk rā"]]},
    {"start": 2, "text": "مِثلِ ایران با هَم نِمی سوزانَند.", "chunks": [
        ["مِثلِ ایران با هَم", "like in Iran, together", "", "mesl-e irān bā ham"],
        ["نِمی سوزانَند.", "do they burn", "", "nemi-suzānand"]]},
    {"start": 4, "text": "پَس اَز پَنج سال", "chunks": [
        ["پَس اَز", "after", "", "pas az"], ["پَنج سال", "five years", "", "panj sāl"]]},
]
FA_ROWS = [("هیچ جایِ دُنیا", "hič jā-ye donyā", r"\dw{جا}{jā} place", "nowhere in the world"),
           ("تَروُ خُشک را", "tar-o xošk rā", r"\dw{تر}{tar} wet", "the wet and the dry"),
           ("مِثلِ ایران با هَم", "mesl-e irān bā ham", r"\dw{مثل}{mesl} like", "like in Iran, together"),
           ("پَس اَز پَنج سال", "pas az panj sāl", r"\dw{سال}{sāl} year", "after five years")]
EN_ROWS = [("The old man", "ðə oʊld mæn", r"\dw{old}{oʊld} having lived a long time", "the old man"),
           ("wound the clock", "waʊnd ðə klɑk", r"\dw{clock}{klɑk} a thing on a wall", "turned the key of the clock"),
           ("and put it down.", "ən pʊt ɪt daʊn", r"\dw{put}{pʊt} to set", "and set it down."),
           ("He hadn't slept,", "hi ˈhædənt slɛpt", r"\dw{sleep}{slip} to rest", "he had not slept,")]


def chapter(rows, num, paras=10):
    """One chapter's .tex: `paras` paragraphs of the four rows, the first glossed
    in full and the others with a meaning alone.  Long enough (about 2000 px) that
    the next chapter is further off than the 1200 px the reader fetches ahead."""
    t = "\\chapopen{%s}\n\n" % num
    for p in range(1, paras + 1):
        t += "\\parstart{%s.%d}{%s}\n\\parnum{%s.%d}\n\\begin{frank}\n" % (num, p, rows[0][0], num, p)
        for k, (text, tr, voc, en) in enumerate(rows):
            if k == 0 or p == 1:
                t += "\\ch{}{%s}{%s}{%s}{%s}\n" % (text, tr, voc, en)
            else:
                t += "\\ch{}{%s}{}{}{%s}\n" % (text, en)
        t += "\\end{frank}\n\n"
    return t


def build(tmp):
    os.chdir(str(REPO))
    import mobile_harness
    with contextlib.redirect_stdout(io.StringIO()) as said:
        mobile_harness.build(tmp)
    made = json.loads(said.getvalue().strip().splitlines()[-1])
    root = tmp / "root"

    def book(folder, slug, source, rows, language, numbers):
        b = root / "books" / folder / slug
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(REPO / "tests/fixtures/books" / source[0] / source[1], b,
                        ignore=shutil.ignore_patterns("reader", "source", "ch1.tex", "audio"))
        meta = json.loads((b / "book.json").read_text(encoding="utf-8"))
        meta["slug"] = slug
        (b / "book.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        main = (b / "main.tex").read_text(encoding="utf-8")
        (b / "main.tex").write_text(main.replace("\\input{ch1.tex}\n", "".join(
            "\\input{ch%d.tex}\n" % (k + 1) for k in range(len(numbers)))), encoding="utf-8")
        for k, n in enumerate(numbers):
            (b / ("ch%d.tex" % (k + 1))).write_text(chapter(rows, n), encoding="utf-8")
        mobile_harness.built_reader(b)
        return "/books/%s/%s/reader/" % (folder, slug)

    made["multi_fa"] = book("persian", "multi-fa", ("persian", "mini-fa"), FA_ROWS, "fa", ["۱", "۲", "۳"])
    made["multi_en"] = book("english", "multi-en", ("english", "mini-en"), EN_ROWS, "en", ["1", "2", "3"])
    # A READER BUILT BEFORE a0.5.0: the fixture edition's, as the checkout's git-ignored
    # build left it (an older tex2html wrote it), with its climb to lib/ made the hub's own
    # absolute path.  It has no review later of its own and gets it as every old reader on
    # a shelf does: from lib/parseh.js, with no rebuild.  Absent where nothing built it.
    old = REPO / "tests/fixtures/books/persian/mini-fa/reader"
    if (old / "index.html").is_file():
        dst = root / "books" / "persian" / "old-fa" / "reader"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(old, dst)
        climb = os.path.relpath(str(REPO), str(old)).replace(os.sep, "/") + "/"
        for page in dst.glob("*.html"):
            page.write_text(page.read_text(encoding="utf-8").replace(climb, "/"), encoding="utf-8")
        made["old_fa"] = "/books/persian/old-fa/reader/"

    videos = root / "youtube" / "videos"
    film = videos / "english" / made["video"] / "media.mp4"

    def video(folder, vid, title, lang, caps):
        d = videos / folder / vid
        d.mkdir(parents=True, exist_ok=True)
        os.symlink(str(film), str(d / "media.mp4"))
        (d / "video.json").write_text(json.dumps(
            {"id": vid, "url": "", "title": title, "title_native": title, "channel": "",
             "language": lang, "gloss": "en", "duration": "0:08"}), encoding="utf-8")
        segs = []
        for s in caps:
            if s.get("plain"):
                segs.append({"start": s["start"], "text": s["text"], "plain": True})
                continue
            chunks = []
            for c in s["chunks"]:
                ch = {"fa": c[0]}
                for k, f in ((1, "en"), (2, "voc"), (3, "tr")):
                    if len(c) > k and c[k]:
                        ch[f] = c[k]
                chunks.append(ch)
            segs.append({"start": s["start"], "text": s["text"], "chunks": chunks})
        (d / "annotations.json").write_text(json.dumps(
            {"video": vid, "language": lang, "segments": segs}, ensure_ascii=False), encoding="utf-8")

    video("english", EN_VIDEO, "Four lines", "en", EN_CAPTIONS)
    video("persian", FA_VIDEO, "Persian lines", "fa", FA_CAPTIONS)
    made.update({"en_video": EN_VIDEO, "fa_video": FA_VIDEO})
    print(json.dumps(made, ensure_ascii=False))


def serve(tmp, port):
    # no dictionary, corpus or model of this machine: a cloud holds what the test put in it
    import corpus
    import getmt
    import lookup
    lookup.DICT_DIR = str(tmp / "dict")
    corpus.CORPUS_DIR = str(tmp / "nocorpus")
    getmt.MT_DIR = str(tmp / "nomt")
    getmt.ENGINE_DIR = str(tmp / "nomt" / "engine")
    os.makedirs(lookup.DICT_DIR, exist_ok=True)
    import mobile_harness
    mobile_harness.serve_it(tmp, port)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "build":
        build(Path(sys.argv[2]))
    elif len(sys.argv) >= 4 and sys.argv[1] == "serve":
        serve(Path(sys.argv[2]), int(sys.argv[3]))
    else:
        raise SystemExit(__doc__)
