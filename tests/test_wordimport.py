#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""A pasted answer on its way into the player: its word lines, and the rules
the add page's door holds every answer to.

    python3 -m unittest discover -s tests -p test_wordimport.py

youtube/lib/ytpages.py's api_add, driven the way serve.py drives it -- a
handler holding the body in _raw and answering through send_json -- over a
temporary videos/ directory, with YouTube's oEmbed answered by nobody, so
nothing is fetched and nothing lands on the real shelf.  The answer is the
fixture video's own parts/01.json, which carries no words.

Under the machine's python3 the analyzers are not importable, and no chunk may
come out with a line: the video is written exactly as it was before words
existed.  Under the ilya-frank environment every chunk of the language's text
the answer left without words comes out with lib/words.py's line.

AddDoor asks the door itself, on every fixture video: a chunk the answer left
blank lands and is counted, one it half glossed is refused by the prompt's own
[i] (SPEC rule 6); a caption a later block gives again replaces the earlier
one, the same caption twice in one block is refused; a fence of prose is
passed over, a broken ```json fence refused, and so is an answer carrying a
broken character or nested too deep to read -- in words, nothing written.
Standard library only.
"""
import glob
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
import check_annotations as CA   # noqa: E402
import languages                 # noqa: E402
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
    """What api_add asks of serve.py's handler, and no more.

    `ascii` sends the body the way a browser's JSON.stringify does when the
    text holds a character UTF-8 cannot carry (half of a surrogate pair):
    escaped as \\udXXX, which decodes on the server side into exactly that
    broken character -- ensure_ascii=False could not even encode it."""

    def __init__(self, body, ascii=False):
        self._raw = json.dumps(body, ensure_ascii=ascii).encode("utf-8")
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


# --- the add page's door, on every fixture video -------------------------------
EVERY = sorted(glob.glob(os.path.join(FIX, "*", "*", "video.json")))
GLOSS = ("kana", "tr", "voc", "en")
# lib/glossregion.json_blocks' own words, which api_add hands the page as
# they are (ytpages._json_blocks delegates to it): the one rule for every
# door that takes an LLM's answer
BROKEN = ("the answer carries a broken character (an unpaired surrogate) -- "
          "copy it again from the chat")
DEEP = "the answer nests too deep to be read"
BROKEN_BODY = ("the request carries a broken character (an unpaired surrogate) "
               "-- copy the text again")


def fence(doc):
    return "```json\n%s\n```" % json.dumps(doc, ensure_ascii=False, indent=1)


class Fixture(object):
    """One fixture video, answered through api_add into a videos/ directory
    of its own: the answer is the video's own parts/01.json, every caption
    numbered [i] as the prompt numbers the captions that want glossing."""

    def __init__(self, test, vj):
        self.test = test
        self.src = os.path.dirname(vj)
        self.id = os.path.basename(self.src)
        self.meta = load(vj)
        self.L = languages.get(self.meta["language"])
        self.transcript = raw(os.path.join(self.src, "transcript.txt"))
        self.captions = ytpages.parse_transcript_text(self.transcript, self.L)
        self.fresh()
        # the chunk every test works on: in the LAST caption that has one
        # glossed in full with a vocabulary -- so taking away any field the
        # language requires leaves it half glossed, never blank -- and so,
        # wherever a plain caption stands before it, a caption whose [i] in
        # the prompt is not its segment number in annotations.json
        parts = self.parts()
        self.i, self.j = next((i, j) for i in reversed(range(len(parts)))
                              for j, c in enumerate(parts[i]["chunks"])
                              if CA.required(c, self.L) and CA.complete(c, self.L)
                              and (c.get("voc") or "").strip())
        self.start = parts[self.i]["start"]
        self.segment = [n for n, c in enumerate(self.captions) if not c["plain"]][self.i]

    def fresh(self):
        """A videos/ directory nothing has been written to yet."""
        self.videos = os.path.join(self.test.td, "%d" % len(os.listdir(self.test.td)))
        os.makedirs(self.videos)
        ytpages.VIDEOS = self.videos
        self.dest = os.path.join(self.videos, self.L.folder, self.id)

    def parts(self):
        return load(os.path.join(self.src, "parts", "01.json"))

    def doc(self, parts=None):
        parts = self.parts() if parts is None else parts
        return {"video": {"level": "beginner"},
                "captions": [{"i": i, "start": p["start"], "chunks": p["chunks"]}
                             for i, p in enumerate(parts)]}

    def caption(self, parts, i=None):
        i = self.i if i is None else i
        return {"i": i, "start": parts[i]["start"], "chunks": parts[i]["chunks"]}

    def add(self, answer, ascii=False):
        h = Handler({"url": self.id, "lang": self.L.code, "gloss": "en",
                     "transcript": self.transcript, "answer": answer}, ascii)
        ytpages.api_add(h)
        return h.status, h.sent

    def chunk(self):
        ann = load(os.path.join(self.dest, "annotations.json"))
        return ann["segments"][self.segment]["chunks"][self.j]

    def nothing_written(self, j):
        self.test.assertEqual(os.listdir(self.videos), [],
                              "nothing written, nothing staged: %s" % j)


class AddDoor(unittest.TestCase):
    """The from-scratch LLM answer (the add page's "paste the answer") is the
    one door that stays strict: a chunk the answer HALF glossed is refused,
    because nothing an LLM hands back is the middle of anybody's work -- while
    a chunk it left with no gloss at all is legal, as it is everywhere, lands
    blank and is counted (SPEC rule 6).  The page's repair loop sends the
    refused lines back to the LLM and has its corrected captions pasted UNDER
    the first answer: a caption a later block gives again replaces the earlier
    one, the same caption twice in one block is a model that lost its place,
    and every line the page shows names a caption by the prompt's own [i]
    (the plain captions have none), since those lines go back to the LLM as
    they are.  A fence of prose (a model showing its working) is passed over;
    a ```json fence that does not parse is refused; so is an answer carrying
    a broken character, or one nested deeper than it can be read -- in words,
    with nothing written, never a crash.  Every fixture video, every
    language."""

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.td = td.name
        for name, value in (("VIDEOS", ytpages.VIDEOS), ("oembed", ytpages.oembed)):
            self.addCleanup(setattr, ytpages, name, value)
        ytpages.oembed = lambda vid: {}

    def every(self, check):
        """check(fixture) on every fixture video, a subtest each -> the
        fixtures, for what a test wants to say about them all."""
        done = []
        for vj in EVERY:
            with self.subTest(os.path.relpath(os.path.dirname(vj), FIX)):
                v = Fixture(self, vj)
                check(v)
                done.append(v)
        return done

    def test_every_fixture_answer_goes_in(self):
        # the control: the answer as the fixture has it is taken whole
        def check(v):
            status, j = v.add(fence(v.doc()))
            self.assertEqual((status, j["ok"], j["blank"]), (200, True, 0), j)
        self.assertEqual(len(self.every(check)), len(EVERY))

    def test_a_chunk_left_blank_lands_and_is_counted(self):
        def check(v):
            for how in ("keys left out", "keys written empty"):
                v.fresh()
                parts = v.parts()
                ch = parts[v.i]["chunks"][v.j]
                for f in GLOSS:
                    ch.pop(f, None)
                    if how == "keys written empty":
                        ch[f] = ""
                status, j = v.add(fence(v.doc(parts)))
                self.assertEqual((status, j["ok"]), (200, True), (how, j))
                self.assertEqual(j["blank"], 1, how)
                self.assertIn("note: 1 chunk left without a gloss -- gloss it in the "
                              "player", j["problems"], how)
                got = v.chunk()
                self.assertEqual(got["fa"], ch["fa"])
                self.assertTrue(CA.unwritten(got, v.L), (how, got))
                self.assertEqual(CA.gloss_state(v.dest)[0], 1, how)
        self.every(check)

    def test_a_half_glossed_chunk_is_refused_by_the_prompts_number(self):
        def check(v):
            for f in CA.required(v.parts()[v.i]["chunks"][v.j], v.L):
                parts = v.parts()
                del parts[v.i]["chunks"][v.j][f]
                status, j = v.add(fence(v.doc(parts)))
                self.assertEqual((status, j["ok"]), (400, False), (f, j))
                self.assertEqual(j["error"], "1 error(s) in the annotation -- nothing written")
                self.assertIn("caption [%d] (start %s) chunk %d: missing %r"
                              % (v.i, v.start, v.j, f), j["problems"])
                self.assertFalse([p for p in j["problems"] if p.startswith("segment ")],
                                 "the checker's own numbering never reaches the page")
                v.nothing_written(j)
        done = self.every(check)
        # ...and the prompt's numbering is not the file's where a plain
        # caption stands before the one refused (Arabic, Chinese, Hindi,
        # Japanese, Persian): the sentence names [i], not segment i
        self.assertTrue([v.L.code for v in done if v.segment != v.i], "a plain caption first")

    def test_a_correction_in_a_later_block_replaces_the_caption(self):
        def check(v):
            parts = v.parts()
            right = parts[v.i]["chunks"][v.j]["en"]
            fix = v.caption(json.loads(json.dumps(parts)))
            parts[v.i]["chunks"][v.j]["en"] = "WRONG FIRST TRY"
            # pasted as the page asks: right under the first answer, its
            # ```json on the line the first one's closing ``` ends
            status, j = v.add(fence(v.doc(parts)) + fence({"captions": [fix]}))
            self.assertEqual((status, j["ok"]), (200, True), j)
            self.assertIn("note: 1 caption(s) given again in a later block -- the later "
                          "one was taken: [%d] %ss" % (v.i, ytpages.secs_str(v.start)),
                          j["problems"])
            self.assertEqual(v.chunk()["en"], right)
            self.assertNotIn("WRONG FIRST TRY", raw(os.path.join(v.dest, "annotations.json")))
        self.every(check)

    def test_the_same_caption_twice_in_one_block_is_refused(self):
        def check(v):
            parts = v.parts()
            doc = v.doc(parts)
            doc["captions"].append(v.caption(parts))
            status, j = v.add(fence(doc))
            self.assertEqual((status, j["ok"]), (400, False), j)
            self.assertEqual(j["error"], "the answer does not cover the transcript")
            self.assertIn("caption [%d] (start %s) appears twice in the answer"
                          % (v.i, ytpages.secs_str(v.start)), j["problems"])
            v.nothing_written(j)
            # ...and twice in the correction block: a correction is one
            # caption given again, not two versions of it to choose from
            status, j = v.add(fence(v.doc(parts)) + "\n"
                              + fence({"captions": [v.caption(parts)] * 2}))
            self.assertEqual(status, 400, j)
            self.assertIn("caption [%d] (start %s) appears twice in the answer (in the "
                          "same block)" % (v.i, ytpages.secs_str(v.start)), j["problems"])
            v.nothing_written(j)
        self.every(check)

    def test_a_stray_kana_is_taken_with_a_warning(self):
        # the chat prompt's example shows a kana for every language, so a
        # model may send one where the language has no reading: taken (a file
        # that has one goes on loading), said, and never counted as a gloss --
        # tests/test_gloss_rules.py has "delete gloss" take it off
        def check(v):
            if v.L.reading:
                return
            parts = v.parts()
            parts[v.i]["chunks"][v.j]["kana"] = "a reading the model added"
            status, j = v.add(fence(v.doc(parts)))
            self.assertEqual((status, j["ok"], j["blank"]), (200, True, 0), j)
            self.assertIn("caption [%d] (start %s) chunk %d: kana on a chunk of a language "
                          "with no reading -- ignored" % (v.i, v.start, v.j), j["warnings"])
            self.assertEqual(v.chunk()["kana"], "a reading the model added")
        self.every(check)

    def test_a_fence_of_prose_is_passed_over(self):
        def check(v):
            status, j = v.add("Here is how I worked:\n```\nI kept every caption as the "
                              "transcript divides it.\n```\n\n" + fence(v.doc())
                              + "\n```text\nDone.\n```\n")
            self.assertEqual((status, j["ok"]), (200, True), j)
            self.assertTrue(os.path.isfile(os.path.join(v.dest, "annotations.json")))
        self.every(check)

    def test_a_broken_json_fence_is_refused(self):
        def check(v):
            for answer in ('```json\n{"captions": [\n```',
                           fence(v.doc()) + '\n```json\n{"captions": [{"i": 0,\n```'):
                status, j = v.add(answer)
                self.assertEqual((status, j["ok"]), (400, False), j)
                self.assertIn("a ```json block is not valid JSON", j["error"])
                v.nothing_written(j)
        self.every(check)

    def test_a_broken_character_is_refused_before_anything_is_read(self):
        # half of a surrogate pair -- what a chat window leaves of an emoji
        # cut in two -- cannot be written to a file in UTF-8, nor sent back
        # to the page: refused in words, with nothing staged.  Wherever it
        # is: in a meaning as pasted, in the answer's JSON as the escape the
        # model wrote (no broken character in the text, one in what it
        # says), or in the prose round the JSON
        def check(v):
            parts = v.parts()
            parts[v.i]["chunks"][v.j]["en"] += " \ud83d"
            doc = v.doc(parts)
            escaped = "```json\n%s\n```" % json.dumps(doc, ensure_ascii=True)
            self.assertNotIn("\ud83d", escaped)
            # a broken character in the TEXT of the answer reaches the server
            # as an escape in the request body, and the body is refused before
            # the answer is read (ytpages._json_in, as serve's _json_body for
            # every other route); one the model wrote as an escape INSIDE the
            # answer's JSON is found when the answer is read (glossregion)
            for answer, ascii, said in ((fence(doc), True, BROKEN_BODY),
                                        (escaped, False, BROKEN),
                                        ("Here you are \ud83d\n" + fence(v.doc()), True,
                                         BROKEN_BODY)):
                status, j = v.add(answer, ascii=ascii)
                self.assertEqual((status, j["ok"]), (400, False), j)
                self.assertEqual(j["error"], said)
                v.nothing_written(j)
        self.every(check)

    def test_an_answer_nested_too_deep_is_refused(self):
        deep = "[" * 100000 + "]" * 100000
        def check(v):
            for answer in ("```json\n%s\n```" % deep, deep, "Sure! " + '{"a": ' * 100000
                           + "1" + "}" * 100000):
                status, j = v.add(answer)
                self.assertEqual((status, j["ok"]), (400, False), j)
                self.assertEqual(j["error"], DEEP)
                v.nothing_written(j)
        self.every(check)


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
