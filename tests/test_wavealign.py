# SPDX-License-Identifier: GPL-3.0-or-later
"""The transcript laid over the picture of its sound (lib/wavealign.py), and
its bench (lib/wavealign_lab.py).

    python3 -m unittest tests/test_wavealign.py -v

What has to hold:

  * THE SHAPE OF TIME: every word 0 <= start < end <= duration and never
    overlapping the next; every piece of estimate_pieces as the contract
    says -- the first starting at exactly 0, none too short to play, a
    video's captions end to end with the last ending at the end, a book's
    pieces split only across a real pause.  Over many made-up recordings,
    not one.
  * THE SAME QUESTION, THE SAME ANSWER, to the last bit.
  * NOTHING BREAKS IT: no sound, a flat line, NaN and inf, a number too
    big for a float, one number, one word, a thousand words in five
    seconds, no words, punctuation alone, a stretch silent but for its two
    ends -- an answer every time, and ValueError only for no pieces or a
    duration that is not a positive number (or shorter than a microsecond).
  * EVERY LANGUAGE Parseh teaches is split and weighed by Unicode, never by
    a word list: Persian with and without its vowel marks weighs the same,
    Hindi's vowel signs count, Japanese and Chinese are read a character at
    a time, and each of them is aligned better than "by the text" does.
  * IT IS BETTER THAN BY THE TEXT where the sound shows its pauses, by the
    margins measured on the made-up recordings (lib/wavealign_lab.py); and
    where the sound shows nothing it falls back to about what the text
    says, with a confidence that says so.
  * IT IS FAST ENOUGH: a quarter of an hour in a few seconds (the hour and
    the four hours of the contract are timed by `wavealign_lab.py bench`),
    and LEAN: two captions left over two hours, three over two hours, four
    thousand pieces in a minute -- each in memory and time far below what
    they once took.
  * A TEXT NOBODY PUNCTUATED (auto-captions) is no worse than half again
    what by the text does, however long; and where the envelope shows
    nothing at all, the answer IS the proportional one.

Made-up recordings only: nothing here reads a shelf, a timings.json or a
waveform.json -- no recording Parseh holds has cuts that could serve as the
truth.  Skips cleanly where NumPy is missing.
"""
import json
import math
import os
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))

try:
    import numpy as np
    import wavealign as W
    import wavealign_lab as lab
except ImportError:                     # no NumPy here: nothing to test
    np = W = lab = None

from dataclasses import replace         # noqa: E402

needs_numpy = unittest.skipUnless(W is not None, "numpy is not installed")

TOL = 1e-9          # the documented tolerance of the word order (exact in fact)


def synth(**kw):
    return lab.synthesize(replace(lab.SynthConfig(), **kw))


def check_words(tc, words, D):
    for w in words:
        tc.assertTrue(0.0 <= w.start < w.end <= D, (w.word, w.start, w.end, D))
        tc.assertTrue(0.0 <= w.confidence <= 1.0)
        tc.assertTrue(w.start_min <= w.start <= w.start_max, w)
        tc.assertTrue(w.end_min <= w.end <= w.end_max, w)
    for a, b in zip(words, words[1:]):
        tc.assertLessEqual(a.end, b.start + TOL, (a.word, a.end, b.word, b.start))


def check_pieces(tc, est, D, texts, kind, opts=None):
    o = opts or W.AlignmentOptions()
    ps = est["pieces"]
    N = len(texts)
    tc.assertEqual(len(ps), N)
    tc.assertEqual(ps[0]["t0"], 0.0)
    tc.assertEqual(est["boundaries"], N - 1)
    tc.assertEqual(est["method"], "wavealign")
    tc.assertEqual(est["version"], "1")
    tc.assertTrue(0.0 <= est["confidence"] <= 1.0)
    tc.assertTrue(0 <= est["anchored"] <= N - 1)
    least = min(o.min_piece, D / N * 0.5)
    for i, p in enumerate(ps):
        tc.assertTrue(0.0 <= p["t0"] < p["t1"] <= D, (i, p, D))
        tc.assertGreaterEqual(p["t1"] - p["t0"], least * (1 - 1e-9), (i, p, least))
        tc.assertTrue(0.0 <= p["confidence"] <= 1.0)
        tc.assertTrue(p["t0_min"] <= p["t0"] <= p["t0_max"], (i, p))
        tc.assertTrue(p["t0"] <= p["speech"][0] <= p["speech"][1] <= p["t1"], (i, p))
        for k in ("t0", "t1", "confidence", "t0_min", "t0_max"):
            tc.assertIsInstance(p[k], float)
    tc.assertEqual(ps[0]["confidence"], 1.0)
    if kind == "point":
        for a, b in zip(ps, ps[1:]):
            tc.assertEqual(a["t1"], b["t0"])
        tc.assertEqual(ps[-1]["t1"], D)
    else:
        for a, b in zip(ps, ps[1:]):
            tc.assertLessEqual(a["t1"], b["t0"])
    json.dumps(est)                     # plain numbers, nothing NumPy


@needs_numpy
class TheTranscript(unittest.TestCase):
    """Tokens, weights and breaks, by Unicode properties alone."""

    def test_whitespace_words_keep_their_punctuation(self):
        self.assertEqual(W.default_tokenize("Hello, world! «Bonjour» dit-il."),
                         ["Hello,", "world!", "«Bonjour»", "dit-il."])

    def test_scripts_without_spaces_go_a_character_at_a_time(self):
        self.assertEqual(W.default_tokenize("我们是学生。"), ["我", "们", "是", "学", "生。"])
        self.assertEqual(W.default_tokenize("こんにちは、世界。"),
                         ["こ", "ん", "に", "ち", "は、", "世", "界。"])
        # a prolonged sound mark stays with its kana; Thai keeps its marks
        self.assertEqual(W.default_tokenize("ポーランド"), ["ポー", "ラ", "ン", "ド"])
        self.assertEqual(W.default_tokenize("สวัสดี"), ["ส", "วั", "ส", "ดี"])
        # Korean writes spaces: its words stay whole
        self.assertEqual(W.default_tokenize("안녕하세요 세계"), ["안녕하세요", "세계"])
        # a Latin word inside Japanese stays a word
        self.assertEqual(W.default_tokenize("私はParsehです"), ["私", "は", "Parseh", "で", "す"])

    def test_character_counts_leave_out_marks_and_punctuation(self):
        bare, vowelled = "سلام دنیا.", "سَلام دُنیا."
        self.assertEqual([W.char_count(t) for t in W.default_tokenize(bare)], [4, 4])
        self.assertEqual([W.char_count(t) for t in W.default_tokenize(vowelled)], [4, 4])
        self.assertEqual(W.char_count("مَرْحَبًا"), W.char_count("مرحبا"))
        # Devanagari: a dependent vowel sign is written and spoken -- it
        # counts; the virama (and nukta, anusvara) do not
        self.assertEqual(W.char_count("नमस्ते"), 5)       # न म स त + े
        self.assertEqual(W.char_count("कि"), 2)
        self.assertEqual(W.char_count("क्"), 1)
        self.assertEqual(W.char_count("...!?"), 0)
        self.assertEqual(W.char_count("2026"), 4)

    def test_punctuation_classes(self):
        for ch in ".!?…。！？؟۔।॥":
            self.assertEqual(W.punctuation_class(ch), W.BREAK_SENTENCE, ch)
        for ch in ",،、，—":
            self.assertEqual(W.punctuation_class(ch), W.BREAK_COMMA, ch)
        for ch in ";:؛；：":
            self.assertEqual(W.punctuation_class(ch), W.BREAK_COLON, ch)
        for ch in "\"«»()-'¿¡":
            self.assertEqual(W.punctuation_class(ch), 0, ch)
        self.assertEqual(W.punctuation_class("a"), -1)

    def test_breaks_paragraphs_and_repeated_punctuation(self):
        m = W.TranscriptAnalyzer(W.AlignmentOptions()).analyze(
            ["One, two; three!!! Four...\n\n  Five?! six «seven.» eight"])
        self.assertEqual(m.tokens, ["One,", "two;", "three!!!", "Four...", "Five?!", "six",
                                    "«seven.»", "eight"])
        self.assertEqual(list(m.level), [W.BREAK_COMMA, W.BREAK_COLON, W.BREAK_SENTENCE,
                                         W.BREAK_PARAGRAPH, W.BREAK_SENTENCE, W.BREAK_WORD,
                                         W.BREAK_SENTENCE, W.BREAK_WORD])
        # a token of punctuation alone joins its neighbour
        m = W.TranscriptAnalyzer(W.AlignmentOptions()).analyze(["Hello ... what ?! « yes »"])
        self.assertEqual(m.tokens, ["Hello...", "what?!", "«yes»"])

    def test_the_duration_priors(self):
        ta = lambda **k: W.TranscriptAnalyzer(W.AlignmentOptions(**k))   # noqa: E731
        self.assertAlmostEqual(ta(duration_prior="linear").weight(9, False), 9.0)
        self.assertAlmostEqual(ta(duration_prior="sqrt").weight(9, False), 3.0)
        self.assertAlmostEqual(ta(duration_prior="power", alpha=0.75).weight(16, False), 8.0)
        self.assertAlmostEqual(ta(duration_prior="affine", affine_constant=2,
                                  affine_per_char=1).weight(5, False), 7.0)
        self.assertEqual(ta(min_weight=1.0).weight(0, False), 1.0)

    def test_the_tokenizer_is_a_callback(self):
        seen = []

        def by_bars(text):
            seen.append(text)
            return text.split("|")
        res = W.align_transcript_to_waveform([0.5] * 100, 5.0, "a b|c d|e", tokenize=by_bars)
        self.assertEqual([w.word for w in res.words], ["a b", "c d", "e"])
        self.assertEqual(seen, ["a b|c d|e"])

        def broken(text):
            raise RuntimeError("no")
        res = W.align_transcript_to_waveform([0.5] * 100, 5.0, "a b c", tokenize=broken)
        self.assertEqual([w.word for w in res.words], ["a", "b", "c"])

        # ... and however else it breaks: not a list at all, a generator
        # that raises halfway, a token that cannot be made a string
        def lazy(text):
            yield "a"
            raise RuntimeError("late")

        class Unsayable:
            def __str__(self):
                raise RuntimeError("no str")
        for tk in (lambda text: 5, lazy, lambda text: [Unsayable()]):
            res = W.align_transcript_to_waveform([0.5] * 100, 5.0, "a b c", tokenize=tk)
            self.assertEqual([w.word for w in res.words], ["a", "b", "c"])
            est = W.estimate_pieces([0.5] * 100, 5.0, ["a b", "c"], tokenize=tk)
            self.assertEqual(est["words"], 3)

    def test_a_tatweel_is_ink_not_a_letter(self):
        # U+0640 stretches a word across the line and is said as nothing:
        # a word drawn out with it weighs what the word without it weighs
        self.assertEqual(W.char_count("سـلام"), W.char_count("سلام"))
        self.assertEqual(W.char_count("كـــتاب"), 4)
        case = synth(seed=10, language="ar", n_words=40)
        drawn = [t.replace("ب", "بـ") for t in case.pieces]
        self.assertNotEqual(drawn, case.pieces)
        a = W.estimate_pieces(case.envelope, case.duration, case.pieces, "span")
        b = W.estimate_pieces(case.envelope, case.duration, drawn, "span")
        self.assertEqual(json.dumps(a), json.dumps(b))


@needs_numpy
class TheShapeOfTime(unittest.TestCase):
    """The invariants, over many made-up recordings of every kind."""

    def test_invariants_over_many_seeds(self):
        rng = np.random.default_rng(1234)
        langs = ["en", "fa", "ar", "hi", "ja", "zh", "it", "fr", "de", "tr", "es"]
        for seed in range(36):
            cfg = lab.SynthConfig(
                seed=seed, language=langs[seed % len(langs)],
                n_words=int(rng.integers(3, 70)),
                rate=float(rng.choice([5.0, 20.0, 100.0, 37.0])),
                style=str(rng.choice(["peak", "rms"])),
                noise_db=float(rng.uniform(-45, -10)),
                valley_depth=float(rng.uniform(0.1, 0.9)),
                sentence_pause_prob=float(rng.uniform(0.2, 1.0)),
                lead=float(rng.uniform(0.0, 3.0)), trail=float(rng.uniform(0.0, 3.0)),
                pieces=str(rng.choice(["sentences", "captions"])), fine_rate=1000.0)
            case = lab.synthesize(cfg)
            with self.subTest(seed=seed, lang=cfg.language, rate=cfg.rate):
                res = W.align_transcript_to_waveform(case.envelope, case.duration, case.transcript)
                self.assertEqual(len(res.words), len(case.tokens))
                check_words(self, res.words, case.duration)
                self.assertTrue(0.0 <= res.global_confidence <= 1.0)
                for kind in ("span", "point"):
                    est = W.estimate_pieces(case.envelope, case.duration, case.pieces, kind)
                    check_pieces(self, est, case.duration, case.pieces, kind)

    def test_a_split_is_a_pause_and_a_join_is_not(self):
        o = W.AlignmentOptions()
        for seed in range(4):
            case = synth(seed=seed, n_words=80)
            est = W.estimate_pieces(case.envelope, case.duration, case.pieces, "span")
            ps = est["pieces"]
            for a, b in zip(ps, ps[1:]):
                gap = b["speech"][0] - a["speech"][1]
                if a["t1"] < b["t0"]:
                    self.assertGreaterEqual(gap, o.split_gap - 1e-9)
                    pad = min(o.pad, gap / 3.0)
                    self.assertAlmostEqual(a["t1"], a["speech"][1] + pad, places=9)
                    self.assertAlmostEqual(b["t0"], b["speech"][0] - pad, places=9)
                else:
                    self.assertLess(gap, o.split_gap)
                    self.assertTrue(a["speech"][1] - 1e-9 <= a["t1"] <= b["speech"][0] + 1e-9)
            # the trailing silence is left to nobody
            self.assertAlmostEqual(ps[-1]["t1"], min(case.duration, ps[-1]["speech"][1] + o.pad))
            est = W.estimate_pieces(case.envelope, case.duration, case.pieces, "point")
            ps = est["pieces"]
            for a, b in zip(ps, ps[1:]):
                gap = b["speech"][0] - a["speech"][1]
                if gap >= o.split_gap:
                    self.assertAlmostEqual(b["t0"], b["speech"][0] - min(o.pad, gap / 2), places=9)

    def test_no_room_still_increasing(self):
        # forty pieces in a second and a half: none can have 0.4 s
        texts = ["w%d" % i for i in range(40)]
        for kind in ("span", "point"):
            est = W.estimate_pieces([0.2, 0.6, 0.1] * 50, 1.5, texts, kind)
            check_pieces(self, est, 1.5, texts, kind)

    def test_empty_and_punctuation_pieces_get_a_slice(self):
        case = synth(seed=3, n_words=30)
        texts = [""] + case.pieces[:2] + ["...", "", "!!"] + case.pieces[2:]
        for kind in ("span", "point"):
            est = W.estimate_pieces(case.envelope, case.duration, texts, kind)
            check_pieces(self, est, case.duration, texts, kind)
        self.assertEqual(est["words"], 30)

    def test_the_same_question_the_same_answer(self):
        case = synth(seed=5, n_words=60, pieces="captions")
        a = W.estimate_pieces(case.envelope, case.duration, case.pieces, "point")
        b = W.estimate_pieces(list(case.envelope), case.duration, list(case.pieces), "point",
                              options=W.AlignmentOptions())
        self.assertEqual(json.dumps(a), json.dumps(b))
        r1 = W.align_transcript_to_waveform(case.envelope, case.duration, case.transcript)
        r2 = W.align_transcript_to_waveform(case.envelope, case.duration, case.transcript)
        self.assertEqual(repr(r1.words), repr(r2.words))
        # and the made-up recording itself is the same twice
        c2 = synth(seed=5, n_words=60, pieces="captions")
        self.assertTrue(np.array_equal(case.envelope, c2.envelope))
        self.assertEqual(case.pieces, c2.pieces)


@needs_numpy
class NothingBreaksIt(unittest.TestCase):
    """SPEC.md's edge cases: an answer every time."""

    TEXT = "Hello everyone. Today we are going to discuss, at length, the matter of words."

    def both(self, env, D, text=TEXT, **kw):
        res = W.align_transcript_to_waveform(env, D, text, **kw)
        check_words(self, res.words, D)
        texts = [t for t in text.split(". ")] if isinstance(text, str) else text
        for kind in ("span", "point"):
            check_pieces(self, W.estimate_pieces(env, D, texts, kind, **kw), D, texts, kind)
        return res

    def test_garbage_and_flat_envelopes(self):
        for env in ([], [0.0] * 500, [0.3] * 500, [5.0] * 10,
                    [math.nan, math.inf, -1.0, 0.5, None, "x"] * 50, [math.nan] * 30):
            with self.subTest(env=str(env)[:30]):
                res = self.both(env, 10.0)
                self.assertEqual(len(res.words), 14)
                self.assertLess(res.global_confidence, 0.3)
                self.assertEqual(res.diagnostics["evidence"], 0.0)

    def test_noise_alone(self):
        rng = np.random.default_rng(0)
        res = self.both(np.abs(rng.normal(size=1000)), 10.0)
        clean = synth(seed=0, n_words=14)
        good = W.align_transcript_to_waveform(clean.envelope, clean.duration, clean.transcript)
        self.assertLess(res.global_confidence, good.global_confidence)

    def test_extremely_sparse(self):
        self.both([0.1, 0.9], 10.0)
        self.both([0.4], 3.0)
        case = synth(seed=2, n_words=40, rate=1.0)
        self.both(case.envelope, case.duration, case.transcript)

    def test_one_word_and_short_recordings(self):
        rng = np.random.default_rng(1)
        res = self.both(np.abs(rng.normal(size=1000)), 10.0, "Hello")
        self.assertEqual(len(res.words), 1)
        self.both([0.2, 0.8, 0.3], 0.05)
        self.both([0.2] * 4, 0.1, "Hello")

    def test_transcript_far_too_long_or_too_short(self):
        rng = np.random.default_rng(2)
        t = time.perf_counter()
        res = self.both(np.abs(rng.normal(size=500)), 5.0, " ".join(["word"] * 1000))
        self.assertEqual(len(res.words), 1000)
        self.assertLess(time.perf_counter() - t, 10.0)
        case = synth(seed=1, n_words=60)
        res = self.both(case.envelope, case.duration, "two words")
        self.assertEqual(len(res.words), 2)

    def test_empty_and_punctuation_only(self):
        res = W.align_transcript_to_waveform([0.3] * 100, 2.0, "")
        self.assertEqual(res.words, [])
        res = W.align_transcript_to_waveform([0.3] * 100, 2.0, "  \n\n ")
        self.assertEqual(res.words, [])
        res = self.both([0.3] * 100, 2.0, "... !!! ,")
        self.assertEqual(len(res.words), 1)

    def test_sample_times(self):
        case = synth(seed=4, n_words=40)
        n = case.envelope.size
        uniform = (np.arange(n) + 0.5) * case.duration / n
        a = W.align_transcript_to_waveform(case.envelope, case.duration, case.transcript)
        b = W.align_transcript_to_waveform(case.envelope, case.duration, case.transcript,
                                           sample_times=uniform)
        self.assertEqual(repr(a.words), repr(b.words))
        # shuffled, uneven, with holes, some outside the stretch
        rng = np.random.default_rng(4)
        keep = np.sort(rng.choice(n, n // 3, replace=False))
        t = uniform[keep] + rng.uniform(-0.004, 0.004, keep.size)
        order = rng.permutation(keep.size)
        t[order[:3]] = [-1.0, case.duration + 5, math.nan]
        self.both(case.envelope[keep][order], case.duration, case.transcript, sample_times=t[order])
        self.both(case.envelope, case.duration, case.transcript, sample_times=[math.nan] * n)

    def test_what_is_refused(self):
        for bad in (0, -1.0, math.nan, math.inf, "x", None):
            with self.assertRaises(ValueError):
                W.estimate_pieces([0.1] * 10, bad, ["a"])
            with self.assertRaises(ValueError):
                W.align_transcript_to_waveform([0.1] * 10, bad, "a")
        for none in ([], None, ()):
            with self.assertRaises(ValueError):
                W.estimate_pieces([0.1] * 10, 1.0, none)
        self.assertEqual(W.estimate_pieces("not a list", 1.0, ["a"])["pieces"][0]["t0"], 0.0)

    def test_numbers_too_big_for_a_float(self):
        # a JSON integer of four hundred digits is a Python int no float can
        # hold: in the envelope or the times it is garbage, survived like
        # NaN; as the duration it is refused like any other non-number
        huge = 10 ** 400
        texts = ["Hello there.", "Goodbye."]
        for kind in ("span", "point"):
            check_pieces(self, W.estimate_pieces([huge, 0.1, 0.5, 0.2] * 20, 5.0, texts, kind),
                         5.0, texts, kind)
            check_pieces(self, W.estimate_pieces([0.5, 0.1, 0.4], 5.0, texts, kind,
                                                 sample_times=[0.0, huge, 1.0]), 5.0, texts, kind)
        check_words(self, W.align_transcript_to_waveform([huge, 0.1] * 30, 5.0, "a b c").words, 5.0)
        with self.assertRaises(ValueError):
            W.estimate_pieces([0.1] * 10, huge, texts)
        with self.assertRaises(ValueError):
            W.align_transcript_to_waveform([0.1] * 10, huge, "a b")

    def test_a_stretch_too_short_or_barely_long_enough(self):
        # below a microsecond there is no answer that keeps its times in
        # order inside the stretch: refused, in words.  Just above it, an
        # answer -- and not the gigabytes a window of 20 ms measured in
        # frames of a nanosecond once asked for
        import tracemalloc
        texts = ["Hello everyone.", "Today we talk."]
        for D in (1e-7, 1e-9, 1e-13, 5e-324):
            with self.assertRaises(ValueError) as cm:
                W.estimate_pieces([0.2, 0.8, 0.1, 0.9], D, texts, "point")
            self.assertIn("too short", str(cm.exception))
        tracemalloc.start()
        try:
            for D in (1e-6, 3e-6, 1e-4, 0.01):
                for kind in ("span", "point"):
                    for tx in (texts, ["w%d" % i for i in range(500)]):
                        est = W.estimate_pieces([0.2, 0.8, 0.1, 0.9], D, tx, kind)
                        check_pieces(self, est, D, tx, kind)
                check_words(self, W.align_transcript_to_waveform([0.2, 0.8, 0.1, 0.9], D,
                                                                 "Hello everyone. Today.").words, D)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertLess(peak, 100 * 2 ** 20, "%d MB" % (peak >> 20))


@needs_numpy
class Silence(unittest.TestCase):
    """Leading, trailing and inner silence is left to nobody."""

    def test_a_long_pause_is_an_unassigned_gap(self):
        case = synth(seed=6, n_words=40, lead=3.0, trail=4.0, sentence_pause_prob=1.0,
                     sentence_pause=(1.8, 2.2))
        res = W.align_transcript_to_waveform(case.envelope, case.duration, case.transcript)
        ws = np.array([w.start for w in res.words])
        we = np.array([w.end for w in res.words])
        self.assertLess(abs(ws[0] - case.starts[0]), 0.1)
        self.assertLess(abs(we[-1] - case.ends[-1]), 0.1)
        long_gaps = np.flatnonzero(case.starts[1:] - case.ends[:-1] >= 1.5)
        self.assertTrue(long_gaps.size)
        for g in long_gaps:
            self.assertLess(abs(we[g] - case.ends[g]), 0.1)
            self.assertLess(abs(ws[g + 1] - case.starts[g + 1]), 0.1)
        roles = {p.role for p in res.pauses}
        self.assertIn("leading", roles)
        self.assertIn("trailing", roles)
        self.assertIn("sentence", roles)
        # the pieces: the leading silence belongs to the first, the
        # trailing silence to nobody
        est = W.estimate_pieces(case.envelope, case.duration, case.pieces, "span")
        self.assertEqual(est["pieces"][0]["t0"], 0.0)
        self.assertLess(est["pieces"][-1]["t1"], case.duration - 3.0)

    def test_a_stretch_silent_but_for_its_ends(self):
        # a recorded picture whose middle was lost (every lost number a
        # zero): sixty sentences, and sound only in the first and last three
        # seconds.  No candidate is left inside a pause, so there are fewer
        # places than boundaries -- and the bands once ran into negative
        # indices and raised IndexError
        rng = np.random.default_rng(0)
        D = 100.0
        t = (np.arange(int(D * 100)) + 0.5) / 100
        env = 0.3 + 0.3 * np.abs(np.sin(np.pi * 5 * t)) * (rng.random(t.size) > 0.1)
        env[(t > 3) & (t < 97)] = 0.001
        texts = ["This is sentence number %d, read at an ordinary pace." % i for i in range(60)]
        for kind in ("span", "point"):
            check_pieces(self, W.estimate_pieces(env, D, texts, kind), D, texts, kind)
        res = W.align_transcript_to_waveform(env, D, " ".join(texts))
        check_words(self, res.words, D)

    def test_a_long_silence_keeps_the_sentence_level(self):
        # an hour whose middle half is silent (a recorded picture that lost
        # it), a hundred captions: the beam loses every path in the widest
        # band -- and the narrower band's answer, feasible though it touched
        # its edge, was thrown away with it, so the sentence level was lost
        # and the words took a minute to find their way alone
        rng = np.random.default_rng(0)
        D, rate = 3600.0, 20
        n = int(D * rate)
        t = (np.arange(n) + 0.5) / rate
        syl = 0.5 + 0.5 * np.abs(np.sin(np.pi * 5 * t + rng.normal(0, 0.3, n).cumsum() * 0.01))
        env = 0.3 * syl * np.exp(rng.normal(0, 0.1, n))
        k = 0.0
        while k < D:
            k += rng.exponential(2.0)
            env[int(k * rate):int((k + rng.uniform(0.15, 0.8)) * rate)] = 0.002
        env = env + 0.001 * rng.random(n)
        env[n // 4:n // 4 + n // 2] = 0.001
        texts = ["caption %d is said here." % i for i in range(100)]
        res, _, _ = W._align_with_internals(env, D, texts, piece_strength=0.5)
        self.assertIn("units", [lv[0] for lv in res.diagnostics["levels"]])
        self.assertNotIn("units", res.diagnostics.get("relaxed", []))
        check_words(self, res.words, D)

    def test_what_comes_out_stays_inside_the_stretch(self):
        # a region ends at a frame's edge, k / rate with rate = frames / D,
        # which may round one ulp past D; and the last end of a book's
        # piece, after the least-squares projection, likewise
        D = 3741.554463064515
        res = W.align_transcript_to_waveform([0.5] * 10, D, "hello world")
        for a, b in res.speech_regions:
            self.assertTrue(0.0 <= a < b <= D, (a, b, D))
        # a duration where (D - off) + off > D, and pieces short enough for
        # the projection to run and pin the last end at the top
        texts = ["a"] * 9 + [" ".join(["word"] * 200)]
        N = len(texts)
        for k in range(20000):
            D = 3.0 + k * 0.0137
            need = min(0.4, D / N * 0.5) * (1 + 1e-9) + 1e-12
            if (D - N * need) + N * need > D:
                break
        self.assertGreater((D - N * need) + N * need, D, "a duration that rounds up")
        for env in ([0.4] * 50, np.abs(np.sin(np.arange(int(D * 100)) / 7.0))):
            est = W.estimate_pieces(env, D, texts, "span")
            check_pieces(self, est, D, texts, "span")
            self.assertLessEqual(est["pieces"][-1]["t1"], D)

    def test_speech_regions_and_candidates(self):
        case = synth(seed=7, n_words=30, paragraph_pause=(1.5, 2.0))
        o = W.AlignmentOptions(keep_candidates=True)
        res = W.align_transcript_to_waveform(case.envelope, case.duration, case.transcript,
                                             options=o)
        self.assertGreaterEqual(len(res.speech_regions), 2)
        for a, b in res.speech_regions:
            self.assertTrue(0 <= a < b <= case.duration)
        kinds = {c.kind for c in res.candidates}
        self.assertTrue({"pause", "valley", "fallback", "edge"} <= kinds, kinds)
        classes = {c.cls for c in res.candidates}
        self.assertTrue(classes & {"short pause", "phrase pause", "long pause"})
        self.assertTrue(classes & {"weak valley", "possible word boundary"})
        for c in res.candidates:
            self.assertLessEqual(c.left, c.right)


@needs_numpy
class ConfidenceAndUncertainty(unittest.TestCase):

    def test_a_pause_is_surer_than_the_middle_of_speech(self):
        case = synth(seed=8, n_words=120)
        res = W.align_transcript_to_waveform(case.envelope, case.duration, case.transcript)
        conf = res.diagnostics["boundary_confidence"][1:-1]
        on_pause = res.diagnostics["boundary_is_pause"][1:-1]
        self.assertTrue(on_pause.any() and (~on_pause).any())
        self.assertGreater(conf[on_pause].mean(), conf[~on_pause].mean() + 0.1)
        # an envelope that shows nothing: the confidence of the text alone
        flat = W.align_transcript_to_waveform([0.5] * 5000, case.duration, case.transcript)
        self.assertLess(flat.global_confidence, res.global_confidence - 0.2)

    def test_a_sure_piece_boundary_is_seldom_wrong(self):
        # the sentence level's own margins (the backward beam): a boundary a
        # whole sentence off must not come out confident.  Measured: none of
        # 26 boundaries at 0.8 or above was off by more than 0.25 s, and the
        # interval held the true silence 97 % of the time.
        sure = wrong_and_sure = covered = total = 0
        for scenario in ("loose lengths", "no pauses", "clean"):
            for seed in range(3):
                case = synth(seed=seed, **lab.SCENARIOS[scenario][1])
                est = W.estimate_pieces(case.envelope, case.duration, case.pieces, "span")
                first, last = case.piece_first, case.piece_last
                for i, p in enumerate(est["pieces"][1:], 1):
                    lo, hi = case.ends[last[i - 1]], case.starts[first[i]]
                    err = max(0.0, lo - p["t0"], p["t0"] - hi)
                    total += 1
                    covered += p["t0_min"] <= hi + 0.05 and p["t0_max"] >= lo - 0.05
                    if p["confidence"] >= 0.8:
                        sure += 1
                        wrong_and_sure += err > 0.25
        self.assertGreater(sure, 10)
        self.assertLessEqual(wrong_and_sure, max(1, sure // 20))
        self.assertGreater(covered / total, 0.9)

    def test_a_refinement_that_fails_is_not_surer(self):
        # when the refinement finds no way through, the coarse path stands --
        # and what the refinement would have measured is taken from the
        # coarse pass, or counts as a half; left at their best, these made
        # the case with the fewest checks the surest one (0.37 -> 0.56)
        case = synth(seed=1, n_words=120, **lab.SCENARIOS["no pauses"][1])
        normal = W.align_transcript_to_waveform(case.envelope, case.duration, case.transcript)
        orig = W._Engine._solve

        def no_refinement(self, *a, **k):
            return None if k.get("name") == "refine" else orig(self, *a, **k)
        W._Engine._solve = no_refinement
        try:
            failed = W.align_transcript_to_waveform(case.envelope, case.duration, case.transcript)
        finally:
            W._Engine._solve = orig
        self.assertTrue(failed.diagnostics.get("refine_failed"))
        self.assertNotIn("refine_failed", normal.diagnostics)
        check_words(self, failed.words, case.duration)
        self.assertLessEqual(failed.global_confidence, normal.global_confidence + 0.02)
        # the intervals are the coarse pass's near-optimal ones, not a point
        width = np.array([w.start_max - w.start_min for w in failed.words])
        self.assertGreater(float(np.median(width)), 0.05)
        # and the margins are measured, not every one the default of 10
        self.assertFalse(bool(np.all(failed.diagnostics["boundary_margin"] == 10.0)))

    def test_the_stability_test_shakes_every_prior(self):
        # the perturbation once shifted alpha alone, which only "power" reads:
        # under the others the weights came back unshaken
        text = ["a bb ccc dddd eeeeeeeeee ffffffffffffffffffff g"]
        for prior in ("power", "linear", "sqrt", "affine"):
            o = W.AlignmentOptions(duration_prior=prior)
            ta = W.TranscriptAnalyzer(o)
            model = ta.analyze(text)
            w, w2 = model.weights, ta.shaken(model)
            with self.subTest(prior=prior):
                self.assertAlmostEqual(float(w2.sum()), float(w.sum()))
                ratio = w2 / w
                self.assertGreater(float(ratio.max() - ratio.min()), 0.05)
                # a long word gains on a short one
                self.assertGreater(ratio[5], ratio[1])

    def test_uncertainty_is_wider_where_the_sound_says_less(self):
        case = synth(seed=9, n_words=120)
        res = W.align_transcript_to_waveform(case.envelope, case.duration, case.transcript)
        on_pause = res.diagnostics["boundary_is_pause"]
        width = np.array([w.start_max - w.start_min for w in res.words])
        self.assertLess(np.median(width[on_pause[:-1]]), np.median(width[~on_pause[:-1]]))


@needs_numpy
class EveryLanguage(unittest.TestCase):
    """Each language aligned, and better than by the text; the vowel marks
    of Persian and Arabic change nothing."""

    def test_harakat_change_nothing(self):
        marks = "\u064e\u0650\u064f\u0652\u0651"      # fatha kasra damma sukun shadda
        for lang in ("fa", "ar"):
            bare = synth(seed=10, language=lang, n_words=60)
            # the same pieces, vowelled: a mark after every other letter
            marked, k = [], 0
            for text in bare.pieces:
                out = ""
                for ch in text:
                    out += ch
                    if ch.isalpha():
                        k += 1
                        if k % 2:
                            out += marks[k % len(marks)]
                marked.append(out)
            self.assertNotEqual(marked, bare.pieces)
            # the same sound: the marks write vowels the bare text leaves out,
            # they do not make it longer
            a = W.estimate_pieces(bare.envelope, bare.duration, bare.pieces, "span")
            b = W.estimate_pieces(bare.envelope, bare.duration, marked, "span")
            self.assertEqual(json.dumps(a), json.dumps(b))

    def test_languages(self):
        for lang, n in (("en", 100), ("fa", 100), ("ar", 100), ("hi", 100), ("ja", 220),
                        ("zh", 220)):
            with self.subTest(lang=lang):
                case = synth(seed=11, language=lang, n_words=n, harakat=lang == "fa")
                r = lab.evaluate(case)
                self.assertLess(r["new_pieces"]["mean"], 0.1)
                self.assertLessEqual(r["new_pieces"]["mean"], 0.5 * r["old_pieces"]["mean"])
                self.assertLess(r["new_words"]["median"], 0.1)
                self.assertLess(r["new_words"]["mean"], 0.5 * r["old_words"]["mean"])


@needs_numpy
class BetterThanByTheText(unittest.TestCase):
    """The bench's scenarios, with thresholds set from what was measured
    (docs/wavealign.md) and a margin -- these guard against a regression,
    they are not the measure itself."""

    # scenario: (words mean <, pieces mean <), over seeds 0 and 1, 120 words
    LIMITS = {"clean": (0.15, 0.05), "noisy": (0.2, 0.05), "20 Hz": (0.2, 0.05),
              "5 Hz": (0.35, 0.1), "rate jump": (0.3, 0.15), "rms": (0.15, 0.05),
              "no pauses": (0.5, 0.4), "loose lengths": (1.3, 0.8), "captions": (0.15, 0.3),
              # a reader who stops for breath after plain words, and one whose
              # sentence ends are all shorter than a phrase pause (the split
              # calibration's trade-off, docs/wavealign.md section 8)
              "hesitations": (0.4, 0.3), "fast reader": (0.3, 0.15)}

    def test_scenarios(self):
        res = lab.run_bench(list(self.LIMITS), seeds=(0, 1), verbose=False)
        for name, (wl, pl) in self.LIMITS.items():
            r = res[name]
            with self.subTest(scenario=name):
                self.assertLess(r["new_words"]["mean"], wl)
                self.assertLess(r["new_pieces"]["mean"], pl)
                # the new beats the old on the pieces -- by far where the
                # envelope has its pauses
                self.assertLess(r["new_pieces"]["mean"], r["old_pieces"]["mean"])
                self.assertLess(r["new_words"]["mean"], r["old_words"]["mean"])
                if name not in ("no pauses", "loose lengths", "captions"):
                    self.assertLess(r["new_pieces"]["mean"], 0.25 * r["old_pieces"]["mean"])

    def test_nothing_to_hear_is_about_the_text(self):
        # no evidence -- a flat line, a muted recording, nothing at all: the
        # answer IS the proportional one over the words' weights, every
        # piece start within a frame of it; the beam, left to the durations
        # alone, once reshaped it and landed worse than the text it began from
        o = W.AlignmentOptions()
        for seed in range(12, 18):
            case = synth(seed=seed, n_words=80, pieces="captions")
            for env in (np.full(case.envelope.size, 0.4), np.zeros(case.envelope.size)):
                for kind in ("point", "span"):
                    est = W.estimate_pieces(env, case.duration, case.pieces, kind)
                    check_pieces(self, est, case.duration, case.pieces, kind)
                    model = W.TranscriptAnalyzer(o).analyze(
                        case.pieces, o.piece_strength_point if kind == "point" else o.piece_strength_span)
                    cw = np.concatenate([[0.0], np.cumsum(model.weights)])
                    want = case.duration * cw / cw[-1]
                    firsts = [int(np.flatnonzero(model.piece == p)[0]) for p in range(len(case.pieces))]
                    got = np.array([p["t0"] for p in est["pieces"]])
                    self.assertLess(float(np.max(np.abs(got - want[firsts]))), 1.0 / o.frame_rate,
                                    (seed, kind))
                    self.assertLess(est["confidence"], 0.3)
                    self.assertEqual(est["anchored"], 0)

    def test_a_text_nobody_punctuated(self):
        # auto-captions as YouTube leaves them: no full stop, no comma, no
        # blank line, while the voice still pauses at every sentence end.  No
        # sentence level can be built from such a text, a plain word may be
        # followed by a sentence's pause, and a caption's end is no likelier
        # a pause than any other word's.  The limit: at most half again the
        # error of by the text, in English, Chinese and Persian, over three
        # hundred words and over a thousand (docs/wavealign.md, section 8;
        # it was up to five times, and grew with the length)
        names = ["bare en", "bare zh", "bare fa", "bare en 1000", "bare zh 1000", "bare fa 1000"]
        res = lab.run_bench(names, seeds=(0, 1), verbose=False)
        for name in names:
            r = res[name]
            with self.subTest(scenario=name):
                self.assertLess(r["new_pieces"]["mean"], 1.5 * r["old_pieces"]["mean"])
                self.assertLess(r["new_words"]["mean"], 1.5 * r["old_words"]["mean"])
        case = synth(seed=0, n_words=300, pieces="captions", bare=True)
        self.assertFalse(any(ch in case.transcript for ch in ".,?\n"))
        res = W.align_transcript_to_waveform(case.envelope, case.duration, case.transcript)
        self.assertTrue(res.diagnostics["units_skipped"] and res.diagnostics["bare_text"])
        # and a punctuated text is never taken for one
        case = synth(seed=0, n_words=300, pieces="captions")
        res = W.align_transcript_to_waveform(case.envelope, case.duration, case.transcript)
        self.assertFalse(res.diagnostics["units_skipped"] or res.diagnostics["bare_text"])


@needs_numpy
class FastEnough(unittest.TestCase):

    def test_a_quarter_of_an_hour(self):
        case = synth(seed=0, n_words=2500, fine_rate=500.0)
        self.assertGreater(case.duration, 900)
        t = time.perf_counter()
        est = W.estimate_pieces(case.envelope, case.duration, case.pieces, "span")
        dt = time.perf_counter() - t
        # ~1 s here unloaded; the contract's hour is 10 s -- this leaves
        # room for a busy machine
        self.assertLess(dt, 8.0)
        self.assertLess(lab.piece_metrics(est["pieces"], case)["mean"], 0.1)


@needs_numpy
class Lean(unittest.TestCase):
    """Stretches that once took gigabytes or minutes, within the doors'
    limits (twelve hours, twenty thousand pieces): the peak of what NumPy and
    Python allocate, measured as it happens."""

    @staticmethod
    def speechlike(D, rate=100, seed=0):
        """Syllables five a second, and a pause of 0.15-0.8 s every two
        seconds or so."""
        rng = np.random.default_rng(seed)
        n = int(round(D * rate))
        t = (np.arange(n) + 0.5) / rate
        env = 0.3 * (0.5 + 0.5 * np.abs(np.sin(np.pi * 5 * t))) * np.exp(rng.normal(0, 0.1, n))
        k = 0.0
        while k < D:
            k += rng.exponential(2.0)
            env[int(k * rate):int((k + rng.uniform(0.15, 0.8)) * rate)] = 0.002
        return env + 0.001 * rng.random(n)

    def peak(self, *a, **k):
        import tracemalloc
        tracemalloc.start()
        try:
            t = time.perf_counter()
            est = W.estimate_pieces(*a, **k)
            dt = time.perf_counter() - t
            peak = tracemalloc.get_traced_memory()[1] >> 20
        finally:
            tracemalloc.stop()
        check_pieces(self, est, a[1], a[2], a[3])
        return est, peak, dt

    def test_two_captions_left_over_two_hours(self):
        # every pause of two hours was a candidate for two words, and the
        # word pass's cost matrix grew as their number squared: 356 MB then,
        # quadratic in the hours
        _, peak, _ = self.peak(self.speechlike(7200.0), 7200.0, ["Thank you.", "Goodbye."], "point")
        self.assertLess(peak, 200, "%d MB" % peak)

    def test_three_captions_over_two_hours(self):
        # the sentence level's first boundary kept every candidate of a band
        # of minutes, unpruned: 636 MB then, 2.4 GB for four hours
        texts = ["caption %d is said here." % i for i in range(3)]
        _, peak, _ = self.peak(self.speechlike(7200.0, rate=20), 7200.0, texts, "point")
        self.assertLess(peak, 400, "%d MB" % peak)

    def test_four_thousand_pieces_in_a_minute(self):
        # far more words than any voice says in the time: the proportional
        # answer at once, where the DP took a minute and gigabytes growing
        # as the words squared
        texts = ["w%d." % i for i in range(4000)]
        _, peak, dt = self.peak(np.tile([0.5, 0.1, 0.9], 2000), 60.0, texts, "span")
        self.assertLess(dt, 5.0)
        self.assertLess(peak, 100, "%d MB" % peak)


@needs_numpy
class TheLab(unittest.TestCase):

    def test_by_the_text_is_spread_rest(self):
        # lib/timeline.js sizeOf: marks stripped, spaces out, never under 1
        self.assertEqual(lab._size_of("سَلام دُنیا"), lab._size_of("سلام دنیا"))
        self.assertEqual(lab._size_of("a b"), 2)
        self.assertEqual(lab._size_of(""), 1)
        self.assertEqual(lab._size_of("𠀀"), 2)          # UTF-16, as JavaScript counts
        p = lab.by_the_text(["aaaa", "b", "cccccc", "x"], 10.0)
        self.assertEqual([round(x["t0"], 9) for x in p], [0.0, 3.333333333, 4.166666667, 9.166666667])
        self.assertEqual(p[-1]["t1"], 10.0)
        p = lab.by_the_text(["a", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"], 10.0)
        self.assertAlmostEqual(p[0]["t1"], 0.4)          # the floor

    def test_metrics(self):
        case = synth(seed=1, n_words=20)
        m = lab.word_metrics(case.starts, case.ends, case)
        self.assertEqual((m["mean"], m["w50"], m["sentence"]), (0.0, 100.0, 0.0))
        m = lab.word_metrics(case.starts + 0.2, case.ends + 0.2, case)
        self.assertAlmostEqual(m["mean"], 0.2)
        self.assertEqual((m["w100"], m["w250"]), (0.0, 100.0))

    def test_the_drawing(self):
        case = synth(seed=2, n_words=25)
        with tempfile.TemporaryDirectory() as d:
            out = lab.plot_alignment(os.path.join(d, "a.svg"), case.envelope, case.duration,
                                     case.transcript, truth=case)
            root = ET.parse(out).getroot()
            self.assertTrue(root.tag.endswith("svg"))
            with open(out, encoding="utf-8") as f:
                text = f.read()
            for tok in case.tokens[:5]:
                self.assertIn(tok, text)
            self.assertIn("polyline", text)
            self.assertIn("not recognition", text)

    def test_demo(self):
        out = lab.demo(seed=4, n_words=12)
        self.assertIn("WORD", out)
        self.assertIn("CONFIDENCE", out)
        self.assertEqual(len([ln for ln in out.splitlines() if ln[:1].isalpha() and "." in ln]), 12)


@needs_numpy
class WhatRealSpeechTaught(unittest.TestCase):
    """What the Kokoro bench (real speech in seven languages, cut by the
    sound itself -- docs/wavealign.md, section 8) found wrong, each held
    here on made-up sound so that it stays fixed."""

    def test_the_pace_step_is_exact(self):
        # the pace between the one before and this unit's own rate: the
        # least of Huber(x - m; a) + Huber(rho - x; b), found without a search
        rng = np.random.default_rng(0)
        grid = np.linspace(-3, 3, 30001)
        for a, b in ((0.07, 0.16), (0.3, 0.1), (0.1, 0.1)):
            rho = rng.normal(0, 0.6, 60)
            m = rng.normal(0, 0.3, 60)
            x, cp, cu = W._pace_step(rho, m, a, b, 1.0)
            for k in range(60):
                f = W._huber(grid - m[k], a, 1.0) + W._huber(rho[k] - grid, b, 1.0)
                self.assertAlmostEqual(cp[k] + cu[k], float(f.min()), places=4)
                self.assertTrue(min(m[k], rho[k]) - 1e-9 <= x[k] <= max(m[k], rho[k]) + 1e-9)

    def test_the_beam_is_local_in_time(self):
        # a state that has read the text too fast stands early and looks
        # cheap; it must not push the states later in time out of the beam
        o = W.AlignmentOptions()
        dp = W.DynamicProgrammingAligner(o, 1.0)
        L = np.arange(100, dtype=float)                 # candidate j at j seconds
        cand = np.array([10, 11, 12, 40, 41, 42])
        cost = np.array([0.0, 1.0, 2.0, 20.0, 21.0, 22.0])
        kept = dp._prune(np.arange(6), cand, cost, L)
        self.assertEqual(kept.tolist(), [0, 1, 2, 3, 4, 5])
        # ... but one far behind the best of all is still dropped
        cost[3:] += 100.0
        self.assertEqual(dp._prune(np.arange(6), cand, cost, L).tolist(), [0, 1, 2])
        # and one place in time keeps only its best few rates
        cand = np.full(6, 10)
        kept = dp._prune(np.arange(6), cand, np.arange(6.0), L)
        self.assertEqual(kept.tolist(), list(range(o.rate_per_candidate)))

    @staticmethod
    def _bed(seed=0):
        """Speech under a bed of music: syllables five a second whose dips
        sink to the bed for 60-130 ms, and between sentences a pause of
        0.7 s at the same level -- by loudness alone the dips are pauses."""
        rng = np.random.default_rng(seed)
        texts, env, t = [], [], 0.0
        starts = []
        for s in range(8):
            words = ["word%d" % k for k in range(int(rng.integers(8, 13)))]
            texts.append(" ".join(words) + ".")
            starts.append(t)
            for _ in range(len(words) * 2):              # two syllables a word
                n_on = int(rng.integers(10, 16))
                env += list(0.5 + 0.3 * rng.random(n_on))
                n_off = int(rng.integers(6, 14))
                env += list(0.05 + 0.01 * rng.random(n_off))
                t += (n_on + n_off) / 100.0
            if s < 7:
                env += list(0.05 + 0.01 * rng.random(70))
                t += 0.7
        return np.array(env), t, texts, starts

    def test_dips_under_a_bed_are_not_pauses(self):
        env, D, texts, starts = self._bed()
        o = W.AlignmentOptions()
        sig, act, det = W.analyze_waveform(env, D, options=o)
        model = W.TranscriptAnalyzer(o).analyze(texts, o.piece_strength_span)
        eng = W._Engine(o)
        act2, det2, dip = eng._dip_length(model, sig, act, det)
        self.assertGreater(dip, 0.1)
        inner = det2.p_role == 0
        short = inner & (det2.p_dur < 0.2)
        longp = inner & (det2.p_dur > 0.6)
        self.assertTrue(short.sum() > 50 and longp.sum() == 7)
        # as anchors the hundred dips were worth several pauses between
        # them; now next to nothing
        self.assertGreater(float(det.p_anchor[short].sum()), 3.0)
        self.assertLess(float(det2.p_anchor[short].sum()), 0.3)
        self.assertGreater(float(det2.p_anchor[longp].min()), 0.5)
        # the dips count as speaking time, the pauses do not
        self.assertGreater(act2.cum_speech[-1], act.cum_speech[-1] + 3.0)
        est = W.estimate_pieces(env, D, texts, "span")
        err = [abs(p["t0"] - s) for p, s in zip(est["pieces"][1:], starts[1:])]
        self.assertLess(max(err), 0.25)

    def test_the_reader_s_pauses_are_fitted_by_their_length(self):
        # one reader stops at every full stop and runs over the commas; the
        # other hardly stops at all: the same text, opposite priors
        o = W.AlignmentOptions()

        def fitted(**kw):
            case = synth(seed=3, n_words=160, **kw)
            sig, act, det = W.analyze_waveform(case.envelope, case.duration, options=o)
            model = W.TranscriptAnalyzer(o).analyze(case.pieces, o.piece_strength_span)
            eng = W._Engine(o)
            act, det, _ = eng._dip_length(model, sig, act, det)
            m2, _ = eng._calibrate(model, det)
            sent = model.level[:-1] >= W.BREAK_SENTENCE
            comma = model.level[:-1] == W.BREAK_COMMA
            return float(m2.prior[:-1][sent].mean()), float(m2.prior[:-1][comma].mean())

        s1, c1 = fitted(comma_pause_prob=0.0, sentence_pause_prob=1.0, stray_pause_prob=0.0)
        s2, c2 = fitted(comma_pause_prob=0.1, sentence_pause_prob=0.2,
                        sentence_pause=(0.12, 0.2), stray_pause_prob=0.0)
        self.assertGreater(s1, 0.8)
        self.assertLess(c1, 0.3)
        self.assertLess(s2, 0.6)

    def test_a_hesitation_after_a_plain_word_is_dear_not_impossible(self):
        # SPEC: "ordinary word + huge pause -> small penalty".  The length
        # term is capped, so a pause of seconds after a plain word costs at
        # most pause_length_cap more than a short one does
        o = W.AlignmentOptions()
        dp = W.DynamicProgrammingAligner(o, 1.0)
        short = float(dp._pause_prior(o.pause_prob_word, 1.0, 0.3, o.pause_length["word"]))
        for dur in (0.6, 1.0, 3.0, 30.0):
            long_ = float(dp._pause_prior(o.pause_prob_word, 1.0, dur, o.pause_length["word"]))
            self.assertLessEqual(long_ - short, o.pause_length_cap + 1e-9, dur)
        self.assertGreater(float(dp._pause_prior(o.pause_prob_word, 1.0, 1.0, 0.12)), short)
        # and on made-up readers who hesitate a second at a time, the pieces
        # land nearer than with the length uncapped
        errs = {}
        for cap in (math.inf, o.pause_length_cap):
            e = []
            for seed in range(6):
                case = synth(seed=seed, n_words=160, stray_pause_prob=0.03, stray_pause=(0.6, 1.2))
                est = W.estimate_pieces(case.envelope, case.duration, case.pieces, "span",
                                        options=W.AlignmentOptions(pause_length_cap=cap))
                e.append(lab.piece_metrics(est["pieces"], case)["mean"])
            errs[cap] = float(np.mean(e))
        self.assertLess(errs[o.pause_length_cap], errs[math.inf])

    def test_a_long_pause_suits_a_sentence_end(self):
        # a narrator's pause between paragraphs runs to seconds; it is where
        # the sentence ends, not a reason to look elsewhere
        o = W.AlignmentOptions()
        self.assertTrue(math.isinf(o.pause_length["sentence"]))
        for seed in (0, 1):
            case = synth(seed=seed, n_words=150, paragraph_pause=(2.0, 3.5),
                         sentence_pause=(0.4, 1.2))
            est = W.estimate_pieces(case.envelope, case.duration, case.pieces, "span")
            self.assertLess(lab.piece_metrics(est["pieces"], case)["mean"], 0.1)


@needs_numpy
class BenchAudio(unittest.TestCase):
    """`wavealign_lab.py bench-audio`: any recording whose cuts someone
    trusts, measured the way the Kokoro bench measures -- here a made-up one
    read at a thousand a second, so no ffmpeg and no shelf is needed."""

    @staticmethod
    def _case():
        case = synth(seed=5, n_words=160, rate=1000.0, fine_rate=4000.0)
        first = [int(np.flatnonzero(case.piece_of == p)[0]) for p in range(len(case.pieces))]
        last = [int(np.flatnonzero(case.piece_of == p)[-1]) for p in range(len(case.pieces))]
        truth = {"texts": list(case.pieces), "t0": case.starts[first].copy(),
                 "t1": [float(case.ends[k]) for k in last], "kind": "span"}
        return case, truth

    def test_the_measure(self):
        case, truth = self._case()
        res = lab.bench_audio(truth, np.asarray(case.envelope, float), case.duration,
                              sizes=("3", "all"), per_size=3)
        for key in ("100 Hz, M=3", "100 Hz, M=all", "20 Hz, M=all"):
            self.assertIn(key, res["by"])
        a = res["all"]
        self.assertLess(a["sound"]["mean"], a["text"]["mean"])
        self.assertLess(a["sound"]["gap"], 0.05)
        self.assertGreater(a["sound_better_pct"], 50)
        self.assertIn("everything", lab.format_bench_audio(res))

    def test_the_command(self):
        import contextlib
        import io
        case, truth = self._case()
        with tempfile.TemporaryDirectory() as d:
            tj = os.path.join(d, "truth.json")
            with open(tj, "w", encoding="utf-8") as f:
                json.dump([{"text": t, "start": float(a), "end": b}
                           for t, a, b in zip(truth["texts"], truth["t0"], truth["t1"])], f)
            back = lab.load_truth(tj)
            self.assertEqual(back["kind"], "span")
            self.assertEqual(back["texts"], truth["texts"])
            wj = os.path.join(d, "waveform.json")
            with open(wj, "w", encoding="utf-8") as f:
                json.dump({"rate": 20, "peaks": lab._picture20(np.asarray(case.envelope)).tolist()}, f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(lab.main(["bench-audio", "-", tj, "--wave", wj,
                                           "--sizes", "10,all", "--per-size", "2",
                                           "--json", os.path.join(d, "r.json")]), 0)
            self.assertIn("20 Hz, M=all", out.getvalue())
            with open(os.path.join(d, "r.json"), encoding="utf-8") as f:
                self.assertIn("all", json.load(f))
            with open(tj, "w", encoding="utf-8") as f:
                json.dump([{"text": "one"}], f)
            with self.assertRaises(ValueError):
                lab.load_truth(tj)


if __name__ == "__main__":
    unittest.main()
