"""What a recording is, by its bytes, and what ffmpeg does with one
(lib/audiofile.py).

    python3 -m unittest discover -s tests -p test_audiofile.py

Every door that takes audio in -- a studio document's audio/, a deck's, the
clip tray -- asks this module, so what it says is what the whole toolbox
accepts.  The files are REAL, made by ffmpeg in a temporary directory: a
recording is recognised by its first bytes, and invented bytes would only
test the invention.  Without ffmpeg on the machine those tests skip and the
refusals, the names and the stdlib WAV path still run.
"""
import contextlib
import os
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "lib", ROOT / "markdown" / "exlex"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import audiofile  # noqa: E402

HAVE = audiofile.have_ffmpeg()
needs_ffmpeg = unittest.skipUnless(HAVE, "ffmpeg is not installed on this machine")


def ff(*args):
    """Run ffmpeg quietly; the raw failure is the test's message."""
    r = subprocess.run([audiofile.ffmpeg(), "-y", "-loglevel", "error"] + list(args),
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError("ffmpeg %s -> exit %d: %s" % (" ".join(args), r.returncode, r.stderr))


def sine(out, secs=2, freq=440, *codec):
    ff("-f", "lavfi", "-i", "sine=frequency=%d:duration=%s" % (freq, secs), *codec, out)
    return out


def stdlib_wav(path, secs=1.0, rate=8000):
    with contextlib.closing(wave.open(str(path), "wb")) as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x10\x00" * int(rate * secs))
    return path


def read(p):
    with open(p, "rb") as f:
        return f.read()


def markers(out, *codec, rate=44100, secs=8):
    """Silence with two short tones in it, 0.6-0.7 s and 5.0-5.1 s: where the
    sound sits inside a cut says whether the cut is true."""
    expr = "if(between(t,0.6,0.7)+between(t,5.0,5.1),0.3*sin(2*PI*440*t),0)"
    ff("-f", "lavfi", "-i", "aevalsrc=exprs='%s':s=%d:d=%s" % (expr, rate, secs),
       "-ac", "1", *codec, out)
    return out


def loud(p, threshold=1000, rate=44100):
    """(the first, the last) second a decoded file is louder than
    `threshold`, and its length: (None, None, length) when it never is."""
    import array
    r = subprocess.run([audiofile.ffmpeg(), "-v", "error", "-i", str(p), "-ac", "1",
                        "-ar", str(rate), "-f", "s16le", "-"], capture_output=True)
    if r.returncode != 0:
        raise AssertionError("decoding %s -> exit %d: %s" % (p, r.returncode, r.stderr[-500:]))
    samples = array.array("h")
    samples.frombytes(r.stdout[:len(r.stdout) // 2 * 2])
    if sys.byteorder == "big":
        samples.byteswap()
    hot = [i for i, v in enumerate(samples) if abs(v) > threshold]
    length = len(samples) / rate
    return (hot[0] / rate, hot[-1] / rate, length) if hot else (None, None, length)


class Temp(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.dir = td.name

    def at(self, name):
        return os.path.join(self.dir, name)


@needs_ffmpeg
class KindOfRealFiles(Temp):
    """Each format, written by ffmpeg, is what its bytes say it is."""

    def made(self, name, *codec):
        return read(sine(self.at(name), 2, 440, *codec))

    def test_every_format_the_toolbox_takes(self):
        cases = [
            ("a.mp3", ("-c:a", "libmp3lame"), ".mp3"),
            ("a.m4a", ("-c:a", "aac"), ".m4a"),
            ("a.aac", ("-c:a", "aac", "-f", "adts"), ".aac"),
            ("a.ogg", ("-c:a", "libvorbis"), ".ogg"),
            ("a.opus", ("-c:a", "libopus"), ".opus"),
            ("a.webm", ("-c:a", "libopus"), ".webm"),
            ("a.wav", ("-c:a", "pcm_s16le"), ".wav"),
            ("a.flac", ("-c:a", "flac"), ".flac"),
        ]
        for name, codec, want in cases:
            with self.subTest(name=name):
                data = self.made(name, *codec)
                self.assertEqual(audiofile.kind(data, name), want)
                # the extension follows the bytes, not the name it came under
                self.assertEqual(audiofile.kind(data, "renamed.bin"),
                                 {".ogg": ".ogg", ".opus": ".opus"}.get(want, want))
                self.assertEqual(audiofile.kind(data), want)

    def test_an_mp3_with_no_id3_tag_is_known_by_its_frame_sync(self):
        data = self.made("bare.mp3", "-c:a", "libmp3lame", "-id3v2_version", "0",
                         "-write_xing", "0")
        self.assertNotEqual(data[:3], b"ID3", "the fixture really has no tag")
        self.assertEqual(audiofile.kind(data), ".mp3")

    def test_the_ogg_family_keeps_the_spelling_it_came_with(self):
        vorbis = self.made("v.ogg", "-c:a", "libvorbis")
        opus = self.made("o.opus", "-c:a", "libopus")
        self.assertEqual(audiofile.kind(vorbis, "lesson.oga"), ".oga")
        self.assertEqual(audiofile.kind(opus, "lesson.ogg"), ".ogg")
        self.assertEqual(audiofile.kind(opus, "lesson"), ".opus")
        self.assertEqual(audiofile.kind(vorbis, "lesson"), ".ogg")

    def test_a_wav_named_mp3_is_a_wav(self):
        data = self.made("liar.mp3", "-c:a", "pcm_s16le", "-f", "wav")
        self.assertEqual(audiofile.kind(data, "liar.mp3"), ".wav")

    def test_mpeg_2_2_5_layer_ii_and_adts_at_every_rate(self):
        # the frame rules must not refuse a stream ffmpeg writes: each is bare,
        # with no tag in front, so its frames are all that say what it is
        cases = [("a-22050.mp3", ("-ar", "22050", "-b:a", "8k", "-c:a", "libmp3lame"), ".mp3"),
                 ("a-16000.mp3", ("-ar", "16000", "-ac", "2", "-b:a", "160k", "-c:a", "libmp3lame"), ".mp3"),
                 ("a-11025.mp3", ("-ar", "11025", "-b:a", "8k", "-c:a", "libmp3lame"), ".mp3"),
                 ("a-8000.mp3", ("-ar", "8000", "-b:a", "64k", "-c:a", "libmp3lame"), ".mp3"),
                 ("a-32000.mp3", ("-ar", "32000", "-b:a", "320k", "-c:a", "libmp3lame"), ".mp3"),
                 ("a.mp2", ("-ar", "32000", "-ac", "2", "-b:a", "384k", "-c:a", "mp2"), ".mp3")]
        cases += [("a-%s.aac" % r, ("-ar", r, "-c:a", "aac", "-f", "adts"), ".aac")
                  for r in ("96000", "22050", "8000", "7350")]
        for name, codec, want in cases:
            with self.subTest(name=name):
                extra = ("-id3v2_version", "0", "-write_xing", "0") if name.endswith(".mp3") else ()
                data = self.made(name, *(codec + extra))
                self.assertEqual(data[0], 0xFF, "no tag in front")
                self.assertEqual(audiofile.kind(data), want)
                self.assertEqual(audiofile.kind(data[:4096]), want)

    def test_matroska_that_is_not_webm_is_refused(self):
        data = self.made("a.mka", "-c:a", "libvorbis", "-f", "matroska")
        self.assertEqual(data[:4], b"\x1a\x45\xdf\xa3")
        self.assertIsNone(audiofile.kind(data, "a.mka"))


class Refusals(Temp):
    def test_what_is_not_a_recording(self):
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
        pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n"
        jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 32
        for label, data in (("png", png), ("pdf", pdf), ("jpeg", jpeg),
                            ("garbage", b"not audio at all, only words"),
                            ("html", b"<!doctype html><script>alert(1)</script>"),
                            ("short", b"RIFF\x00\x00"), ("empty", b""), ("none", None)):
            with self.subTest(label):
                self.assertIsNone(audiofile.kind(data, "x.mp3"))

    def test_a_jpeg_is_not_mistaken_for_mpeg_audio(self):
        # 0xFF 0xD8: a sync byte, then no MPEG layer bits -- must stay a picture
        self.assertIsNone(audiofile.kind(b"\xff\xd8\xff\xdb" + b"\x00" * 20))


def adts(length, rate_index=4):
    """An ADTS header (MPEG-4 AAC LC, stereo, no CRC) for a frame of `length`."""
    return bytes([0xFF, 0xF1, (1 << 6) | (rate_index << 2), (2 << 6) | (length >> 11) & 3,
                  (length >> 3) & 0xFF, ((length & 7) << 5) | 0x1F, 0xFC])


class NotAStream(unittest.TestCase):
    """A frame header is four bytes any file may begin with: a stream of
    frames is what an MP3 or an AAC with no tag in front is known by."""

    TEXT = "Shall I compare thee to a summer's day? Thou art more lovely.\n" * 40
    # MPEG-1 layer III, 128 kbit/s, 44.1 kHz, no padding: a frame of 417 bytes
    HEADER = b"\xff\xfb\x90\x64"

    def test_a_utf16_text_is_not_mpeg_audio(self):
        # its byte-order mark, FF FE, then "S\0": a well-formed layer I header
        data = b"\xff\xfe" + self.TEXT.encode("utf-16-le")
        self.assertEqual(data[:4], b"\xff\xfeS\x00")
        self.assertIsNone(audiofile.kind(data, "poem.mp3"))
        self.assertIsNone(audiofile.kind(data[:4096], "poem.mp3"), "nor its first 4096 bytes")

    def test_one_header_is_not_a_stream_and_two_are(self):
        frame = self.HEADER + b"\x00" * 413
        self.assertIsNone(audiofile.kind(frame + self.TEXT.encode(), "x.mp3"), "a frame, then text")
        self.assertIsNone(audiofile.kind(self.HEADER + b"\x00" * 100, "x.mp3"), "not even one frame")
        self.assertIsNone(audiofile.kind(frame + b"\xff\xf3\x90\x64" + b"\x00" * 400),
                          "a second header of another stream (MPEG-2)")
        self.assertEqual(audiofile.kind(frame * 2), ".mp3")
        self.assertEqual(audiofile.kind((frame * 20)[:4096]), ".mp3")

    def test_headers_no_mpeg_stream_can_have(self):
        for label, header in (("bitrate 15", b"\xff\xfb\xf0\x64"),
                              ("free bitrate", b"\xff\xfb\x00\x64"),
                              ("sample rate 3", b"\xff\xfb\x9c\x64"),
                              ("version 01", b"\xff\xeb\x90\x64"),
                              ("emphasis 2", b"\xff\xfb\x90\x66")):
            with self.subTest(label):
                # repeated at every length a frame could have: still no stream
                self.assertIsNone(audiofile.kind(header * 1024), label)

    def test_adts_is_known_by_two_frames(self):
        frame = adts(200) + b"\x00" * 193
        self.assertEqual(audiofile.kind(frame * 3, "x.aac"), ".aac")
        self.assertIsNone(audiofile.kind(adts(200) + self.TEXT.encode(), "x.aac"))
        self.assertIsNone(audiofile.kind((adts(200, rate_index=13) + b"\x00" * 193) * 3),
                          "a sample rate index ADTS does not have")
        self.assertIsNone(audiofile.kind((adts(5) + b"\x00") * 600), "a frame shorter than its header")


class Names(Temp):
    def test_clean_stem(self):
        self.assertEqual(audiofile.clean_stem("Hello World!.mp3"), "hello-world")
        self.assertEqual(audiofile.clean_stem("Café crème.m4a"), "cafe-creme")
        self.assertEqual(audiofile.clean_stem("../../etc/passwd"), "passwd")
        self.assertEqual(audiofile.clean_stem("سلام.mp3"), "audio", "no Latin: the fallback")
        self.assertEqual(audiofile.clean_stem("سلام", "clip"), "clip")
        self.assertEqual(audiofile.clean_stem("--._x_.--"), "x", "no dot, dash or underscore at either end")
        self.assertEqual(len(audiofile.clean_stem("a" * 200)), 80)
        self.assertEqual(audiofile.clean_stem("word " * 30, limit=10), "word-word")
        for stem in (audiofile.clean_stem(s) for s in ("A b", "é", "x.y.z", "-")):
            self.assertTrue(audiofile.NAME_RE.match(stem + ".mp3"), stem)

    def test_free_name(self):
        one, two = b"RIFF one", b"RIFF two"
        self.assertEqual(audiofile.free_name(self.dir, "w", ".wav", one), "w.wav")
        Path(self.at("w.wav")).write_bytes(one)
        self.assertEqual(audiofile.free_name(self.dir, "w", ".wav", one), "w.wav",
                         "the same bytes again are the same file")
        self.assertEqual(audiofile.free_name(self.dir, "w", ".wav", two), "w-2.wav")
        Path(self.at("w-2.wav")).write_bytes(two)
        self.assertEqual(audiofile.free_name(self.dir, "w", ".wav", b"three"), "w-3.wav")
        self.assertEqual(audiofile.free_name(self.dir, "w", ".wav", two), "w-2.wav")
        self.assertEqual(audiofile.free_name(self.dir, "w", ".wav"), "w-3.wav",
                         "no bytes to compare: the first free name")

    def test_mime_and_accept(self):
        self.assertEqual(audiofile.mime_for("a.MP3"), "audio/mpeg")
        self.assertEqual(audiofile.mime_for("audio/x.opus"), "audio/ogg")
        self.assertEqual(audiofile.mime_for("x.webm"), "audio/webm")
        self.assertIsNone(audiofile.mime_for("x.png"))
        for e in audiofile.EXTS:
            self.assertIn("." + e, audiofile.ACCEPT.split(","))
            self.assertIn(e, audiofile.MIME)

    def test_name_and_path_patterns(self):
        for ok in ("word.mp3", "a-b_c.2.m4a", "x.webm", "9.flac"):
            self.assertTrue(audiofile.NAME_RE.match(ok), ok)
            self.assertTrue(audiofile.PATH_RE.match("audio/" + ok), ok)
        for bad in ("Word.mp3", "-x.mp3", ".x.mp3", "x.mp4", "x.mp3.png", "a/b.mp3", "x"):
            self.assertFalse(audiofile.NAME_RE.match(bad), bad)
        self.assertTrue(audiofile.PATH_RE.match("audio/Word.MP3"), "a path may keep its case")
        for bad in ("audio/../x.mp3", "images/x.mp3", "audio/x.wma", "audio/sub/x.mp3", "audio/.x.mp3"):
            self.assertFalse(audiofile.PATH_RE.match(bad), bad)

    def test_the_dialect_names_audio_the_way_this_module_does(self):
        import mdparser
        probe = ["audio/%s.%s" % (stem, ext)
                 for stem in ("word", "Word", "a-b_c.2", "9", "-x", ".x", "a/b", "")
                 for ext in audiofile.EXTS + ("MP3", "Opus", "wma", "mp4", "png")]
        probe += ["images/x.mp3", "audio/x.mp3/", "audio/x.mp3 ", " audio/x.mp3", "audio/"]
        for p in probe:
            self.assertEqual(bool(mdparser.AUDIO_PATH_RE.match(p)),
                             bool(audiofile.PATH_RE.match(p)), p)


class WithoutFFmpeg(Temp):
    def test_every_ffmpeg_job_says_it_is_missing(self):
        src = str(stdlib_wav(self.at("a.wav")))
        with mock.patch.object(audiofile, "ffmpeg", lambda: None):
            self.assertFalse(audiofile.have_ffmpeg())
            self.assertEqual(audiofile.encoders(), set())
            self.assertEqual(audiofile.best_output()[0], ".wav")
            for job in (lambda: audiofile.extract(src, 0, 0.5, self.at("o")),
                        lambda: audiofile.transcode(src, self.at("o")),
                        lambda: audiofile.peaks(src, 0, 0.5, 10)):
                with self.assertRaisesRegex(audiofile.AudioError, "ffmpeg is not installed"):
                    job()
            self.assertAlmostEqual(audiofile.duration(src), 1.0, places=3,
                                   msg="a WAV's length is read from its header")


@needs_ffmpeg
class FFmpegJobs(Temp):
    def test_best_output_on_this_machine(self):
        ext, codec = audiofile.best_output()
        self.assertIn(ext, (".mp3", ".m4a", ".wav"))
        if "libmp3lame" in audiofile.encoders():
            self.assertEqual(ext, ".mp3")

    def test_extract_cuts_the_window_asked_for(self):
        src = sine(self.at("six.mp3"), 6, 440, "-c:a", "libmp3lame")
        self.assertAlmostEqual(audiofile.duration(src), 6.0, delta=0.06)
        for start, end in ((1.25, 3.75), (0.0, 0.8), (4.9, 5.9)):
            with self.subTest(start=start, end=end):
                out = audiofile.extract(src, start, end, self.at("cut-%s" % start))
                self.assertTrue(out.endswith(audiofile.best_output()[0]))
                self.assertEqual(audiofile.kind(read(out)), os.path.splitext(out)[1])
                self.assertAlmostEqual(audiofile.duration(out), end - start, delta=0.06)

    def test_a_cut_holds_the_sound_from_its_first_moment(self):
        """The duration of a cut can be right while its sound is not: ffmpeg's
        MP3 decoder gives silence for 50 to 140 ms after a seek, so a word cut
        tight lost its first consonant, and a tone cut 20 ms in was not there
        at all.  In every format the tone is where the source has it, whole."""
        film = self.at("film.mp4")
        ff("-f", "lavfi", "-i", "testsrc=duration=8:size=160x120:rate=10",
           "-i", markers(self.at("film-sound.wav"), "-c:a", "pcm_s16le"),
           "-shortest", "-c:v", "libx264", "-c:a", "aac", film)
        sources = {
            "vbr.mp3": markers(self.at("vbr.mp3"), "-c:a", "libmp3lame", "-q:a", "4"),
            "cbr.mp3": markers(self.at("cbr.mp3"), "-c:a", "libmp3lame", "-b:a", "64k"),
            "a.m4a": markers(self.at("a.m4a"), "-c:a", "aac"),
            "a.ogg": markers(self.at("a.ogg"), "-c:a", "libvorbis"),
            "a.opus": markers(self.at("a.opus"), "-c:a", "libopus", rate=48000),
            "a.wav": markers(self.at("a.wav"), "-c:a", "pcm_s16le"),
            "film.mp4": film,
        }
        # a start before the tone, on it, inside it; and the same near the
        # beginning of the file, where there is less than a second to seek back
        for label, src in sources.items():
            for start, tone in ((4.95, 5.0), (4.99, 5.0), (5.0, 5.0), (5.02, 5.0), (5.06, 5.0),
                                (0.55, 0.6), (0.62, 0.6)):
                with self.subTest(src=label, start=start):
                    out = audiofile.extract(src, start, start + 0.3, self.at("c-%s-%s" % (label, start)))
                    first, last, length = loud(out)
                    self.assertAlmostEqual(length, 0.3, delta=0.03)
                    self.assertIsNotNone(first, "the tone is in the cut")
                    self.assertAlmostEqual(first, max(0.0, tone - start), delta=0.012,
                                           msg="the sound starts where the source's does")
                    self.assertAlmostEqual(last, tone + 0.1 - start, delta=0.012,
                                           msg="and ends where it ends: nothing faded away")

    def test_peaks_see_the_sound_at_the_start_of_a_window(self):
        for label, codec in (("vbr.mp3", ("-c:a", "libmp3lame", "-q:a", "4")),
                             ("cbr.mp3", ("-c:a", "libmp3lame", "-b:a", "64k"))):
            with self.subTest(label):
                src = markers(self.at(label), *codec)
                got = audiofile.peaks(src, 5.0, 5.2, 10)
                self.assertTrue(all(v > 0.5 for v in got[:4]), got)
                self.assertTrue(all(v < 0.05 for v in got[6:]), got)
                got = audiofile.peaks(src, 0.6, 0.8, 10)
                self.assertTrue(all(v > 0.5 for v in got[:4]), got)

    def test_extract_from_a_film_takes_the_sound_only(self):
        film = self.at("media.mp4")
        ff("-f", "lavfi", "-i", "testsrc=duration=6:size=160x120:rate=10",
           "-f", "lavfi", "-i", "sine=frequency=440:duration=6", "-shortest",
           "-c:v", "libx264", "-c:a", "aac", film)
        out = audiofile.extract(film, 2.0, 3.5, self.at("film-cut"))
        self.assertAlmostEqual(audiofile.duration(out), 1.5, delta=0.06)
        probe = os.path.join(os.path.dirname(audiofile.ffmpeg()), "ffprobe")
        streams = subprocess.run([probe, "-v", "error", "-show_entries", "stream=codec_type",
                                  "-of", "csv=p=0", out], capture_output=True, text=True).stdout
        self.assertEqual(streams.split(), ["audio"])

    def test_extract_refuses_a_backwards_window(self):
        src = sine(self.at("s.wav"), 2)
        with self.assertRaisesRegex(audiofile.AudioError, "end must come after"):
            audiofile.extract(src, 1.5, 1.0, self.at("x"))

    def test_transcode_a_browser_recording(self):
        for name, codec in (("rec.wav", ("-c:a", "pcm_s16le")), ("rec.webm", ("-c:a", "libopus"))):
            with self.subTest(name):
                src = sine(self.at(name), 3, 440, *codec)
                out = audiofile.transcode(src, self.at("t-" + name))
                ext = audiofile.best_output()[0]
                self.assertTrue(out.endswith(ext), out)
                self.assertEqual(audiofile.kind(read(out)), ext)
                self.assertAlmostEqual(audiofile.duration(out), 3.0, delta=0.08)

    def test_peaks(self):
        # a second of silence, then a second of tone
        src = self.at("half.wav")
        ff("-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-af", "adelay=1000:all=1",
           "-c:a", "pcm_s16le", src)
        self.assertAlmostEqual(audiofile.duration(src), 2.0, delta=0.06)
        got = audiofile.peaks(src, 0, 2, 20)
        self.assertEqual(len(got), 20)
        self.assertTrue(all(isinstance(v, float) and 0.0 <= v <= 1.0 for v in got), got)
        self.assertEqual(max(got), 1.0)
        self.assertTrue(all(v < 0.05 for v in got[:9]), got[:9])
        self.assertTrue(all(v > 0.5 for v in got[11:]), got[11:])
        self.assertEqual(len(audiofile.peaks(src, 0.5, 1.5, 4000)), 4000)
        self.assertEqual(len(audiofile.peaks(src, 0.5, 1.5, 999999)), 4000, "capped")
        self.assertEqual(audiofile.peaks(src, 5, 6, 8), [0.0] * 8, "past the end: silence")


if __name__ == "__main__":
    unittest.main()
