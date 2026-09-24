#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Moving a caption's start on a video already on the shelf.

    python3 -m unittest discover -s tests -p test_captimes.py

WHAT HAS TO HOLD, and why this file exists at all.  youtube/lib/subedit.js
says there is no editor for a video already in the player, because "a door
that could rewrite it would quietly unmake that check" -- the check being
check_annotations holding annotations.json and transcript.txt to each other.
youtube/lib/captimes.py argues that a START is the one thing that door may
move, because moving it in BOTH files by the same amount leaves every rule
the checker enforces exactly as true as before.

That argument is only worth anything if it is tested, so:

  a) THE THREE FILES MOVE TOGETHER.  annotations.json, transcript.txt and
     parts/NN.json all carry the start.  The proof that they agree afterwards
     is the one smoke.py uses for the whole shelf: delete annotations.json,
     let merge_parts.py rebuild it from the parts and the transcript, and
     require the result to be byte for byte what was there before.  A start
     left behind in any one of the three fails that.
  b) THE CHECKER STILL PASSES, and passed before, and the edit brought in no
     error of its own.
  c) WHAT IT REFUSES, it refuses whole: a start pushed before the one in
     front of it, a caption that is not where the editor thought it was, a
     caption that does not exist -- and after each refusal nothing on disk
     has moved at all.
  d) A PRE-EXISTING COMPLAINT IS NOT "BROUGHT IN".  The checker names a
     segment by its start ("segment 1 (start 3): no chunks"), so the very
     same complaint reads differently once the start moves.  Every draft has
     unglossed segments; if that counted as an error the edit introduced, no
     draft could ever have a caption moved.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
for folder in ("youtube/lib", "lib", "markdown/app"):
    sys.path.insert(0, os.path.join(REPO, folder))

import bundle                                      # noqa: E402
import captimes                                    # noqa: E402
import check_annotations as CA                     # noqa: E402

FIXTURE = os.path.join(REPO, "tests/fixtures/videos/persian/fA6bK2mQ8sT")


class Moving(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="parseh-captimes-")
        self.d = os.path.join(self.tmp, "fA6bK2mQ8sT")
        shutil.copytree(FIXTURE, self.d)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ann(self):
        with io.open(os.path.join(self.d, "annotations.json"), encoding="utf-8") as f:
            return json.load(f)

    def starts(self):
        return [s["start"] for s in self.ann()["segments"]]

    def captions(self):
        with io.open(os.path.join(self.d, "transcript.txt"), encoding="utf-8") as f:
            return CA.parse_transcript_text(f.read(), "fa")

    def test_the_fixture_starts_clean(self):
        errors, _warn, _n = CA.check(self.d)
        self.assertEqual(errors, [], "the fixture is the ground this stands on")

    def test_a_start_moves_in_annotations_and_in_the_transcript(self):
        was = self.starts()
        to = round((was[1] + was[2]) / 2, 1)
        out = captimes.move(self.d, [{"i": 1, "from": was[1], "to": to}])
        self.assertEqual(out["moved"], 1)
        now = self.starts()
        self.assertEqual(now[1], to)
        self.assertEqual(now[:1] + now[2:], was[:1] + was[2:],
                         "nothing but the caption asked for moved")
        self.assertEqual([c["start"] for c in self.captions()], now,
                         "transcript.txt carries exactly the same starts")
        errors, _w, _n = CA.check(self.d)
        self.assertEqual(errors, [], "and the checker still passes")

    def test_the_batches_move_too_so_merge_parts_rebuilds_the_same_file(self):
        was = self.starts()
        captimes.move(self.d, [{"i": 1, "from": was[1], "to": was[1] + 1}])
        path = os.path.join(self.d, "annotations.json")
        with io.open(path, encoding="utf-8") as f:
            built = f.read()
        os.remove(path)
        r = subprocess.run([sys.executable,
                            os.path.join(REPO, "youtube/lib/merge_parts.py"), self.d],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr or r.stdout)
        with io.open(path, encoding="utf-8") as f:
            again = f.read()
        self.assertEqual(again, built,
                         "a start left behind in parts/ would show up right here")

    def test_a_start_may_not_pass_the_one_in_front_of_it(self):
        was = self.starts()
        with self.assertRaises(ValueError) as e:
            captimes.move(self.d, [{"i": 2, "from": was[2], "to": was[1] - 1}])
        self.assertIn("cannot start before", str(e.exception))
        self.assertEqual(self.starts(), was, "and nothing moved")

    def test_a_caption_that_has_moved_under_the_editor_is_refused(self):
        was = self.starts()
        with self.assertRaises(ValueError) as e:
            captimes.move(self.d, [{"i": 0, "from": was[0] + 5, "to": 1}])
        self.assertIn("another hand", str(e.exception))
        self.assertEqual(self.starts(), was)

    def test_a_caption_that_is_not_there(self):
        was = self.starts()
        for moves in ([{"i": 99, "from": 1, "to": 2}], [], "not a list"):
            with self.assertRaises(ValueError):
                captimes.move(self.d, moves)
        self.assertEqual(self.starts(), was)

    def test_several_at_once(self):
        was = self.starts()
        out = captimes.move(self.d, [{"i": 1, "from": was[1], "to": was[1] + 1},
                                     {"i": 3, "from": was[3], "to": was[3] + 2}])
        self.assertEqual(out["moved"], 2)
        now = self.starts()
        self.assertEqual([now[1], now[3]], [was[1] + 1, was[3] + 2])
        self.assertEqual([c["start"] for c in self.captions()], now)
        errors, _w, _n = CA.check(self.d)
        self.assertEqual(errors, [])

    def test_the_same_caption_twice_in_one_ask(self):
        was = self.starts()
        with self.assertRaises(ValueError) as e:
            captimes.move(self.d, [{"i": 1, "from": was[1], "to": was[1] + 1},
                                   {"i": 1, "from": was[1], "to": was[1] + 2}])
        self.assertIn("twice", str(e.exception))

    def test_a_whole_number_stays_whole(self):
        was = self.starts()
        captimes.move(self.d, [{"i": 1, "from": was[1], "to": was[1] + 1.0}])
        self.assertIsInstance(self.starts()[1], int,
                              "6.0 where every other hand writes 6 is a diff that means nothing")

    def test_a_tenth_survives(self):
        was = self.starts()
        captimes.move(self.d, [{"i": 1, "from": was[1], "to": was[1] + 0.5}])
        self.assertEqual(self.starts()[1], was[1] + 0.5)
        self.assertEqual([c["start"] for c in self.captions()][1], was[1] + 0.5,
                         "the transcript writes the fraction too (stamp_of)")


class UnglossedSegments(unittest.TestCase):
    """A draft has segments nobody has glossed, and the checker says so every
    time.  That complaint names the segment by its start, so it READS
    differently once the start moves -- and counting that as an error the
    edit brought in would lock every draft out of this door."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="parseh-captimes-draft-")
        self.d = os.path.join(self.tmp, "v")
        os.makedirs(self.d)
        with io.open(os.path.join(self.d, "annotations.json"), "w", encoding="utf-8") as f:
            json.dump({"video": "v", "language": "en", "segments": [
                {"start": 0, "text": "Hello there."},
                {"start": 2, "text": "The market opens early."},
                {"start": 5, "text": "Bring a bag."}]}, f)
        with io.open(os.path.join(self.d, "video.json"), "w", encoding="utf-8") as f:
            json.dump({"id": "v", "language": "english", "title": "t"}, f)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_segment_with_no_chunks_does_not_block_the_move(self):
        out = captimes.move(self.d, [{"i": 1, "from": 2, "to": 3}])
        self.assertEqual(out["moved"], 1)
        with io.open(os.path.join(self.d, "annotations.json"), encoding="utf-8") as f:
            self.assertEqual([s["start"] for s in json.load(f)["segments"]], [0, 3, 5])

    def test_and_a_video_with_no_transcript_is_still_written(self):
        captimes.move(self.d, [{"i": 2, "from": 5, "to": 6}])
        self.assertFalse(os.path.exists(os.path.join(self.d, "transcript.txt")),
                         "none was there and none was invented")


class Notes(unittest.TestCase):
    """A note names its caption by that caption's start, so a start that
    moves without it leaves the note pointing at nothing."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="parseh-captimes-notes-")
        self.d = os.path.join(self.tmp, "fA6bK2mQ8sT")
        shutil.copytree(FIXTURE, self.d)
        # WHERE THE STUDIO REALLY PUTS A VIDEO'S NOTES (§2.1): this test used
        # to write into <video>/notes/, the same folder captimes.py looked in
        # and the studio has never written -- so both were wrong together and
        # the test passed while a moved caption left its note behind.  The
        # studio's own layout is markdown/<language>/<id>/source.md
        # (markdown/app/notes.py, DIR = "markdown").
        d = os.path.join(self.d, "markdown", "persian", "a-note")
        os.makedirs(d)
        self.note = os.path.join(d, "source.md")
        with io.open(self.note, "w", encoding="utf-8") as f:
            f.write("---\ntitle: About this bit\nanchor: after cap 12\n---\n\nSomething.\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_note_follows_the_caption_it_is_anchored_to(self):
        out = captimes.move(self.d, [{"i": 2, "from": 12, "to": 13}])
        self.assertEqual(out["notes"], 1)
        with io.open(self.note, encoding="utf-8") as f:
            self.assertIn("anchor: after cap 13", f.read())

    def test_a_note_anchored_elsewhere_is_left_alone(self):
        out = captimes.move(self.d, [{"i": 1, "from": 6, "to": 7}])
        self.assertEqual(out["notes"], 0)
        with io.open(self.note, encoding="utf-8") as f:
            self.assertIn("anchor: after cap 12", f.read())


if __name__ == "__main__":
    unittest.main()


class Travelling(unittest.TestCase):
    """A recorded waveform goes in the bundle.

    A YouTube video's sound reaches no script in this toolbox, so the
    picture of it is a recording of the whole video made in real time in a
    browser that can share a tab.  It is derived, and it is derived from a
    source no bundle can carry -- so a video that arrives on another machine
    without it costs somebody an hour of sitting through the video again.
    It travels, and (like the film, for the same reason at a larger size) it
    is given up only to another waveform: a bundle made before it was
    recorded carries none, and must not take the one that is here.
    """

    WAVE = {"rate": 20, "peaks": [0, 0.5, 1, 0.25]}

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="parseh-wave-bundle-")
        self.src = os.path.join(self.tmp, "fA6bK2mQ8sT")
        shutil.copytree(FIXTURE, self.src)
        self.wave = os.path.join(self.src, "waveform.json")
        with io.open(self.wave, "w", encoding="utf-8") as f:
            json.dump(self.WAVE, f)
        # the same video as it was before anybody drew its sound
        self.plain = os.path.join(self.tmp, "plain", "fA6bK2mQ8sT")
        os.makedirs(os.path.dirname(self.plain))
        shutil.copytree(FIXTURE, self.plain)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def waveform_at(self, d):
        p = os.path.join(d, "waveform.json")
        if not os.path.exists(p):
            return None
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)

    def test_the_download_carries_it(self):
        data, _name = bundle.pack_video(self.src)
        names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        self.assertTrue([n for n in names if n.endswith("waveform.json")],
                        "it is in the zip: %s" % names)

    def test_and_it_arrives_byte_for_byte(self):
        data, _name = bundle.pack_video(self.src)
        into = os.path.join(self.tmp, "far")
        os.makedirs(into)
        r = bundle.install(data, root=into)
        self.assertTrue(r.get("ok"), r)
        dest = os.path.join(into, r["dir"])
        self.assertEqual(self.waveform_at(dest), self.WAVE)
        with io.open(os.path.join(dest, "waveform.json"), "rb") as a, \
             io.open(self.wave, "rb") as b:
            self.assertEqual(a.read(), b.read())

    def test_a_bundle_carrying_none_leaves_the_one_here_alone(self):
        into = os.path.join(self.tmp, "far")
        os.makedirs(into)
        bundle.install(bundle.pack_video(self.src)[0], root=into)
        r = bundle.install(bundle.pack_video(self.plain)[0], replace=True, root=into)
        self.assertTrue(r.get("ok"), r)
        self.assertEqual(self.waveform_at(os.path.join(into, r["dir"])), self.WAVE,
                         "an hour of somebody's afternoon is not given up to a "
                         "bundle made before it was spent")

    def test_but_a_bundle_carrying_one_replaces_it(self):
        other = {"rate": 50, "peaks": [1, 1, 1]}
        with io.open(os.path.join(self.plain, "waveform.json"), "w", encoding="utf-8") as f:
            json.dump(other, f)
        into = os.path.join(self.tmp, "far")
        os.makedirs(into)
        bundle.install(bundle.pack_video(self.src)[0], root=into)
        r = bundle.install(bundle.pack_video(self.plain)[0], replace=True, root=into)
        self.assertEqual(self.waveform_at(os.path.join(into, r["dir"])), other,
                         "a waveform IS given up to another waveform")

    def test_a_video_with_no_waveform_packs_as_it_always_did(self):
        data, _name = bundle.pack_video(self.plain)
        names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        self.assertFalse([n for n in names if n.endswith("waveform.json")],
                         "nothing is invented for a video that has none: %s" % names)
