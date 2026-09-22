#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""lib/fill_words.py on copies of the Japanese and Chinese fixture videos.

    python3 -m unittest discover -s tests -p test_fillwords.py

The filling itself needs the analyzers, so it is skipped under a Python that
lacks them; the refusals are tested under any Python.
"""
import hashlib
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
import check_annotations                                        # noqa: E402
import fill_words                                               # noqa: E402
import languages                                                # noqa: E402
import words                                                    # noqa: E402

FIXTURES = os.path.join(ROOT, "tests", "fixtures", "videos")
QUIET = lambda *a, **k: None                                     # noqa: E731


def _digest(path):
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()


class FillVideo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="parseh-fillwords-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def copy(self, folder):
        src_parent = os.path.join(FIXTURES, folder)
        name = sorted(os.listdir(src_parent))[0]
        dst = os.path.join(self.tmp, folder, name)
        shutil.copytree(os.path.join(src_parent, name), dst)
        return dst

    def wanting(self, vdir):
        """The chunks the tool should give words: glossed, not plain, holding
        the language's script."""
        with open(os.path.join(vdir, "annotations.json"), encoding="utf-8") as f:
            ann = json.load(f)
        with open(os.path.join(vdir, "video.json"), encoding="utf-8") as f:
            L = languages.get(json.load(f)["language"])
        return sum(1 for s in ann["segments"] if not s.get("plain")
                   for c in s.get("chunks") or []
                   if not c.get("plain") and L.has_script(c.get("fa") or ""))

    def test_fills_checks_and_is_idempotent(self):
        for folder, code in (("japanese", "ja"), ("chinese", "zh")):
            with self.subTest(code=code):
                if not words.available(code):
                    self.skipTest("no analyzer for %s in %s" % (code, sys.executable))
                vdir = self.copy(folder)
                want = self.wanting(vdir)
                self.assertGreater(want, 0)
                first = fill_words.fill_video(vdir, say=QUIET)
                self.assertEqual((first["given"], first["refused"]), (want, []))
                errors, _warnings, _counts = check_annotations.check(vdir)
                self.assertEqual(errors, [])
                again = fill_words.fill_video(vdir, say=QUIET)
                self.assertEqual((again["given"], again["had"]), (0, want))

    def test_dry_run_writes_nothing(self):
        if not words.available("ja"):
            self.skipTest("no analyzer for ja in %s" % sys.executable)
        vdir = self.copy("japanese")
        path = os.path.join(vdir, "annotations.json")
        before = _digest(path)
        r = fill_words.fill_video(vdir, dry_run=True, say=QUIET)
        self.assertGreater(r["given"], 0)
        self.assertEqual(_digest(path), before)

    def test_a_line_already_there_is_kept(self):
        if not words.available("ja"):
            self.skipTest("no analyzer for ja in %s" % sys.executable)
        vdir = self.copy("japanese")
        path = os.path.join(vdir, "annotations.json")
        with open(path, encoding="utf-8") as f:
            ann = json.load(f)
        seg = next(s for s in ann["segments"] if s.get("chunks"))
        ch = seg["chunks"][0]
        mine = " ".join(ch["fa"])                # one word per character: a hand line
        ch["words"] = mine
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ann, f, ensure_ascii=False, indent=1)
        fill_words.fill_video(vdir, say=QUIET)
        with open(path, encoding="utf-8") as f:
            again = json.load(f)
        first = next(s for s in again["segments"] if s.get("chunks"))["chunks"][0]
        self.assertEqual(first["words"], mine)

    def test_refuses_without_analyzers(self):
        vdir = self.copy("japanese")
        real = words.available
        words.available = lambda code: False
        try:
            with self.assertRaises(SystemExit) as cm:
                fill_words.fill_video(vdir, say=QUIET)
        finally:
            words.available = real
        self.assertIn(sys.executable, str(cm.exception))

    def test_refuses_a_language_without_words(self):
        vdir = self.copy("arabic")
        with self.assertRaises(SystemExit) as cm:
            fill_words.fill_video(vdir, say=QUIET)
        self.assertIn("no word layer", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
