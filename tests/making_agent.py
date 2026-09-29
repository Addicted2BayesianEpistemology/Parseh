#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""A scripted stand-in for the agent a book is made by, and the scratch install it works in.

A DEVELOPER'S TOOL for the tests of a book made in place (a0.4.2, TO-DO §8.40) -- not a page,
not part of anybody's use of Parseh, and not a model.  A real agent cannot be run inside a
test; this does, deterministically, what the instructions in the book's AGENTS.md tell an
agent to do, by calling Parseh's own tools with Parseh's own Python, by their full paths:

    python3 tests/making_agent.py original <model book> <out.txt>
        the two-paragraph original a run is made from: the text of the first two paragraphs of
        a fixture edition (tests/fixtures/books/<folder>/mini-xx), so that every language of the
        registry has one
    python3 tests/making_agent.py step <book folder> <model book>
        the next stage, and stop -- so that a browser test can look at the book between two
    python3 tests/making_agent.py run <book folder> <model book> [--pause SECONDS]
        every stage in a row, with a pause between them
    python3 tests/making_agent.py scratch <dir>
        a copy of this checkout as a scratch install (its own books/, config/, everything the
        server writes), so that a real server can be driven without a byte of the owner's touched
    python3 tests/making_agent.py serve <scratch dir> <port> [--phone]
        that install's server, plain http on this computer, with the file manager stood in for
        by a line in <scratch>/opened.txt; --phone makes every request come from a phone let in
        over the Wi-Fi (the address is judged the Wi-Fi's), which is how the doors that are the
        computer's alone are driven from a device that is not

THE STAGES, in the order an agent does them, each a rest point the panel can be looked at in:

    source     the original recovered into source/clean.txt and source/paras/ (a paragraph a chapter,
               so that "chapters still to come" has something to say)
    chapters   lib/chapter_src.py, the chapter table written into NOTES.md and making.json
    batch N    one paragraph: ASKS.md read first; annot/chN_p00.json made from the MODEL's chunks
               (the scripted part -- a real agent writes them); lib/check_batch.py, merge_batch.py,
               normalize_batch.py and assemble.py, which must say ALL PARAGRAPHS CLEAN; \\input{chN.tex}
               added to main.tex; making.json and NOTES.md kept
    final      lib/verify_book.py, and the record says every batch is in

WHAT IT UNDERSTANDS IN ASKS.md, because it has to do something checkable with an ask: one that says
"capitals" makes the meanings of every later batch capitals, one that says "lower case" puts them back;
every ask it reads is written in NOTES.md with what it did about it, and an ask about a chunk is noted and
left, as a real agent leaves what it would have to judge.  It reads ASKS.md again before EVERY batch and
keeps in making.json how many entries it has read.

It writes only inside the book's folder, keeps `state`, `parseh` and `started` of making.json as they
were, and never runs the full build.
"""
import argparse
import datetime
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(HERE)
for folder in ("lib", "youtube/lib"):
    if os.path.join(REPO, folder) not in sys.path:
        sys.path.insert(0, os.path.join(REPO, folder))

STAGES = ("source", "chapters", "batch", "final")


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- what the instructions say
def instructions(book):
    """The full paths AGENTS.md gives -- Parseh's Python and Parseh's lib/ -- as a real agent reads
    them; the checkout's own where the file names none that exists."""
    text = ""
    try:
        with io.open(os.path.join(book, "AGENTS.md"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        pass
    ticked = re.findall(r"`([^`\n]+)`", text)
    python = next((t for t in ticked if re.search(r"python3?(\.exe)?$", t) and os.path.isfile(t)), None)
    lib = next((t for t in ticked if re.search(r"[/\\]lib$", t) and os.path.isdir(t)), None)
    return (python or os.environ.get("PARSEH_PYTHON") or sys.executable), (lib or os.path.join(REPO, "lib"))


def tool(book, name, *args, ok=(0,)):
    python, lib = instructions(book)
    cmd = [python, os.path.join(lib, name)] + [str(a) for a in args]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=book)
    out = (r.stdout + r.stderr).strip()
    if r.returncode not in ok:
        raise SystemExit("%s failed (%d):\n%s" % (name, r.returncode, out))
    return out


# ---------------------------------------------------------------- the model, and the original
def model_paragraphs(model, count=2):
    """The first `count` paragraphs of a fixture edition as (text, [sentences of chunks]) -- the
    text is exactly what the chunks' fa add up to, the way lib/assemble.py compares it."""
    import books as booklib
    import texparse
    b = booklib.Book(model)
    out = []
    for para in texparse.parse_book(b.main, b.lang)[0].paragraphs[:count]:
        sents = []
        for s in para.subs:
            chunks = []
            for c in s.chunks:
                d = {"fa": c.fa, "tr": c.tr, "voc": c.voc, "en": c.en}
                if getattr(c, "kana", ""):
                    d["kana"] = c.kana
                if getattr(c, "wordline", ""):
                    d["words"] = c.wordline
                chunks.append(d)
            sents.append(chunks)
        text = (b.lang.word_sep or "").join(c["fa"] for chunks in sents for c in chunks)
        out.append((text, sents))
    if len(out) < count:
        raise SystemExit("%s has fewer than %d paragraphs" % (model, count))
    return out


def write_original(model, out):
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n\n".join(t for t, _s in model_paragraphs(model)) + "\n")
    return out


# ---------------------------------------------------------------- the record
def read_json(path, default):
    try:
        with io.open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def keep(book, **fields):
    """making.json as the instructions say to keep it: what Parseh wrote is left alone, and the
    file is replaced whole, never half written."""
    path = os.path.join(book, "making.json")
    doc = read_json(path, {})
    doc.update(fields)
    doc["updated"] = now()
    tmp = path + ".agent"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)
    return doc


def note(book, line):
    with io.open(os.path.join(book, "NOTES.md"), "a", encoding="utf-8", newline="\n") as f:
        f.write(line.rstrip("\n") + "\n")


def entries(book):
    """ASKS.md as its entries -> [(the heading, the text)]."""
    try:
        with io.open(os.path.join(book, "ASKS.md"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return []
    out = []
    for part in re.split(r"(?m)^(?=## )", text):
        if part.startswith("## "):
            head, _, body = part.partition("\n")
            out.append((head[3:].strip(), body.strip()))
    return out


def read_asks(book, upto):
    """The asks written since the last time, done as far as a script can -> the case the meanings
    are now written in ("upper" or "")."""
    doc = read_json(os.path.join(book, "making.json"), {})
    seen = int(doc.get("asks_read", 0))
    case = doc.get("meanings", "")
    got = entries(book)
    for head, body in got[seen:]:
        if "finished" in head:
            raise SystemExit("ASKS.md says the person finished this book: stopping")
        low = body.lower()
        if "about a chunk" in head:
            note(book, "- ASKS.md, %s: %s -- an ask about one chunk: noted, and left for a person to judge."
                 % (head, " ".join(body.split())[:160]))
        elif "capitals" in low or "upper case" in low:
            case = "upper"
            note(book, "- ASKS.md, %s: %s -- done from batch %d on: the meanings are written in capitals."
                 % (head, " ".join(body.split())[:160], upto))
        elif "lower case" in low:
            case = ""
            note(book, "- ASKS.md, %s: %s -- done from batch %d on: the meanings are in lower case again."
                 % (head, " ".join(body.split())[:160], upto))
        else:
            note(book, "- ASKS.md, %s: %s -- read; nothing a script can do about it." % (head, " ".join(body.split())[:160]))
    keep(book, asks_read=len(got), meanings=case)
    return case


# ---------------------------------------------------------------- the stages
def find_original(book):
    files = sorted(glob.glob(os.path.join(book, "original", "*")))
    if not files:
        raise SystemExit("no original in %s/original/" % book)
    return files[0]


def next_stage(book):
    doc = read_json(os.path.join(book, "making.json"), {})
    if doc.get("state") == "finished":
        return "finished"
    stage = doc.get("stage", "folder")
    if stage in ("folder", ""):
        return "source"
    if stage == "source":
        return "chapters"
    b = doc.get("batches") or {}
    if stage in ("chapters", "batch") and int(b.get("done", 0)) < int(b.get("of", 0)):
        return "batch"
    return "final" if stage != "done" else "done"


def do_source(book):
    text = io.open(find_original(book), encoding="utf-8").read()
    paras = [" ".join(p.split()) for p in re.split(r"\n\s*\n", text) if p.strip()]
    os.makedirs(os.path.join(book, "source", "paras"), exist_ok=True)
    with io.open(os.path.join(book, "source", "clean.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(paras) + "\n")
    for i, p in enumerate(paras):
        # a paragraph a chapter: a small original, and a book that can be seen growing chapter by chapter
        with io.open(os.path.join(book, "source", "paras", "ch%d_p00.txt" % (i + 1)), "w",
                     encoding="utf-8", newline="\n") as f:
            f.write(p + "\n")
    note(book, "\n## 1. The source\n\nRecovered from `%s`: %d paragraphs, one to a chapter."
         % (os.path.relpath(find_original(book), book).replace(os.sep, "/"), len(paras)))
    keep(book, stage="source", on="the original is recovered: %d paragraphs" % len(paras))
    return "source recovered: %d paragraphs" % len(paras)


def do_chapters(book):
    n = len(glob.glob(os.path.join(book, "source", "paras", "ch*_p00.txt")))
    tool(book, "chapter_src.py", "--book", book, "--all")
    table = [{"chapter": i + 1, "paragraphs": 1} for i in range(n)]
    note(book, "\n## 2. The chapters\n\n| chapter | paragraphs |\n|---|---|\n" +
         "\n".join("| %d | 1 |" % (i + 1) for i in range(n)))
    keep(book, stage="chapters", chapters=table, batches={"done": 0, "of": n},
         on="the chapter table is written: %d chapters" % n)
    return "chapter table: %d chapters" % n


def input_line(book, chapter_file):
    """\\input{chN.tex} into main.tex, before \\end{document}, the file replaced whole."""
    path = os.path.join(book, "main.tex")
    text = io.open(path, encoding="utf-8").read()
    line = "\\input{%s}" % chapter_file
    # the skeleton's own comment says `% \input{ch1.tex}`, which a plain search for the line would
    # take for the line: only a line that is not a comment counts
    if any(l.strip() == line for l in text.split("\n")):
        return
    text = text.replace("\\end{document}", line + "\n\n\\end{document}") if "\\end{document}" in text else text + line + "\n"
    tmp = path + ".agent"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)


def do_batch(book, model):
    doc = read_json(os.path.join(book, "making.json"), {})
    b = doc.get("batches") or {}
    k = int(b.get("done", 0)) + 1
    of = int(b.get("of", 0))
    case = read_asks(book, k)
    text, sents = model_paragraphs(model, of)[k - 1]
    want = " ".join(io.open(os.path.join(book, "source", "paras", "ch%d_p00.txt" % k), encoding="utf-8").read().split())
    if " ".join(text.split()) != want:
        raise SystemExit("the model's paragraph %d is not the original's" % k)
    ann = {"idx": 0, "ch": k, "ann": {"sentences": [
        {"chunks": [dict(c, en=c["en"].upper() if case == "upper" else c["en"]) for c in chunks]}
        for chunks in sents]}}
    annot = os.path.join(book, "annot")
    os.makedirs(annot, exist_ok=True)
    para = os.path.join(annot, "ch%d_p00.json" % k)
    with io.open(para, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ann, f, ensure_ascii=False, indent=1)
    checked = tool(book, "check_batch.py", para, "--book", book)
    batch = os.path.join(annot, "ch%d_batchA.json" % k)
    tool(book, "merge_batch.py", "--book", book, batch, "-", para)
    norm = os.path.join(annot, "ch%d_batchA.norm.json" % k)
    tool(book, "normalize_batch.py", "--book", book, batch, norm)
    label = str(k)
    assembled = tool(book, "assemble.py", "--book", book, norm,
                     os.path.join(book, "source", "src_ch%d.json" % k), label,
                     os.path.join(book, "ch%d.tex" % k))
    if "ALL PARAGRAPHS CLEAN" not in assembled:
        raise SystemExit("assemble.py did not end clean:\n" + assembled)
    input_line(book, "ch%d.tex" % k)
    errors = re.search(r"(\d+) errors?", checked)
    note(book, "\n## Batch %d of %d\n\nChapter %d, one paragraph, %d chunks; check_batch %s; assemble: ALL PARAGRAPHS CLEAN%s."
         % (k, of, k, sum(len(c) for c in sents), "%s error(s)" % errors.group(1) if errors else "clean",
            "; meanings in capitals, as asked" if case == "upper" else ""))
    keep(book, stage="batch", batches={"done": k, "of": of},
         on=("chapter %d is in; next: chapter %d" % (k, k + 1)) if k < of else "the last chapter is in",
         checks={"check_batch": "%s errors" % (errors.group(1) if errors else "0"),
                 "assemble": "ALL PARAGRAPHS CLEAN"})
    return "batch %d of %d: chapter %d assembled" % (k, of, k)


def do_final(book):
    out = tool(book, "verify_book.py", "--book", book)
    checks = read_json(os.path.join(book, "making.json"), {}).get("checks") or {}
    checks["verify_book"] = "clean"
    note(book, "\n## Done\n\nverify_book: every paragraph reproduces its source. Open questions: none.")
    keep(book, stage="done", checks=checks, on="every batch is in and verify_book is clean; ready to finish")
    return "final: " + out.splitlines()[-1].strip()


def step(book, model):
    which = next_stage(book)
    if which == "finished":
        return "finished: the person ended the making; nothing more to do"
    if which == "done":
        return "already done"
    return {"source": do_source, "chapters": do_chapters, "batch": lambda b: do_batch(b, model),
            "final": do_final}[which](book)


def run(book, model, pause):
    while True:
        said = step(book, model)
        print(said, flush=True)
        if said.startswith(("finished", "already done", "final")):
            return
        time.sleep(pause)


# ---------------------------------------------------------------- the scratch install
def scratch_install(dest, src=REPO):
    """A copy of this checkout that is a whole Parseh of its own: everything a server writes
    (books/, config/, the studio's library ...) is under `dest`, because a server takes its root
    from where serve.py lies.  The owner's tree is never in it, and never touched."""
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    skip = shutil.ignore_patterns("__pycache__", "*.pyc", "reader", "*.pdf", "*.aux", "*.log", "*.toc")
    for name in ("lib", "youtube", "markdown", "docs", "texmf"):
        if os.path.isdir(os.path.join(src, name)):
            shutil.copytree(os.path.join(src, name), os.path.join(dest, name), ignore=skip)
    for name in ("serve.py", "build.sh", "VERSION", "environment.yml", "serve.sh"):
        if os.path.exists(os.path.join(src, name)):
            shutil.copy2(os.path.join(src, name), os.path.join(dest, name))
    for name in ("books", "config", "dict", "exercises", "clips", "corpus", "mt", "components"):
        os.makedirs(os.path.join(dest, name), exist_ok=True)
    for name in ("youtube/videos", "youtube/anki", "markdown/library"):
        os.makedirs(os.path.join(dest, *name.split("/")), exist_ok=True)
    return dest


def serve(scratch, port, phone=False):
    """That install's server in this process, with the file manager stood in for."""
    scratch = os.path.realpath(scratch)
    os.chdir(scratch)
    for folder in ("lib", "youtube/lib", "markdown/app", "markdown/exlex", "."):
        sys.path.insert(0, os.path.join(scratch, folder))
    import making
    if phone:
        # the three things tests/test_settings_risk.py's as_phone says: the address is the
        # Wi-Fi's, its door is open, and the device has been let in with a code
        import network
        network.where = lambda ip, doc=None: network.LAN
        network.may_connect = lambda ip, doc=None: True
        network.let_in = lambda *a, **k: True

    def opened(path):
        with io.open(os.path.join(scratch, "opened.txt"), "a", encoding="utf-8") as f:
            f.write(path + "\n")
        return None
    making.open_folder = opened
    import serve as server
    sys.argv = ["serve.py", "--http", "--local", str(port)]
    server.main()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("original")
    p.add_argument("model")
    p.add_argument("out")
    p = sub.add_parser("step")
    p.add_argument("book")
    p.add_argument("model")
    p = sub.add_parser("run")
    p.add_argument("book")
    p.add_argument("model")
    p.add_argument("--pause", type=float, default=1.0)
    p = sub.add_parser("scratch")
    p.add_argument("dest")
    p = sub.add_parser("serve")
    p.add_argument("scratch")
    p.add_argument("port", type=int)
    p.add_argument("--phone", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "original":
        print(write_original(a.model, a.out))
    elif a.cmd == "step":
        print(step(os.path.realpath(a.book), os.path.realpath(a.model)))
    elif a.cmd == "run":
        run(os.path.realpath(a.book), os.path.realpath(a.model), a.pause)
    elif a.cmd == "scratch":
        print(scratch_install(a.dest))
    else:
        serve(a.scratch, a.port, a.phone)
    return 0


if __name__ == "__main__":
    sys.exit(main())
