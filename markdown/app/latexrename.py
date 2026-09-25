# SPDX-License-Identifier: GPL-3.0-or-later
"""Renaming a LaTeX theme puts every block that names it right (TO-DO §8.39).

THE BLOCKS ARE CORRECTED, NOT ORPHANED (the owner, 2026-09-24, settled):
renaming a theme in Settings rewrites the name in every latex block that
names it, everywhere in the software.  It is the one place this feature
writes into what a person wrote, so it is done carefully:

  * every reference is found first, and counted, and the count is said
    before anything is done -- "3 documents, 1 exercise deck, 2 notes";
  * where a block can be is where the parser reads one (mdparser, the same
    set as `:::math`, and a jolly card's four fields): a studio document, a
    note in a book or a video, an exercise of a deck -- and each of them in
    its trash too, so that what comes back from it finds its theme;
  * a name another theme has is refused before anything is written;
  * anything that cannot be written right now -- a deck taken out on a
    phone, a file that is not there or may not be written -- stops the
    rename before anything is written, and says which (the owner,
    2026-09-25); there is no undo, and renaming back is a rename;
  * a write that fails half way puts back every file already written, so
    no text is ever left with some blocks on the old name and some on the
    new.

The key of a drawing is the RESOLVED theme and not its name, so a rename
changes no picture and recompiles nothing.
"""
import os
from pathlib import Path

import decks
import store
import latexthemes


def _counts(text, old):
    return sum(1 for b in latexthemes.blocks_in(text)
               if b["theme"] and latexthemes.name_key(b["theme"]) == latexthemes.name_key(old))


def _doc_roots(libraries):
    """(kind, library root, label) for the studio's library and every notes
    library the server knows (a book's, a video's, in a trash or not)."""
    yield "document", Path(store.LIB), ""
    for root, label in libraries:
        yield "note", Path(root), label


def _docs(root):
    """(doc id, source.md) of every document of the library at `root`."""
    if not root.is_dir():
        return
    was = store.use_library(root)
    try:
        for d in store._doc_dirs():
            src = d / "source.md"
            if src.is_file():
                yield d.name, src
    finally:
        store.use_library(was)


def _deck_dirs():
    """(deck dir, label, in the trash) of every deck, the trash's included."""
    base = Path(decks.DIR)
    if not base.is_dir():
        return
    for lang in sorted(os.listdir(base)):
        top = base / lang
        if not top.is_dir():
            continue
        if lang == ".trash":
            for name in sorted(os.listdir(top)):
                if (top / name / "items").is_dir():
                    yield top / name, name, True
            continue
        if lang.startswith("."):
            continue
        for name in sorted(os.listdir(top)):
            d = top / name
            if not name.startswith(".") and (d / "items").is_dir():
                yield d, "%s/%s" % (lang, name), False


def plan(old, new, libraries=()):
    """What renaming `old` to `new` would change -> {"said", "documents",
    "notes", "decks", "exercises", "blocks", "places", "blocked": [why...],
    "refused": why or ""}.  Nothing is written."""
    out = {"documents": 0, "notes": 0, "decks": 0, "exercises": 0, "blocks": 0,
           "places": [], "blocked": [], "refused": "", "trash": 0}
    if latexthemes.find(old) is None:
        out["refused"] = "There is no theme called %s." % old
        return out
    if not latexthemes.name_ok(new):
        out["refused"] = "%r cannot be a theme's name: %s." % (new, latexthemes.NAME_RULE)
        return out
    other = latexthemes.find(new)
    if other is not None and latexthemes.name_key(other["name"]) != latexthemes.name_key(old):
        out["refused"] = ("There is a theme called %s already: a name another theme has is "
                          "refused, and nothing was changed." % other["name"])
        return out
    if latexthemes.name_key(old) == latexthemes.name_key(latexthemes.DEFAULT) \
            and latexthemes.name_key(new) != latexthemes.name_key(old):
        out["refused"] = ("The theme called default keeps its name: a block that names no "
                          "theme is drawn with it.")
        return out
    for kind, root, label in _doc_roots(libraries):
        for doc_id, src in _docs(root):
            try:
                text = src.read_text(encoding="utf-8")
            except OSError as e:
                out["blocked"].append("%s could not be read (%s)" % (src, e))
                continue
            n = _counts(text, old)
            if not n:
                continue
            out["blocks"] += n
            out["documents" if kind == "document" else "notes"] += 1
            if ".trash" in src.parts:
                out["trash"] += 1
            out["places"].append({"kind": kind, "where": label or doc_id, "id": doc_id,
                                  "blocks": n})
            if not os.access(str(src), os.W_OK) or not os.access(str(src.parent), os.W_OK):
                out["blocked"].append("%s cannot be written" % src)
    for d, label, trashed in _deck_dirs():
        hits = 0
        for item_id in decks._item_ids(d):
            raw = decks._read_json(d / "items" / (item_id + ".json")) or {}
            n = _counts(raw.get("markdown") or "", old)
            if n:
                hits += 1
                out["blocks"] += n
                path = d / "items" / (item_id + ".json")
                if not os.access(str(path), os.W_OK) or not os.access(str(path.parent), os.W_OK):
                    out["blocked"].append("an exercise of %s cannot be written" % label)
        if not hits:
            continue
        out["decks"] += 1
        out["exercises"] += hits
        if trashed:
            out["trash"] += 1
        out["places"].append({"kind": "deck", "where": label, "blocks": hits})
        rec = decks._read_json(d / decks.CHECKOUT) if not trashed else None
        if isinstance(rec, dict) and rec.get("out"):
            out["blocked"].append("the deck %s is taken out on %s: give it back, or take it "
                                  "back, first" % (label, rec.get("device") or "a phone"))
    parts = []
    for n, one, many in ((out["documents"], "document", "documents"),
                         (out["decks"], "exercise deck", "exercise decks"),
                         (out["notes"], "note", "notes")):
        if n:
            parts.append("%d %s" % (n, one if n == 1 else many))
    out["said"] = (", ".join(parts) if parts else "no document, deck or note") + (
        " (%d of them in a trash)" % out["trash"] if out["trash"] else "")
    return out


def apply(old, new, libraries=()):
    """The rename, done -> the plan it followed, with "done": True.  Refused
    (ValueError, in words) before anything is written when the plan is."""
    p = plan(old, new, libraries)
    if p["refused"]:
        raise ValueError(p["refused"])
    if p["blocked"]:
        raise ValueError("Nothing was renamed: " + "; ".join(p["blocked"]) + ".")
    written = []               # (how to put it back)
    try:
        for kind, root, _label in _doc_roots(libraries):
            for doc_id, src in list(_docs(root)):
                text = src.read_text(encoding="utf-8")
                if not _counts(text, old):
                    continue
                was = store.use_library(root)
                try:
                    before = {}

                    def change(src_text, before=before):
                        before["text"] = src_text
                        return latexthemes.rename_in_text(src_text, old, new)[0]
                    if store._rewrite_source(doc_id, change):
                        written.append(("doc", root, doc_id, before["text"]))
                finally:
                    store.use_library(was)
        for d, _label, _trashed in _deck_dirs():
            with decks._lock(d):
                for item_id in decks._item_ids(d):
                    path = d / "items" / (item_id + ".json")
                    raw = decks._read_json(path)
                    if not raw or not _counts(raw.get("markdown") or "", old):
                        continue
                    before = dict(raw)
                    raw["markdown"] = latexthemes.rename_in_text(raw["markdown"], old, new)[0]
                    decks._write_json(path, raw)
                    written.append(("item", path, before))
        latexthemes.rename_store(old, new)
    except Exception:
        for w in reversed(written):
            try:
                if w[0] == "doc":
                    was = store.use_library(w[1])
                    try:
                        store._rewrite_source(w[2], lambda _t, back=w[3]: back)
                    finally:
                        store.use_library(was)
                else:
                    decks._write_json(w[1], w[2])
            except Exception:                                # noqa: BLE001
                pass
        raise
    latexthemes.log_rename(old, new)
    return dict(p, done=True)


def every_block(libraries=()):
    """(tex, theme) of every well-formed latex block there is -- the drawings
    "Forget drawings nothing uses" keeps."""
    for _kind, root, _label in _doc_roots(libraries):
        for _doc_id, src in _docs(root):
            try:
                text = src.read_text(encoding="utf-8")
            except OSError:
                continue
            for b in latexthemes.blocks_in(text):
                if not b["errors"] and b["closed"]:
                    yield b["tex"], b["theme"] or None
    for d, _label, _trashed in _deck_dirs():
        for item_id in decks._item_ids(d):
            raw = decks._read_json(d / "items" / (item_id + ".json")) or {}
            for b in latexthemes.blocks_in(raw.get("markdown") or ""):
                if not b["errors"] and b["closed"]:
                    yield b["tex"], b["theme"] or None
