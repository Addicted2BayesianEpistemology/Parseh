#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""A book made by an agent, in place: its folder, its record, its asks, its end.

    making.make(fields, original, options=None, into=None)
                                    the book's folder, written into books/ -> {"dir", "path", ...}
    making.instructions_text(fields, options=None)
                                    what AGENTS.md would say, before any folder is made
    making.write_instructions(book_dir, facts, options)
                                    THE SEAM: AGENTS.md and CLAUDE.md into the folder
    making.is_making(book_dir)      True while an agent may still be writing the .tex
    making.describe(book_dir)       everything the making panel shows
    making.ask(book_dir, line, chunk=None)
                                    one dated entry more in ASKS.md
    making.finish_start(book_dir)   verify_book and the full build, as a job the page polls
    making.open_folder(path)        the system's file manager, on the folder

PARSEH NEVER STARTS AN AGENT (TO-DO §18, the owner, 2026-09-28).  It prepares a
folder under books/, shows where it is, and the person opens whatever agent they
use on it.  The agent works on the REAL tree -- Parseh's own lib/*.py, run with
Parseh's own Python -- and writes only inside the book's folder, so the book is
in the library from the first minute and can be looked at while it grows.

WHAT THE FOLDER HOLDS beside the book's own files (book.json, main.tex, source/,
annot/, the chapters):

    original/<file>   the source text the book is made from -- in the book's own
                      folder and not in others/, which a release neither ships
                      nor keeps (lib/release.py CONTENT), so it travels with the
                      book (lib/bundle.py)
    NOTES.md          the book's journal: the source's oddities, the decisions
                      taken, what is open.  Kept by whoever makes the book
    ASKS.md           what the person asks of the agent, dated entries, written
                      from the making panel and from the reader's chunk sheet.
                      The agent reads it again before every batch
    making.json       the record of the making, below
    AGENTS.md         the instructions, in words any agent can be told to read
    CLAUDE.md         one line pointing at AGENTS.md, which Claude Code reads
                      by itself

making.json is ONE small object that Parseh and the agent keep between them.
Every field is optional to read -- an agent's file may be half written, and the
panel says so instead of stopping:

    state     "making", or "finished".  PARSEH'S ALONE: written when the folder is
              made and by Finish (finish_start), never by the agent.  Anything but
              "finished" means the book is still being made
    parseh    the version of Parseh the folder was made under; the panel says
              "Parseh was updated during the making" when this Parseh differs
    started   when the folder was made (UTC, 2026-09-29T14:00:12Z)
    finished  when Finish ended the making
    updated   when the AGENT last wrote the file: it writes it every time it
              finishes something
    stage     the agent's: "source" (the original recovered), "chapters" (the
              chapter table written), "batch", "done" (every batch is in)
    on        the agent's: one line, what it is on now
    chapters  the agent's chapter table: [{"chapter": 1, "paragraphs": 24}, ...]
    batches   the agent's: {"done": 3, "of": 12}
    checks    the agent's: what the tools last said, {"check_batch": "0 errors",
              "assemble": "ALL PARAGRAPHS CLEAN", "verify_book": "clean"}

WHILE A BOOK IS BEING MADE its reader does not edit (serve.py refuses LOCKED
doors, lib/making.js says why): the pipeline's truth is annot/*.json and the
.tex is assembled from it, so a hand edit would be erased by the agent's next
assembly.  Finish ends that: the .tex is the truth from then on, and annot/
stays as the record of how it was made.

Standard library only: the server imports this.
"""
import calendar
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

LIB = os.path.dirname(os.path.realpath(__file__))
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import books as booklib                                        # noqa: E402
import languages                                               # noqa: E402
import promptkit                                               # noqa: E402  the meaning rule the gloss prompts carry
import version                                                 # noqa: E402

MAKING = "making.json"
ASKS = "ASKS.md"
NOTES = "NOTES.md"
AGENTS = "AGENTS.md"
CLAUDE = "CLAUDE.md"
ORIGINAL = "original"
# what the tools can recover the text of a book from: a PDF with a text layer,
# an epub, a plain text file.  It is also the allowlist of what the folder's
# original/ may hold when a bundle carries it (lib/bundle.py)
ORIGINAL_EXTS = (".pdf", ".epub", ".txt")
BATCH = 10                                  # paragraphs to a batch (docs/new-book-prompt.md)

# THE SHAPE OF annot/*.json, as a number (lib/version.py FORMATS): the annotation
# JSON the agent writes a paragraph and a batch at a time and lib/assemble.py
# builds the chapters from -- {"idx", "ch", "ann": {"sentences": [{"chunks": [...]}]}},
# a chunk holding fa, tr, voc, en and, for a language with a reading or words,
# kana and words (lib/check_batch.py's docstring).  It rides in a book's bundle
# from a0.4.2 (lib/bundle.py), so an older Parseh must be told it may not read it.
# RAISE IT when the shape changes so that the Parseh before this one would read
# what is written now wrong.
ANNOT_FORMAT = 1

# THE DOORS OF A BOOK'S READER THAT WRITE ITS .tex OR ITS TITLE PAGE, shut while
# the agent makes it (serve.py's _books_post asks is_making before any of them).
# A hand edit would be erased by the next assembly, and one that lands while the
# agent is appending a batch to main.tex could lose that line.  The passes, the
# clouds, the dictionary, the narration and the builds are not here: none of them
# writes what the agent writes.
LOCKED = ("__edit/chunk", "__edit/meta", "__divide/chunk", "__struct/section",
          "__struct/chapter", "__region/apply", "__reading/free")
LOCK_SAID = ("This book is being made by an agent. It writes the book's .tex from its own "
             "files (annot/), so whatever is changed here would be erased by its next batch: "
             "editing is off until the making is finished. To change something, ask -- the "
             "making panel has a box for it, and the chunk sheet has \u201cask about this "
             "chunk\u201d.")

# one writer at a time to ASKS.md: two devices asking together must not
# interleave their entries
_ASKS_LOCK = threading.Lock()

FIELD_MAX = 300                             # what the panel keeps of an agent's one-line fields
ASK_MAX = 4000
NOTES_TAIL = 2500                           # characters of NOTES.md the panel shows
TEX_SPECIAL = re.compile(r"[\\{}$%&#_^~]")


# ------------------------------------------------------------------ time
def _iso(t=None):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() if t is None else t))


def _epoch(v):
    """A moment as making.json spells it -> seconds since 1970, or None.  The
    agent writes ISO 8601, in UTC unless it says another zone; a number is taken
    as seconds, so an agent that writes `time.time()` is read too."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if not isinstance(v, str):
        return None
    m = re.fullmatch(r"(\d{4})-(\d\d)-(\d\d)[T ](\d\d):(\d\d)(?::(\d\d))?(?:\.\d+)?(Z|[+-]\d\d:?\d\d)?",
                     v.strip())
    if not m:
        return None
    y, mo, d, h, mi, s = (int(g or 0) for g in m.groups()[:6])
    zone = m.group(7)
    try:
        t = calendar.timegm((y, mo, d, h, mi, s, 0, 0, 0))
    except (ValueError, OverflowError):
        return None
    if zone and zone != "Z":
        digits = zone[1:].replace(":", "")
        t -= (1 if zone[0] == "+" else -1) * (int(digits[:2]) * 3600 + int(digits[2:]) * 60)
    return float(t)


# ------------------------------------------------------------------ the record
def path_of(book_dir, name):
    return os.path.join(book_dir, name)


def _write_json(path, doc):
    """A file replaced whole or not at all: the panel reads making.json while
    the agent may be writing it, and half a file is not what it should see."""
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def read(book_dir):
    """making.json as a dict -> (the dict, or None when the book has none; a
    sentence when the file is there and cannot be read).  A file that will not
    parse is still a book being made: an agent's write may be half done, and the
    lock on editing must not lift for it."""
    path = path_of(book_dir, MAKING)
    if not os.path.isfile(path):
        return None, ""
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError) as e:
        return {}, "making.json cannot be read just now (%s): the agent may be writing it" % e
    if not isinstance(doc, dict):
        return {}, "making.json is not a JSON object: the agent has to write it again"
    return doc, ""


def state(book_dir):
    """"none" (an ordinary book), "making" or "finished"."""
    doc, _bad = read(book_dir)
    if doc is None:
        return "none"
    return "finished" if doc.get("state") == "finished" else "making"


def is_making(book_dir):
    return state(book_dir) == "making"


def _int(v, default=0):
    try:
        return max(0, int(v))
    except (TypeError, ValueError, OverflowError):
        return default


def _line(v, cap=FIELD_MAX):
    return " ".join(str(v if v is not None else "").split())[:cap]


def stage_words(doc):
    """Where the making stands, in the words the panel and the card say."""
    if doc.get("state") == "finished":
        return "finished"
    stage = _line(doc.get("stage")).lower() or "folder"
    b = doc.get("batches") if isinstance(doc.get("batches"), dict) else {}
    done, of = _int(b.get("done")), _int(b.get("of"))
    if stage == "batch":
        if of and done >= of:
            return "all batches in"
        return "batch %d of %d" % (done + 1, of) if of else "batch %d" % (done + 1)
    return {"folder": "not started yet", "source": "source recovered",
            "chapters": "chapter table", "done": "all batches in"}.get(stage, stage)


def _chapter_table(doc):
    out = []
    rows = doc.get("chapters")
    for row in rows[:500] if isinstance(rows, list) else ():
        if isinstance(row, dict) and not isinstance(row.get("chapter"), bool):
            n = _int(row.get("chapter"), -1)
            if n >= 0:
                out.append({"chapter": n, "paragraphs": _int(row.get("paragraphs"))})
        elif isinstance(row, int) and not isinstance(row, bool) and row >= 0:
            out.append({"chapter": row, "paragraphs": 0})
    return out


# ------------------------------------------------------------------ chapters and drafts
def chapter_inputs(book_dir):
    """The chapter files main.tex inputs, in the order it inputs them -- the one
    place chapter order is written down (lib/texparse.py reads it the same way)
    -- and that are on the disk.  A commented-out \\input is not one."""
    try:
        with open(path_of(book_dir, "main.tex"), encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return []
    out = []
    for line in text.split("\n"):
        # THE READER'S OWN RULE (lib/texparse.py parse_book), so that what this says is written is
        # what the reader shows: a line that starts with % is a comment, and the first \input on
        # a line is the one that counts
        if line.lstrip().startswith("%"):
            continue
        m = re.search(r"\\input\{([^}]+)\}", line)
        if not m or not re.match(r"ch[^\\]*$", m.group(1)):
            continue
        name = m.group(1)[:-4] if m.group(1).endswith(".tex") else m.group(1)
        if os.path.isfile(path_of(book_dir, name + ".tex")) and name not in out:
            out.append(name)
    return out


def _chapter_number(name):
    m = re.match(r"ch(\d+)", name)
    return int(m.group(1)) if m else None


def draft_state(book_dir):
    """Whether the PDF of the chapters so far can be made here, and the last
    one made.  build.sh's --draft is a shell script that typesets just the
    chapters named under a jobname of its own (frankdraft), so it can never
    touch main.pdf: where there is no sh -- Windows -- there is no draft, and
    the panel says so and offers the reader instead."""
    import bookbuild
    can, why = bookbuild.available("draft")
    names = chapter_inputs(book_dir)
    if can and not names:
        can, why = False, "there is no chapter in the book yet: nothing to typeset"
    pdf = path_of(book_dir, "frankdraft.pdf")
    made = os.path.getmtime(pdf) if os.path.isfile(pdf) else None
    newest = max((os.path.getmtime(path_of(book_dir, n + ".tex")) for n in names), default=0)
    return {"can": can, "why": why, "chapters": names,
            "pdf": "frankdraft.pdf" if made else "", "pdf_at": made,
            "pdf_old": bool(made and newest > made)}


# ------------------------------------------------------------------ what the panel shows
def _tail(path, chars):
    """The last `chars` characters of a text file, from the start of a line."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - chars * 4))
            text = f.read().decode("utf-8", "replace")
    except OSError:
        return ""
    cut = size > chars * 4 or len(text) > chars
    text = text[-chars:]
    if cut and "\n" in text:
        text = text.split("\n", 1)[1]           # what is left of the line the cut went through
    return text.strip("\n")


def _asks(book_dir):
    """How many entries ASKS.md holds, and the last of them."""
    try:
        with open(path_of(book_dir, ASKS), encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return {"count": 0, "last": ""}
    parts = re.split(r"(?m)^(?=## )", text)
    entries = [p.strip() for p in parts if p.startswith("## ")]
    return {"count": len(entries), "last": entries[-1][:ASK_MAX] if entries else ""}


def describe(book_dir):
    """What the making panel shows of a book -> a plain dict.  For a book that
    was never made this way it says so and nothing else."""
    doc, bad = read(book_dir)
    now = time.time()
    if doc is None:
        return {"ok": True, "making": False, "state": "none", "now": now}
    finished = doc.get("state") == "finished"
    inputs = chapter_inputs(book_dir)
    present = sorted({n for n in map(_chapter_number, inputs) if n is not None})
    table = _chapter_table(doc)
    wanted = sorted({row["chapter"] for row in table})
    b = doc.get("batches") if isinstance(doc.get("batches"), dict) else {}
    checks = doc.get("checks") if isinstance(doc.get("checks"), dict) else {}
    try:
        stamp = os.path.getmtime(path_of(book_dir, MAKING))
    except OSError:
        stamp = None
    # WHETHER THE READER IS OLDER THAN WHAT THE AGENT HAS WRITTEN, said by the files' own
    # times: a page built before the last batch lands is the page the person is looking at
    written = [path_of(book_dir, n) for n in [name + ".tex" for name in inputs] + ["main.tex"]]
    newest = max((os.path.getmtime(p) for p in written if os.path.isfile(p)), default=0)
    reader = os.path.join(book_dir, "reader", "index.html")
    built = os.path.getmtime(reader) if os.path.isfile(reader) else None
    ran_under = _line(doc.get("parseh"), 40)
    return {
        "ok": True, "making": not finished, "state": "finished" if finished else "making",
        "stage": _line(doc.get("stage")).lower() or "folder", "words": stage_words(doc),
        "on": _line(doc.get("on")), "batches": {"done": _int(b.get("done")), "of": _int(b.get("of"))},
        "chapters": table, "present": present,
        "to_come": [n for n in wanted if n not in present],
        "stale": bool(newest and (built is None or newest > built)),
        "checks": {_line(k, 40): _line(v) for k, v in list(checks.items())[:12]},
        "started": _epoch(doc.get("started")),
        "updated": _epoch(doc.get("updated")) or stamp,
        "finished_at": _epoch(doc.get("finished")),
        "parseh": ran_under, "parseh_now": version.VERSION,
        "updated_by_parseh": bool(ran_under and ran_under != version.VERSION),
        "notes": _tail(path_of(book_dir, NOTES), NOTES_TAIL), "asks": _asks(book_dir),
        "draft": draft_state(book_dir), "broken": bad, "now": now}


# ------------------------------------------------------------------ steering
def _clean_text(text, cap):
    text = str(text if text is not None else "").replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(c for c in text if c == "\n" or c == "\t" or ord(c) >= 32)
    return text.strip()[:cap]


def ask(book_dir, line, chunk=None, when=None):
    """One dated entry more in ASKS.md -> {"ok", "at", "count"}.  `chunk`, from
    the reader's chunk sheet, is {"address": "chapter 1, paragraph 2, ...",
    "text": "the chunk as it stands"}: the remark is anchored where it was seen.

    A finished book is refused: nothing reads ASKS.md any more, and an ask that
    goes nowhere is worse than being told so.  Every entry is one write, opened
    for appending, so an agent reading the file between two of them never finds
    half of one."""
    line = _clean_text(line, ASK_MAX)
    if not line:
        raise ValueError("write what to change first: there is nothing in the box")
    if state(book_dir) == "finished":
        raise ValueError("this book is finished: the agent is not reading its asks any more")
    if state(book_dir) == "none":
        raise ValueError("this book was not made by an agent, so there is nobody to ask")
    stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(when))
    if isinstance(chunk, dict) and (chunk.get("address") or chunk.get("text")):
        where = _line(chunk.get("address"), 200)
        text = " ".join(_clean_text(chunk.get("text"), 600).split())
        entry = "## %s \u2014 about a chunk\n\n%s%s\n%s\n" % (
            stamp, where + ":\n" if where else "", "> " + text + "\n" if text else "", line)
    else:
        entry = "## %s \u2014 what to change from now on\n\n%s\n" % (stamp, line)
    with _ASKS_LOCK:
        path = path_of(book_dir, ASKS)
        need_gap = os.path.isfile(path) and os.path.getsize(path) > 0
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(("\n" if need_gap else "") + entry)
    return {"ok": True, "at": stamp, "count": _asks(book_dir)["count"]}


# ------------------------------------------------------------------ the instructions (the seam)
STUB = """\
# {{TITLE_LATIN}} -- a book made with Parseh's tools

You are making a reading edition of **{{TITLE_LATIN}}**{{TITLE_NOTE}} by {{AUTHOR_LATIN}}: a book \
in {{LANG_NAME}}, glossed in {{GLOSS_NAME}}. This folder is the book. Parseh made it and does not \
start any agent: the person opened you here, watches the book grow in Parseh's library, and \
writes you asks.

## Where everything is

- The book, and the only place you write: `{{BOOK_DIR}}`
- Parseh's tools: `{{LIB}}`, the `*.py` files. Run them with the Python at `{{PYTHON}}`, by its \
full path -- no `conda`, nothing to install.
- The original text: `{{ORIGINAL}}`{{PAGES}}
- {{LANG_NAME}}'s conventions, binding for every chunk: `{{CONVENTIONS}}`
{{REFERENCE}}{{EXAMPLES}}
## The rules

1. Write only inside this folder. Read anything of Parseh's; change nothing of it.
2. Never run the full build (`build.sh <book>`): the person's page does. To look at your work, \
typeset the chapters so far: `sh {{ROOT}}/build.sh {{BOOK_REL}} --draft ch1 ch1b` writes \
`frankdraft.pdf` beside the book, never `main.pdf`.
3. `annot/*.json` is the truth; the `.tex` chapters are assembled from it by `assemble.py` and \
never edited by hand.
4. Before EVERY batch, read `ASKS.md` again. Do what an entry asks from the next batch on, write \
in `NOTES.md` what you changed because of it, and ask the person in your own chat if an ask goes \
against the method.
5. Keep `NOTES.md`: the source's oddities, the decisions, what is open.
6. Keep `making.json` (below) every time you finish something. Never change its `state`, \
`parseh` or `started`. When `state` says `finished`, stop: the book is the person's now.

## `making.json`

`stage`: `source` (the original recovered), `chapters` (the chapter table written), `batch`, \
`done` (every batch is in). `on`: one line, what you are on. `chapters`: \
`[{"chapter": 1, "paragraphs": 24}, ...]`. `batches`: `{"done": 3, "of": 12}`. `checks`: what \
the tools last said, e.g. `{"check_batch": "0 errors", "assemble": "ALL PARAGRAPHS CLEAN", \
"verify_book": "clean"}`. `updated`: the time you wrote it, UTC (`2026-09-29T14:20:01Z`).

{{MEANING_RULE}}

## The work, {{BATCH}} paragraphs at a time

1. Recover the text into `source/clean.txt` (one paragraph a line) and `source/paras/chN_pNN.txt` \
-- `extract_pdf.py` for a PDF with a text layer, your own care for an epub or a text file -- and \
run `chapter_src.py --book {{BOOK_DIR}} --all`. Write the chapter table into `NOTES.md` and show \
it to the person before annotating anything.
2. For each batch: one `annot/chN_pNN.json` a paragraph. {{WORDS}}Check each with \
`check_batch.py <json> --book {{BOOK_DIR}}` until it says 0 errors; then `merge_batch.py`, \
`normalize_batch.py` and `assemble.py` (it must end `ALL PARAGRAPHS CLEAN`) make `chNx.tex`, \
which you `\\input` in `main.tex`, in order.
3. At the end: `verify_book.py --book {{BOOK_DIR}}` must be clean. Then tell the person; they \
press Finish in Parseh.
"""

_TOKEN = re.compile(r"\{\{([A-Z_]+)\}\}")


def _fill(text, values):
    return _TOKEN.sub(lambda m: str(values.get(m.group(1), m.group(0))), text)


def _meaning_rule(book):
    """docs/meaning-rule.md in the words of this book's language and gloss language: the rule
    every chunk's `en` follows, the same text the gloss prompts carry."""
    with open(os.path.join(os.path.dirname(LIB), "docs", "meaning-rule.md"), encoding="utf-8") as f:
        text = promptkit.blocks(f.read(), {"video": False})
    return (text.replace("{{LANGUAGE}}", book["language_name"])
            .replace("{{GLOSS_LANGUAGE}}", book["gloss_name"]).strip() + "\n")


def instructions_text(facts, options=None):
    """What AGENTS.md says for these facts -> str.  This is the text Lane H's
    real instructions replace; the seam is write_instructions, which calls it."""
    book, orig = facts["book"], facts["original"]
    options = options or {}
    ref = facts.get("reference")
    ex = facts.get("examples") or []
    pages = ", pages %d-%d of it (counted from 0)" % tuple(orig["pages"]) if orig.get("pages") else ""
    lang = book["language"]
    latin = book["title_latin"] or book["slug"]
    # A LANGUAGE THAT DIVIDES A CHUNK INTO WORDS (Japanese, Chinese: the registry's `words`) has the
    # machine start the division and the annotator correct it -- the step the page's old recipe carried
    # in its prompt, and the one an agent cannot know of without being told
    words = ("For %s every chunk also has `words`, its division into words: start it from the machine's "
             "with `%s %s --lang %s --json <the paragraph's JSON>`, then correct it against the `## Words` "
             "section of the conventions. " % (book["language_name"], facts["python"],
                                              os.path.join(facts["lib"], "fill_words.py"), lang)
             ) if languages.get(lang).words else ""
    values = {
        "WORDS": words,
        "MEANING_RULE": _meaning_rule(book),
        "TITLE_NOTE": " (%s)" % book["title"] if book["title"] and book["title"] != latin else "",
        "TITLE_LATIN": latin,
        "AUTHOR_LATIN": book["author_latin"] or book["author"] or "an unnamed author",
        "LANG_NAME": book["language_name"], "GLOSS_NAME": book["gloss_name"],
        "BOOK_DIR": book["dir"], "BOOK_REL": book["rel"], "ROOT": facts["root"],
        "LIB": facts["lib"], "PYTHON": facts["python"], "BATCH": facts.get("batch", BATCH),
        "ORIGINAL": os.path.join(book["dir"], *orig["file"].split("/")), "PAGES": pages,
        "CONVENTIONS": os.path.join(facts["root"], "docs", "lang", lang + ".md"),
        "REFERENCE": ("- A finished edition to learn the method from -- read it, change nothing: "
                      "`%s`\n" % ref["path"]) if ref else "",
        "EXAMPLES": ("- The person's finished books in %s, as examples only -- read them, change "
                     "nothing: `%s` (%s)\n" % (book["language_name"], facts["examples_dir"],
                                               ", ".join(e["rel"] for e in ex[:12]))) if ex else "",
    }
    return _fill(STUB, values)


CLAUDE_LINE = "Read AGENTS.md in this folder before anything else, and follow it.\n"


def write_instructions(book_dir, facts, options=None):
    """THE SEAM for the agent's instructions -> [the relative paths written].

    `book_dir` is where to write, which may not be the folder's final name yet
    (make() writes into a staging directory and renames it); everything the text
    says about places comes from `facts`.  `facts` is what make() knows -- see
    facts_for -- and `options` what the page chose ("reference", "examples").
    Written again at any time, it replaces only its own files.  Parseh writes no
    tool's permission file: the agent and its permissions are the person's."""
    with open(path_of(book_dir, AGENTS), "w", encoding="utf-8", newline="\n") as f:
        f.write(instructions_text(facts, options))
    with open(path_of(book_dir, CLAUDE), "w", encoding="utf-8", newline="\n") as f:
        f.write(CLAUDE_LINE)
    return [AGENTS, CLAUDE]


# ------------------------------------------------------------------ making the folder
def _shelf_book(rel, shelf):
    """A book on the shelf by its address (persian/farsi-shakar-ast) -> its
    directory, or a refusal.  Checked as serve.py's book_dir checks a URL: no
    climb out of books/, and a book.json there."""
    parts = str(rel or "").strip("/").split("/")
    if not (1 <= len(parts) <= 2) or any(p in ("", ".", "..") or p.startswith(".") for p in parts):
        raise ValueError("%r is not a book on the shelf" % rel)
    d = os.path.join(shelf, *parts)
    if not os.path.isfile(os.path.join(d, "book.json")):
        raise ValueError("there is no book called %r on the shelf to learn from" % rel)
    return d


def _identity(fields, need=True):
    """The book's facts, checked -> a dict.  `need` is False for the preview of
    the instructions, which is asked for while the form is still being filled."""
    import draft                                        # noqa: E402  lazily: it pulls the video door in
    fields = fields or {}
    L = draft._lang(fields.get("lang"))
    G = draft._gloss(fields.get("gloss"))
    title = _line(fields.get("title"), 200)
    if need and not title:
        raise ValueError("a book needs a title in %s" % L.name)
    got = {"title": title}
    for k in ("title_latin", "title_en", "author", "author_latin", "year", "blurb"):
        got[k] = _line(fields.get(k), 400)
    # what goes into main.tex is TeX, and one of these characters ends the book
    # there as surely as it would in a paragraph: refused here, in words, and not
    # found days later in a LaTeX log
    for k, said in (("title", "the title"), ("title_latin", "the transliterated title"),
                    ("author", "the author"), ("author_latin", "the transliterated author")):
        bad = TEX_SPECIAL.search(got[k])
        if bad:
            raise ValueError("%s cannot hold %s: TeX reads it as an instruction. Write it out in "
                             "words." % (said, "a backslash" if bad.group() == "\\" else
                                         "the character " + bad.group()))
    upper = _line(fields.get("title_latin_upper"), 400)
    if upper and TEX_SPECIAL.search(upper):
        upper = ""
    wanted = _line(fields.get("slug"), 80) or got["title_latin"] or title
    slug = draft.slugify(wanted)
    if need and not slug:
        raise ValueError("no directory name could be made from %r: give a slug of ascii letters, "
                         "digits and hyphens (a title written in its own script leaves none "
                         "behind)" % wanted)
    got.update(slug=slug or "new-book", lang=L, gloss=G,
               upper=upper or (got["title_latin"] or slug or "new-book").upper())
    return got


def _pages(v):
    m = re.fullmatch(r"\s*(\d+)\s*[-\u2013]\s*(\d+)\s*", str(v or ""))
    if not v or not str(v).strip():
        return None
    if not m or int(m.group(1)) > int(m.group(2)):
        raise ValueError("the page range is two numbers, the first not after the last: 13-21")
    return [int(m.group(1)), int(m.group(2))]


def _original_name(name):
    base = os.path.basename(str(name or "").replace("\\", "/")).strip()
    stem, ext = os.path.splitext(base)
    ext = ext.lower()
    if ext not in ORIGINAL_EXTS:
        raise ValueError("the original has to be a PDF with a text layer, an epub or a plain text "
                         "file (%s): %r is none of them" % (", ".join(ORIGINAL_EXTS), base or "no file"))
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-.")[:60] or "original"
    return stem + ext


def _looks_like(ext, head):
    if ext == ".pdf":
        return head.lstrip().startswith(b"%PDF-")
    if ext == ".epub":
        return head.startswith(b"PK")
    return b"\x00" not in head[:4096]


def facts_for(identity, orig_file, pages, options, dest, shelf=None):
    """Everything the instructions may need, as one plain dict.  `dest` is the
    folder's final place; the Python is the environment's (runtime.find_env) and
    its full path, so the agent needs no conda of its own.  A reference is read
    where it lies and never copied; the person's other books are named only when
    the page's box says so, and only the ones in this book's language."""
    import runtime
    shelf = shelf or booklib.BOOKS_DIR
    L, G = identity["lang"], identity["gloss"]
    reference = None
    if options.get("reference"):
        rd = _shelf_book(options["reference"], shelf)
        rb = booklib.Book(rd)
        reference = {"rel": os.path.relpath(rd, shelf).replace(os.sep, "/"), "path": rd,
                     "title": rb.title_latin or rb.title, "language": rb.language,
                     "has_notes": os.path.isfile(path_of(rd, NOTES))}
    examples = []
    if options.get("examples"):
        for b in booklib.all_books(shelf, language=L.code):
            if os.path.realpath(b.dir) != os.path.realpath(dest) and not is_making(b.dir):
                examples.append({"rel": os.path.relpath(b.dir, shelf).replace(os.sep, "/"),
                                 "path": b.dir, "title": b.title_latin or b.title})
    return {
        "parseh": version.VERSION, "root": booklib.ROOT, "lib": LIB,
        "python": runtime.find_env()[1] or sys.executable, "batch": BATCH,
        "book": {"dir": dest, "rel": "books/%s/%s" % (L.folder, identity["slug"]),
                 "folder": L.folder, "slug": identity["slug"],
                 "title": identity["title"], "title_latin": identity["title_latin"],
                 "title_en": identity["title_en"], "author": identity["author"],
                 "author_latin": identity["author_latin"], "year": identity["year"],
                 "blurb": identity["blurb"], "language": L.code, "language_name": L.name,
                 "gloss": G.code, "gloss_name": G.name},
        "original": {"file": "%s/%s" % (ORIGINAL, orig_file), "pages": pages},
        "reference": reference, "examples": examples,
        "examples_dir": os.path.join(shelf, L.folder)}


def instructions_for(fields, options=None, into=None):
    """What the folder's AGENTS.md would say for what is in the form now, written
    nowhere: the page shows it, and copies it for an agent that does not read the
    file by itself.  The form may be half filled -- what is missing reads as a
    placeholder -- but a reference that is not on the shelf is still refused."""
    options = options or {}
    into = into or booklib.BOOKS_DIR
    ident = _identity(fields, need=False)
    try:
        name = _original_name(fields.get("original"))
    except ValueError:
        name = "the-book.pdf"
    try:
        pages = _pages(fields.get("pages")) if name.endswith(".pdf") else None
    except ValueError:
        pages = None
    dest = os.path.join(into, ident["lang"].folder, ident["slug"])
    return instructions_text(facts_for(ident, name, pages, options, dest, into), options)


NOTES_START = """\
# {title} -- notes

The journal of this edition: what the source needed, the decisions taken, what is open. It is
kept by whoever makes the book, and it is the first thing to read if you take over.

- Made from `{original}`{pages}, started {when}.
"""


def make(fields, original, options=None, into=None):
    """The book's folder, written whole or not at all -> {"dir", "path", "slug",
    "folder", "language", "files", "instructions"}.

    `fields` is the book's facts (the ones the add page asks, and `pages`);
    `original` is {"name": the file's name, "data": bytes} or {"name", "path"} for
    an upload spooled to disk; `options` is {"reference": "<folder>/<slug>" or "",
    "examples": bool}.  Every refusal is a ValueError with a sentence to show.

    The tree is built beside its place, in a directory with a dot in front (which
    nothing on the shelf reads as a book), and renamed into place at the end: a
    refusal, or a disk that fills, leaves nothing behind, and a book already there
    is never written over."""
    options = options or {}
    into = into or booklib.BOOKS_DIR
    ident = _identity(fields)
    name = _original_name(original.get("name"))
    # a page range is a PDF's: an epub or a text file has no pages to count
    pages = _pages(fields.get("pages")) if name.endswith(".pdf") else None
    if "data" in original:
        size, head = len(original["data"]), original["data"][:4096]
    else:
        size = os.path.getsize(original["path"])
        with open(original["path"], "rb") as f:
            head = f.read(4096)
    if not size:
        raise ValueError("the original is empty: choose the file again")
    if not _looks_like(os.path.splitext(name)[1], head):
        raise ValueError("%s does not look like %s: choose the right file" % (
            name, {"pdf": "a PDF", "epub": "an epub"}.get(name.rsplit(".", 1)[1], "a text file")))
    L = ident["lang"]
    parent = os.path.join(into, L.folder)
    dest = os.path.join(parent, ident["slug"])
    if os.path.exists(dest):
        raise ValueError("a book is already at books/%s/%s/ -- choose another slug, or move that "
                         "one out of the way" % (L.folder, ident["slug"]))
    facts = facts_for(ident, name, pages, options, dest, into)     # a reference not on the shelf is refused here, before a file is written
    import newbook                                      # noqa: E402  its skeleton is the one place the main.tex is written
    made_parent = not os.path.isdir(parent)
    os.makedirs(parent, exist_ok=True)
    stage = tempfile.mkdtemp(prefix=".making-", dir=parent)
    tree = os.path.join(stage, ident["slug"])
    try:
        os.makedirs(tree)
        for sub in (ORIGINAL, "source/paras", "annot"):
            os.makedirs(os.path.join(tree, *sub.split("/")))
        target = os.path.join(tree, ORIGINAL, name)
        if "data" in original:
            with open(target, "wb") as f:
                f.write(original["data"])
        else:
            shutil.copyfile(original["path"], target)
        meta = {"slug": ident["slug"], "language": L.code, "gloss": ident["gloss"].code,
                "title": ident["title"],
                "title_latin": ident["title_latin"] or ident["slug"], "title_en": ident["title_en"],
                "author": ident["author"], "author_latin": ident["author_latin"],
                "year": ident["year"], "blurb": ident["blurb"], "main": "main.tex",
                "audio": None, "transcript": None, "source_pdf": "%s/%s" % (ORIGINAL, name)}
        if pages:
            meta["source_pages"] = pages
        _write_json(os.path.join(tree, "book.json"), meta)
        values = {"TITLE": ident["title"], "AUTHOR": ident["author"],
                  "TITLE_LATIN": meta["title_latin"], "AUTHOR_LATIN": ident["author_latin"],
                  "TITLE_LATIN_UPPER": ident["upper"], "LANG": L.code, "LANG_NAME": L.name,
                  "GLOSS": ident["gloss"].code, "GLOSS_NAME": ident["gloss"].name,
                  "SLUG": ident["slug"]}
        with open(os.path.join(tree, "main.tex"), "w", encoding="utf-8", newline="\n") as f:
            f.write(_fill(newbook.MAIN_TEX, values) + "\n")
        with open(os.path.join(tree, NOTES), "w", encoding="utf-8", newline="\n") as f:
            f.write(NOTES_START.format(
                title=meta["title_latin"], original="%s/%s" % (ORIGINAL, name),
                pages=", pages %d-%d" % tuple(pages) if pages else "",
                when=time.strftime("%Y-%m-%d")))
        open(os.path.join(tree, ASKS), "w", encoding="utf-8").close()
        now = _iso()
        _write_json(os.path.join(tree, MAKING), {
            "state": "making", "parseh": version.VERSION, "started": now, "updated": now,
            "stage": "folder", "on": "", "chapters": [], "batches": {"done": 0, "of": 0},
            "checks": {}})
        written = write_instructions(tree, facts, options)
        try:
            os.rename(tree, dest)
        except OSError as e:
            raise ValueError("the folder could not be put in place (%s); nothing was written" % e)
    except BaseException:
        if made_parent:
            try:
                os.rmdir(parent)
            except OSError:
                pass
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return {"slug": ident["slug"], "folder": L.folder, "language": L.code,
            "dir": os.path.relpath(dest, into).replace(os.sep, "/"), "path": dest,
            "original": "%s/%s" % (ORIGINAL, name), "instructions": written,
            "files": sorted(["book.json", "main.tex", NOTES, ASKS, MAKING, "%s/%s" % (ORIGINAL, name)]
                            + written)}


# ------------------------------------------------------------------ opening the folder
def open_program(path):
    """The command that shows a folder in this system's file manager, or None."""
    if os.name == "nt":
        return ["explorer", path]
    if sys.platform == "darwin":
        return ["open", path]
    return [shutil.which("xdg-open") or "xdg-open", path]


def open_folder(path):
    """The system's file manager on `path` -> None, or a sentence saying why it
    could not be opened.  Never waited for: a file manager runs as long as the
    person keeps it open."""
    if not os.path.isdir(path):
        return "the folder is not there any more"
    try:
        subprocess.Popen(open_program(path), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=os.name != "nt")
    except OSError as e:
        return ("this computer has no file manager Parseh can start (%s): open the folder "
                "from the path above" % (e.strerror or e))
    return None


# ------------------------------------------------------------------ Finish
FINISH = {}                         # a book's directory -> its Finish job
_FINISH_LOCK = threading.Lock()


def _job_view(job):
    return {"state": job["state"], "steps": [dict(s) for s in job["steps"]], "said": job["said"],
            "started": job["started"], "finished": job["finished"], "ok": job["ok"]}


def finish_status(book_dir):
    with _FINISH_LOCK:
        job = FINISH.get(os.path.realpath(book_dir))
        return _job_view(job) if job else {"state": "idle", "steps": [], "said": "", "ok": None}


def _python():
    import runtime
    return runtime.find_env()[1] or sys.executable


def verify_words(code, out):
    """verify_book's output in words: (clean, one sentence, [the lines that say what]).
    It prints one summary line, and a line or three for every paragraph that fails."""
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    m = re.search(r"(\d+) paragraphs built, (\d+) reproduce their source exactly, (\d+) mismatched, "
                  r"(\d+) without a source", out)
    built, ok, bad, missing = (int(g) for g in m.groups()) if m else (0, 0, 0, 0)
    problems = []
    for l in lines:
        mm = re.match(r"MISMATCH chapter (\d+) paragraph (\d+) at char (\d+)", l)
        if mm:
            problems.append("chapter %s paragraph %s does not reproduce its source (it differs at "
                            "character %s)" % mm.groups())
        mm = re.match(r"NO SOURCE for chapter (\d+) paragraph (\d+)", l)
        if mm:
            problems.append("chapter %s paragraph %s has no source file in source/paras/" % mm.groups())
    if m and not built:
        return False, "there is no chapter in the book yet, so there is nothing to finish", []
    if code == 0 and m:
        return True, "every paragraph reproduces its source (%d paragraphs)" % built, []
    if not m:
        return False, "the check itself could not run: %s" % (lines[-1] if lines else "it said nothing"), []
    return (False, "%d paragraph%s do%s not reproduce %s source" % (
        bad + missing, "" if bad + missing == 1 else "s", "es" if bad + missing == 1 else "",
        "its" if bad + missing == 1 else "their"), problems[:9])


def build_words(log):
    """The first thing a failed build says was wrong, as buildWhy in lib/parseh.js
    puts it: TeX's own first error, else the line that names what failed."""
    log = [str(l).strip() for l in (log or []) if str(l).strip()]
    err = next((l for l in log if l.startswith("!")), "")
    failed = next((l for l in log if re.search(r"FAILED|could not run|no lualatex", l, re.I)), "")
    if err:
        return (re.sub(r"\s*--.*$", "", failed) + ": " if failed else "") + err
    return failed or " / ".join(log[-2:]) or "the server's log says why"


def finish_start(book_dir, runner=None, wait=1.0):
    """Check the book and build it, as a job -> (the job's view, started).

    Two steps.  verify_book proves every paragraph still reproduces its source;
    then the full build (lib/bookbuild.py, the job the page's build button
    runs -- the ONE build of a book at a time).  Both clean ends the making:
    making.json says finished, and the reader's doors edit the .tex from then on.
    Either not clean says why, in words, and leaves the book being made.

    A COMPUTER WITH NO TeX cannot build the PDF, and would never be able to
    finish.  There the second step builds the reader alone and says the PDF was
    left, which is all that machine could ever have had.

    `runner(cmd, say) -> exit status` stands in for the subprocesses, for a test."""
    key = os.path.realpath(book_dir)
    if state(book_dir) != "making":
        raise ValueError("this book is not being made" if state(book_dir) == "none"
                         else "this book is finished already")
    with _FINISH_LOCK:
        job = FINISH.get(key)
        if job and job["state"] == "running":
            return _job_view(job), False
        job = {"state": "running", "started": time.time(), "finished": None, "ok": None, "said": "",
               "steps": [{"name": "check", "state": "running", "said": "", "lines": []},
                         {"name": "build", "state": "waiting", "said": "", "lines": []}]}
        FINISH[key] = job
        view = _job_view(job)
    threading.Thread(target=_finish, args=(job, book_dir, runner, wait), daemon=True).start()
    return view, True


def _step(job, i, **kw):
    with _FINISH_LOCK:
        job["steps"][i].update(kw)


def _finish(job, book_dir, runner, wait):
    import bookbuild
    import runtime
    clean = False
    try:
        # 1. every paragraph against its source
        cmd = [_python(), os.path.join(LIB, "verify_book.py"), "--book", book_dir]
        out = []
        if runner is not None:
            code = runner(cmd, out.append)
        else:
            r = subprocess.run(cmd, cwd=booklib.ROOT, capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               env=runtime.environ_for(runtime.find_env()[0]))
            code, out = r.returncode, (r.stdout + r.stderr).splitlines()
        ok, said, lines = verify_words(code, "\n".join(out))
        _step(job, 0, state="done" if ok else "failed", said=said, lines=lines)
        # 2. the full build -- or the reader alone where TeX is not installed
        if not ok:
            _step(job, 1, state="skipped", said="not tried: the check above comes first")
        else:
            no_tex = not shutil.which("lualatex")
            way = "html" if no_tex else "pdf"
            _step(job, 1, state="running")
            while True:
                view, started = bookbuild.start(book_dir, way, runner=runner)
                if started:
                    break
                time.sleep(wait)                    # another build of this book is running: after it
            while bookbuild.status(book_dir)["state"] == "running":
                time.sleep(wait)
            built = bookbuild.status(book_dir)
            if built["state"] == "done":
                _step(job, 1, state="done", said=(
                    "the reader was built; the PDF was left, because TeX is not installed on this "
                    "computer" if no_tex else "the PDF and the reader were built"))
                clean = True
            else:
                _step(job, 1, state="failed", said="the build failed: " + build_words(built["log"]))
    except Exception as e:                              # a bug here must not leave the job running for ever
        _step(job, 1 if job["steps"][0]["state"] == "done" else 0, state="failed",
              said="%s: %s" % (type(e).__name__, e))
    if clean:
        _end_making(book_dir)
    with _FINISH_LOCK:
        job.update(ok=clean, finished=time.time(), state="done" if clean else "failed",
                   said=("finished: the .tex is the book now, and annot/ stays as the record of how "
                         "it was made" if clean else
                         "not finished: the book is still being made; put what is said above right, "
                         "then finish again"))


def _end_making(book_dir):
    """The making is over: making.json says so, the agent is told in ASKS.md (an
    agent still working reads that file before its next batch), and the library
    page is written again so that the card stops saying `being made`."""
    doc, _bad = read(book_dir)
    doc = dict(doc or {}, state="finished", finished=_iso(), updated=_iso())
    _write_json(path_of(book_dir, MAKING), doc)
    with _ASKS_LOCK:
        path = path_of(book_dir, ASKS)
        gap = "\n" if os.path.isfile(path) and os.path.getsize(path) else ""
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write("%s## %s \u2014 finished\n\nThe person finished this book from Parseh. Stop: the "
                    ".tex is the book now. Do not assemble or write anything more in this folder.\n"
                    % (gap, time.strftime("%Y-%m-%d %H:%M")))
    try:
        subprocess.run([sys.executable, os.path.join(LIB, "make_index.py")], cwd=booklib.ROOT,
                       capture_output=True, timeout=300)
    except (OSError, subprocess.SubprocessError):
        pass                                # the card catches up at the next build


if __name__ == "__main__":
    for b in booklib.all_books():
        s = state(b.dir)
        if s != "none":
            print("%-40s %-9s %s" % (b.rel_from_books(), s, stage_words(read(b.dir)[0] or {})))
