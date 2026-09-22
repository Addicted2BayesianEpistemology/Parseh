#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Give every chunk of a Japanese or Chinese book or video the words it lacks.

    python3 lib/fill_words.py --video <id or directory> [--dry-run]
    python3 lib/fill_words.py --book <slug, folder/slug or directory> [--dry-run]
    python3 lib/fill_words.py --lang ja --json <annotator json>... [--door book|video] [--dry-run]

`--json` is where an annotator's words begin: a book's paragraph or batch, a
video's part, gets for every chunk without words the proposal a pasted draft
would get, and a chunk whose reading is still blank gets that too, read from
the words (fill_json).  The annotator then corrects both in the file.

A text added from now on is divided into words when it is added (lib/draft.py,
the video add page).  This is for what was added before, or through a door
that did not: each glossed chunk of a words language (lib/languages.json
"words") that has no word line is given lib/words.py's proposal for it.

A line already there is never replaced -- it may be somebody's correction --
and a chunk the analyzers propose nothing for is left without one, which is
always legal.  Every line goes in through the same writer the reader's editor
uses (youtube/lib/annwrite.py, lib/texwrite.py), one chunk at a time, so each
is proved against the checker before it is written, a refusal writes nothing,
and a book chunk is rewritten from \\chr to \\chrw (or \\ch to \\chw) and not a
byte beside it.  What was proposed is a draft to correct, as every proposal is.

Run it with the Python that has the analyzers (the ilya-frank environment):
without them there is nothing to propose and it says so.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
YT_LIB = os.path.join(ROOT, "youtube", "lib")
for _p in (HERE, YT_LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import segmenter                                               # noqa: E402
import words                                                   # noqa: E402


def _video_dir(where):
    if os.path.isfile(os.path.join(where, "annotations.json")):
        return os.path.realpath(where)
    import ytpages
    _meta, path = ytpages.find_video(where)
    if not path:
        raise SystemExit("fill_words: no video %r (neither a directory holding "
                         "annotations.json nor an id in youtube/videos/)" % where)
    return path


def _usable(L):
    if not L.words:
        raise SystemExit("fill_words: %s has no word layer (lib/languages.json)" % L.name)
    if not words.available(L.code):
        raise SystemExit("fill_words: nothing can divide %s in %s -- run it with the "
                         "Python that has %s (conda activate ilya-frank)"
                         % (L.name, sys.executable, segmenter.about(L.code)["packages"]))


def _said(chunk, L):
    """The chunk's own reading -- kana, or the pinyin of tr -- which gives the
    proposed words theirs (lib/words.py)."""
    v = chunk.get("kana" if L.reading else "tr")
    return v if isinstance(v, str) else ""


def fill_video(where, dry_run=False, say=print):
    import annwrite
    from check_annotations import video_language
    vdir = _video_dir(where)
    ann = annwrite.read(vdir)
    try:
        with open(os.path.join(vdir, "video.json"), encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        meta = {}
    L = video_language(vdir, meta, ann)
    _usable(L)
    given = had = none = 0
    refused = []
    for si, seg in enumerate(ann.get("segments") or []):
        if seg.get("plain"):
            continue
        for ci, ch in enumerate(seg.get("chunks") or []):
            fa = ch.get("fa") or ""
            if ch.get("plain") or not L.has_script(fa):
                continue
            if (ch.get("words") or "").strip():
                had += 1
                continue
            line = words.line(fa, L.code, _said(ch, L))
            if not line:
                none += 1
                continue
            if dry_run:
                say("  segment %d chunk %d: %s" % (si, ci, line))
                given += 1
                continue
            try:
                annwrite.edit_chunk(vdir, si, ci, {"words": line})
                given += 1
            except ValueError as e:
                refused.append("segment %d chunk %d: %s" % (si, ci, e))
    return _report(os.path.relpath(vdir, ROOT), given, had, none, refused, dry_run, say)


def fill_book(where, dry_run=False, say=print):
    import books
    import texwrite
    book = books.find_book(where)
    L = book.lang
    _usable(L)
    given = had = none = 0
    refused = []
    for chapter in texwrite.book_chapters(book.dir):
        for rec in texwrite.read_chunks(chapter["path"]):
            fa = rec.get("fa") or ""
            if not rec.get("glossed") or not L.has_script(fa):
                continue
            if (rec.get("words") or "").strip():
                had += 1
                continue
            line = words.line(fa, L.code, _said(rec, L))
            if not line:
                none += 1
                continue
            where_ = "%s chunk %d" % (chapter["file"], rec["index"])
            if dry_run:
                say("  %s: %s" % (where_, line))
                given += 1
                continue
            try:
                texwrite.edit_chunk(chapter["path"], rec["index"], {"words": line})
                given += 1
            except (texwrite.Refused, ValueError) as e:
                refused.append("%s: %s" % (where_, e))
    return _report(os.path.relpath(book.dir, ROOT), given, had, none, refused, dry_run, say)


def _shown(path):
    """A document's path relative to the toolbox when it lives in it, whole
    when it does not (a copy somewhere else)."""
    rel = os.path.relpath(path, ROOT)
    return path if rel.startswith("..") else rel


def _report(name, given, had, none, refused, dry_run, say):
    name = _shown(name)
    for r in refused:
        say("  refused  " + r)
    say("%s: %d chunk%s %s words, %d already had them, %d had no proposal, %d refused"
        % (name, given, "" if given == 1 else "s",
           "would be given" if dry_run else "given", had, none, len(refused)))
    return {"given": given, "had": had, "none": none, "refused": refused}


def _chunk_lists(doc):
    """Every list of chunks in an annotator's file, whatever its shape: a
    book's paragraph ({"ann": {"sentences": [{"chunks": [...]}]}}) or batch
    ({"paragraphs": [...]}), a video's part ([{"start", "chunks"}]) or a
    pasted answer ({"captions": [...]})."""
    found = []

    def walk(v):
        if isinstance(v, dict):
            if isinstance(v.get("chunks"), list):
                found.append(v["chunks"])
            for k, x in v.items():
                if k != "chunks":
                    walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(doc)
    return found


def fill_json(paths, lang, door=None, dry_run=False, say=print):
    """The words for every chunk of annotator JSON files that has none, in
    place -- the proposal a pasted draft gets (lib/draft.py), laid over the
    chunk's own reading where it has one -- and, where that reading is still
    blank, the reading filled in from the words, as a draft fills it.  This is
    how an annotator starts a chunk's words: from the machine's, corrected.

    A line already there is never replaced, a proposal the checker refuses is
    reported and not written, and a file with nothing given is not rewritten.
    `door` is "book" or "video" (whose checks a line must pass); by default a
    file that is a list, or holds "captions", is a video's."""
    import languages
    import wordline
    try:
        L = languages.get(lang)
    except KeyError:
        raise SystemExit("fill_words: %r is not a language of the registry" % lang)
    _usable(L)
    field = "kana" if L.reading else "tr"
    total = {"given": 0, "had": 0, "none": 0, "refused": []}
    for path in paths:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        kind = door or ("video" if isinstance(doc, list) or
                        (isinstance(doc, dict) and "captions" in doc) else "book")
        gate = wordline.VIDEO if kind == "video" else wordline.BOOK
        given = had = none = 0
        refused = []
        for chunks in _chunk_lists(doc):
            for ci, ch in enumerate(chunks):
                if not isinstance(ch, dict) or ch.get("plain"):
                    continue
                fa = ch.get("fa")
                if not isinstance(fa, str) or not fa.strip() or (L.chars and not L.has_script(fa)):
                    continue
                if isinstance(ch.get("words"), str) and ch["words"].strip():
                    had += 1
                    continue
                said = _said(ch, L)
                line = words.line(fa, L.code, said)
                if not line:
                    none += 1
                    continue
                bad = wordline.check(fa, line, L, reading=said, door=gate)[0]
                if bad:
                    refused.append("%r: %s" % (fa, "; ".join(bad)))
                    continue
                given += 1
                if dry_run:
                    say("  %s" % line)
                    continue
                new = {}
                for k, v in ch.items():
                    if k == "words":
                        continue
                    new[k] = v
                    if k == "fa":
                        new["words"] = line
                if not (new.get(field) or "").strip():
                    seeded = wordline.reading_from(line, L)
                    if seeded:
                        new[field] = seeded
                chunks[ci] = new
        if given and not dry_run:
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=1)
                f.write("\n")
            os.replace(tmp, path)
        r = _report(os.path.abspath(path), given, had, none, refused, dry_run, say)
        for k in ("given", "had", "none"):
            total[k] += r[k]
        total["refused"] += refused
    return total


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--video", help="a video id, or its directory")
    what.add_argument("--book", help="a book slug, folder/slug, or directory")
    what.add_argument("--json", nargs="+", metavar="FILE",
                      help="annotator JSON files, filled in place: a book's paragraph "
                           "or batch, a video's part")
    ap.add_argument("--lang", help="with --json: the registry code (ja, zh)")
    ap.add_argument("--door", choices=("book", "video"),
                    help="with --json: whose checks each line must pass")
    ap.add_argument("--dry-run", action="store_true",
                    help="print each proposal and write nothing")
    a = ap.parse_args(argv)
    if a.json:
        if not a.lang:
            ap.error("--json needs --lang (ja or zh)")
        r = fill_json(a.json, a.lang, a.door, a.dry_run)
    else:
        r = (fill_video(a.video, a.dry_run) if a.video else fill_book(a.book, a.dry_run))
    return 1 if r["refused"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
