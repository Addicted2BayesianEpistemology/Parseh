#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""What a transcription becomes on the add page: the panel, on the video's own clock.

    segments = sttpanel.remap(segments, marks)         # recording time -> video time
    panel, notes = sttpanel.segments_to_panel(segments)
    facts = sttpanel.facts(panel, "fa")                # what the parser makes of it

The worker hands over `[{start, end, text}]` in seconds of the RECORDING and
never learns the panel format; the result route of the job calls these two.

THE PANEL, NOT A SUBTITLE FILE.  The add page's Transcript box holds the
panel YouTube shows -- a clock line, then the caption on one line -- which is
what check_annotations.transcript_text writes and parse_transcript_text
reads, and what merge_parts, the prompt and the checker all read back.
Rendering a Whisper result as .srt/.vtt would be wrong: ytpages'
subtitles_to_transcript collapses a cue that begins with the whole cue
before it, so "Ciao" then "Ciao a tutti" would come out as "Ciao" and
"a tutti", and words would be lost without a word said.

THE CLOCK.  A capture is in RECORDING time and captions must be in VIDEO
time.  They differ by the time between the share being granted and the video
playing (the start latency, YouTube saying PLAYING a fraction late) and by
every buffering stall, when the tab goes on recording silence while the
video stands still.  Without a correction every caption after a two-second
stall is two seconds off, and nobody would ever know.  The browser therefore
sends MARKS -- [frame, video seconds], a few a second, the sample index of
the recording beside what the player's own clock said at that instant -- and
`remap` moves each segment by the difference between the two clocks where
that segment lies.  A film has no marks and needs none: the worker decodes it
from its own start, so its times ARE the film's.
"""
import bisect
import math
import os
import sys

LIB = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(os.path.dirname(LIB))
for _p in (LIB, os.path.join(ROOT, "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import check_annotations as CA      # noqa: E402  the panel's own writer and its regexes

SAMPLE_RATE = 16000
MAX_MARKS = 400000              # four a second for a day
MAX_VIDEO_SECONDS = 86400.0
SMOOTH = 7                      # each side: a mark's lag is the median of 15 marks around it
STALL_SLOPE = 0.5               # the recording gains on the video by more than this: it stalled
STALL_LEAST = 0.4               # seconds a stall must last to drop what was heard inside it


def _reads_as_furniture(text):
    """Would the panel's own reader take this line for something that is not
    a caption?  A clock, a chapter marker, a spoken duration, a subtitle cue."""
    import ytpages
    return bool(CA.TIMESTAMP.match(text) or CA.CHAPTER.match(text)
                or CA.DURATION.match(text) or ytpages.CUE.match(text))


def segments_to_panel(segments):
    """[{start, end, text}] (faster-whisper segments, seconds) -> (panel, notes).

    Written by the checker's own writer, so the page, the prompt, merge_parts
    and check_annotations read it as they read a pasted YouTube panel.  Three
    traps of the real parser are avoided:

      * a segment whose whole text READS AS the panel's furniture -- `12:30`
        (taken for a clock), `10 minutes` (a spoken duration), `Chapter 3:
        fruit` (a chapter heading), a subtitle cue -- would be eaten or
        mis-typed, so it is said inside the caption beside it, where none of
        those rules looks, and `notes` says so;
      * the editor refuses two captions that start together (the checker
        allows it), so a start that is not after the last is put one
        thousandth after it;
      * Whisper puts a space before each segment and may give an empty one:
        whitespace is collapsed and the empty ones are none.
    """
    caps, notes, carry, prev = [], [], "", -1.0
    for s in segments or []:
        if not isinstance(s, dict):
            continue
        text = " ".join(str(s.get("text") or "").split())
        if not text:
            continue
        if _reads_as_furniture(text):
            if not caps:
                # nothing before it: it waits for the caption after it, and
                # is said to have been joined only once there is one
                carry = (carry + " " + text).strip()
                continue
            joined = caps[-1]["text"] + " " + text
            if _reads_as_furniture(joined):
                notes.append("%r was left out: the transcript would have read it as "
                             "something else" % text)
            else:
                caps[-1]["text"] = joined
                notes.append("%r was joined to the caption before it" % text)
            continue
        try:
            start = float(s.get("start") or 0.0)
        except (TypeError, ValueError):
            start = 0.0
        if not math.isfinite(start):
            start = 0.0
        start = max(0.0, round(start, 3))
        if start <= prev:
            start = round(prev + 0.001, 3)
        said = (carry + " " + text).strip()
        if carry and _reads_as_furniture(said):
            notes.append("%r was left out: the transcript would have read it as "
                         "something else" % carry)
            said = text
        elif carry:
            notes.append("%r was joined to the caption after it" % carry)
        prev = start
        caps.append({"start": start, "text": said, "chapter": None})
        carry = ""
    if carry:
        notes.append("%r was left out: nothing came after it to be joined to" % carry)
    return CA.transcript_text(caps), notes


def facts(panel, lang):
    """What the add page's own parser makes of a panel -> {captions, want,
    plain, duration}: the numbers /api/prepare gives for the same text, from
    the same functions, so the box and the prompt never disagree about them."""
    import ytpages
    caps = ytpages.parse_transcript_text(ytpages.as_transcript(panel), lang)
    want = [c for c in caps if not c["plain"]]
    return {"captions": len(caps), "want": len(want), "plain": len(caps) - len(want),
            "duration": ytpages.fmt_time(caps[-1]["start"]) if caps else ""}


# ------------------------------------------------------------------ the clock
def _marks(marks, rate):
    """The marks that can be believed, as (recording seconds, video seconds),
    the recording moving forward: [[frame, seconds], ...] from a browser is
    not to be trusted with a type, a sign or an order."""
    out = []
    if not isinstance(marks, (list, tuple)):
        return out
    for m in marks[:MAX_MARKS]:
        if not isinstance(m, (list, tuple)) or len(m) != 2:
            continue
        f, v = m
        if isinstance(f, bool) or isinstance(v, bool):
            continue
        try:
            f, v = float(f), float(v)
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(f) and math.isfinite(v)) or f < 0 or not 0 <= v <= MAX_VIDEO_SECONDS:
            continue
        r = f / rate
        if out and r <= out[-1][0]:
            continue
        out.append((r, v))
    return out


def clean_marks(marks, rate=SAMPLE_RATE):
    """The marks a browser sent, kept as [[frame, video seconds], ...] with
    what cannot be believed left out -- what a job stores, and what remap
    reads again without changing."""
    return [[int(round(r * rate)), v] for r, v in _marks(marks, rate)]


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def _lags(pts):
    """How far the recording is ahead of the video at each mark, with the
    jitter taken out: the median of the marks around it.  A median keeps a
    step where a step is (a stall is one) and flattens a reading that was a
    tenth of a second off, which an average would do neither of."""
    raw = [r - v for r, v in pts]
    n = len(raw)
    return [_median(raw[max(0, i - SMOOTH):i + SMOOTH + 1]) for i in range(n)]


def _stalls(rec, lag):
    """The stretches of the recording in which the video stood still, as
    (from, to) in recording seconds: where the lag climbs about as fast as
    the recording runs, for at least STALL_LEAST seconds together."""
    out, run = [], None
    for i in range(len(rec) - 1):
        span = rec[i + 1] - rec[i]
        if span > 0 and (lag[i + 1] - lag[i]) / span > STALL_SLOPE:
            run = (run[0] if run else rec[i], rec[i + 1])
        elif run:
            out.append(run)
            run = None
    if run:
        out.append(run)
    return [r for r in out if r[1] - r[0] >= STALL_LEAST]


def remap(segments, marks, rate=SAMPLE_RATE):
    """Segments in seconds of the RECORDING -> the same in seconds of the VIDEO.

    Each segment is moved back by the lag of the recording behind the video
    where it lies (the lag between marks is read off the straight line
    between them, so a stall -- no marks, and the lag growing as fast as the
    recording -- leaves the video's own time standing still across it).  A
    segment that lies wholly inside a stall is dropped: what Whisper made of
    the silence of a buffering video was never said.  Starts never go
    backwards.  Without marks the segments come back as they are.
    """
    segs = [dict(s) for s in (segments or []) if isinstance(s, dict)]
    pts = _marks(marks, rate)
    if not pts:
        return segs
    rec = [p[0] for p in pts]
    lag = _lags(pts)
    stalls = _stalls(rec, lag)

    def lag_at(s):
        if s <= rec[0]:
            return lag[0]
        if s >= rec[-1]:
            return lag[-1]
        i = bisect.bisect_right(rec, s) - 1
        span = rec[i + 1] - rec[i]
        return lag[i] + (lag[i + 1] - lag[i]) * ((s - rec[i]) / span if span else 0.0)

    def stalled(a, b):
        return any(x <= a and b <= y for x, y in stalls)

    out, prev = [], 0.0
    for seg in segs:
        try:
            a = float(seg.get("start") or 0.0)
            b = float(seg.get("end") if seg.get("end") is not None else a)
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(a) and math.isfinite(b)):
            continue
        if stalled(a, b):
            continue
        start = max(prev, a - lag_at(a), 0.0)
        end = max(start, b - lag_at(b))
        prev = start
        out.append(dict(seg, start=round(start, 3), end=round(end, 3)))
    return out
