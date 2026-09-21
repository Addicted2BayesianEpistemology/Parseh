#!/usr/bin/env python3
"""Stage 1 — align the narration to the reading edition and record the times.

Writes full-line `% @par` comments (one per subparagraph) into the ch*.tex files and a
`timings.json` sidecar keyed by a hash of each subparagraph's text (stripped of
the marks the book's language drops in its bare pass -- the Persian keys are
what they always were).

The book's language (books.Book.lang) decides how the text is normalised for
matching: which marks come off, whether the Arabic-script letter variants are
folded, which digits are read, and what a token is -- a space-separated word,
or, for a language without word separators (Japanese), one character, so a
narration can still be aligned roughly.  The algorithm is the same for all.

    python3 timestamp.py                 align, insert comments, write sidecar
    python3 timestamp.py --force         redo chunks that already carry a time
    python3 timestamp.py --from-sidecar  restore comments from timings.json only
    python3 timestamp.py --dry-run       report, touch nothing

The .tex is the only authority on what the text says.  The transcript is a
noisy time index: it tells us *when*, never *what*.  Not one of its words is
written into the .tex or into the reader.

A comment that OCCUPIES A WHOLE LINE is consumed by TeX together with its
newline and cannot affect output.  A trailing `%` would swallow the following
newline and the inter-token space with it.  Every comment written here starts
at column 0 for that reason, and `--verify-pdf` proves it.
"""
import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from bisect import bisect_left, bisect_right

LIB = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, LIB)
import texparse as T                                           # noqa: E402
import languages                                               # noqa: E402
from books import find_book                                    # noqa: E402

# filled in by main() once --book is known
HERE = BOOK = SIDECAR = None
BOOKOBJ = None
# the book's language; Persian until a book is bound, so the helpers below
# (canon, tokens, subkey) work for a caller that only imports them
LANG = languages.get(languages.DEFAULT)


def _bind(b):
    """Point the module at one book."""
    global HERE, BOOK, SIDECAR, BOOKOBJ, LANG
    BOOKOBJ = b
    LANG = b.lang
    HERE, BOOK, SIDECAR = b.dir, b.main, b.timings


def subkey(sub):
    """Stable id for a subparagraph.  The label alone collides -- chapter 1 and
    chapter 2 both have a 4.3 -- so the text is what makes it unique: hashed
    with the language's marks stripped (the Sub knows its language), so a
    re-vowelling does not lose the times.  Persian keys are unchanged.

    The chunks are joined with the LANGUAGE's word separator rather than with
    texparse's own space (Sub.fa), so that the key is the subparagraph's text
    and not its division into chunks: joining a Japanese subparagraph's chunks
    with a space gives one string before two chunks are merged and another
    after, and the times of a subparagraph nobody retimed would be looked up
    under a key that had moved.  For every language whose words are separated
    by a space the two joins are the same string, so no existing key changes
    -- Persian's, Arabic's and the Latin-script ones' least of all.  Japanese is
    the one language where the key does move, and a Japanese edition with times
    already recorded loses them to it: re-run `timestamp.py --from-sidecar` if
    the sidecar still has them under the old keys, or re-align.  No such
    edition exists here, and the alternative was a key that moved every time
    somebody re-chunked a Japanese subparagraph."""
    lang = getattr(sub, "lang", None) or LANG
    text = (lang.word_sep or "").join(c.fa for c in sub.chunks)
    h = hashlib.sha1(lang.strip(text).encode("utf-8")).hexdigest()[:12]
    return "%s-%s" % (sub.num, h)


def audio_seconds(path):
    """How long a recording is, or None when nothing here can tell.

    ffprobe if it is on the machine (it comes with ffmpeg, which the silence
    snapping already wants), and otherwise the WAV header, which the standard
    library reads without anything installed.  NONE IS AN ANSWER: a length
    invented out of nothing would put every subparagraph at the wrong second
    and look exactly like a real alignment.
    """
    if not path or not os.path.exists(path):
        return None
    probe = shutil.which("ffprobe") or (
        os.path.join(os.path.dirname(FFMPEG), "ffprobe")
        if os.path.exists(FFMPEG) else None)
    if probe and os.path.exists(probe):
        try:
            r = subprocess.run([probe, "-v", "error", "-show_entries",
                                "format=duration", "-of",
                                "default=noprint_wrappers=1:nokey=1", path],
                               capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                secs = float((r.stdout or "").strip())
                if secs > 0:
                    return secs
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    try:
        import wave
        with contextlib.closing(wave.open(path, "rb")) as w:
            rate = w.getframerate()
            if rate:
                return w.getnframes() / float(rate)
    except Exception:
        pass
    return None


def spread(subs, seconds, floor=0.4):
    """Times laid across a recording in proportion to how long each
    subparagraph IS -> [(t0, t1), ...].

    The measure is the aligner's own: the text with the language's marks
    stripped and the spaces taken out, so a long sentence gets a long slice
    and the two ways of timing a book agree about what "long" means.

    This is a FIRST GUESS and nothing more.  It is what a recording with no
    transcript can honestly offer -- somewhere to start from, so every
    subparagraph plays something and the ones that drift can be nudged by
    hand -- and it is written with a low confidence and its own `src` so that
    a real alignment later replaces it without being asked twice.
    """
    sizes = [max(1, len(LANG.strip(x.fa).replace(" ", ""))) for x in subs]
    total = float(sum(sizes)) or 1.0
    out, at = [], 0.0
    for k, size in enumerate(sizes):
        # the last one ends at the end: rounding must not leave a gap of
        # silence nobody can play
        end = seconds if k == len(sizes) - 1 else at + seconds * size / total
        if end < at + floor:
            end = min(seconds, at + floor)
        out.append((round(at, 3), round(end, 3)))
        at = end
    return out


def region_subs(allsubs, first, last):
    """The subparagraphs a narration covers, named by label: "1.1" to "3.4".

    LABELS AND NOT INDICES, and not text hashes either: a label is what the
    page shows, what the `% @par` line has always carried and what somebody
    types into the panel, and it survives the re-chunking that moves a hash.
    Either end left out means "from the beginning" or "to the end", so a
    narration that names no region covers the whole book -- which is the
    single-recording case, and every book written before this one.

    A label is unique only within its chapter (chapter 1 and chapter 2 both
    have a 4.3), so the first match is taken for the start and the last for
    the end: the widest reading of what somebody asked for, and the panel
    offers chapter ends rather than making anyone type one.
    """
    i, j = 0, len(allsubs) - 1
    if first:
        for k, x in enumerate(allsubs):
            if x.num == first:
                i = k
                break
        else:
            sys.exit("no subparagraph %r in this book (a narration's from:)" % first)
    if last:
        for k in range(len(allsubs) - 1, -1, -1):
            if allsubs[k].num == last:
                j = k
                break
        else:
            sys.exit("no subparagraph %r in this book (a narration's to:)" % last)
    if j < i:
        sys.exit("that narration ends (%s) before it begins (%s)" % (last, first))
    return allsubs[i:j + 1]

FFMPEG = "/opt/homebrew/bin/ffmpeg"
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"

# ---------------------------------------------------------------- normalising
ZWNJ = "‌"
# The letter variants an ASR (or a transcript typed on another keyboard) is
# entitled to get wrong in the Arabic script: applied to every Arabic-script
# language (Persian, Arabic), never to the others.
_FOLD = {
    "ي": "ی", "ى": "ی",           # Arabic yeh / alef maqsura -> Persian ye
    "ك": "ک",                                 # Arabic kaf -> Persian ke
    "ة": "ه", "ۀ": "ه",           # teh marbuta, heh+hamza -> he
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
    "ؤ": "و", "ئ": "ی",
}


def _keep(c):
    """Keep letters, marks and digits; drop punctuation, symbols, spaces
    and format characters, whichever script they come from."""
    return unicodedata.category(c)[0] in "LMN"


def canon(word, lang=None):
    """Fold every difference an ASR is entitled to get wrong, in the book's
    language: the marks the bare pass drops, the ZWNJ, the Arabic-script
    letter variants (Arabic-script languages only), the digits of any
    language, case (Latin), and every punctuation mark.  For a script
    language only characters of its script survive, so a Latin aside in a
    transcript (a caption's "music") is not a token."""
    L = lang or LANG
    w = L.strip(word)
    w = w.replace(ZWNJ, "")
    if L.script == "arabic":
        w = "".join(_FOLD.get(c, c) for c in w)
    w = languages.any_to_latin_digits(w)
    if L.re_chars is not None:
        w = "".join(c for c in w if _keep(c) and (L.re_chars.match(c) or c.isdigit()))
    else:
        # languages.fold, not .lower(): Turkish's dotted and dotless i are
        # exactly the difference a narrator's transcript is entitled to get
        # wrong, and a plain .lower() would leave "Işık" and "ışık" as two
        # different tokens (and turn every İ into i + a combining dot,
        # which matches nothing at all).
        w = languages.fold("".join(c for c in w if _keep(c)))
    return w


def tokens(text, lang=None):
    """-> [(canonical, raw)] dropping anything that canonicalises to nothing.

    A token is a whitespace-separated word; for a language without word
    separators every character is its own token -- coarse, but a run of
    three matching characters is still a usable anchor, and it is the only
    way a narration of such a book can be aligned at all."""
    L = lang or LANG
    out = []
    for raw in re.split(r"\s+", text):
        c = canon(raw, L)
        if not c:
            continue
        if L.spaced:
            out.append((c, raw))
        else:
            out.extend((ch, ch) for ch in c)
    return out


# ------------------------------------------------------------- the transcript
TS_RE = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})$")
# YouTube's panel puts a spoken duration under each clock, in the language the
# panel was copied under: "1 minuto e 6 secondi", "6 seconds", "۱ دقیقه و ۳
# ثانیه", "1分6秒".  Every language's units must be listed -- one in the
# book's own script would otherwise pass for speech -- so the words come from
# the registry (duration_units of every language, the same list the video
# pipeline's check_annotations.py reads), plus the English and the Italian
# forms the panel produces under those interface languages.  The digits are
# every language's too.  The joining word is the panel's, optional because
# Japanese and Turkish juxtapose instead ("1分6秒", "1 dakika 6 saniye");
# it is interface language, not a taught one, so it is written here and not
# asked of the registry -- the same list check_annotations.py carries.
_DUR_NUM = r"[%s]+" % languages.digit_class()
_DUR_UNIT = "|".join(
    [r"secondi?", r"second[so]?", r"seconds?", r"minut[oi]", r"minutes?", r"or[ae]", r"hours?"]
    + sorted({re.escape(u) for L in languages.LANGS.values() for u in L.duration_units},
             key=len, reverse=True))
_DUR_JOIN = r",\s*and|und|and|et|,|e|y|و"      # longest first: "und" not "un"
DURATION_RE = re.compile(
    r"^%s\s*(?:%s)(?:\s*(?:%s)?\s*%s\s*(?:%s)){0,2}\s*$"
    % (_DUR_NUM, _DUR_UNIT, _DUR_JOIN, _DUR_NUM, _DUR_UNIT), re.I)
CUE_RE = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})\s*-->\s*"
                    r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})")


def parse_transcript(path):
    """-> [(t_start, t_end, text)] segments, in order, from any of:

      * YouTube's transcript panel, copied whole: a clock line (0:00, or
        1:23:45), optionally the spoken-duration line the panel puts under
        it, then the words spoken up to the next clock;
      * an .srt or .vtt: "00:01:02,000 --> 00:01:05,500" cues;
      * whisper's .json: {"segments": [{"start", "end", "text"}, ...]}.

    Whatever the shape, it is a time index and nothing else.
    """
    text = (open(path, encoding="utf-8-sig").read()
            .replace("\r\n", "\n").replace("\r", "\n"))
    if text.lstrip()[:1] in ("{", "["):
        try:
            return _segments_json(json.loads(text))
        except ValueError:
            pass
    if "-->" in text:
        return _segments_cues(text)
    return _segments_clocks(text)


def _segments_json(doc):
    segs = doc.get("segments", []) if isinstance(doc, dict) else doc
    out = []
    for seg in segs or []:
        try:
            t0, t1 = float(seg["start"]), float(seg["end"])
            tx = str(seg.get("text", "")).strip()
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if tx and t1 > t0:
            out.append((t0, t1, tx))
    return out


def _cue_secs(h, m, s, ms):
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + float("0." + ms)


def _segments_cues(text):
    out, cur, body = [], None, []

    def flush():
        tx = " ".join(body).strip()
        if cur and tx:
            out.append((cur[0], cur[1], tx))
    for ln in text.split("\n"):
        m = CUE_RE.search(ln)
        if m:
            flush()
            g = m.groups()
            cur, body = (_cue_secs(*g[:4]), _cue_secs(*g[4:])), []
            continue
        t = ln.strip()
        if not t or t.isdigit() or t.startswith(("WEBVTT", "NOTE", "STYLE", "Kind:", "Language:")):
            continue                              # cue numbers, the VTT header
        if cur is not None:
            body.append(re.sub(r"<[^>]+>", "", t))   # VTT's inline tags
    flush()
    return out


def _segments_clocks(text):
    lines = text.split("\n")
    marks = []                                   # (line_index, seconds)
    for i, ln in enumerate(lines):
        m = TS_RE.fullmatch(ln.strip())
        if m:
            h, mn, s = m.groups()
            marks.append((i, int(h or 0) * 3600 + int(mn) * 60 + int(s)))
    segs = []
    for k, (li, t_start) in enumerate(marks):
        # the clock labels the text that FOLLOWS it, so a segment runs from its
        # own mark to the next one.  Reading it the other way put every word a
        # segment early -- about eleven seconds.
        t_end = marks[k + 1][1] if k + 1 < len(marks) else t_start + 10.0
        body = lines[li + 1: marks[k + 1][0] if k + 1 < len(marks) else len(lines)]
        body = [b.strip() for b in body if b.strip()]
        if body and DURATION_RE.match(body[0]):
            body = body[1:]                      # the panel's spoken duration
        tx = " ".join(body).strip()
        if tx:
            segs.append((float(t_start), float(t_end), tx))
    return segs


def transcript_tokens(segs):
    """Flatten to tokens, each given a time by character position in its segment."""
    toks, times = [], []
    for t0, t1, text in segs:
        tk = tokens(text)
        if not tk:
            continue
        widths = [len(c) + 1 for c, _ in tk]
        total = float(sum(widths))
        acc = 0.0
        for (c, raw), w in zip(tk, widths):
            frac0 = acc / total
            acc += w
            frac1 = acc / total
            toks.append(c)
            times.append((t0 + (t1 - t0) * frac0, t0 + (t1 - t0) * frac1))
    return toks, times


# ---------------------------------------------------------------- alignment
# Persian's function words: a one- or two-token match on these is coincidence.
# The list is Persian's (the toolbox's first language) and does no harm to
# the others -- none of their tokens is in it -- but a language with its own
# set would want it in the registry; until then the length test does the work.
STOP = set("و در به از که این آن را با تا هم یا نه بر من او ما اگر است بود می".split())


def align(tex_toks, tr_toks):
    """Monotonic token alignment -> {tex_index: tr_index} for confident anchors.

    difflib gives the monotonic backbone from exactly-matching runs of the
    canonical forms (canon() has already absorbed the spelling differences an
    ASR is entitled to make).  rapidfuzz then rescues near-misses inside the
    gaps between those runs, still monotonically.
    """
    import difflib
    sm = difflib.SequenceMatcher(a=tex_toks, b=tr_toks, autojunk=False)
    anchors = {}
    blocks = sm.get_matching_blocks()
    for a, b, n in blocks:
        if n < 3:
            # a one- or two-token "match" on common words is coincidence, and a
            # single bad one drags every interpolated neighbour with it
            continue
        for k in range(n):
            ti, ri = a + k, b + k
            w = tex_toks[ti]
            if len(w) >= 4 or w not in STOP:
                anchors[ti] = ri
    # rescue near-misses in the gaps, keeping the mapping monotonic
    try:
        from rapidfuzz.distance import Levenshtein
    except ImportError:
        return anchors, blocks
    keys = sorted(anchors)
    for lo, hi in zip([None] + keys, keys + [None]):
        ta0 = 0 if lo is None else lo + 1
        ta1 = len(tex_toks) if hi is None else hi
        ra0 = 0 if lo is None else anchors[lo] + 1
        ra1 = len(tr_toks) if hi is None else anchors[hi]
        if ta1 <= ta0 or ra1 <= ra0 or (ta1 - ta0) > 60 or (ra1 - ra0) > 200:
            continue
        r = ra0
        for t in range(ta0, ta1):
            w = tex_toks[t]
            if len(w) < 4 or w in STOP:
                continue
            best, bi = 0.0, None
            for j in range(r, min(ra1, r + 40)):
                s = Levenshtein.normalized_similarity(w, tr_toks[j])
                if s > best:
                    best, bi = s, j
            if bi is not None and best >= 0.82:
                anchors[t] = bi
                r = bi + 1
    return anchors, blocks


def interpolate(tex_toks, anchors, tr_times):
    """Give every .tex token a (start, end), marking how it was obtained."""
    n = len(tex_toks)
    t0 = [None] * n
    t1 = [None] * n
    src = ["interp"] * n
    for i, j in anchors.items():
        t0[i], t1[i] = tr_times[j]
        src[i] = "anchor"
    keys = sorted(anchors)
    if not keys:
        return t0, t1, src
    # extrapolate the ends from the nearest anchor, weighted by characters
    for i in range(keys[0] - 1, -1, -1):
        nxt = i + 1
        w = (len(tex_toks[i]) + 1) * 0.075
        t1[i] = t0[nxt]
        t0[i] = t1[i] - w
    for i in range(keys[-1] + 1, n):
        prv = i - 1
        w = (len(tex_toks[i]) + 1) * 0.075
        t0[i] = t1[prv]
        t1[i] = t0[i] + w
    # fill the gaps between anchors, sharing the span out by character count
    for a, b in zip(keys, keys[1:]):
        if b - a <= 1:
            continue
        span0, span1 = t1[a], t0[b]
        if span1 < span0:
            span1 = span0
        widths = [len(tex_toks[k]) + 1 for k in range(a + 1, b)]
        total = float(sum(widths)) or 1.0
        acc = 0.0
        for k, w in zip(range(a + 1, b), widths):
            f0 = acc / total
            acc += w
            f1 = acc / total
            t0[k] = span0 + (span1 - span0) * f0
            t1[k] = span0 + (span1 - span0) * f1
    return t0, t1, src


# --------------------------------------------------------------- sanity pass
# Persian narration runs at roughly 11-17 characters a second.  Anything far
# outside that band is not a slow reader, it is a misalignment, and it must not
# be allowed to stand just because an anchor said so.
CPS_LO, CPS_HI = 6.0, 30.0


def repair(spans, sizes):
    """spans: [[t0,t1]] per subparagraph in reading order; sizes: characters.

    Enforce, in order: monotonic and non-overlapping; plausible duration.
    Anything implausible is rebuilt by sharing the time between its nearest
    trustworthy neighbours out by character count.  Returns (spans, trusted).
    """
    n = len(spans)
    trusted = [False] * n
    for i, (sp, sz) in enumerate(zip(spans, sizes)):
        if sp[0] is None or sp[1] is None:
            continue
        d = sp[1] - sp[0]
        trusted[i] = d > 0.25 and CPS_LO <= sz / d <= CPS_HI

    # a span may not start before the previous one ended
    last = None
    for i in range(n):
        if not trusted[i]:
            continue
        if last is not None and spans[i][0] < last - 0.05:
            trusted[i] = False
            continue
        last = spans[i][1]

    # rebuild every untrusted run between two trusted anchors
    idx = [i for i in range(n) if trusted[i]]
    if not idx:
        return spans, trusted
    for a, b in zip([None] + idx, idx + [None]):
        lo = 0 if a is None else a + 1
        hi = n if b is None else b
        if hi <= lo:
            continue
        t_start = spans[a][1] if a is not None else max(0.0, spans[idx[0]][0] - sum(sizes[lo:hi]) / 14.0)
        t_end = spans[b][0] if b is not None else spans[idx[-1]][1] + sum(sizes[lo:hi]) / 14.0
        if t_end <= t_start:
            t_end = t_start + sum(sizes[lo:hi]) / 14.0
        tot = float(sum(sizes[lo:hi])) or 1.0
        acc = 0.0
        for i in range(lo, hi):
            f0 = acc / tot
            acc += sizes[i]
            f1 = acc / tot
            spans[i] = [t_start + (t_end - t_start) * f0,
                        t_start + (t_end - t_start) * f1]
    return spans, trusted


# ------------------------------------------------------------ silence snapping
def silences(audio, t_from, t_to, noise="-32dB", dur=0.10):
    """-> sorted [(start, end)] of detected silence in the window."""
    if not os.path.exists(audio):
        return []
    cmd = [FFMPEG, "-v", "info", "-nostdin", "-ss", "%.2f" % max(0, t_from - 5),
           "-t", "%.2f" % (t_to - t_from + 10), "-i", audio,
           "-af", "silencedetect=noise=%s:d=%s" % (noise, dur), "-f", "null", "-"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    except Exception:
        return []
    base = max(0, t_from - 5)
    out, start = [], None
    for line in p.stderr.split("\n"):
        m = re.search(r"silence_start:\s*(-?[\d.]+)", line)
        if m:
            start = float(m.group(1)) + base
        m = re.search(r"silence_end:\s*(-?[\d.]+)", line)
        if m and start is not None:
            out.append((start, float(m.group(1)) + base))
            start = None
    out.sort()
    return out


def snap(t, sils, starts, window=0.45, prefer="end"):
    """Move a boundary to the nearest silence inside ±window, if there is one."""
    if not sils:
        return t, False
    i = bisect_left(starts, t)
    best, bd = t, window
    for j in (i - 1, i, i + 1):
        if 0 <= j < len(sils):
            s, e = sils[j]
            cand = (s + e) / 2.0
            if s <= t <= e:                       # already inside a silence
                cand = e if prefer == "start" else s
            for c in (cand, s, e):
                d = abs(c - t)
                if d < bd:
                    best, bd = c, d
    return best, best != t


# ------------------------------------------------------------- writing it back
AT_RE = re.compile(r"^%\s*@(t|par)\b")


def strip_comments(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    return [ln for ln in lines if not AT_RE.match(ln)]


def write_comments(path, chapter, dry=False):
    """Rebuild the file with a full-line comment above each \\ch and \\begin{frank}."""
    lines = open(path, encoding="utf-8").read().split("\n")
    keep = [i for i, ln in enumerate(lines) if not AT_RE.match(ln)]
    remap = {old: new for new, old in enumerate(keep)}
    lines = [lines[i] for i in keep]
    # The subparagraph is the unit of playback, so it is the only unit that
    # carries a time.  Per-chunk times were never good enough to cut on -- the
    # transcript has one clock every 8-10 s -- and writing them implied a
    # precision that did not exist.
    ins = {}                                       # line index -> [comment, ...]
    for s in chapter.subs:
        if s.t0 is None:
            continue
        bl = remap.get(s.begin_line)
        if bl is not None:
            line = ("%% @par %s %.2f %.2f %.2f %s"
                    % (s.num, s.t0, s.t1, getattr(s, "conf", 1.0),
                       getattr(s, "src", "anchor")))
            # WHICH RECORDING THE TIME IS IN, and only when there is more than
            # the one: a sixth field, after everything the line has always
            # carried, so a reader of the old five parses this line exactly as
            # before and a book with one narration writes the very same bytes.
            nid = str(getattr(s, "nid", "") or "")
            if nid:
                line += " " + nid
            ins.setdefault(bl, []).append(line)
    out = []
    for i, ln in enumerate(lines):
        for cm in ins.get(i, []):
            out.append(cm)
        out.append(ln)
    text = "\n".join(out)
    if not dry:
        open(path, "w", encoding="utf-8").write(text)
    return sum(len(v) for v in ins.values())


# ------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-time chunks that already have one")
    ap.add_argument("--from-sidecar", action="store_true", help="restore comments from timings.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-snap", action="store_true", help="skip ffmpeg silence snapping")
    ap.add_argument("--apply-review", action="store_true",
                    help="fold review-corrections.json into the sidecar and comments")
    ap.add_argument("--book", default=None,
                    help="book directory, slug or <language folder>/<slug> (default: the current one)")
    ap.add_argument("--audio", default=None)
    ap.add_argument("--transcript", default=None)
    ap.add_argument("--narration", default=None,
                    help="the id of the recording to align (book.json: "
                         "narrations); only the text it covers is re-timed")
    ap.add_argument("--spread", action="store_true",
                    help="with no transcript: share the recording out over the "
                         "text it covers, in proportion to how long each "
                         "subparagraph is (a first guess, not an alignment)")
    args = ap.parse_args()
    book = find_book(args.book)
    book.check_placement()
    _bind(book)
    print("book: %s [%s]" % (book.rel_from_books(), LANG.code))

    chapters = T.parse_book(BOOK, LANG)
    chunks = T.all_chunks(chapters)
    print("parsed %d chunks in %d subparagraphs from %d files"
          % (len(chunks), sum(len(c.subs) for c in chapters), len(chapters)))

    sidecar = {}
    if os.path.exists(SIDECAR):
        _sc = json.load(open(SIDECAR, encoding="utf-8"))
        sidecar = _sc.get("subs", _sc.get("chunks", {}))

    if args.apply_review:
        path = os.path.join(HERE, "review-corrections.json")
        if not os.path.exists(path):
            sys.exit("no review-corrections.json - save from review.html first")
        fixes = json.load(open(path, encoding="utf-8"))
        allsubs0 = [x for ch in chapters for pp in ch.paragraphs for x in pp.subs]
        n = 0
        for x in allsubs0:
            k = subkey(x)
            rec, f = sidecar.get(k), fixes.get(k)
            if f:
                x.t0, x.t1, x.conf, x.src = float(f["t0"]), float(f["t1"]), 1.0, "manual"
                n += 1
            elif rec:
                x.t0, x.t1, x.conf, x.src = rec["t0"], rec["t1"], rec["conf"], rec["src"]
        for ch in chapters:
            write_comments(ch.path, ch, args.dry_run)
        merged = dict(sidecar)
        for x in allsubs0:
            if x.t0 is not None:
                merged[subkey(x)] = {"t0": round(x.t0, 3), "t1": round(x.t1, 3),
                                     "conf": round(x.conf, 3), "src": x.src,
                                     "label": x.num}
        if not args.dry_run:
            # What the sidecar already says about the recordings is kept: this
            # used to write a hardcoded ../audiobook/audio.webm over it, which
            # threw away the real path -- and would now throw away the table
            # saying which recording each time belongs to.
            doc = {}
            try:
                doc = json.load(open(SIDECAR, encoding="utf-8"))
            except (ValueError, OSError):
                doc = {}
            if not isinstance(doc, dict):
                doc = {}
            doc.update({"generated_by": "timestamp.py --apply-review",
                        "subs": merged})
            json.dump(doc, open(SIDECAR, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
        print("applied %d hand corrections" % n)
        return

    allsubs0 = [x for ch in chapters for pp in ch.paragraphs for x in pp.subs]

    if args.from_sidecar:
        n = 0
        for x in allsubs0:
            rec = sidecar.get(subkey(x))
            if rec:
                x.t0, x.t1, x.conf, x.src = rec["t0"], rec["t1"], rec["conf"], rec["src"]
                # the recording the time was measured in travels with it, so
                # the comments the reader is built from say so too
                x.nid = rec.get("n") or ""
                n += 1
        for ch in chapters:
            write_comments(ch.path, ch, args.dry_run)
        print("restored %d subparagraph timings from the sidecar" % n)
        return

    # WHICH RECORDING THIS RUN IS FOR.  A book with one narration -- or with
    # only the old scalars, which is every book written before this -- aligns
    # exactly as it always did.  With several, the run is named (--narration
    # n2) and it re-times only the stretch of text that one covers; every
    # other stretch comes out with the times it went in with.
    narrs = book.narrations
    want = None
    if args.narration:
        want = book.narration(args.narration)
        if want is None:
            sys.exit("%s has no narration called %r (book.json: narrations)"
                     % (book.slug, args.narration))
    elif len(narrs) > 1:
        sys.exit("%s has %d narrations: say which one to align, --narration %s"
                 % (book.slug, len(narrs), "|".join(n["id"] for n in narrs)))
    elif narrs:
        want = narrs[0]

    audio = args.audio or (want or {}).get("audio") or book.audio
    trpath = args.transcript or (want or {}).get("transcript") or book.transcript

    if args.spread:
        # A RECORDING WITH NO TRANSCRIPT STILL KNOWS TWO THINGS: which stretch
        # of the text it is of, and how long it runs.  That is enough to give
        # every subparagraph in the stretch a slice of the recording in
        # proportion to its length -- somewhere to start, so the file can be
        # played and nudged instead of waiting for a transcript that may never
        # be written.  It is a guess and says so: `spread`, at a low
        # confidence, which a real alignment later overwrites without asking.
        if not (audio and os.path.exists(audio)):
            sys.exit("%s: that recording is not on the shelf" % book.slug)
        seconds = audio_seconds(audio)
        if not seconds:
            sys.exit("could not tell how long %s is -- install ffmpeg (ffprobe "
                     "comes with it) and try again" % os.path.basename(audio))
        nid = (want or {}).get("id", "") if len(narrs) > 1 else ""
        region = region_subs(allsubs0, (want or {}).get("from", ""),
                             (want or {}).get("to", ""))
        # every other stretch keeps what it has: the comments are rebuilt for
        # the whole book, so the rest must be seeded from the sidecar first
        for x in allsubs0:
            rec = sidecar.get(subkey(x))
            if rec:
                x.t0, x.t1 = rec["t0"], rec["t1"]
                x.conf, x.src = rec.get("conf", 1.0), rec.get("src", "anchor")
                x.nid = rec.get("n") or ""
        # ...and inside the stretch, only what has no time yet, unless the run
        # is told to start over: a guess must never push out a time somebody
        # stamped by hand or an alignment worked out.
        # THE WHOLE STRETCH, OR NONE OF IT.  The slices are shares of one
        # recording, so laying out half a stretch would give that half the
        # whole file's length again and run it over the rest.  What is laid
        # out is therefore always the entire stretch -- which means a time
        # somebody worked for, stamped by hand or found by an alignment,
        # would go with it.  A stretch holding any of those is refused unless
        # the run says plainly that it means to.
        real = [x for x in region if x.t0 is not None and x.src != "spread"]
        if real and not args.force:
            said = real[0].num if len(real) == 1 else "%s to %s" % (real[0].num,
                                                                    real[-1].num)
            sys.exit("%s covers %d subparagraph%s already timed for real (%s): "
                     "--force to lay a guess over them"
                     % (nid or "that recording", len(real),
                        "" if len(real) == 1 else "s", said))
        for x, (t0, t1) in zip(region, spread(region, seconds)):
            x.t0, x.t1, x.conf, x.src, x.nid = t0, t1, 0.3, "spread", nid
        written = 0
        for ch in chapters:
            written += write_comments(ch.path, ch, args.dry_run)
        subs_out = dict(sidecar)
        for x in allsubs0:
            if x.t0 is None:
                continue
            rec = {"t0": round(x.t0, 3), "t1": round(x.t1, 3),
                   "conf": round(x.conf, 3), "src": x.src, "label": x.num}
            if getattr(x, "nid", ""):
                rec["n"] = x.nid
            subs_out[subkey(x)] = rec
        out = {"audio": os.path.relpath(audio, HERE), "book": BOOKOBJ.slug,
               "generated_by": "timestamp.py --spread", "subs": subs_out}
        if len(narrs) > 1:
            out["narrations"] = [{"id": n["id"], "audio": n["audio_rel"],
                                  "transcript": n["transcript_rel"],
                                  "from": n["from"], "to": n["to"]} for n in narrs]
        if not args.dry_run:
            json.dump(out, open(SIDECAR, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
        print("spread %.1f s of %s over the %d subparagraphs it covers "
              "(%s-%s), %d comments written"
              % (seconds, os.path.basename(audio), len(region),
                 region[0].num, region[-1].num, written))
        return

    if not (audio and trpath and os.path.exists(trpath)):
        sys.exit("%s has no narration to align against "
                 "(book.json: audio / transcript)." % book.slug)

    # The id the times of this run are attributed to, and the stretch of text
    # they may touch.  The id stays empty for a book with one recording, so
    # its `% @par` lines keep the five fields they have always had.
    nid = (want or {}).get("id", "") if len(narrs) > 1 else ""
    region = region_subs(allsubs0, (want or {}).get("from", ""),
                         (want or {}).get("to", ""))
    if len(region) != len(allsubs0):
        # EVERY OTHER STRETCH MUST SURVIVE THIS RUN.  write_comments rebuilds a
        # chapter file whole and writes nothing above a subparagraph whose t0
        # is None, so without seeding them from the sidecar first, the first
        # regional align would quietly delete every other region's times.
        for x in allsubs0:
            rec = sidecar.get(subkey(x))
            if rec:
                x.t0, x.t1 = rec["t0"], rec["t1"]
                x.conf, x.src = rec.get("conf", 1.0), rec.get("src", "anchor")
                x.nid = rec.get("n") or ""
        mine = {id(c) for x in region for c in x.chunks}
        chunks = [c for c in chunks if id(c) in mine]
        print("narration %s: %d of %d subparagraphs (%s-%s)"
              % (nid or "the one", len(region), len(allsubs0),
                 region[0].num, region[-1].num))
    segs = parse_transcript(trpath)
    tr_toks, tr_times = transcript_tokens(segs)
    print("transcript: %d segments, %d tokens, %.1f s span"
          % (len(segs), len(tr_toks), segs[-1][1] if segs else 0))

    # the .tex token stream, each token remembering its chunk
    tex_toks, owner = [], []
    for c in chunks:
        for t, _raw in tokens(c.fa):
            tex_toks.append(t)
            owner.append(c)
    print("reference text: %d tokens" % len(tex_toks))

    anchors, blocks = align(tex_toks, tr_toks)
    print("anchors: %d of %d tokens (%.1f%%)"
          % (len(anchors), len(tex_toks), 100.0 * len(anchors) / max(1, len(tex_toks))))
    t0s, t1s, srcs = interpolate(tex_toks, anchors, tr_times)

    # ---- per-token times, then one span per subparagraph
    per = {}
    for i, c in enumerate(owner):
        per.setdefault(id(c), []).append(i)
    for c in chunks:
        idxs = per.get(id(c))
        if not idxs:
            continue
        c.t0 = min(t0s[i] for i in idxs)
        c.t1 = max(t1s[i] for i in idxs)
        c.src = "anchor" if any(srcs[i] == "anchor" for i in idxs) else "interp"

    # Only what this recording covers.  Every pass below -- repair's
    # monotonicity, the silence scan, the padding chain -- is about ONE
    # timeline, and a region's first subparagraph starts near zero in its own
    # file; run over the whole book they would rebuild every later region as
    # "out of order" against times that were never on the same clock.
    allsubs = region
    for x in allsubs:
        x.nid = nid                      # "" for a book with one recording
    spans, sizes = [], []
    for x in allsubs:
        got = [c for c in x.chunks if c.t0 is not None]
        spans.append([min(c.t0 for c in got), max(c.t1 for c in got)] if got else [None, None])
        sizes.append(max(1, len(LANG.strip(x.fa).replace(" ", ""))))

    before = sum(1 for sp, sz in zip(spans, sizes)
                 if sp[0] is None or not (sp[1] - sp[0] > 0.25 and
                                          CPS_LO <= sz / (sp[1] - sp[0]) <= CPS_HI))
    spans, trusted = repair(spans, sizes)
    print("subparagraphs: %d, %d rebuilt as implausible or out of order"
          % (len(allsubs), len(allsubs) - sum(trusted)))

    for x, sp, tr in zip(allsubs, spans, trusted):
        x.t0, x.t1 = sp
        x.src = "anchor" if tr else "interp"
        x.conf = 1.0 if tr else 0.45

    # ---- silence snapping, on subparagraph boundaries only
    if not args.no_snap and os.path.exists(audio):
        lo = min(x.t0 for x in allsubs if x.t0 is not None)
        hi = max(x.t1 for x in allsubs if x.t1 is not None)
        print("silence scan over %.0f-%.0f s ..." % (lo, hi))
        sils = silences(audio, lo, hi)
        starts = [z for z, _ in sils]
        moved = 0
        for x in allsubs:
            if x.t0 is None:
                continue
            a2, m1 = snap(x.t0, sils, starts, prefer="start")
            b2, m2 = snap(x.t1, sils, starts, prefer="end")
            if b2 - a2 >= 0.4:
                x.t0, x.t1 = a2, b2
                moved += int(m1 or m2)
        print("  %d silences, %d boundaries snapped" % (len(sils), moved))

    # ---- padding, then a final monotonic pass
    prev = None
    for x in allsubs:
        if x.t0 is None:
            continue
        x.t0 = max(0.0, x.t0 - 0.15)
        x.t1 = x.t1 + 0.25
        if prev is not None and x.t0 < prev - 0.30:
            x.t0 = prev - 0.30
        if x.t1 < x.t0 + 0.4:
            x.t1 = x.t0 + 0.4
        prev = x.t1

    if not args.force and sidecar:
        kept = 0
        for x in allsubs:
            rec = sidecar.get(subkey(x))
            if rec and rec.get("src") == "manual":
                x.t0, x.t1, x.conf, x.src = rec["t0"], rec["t1"], 1.0, "manual"
                kept += 1
        if kept:
            print("kept %d hand-corrected subparagraphs" % kept)

    # ---- write the comments and the sidecar
    written = 0
    for ch in chapters:
        written += write_comments(ch.path, ch, args.dry_run)
    # MERGED, NEVER REPLACED: the records of every stretch this run did not
    # touch stay exactly as they were.  `n` says which recording a time is
    # seconds into, and is written only for a book that has more than one --
    # so an existing sidecar keeps its shape to the byte.
    subs_out = dict(sidecar)
    for x in allsubs:
        if x.t0 is None:
            continue
        rec = {"t0": round(x.t0, 3), "t1": round(x.t1, 3),
               "conf": round(x.conf, 3), "src": x.src, "label": x.num}
        if nid:
            rec["n"] = nid
        subs_out[subkey(x)] = rec
    out = {"audio": os.path.relpath(audio, HERE),
           "book": BOOKOBJ.slug,
           "generated_by": "timestamp.py",
           "subs": subs_out}
    if len(narrs) > 1:
        # what each recording is and what it covers, beside the times, so the
        # sidecar says on its own how to read them
        out["narrations"] = [{"id": n["id"], "audio": n["audio_rel"],
                              "transcript": n["transcript_rel"],
                              "from": n["from"], "to": n["to"]} for n in narrs]
    if not args.dry_run:
        json.dump(out, open(SIDECAR, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    # ---- review sidecar: the doubtful chunks, with the transcript words that
    # fell in their window.  The transcript is evidence about *timing*; it is
    # labelled as such and is never presented as text to read.
    review = []
    for x in allsubs:
        if x.t0 is None or x.conf >= 0.9:
            continue
        words = [tr_toks[k] for k in range(len(tr_toks))
                 if tr_times[k][1] > x.t0 and tr_times[k][0] < x.t1]
        item = {"key": subkey(x), "label": x.num, "fa": x.fa,
                "tr": "", "en": "",
                "t0": round(x.t0, 2), "t1": round(x.t1, 2),
                "conf": round(x.conf, 2), "src": x.src,
                "asr": " ".join(words[:40])}
        if nid:
            item["n"] = nid
        review.append(item)
    # the doubts of the stretches this run did not touch are still doubts
    if nid:
        mine = {r["key"] for r in review}
        old = []
        try:
            old = (json.load(open(os.path.join(HERE, "review.json"),
                                  encoding="utf-8")).get("items") or [])
        except (ValueError, OSError):
            old = []
        review = [r for r in old
                  if r.get("n") != nid and r.get("key") not in mine] + review
    if not args.dry_run:
        json.dump({"audio": os.path.relpath(audio, HERE), "items": review},
                  open(os.path.join(HERE, "review.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print("review.json: %d subparagraphs to check by ear" % len(review))

    # ---- report
    timed = [x for x in allsubs if x.t0 is not None]
    print("\n--- report ---")
    print("subparagraphs timed : %d / %d" % (len(timed), len(allsubs)))
    print("comment lines written: %d" % written)
    for lo, hi in ((0.9, 1.01), (0.6, 0.9), (0.3, 0.6), (-0.01, 0.3)):
        n = sum(1 for c in timed if lo <= c.conf < hi)
        print("  confidence %.1f-%.1f : %4d  (%.1f%%)"
              % (max(lo, 0), min(hi, 1), n, 100.0 * n / max(1, len(timed))))
    print("implausible or out of order before repair: %d" % before)
    if timed:
        print("span: %.1f s -> %.1f s" % (min(c.t0 for c in timed), max(c.t1 for c in timed)))

    rate = sorted((len(LANG.strip(x.fa).replace(" ", "")) / max(0.01, x.t1 - x.t0), x.num)
                  for x in timed)
    print("\nimplied reading rate, slowest and fastest (chars/second):")
    for r, num in rate[:4] + rate[-4:]:
        print("   %-8s %5.1f cps" % (num, r))


if __name__ == "__main__":
    main()
