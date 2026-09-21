#!/usr/bin/env python3
"""Edit a book's own identity fields -- title, author, year, the blurb the
library card shows -- from inside the reader, without touching a chunk.

book.json holds every field a reader edits here.  Four of them are ALSO
baked into main.tex at the moment the book is created (lib/draft.py's
MAIN_TEX, lib/newbook.py's): \\BookTitle, \\BookAuthor, \\BookTitleLatin,
\\BookAuthorLatin, each a \\newcommand{...}{...} line that becomes the PDF's
title page.  Nothing re-derives those from book.json at build time -- the
book is built by running LaTeX on main.tex, and book.json is never read
during that -- so an edit that touched only book.json would leave the next
PDF built from main.tex naming the OLD title, silently, with no error
anywhere to say so.  edit_meta rewrites both, in one call, or neither: the
whole edit is prepared as text before anything is written, so a value
main.tex cannot hold refuses the edit before book.json changes either, and
the two never drift apart because of a metadata edit.

    edit_meta(book_dir, fields)   # fields: {name: new value, ...} of EDITABLE

Raises Refused (texwrite's own, imported and not restated -- its docstring
says why a field is refused rather than escaped) for a value that cannot be
written, or ValueError for a field name edit_meta does not know or a book
whose main.tex does not carry the line an edit is about to rewrite.
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import books                                                     # noqa: E402
import texwrite                                                  # noqa: E402
from texwrite import Refused                                     # noqa: E402

# every field the sheet may change, in the order the form shows them
EDITABLE = ("title", "title_latin", "title_en", "author", "author_latin",
            "year", "blurb", "reorders")

# the ones of those that are a switch, not text: "reorders", a text read out
# of its written order (kanbun), whose words' readings are not held to the
# chunk's reading (lib/wordline.py's check).  true, or not written at all --
# books.Book.reorders reads a missing key as false, and so does every checker
SWITCHES = ("reorders",)

# the four of those also written into main.tex at creation time, and the
# macro each becomes -- lib/draft.py's MAIN_TEX and lib/newbook.py's agree
# on the names, though not, see _sync_main_tex, on the case of the Latin one
MAINTEX_MACRO = {"title": "BookTitle", "title_latin": "BookTitleLatin",
                 "author": "BookAuthor", "author_latin": "BookAuthorLatin"}


def _write(path, text):
    """Written beside the file and renamed over it, so book.json or main.tex
    is never left half-written by a crash or a full disk.  texwrite._write
    and languages.write_css make the same choice; a leading underscore marks
    theirs private to their own module, so this is a third copy of five
    lines rather than a new coupling between three unrelated ones."""
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, path)


def _check_field(field, value):
    """The value as it will be written: stripped, and refused outright if it
    cannot be.  Every field refuses what texwrite.NOT_TEXT refuses -- the
    control characters and the unpaired surrogates, for the reasons
    texwrite's own docstring gives, since book.json is read by the same
    tools a chunk's fields are.  The four MAINTEX_MACRO fields refuse LaTeX
    specials too: they are written into main.tex as literal text inside a
    \\newcommand{...}{...} group, unescaped, exactly as texwrite refuses
    them in fa/kana/tr/en rather than escape them (its docstring: no escape
    satisfies the PDF, check_batch.py and the reader all at once).  A
    SWITCHES field is true or false and nothing else, "yes" and 1 included."""
    if field in SWITCHES:
        if not isinstance(value, bool):
            raise Refused("%s must be true or false, not %s"
                          % (field, type(value).__name__))
        return value
    if not isinstance(value, str):
        raise Refused("%s must be a string, not %s" % (field, type(value).__name__))
    m = texwrite.NOT_TEXT.search(value)
    if m:
        k, cp = m.start(), ord(m.group())
        why = ("an unpaired surrogate, which UTF-8 cannot encode"
               if 0xd800 <= cp <= 0xdfff else "a control character")
        raise Refused("%s carries U+%04X at character %d, which is not text -- %s"
                      % (field, cp, k, why))
    value = value.strip()
    if field in MAINTEX_MACRO:
        bad = sorted({c for c in value if c in texwrite.TEX_SPECIALS})
        if bad:
            it = "them" if len(bad) > 1 else "it"
            raise Refused("%s may not contain %s -- it is written into main.tex's "
                          "\\newcommand{\\%s}{...} as literal text, and LaTeX would "
                          "read %s as an instruction"
                          % (field, " ".join(repr(c) for c in bad),
                             MAINTEX_MACRO[field], it))
    return value


def _sync_main_tex(text, updates):
    """main.tex with the \\newcommand lines `updates` names rewritten to
    their new values.  Each value has already passed _check_field, so it
    holds none of \\ { } $ % & # _ ^ ~ and the simple [^}]* below cannot
    cross into the next line or swallow a brace that was never there.

    NOT upper-cased.  lib/draft.py writes \\BookTitleLatin exactly as typed,
    and its own comment says why: Python's str.upper() does not know a
    Turkish dotted i from an English one, and the registry keeps no case
    table for it (languages.py has lower and fold, deliberately no upper).
    lib/newbook.py's page instead uppercases title_latin in the BROWSER,
    with toLocaleUpperCase, before main.tex is ever written -- a choice this
    function cannot tell apart from a title_latin that was simply typed in
    capitals, so an edit here always writes the field as given.  A book
    built through newbook.py's page and then edited here loses the
    capitalisation its title page opened with; the alternative, guessing at
    a client-side transform from inside the server, would misspell every
    Turkish title it tried to fix.
    """
    for field, value in updates.items():
        macro = MAINTEX_MACRO[field]
        pat = re.compile(r"(\\newcommand\{\\%s\}\{)[^}]*(\})" % re.escape(macro))
        new_text, n = pat.subn(lambda m: m.group(1) + value + m.group(2), text, count=1)
        if n == 0:
            raise ValueError("main.tex has no \\newcommand{\\%s}{...} line to "
                             "rewrite -- the edit was not made, to book.json "
                             "either, so the PDF and the library page cannot go "
                             "out of step over this" % macro)
        text = new_text
    return text


def edit_meta(book_dir, fields):
    """Rewrite book.json's metadata fields, and main.tex's \\newcommand lines
    for the ones it also carries.  `fields` may name any subset of EDITABLE;
    a name it does not carry raises ValueError.  Returns the book's full,
    updated meta dict."""
    if not isinstance(fields, dict) or not fields:
        raise ValueError("nothing to change")
    unknown = sorted(set(fields) - set(EDITABLE))
    if unknown:
        raise ValueError("not an editable field: %s (editable: %s)"
                         % (", ".join(unknown), ", ".join(EDITABLE)))
    book = books.Book(book_dir)
    checked = {k: _check_field(k, v) for k, v in fields.items()}
    if "title" in checked and not checked["title"]:
        raise Refused("title may not be blank")

    main_updates = {k: v for k, v in checked.items() if k in MAINTEX_MACRO}
    main_path = os.path.join(book.dir, "main.tex")
    new_main = None
    if main_updates:
        if not os.path.isfile(main_path):
            raise ValueError("this book has no main.tex to keep in step -- "
                             "the edit was not made")
        with io.open(main_path, encoding="utf-8", newline="") as f:
            main_text = f.read()
        new_main = _sync_main_tex(main_text, main_updates)

    meta = dict(book.meta)
    meta.update(checked)
    for field in SWITCHES:
        if checked.get(field) is False:         # a switch turned off is not written
            meta.pop(field, None)
    _write(os.path.join(book.dir, "book.json"),
           json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    if new_main is not None:
        _write(main_path, new_main)
    return meta
