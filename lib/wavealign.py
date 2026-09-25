#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""A known transcript laid over the picture of its sound -- and nothing else.

    import wavealign
    res = wavealign.align_transcript_to_waveform(peaks, 37.42, "Hello everyone. Today ...")
    for w in res.words:
        print(w.word, w.start, w.end, w.confidence)

    wavealign.estimate_pieces(peaks, 61.0, ["first caption", "second one"], "point")
    # -> {"pieces": [{"t0", "t1", "confidence", "t0_min", "t0_max", "speech"}, ...], ...}

THE LIMITATION, FIRST.  The only input is a waveform ENVELOPE: one amplitude
per bucket of time, the thing an audio editor draws.  It carries how loud the
sound was and when it went quiet; it does not carry what was said.  Nothing
here can know that a stretch of the envelope IS a particular word, and nothing
here tries: there is no audio, no spectrum, no recogniser, no phoneme model.
What comes out is the globally most plausible MONOTONIC SEGMENTATION of the
transcript through time given

    transcript structure + duration priors + waveform activity + pause structure

and it must never be mistaken for acoustic forced alignment.  Its confidence
is STRUCTURAL TIMING confidence -- how firmly the envelope pins a boundary
where it was put -- and never a probability that a word was recognised.

The question asked is not "which stretch sounds like this word?" (impossible
with this data) but "among all monotonic ways to spread this text through
time, which is most consistent with where the sound is, where it pauses, how
long the words are, where the punctuation is, and a speaking rate that
changes smoothly?"  The stages, each a class below:

    WaveformPreprocessor        garbage out, a uniform grid, a log (dB) curve,
                                normalised by percentiles, smoothed in seconds
    ActivityEstimator           Otsu split, hysteresis thresholds, a soft
                                activity likelihood, speech regions
    PauseDetector               pauses (runs below the low threshold, with two
                                edges each) and valleys (prominent minima)
    BoundaryCandidateGenerator  the places a boundary may go: pause OBJECTS,
                                valleys, edges, a fallback grid, the prior
    TranscriptAnalyzer          tokens (a callback), weights, break levels
    InitialDurationModel        a rate, expected durations, proportional
                                positions laid over the speech regions only
    HierarchicalAligner         units (sentences, pieces, phrases) -> words,
                                the words banded around the units
    DynamicProgrammingAligner   the monotonic DP over boundary objects: a
                                beam with the speaking pace in its state for
                                the units; banded, duration-limited, forward
                                and backward (min-marginals) for the words
    BoundaryRefiner             a finer search round each boundary, then the
                                DP again in a narrow band, until it settles
    ConfidenceEstimator         margin, uncertainty interval, evidence,
                                stability under perturbation, agreement --
                                with the sentence level's own margins, from
                                the beam run forwards and backwards

docs/wavealign.md is the description in prose: the cost terms, why a pause is
an object with two edges, the complexity, which parameters matter, and what
was measured.  lib/wavealign_lab.py holds the synthetic generator, the metrics,
the drawing and the bench.

NumPy only (SciPy is never needed).  Deterministic: no randomness, no
dependence on dict or set order, the same input gives the same output.
"""
from __future__ import annotations

import bisect
import math
import re
import time
import unicodedata
from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import Callable, Optional, Sequence

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

__all__ = [
    "AlignmentOptions", "WordAlignment", "Pause", "BoundaryCandidate",
    "AlignmentResult", "align_transcript_to_waveform", "estimate_pieces",
    "default_tokenize", "char_count", "punctuation_class", "analyze_waveform",
    "WaveformPreprocessor", "ActivityEstimator", "PauseDetector",
    "BoundaryCandidateGenerator", "TranscriptAnalyzer", "InitialDurationModel",
    "HierarchicalAligner", "DynamicProgrammingAligner", "BoundaryRefiner",
    "ConfidenceEstimator", "VERSION",
]

VERSION = "1"

# the textual break after a token, weakest to strongest
BREAK_WORD, BREAK_COMMA, BREAK_COLON, BREAK_SENTENCE, BREAK_PARAGRAPH = 0, 1, 2, 3, 4
BREAK_NAMES = ("word", "comma", "colon", "sentence", "paragraph")

# what a boundary candidate is
KIND_EDGE, KIND_PAUSE, KIND_VALLEY, KIND_REFINED, KIND_PRIOR, KIND_FALLBACK = range(6)
KIND_NAMES = ("edge", "pause", "valley", "refined", "prior", "fallback")
# who wins when two candidates fall on the same spot
_PRIORITY = np.array([6, 5, 4, 3, 2, 1], dtype=np.int8)

PAUSE_CLASSES = ("short pause", "phrase pause", "long pause")

_INF = np.inf


# =================================================================== options
@dataclass
class AlignmentOptions:
    """Every number the aligner uses.  The defaults are reasoned, not fitted to
    one recording; docs/wavealign.md says which of them matter most."""

    # -- the working grid.  The envelope is resampled onto a uniform grid of
    #    this many frames a second (peak per frame when it is finer, linear
    #    between samples when it is coarser); every duration below is in
    #    SECONDS, so the same options suit a 5 Hz and a 200 Hz envelope.
    frame_rate: float = 100.0
    median_s: float = 0.03          # median filter: removes one-frame spikes
    smooth_s: float = 0.02          # Gaussian sigma of the level curve
    floor_percentile: float = 5.0   # robust normalisation: floor ...
    ceil_percentile: float = 99.0   # ... and ceiling, both in the dB domain

    # -- activity.  Thresholds sit between the two classes Otsu finds, as
    #    fractions of the way from the noise level to the speech level.
    low_frac: float = 0.30          # stay active until below this
    high_frac: float = 0.50         # become active above this
    min_active_s: float = 0.04      # a burst shorter than this is a click
    evidence_db_lo: float = 6.0     # dynamic range (p5..p99) with no evidence
    evidence_db_hi: float = 18.0    # ... and with full evidence

    # -- pauses and valleys
    min_pause_s: float = 0.06       # shortest silence that is a pause
    phrase_pause_s: float = 0.25    # short pause < this <= phrase pause
    long_pause_s: float = 0.60      # phrase pause < this <= long pause
    region_gap_s: float = 0.35      # a silence this long splits speech regions
    pause_tau_s: float = 0.12       # duration scale of a pause's strength
    context_s: float = 0.25         # how far either side "context" reaches
    anchor_short_s: float = 0.08    # a pause shorter than this is no anchor
    anchor_full_s: float = 0.30     # ... one this long is a whole one
    swallow_length: float = 1.0     # a long pause swallowed inside a unit counts as more than one
    dip_rank: float = 2.0           # silences beyond this many times the pauses the
                                    # text expects are taken for dips (_dip_length)
    valley_window_s: float = 0.12   # prominence is measured this far each side
    valley_min_prominence: float = 0.05   # in normalised level units
    valley_full_prominence: float = 0.35

    # -- candidates.  The fallback grid guarantees the DP always has somewhere
    #    to put a boundary, even in an envelope with no valleys at all.
    fallback_step_s: float = 0.08
    unit_step_s: float = 0.5
    unit_valley_strength: float = 0.35
    min_separation_s: float = 0.015

    # -- the pause priors fitted to the reader (Engine._calibrate)
    calibrate_pauses: bool = True
    calibrate_mode: str = "split"   # split (long pauses vs strong breaks) | scale (see _calibrate)
    calibrate_floor: float = 0.15   # never scaled down further than this
    calibrate_full: float = 0.5     # a pause this plain counts as a whole one
    calibrate_prior: float = 4.0    # pauses' worth of doubt in the count
    calibrate_word_max: float = 0.3  # never more likely after a plain word

    # -- the transcript.  weight(word) = max(min_weight, prior(chars)).
    duration_prior: str = "power"   # power | linear | sqrt | affine
    alpha: float = 0.8              # the exponent of "power"
    min_weight: float = 1.0
    affine_constant: float = 2.0    # "affine": constant + per_char * chars
    affine_per_char: float = 1.0
    continua_weight: float = 2.0    # a Han/kana/Thai... character vs a letter
    empty_weight: float = 0.5       # an empty or punctuation-only piece
    # THE PAUSE PRIORS are probabilities: how likely a reader is to pause
    # after a plain word, a comma, a colon, a sentence, a paragraph.  They
    # are soft -- a sentence read straight on costs -log(1 - p), a pause
    # after a plain word -log(p_word) -- and never required.
    pause_prob_word: float = 0.04
    pause_prob_inside: float = 0.01     # ... and inside a word
    break_strength: dict = field(default_factory=lambda: {
        "comma": 0.45, "colon": 0.55, "sentence": 0.85, "paragraph": 0.95})
    piece_strength_span: float = 0.90   # a book's piece boundary
    piece_strength_point: float = 0.50  # a caption boundary
    # how long a pause each break is apt to have: beyond anchor_full_s, a
    # pause of g seconds is exp(-(g - anchor_full_s) / length) as likely --
    # so a whole second of silence belongs at a sentence or paragraph end,
    # hardly after a comma, and not after a plain word at all.  A sentence
    # end and a paragraph have no such limit: what follows them may be a
    # breath, a page turned, a chapter's silence; measured on real speech
    # (docs/wavealign.md, section 8), charging their long pauses drove
    # sentence ends off the very pauses that mark them.
    pause_length: dict = field(default_factory=lambda: {
        "word": 0.12, "comma": 0.25, "colon": 0.35, "sentence": math.inf, "paragraph": math.inf})
    # ... and never less likely than this many nats for its length.  THE
    # SPEC ASKS "a small penalty" for a plain word followed by a huge pause,
    # and uncapped the length made it a large one: a breath of a second
    # after a plain word cost some nine nats, so the DP would rather drag a
    # sentence end onto the hesitation, or read the words around it at an
    # absurd pace.  Capped, a pause after a plain word costs at most
    # -log(p_word) and this -- still dear, no longer impossible.  Measured
    # (docs/wavealign.md, sections 6 and 8): hesitating readers gain, real
    # speech moves by less than a thousandth of a second.
    pause_length_cap: float = 1.5

    # -- the cost weights (the lambdas of docs/wavealign.md).  Every term is
    #    in nats -- a negative log-likelihood, or something scaled like one --
    #    so a weight of 1 means "as the model says" and the terms can be
    #    weighed against each other by what they claim.
    w_duration: float = 1.0
    w_boundary: float = 1.0
    w_activity: float = 2.0
    w_rate: float = 1.0
    w_pause: float = 1.0
    w_anchor: float = 1.0
    w_smooth: float = 0.3
    w_unassigned: float = 1.5
    global_share: float = 0.3       # the global-rate term, once a local rate exists
    sigma_duration: float = 0.45    # log-ratio spread against the global rate
    sigma_rate: float = 0.35        # ... against the local rate curve
    sigma_smooth: float = 0.5       # ... against the neighbours' rate
    sigma_rate_variation: float = 0.25   # a unit's rate beyond word noise
    dmin_ratio: float = 0.2         # hard limits on a word's duration, as a
    dmax_ratio: float = 5.0         # multiple of its expected one ...
    dmax_extra_s: float = 0.6       # ... and never less than expected + this
    min_word_s: float = 0.03

    # -- hierarchy and bands (Sakoe-Chiba, around the level above)
    direct_max_words: int = 4       # this few words are aligned in one go
    min_units: int = 2              # ... and so are fewer sentences than this
    max_words_per_s: float = 20.0   # more tokens a second than this: the proportional guess
    bare_min_tokens: int = 40       # this many with no mark at all: a text nobody punctuated
    unit_max_s: float = 10.0
    unit_min_s: float = 1.5
    top_band_min_s: float = 20.0
    top_band_frac: float = 0.08
    word_band_min_s: float = 1.5
    word_band_frac: float = 0.25
    max_band_s: float = 60.0
    band_retries: int = 2

    # -- the local rate curve, re-estimated between passes
    rate_window_s: float = 6.0
    rate_short_s: float = 1.5
    rate_shrink: float = 0.2
    rate_clip: float = 3.0
    # -- the pace in the state of the sentence level's beam (solve_rated)
    rate_state: bool = True
    rate_q_max: float = 1.1         # log-rates from 1/3 to 3 times the global
    rate_q_step: float = 0.05
    rate_unit_sigma: float = 0.10   # what a sentence's own text does to its rate
    rate_huber: float = 1.0         # past this many sigmas a step costs linearly
    group_rate_trust: float = 0.12  # how far a group's own rate may pull from the curve
    rate_drift: float = 0.08        # the pace's own wander, per root second
    rate_global_sigma: float = 0.35  # the first unit's rate against the global
    rate_revert_s: float = 120.0    # how long the pace takes to forget itself
    w_rate_step: float = 1.0
    rate_latent: bool = True        # the state holds the pace, not the unit's own rate
                                    # (False: the older model, kept for comparison)
    rate_drift_min: float = 0.03    # the least a pace may move between two units (log)
    rate_jump_nats: float = 3.0     # a sudden change of pace: about one unit in twenty
    rate_jump_scale: float = 1.0    # ... and a nat for every unit of log-rate it jumps
    rate_beam: float = 8.0          # nats behind the best a state may fall ...
    rate_beam_states: int = 200     # ... and how many states survive a unit
    rate_per_candidate: int = 3     # ... and how many of them at one candidate
    rate_beam_window_s: float = 2.0  # the beam compares states this near in time
    rate_beam_global: float = 40.0  # ... and drops one this far behind the best of all

    # -- coarse to fine
    refine_passes: int = 1          # after the coarse word pass; more change nothing measured
    refine_window_s: float = 0.35
    refine_tol_s: float = 0.005
    perturb: bool = True

    # -- confidence and uncertainty
    uncertainty_cost: float = 1.0   # near-optimal = within this of the best
    unit_marginals: bool = True     # the sentence level's own margins (a backward beam)
    unit_uncertainty_cost: float = 2.0  # ... near-optimal there, in nats
    unit_marginal_states: int = 100     # ... and the backward beam's size
    margin_tol_s: float = 0.10      # "second best" must be further than this
    margin_scale: float = 2.0

    # -- estimate_pieces
    split_gap: float = 0.5
    pad: float = 0.1
    min_piece: float = 0.4

    # -- debugging: keep the candidate list on the result (the lab's plots)
    keep_candidates: bool = False


# ================================================================ the output
@dataclass
class WordAlignment:
    """One token's place in time.  `confidence` is structural timing
    confidence (0..1): how firmly the envelope supports these boundaries --
    NOT a probability that the word was recognised.  The four *_min/*_max
    numbers bound where near-optimal segmentations put the two edges."""
    word: str
    start: float
    end: float
    confidence: float
    start_min: float = 0.0
    start_max: float = 0.0
    end_min: float = 0.0
    end_max: float = 0.0


@dataclass
class Pause:
    """A silence the envelope shows.  `kind` is what it is by its sound
    (short / phrase / long pause); `role` is what the alignment made of it:
    leading, trailing, inter-word, phrase, sentence, paragraph, within-word."""
    start: float
    end: float
    duration: float
    strength: float
    kind: str
    role: str = ""


@dataclass
class BoundaryCandidate:
    """A place a boundary may go.  A pause has two edges (`left` = where the
    word before it may end, `right` = where the word after it may start); a
    valley or a grid point has both equal to `time`."""
    time: float
    strength: float
    duration: float
    local_minimum_energy: float
    context_energy: float
    kind: str = "valley"
    cls: str = ""
    left: float = 0.0
    right: float = 0.0


@dataclass
class AlignmentResult:
    words: list
    speech_regions: list
    pauses: list
    global_confidence: float
    diagnostics: dict
    candidates: list = field(default_factory=list)


# ============================================================ small helpers
def _as_float_array(x) -> np.ndarray:
    """Anything list-like as a 1-D float array; what will not convert is NaN
    -- a string, None, and an integer too big for a float alike."""
    if x is None:
        return np.zeros(0)
    try:
        a = np.asarray(x, dtype=float)
    except (TypeError, ValueError, OverflowError):
        out = []
        try:
            items = list(x)
        except TypeError:
            return np.zeros(0)
        for v in items:
            try:
                out.append(float(v))
            except (TypeError, ValueError, OverflowError):
                out.append(math.nan)
        a = np.asarray(out, dtype=float)
    return a.ravel() if a.ndim != 1 else a


def _runs(mask: np.ndarray):
    """Starts and (exclusive) ends of the True runs of a boolean array."""
    m = np.asarray(mask, dtype=bool)
    if m.size == 0:
        return np.zeros(0, np.intp), np.zeros(0, np.intp)
    d = np.diff(m.astype(np.int8), prepend=0, append=0)
    return np.flatnonzero(d == 1), np.flatnonzero(d == -1)


def _fill_runs(mask: np.ndarray, starts, ends, value: bool) -> np.ndarray:
    out = mask.copy()
    if len(starts):
        d = np.zeros(mask.size + 1, np.int32)
        np.add.at(d, starts, 1)
        np.add.at(d, ends, -1)
        out[np.cumsum(d[:-1]) > 0] = value
    return out


def _gauss(x: np.ndarray, sigma_frames: float) -> np.ndarray:
    if sigma_frames < 0.5 or x.size < 3:
        return x.copy()
    # never wider than the curve itself: a stretch of a millionth of a
    # second still has its sixteen frames, and a sigma of 20 ms is then
    # millions of them -- a kernel of that many would be gigabytes of
    # weights, all of them equal over a curve that short
    r = min(int(math.ceil(3 * min(sigma_frames, x.size))), x.size)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma_frames) ** 2)
    k /= k.sum()
    return np.convolve(np.pad(x, r, mode="edge"), k, mode="valid")


def _median(x: np.ndarray, width: int) -> np.ndarray:
    if width < 3 or x.size < width:
        return x.copy()
    h = width // 2
    return np.median(sliding_window_view(np.pad(x, h, mode="edge"), 2 * h + 1), axis=1)


def _side_max(x: np.ndarray, at: np.ndarray, w: int, side: str) -> np.ndarray:
    """max of x[k-w..k-1] (side 'left') or of x[k+1..k+w] ('right') for every
    k in `at`; what falls off the ends does not count."""
    w = max(1, min(int(w), x.size))       # beyond the curve there is nothing to see
    off = -np.arange(1, w + 1) if side == "left" else np.arange(1, w + 1)
    idx = at[:, None] + off[None, :]
    ok = (idx >= 0) & (idx < x.size)
    vals = np.where(ok, x[np.clip(idx, 0, x.size - 1)], -np.inf)
    out = vals.max(axis=1) if vals.size else np.full(at.size, -np.inf)
    return np.where(np.isfinite(out), out, x[at])


def _otsu(x: np.ndarray, bins: int = 128):
    """Otsu's split of values in [0, 1]: the threshold and the two class means."""
    h, edges = np.histogram(np.clip(x, 0, 1), bins=bins, range=(0.0, 1.0))
    h = h.astype(float)
    tot = h.sum()
    if tot <= 0:
        return 0.5, 0.0, 1.0
    c = 0.5 * (edges[:-1] + edges[1:])
    w0 = np.cumsum(h)
    w1 = tot - w0
    s0 = np.cumsum(h * c)
    m0 = np.where(w0 > 0, s0 / np.maximum(w0, 1e-12), 0)
    m1 = np.where(w1 > 0, (s0[-1] - s0) / np.maximum(w1, 1e-12), 0)
    between = w0 * w1 * (m0 - m1) ** 2
    k = int(np.argmax(between[:-1])) if bins > 1 else 0
    return float(edges[k + 1]), float(m0[k]), float(m1[k])


_LF_X = np.linspace(0.0, 40.0, 801)
_LF_Y = np.array([math.lgamma(x + 1.0) for x in _LF_X])


def _log_factorial(x: np.ndarray) -> np.ndarray:
    """log(x!) of a nonnegative (real) count, from a table: NumPy has no
    vectorised lgamma and SciPy is not needed for this."""
    return np.interp(x, _LF_X, _LF_Y)


def _huber(x: np.ndarray, s: float, c: float) -> np.ndarray:
    """-log of a density with a Gaussian core (sd `s`) and exponential
    tails beyond `c` sds, up to a constant: x^2/2s^2 inside, linear outside."""
    z = np.abs(x) / max(s, 1e-9)
    return np.where(z <= c, 0.5 * z * z, c * (z - 0.5 * c))


def _logit_fit(p: np.ndarray, target: float) -> np.ndarray:
    """The probabilities `p` shifted by one amount in their log-odds so that
    they sum to `target` (bisection): the order among them is kept and none
    reaches 0 or 1."""
    if p.size == 0:
        return p
    base = np.clip(p, 1e-4, 1 - 1e-4)
    lo = np.log(base / (1 - base))
    a, b = -12.0, 12.0
    for _ in range(60):
        d = 0.5 * (a + b)
        if float((1.0 / (1.0 + np.exp(-(lo + d)))).sum()) > target:
            b = d
        else:
            a = d
    return 1.0 / (1.0 + np.exp(-(lo + 0.5 * (a + b))))


def _pace_step(rho: np.ndarray, m, a: float, b: float, c: float):
    """One step of the pace: the unit's own log-rate `rho`, the pace the
    step comes from `m` (already pulled back towards the global rate), the
    spread `a` of the pace's move and the spread `b` of a unit's own scatter
    around the pace.  Returns the new pace x (the best, for each
    transition), the cost of its move -- Huber(x - m; a) -- and the cost of
    the unit's scatter -- Huber(rho - x; b).  Both are Huber so that a real
    change of pace, and a sentence read oddly fast, each cost in proportion
    to their size.

    The best x lies between m and rho.  With y its distance from m (of D =
    |rho - m|), the sum's slope is g(y) = min(y/a^2, c/a) - min((D-y)/b^2,
    c/b): increasing, and straight between its two corners (y = c a and y
    = D - c b).  So the root is found exactly by looking at the corners and
    interpolating in the one piece where g changes sign -- a few array
    operations, no search."""
    rho = np.asarray(rho, float)
    m = np.broadcast_to(np.asarray(m, float), rho.shape)
    a = max(a, 1e-6)
    b = max(b, 1e-6)
    d = rho - m
    sgn = np.where(d < 0, -1.0, 1.0)
    D = np.abs(d)

    def g(y):
        return np.minimum(y / (a * a), c / a) - np.minimum((D - y) / (b * b), c / b)

    p1 = np.minimum(c * a, D)
    p2 = np.clip(D - c * b, 0.0, None)
    lo = np.minimum(p1, p2)
    hi = np.maximum(p1, p2)
    g0, glo, ghi, gD = g(np.zeros_like(D)), g(lo), g(hi), g(D)
    first = glo >= 0
    second = ~first & (ghi >= 0)
    ya = np.where(first, 0.0, np.where(second, lo, hi))
    yb = np.where(first, lo, np.where(second, hi, D))
    ga = np.where(first, g0, np.where(second, glo, ghi))
    gb = np.where(first, glo, np.where(second, ghi, gD))
    den = gb - ga
    y = np.where(den > 1e-12, ya - ga * (yb - ya) / np.where(den > 1e-12, den, 1.0), ya)
    y = np.clip(y, 0.0, D)
    return m + sgn * y, _huber(y, a, c), _huber(D - y, b, c)


def _pava(y: list) -> list:
    """Least-squares nondecreasing fit (pool adjacent violators)."""
    vals, wts, cnt = [], [], []
    for v in y:
        vals.append(float(v)); wts.append(1.0); cnt.append(1)
        while len(vals) > 1 and vals[-2] > vals[-1]:
            v2, w2, c2 = vals.pop(), wts.pop(), cnt.pop()
            vals[-1] = (vals[-1] * wts[-1] + v2 * w2) / (wts[-1] + w2)
            wts[-1] += w2
            cnt[-1] += c2
    out = []
    for v, c in zip(vals, cnt):
        out.extend([v] * c)
    return out


# ============================================================ the transcript
# THE SCRIPTS WRITTEN WITHOUT SPACES, by the Unicode Script property (as the
# ranges Scripts.txt gives them): Han, Hiragana, Katakana, Bopomofo, Thai, Lao,
# Tibetan, Myanmar, Khmer, Yi and the Tai scripts, Balinese, Javanese.  A run
# of them is split into single characters (each with the marks that follow
# it) because there is no space to split at -- the rule is the script's, not
# a language's, and no word list is consulted.  Hangul is not here: Korean
# writes spaces.
_CONTINUA = sorted([
    (0x0E00, 0x0E7F), (0x0E80, 0x0EFF), (0x0F00, 0x0FFF), (0x1000, 0x109F),
    (0x1780, 0x17FF), (0x1950, 0x197F), (0x1980, 0x19DF), (0x19E0, 0x19FF),
    (0x1A20, 0x1AAF), (0x1B00, 0x1B7F), (0x2E80, 0x2FDF), (0x3005, 0x3007),
    (0x3021, 0x3029), (0x3038, 0x303B), (0x3041, 0x309F), (0x30A0, 0x30FF),
    (0x3100, 0x312F), (0x31A0, 0x31BF), (0x31F0, 0x31FF), (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF), (0xA000, 0xA4CF), (0xA980, 0xA9DF), (0xA9E0, 0xA9FF),
    (0xAA60, 0xAA7F), (0xAA80, 0xAADF), (0xF900, 0xFAFF), (0xFF66, 0xFF9F),
    (0x1B000, 0x1B16F), (0x20000, 0x323AF),
])
_CONTINUA_STARTS = [a for a, _ in _CONTINUA]


def _is_continua(ch: str) -> bool:
    cp = ord(ch)
    i = bisect.bisect_right(_CONTINUA_STARTS, cp) - 1
    return i >= 0 and _CONTINUA[i][0] <= cp <= _CONTINUA[i][1]


@lru_cache(maxsize=4096)
def punctuation_class(ch: str) -> int:
    """The break a punctuation character marks, by its Unicode properties:
    -1 not punctuation, 0 none (quotes, brackets, hyphens), 1 comma, 2
    semicolon or colon, 3 sentence end.  General category says whether it
    is punctuation; the Name property says which kind -- so the Arabic
    question mark, the Devanagari danda and the ideographic full stop are
    sentence ends without a table of languages."""
    cat = unicodedata.category(ch)
    if cat[0] != "P":
        return -1
    name = unicodedata.name(ch, "")
    if "INVERTED" in name:          # the Spanish openers: they end nothing
        return 0
    if ("FULL STOP" in name or "QUESTION MARK" in name or "EXCLAMATION MARK" in name
            or "ELLIPSIS" in name or "DANDA" in name or "INTERROBANG" in name):
        return BREAK_SENTENCE
    if "COLON" in name:             # SEMICOLON contains it too
        return BREAK_COLON
    if "COMMA" in name:
        return BREAK_COMMA
    if cat == "Pd" and "DASH" in name:
        return BREAK_COMMA
    return 0


def _is_mark_like(ch: str) -> bool:
    cat = unicodedata.category(ch)
    return cat[0] == "M" or cat == "Sk" or "PROLONGED SOUND MARK" in unicodedata.name(ch, "")


@lru_cache(maxsize=65536)
def char_count(token: str) -> int:
    """How many characters a token has for its duration prior: letters and
    digits, not punctuation, not symbols, and not the combining marks -- a
    vowelled Persian or Arabic word (its harakat are optional notation of
    vowels the bare letters leave unwritten) weighs the same as the bare one.
    The one exception is a dependent VOWEL SIGN (the Unicode Name says so):
    Devanagari's matras, and their kin in the other Indic and South-East Asian
    scripts, are always written and always spoken, so each counts as one.
    Virama, nukta, anusvara and candrabindu do not.  Nor does the Arabic
    TATWEEL (U+0640, kashida): Unicode files it as a letter, but it is only
    ink that stretches a word across the line, and a word drawn out with it
    is said exactly as the one without -- the same case as the harakat."""
    n = 0
    for ch in token:
        if ch == "\u0640":
            continue
        cat = unicodedata.category(ch)
        if cat[0] in "LN":
            n += 1
        elif cat in ("Mn", "Mc") and "VOWEL SIGN" in unicodedata.name(ch, ""):
            n += 1
    return n


def default_tokenize(text: str) -> list:
    """Whitespace words; inside them, a run of a script written without spaces
    becomes single characters (each with its marks).  Punctuation stays on the
    token it follows (opening brackets and quotes on the one they open)."""
    out = []
    for chunk in str(text).split():
        out.extend(_split_chunk(chunk))
    return out


def _split_chunk(chunk: str) -> list:
    out, cur, mode, prefix = [], "", None, ""
    for ch in chunk:
        cat = unicodedata.category(ch)
        if cat in ("Ps", "Pi"):
            prefix += ch                      # it opens what follows
        elif cat[0] == "P" or cat in ("Sm", "Sc", "So"):
            if cur:
                cur += prefix + ch
                prefix = ""
            else:
                prefix += ch
        elif _is_mark_like(ch) and (cur or prefix):
            if cur:
                cur += ch
            else:
                prefix += ch
        elif _is_continua(ch):
            if cur:
                out.append(cur)
            cur, mode, prefix = prefix + ch, "c", ""
        else:
            if cur and (mode == "c" or prefix):
                out.append(cur)
                cur = ""
            cur, mode, prefix = cur + prefix + ch, "w", ""
    if cur:
        out.append(cur + prefix)
    elif prefix:
        out.append(prefix)
    return out


def _trailing_break(token: str) -> int:
    """The strongest break the punctuation after a token's last letter marks
    (repeated punctuation, "?!", "..." and a closing quote after a full stop
    all come out as the strongest one among them)."""
    lvl = 0
    for ch in reversed(token):
        cat = unicodedata.category(ch)
        if cat[0] in "LN" or cat[0] == "M":
            break
        lvl = max(lvl, punctuation_class(ch))
    return max(lvl, 0)


@dataclass
class TranscriptModel:
    tokens: list            # the token texts, punctuation attached
    chars: np.ndarray       # character counts (char_count)
    weights: np.ndarray     # duration weights
    level: np.ndarray       # break level after each token (BREAK_*)
    prior: np.ndarray       # pause preference after each token, 0..1
    piece: np.ndarray       # which piece each token belongs to
    piece_break: np.ndarray  # True after the last token of a piece
    placeholder: np.ndarray  # True for a stand-in of an empty piece
    continua: np.ndarray    # True for a character of a script without spaces
    cut: np.ndarray         # True where a unit must end (a sentence, a strong piece end)
    plen: np.ndarray        # the pause length each break is apt to have (seconds)
    bare: bool = False      # a text nobody punctuated (TranscriptAnalyzer.analyze)

    @property
    def n(self) -> int:
        return len(self.tokens)


class TranscriptAnalyzer:
    """Tokens, their duration weights, and the break after each.  The
    tokenizer is a callback (`tokenize(text) -> Sequence[str]`); what it
    returns is taken as it is, except that a token with no letters in it
    (a lone dash, a quote, an ellipsis) is joined to its neighbour, because a
    token that is only punctuation is not a thing anyone says."""

    def __init__(self, opts: AlignmentOptions, tokenize: Optional[Callable] = None):
        self.o = opts
        self.tokenize = tokenize or default_tokenize

    def _prior(self, chars: int) -> float:
        """The duration prior in force, of a word this many characters long."""
        o = self.o
        n = float(chars)
        prior = o.duration_prior
        if prior == "linear":
            return n
        if prior == "sqrt":
            return math.sqrt(n)
        if prior == "affine":
            return o.affine_constant + o.affine_per_char * n
        return n ** o.alpha if n > 0 else 0.0

    def weight(self, chars: int, continua: bool, power: float = 1.0) -> float:
        v = self._prior(chars) ** power
        if continua:
            v *= self.o.continua_weight
        return max(self.o.min_weight, v)

    # how hard the stability test shakes the prior: its value to this power,
    # so a long word gains on a short one whichever prior is in force (for
    # the default power prior, n ** 0.8 becomes about n ** 0.95)
    SHAKE = 1.19

    def shaken(self, model: TranscriptModel) -> np.ndarray:
        """The weights of `model` with the duration prior shaken, as the
        confidence's stability test asks (_Engine.run): every word's prior
        raised to SHAKE, the stand-ins and the wordless left as they were,
        the whole scaled back to the same total.  Shaking only alpha, as it
        first did, shook nothing unless the prior was "power"."""
        w = model.weights
        w2 = np.array([w[i] if model.placeholder[i] or model.chars[i] == 0
                       else self.weight(int(model.chars[i]), bool(model.continua[i]), self.SHAKE)
                       for i in range(model.n)])
        return w2 * (w.sum() / max(float(w2.sum()), 1e-9))

    def _paragraph_tokens(self, par: str) -> list:
        # A CALLBACK THAT BREAKS FALLS BACK TO THE DEFAULT, however it
        # breaks: raising when called, returning something that is not a
        # list, a generator that raises halfway, a token that cannot be
        # made a string.  So the tokens are taken out of it inside the same
        # guard as the call itself -- a lazy result fails only when read.
        try:
            raw = self.tokenize(par)
            toks = [str(t).strip() for t in ([] if raw is None else raw) if t is not None]
        except Exception:
            toks = [str(t).strip() for t in default_tokenize(par)]
        toks = [t for t in toks if t]
        # tokens with no letters join a neighbour: an opening one the token
        # after it, any other the token before it
        out = []
        pending = ""
        for t in toks:
            if char_count(t) == 0:
                opening = all(unicodedata.category(c) in ("Ps", "Pi") for c in t)
                if out and not opening:
                    out[-1] += t
                else:
                    pending += t
                continue
            out.append(pending + t)
            pending = ""
        if pending:
            if out:
                out[-1] += pending
            else:
                out.append(pending)     # nothing but punctuation
        return out

    def analyze(self, pieces: Sequence[str], piece_strength: float = 0.0) -> TranscriptModel:
        o = self.o
        bs = o.break_strength
        strength = [float(o.pause_prob_word), float(bs.get("comma", 0.45)),
                    float(bs.get("colon", 0.55)), float(bs.get("sentence", 0.85)),
                    float(bs.get("paragraph", 0.95))]
        tokens, level, piece_of, pbreak, holder = [], [], [], [], []
        for pi, text in enumerate(pieces):
            text = "" if text is None else str(text)
            # a paragraph is what a blank line ends
            pars = re.split(r"\n[^\S\n]*\n\s*", text)
            mine = []
            for pj, par in enumerate(pars):
                toks = self._paragraph_tokens(par)
                for k, t in enumerate(toks):
                    lvl = _trailing_break(t)
                    if k == len(toks) - 1 and pj < len(pars) - 1:
                        lvl = BREAK_PARAGRAPH
                    mine.append((t, lvl))
            if any(char_count(t) for t, _ in mine):
                for t, lvl in mine:
                    tokens.append(t)
                    level.append(lvl)
                    piece_of.append(pi)
                    pbreak.append(False)
                    holder.append(False)
            else:
                # an empty or punctuation-only piece still gets a slot -- a
                # stand-in, not a word anyone says
                tokens.append(text.strip())
                level.append(_trailing_break(text.strip()) if text.strip() else 0)
                piece_of.append(pi)
                pbreak.append(False)
                holder.append(True)
            pbreak[-1] = True
        n = len(tokens)
        chars = np.array([char_count(t) for t in tokens], dtype=float)
        weights = np.empty(n)
        cont = np.zeros(n, bool)
        for i, t in enumerate(tokens):
            first = next((c for c in t if unicodedata.category(c)[0] in "LN"), "")
            cont[i] = bool(first) and _is_continua(first)
            if holder[i] or chars[i] == 0:
                weights[i] = o.min_weight * o.empty_weight
            else:
                weights[i] = self.weight(int(chars[i]), bool(cont[i]))
        lv = np.array(level, dtype=np.int8)
        prior = np.array([strength[int(x)] for x in lv], dtype=float)
        pb = np.array(pbreak, dtype=bool)
        # A TEXT NOBODY PUNCTUATED: forty words and more with no mark between
        # them, not a comma, not a full stop, not a blank line -- which a
        # punctuated text almost never manages -- is an auto-caption as the
        # recogniser wrote it, lyrics, subtitles in a script whose captions
        # carry no full stop.  Its sentences end all the same, unmarked, so
        # any of its words may be followed by a sentence's pause, as long a
        # one as a sentence end has; and its captions end where a line filled
        # up, not where the voice stopped, so a caption's end is no likelier
        # a pause than any other word's.  Measured on made-up auto-captions
        # (docs/wavealign.md, section 6), that took a thousand words of them
        # from worse than by the text to better; a punctuated text is never
        # touched by it.  (A book's piece end is the book's own cut, and
        # stays one.)
        bare = n >= o.bare_min_tokens and not (lv[:-1] > BREAK_WORD).any()
        if piece_strength > 0 and n and not (bare and piece_strength < strength[BREAK_SENTENCE]):
            prior = np.where(pb, np.maximum(prior, piece_strength), prior)
        if n:
            prior[-1] = 1.0     # the end of the transcript: the end of speech
        # the units above words end at sentences, and at the pieces' ends
        # when a piece end is as strong as a sentence's (a book's pieces);
        # a caption cut in mid-sentence is left to the words
        cut = (lv >= BREAK_SENTENCE) | (pb & (piece_strength >= strength[BREAK_SENTENCE]))
        pl = o.pause_length
        lengths = [float(pl.get(k, 0.3)) for k in BREAK_NAMES]
        plen = np.array([lengths[int(x)] for x in lv], dtype=float)
        if n and piece_strength > 0:
            # a piece end is as apt to pause long as the break it is as
            # strong as
            k = max(i for i in range(len(strength)) if strength[i] <= piece_strength or i == 0)
            plen = np.where(pb, np.maximum(plen, lengths[k]), plen)
        if bare:
            plen = np.where(lv == BREAK_WORD, np.maximum(plen, lengths[BREAK_SENTENCE]), plen)
        return TranscriptModel(tokens, chars, weights, lv, prior,
                               np.array(piece_of, dtype=np.int64), pb,
                               np.array(holder, dtype=bool), cont, cut, plen, bool(bare))


# ============================================================ the waveform
@dataclass
class Signal:
    duration: float
    rate: float             # frames a second of the working grid
    raw: np.ndarray         # the envelope on the grid, linear, >= 0
    db: np.ndarray          # 20 log10, smoothed
    level: np.ndarray       # normalised 0..1 (smoothed): the curve used
    fine: np.ndarray        # normalised 0..1, median only: for refinement
    native_rate: float
    dyn_range_db: float
    degenerate: bool
    garbage: int

    @property
    def n(self) -> int:
        return self.level.size

    @property
    def centres(self) -> np.ndarray:
        return (np.arange(self.n) + 0.5) / self.rate


class WaveformPreprocessor:
    """Garbage out, a uniform grid, a compressed (dB) curve normalised by
    percentiles -- never by the maximum, which one click would decide -- and
    smoothing measured in seconds, not samples."""

    def __init__(self, opts: AlignmentOptions):
        self.o = opts

    def run(self, waveform, duration: float, sample_times=None) -> Signal:
        o = self.o
        D = float(duration)
        vals = _as_float_array(waveform)
        if sample_times is None:
            n = vals.size
            t = (np.arange(n) + 0.5) * (D / n) if n else np.zeros(0)
        else:
            t = _as_float_array(sample_times)
            k = min(t.size, vals.size)
            t, vals = t[:k], vals[:k]
        ok = np.isfinite(vals) & np.isfinite(t)
        garbage = int((~ok).sum() + (vals[ok] < 0).sum())
        # a negative number is a magnitude written signed; NaN and inf are
        # holes, filled from their neighbours below
        v = np.abs(vals[ok])
        t = t[ok]
        if sample_times is not None and t.size:
            order = np.argsort(t, kind="stable")
            t, v = t[order], v[order]
        t = np.clip(t, 0.0, D)
        if t.size >= 2:
            dt = np.diff(t)
            dt = dt[dt > 0]
            native = 1.0 / float(np.median(dt)) if dt.size else t.size / D
        else:
            native = max(t.size, 1) / D
        native = float(min(max(native, 1e-3), 1e5))

        nf = max(16, int(math.ceil(D * o.frame_rate - 1e-9)))
        rate = nf / D
        grid = np.full(nf, -1.0)
        if v.size:
            k = np.clip((t * rate).astype(np.int64), 0, nf - 1)
            np.maximum.at(grid, k, v)
        filled = grid >= 0
        degenerate = False
        centres = (np.arange(nf) + 0.5) / rate
        if not filled.any():
            grid[:] = 0.0
            degenerate = True
        elif not filled.all():
            grid = np.interp(centres, centres[filled], grid[filled])

        top = float(np.percentile(grid, 99.5))
        eps = max(1e-7, 1e-3 * top)
        db = 20.0 * np.log10(grid + eps)
        # every window in seconds, and none wider than the grid: see _gauss
        med = _median(db, int(round(min(o.median_s * rate, nf))) | 1)
        sm = _gauss(med, min(o.smooth_s * rate, nf))
        floor = float(np.percentile(sm, o.floor_percentile))
        ceil = float(np.percentile(sm, o.ceil_percentile))
        rng = ceil - floor
        if not (rng > 1e-6) or degenerate:
            degenerate = True
            level = np.full(nf, 0.5)
            fine = level.copy()
            rng = 0.0
        else:
            level = np.clip((sm - floor) / rng, 0.0, 1.0)
            fine = np.clip((med - floor) / rng, 0.0, 1.0)
        return Signal(D, rate, grid, sm, level, fine, native, float(rng), degenerate, garbage)


@dataclass
class Activity:
    noise_floor: float
    speech_level: float
    low: float
    high: float
    otsu: float
    evidence: float         # 0..1: how much the envelope can be believed
    likelihood: np.ndarray  # soft activity per frame, 0..1
    active: np.ndarray      # hysteresis decision per frame
    speech: np.ndarray      # active with the short gaps closed
    regions: list           # [(start, end)] major speech regions
    edges: np.ndarray       # frame edges, seconds
    cum_act: np.ndarray     # integral of the likelihood at the edges
    cum_speech: np.ndarray  # integral of `speech` (plus a tiny slope)
    min_pause: float

    def A(self, t):
        return np.interp(t, self.edges, self.cum_act)

    def S(self, t):
        return np.interp(t, self.edges, self.cum_speech)

    def S_inv(self, s):
        return np.interp(s, self.cum_speech, self.edges)


class ActivityEstimator:
    """An energy-activity estimate -- not voice activity detection, which the
    envelope cannot support.  Otsu's split of the level histogram gives a
    noise level and a speech level; the two hysteresis thresholds are
    fractions of the way between them, so no amplitude is hard-coded."""

    def __init__(self, opts: AlignmentOptions):
        self.o = opts

    def run(self, sig: Signal) -> Activity:
        o = self.o
        lev = sig.level
        rate = sig.rate
        thr, m0, m1 = _otsu(lev)
        noise, speech = m0, max(m1, m0 + 1e-3)
        low = noise + o.low_frac * (speech - noise)
        high = noise + o.high_frac * (speech - noise)
        ev = 0.0 if sig.degenerate else float(np.clip(
            (sig.dyn_range_db - o.evidence_db_lo) / (o.evidence_db_hi - o.evidence_db_lo), 0, 1))

        # hysteresis, vectorised: a run above `low` is active when it reaches
        # `high` somewhere
        s, e = _runs(lev >= low)
        cs = np.concatenate([[0], np.cumsum(lev >= high)])
        keep = (cs[e] - cs[s]) > 0
        active = _fill_runs(np.zeros(sig.n, bool), s[keep], e[keep], True)
        s, e = _runs(active)
        short = (e - s) / rate < o.min_active_s
        active = _fill_runs(active, s[short], e[short], False)
        if sig.degenerate or ev <= 0 or not active.any():
            # nothing to believe: everything counts as sound, and the text
            # alone will decide
            ev = 0.0
            active = np.ones(sig.n, bool)

        min_pause = max(o.min_pause_s, 0.5 / sig.native_rate)
        s, e = _runs(~active)
        inner = (s > 0) & (e < sig.n) & ((e - s) / rate < min_pause)
        speech_mask = _fill_runs(active, s[inner], e[inner], True)

        # speech regions: active runs merged over gaps shorter than region_gap
        s, e = _runs(~active)
        gap = (s > 0) & (e < sig.n) & ((e - s) / rate < o.region_gap_s)
        merged = _fill_runs(active, s[gap], e[gap], True)
        rs, re_ = _runs(merged)
        # a frame's edge is k / rate, and nf / (nf / D) may round a hair past
        # D: the regions are the caller's, and promised inside [0, D]
        D = sig.duration
        regions = [(float(min(a / rate, D)), float(min(b / rate, D))) for a, b in zip(rs, re_)]

        mid = 0.5 * (low + high)
        sc = max(0.02, (high - low) / 4)
        like = 1.0 / (1.0 + np.exp(-(lev - mid) / sc))
        like = 1.0 - ev * (1.0 - like)
        edges = np.arange(sig.n + 1) / rate
        cum_act = np.concatenate([[0.0], np.cumsum(like) / rate])
        sp = speech_mask.astype(float) + 1e-3
        cum_speech = np.concatenate([[0.0], np.cumsum(sp) / rate])
        return Activity(noise, speech, low, high, thr, ev, like, active, speech_mask,
                        regions, edges, cum_act, cum_speech, min_pause)


@dataclass
class Detection:
    # pauses (structure of arrays)
    p_left: np.ndarray
    p_right: np.ndarray
    p_dur: np.ndarray
    p_min: np.ndarray
    p_ctx: np.ndarray
    p_strength: np.ndarray
    p_anchor: np.ndarray
    p_cls: np.ndarray
    p_role: np.ndarray      # 0 inner, 1 leading, 2 trailing
    # valleys
    v_time: np.ndarray
    v_level: np.ndarray
    v_prom: np.ndarray
    v_ctx: np.ndarray
    v_strength: np.ndarray
    n_peaks: int


class PauseDetector:
    """Pauses and valleys.  A pause is a run below the low threshold, and it
    keeps BOTH edges -- where the sound stopped and where it began again --
    because the word before it ends at one and the word after it starts at
    the other, and the silence between belongs to neither.  A valley is a
    prominent local minimum inside speech: a place where a word boundary
    might be, never assumed to be one."""

    def __init__(self, opts: AlignmentOptions):
        self.o = opts

    def run(self, sig: Signal, act: Activity) -> Detection:
        o = self.o
        lev, rate, n = sig.level, sig.rate, sig.n
        c = (np.arange(n) + 0.5) / rate
        spread = max(act.speech_level - act.noise_floor, 1e-3)

        # ---- pauses
        s, e = _runs(~act.active)
        if act.evidence <= 0:
            s, e = s[:0], e[:0]
        lead = s == 0
        trail = e == n
        sp = np.maximum(s - 1, 0)
        den = lev[sp] - lev[np.minimum(s, n - 1)]
        fr = np.where(den > 1e-9, (lev[sp] - act.low) / np.where(den > 1e-9, den, 1), 0.5)
        left = np.where(lead, 0.0, c[sp] + np.clip(fr, 0, 1) / rate)
        ep = np.minimum(e, n - 1)
        den = lev[ep] - lev[np.maximum(e - 1, 0)]
        fr = np.where(den > 1e-9, (act.low - lev[np.maximum(e - 1, 0)]) / np.where(den > 1e-9, den, 1), 0.5)
        right = np.where(trail, sig.duration, c[np.maximum(e - 1, 0)] + np.clip(fr, 0, 1) / rate)
        right = np.maximum(right, left)
        dur = right - left
        keep = (lead | trail) & (dur > 0) | (dur >= act.min_pause)
        s, e, left, right, dur, lead, trail = (a[keep] for a in (s, e, left, right, dur, lead, trail))
        ext = np.append(lev, np.inf)
        if s.size:
            pmin = np.minimum.reduceat(ext, np.ravel(np.column_stack([s, e])))[::2]
        else:
            pmin = np.zeros(0)
        cl = np.concatenate([[0.0], np.cumsum(lev)])
        w = max(1, int(round(min(o.context_s * rate, n))))
        a0 = np.maximum(s - w, 0)
        b1 = np.minimum(e + w, n)
        nl = s - a0
        nr = b1 - e
        tot = (cl[s] - cl[a0]) + (cl[b1] - cl[e])
        ctx = np.where(nl + nr > 0, tot / np.maximum(nl + nr, 1), act.speech_level)
        depth = np.clip((act.high - pmin) / max(act.high - act.noise_floor, 1e-3), 0, 1)
        dscore = 1.0 - np.exp(-dur / o.pause_tau_s)
        contrast = np.clip((ctx - pmin) / spread, 0, 1)
        strength = act.evidence * np.sqrt(depth) * (0.35 + 0.65 * dscore) * (0.5 + 0.5 * contrast)
        anchor = strength * np.clip((dur - o.anchor_short_s) / max(o.anchor_full_s - o.anchor_short_s, 1e-3), 0, 1)
        cls = np.where(dur < o.phrase_pause_s, 0, np.where(dur < o.long_pause_s, 1, 2)).astype(np.int8)
        role = np.where(lead, 1, np.where(trail, 2, 0)).astype(np.int8)

        # ---- valleys: minima of the level curve inside speech, measured on
        # runs of equal values so that a flat bottom gives its middle
        if n >= 3 and act.evidence > 0:
            change = np.concatenate([[True], lev[1:] != lev[:-1]])
            rs = np.flatnonzero(change)
            re_ = np.append(rs[1:], n)
            rv = lev[rs]
            mid = (rs + re_ - 1) / 2.0
            is_min = np.zeros(rs.size, bool)
            if rs.size >= 3:
                is_min[1:-1] = (rv[1:-1] < rv[:-2]) & (rv[1:-1] < rv[2:])
            is_max = np.zeros(rs.size, bool)
            if rs.size >= 3:
                is_max[1:-1] = (rv[1:-1] > rv[:-2]) & (rv[1:-1] > rv[2:])
            n_peaks = int(is_max.sum())
            k = np.flatnonzero(is_min)
            fk = np.round(mid[k]).astype(np.int64)
            inside = act.speech[fk] if k.size else np.zeros(0, bool)
            k, fk = k[inside], fk[inside]
            wv = max(1, int(round(min(o.valley_window_s * rate, n))))
            lmax = _side_max(lev, fk, wv, "left")
            rmax = _side_max(lev, fk, wv, "right")
            vl = rv[k]
            prom = np.minimum(lmax, rmax) - vl
            ok = prom >= o.valley_min_prominence
            k, fk, vl, prom, lmax, rmax = (a[ok] for a in (k, fk, vl, prom, lmax, rmax))
            # sub-frame position: a parabola through the frame and its two
            # neighbours, for a single-frame minimum
            single = (re_[k] - rs[k]) == 1
            f0 = np.clip(fk - 1, 0, n - 1)
            f2 = np.clip(fk + 1, 0, n - 1)
            den = lev[f0] - 2 * lev[fk] + lev[f2]
            delta = np.where(single & (den > 1e-9), 0.5 * (lev[f0] - lev[f2]) / np.where(den > 1e-9, den, 1), 0.0)
            vt = (mid[k] + 0.5 + np.clip(delta, -0.5, 0.5)) / rate
            depth = np.clip((act.high - vl) / max(act.high - act.noise_floor, 1e-3), 0, 1)
            vs = act.evidence * np.clip(prom / o.valley_full_prominence, 0, 1) ** 0.7 * (0.6 + 0.4 * depth)
            vctx = 0.5 * (lmax + rmax)
        else:
            vt = vl = prom = vs = vctx = np.zeros(0)
            n_peaks = 0
        return Detection(left, right, dur, pmin, ctx, strength, anchor, cls, role,
                         vt, vl, prom, vctx, vs, n_peaks)


# ============================================================ candidates
@dataclass
class CandidateSet:
    L: np.ndarray           # where the word before may end
    R: np.ndarray           # where the word after may start
    kind: np.ndarray
    strength: np.ndarray
    dur: np.ndarray         # gap length (0 for a point)
    lev: np.ndarray         # level at the boundary
    ctx: np.ndarray         # level of the context
    bcost: np.ndarray       # boundary cost: low at a deep, strong valley
    anchor: np.ndarray      # how strongly the envelope marks a real break
    AL: np.ndarray          # activity integral at L / R
    AR: np.ndarray
    SL: np.ndarray          # speech-time integral at L / R
    SR: np.ndarray
    P: np.ndarray           # prefix sums of the pause mass (straddling costs)

    @property
    def m(self) -> int:
        return self.L.size


class BoundaryCandidateGenerator:
    """The places a boundary may go: the two edges of every pause (one
    OBJECT), valleys, the edges of speech, the proportional prior, and a
    regular fallback grid so that an envelope with no valleys at all still
    leaves the DP somewhere to go.  Nothing but a pause's own edges is left
    inside a pause.  Coarser levels ask for a sparser set."""

    def __init__(self, opts: AlignmentOptions):
        self.o = opts

    def build(self, sig: Signal, act: Activity, det: Detection, *, step: float,
              pause_min_s: float = 0.0, valley_min_strength: float = 0.0,
              extra_t=None, extra_kind=None, extra_s=None, n_words: int = 0,
              max_valleys: int = 0) -> CandidateSet:
        o = self.o
        D = sig.duration
        sep = min(o.min_separation_s, D / (4.0 * (n_words + 2)))
        # ---- gap objects: the inner pauses
        inner = (det.p_role == 0) & (det.p_dur >= max(pause_min_s, act.min_pause))
        if max_valleys and int(inner.sum()) > max_valleys:
            # THE BUDGET HOLDS FOR PAUSES TOO.  Two captions left before the
            # end of a two-hour video are two words for a whole stretch full
            # of pauses; every pause is a candidate every boundary may take,
            # and the word pass's cost matrix grows as their number squared
            # -- gigabytes for a few hours.  A transcript that short needs
            # only the pauses most likely to be its breaks: the surest
            # anchors, the longest first where they tie.
            ii = np.flatnonzero(inner)
            order = np.lexsort((-det.p_dur[ii], -det.p_anchor[ii]))
            keep = np.zeros(inner.size, bool)
            keep[ii[order[:max_valleys]]] = True
            inner &= keep
        gl, gr = det.p_left[inner], det.p_right[inner]
        g_s, g_d, g_min, g_ctx, g_a = (det.p_strength[inner], det.p_dur[inner], det.p_min[inner],
                                       det.p_ctx[inner], det.p_anchor[inner])
        # ---- points
        pts_t, pts_k, pts_s, pts_l, pts_c = [], [], [], [], []

        def add(t, k, s, lv=None, cx=None):
            t = np.asarray(t, float)
            pts_t.append(t)
            pts_k.append(np.full(t.size, k, np.int8))
            pts_s.append(np.broadcast_to(np.asarray(s, float), t.shape).astype(float))
            pts_l.append(np.full(t.size, np.nan) if lv is None else np.asarray(lv, float))
            pts_c.append(np.full(t.size, np.nan) if cx is None else np.asarray(cx, float))

        add([0.0, D], KIND_EDGE, 0.0)
        lead = det.p_role == 1
        trail = det.p_role == 2
        if lead.any():
            add(det.p_right[lead], KIND_EDGE, det.p_strength[lead], det.p_min[lead], det.p_ctx[lead])
        if trail.any():
            add(det.p_left[trail], KIND_EDGE, det.p_strength[trail], det.p_min[trail], det.p_ctx[trail])
        vk = det.v_strength >= valley_min_strength
        if max_valleys and vk.sum() > max_valleys:
            # a transcript far shorter than the sound does not need a
            # boundary at every ripple: keep the strongest
            order = np.argsort(-det.v_strength, kind="stable")
            keep = np.zeros(vk.size, bool)
            keep[order[:max_valleys]] = True
            vk &= keep
        if vk.any():
            add(det.v_time[vk], KIND_VALLEY, det.v_strength[vk], det.v_level[vk], det.v_ctx[vk])
        if extra_t is not None and len(extra_t):
            et = np.asarray(extra_t, float)
            ek = np.asarray(extra_kind, np.int8) if extra_kind is not None else np.full(et.size, KIND_PRIOR, np.int8)
            es = np.asarray(extra_s, float) if extra_s is not None else np.zeros(et.size)
            for kk in np.unique(ek):
                sel = ek == kk
                add(et[sel], int(kk), es[sel])
        st = step
        if n_words > 0:
            st = min(st, D / (3.0 * (n_words + 1)))
        st = max(st, 1e-4)
        grid = np.arange(st, D - 0.5 * st, st)
        add(grid, KIND_FALLBACK, 0.0)

        t = np.concatenate(pts_t)
        k = np.concatenate(pts_k)
        s = np.concatenate(pts_s)
        lv = np.concatenate(pts_l)
        cx = np.concatenate(pts_c)
        ok = np.isfinite(t) & (t >= 0) & (t <= D)
        t, k, s, lv, cx = t[ok], k[ok], s[ok], lv[ok], cx[ok]
        # nothing inside a gap object (or too close to its edges)
        if gl.size:
            i = np.searchsorted(gl - sep, t, side="right") - 1
            inside = (i >= 0) & (t <= gr[np.maximum(i, 0)] + sep)
            inside &= ~((k == KIND_EDGE) & ((t == 0.0) | (t == D)))
            t, k, s, lv, cx = t[~inside], k[~inside], s[~inside], lv[~inside], cx[~inside]
        # de-duplicate points closer than `sep`, keeping the higher priority
        order = np.lexsort((-_PRIORITY[k], t))
        t, k, s, lv, cx = t[order], k[order], s[order], lv[order], cx[order]
        for _ in range(4):
            if t.size < 2:
                break
            close = np.diff(t) < sep
            if not close.any():
                break
            pa = _PRIORITY[k[:-1]]
            pb = _PRIORITY[k[1:]]
            drop = np.zeros(t.size, bool)
            idx = np.flatnonzero(close)
            later_loses = pa[idx] >= pb[idx]
            drop[idx[later_loses] + 1] = True
            drop[idx[~later_loses]] = True
            # the two ends of the stretch are never dropped
            drop &= ~((k == KIND_EDGE) & ((t == 0.0) | (t == D)))
            if not drop.any():
                break
            keep = ~drop
            t, k, s, lv, cx = t[keep], k[keep], s[keep], lv[keep], cx[keep]

        # ---- one sorted list of objects
        L = np.concatenate([t, gl])
        R = np.concatenate([t, gr])
        kind = np.concatenate([k, np.full(gl.size, KIND_PAUSE, np.int8)])
        strength = np.concatenate([s, g_s])
        dur = np.concatenate([np.zeros(t.size), g_d])
        lvl = np.concatenate([lv, g_min])
        ctx = np.concatenate([cx, g_ctx])
        anchor = np.concatenate([np.zeros(t.size), g_a])
        order = np.argsort(L, kind="stable")
        L, R, kind, strength, dur, lvl, ctx, anchor = (a[order] for a in (L, R, kind, strength, dur, lvl, ctx, anchor))
        # strictly ordered objects: every one ends before the next begins
        if L.size > 1:
            for _ in range(3):
                bad = np.flatnonzero(R[:-1] >= L[1:])
                if not bad.size:
                    break
                drop = np.zeros(L.size, bool)
                for b in bad:
                    a, c2 = b, b + 1
                    pa, pb = _PRIORITY[kind[a]], _PRIORITY[kind[c2]]
                    victim = c2 if pa >= pb else a
                    if kind[victim] == KIND_EDGE and (L[victim] == 0.0 or R[victim] == D):
                        victim = a if victim == c2 else c2
                    drop[victim] = True
                keep = ~drop
                L, R, kind, strength, dur, lvl, ctx, anchor = (a[keep] for a in (L, R, kind, strength, dur, lvl, ctx, anchor))
        centres = sig.centres
        miss = ~np.isfinite(lvl)
        lvl[miss] = np.interp(0.5 * (L[miss] + R[miss]), centres, sig.level)
        miss = ~np.isfinite(ctx)
        ctx[miss] = lvl[miss]
        # low in a deep, strong valley or a pause, high in loud sound; never
        # a reward, so that no boundary is drawn to a pause for its own sake
        # (whether a pause suits the text there is the pause prior's say)
        bcost = np.clip(lvl, 0.0, 1.0) * (1.0 - np.clip(strength, 0.0, 1.0))
        ends = (kind == KIND_EDGE) & ((L == 0.0) | (R == D))
        bcost[ends] = 0.0
        # a boundary in loud sound is bad only as far as the envelope is
        # believed at all
        bcost = bcost * act.evidence
        return CandidateSet(L, R, kind, strength, dur, lvl, ctx, bcost, anchor,
                            act.A(L), act.A(R), act.S(L), act.S(R),
                            np.concatenate([[0.0], np.cumsum(anchor * (1.0 + o.swallow_length * np.maximum(
                                dur - o.anchor_full_s, 0.0) / o.anchor_full_s))]))


# ============================================================ duration model
class RateCurve:
    """A local speaking rate (text weight per second of speech), smooth in
    time, re-estimated from each pass for the next -- so the next pass can
    ask a word to agree with the rate around it without a second-order DP."""

    def __init__(self, t: np.ndarray, log_rate: np.ndarray):
        self.t = t
        self.lr = log_rate

    @classmethod
    def constant(cls, rate: float) -> "RateCurve":
        return cls(np.array([0.0, 1.0]), np.full(2, math.log(max(rate, 1e-9))))

    def log_rate_at(self, t) -> np.ndarray:
        return np.interp(t, self.t, self.lr)

    @classmethod
    def from_intervals(cls, starts, ends, weights, act: Activity, D: float, window: float,
                       R0: float, shrink: float, clip: float) -> "RateCurve":
        starts = np.asarray(starts, float)
        ends = np.asarray(ends, float)
        sp = np.maximum(act.S(ends) - act.S(starts), 0.02)
        mids = 0.5 * (starts + ends)
        h = max(window / 4.0, 0.05)
        nb = max(2, int(math.ceil(D / h)) + 1)
        bi = np.clip((mids / h).astype(np.int64), 0, nb - 1)
        W = np.bincount(bi, weights=np.asarray(weights, float), minlength=nb)
        S = np.bincount(bi, weights=sp, minlength=nb)
        sig = 2.0                        # bins: a Gaussian of window/2 seconds
        r = int(math.ceil(3 * sig))
        k = np.exp(-0.5 * (np.arange(-r, r + 1) / sig) ** 2)
        Wc = np.convolve(W, k, mode="same") if nb >= k.size else np.full(nb, W.sum())
        Sc = np.convolve(S, k, mode="same") if nb >= k.size else np.full(nb, S.sum())
        lr0 = math.log(max(R0, 1e-9))
        with np.errstate(divide="ignore", invalid="ignore"):
            lr = np.where((Sc > 1e-9) & (Wc > 1e-9), np.log(Wc / np.maximum(Sc, 1e-12)), lr0)
        # little data nearby: lean on the global rate
        trust = Sc / (Sc + 1.0)
        lr = trust * lr + (1 - trust) * lr0
        lr = (1 - shrink) * lr + shrink * lr0
        lr = np.clip(lr, lr0 - math.log(clip), lr0 + math.log(clip))
        return cls((np.arange(nb) + 0.5) * h, lr)


class InitialDurationModel:
    """A global rate (text weight per second of SPEECH, the silences left
    out), the expected duration of every token, and the proportional first
    guess -- laid over the speech regions only, so a long silence stays
    unassigned from the start."""

    def __init__(self, opts: AlignmentOptions):
        self.o = opts

    def global_rate(self, weights: np.ndarray, act: Activity, D: float):
        total_w = float(weights.sum())
        if act.speech.any():
            idx = np.flatnonzero(act.speech)
            onset = float(idx[0] / (act.edges.size - 1) * D)
            offset = float((idx[-1] + 1) / (act.edges.size - 1) * D)
        else:
            onset, offset = 0.0, D
        sp = float(act.S(offset) - act.S(onset))
        if sp < 0.05 * D or sp <= 0:
            sp, onset, offset = D, 0.0, D
        return total_w / max(sp, 1e-6), onset, offset

    @staticmethod
    def proportional(weights: np.ndarray, act: Activity, t0: float, t1: float) -> np.ndarray:
        """Boundary times (len n+1) laying the weights over the speech time
        between t0 and t1."""
        cw = np.concatenate([[0.0], np.cumsum(weights)])
        tot = cw[-1] if cw[-1] > 0 else 1.0
        s0, s1 = act.S(t0), act.S(t1)
        out = act.S_inv(s0 + (s1 - s0) * cw / tot)
        out[0], out[-1] = t0, t1
        return out


# ============================================================ the DP
@dataclass
class Units:
    """Things to place in order: words, or groups of words at a coarser level."""
    loge_g: np.ndarray      # log expected duration from the global rate
    sig_g: np.ndarray
    loge_l: np.ndarray      # ... from the local rate curve
    sig_l: np.ndarray
    use_l: bool
    loge_n: np.ndarray      # ... from the neighbours' rate
    sig_n: np.ndarray
    use_n: bool
    dmin: np.ndarray        # hard limits on the raw duration
    dmax: np.ndarray
    prior: np.ndarray       # pause preference after the unit
    plen: np.ndarray        # ... and how long a pause there is apt to be
    lam_in: np.ndarray      # how many pauses the text expects inside each
    count: np.ndarray       # how many words each holds
    rate_var: np.ndarray    # how far its rate may stray from its neighbour's
    speech_time: bool       # durations measured in speech time (units)
    wg: float               # the share of the global-rate term
    activity: bool          # the activity term applies (words)
    scale: float            # seconds that make one "word's worth"

    @property
    def n(self) -> int:
        return self.loge_g.size


@dataclass
class DPResult:
    path: np.ndarray        # candidate index of every boundary (n + 1)
    cost: float
    hits: bool              # the path touched the edge of its band
    marg: list              # [(lo, min-marginals)] per boundary, or []
    beam: list = field(default_factory=list)   # [(candidates, best cost)] per boundary
    lo: Optional[np.ndarray] = None     # the band it was solved in
    hi: Optional[np.ndarray] = None


class DynamicProgrammingAligner:
    """The monotonic DP over boundary OBJECTS.  Boundary i of n+1 is the start
    of token i (and the end of token i-1); token i occupies
    [R[b_i], L[b_i+1]].  DP[i][j] = the best cost of the first i tokens with
    token i-1 ending at candidate j.  Every step is vectorised over the band
    of j (Sakoe-Chiba, around the level above) and over the predecessors k a
    token's duration limits allow, so a step costs band x transitions and the
    whole pass words x band x transitions.  With `marginals`, a backward pass
    gives min-marginals: the cost of the best path forced through each
    (boundary, candidate) -- whence the margin and the uncertainty interval."""

    def __init__(self, opts: AlignmentOptions, evidence: float):
        self.o = opts
        self.ev = evidence

    def _cost(self, U: Units, C: CandidateSet, i: int, K: np.ndarray, Jc: np.ndarray):
        """The cost of unit i running from candidate K to candidate Jc (any
        two arrays that broadcast together), and its log duration.  Every
        term of the objective is here, so the dense band and the beam below
        cannot disagree about what a segmentation costs."""
        o = self.o
        ev = self.ev
        draw = C.L[Jc] - C.R[K]
        if U.speech_time:
            d = np.maximum(C.SL[Jc] - C.SR[K], 1e-3)
        else:
            d = np.maximum(draw, 1e-4)
        ld = np.log(d)
        # log-normal durations: -log N(log d; log e, sigma), in nats, for
        # the global rate, the local one and the neighbours' -- a sum of
        # quadratics in log d, so one quadratic (a ld^2 + b ld + c)
        a2 = b1 = c0 = 0.0
        for w, m, sg, on in ((0.5 * o.w_duration * U.wg, U.loge_g[i], U.sig_g[i], True),
                             (0.5 * o.w_rate, U.loge_l[i], U.sig_l[i], U.use_l),
                             (0.5 * o.w_smooth, U.loge_n[i], U.sig_n[i], U.use_n)):
            if on and w > 0:
                k = w / (sg * sg)
                a2 += k
                b1 -= 2.0 * k * m
                c0 += k * m * m
        cost = (a2 * ld + b1) * ld + c0
        wact = o.w_activity * ev
        if U.activity and wact > 0:
            # a word laid over silence: the share of it the envelope calls quiet
            mean_act = (C.AL[Jc] - C.AR[K]) / np.maximum(draw, 1e-6)
            sil = np.clip(1.0 - mean_act, 0.0, 1.0)
            cost = cost + wact * sil * sil
        if o.w_anchor > 0:
            # the pauses a unit swallows, as a Poisson count against what its
            # inner breaks expect (a word almost none, a sentence with two
            # commas about one) -- charged only for an EXCESS: fewer pauses
            # than the text allows is no evidence of anything (a reader may
            # simply not pause), and rewarding it would pull every long unit
            # towards swallowing as many pauses as it can
            lam = max(float(U.lam_in[i]), 1e-6)
            strad = np.maximum(C.P[Jc] - C.P[K + 1], 0.0)
            if strad.max(initial=0.0) > lam:
                f = strad * (-math.log(lam)) + _log_factorial(strad)
                f0 = lam * (-math.log(lam)) + float(_log_factorial(np.array(lam)))
                cost = cost + o.w_anchor * np.where(strad > lam, np.maximum(f - f0, 0.0), 0.0)
        endc = o.w_boundary * C.bcost[Jc]
        if i < U.n - 1 and o.w_pause > 0:
            # the pause prior, in nats: the boundary is a pause with
            # probability `a` (what the envelope says), and the text expects
            # one with probability `pr` (what the punctuation says)
            pr = min(max(float(U.prior[i]), 0.005), 0.995)
            a = C.anchor[Jc]
            endc = endc + o.w_pause * self._pause_prior(pr, a, C.dur[Jc], float(U.plen[i]))
        return cost + endc, ld

    def _pause_prior(self, pr: float, a, dur, plen: float):
        """The pause prior of one boundary, in nats: it is a pause with
        probability `a` (what the envelope says) lasting `dur`, and the text
        expects one there with probability `pr`, apt to last `plen` beyond
        anchor_full_s.  A pause longer than its break is apt to have is that
        much less likely -- but never by more than pause_length_cap nats (see
        AlignmentOptions): a long pause where the text has no mark is a
        hesitation, dear but not impossible."""
        o = self.o
        longer = np.minimum(np.maximum(dur - o.anchor_full_s, 0.0) / max(plen, 1e-3),
                            o.pause_length_cap)
        return -np.log(a * pr * np.exp(-longer) + (1.0 - a) * (1.0 - pr) + 1e-12)

    def _step(self, U: Units, C: CandidateSet, i: int, lo: np.ndarray, hi: np.ndarray):
        """The cost of unit i from every candidate k of boundary i to every
        candidate j of boundary i+1 its duration limits allow: J (the j's),
        idx (J x Kw: the k's, padded), valid, the cost, and the log duration.
        None when no transition is possible."""
        L, R = C.L, C.R
        plo, phi = lo[i], hi[i]
        J = np.arange(lo[i + 1], hi[i + 1] + 1)
        Lj = L[J]
        klo = np.searchsorted(R, Lj - U.dmax[i], side="left")
        khi = np.searchsorted(R, Lj - U.dmin[i], side="right") - 1
        np.maximum(klo, plo, out=klo)
        np.minimum(khi, np.minimum(J - 1, phi), out=khi)
        width = khi - klo + 1
        Kw = int(width.max()) if width.size else 0
        if Kw <= 0:
            return None
        ar = np.arange(Kw)
        valid = ar[None, :] < width[:, None]
        idx = klo[:, None] + ar[None, :]
        idx = np.where(valid, idx, klo[:, None])
        np.clip(idx, plo, phi, out=idx)
        cost, ld = self._cost(U, C, i, idx, J[:, None])
        cost[~valid] = _INF
        return J, idx, valid, cost, ld, klo, width

    def _start(self, U: Units, C: CandidateSet, lo, hi):
        ks = np.arange(lo[0], hi[0] + 1)
        return self.o.w_unassigned * self.ev * C.AR[ks] / U.scale + self.o.w_boundary * C.bcost[ks]

    def _finish(self, U: Units, C: CandidateSet, lo, hi, A_end):
        J = np.arange(lo[U.n], hi[U.n] + 1)
        return J, self.o.w_unassigned * self.ev * (A_end - C.AL[J]) / U.scale

    def solve(self, U: Units, C: CandidateSet, lo: np.ndarray, hi: np.ndarray,
              A_end: float, marginals: bool = False) -> Optional[DPResult]:
        if U.speech_time and self.o.rate_state:
            return self.solve_rated(U, C, lo, hi, A_end)
        n = U.n
        F = self._start(U, C, lo, hi)
        bps = []
        store = []
        Fs = [F] if marginals else None
        for i in range(n):
            st = self._step(U, C, i, lo, hi)
            if st is None:
                return None
            J, idx, valid, cost, _, klo, width = st
            tot = F[idx - lo[i]] + cost
            a = np.argmin(tot, axis=1)
            rows = np.arange(J.size)
            Fn = tot[rows, a]
            # the backpointers are the one thing kept for every word and
            # every candidate of its band, and on hours of speech the
            # largest thing the process holds: a candidate's index fits in
            # 32 bits, and half the bytes is half of that
            bps.append(idx[rows, a].astype(np.int32))
            if marginals:
                store.append((klo, width, cost.astype(np.float32)))
                Fs.append(Fn)
            F = Fn
            if not np.isfinite(F).any():
                return None
        J, fin = self._finish(U, C, lo, hi, A_end)
        tot = F + fin
        jb = int(np.argmin(tot))
        best = float(tot[jb])
        if not math.isfinite(best):
            return None
        path = np.empty(n + 1, np.int64)
        path[n] = J[jb]
        for i in range(n - 1, -1, -1):
            path[i] = bps[i][path[i + 1] - lo[i + 1]]
        marg = []
        if marginals:
            # the backward pass: B[k] = the best cost of the rest from
            # candidate k of boundary i; F + B is the min-marginal
            B = fin
            margs = [None] * (n + 1)
            margs[n] = (int(lo[n]), Fs[n] + B)
            for i in range(n - 1, -1, -1):
                klo, width, cost = store[i]
                plo, phi = lo[i], hi[i]
                vals = cost + B[:, None]
                ar = np.arange(cost.shape[1])
                valid = ar[None, :] < width[:, None]
                tgt = (klo[:, None] + ar[None, :]) - plo
                out = np.full(phi - plo + 1, _INF)
                np.minimum.at(out, tgt[valid], vals[valid])
                B = out
                margs[i] = (int(plo), Fs[i] + B)
            marg = margs
        return DPResult(path, best, False, marg)

    def _prune(self, sel: np.ndarray, cand: np.ndarray, cost: np.ndarray, L: np.ndarray) -> np.ndarray:
        """Which states of the rate-aware beam survive a unit (indices into
        `sel`'s arrays, sorted).  THE BEAM IS LOCAL IN TIME.  States that
        stand at different times are not comparable by their cost so far:
        one that has read the text too fast stands early, has swallowed
        less sound and fewer pauses, and looks cheap -- until the end, where
        the sound it left over is charged all at once.  Compared with every
        other state it would push the right ones, later in time, out of the
        beam for good.  So a state is measured against the best within
        `rate_beam_window_s` of it (and only loosely, `rate_beam_global`,
        against the best of all); each candidate keeps its best few rates;
        and when there are still too many, the cap is shared out over the
        windows -- the best of every window first, then the second best,
        and so on -- so that it buys different places in time rather than
        many rates at one place."""
        o = self.o
        if sel.size == 0:
            return sel
        c = cost[sel]
        keep = c <= c.min() + max(o.rate_beam_global, o.rate_beam)
        # the best within a window either side: bins of the window's width,
        # and each bin's best against its own and its two neighbours'
        t = L[cand[sel]]
        W = max(o.rate_beam_window_s, 1e-3)
        b = np.floor((t - t.min()) / W).astype(np.int64)
        nbin = int(b.max()) + 1
        best = np.full(nbin + 2, np.inf)
        np.minimum.at(best, b + 1, np.where(keep, c, np.inf))
        near = np.minimum(np.minimum(best[:-2], best[1:-1]), best[2:])
        keep &= c <= near[b] + o.rate_beam
        # the best few rates of each candidate
        cs = cand[sel]
        rank = np.lexsort((c, cs))
        srt = cs[rank]
        pos = np.empty(sel.size, np.int64)
        pos[rank] = np.arange(srt.size) - np.searchsorted(srt, srt, side="left")
        if o.rate_per_candidate > 0:
            keep &= pos < o.rate_per_candidate
        idx = np.flatnonzero(keep)
        if idx.size > o.rate_beam_states:
            # the cap, shared over the windows: rank within its bin first
            bb = b[idx]
            order = np.lexsort((c[idx], bb))
            sb = bb[order]
            r_in = np.empty(idx.size, np.int64)
            r_in[order] = np.arange(sb.size) - np.searchsorted(sb, sb, side="left")
            part = np.lexsort((c[idx], r_in))[:o.rate_beam_states]
            idx = np.sort(idx[part])
        return sel[idx]

    def solve_rated(self, U: Units, C: CandidateSet, lo: np.ndarray, hi: np.ndarray,
                    A_end: float) -> Optional[DPResult]:
        """The same DP for the level above words (sentences, pieces), with the
        speaking PACE in the state.  A unit's own rate (its expected length
        over its length in speech time) is the pace plus that unit's own
        scatter -- its words' lengths, its punctuation, a number read out --
        and the pace itself moves slowly: a Huber step from one unit's pace
        to the next (Gaussian for the wander `rate_drift` allows over the
        time between them, linear beyond), pulled back towards the global
        rate as far as that time makes it forget (an Ornstein-Uhlenbeck
        chain), or, rarely, a JUMP to a new pace at a fixed price.  Keeping
        the scatter out of the pace matters: when a unit's own rate was the
        state, every sentence's scatter became a step of the pace, the
        steps added up to a random walk that could wander anywhere, and a
        path that read a minute of text a third too fast and the next a
        third too slow cost next to nothing -- on real speech that was the
        commonest way to land ten seconds off (docs/wavealign.md, section
        8).  The global rate is the prior of the first unit's pace.

        The states (candidate, pace) are searched as a BEAM (_prune): after
        each unit only those near the best at about the same time survive,
        at most `rate_beam_states` of them, so the work follows the
        ambiguity rather than the length of the recording -- hours of
        sentences are aligned in one pass with no coarser level to go wrong
        first.  The words, many, get the rate as a curve instead."""
        o = self.o
        n = U.n
        L, R = C.L, C.R
        q = np.arange(-o.rate_q_max, o.rate_q_max + 1e-9, o.rate_q_step)
        Q = q.size
        # the global rate enters once, as the prior of the first unit's
        # rate; after that each rate is drawn from the one before it,
        # pulled back towards the global one as far as the time between
        # them makes the pace forget (an Ornstein-Uhlenbeck chain) -- a
        # prior on every unit's rate would count the same belief once per
        # unit, and hold a long slow stretch to the average
        U = replace(U, wg=0.0)
        te = np.exp(U.loge_g)
        gap = 0.5 * (te[1:] + te[:-1])
        phi = np.concatenate([[0.0], np.exp(-gap / o.rate_revert_s)])
        # the spread of a step: each unit's own noise (U.rate_var: its words'
        # scatter and its sentences' ways, averaged over it) and the wander
        # of the pace over the time between the two
        qv = np.concatenate([[0.0], o.rate_drift ** 2 * gap])
        # boundary 0: the candidates the band allows, with no rate yet --
        # PRUNED LIKE EVERY LATER BOUNDARY.  Kept whole, the first unit was
        # expanded from all of them over all its transitions: a band of
        # minutes over a grid of half-seconds, squared, which on a long
        # stretch with few pieces was gigabytes for that one step
        js = np.arange(lo[0], hi[0] + 1)
        F = self._start(U, C, lo, hi)
        keep0 = self._prune(np.arange(js.size), js, F, C.L)
        js, F = js[keep0], F[keep0]
        js0 = js.copy()
        qs = np.full(js.size, -1, np.int64)
        hist = []                               # (j, q, parent) per boundary
        beam = [(js.copy(), F.copy())]          # (j, best cost into it) per boundary
        for i in range(n):
            # the candidates the surviving states stand at, each once --
            # what a unit costs depends on where it starts and ends, not on
            # the pace it is read at -- stretched over the candidates the
            # unit may end at
            uj, inv = np.unique(js, return_inverse=True)
            jlo = np.searchsorted(L, R[uj] + U.dmin[i], side="left")
            jhi = np.searchsorted(L, R[uj] + U.dmax[i], side="right") - 1
            jlo = np.maximum(np.maximum(jlo, uj + 1), lo[i + 1])
            jhi = np.minimum(jhi, hi[i + 1])
            w = np.maximum(jhi - jlo + 1, 0)
            tot_u = int(w.sum())
            if tot_u == 0:
                return None
            pu = np.repeat(np.arange(uj.size), w)
            offu = np.concatenate([[0], np.cumsum(w)[:-1]])
            pj_u = jlo[pu] + (np.arange(tot_u) - offu[pu])
            cost_u, ld_u = self._cost(U, C, i, uj[pu], pj_u)
            # ... and then every state over its candidate's transitions
            ws = w[inv]
            tot_n = int(ws.sum())
            if tot_n == 0:
                return None
            ps = np.repeat(np.arange(js.size), ws)
            offs = np.concatenate([[0], np.cumsum(ws)[:-1]])
            pair = offu[inv][ps] + (np.arange(tot_n) - offs[ps])
            pj = pj_u[pair]
            cost = cost_u[pair]
            rho = U.loge_g[i] - ld_u[pair]      # this unit's log-rate
            prev_q = qs[ps]
            if o.rate_latent:
                # the state holds the PACE, and a unit's own rate is the
                # pace plus that unit's scatter: see _pace_step
                if i == 0:
                    m = np.zeros(rho.size)
                    a = o.rate_global_sigma
                    wa = 0.5 * o.w_duration
                else:
                    m = phi[i] * q[np.maximum(prev_q, 0)]
                    a = max(math.sqrt(qv[i]), o.rate_drift_min)
                    wa = o.w_rate_step
                x, c_pace, c_unit = _pace_step(rho, m, a, math.sqrt(U.rate_var[i]), o.rate_huber)
                if i > 0 and o.rate_jump_nats > 0:
                    # ... or the pace JUMPS: a new chapter, a new day at the
                    # microphone, a speed set by hand.  Rare, so it costs a
                    # fixed rate_jump_nats (and a little for its size), but
                    # then the new pace is simply this unit's own
                    jump = (o.rate_jump_nats + np.abs(rho - m) / o.rate_jump_scale) / wa
                    j_ = jump < c_pace + c_unit
                    x = np.where(j_, rho, x)
                    c_pace = np.where(j_, jump, c_pace)
                    c_unit = np.where(j_, 0.0, c_unit)
                cost = cost + wa * c_pace + o.w_rate_step * c_unit
                pq = np.clip(np.rint((x + o.rate_q_max) / o.rate_q_step), 0, Q - 1).astype(np.int64)
            else:
                pq = np.clip(np.rint((rho + o.rate_q_max) / o.rate_q_step), 0, Q - 1).astype(np.int64)
                if i == 0:
                    cost = cost + (0.5 * o.w_duration) * (rho / o.rate_global_sigma) ** 2
                else:
                    sd = math.sqrt(U.rate_var[i] + U.rate_var[i - 1] + qv[i])
                    step = np.where(prev_q >= 0, q[pq] - phi[i] * q[np.maximum(prev_q, 0)], 0.0)
                    cost = cost + o.w_rate_step * _huber(step, sd, o.rate_huber)
            tot = F[ps] + cost
            # the best way into each (candidate, rate): the least cost of
            # every key, and the first transition that reaches it
            key = pj * Q + pq
            kmin = int(key.min())
            span = int(key.max()) - kmin + 1
            kk = key - kmin
            bestk = np.full(span, _INF)
            np.minimum.at(bestk, kk, tot)
            win = np.flatnonzero(tot <= bestk[kk])
            firstk = np.full(span, tot_n, np.int64)
            np.minimum.at(firstk, kk[win], win)
            uk = np.flatnonzero(firstk < tot_n)
            pick = firstk[uk]
            uk = uk + kmin
            nF = tot[pick]
            keep = np.isfinite(nF)
            if not keep.any():
                return None
            sel = self._prune(np.flatnonzero(keep), uk // Q, nF, C.L)
            pick = pick[sel]
            js, qs, F = pj[pick], pq[pick], nF[sel]
            hist.append((js, qs, ps[pick]))
            srt = np.argsort(js, kind="stable")
            uj, first = np.unique(js[srt], return_index=True)
            beam.append((uj, np.minimum.reduceat(F[srt], first) if uj.size else F[:0]))
        # the end: a state at a candidate the last boundary may take
        J = js
        ok = (J >= lo[n]) & (J <= hi[n])
        if not ok.any():
            return None
        fin = o.w_unassigned * self.ev * (A_end - C.AL[J]) / U.scale
        tot = np.where(ok, F + fin, _INF)
        s_best = int(np.argmin(tot))
        best = float(tot[s_best])
        if not math.isfinite(best):
            return None
        path = np.empty(n + 1, np.int64)
        cur = s_best
        for i in range(n - 1, -1, -1):
            hj, _, hp = hist[i]
            path[i + 1] = hj[cur]
            cur = int(hp[cur])
        path[0] = int(js0[cur])             # the states of boundary 0 that survived
        return DPResult(path, best, False, [], beam)


# ============================================================ refinement
class BoundaryRefiner:
    """Pass 2 of coarse-to-fine: round every boundary the last pass chose,
    search a small window of the FINER curve (median only, no Gaussian) for
    its lowest point -- in the whole window and in each half of it -- and
    offer those as new candidates.  The DP then runs again in a narrow band,
    so no boundary moves on its own and monotonicity is never broken."""

    def __init__(self, opts: AlignmentOptions):
        self.o = opts

    def candidates(self, sig: Signal, act: Activity, times: np.ndarray, window: float):
        o = self.o
        if act.evidence <= 0 or not len(times):
            return np.zeros(0), np.zeros(0)
        rate, n = sig.rate, sig.n
        w = max(2, int(round(min(window * rate, n))))
        k = np.clip(np.round(np.asarray(times) * rate - 0.5).astype(np.int64), 0, n - 1)
        off = np.arange(-w, w + 1)
        win = np.clip(k[:, None] + off[None, :], 0, n - 1)
        vals = sig.fine[win]
        out_t, out_s = [], []
        for sl in (slice(0, 2 * w + 1), slice(0, w + 1), slice(w, 2 * w + 1)):
            sub = vals[:, sl]
            a = np.argmin(sub, axis=1)
            f = win[:, sl][np.arange(k.size), a]
            f0 = np.clip(f - 1, 0, n - 1)
            f2 = np.clip(f + 1, 0, n - 1)
            den = sig.fine[f0] - 2 * sig.fine[f] + sig.fine[f2]
            delta = np.where(den > 1e-9, 0.5 * (sig.fine[f0] - sig.fine[f2]) / np.where(den > 1e-9, den, 1), 0.0)
            t = (f + 0.5 + np.clip(delta, -0.5, 0.5)) / rate
            prom = np.minimum(vals[:, : w + 1].max(axis=1), vals[:, w:].max(axis=1)) - sig.fine[f]
            depth = np.clip((act.high - sig.fine[f]) / max(act.high - act.noise_floor, 1e-3), 0, 1)
            s = act.evidence * np.clip(prom / o.valley_full_prominence, 0, 1) ** 0.7 * (0.6 + 0.4 * depth)
            inside = act.speech[f]
            out_t.append(t[inside])
            out_s.append(s[inside] * 0.9)
        return np.concatenate(out_t), np.concatenate(out_s)


# ============================================================ confidence
class ConfidenceEstimator:
    """Structural timing confidence of every boundary -- NOT recognition.

    Six things say a boundary is where it belongs, weighed as a mean:

        0.30  the evidence under it: the strength of the pause or valley it
              sits on (a grid point has none).  Nearness to a strong
              silence is carried here, and needs no factor of its own: a
              boundary on a pause sits on its very edge
        0.25  the margin between the best segmentation and the best one that
              puts this boundary elsewhere (min-marginals -- the words' within
              the refinement's window, and the sentence level's across its
              whole band, so a sentence end that could as well be a sentence
              later is not called sure)
        0.15  how narrow the interval of near-optimal positions is
        0.15  whether it stays put when the parameters are shaken (and
              whether its sentence could move)
        0.10  whether the coarse and the fine pass agree
        0.05  how well the length of the words beside it fits the pace
              around them: the duration prior against the waveform

    and the whole scaled by 0.4 + 0.6 x the envelope's evidence, so that a
    boundary on a strong pause comes out near 0.9, one the duration prior
    mostly decided near 0.5, and one only proportional allocation put there
    near 0.2.  A factor that could not be measured -- no marginals (`marg`
    empty), no perturbation or no fine pass (`dpert` or `dcoarse` None) --
    counts as a half, never as the best it could have been: the case with
    the fewest checks must not come out the surest."""

    def __init__(self, opts: AlignmentOptions):
        self.o = opts

    def run(self, C: CandidateSet, path, marg, dpert, dcoarse, durfit, evidence: float, D: float,
            resolution: float, margin_cap=None, spans=None):
        o = self.o
        nb = path.size
        L = C.L[path]
        R = C.R[path]
        ev = np.clip(C.strength[path], 0, 1)
        lo_L, hi_L, lo_R, hi_R = L.copy(), L.copy(), R.copy(), R.copy()
        # no alternative within the marginals' band is a wide margin; no
        # marginals at all is no margin known
        margin = np.full(nb, 10.0 if marg else 0.0)
        clipped = np.zeros(nb, bool)
        if marg:
            for b in range(nb):
                lo, M = marg[b]
                best = float(np.min(M))
                if not math.isfinite(best):
                    continue
                cand = np.arange(lo, lo + M.size)
                near = M - best <= o.uncertainty_cost
                if near.any():
                    cl, cr = C.L[cand[near]], C.R[cand[near]]
                    lo_L[b] = min(lo_L[b], cl.min()); hi_L[b] = max(hi_L[b], cl.max())
                    lo_R[b] = min(lo_R[b], cr.min()); hi_R[b] = max(hi_R[b], cr.max())
                    nz = np.flatnonzero(near)
                    clipped[b] = nz[0] == 0 or nz[-1] == M.size - 1
                far = np.abs(C.L[cand] - L[b]) > o.margin_tol_s
                if far.any():
                    fm = M[far]
                    fm = fm[np.isfinite(fm)]
                    if fm.size:
                        margin[b] = float(fm.min()) - best
        if margin_cap is not None:
            # the unit level's own margin and near-optimal span, where it
            # has one: an alternative a sentence away counts too
            margin = np.minimum(margin, margin_cap)
            ok = np.isfinite(spans[:, 0])
            lo_L[ok] = np.minimum(lo_L[ok], spans[ok, 0])
            hi_L[ok] = np.maximum(hi_L[ok], spans[ok, 1])
            lo_R[ok] = np.minimum(lo_R[ok], spans[ok, 2])
            hi_R[ok] = np.maximum(hi_R[ok], spans[ok, 3])
        lo_L = np.maximum(0.0, np.minimum(lo_L, L - resolution))
        hi_L = np.minimum(D, np.maximum(hi_L, L + resolution))
        lo_R = np.maximum(0.0, np.minimum(lo_R, R - resolution))
        hi_R = np.minimum(D, np.maximum(hi_R, R + resolution))
        width = 0.5 * ((hi_L - lo_L) + (hi_R - lo_R))
        mconf = 1.0 - np.exp(-np.maximum(margin, 0) / o.margin_scale)
        half = np.full(nb, 0.5)
        uconf = np.exp(-np.maximum(width - 2 * resolution, 0) / 0.3) if marg else half
        pconf = half if dpert is None else np.exp(-np.asarray(dpert) / 0.1)
        gconf = half if dcoarse is None else np.exp(-np.asarray(dcoarse) / 0.15)
        conf = 0.05 + 0.9 * (0.30 * ev + 0.25 * mconf + 0.15 * uconf + 0.15 * pconf
                             + 0.10 * gconf + 0.05 * durfit)
        conf *= 0.4 + 0.6 * evidence
        return np.clip(conf, 0, 1), lo_L, hi_L, lo_R, hi_R, margin, clipped


# ============================================================ the hierarchy
class HierarchicalAligner:
    """Units, then words.  The units come from the text alone: sentences
    and pieces (paragraphs end sentences too), a long one split at its
    strongest inner break, short ones merged forward but never across a
    sentence end.  They are aligned first, over coarse candidates, by the
    rate-aware beam; the words are then aligned in a band around them, at
    the rate each unit was found to be read at.  A long recording is thus
    pinned at its pauses and sentence ends before a single word is placed,
    which keeps the error of proportional allocation from drifting over the
    hours -- and keeps the cost linear in the words."""

    def __init__(self, opts: AlignmentOptions):
        self.o = opts

    # ---- text structure
    def build_units(self, model: TranscriptModel, e: np.ndarray):
        o = self.o
        n = model.n
        cuts = [0]
        for i in range(n - 1):
            if model.cut[i]:
                cuts.append(i + 1)
        cuts.append(n)
        ce = np.concatenate([[0.0], np.cumsum(e)])

        def split(a, b, out):
            if b - a <= 1 or ce[b] - ce[a] <= o.unit_max_s:
                out.append((a, b))
                return
            pr = model.prior[a:b - 1]
            best = pr.max()
            pos = np.arange(a + 1, b)
            midt = 0.5 * (ce[a] + ce[b])
            if best > 0:
                cand = pos[pr >= best - 1e-9]
            else:
                cand = pos
            c = int(cand[np.argmin(np.abs(ce[cand] - midt))])
            split(a, c, out)
            split(c, b, out)

        units = []
        for a, b in zip(cuts[:-1], cuts[1:]):
            if b > a:
                split(a, b, units)
        # merge the short ones forward -- but never across a cut (a sentence
        # end, a book's piece end): the pauses a unit may swallow are what
        # its inner breaks expect, and a sentence end inside a unit would let
        # a long pause fall anywhere in it
        merged = []
        for a, b in units:
            if merged:
                pa, pb = merged[-1]
                short = (ce[pb] - ce[pa] < o.unit_min_s) or (ce[b] - ce[a] < o.unit_min_s)
                if (short and not model.cut[pb - 1]
                        and ce[b] - ce[pa] <= o.unit_max_s * 1.5):
                    merged[-1] = (pa, b)
                    continue
            merged.append((a, b))
        return merged


# ============================================================ the engine
class _Engine:
    def __init__(self, opts: AlignmentOptions):
        self.o = opts
        self.timing = {}

    def _tick(self, name, t0):
        self.timing[name] = self.timing.get(name, 0.0) + (time.perf_counter() - t0)
        return time.perf_counter()

    # ---- building the units of one level
    def _units(self, groups, model, e_g, e_l, e_n, speech_time: bool, R0: float, scale: float,
               D: float, n_total: int, relaxed: bool = False) -> Units:
        o = self.o
        G = len(groups)
        a = np.array([g[0] for g in groups], np.int64)
        b = np.array([g[1] for g in groups], np.int64)
        cg = np.concatenate([[0.0], np.cumsum(e_g)])
        eg = cg[b] - cg[a]
        cl = np.concatenate([[0.0], np.cumsum(e_l)]) if e_l is not None else cg
        el = cl[b] - cl[a]
        cnt = (b - a).astype(float)
        if speech_time:
            # a group's length in speech time: the words' own scatter
            # averages out, the rate's does not
            sig = np.sqrt(o.sigma_rate ** 2 / cnt + o.sigma_rate_variation ** 2)
            sig_g = sig
            sig_l = sig
            dmin = el * np.exp(-3 * sig) * 0.8
            dmax = (el * np.exp(3 * sig) * 1.3 + 2.0) * 1.5
            prior = model.prior[b - 1].copy()
            cp = np.concatenate([[0.0], np.cumsum(model.prior)])
            lam = (cp[b - 1] - cp[a]) + o.pause_prob_inside * cnt
            # the spread of a unit's rate: its words' scatter and its
            # sentences' own ways average out over it, and so does the pace
            # itself over a unit much longer than the pace holds
            cs = np.concatenate([[0], np.cumsum(model.level >= BREAK_SENTENCE)])
            sents = np.maximum(cs[b - 1] - cs[a], 0) + 1.0
            rvar = o.sigma_rate ** 2 / cnt + o.rate_unit_sigma ** 2 / sents
        else:
            sig_g = np.full(G, o.sigma_duration)
            sig_l = np.full(G, o.sigma_rate)
            min_word = min(o.min_word_s, 0.25 * D / (n_total + 1))
            dmin = np.maximum(min_word, o.dmin_ratio * el)
            # the slack above the expected length is in seconds (a short word
            # can be drawn out), but never more than a few words' worth of
            # the recording -- else a transcript far too long for its sound
            # would give every word the whole stretch to choose from
            extra = min(o.dmax_extra_s, 3.0 * D / (n_total + 1))
            dmax = np.maximum(o.dmax_ratio * el, el + extra)
            prior = model.prior[b - 1].copy()
            lam = np.full(G, o.pause_prob_inside)
            rvar = np.full(G, o.sigma_rate ** 2)
        if relaxed:
            dmin = np.full(G, 1e-6)
            dmax = np.full(G, 2.0 * D + 1.0)
        prior[-1] = 1.0
        en = None
        if e_n is not None:
            cn = np.concatenate([[0.0], np.cumsum(e_n)])
            en = cn[b] - cn[a]
        return Units(np.log(np.maximum(eg, 1e-4)), sig_g,
                     np.log(np.maximum(el, 1e-4)), sig_l, e_l is not None,
                     np.log(np.maximum(en, 1e-4)) if en is not None else np.zeros(G),
                     np.full(G, o.sigma_smooth), en is not None,
                     dmin, dmax, prior, model.plen[b - 1].copy(), lam, cnt, rvar, speech_time,
                     o.global_share if e_l is not None else 1.0, not speech_time, scale)

    # ---- the band around centres
    @staticmethod
    def _band(C: CandidateSet, centres: np.ndarray, widths: np.ndarray, soft: bool = False):
        """Candidate index ranges [lo, hi] of every boundary: the candidates
        within `widths` of `centres`, made monotonic and leaving room for
        the boundaries before and after.  With `soft`, also which of the
        range ends were set by the width (and not by the ends or by room),
        so a path pressed against one can be told apart."""
        m = C.m
        nb = centres.size
        n = nb - 1
        lo0 = np.searchsorted(C.L, centres - widths, side="left")
        hi0 = np.searchsorted(C.L, centres + widths, side="right") - 1
        i = np.arange(nb)
        lo = np.clip(lo0, i, m - 1 - n + i)
        hi = np.clip(hi0, i, m - 1 - n + i)
        lo = np.maximum.accumulate(lo)
        hi = np.minimum.accumulate(hi[::-1])[::-1]
        hi = np.maximum(hi, lo)
        lo, hi = lo.astype(np.int64), hi.astype(np.int64)
        if not soft:
            return lo, hi
        slo = (lo == lo0) & (lo0 > i)
        shi = (hi == hi0) & (hi0 < m - 1 - n + i)
        return lo, hi, slo, shi

    def _solve(self, dp, U, C, centres, widths, A_end, marginals=False, diag=None, name="",
               retries: Optional[int] = None, relax: bool = True):
        """The DP in the band; a path pressed against the band's edge (set by
        the width, not by the ends) is solved again in a band 2.5 times as
        wide, `retries` times.  (Widening only round the boundaries that
        touched the edge was tried, to save time on long recordings, and
        cost real speech 0.01-0.02 s: a wider band finds better paths away
        from the touch too.)  With nothing feasible, and `relax`, it is
        solved once more with the duration limits loosened."""
        o = self.o
        res = None
        if C.m < centres.size:
            # FEWER PLACES THAN BOUNDARIES: n + 1 boundaries need n + 1
            # candidates, each after the last, and a mostly silent stretch
            # (nothing but a pause's own edges is left inside a pause) can
            # hold fewer.  No band can be drawn -- the ranges would run into
            # negative indices -- so this level has no answer, and the
            # caller goes on without it: the units are skipped, the words
            # fall back to the proportional guess.
            return None
        w = widths.copy()
        retries = o.band_retries if retries is None else retries
        for attempt in range(retries + 1):
            lo, hi, slo, shi = self._band(C, centres, w, soft=True)
            got = dp.solve(U, C, lo, hi, A_end, marginals)
            if got is None and res is not None:
                # A WIDER BAND IS NOT ALWAYS A BETTER ONE for the beam: the
                # plain DP's wider band holds every path of the narrower,
                # but the beam's pruning can lose them all where a long
                # silence leaves one state to cross it.  The answer that
                # touched the narrower band's edge is still an answer, and
                # far better than none: throwing it away dropped the whole
                # sentence level and left the words to find their way alone.
                break
            res = got
            if res is not None:
                res.lo, res.hi = lo, hi
                p = res.path
                res.hits = bool(np.any(((p == lo) & slo) | ((p == hi) & shi)))
                if not res.hits:
                    break
            if diag is not None:
                diag.setdefault("band_retries", {}).setdefault(name, 0)
                diag["band_retries"][name] += 1
            if attempt < retries:
                w = w * 2.5
        if res is None and relax:
            # nothing fits: once more with the duration limits loosened four
            # times over and the widest band tried -- never unbounded, which
            # would cost words x candidates squared
            if diag is not None:
                diag.setdefault("relaxed", []).append(name)
            U2 = replace(U, dmin=np.full(U.n, 1e-6),
                         dmax=np.maximum(4.0 * U.dmax, 4.0 * float(C.L[-1]) / max(U.n, 1)))
            lo, hi = self._band(C, centres, w)
            res = dp.solve(U2, C, lo, hi, A_end, marginals)
            if res is not None:
                res.lo, res.hi = lo, hi
        return res

    # ---- everything
    def run(self, waveform, duration, sample_times, model: TranscriptModel, want_candidates=False):
        o = self.o
        diag = {}
        t = time.perf_counter()
        sig = WaveformPreprocessor(o).run(waveform, duration, sample_times)
        t = self._tick("preprocess", t)
        act = ActivityEstimator(o).run(sig)
        t = self._tick("activity", t)
        det = PauseDetector(o).run(sig, act)
        t = self._tick("pauses", t)
        D = sig.duration
        diag.update({
            "frames": sig.n, "frame_rate": sig.rate, "native_rate": sig.native_rate,
            "dynamic_range_db": sig.dyn_range_db, "degenerate": sig.degenerate,
            "garbage_values": sig.garbage, "noise_floor": act.noise_floor,
            "speech_level": act.speech_level, "low_threshold": act.low,
            "high_threshold": act.high, "evidence": act.evidence,
            "pauses": int((det.p_role == 0).sum()), "valleys": int(det.v_time.size),
            "peaks": det.n_peaks, "speech_regions": len(act.regions),
        })
        regions = [(a, b) for a, b in act.regions]
        n = model.n
        pauses_out = self._pauses_out(det, None, None, model)
        if n == 0:
            return AlignmentResult([], regions, pauses_out, 0.0, diag), (sig, act, det, None, None)
        idm = InitialDurationModel(o)
        if act.evidence <= 0:
            # NOTHING TO HEAR, SO THE TEXT DECIDES -- and nothing else does.
            # A flat line, a muted or silent recording, a picture with no
            # range left in it: the envelope says no more than that there was
            # sound, and the answer is the proportional one over the words'
            # weights (with a confidence of 0.1, which says so).  Left
            # to the DP, the rate-aware beam would still reshape the pieces
            # on the durations alone, with no pause to hold them, and land
            # them worse than the proportion it started from.
            diag["fallback"] = "no evidence"
            return self._proportional_result(model, sig, act, det, regions,
                                             idm.proportional(model.weights, act, 0.0, D),
                                             diag, None), (sig, act, det, None, None)

        act, det, diag["dip_length"] = self._dip_length(model, sig, act, det)
        model, diag["pause_calibration"] = self._calibrate(model, det)
        R0, onset, offset = idm.global_rate(model.weights, act, D)
        e_g = model.weights / R0
        scale = float(max(np.median(e_g), 0.05))
        diag["global_rate"] = R0
        if n > o.max_words_per_s * D:
            # FAR MORE WORDS THAN ANY VOICE SAYS in this time: dozens a second,
            # where the densest real speech measured is six and a half (Chinese
            # and Japanese characters).  No envelope resolves boundaries that
            # close, the answer would be the proportional one anyway, and the
            # DP would get there in time and memory growing as the words
            # squared -- minutes and gigabytes for a mistake in the timings
            # asked about.  So it is the proportional one at once.
            diag["fallback"] = "proportional"
            return self._proportional_result(model, sig, act, det, regions,
                                             idm.proportional(e_g, act, onset, offset),
                                             diag, e_g), (sig, act, det, None, None)
        dp = DynamicProgrammingAligner(o, act.evidence)
        gen = BoundaryCandidateGenerator(o)
        A_end = float(act.cum_act[-1])
        hier = HierarchicalAligner(o)
        all_words = [(i, i + 1) for i in range(n)]
        levels = []

        # ---- the level above words: sentences (and pieces, and the phrases
        # of a long sentence), aligned all at once by the rate-aware beam.
        # A still coarser level of minute-long chunks was tried and dropped:
        # with hundreds of sentence pauses that look alike it can only follow
        # the durations, lands tens of seconds off, and the sentences are
        # then aligned in the wrong place (docs/wavealign.md, "what was
        # measured").  The sequence of sentence lengths against the
        # sequence of pauses is what pins a long recording down.
        word_centres = None
        word_widths = None
        rate_curve = None
        unit_groups = None
        unit_amb = None
        e_l = None
        # A TEXT WITH NOTHING TO CUT IT AT has no level above its words.  The
        # units are sentences, and a book's pieces; with no sentence mark, no
        # paragraph and no piece end anywhere -- an auto-caption left as
        # YouTube wrote it, lyrics, subtitles in a script whose captions carry
        # no full stop -- they could only be made up, split at a caption's
        # end or in the middle of the words, and the beam would pin those
        # made-up boundaries while every real pause had to fall inside them.
        # Measured, that was worse than the proportional guess it starts
        # from; the words aligned directly, in their wide band, are not.
        cuts = bool(model.cut[:-1].any())
        diag["units_skipped"] = not cuts
        diag["bare_text"] = model.bare
        units = hier.build_units(model, e_g) if n > o.direct_max_words and cuts else []
        if len(units) >= o.min_units:
            C = gen.build(sig, act, det, step=o.unit_step_s, pause_min_s=o.min_pause_s,
                          valley_min_strength=o.unit_valley_strength, n_words=len(units))
            uw = np.array([e_g[a:b].sum() for a, b in units])
            ucent = idm.proportional(uw, act, onset, offset)
            uwid = np.full(ucent.size, max(o.top_band_min_s, o.top_band_frac * D))
            U = self._units(units, model, e_g, None, None, True, R0, scale, D, n)
            res = self._solve(dp, U, C, ucent, uwid, A_end, diag=diag, name="units")
            t = self._tick("dp_units", t)
            if res is not None:
                us, ue = C.R[res.path[:-1]], C.L[res.path[1:]]
                unit_groups = units
                levels.append(("units", len(units), C.m))
                if o.unit_marginals and o.rate_state and res.beam:
                    unit_amb = self._unit_marginals(dp, C, U, res, res.lo, res.hi, D, A_end, act)
                    t = self._tick("unit_marginals", t)
                rate_curve = RateCurve.from_intervals(us, ue, [model.weights[a:b].sum() for a, b in units],
                                                      act, D, o.rate_window_s, R0, o.rate_shrink, o.rate_clip)
                e_l = self._group_expect(model, rate_curve, units, us, ue, act)
                word_centres, word_widths = self._interpolate(all_words, units, us, ue, e_l, act,
                                                              o.word_band_min_s, o.word_band_frac)
        if word_centres is None:
            word_centres = idm.proportional(e_g, act, onset, offset)
            # a short transcript may go anywhere; a long one with no sentence
            # to pin it gets a band of some dozens of words either side
            word_widths = np.full(n + 1, min(max(4 * o.word_band_min_s, 0.3 * D),
                                             max(0.05, 40.0 * float(np.mean(e_g)))))
            e_l = None
        # ---- the word pass.  The grid need not be finer than a sixth of a
        # word, and a transcript far shorter than the sound keeps only its
        # strongest valleys: the candidates stay in proportion to the words.
        step = max(o.fallback_step_s, scale / 6.0)
        budget = 30 * (n + 1)
        C = gen.build(sig, act, det, step=step, pause_min_s=o.min_pause_s,
                      extra_t=word_centres[1:-1], n_words=n, max_valleys=budget)
        U = self._units(all_words, model, e_g, e_l, None, False, R0, scale, D, n)
        res = self._solve(dp, U, C, word_centres, word_widths, A_end, diag=diag, name="words")
        t = self._tick("dp_words", t)
        levels.append(("words", n, C.m))
        if res is None:
            diag["fallback"] = "proportional"
            return self._proportional_result(model, sig, act, det, regions, word_centres, diag, e_g), \
                (sig, act, det, C, None)
        coarse_times = C.L[res.path].copy()
        path, cands = res.path, C
        U_words = U
        # ---- refinement: the rate from the words, finer candidates, and a
        # narrow band that is never widened -- a refinement that wanted to go
        # further than its window would be the word level overruling the
        # rate-aware level above it, which knows better
        refiner = BoundaryRefiner(o)
        # the window: refine_window_s, or a few words' worth when the words
        # are far shorter than any spoken word could be
        refine_w = max(min(o.refine_window_s, 3.0 * float(np.mean(e_g))), 2.0 / sig.rate)
        shifts = []
        final = None
        passes = max(1, o.refine_passes)
        p = 0
        settled = False
        while True:
            last = p >= passes - 1 or settled
            ws, we = cands.R[path[:-1]], cands.L[path[1:]]
            rc = RateCurve.from_intervals(ws, we, model.weights, act, D, o.rate_window_s, R0,
                                          o.rate_shrink, o.rate_clip)
            if unit_groups is not None:
                ua = np.array([g[0] for g in unit_groups])
                ub = np.array([g[1] for g in unit_groups])
                e_l = self._group_expect(model, rc, unit_groups, ws[ua], we[ub - 1], act)
            else:
                e_l = self._local_expect(model, rc, all_words, ws, we, act)
            nb = RateCurve.from_intervals(ws, we, model.weights, act, D, o.rate_short_s, R0,
                                          0.0, o.rate_clip)
            e_n = self._local_expect(model, nb, all_words, ws, we, act)
            bt = 0.5 * (cands.L[path] + cands.R[path])
            rt, rs = refiner.candidates(sig, act, bt[1:-1], refine_w)
            et = np.concatenate([bt, rt])
            ek = np.concatenate([np.full(bt.size, KIND_PRIOR, np.int8), np.full(rt.size, KIND_REFINED, np.int8)])
            es = np.concatenate([np.zeros(bt.size), rs])
            C2 = gen.build(sig, act, det, step=step, pause_min_s=o.min_pause_s,
                           extra_t=et, extra_kind=ek, extra_s=es, n_words=n, max_valleys=budget)
            U = self._units(all_words, model, e_g, e_l, e_n, False, R0, scale, D, n)
            centres = cands.L[path]
            widths = np.full(n + 1, refine_w)
            r2 = self._solve(dp, U, C2, centres, widths, A_end, marginals=last, name="refine",
                             retries=0, relax=False)
            if r2 is None:
                break
            shift = float(np.max(np.abs(C2.L[r2.path] - cands.L[path])))
            shifts.append(shift)
            path, cands, final = r2.path, C2, (r2, U, r2.lo, r2.hi)
            t = self._tick("refine", t)
            if last:
                break
            # settled: one more pass only to take the marginals
            settled = shift < o.refine_tol_s
            p += 1
        diag["refine_shifts"] = shifts
        dcoarse = np.abs(cands.L[path] - coarse_times)
        if final is None:
            # THE REFINEMENT FOUND NO WAY THROUGH, and the coarse path stands.
            # What the refinement would have measured -- the margins, the
            # interval, the stability -- is taken from the coarse pass
            # instead, in the same narrow band round its own path, where the
            # path itself is always a way through; and the agreement of a
            # coarse and a fine pass, with no fine pass, is not known.  Left
            # at their defaults these were all the best they could be, and
            # the case with the fewest checks came out the surest.
            diag["refine_failed"] = True
            dcoarse = None
            lo, hi = self._band(C, C.L[path], np.full(n + 1, refine_w))
            r1 = dp.solve(U_words, C, lo, hi, A_end, True)
            if r1 is not None:
                r1.lo, r1.hi = lo, hi
                path, final = r1.path, (r1, U_words, lo, hi)
        levels.append(("refine", n, cands.m))
        diag["levels"] = levels
        marg = final[0].marg if final is not None else []
        # ---- stability under perturbation: the weights of the words shaken,
        # the pause and boundary terms weakened and strengthened, the spread
        # of the durations widened -- and how far each boundary moves.  Not
        # run (or no way through), it is not known, and counts as a half.
        dpert = None
        if o.perturb and final is not None:
            _, U, lo, hi = final
            o2 = replace(o, w_pause=o.w_pause * 0.7, sigma_duration=o.sigma_duration * 1.25,
                         w_boundary=o.w_boundary * 1.3)
            w2 = TranscriptAnalyzer(o).shaken(model)
            U2 = replace(U, loge_g=np.log(np.maximum(w2 / R0, 1e-4)),
                         sig_g=U.sig_g * 1.25)
            dp2 = DynamicProgrammingAligner(o2, act.evidence)
            r3 = dp2.solve(U2, cands, lo, hi, A_end, False)
            if r3 is not None:
                dpert = np.abs(cands.L[r3.path] - cands.L[path])
            t = self._tick("perturb", t)
        margin_cap = np.full(n + 1, np.inf)
        spans = np.full((n + 1, 4), np.nan)
        if unit_groups is not None and unit_amb is not None:
            # a word boundary is no surer than the ends of the unit it is in:
            # if another place for the unit is nearly as good, the words
            # inside may go with it
            ua = np.array([g[0] for g in unit_groups])
            ub_word = np.append(ua, n)
            gi = np.searchsorted(ua, np.arange(n + 1), side="right") - 1
            gi = np.clip(gi, 0, len(unit_groups) - 1)
            um, us_ = unit_amb
            moved = np.maximum(us_[:, 1] - us_[:, 0], us_[:, 3] - us_[:, 2])
            margin_cap[ub_word] = um
            spans[ub_word] = us_
            unit_moved = np.maximum(moved[gi], moved[np.minimum(gi + 1, len(unit_groups))])
            # (with no perturbation, what the sentence level says can only
            # make the stability worse than the half it counts as unknown)
            dpert = np.maximum(0.1 * math.log(2.0) if dpert is None else dpert, unit_moved)
        # ---- confidence and the words
        ws, we = cands.R[path[:-1]], cands.L[path[1:]]
        rc = RateCurve.from_intervals(ws, we, model.weights, act, D, o.rate_window_s, R0,
                                      o.rate_shrink, o.rate_clip)
        e_l = self._local_expect(model, rc, all_words, ws, we, act)
        lr = np.log(np.maximum(we - ws, 1e-4) / np.maximum(e_l, 1e-4))
        fit_w = np.exp(-0.5 * (lr / o.sigma_rate) ** 2)
        durfit = np.empty(n + 1)
        durfit[0] = fit_w[0]
        durfit[-1] = fit_w[-1]
        if n > 1:
            durfit[1:-1] = 0.5 * (fit_w[:-1] + fit_w[1:])
        resolution = max(0.5 / sig.native_rate, 0.5 / sig.rate)
        conf, loL, hiL, loR, hiR, margin, clipped = ConfidenceEstimator(o).run(
            cands, path, marg, dpert, dcoarse, durfit, act.evidence, D, resolution,
            margin_cap, spans)
        t = self._tick("confidence", t)
        words = []
        for i in range(n):
            s0, e0 = float(ws[i]), float(we[i])
            words.append(WordAlignment(
                model.tokens[i], s0, e0, float(0.5 * (conf[i] + conf[i + 1])),
                float(min(loR[i], s0)), float(max(hiR[i], s0)),
                float(min(loL[i + 1], e0)), float(max(hiL[i + 1], e0))))
        inner = conf[1:-1] if n > 1 else conf
        gconf = float(np.mean(inner)) if inner.size else 0.0
        diag["boundary_confidence"] = conf
        diag["boundary_kind"] = [KIND_NAMES[k] for k in cands.kind[path]]
        diag["boundary_margin"] = margin
        diag["uncertainty_clipped"] = int(clipped.sum())
        diag["boundary_gap"] = cands.R[path] - cands.L[path]
        diag["boundary_is_pause"] = cands.kind[path] == KIND_PAUSE
        diag["timing"] = dict(self.timing)
        pauses_out = self._pauses_out(det, ws, we, model)
        cand_list = self._cand_list(cands) if want_candidates else []
        return (AlignmentResult(words, regions, pauses_out, gconf, diag, cand_list),
                (sig, act, det, cands, path))

    # ---- helpers of the engine
    @staticmethod
    def _reversed_problem(C: CandidateSet, U: Units, lo, hi, D: float, A_end: float, S_end: float):
        """The same alignment with time running backwards: the candidates
        mirrored (a pause's two edges swapping roles), the units in reverse
        order, each unit's pause prior moved to what is now its end, and the
        band mirrored.  A path costs the same both ways, but for which end
        of the chain the rate's first prior falls on."""
        m = C.m
        r = lambda a: a[::-1].copy()        # noqa: E731
        mass = np.diff(C.P)
        C2 = CandidateSet(D - r(C.R), D - r(C.L), r(C.kind), r(C.strength), r(C.dur), r(C.lev),
                          r(C.ctx), r(C.bcost), r(C.anchor), A_end - r(C.AR), A_end - r(C.AL),
                          S_end - r(C.SR), S_end - r(C.SL),
                          np.concatenate([[0.0], np.cumsum(mass[::-1])]))
        n = U.n
        prior = np.ones(n)
        plen = np.ones(n)
        if n > 1:
            prior[:-1] = U.prior[:-1][::-1]
            plen[:-1] = U.plen[:-1][::-1]
        U2 = replace(U, loge_g=r(U.loge_g), sig_g=r(U.sig_g), loge_l=r(U.loge_l),
                     sig_l=r(U.sig_l), loge_n=r(U.loge_n), sig_n=r(U.sig_n), dmin=r(U.dmin),
                     dmax=r(U.dmax), prior=prior, plen=plen, lam_in=r(U.lam_in),
                     count=r(U.count), rate_var=r(U.rate_var))
        return C2, U2, r(m - 1 - hi), r(m - 1 - lo)

    def _unit_marginals(self, dp, C: CandidateSet, U: Units, fwd: DPResult, lo, hi, D, A_end,
                        act: Activity):
        """Min-marginals of every unit boundary: the beam run forwards gives
        the best cost of reaching each candidate, the beam run backwards the
        best cost of going on from it, and their sum (less the boundary's own
        cost, counted by both) is the best segmentation forced through that
        candidate.  So a sentence end with another pause a sentence away
        that would do nearly as well is seen to be uncertain -- which the
        words' own marginals, confined to the refinement's window, cannot
        see.  The rate step across the boundary itself is left out: an
        alternative is taken to be a little more plausible than it is,
        which errs on the side of doubt.  Returns, per unit boundary, the
        margin to the best segmentation that puts it more than margin_tol_s
        away, and the span (of L and of R) of the near-optimal positions."""
        o = self.o
        n = U.n
        m = C.m
        C2, U2, lo2, hi2 = self._reversed_problem(C, U, lo, hi, D, A_end, float(act.cum_speech[-1]))
        # the backward run only has to see the alternatives near the path,
        # so it keeps a smaller beam (half the time of the forward one)
        dpb = DynamicProgrammingAligner(replace(o, rate_beam_states=o.unit_marginal_states), dp.ev)
        bwd = dpb.solve_rated(U2, C2, lo2, hi2, A_end)
        margin = np.full(n + 1, 10.0)
        span = np.stack([C.L[fwd.path], C.L[fwd.path], C.R[fwd.path], C.R[fwd.path]], axis=1)
        if bwd is None or not fwd.beam or not bwd.beam:
            return margin, span
        for i in range(n + 1):
            fj, fF = fwd.beam[i]
            bj, bB = bwd.beam[n - i]
            bj = m - 1 - bj
            common, ia, ib = np.intersect1d(fj, bj, assume_unique=True, return_indices=True)
            if common.size == 0:
                continue
            own = o.w_boundary * C.bcost[common]
            if 1 <= i <= n - 1 and o.w_pause > 0:
                pr = min(max(float(U.prior[i - 1]), 0.005), 0.995)
                own = own + o.w_pause * dp._pause_prior(pr, C.anchor[common], C.dur[common],
                                                        float(U.plen[i - 1]))
            M = fF[ia] + bB[ib] - own
            best = float(M.min())
            near = M - best <= o.unit_uncertainty_cost
            span[i] = [min(span[i, 0], C.L[common[near]].min()), max(span[i, 1], C.L[common[near]].max()),
                       min(span[i, 2], C.R[common[near]].min()), max(span[i, 3], C.R[common[near]].max())]
            far = np.abs(C.L[common] - C.L[fwd.path[i]]) > o.margin_tol_s
            if far.any():
                margin[i] = float(M[far].min()) - best
        return margin, span

    def _dip_length(self, model: TranscriptModel, sig: Signal, act: Activity, det: Detection):
        """How short a silence this envelope makes INSIDE speech, and so
        how long one must be to count as a pause.  Under a bed of music or
        noise the quiet between two syllables sinks to the level of the
        bed, and the envelope shows a "pause" at every stop consonant --
        hundreds of them, as deep as the real ones and only shorter.  By
        level they cannot be told apart; by length and by number they can:
        the text says about how many pauses a reader makes (the sum of its
        pause priors), and a reader makes nowhere near a pause a syllable.
        So the length of the `dip_rank`-times-that-many-th longest silence
        is taken as the length a dip may reach here, and a pause is judged
        against it: its weight as an anchor ramps up from there, and a
        shorter one is left inside the speech it interrupts (it counts as
        speech time for the rate).  In a clean recording that length is
        below anchor_short_s and nothing changes."""
        o = self.o
        inner = det.p_role == 0
        if o.dip_rank <= 0 or act.evidence <= 0 or model.n < 2 or not inner.any():
            return act, det, 0.0
        expected = float(model.prior[:-1].sum())
        k = int(math.ceil(o.dip_rank * expected + o.calibrate_prior))
        durs = np.sort(det.p_dur[inner])[::-1]
        if durs.size <= k:
            return act, det, 0.0
        dip = float(durs[k])
        short = max(o.anchor_short_s, dip)
        if short <= o.anchor_short_s:
            return act, det, dip
        full = short + (o.anchor_full_s - o.anchor_short_s)
        anchor = det.p_strength * np.clip((det.p_dur - short) / (full - short), 0, 1)
        det = replace(det, p_anchor=anchor)
        # the speech mask: the dips closed, so the rate is measured over
        # the time the reader was actually speaking
        rate = sig.rate
        s, e = _runs(~act.active)
        close = (s > 0) & (e < sig.n) & ((e - s) / rate <= dip)
        speech = _fill_runs(act.speech, s[close], e[close], True)
        cum = np.concatenate([[0.0], np.cumsum(speech.astype(float) + 1e-3) / rate])
        act = replace(act, speech=speech, cum_speech=cum)
        return act, det, dip

    def _calibrate(self, model: TranscriptModel, det: Detection):
        """The pause priors, fitted to this reader.  The text expects so many
        pauses (the sum of its priors); the envelope shows so many (the sum
        of its pauses' evidence).  A reader who pauses at half the commas and
        sentence ends the priors assume would otherwise have every sentence
        read straight on charged -log(1 - p), and the alignment would chase
        the few pauses there are at the price of absurd rates; one who
        hesitates between plain words more than they assume would have every
        hesitation charged -log(p_word).  So the priors are fitted until the
        counts agree -- a moment estimate, and the only thing learned from
        the recording before aligning it.  `calibrate_mode` "split" (the
        default) fits the strong breaks to the long pauses and the weak ones
        to the rest (below); "scale", the first way, scales every prior
        alike, which on real speech made a sentence end with a pause and one
        without cost about the same whenever the reader skipped commas."""
        o = self.o
        if not o.calibrate_pauses or model.n < 2:
            return model, 1.0
        # a pause the envelope shows plainly counts as one, whatever its
        # evidence short of certainty; a doubtful one as the part it is
        shown = float(np.minimum(1.0, det.p_anchor[det.p_role == 0] / o.calibrate_full).sum())
        prior = model.prior.copy()
        expected = float(prior[:-1].sum())
        if expected <= 0:
            return model, 1.0
        # a few pauses' worth of doubt, so a short text is not recalibrated
        # on the strength of one pause more or less
        r = (shown + o.calibrate_prior) / (expected + o.calibrate_prior)
        if o.calibrate_mode == "split":
            # two counts, not one: the LONG pauses the envelope shows against
            # the strong breaks (sentence ends, a book's piece ends), and the
            # rest against the weak ones (commas, plain words, a caption's
            # cut).  A reader who stops at every full stop but runs over
            # the commas, and one who hardly stops anywhere, show the same
            # total and want opposite priors: the length of the pauses tells
            # them apart.  Each group is shifted in its log-odds (the order
            # within it kept); the strong breaks are never made likelier than
            # the text says.
            inner = det.p_role == 0
            wgt = np.minimum(1.0, det.p_anchor[inner] / o.calibrate_full)
            is_long = det.p_dur[inner] >= o.phrase_pause_s
            strong = model.cut[:-1].copy()
            p = prior[:-1]
            c = o.calibrate_prior
            e_s = float(p[strong].sum())
            L = float(wgt[is_long].sum())
            if e_s > 0:
                r_s = (L + c) / (e_s + c)
                if r_s < 1.0:
                    p[strong] = _logit_fit(p[strong], max(r_s, o.calibrate_floor) * e_s)
            e_w = float(p[~strong].sum())
            left = shown - min(L, float(p[strong].sum()))
            if e_w > 0:
                r_w = (left + c) / (e_w + c)
                if r_w < 1.0:
                    p[~strong] = _logit_fit(p[~strong], max(r_w, o.calibrate_floor) * e_w)
                elif r_w > 1.0:
                    # (in a bare text a caption's end is a plain word's)
                    plain = (model.level[:-1] == BREAK_WORD) & (~model.piece_break[:-1] | model.bare)
                    if plain.any():
                        extra = (left - e_w) / float(plain.sum())
                        p[plain] = np.clip(p[plain] + extra, 0.005, o.calibrate_word_max)
            prior[:-1] = np.clip(p, 0.005, 0.995)
            return replace(model, prior=prior), float(r)
        if r < 1.0:
            r = max(r, o.calibrate_floor)
            prior[:-1] = np.clip(prior[:-1] * r, 0.005, 0.995)
        elif r > 1.0:
            plain = model.level[:-1] == BREAK_WORD
            plain &= ~model.piece_break[:-1] | model.bare
            if plain.any():
                extra = (shown - expected) / float(plain.sum())
                prior[:-1][plain] = np.clip(prior[:-1][plain] + extra, 0.005, o.calibrate_word_max)
        return replace(model, prior=prior), float(r)

    def _group_expect(self, model, curve: RateCurve, groups, gs, ge, act) -> np.ndarray:
        """Expected duration of every token at the rate of the group the
        level above put it in -- that group's own rate, as its words and its
        speech time say, drawn towards the smooth curve as far as the group
        is too short to be sure of it.  The level below thus inherits the
        rate the rate-aware level found, sudden changes included, instead of
        a curve that smears a change of pace over its window."""
        o = self.o
        w = model.weights
        n = model.n
        cw = np.concatenate([[0.0], np.cumsum(w)])
        ga = np.array([g[0] for g in groups], np.int64)
        gb = np.array([g[1] for g in groups], np.int64)
        gs = np.asarray(gs, float)
        ge = np.asarray(ge, float)
        sp = np.maximum(act.S(ge) - act.S(gs), 1e-3)
        lr_obs = np.log(np.maximum(cw[gb] - cw[ga], 1e-9) / sp)
        v_obs = o.sigma_rate ** 2 / np.maximum(gb - ga, 1) + 1e-6
        v_cur = o.group_rate_trust ** 2 + 1e-6
        lr_cur = curve.log_rate_at(0.5 * (gs + ge))
        lr = (lr_obs / v_obs + lr_cur / v_cur) / (1.0 / v_obs + 1.0 / v_cur)
        gi = np.searchsorted(ga, np.arange(n), side="right") - 1
        return w / np.exp(lr[gi])

    def _local_expect(self, model, curve: RateCurve, groups, gs, ge, act) -> np.ndarray:
        """Expected duration of every token under a local rate curve, each
        read at its own place inside the group the level above put it in."""
        n = model.n
        w = model.weights
        cw = np.concatenate([[0.0], np.cumsum(w)])
        ga = np.array([g[0] for g in groups], np.int64)
        gb = np.array([g[1] for g in groups], np.int64)
        gi = np.searchsorted(ga, np.arange(n), side="right") - 1
        a, b = ga[gi], gb[gi]
        frac = (cw[:-1] + 0.5 * w - cw[a]) / np.maximum(cw[b] - cw[a], 1e-9)
        s0 = np.asarray(gs, float)[gi]
        s1 = np.asarray(ge, float)[gi]
        mids = s0 + (s1 - s0) * frac
        return w / np.exp(curve.log_rate_at(mids))

    def _interpolate(self, children, groups, gs, ge, e_l, act, wmin, wfrac):
        """Centres (len = children + 1) of the children's boundaries,
        interpolated through speech time inside the groups the level above
        solved, and band widths growing with the group's length.  A child
        that starts a group takes that group's own solved boundary."""
        o = self.o
        gs = np.asarray(gs, float)
        ge = np.asarray(ge, float)
        ce = np.concatenate([[0.0], np.cumsum(e_l)])
        ga = np.array([g[0] for g in groups], np.int64)
        gb = np.array([g[1] for g in groups], np.int64)
        ca = np.array([c[0] for c in children], np.int64)
        gi = np.searchsorted(ga, ca, side="right") - 1
        frac = (ce[ca] - ce[ga[gi]]) / np.maximum(ce[gb[gi]] - ce[ga[gi]], 1e-9)
        S0, S1 = act.S(gs[gi]), act.S(ge[gi])
        cent = act.S_inv(S0 + (S1 - S0) * frac)
        first = ca == ga[gi]
        prev_end = np.where(gi > 0, ge[np.maximum(gi - 1, 0)], gs[0])
        cent = np.where(first, prev_end, cent)
        wid = np.minimum(o.max_band_s, wmin + wfrac * np.maximum(ge[gi] - gs[gi], 0.0))
        centres = np.append(cent, ge[-1])
        widths = np.append(wid, min(o.max_band_s, wmin + wfrac * max(ge[-1] - gs[-1], 0.0)))
        return centres, widths

    def _proportional_result(self, model, sig, act, det, regions, centres, diag, e_g):
        n = model.n
        D = sig.duration
        b = np.clip(centres, 0, D)
        b = np.maximum.accumulate(b)
        eps = D / (4.0 * (n + 1))
        for i in range(1, n + 1):
            if b[i] <= b[i - 1]:
                b[i] = b[i - 1] + eps
        b = b * (D / max(b[-1], D))
        words = [WordAlignment(model.tokens[i], float(b[i]), float(b[i + 1]), 0.1,
                               float(b[i]), float(b[i]), float(b[i + 1]), float(b[i + 1]))
                 for i in range(n)]
        diag["boundary_confidence"] = np.full(n + 1, 0.1)
        diag["boundary_kind"] = ["prior"] * (n + 1)
        diag["boundary_gap"] = np.zeros(n + 1)
        diag["boundary_is_pause"] = np.zeros(n + 1, bool)
        diag["timing"] = dict(self.timing)
        return AlignmentResult(words, regions, self._pauses_out(det, b[:-1], b[1:], model), 0.1, diag)

    def _pauses_out(self, det: Detection, ws, we, model) -> list:
        out = []
        for i in range(det.p_left.size):
            a, b = float(det.p_left[i]), float(det.p_right[i])
            role = {1: "leading", 2: "trailing"}.get(int(det.p_role[i]), "inter-word")
            if ws is not None and len(ws):
                mid = 0.5 * (a + b)
                if b <= ws[0] + 1e-9:
                    role = "leading"
                elif a >= we[-1] - 1e-9:
                    role = "trailing"
                else:
                    k = int(np.searchsorted(ws, mid, side="right")) - 1
                    if 0 <= k and mid < we[k]:
                        role = "within-word"
                    elif 0 <= k < len(ws) - 1:
                        lvl = int(model.level[k])
                        role = ("paragraph" if lvl >= BREAK_PARAGRAPH else "sentence" if lvl >= BREAK_SENTENCE
                                else "phrase" if lvl >= BREAK_COMMA else "inter-word")
            out.append(Pause(a, b, b - a, float(det.p_strength[i]), PAUSE_CLASSES[int(det.p_cls[i])], role))
        return out

    def _cand_list(self, C: CandidateSet) -> list:
        out = []
        for j in range(C.m):
            k = int(C.kind[j])
            if k == KIND_PAUSE:
                cls = PAUSE_CLASSES[0 if C.dur[j] < self.o.phrase_pause_s else 1 if C.dur[j] < self.o.long_pause_s else 2]
            elif k in (KIND_VALLEY, KIND_REFINED):
                cls = "possible word boundary" if C.strength[j] >= 0.3 else "weak valley"
            else:
                cls = KIND_NAMES[k]
            out.append(BoundaryCandidate(float(0.5 * (C.L[j] + C.R[j])), float(C.strength[j]), float(C.dur[j]),
                                         float(C.lev[j]), float(C.ctx[j]), KIND_NAMES[k], cls,
                                         float(C.L[j]), float(C.R[j])))
        return out


# ============================================================ public API
# THE SHORTEST STRETCH ANSWERED.  Below a microsecond there is no answer to
# give: the pieces' floor and the projection's own slack (a picosecond)
# no longer fit inside it, so their times could not stay in [0, D] and in
# order.  The page never asks for less than 0.4 s, and the doors refuse
# less than a tenth of a second; this is for a caller of the library.
MIN_DURATION = 1e-6


def _check_duration(duration) -> float:
    try:
        D = float(duration)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("the duration is not a number")
    if not math.isfinite(D) or D <= 0:
        raise ValueError("the duration must be a positive number of seconds")
    if D < MIN_DURATION:
        raise ValueError("the stretch is too short to estimate")
    return D


def analyze_waveform(waveform, duration_seconds: float, sample_times=None,
                     options: Optional[AlignmentOptions] = None):
    """The first three stages alone (for drawing and debugging): the
    Signal, the Activity and the Detection."""
    o = options or AlignmentOptions()
    D = _check_duration(duration_seconds)
    sig = WaveformPreprocessor(o).run(waveform, D, sample_times)
    act = ActivityEstimator(o).run(sig)
    return sig, act, PauseDetector(o).run(sig, act)


def align_transcript_to_waveform(waveform: Sequence[float], duration_seconds: float, transcript: str,
                                 sample_times: Optional[Sequence[float]] = None,
                                 options: Optional[AlignmentOptions] = None,
                                 tokenize: Optional[Callable[[str], Sequence[str]]] = None) -> AlignmentResult:
    """Word timestamps for `transcript` over the envelope `waveform`.

    Every word satisfies 0 <= start < end <= duration, and word[i].end <=
    word[i+1].start exactly (the times are the candidates' own numbers, so
    no tolerance is needed; a caller comparing after its own arithmetic may
    allow 1e-9 s).  A gap between them is a silence left to nobody.  Raises
    ValueError only for a duration that is not a positive number (or is
    shorter than MIN_DURATION, a microsecond)."""
    o = options or AlignmentOptions()
    D = _check_duration(duration_seconds)
    model = TranscriptAnalyzer(o, tokenize).analyze([transcript or ""], 0.0)
    if model.n == 1 and model.placeholder[0] and not model.tokens[0]:
        model = TranscriptAnalyzer(o, tokenize).analyze([], 0.0)
    res, _ = _Engine(o).run(waveform, D, sample_times, model, o.keep_candidates)
    return res


def _align_with_internals(waveform, duration, transcript_or_pieces, sample_times=None,
                          options=None, tokenize=None, piece_strength=0.0):
    """For the lab: the result together with the internal stages."""
    o = options or AlignmentOptions()
    D = _check_duration(duration)
    pieces = [transcript_or_pieces] if isinstance(transcript_or_pieces, str) else list(transcript_or_pieces)
    model = TranscriptAnalyzer(o, tokenize).analyze(pieces, piece_strength)
    res, internals = _Engine(o).run(waveform, D, sample_times, model, True)
    return res, model, internals


def estimate_pieces(envelope, duration, texts, kind="span", *, sample_times=None,
                    options=None, tokenize=None) -> dict:
    """Where each piece (a book's subparagraph, a video's caption) starts and
    ends, from the envelope of the stretch [0, duration] that holds them.

    The same engine as align_transcript_to_waveform: the pieces' tokens are
    aligned as words, each piece boundary being a break of its own strength
    at the top of the hierarchy (piece_strength_span for a book, the weaker
    piece_strength_point for captions), and the pieces are read off the
    words.  See the contract in docs/wavealign.md for every invariant."""
    o = options or AlignmentOptions()
    if texts is None or len(texts) == 0:
        raise ValueError("there are no pieces to estimate")
    D = _check_duration(duration)
    point = kind == "point"
    texts = ["" if t is None else str(t) for t in texts]
    N = len(texts)
    strength = o.piece_strength_point if point else o.piece_strength_span
    model = TranscriptAnalyzer(o, tokenize).analyze(texts, strength)
    res, (sig, act, det, cands, path) = _Engine(o).run(envelope, D, sample_times, model, False)
    words = res.words
    conf_b = res.diagnostics.get("boundary_confidence")
    is_pause = res.diagnostics.get("boundary_is_pause")
    first = np.zeros(N, np.int64)
    last = np.zeros(N, np.int64)
    for p in range(N):
        idx = np.flatnonzero(model.piece == p)
        first[p], last[p] = idx[0], idx[-1]
    level = sig.level
    rate = sig.rate

    def quietest(a, b):
        """The quietest point of [a, b] (the middle of the quietest stretch)."""
        if b - a <= 1e-9:
            return 0.5 * (a + b)
        fa = int(math.floor(a * rate))
        fb = int(math.ceil(b * rate))
        fa, fb = max(fa, 0), min(fb, sig.n)
        if fb - fa < 3:
            return 0.5 * (a + b)
        seg = level[fa:fb]
        lo = seg.min()
        low = np.flatnonzero(seg <= lo + 0.02)
        k = low[low.size // 2]
        return float(np.clip((fa + k + 0.5) / rate, a, b))

    # boundaries between pieces, from the words
    t0 = np.zeros(N)
    t1 = np.zeros(N)
    anchored = 0
    for p in range(N - 1):
        we = words[last[p]].end
        ws = words[first[p + 1]].start
        gap = ws - we
        b = int(first[p + 1])
        if is_pause is not None and bool(is_pause[b]):
            anchored += 1
        if gap >= o.split_gap:
            if point:
                t1[p] = t0[p + 1] = ws - min(o.pad, gap / 2.0)
            else:
                pad = min(o.pad, gap / 3.0)
                t1[p] = we + pad
                t0[p + 1] = ws - pad
        else:
            q = quietest(we, ws)
            t1[p] = t0[p + 1] = q
    t0[0] = 0.0
    t1[N - 1] = D if point else min(D, words[last[N - 1]].end + o.pad)
    # every piece long enough to play: a least-squares projection onto the
    # constraints, applied only when something violates them
    mlen = min(o.min_piece, D / N * 0.5)
    need = mlen * (1 + 1e-9) + 1e-12
    if point:
        x = np.concatenate([t0, [D]])
        if np.any(np.diff(x) < need):
            off = np.arange(N + 1) * need
            y = x - off
            mid = _pava(list(y[1:-1])) if N > 1 else []
            y = np.concatenate([[0.0], np.clip(mid, 0.0, D - off[-1]), [D - off[-1]]])
            x = y + off
            x[0], x[-1] = 0.0, D
        t0 = x[:-1].copy()
        t1 = x[1:].copy()
    else:
        x = np.ravel(np.column_stack([t0, t1]))
        spacing = np.zeros(2 * N)
        spacing[1::2] = need
        if np.any(np.diff(x) < spacing[1:]) or x[-1] > D:
            off = ((np.arange(2 * N) + 1) // 2) * need
            y = x - off
            fit = _pava(list(y[1:]))
            y = np.concatenate([[0.0], np.clip(fit, 0.0, D - off[-1])])
            x = y + off
            x[0] = 0.0
            # (D - off) + off may round one ulp past D; only the last can,
            # the others standing at least `need` below it
            x[-1] = min(x[-1], D)
        t0 = x[0::2].copy()
        t1 = x[1::2].copy()
    pieces = []
    for p in range(N):
        fw, lw = words[first[p]], words[last[p]]
        a, b = float(t0[p]), float(t1[p])
        if p == 0:
            c, lo_, hi_ = 1.0, 0.0, 0.0
        else:
            # a split start moves with its first word's start; a joined one
            # may fall anywhere between the last near-optimal end of the
            # word before and the first near-optimal start of the word after
            bi = int(first[p])
            c = float(conf_b[bi]) if conf_b is not None else 0.5
            prev = words[bi - 1]
            if fw.start - prev.end >= o.split_gap:
                shift = fw.start - a
                lo_ = min(a, fw.start_min - shift)
                hi_ = max(a, fw.start_max - shift)
            else:
                lo_ = min(a, prev.end_min)
                hi_ = max(a, fw.start_max)
        sp0 = float(np.clip(fw.start, a, b))
        sp1 = float(np.clip(lw.end, sp0, b))
        pieces.append({"t0": a, "t1": b, "confidence": float(np.clip(c, 0, 1)),
                       "t0_min": float(max(0.0, lo_)), "t0_max": float(min(D, hi_)),
                       "speech": [sp0, sp1]})
    return {
        "pieces": pieces,
        "confidence": float(np.clip(res.global_confidence, 0, 1)),
        "anchored": int(anchored),
        "boundaries": N - 1,
        "words": int((~model.placeholder).sum()),
        "method": "wavealign",
        "version": VERSION,
    }
