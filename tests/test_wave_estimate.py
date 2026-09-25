# SPDX-License-Identifier: GPL-3.0-or-later
"""Estimating the timings by the sound: the picture of a stretch
(lib/audiofile.py, envelope) and the two doors that hand it, with the
pieces' texts, to lib/wavealign.py (serve.py: <reader>/__clip/estimate and
/youtube/api/estimate).

    python3 -m unittest tests/test_wave_estimate.py -v

What has to hold:

  * THE PICTURE IS THE SOUND'S, at the second it is at: a tone reads high
    and a silence reads near nothing, over full scale and never scaled to
    the stretch -- also for a stretch that starts in the middle of a file,
    where an MP3 decoder is silent for a while after a seek (audiofile._seek
    reads a second early for that).  NumPy and the standard library count
    the same numbers, and a long stretch read in parts at once is the same
    stretch read in one go.
  * THE DOORS GIVE THE ALIGNER WHAT IT NEEDS AND NOTHING ELSE: a book's and
    a film's picture through ffmpeg at 100 a second, a YouTube video's from
    the numbers the page sent, else from the waveform.json on the shelf; the
    answer comes back with every time absolute and to a hundredth, the first
    piece starting at exactly the line in hand.
  * WHAT CANNOT BE DONE IS SAID, in plain words and never as a command to
    type: no ffmpeg, a YouTube video not drawn yet, NumPy missing -- each a
    409 -- and a bad question is a 400, a missing book or video a 404.
  * A LONG ESTIMATE KEEPS NOBODY WAITING: every request has its thread, and
    while one is being laid out the server answers the next.

lib/wavealign.py is somebody else's work, and the doors are what is tested
here: it is replaced by a stand-in that records what it was given and
answers in its shape.  The real one is run too (WithTheRealAligner) wherever
it imports.  Real recordings throughout, made by ffmpeg in a temporary
directory; without ffmpeg the tests that need it skip.
"""
import http.client
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "markdown" / "exlex", ROOT / "markdown" / "app",
               ROOT / "youtube" / "lib", ROOT / "lib", ROOT):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import audiofile  # noqa: E402

HAVE = audiofile.have_ffmpeg()
needs_ffmpeg = unittest.skipUnless(HAVE, "ffmpeg is not installed on this machine")

BOOK_FIXTURE = ROOT / "tests" / "fixtures" / "books" / "english" / "mini-en"
YT_FIXTURE = ROOT / "tests" / "fixtures" / "videos" / "english" / "eN5wX7zA9bC"

# a tone for the first second, silence for the second, a tone for the third,
# and silence after it for as long as the file goes on
TONE_GAP_TONE = "if(lt(t\\,1)+gte(t\\,2)*lt(t\\,3)\\,0.5*sin(2*PI*440*t)\\,0)"


def ff(*args):
    r = subprocess.run([audiofile.ffmpeg(), "-y", "-loglevel", "error"] + [str(a) for a in args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError("ffmpeg %s -> exit %d: %s" % (" ".join(map(str, args)),
                                                            r.returncode, r.stderr))
    return str(args[-1])


def tone_gap_tone(out, *codec, secs=3):
    """[0, 1) a 440 Hz tone at half of full scale, [1, 2) silence, [2, 3) the
    tone again (and silence after, when `secs` is longer)."""
    return ff("-f", "lavfi", "-i", "aevalsrc=exprs='%s':s=44100:d=%s" % (TONE_GAP_TONE, secs),
              "-ac", "1", *codec, out)


def real_aligner():
    """lib/wavealign.py where it imports here (it needs NumPy), else None."""
    try:
        import wavealign
    except ImportError:
        return None
    return wavealign if hasattr(wavealign, "estimate_pieces") else None


# ------------------------------------------------------------------ the picture

@needs_ffmpeg
class Envelope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        td = tempfile.TemporaryDirectory()
        cls._td = td
        cls.dir = Path(td.name)
        cls.wav = tone_gap_tone(cls.dir / "ttt.wav", "-c:a", "pcm_s16le")
        cls.mp3 = tone_gap_tone(cls.dir / "ttt.mp3", "-c:a", "libmp3lame", "-q:a", "4")

    @classmethod
    def tearDownClass(cls):
        cls._td.cleanup()

    def assertShape(self, got, loud, quiet, what):
        for i in loud:
            self.assertGreater(got[i], 0.4, "%s: slice %d (%.2f s) is the tone: %r"
                               % (what, i, i / 100, got[max(0, i - 3):i + 3]))
        for i in quiet:
            self.assertLess(got[i], 0.01, "%s: slice %d (%.2f s) is the silence: %r"
                            % (what, i, i / 100, got[max(0, i - 3):i + 3]))

    def test_tone_silence_tone_is_high_low_high_where_they_are(self):
        for label, src in (("wav", self.wav), ("mp3", self.mp3)):
            with self.subTest(label):
                got = audiofile.envelope(src, 0, 3)
                self.assertEqual(len(got), 300, "one number every 10 ms")
                self.assertTrue(all(isinstance(v, float) and 0.0 <= v <= 1.0 for v in got))
                self.assertShape(got, range(3, 97), range(104, 196), label)
                self.assertShape(got, range(204, 297), (), label)

    def test_full_scale_and_never_the_window_s_own_loudest(self):
        # the tone is at half of full scale, and stays half however loud or
        # quiet the rest of the stretch is: `peaks` would have made it 1.0
        got = audiofile.envelope(self.wav, 0.2, 0.8)
        self.assertAlmostEqual(max(got), 0.5, delta=0.02)
        self.assertAlmostEqual(min(got), 0.5, delta=0.05, msg="every 10 ms of a 440 Hz tone "
                               "holds a whole cycle, so every slice reaches its peak")
        self.assertEqual(max(audiofile.peaks(self.wav, 0.2, 0.8, 60)), 1.0,
                         "(where peaks scales the window to itself)")

    def test_a_stretch_from_the_middle_of_the_file(self):
        for label, src in (("wav", self.wav), ("mp3", self.mp3)):
            with self.subTest(label):
                got = audiofile.envelope(src, 1.5, 3.0)
                self.assertEqual(len(got), 150)
                # 1.5..2.0 silent, 2.0..3.0 the tone: slice 50 is 2.0 s
                self.assertShape(got, range(53, 147), range(0, 47), label)

    def test_the_first_slices_after_a_seek_are_the_file_s_own(self):
        """The MP3 decoder gives silence for 50 to 140 ms after a seek; a
        stretch starting ON the tone must read the tone from its first
        slice, and one starting just before it must see where it starts."""
        for label, src in (("wav", self.wav), ("mp3", self.mp3)):
            with self.subTest(label, at=2.0):
                got = audiofile.envelope(src, 2.0, 2.5)
                self.assertShape(got, range(0, 48), (), label)
            with self.subTest(label, at=1.9):
                got = audiofile.envelope(src, 1.9, 2.4)
                self.assertShape(got, range(12, 38), range(0, 8), label)

    def test_how_many_numbers(self):
        self.assertEqual(len(audiofile.envelope(self.wav, 0, 1.234)), 123)
        self.assertEqual(len(audiofile.envelope(self.wav, 0, 1.236)), 124)
        self.assertEqual(len(audiofile.envelope(self.wav, 0, 1.234, rate=20)), 25)
        self.assertEqual(len(audiofile.envelope(self.wav, 0.5, 0.501)), 1, "at least one")
        got = audiofile.envelope(self.wav, 0, 3, rate=20)
        self.assertEqual(len(got), 60)
        self.assertShape(got, (), range(21, 39), "20 a second")

    def test_past_the_end_is_silence(self):
        self.assertEqual(audiofile.envelope(self.wav, 5, 6), [0.0] * 100)
        got = audiofile.envelope(self.wav, 2.5, 3.5)
        self.assertEqual(len(got), 100)
        self.assertShape(got, range(0, 48), range(52, 100), "running off the end")

    def test_numpy_and_the_standard_library_count_the_same(self):
        with_np = audiofile.envelope(self.mp3, 0.37, 2.91)
        with mock.patch.object(audiofile, "_numpy", lambda: None):
            without = audiofile.envelope(self.mp3, 0.37, 2.91)
        self.assertEqual(with_np, without)

    def test_in_parts_and_in_small_pieces_it_is_the_same_stretch(self):
        whole = audiofile.envelope(self.wav, 0.13, 2.97)
        with mock.patch.object(audiofile, "ENVELOPE_PIECE", 0.4), \
                mock.patch.object(audiofile, "ENVELOPE_JOBS", 5), \
                mock.patch.object(audiofile, "_ENVELOPE_CHUNK", 3):
            parted = audiofile.envelope(self.wav, 0.13, 2.97)
        self.assertEqual(len(parted), len(whole))
        self.assertEqual(parted, whole, "read in five parts, three slices at a time")
        # an MP3's seams are each a seek of its own, with its own pre-roll
        whole = audiofile.envelope(self.mp3, 0.13, 2.97)
        with mock.patch.object(audiofile, "ENVELOPE_PIECE", 0.4), \
                mock.patch.object(audiofile, "ENVELOPE_JOBS", 5):
            parted = audiofile.envelope(self.mp3, 0.13, 2.97)
        self.assertEqual(len(parted), len(whole))
        self.assertLess(max(abs(a - b) for a, b in zip(whole, parted)), 0.02)

    def test_it_streams_and_never_asks_for_the_whole_output_at_once(self):
        with mock.patch.object(audiofile, "_run",
                               side_effect=AssertionError("the whole decode held in memory")):
            self.assertEqual(len(audiofile.envelope(self.wav, 0, 3)), 300)

    def test_a_film_s_sound(self):
        film = self.dir / "film.mp4"
        if not film.exists():
            ff("-f", "lavfi", "-i", "testsrc=duration=3:size=160x120:rate=10",
               "-i", self.wav, "-shortest", "-c:v", "libx264", "-c:a", "aac", film)
        got = audiofile.envelope(str(film), 0, 3)
        self.assertEqual(len(got), 300)
        self.assertShape(got, range(10, 90), range(110, 190), "film")

    def test_refusals(self):
        with self.assertRaisesRegex(audiofile.AudioError, "end must come after"):
            audiofile.envelope(self.wav, 2, 1)
        with self.assertRaisesRegex(audiofile.AudioError, "ffmpeg failed"):
            audiofile.envelope(str(self.dir / "nothing-here.mp3"), 0, 1)
        with mock.patch.object(audiofile, "ffmpeg", lambda: None):
            with self.assertRaisesRegex(audiofile.AudioError, "ffmpeg is not installed"):
                audiofile.envelope(self.wav, 0, 1)


# ------------------------------------------------------------------ what the doors share

class Asked(unittest.TestCase):
    """serve.estimate_request, wave_slice, estimate_answer, load_wavealign:
    the doors' questions and answers, without a server."""

    @classmethod
    def setUpClass(cls):
        import serve
        cls.serve = serve

    def refused(self, body, kind="span"):
        got, why = self.serve.estimate_request(body, kind)
        self.assertIsNone(got, body)
        self.assertTrue(why)
        return why

    def test_a_good_question(self):
        got, why = self.serve.estimate_request(
            {"texts": ["One.", "Two, three."], "start": 1, "end": 4.5}, "span")
        self.assertIsNone(why)
        self.assertEqual(got, {"start": 1.0, "end": 4.5, "texts": ["One.", "Two, three."],
                               "kind": "span", "wave": None})
        got, _ = self.serve.estimate_request({"texts": [""], "start": 0, "end": 1}, "point")
        self.assertEqual(got["kind"], "point", "the door's own kind when none is named")
        got, _ = self.serve.estimate_request({"texts": ["a"], "start": 0, "end": 1,
                                              "kind": "span"}, "point")
        self.assertEqual(got["kind"], "span")
        got, _ = self.serve.estimate_request(
            {"texts": ["a"], "start": 0, "end": 1, "wave": {"rate": 20, "start": 0.5,
                                                             "peaks": [0, 1, None]}}, "point")
        self.assertEqual(got["wave"], {"rate": 20.0, "start": 0.5, "peaks": [0, 1, None]})

    def test_what_is_refused(self):
        many = ["x"] * (self.serve.ESTIMATE_TEXTS + 1)
        for body, said in (
                ({"start": 0, "end": 1}, "texts"),
                ({"texts": "one", "start": 0, "end": 1}, "texts"),
                ({"texts": [], "start": 0, "end": 1}, "texts"),
                ({"texts": ["a", 3], "start": 0, "end": 1}, "texts"),
                ({"texts": many, "start": 0, "end": 1}, "at most 20000"),
                ({"texts": ["x" * 20001], "start": 0, "end": 1}, "20001 characters"),
                ({"texts": ["a"], "start": "0", "end": 1}, "numbers of seconds"),
                ({"texts": ["a"], "start": True, "end": 1}, "numbers of seconds"),
                ({"texts": ["a"], "start": float("nan"), "end": 1}, "numbers of seconds"),
                ({"texts": ["a"], "start": 0, "end": float("inf")}, "numbers of seconds"),
                ({"texts": ["a"], "start": 0}, "numbers of seconds"),
                ({"texts": ["a"], "start": -1, "end": 1}, "at 0 s or after"),
                ({"texts": ["a"], "start": 2, "end": 2}, "end must come after"),
                ({"texts": ["a"], "start": 2, "end": 2.05}, "too short to estimate"),
                ({"texts": ["a"], "start": 0, "end": 12 * 3600 + 1}, "12 hours"),
                ({"texts": ["a"], "start": 0, "end": 1, "kind": "words"}, "kind"),
                ({"texts": ["a"], "start": 0, "end": 1, "wave": [1, 2]}, "picture of the sound"),
                ({"texts": ["a"], "start": 0, "end": 1, "wave": {"rate": 20, "peaks": []}},
                 "picture of the sound"),
                ({"texts": ["a"], "start": 0, "end": 1, "wave": {"rate": 0, "peaks": [1]}},
                 "between 1 and 200"),
                ({"texts": ["a"], "start": 0, "end": 1, "wave": {"rate": 900, "peaks": [1]}},
                 "between 1 and 200"),
                ({"texts": ["a"], "start": 0, "end": 1,
                  "wave": {"rate": 20, "start": -2, "peaks": [1]}}, "waveform's start"),
                ({"texts": ["a"], "start": 0, "end": 1,
                  "wave": {"rate": 20, "peaks": [0] * (self.serve.ESTIMATE_WAVE + 1)}},
                 "too fine")):
            with self.subTest(said=said, body=str(body)[:80]):
                self.assertIn(said, self.refused(body))

    def test_a_recorded_waveform_is_cut_to_the_stretch(self):
        wave = {"rate": 20, "start": 1.0, "peaks": [k / 100 for k in range(100)]}
        values, times = self.serve.wave_slice(wave, 2.0, 3.0)
        # the k-th number was heard at 1.0 + k/20: 2.0 is k = 20, 3.0 is k = 40
        self.assertEqual(values, [k / 100 for k in range(20, 41)])
        self.assertEqual(len(times), 21)
        for got, want in zip(times, [k / 20 for k in range(21)]):
            self.assertAlmostEqual(got, want, places=9)
        # a stretch between two numbers takes the ones inside it
        values, times = self.serve.wave_slice(wave, 2.01, 2.12)
        self.assertEqual(values, [0.21, 0.22])
        self.assertAlmostEqual(times[0], 0.04)
        # past its end there is nothing; garbage counts as silence
        self.assertEqual(self.serve.wave_slice(wave, 9, 10), ([], []))
        values, _ = self.serve.wave_slice({"rate": 10, "start": 0,
                                           "peaks": [0.5, None, "x", -1, True, 2.0]}, 0, 1)
        self.assertEqual(values, [0.5, 0.0, 0.0, 0.0, 0.0, 2.0])
        # an integer four hundred digits long is no float either: silence,
        # and not an OverflowError out of the door as a 500
        values, _ = self.serve.wave_slice({"rate": 10, "start": 0,
                                           "peaks": [10 ** 400, 0.5, float("nan")]}, 0, 1)
        self.assertEqual(values, [0.0, 0.5, 0.0])

    def test_the_answer_is_absolute_and_to_a_hundredth(self):
        res = {"pieces": [{"t0": 0.0, "t1": 1.23456, "confidence": 1.0, "t0_min": 0, "t0_max": 0},
                          {"t0": 1.9, "t1": 2.5049, "confidence": 0.4321, "t0_min": 1.7,
                           "t0_max": 2.0},
                          {"t0": 2.5049, "t1": 4.0, "confidence": 1.7, "t0_min": 2.3,
                           "t0_max": 2.6}],
               "confidence": 0.61234, "anchored": 1, "boundaries": 2, "words": 9,
               "method": "wavealign", "version": "1"}
        got = self.serve.estimate_answer(res, 10.004, 14.004, "span")
        self.assertEqual([p["t0"] for p in got["pieces"]], [10.004, 11.9, 12.51])
        self.assertEqual(got["pieces"][0]["t0"], 10.004, "the line in hand, exactly")
        self.assertEqual([p["t1"] for p in got["pieces"]], [11.24, 12.51, 14.0])
        self.assertEqual([p["confidence"] for p in got["pieces"]], [1.0, 0.432, 1.0])
        self.assertEqual((got["pieces"][1]["t0_min"], got["pieces"][1]["t0_max"]), (11.7, 12.0))
        self.assertEqual({k: got[k] for k in ("ok", "confidence", "anchored", "boundaries",
                                                "words", "method")},
                         {"ok": True, "confidence": 0.612, "anchored": 1, "boundaries": 2,
                          "words": 9, "method": "wavealign"})
        self.assertEqual(set(got["pieces"][0]), {"t0", "t1", "confidence", "t0_min", "t0_max"})

    def test_a_caption_ends_where_the_next_begins_and_the_last_at_the_end(self):
        res = {"pieces": [{"t0": 0, "t1": 1.004}, {"t0": 1.004, "t1": 2.2},
                          {"t0": 2.2, "t1": 3.0}]}
        got = self.serve.estimate_answer(res, 5.25, 8.25, "point")["pieces"]
        self.assertEqual([(p["t0"], p["t1"]) for p in got],
                         [(5.25, 6.25), (6.25, 7.45), (7.45, 8.25)])

    def test_pieces_closer_than_a_hundredth_keep_a_finer_figure(self):
        res = {"pieces": [{"t0": 0, "t1": 0.002}, {"t0": 0.002, "t1": 0.004},
                          {"t0": 0.004, "t1": 0.006}]}
        got = self.serve.estimate_answer(res, 0, 0.006, "point")["pieces"]
        t0 = [p["t0"] for p in got]
        self.assertEqual(t0, sorted(set(t0)), "still strictly one after another: %r" % t0)
        self.assertTrue(all(p["t0"] < p["t1"] for p in got))

    def test_numpy_missing_is_said_in_plain_words(self):
        """The Python running Parseh without NumPy: the one door says what
        is missing and how Parseh gets it -- never a command to type."""
        with tempfile.TemporaryDirectory() as td:
            Path(td, "wavealign.py").write_text("import numpy\n", encoding="utf-8")
            saved = sys.modules.pop("wavealign", None)
            try:
                with mock.patch.object(sys, "path", [td] + sys.path), \
                        mock.patch.dict(sys.modules, {"numpy": None}):
                    engine, why = self.serve.load_wavealign()
            finally:
                sys.modules.pop("wavealign", None)
                if saved is not None:
                    sys.modules["wavealign"] = saved
        self.assertIsNone(engine)
        self.assertIn("needs numpy", why)
        self.assertIn("installer", why)
        for command in ("pip", "conda", "./", "python", ".sh", ".bat", "`"):
            self.assertNotIn(command, why, "no command to type: " + why)

    def test_the_two_doors_are_long_work_on_the_activity_list(self):
        kind, label, _after = self.serve.long_work(
            "POST", "/books/english/nowhere/reader/__clip/estimate", {}, 100)
        self.assertEqual((kind, label), ("narration", "Estimating the timings of a book by the sound"))
        kind, label, _after = self.serve.long_work("POST", "/youtube/api/estimate", {}, 100)
        self.assertEqual(kind, "narration")
        self.assertIn("by the sound", label)


# ------------------------------------------------------------------ the doors

class StandIn(object):
    """What lib/wavealign.estimate_pieces answers, in its shape, with a note
    of every question -- so what the door handed over can be looked at.  The
    pieces share the stretch equally; for a book the first boundary is left
    split by 0.3 s, as a pause heard between them would leave it."""

    def __init__(self):
        self.calls = []
        self.hold = None                # an Event: the answer waits for it

    def module(self):
        m = types.ModuleType("wavealign")
        m.estimate_pieces = self.estimate_pieces
        return m

    def estimate_pieces(self, envelope, duration, texts, kind="span", *, sample_times=None,
                        options=None, tokenize=None):
        self.calls.append({"envelope": list(envelope), "duration": duration, "texts": list(texts),
                           "kind": kind, "sample_times": None if sample_times is None
                           else list(sample_times)})
        if self.hold is not None:
            self.hold.wait(30)
        n = len(texts)
        t = [duration * k / n for k in range(n + 1)]
        pieces = []
        for k in range(n):
            t1 = t[k + 1] - (0.3 if kind == "span" and k == 0 and n > 1 else 0.0)
            pieces.append({"t0": t[k], "t1": t1, "confidence": 1.0 if k == 0 else 0.5,
                           "t0_min": max(0.0, t[k] - 0.1), "t0_max": t[k] + 0.1,
                           "speech": [t[k], t1]})
        return {"pieces": pieces, "confidence": 0.5, "anchored": 1, "boundaries": n - 1,
                "words": sum(len(x.split()) for x in texts), "method": "wavealign",
                "version": "1"}


@needs_ffmpeg
class Doors(unittest.TestCase):
    """serve.py's Handler over real HTTP, on a temporary toolbox: a book with
    one recording (tone, silence, tone), a film with the same sound, and a
    YouTube video with no film -- lib/wavealign.py stood in for."""

    @classmethod
    def setUpClass(cls):
        import serve
        import books
        import texparse
        import ytpages
        import prefs
        import network
        import offline
        cls.serve = serve
        td = tempfile.TemporaryDirectory()
        cls._td = td
        cls.root = root = Path(td.name) / "root"
        book = root / "books" / "english" / "mini-en"
        book.parent.mkdir(parents=True)
        shutil.copytree(BOOK_FIXTURE, book, ignore=shutil.ignore_patterns("reader"))
        (book / "audio").mkdir()
        tone_gap_tone(book / "audio" / "part1.mp3", "-c:a", "libmp3lame", secs=6)
        b = books.Book(str(book))
        subs = [x for ch in texparse.parse_book(b.main, b.lang)
                for pp in ch.paragraphs for x in pp.subs]
        serve.set_narrations(b, [{"id": "n1", "audio": "audio/part1.mp3", "transcript": "",
                                  "from": subs[0].num, "to": ""}])
        videos = root / "youtube" / "videos"
        cls.film_id = "street-market-a1b2c3"
        vdir = videos / "english" / cls.film_id
        vdir.mkdir(parents=True)
        sound = tone_gap_tone(Path(td.name) / "film-sound.wav", "-c:a", "pcm_s16le", secs=6)
        ff("-f", "lavfi", "-i", "testsrc=duration=6:size=160x120:rate=10", "-i", sound,
           "-shortest", "-c:v", "libx264", "-c:a", "aac", vdir / "media.mp4")
        (vdir / "video.json").write_text(json.dumps({
            "id": cls.film_id, "url": "", "title": "Street market", "language": "en",
            "gloss": "en", "duration": "0:06"}), encoding="utf-8")
        (vdir / "annotations.json").write_text(json.dumps(
            {"video": cls.film_id, "language": "en", "segments": [{"start": 0, "text": "Hello."}]}))
        cls.yt_id = YT_FIXTURE.name
        cls.yt_dir = videos / "english" / cls.yt_id
        shutil.copytree(YT_FIXTURE, cls.yt_dir)
        config = Path(td.name) / "config"
        cls.patches = [mock.patch.object(serve, "ROOT", str(root)),
                       mock.patch.object(serve._AtRoot, "directory", str(root)),
                       mock.patch.object(ytpages, "VIDEOS", str(videos)),
                       # nothing of this run reaches the checkout's own config/
                       mock.patch.object(prefs, "STORE", str(config / "prefs.json")),
                       mock.patch.object(network, "STORE", str(config / "network.json")),
                       mock.patch.object(offline, "DIGESTS", str(config / "digests.json")),
                       mock.patch.object(offline, "WHERES", str(config / "wheres.json")),
                       mock.patch.object(serve.Handler, "log_request", lambda *a, **k: None)]
        for p in cls.patches:
            p.start()
        cls.srv = serve.Server(("127.0.0.1", 0), serve.Handler)
        cls.port = cls.srv.server_address[1]
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        for p in reversed(cls.patches):
            p.stop()
        cls._td.cleanup()

    def setUp(self):
        self.aligner = StandIn()
        saved = sys.modules.get("wavealign")
        sys.modules["wavealign"] = self.aligner.module()

        def back():
            if saved is None:
                sys.modules.pop("wavealign", None)
            else:
                sys.modules["wavealign"] = saved
        self.addCleanup(back)
        wave = self.yt_dir / "waveform.json"
        if wave.exists():
            wave.unlink()

    def http(self, method, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=120)
        headers = {}
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        c.request(method, path, body, headers)
        r = c.getresponse()
        raw = r.read()
        c.close()
        return r.status, raw

    def ask(self, path, body, want=200):
        status, raw = self.http("POST", path, body)
        self.assertEqual(status, want, "%s -> %d %s" % (path, status, raw[:300]))
        return json.loads(raw.decode("utf-8"))

    BOOK = "/books/english/mini-en/reader/__clip/estimate"
    VIDEO = "/youtube/api/estimate"
    TEXTS = ["The first line, said once.", "A second.", "And the third one, the longest of all."]

    def tree(self):
        """Every file under the temporary toolbox, with its size and time:
        an estimate writes nothing anywhere."""
        return sorted((str(p), p.stat().st_size, p.stat().st_mtime_ns)
                      for p in self.root.rglob("*") if p.is_file())

    # ---- a book
    def test_a_book(self):
        before = self.tree()
        got = self.ask(self.BOOK, {"narration": "n1", "start": 0.5, "end": 2.9,
                                   "texts": self.TEXTS})
        call, = self.aligner.calls
        self.assertEqual((call["duration"], call["texts"], call["kind"], call["sample_times"]),
                         (2.4, self.TEXTS, "span", None), "a book is two numbers a piece")
        env = call["envelope"]
        self.assertEqual(len(env), 240, "one number every 10 ms of the stretch")
        # the stretch starts 0.5 s in: the tone until 1.0 s, silence to 2.0, the tone again
        self.assertTrue(all(v > 0.4 for v in env[3:47]), env[:50])
        self.assertTrue(all(v < 0.01 for v in env[54:146]), env[50:150])
        self.assertTrue(all(v > 0.4 for v in env[154:237]), env[150:])
        self.assertEqual(got["pieces"][0]["t0"], 0.5, "the line in hand, exactly")
        self.assertEqual([(p["t0"], p["t1"]) for p in got["pieces"]],
                         [(0.5, 1.0), (1.3, 2.1), (2.1, 2.9)],
                         "absolute, and the split the aligner heard kept")
        self.assertEqual((got["ok"], got["anchored"], got["boundaries"], got["method"]),
                         (True, 1, 2, "wavealign"))
        self.assertEqual(self.tree(), before, "and nothing was written")

    def test_a_book_s_first_recording_is_the_one_when_none_is_named(self):
        self.ask(self.BOOK, {"start": 0, "end": 3, "texts": ["a", "b"], "kind": "point"})
        self.assertEqual(self.aligner.calls[0]["kind"], "point")
        self.assertEqual(len(self.aligner.calls[0]["envelope"]), 300)

    def test_a_book_s_refusals(self):
        for body, want, said in (
                ({"narration": "n9", "start": 0, "end": 1, "texts": ["a"]}, 400, "no recording 'n9'"),
                ({"narration": ["n1"], "start": 0, "end": 1, "texts": ["a"]}, 400, "recording's id"),
                ({"narration": "n1", "start": 1, "end": 0.5, "texts": ["a"]}, 400, "end must come after"),
                ({"narration": "n1", "start": 0, "end": 1}, 400, "texts"),
                ({"narration": "n1", "start": 0, "end": 1, "texts": ["a"], "kind": "x"}, 400, "kind")):
            with self.subTest(said):
                j = self.ask(self.BOOK, body, want)
                self.assertFalse(j["ok"])
                self.assertIn(said, j["error"])
        j = self.ask("/books/english/nobook/reader/__clip/estimate",
                     {"start": 0, "end": 1, "texts": ["a"]}, 404)
        self.assertEqual(j, {"ok": False, "error": "no book here"})
        self.assertEqual(self.http("POST", self.BOOK, b"not json")[0], 400)
        self.assertEqual(self.aligner.calls, [], "nothing refused reached the aligner")

    # ---- a film on this machine
    def test_a_film(self):
        got = self.ask(self.VIDEO, {"video": self.film_id, "start": 1.5, "end": 6.0,
                                    "texts": self.TEXTS, "kind": "point"})
        call, = self.aligner.calls
        self.assertEqual((call["duration"], call["kind"], call["sample_times"]), (4.5, "point", None))
        env = call["envelope"]
        self.assertEqual(len(env), 450)
        self.assertTrue(all(v < 0.01 for v in env[5:45]), "1.5..2.0 s is silent")
        self.assertTrue(all(v > 0.3 for v in env[60:140]), "2.0..3.0 s is the tone")
        self.assertTrue(all(v < 0.01 for v in env[160:440]), "and after 3.0 s nothing")
        pieces = got["pieces"]
        self.assertEqual(pieces[0]["t0"], 1.5)
        self.assertEqual([p["t0"] for p in pieces], [1.5, 3.0, 4.5])
        for a, b in zip(pieces, pieces[1:]):
            self.assertEqual(a["t1"], b["t0"], "a caption runs until the next begins")
        self.assertEqual(pieces[-1]["t1"], 6.0)

    def test_a_video_s_kind_is_point_unless_it_says(self):
        self.ask(self.VIDEO, {"video": self.film_id, "start": 0, "end": 2, "texts": ["a", "b"]})
        self.assertEqual(self.aligner.calls[0]["kind"], "point")

    # ---- a YouTube video: only the picture a tab recorded
    def test_a_youtube_video_with_the_page_s_wave(self):
        peaks = [round(k / 1000, 3) for k in range(200)]       # 20 a second from 3.0 s
        got = self.ask(self.VIDEO, {"video": self.yt_id, "start": 4.0, "end": 8.0,
                                    "texts": self.TEXTS, "kind": "point",
                                    "wave": {"rate": 20, "start": 3.0, "peaks": peaks}})
        call, = self.aligner.calls
        # 4.0 s is the 20th number, 8.0 s the 100th
        self.assertEqual(call["envelope"], peaks[20:101])
        self.assertEqual(call["duration"], 4.0)
        self.assertEqual(len(call["sample_times"]), 81)
        self.assertAlmostEqual(call["sample_times"][0], 0.0)
        self.assertAlmostEqual(call["sample_times"][1], 0.05)
        self.assertAlmostEqual(call["sample_times"][-1], 4.0)
        self.assertEqual(got["pieces"][0]["t0"], 4.0)
        self.assertEqual(got["pieces"][-1]["t1"], 8.0)

    def test_a_youtube_video_with_its_waveform_on_the_shelf(self):
        peaks = [0.0] * 40 + [1.0] * 20 + [0.0] * 40            # 5 s at 20 a second
        (self.yt_dir / "waveform.json").write_text(json.dumps({"rate": 20, "peaks": peaks}),
                                                   encoding="utf-8")
        self.ask(self.VIDEO, {"video": self.yt_id, "start": 1.0, "end": 4.0,
                              "texts": ["a", "b"]})
        call, = self.aligner.calls
        self.assertEqual(call["envelope"], peaks[20:81])
        self.assertAlmostEqual(call["sample_times"][20], 1.0)
        self.assertEqual(call["kind"], "point")

    def test_a_youtube_video_not_drawn_yet(self):
        j = self.ask(self.VIDEO, {"video": self.yt_id, "start": 1.0, "end": 4.0,
                                  "texts": ["a", "b"]}, 409)
        self.assertFalse(j["ok"])
        self.assertIn("draw the sound", j["error"])
        # a waveform that ends before the stretch is no picture of it either
        # -- and the way out it names is one the page has: once a video is
        # drawn, "● draw the sound" is gone, so it cannot ask for that
        j = self.ask(self.VIDEO, {"video": self.yt_id, "start": 100, "end": 104,
                                  "texts": ["a", "b"],
                                  "wave": {"rate": 20, "start": 0, "peaks": [0.5] * 100}}, 409)
        self.assertIn("ends before this stretch begins", j["error"])
        self.assertIn("estimate it by the text", j["error"])
        self.assertNotIn("draw the sound", j["error"])
        self.assertEqual(self.aligner.calls, [])

    def test_a_video_s_refusals(self):
        j = self.ask(self.VIDEO, {"video": "nope", "start": 0, "end": 1, "texts": ["a"]}, 404)
        self.assertEqual(j, {"ok": False, "error": "no such video"})
        j = self.ask(self.VIDEO, {"video": "../../etc", "start": 0, "end": 1, "texts": ["a"]}, 404)
        self.assertFalse(j["ok"])
        j = self.ask(self.VIDEO, {"video": self.yt_id, "start": 0, "end": 1, "texts": ["a"],
                                  "wave": {"rate": 5000, "peaks": [1]}}, 400)
        self.assertIn("between 1 and 200", j["error"])
        self.assertEqual(self.aligner.calls, [])

    # ---- what this machine cannot do
    def test_without_ffmpeg(self):
        with mock.patch.object(audiofile, "ffmpeg", lambda: None):
            for path, body in ((self.BOOK, {"narration": "n1", "start": 0, "end": 2, "texts": ["a"]}),
                               (self.VIDEO, {"video": self.film_id, "start": 0, "end": 2,
                                             "texts": ["a"]})):
                with self.subTest(path):
                    j = self.ask(path, body, 409)
                    self.assertFalse(j["ok"])
                    self.assertIn("ffmpeg", j["error"])
                    self.assertIn("not installed", j["error"])
            # a YouTube video's picture is not ffmpeg's, and does not need it
            self.ask(self.VIDEO, {"video": self.yt_id, "start": 0, "end": 2, "texts": ["a"],
                                  "wave": {"rate": 20, "start": 0, "peaks": [0.2] * 60}})
        self.assertEqual(len(self.aligner.calls), 1)

    def test_without_numpy(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "wavealign.py").write_text("import numpy\n", encoding="utf-8")
            sys.modules.pop("wavealign", None)
            try:
                with mock.patch.object(sys, "path", [td] + sys.path), \
                        mock.patch.dict(sys.modules, {"numpy": None}):
                    for path, body in (
                            (self.BOOK, {"narration": "n1", "start": 0, "end": 2, "texts": ["a"]}),
                            (self.VIDEO, {"video": self.film_id, "start": 0, "end": 2,
                                          "texts": ["a"]}),
                            (self.VIDEO, {"video": self.yt_id, "start": 0, "end": 2, "texts": ["a"],
                                          "wave": {"rate": 20, "peaks": [0.2] * 60}})):
                        with self.subTest(path):
                            j = self.ask(path, body, 409)
                            self.assertIn("needs numpy", j["error"])
            finally:
                sys.modules.pop("wavealign", None)
        self.assertEqual(self.aligner.calls, [])

    def test_a_bad_question_is_asked_before_the_machine_is(self):
        # a 400 is a 400 even where the answer would have been a 409
        with mock.patch.object(audiofile, "ffmpeg", lambda: None):
            j = self.ask(self.BOOK, {"narration": "n1", "start": 0, "end": 2}, 400)
        self.assertIn("texts", j["error"])

    def test_an_aligner_that_fails_is_a_500_in_words(self):
        def broken(*a, **k):
            raise RuntimeError("the numbers ran out")
        sys.modules["wavealign"].estimate_pieces = broken
        with mock.patch("traceback.print_exc"):
            j = self.ask(self.BOOK, {"narration": "n1", "start": 0, "end": 2, "texts": ["a"]}, 500)
        self.assertEqual(j, {"ok": False, "error": "the estimate failed: the numbers ran out"})

    def test_a_stretch_too_big_for_the_memory_says_what_to_do(self):
        # the one failure with a way out: a shorter stretch, or the text --
        # and the slot is free again afterwards
        def too_big(*a, **k):
            raise MemoryError()
        sys.modules["wavealign"].estimate_pieces = too_big
        j = self.ask(self.BOOK, {"narration": "n1", "start": 0, "end": 2, "texts": ["a"]}, 409)
        self.assertIn("too long to estimate by the sound at once", j["error"])
        self.assertIn("by the text", j["error"])
        sys.modules["wavealign"].estimate_pieces = self.aligner.estimate_pieces
        self.ask(self.BOOK, {"narration": "n1", "start": 0, "end": 2, "texts": ["a"]})

    # ---- a long one keeps nobody waiting
    def test_a_long_estimate_does_not_block_the_server(self):
        self.aligner.hold = threading.Event()
        done = {}

        def long_one():
            done["answer"] = self.http("POST", self.BOOK, {"narration": "n1", "start": 0,
                                                           "end": 3, "texts": self.TEXTS})
        t = threading.Thread(target=long_one, daemon=True)
        t.start()
        try:
            for _ in range(200):
                if self.aligner.calls:
                    break
                time.sleep(0.02)
            self.assertTrue(self.aligner.calls, "the estimate is under way")
            began = time.time()
            status, raw = self.http("GET", "/__activity")
            self.assertEqual(status, 200)
            self.assertLess(time.time() - began, 5, "answered while the estimate runs")
            running = [e["label"] for e in json.loads(raw)["running"]]
            self.assertTrue(any("by the sound" in lab for lab in running),
                            "and the estimate is on the activity list: %r" % running)
            status, _ = self.http("GET", "/books/english/mini-en/book.json")
            self.assertEqual(status, 200)
            self.assertNotIn("answer", done, "the estimate is still waiting")
            # A SECOND ESTIMATE IS REFUSED AT ONCE, in words, while the
            # first runs -- never queued behind it, where a sheet would wait
            # for minutes with nothing said
            began = time.time()
            j = self.ask(self.VIDEO, {"video": self.film_id, "start": 0, "end": 2,
                                      "texts": ["a", "b"]}, 409)
            self.assertLess(time.time() - began, 5, "refused at once")
            self.assertEqual(j, {"ok": False, "error": self.serve.ESTIMATE_BUSY})
            self.assertIn("try again when it has finished", j["error"])
            self.assertEqual(len(self.aligner.calls), 1, "the second never reached the aligner")
        finally:
            self.aligner.hold.set()
        t.join(30)
        self.assertEqual(done["answer"][0], 200)
        # and once it has finished, the next is answered
        self.aligner.hold = None
        self.ask(self.VIDEO, {"video": self.film_id, "start": 0, "end": 2, "texts": ["a", "b"]})


# ------------------------------------------------------------------ the real one

@needs_ffmpeg
@unittest.skipUnless(real_aligner(), "lib/wavealign.py does not import here (it needs numpy)")
class WithTheRealAligner(Doors):
    """The same toolbox with lib/wavealign.py itself behind the doors: the
    invariants the contract promises, on a real recording."""

    def setUp(self):
        sys.modules.pop("wavealign", None)

    # the stand-in's own tests are not this class's
    test_a_book = test_a_book_s_first_recording_is_the_one_when_none_is_named = None
    test_a_film = test_a_video_s_kind_is_point_unless_it_says = None
    test_a_youtube_video_with_the_page_s_wave = None
    test_a_youtube_video_with_its_waveform_on_the_shelf = None
    test_a_youtube_video_not_drawn_yet = test_a_video_s_refusals = None
    test_without_ffmpeg = test_without_numpy = None
    test_a_bad_question_is_asked_before_the_machine_is = None
    test_an_aligner_that_fails_is_a_500_in_words = None
    test_a_stretch_too_big_for_the_memory_says_what_to_do = None
    test_a_long_estimate_does_not_block_the_server = test_a_book_s_refusals = None

    def check(self, got, start, end, n, kind):
        pieces = got["pieces"]
        self.assertEqual(len(pieces), n)
        self.assertEqual(pieces[0]["t0"], start, "the line in hand, exactly")
        for p in pieces:
            self.assertLess(p["t0"], p["t1"])
            self.assertTrue(start <= p["t0"] and p["t1"] <= end, p)
            self.assertTrue(0 <= p["confidence"] <= 1)
            self.assertTrue(p["t0_min"] <= p["t0"] <= p["t0_max"], p)
        for a, b in zip(pieces, pieces[1:]):
            if kind == "point":
                self.assertEqual(a["t1"], b["t0"])
            else:
                self.assertLessEqual(a["t1"], b["t0"])
        if kind == "point":
            self.assertEqual(pieces[-1]["t1"], end)
        self.assertEqual(got["method"], "wavealign")
        self.assertEqual(got["boundaries"], n - 1)

    def test_a_book_by_the_real_aligner(self):
        got = self.ask(self.BOOK, {"narration": "n1", "start": 0.25, "end": 3.5,
                                   "texts": ["The first sentence, all of it.",
                                             "And then the second."]})
        self.check(got, 0.25, 3.5, 2, "span")
        # the one pause in the recording is 1.0..2.0 s, a whole second of
        # nothing between two sentences, and the one boundary between the two
        # pieces belongs in it -- even though the first piece has more text
        # than the first tone has time for: a pause that clear is worth more
        # than the length of the text, which is the order the owner's
        # specification of the aligner puts them in ("strong waveform pauses
        # over proportional timing assumptions")
        a, b = got["pieces"]
        self.assertTrue(0.9 <= a["t1"] <= 2.1 and 0.9 <= b["t0"] <= 2.1,
                        "the boundary is not in the second of silence: %r" % got)

    def test_a_film_by_the_real_aligner(self):
        got = self.ask(self.VIDEO, {"video": self.film_id, "start": 0, "end": 6,
                                    "texts": ["Hello there.", "Bring a bag."]})
        self.check(got, 0.0, 6.0, 2, "point")

    def test_a_youtube_video_by_the_real_aligner(self):
        peaks = ([0.8] * 20 + [0.0] * 20) * 3
        got = self.ask(self.VIDEO, {"video": self.yt_id, "start": 0, "end": 6,
                                    "texts": ["One.", "Two.", "Three."],
                                    "wave": {"rate": 20, "start": 0, "peaks": peaks}})
        self.check(got, 0.0, 6.0, 3, "point")


if __name__ == "__main__":
    unittest.main()
