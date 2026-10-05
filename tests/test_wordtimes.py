#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The held word-time tape: identities, exact starts and safe adoption."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "youtube", "lib"), os.path.join(ROOT, "lib")]
import wordtimes as W  # noqa: E402


JOB = "Abcdefghijklmnop"
WORDS = [{"text": "hello", "start": 1.0, "end": 1.2},
         {"text": "world", "start": 1.4, "end": 1.8},
         {"text": "again", "start": 3.0, "end": 3.4}]
CAPS = [{"start": 1.0, "text": "hello world", "chapter": None},
        {"start": 3.0, "text": "again", "chapter": None}]


class WordTimes(unittest.TestCase):
    def document(self):
        return W.sync(W.empty(JOB, "en", WORDS), CAPS, "en")

    def test_split_uses_the_moved_word_not_half_a_caption(self):
        doc = self.document()
        split = [{"start": 1.0, "text": "hello", "chapter": None},
                 {"start": 1.4, "text": "world", "chapter": None},
                 {"start": 3.0, "text": "again", "chapter": None}]
        doc = W.sync(doc, split, "en")
        self.assertEqual([W.caption_start(doc, c) for c in doc["captions"]], [1.0, 1.4, 3.0])
        self.assertEqual([a["id"] for a in doc["atoms"]][:2],
                         ["w:%s:000000" % JOB, "w:%s:000001" % JOB])

    def test_inserted_word_is_not_claimed_as_recording(self):
        doc = W.sync(self.document(), [{"start": 1, "text": "hello new world", "chapter": None},
                                        {"start": 3, "text": "again", "chapter": None}], "en")
        self.assertEqual([a["time_source"] for a in doc["atoms"]],
                         ["whisper", "interpolated", "whisper", "whisper"])

    def test_pin_wins_and_shift_moves_words_and_pin(self):
        doc = self.document()
        atom = doc["captions"][1]["id"].removeprefix("c:")
        doc = W.set_pins(doc, [{"atom": atom, "start": 2.75}])
        doc = W.shift_all(doc, 0.5)
        self.assertEqual(W.caption_start(doc, doc["captions"][1]), 3.25)
        self.assertEqual(doc["atoms"][2]["start"], 3.5)

    def test_hold_adopts_only_its_exact_panel(self):
        doc = self.document()
        panel = "0:01\nhello world\n0:03\nagain\n"
        doc["panel_sha256"] = W.panel_hash(panel)
        with tempfile.TemporaryDirectory() as tmp:
            W.hold(JOB, doc, tmp)
            video = os.path.join(tmp, "video"); os.mkdir(video)
            self.assertEqual(W.adopt(JOB, video, panel, "en", tmp)["kept"], True)
            self.assertTrue(os.path.isfile(os.path.join(video, "wordtimes.json")))
            W.hold(JOB, doc, tmp)
            self.assertFalse(W.adopt(JOB, video, panel + "changed", "en", tmp)["kept"])

    def test_cjk_marks_and_punctuation_do_not_make_extra_atoms(self):
        self.assertEqual(W.pieces("你好，世界。", "zh"), ["你", "好", "世", "界"])
        self.assertEqual(W.pieces("می‌گوید، خوب", "fa"), ["می‌گوید،", "خوب"])
        doc = W.empty(JOB, "zh", [{"text": "你好", "start": 1, "end": 3}])
        self.assertEqual([(a["surface"], a["start"], a["end"]) for a in doc["atoms"]],
                         [("你", 1.0, 2.0), ("好", 2.0, 3.0)])

    def test_an_interior_person_pin_is_reported_not_silently_lost(self):
        doc = self.document()
        atom = doc["atoms"][1]["id"]
        doc = W.set_pins(doc, [{"atom": atom, "start": 1.4}])
        self.assertEqual(W.orphaned_pins(doc), [atom])


if __name__ == "__main__":
    unittest.main()
