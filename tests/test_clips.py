# SPDX-License-Identifier: GPL-3.0-or-later
"""The clip tray (lib/clips.py) and the hub's doors to it (serve.py).

    python3 -m unittest discover -s tests -p test_clips.py

A clip is cut where the sentence is -- a book's narration, a film on this
machine -- and put onto a card somewhere else, so what has to hold is:

  * a clip's NAME is unique and pasteable (`<stem>-<6 hex>.<ext>`), its
    bytes say what it is, and a browser's WAV or WebM comes out in the
    format ffmpeg writes best here;
  * a cut lands the window it was asked for, to within a frame of audio,
    with the source's sound from its first moment (ffmpeg's MP3 decoder is
    silent for a while after a seek), and a cut or a recording that holds
    no sound is refused -- judged by decoding it, not by ffprobe's guess;
  * hostile numbers (NaN, 1e400, 400 digits) and deep JSON are a 400 or
    ignored, never a 500; a Range that is not bytes is ignored;
  * the tray lists newest first, filtered, and refuses every name that is
    not a clip's -- nothing outside clips/ is reachable through it;
  * the hub's routes, driven over REAL HTTP against serve.py's own Handler
    on a temporary toolbox (a book with two recordings and timings, a film
    on this machine, a YouTube video, a studio document): uploads, the
    listing, media with Range, delete, preview, cut and peaks from a book
    and from a film, the YouTube refusal, and the 409 that tells a page
    with no ffmpeg behind it to record in the browser instead.

Real files throughout, made by ffmpeg in a temporary directory; without
ffmpeg the tests that need it skip.
"""
import base64
import contextlib
import http.client
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "markdown" / "exlex", ROOT / "markdown" / "app",
               ROOT / "youtube" / "lib", ROOT / "lib", ROOT):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import audiofile  # noqa: E402
import clips      # noqa: E402

HAVE = audiofile.have_ffmpeg()
needs_ffmpeg = unittest.skipUnless(HAVE, "ffmpeg is not installed on this machine")
BEST = audiofile.best_output()[0] if HAVE else None

BOOK_FIXTURE = ROOT / "tests" / "fixtures" / "books" / "english" / "mini-en"
YT_FIXTURE = ROOT / "tests" / "fixtures" / "videos" / "english" / "eN5wX7zA9bC"
# a real 1x1 PNG, as a canvas's toDataURL would hand it over
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
JPEG_HEAD = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
NAME = re.compile(r"^([a-z0-9][a-z0-9._\-]*)-([0-9a-f]{6})\.([a-z0-9]+)$")


def ff(*args):
    r = subprocess.run([audiofile.ffmpeg(), "-y", "-loglevel", "error"] + [str(a) for a in args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError("ffmpeg %s -> exit %d: %s" % (" ".join(map(str, args)),
                                                            r.returncode, r.stderr))
    return args[-1]


def sine(out, secs, freq=440, *codec):
    return ff("-f", "lavfi", "-i", "sine=frequency=%d:duration=%s" % (freq, secs), *codec, out)


def silence(out, secs):
    return ff("-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono", "-t", secs, out)


def film(out, secs=6):
    return ff("-f", "lavfi", "-i", "testsrc=duration=%s:size=160x120:rate=10" % secs,
              "-f", "lavfi", "-i", "sine=frequency=440:duration=%s" % secs, "-shortest",
              "-c:v", "libx264", "-c:a", "aac", out)


def loud(p, threshold=1000, rate=44100):
    """The first second a decoded file is louder than `threshold` (None when
    it never is), and its length."""
    import array
    r = subprocess.run([audiofile.ffmpeg(), "-v", "error", "-i", str(p), "-ac", "1",
                        "-ar", str(rate), "-f", "s16le", "-"], capture_output=True)
    if r.returncode != 0:
        raise AssertionError("decoding %s -> exit %d: %s" % (p, r.returncode, r.stderr[-500:]))
    samples = array.array("h")
    samples.frombytes(r.stdout[:len(r.stdout) // 2 * 2])
    if sys.byteorder == "big":
        samples.byteswap()
    first = next((i for i, v in enumerate(samples) if abs(v) > threshold), None)
    return (None if first is None else first / rate), len(samples) / rate


def empty_wav():
    """A WAV header saying 44.1 kHz, 16 bit, and no samples after it: what a
    browser's capture makes of a recording that got nothing."""
    import struct
    fmt = struct.pack("<4sIHHIIHH", b"fmt ", 16, 1, 1, 44100, 88200, 2, 16)
    body = b"WAVE" + fmt + b"data" + struct.pack("<I", 0)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def disk(d):
    """What is really in a directory, dot files included."""
    try:
        return sorted(os.listdir(d))
    except OSError:
        return []


class Tray(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.tmp = Path(td.name)
        self.tray = self.tmp / "clips"
        was = clips.DIR
        clips.set_dir(self.tray)
        self.addCleanup(clips.set_dir, was)

    def media(self, name):
        return (self.tmp / name).read_bytes()


# ------------------------------------------------------------------ the store

class SaveAudio(Tray):
    @needs_ffmpeg
    def test_an_mp3_is_kept_as_it_came_under_a_unique_name(self):
        data = Path(sine(self.tmp / "in.mp3", 2, 440, "-c:a", "libmp3lame")).read_bytes()
        rec = clips.save_audio(data, "Hello World!", {
            "lang": "en", "label": "1.2", "text": "Hello, world.",
            "source": {"kind": "book", "book": "/books/english/mini-en", "narration": "n1",
                       "start": 1.5, "junk": "dropped", "end": True}})
        m = NAME.match(rec["name"])
        self.assertTrue(m, rec["name"])
        self.assertEqual((m.group(1), m.group(3)), ("hello-world", "mp3"))
        self.assertEqual(disk(self.tray), sorted([rec["name"], rec["name"] + ".json"]))
        self.assertEqual((self.tray / rec["name"]).read_bytes(), data, "not re-encoded")
        self.assertEqual(rec["kind"], "audio")
        self.assertEqual(rec["path"], "audio/" + rec["name"])
        self.assertEqual(rec["url"], "/clips/media/" + rec["name"])
        self.assertEqual(rec["size"], len(data))
        self.assertEqual((rec["lang"], rec["label"], rec["text"]), ("en", "1.2", "Hello, world."))
        self.assertEqual(rec["source"], {"kind": "book", "book": "/books/english/mini-en",
                                         "narration": "n1", "start": 1.5})
        self.assertAlmostEqual(rec["duration"], 2.0, delta=0.08)
        self.assertRegex(rec["created"], r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$")
        on_disk = json.loads((self.tray / (rec["name"] + ".json")).read_text(encoding="utf-8"))
        self.assertEqual(on_disk["label"], "1.2")
        self.assertEqual(on_disk["source"]["narration"], "n1")
        self.assertEqual(clips.record(rec["name"]), rec)

        again = clips.save_audio(data, "Hello World!", {})
        self.assertNotEqual(again["name"], rec["name"], "every clip is its own file")
        self.assertTrue(again["name"].startswith("hello-world-"))

    @needs_ffmpeg
    def test_a_browser_recording_comes_out_in_the_best_format(self):
        for name, codec in (("rec.wav", ("-c:a", "pcm_s16le")), ("rec.webm", ("-c:a", "libopus"))):
            with self.subTest(name):
                data = Path(sine(self.tmp / name, 3, 440, *codec)).read_bytes()
                rec = clips.save_audio(data, "سلام", {"lang": "fa"})
                self.assertTrue(rec["name"].startswith("clip-"), "no Latin in the hint: 'clip'")
                self.assertTrue(rec["name"].endswith(BEST), rec["name"])
                out = (self.tray / rec["name"]).read_bytes()
                self.assertEqual(audiofile.kind(out), BEST)
                self.assertAlmostEqual(audiofile.duration(str(self.tray / rec["name"])), 3.0, delta=0.1)
        self.assertEqual([n for n in disk(self.tray) if n.startswith(".")], [],
                         "no scratch file left behind")

    def test_without_ffmpeg_a_wav_is_kept(self):
        import wave
        p = self.tmp / "rec.wav"
        with contextlib.closing(wave.open(str(p), "wb")) as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(b"\x20\x00" * 8000)
        with mock.patch.object(audiofile, "ffmpeg", lambda: None):
            rec = clips.save_audio(p.read_bytes(), "word", {})
        self.assertTrue(rec["name"].endswith(".wav"))
        self.assertEqual((self.tray / rec["name"]).read_bytes(), p.read_bytes())
        self.assertAlmostEqual(rec["duration"], 1.0, places=3)
        with mock.patch.object(audiofile, "ffmpeg", lambda: None):
            with self.assertRaisesRegex(clips.ClipError, "holds no sound"):
                clips.save_audio(empty_wav(), "nothing", {})
        self.assertEqual(disk(self.tray), sorted([rec["name"], rec["name"] + ".json"]))

    @needs_ffmpeg
    def test_a_recording_with_no_sound_in_it_is_refused(self):
        """A header with nothing after it re-encodes into a file that plays
        nothing; the tray said 201 to it and listed a clip that was silence."""
        webm = Path(sine(self.tmp / "rec.webm", 3, 440, "-c:a", "libopus")).read_bytes()
        cut_short = webm[:700]
        self.assertEqual(audiofile.kind(cut_short), ".webm", "still WebM by its bytes")
        self.assertEqual(audiofile.kind(empty_wav()), ".wav")
        for label, data in (("empty wav", empty_wav()), ("truncated webm", cut_short)):
            with self.subTest(label):
                with self.assertRaisesRegex(clips.ClipError, "holds no sound"):
                    clips.save_audio(data, label, {})
        self.assertEqual(disk(self.tray), [], "nothing kept, not even scratch")
        # and the whole of the same recording is kept, with its true length
        rec = clips.save_audio(webm, "whole", {})
        self.assertAlmostEqual(rec["duration"], 3.0, delta=0.05)

    def test_refusals_write_nothing(self):
        cases = ((b"", "empty upload"),
                 (PNG_1PX, "only MP3, M4A, AAC, Ogg, Opus, WAV, FLAC and WebM recordings"),
                 (b"RIFF\x00\x00\x00\x00WAVEfmt " + b"\x00" * 64, None))
        for data, why in cases[:2]:
            with self.subTest(why):
                with self.assertRaisesRegex(clips.ClipError, re.escape(why)):
                    clips.save_audio(data, "x", {})
        with mock.patch.object(audiofile, "MAX_BYTES", 16):
            with self.assertRaisesRegex(clips.ClipError, "larger than 30 MB"):
                clips.save_audio(cases[2][0], "x", {})
        self.assertEqual(disk(self.tray), [])


class SaveImage(Tray):
    def test_png_jpeg_and_a_data_url(self):
        a = clips.save_image(PNG_1PX, "Frame at 0:12", {"lang": "ja", "source": {"kind": "film", "video": "v"}})
        self.assertTrue(NAME.match(a["name"]) and a["name"].startswith("frame-at-0-12-"), a["name"])
        self.assertTrue(a["name"].endswith(".png"))
        self.assertEqual((a["kind"], a["path"]), ("image", "images/" + a["name"]))
        self.assertNotIn("duration", a)
        b = clips.save_image(JPEG_HEAD + b"\x00" * 100, "", {})
        self.assertTrue(b["name"].startswith("clip-") and b["name"].endswith(".jpg"), b["name"])
        url = "data:image/png;base64," + base64.b64encode(PNG_1PX).decode()
        for form in (url, url.encode()):
            c = clips.save_image(form, "canvas", {})
            self.assertTrue(c["name"].endswith(".png"))
            self.assertEqual((self.tray / c["name"]).read_bytes(), PNG_1PX, "decoded, not stored as text")

    def test_refusals(self):
        for data in (b"GIF89a....", b"%PDF-1.4", "data:text/html;base64,PHNjcmlwdD4=",
                     "data:image/png;base64,!!!notbase64", b"", 42):
            with self.subTest(repr(data)[:30]):
                with self.assertRaises(clips.ClipError):
                    clips.save_image(data, "x", {})
        self.assertEqual(disk(self.tray), [])


@needs_ffmpeg
class Cut(Tray):
    def test_a_cut_lands_the_window(self):
        src = sine(self.tmp / "six.mp3", 6, 440, "-c:a", "libmp3lame")
        rec = clips.cut(src, 1.0, 3.5, "The wind", {"lang": "en", "label": "1.1",
                                                     "source": {"kind": "book", "narration": "n1"}})
        self.assertTrue(rec["name"].startswith("the-wind-") and rec["name"].endswith(BEST))
        path = self.tray / rec["name"]
        self.assertAlmostEqual(audiofile.duration(str(path)), 2.5, delta=0.06)
        self.assertAlmostEqual(rec["duration"], 2.5, delta=0.06)
        self.assertEqual(rec["source"], {"kind": "book", "narration": "n1", "start": 1.0, "end": 3.5})
        self.assertEqual(sorted(disk(self.tray)), sorted([rec["name"], rec["name"] + ".json"]))

    def test_a_cut_out_of_a_film(self):
        rec = clips.cut(film(self.tmp / "media.mp4"), 2, 3.25, "scene", {})
        self.assertAlmostEqual(audiofile.duration(str(self.tray / rec["name"])), 1.25, delta=0.06)

    def test_refusals(self):
        src = sine(self.tmp / "two.wav", 2)
        for start, end, why in ((1.5, 1.0, "end must come after"), (1, 1, "end must come after"),
                                ("a", 2, "numbers of seconds"), (float("nan"), 1, "numbers of seconds"),
                                (True, 2, "numbers of seconds"), (0, 301, "at most 300 seconds")):
            with self.subTest(start=start, end=end):
                with self.assertRaisesRegex(clips.ClipError, why):
                    clips.cut(src, start, end, "x", {})
        with self.assertRaisesRegex(clips.ClipError, "not on this machine"):
            clips.cut(self.tmp / "gone.mp3", 0, 1, "x", {})
        with self.assertRaisesRegex(clips.ClipError, "ffmpeg is not installed"):
            with mock.patch.object(audiofile, "ffmpeg", lambda: None):
                clips.cut(src, 0, 1, "x", {})
        # past the end of the recording: ffmpeg writes a header with no sound
        # in it, and that is not a clip -- in every format it writes
        mp3 = sine(self.tmp / "two.mp3", 2, 440, "-c:a", "libmp3lame")
        for recording in (src, mp3):
            for start in (2.0, 10):
                with self.subTest(recording=Path(recording).name, start=start):
                    with self.assertRaisesRegex(clips.ClipError, "no sound at %.2f s" % start):
                        clips.cut(recording, start, start + 1, "x", {})
        self.assertEqual(disk(self.tray), [], "nothing, not even scratch, is left")
        # a window that runs past the end is the part that is there
        rec = clips.cut(mp3, 1.5, 3, "tail", {})
        self.assertAlmostEqual(rec["duration"], 0.5, delta=0.06)

    def test_a_cut_holds_the_sound_from_its_first_moment(self):
        """ffmpeg's MP3 decoder gives 50 to 140 ms of silence after a seek:
        a clip cut out of a narration, which is usually an MP3, must not."""
        src = sine(self.tmp / "tone.mp3", 8, 440, "-c:a", "libmp3lame", "-q:a", "4")
        for start in (0.3, 1.02, 5.5):
            with self.subTest(start=start):
                rec = clips.cut(src, start, start + 0.28, "t", {})
                first, length = loud(self.tray / rec["name"])
                self.assertAlmostEqual(length, 0.28, delta=0.03)
                self.assertIsNotNone(first, "the tone is in the clip")
                self.assertLess(first, 0.012, "and it is there from the start")

    def test_a_cut_in_the_tail_ffprobe_does_not_know(self):
        """A VBR MP3 with no Xing header: ffprobe estimates its length from the
        first frames' bitrate and says 27 s of a 60 s file.  The cut is judged
        by what it holds, so the last half of the file is still cut."""
        src = self.tmp / "noxing.mp3"
        ff("-f", "lavfi", "-i", "anoisesrc=d=5:a=0.6", "-f", "lavfi", "-i", "sine=frequency=300:duration=55",
           "-filter_complex", "[1]volume=0.2[q];[0][q]concat=n=2:v=0:a=1", "-ac", "1",
           "-c:a", "libmp3lame", "-q:a", "4", "-write_xing", "0", src)
        guess = audiofile.duration(str(src))
        if guess is None or guess > 38:
            self.skipTest("this ffprobe knows the length (%s s): nothing to prove" % guess)
        self.assertEqual(clips.plays(str(src)) // 1, 60.0, "the file really is a minute long")
        rec = clips.cut(src, 40.0, 41.0, "tail", {})
        first, length = loud(self.tray / rec["name"], threshold=500)
        self.assertAlmostEqual(rec["duration"], 1.0, delta=0.06)
        self.assertAlmostEqual(length, 1.0, delta=0.06)
        self.assertIsNotNone(first, "the tone is in the clip")


class ListingAndNames(Tray):
    def made(self, name, lang, created):
        self.tray.mkdir(exist_ok=True)
        (self.tray / name).write_bytes(PNG_1PX if name.endswith(".png") else b"ID3" + b"\x00" * 30)
        (self.tray / (name + ".json")).write_text(json.dumps(
            {"lang": lang, "label": name, "text": "", "source": {}, "created": created}))

    def test_newest_first_and_filtered(self):
        self.made("old-aaaaaa.mp3", "en", "2026-01-01 10:00:00")
        self.made("new-bbbbbb.mp3", "fa", "2026-09-01 10:00:00")
        self.made("mid-cccccc.png", "en", "2026-05-01 10:00:00")
        for junk in ("README.md", ".part-0123.mp3", "x.txt", "Upper-dddddd.mp3", "orphan.json"):
            (self.tray / junk).write_bytes(b"ID3 junk")
        (self.tray / "sub").mkdir()
        (self.tray / "sub" / "deep-eeeeee.mp3").write_bytes(b"ID3")
        names = lambda **kw: [r["name"] for r in clips.listing(**kw)]
        self.assertEqual(names(), ["new-bbbbbb.mp3", "mid-cccccc.png", "old-aaaaaa.mp3"])
        self.assertEqual(names(kind="audio"), ["new-bbbbbb.mp3", "old-aaaaaa.mp3"])
        self.assertEqual(names(kind="image"), ["mid-cccccc.png"])
        self.assertEqual(names(lang="en"), ["mid-cccccc.png", "old-aaaaaa.mp3"])
        self.assertEqual(names(lang="en", kind="audio"), ["old-aaaaaa.mp3"])
        self.assertEqual(names(lang="ja"), [])

    def test_two_in_one_second_list_in_the_order_made(self):
        self.made("first-aaaaaa.mp3", "en", "2026-09-01 10:00:00")
        self.made("second-bbbbbb.mp3", "en", "2026-09-01 10:00:00")
        past = time.time() - 5
        os.utime(self.tray / "first-aaaaaa.mp3", (past, past))
        self.assertEqual([r["name"] for r in clips.listing()], ["second-bbbbbb.mp3", "first-aaaaaa.mp3"])

    def test_a_file_dropped_in_by_hand_still_lists(self):
        self.tray.mkdir()
        (self.tray / "dropped-abcdef.mp3").write_bytes(b"ID3" + b"\x00" * 9)
        (rec,) = clips.listing()
        self.assertEqual((rec["name"], rec["lang"], rec["label"], rec["source"]),
                         ("dropped-abcdef.mp3", "", "", {}))
        self.assertRegex(rec["created"], r"^\d{4}-")

    def test_path_and_delete_refuse_what_is_not_a_clip(self):
        self.made("keep-aaaaaa.mp3", "en", "2026-09-01 10:00:00")
        (self.tmp / "secret.mp3").write_bytes(b"ID3")
        for bad in ("../secret.mp3", "sub/keep-aaaaaa.mp3", "keep-aaaaaa.mp3.json", "Keep-aaaaaa.mp3",
                    "missing-ffffff.mp3", "", ".part-x.mp3", "keep-aaaaaa", None, "..", "/etc/passwd"):
            with self.subTest(bad):
                with self.assertRaises(KeyError):
                    clips.path(bad)
                with self.assertRaises(KeyError):
                    clips.delete(bad)
        self.assertTrue((self.tmp / "secret.mp3").exists())
        self.assertEqual(clips.path("keep-aaaaaa.mp3"), str(self.tray / "keep-aaaaaa.mp3"))
        clips.delete("keep-aaaaaa.mp3")
        self.assertEqual(disk(self.tray), [])
        with self.assertRaises(KeyError):
            clips.delete("keep-aaaaaa.mp3")

    def test_empty_takes_every_clip_and_nothing_else(self):
        self.assertEqual(clips.empty(), 0, "no tray yet: nothing to take")
        self.made("one-aaaaaa.mp3", "en", "2026-09-01 10:00:00")
        self.made("two-bbbbbb.png", "fa", "2026-09-02 10:00:00")
        (self.tray / "three-cccccc.mp3").write_bytes(b"ID3" + b"\x00" * 9)   # no JSON beside it
        for keep in ("README.md", ".part-0123.mp3", "orphan-dddddd.mp3.json"):
            (self.tray / keep).write_bytes(b"keep")
        (self.tray / "sub").mkdir()
        self.assertEqual(clips.empty(), 3)
        self.assertEqual(disk(self.tray), [".part-0123.mp3", "README.md", "orphan-dddddd.mp3.json", "sub"])
        self.assertEqual(clips.listing(), [])
        self.assertEqual(clips.empty(), 0)


# ------------------------------------------------------------------ the hub

@needs_ffmpeg
class HubRoutes(unittest.TestCase):
    """serve.py's Handler over real HTTP, on a temporary toolbox."""

    @classmethod
    def setUpClass(cls):
        import serve
        import books
        import texparse
        import ytpages
        cls.serve = serve
        td = tempfile.TemporaryDirectory()
        cls._td = td
        cls.root = root = Path(td.name)
        # a book with two recordings: n1 a tone, n2 silence -- so a waveform
        # says which file it was read from
        book = root / "books" / "english" / "mini-en"
        book.parent.mkdir(parents=True)
        shutil.copytree(BOOK_FIXTURE, book, ignore=shutil.ignore_patterns("reader"))
        (book / "audio").mkdir()
        sine(book / "audio" / "part1.mp3", 6, 440, "-c:a", "libmp3lame")
        silence(book / "audio" / "part2.wav", 4)
        b = books.Book(str(book))
        subs = [x for ch in texparse.parse_book(b.main, b.lang)
                for pp in ch.paragraphs for x in pp.subs]
        labels = [x.num for x in subs]
        serve.set_narrations(b, [
            {"id": "n1", "audio": "audio/part1.mp3", "transcript": "", "from": labels[0], "to": labels[0]},
            {"id": "n2", "audio": "audio/part2.wav", "transcript": "", "from": labels[1], "to": ""}])
        import timestamp as ts
        cls.times = {labels[0]: (0.75, 3.1), labels[1]: (0.5, 2.0)}
        (book / "timings.json").write_text(json.dumps({
            "audio": "audio/part1.mp3", "book": "mini-en", "generated_by": "test_clips",
            "subs": {ts.subkey(x): {"t0": cls.times[x.num][0], "t1": cls.times[x.num][1], "conf": 1.0,
                                    "src": "manual", "label": x.num, "n": "n1" if i == 0 else "n2"}
                     for i, x in enumerate(subs[:2])}}), encoding="utf-8")
        cls.labels = labels
        # a film on this machine, and a YouTube video with none
        videos = root / "youtube" / "videos"
        cls.local_id = "street-market-a1b2c3"
        vdir = videos / "english" / cls.local_id
        vdir.mkdir(parents=True)
        film(vdir / "media.mp4")
        (vdir / "video.json").write_text(json.dumps({
            "id": cls.local_id, "url": "", "title": "Street market", "language": "en",
            "gloss": "en", "duration": "0:06"}), encoding="utf-8")
        (vdir / "annotations.json").write_text(json.dumps(
            {"video": cls.local_id, "language": "en", "segments": [{"start": 0, "text": "Hello."}]}))
        shutil.copytree(YT_FIXTURE, videos / "english" / YT_FIXTURE.name)
        # a studio document with a picture and, where the studio has the door
        # for it, a recording -- served by the same send_file
        library = root / "library"
        cls.tray = root / "clips"
        cls.patches = [mock.patch.object(serve, "ROOT", str(root)),
                       mock.patch.object(serve._AtRoot, "directory", str(root)),
                       mock.patch.object(ytpages, "VIDEOS", str(videos)),
                       mock.patch.object(serve.studio.store, "LIB", library),
                       mock.patch.object(clips, "DIR", str(cls.tray)),
                       # quiet: every POST is logged, and a test run is not a log
                       mock.patch.object(serve.Handler, "log_request", lambda *a, **k: None)]
        for p in cls.patches:
            p.start()
        store = serve.studio.store
        meta = store.create("---\ntitle: Clips\ntarget: en\n---\n\nText.\n")
        cls.doc_id = meta["id"]
        cls.picture = store.save_image(cls.doc_id, "big.png", PNG_1PX + os.urandom(3000))
        cls.doc_audio = None
        if hasattr(store, "save_audio"):
            cls.doc_audio = store.save_audio(
                cls.doc_id, "word.mp3", Path(sine(root / "doc.mp3", 2, 660, "-c:a", "libmp3lame")).read_bytes())
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

    def http(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=120)
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
            headers = dict(headers or {}, **{"Content-Type": "application/json"})
        c.request(method, path, body, headers or {})
        r = c.getresponse()
        raw = r.read()
        c.close()
        return r.status, r.msg, raw

    def json_of(self, method, path, body=None, want=200):
        status, _, raw = self.http(method, path, body)
        j = json.loads(raw.decode("utf-8"))
        self.assertEqual(status, want, "%s %s -> %d %s" % (method, path, status, raw[:300]))
        return j

    def tray_files(self):
        return disk(self.tray)

    def empty_tray(self):
        shutil.rmtree(self.tray, ignore_errors=True)

    def setUp(self):
        self.empty_tray()

    # ---- the tray's own doors
    def test_status(self):
        j = self.json_of("GET", "/clips/api/status")
        self.assertEqual(j, {"ok": True, "ffmpeg": True, "format": BEST})
        with mock.patch.object(audiofile, "ffmpeg", lambda: None):
            j = self.json_of("GET", "/clips/api/status")
        self.assertEqual(j, {"ok": True, "ffmpeg": False, "format": None})

    def test_upload_list_media_range_delete(self):
        wav = Path(sine(self.root / "up.wav", 2, 440, "-c:a", "pcm_s16le")).read_bytes()
        j = self.json_of("POST", "/clips/api/upload?kind=audio&hint=Good%20morning&lang=en"
                         "&label=0%3A12&text=Good%20morning.", wav, want=201)
        clip = j["clip"]
        self.assertTrue(j["ok"])
        self.assertTrue(clip["name"].startswith("good-morning-") and clip["name"].endswith(BEST))
        self.assertEqual((clip["lang"], clip["label"], clip["text"]), ("en", "0:12", "Good morning."))
        self.assertIn(clip["name"], self.tray_files())
        data = (self.tray / clip["name"]).read_bytes()
        self.assertEqual(audiofile.kind(data), BEST)

        url = "data:image/png;base64," + base64.b64encode(PNG_1PX).decode()
        img = self.json_of("POST", "/clips/api/upload?kind=image&hint=frame&lang=fa", url.encode(), want=201)["clip"]
        self.assertTrue(img["name"].endswith(".png"))
        self.assertEqual((self.tray / img["name"]).read_bytes(), PNG_1PX)

        before = self.tray_files()
        for q, body in (("kind=audio", PNG_1PX), ("kind=image", wav), ("kind=audio", b""), ("kind=video", wav)):
            with self.subTest(q):
                j = self.json_of("POST", "/clips/api/upload?" + q, body, want=400)
                self.assertFalse(j["ok"])
                self.assertTrue(j["error"])
        self.assertEqual(self.tray_files(), before, "a refused upload writes nothing")

        listed = self.json_of("GET", "/clips/api/list")
        self.assertEqual([c["name"] for c in listed["clips"]], [img["name"], clip["name"]])
        self.assertEqual([c["name"] for c in self.json_of("GET", "/clips/api/list?kind=audio&lang=en")["clips"]],
                         [clip["name"]])
        self.assertEqual(self.json_of("GET", "/clips/api/list?lang=ja")["clips"], [])
        self.json_of("GET", "/clips/api/list?kind=nope", want=400)

        # the file, whole and in pieces
        size = len(data)
        for path in (clip["url"], "/clips/media/audio/" + clip["name"]):
            status, head, body = self.http("GET", path)
            self.assertEqual((status, body), (200, data))
            self.assertEqual(head["Content-Type"], audiofile.mime_for(clip["name"]))
            self.assertEqual(head["Accept-Ranges"], "bytes")
            self.assertEqual(head["Content-Length"], str(size))
        status, head, body = self.http("GET", clip["url"], headers={"Range": "bytes=10-99"})
        self.assertEqual(status, 206)
        self.assertEqual(head["Content-Range"], "bytes 10-99/%d" % size)
        self.assertEqual(head["Content-Length"], "90")
        self.assertEqual(body, data[10:100])
        status, head, body = self.http("GET", clip["url"], headers={"Range": "bytes=-50"})
        self.assertEqual((status, body, head["Content-Range"]),
                         (206, data[-50:], "bytes %d-%d/%d" % (size - 50, size - 1, size)))
        status, head, body = self.http("GET", clip["url"], headers={"Range": "bytes=%d-" % (size - 7)})
        self.assertEqual((status, body), (206, data[-7:]))
        status, head, body = self.http("GET", clip["url"], headers={"Range": "bytes=%d-" % size})
        self.assertEqual((status, head["Content-Range"], body), (416, "bytes */%d" % size, b""))
        # a Range that is not a byte range is ignored, as RFC 9110 14.2 has a
        # server do with a unit it does not know: the whole file, not a 400
        for asked in ("items=0-1", "Bytes=0-1", "bytes= 0-1", "bytes=abc"):
            with self.subTest(asked=asked):
                status, head, body = self.http("GET", clip["url"], headers={"Range": asked})
                self.assertEqual((status, head["Content-Length"], body), (200, str(size), data))
                self.assertNotIn("Content-Range", head)
        status, head, body = self.http("HEAD", clip["url"], headers={"Range": "bytes=0-9"})
        self.assertEqual((status, head["Content-Length"], body), (206, "10", b""))
        status, head, body = self.http("GET", "/clips/media/images/" + img["name"])
        self.assertEqual((status, body, head["Content-Type"]), (200, PNG_1PX, "image/png"))
        for bad in ("/clips/media/images/" + clip["name"], "/clips/media/audio/" + img["name"],
                    "/clips/media/..%2fup.wav", "/clips/media/%2e%2e", "/clips/media/nope-abcdef.mp3",
                    "/clips/media/" + clip["name"] + ".json"):
            with self.subTest(bad):
                self.assertEqual(self.http("GET", bad)[0], 404)
        self.assertEqual(self.http("POST", clip["url"], b"x")[0], 405)

        self.assertEqual(self.json_of("DELETE", "/clips/api/" + clip["name"]), {"ok": True})
        self.assertEqual(self.tray_files(), sorted([img["name"], img["name"] + ".json"]))
        self.json_of("DELETE", "/clips/api/" + clip["name"], want=404)
        self.json_of("DELETE", "/clips/api/..%2f..%2fserve.py", want=404)
        self.assertEqual(self.http("GET", clip["url"])[0], 404)

    def test_the_tray_page_lists_and_empty_deletes(self):
        """The page a person deletes clips from (never a file manager): every
        clip listed, escaped, and POST /clips/api/empty taking them all."""
        wav = Path(sine(self.root / "page.wav", 1, 440, "-c:a", "pcm_s16le")).read_bytes()
        said = self.json_of("POST", "/clips/api/upload?kind=audio&hint=said&lang=fa&text=%3Cb%3Ehi%3C%2Fb%3E",
                            wav, want=201)["clip"]
        frame = clips.save_image(PNG_1PX, "frame", {"lang": "it", "source": {"title": "A & B", "url": "javascript:alert(1)"}})
        self.assertEqual(self.http("GET", "/clips")[:1], (302,))
        status, head, raw = self.http("GET", "/clips/")
        page = raw.decode("utf-8")
        self.assertEqual((status, head["Content-Type"].split(";")[0]), (200, "text/html"))
        self.assertEqual(re.findall(r'<div class="crow" data-name="([^"]+)"', page), [frame["name"], said["name"]])
        self.assertIn('<audio controls preload="none" src="/clips/media/%s">' % said["name"], page)
        self.assertIn('<img src="/clips/media/%s"' % frame["name"], page)
        self.assertIn('<b dir="auto">&lt;b&gt;hi&lt;/b&gt;</b>', page, "a clip's words are escaped")
        self.assertIn("A &amp; B", page)
        self.assertNotIn("javascript:", page, "a source link is a path or https, nothing else")
        for link, linked in (("/books/english/x/reader/#p3", True), ("https://www.youtube.com/watch?v=x", True),
                             ("//elsewhere.example/", False), ("http://elsewhere.example/", False)):
            with self.subTest(link=link):
                rec = clips.save_image(PNG_1PX, "linked", {"source": {"title": "Where", "url": link}})
                shown = self.http("GET", "/clips/")[2].decode("utf-8")
                row = re.search(r'<div class="crow" data-name="%s".*?</button></div>' % re.escape(rec["name"]), shown).group(0)
                self.assertEqual('<a href="%s">Where</a>' % link in row, linked, row)
                clips.delete(rec["name"])
        self.assertIn('id="empty-tray"', page)
        hub = self.http("GET", "/")[2].decode("utf-8")
        door = re.search(r'<a class="door wide" href="/clips/">.*?</a>', hub, re.S).group(0)
        self.assertIn('<span class="tag on">2 clips</span>', door)

        self.assertEqual(self.http("GET", "/clips/api/empty")[0], 405)
        self.assertEqual(self.http("POST", "/clips/")[0], 405)
        self.assertEqual(self.json_of("POST", "/clips/api/empty"), {"ok": True, "deleted": 2})
        self.assertEqual(self.tray_files(), [])
        self.assertEqual(self.json_of("POST", "/clips/api/empty"), {"ok": True, "deleted": 0})
        page = self.http("GET", "/clips/")[2].decode("utf-8")
        self.assertNotIn('class="crow"', page)
        door = re.search(r'<a class="door wide" href="/clips/">.*?</a>', self.http("GET", "/")[2].decode("utf-8"), re.S).group(0)
        self.assertIn('<span class="tag">the tray is empty</span>', door)

    def test_preview_renders_a_card_with_the_tray_as_its_assets(self):
        img = clips.save_image(PNG_1PX, "cat", {})
        md = (":::exercise flashcard\ncard-type: vocab\ntarget: [cat]{tl}\nmeaning: gatto\n"
              "front-image: images/%s\nfront-audio: audio/word-abcdef.mp3\n:::" % img["name"])
        j = self.json_of("POST", "/clips/api/preview", {"markdown": md, "lang": "en"})
        self.assertTrue(j["ok"])
        self.assertIn("ex-flashcard", j["html"])
        self.assertIn('src="/clips/media/images/%s"' % img["name"], j["html"])
        self.assertIn('lang="en"', j["html"], "the card is read in the language it was asked in")
        import mdparser
        if hasattr(mdparser, "AUDIO_PATH_RE"):
            self.assertIn('src="/clips/media/audio/word-abcdef.mp3"', j["html"])
        self.json_of("POST", "/clips/api/preview", {"markdown": 12}, want=400)
        self.assertEqual(self.http("GET", "/clips/api/preview")[0], 405)

    # ---- a book's recordings
    def reader(self, what):
        return "/books/english/mini-en/reader/__clip/" + what

    def test_cut_from_a_book(self):
        t0, t1 = self.times[self.labels[0]]
        j = self.json_of("POST", self.reader("cut"), {
            "narration": "n1", "start": t0, "end": t1, "lang": "en", "hint": "the clock",
            "label": self.labels[0], "text": "The clock ..."}, want=201)
        clip = j["clip"]
        self.assertTrue(j["ok"])
        self.assertTrue(clip["name"].startswith("the-clock-") and clip["name"].endswith(BEST))
        path = self.tray / clip["name"]
        self.assertTrue(path.is_file(), "written on disk, in the tray")
        self.assertAlmostEqual(audiofile.duration(str(path)), t1 - t0, delta=0.06)
        self.assertEqual(clip["source"]["kind"], "book")
        self.assertEqual(clip["source"]["book"], "/books/english/mini-en")
        self.assertEqual(clip["source"]["narration"], "n1")
        self.assertEqual((clip["source"]["start"], clip["source"]["end"]), (t0, t1))
        self.assertEqual((clip["lang"], clip["label"]), ("en", self.labels[0]))
        # the book's own language when the page sends none, and the first
        # recording when it names none
        j = self.json_of("POST", self.reader("cut"), {"start": 0.2, "end": 0.9}, want=201)
        self.assertEqual((j["clip"]["lang"], j["clip"]["source"]["narration"]), ("en", "n1"))
        self.assertTrue(j["clip"]["name"].startswith("clip-"))
        # the same file served back through the tray, seekable
        status, head, body = self.http("GET", clip["url"], headers={"Range": "bytes=0-3"})
        self.assertEqual((status, body), (206, path.read_bytes()[:4]))
        # the narration is an MP3, whose decoder is silent for a moment after
        # a seek: the clip still has the sound from its first moment
        for start in (1.0, 1.02, 2.5):
            with self.subTest(start=start):
                j = self.json_of("POST", self.reader("cut"), {
                    "narration": "n1", "start": start, "end": start + 0.28}, want=201)
                first, length = loud(self.tray / j["clip"]["name"])
                self.assertAlmostEqual(length, 0.28, delta=0.03)
                self.assertIsNotNone(first, "the tone is in the clip")
                self.assertLess(first, 0.012, "and it is there from the start")
        peaks = self.json_of("POST", self.reader("peaks"), {"narration": "n1", "start": 1.02,
                                                            "end": 1.22, "buckets": 10})["peaks"]
        self.assertTrue(all(v > 0.5 for v in peaks), "the waveform is the tone, from its first bucket: %s" % peaks)

    def test_peaks_from_the_recording_named(self):
        tone = self.json_of("POST", self.reader("peaks"), {"narration": "n1", "start": 1, "end": 3, "buckets": 50})
        self.assertEqual((tone["ok"], len(tone["peaks"]), tone["start"], tone["end"]), (True, 50, 1.0, 3.0))
        self.assertEqual(max(tone["peaks"]), 1.0)
        quiet = self.json_of("POST", self.reader("peaks"), {"narration": "n2", "start": 1, "end": 3, "buckets": 50})
        self.assertEqual(quiet["peaks"], [0.0] * 50, "n2 is the silent file: it was the one read")
        first = self.json_of("POST", self.reader("peaks"), {"narration": "", "start": -2, "end": 1})
        self.assertEqual((len(first["peaks"]), first["start"], max(first["peaks"])), (400, 0.0, 1.0))

    def test_the_book_narration_ignores_a_range_that_is_not_bytes(self):
        """The static path the reader plays its narration from shares the
        Range parser with send_file, and ignores what is not a byte range."""
        url = "/books/english/mini-en/audio/part1.mp3"
        whole = self.http("GET", url)
        self.assertEqual(whole[0], 200)
        data = whole[2]
        status, head, body = self.http("GET", url, headers={"Range": "bytes=10-19"})
        self.assertEqual((status, head["Content-Range"], body), (206, "bytes 10-19/%d" % len(data), data[10:20]))
        for asked in ("items=0-1", "Bytes=0-1", "bytes=abc"):
            with self.subTest(asked=asked):
                status, head, body = self.http("GET", url, headers={"Range": asked})
                self.assertEqual((status, body), (200, data))
                self.assertNotIn("Content-Range", head)

    def test_hostile_numbers_and_nesting_are_refused_or_ignored_never_a_500(self):
        """Python's json reads NaN, Infinity and 1e400, integers of any length
        and nesting deep enough to exhaust the stack; none is a server fault."""
        def raw(path, text):
            status, _, body = self.http("POST", path, text.encode("utf-8"),
                                        {"Content-Type": "application/json"})
            return status, json.loads(body.decode("utf-8"))
        for buckets in ("NaN", "Infinity", "-Infinity", "1e400", "-5", "1e300", '"x"', "true", "null"):
            with self.subTest(buckets=buckets):
                status, j = raw(self.reader("peaks"),
                                '{"narration": "n1", "start": 1, "end": 2, "buckets": %s}' % buckets)
                self.assertEqual(status, 200, j)
                self.assertTrue(j["ok"])
                self.assertIn(len(j["peaks"]), (1, 400, 4000))
        huge = "9" * 400
        for what in ("cut", "peaks"):
            for body in ('{"narration": "n1", "start": %s, "end": 2}' % huge,
                         '{"narration": "n1", "start": 1, "end": %s}' % huge,
                         '{"narration": "n1", "start": NaN, "end": 2}'):
                with self.subTest(what=what, body=body[:40]):
                    status, j = raw(self.reader(what), body)
                    self.assertEqual((status, j["ok"]), (400, False), j)
                    self.assertIn("numbers of seconds", j["error"])
        for body in ('{"video": "%s", "start": %s, "end": 2}' % (self.local_id, huge),):
            status, j = raw("/youtube/api/clip", body)
            self.assertEqual(status, 400, j)
        deep = "[" * 30000                  # as it is, inside the request line's 65536
        status, _, body = self.http("POST", "/clips/api/upload?kind=image&hint=deep&source=" + deep,
                                    PNG_1PX)
        self.assertEqual(status, 201, body[:300])
        self.assertEqual(json.loads(body)["clip"]["source"], {}, "a source past reading is no source")
        status, _, body = self.http("POST", "/clips/api/upload?kind=image&hint=big&source="
                                    + urllib.parse.quote('{"start": %s, "title": "t"}' % huge), PNG_1PX)
        self.assertEqual(status, 201, body[:300])
        self.assertEqual(json.loads(body)["clip"]["source"], {"title": "t"})
        listed = self.json_of("GET", "/clips/api/list")
        self.assertEqual(len(listed["clips"]), 2)

    def test_a_recording_with_no_sound_is_not_a_clip(self):
        webm = Path(sine(self.root / "rec.webm", 3, 440, "-c:a", "libopus")).read_bytes()
        for label, data in (("empty.wav", empty_wav()), ("trunc.webm", webm[:700])):
            with self.subTest(label):
                j = self.json_of("POST", "/clips/api/upload?kind=audio&hint=" + label, data, want=400)
                self.assertEqual(j, {"ok": False, "error": "the recording holds no sound"})
        self.assertEqual(self.tray_files(), [])

    def test_book_refusals(self):
        before = self.tray_files()
        for body, want, why in (
                ({"narration": "n9", "start": 0, "end": 1}, 400, "no recording 'n9'"),
                ({"narration": "n1", "start": 2, "end": 1}, 400, "end must come after"),
                ({"narration": "n1", "start": "x", "end": 1}, 400, "numbers of seconds"),
                ({"narration": "n1", "start": 0, "end": 400}, 400, "at most"),
                ({"narration": ["n1"], "start": 0, "end": 1}, 400, "recording's id"),
                ({"narration": "n1", "start": 30, "end": 31}, 400, "no sound at 30.00 s")):
            for what in ("cut", "peaks") if "no sound" not in why else ("cut",):
                with self.subTest(what=what, body=body):
                    j = self.json_of("POST", self.reader(what), body, want=want)
                    self.assertFalse(j["ok"])
                    self.assertIn(why, j["error"])
        j = self.json_of("POST", "/books/english/nobook/reader/__clip/cut", {"start": 0, "end": 1}, want=404)
        self.assertFalse(j["ok"])
        self.assertEqual(self.http("POST", self.reader("cut"), b"not json")[0], 400)
        self.assertNotEqual(self.http("POST", self.reader("elsewhere"), {"start": 0, "end": 1})[0], 405,
                            "the door is on the books POST allowlist")
        self.assertEqual(self.http("GET", self.reader("cut"))[0], 404, "a GET is a file, and there is none")
        self.assertEqual(self.tray_files(), before, "nothing refused was written")

    def test_without_ffmpeg_the_page_is_told_to_record(self):
        with mock.patch.object(audiofile, "ffmpeg", lambda: None):
            for path, body in ((self.reader("cut"), {"narration": "n1", "start": 1, "end": 2}),
                               (self.reader("peaks"), {"narration": "n1", "start": 1, "end": 2}),
                               ("/youtube/api/clip", {"video": self.local_id, "start": 1, "end": 2}),
                               ("/youtube/api/peaks", {"video": self.local_id, "start": 1, "end": 2})):
                with self.subTest(path):
                    j = self.json_of("POST", path, body, want=409)
                    self.assertEqual(j, {"ok": False, "error": "ffmpeg is not installed", "record": True})
        self.assertEqual(self.tray_files(), [])

    # ---- a film on this machine
    def test_cut_and_peaks_from_a_local_film(self):
        j = self.json_of("POST", "/youtube/api/clip", {
            "video": self.local_id, "start": 1.5, "end": 3.0, "lang": "en", "hint": "market",
            "label": "0:01", "text": "Hello."}, want=201)
        clip = j["clip"]
        self.assertAlmostEqual(audiofile.duration(str(self.tray / clip["name"])), 1.5, delta=0.06)
        self.assertEqual(clip["source"], {"kind": "film", "video": self.local_id, "title": "Street market",
                                          "url": "/youtube/v/%s/#t=1" % self.local_id,
                                          "start": 1.5, "end": 3.0})
        no_lang = self.json_of("POST", "/youtube/api/clip", {"video": self.local_id, "start": 0, "end": 1}, want=201)
        self.assertEqual(no_lang["clip"]["lang"], "en", "the video's own language")
        peaks = self.json_of("POST", "/youtube/api/peaks", {"video": self.local_id, "start": 0, "end": 6, "buckets": 60})
        self.assertEqual(len(peaks["peaks"]), 60)
        self.assertGreater(min(peaks["peaks"][2:-2]), 0.5, "the film's sound is a steady tone")

    def test_a_youtube_video_is_refused(self):
        for what in ("clip", "peaks"):
            with self.subTest(what):
                j = self.json_of("POST", "/youtube/api/" + what,
                                 {"video": YT_FIXTURE.name, "start": 0, "end": 1}, want=400)
                self.assertEqual(j, {"ok": False, "error": "only a film on this machine can be cut"})
                j = self.json_of("POST", "/youtube/api/" + what,
                                 {"video": "../../etc", "start": 0, "end": 1}, want=404)
                self.assertFalse(j["ok"])
        self.assertEqual(self.tray_files(), [])

    # ---- everything else send_file serves
    def test_studio_document_media_is_range_aware_inside_the_hub(self):
        pic = (self.root / "library").rglob(self.picture)
        data = next(p for p in pic if p.is_file()).read_bytes()
        url = "/studio/media/%s/images/%s" % (self.doc_id, self.picture)
        status, head, body = self.http("GET", url)
        self.assertEqual((status, body), (200, data))
        status, head, body = self.http("GET", url, headers={"Range": "bytes=100-199"})
        self.assertEqual((status, head["Content-Range"], body),
                         (206, "bytes 100-199/%d" % len(data), data[100:200]))
        status, head, body = self.http("GET", url, headers={"Range": "bytes=99999-"})
        self.assertEqual(status, 416)
        if self.doc_audio:
            url = "/studio/media/%s/audio/%s" % (self.doc_id, self.doc_audio)
            status, head, body = self.http("GET", url, headers={"Range": "bytes=4-"})
            self.assertEqual(status, 206)
            self.assertEqual(head["Content-Type"], "audio/mpeg")
            whole = self.http("GET", url)[2]
            self.assertEqual(body, whole[4:])

    def test_the_card_kit_is_served_when_it_is_there(self):
        lib = self.root / "lib"
        lib.mkdir(exist_ok=True)
        try:
            for name in ("cardkit.js", "cardkit.css"):
                with self.subTest(name):
                    self.assertEqual(self.http("GET", "/lib/" + name)[0], 404, "not written yet")
                    (lib / name).write_text("/* kit */", encoding="utf-8")
                    status, head, body = self.http("GET", "/lib/" + name)
                    self.assertEqual((status, body), (200, b"/* kit */"))
                    self.assertIn("javascript" if name.endswith(".js") else "text/css",
                                  head["Content-Type"])
            (lib / "unlisted.js").write_text("/* no */", encoding="utf-8")
            self.assertEqual(self.http("GET", "/lib/unlisted.js")[0], 404,
                             "only the files STATIC_FILES names are on the web")
        finally:
            shutil.rmtree(lib)


class Notes(unittest.TestCase):
    def test_a_note_may_carry_a_recording_in_a_bundle(self):
        import bundle
        for e in audiofile.EXTS:
            self.assertIn("." + e, bundle.NOTES_EXTS)
        self.assertNotIn(".svg", bundle.NOTES_EXTS)


if __name__ == "__main__":
    unittest.main()
