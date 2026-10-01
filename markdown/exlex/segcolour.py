# SPDX-License-Identifier: GPL-3.0-or-later
"""Semantic partial-foreground-colour runs in Parseh markdown.

The spelling is ``[[plain[coloured]{teal}plain]]{translit:...}``.  This
module deliberately uses a small scanner, rather than a regular expression:
``[[slot]]`` was Parseh's exercise-blank syntax first, and only a complete
run containing at least one valid inner colour piece belongs to this feature.
"""
from dataclasses import dataclass
import re


PALETTE = {
    "crimson": "8E2B34",
    "indigo": "2F3E8F",
    "teal": "13605C",
    "violet": "5C2E7E",
    "amber": "8A5A0B",
}
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_MARK_KEY = re.compile(r"(?:^|\s)(translit|kana|reading):")


def normalise_colour(value):
    """A palette name or #RRGGBB in canonical form; None when invalid."""
    if not value:
        return None
    if value.startswith("#"):
        return "#" + value[1:].upper() if HEX_RE.fullmatch(value) else None
    value = value.lower()
    return value if value in PALETTE else None


def parse_marks(raw):
    """Parse the ordinary whole-run linguistic fields, keeping last wins."""
    raw = (raw or "").strip()
    hits = list(_MARK_KEY.finditer(raw))
    if not hits:
        return {}
    out = {}
    for i, hit in enumerate(hits):
        value = raw[hit.end():hits[i + 1].start() if i + 1 < len(hits) else None].strip()
        key = "kana" if hit.group(1) == "reading" else hit.group(1)
        out[key] = value
    return out


@dataclass(frozen=True)
class Piece:
    text: str
    colour: str | None = None


@dataclass(frozen=True)
class SegmentedColourRun:
    start: int
    end: int
    pieces: tuple[Piece, ...]
    marks: tuple[tuple[str, str], ...] = ()
    positions: tuple[int, ...] = ()

    @property
    def plain_text(self):
        return "".join(piece.text for piece in self.pieces)

    def mark(self, key):
        return dict(self.marks).get("kana" if key == "reading" else key, "")


def _annotation(text, at):
    """Return (end, marks) for an optional valid linguistic annotation."""
    if at >= len(text) or text[at] != "{":
        return at, {}
    close = text.find("}", at + 1)
    if close < 0 or "\n" in text[at:close]:
        return at, {}
    raw = text[at + 1:close]
    marks = parse_marks(raw)
    # Outer wrappers are linguistic only.  Unknown/bare fields remain
    # literal after the run rather than being silently swallowed.
    first = _MARK_KEY.search(raw)
    if (not marks or not first or raw[:first.start()].strip()
            or any(c in raw for c in "{}[]")):
        return at, {}
    return close + 1, marks


def parse_at(text, start):
    """Parse one segmented run beginning at *start*, or return None."""
    if not text.startswith("[[", start):
        return None
    line_end = text.find("\n", start + 2)
    limit = len(text) if line_end < 0 else line_end
    close = text.find("]]", start + 2, limit)
    if close < 0:
        return None
    interior = text[start + 2:close]
    if "[[" in interior:
        return None                 # segmented runs cannot nest
    pieces, plain, plain_pos, positions, found, i = [], [], [], [], False, 0

    def flush():
        if plain:
            pieces.append(Piece("".join(plain)))
            plain.clear()
            positions.extend(plain_pos)
            plain_pos.clear()

    while i < len(interior):
        if interior[i] != "[":
            plain.append(interior[i])
            plain_pos.append(start + 2 + i)
            i += 1
            continue
        shut = interior.find("]", i + 1)
        if shut < 0 or shut == i + 1 or shut + 1 >= len(interior) or interior[shut + 1] != "{":
            plain.append(interior[i])
            plain_pos.append(start + 2 + i)
            i += 1
            continue
        brace = interior.find("}", shut + 2)
        if brace < 0:
            plain.append(interior[i])
            plain_pos.append(start + 2 + i)
            i += 1
            continue
        # No recursive brackets or line breaks in a colour piece.
        body = interior[i + 1:shut]
        raw_colour = interior[shut + 2:brace].strip()
        colour = normalise_colour(raw_colour)
        if not colour or "[" in body or "]" in body or "{" in raw_colour:
            plain.append(interior[i])
            plain_pos.append(start + 2 + i)
            i += 1
            continue
        flush()
        pieces.append(Piece(body, colour))
        positions.extend(range(start + 2 + i + 1, start + 2 + shut))
        found = True
        i = brace + 1
    flush()
    if not found:
        return None
    end, marks = _annotation(text, close + 2)
    return SegmentedColourRun(start, end, tuple(pieces), tuple(marks.items()),
                              tuple(positions))


def find_runs(text):
    """Yield complete, non-overlapping segmented runs in source order."""
    i = 0
    while True:
        i = text.find("[[", i)
        if i < 0:
            return
        node = parse_at(text, i)
        if node is None:
            i += 2
        else:
            yield node
            i = node.end


def merge_pieces(pieces):
    """Drop empties and merge adjacent pieces with the same colour."""
    out = []
    for piece in pieces:
        if not piece.text:
            continue
        colour = normalise_colour(piece.colour) if piece.colour else None
        if out and out[-1].colour == colour:
            out[-1] = Piece(out[-1].text + piece.text, colour)
        else:
            out.append(Piece(piece.text, colour))
    return tuple(out)


def serialize(pieces, marks=None, latin=False):
    """Canonical spelling for coloured pieces and whole-run marks."""
    pieces = merge_pieces(pieces)
    plain = "".join(p.text for p in pieces)
    marks = dict(marks or {})
    fields = []
    if marks.get("kana"):
        fields.append("kana:" + marks["kana"])
    if marks.get("translit"):
        fields.append("translit:" + marks["translit"])
    colours = {p.colour for p in pieces if p.colour}
    all_coloured = bool(pieces) and all(p.colour for p in pieces)
    if not colours:
        if fields or latin:
            return "[%s]{%s}" % (plain, " ".join(fields) if fields else "tl")
        return plain
    if len(colours) == 1 and all_coloured:
        return "[%s]{%s}" % (plain, " ".join([next(iter(colours))] + fields))
    body = "".join(("[%s]{%s}" % (p.text, p.colour)) if p.colour else p.text
                   for p in pieces)
    return "[[%s]]%s" % (body, ("{%s}" % " ".join(fields)) if fields else "")


def recolour_pieces(pieces, start, end, colour):
    """Set colour on the half-open plain-text interval, canonically."""
    colour = normalise_colour(colour) if colour else None
    out, at = [], 0
    for piece in pieces:
        stop = at + len(piece.text)
        left, right = max(start, at), min(end, stop)
        if left > at:
            out.append(Piece(piece.text[:left - at], piece.colour))
        if right > left:
            out.append(Piece(piece.text[left - at:right - at], colour))
        if right < stop:
            out.append(Piece(piece.text[right - at:], piece.colour))
        at = stop
    return merge_pieces(out)


def flatten(text):
    """Source with segmented markup replaced by its exact visible text."""
    out, at = [], 0
    for node in find_runs(text):
        out.extend((text[at:node.start], node.plain_text))
        at = node.end
    out.append(text[at:])
    return "".join(out)
