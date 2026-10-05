#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The text of a file, recovered as paragraphs: ONE recovery for a PDF, an epub and a plain text file.

    sourcetext.recover(path, lang, pages=None, drop=(), info=None) -> [paragraph, ...]

    python3 lib/sourcetext.py <file> --lang fa [--from N] [--to N] [--drop REGEX]
                              [--book DIR --chapter new|last|N]
                              [--out FILE [--append]] [--paras DIR --tag ch1 [--start NN]]

Two callers, so that a text is recovered the same way wherever it comes in: the agent that makes a book
in place (its Step 1, and every part the person adds later: docs/new-book-prompt.md) and the door that
adds text onto a book that is already here (serve.py `__append`, which is given a file and a page range
in place of a pasted text).

WHAT EACH KIND IS TREATED AS.  A PDF goes through lib/extract_pdf.py, which is the recovery the method
was made on (the repairs of a broken Arabic-script text layer, the paragraph structure measured from the
page); `pages` is `[first, last]`, counted from 0, and is a PDF's alone.  An epub is its spine, in
reading order, one block of text a paragraph: its headings are not paragraphs but are reported (a
chapter's name is the agent's to write down, and a heading is where a chapter begins), and so is where
each document of the spine starts.  A plain text file is its blocks between blank lines, a block's
lines joined as a typesetter's are; with no blank line in it at all, a line a paragraph, as
lib/draft.py's `paragraphs` takes a pasted text.  An epub and a text file are NOT repaired the way a
PDF's text layer is: they are clean already, and the edition's own spelling is what a book is made
from (a Persian text's kaf and ye are the edition's, not ours to change).

`info`, when given, is filled with what a caller may want beside the paragraphs: `kind`, `warnings`
(sentences, in words), `headings` ([{"at": paragraph index, "text": ...}], an epub's) and `documents`
(the paragraph index each document of an epub's spine starts at).

THE NUMBERING.  `--book DIR --chapter new` writes the paragraphs as the next chapter of the book,
`last` as more of its last chapter, a number as more of that chapter: source/paras/chN_pNN.txt, numbered
on from what the folder already holds (the folder is the one place the numbering lives), with
source/clean.txt added to.  And with the book in hand the tool says what it cannot decide for the person
who reads its output: a text that starts in lower case, or a book whose last paragraph ends without a
stop, may be a part cut in the middle of a paragraph.

Standard library, and what extract_pdf.py already needs (PyMuPDF, and pdftotext for a right-to-left PDF).
"""
import argparse
import html.parser
import os
import posixpath
import re
import sys
import threading
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile

LIB = os.path.dirname(os.path.realpath(__file__))
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import languages                                                    # noqa: E402

KINDS = {".pdf": "pdf", ".epub": "epub", ".txt": "txt"}
SENTENCE_END = ".!?…»”’\"')]」』。！？؟۔।"
# extract_pdf's LANG is a module global its functions read: one recovery at a time under the server
_LOCK = threading.Lock()


class SourceError(ValueError):
    """The file cannot be recovered; the message is a sentence to show."""


def kind_of(path):
    kind = KINDS.get(os.path.splitext(path)[1].lower())
    if kind:
        return kind
    with open(path, "rb") as f:
        head = f.read(8)
    return "pdf" if head.startswith(b"%PDF-") else "epub" if head.startswith(b"PK") else "txt"


def _clean(text):
    """What every kind has done to a line: the controls and bidi marks and soft hyphens that are no
    part of the text, and a run of whitespace as one space.  Nothing that changes a letter."""
    import extract_pdf
    text = extract_pdf.CONTROL.sub("", text)
    text = re.sub("[" + extract_pdf.BIDI + "­]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _debris(drop):
    """Running headers (--drop) and a page number's line are not the book's text -> a test of one block."""
    pat = [re.compile(d) for d in drop]
    pagenum = re.compile(r"[%s]+" % languages.digit_class())
    return lambda p: not p or bool(pagenum.fullmatch(p)) or any(r.search(p) for r in pat)


# ------------------------------------------------------------------ a PDF
def _pdf(path, L, pages, drop, info):
    import extract_pdf
    first, last = pages if pages else (0, 10 ** 6)
    try:
        with _LOCK:
            extract_pdf.LANG = L
            paras, bad = extract_pdf.extract(path, first, last, drop)
    except FileNotFoundError as e:
        raise SourceError("this computer has no %s, which a PDF in %s needs to be read (%s)"
                          % (os.path.basename(str(e.filename or "pdftotext")), L.name, e.strerror))
    except Exception as e:                                          # PyMuPDF raises its own kinds
        raise SourceError("the PDF could not be read (%s)" % (str(e).strip() or type(e).__name__))
    if bad:
        info["warnings"].append("%d page%s where the text and the page's lines disagreed: paragraph breaks "
                                "there may be wrong" % (bad, "" if bad == 1 else "s"))
    if not paras:
        info["warnings"].append("the PDF has no text layer in these pages (a scan?): there is nothing to "
                                "recover from it")
    return paras


# ------------------------------------------------------------------ a plain text file
LEGACY = (("japanese", "cp932"), ("cjk", "gb18030"), ("arabic", "cp1256"), ("", "cp1252"))


def _decode(raw, L, info):
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    script = (getattr(L, "tex", None) or {}).get("script", "")
    for key, codec in LEGACY:
        if not key or key in (L.script, script.lower()):
            try:
                text = raw.decode(codec)
            except UnicodeDecodeError:
                continue
            info["warnings"].append("the file is not UTF-8: it was read as %s, so check the accents and "
                                    "letters of the first paragraphs" % codec)
            return text
    raise SourceError("the text file cannot be read: it is not UTF-8 and no other encoding fits")


def _txt(path, L, drop, info):
    import extract_pdf
    with open(path, "rb") as f:
        text = _decode(f.read(), L, info)
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if re.search("[ﭐ-﷿ﹰ-﻿]", text):
        info["warnings"].append("the text holds Arabic presentation forms (a copy out of a PDF?): they are "
                                "kept as the file has them")
    blocks = re.split(r"\n[ \t]*\n+", text)
    if len(blocks) == 1:
        blocks = text.split("\n")
    out = []
    with _LOCK:
        extract_pdf.LANG = L
        for b in blocks:
            lines = [c for c in (_clean(l) for l in b.split("\n")) if c]
            if lines:
                out.append(_clean(extract_pdf.join_lines(lines)))
    return out


# ------------------------------------------------------------------ an epub
class _Blocks(html.parser.HTMLParser):
    """The blocks of text of one xhtml document, in order: [(is a heading, text)]."""
    BLOCK = {"p", "div", "li", "blockquote", "tr", "td", "th", "pre", "section", "article", "dd", "dt",
             "figcaption", "caption", "h1", "h2", "h3", "h4", "h5", "h6", "body", "ul", "ol", "table"}
    SKIP = {"script", "style", "head", "title", "svg", "math"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks, self._buf, self._skip, self._heading = [], [], 0, False

    def _flush(self):
        text = "".join(self._buf)
        self._buf = []
        if text.strip():
            self.blocks.append((self._heading, text))

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in self.BLOCK:
            self._flush()
            self._heading = tag in ("h1", "h2", "h3", "h4", "h5", "h6")
        elif tag == "br":
            self._buf.append(" ")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)
        elif tag in self.BLOCK:
            self._flush()
            self._heading = False

    def handle_data(self, data):
        if not self._skip:
            self._buf.append(data)


def _spine(z):
    """The documents of an epub in reading order -> [zip member names], the navigation document left out."""
    try:
        root = ET.fromstring(z.read("META-INF/container.xml"))
        opf = next(e.get("full-path") for e in root.iter() if e.tag.endswith("rootfile"))
        pkg = ET.fromstring(z.read(opf))
    except (KeyError, StopIteration, ET.ParseError):
        raise SourceError("the epub has no readable table of contents (META-INF/container.xml and the "
                          "package file it names): it may be damaged")
    base = posixpath.dirname(opf)
    items = {}
    for e in pkg.iter():
        if e.tag.endswith("}item") or e.tag == "item":
            items[e.get("id")] = (e.get("href") or "", e.get("properties") or "", e.get("media-type") or "")
    out = []
    for e in pkg.iter():
        if e.tag.endswith("itemref") and e.get("idref") in items and e.get("linear") != "no":
            href, props, media = items[e.get("idref")]
            if "nav" in props.split() or "html" not in media:
                continue
            name = posixpath.normpath(posixpath.join(base, urllib.parse.unquote(href.split("#")[0])))
            if name in z.namelist() and name not in out:
                out.append(name)
    return out


def _epub(path, L, drop, info):
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as e:
        raise SourceError("the epub could not be opened (%s)" % (e,))
    out, info["headings"], info["documents"] = [], [], []
    debris = _debris(drop)
    with z:
        for name in _spine(z):
            parser = _Blocks()
            parser.feed(z.read(name).decode("utf-8", "replace"))
            parser.close()
            started = False
            for heading, text in parser.blocks:
                text = _clean(text)
                if debris(text):
                    continue
                if not started:
                    info["documents"].append(len(out))
                    started = True
                if heading:
                    info["headings"].append({"at": len(out), "text": text[:120]})
                else:
                    out.append(text)
    if not out:
        info["warnings"].append("the epub has no text in its spine (images only?): there is nothing to "
                                "recover from it")
    return out


# ------------------------------------------------------------------ the one entry
def recover(path, lang, pages=None, drop=(), info=None, kind=None):
    """The file's text as a list of paragraphs, one string each.  `lang` is a registry code; `pages` is
    `[first, last]` (0-based) or None; see the module's docstring for `info`.  `kind` ("pdf", "epub",
    "txt") is for a file whose name says nothing, such as one a server spooled.  A file that cannot be
    read is a SourceError with a sentence."""
    info = info if info is not None else {}
    info.setdefault("warnings", [])
    L = languages.get(lang)
    kind = info["kind"] = kind or kind_of(path)
    if pages is not None:
        pages = [int(pages[0]), int(pages[1])]
        if pages[0] < 0 or pages[0] > pages[1]:
            raise SourceError("the page range is two numbers, the first not after the last: 13-21")
        if kind != "pdf":
            info["warnings"].append("a page range is a PDF's: it was ignored for this %s" % kind)
            pages = None
    if not os.path.isfile(path):
        raise SourceError("there is no file to read the text from")
    paras = {"pdf": lambda: _pdf(path, L, pages, drop, info), "epub": lambda: _epub(path, L, drop, info),
             "txt": lambda: _txt(path, L, drop, info)}[kind]()
    if kind == "txt":
        debris = _debris(drop)
        paras = [p for p in paras if not debris(p)]
    return paras


# ------------------------------------------------------------------ numbering onto a book
PARA_FILE = re.compile(r"^ch(\d+)_p(\d+)\.txt$")


def _numbers(book):
    """The paragraph files a book holds -> {chapter: [paragraph numbers]}."""
    found = {}
    folder = os.path.join(book, "source", "paras")
    for name in os.listdir(folder) if os.path.isdir(folder) else ():
        m = PARA_FILE.match(name)
        if m:
            found.setdefault(int(m.group(1)), []).append(int(m.group(2)))
    return found


def place(book, chapter):
    """Where the next paragraphs of a book go -> (chapter number, first paragraph number).  `chapter` is
    "new", "last" or a chapter's number; a book with nothing yet starts at chapter 1, paragraph 0."""
    have = _numbers(book)
    if chapter == "new" or (chapter == "last" and not have):
        return (max(have) + 1 if have else 1), 0
    if chapter == "last":
        return max(have), max(have[max(have)]) + 1
    n = int(chapter)
    return n, (max(have[n]) + 1 if n in have else 0)


def last_paragraph(book):
    have = _numbers(book)
    if not have:
        return ""
    n = max(have)
    try:
        with open(os.path.join(book, "source", "paras", "ch%d_p%02d.txt" % (n, max(have[n]))),
                  encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def joins(paras, before):
    """What the person who reads the output should look at -> sentences: a part that may be cut in the
    middle of a paragraph, from how it starts and how the text before it ends."""
    said = []
    first = next((c for c in (paras[0] if paras else "") if c.isalpha()), "")
    if first and first.islower():
        said.append("the first paragraph starts with a lowercase letter: it may continue the paragraph "
                    "before it, which was cut in the middle")
    if before and before[-1] not in SENTENCE_END:
        said.append("the paragraph before ends without a full stop (…%s): it may be continued by the "
                    "first paragraph here" % before[-40:])
    return said


def write_paras(folder, tag, start, paras):
    os.makedirs(folder, exist_ok=True)
    names = []
    for i, p in enumerate(paras):
        name = "%s_p%02d.txt" % (tag, start + i)
        with open(os.path.join(folder, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(p + "\n")
        names.append(name)
    return names


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--lang", default=languages.DEFAULT, choices=languages.CODES,
                    help="the book's language, a registry code (default %s)" % languages.DEFAULT)
    ap.add_argument("--from", dest="first", type=int, default=None, help="first PDF page, 0-based")
    ap.add_argument("--to", dest="last", type=int, default=None, help="last PDF page, 0-based")
    ap.add_argument("--drop", action="append", default=[], help="regex of a running header line to discard")
    ap.add_argument("--book", default=None, help="a book's folder: number the paragraphs on from what it holds")
    ap.add_argument("--chapter", default="new", help="with --book: new, last, or a chapter's number")
    ap.add_argument("--out", default=None, help="a file with one paragraph a line")
    ap.add_argument("--append", action="store_true", help="add to --out (or to the book's source/clean.txt)")
    ap.add_argument("--paras", default=None, help="a directory for one file per paragraph")
    ap.add_argument("--tag", default="ch1")
    ap.add_argument("--start", type=int, default=0, help="the number of the first paragraph file")
    a = ap.parse_args(argv)
    pages = None if a.first is None and a.last is None else [a.first or 0, a.last if a.last is not None else 10 ** 6]
    info = {}
    try:
        paras = recover(a.file, a.lang, pages, a.drop, info)
    except SourceError as e:
        print("sourcetext: %s" % e, file=sys.stderr)
        return 2
    L = languages.get(a.lang)
    size = ("%d words" % sum(len(p.split()) for p in paras)) if L.spaced else "%d characters" % sum(len(p) for p in paras)
    print("%d paragraphs, %s (%s)" % (len(paras), size, info["kind"]))
    warnings = list(info["warnings"])
    out, folder, tag, start = a.out, a.paras, a.tag, a.start
    if a.book:
        book = os.path.realpath(a.book)
        if a.chapter not in ("new", "last") and not a.chapter.isdigit():
            print("sourcetext: --chapter is new, last or a chapter's number", file=sys.stderr)
            return 2
        n, start = place(book, a.chapter if a.chapter in ("new", "last") else int(a.chapter))
        tag, folder = "ch%d" % n, os.path.join(book, "source", "paras")
        out, a.append = out or os.path.join(book, "source", "clean.txt"), True
        warnings += joins(paras, last_paragraph(book))
    if out and paras:
        with open(out, "a" if a.append else "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(paras) + "\n")
        print("%s %s" % ("added to" if a.append else "wrote", out))
    if folder and paras:
        names = write_paras(folder, tag, start, paras)
        print("wrote %s, paragraphs %02d-%02d: %s ... %s" % (tag, start, start + len(paras) - 1, names[0], names[-1]))
    if info.get("documents") and len(info["documents"]) > 1:
        print("the epub's documents begin at paragraphs %s" % ", ".join(str(i) for i in info["documents"]))
    for h in info.get("headings", [])[:40]:
        print("heading before paragraph %d: %s" % (h["at"], h["text"]))
    for w in warnings:
        print("warning: %s" % w)
    for p in paras[:2]:
        print("   ", p[:78])
    return 0


if __name__ == "__main__":
    sys.exit(main())
