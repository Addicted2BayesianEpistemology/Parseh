#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The note types' own appearance, kept in step with the live collection.

A note type carries more than its fields: it carries the CSS the cards
wear and the templates that decide what each side asks.  Those live in
the NOTE TYPE, not in any note -- so nothing in anki/<deck>/cards/ can
hold them, and until this module existed every rebuild silently asserted
the styling hard-coded in anki_export.py over whatever had been set
inside Anki.

Note types are collection-global (one set shared by every deck), so the
capture is one store-level file:

    anki/notetypes.json      {mid: {name, fields, css, templates, ...}}

Written by a sync or a bootstrap import; read by anki_export when it
builds a package or renders a preview.  With it, restyling a card inside
Anki survives the next rebuild, and the dashboard's preview shows the
cards as they actually look.

Only this project's own note types are captured -- the pair each
language has in anki_export.MODELS.  A foreign note type is Anki's
business alone -- see the "anki-owned" cards in sync_apkg.py.

Standard library only.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anki_export as ax

# what a snapshot records; "fields" is kept for VALIDATION rather than
# use -- anki_export builds a note's values positionally, so a field list
# that has drifted from the model's list in MODELS is a shape change that
# needs code, and must stop a build rather than quietly produce a
# mismatched model
SNAP_KEYS = ("name", "fields", "css", "templates")


def _pb_walk(data):
    """Minimal protobuf field walk: yields (field_no, wire_type, value).

    Kept here as well as in sync_apkg so that this module stands on its
    own; the two are the same handful of lines and neither imports the
    other (sync_apkg imports THIS one).
    """
    i, n = 0, len(data)
    while i < n:
        tag = shift = 0
        while True:
            b = data[i]; i += 1
            tag |= (b & 0x7f) << shift
            shift += 7
            if not b & 0x80:
                break
        field, wt = tag >> 3, tag & 7
        if wt == 0:
            v = shift = 0
            while True:
                b = data[i]; i += 1
                v |= (b & 0x7f) << shift
                shift += 7
                if not b & 0x80:
                    break
        elif wt == 2:
            ln = shift = 0
            while True:
                b = data[i]; i += 1
                ln |= (b & 0x7f) << shift
                shift += 7
                if not b & 0x80:
                    break
            v = data[i:i + ln]; i += ln
        elif wt == 5:
            i += 4; v = None
        elif wt == 1:
            i += 8; v = None
        else:
            return
        yield field, wt, v


def _pb_str(blob, want):
    for f, wt, v in _pb_walk(blob or b""):
        if wt == 2 and f == want:
            try:
                return v.decode("utf-8")
            except UnicodeDecodeError:
                return ""
    return ""


def snapshot(con):
    """{mid: {name, fields, css, templates}} for this project's note
    types, from either schema.  Missing pieces simply come back empty,
    so a package that cannot be read this way changes nothing.
    """
    out = {}
    mine = set(ax.MODELS)                  # every language's pair
    try:                                   # schema 18: real tables
        rows = con.execute("select id, name, config from notetypes").fetchall()
        flds = {}
        for ntid, ord_, name in con.execute(
                "select ntid, ord, name from fields order by ntid, ord"):
            flds.setdefault(ntid, []).append(name)
        tmpls = {}
        for ntid, ord_, name, cfg in con.execute(
                "select ntid, ord, name, config from templates "
                "order by ntid, ord"):
            tmpls.setdefault(ntid, []).append({
                "name": name,
                "qfmt": _pb_str(cfg, 1), "afmt": _pb_str(cfg, 2),
                "bqfmt": _pb_str(cfg, 3), "bafmt": _pb_str(cfg, 4)})
        for mid, name, cfg in rows:
            if mid in mine:
                out[mid] = {"name": name, "fields": flds.get(mid, []),
                            "css": _pb_str(cfg, 3),
                            "templates": tmpls.get(mid, [])}
    except Exception:                      # legacy: one JSON blob in col
        out = {}                           # never blend half a schema-18
        try:                               # read into the legacy one
            (blob,) = con.execute("select models from col").fetchone()
            for smid, m in json.loads(blob).items():
                mid = int(smid)
                if mid not in mine:
                    continue
                out[mid] = {
                    "name": m.get("name", ""),
                    "fields": [f["name"] for f in m.get("flds", [])],
                    "css": m.get("css", ""),
                    "templates": [{"name": t.get("name", ""),
                                   "qfmt": t.get("qfmt", ""),
                                   "afmt": t.get("afmt", ""),
                                   "bqfmt": t.get("bqfmt", ""),
                                   "bafmt": t.get("bafmt", "")}
                                  for t in m.get("tmpls", [])]}
        except Exception:
            return {}
    # a snapshot with no css AND no templates tells us nothing; drop it
    # rather than record an empty appearance over a good one
    return {mid: s for mid, s in out.items()
            if s.get("css") or s.get("templates")}


def _core(snap):
    return {k: snap.get(k) for k in SNAP_KEYS}


def capture(anki_dir, snap, source=""):
    """Record what the collection says a note type looks like.

    Returns a list of {mid, name, what} describing what changed, so a
    sync can report "your restyling came home" rather than doing it
    silently.  Writing nothing when nothing differs keeps the file's
    mtime meaningful.
    """
    if not snap:
        return []
    path = os.path.join(anki_dir, ax.OVERRIDES_NAME)
    have = ax.load_overrides(anki_dir)
    changes = []
    merged = {str(k): v for k, v in have.items()}
    for mid, s in snap.items():
        old = have.get(mid)
        if old is not None and _core(old) == _core(s):
            continue
        what = []
        if old is None:
            what.append("first capture")
        else:
            if (old.get("css") or "") != (s.get("css") or ""):
                what.append("styling")
            if old.get("templates") != s.get("templates"):
                what.append("templates")
            if old.get("fields") != s.get("fields"):
                what.append("fields")
            if not what:
                what.append("name")
        rec = dict(_core(s))
        rec["captured"] = time.strftime("%Y-%m-%d %H:%M:%S")
        rec["source"] = os.path.basename(source or "")
        merged[str(mid)] = rec
        changes.append({"mid": mid, "name": s.get("name") or str(mid),
                        "what": ", ".join(what)})
    if changes:
        os.makedirs(anki_dir, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=1,
                      sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
    return changes


def describe(anki_dir):
    """What the store currently believes each note type looks like --
    for a person, not a machine."""
    out = []
    for mid, s in sorted(ax.load_overrides(anki_dir).items()):
        out.append({"mid": mid, "name": s.get("name") or str(mid),
                    "captured": s.get("captured") or "",
                    "source": s.get("source") or "",
                    "fields": s.get("fields") or [],
                    # a captured id the code does not know at all can
                    # match nothing -- an old capture of a model since
                    # dropped from the registry, say
                    "matches_code": (s.get("fields") or []) ==
                    (ax.MODELS.get(mid) or {}).get("fields")})
    return out
