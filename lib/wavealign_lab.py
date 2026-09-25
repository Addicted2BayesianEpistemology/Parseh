#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The bench of lib/wavealign.py: sound made up with its answer known, the
measures of how far a guess lands from it, the guess made today ("by the
text"), a drawing of one alignment, and the command that runs them.

    python3 lib/wavealign_lab.py demo              # the WORD / START / END table
    python3 lib/wavealign_lab.py bench             # new against by the text
    python3 lib/wavealign_lab.py bench --quick     # without the hour-long case
    python3 lib/wavealign_lab.py bench --long 4    # ... and time four hours too
    python3 lib/wavealign_lab.py plot OUT.svg      # one case, drawn
    python3 lib/wavealign_lab.py sensitivity       # each parameter varied
    python3 lib/wavealign_lab.py bench-audio SOUND TRUTH.json
                                  # by the text against by the sound on a
                                  # recording whose cuts someone trusts

    import wavealign_lab as lab
    case = lab.synthesize(lab.SynthConfig(seed=3, language="fa"))
    res = wavealign.align_transcript_to_waveform(case.envelope, case.duration,
                                                 case.transcript)
    print(lab.word_metrics([w.start for w in res.words], [w.end for w in res.words], case))

MADE-UP SOUND, NOT A RECORDING.  The generator lays out words whose lengths
follow their letters (with as much scatter as it is told), fills each with
syllable-like bumps, dips between words as deep as it is told, pauses at
commas and sentence ends, varies the pace smoothly or all at once, adds a
noise floor, and reads the result the way Parseh does -- the peak (or the
RMS) of each bucket of a fine signal.  It knows where every word starts and
ends, which is the one thing no recording in Parseh can tell (the owner's
cuts are not ground truth), so it is what the aligner is measured on here.
Real speech is harder than this in ways a generator only imitates: that is
what the Kokoro bench is for (docs/wavealign.md, section 8), and what
`bench-audio` does for any recording whose cuts someone trusts -- it is
handed the sound and the true times, and nothing of anyone's shelf.

Seeded and deterministic: the same SynthConfig gives the same numbers.
NumPy only; matplotlib is used when it is there (a PNG beside the SVG) and
never needed.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from dataclasses import dataclass, replace
from typing import Optional, Sequence

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wavealign as W  # noqa: E402

__all__ = ["SynthConfig", "SynthCase", "synthesize", "make_text", "word_metrics",
           "piece_metrics", "by_the_text", "by_the_text_words", "plot_alignment",
           "SCENARIOS", "run_bench", "load_truth", "recording_peaks", "bench_audio", "main"]


# =================================================================== text
# Letters to make words of, per script.  They are only letters: the aligner
# sees how many there are and where the punctuation is, never what they say,
# so a random string of the right script and length is as good a word here as
# a real one -- and it keeps every language on an equal footing.
_LATIN = "abcdefghijklmnopqrstuvwxyz"
_LATIN_EXTRA = {"it": "àèéìòù", "fr": "éèêàçôûî", "de": "äöüß", "tr": "çğıöşü", "es": "áéíóúñ"}
_PERSIAN = "ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی"
_ARABIC = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"
_HARAKAT = "\u064e\u0650\u064f\u0652"          # fatha, kasra, damma, sukun
_DEVA_CONS = "कखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह"
_DEVA_VOWEL_SIGNS = "\u093e\u093f\u0940\u0941\u0942\u0947\u0948\u094b\u094c"
_DEVA_OTHER = "\u0902\u0901"                   # anusvara, candrabindu
_KANA = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわん"
_KANJI = "日本語学生時間大人今年月見行出来話言"
_HAN = "我你他们的是在有不了人这中大为上个国说到和地也子时道出而要于就下得可"

# seconds a spoken unit takes at the pace of 1.0, per language: a Latin or
# Devanagari letter, an Arabic-script letter (it carries an unwritten vowel,
# so it is longer), a mora of kana, a Han character (a whole syllable)
_SEC_PER_UNIT = {"en": 0.075, "it": 0.068, "fr": 0.068, "de": 0.075, "tr": 0.07,
                 "es": 0.064, "fa": 0.095, "ar": 0.095, "hi": 0.08, "ja": 0.125,
                 "zh": 0.23}

_PUNCT = {  # (comma, sentence end, question)
    "fa": ("،", ".", "؟"), "ar": ("،", ".", "؟"), "hi": (",", "।", "?"),
    "ja": ("、", "。", "？"), "zh": ("，", "。", "？"),
}
_SPACELESS = ("ja", "zh")


def _word(rng: np.random.Generator, lang: str, harakat: bool) -> tuple:
    """(written word, spoken units) for one made-up word."""
    if lang == "zh":
        return _HAN[rng.integers(len(_HAN))], 1.0
    if lang == "ja":
        if rng.random() < 0.3:
            return _KANJI[rng.integers(len(_KANJI))], 1.7   # a kanji: ~two morae
        return _KANA[rng.integers(len(_KANA))], 1.0
    if lang in ("fa", "ar"):
        letters = _PERSIAN if lang == "fa" else _ARABIC
        n = int(np.clip(rng.poisson(3.2) + 1, 1, 9))
        out = ""
        for _ in range(n):
            out += letters[rng.integers(len(letters))]
            if harakat and rng.random() < 0.7:
                out += _HARAKAT[rng.integers(len(_HARAKAT))]
        return out, float(n)
    if lang == "hi":
        n = int(np.clip(rng.poisson(1.8) + 1, 1, 6))
        out, units = "", 0.0
        for _ in range(n):
            out += _DEVA_CONS[rng.integers(len(_DEVA_CONS))]
            units += 1
            if rng.random() < 0.6:
                out += _DEVA_VOWEL_SIGNS[rng.integers(len(_DEVA_VOWEL_SIGNS))]
                units += 1
            if rng.random() < 0.08:
                out += _DEVA_OTHER[rng.integers(len(_DEVA_OTHER))]
        return out, units
    letters = _LATIN + _LATIN_EXTRA.get(lang, "")
    n = int(np.clip(rng.poisson(3.6) + 1, 1, 14))
    return "".join(letters[rng.integers(len(letters))] for _ in range(n)), float(n)


def make_text(n_words: int, language: str = "en", seed: int = 0, harakat: bool = False,
              sentence_words=(4, 16), comma_rate: float = 0.12, question_rate: float = 0.1,
              paragraph_sentences=(2, 5)):
    """A made-up transcript: a list of paragraphs, each a list of sentences,
    each a list of (token, units, break) where break is the BREAK_* level
    after the token.  Used by synthesize(); handy alone for the tokenizer's
    tests."""
    rng = np.random.default_rng([seed, 7])
    comma, stop, question = _PUNCT.get(language, (",", ".", "?"))
    pars, left = [], n_words
    while left > 0:
        sents = []
        for _ in range(int(rng.integers(paragraph_sentences[0], paragraph_sentences[1] + 1))):
            if left <= 0:
                break
            k = int(min(left, rng.integers(sentence_words[0], sentence_words[1] + 1)))
            left -= k
            sent = []
            for j in range(k):
                w, u = _word(rng, language, harakat)
                brk = W.BREAK_WORD
                if j == k - 1:
                    w += question if rng.random() < question_rate else stop
                    brk = W.BREAK_SENTENCE
                elif 0 < j < k - 2 and rng.random() < comma_rate:
                    w += comma
                    brk = W.BREAK_COMMA
                sent.append((w, u, brk))
            sents.append(sent)
        pars.append(sents)
    return pars


# ============================================================== the sound
@dataclass
class SynthConfig:
    """Everything the made-up sound can be told.  Times are in seconds,
    levels in decibels below the typical loudness of a word."""
    seed: int = 0
    language: str = "en"
    n_words: int = 120
    harakat: bool = False
    text: Optional[list] = None         # a make_text() structure, else one is made
    rate: float = 100.0                 # envelope samples a second
    style: str = "peak"                 # peak | rms
    fine_rate: float = 2000.0           # the "signal" the buckets are read from
    pace: float = 1.0                   # overall speed (2.0 = twice as fast)
    char_exponent: float = 0.85         # duration ~ units ** this ...
    word_constant: float = 0.6          # ... + this many units for every word
    duration_jitter: float = 0.22       # log-normal scatter of a word's length
    length_correlation: float = 1.0     # 1: lengths follow the letters; 0: not at all
    rate_sd: float = 0.12               # the spread of the log pace ...
    rate_tau: float = 8.0               # ... and how many seconds it holds
    rate_jump: Optional[tuple] = None   # (where, as a fraction of the words; factor)
    valley_depth: float = 0.55          # mean depth of a dip between words (0..1)
    valley_prob: float = 0.75           # how many word boundaries dip at all
    word_gap_prob: float = 0.15         # ... and how many leave a little silence
    word_gap: tuple = (0.02, 0.09)
    intra_dip: tuple = (0.15, 0.75)     # depth of the dips between syllables
    syllable_rate: float = 5.0          # syllables a second
    comma_pause_prob: float = 0.65
    comma_pause: tuple = (0.12, 0.35)
    sentence_pause_prob: float = 0.92
    sentence_pause: tuple = (0.30, 0.85)
    paragraph_pause: tuple = (0.8, 1.6)
    stray_pause_prob: float = 0.02      # a hesitation where the text has no mark
    stray_pause: tuple = (0.15, 0.5)
    lead: float = 0.7                   # silence before the first word
    trail: float = 0.9                  # ... and after the last
    noise_db: float = -38.0             # the noise floor
    noise_wobble_db: float = 3.0        # its slow drift
    level_jitter_db: float = 4.0        # word-to-word loudness
    gain: float = 0.35                  # full scale of a typical word
    clicks: int = 0                     # isolated spikes of full loudness
    pieces: str = "sentences"           # sentences (a book) | captions (a video)
    caption_words: tuple = (5, 12)
    bare: bool = False                  # the text handed over has no punctuation and no
                                        # paragraphs, as YouTube leaves its auto-captions;
                                        # the sound still pauses where the sentences end


@dataclass
class SynthCase:
    """One made-up recording and its answer."""
    config: SynthConfig
    envelope: np.ndarray
    duration: float
    rate: float
    transcript: str
    tokens: list
    starts: np.ndarray
    ends: np.ndarray
    level: np.ndarray               # the break after each token (BREAK_*)
    pieces: list                    # the pieces' texts
    piece_of: np.ndarray            # the piece of each token
    pace: np.ndarray                # the pace each word was said at

    @property
    def sentence_end(self) -> np.ndarray:
        return self.level >= W.BREAK_SENTENCE

    @property
    def piece_first(self) -> np.ndarray:
        return np.array([int(np.flatnonzero(self.piece_of == p)[0]) for p in range(len(self.pieces))])

    @property
    def piece_last(self) -> np.ndarray:
        return np.array([int(np.flatnonzero(self.piece_of == p)[-1]) for p in range(len(self.pieces))])


def _join(tokens: list, lang: str) -> str:
    return ("" if lang in _SPACELESS else " ").join(tokens)


def _bare(token: str) -> str:
    """A token with its punctuation taken out: what an untidied
    auto-caption writes."""
    import unicodedata
    return "".join(ch for ch in token if unicodedata.category(ch)[0] != "P")


def synthesize(cfg: SynthConfig = SynthConfig()) -> SynthCase:
    """A made-up recording of a made-up (or given) text, with its answer."""
    rng = np.random.default_rng([cfg.seed, 11])
    lang = cfg.language
    pars = cfg.text if cfg.text is not None else make_text(
        cfg.n_words, lang, cfg.seed, cfg.harakat)
    flat = []                           # (token, units, break, paragraph end)
    for pi, par in enumerate(pars):
        for si, sent in enumerate(par):
            for wi, (tok, units, brk) in enumerate(sent):
                last = si == len(par) - 1 and wi == len(sent) - 1 and pi < len(pars) - 1
                flat.append((tok, units, W.BREAK_PARAGRAPH if last else brk))
    n = len(flat)
    units = np.array([u for _, u, _ in flat], float)
    level = np.array([b for _, _, b in flat], np.int8)

    # ---- how long each word lasts
    spu = _SEC_PER_UNIT.get(lang, 0.075)
    prior = spu * (units ** cfg.char_exponent + cfg.word_constant)
    c = float(np.clip(cfg.length_correlation, 0, 1))
    if c < 1:
        # the lengths are shuffled against the words, the mix keeping the mean
        other = rng.permutation(prior)
        prior = np.exp(c * np.log(prior) + (1 - c) * np.log(other))
    dur = prior * np.exp(rng.normal(0.0, cfg.duration_jitter, n))
    # the pace: a mean-reverting wander in time (Ornstein-Uhlenbeck: it
    # drifts for about rate_tau seconds, then comes back), and perhaps a jump
    logpace = np.zeros(n)
    x = rng.normal(0.0, cfg.rate_sd)
    for i in range(n):
        keep = math.exp(-max(dur[i], 0.05) / cfg.rate_tau)
        x = keep * x + math.sqrt(1 - keep * keep) * cfg.rate_sd * rng.normal()
        logpace[i] = x
    logpace += math.log(cfg.pace)
    if cfg.rate_jump:
        at, factor = cfg.rate_jump
        logpace[int(at * n):] += math.log(factor)
    pace = np.exp(logpace)
    dur = np.maximum(dur / pace, 0.07)

    # ---- the gaps after each word
    gaps = np.zeros(n)
    dips = np.zeros(n)
    for i in range(n - 1):
        lv = level[i]
        if lv >= W.BREAK_PARAGRAPH:
            gaps[i] = rng.uniform(*cfg.paragraph_pause)
        elif lv >= W.BREAK_SENTENCE and rng.random() < cfg.sentence_pause_prob:
            gaps[i] = rng.uniform(*cfg.sentence_pause)
        elif lv >= W.BREAK_COMMA and rng.random() < cfg.comma_pause_prob:
            gaps[i] = rng.uniform(*cfg.comma_pause)
        elif rng.random() < cfg.stray_pause_prob:
            gaps[i] = rng.uniform(*cfg.stray_pause)
        elif rng.random() < cfg.word_gap_prob:
            gaps[i] = rng.uniform(*cfg.word_gap)
        if gaps[i] == 0.0 and rng.random() < cfg.valley_prob:
            dips[i] = float(np.clip(rng.normal(cfg.valley_depth, 0.2), 0.05, 0.98))
        gaps[i] /= math.sqrt(pace[i])  # a fast speaker pauses less, not much less
    starts = np.empty(n)
    ends = np.empty(n)
    t = cfg.lead
    for i in range(n):
        starts[i] = t
        ends[i] = t + dur[i]
        t = ends[i] + gaps[i]
    D = float(ends[-1] + cfg.trail)

    # ---- the loudness of the speech on a fine grid
    fr = cfg.fine_rate
    nf = int(math.ceil(D * fr))
    tt = (np.arange(nf) + 0.5) / fr
    amp = np.zeros(nf)
    wlev = 10 ** (rng.normal(0.0, cfg.level_jitter_db, n) / 20.0)
    for i in range(n):
        a, b = int(starts[i] * fr), min(nf, int(math.ceil(ends[i] * fr)))
        if b <= a:
            continue
        x = (tt[a:b] - starts[i]) / dur[i]                  # 0..1 inside the word
        k = max(1, int(round(dur[i] * cfg.syllable_rate)))
        # syllables: humps with dips between them of a random depth
        depth = rng.uniform(*cfg.intra_dip, k + 1)
        hump = np.abs(np.sin(math.pi * k * x)) ** 0.8
        which = np.minimum((x * k).astype(int), k - 1)
        floor = 1.0 - depth[which + (x * k - which > 0.5)]
        shape = floor + (1.0 - floor) * hump
        # the onset and the release: a word begins and ends at nothing
        ramp = np.minimum(1.0, np.minimum(x, 1 - x) * dur[i] / 0.025)
        peaks = rng.uniform(0.7, 1.0, k)[which]
        amp[a:b] = np.maximum(amp[a:b], wlev[i] * peaks * shape * ramp)
    # a boundary without a gap does not fall to nothing: it dips as deep as
    # it was told (a coarticulated boundary barely at all)
    for i in range(n - 1):
        if gaps[i] > 0:
            continue
        a, b = int((ends[i] - 0.04) * fr), min(nf, int((starts[i + 1] + 0.04) * fr))
        bridge = (1.0 - dips[i]) * min(wlev[i], wlev[i + 1]) * 0.8
        amp[a:b] = np.maximum(amp[a:b], bridge)
    amp *= cfg.gain

    # ---- the sound: the loudness on a noisy carrier, plus the noise floor
    noise = 10 ** ((cfg.noise_db + cfg.noise_wobble_db * np.sin(
        2 * math.pi * tt / 7.3 + rng.uniform(0, 6.28))) / 20.0) * cfg.gain
    carrier = np.abs(rng.standard_normal(nf)).astype(np.float32)
    sig = amp * carrier + noise * np.abs(rng.standard_normal(nf)).astype(np.float32)
    for _ in range(cfg.clicks):
        sig[rng.integers(nf)] = 1.0
    sig = np.minimum(sig, 1.0)

    # ---- read as Parseh reads it: one number a bucket
    nb = max(1, int(round(D * cfg.rate)))
    edges = np.minimum((np.arange(nb + 1) * nf / nb).astype(np.int64), nf)
    if cfg.style == "rms":
        cs = np.concatenate([[0.0], np.cumsum(sig.astype(float) ** 2)])
        cnt = np.maximum(np.diff(edges), 1)
        env = np.sqrt((cs[edges[1:]] - cs[edges[:-1]]) / cnt)
    else:
        env = np.maximum.reduceat(sig, np.minimum(edges[:-1], nf - 1)).astype(float)

    # the text as it is handed over: whole, or bare of its punctuation --
    # the sound is the same either way, pausing where the sentences end
    plain = _bare if cfg.bare else (lambda tok: tok)
    tokens = [plain(tok) for tok, _, _ in flat]
    # the pieces: a book's are one to three sentences (never across a
    # paragraph), a video's are captions of a few words cut anywhere
    piece_of = np.zeros(n, np.int64)
    p = 0
    if cfg.pieces == "captions":
        i = 0
        while i < n:
            k = int(rng.integers(cfg.caption_words[0], cfg.caption_words[1] + 1))
            piece_of[i:i + k] = p
            i += k
            p += 1
    else:
        left = int(rng.integers(1, 4))
        for i in range(n):
            piece_of[i] = p
            if level[i] >= W.BREAK_SENTENCE and i < n - 1:
                left -= 1
                if left == 0 or level[i] >= W.BREAK_PARAGRAPH:
                    p += 1
                    left = int(rng.integers(1, 4))
    npieces = int(piece_of[-1]) + 1
    pieces = [_join([tokens[i] for i in np.flatnonzero(piece_of == q)], lang) for q in range(npieces)]
    paragraphs = []
    for par in pars:
        paragraphs.append(" ".join(_join([plain(tok) for tok, _, _ in s], lang) for s in par)
                          if lang not in _SPACELESS else
                          "".join(_join([plain(tok) for tok, _, _ in s], lang) for s in par))
    # (a bare text has no blank lines either: nothing marks a paragraph)
    transcript = (_join(paragraphs, lang) if cfg.bare else "\n\n".join(paragraphs))
    return SynthCase(cfg, env, D, cfg.rate, transcript, tokens, starts, ends, level,
                     pieces, piece_of, pace)


# ============================================================ the measures
def _summary(err: np.ndarray) -> dict:
    err = np.abs(np.asarray(err, float))
    if err.size == 0:
        return {"n": 0, "mean": float("nan"), "median": float("nan"), "p90": float("nan"),
                "w50": float("nan"), "w100": float("nan"), "w250": float("nan")}
    return {"n": int(err.size), "mean": float(err.mean()), "median": float(np.median(err)),
            "p90": float(np.percentile(err, 90)),
            "w50": float((err <= 0.05).mean() * 100), "w100": float((err <= 0.10).mean() * 100),
            "w250": float((err <= 0.25).mean() * 100)}


def word_metrics(pred_starts, pred_ends, case: SynthCase) -> dict:
    """Every word's start and end against the answer: mean, median and 90th
    percentile of the absolute error, the share within 50, 100 and 250 ms,
    and the mean error of the boundaries at sentence ends alone (the end of
    a sentence's last word and the start of the next one's first)."""
    ps = np.asarray(pred_starts, float)
    pe = np.asarray(pred_ends, float)
    err = np.concatenate([ps - case.starts, pe - case.ends])
    out = _summary(err)
    se = np.flatnonzero(case.sentence_end[:-1])
    serr = np.concatenate([pe[se] - case.ends[se], ps[se + 1] - case.starts[se + 1]])
    out["sentence"] = float(np.abs(serr).mean()) if serr.size else float("nan")
    return out


def _gap_distance(t, lo, hi):
    """How far t is from the silence [lo, hi] (0 inside it)."""
    return np.maximum(0.0, np.maximum(lo - t, t - hi))


def piece_metrics(pieces: list, case: SynthCase) -> dict:
    """A piece boundary is right anywhere in the silence between the last
    word of one piece and the first word of the next (both ends, for a
    book's; the one number, for a caption's) -- so the error is the distance
    from that silence, 0 inside it.  `sentence` is the same over the
    boundaries that are also the end of a sentence."""
    first, last = case.piece_first, case.piece_last
    errs, sent = [], []
    for p in range(1, len(pieces)):
        lo, hi = case.ends[last[p - 1]], case.starts[first[p]]
        for t in {pieces[p - 1]["t1"], pieces[p]["t0"]}:
            e = float(_gap_distance(t, lo, hi))
            errs.append(e)
            if case.level[last[p - 1]] >= W.BREAK_SENTENCE:
                sent.append(e)
    out = _summary(np.array(errs))
    out["sentence"] = float(np.mean(sent)) if sent else float("nan")
    return out


# ============================================================ by the text
def _size_of(text: str) -> int:
    """lib/timeline.js sizeOf, to the letter: NFD, the combining marks of
    U+0300-036F, U+064B-0652, U+0610-061A and U+06D6-06ED dropped, the
    whitespace taken out, and the length counted as JavaScript counts it
    (UTF-16 code units), never less than 1."""
    import re
    import unicodedata
    bare = unicodedata.normalize("NFD", str(text or ""))
    bare = re.sub("[\u0300-\u036f\u064b-\u0652\u0610-\u061a\u06d6-\u06ed]", "", bare)
    bare = re.sub(r"\s+", "", bare)
    return max(1, len(bare.encode("utf-16-le")) // 2)


def by_the_text(texts: Sequence[str], duration: float, kind: str = "span",
                floor: float = 0.4) -> list:
    """The pieces as "estimate the rest" lays them today (lib/timeline.js,
    spreadRest) over the stretch [0, duration]: in proportion to sizeOf, a
    floor of 0.4 s under each, the last ending at the end, contiguous."""
    sizes = [_size_of(t) for t in texts]
    total = sum(sizes) or 1
    out, t = [], 0.0
    N = len(texts)
    for i in range(N):
        end = duration if i == N - 1 else t + duration * sizes[i] / total
        if end < t + floor:
            end = min(duration, t + floor)
        out.append({"t0": t, "t1": end})
        t = end
    return out


def by_the_text_words(tokens: Sequence[str], duration: float):
    """The same rule for words (each word a piece), with no floor: 0.4 s is
    a piece's floor, not a word's, and would only handicap it."""
    p = by_the_text(tokens, duration, floor=0.0)
    return np.array([x["t0"] for x in p]), np.array([x["t1"] for x in p])


# ============================================================ the drawing
def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def plot_alignment(out_path: str, waveform, duration: float, transcript, *,
                   sample_times=None, options: Optional[W.AlignmentOptions] = None,
                   tokenize=None, truth: Optional[SynthCase] = None,
                   t0: float = 0.0, t1: Optional[float] = None,
                   px_per_s: float = 120.0, result=None) -> str:
    """Draw one alignment as an SVG (no dependency): the envelope (its
    normalised level curve), the speech regions, the pauses, the candidate
    boundaries, the words with their labels and a bar of confidence under
    each, the uncertainty of each start -- and, when `truth` is given, the
    true words beneath.  `transcript` may be a string or a list of pieces.
    A window [t0, t1] keeps a long case legible.  When matplotlib imports, a
    PNG of the same is written next to it.  Returns the SVG's path."""
    o = replace(options or W.AlignmentOptions(), keep_candidates=True)
    res, model, (sig, act, det, cands, path) = W._align_with_internals(
        waveform, duration, transcript, sample_times, o, tokenize)
    if result is not None:
        res = result
    D = float(duration)
    t1 = D if t1 is None else min(D, t1)
    t0 = max(0.0, min(t0, t1 - 1e-3))
    span = t1 - t0
    width = int(max(600, min(20000, span * px_per_s))) + 80
    X = lambda t: 60 + (t - t0) / span * (width - 80)  # noqa: E731
    top, eh = 30, 180                   # the envelope band
    wy = top + eh + 20                  # the words band
    ty = wy + 70                        # the truth band
    height = ty + (60 if truth is not None else 0) + 30
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'viewBox="0 0 {width} {height}" font-family="sans-serif" font-size="11">',
             '<rect width="100%" height="100%" fill="#fff"/>']
    Y = lambda v: top + eh - v * eh     # noqa: E731
    # speech regions and pauses
    for a, b in res.speech_regions:
        if b < t0 or a > t1:
            continue
        parts.append(f'<rect x="{X(max(a, t0)):.1f}" y="{top}" width="{max(0.5, X(min(b, t1)) - X(max(a, t0))):.1f}" '
                     f'height="{eh}" fill="#e8f1fb"/>')
    for p in res.pauses:
        if p.end < t0 or p.start > t1:
            continue
        op = 0.15 + 0.5 * p.strength
        parts.append(f'<rect x="{X(max(p.start, t0)):.1f}" y="{top}" '
                     f'width="{max(0.5, X(min(p.end, t1)) - X(max(p.start, t0))):.1f}" height="{eh}" '
                     f'fill="#f6c28b" fill-opacity="{op:.2f}"><title>{_esc(p.kind)} ({_esc(p.role)}) '
                     f'{p.start:.2f}-{p.end:.2f}</title></rect>')
    # the thresholds
    for v, col in ((act.low, "#9bb"), (act.high, "#6aa")):
        parts.append(f'<line x1="60" x2="{width - 20}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" '
                     f'stroke="{col}" stroke-dasharray="4 3"/>')
    # the envelope: its max per pixel column, so nothing is lost to drawing
    c = sig.centres
    sel = (c >= t0) & (c <= t1)
    if sel.any():
        cols = ((c[sel] - t0) / span * (width - 80)).astype(int)
        lv = sig.level[sel]
        mx = np.full(cols.max() + 1, -1.0)
        np.maximum.at(mx, cols, lv)
        xs = np.flatnonzero(mx >= 0)
        pts = " ".join(f"{60 + x},{Y(mx[x]):.1f}" for x in xs)
        parts.append(f'<polyline points="{pts}" fill="none" stroke="#345" stroke-width="1"/>')
    # candidates
    for cb in res.candidates:
        if cb.time < t0 or cb.time > t1:
            continue
        col = {"pause": "#d80", "valley": "#2a2", "refined": "#6c6", "edge": "#000",
               "prior": "#aaa", "fallback": "#ddd"}.get(cb.kind, "#ccc")
        h = 6 + 14 * max(0.0, min(1.0, cb.strength))
        parts.append(f'<line x1="{X(cb.time):.1f}" x2="{X(cb.time):.1f}" y1="{top + eh}" '
                     f'y2="{top + eh + h:.1f}" stroke="{col}"/>')
    # the words
    for i, w in enumerate(res.words):
        if w.end < t0 or w.start > t1:
            continue
        a, b = X(max(w.start, t0)), X(min(w.end, t1))
        col = "#1b6ac9" if i % 2 == 0 else "#7a3fc2"
        parts.append(f'<rect x="{a:.1f}" y="{wy}" width="{max(0.5, b - a):.1f}" height="22" '
                     f'fill="{col}" fill-opacity="0.18" stroke="{col}"/>')
        parts.append(f'<line x1="{a:.1f}" x2="{a:.1f}" y1="{top}" y2="{wy + 22}" stroke="{col}" '
                     f'stroke-opacity="0.5"/>')
        if w.start_max > w.start_min:
            parts.append(f'<line x1="{X(max(w.start_min, t0)):.1f}" x2="{X(min(w.start_max, t1)):.1f}" '
                         f'y1="{wy - 4}" y2="{wy - 4}" stroke="{col}" stroke-width="2"/>')
        parts.append(f'<text x="{a + 2:.1f}" y="{wy + 15}" fill="#111">{_esc(w.word)}</text>')
        parts.append(f'<rect x="{a:.1f}" y="{wy + 26}" width="{max(0.5, b - a):.1f}" '
                     f'height="{20 * w.confidence:.1f}" fill="#3a3"><title>confidence '
                     f'{w.confidence:.2f}</title></rect>')
    if truth is not None:
        parts.append(f'<text x="4" y="{ty + 15}" fill="#555">truth</text>')
        for i in range(len(truth.tokens)):
            s, e = truth.starts[i], truth.ends[i]
            if e < t0 or s > t1:
                continue
            a, b = X(max(s, t0)), X(min(e, t1))
            parts.append(f'<rect x="{a:.1f}" y="{ty}" width="{max(0.5, b - a):.1f}" height="22" '
                         f'fill="#c33" fill-opacity="0.12" stroke="#c33"/>')
            parts.append(f'<text x="{a + 2:.1f}" y="{ty + 15}" fill="#822">{_esc(truth.tokens[i])}</text>')
    # the time axis
    step = 1.0 if span <= 30 else 5.0 if span <= 150 else 30.0 if span <= 900 else 300.0
    k = math.ceil(t0 / step)
    while k * step <= t1:
        x = X(k * step)
        parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top - 4}" y2="{top}" stroke="#666"/>'
                     f'<text x="{x + 2:.1f}" y="{top - 6}" fill="#666">{k * step:g}s</text>')
        k += 1
    parts.append(f'<text x="4" y="{top + 12}" fill="#555">level</text>'
                 f'<text x="4" y="{wy + 15}" fill="#555">words</text>'
                 f'<text x="{width - 420}" y="{height - 8}" fill="#555">global confidence '
                 f'{res.global_confidence:.2f} -- alignment confidence, not recognition</text>')
    parts.append("</svg>")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    try:                                # the optional PNG
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(min(60, span * px_per_s / 100), 3))
        ax.plot(c[sel], sig.level[sel], lw=0.6, color="#345")
        for w in res.words:
            if t0 <= w.start <= t1:
                ax.axvline(w.start, color="#1b6ac9", lw=0.6)
        if truth is not None:
            for s in truth.starts:
                if t0 <= s <= t1:
                    ax.axvline(s, color="#c33", lw=0.5, ls=":")
        fig.savefig(os.path.splitext(out_path)[0] + ".png", dpi=100)
        plt.close(fig)
    except Exception:
        pass
    return out_path


# ============================================================ the bench
SCENARIOS = {
    # name: (what it is, the SynthConfig changes)
    "clean": ("a clear recording at 100 a second", {}),
    "no pauses": ("pauses mostly gone, shallow dips between words",
                  dict(sentence_pause_prob=0.25, comma_pause_prob=0.1, sentence_pause=(0.12, 0.3),
                       valley_depth=0.3, word_gap_prob=0.02)),
    "noisy": ("the noise floor 20 dB higher, and clicks",
              dict(noise_db=-18.0, noise_wobble_db=5.0, clicks=6)),
    "loose lengths": ("word lengths poorly follow their letters",
                      dict(length_correlation=0.3, duration_jitter=0.45)),
    "rate jump": ("the pace doubles halfway",
                  dict(rate_jump=(0.5, 2.0))),
    "20 Hz": ("a YouTube picture of the sound: 20 a second", dict(rate=20.0)),
    "5 Hz": ("a very sparse picture: 5 a second", dict(rate=5.0)),
    "rms": ("RMS rather than peak buckets", dict(style="rms")),
    "persian": ("Persian with harakat", dict(language="fa", harakat=True)),
    "chinese": ("Chinese, no spaces", dict(language="zh", n_words=260)),
    "captions": ("a video: captions cut anywhere", dict(pieces="captions")),
    # a reader who stops for breath between plain words, a second at a time:
    # the pause prior's length term, uncapped, could not bear it
    "hesitations": ("pauses of 0.6-1.5 s after plain words, 6 in 100",
                    dict(stray_pause_prob=0.06, stray_pause=(0.6, 1.5))),
    # a reader whose sentence ends are all shorter than a phrase pause: the
    # split calibration lowers a sentence end's prior below a comma's here
    # (docs/wavealign.md, section 3) -- the trade-off, kept on the bench
    "fast reader": ("sentence pauses of 0.10-0.22 s, commas read straight on",
                    dict(sentence_pause=(0.10, 0.22), sentence_pause_prob=0.9,
                         comma_pause_prob=0.0, stray_pause_prob=0.0)),
    # auto-captions as YouTube leaves them: no punctuation, no paragraph --
    # by the sound's weakest case, still behind by the text on 300 Chinese
    # characters (docs/wavealign.md, section 6); held to within a margin
    "bare en": ("captions with no punctuation, 300 words",
                dict(pieces="captions", bare=True, n_words=300)),
    "bare zh": ("Chinese captions with no punctuation, 300 characters",
                dict(language="zh", pieces="captions", bare=True, n_words=300)),
    "bare fa": ("Persian captions with no punctuation, 300 words",
                dict(language="fa", pieces="captions", bare=True, n_words=300)),
    "bare en 1000": ("captions with no punctuation, 1000 words",
                     dict(pieces="captions", bare=True, n_words=1000)),
    "bare zh 1000": ("Chinese captions with no punctuation, 1000 characters",
                     dict(language="zh", pieces="captions", bare=True, n_words=1000)),
    "bare fa 1000": ("Persian captions with no punctuation, 1000 words",
                     dict(language="fa", pieces="captions", bare=True, n_words=1000)),
    "an hour": ("one hour, about 10,000 words", dict(n_words=10000, fine_rate=1000.0)),
}


def evaluate(case: SynthCase, options=None, kind: Optional[str] = None) -> dict:
    """The new aligner and by the text on one case: word and piece measures
    for both, and the time the new one took."""
    kind = kind or ("point" if case.config.pieces == "captions" else "span")
    t = time.perf_counter()
    res = W.align_transcript_to_waveform(case.envelope, case.duration, case.transcript,
                                         options=options)
    t_words = time.perf_counter() - t
    t = time.perf_counter()
    est = W.estimate_pieces(case.envelope, case.duration, case.pieces, kind, options=options)
    t_pieces = time.perf_counter() - t
    if len(res.words) != len(case.tokens):
        raise AssertionError(f"{len(res.words)} words aligned, {len(case.tokens)} made")
    bs, be = by_the_text_words(case.tokens, case.duration)
    return {
        "new_words": word_metrics([w.start for w in res.words], [w.end for w in res.words], case),
        "old_words": word_metrics(bs, be, case),
        "new_pieces": piece_metrics(est["pieces"], case),
        "old_pieces": piece_metrics(by_the_text(case.pieces, case.duration, kind), case),
        "seconds_words": t_words, "seconds_pieces": t_pieces,
        "confidence": res.global_confidence, "anchored": est["anchored"],
        "boundaries": est["boundaries"], "n_words": len(case.tokens), "duration": case.duration,
    }


def _mean_dicts(ds: list) -> dict:
    out = {}
    for k in ds[0]:
        v = [d[k] for d in ds if isinstance(d.get(k), (int, float)) and not math.isnan(d[k])]
        out[k] = float(np.mean(v)) if v else float("nan")
    return out


def run_bench(names=None, seeds=(0, 1, 2), options=None, n_words: Optional[int] = None,
              verbose: bool = True) -> dict:
    """Every scenario over a few seeds; returns {name: averaged results}."""
    names = list(names or SCENARIOS)
    out = {}
    for name in names:
        desc, changes = SCENARIOS[name]
        rows = []
        for s in (seeds if name != "an hour" else seeds[:1]):
            ch = dict(changes)
            if n_words and name != "an hour" and "n_words" not in ch:
                ch["n_words"] = n_words
            cfg = replace(SynthConfig(seed=s), **ch)
            rows.append(evaluate(synthesize(cfg), options))
        agg = {k: _mean_dicts([r[k] for r in rows]) for k in
               ("new_words", "old_words", "new_pieces", "old_pieces")}
        for k in ("seconds_words", "seconds_pieces", "confidence", "anchored", "boundaries",
                  "n_words", "duration"):
            agg[k] = float(np.mean([r[k] for r in rows]))
        out[name] = agg
        if verbose:
            print(f"  {name}: done in {agg['seconds_words'] + agg['seconds_pieces']:.2f} s", file=sys.stderr)
    return out


def format_bench(results: dict) -> str:
    """The bench as tables: words, then pieces; new against by the text."""
    lines = []
    head = (f"{'scenario':<14} {'':<5} {'mean':>6} {'median':>6} {'p90':>6} {'sent.':>6} "
            f"{'<50ms':>6} {'<100':>6} {'<250':>6}")
    for what, a, b in (("WORDS (seconds; % within)", "new_words", "old_words"),
                       ("PIECES (distance from the true silence between pieces)", "new_pieces", "old_pieces")):
        lines += ["", what, head, "-" * len(head)]
        for name, r in results.items():
            for tag, key in (("new", a), ("text", b)):
                m = r[key]
                lines.append(f"{name if tag == 'new' else '':<14} {tag:<5} {m['mean']:6.3f} {m['median']:6.3f} "
                             f"{m['p90']:6.3f} {m['sentence']:6.3f} {m['w50']:6.1f} {m['w100']:6.1f} "
                             f"{m['w250']:6.1f}")
    lines += ["", f"{'scenario':<14} {'words':>6} {'length':>8} {'align s':>8} {'pieces s':>8} "
              f"{'conf.':>6} {'anchored':>9}"]
    for name, r in results.items():
        lines.append(f"{name:<14} {r['n_words']:6.0f} {r['duration']:7.0f}s {r['seconds_words']:8.2f} "
                     f"{r['seconds_pieces']:8.2f} {r['confidence']:6.2f} "
                     f"{r['anchored']:4.0f}/{r['boundaries']:<4.0f}")
    return "\n".join(lines)


# the parameters the sensitivity study varies: (name, lower, higher) -- each
# once below and once above its default, the rest left alone
SENSITIVITY = [
    ("w_pause", 0.5, 2.0), ("w_anchor", 0.5, 2.0), ("w_boundary", 0.5, 2.0),
    ("w_activity", 1.0, 4.0), ("w_duration", 0.5, 2.0), ("w_rate", 0.5, 2.0),
    ("w_rate_step", 0.5, 2.0), ("w_unassigned", 0.75, 3.0),
    ("sigma_duration", 0.3, 0.7), ("sigma_rate", 0.25, 0.5), ("alpha", 0.6, 1.0),
    ("pause_prob_word", 0.02, 0.08), ("anchor_full_s", 0.2, 0.45),
    ("calibrate_pauses", False, True), ("rate_state", False, True),
    ("low_frac", 0.2, 0.4), ("high_frac", 0.4, 0.65), ("min_pause_s", 0.04, 0.12),
    ("smooth_s", 0.01, 0.04), ("refine_passes", 1, 3), ("rate_beam", 5.0, 12.0),
    ("rate_latent", False, True), ("rate_jump_nats", 1.5, 6.0), ("rate_unit_sigma", 0.08, 0.15),
    ("dip_rank", 0.0, 4.0), ("calibrate_mode", "scale", "split"), ("rate_per_candidate", 0, 8),
    ("rate_beam_window_s", 1e9, 1.0),
]


def run_sensitivity(names=("clean", "no pauses", "noisy", "20 Hz", "rate jump", "loose lengths"),
                    seeds=(0, 1),
                    params=None) -> list:
    """Each parameter at a lower and a higher value, the rest at their
    defaults: the change in the mean word error and the mean piece error
    over the scenarios, against the defaults."""
    def score(opts):
        r = run_bench(names, seeds, opts, verbose=False)
        return (float(np.mean([r[n]["new_words"]["mean"] for n in names])),
                float(np.mean([r[n]["new_pieces"]["mean"] for n in names])))
    base = score(W.AlignmentOptions())
    rows = [("defaults", "", base[0], base[1], 0.0, 0.0)]
    for name, lo, hi in (params or SENSITIVITY):
        for v in (lo, hi):
            o = replace(W.AlignmentOptions(), **{name: v})
            s = score(o)
            rows.append((name, v, s[0], s[1], s[0] - base[0], s[1] - base[1]))
            print(f"  {name}={v}: words {s[0]:.3f} pieces {s[1]:.3f}", file=sys.stderr)
    return rows


# ============================================================ the command
# ============================================================ a real recording
# "bench-audio": the same measure as the Kokoro bench, on any recording
# someone trusts the cuts of.  Nothing here knows of a shelf: it is handed
# a sound file and a list of pieces with their true times, and it plays the
# user's part -- the boundaries are right up to a line, E is pressed -- over
# stretches of 3, 10, 30 pieces and all the rest, "by the text" against "by
# the sound", each answer rounded to a hundredth as the page and the door
# round it.

def _r2(x: float) -> float:
    """timeline.js r2: Math.round(x * 100) / 100 (a half goes up)."""
    return math.floor(x * 100 + 0.5) / 100


def load_truth(path: str) -> dict:
    """The pieces and their true times from a JSON file: a list of
    {"text", "t0" (or "start"), "t1" (or "end")}, or {"pieces": [...],
    "kind": "span" | "point"}.  A caption needs no "t1" (it runs until the
    next begins); a book's piece does.  Times in seconds from the start of
    the recording, in order."""
    import json
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    items = raw.get("pieces") if isinstance(raw, dict) else raw
    kind = (raw.get("kind") if isinstance(raw, dict) else None) or ""
    if not isinstance(items, list) or len(items) < 2:
        raise ValueError("the file must hold at least two pieces")
    texts, t0, t1 = [], [], []
    for k, it in enumerate(items):
        if not isinstance(it, dict) or "text" not in it:
            raise ValueError(f"piece {k} has no text")
        a = it.get("t0", it.get("start"))
        b = it.get("t1", it.get("end"))
        if a is None:
            raise ValueError(f"piece {k} has no start (t0)")
        texts.append(str(it["text"]))
        t0.append(float(a))
        t1.append(None if b is None else float(b))
    if any(y < x for x, y in zip(t0, t0[1:])):
        raise ValueError("the pieces' starts must not go backwards")
    kind = kind or ("span" if all(b is not None for b in t1) else "point")
    if kind == "span" and any(b is None for b in t1):
        raise ValueError("a book's pieces need their ends (t1)")
    return {"texts": texts, "t0": np.array(t0), "t1": t1, "kind": kind}


def recording_peaks(src: str):
    """(1 ms peaks of the whole recording, its duration): Parseh's own
    envelope (lib/audiofile.py) at a thousand a second, from which every
    stretch's picture is then cut exactly as the doors would make it."""
    import audiofile
    dur = float(audiofile.duration(src))
    if not dur > 0:
        raise ValueError("the recording has no length")
    return np.asarray(audiofile.envelope(src, 0.0, dur, 1000), float), dur


def _env100(p1k: np.ndarray, start: float, end: float) -> np.ndarray:
    """The 100 a second a book's door hands over for [start, end]: the peak
    of every 10 ms from `start`, cut from the 1 ms peaks."""
    count = max(1, int((end - start) * 100 + 0.5))
    j0 = int(round(start * 1000))
    seg = p1k[j0:j0 + count * 10]
    if seg.size < count * 10:
        seg = np.concatenate([seg, np.zeros(count * 10 - seg.size)])
    return seg.reshape(count, 10).max(axis=1)


def _picture20(p1k: np.ndarray) -> np.ndarray:
    """A YouTube video's recorded picture (player.js capRecordWave): the
    k-th number the loudest of the 50 ms centred on k/20 s, the whole
    divided by its loudest and kept to three decimals."""
    n = int(math.ceil(p1k.size / 50.0)) + 1
    pad = np.concatenate([np.zeros(25), p1k, np.zeros(n * 50 - p1k.size)])
    v = pad[:n * 50].reshape(n, 50).max(axis=1)
    top = float(v.max()) or 1.0
    return np.round(v / top, 3)


def _slice20(w20: np.ndarray, rate: float, start: float, end: float):
    """(values, times from `start`) of a recorded picture over [start, end]
    as serve.py's wave_slice hands them over: every number whose moment
    k/rate falls inside, at its moment."""
    lo = max(0, int(math.ceil(start * rate - 1e-6)))
    hi = min(w20.size - 1, int(math.floor(end * rate + 1e-6)))
    k = np.arange(lo, hi + 1)
    return w20[lo:hi + 1], np.minimum(end - start, np.maximum(0.0, k / rate - start))


def audio_stretches(n: int, sizes=("3", "10", "30", "all"), per_size: int = 12) -> list:
    """(first piece, how many) of every stretch: for each size M, up to
    `per_size` starting pieces spread evenly over the recording ("all" runs
    to the last piece)."""
    out = []
    for m in sizes:
        if m == "all":
            firsts = np.unique(np.linspace(0, n - 2, min(per_size, n - 1)).round().astype(int))
            out += [(int(i), n - int(i), m) for i in firsts]
            continue
        M = int(m)
        if M < 2 or M > n:
            continue
        firsts = np.unique(np.linspace(0, n - M, min(per_size, n - M + 1)).round().astype(int))
        out += [(int(i), M, m) for i in firsts]
    return out


def bench_audio(truth: dict, p1k: Optional[np.ndarray] = None, duration: float = 0.0,
                wave: Optional[dict] = None, rates=(100, 20), sizes=("3", "10", "30", "all"),
                per_size: int = 12, options=None) -> dict:
    """"By the text" against "by the sound" over the stretches of a trusted
    recording.  `p1k` (1 ms peaks, recording_peaks) gives both pictures, a
    book's 100 a second and a video's 20; `wave` ({"rate", "peaks"}, a video's
    recorded waveform.json) gives the second alone.  Returns, per rate and
    size and over all, the errors of every piece start but the first (the
    line in hand): mean, median, p90, the share within 0.1 / 0.25 / 0.5 / 1
    s, the mean distance from the pause before the piece (0 anywhere in it,
    where a hand might put it), and how often the sound beats the text."""
    texts, T0, T1, kind = truth["texts"], truth["t0"], truth["t1"], truth["kind"]
    n = len(texts)
    point = kind == "point"
    w20 = None
    if wave is not None:
        w20 = np.asarray(wave["peaks"], float)
        wrate = float(wave.get("rate", 20))
        rates = (20,)
    elif p1k is not None:
        w20, wrate = _picture20(p1k), 20.0
    rows = []
    for first, count, m in audio_stretches(n, sizes, per_size):
        idx = slice(first, first + count)
        last = first + count - 1
        start = float(T0[first])
        if T1[last] is not None:
            end = float(T1[last])
        elif last + 1 < n:
            end = float(T0[last + 1])
        else:
            end = float(duration)
        if not end > start + 0.4:
            continue
        ts = texts[idx]
        true0 = T0[idx]
        # the pause before each piece: from the last one's end, where known
        prev_end = np.array([T1[k - 1] if (k > first and T1[k - 1] is not None) else T0[k]
                             for k in range(first, first + count)], float)
        old = by_the_text(ts, end - start, kind)
        old0 = np.array([_r2(start + p["t0"]) for p in old])
        for rate in rates:
            if rate == 100:
                if p1k is None:
                    continue
                vals, times = _env100(p1k, start, end), None
            else:
                vals, times = _slice20(w20, wrate, start, end)
            t = time.perf_counter()
            est = W.estimate_pieces(vals, end - start, ts, kind, sample_times=times,
                                    options=options)
            secs = time.perf_counter() - t
            new0 = np.array([start] + [_r2(start + p["t0"]) for p in est["pieces"][1:]])
            rows.append({"m": m, "rate": rate, "first": first, "count": count, "secs": secs,
                         "text": np.abs(old0[1:] - true0[1:]), "sound": np.abs(new0[1:] - true0[1:]),
                         "text_gap": _gap_distance(old0[1:], prev_end[1:], true0[1:]),
                         "sound_gap": _gap_distance(new0[1:], prev_end[1:], true0[1:])})

    def stats(sel):
        out = {}
        for est in ("text", "sound"):
            e = np.concatenate([r[est] for r in sel]) if sel else np.zeros(0)
            g = np.concatenate([r[est + "_gap"] for r in sel]) if sel else np.zeros(0)
            if not e.size:
                continue
            out[est] = {"n": int(e.size), "mean": float(e.mean()), "median": float(np.median(e)),
                        "p90": float(np.percentile(e, 90)),
                        **{f"w{x}": float((e <= x).mean() * 100) for x in (0.1, 0.25, 0.5, 1.0)},
                        "gap": float(g.mean())}
        if sel:
            win = [r["sound"].mean() < r["text"].mean() for r in sel if r["text"].size]
            out["stretches"] = len(sel)
            out["sound_better_pct"] = float(np.mean(win) * 100) if win else float("nan")
        return out

    res = {"kind": kind, "pieces": n, "all": stats(rows), "by": {}}
    for rate in sorted({r["rate"] for r in rows}, reverse=True):
        for m in sizes:
            sel = [r for r in rows if r["rate"] == rate and r["m"] == m]
            if sel:
                res["by"][f"{rate} Hz, M={m}"] = stats(sel)
        res["by"][f"{rate} Hz, all sizes"] = stats([r for r in rows if r["rate"] == rate])
    res["seconds"] = float(np.mean([r["secs"] for r in rows])) if rows else 0.0
    return res


def format_bench_audio(res: dict) -> str:
    head = (f"{'':<22} {'':<5} {'starts':>6} {'mean':>6} {'median':>6} {'p90':>6} "
            f"{'<.1':>5} {'<.25':>5} {'<.5':>5} {'<1':>5} {'gap':>6} {'win%':>5}")
    lines = [f"{res['pieces']} pieces ({res['kind']}); errors of the piece starts in seconds, the "
             "first of each stretch (the line in hand) left out; 'gap' counts a start anywhere "
             "in the pause before its piece as right; win% = stretches where the sound beats "
             "the text", "", head, "-" * len(head)]
    for name, st in list(res["by"].items()) + [("everything", res["all"])]:
        for est in ("text", "sound"):
            s = st.get(est)
            if not s:
                continue
            win = f"{st['sound_better_pct']:5.1f}" if est == "sound" else ""
            lines.append(f"{name if est == 'text' else '':<22} {est:<5} {s['n']:>6} {s['mean']:6.3f} "
                         f"{s['median']:6.3f} {s['p90']:6.3f} {s['w0.1']:5.1f} {s['w0.25']:5.1f} "
                         f"{s['w0.5']:5.1f} {s['w1.0']:5.1f} {s['gap']:6.3f} {win:>5}")
    lines.append("")
    lines.append(f"by the sound took {res['seconds']:.2f} s a stretch on average")
    return "\n".join(lines)


def demo(seed: int = 4, language: str = "en", n_words: int = 40) -> str:
    """The table SPEC.md asks for, for one made-up recording."""
    case = synthesize(SynthConfig(seed=seed, language=language, n_words=n_words))
    res = W.align_transcript_to_waveform(case.envelope, case.duration, case.transcript)
    lines = [f"{'WORD':<15}{'START':>7}{'END':>9}{'CONFIDENCE':>13}   {'(true start':>11} {'end)':>6}",
             "-" * 64]
    for i, w in enumerate(res.words):
        lines.append(f"{w.word:<15}{w.start:7.2f}{w.end:9.2f}{w.confidence:13.2f}   "
                     f"{case.starts[i]:11.2f} {case.ends[i]:6.2f}")
    m = word_metrics([w.start for w in res.words], [w.end for w in res.words], case)
    bs, be = by_the_text_words(case.tokens, case.duration)
    b = word_metrics(bs, be, case)
    lines += ["", f"{len(res.words)} words over {case.duration:.2f} s; global confidence "
                  f"{res.global_confidence:.2f} (alignment confidence, not recognition)",
              f"mean boundary error {m['mean'] * 1000:.0f} ms (by the text: {b['mean'] * 1000:.0f} ms); "
              f"within 100 ms {m['w100']:.0f}% (by the text: {b['w100']:.0f}%)"]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="wavealign_lab", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo", help="align a made-up recording and print the table")
    d.add_argument("--seed", type=int, default=4)
    d.add_argument("--language", default="en")
    d.add_argument("--words", type=int, default=40)
    b = sub.add_parser("bench", help="new against by the text, over the scenarios")
    b.add_argument("--quick", action="store_true", help="leave out the hour-long case")
    b.add_argument("--seeds", type=int, default=3)
    b.add_argument("--only", nargs="*", help="these scenarios alone")
    b.add_argument("--long", type=float, default=0.0,
                   help="also time a case this many hours long (4 = the contract's)")
    p = sub.add_parser("plot", help="draw one case as SVG")
    p.add_argument("out")
    p.add_argument("--seed", type=int, default=4)
    p.add_argument("--scenario", default="clean")
    p.add_argument("--words", type=int, default=60)
    p.add_argument("--start", type=float, default=0.0)
    p.add_argument("--end", type=float, default=None)
    s = sub.add_parser("sensitivity", help="vary each parameter and report the effect")
    s.add_argument("--seeds", type=int, default=2)
    r = sub.add_parser("bench-audio", help="by the text against by the sound on a recording "
                       "whose cuts you trust")
    r.add_argument("audio", help="the sound file (anything ffmpeg reads); with --wave, may be -")
    r.add_argument("truth", help="JSON: [{text, t0, t1}, ...] or {pieces: [...], kind}")
    r.add_argument("--kind", choices=("span", "point"), default=None,
                   help="span (a book) or point (captions); else the file says, or t1 does")
    r.add_argument("--wave", default=None,
                   help="a video's recorded picture ({rate, peaks}, its waveform.json) "
                        "instead of the sound file: 20 a second only")
    r.add_argument("--rate", choices=("100", "20", "both"), default="both")
    r.add_argument("--sizes", default="3,10,30,all", help="stretch sizes, in pieces")
    r.add_argument("--per-size", type=int, default=12, help="stretches of each size")
    r.add_argument("--json", default=None, help="also write the numbers here")
    a = ap.parse_args(argv)
    if a.cmd == "demo":
        print(demo(a.seed, a.language, a.words))
    elif a.cmd == "bench":
        names = a.only or [n for n in SCENARIOS if not (a.quick and n == "an hour")]
        res = run_bench(names, tuple(range(a.seeds)))
        print(format_bench(res))
        if a.long > 0:
            print()
            print(time_long(a.long))
    elif a.cmd == "plot":
        cfg = replace(SynthConfig(seed=a.seed, n_words=a.words), **SCENARIOS[a.scenario][1])
        case = synthesize(cfg)
        plot_alignment(a.out, case.envelope, case.duration, case.transcript, truth=case,
                       t0=a.start, t1=a.end)
        print(a.out)
    elif a.cmd == "bench-audio":
        import json
        truth = load_truth(a.truth)
        if a.kind:
            truth["kind"] = a.kind
        rates = {"100": (100,), "20": (20,), "both": (100, 20)}[a.rate]
        sizes = tuple(x.strip() for x in a.sizes.split(",") if x.strip())
        if a.wave:
            with open(a.wave, encoding="utf-8") as f:
                wave = json.load(f)
            # the picture's own length stands in for the recording's
            dur = (len(wave.get("peaks") or []) / float(wave.get("rate", 20))
                   if a.audio == "-" else recording_peaks(a.audio)[1])
            res = bench_audio(truth, None, dur, wave=wave, sizes=sizes, per_size=a.per_size)
        else:
            p1k, dur = recording_peaks(a.audio)
            res = bench_audio(truth, p1k, dur, rates=rates, sizes=sizes, per_size=a.per_size)
        print(format_bench_audio(res))
        if a.json:
            with open(a.json, "w", encoding="utf-8") as f:
                json.dump(res, f, indent=1)
    elif a.cmd == "sensitivity":
        rows = run_sensitivity(seeds=tuple(range(a.seeds)))
        print(f"{'parameter':<16} {'value':>6} {'words':>7} {'pieces':>7} {'d words':>8} {'d pieces':>9}")
        for r in rows:
            print(f"{r[0]:<16} {str(r[1]):>6} {r[2]:7.3f} {r[3]:7.3f} {r[4]:+8.3f} {r[5]:+9.3f}")
    return 0


def time_long(hours: float, seed: int = 0) -> str:
    """How long estimate_pieces takes on a recording `hours` long (about
    10,000 words and 450 pieces an hour), and its error."""
    n = int(10000 * hours)
    case = synthesize(SynthConfig(seed=seed, n_words=n, fine_rate=500.0))
    t = time.perf_counter()
    est = W.estimate_pieces(case.envelope, case.duration, case.pieces, "span")
    dt = time.perf_counter() - t
    m = piece_metrics(est["pieces"], case)
    o = piece_metrics(by_the_text(case.pieces, case.duration), case)
    try:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except Exception:
        peak = float("nan")
    return (f"{hours:g} h: {n} words, {len(case.pieces)} pieces, {case.duration:.0f} s of envelope "
            f"-> estimate_pieces {dt:.1f} s (peak memory of the process {peak:.0f} MB); "
            f"piece error mean {m['mean']:.3f} s (by the text {o['mean']:.3f} s), "
            f"within 250 ms {m['w250']:.0f}% (by the text {o['w250']:.0f}%)")


if __name__ == "__main__":
    sys.exit(main())
