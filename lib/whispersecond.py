# SPDX-License-Identifier: GPL-3.0-or-later
"""Second-pass crop/alignment rules. Stdlib only; never changes source text.

Alignment needs unchanged adjacent phrase anchors and consistent audio timing.
Edits spanning several first-pass words are ambiguous and are deliberately kept
out of a single word's candidate list. A failure is evidence, not an ASR failure.
"""
import difflib
import math
from numbers import Real
import unicodedata

CROP_SECONDS = 15.0
PAUSE_RADIUS = 1.5


def number(value):
    """Finite native/NumPy real scalars -> JSON-safe float, without NumPy imports.

    faster-whisper's alignment returns NumPy timestamps and probabilities.
    Testing exact Python types silently discarded those decoded words.
    """
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def surface(text):
    def lexical(c):
        return unicodedata.category(c)[0] in 'LNM'
    a, b = 0, len(text)
    while a < b and not lexical(text[a]):
        a += 1
    while b > a and not lexical(text[b-1]):
        b -= 1
    return text[:a], text[a:b], text[b:]


def key(text):
    return unicodedata.normalize('NFC', surface(text)[1]).casefold()


def crop_bounds(words, target, duration, pauses=()):
    start, end = number(target.get('start')), number(target.get('end'))
    if start is None or end is None or not 0 <= start <= end <= duration:
        raise ValueError('missing-timestamps')
    middle = (start + end) / 2
    left = min(max(0., middle-CROP_SECONDS/2), max(0., duration-CROP_SECONDS))
    right = min(duration, left+CROP_SECONDS)
    left, right = min(left, max(0., start-.2)), max(right, min(duration, end+.2))
    timed = [(number(w.get('start')), number(w.get('end'))) for w in words]
    timed = sorted((a, b) for a, b in timed if a is not None and b is not None and 0 <= a <= b <= duration)
    gaps = [(b+a)/2 for (_, b), (a, _) in zip(timed, timed[1:]) if a-b >= .12]
    def safe(t):
        return not any(a < t < b for a, b in timed)
    choices = [t for t in list(pauses)+gaps if 0 <= t <= duration and safe(t)]
    before = [t for t in choices if abs(t-left) <= PAUSE_RADIUS and t <= start-.1]
    after = [t for t in choices if abs(t-right) <= PAUSE_RADIUS and t >= end+.1]
    if before:
        left = min(before, key=lambda t: (abs(t-left), t))
    if after:
        right = min(after, key=lambda t: (abs(t-right), t))
    # When there is no pause nearby, expand rather than bisect a known word.
    for a, b in timed:
        if a < left < b:
            left = max(0., a-.02)
        if a < right < b:
            right = min(duration, b+.02)
    return left, right


def origins(raw):
    out = []
    for value in raw if isinstance(raw, list) else []:
        if not isinstance(value, dict) or value.get('kind') not in ('whisper-first-pass', 'whisper-second-pass'):
            continue
        item = {'kind': value['kind'], 'hypothesis': 'alternative' if value.get('hypothesis') == 'alternative' else 'original'}
        for k in ('crop_start', 'crop_end', 'score', 'sequence_score'):
            n = number(value.get(k))
            if n is not None:
                item[k] = n
        if item not in out:
            out.append(item)
    return out


def merge(target, additions):
    """No hint limit: preserve every original/alternative and all origins."""
    out, by_text = [], {}
    original = {'text': target['text'], 'score': target.get('score'),
                'origins': [{'kind': 'whisper-first-pass', 'hypothesis': 'original'}]}
    for item in [original] + list(target.get('asr_alternatives') or []) + additions:
        row = dict(item)
        source = origins(row.get('origins'))
        if not source:
            source = [{'kind': 'whisper-first-pass', 'hypothesis': 'alternative'}]
            for k in ('score', 'sequence_score'):
                if number(row.get(k)) is not None:
                    source[0][k] = row[k]
        if row['text'] in by_text:
            saved = by_text[row['text']]
            for origin in source:
                if origin not in saved['origins']:
                    saved['origins'].append(origin)
            # Keep the first evidence's score; later scores live in provenance.
        else:
            row['origins'] = source
            by_text[row['text']] = row
            out.append(row)
    return out


def attributable(original, target_index, decoded, crop_start, crop_end):
    """Return only a uniquely anchored replacement of this one source word."""
    a, b = [key(w['text']) for w in original], [key(w['text']) for w in decoded]
    if not b or not a[target_index]:
        raise ValueError('no-word-result')
    ts, te = original[target_index]['start'], original[target_index]['end']
    operations = difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes()
    for tag, i, j, x, y in operations:
        if not i <= target_index < j:
            continue
        if tag == 'equal':
            x = x+target_index-i
            y = x+1
            # A split word can leave its first part unchanged and insert the
            # rest. Attribute that insertion only if its entire audio interval
            # lies inside this original word, then verify both phrase anchors.
            for kind, p, q, u, v in operations:
                if kind != 'insert' or p != q or p not in (target_index, target_index+1):
                    continue
                begin, finish = number(decoded[u].get('start')), number(decoded[v-1].get('end'))
                if (begin is None or finish is None or finish <= begin or
                        crop_start+begin < ts-.08 or crop_start+finish > te+.08):
                    continue
                if p == target_index and v == x:
                    x = u
                elif p == target_index+1 and u == y:
                    y = v
        elif tag != 'replace' or j-i != 1 or y-x < 1:
            raise ValueError('ambiguous-alignment')
        # At least one adjacent unchanged word must establish the phrase.
        anchors = []
        if target_index > 0 and x > 0 and a[target_index-1] and a[target_index-1] == b[x-1]:
            anchors.append((target_index-1, x-1))
        if target_index+1 < len(a) and y < len(b) and a[target_index+1] and a[target_index+1] == b[y]:
            anchors.append((target_index+1, y))
        if not anchors:
            raise ValueError('ambiguous-alignment')
        for oi, ni in anchors:
            os, ns = number(original[oi].get('start')), number(decoded[ni].get('start'))
            if os is None or ns is None or abs(os-(crop_start+ns)) > 1.5:
                raise ValueError('ambiguous-alignment')
        parts = decoded[x:y]
        start, end = number(parts[0].get('start')), number(parts[-1].get('end'))
        if start is None or end is None or not 0 <= start <= end <= crop_end-crop_start+.05:
            raise ValueError('ambiguous-alignment')
        if crop_start+end < ts-.5 or crop_start+start > te+.5:
            raise ValueError('ambiguous-alignment')
        # Repeated surrounding phrases need both anchors, with unique timing.
        if a.count(a[target_index]) > 1 and len(anchors) < 2:
            raise ValueError('ambiguous-alignment')
        prefix, _, suffix = surface(original[target_index]['text'])
        cores = [surface(w['text'])[1] for w in parts]
        if not all(cores):
            raise ValueError('ambiguous-alignment')
        def joined(values):
            return values[0]+''.join((' ' if w.get('space_before', True) else '')+v for w, v in zip(parts[1:], values[1:]))
        replacements = [(joined(cores), parts[0].get('score') if len(parts) == 1 else None, None)]
        for n, word in enumerate(parts):
            for alt in word.get('asr_alternatives') or []:
                core = surface(alt['text'])[1]
                if core:
                    changed = list(cores)
                    changed[n] = core
                    replacements.append((joined(changed), alt.get('score') if len(parts) == 1 else None, alt))
        out = []
        for text, score, alt in replacements:
            text = prefix+text+suffix
            if not text.strip() or len(text) > 400:
                raise ValueError('ambiguous-alignment')
            origin = {'kind': 'whisper-second-pass', 'hypothesis': 'alternative' if alt is not None else 'original',
                      'crop_start': round(crop_start, 3), 'crop_end': round(crop_end, 3)}
            if number(score) is not None:
                origin['score'] = score
            row = {'text': text, 'score': score, 'origins': [origin]}
            if alt is not None and alt.get('score_kind') == 'sequence_log_score':
                row.update(sequence_score=alt['sequence_score'], score_kind='sequence_log_score')
                origin['sequence_score'] = alt['sequence_score']
            out.append(row)
        return out
    raise ValueError('ambiguous-alignment')


REASONS = {
    'missing-timestamps': 'The first pass did not provide a usable word timestamp.',
    'no-word-result': 'The crop did not return word evidence.',
    'ambiguous-alignment': 'The crop could not be safely matched to this original word.',
    'transcription-failed': 'Whisper could not transcribe this crop.',
    'worker-stopped': 'The second-pass worker stopped before processing this word.',
}
