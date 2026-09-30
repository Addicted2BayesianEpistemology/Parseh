#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Small deterministic CTC-trellis checks; ONNX itself stays in the worker."""
import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))
import ctcalign  # noqa: E402


class Trellis(unittest.TestCase):
    def test_spaced_words_follow_their_highest_monotonic_emissions(self):
        # blank, a, b, delimiter.  The best CTC path says a | b.
        logits = np.array([[7, 0, 0, 0], [0, 9, 0, 0], [7, 0, 0, 0],
                           [0, 0, 0, 9], [7, 0, 0, 0], [0, 0, 9, 0], [7, 0, 0, 0]],
                          dtype=np.float32)
        meta = {"model": {"blank_id": 0, "word_delimiter": "|"},
                "text": {"spaces_separate_words": True}}
        spans = ctcalign._spans(np, logits, "a b", {"a": 1, "b": 2, "|": 3}, meta)
        self.assertEqual([s[0] for s in spans], ["a", "b"])
        self.assertLess(spans[0][1], spans[0][2])
        self.assertLess(spans[0][2], spans[1][1])

    def test_an_unknown_character_remains_monotonic_without_claiming_a_vocab_entry(self):
        logits = np.array([[6, 0], [0, 8], [6, 0], [0, 8], [6, 0]], dtype=np.float32)
        meta = {"model": {"blank_id": 0}, "text": {"spaces_separate_words": False}}
        spans = ctcalign._spans(np, logits, "a?", {"a": 1}, meta)
        self.assertEqual("".join(s[0] for s in spans), "a?")


if __name__ == "__main__":
    unittest.main()
