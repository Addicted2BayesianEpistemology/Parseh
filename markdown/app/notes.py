#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The notes that sit beside a book or a video, between two of its lines.

    from notes import library, index, create, DIR
    with library(book_dir):
        for n in index(book_dir):
            ...                       # a mark to draw in the reader

A reading edition is a text and its gloss, and a video is a transcript and
its gloss; neither has anywhere to say the other thing -- that this idiom is
the one from chapter two, that the speaker has just switched register, that
the next four lines are a quotation.  A note is that anywhere.  It goes in
the gap between two lines, it is not shown in the page (the reading is the
point), the gap is marked, and clicking the mark opens it.

WHY THERE IS ALMOST NO CODE HERE.  A note is a studio document.  Not "like"
one: the same store writes it, the same editor edits it, the same renderer
renders it, and the same marks mean the same things in it -- because the
whole of what differs is WHERE IT LIVES, and that is one thread-local in
store.py (`store.use_library`) and one in server.py (`server.use_mount`).
So this file holds the two things that are genuinely new: which directory a
content folder keeps its notes in, and how a note says where it sits.

WHERE THEY LIVE.  `<the book or the video>/markdown/`, which is a library
root of its own -- so a note is at

    books/persian/<slug>/markdown/<language>/<id>/source.md
    youtube/videos/persian/<id>/markdown/<language>/<id>/source.md

with the same `meta.json`, the same `images/`, the same everything.  The
language folder is the studio's own layout and is kept rather than flattened:
one layout, one store, nothing to keep in step later.  They travel in the
download of the book or the video (lib/bundle.py) because they are part of
it, and they are never mixed with the studio's own library, which is about
whatever you are reading rather than about one book.

WHERE A NOTE SAYS IT SITS.  In its own front matter, one line:

    anchor: after sub ۱.۲-6f8f21d7175b
    anchor: before cap 126

`side` is `before` or `after`, `kind` is `sub` (a book's subparagraph) or
`cap` (a video's caption), and the identifier is the thing the content side
already uses to name one of those and keep naming it: a subparagraph's key,
which is its label and a hash of its text (lib/timestamp.py subkey, stable
across a rebuild, a chunk edit and a chunk merged or divided), and a
caption's start in seconds, which is what transcript.txt is keyed by.

In the FRONT MATTER and not in meta.json, because the file is the truth
here as everywhere else in this toolbox: moving a note is editing one line
of it, by hand or in the editor, and nothing has to be told.  An anchor
naming something that is no longer there is not an error and is not dropped
-- `index` reports it as adrift, and the reader shows it at the end rather
than pretending the note does not exist.

WHAT A NOTE SAYS BEFORE IT IS OPENED.  The mark in the gap says only that a
note is there; hovering it shows the first few lines of what the note says
(`excerpt`), so a reader can tell whether to open it without leaving the
line.  Made HERE, as plain text, and not in the page: `index` already reads
every note's markdown for its anchor, so the preview costs no request per
hover and no second copy of the dialect in two readers' JavaScript -- and
plain text is the only thing a page should put on screen from a note it
has not been asked to open.  A note travels in the download of a book or a
video, from somebody else's toolbox; a hover is not consent to render it.

NOTHING HERE IS FOR A MODEL.  No prompt mentions notes and none should: a
note is somebody's own reading, and a machine has nothing to put in one.
"""
import os
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import store                                                 # noqa: E402
# store has put the parser, the generator and the registry on the path; the
# excerpt reads a note by their rules, not by copies of them
import languages                                             # noqa: E402
import mdparser                                              # noqa: E402
import texgen                                                # noqa: E402

# The subdirectory of a book's or a video's own folder.  Named for what is in
# it and not for what it is for: somebody looking at the directory should see
# markdown and know what to open it with.
DIR = "markdown"

SIDES = ("before", "after")
KINDS = ("sub", "cap")

# `anchor: after sub ۱.۲-6f8f21d7175b` -- three words, the third being
# whatever the content side calls one of its lines.  Anything else is a note
# that has an anchor nobody here can read, which is reported and not touched.
_ANCHOR = re.compile(r"^\s*(before|after)\s+(sub|cap)\s+(\S+)\s*$")


def dir_for(content_dir):
    """The notes directory of one book or one video."""
    return Path(content_dir) / DIR


class library(object):
    """The store, pointed at this content's notes for the block.

        with library(book_dir):
            store.list_docs()

    A context manager and not a setting, so a request cannot leave the
    thread pointed at somebody's book.
    """

    def __init__(self, content_dir):
        self.root = dir_for(content_dir)
        self.was = None

    def __enter__(self):
        self.was = store.use_library(self.root)
        return self.root

    def __exit__(self, *exc):
        store.use_library(self.was)
        return False


def parse_anchor(text):
    """`"after sub ۱.۲-abc"` -> {"side", "kind", "at"}, or None."""
    m = _ANCHOR.match(text or "")
    if not m:
        return None
    return {"side": m.group(1), "kind": m.group(2), "at": m.group(3)}


def format_anchor(side, kind, at):
    if side not in SIDES:
        raise ValueError("a note sits %s a line" % " or ".join(SIDES))
    if kind not in KINDS:
        raise ValueError("a note is anchored to %s" % " or ".join(KINDS))
    at = str(at).strip()
    if not at or re.search(r"\s", at):
        raise ValueError("the line a note sits by is named by one word")
    return "%s %s %s" % (side, kind, at)


def _split(markdown):
    """A document's lines, cut into (front matter, body).

    mdparser's own walk over its own block, done in one place for both the
    anchor and the excerpt, so that neither can disagree with the page about
    where the front matter ends.  An unclosed block is front matter to the
    end of the file, which is how mdparser reads it: the body is then empty,
    not the whole file over again with `anchor:` in it.
    """
    # mdparser's own split, not str.splitlines(): that one breaks on a lone
    # \r and on the Unicode line separators, and a file the two disagreed
    # about would have an anchor by one reading and none by the other
    lines = (markdown or "").replace("\r\n", "\n").split("\n")
    i, n = 0, len(lines)
    while i < n and not lines[i].strip():
        i += 1
    if i >= n or lines[i].strip() != "---":
        return [], lines[i:]
    j = i + 1
    while j < n and lines[j].strip() != "---":
        j += 1
    return lines[i + 1:j], lines[j + 1:]


def _front_value(front, key):
    """The value of the first `key:` line among these front-matter lines."""
    for line in front:
        m = re.match(r"^([A-Za-z_]+)\s*:\s*(.*)$", line)
        if m and m.group(1).lower() == key:
            return m.group(2).strip()
    return None


def _front_matter_line(markdown, key):
    """One line out of a document's front matter, by name.

    mdparser has an allowlist of front-matter keys (`FM_KEYS`) and drops the
    rest, which is right: the dialect is documented, and the prompt handed to
    a model lists what it may write.  `anchor` is deliberately NOT one of
    them -- a note is nobody's to generate -- so it is read here instead, by
    the same walk over the same block (`_split`), so that the two can never
    disagree about where the front matter is.
    """
    return _front_value(_split(markdown)[0], key)


def anchor_of(markdown):
    """The anchor a note's own text declares, or None."""
    return parse_anchor(_front_matter_line(markdown, "anchor") or "")


# ---- the preview a reader shows on hover
#
# THE BLOCKS ARE mdparser's AND THE MARKS ARE texgen's, by their own patterns
# wherever one exists (the footnotes, the links, the figure lines, the table
# rule), because the excerpt is what the page would show and the page is
# made by those two.  What is new here is only what plain text needs: which
# of it to leave out, and where to put a line break.

# `> > text` -> (2, "text").  A box is read for its text however deep it
# is; the depth is kept only because going into or out of one ends a
# paragraph, as mdparser's recursive parse of a blockquote does.
_QUOTE = re.compile(r"^[ \t]*((?:>[ \t]?)+)")
_RULE = re.compile(r"-{3,}|\*{3,}|_{3,}")          # mdparser: ignored
_HEADING = re.compile(r"^(#{1,3})\s+(.*)$")         # mdparser's three levels
_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
# `[text]{…}` in every shape the dialect has -- a colour, a transliteration,
# a reading, a `{tl}` block, a `{la …}` block, `✗`'s run -- is its text on
# the page, and the braces are what the hover tools read, not the reader
_MARK = re.compile(r"\[([^\[\]]*)\]\{[^{}]*\}")
# texgen's italic, lookbehind and all
_ITALIC = re.compile(r"(?<![\w*\\])\*([^*\n]+?)\*(?!\*)")
# A footnote call and the space before it go together: the page puts a
# raised number there, so "word ^[a note]." reads "word¹." -- and with the
# note taken out and the space left in, the excerpt said "word ."
_NOTE_CALL = re.compile(r"\s*(?:%s|%s)" % (texgen.FN_INLINE_RE.pattern,
                                           texgen.FN_REF_RE.pattern))
# How many marks deep a link label or a block may nest before the rest is
# left as it is: the renderers read one level (FN_INLINE_RE, LA_RE), and
# every pass takes off one.
_NESTING = 4
# What a cut excerpt may not end on before its ellipsis: a space, a line
# break, a separator of a list (Latin, Arabic-script and CJK), a dash, a
# gloss's `=` or an arrow with nothing after them (the Persian starter cut
# at "— تند =…"), or a joiner with nothing left to join.
_LOOSE_END = " \n,;:·،؛、，；：-–—/=→\u200c\u200d"


def _dequote(line):
    """A line -> (how many boxes deep it is, the line without their `>`)."""
    m = _QUOTE.match(line)
    return (m.group(1).count(">"), line[m.end():]) if m else (0, line)


def _is_anchor_line(s):
    """An `anchor:` line outside the front matter -- a note whose `---` the
    parser did not take for one: where the note sits, never what it says."""
    m = re.match(r"^([A-Za-z_]+)\s*:\s*(.*)$", s)
    return bool(m and m.group(1).lower() == "anchor"
                and parse_anchor(m.group(2)))


def _heading(txt):
    """A level-2 heading as the page prints it.  A lemma's fields are joined
    by " · " (`## تند | tond | mp. tund` -> "تند · tond · mp. tund"); its
    `= *gloss*` goes, being printed nowhere (mdparser: it exists for the
    glossary); a section loses a hand-typed number, which the renderers
    replace with their own."""
    txt = mdparser._split_voce_gloss(txt)[0]
    fields = [f.strip() for f in txt.split("|")]
    if len(fields) > 1:
        return " · ".join(f for f in fields if f)
    return re.sub(r"^\d+[.)]\s+", "", txt)


def _row(line):
    """A table row as one line: its cells, by mdparser's split, joined by
    " · ", without the empty ones (`—` is the dialect's empty cell)."""
    return " · ".join(c for c in mdparser._split_cells(line)
                      if c and c != "—")


def _plain(text, L, docs=None):
    """One block of the dialect, its lines already joined -> the text the
    page shows of it, on one line (a `⏎` is the only line break left).
    `docs` is a prepared index (texgen.prepare_doc_index)."""
    text = _NOTE_CALL.sub("", text)
    docs = docs if docs is not None else texgen.prepare_doc_index({})

    def doc(m):
        # the page's own choice (texgen.resolve_doclink): the label, else
        # the target's current title, else the name it is waiting for.
        # Left out instead, a link to a note deleted since read "see the
        # grammar and ." -- the page names what would bring it back, and
        # so does the preview
        return texgen.resolve_doclink(m.group(2), m.group(1), docs)[0]
    # innermost first, so a mark inside a link's label (`[[bello]{tl}](…)`)
    # or a colour inside a block comes off before what holds it
    for _ in range(_NESTING):
        was = text
        text = texgen.DOCLINK_RE.sub(doc, text)
        text = texgen.LINK_RE.sub(r"\1", text)
        text = _MARK.sub(r"\1", text)
        if text == was:
            break
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    # an italic is never across a run of the target script: there the `*`
    # is the linguist's, a reconstructed form (`*tund`), and the page keeps
    # it -- so does this, by texgen's own test (a Latin target has none)
    text = _ITALIC.sub(lambda m: (m.group(0) if L.has_script(m.group(1))
                                  else m.group(1)), text)
    text = re.sub(r"\s*->\s*", " → ", text)
    # every other line separator a file can hold (\r, U+2028, …) is a space
    # here, so that "\n" in an excerpt means one thing
    text = re.sub(r"\s+", " ", text)
    return re.sub(r"(?: ?⏎ ?)+", "\n", text).strip()


def _cap(text, limit):
    """`text` in at most `limit` characters, the ellipsis included, cut
    between two words."""
    if len(text) <= limit:
        return text
    if limit < 1:
        return ""
    room = limit - 1
    k = max(text.rfind(" ", 0, room + 1), text.rfind("\n", 0, room + 1))
    if k < room * 2 // 3:
        # No space in the last third: a language written without them, or
        # one very long word.  Cutting back to the last space regardless
        # (the first draft of this) turned a 292-character Japanese note,
        # a lemma heading and one paragraph, into "速い · はやい ·…":
        # the only spaces were in the heading.  So the cut is between two
        # characters -- but never between a letter and its marks (a Hindi
        # vowel sign or a Persian kasra on its own is a glyph nobody
        # wrote), nor straight after a virama, which would leave half of a
        # Devanagari conjunct (क्ष as क्…).
        k = room
        while k > 0 and (unicodedata.category(text[k])[0] == "M"
                         or unicodedata.combining(text[k - 1]) == 9):
            k -= 1
    return text[:k].rstrip(_LOOSE_END) + "…"


def excerpt(markdown, limit=280, docs=None):
    """What a note says, as the plain text a reader shows on hover.

    Everything the page does not show as the note's text is left out: the
    front matter (the anchor with it), footnotes (calls, definitions and
    their indented continuation lines), figures and videos, a table's rule
    line, `:::` fences, horizontal rules, and a level-1 heading, which is
    the title (the preview shows that on its own).  The rest is read block
    by block, and a paragraph's lines are joined BEFORE any markup comes
    off: read line by line, the inline note in the feature-test fixture
    ("like this ^[This is a note … with Persian کند" / "inside it.] and
    the sentence carries on") kept its `^[` on one line and its `]` on the
    next, matched on neither, and went into the preview whole.

    One line per block, joined by a single "\\n" -- a paragraph, a heading,
    a list item ("• …"), a table row (cells joined by " · "); a `⏎` is a
    "\\n" as well, and nothing else is.  A reader sets it with
    `white-space: pre-line` (and `unicode-bidi: plaintext`, which gives
    each of those lines its own direction, so a Persian paragraph after an
    English one is right-to-left).  At most `limit` characters, cut
    between two words with "…"; "" for a note that says nothing yet.

    `docs` (store.doc_index()'s uid -> {id, title, created}) is what an
    empty-labelled `[](doc:Name)` link shows, the page showing that
    document's title; `index` passes the notes it has just listed.  A name
    not in it reads as itself, as it does on the page.
    """
    front, body = _split(markdown)
    # the note's own target, as mdparser takes it: unknown or absent is
    # the default language -- it decides only what an italic may cross
    code = (_front_value(front, "target") or "").strip().lower()
    L = languages.LANGS.get(code) or languages.LANGS[languages.DEFAULT]
    out, para = [], []
    size = [0]
    docs = texgen.prepare_doc_index(docs)

    def put(block):
        block = _plain(block, L, docs)
        if block:
            out.append(block)
            size[0] += len(block) + 1

    def flush():
        if para:
            put(" ".join(para))
            del para[:]

    # One pass, in mdparser's order, that stops as soon as there is enough
    # -- `index` runs this for every note on every GET of the marks.  The
    # feature-test fixture a hundred times over (314 KB) previews in 0.7 ms,
    # the fixture itself in 0.3.
    i, n, depth, listing = 0, len(body), 0, False
    while i < n and size[0] <= limit:
        d, raw = _dequote(body[i])
        s = raw.strip()
        if d != depth or not s:
            flush()
            depth, listing = d, False
            if not s:
                i += 1
                continue
        if listing and not _ITEM.match(raw):
            if raw.startswith(("  ", "\t")):
                para.append(s)                  # an item's next line
                i += 1
                continue
            flush()
            listing = False
        # An exercise's answer rows are deliberately part of the Markdown
        # source, but a book/video hover card appears before the learner has
        # opened the note.  Treat the complete container as one opaque item:
        # showing even its prompt can leave a nearby ``[x]`` answer inside the
        # excerpt after it is capped.  The full exercise is rendered only in
        # the opened Studio note.
        if mdparser.EXERCISE_OPEN_RE.match(s):
            flush()
            put("<Exercise>")
            i += 1
            while i < n and body[i].strip() != ":::":
                i += 1
            if i < n:
                i += 1
            continue
        if (_RULE.fullmatch(s) or s.startswith(":::")
                or mdparser._TABLE_SEP.match(s) or _is_anchor_line(s)):
            flush()
            i += 1
            continue
        if mdparser._FOOTNOTE_DEF.match(s):
            flush()
            i += 1
            while i < n:
                d2, r2 = _dequote(body[i])
                if d2 != depth or not r2.strip() \
                        or not r2.startswith(("  ", "\t")):
                    break
                i += 1
            continue
        m = _HEADING.match(s)
        if m:
            flush()
            i += 1
            level = len(m.group(1))
            if level == 2:
                put(_heading(m.group(2).strip()))
            elif level == 3:
                put(m.group(2).strip())
            continue
        if "|" in s and i + 1 < n:
            d2, r2 = _dequote(body[i + 1])
            if d2 == depth and mdparser._TABLE_SEP.match(r2):
                flush()
                put(_row(s))
                i += 2
                while i < n and size[0] <= limit:
                    d2, r2 = _dequote(body[i])
                    if d2 != depth or "|" not in r2 or not r2.strip():
                        break
                    put(_row(r2))
                    i += 1
                continue
        if mdparser.IMAGE_RE.match(s) or mdparser.VIDEO_RE.match(s):
            flush()
            i += 1
            continue
        m = _ITEM.match(raw)
        if m:
            flush()
            listing = True
            mark = "•" if m.group(2) in ("-", "*", "+") else m.group(2)
            para.append(mark + " " + m.group(3).strip())
            i += 1
            continue
        para.append(s)
        i += 1
    flush()
    return _cap("\n".join(out), limit)


def index(content_dir):
    """Every note beside this content, each with where it says it sits.

    [{id, title, subtitle, target, updated, anchor: {side, kind, at} | None,
      excerpt}]
    in the store's own order.  A note whose anchor will not read carries
    None, which is what makes it show up as adrift rather than vanish.
    `excerpt` is its first few lines as plain text (`excerpt`), made from
    the same read as the anchor, so a reader's hover preview needs no
    request of its own and GET <notes>/api/marks carries it to both.

    The caller is inside `library(content_dir)`; this asserts nothing about
    that, because a caller that forgets simply reads the studio's own library
    and gets no notes, which is a wrong answer and not a broken one.
    """
    docs = store.list_docs()
    # the library a `[](doc:Name)` between two of these notes resolves in:
    # the metas in hand already hold every one (store.doc_index would read
    # each meta.json a second time to say the same), prepared once for all
    docs_index = texgen.prepare_doc_index(dict(
        (str(m["uid"]).lower(), {"id": m["id"], "title": m.get("title") or m["id"],
                                 "created": m.get("created") or ""})
        for m in docs if m.get("uid")))
    out = []
    for meta in docs:
        try:
            _m, md = store.get(meta["id"])
        except Exception:
            continue
        # a note whose text trips the preview still gets its mark: the
        # mark is how it is found, and opened, and mended
        try:
            text = excerpt(md, docs=docs_index)
        except Exception:
            text = ""
        out.append({"id": meta["id"], "title": meta.get("title") or "",
                    "subtitle": meta.get("subtitle") or "",
                    "target": meta.get("target") or "",
                    "updated": meta.get("updated") or "",
                    "anchor": anchor_of(md),
                    "excerpt": text})
    return out


def starter(side, kind, at, target, lang="en"):
    """The text a new note begins as: its anchor, and nothing else to delete.

    A title, because the store slugs the directory from it and a library of
    documents called "untitled" is a library nobody can search; the rest is
    the person's.
    """
    where = "the line above" if side == "after" else "the line below"
    return ("---\n"
            "title: A note\n"
            "lang: %s\n"
            "target: %s\n"
            "anchor: %s\n"
            "---\n"
            "\n"
            "Written by hand, about %s. Everything the studio can do goes\n"
            "here; nothing here is ever built to a PDF.\n"
            % (lang, target, format_anchor(side, kind, at), where))


def create(content_dir, side, kind, at, target, lang="en"):
    """A new empty note in this content's own library, at that anchor.

    The caller is inside `library(content_dir)`.  Returns the store's meta.
    Its title is the starter's "A note", or "A note 2", "A note 3"… when the
    notes beside this content have that one already (store.create): a link
    between two notes names its target, so no two may share a name.
    """
    return store.create(starter(side, kind, at, target, lang), tags=["note"])
