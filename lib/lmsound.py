# SPDX-License-Identifier: GPL-3.0-or-later
"""Conservative spelling-to-sound approximation; never acoustic evidence."""
import unicodedata
from functools import lru_cache


def key(text):
    text = unicodedata.normalize('NFKD', text.casefold())
    text = ''.join(c for c in text if unicodedata.category(c)[0] in 'LN')
    # Common Persian/Arabic spellings of the same sound. Latin folding is
    # deliberately modest; this is not a language-independent pronunciation model.
    text = text.translate(str.maketrans('يىكأإآؤئثصذضظطح', 'ییکاااوئسسزززته'))
    for a, b in (('ph', 'f'), ('ck', 'k'), ('qu', 'k'), ('sh', 'ش'), ('ch', 'چ')):
        text = text.replace(a, b)
    return text


def similarity(a, b):
    a, b = key(a), key(b)
    if not a or not b:
        return 0.0
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        nxt = [i]
        for j, y in enumerate(b, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (x != y)))
        row = nxt
    return 1 - row[-1] / max(len(a), len(b))


@lru_cache(maxsize=1024)
def readings(text, language):
    """Use Parseh's installed dictionary, including its inflected-form sound."""
    try:
        import lookup
        raw = lookup.look_up(language, text)
        if not raw:
            return ()
        hits = [h for row in raw['words'] for h in row.get('hits', [])]
        return tuple(dict.fromkeys(h.get('reading') or h.get('translit') or h.get('head_sound') for h in hits
                                   if h.get('reading') or h.get('translit') or h.get('head_sound')))[:8]
    except Exception:
        return ()


def sound_similarity(a, b, language=''):
    aa, bb = readings(a, language), readings(b, language)
    if aa and bb:
        return max(similarity(x, y) for x in aa for y in bb)
    # Written Han characters do not determine pronunciation. Missing readings
    # leave the candidate available instead of inventing a dissimilar sound.
    if any('CJK' in unicodedata.name(c, '') for c in a + b):
        return None
    # Katakana and hiragana encode the same Japanese syllables.
    fold = lambda text: ''.join(chr(ord(c) - 0x60) if '\u30a1' <= c <= '\u30f6' else c for c in text)
    return similarity(fold(a), fold(b))
