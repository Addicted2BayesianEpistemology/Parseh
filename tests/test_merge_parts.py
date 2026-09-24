#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""THE BATCHES MAY NEVER OVERWRITE WHAT THE PLAYER WROTE (TO-DO §2.2).

    python3 -m unittest discover -s tests -p test_merge_parts.py

`parts/` is retired: the batches are folded into annotations.json once,
while a video is being added, and dropped before it reaches the shelf
(`youtube/lib/ytpages.py`'s add road, `import_old_video.py`).  A video added
before that still has them on disk, so `merge_parts.py` keeps a guard: run
by hand over annotations that are NEWER than the batches and different from
what they would build, it refuses and says what would be lost -- because
that is exactly how a colour, a gloss or a note written in the player
disappeared without a word.

The guard is driven here over a copy of a real fixture video, on all four of
its paths, and the raw sentences it returns are read rather than a property
of them asserted.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "youtube", "lib"))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import merge_parts                                       # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "videos", "persian", "fA6bK2mQ8sT")


class Guard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="parseh-merge-guard-")
        self.d = os.path.join(self.tmp, "fA6bK2mQ8sT")
        shutil.copytree(FIXTURE, self.d)
        self.apath = os.path.join(self.d, "annotations.json")
        self.parts = sorted(merge_parts.glob.glob(os.path.join(self.d, "parts", "*.json")))
        self.assertTrue(self.parts, "the fixture carries its batches")
        with io.open(self.apath, encoding="utf-8") as f:
            self.was = json.load(f)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def glossed(self, ann):
        """The first caption that HAS chunks: a plain one (the video's own
        framing) has nothing a player could have changed."""
        return next(s for s in ann["segments"] if s.get("chunks"))

    def touch(self, path, when):
        os.utime(path, (when, when))

    def test_no_annotations_at_all_merges(self):
        """The add road, and every test that unlinks the file first: there is
        nothing to lose, so there is nothing to say."""
        os.unlink(self.apath)
        no, note = merge_parts.guard(self.d, self.parts, self.was)
        self.assertEqual((no, note), ("", ""))

    def test_the_same_file_again_merges(self):
        """Re-deriving a video to check it still works must keep working: the
        merge's result IS the file that is there, so nothing is lost."""
        self.touch(self.apath, time.time() + 600)        # newer, and identical
        no, note = merge_parts.guard(self.d, self.parts, self.was)
        self.assertEqual((no, note), ("", ""))

    def test_older_and_different_merges_but_says_so(self):
        """The by-hand pipeline doing what it always did -- allowed, because
        the batches are the later word, but never silently again."""
        out = json.loads(json.dumps(self.was))
        # the first caption is the video's own framing and carries no chunks
        self.glossed(out)["chunks"][0]["en"] = "something else entirely"
        # older than the batches THEMSELVES, not merely than now: the fixture's
        # batches were written when the fixture was
        self.touch(self.apath, max(os.path.getmtime(p) for p in self.parts) - 600)
        no, note = merge_parts.guard(self.d, self.parts, out)
        self.assertEqual(no, "")
        self.assertIn("annotations.json was there and is being replaced", note)
        self.assertIn("caption(s) differ", note)

    def test_newer_and_different_is_refused_naming_what_would_be_lost(self):
        """The fault itself: a video edited in the player, merged again by a
        hand following an older page of the guide."""
        out = json.loads(json.dumps(self.was))
        seg = self.glossed(out)
        seg["chunks"][0]["col"] = "green"                # a colour, as the player writes it
        seg["chunks"][0]["en"] = "not what the batch said"
        self.touch(self.apath, time.time() + 600)        # newer than the batches
        no, note = merge_parts.guard(self.d, self.parts, out)
        self.assertEqual(note, "")
        self.assertIn("annotations.json is newer than the batches", no)
        self.assertIn("Rebuilding would throw that away", no)
        self.assertIn("parts/ is retired", no)
        # it says WHICH captions, at what time on the player's own clock, and
        # in which fields -- a refusal nobody can act on is half a refusal
        self.assertIn("caption(s) differ, at ", no)
        self.assertIn("in: ", no)
        self.assertIn("col", no)

    def test_annotations_that_cannot_be_read_are_not_overwritten_either(self):
        """A half-written or hand-broken file is the one most worth keeping:
        it cannot be compared, so it is refused rather than replaced."""
        with io.open(self.apath, "w", encoding="utf-8") as f:
            f.write("{ not json at all")
        self.touch(self.apath, time.time() + 600)
        no, note = merge_parts.guard(self.d, self.parts, self.was)
        self.assertIn("annotations.json is newer than the batches", no)
        self.assertIn("cannot be read here", no)


class Retired(unittest.TestCase):
    """The tools that write the batches drop them, so nothing on the shelf
    carries a parts/ and the guard above is only ever met on an old video."""

    def test_the_add_road_and_the_importer_both_drop_them(self):
        for rel in ("youtube/lib/ytpages.py", "youtube/lib/import_old_video.py"):
            with io.open(os.path.join(ROOT, rel), encoding="utf-8") as f:
                src = f.read()
            self.assertIn('"parts"', src, rel)
            self.assertIn("rmtree", src, rel)

    def test_the_tool_says_what_it_is_for_now(self):
        with io.open(os.path.join(ROOT, "youtube/lib/merge_parts.py"), encoding="utf-8") as f:
            doc = f.read()
        self.assertIn("parts/ IS RETIRED", doc)


if __name__ == "__main__":
    unittest.main()
