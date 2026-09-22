#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bring a video from the older "watching edition" format into videos/<folder>/<id>/.

    python3 lib/import_old_video.py "../old videos format/<slug>" [...] [--dry-run] [--replace]

The older player kept a video as a directory with the transcript in
segments.json ([{n, t0, t1, sec, lang, text}]), the section names in
sections.json, and the annotation as a script.tex in the books' own
\\ch{fa}{tr}{voc}{en} form (four arguments -- no colour slot yet) with
\\chp{text} for anything not glossed.  The current player wants
transcript.txt (the pasted YouTube transcript), video.json, parts/*.json
and annotations.json under videos/<language folder>/<id>/, and it checks
every caption against the transcript.  The old editions were all Persian;
an old video.json may still say "language", and the folder follows it.

So this rebuilds a transcript from the segments -- a timestamp line and a
text line per segment, a "Chapter N: title" line where a section begins --
turns each script block into the chunks of its caption, and writes the parts
the way the pipeline expects, before running merge_parts.py and
check_annotations.py on the result exactly as a fresh video would get.

The vocabulary lines are read with the same parser the book reader uses
(texparse.parse_voc, flattened by texparse.voc_text), told the video's
language, so a \\vb comes out as "verb rom · pres. stem rom · past stem rom
· meaning" -- with the pair of labels that language gives its verb forms,
Arabic's impf./masdar where Persian has pres./past, and without a pair whose
form was left blank -- the very shape the conventions ask for.  A \\chp
holding target text becomes a chunk marked "plain": true -- shown as text,
never glossed -- which is how the older format's partial annotation survives.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

LIB = os.path.dirname(os.path.realpath(__file__))
HERE = os.path.dirname(LIB)                       # youtube/
VIDEOS = os.path.join(HERE, "videos")
TOOLBOX_LIB = os.path.join(os.path.dirname(HERE), "lib")
for p in (LIB, TOOLBOX_LIB):
    if p not in sys.path:
        sys.path.insert(0, p)
import texparse as T                 # noqa: E402  the books' .tex reader
import check_annotations as CA       # noqa: E402  the transcript parser, the checks
import languages                     # noqa: E402  the registry (folders, digits, scripts)

PART_SIZE = 25


def tex_text(s, lang):
    """A \\ch argument as plain text: macros unwrapped, escapes undone.

    The language is the video's own, because a \\vb prints the two labels
    that language gives its verb forms -- Arabic's impf./masdar, Japanese's
    stem/-te -- and the field, read on its own, cannot say who wrote it: the
    parser would otherwise go on printing the default's pres./past.  A pair
    whose form is blank is left out with its label, as the PDF leaves it out
    (a Chinese verb's missing "can't" form, an Arabic verb with no masdar).

    The walk itself is texparse.voc_text, which began here: the server's
    verb entries flatten their TeX with the same function, so a video line
    written by this importer and one written from the reader's sidebar are
    the same string for the same \\vb."""
    return T.voc_text(s, lang)


def parse_script(tex, lang):
    """The blocks of a script.tex, in order: {label, t0, t1, chunks}."""
    blocks, cur, label, span = [], None, None, None
    lines = tex.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        m = re.match(r"\\parnum\{([^}]*)\}", line)
        if m:
            # the old labels were written in the language's digits (\parnum{۳.۱})
            label = tuple(int(x) for x in
                          languages.any_to_latin_digits(m.group(1)).split("."))
            continue
        m = re.match(r"^%\s*@par\s+\S+\s+([\d.]+)\s+([\d.]+)", line)
        if m:
            span = (float(m.group(1)), float(m.group(2)))
            continue
        if line.startswith("\\begin{frank}"):
            cur = {"label": label, "t0": span[0] if span else None,
                   "t1": span[1] if span else None, "chunks": []}
            continue
        if line.startswith("\\end{frank}"):
            blocks.append(cur)
            cur, span = None, None
            continue
        if cur is None or not (line.startswith("\\ch{") or line.startswith("\\chp{")):
            continue
        # a chunk is one line, unless its braces run on (they never do in a
        # generated script, but a hand edit could wrap one)
        while line.count("{") > line.count("}") and i < len(lines):
            line += "\n" + lines[i]
            i += 1
        if line.startswith("\\chp{"):
            args, _ = T.read_args(line, 4, 1)
            ch = {"fa": args[0].strip()}
            if lang.has_script(ch["fa"]):
                ch["plain"] = True         # target text never glossed: shown as text
            cur["chunks"].append(ch)
        else:
            args, _ = T.read_args(line, 3, 4)
            fa, tr, voc, en = args
            ch = {"fa": fa.strip(), "tr": tex_text(tr, lang),
                  "en": tex_text(en, lang)}
            voc = tex_text(voc, lang)
            if voc:
                ch["voc"] = voc
            cur["chunks"].append(ch)
    return blocks


def stamp(t):
    t = int(t)
    if t >= 3600:
        return "%d:%02d:%02d" % (t // 3600, (t % 3600) // 60, t % 60)
    return "%d:%02d" % (t // 60, t % 60)


def make_transcript(segs, sections):
    """The transcript the current pipeline reads, rebuilt from the segments."""
    lines, seen = [], set()
    for s in segs:
        sec = s.get("sec")
        if sec is not None and sec not in seen:
            seen.add(sec)
            t = sections.get(str(sec)) or ["", ""]
            title = (t[0] or t[1] or "").strip() if isinstance(t, list) else str(t).strip()
            if title:
                lines.append("Chapter %d: %s" % (sec, title))
        lines.append(stamp(s["t0"]))
        lines.append(re.sub(r"\s+", " ", s["text"]).strip())
    return "\n".join(lines) + "\n"


def parse_transcript_text(text, lang):
    fd, path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        return CA.parse_transcript(path, lang)
    finally:
        os.unlink(path)


def convert(old_dir):
    """-> (meta, transcript, parts, warnings); raises on anything unsound."""
    with open(os.path.join(old_dir, "video.json"), encoding="utf-8") as f:
        old = json.load(f)
    with open(os.path.join(old_dir, "segments.json"), encoding="utf-8") as f:
        segs = json.load(f)
    sections = {}
    sp = os.path.join(old_dir, "sections.json")
    if os.path.exists(sp):
        with open(sp, encoding="utf-8") as f:
            sections = json.load(f)
    # the old editions were Persian; a video.json that says otherwise is believed
    lang = languages.get_or_default(CA.lang_code(old.get("language")))
    with open(os.path.join(old_dir, "script.tex"), encoding="utf-8") as f:
        blocks = parse_script(f.read(), lang)
    vid = old.get("youtube_id") or old.get("id")
    if not vid or not re.match(r"^[A-Za-z0-9_-]{11}$", vid):
        raise ValueError("no usable youtube_id in video.json")
    segs = sorted(segs, key=lambda s: s.get("n", 0))
    if len(blocks) != len(segs):
        raise ValueError("script.tex has %d blocks, segments.json %d segments"
                         % (len(blocks), len(segs)))
    # block i belongs to segment i: prove it by the section counter and the time
    counter, warnings = {}, []
    for i, (b, s) in enumerate(zip(blocks, segs)):
        sec = s.get("sec")
        counter[sec] = counter.get(sec, 0) + 1
        if b["label"] != (sec, counter[sec]):
            raise ValueError("block %d is \\parnum %s but segment %d is %s"
                             % (i, b["label"], s.get("n"), (sec, counter[sec])))
        if b["t0"] is not None and abs(b["t0"] - float(s["t0"])) > 0.02:
            raise ValueError("block %d starts at %s, its segment at %s"
                             % (i, b["t0"], s["t0"]))
    transcript = make_transcript(segs, sections)
    captions = parse_transcript_text(transcript, lang)
    if len(captions) != len(segs):
        raise ValueError("the rebuilt transcript parses to %d captions for %d "
                         "segments -- a text line looks like a timestamp or a "
                         "chapter" % (len(captions), len(segs)))
    for c, s in zip(captions, segs):
        if CA.norm(c["text"], lang) != CA.norm(re.sub(r"\s+", " ", s["text"]), lang):
            raise ValueError("transcript text drifted at %s" % stamp(s["t0"]))
    parts, unglossed = [], 0
    for c, b in zip(captions, blocks):
        if c["plain"]:
            continue                      # merge_parts fills these from the transcript
        chunks = b["chunks"]
        if not chunks:
            raise ValueError("segment at %s has no chunks" % stamp(c["start"]))
        if any(ch.get("plain") for ch in chunks):
            unglossed += 1
        parts.append({"start": c["start"], "chunks": chunks})
    if unglossed:
        warnings.append("%d caption(s) carry %s that was never glossed; "
                        "they are marked plain and show as text" % (unglossed, lang.name))
    dur = int(old.get("duration") or (segs[-1].get("t1") or segs[-1]["t0"]))
    meta = {
        "id": vid,
        "url": "https://www.youtube.com/watch?v=" + vid,
        "title": old.get("title_en") or old.get("title_latin") or old.get("title") or vid,
        # title_native is the display title in the video's language; title_fa
        # is the same value under its legacy name, which older readers look for
        "title_native": old.get("title") or "",
        "title_fa": old.get("title") or "",
        "channel": old.get("channel") or "Unknown channel",
        "language": lang.code,
        "level": old.get("level") or "intermediate",
        "duration": stamp(dur),
        "added": datetime.date.today().isoformat(),
        "blurb": old.get("blurb") or "",
    }
    if old.get("captions"):
        meta["captions"] = old["captions"]          # human-written or ASR: say which
    if old.get("published"):
        meta["published"] = old["published"]
    meta["imported_from"] = "old videos format/" + os.path.basename(os.path.normpath(old_dir))
    # the same checks the pipeline will run, before anything is written
    segs_out, it = [], iter(parts)
    for cap in captions:
        sg = {"start": cap["start"], "plain": True} if cap["plain"] else dict(next(it))
        sg["text"] = cap["text"]
        if cap["chapter"]:
            sg["chapter"] = cap["chapter"]
        segs_out.append(sg)
    errors, warns = [], []
    CA.check_segments(segs_out, captions, errors.append, warns.append, lang)
    if errors:
        raise ValueError("%d error(s):\n  " % len(errors) + "\n  ".join(errors[:8]))
    warnings += warns
    return meta, transcript, parts, warnings


def write(meta, transcript, parts, replace=False):
    vid = meta["id"]
    folder = languages.get_or_default(meta.get("language")).folder
    vdir = os.path.join(VIDEOS, folder, vid)
    # the same id may already sit in another language folder, or flat under
    # videos/ from before languages: that is the one to replace.  A fresh
    # checkout has no videos/ yet (the first import makes it), and
    # videos/.trash/ is never a language folder.
    folders = sorted(os.listdir(VIDEOS)) if os.path.isdir(VIDEOS) else []
    for cand in [os.path.join(VIDEOS, f, vid) for f in folders
                 if not f.startswith(".") and os.path.isdir(os.path.join(VIDEOS, f))] \
            + [os.path.join(VIDEOS, vid)]:
        if os.path.isfile(os.path.join(cand, "video.json")):
            vdir_old = cand
            break
    else:
        vdir_old = vdir
    if os.path.isdir(vdir_old):
        if not replace:
            return None
        import shutil, time
        # the trash name is made unique, as ytpages.trash_video does: moving
        # onto a name that exists (two replaces within one second) would put
        # the tree inside the earlier entry instead of beside it
        trash = os.path.join(VIDEOS, ".trash")
        os.makedirs(trash, exist_ok=True)
        base = os.path.join(trash, "%s-%s" % (vid, time.strftime("%Y%m%d-%H%M%S")))
        dest, n = base, 1
        while os.path.exists(dest):
            n += 1
            dest = "%s-%d" % (base, n)
        shutil.move(vdir_old, dest)
    os.makedirs(os.path.join(vdir, "parts"))
    with open(os.path.join(vdir, "transcript.txt"), "w", encoding="utf-8") as f:
        f.write(transcript)
    with open(os.path.join(vdir, "video.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")
    for n in range(0, len(parts), PART_SIZE):
        with open(os.path.join(vdir, "parts", "%02d.json" % (n // PART_SIZE + 1)),
                  "w", encoding="utf-8") as f:
            json.dump(parts[n:n + PART_SIZE], f, ensure_ascii=False, indent=1)
            f.write("\n")
    rel = os.path.join("videos", folder, vid)
    for tool in ("merge_parts.py", "check_annotations.py"):
        r = subprocess.run([sys.executable, os.path.join("lib", tool), rel], cwd=HERE,
                           capture_output=True, text=True)
        tail = (r.stdout or "").strip().split("\n")[-1]
        print("   %s: %s" % (tool, tail))
        if r.returncode:
            print((r.stdout or "") + (r.stderr or ""))
            return False
    return vdir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+", help="old-format video directories")
    ap.add_argument("--dry-run", action="store_true", help="convert and check, write nothing")
    ap.add_argument("--replace", action="store_true", help="overwrite a video already present")
    a = ap.parse_args()
    bad = 0
    for d in a.dirs:
        name = os.path.basename(os.path.normpath(d))
        try:
            meta, transcript, parts, warnings = convert(d)
        except (OSError, ValueError, KeyError) as e:
            print("%s: FAILED -- %s" % (name, e))
            bad += 1
            continue
        nch = sum(len(p["chunks"]) for p in parts)
        print("%s -> videos/%s/%s  (%s; %d captions glossed, %d chunks, %s)"
              % (name, languages.get_or_default(meta.get("language")).folder, meta["id"],
                 meta["title_native"], len(parts), nch, meta["duration"]))
        for w in warnings:
            print("   note: %s" % w)
        if a.dry_run:
            continue
        out = write(meta, transcript, parts, replace=a.replace)
        if out is None:
            print("   already present as videos/*/%s -- kept (use --replace to overwrite)" % meta["id"])
        elif out is False:
            bad += 1
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
