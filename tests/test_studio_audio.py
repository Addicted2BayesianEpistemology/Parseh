"""A studio document's recordings: stored, listed and deleted, served a byte
range at a time, carried out and back in zips and backups, brought in from
the clip tray, and laid out by the same numbering as its pictures
(markdown/app/store.py, markdown/app/server.py).

    python3 -m unittest discover -s tests -p test_studio_audio.py

The recordings are real: ffmpeg writes a three-second tone in every format
the studio takes into a temporary directory (a format this machine's ffmpeg
cannot write skips the tests that need it; without ffmpeg a WAV is written by
the standard library and the rest skip).  The routes are driven twice:
through a fake handler, and through the studio's own handler on a real
socket, on a temporary library -- a byte range is only a byte range when it
went over the wire."""
import http.client
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.parse
import wave
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "markdown" / "exlex", ROOT / "markdown" / "app",
               ROOT / "lib", ROOT / "youtube" / "lib"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import audiofile  # noqa: E402
import htmlgen    # noqa: E402
import server     # noqa: E402
import store      # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"pixels"
FULL = """---
title: Cats
subtitle: about cats
note: a small line
lang: en
target: fa
---

Body [گربه]{tl}.
"""
HUMAN_REFUSAL = "only MP3, M4A, AAC, Ogg, Opus, WAV, FLAC and WebM recordings are supported"

# the encoder ffmpeg writes each format with
CODECS = {"mp3": "libmp3lame", "ogg": "libvorbis", "opus": "libopus", "webm": "libopus",
          "m4a": "aac", "flac": "flac", "wav": "pcm_s16le"}
SOUNDS = {}          # (ext, frequency) -> bytes
_TMP = None


def setUpModule():
    global _TMP
    _TMP = tempfile.TemporaryDirectory(prefix="parseh-audio-test-")
    d = Path(_TMP.name)
    ffmpeg = shutil.which("ffmpeg")
    for freq in (440, 660, 880):
        for ext, codec in CODECS.items():
            if not ffmpeg or (freq != 440 and ext not in ("mp3", "wav")):
                continue
            out = d / ("tone-%d.%s" % (freq, ext))
            r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                                "sine=frequency=%d:duration=3" % freq, "-c:a", codec, str(out)],
                               capture_output=True)
            if r.returncode == 0 and out.is_file() and out.stat().st_size:
                SOUNDS[(ext, freq)] = out.read_bytes()
    if ffmpeg:
        # an MP4 with a picture track and no sound: its first bytes are an M4A's
        out = d / "video-only.mp4"
        r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                            "testsrc=duration=1:size=64x48:rate=5", "-an", "-c:v", "mpeg4", str(out)],
                           capture_output=True)
        if r.returncode == 0 and out.is_file() and out.stat().st_size:
            SOUNDS[("video-only", 0)] = out.read_bytes()
    for freq in (440, 660, 880):
        if ("wav", freq) not in SOUNDS:
            out = d / ("stdlib-%d.wav" % freq)
            with wave.open(str(out), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(8000)
                w.writeframes(bytes([freq % 251, 0]) * 8000 * 3)
            SOUNDS[("wav", freq)] = out.read_bytes()


def tearDownModule():
    _TMP.cleanup()


def sound(case, ext, freq=440):
    """The real recording, or the test is skipped: this ffmpeg cannot write it."""
    if (ext, freq) not in SOUNDS:
        case.skipTest("ffmpeg could not write a .%s here" % ext)
    return SOUNDS[(ext, freq)]


def zip_of(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


class Fake:
    """What the studio's routes use of a handler, recording the answer."""

    def __init__(self, body=None, query="", raw=b""):
        self.body, self.raw = body, raw
        self.query = urllib.parse.parse_qs(query)
        self.sent = None

    def _json_body(self):
        return self.body

    def _body(self):
        return self.raw

    def send_json(self, payload, status=200):
        self.sent = (status, payload)

    def send_bytes(self, data, ctype, status=200, headers=None):
        self.sent = (status, data, ctype, headers or {})

    def send_file(self, path, download_name=None, inline_type=None):
        self.sent = ("file", Path(path), download_name)


class LibraryCase(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.lib = Path(td.name) / "library"
        self.lib.mkdir()
        was = store.use_library(self.lib)
        self.addCleanup(store.use_library, was)
        self.tray = Path(td.name) / "clips"
        self.tray.mkdir()
        was_tray = store.CLIPS_DIR
        store.set_clips_dir(self.tray)
        self.addCleanup(store.set_clips_dir, was_tray)

    def doc(self, body=""):
        return store.create(FULL + body)["id"]

    def files(self, doc_id, sub="audio"):
        d = store.doc_dir(doc_id) / sub
        return sorted(p.name for p in d.iterdir()) if d.is_dir() else []


# ---------------------------------------------------------------- storing

class SaveTests(LibraryCase):
    def test_the_extension_follows_the_bytes_and_the_name_is_folded(self):
        doc = self.doc()
        for ext, upload, want in (("mp3", "Word.mp3", "word.mp3"),
                                  ("wav", "word.mp3", "word.wav"),
                                  ("ogg", "lesson", "lesson.ogg"),
                                  ("opus", "lesson.bin", "lesson.opus"),
                                  ("opus", "kept.ogg", "kept.ogg"),   # the Ogg family keeps its spelling
                                  ("webm", "take.webm", "take.webm"),
                                  ("m4a", "song.mp4", "song.m4a"),
                                  ("flac", "Leçon Un!.FLAC", "lecon-un.flac")):
            with self.subTest(ext=ext, upload=upload):
                data = sound(self, ext)
                name = store.save_audio(doc, upload, data)
                self.assertEqual(name, want)
                self.assertTrue(audiofile.NAME_RE.match(name))
                self.assertEqual((store.audio_dir(doc) / name).read_bytes(), data)

    def test_a_clash_is_numbered_and_the_same_file_is_stored_once(self):
        doc = self.doc()
        a, b, c = sound(self, "mp3", 440), sound(self, "mp3", 880), sound(self, "mp3", 660)
        self.assertEqual(store.save_audio(doc, "word.mp3", a), "word.mp3")
        self.assertEqual(store.save_audio(doc, "word.mp3", b), "word-2.mp3")
        self.assertEqual(store.save_audio(doc, "Word.MP3", c), "word-3.mp3")
        self.assertEqual(store.save_audio(doc, "word.mp3", a), "word.mp3", "the same file again")
        self.assertEqual(store.save_audio(doc, "word.mp3", b), "word-2.mp3")
        self.assertEqual(self.files(doc), ["word-2.mp3", "word-3.mp3", "word.mp3"])
        self.assertEqual((store.audio_dir(doc) / "word-2.mp3").read_bytes(), b)

    def test_what_claims_to_be_a_recording_and_holds_no_sound_is_refused(self):
        doc = self.doc()
        # a UTF-16 text: its byte-order mark reads as an MPEG frame header
        utf16 = b"\xff\xfe" + ("Only words, and no recording.\n" * 20).encode("utf-16-le")
        with self.assertRaises(store.StoreError) as caught:
            store.save_audio(doc, "utf16.mp3", utf16)
        self.assertEqual(str(caught.exception), HUMAN_REFUSAL)
        # a film with no sound track: an MP4 by its first bytes, silent decoded
        video = sound(self, "video-only", 0)
        self.assertEqual(audiofile.kind(video, "videoonly.mp3"), ".m4a")
        with self.assertRaises(store.StoreError) as caught:
            store.save_audio(doc, "videoonly.mp3", video)
        self.assertEqual(str(caught.exception), "the recording holds no sound")
        self.assertEqual(self.files(doc), [], "nothing written, no temporary file left")
        # through the upload route, as the page sends it: a refusal, not a 201
        h = Fake(query="name=videoonly.mp3", raw=video)
        with self.assertRaises(store.StoreError):
            server.api_audio_upload(h, doc)
        self.assertIsNone(h.sent)
        self.assertEqual(store.save_audio(doc, "tone.m4a", sound(self, "m4a")), "tone.m4a",
                         "an M4A with sound in it is kept")
        # a machine without ffmpeg cannot decode: it refuses nothing for that
        with mock.patch.object(audiofile, "ffmpeg", lambda: None):
            self.assertEqual(store.save_audio(doc, "videoonly.mp3", video), "videoonly.m4a")

    def test_what_is_empty_not_a_recording_or_too_large_is_refused_and_nothing_is_written(self):
        doc = self.doc()
        mp3 = sound(self, "mp3")
        big = mp3 + b"\0" * (audiofile.MAX_BYTES + 1 - len(mp3))
        for data, message in ((b"", "empty upload"),
                              (PNG, HUMAN_REFUSAL),
                              (b"this is only some text, and not a recording", HUMAN_REFUSAL),
                              (big, "recording larger than 30 MB")):
            with self.subTest(message=message, size=len(data)):
                with self.assertRaises(store.StoreError) as caught:
                    store.save_audio(doc, "word.mp3", data)
                self.assertEqual(str(caught.exception), message)
        self.assertEqual(self.files(doc), [])
        self.assertEqual(store.save_audio(doc, "word.mp3", mp3[:audiofile.MAX_BYTES]), "word.mp3",
                         "right at the limit is taken")
        with self.assertRaises(KeyError):
            store.save_audio("no-such-doc", "word.mp3", mp3)


class ListTests(LibraryCase):
    def test_the_list_says_what_the_markdown_names(self):
        doc = self.doc("\n![a word](audio/word.mp3)\n\n:::exercise flashcard\ncard-type: vocab\n"
                       "target: x\nmeaning: y\nback-audio: audio/back.ogg\n:::\n\n"
                       "see myaudio/aa.mp3 and audio/aa.mp3x\n")
        store.save_audio(doc, "word.mp3", sound(self, "mp3"))
        store.save_audio(doc, "back.ogg", sound(self, "ogg"))
        store.save_audio(doc, "aa.mp3", sound(self, "mp3", 880))
        d = store.audio_dir(doc)
        (d / "notes.txt").write_text("not a recording")
        (d / ".hidden.mp3").write_bytes(sound(self, "mp3"))
        (d / "Upper.MP3").write_bytes(sound(self, "mp3"))
        listed = store.list_audio(doc)
        self.assertEqual([(r["name"], r["referenced"]) for r in listed],
                         [("aa.mp3", False), ("back.ogg", True), ("word.mp3", True)],
                         "only names a recording may have; a name inside another is no reference")
        self.assertEqual(listed[2]["size"], len(sound(self, "mp3")))
        self.assertEqual(store.list_audio(self.doc()), [], "no audio/ at all")

    def test_a_path_is_given_only_for_a_recording_that_is_there(self):
        doc = self.doc()
        store.save_audio(doc, "word.mp3", sound(self, "mp3"))
        self.assertEqual(store.audio_path(doc, "word.mp3"), store.audio_dir(doc) / "word.mp3")
        (store.doc_dir(doc) / "audio" / "Upper.MP3").write_bytes(b"x")
        for bad in ("../source.md", "..", "", None, "source.md", "sub/word.mp3", "..%2Fsource.md",
                    "word.txt", ".word.mp3", "Upper.MP3", "gone.mp3", "word.mp3/", "/etc/passwd"):
            with self.subTest(name=bad):
                with self.assertRaises(KeyError):
                    store.audio_path(doc, bad)
                with self.assertRaises(KeyError):
                    store.delete_audio(doc, bad)
        with self.assertRaises(KeyError):
            store.audio_path("../library", "word.mp3")
        self.assertTrue((store.doc_dir(doc) / "source.md").is_file(), "nothing else went")

    def test_delete_removes_the_recording_and_only_it(self):
        doc = self.doc()
        store.save_audio(doc, "word.mp3", sound(self, "mp3"))
        store.save_audio(doc, "other.wav", sound(self, "wav"))
        store.delete_audio(doc, "word.mp3")
        self.assertEqual(self.files(doc), ["other.wav"])
        with self.assertRaises(KeyError):
            store.delete_audio(doc, "word.mp3")


# ------------------------------------------------------- carried in and out

class CarryTests(LibraryCase):
    def recorded(self):
        doc = self.doc("\n![a word](audio/word.mp3)\n\n![lesson](audio/lesson.m4a){width=50 start=1.5}\n\n"
                       "![a cat](images/cat.png)\n")
        store.save_audio(doc, "word.mp3", sound(self, "mp3"))
        store.save_audio(doc, "lesson.m4a", sound(self, "m4a"))
        store.save_audio(doc, "unused.wav", sound(self, "wav"))
        store.save_image(doc, "cat.png", PNG)
        return doc

    def test_a_duplicate_has_its_recordings(self):
        doc = self.recorded()
        copy = store.duplicate(doc)["id"]
        self.assertEqual(self.files(copy), ["lesson.m4a", "unused.wav", "word.mp3"])
        self.assertEqual((store.audio_dir(copy) / "word.mp3").read_bytes(), sound(self, "mp3"))
        self.assertEqual(self.files(copy, "images"), ["cat.png"])

    def test_the_download_holds_the_recordings_it_names_and_no_other(self):
        doc = self.recorded()
        z = zipfile.ZipFile(io.BytesIO(store.doc_zip(doc, "cats")))
        self.assertEqual(sorted(z.namelist()),
                         ["audio/lesson.m4a", "audio/word.mp3", "cats.md", "images/cat.png"])
        self.assertEqual(z.read("audio/word.mp3"), sound(self, "mp3"))
        self.assertEqual(z.read("audio/lesson.m4a"), sound(self, "m4a"))

    def test_the_download_comes_back_with_its_recordings(self):
        doc = self.recorded()
        # into a library where its name is free again (test_doclinks.py)
        data, text = store.doc_zip(doc, "cats"), store.get(doc)[1]
        store.delete(doc)
        out = store.import_zip(data)
        self.assertEqual((len(out["docs"]), out["warnings"]), (1, []))
        new = out["docs"][0]["id"]
        self.assertEqual(store.get(new)[1], text)
        self.assertEqual(self.files(new), ["lesson.m4a", "word.mp3"])
        self.assertEqual((store.audio_dir(new) / "lesson.m4a").read_bytes(), sound(self, "m4a"))

    def test_recordings_are_found_beside_their_markdown_and_renamed_as_stored(self):
        md = (FULL + "\n![big](audio/Word.MP3)\n\n![wav](audio/lesson.mp3)\n\n"
              ":::exercise flashcard\ncard-type: vocab\ntarget: x\nmeaning: y\n"
              "front-audio: audio/Word.MP3\nback-audio: audio/word.mp3\n:::\n\n"
              "![fake](audio/fake.mp3)\n\n![gone](audio/gone.ogg)\n\n![](images/Cat.PNG)\n\n"
              "![other cat](images/cat.png)\n")
        mp3, wav = sound(self, "mp3"), sound(self, "wav")
        out = store.import_zip(zip_of({"notes/cats.md": md,
                                       "notes/audio/Word.MP3": mp3,
                                       "notes/lesson.mp3": wav,
                                       "notes/audio/fake.mp3": PNG,
                                       "notes/images/Cat.PNG": PNG,
                                       "notes/images/cat.png": PNG + b" but another picture"}))
        doc = out["docs"][0]["id"]
        text = store.get(doc)[1]
        self.assertIn("![big](audio/word.mp3)", text)
        self.assertIn("![wav](audio/lesson.wav)", text, "a WAV called .mp3 is kept, and named, as .wav")
        self.assertIn("front-audio: audio/word.mp3\nback-audio: audio/word.mp3", text)
        self.assertNotIn("Word.MP3", text)
        self.assertEqual(self.files(doc), ["lesson.wav", "word.mp3"])
        self.assertEqual((store.audio_dir(doc) / "lesson.wav").read_bytes(), wav)
        # two pictures whose names differ in case: one pass, so the first's
        # new name is not taken for the second's old one
        self.assertIn("![](images/cat.png)", text)
        self.assertIn("![other cat](images/cat-2.png)", text)
        self.assertEqual(sorted(out["warnings"]), [
            "notes/cats.md: audio/fake.mp3 was not kept (%s)" % HUMAN_REFUSAL,
            "notes/cats.md: audio/gone.ogg is not in the zip"])

    def test_a_backup_puts_the_recordings_back(self):
        doc = self.recorded()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for f in sorted(self.lib.rglob("*")):
                if f.is_file():
                    zf.write(f, str(f.relative_to(self.lib)))
            folder = store.doc_dir(doc).relative_to(self.lib)
            zf.writestr("%s/audio/Bad.MP3" % folder, b"x")
            zf.writestr("%s/audio/sub/deep.mp3" % folder, b"x")
        with tempfile.TemporaryDirectory() as td:
            was = store.use_library(Path(td))
            try:
                out = store.import_library(buf.getvalue())
                back = sorted(p.name for p in store.audio_dir(doc).iterdir())
                data = (store.audio_dir(doc) / "word.mp3").read_bytes()
            finally:
                store.use_library(was)
        self.assertEqual(out["restored"], [doc])
        self.assertEqual(back, ["lesson.m4a", "unused.wav", "word.mp3"])
        self.assertEqual(data, sound(self, "mp3"))
        self.assertEqual(sorted(out["warnings"]), [
            "%s: audio/Bad.MP3 is no part of a document" % doc,
            "%s: audio/sub/deep.mp3 is no part of a document" % doc])


# ----------------------------------------------------------------- the tray

class AdoptTests(LibraryCase):
    def test_the_tray_is_at_the_toolbox_root_unless_told_otherwise(self):
        self.assertEqual(store.CLIPS_DIR, self.tray)
        with mock.patch.object(store, "CLIPS_DIR", store.CLIPS_DIR):
            store.set_clips_dir(str(self.tray / "elsewhere"))
            self.assertEqual(store.CLIPS_DIR, self.tray / "elsewhere")
        import importlib.util
        spec = importlib.util.spec_from_file_location("store_fresh", ROOT / "markdown" / "app" / "store.py")
        fresh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fresh)
        self.assertEqual(fresh.CLIPS_DIR, ROOT / "clips")

    def test_what_the_document_lacks_is_copied_in_and_the_rest_named_missing(self):
        mp3, png = sound(self, "mp3"), PNG
        (self.tray / "hello-a1b2c3.mp3").write_bytes(mp3)
        (self.tray / "hello-a1b2c3.mp3.json").write_text("{}")
        (self.tray / "frame-d4e5f6.png").write_bytes(png)
        (self.tray / "bogus-000000.mp3").write_bytes(b"text that only calls itself a recording")
        (self.tray / "Upper.MP3").write_bytes(mp3)
        doc = self.doc("\n![](audio/hello-a1b2c3.mp3)\n\n:::exercise flashcard\ncard-type: vocab\n"
                       "target: x\nmeaning: y\nfront-image: images/frame-d4e5f6.png\n"
                       "back-audio: audio/hello-a1b2c3.mp3\n:::\n\n![](audio/absent.ogg)\n\n"
                       "![](audio/bogus-000000.mp3)\n\n![](audio/Upper.MP3)\n\n![](images/cat.png)\n")
        store.save_image(doc, "cat.png", PNG)
        out = store.adopt_media(doc)
        self.assertEqual(out, {"adopted": ["audio/hello-a1b2c3.mp3", "images/frame-d4e5f6.png"],
                               "missing": ["audio/absent.ogg", "audio/bogus-000000.mp3",
                                           "audio/Upper.MP3"]})
        self.assertEqual((store.audio_dir(doc) / "hello-a1b2c3.mp3").read_bytes(), mp3)
        self.assertEqual((store.images_dir(doc) / "frame-d4e5f6.png").read_bytes(), png)
        self.assertEqual(self.files(doc), ["hello-a1b2c3.mp3"], "no temporary file is left")
        self.assertTrue((self.tray / "hello-a1b2c3.mp3").is_file(), "the tray keeps its clip")
        again = store.adopt_media(doc)
        self.assertEqual(again["adopted"], [], "what is here is not copied again")
        self.assertEqual(again["missing"], out["missing"])

    def test_a_document_and_a_deck_name_the_same_files(self):
        # one finder (mdparser.media_refs): a web address or myimages/ in the
        # prose names no file of the tray, and a sentence's full stop is not
        # part of the name it ends
        mp3, png = sound(self, "mp3"), PNG
        (self.tray / "cat-a1b2c3.png").write_bytes(png)
        (self.tray / "dog-d4e5f6.png").write_bytes(png)
        (self.tray / "word-a1b2c3.mp3").write_bytes(mp3)
        (self.tray / "hum-b2c3d4.mp3").write_bytes(mp3)
        text = ("See https://example.org/images/cat-a1b2c3.png for the original, "
                "or myimages/dog-d4e5f6.png, or myaudio/hum-b2c3d4.mp3.\n\n"
                "Listen to audio/word-a1b2c3.mp3.\n")
        doc = self.doc("\n" + text)
        import decks
        for kind in ("images", "audio"):
            self.assertEqual(store._named(text, kind),
                             [n for k, n in decks._media_names([text]) if k == kind], kind)
        self.assertEqual(store.adopt_media(doc), {"adopted": ["audio/word-a1b2c3.mp3"], "missing": []})
        self.assertEqual(self.files(doc, "images"), [], "no picture came in for a web address")
        self.assertEqual(self.files(doc), ["word-a1b2c3.mp3"])
        # what the document lists as used, and so zips, is what it names
        store.save_image(doc, "cat-a1b2c3.png", png)
        self.assertEqual([(i["name"], i["referenced"]) for i in store.list_images(doc)],
                         [("cat-a1b2c3.png", False)])
        self.assertEqual([(r["name"], r["referenced"]) for r in store.list_audio(doc)],
                         [("word-a1b2c3.mp3", True)])
        z = zipfile.ZipFile(io.BytesIO(store.doc_zip(doc, "prose")))
        self.assertEqual(sorted(z.namelist()), ["audio/word-a1b2c3.mp3", "prose.md"])
        # and a name at the end of a sentence is renamed where it stands
        # (under a name of its own: "Cats" is the document's above)
        out = store.import_zip(zip_of({"p.md": FULL.replace("title: Cats", "title: Prose")
                                              + "\nListen to audio/Word.MP3.\n\n"
                                              "And look at images/Cat.PNG.\n",
                                       "audio/Word.MP3": mp3, "images/Cat.PNG": png}))
        self.assertEqual(out["warnings"], [])
        body = store.get(out["docs"][0]["id"])[1]
        self.assertIn("Listen to audio/word.mp3.\n", body)
        self.assertIn("And look at images/cat.png.\n", body)

    def test_a_markdown_given_is_read_instead_of_the_saved_one(self):
        (self.tray / "pasted-abcdef.ogg").write_bytes(sound(self, "ogg"))
        doc = self.doc()
        out = store.adopt_media(doc, "a pasted card\nfront-audio: audio/pasted-abcdef.ogg\n")
        self.assertEqual(out, {"adopted": ["audio/pasted-abcdef.ogg"], "missing": []})
        self.assertEqual(store.adopt_media(doc), {"adopted": [], "missing": []}, "the source names none")
        with self.assertRaises(KeyError):
            store.adopt_media("no-such-doc", "")

    def test_create_and_save_bring_clips_in(self):
        mp3 = sound(self, "mp3")
        (self.tray / "one-111111.mp3").write_bytes(mp3)
        (self.tray / "two-222222.wav").write_bytes(sound(self, "wav"))
        h = Fake({"markdown": FULL + "\n![](audio/one-111111.mp3)\n"})
        server.api_create(h)
        self.assertEqual(h.sent[0], 201)
        doc = h.sent[1]["meta"]["id"]
        self.assertEqual((store.audio_dir(doc) / "one-111111.mp3").read_bytes(), mp3)
        h = Fake({"markdown": FULL + "\n![](audio/one-111111.mp3)\n\n![](audio/two-222222.wav)\n"})
        server.api_save(h, doc)
        self.assertEqual(h.sent[0], 200)
        self.assertEqual(self.files(doc), ["one-111111.mp3", "two-222222.wav"])

    def test_a_tray_that_fails_never_fails_the_save(self):
        doc = self.doc()
        text = FULL + "\n![](audio/one-111111.mp3)\n"
        with mock.patch.object(store, "adopt_media", side_effect=OSError("the tray is unreadable")), \
                mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            h = Fake({"markdown": text})
            server.api_save(h, doc)
            # a new document needs a name of its own: "Cats" is `doc`'s
            made = Fake({"markdown": text.replace("title: Cats", "title: More cats")})
            server.api_create(made)
        self.assertEqual((h.sent[0], store.get(doc)[1]), (200, text))
        self.assertEqual(made.sent[0], 201)
        self.assertIn("the tray is unreadable", err.getvalue())


# ------------------------------------------------------------------ layout

NUMBERED = """---
title: Numbers
target: fa
---

![first picture](images/a.png)

:::exercise flashcard
card-type: jolly
front-primary: |
  ![inside picture](images/in.png)

  ![inside recording](audio/in.mp3)
front-secondary: x
back-primary: y
back-secondary: z
:::

![a recording](audio/rec.mp3){width=50 align=center offset=0 start=1.5 end=3}

> a box
>
> ![boxed picture](images/b.png)
>
> :::exercise flashcard
> card-type: jolly
> front-primary: |
>   ![boxed inside](images/bin.png)
> front-secondary: x
> back-primary: y
> back-secondary: z
> :::
>
> ![after the boxed card](images/c.png)

@[a video](https://www.youtube.com/watch?v=dQw4w9WgXcQ){start=10 end=20}

> > ![nested](images/n.png)

![last picture](images/z.png)
"""


def changed_line(before, after):
    lines = [(a, b) for a, b in zip(before.split("\n"), after.split("\n")) if a != b]
    assert len(lines) == 1, lines
    return lines[0][1]


class LayoutTests(unittest.TestCase):
    def test_a_recording_takes_its_clip_to_the_hundredth(self):
        src = "text\n\n![a word](audio/word.mp3)\n"
        out = store.image_layout_markdown(src, 0, 60, "center", 0, start=65.5, end=69.254)
        self.assertEqual(changed_line(src, out),
                         "![a word](audio/word.mp3){width=60 align=center offset=0 start=65.5 end=69.25}")
        out = store.image_layout_markdown(src, 0, 60, "left", 0, start=2, end=1.5)
        self.assertEqual(changed_line(src, out),
                         "![a word](audio/word.mp3){width=60 align=left offset=0 start=2}",
                         "an end before the start is dropped")
        out = store.image_layout_markdown(src, 0, 40, "right", 10)
        self.assertEqual(changed_line(src, out), "![a word](audio/word.mp3){width=40 align=right offset=10}")
        # no start is a start at 0: an end at or before it is dropped, as it
        # is after a start that is given -- `#t=0,0` would never play
        for start, end, attrs in ((None, 0, ""), (None, 0.004, ""), (None, -3, ""), (0, 0, " start=0"),
                                  (None, 0.3, " end=0.3"), (0.5, 0.504, " start=0.5")):
            with self.subTest(start=start, end=end):
                out = store.image_layout_markdown(src, 0, 50, "left", 0, start=start, end=end)
                self.assertEqual(changed_line(src, out),
                                 "![a word](audio/word.mp3){width=50 align=left offset=0%s}" % attrs)
                html = htmlgen.render_document(out, asset_base="/media/x/")["html"]
                self.assertNotIn('data-end="0"', html)
                self.assertNotRegex(html, r'#t=[\d.]*,0"')
        with self.assertRaises(store.StoreError):
            store.image_layout_markdown(src, 0, 60, "left", 0, start=float("nan"))

    def test_a_video_keeps_whole_seconds_and_a_picture_takes_no_clip(self):
        src = "@[v](https://youtu.be/dQw4w9WgXcQ)\n\n![p](images/p.png)\n"
        out = store.image_layout_markdown(src, 0, 70, "center", 0, start=116.7, end=140.2)
        self.assertEqual(changed_line(src, out),
                         "@[v](https://youtu.be/dQw4w9WgXcQ){width=70 align=center offset=0 start=116 end=140}")
        for end in (0, 0.7, -3):
            with self.subTest(end=end):
                out = store.image_layout_markdown(src, 0, 70, "center", 0, end=end)
                self.assertEqual(changed_line(src, out),
                                 "@[v](https://youtu.be/dQw4w9WgXcQ){width=70 align=center offset=0}",
                                 "no start and an end under a second: no end")
        out = store.image_layout_markdown(src, 1, 70, "center", 0, start=1.5, end=3)
        self.assertEqual(changed_line(src, out), "![p](images/p.png){width=70 align=center offset=0}")

    def test_what_is_inside_an_exercise_is_not_counted(self):
        want = ["first picture", "a recording", "boxed picture", "after the boxed card",
                "a video", "nested", "last picture"]
        for index, caption in enumerate(want):
            with self.subTest(index=index):
                line = changed_line(NUMBERED, store.image_layout_markdown(NUMBERED, index, 33, "right", 0))
                self.assertIn("[%s]" % caption, line)
        self.assertEqual(changed_line(NUMBERED, store.image_layout_markdown(NUMBERED, 5, 33, "right", 0)),
                         "> > ![nested](images/n.png){width=33 align=right offset=0}",
                         "the quote marks are kept")
        with self.assertRaises(store.StoreError):
            store.image_layout_markdown(NUMBERED, len(want), 33, "right", 0)

    def test_an_exercise_left_open_ends_with_its_box_or_with_the_document(self):
        src = ("> :::exercise flashcard\n> card-type: jolly\n> front-primary: |\n"
               ">   ![in the open card](images/u.png)\n\n![after the box](images/after.png)\n\n"
               ":::exercise flashcard\nfront-primary: |\n  ![never closed](images/x.png)\n\n"
               "![still inside](images/y.png)\n")
        line = changed_line(src, store.image_layout_markdown(src, 0, 50, "left", 0))
        self.assertEqual(line, "![after the box](images/after.png){width=50 align=left offset=0}")
        with self.assertRaises(store.StoreError):
            store.image_layout_markdown(src, 1, 50, "left", 0)
        self.assertEqual(self.numbered(src), {0: "after the box"})

    def numbered(self, markdown):
        """data-idx -> caption, as the renderer numbers the figures"""
        html = htmlgen.render_document(markdown, asset_base="/media/x/")["html"]
        found = {}
        for fig in re.findall(r"<figure\b[^>]*>.*?</figure>", html, re.S):
            idx = re.search(r'data-idx="(\d+)"', fig)
            cap = re.search(r"<figcaption>(.*?)</figcaption>", fig, re.S)
            if idx:
                found[int(idx.group(1))] = re.sub(r"<[^>]+>", "", cap.group(1)) if cap else ""
        return found

    def test_the_index_is_the_one_the_renderer_gives(self):
        """whichever figures htmlgen numbers, store rewrites the same line
        for the same number -- recordings too, once they are figures"""
        found = self.numbered(NUMBERED)
        self.assertEqual(sorted(found), list(range(len(found))))
        self.assertEqual(set(found.values()), {"first picture", "a recording", "boxed picture",
                                               "after the boxed card", "a video", "nested",
                                               "last picture"})
        self.assertFalse({"inside picture", "inside recording", "boxed inside"} & set(found.values()),
                         "a card's pictures are not numbered")
        for idx, caption in found.items():
            with self.subTest(idx=idx, caption=caption):
                line = changed_line(NUMBERED, store.image_layout_markdown(NUMBERED, idx, 33, "right", 0))
                self.assertIn("[%s]" % caption, line)

    def test_the_layout_routes_take_decimals(self):
        h = Fake({"markdown": "![w](audio/w.mp3)", "index": 0, "width": 60, "align": "center",
                  "offset": 0, "start": "1.25", "end": 2.5})
        server.api_image_layout_pure(h)
        self.assertEqual(h.sent, (200, {"markdown":
                                        "![w](audio/w.mp3){width=60 align=center offset=0 start=1.25 end=2.5}"}))
        h = Fake({"markdown": "![w](audio/w.mp3)", "index": 0, "start": "1:05"})
        server.api_image_layout_pure(h)
        self.assertEqual(h.sent[0], 400)


# ------------------------------------------------------------ routes, faked

class FakeRouteTests(LibraryCase):
    def route(self, method, path):
        for m, pattern, fn in server.ROUTES:
            match = re.match(pattern, path) if m == method else None
            if match:
                return fn, match.groups()
        return None, ()

    def test_the_five_routes(self):
        self.assertEqual(self.route("GET", "/media/cats-abc123/audio/word.mp3"),
                         (server.serve_audio, ("cats-abc123", "word.mp3")))
        self.assertEqual(self.route("GET", "/api/docs/cats-abc123/audio"),
                         (server.api_audio_list, ("cats-abc123",)))
        self.assertEqual(self.route("POST", "/api/docs/cats-abc123/audio"),
                         (server.api_audio_upload, ("cats-abc123",)))
        self.assertEqual(self.route("DELETE", "/api/docs/cats-abc123/audio/word.mp3"),
                         (server.api_audio_delete, ("cats-abc123", "word.mp3")))
        self.assertEqual(self.route("POST", "/api/docs/cats-abc123/adopt"),
                         (server.api_adopt, ("cats-abc123",)))
        for path in ("/media/cats-abc123/audio/../source.md", "/media/cats-abc123/audio/..%2Fsource.md",
                     "/media/cats-abc123/audio/"):
            self.assertIsNone(self.route("GET", path)[0], path)

    def test_upload_list_serve_delete_and_adopt(self):
        doc = self.doc("\n![](audio/word.mp3)\n\n![](audio/clip-abcdef.mp3)\n")
        mp3 = sound(self, "mp3")
        h = Fake(query="name=Word.mp3", raw=mp3)
        server.api_audio_upload(h, doc)
        self.assertEqual(h.sent, (201, {"name": "word.mp3", "path": "audio/word.mp3",
                                        "url": "/media/%s/audio/word.mp3" % doc}))
        h = Fake()
        server.api_audio_list(h, doc)
        self.assertEqual(h.sent, (200, {"audio": [{"name": "word.mp3", "size": len(mp3), "referenced": True}]}))
        h = Fake()
        server.serve_audio(h, doc, "word.mp3")
        self.assertEqual(h.sent, ("file", store.audio_dir(doc) / "word.mp3", None))
        (self.tray / "clip-abcdef.mp3").write_bytes(mp3)
        h = Fake({})
        server.api_adopt(h, doc)
        self.assertEqual(h.sent, (200, {"adopted": ["audio/clip-abcdef.mp3"], "missing": []}))
        h = Fake({"markdown": "![](audio/else-123456.ogg)"})
        server.api_adopt(h, doc)
        self.assertEqual(h.sent, (200, {"adopted": [], "missing": ["audio/else-123456.ogg"]}))
        h = Fake({"markdown": ["not", "text"]})
        server.api_adopt(h, doc)
        self.assertEqual(h.sent[0], 400)
        h = Fake()
        server.api_audio_delete(h, doc, "word.mp3")
        self.assertEqual((h.sent, self.files(doc)), ((200, {"ok": True}), ["clip-abcdef.mp3"]))

    def test_refusals_raise_what_the_dispatcher_answers_404_and_400_for(self):
        doc = self.doc()
        with self.assertRaises(store.StoreError):          # 400
            server.api_audio_upload(Fake(query="name=x.mp3", raw=PNG), doc)
        for call in (lambda: server.api_audio_upload(Fake(raw=sound(self, "mp3")), "no-such-doc"),
                     lambda: server.serve_audio(Fake(), doc, "gone.mp3"),
                     lambda: server.serve_audio(Fake(), doc, "..source.md"),
                     lambda: server.api_audio_list(Fake(), "no-such-doc"),
                     lambda: server.api_audio_delete(Fake(), doc, "gone.mp3"),
                     lambda: server.api_adopt(Fake({}), "no-such-doc")):
            with self.assertRaises(KeyError):              # 404
                call()
        self.assertEqual(self.files(doc), [])

    def test_the_layout_panel_saves_a_clip_the_page_then_plays(self):
        doc = self.doc("\n![a picture](images/p.png)\n\n![a word](audio/word.mp3)\n")
        h = Fake({"index": 1, "width": 50, "align": "center", "offset": 0, "start": 1.5, "end": "3.25"})
        server.api_image_layout(h, doc)
        self.assertEqual(h.sent[0], 200)
        text = store.get(doc)[1]
        self.assertIn("![a word](audio/word.mp3){width=50 align=center offset=0 start=1.5 end=3.25}", text)
        html = htmlgen.render_document(text, asset_base="/media/%s/" % doc)["html"]
        fig = re.search(r'<figure class="img audio[^"]*"[^>]*>', html)
        self.assertIsNotNone(fig, "the renderer draws the recording")
        self.assertIn('data-idx="1"', fig.group(0))
        self.assertIn('data-start="1.5"', fig.group(0))
        self.assertIn('data-end="3.25"', fig.group(0))

    def test_a_note_upload_answers_its_own_mount(self):
        doc = self.doc()
        was = server.use_mount("/books/english/mini-en/notes", html_only=True)
        try:
            h = Fake(query="name=w.ogg", raw=sound(self, "ogg"))
            server.api_audio_upload(h, doc)
        finally:
            server.restore_mount(was)
        self.assertEqual(h.sent[1]["url"], "/books/english/mini-en/notes/media/%s/audio/w.ogg" % doc)


LONG = "9" * 4301           # more digits than int() reads by default
# headers the studio and the hub must answer alike, the odd ones included
RANGE_HEADERS = (
    "bytes=0-99", "bytes=0-", "bytes=500-", "bytes=-10", "bytes=-5000", "bytes=900-5000",
    "bytes=999-999", "bytes=1000-", "bytes=500000-", "bytes=-0", "bytes=20-10",
    "bytes=0-1,5-6", "bytes=0-5x", "bytes=-", "bytes=", "bytes=a-b", "bytes= 0-5", "Bytes=0-5",
    "items=0-9", "abc", "bytes=%s-" % LONG, "bytes=-%s" % LONG, "bytes=0-%s" % LONG,
    "bytes=%s1-" % ("0" * 4300), "bytes=%s-" % ("9" * 40), "bytes=-%s" % ("9" * 40))


def range_answer(fn, header, size):
    """What a byte_range makes of a header, as the handler answers it:
    ["206", first, last], ["416"] or ["400"]."""
    try:
        got = fn(header, size)
    except ValueError:
        return ["400"]
    return ["416"] if got is None else ["206", got[0], got[1]]


class ByteRangeTests(unittest.TestCase):
    def test_what_a_range_header_asks_for(self):
        for header, size, want in (
                ("bytes=0-99", 1000, (0, 99)), ("bytes=0-", 1000, (0, 999)),
                ("bytes=500-", 1000, (500, 999)), ("bytes=-10", 1000, (990, 999)),
                ("bytes=-5000", 1000, (0, 999)), ("bytes=900-5000", 1000, (900, 999)),
                ("bytes=999-999", 1000, (999, 999)), ("bytes=0-1,5-6", 1000, (0, 1)),
                ("bytes=-%s" % ("9" * 40), 1000, (0, 999)),
                ("bytes=1000-", 1000, None), ("bytes=500000-", 1000, None),
                ("bytes=-0", 1000, None), ("bytes=20-10", 1000, None), ("bytes=0-", 0, None),
                ("bytes=-", 1000, None), ("bytes=%s-" % ("9" * 40), 1000, None)):
            with self.subTest(header=header, size=size):
                self.assertEqual(server.byte_range(header, size), want)
        for header in (None, "items=0-9", "abc", "bytes=", "bytes=a-b", "bytes= 0-5",
                       "bytes=%s-" % LONG, "bytes=-%s" % LONG, "bytes=0-%s" % LONG):
            with self.subTest(header=header[:20] if header else header):
                with self.assertRaises(ValueError):
                    server.byte_range(header, 1000)

    def test_the_hub_answers_every_header_alike(self):
        """serve.py's byte_range, read in a process of its own (loading the
        hub sets the studio's base for the whole process)"""
        cases = [[h, n] for h in RANGE_HEADERS for n in (1000, 1, 0)]
        script = ("import json, sys\nsys.path.insert(0, %r)\n"
                  "try:\n    import serve\nexcept ImportError as e:\n"
                  "    print(json.dumps({'skip': str(e)})); sys.exit(0)\n"
                  "def answer(h, n):\n"
                  "    try:\n        got = serve.byte_range(h, n)\n"
                  "    except ValueError:\n        return ['400']\n"
                  "    return ['416'] if got is None else ['206', got[0], got[1]]\n"
                  "cases = json.load(sys.stdin)\n"
                  "print(json.dumps({'answers': [answer(h, n) for h, n in cases]}))\n") % str(ROOT)
        r = subprocess.run([sys.executable, "-c", script], cwd=str(ROOT), input=json.dumps(cases),
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        hub = json.loads(r.stdout.strip().splitlines()[-1])
        if "skip" in hub:
            self.skipTest("the hub does not load here: " + hub["skip"])
        self.assertEqual(len(hub["answers"]), len(cases))
        for (header, size), theirs in zip(cases, hub["answers"]):
            with self.subTest(header=header[:24], size=size):
                self.assertEqual(range_answer(server.byte_range, header, size), theirs)


# ------------------------------------------------------ routes, over the wire

class HttpTests(unittest.TestCase):
    """The studio's own handler on 127.0.0.1, on a temporary library."""

    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory(prefix="parseh-audio-http-")
        root = Path(cls.td.name)
        cls.was_lib, cls.was_tray = store.LIB, store.CLIPS_DIR
        store.LIB = root / "library"
        store.LIB.mkdir()
        cls.tray = root / "clips"
        cls.tray.mkdir()
        store.set_clips_dir(cls.tray)
        cls.quiet = mock.patch.object(server.Handler, "log_message", lambda *a: None)
        cls.quiet.start()
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.srv.daemon_threads = True
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.srv.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.quiet.stop()
        store.LIB = cls.was_lib
        store.set_clips_dir(cls.was_tray)
        cls.td.cleanup()

    def setUp(self):
        was = store.use_library(None)       # this thread reads store.LIB too
        self.addCleanup(store.use_library, was)

    def conn(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        self.addCleanup(c.close)
        return c

    def ask(self, method, path, body=None, headers=None, conn=None):
        c = conn or self.conn()
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        return r.status, {k.lower(): v for k, v in r.getheaders()}, r.read()

    def json(self, method, path, obj=None, raw=None):
        body = raw if raw is not None else (None if obj is None else json.dumps(obj).encode())
        status, headers, data = self.ask(method, path, body)
        return status, json.loads(data)

    def made(self, body=""):
        # every test here makes its documents in the one library the server
        # was started on, and a name is one document's: each gets its own
        HttpTests.made_n = getattr(HttpTests, "made_n", 0) + 1
        status, answer = self.json("POST", "/api/docs", {
            "markdown": self.full(HttpTests.made_n) + body})
        self.assertEqual(status, 201)
        return answer["meta"]["id"]

    @staticmethod
    def full(n):
        return FULL.replace("title: Cats", "title: Cats %d" % n)

    def test_upload_list_and_delete(self):
        doc = self.made("\n![a word](audio/word.mp3)\n")
        mp3 = sound(self, "mp3")
        status, answer = self.json("POST", "/api/docs/%s/audio?name=%s" % (doc, urllib.parse.quote("Word.mp3")),
                                   raw=mp3)
        self.assertEqual((status, answer), (201, {"name": "word.mp3", "path": "audio/word.mp3",
                                                  "url": "/media/%s/audio/word.mp3" % doc}))
        self.assertEqual(self.json("GET", "/api/docs/%s/audio" % doc),
                         (200, {"audio": [{"name": "word.mp3", "size": len(mp3), "referenced": True}]}))
        status, headers, data = self.ask("GET", answer["url"])
        self.assertEqual((status, data), (200, mp3))
        self.assertEqual(self.json("DELETE", "/api/docs/%s/audio/word.mp3" % doc), (200, {"ok": True}))
        self.assertEqual(self.ask("GET", answer["url"])[0], 404)
        self.assertEqual(self.json("GET", "/api/docs/%s/audio" % doc), (200, {"audio": []}))

    def test_refusals_over_the_wire(self):
        doc = self.made()
        status, answer = self.json("POST", "/api/docs/%s/audio?name=x.mp3" % doc, raw=PNG)
        self.assertEqual((status, answer), (400, {"error": HUMAN_REFUSAL}))
        status, answer = self.json("POST", "/api/docs/%s/audio?name=x.mp3" % doc, raw=b"")
        self.assertEqual((status, answer), (400, {"error": "empty upload"}))
        self.assertEqual(self.json("POST", "/api/docs/no-such-doc/audio?name=x.mp3", raw=sound(self, "mp3"))[0], 404)
        self.assertEqual(self.json("DELETE", "/api/docs/%s/audio/gone.mp3" % doc)[0], 404)
        for path in ("/media/%s/audio/../source.md" % doc, "/media/%s/audio/..%%2Fsource.md" % doc,
                     "/media/%s/audio/.hidden.mp3" % doc, "/media/%s/audio/source.md" % doc,
                     "/media/no-such-doc/audio/word.mp3"):
            with self.subTest(path=path):
                status, headers, data = self.ask("GET", path)
                self.assertEqual(status, 404)
                self.assertNotIn(b"title: Cats", data)
        self.assertFalse(store.audio_dir(doc).exists(), "nothing was written")

    def test_a_recording_is_served_whole_or_a_range_at_a_time(self):
        doc = self.made()
        mp3 = sound(self, "mp3")
        self.assertLess(len(mp3), 500000)
        self.assertEqual(self.json("POST", "/api/docs/%s/audio?name=tone.mp3" % doc, raw=mp3)[0], 201)
        url, size = "/media/%s/audio/tone.mp3" % doc, len(mp3)
        c = self.conn()                     # one connection throughout: every length must be true
        status, h, data = self.ask("GET", url, conn=c)
        self.assertEqual((status, h["content-type"], h["accept-ranges"], int(h["content-length"]), data),
                         (200, "audio/mpeg", "bytes", size, mp3))
        self.assertNotIn("content-range", h)
        status, h, data = self.ask("GET", url, headers={"Range": "bytes=0-99"}, conn=c)
        self.assertEqual((status, h["content-range"], h["content-length"], data),
                         (206, "bytes 0-99/%d" % size, "100", mp3[:100]))
        status, h, data = self.ask("GET", url, headers={"Range": "bytes=-10"}, conn=c)
        self.assertEqual((status, h["content-range"], data),
                         (206, "bytes %d-%d/%d" % (size - 10, size - 1, size), mp3[-10:]))
        status, h, data = self.ask("GET", url, headers={"Range": "bytes=1000-"}, conn=c)
        self.assertEqual((status, h["content-range"], data),
                         (206, "bytes 1000-%d/%d" % (size - 1, size), mp3[1000:]))
        status, h, data = self.ask("GET", url, headers={"Range": "bytes=500000-"}, conn=c)
        self.assertEqual((status, h["content-range"], h["content-length"], data),
                         (416, "bytes */%d" % size, "0", b""))
        status, h, data = self.ask("GET", url, headers={"Range": "bytes=0-1,4-5"}, conn=c)
        self.assertEqual((status, h["content-range"], data), (206, "bytes 0-1/%d" % size, mp3[:2]),
                         "several ranges: the first, as the hub answers")
        # a header that is no byte range is ignored, as the hub ignores it
        # (RFC 9110 14.2): the whole file, never a 400 and never a traceback
        for bad in ("bytes=abc", "items=0-5", "bytes=%s-" % LONG, "bytes=-%s" % LONG, "bytes=0-%s" % LONG):
            with self.subTest(bad=bad[:20]):
                status, h, data = self.ask("GET", url, headers={"Range": bad}, conn=c)
                self.assertEqual((status, int(h["content-length"]), data), (200, size, mp3))
                self.assertNotIn("content-range", h)
        status, h, data = self.ask("HEAD", url, headers={"Range": "bytes=10-19"}, conn=c)
        self.assertEqual((status, h["content-range"], h["content-length"], data),
                         (206, "bytes 10-19/%d" % size, "10", b""))
        status, h, data = self.ask("GET", url, headers={"Range": "bytes=%d-" % (size - 1)}, conn=c)
        self.assertEqual((status, data), (206, mp3[-1:]), "and the connection still answers true")

    def test_a_download_is_whole_whatever_is_asked(self):
        doc = self.made("\n![](audio/tone.mp3)\n")
        self.assertEqual(self.json("POST", "/api/docs/%s/audio?name=tone.mp3" % doc, raw=sound(self, "mp3"))[0], 201)
        status, h, data = self.ask("GET", "/download/%s/zip" % doc, headers={"Range": "bytes=0-9"})
        self.assertEqual((status, h["content-type"]), (200, "application/zip"))
        self.assertIn("audio/tone.mp3", zipfile.ZipFile(io.BytesIO(data)).namelist())
        # the zip is written in memory (send_bytes); the markdown is a file on
        # disk, answered by send_file with a download name: that is the branch
        # that must not honour a Range
        source = (store.doc_dir(doc) / "source.md").read_bytes()
        self.assertGreater(len(source), 10)
        c = self.conn()
        for asked in ("bytes=0-9", "bytes=-5", "bytes=999999-", "bytes=abc"):
            with self.subTest(asked=asked):
                status, h, data = self.ask("GET", "/download/%s/md" % doc, headers={"Range": asked}, conn=c)
                self.assertEqual((status, data, h["content-length"]), (200, source, str(len(source))))
                self.assertNotIn("content-range", h)
                self.assertTrue(h["content-disposition"].startswith("attachment; "), h["content-disposition"])

    def test_every_format_has_its_type(self):
        doc = self.made()
        for ext in CODECS:
            with self.subTest(ext=ext):
                data = sound(self, ext)
                status, answer = self.json("POST", "/api/docs/%s/audio?name=tone.%s" % (doc, ext), raw=data)
                self.assertEqual((status, answer["name"]), (201, "tone." + ext))
                status, h, got = self.ask("GET", answer["url"], headers={"Range": "bytes=0-"})
                self.assertEqual((status, h["content-type"], got), (206, audiofile.MIME[ext], data))

    def test_a_save_and_the_adopt_route_bring_clips_in(self):
        mp3, ogg = sound(self, "mp3"), sound(self, "ogg")
        (self.tray / "saved-aaaaaa.mp3").write_bytes(mp3)
        (self.tray / "pasted-bbbbbb.ogg").write_bytes(ogg)
        doc = self.made()
        status, answer = self.json("PUT", "/api/docs/%s" % doc,
                                   {"markdown": self.full(HttpTests.made_n)
                                    + "\n![](audio/saved-aaaaaa.mp3)\n"})
        self.assertEqual(status, 200)
        self.assertEqual(self.ask("GET", "/media/%s/audio/saved-aaaaaa.mp3" % doc)[2], mp3)
        status, answer = self.json("POST", "/api/docs/%s/adopt" % doc,
                                   {"markdown": "front-audio: audio/pasted-bbbbbb.ogg\n![](images/gone.png)"})
        self.assertEqual((status, answer), (200, {"adopted": ["audio/pasted-bbbbbb.ogg"],
                                                  "missing": ["images/gone.png"]}))
        status, h, got = self.ask("GET", "/media/%s/audio/pasted-bbbbbb.ogg" % doc)
        self.assertEqual((status, h["content-type"], got), (200, "audio/ogg", ogg))
        self.assertEqual(self.json("POST", "/api/docs/no-such-doc/adopt", {})[0], 404)


if __name__ == "__main__":
    unittest.main()
