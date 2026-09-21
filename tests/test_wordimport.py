#!/usr/bin/env python3
"""A pasted answer's word lines, on their way into the player.

    python3 -m unittest discover -s tests -p test_wordimport.py

youtube/lib/ytpages.py's api_add, driven the way serve.py drives it -- a
handler holding the body in _raw and answering through send_json -- over a
temporary videos/ directory, with YouTube's oEmbed answered by nobody, so
nothing is fetched and nothing lands on the real shelf.  The answer is the
fixture video's own parts/01.json, which carries no words.

Under the machine's python3 the analyzers are not importable, and no chunk may
come out with a line: the video is written exactly as it was before words
existed.  Under the ilya-frank environment every chunk of the language's text
the answer left without words comes out with lib/words.py's line.  Standard
library only.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(ROOT, "lib"), os.path.join(ROOT, "youtube", "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import wordline                  # noqa: E402
import words                     # noqa: E402
import ytpages                   # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "videos")


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def raw(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


class Handler:
    """What api_add asks of serve.py's handler, and no more."""

    def __init__(self, body):
        self._raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.query = {}
        self.status = self.sent = None

    def send_json(self, obj, code=200):
        self.status, self.sent = code, obj


class Shelf(unittest.TestCase):
    """A temporary videos/ directory, with ytpages pointed at it."""
    FOLDER, ID, CODE = "japanese", "aB3dE5fG7hI", "ja"

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.videos = os.path.join(td.name, "videos")
        os.makedirs(self.videos)
        for name, value in (("VIDEOS", self.videos), ("oembed", lambda vid: {})):
            self.addCleanup(setattr, ytpages, name, getattr(ytpages, name))
            setattr(ytpages, name, value)
        self.src = os.path.join(FIX, self.FOLDER, self.ID)
        self.dest = os.path.join(self.videos, self.FOLDER, self.ID)


class Answers:
    """An answer through api_add, for a language divided into words."""
    # a line the analyzers would not write, for "kept as written"
    WRITTEN = {}

    def parts(self):
        return load(os.path.join(self.src, "parts", "01.json"))

    def add(self, parts, transcript=None):
        caps = [{"i": i, "start": p["start"], "chunks": p["chunks"]}
                for i, p in enumerate(parts)]
        answer = "```json\n%s\n```" % json.dumps(
            {"video": {"level": "beginner"}, "captions": caps}, ensure_ascii=False)
        h = Handler({"url": self.ID, "lang": self.CODE, "gloss": "en",
                     "transcript": transcript or raw(os.path.join(self.src,
                                                                  "transcript.txt")),
                     "answer": answer})
        ytpages.api_add(h)
        return h.status, h.sent

    def chunks(self):
        ann = load(os.path.join(self.dest, "annotations.json"))
        return [c for sg in ann["segments"] for c in sg.get("chunks") or []]

    def assertAdded(self, status, j):
        self.assertEqual(status, 200, j)
        self.assertIs(j["ok"], True, j)

    def test_an_answer_without_words_is_given_them(self):
        if not words.available(self.CODE):
            self.skipTest("no %s analyzer in %s" % (self.CODE, sys.executable))
        parts = self.parts()
        status, j = self.add(parts)
        self.assertAdded(status, j)
        got = self.chunks()
        self.assertEqual(len(got), sum(len(p["chunks"]) for p in parts))
        for c in got:
            # proposed with the answer's own reading of the chunk, which gives
            # each word its stretch of it (私 わたし, not the dictionary's わたくし)
            said = c.get("kana" if self.CODE == "ja" else "tr") or ""
            self.assertEqual(c["words"], words.line(c["fa"], self.CODE, said), c["fa"])
            self.assertEqual(list(c)[:2], ["fa", "words"], "the key stands after fa")
        self.assertEqual(j["proposed"], len(got))
        # and nothing else about a chunk is touched
        self.assertEqual([{k: v for k, v in c.items() if k != "words"} for c in got],
                         [c for p in parts for c in p["chunks"]])

    def test_without_the_analyzers_the_video_is_as_it_was(self):
        if words.available(self.CODE):
            self.skipTest("the %s analyzer is installed in %s" % (self.CODE, sys.executable))
        status, j = self.add(self.parts())
        self.assertAdded(status, j)
        self.assertEqual(j["proposed"], 0)
        self.assertFalse(any("words" in c for c in self.chunks()))
        self.assertEqual(raw(os.path.join(self.dest, "annotations.json")),
                         raw(os.path.join(self.src, "annotations.json")))

    def test_words_the_answer_wrote_are_kept(self):
        parts = self.parts()
        (si, ci), line = next(iter(self.WRITTEN.items()))
        ch = parts[si]["chunks"][ci]
        said = ch.get("kana" if self.CODE == "ja" else "tr") or ""
        self.assertNotEqual(line, words.line(ch["fa"], self.CODE, said),
                            "a line the analyzer would write proves nothing kept")
        parts[si]["chunks"][ci] = {"fa": ch.pop("fa"), "words": line, **ch}
        status, j = self.add(parts)
        self.assertAdded(status, j)
        got = self.chunks()
        self.assertEqual(sum(1 for c in got if c.get("words") == line), 1)
        self.assertEqual(j["proposed"], (len(got) - 1) if words.available(self.CODE) else 0)
        # and judged by the checker like any other: one that does not give
        # its text back is refused, not replaced by a proposal
        parts[si]["chunks"][ci]["words"] = line + " 了"
        status, j = self.add(parts)
        self.assertEqual(status, 400, j)
        self.assertTrue(any("the words do not reproduce the text" in p
                            for p in j["problems"]), j["problems"])

    def test_words_that_are_not_text_are_refused_by_the_caption(self):
        parts = self.parts()
        parts[2]["chunks"][1]["words"] = ["a", "b"]
        parts[0]["chunks"][0]["words"] = None
        status, j = self.add(parts)
        self.assertEqual(status, 400, j)
        self.assertIs(j["ok"], False)
        self.assertIn("not text -- nothing written", j["error"])
        self.assertEqual(j["problems"], [
            "caption [0] (start %s) chunk 0: words must be text, not NoneType"
            % parts[0]["start"],
            "caption [2] (start %s) chunk 1: words must be text, not list"
            % parts[2]["start"]])
        self.assertEqual(os.listdir(self.videos), [], "nothing written, nothing staged")

    def test_a_plain_chunk_gets_none(self):
        parts = self.parts()
        parts[1]["chunks"][0]["plain"] = True
        status, j = self.add(parts)
        self.assertAdded(status, j)
        got = self.chunks()
        plain = [c for c in got if c.get("plain")]
        self.assertEqual(len(plain), 1)
        self.assertNotIn("words", plain[0])
        worded = sum(1 for c in got if "words" in c)
        self.assertEqual((worded, j["proposed"]),
                         ((len(got) - 1,) * 2 if words.available(self.CODE) else (0, 0)))

    def test_a_proposal_the_checker_refuses_is_not_given(self):
        # a stand-in analyzer, every character a word, so this runs under any
        # Python; a control character the transcript carries comes back as a
        # word the checker refuses, and the answer that went in without the
        # analyzers must go in with them, that one chunk still without words
        for name, value in (("available", lambda code: True),
                            ("line", lambda fa, code, reading="": wordline.render(
                                [(c, "") for c in fa if not c.isspace()]))):
            self.addCleanup(setattr, words, name, getattr(words, name))
            setattr(words, name, value)
        parts = self.parts()
        fa = parts[0]["chunks"][0]["fa"]
        transcript = raw(os.path.join(self.src, "transcript.txt"))
        self.assertIn(fa, transcript)
        bad = fa[0] + "\x81" + fa[1:]
        parts[0]["chunks"][0]["fa"] = bad
        status, j = self.add(parts, transcript.replace(fa, bad, 1))
        self.assertAdded(status, j)
        got = self.chunks()
        self.assertEqual([c["fa"] for c in got if "words" not in c], [bad])
        self.assertEqual(j["proposed"], len(got) - 1)


class Japanese(Answers, Shelf):
    FOLDER, ID, CODE = "japanese", "aB3dE5fG7hI", "ja"
    WRITTEN = {(2, 1): "毎(まい) 朝(あさ)"}          # 毎朝, as two words


class Chinese(Answers, Shelf):
    FOLDER, ID, CODE = "chinese", "zH8cN2hA6nZ", "zh"
    WRITTEN = {(0, 1): "我(wǒ) 想要(xiǎng yào) 一(yì) 杯(bēi) 茶(chá)"}


class Persian(Answers, Shelf):
    """A language with no word layer: nothing proposed, under any Python."""
    FOLDER, ID, CODE = "persian", "fA6bK2mQ8sT", "fa"

    def test_an_answer_without_words_is_given_them(self):
        status, j = self.add(self.parts())
        self.assertAdded(status, j)
        self.assertEqual(j["proposed"], 0)
        self.assertEqual(raw(os.path.join(self.dest, "annotations.json")),
                         raw(os.path.join(self.src, "annotations.json")))

    test_without_the_analyzers_the_video_is_as_it_was = None
    test_words_the_answer_wrote_are_kept = None
    test_a_proposal_the_checker_refuses_is_not_given = None


class Player(Shelf):
    def cfg(self):
        page = ytpages.player_page(self.ID)
        return json.loads(page.split("window.YTFRANK=", 1)[1]
                          .split("</script>", 1)[0].strip().rstrip(";"))

    def test_the_page_is_told_whether_the_video_reorders(self):
        shutil.copytree(self.src, self.dest)
        self.assertIs(self.cfg()["reorders"], False)
        mp = os.path.join(self.dest, "video.json")
        meta = load(mp)
        meta["reorders"] = True
        with io.open(mp, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        self.assertIs(self.cfg()["reorders"], True)


if __name__ == "__main__":
    unittest.main()
