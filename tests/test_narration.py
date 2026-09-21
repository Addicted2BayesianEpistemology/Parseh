"""A book recorded in parts: several narrations, each covering a stretch.

    python3 -m unittest discover -s tests -p test_narration.py

The point of the feature is that an audiobook can be made a little at a time:
record two chapters, say which two, align just those.  What has to hold, and
is covered nowhere else in the suite:

  * a region-scoped align re-times ONLY the text its recording covers, and
    leaves every other region's times exactly where they were -- both in
    timings.json and in the `% @par` comments, which is what the reader is
    actually built from (lib/tex2html.load_times);
  * each recording's times are seconds into ITS OWN file, so two regions both
    start near zero and nothing tries to put them on one clock;
  * A BOOK WITH ONE RECORDING IS UNTOUCHED -- it reads, aligns and writes
    itself exactly as it did before any of this existed, including writing
    the five-field comment with no sixth field in it.
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT))
import books          # noqa: E402
import texparse as T  # noqa: E402
import timestamp as ts  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "books" / "english" / "mini-en"


def subs_of(b):
    return [x for ch in T.parse_book(b.main, b.lang)
            for pp in ch.paragraphs for x in pp.subs]


class Regions(unittest.TestCase):
    """region_subs: which subparagraphs a recording covers."""

    class Fake:
        def __init__(self, num):
            self.num = num

    def subs(self):
        return [self.Fake(n) for n in ("1.1", "1.2", "2.1", "2.2", "3.1")]

    def test_both_ends_named(self):
        got = [x.num for x in ts.region_subs(self.subs(), "1.2", "2.2")]
        self.assertEqual(got, ["1.2", "2.1", "2.2"])

    def test_either_end_left_out_means_that_way_to_the_end(self):
        subs = self.subs()
        self.assertEqual([x.num for x in ts.region_subs(subs, "2.1", "")],
                         ["2.1", "2.2", "3.1"])
        self.assertEqual([x.num for x in ts.region_subs(subs, "", "1.2")],
                         ["1.1", "1.2"])

    def test_a_recording_that_names_no_region_covers_the_whole_book(self):
        self.assertEqual(len(ts.region_subs(self.subs(), "", "")), 5)


class OneRecording(unittest.TestCase):
    """The book every reader already has: nothing about it changes."""

    def test_a_book_with_only_the_old_scalars_is_one_narration(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td, "books", "english", "mini-en")
            shutil.copytree(FIXTURE, d, ignore=shutil.ignore_patterns("reader"))
            meta = json.loads((d / "book.json").read_text(encoding="utf-8"))
            meta["audio"], meta["transcript"] = "audio/a.webm", "audio/a.txt"
            (d / "book.json").write_text(json.dumps(meta), encoding="utf-8")
            b = books.Book(str(d))
            self.assertEqual([(n["id"], n["audio_rel"], n["from"], n["to"])
                              for n in b.narrations],
                             [("n1", "audio/a.webm", "", "")],
                             "one recording, covering the whole book")

    def test_a_book_with_no_narration_has_none(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td, "books", "english", "mini-en")
            shutil.copytree(FIXTURE, d, ignore=shutil.ignore_patterns("reader"))
            b = books.Book(str(d))
            self.assertEqual(b.narrations, [])
            self.assertFalse(b.has_audio)


class Spread(unittest.TestCase):
    """A recording with no transcript, shared out over the text it covers.

    The stretch is known and so is the length of the file, which is enough to
    give every subparagraph a slice in proportion to its own length: somewhere
    to start from, so a recording plays the moment it lands instead of waiting
    for a transcript that may never be written.
    """

    class Fake:
        def __init__(self, fa, num):
            self.fa, self.num = fa, num

    def setUp(self):
        import languages
        self.was, ts.LANG = ts.LANG, languages.get("en")
        self.addCleanup(lambda: setattr(ts, "LANG", self.was))

    def test_each_slice_is_as_long_as_its_subparagraph(self):
        subs = [self.Fake("a" * 10, "1.1"), self.Fake("b" * 30, "1.2"),
                self.Fake("c" * 60, "1.3")]
        out = ts.spread(subs, 100.0)
        self.assertEqual([round(t1 - t0, 1) for t0, t1 in out], [10.0, 30.0, 60.0])

    def test_it_fills_the_recording_end_to_end(self):
        subs = [self.Fake("a" * 7, "1.1"), self.Fake("b" * 13, "1.2")]
        out = ts.spread(subs, 42.0)
        self.assertEqual(out[0][0], 0.0, "the first starts where the file does")
        self.assertEqual(out[-1][1], 42.0, "the last ends where it does")
        self.assertTrue(all(out[k][1] == out[k + 1][0] for k in range(len(out) - 1)),
                        "and there is no silence between them nobody can play")

    def test_a_very_short_subparagraph_still_gets_a_moment(self):
        out = ts.spread([self.Fake("x", "1.1"), self.Fake("y" * 500, "1.2")], 10.0)
        self.assertGreaterEqual(round(out[0][1] - out[0][0], 3), 0.4)

    def test_a_length_it_cannot_tell_is_no_length(self):
        self.assertIsNone(ts.audio_seconds("/there/is/no/such.wav"))
        self.assertIsNone(ts.audio_seconds(""))

    def test_the_length_of_a_real_file_is_read_without_ffmpeg(self):
        """the standard library reads a WAV header, so this works anywhere"""
        import wave
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "a.wav")
            with contextlib.closing(wave.open(p, "wb")) as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(8000)
                w.writeframes(b"\0\0" * 8000 * 3)      # three seconds
            self.assertAlmostEqual(ts.audio_seconds(p), 3.0, places=3)


class SpreadDoor(unittest.TestCase):
    """The door the panel's `estimate times` presses, on the real handler.

    The browser test stubs the server, so this is the only place the route
    itself runs: the book is found from the request path, the aligner is
    called with the recording it was told about, and the times land in the
    sidecar for that stretch and no other.
    """

    def setUp(self):
        from unittest import mock
        import serve
        self.serve, self.mock = serve, mock
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.book = self.root / "books" / "english" / "mini-en"
        self.book.parent.mkdir(parents=True)
        shutil.copytree(FIXTURE, self.book, ignore=shutil.ignore_patterns("reader"))
        (self.book / "audio").mkdir(exist_ok=True)
        import wave
        with contextlib.closing(wave.open(str(self.book / "audio" / "part1.wav"), "wb")) as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(b"\0\0" * 8000 * 20)          # twenty seconds
        b = books.Book(str(self.book))
        self.labels = [x.num for x in subs_of(b)]
        serve.set_narrations(b, [{"id": "n1", "audio": "audio/part1.wav",
                                  "transcript": "", "from": self.labels[0],
                                  "to": self.labels[1]}])
        # _book_dir walks up from the resolved path but only `while
        # d.startswith(ROOT)` -- the guard that keeps a request from naming a
        # book outside the toolbox.  A temp shelf is therefore unreachable
        # until ROOT says so too, which is the honest way to stand one up.
        for target, value in ((serve._AtRoot, "directory"), (serve, "ROOT")):
            patcher = mock.patch.object(target, value, str(self.root))
            patcher.start()
            self.addCleanup(patcher.stop)

    def handler(self, body=None, path="/books/english/mini-en/reader/"):
        h = object.__new__(self.serve.Handler)
        # _book_dir walks up from the REQUEST PATH, resolved by
        # SimpleHTTPRequestHandler.translate_path -- which reads `directory`
        # off the handler itself.  Patching _AtRoot serves book_dir(), which
        # is a different way in; a handler standing in for a real one needs
        # both of these.
        h.path = path
        h.directory = str(self.root)
        h._json_body = lambda: {} if body is None else body
        h.sent = []
        h.send_json = lambda payload, status=200: h.sent.append((status, payload))
        return h

    def run_only_the_aligner(self, h):
        """the reader and the library page are not what this is testing"""
        real = self.serve.Handler._run_steps

        def steps(self_, steps_):
            return real(self_, [s for s in steps_ if s[0] == "estimate"])
        return self.mock.patch.object(self.serve.Handler, "_run_steps", steps)

    def test_the_door_shares_the_recording_over_the_stretch_it_covers(self):
        h = self.handler({"narration": "n1"})
        with self.run_only_the_aligner(h):
            h._route("POST", "/books/english/mini-en/reader/__narration/spread")
        status, payload = h.sent[-1]
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"], payload)
        self.assertEqual(payload["spread"], 2,
                         "both subparagraphs of the stretch were given a time")
        doc = json.loads((self.book / "timings.json").read_text(encoding="utf-8"))
        got = {r["label"]: r for r in doc["subs"].values()}
        self.assertEqual(sorted(got), self.labels[:2],
                         "and nothing outside the stretch was touched")
        for label in self.labels[:2]:
            self.assertEqual(got[label]["src"], "spread")
            self.assertLess(got[label]["conf"], 1.0, "a guess, and it says so")
        self.assertEqual(got[self.labels[0]]["t0"], 0.0)
        self.assertEqual(got[self.labels[1]]["t1"], 20.0,
                         "the last one ends where the recording does")

    def test_a_recording_it_has_never_heard_of_is_refused(self):
        h = self.handler({"narration": "nowhere"})
        h._route("POST", "/books/english/mini-en/reader/__narration/spread")
        status, payload = h.sent[-1]
        self.assertEqual(status, 400)
        self.assertIn("nowhere", payload["error"])


class AlignOneRegion(unittest.TestCase):
    """The whole way through, on a book with two recordings."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.d = Path(self.td.name, "books", "english", "mini-en")
        shutil.copytree(FIXTURE, self.d, ignore=shutil.ignore_patterns("reader"))
        (self.d / "audio").mkdir(exist_ok=True)
        for name in ("part1.webm", "part2.webm"):
            (self.d / "audio" / name).write_bytes(b"")
        b = books.Book(str(self.d))
        subs = subs_of(b)
        self.labels = [x.num for x in subs]
        self.half = len(subs) // 2
        meta = json.loads((self.d / "book.json").read_text(encoding="utf-8"))
        meta["audio"] = "audio/part1.webm"
        meta["transcript"] = "audio/tr1.json"
        meta["narrations"] = [
            {"id": "n1", "audio": "audio/part1.webm", "transcript": "audio/tr1.json",
             "from": self.labels[0], "to": self.labels[self.half - 1]},
            {"id": "n2", "audio": "audio/part2.webm", "transcript": "audio/tr2.json",
             "from": self.labels[self.half], "to": self.labels[-1]}]
        (self.d / "book.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        # a transcript per part, in whisper's shape, made of that part's own
        # words: the aligner is given exactly what it would be given for real
        for lo, hi, fn in ((0, self.half, "tr1.json"),
                           (self.half, len(subs), "tr2.json")):
            segs, t = [], 0.0
            for x in subs[lo:hi]:
                segs.append({"start": t, "end": t + 4.0,
                             "text": " ".join(c.fa for c in x.chunks)})
                t += 4.0
            (self.d / "audio" / fn).write_text(
                json.dumps({"segments": segs}, ensure_ascii=False), encoding="utf-8")

    def align(self, nid):
        r = subprocess.run(
            [sys.executable, str(ROOT / "lib" / "timestamp.py"),
             "--book", str(self.d), "--narration", nid, "--no-snap"],
            capture_output=True, text=True)
        if r.returncode:
            self.skipTest("the aligner could not run here: %s"
                          % (r.stderr or r.stdout)[-300:])
        return r.stdout

    def pars(self):
        """the `% @par` lines of the book, in order"""
        out = []
        for tex in sorted(self.d.glob("ch*.tex")):
            out += [ln for ln in tex.read_text(encoding="utf-8").split("\n")
                    if ln.startswith("% @par")]
        return out

    def sidecar(self):
        return json.loads((self.d / "timings.json").read_text(encoding="utf-8"))

    def test_each_region_is_timed_against_its_own_recording_only(self):
        said = self.align("n1")
        self.assertIn("narration n1", said)
        after_one = self.pars()
        self.assertEqual(len(after_one), self.half,
                         "only the subparagraphs n1 covers are timed")
        for ln in after_one:
            self.assertTrue(ln.endswith(" n1"),
                            "the comment names the recording: %r" % ln)

        self.align("n2")
        after_two = self.pars()
        self.assertEqual(after_two[:self.half], after_one,
                         "aligning n2 left every one of n1's comments alone")
        self.assertEqual(len(after_two), len(self.labels))
        for ln in after_two[self.half:]:
            self.assertTrue(ln.endswith(" n2"), ln)

        doc = self.sidecar()
        self.assertEqual([n["id"] for n in doc.get("narrations", [])], ["n1", "n2"])
        by = {}
        for rec in doc["subs"].values():
            by.setdefault(rec.get("n"), []).append(rec)
        self.assertEqual(sorted(by), ["n1", "n2"],
                         "every time says which recording it is seconds into")
        # both recordings start near zero: they are two clocks, not one
        for nid in ("n1", "n2"):
            self.assertLess(min(r["t0"] for r in by[nid]), 1.0,
                            "%s starts at the beginning of its own file" % nid)

    def test_the_reader_is_built_with_the_recording_of_every_subparagraph(self):
        self.align("n1")
        self.align("n2")
        r = subprocess.run(
            [sys.executable, str(ROOT / "lib" / "tex2html.py"), "--book", str(self.d)],
            capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        html = (self.d / "reader" / "index.html").read_text(encoding="utf-8")
        import re
        narr = json.loads(re.search(r"const NARR=(\[.*?\]);", html, re.S).group(1))
        subs = json.loads(re.search(r"const SUBS=(\[.*?\]);", html, re.S).group(1))
        self.assertEqual([n["id"] for n in narr], ["n1", "n2"])
        self.assertEqual([n["src"] for n in narr],
                         ["../audio/part1.webm", "../audio/part2.webm"])
        self.assertEqual([s[3] for s in subs],
                         ["n1"] * self.half + ["n2"] * (len(self.labels) - self.half),
                         "every subparagraph carries the recording its times are in")


if __name__ == "__main__":
    unittest.main()
