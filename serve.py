#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Parseh -- one server for the whole toolbox, over HTTPS.

    python3 serve.py                 every interface, https on port 8765
    python3 serve.py 9000            ... on another port
    python3 serve.py --host 100.x.y.z    bind one address only (e.g. Tailscale)
    python3 serve.py --local         bind 127.0.0.1 only
    python3 serve.py --http          plain http, no TLS (debugging only)
    python3 serve.py --cert          (re)make the certificate and exit

What is mounted where -- one address, one port, one process:

    /                 the hub: books, videos, studio, exercises, Anki
    /books/           the reading editions (static pages built by ./build.sh)
    /youtube/         the video player (pages assembled per request)
    /youtube/add/     paste a transcript, copy the prompt, paste the answer
    /books/add/       the recipe and the Claude Code prompt for a new edition
    /studio/          the LLM-answer studio, under a prefix
    /exercises/       decks of studio exercises, studied like Anki cards
                      (markdown/app/deckroutes.py, the store in exercises/)
    /anki/...         the card store BOTH readers write into -- shared
    /clips/...        the clip tray: recordings cut from a narration or a film or
                      recorded from a YouTube video in the tab, frames captured
                      from a video (lib/clips.py, the folder clips/); /clips/
                      itself is the page that plays and deletes them
    /lib/...          the palette, the shared script, the fonts
    /lib/langs.css    the per-language font tokens, generated from lib/languages.json
    /guide/           the guide: html-guide/'s front page and its compiled pages
                      (lib/guidebuild.py), compiled from the page's own button
    /guide.pdf        where the PDF manual was: on to /guide/, which is the manual
    /licences/        the licences: Parseh's (GPL-3.0-or-later, its text at
                      /licences/LICENSE), and those of the fonts, MathJax and
                      the data the reading help downloads (lib/notices.py)
    /__shutdown       POST: stop the server (every page has a button)

HTTPS, with a certificate this program makes itself.  Browsers hand out
screen capture (the frame button on a card) and the clipboard only on
secure origins, and localhost is the only plain-http origin they trust --
so a phone or a laptop reaching this over Tailscale needs TLS.  Nobody but
us ever connects, so a certificate nobody else vouches for is exactly
right: each browser warns ONCE about it, you accept, and that is the end of
it.  It lives in .tls/ and is minted on first start with openssl (every
address the machine has in its SAN), signed by an authority of the
machine's own that a phone can be told to trust -- which is what installing
the mobile interface as an app needs (make_cert); `--cert` mints a fresh
server certificate under the same authority.

A plain-http request that lands on the https port (an old bookmark) is
answered with a redirect to the https address, not a handshake error.

The request body is read once, up front, and every handler sees it
through rfile -- so a POST can never be left half-read on a keep-alive
connection, whichever of the three route sets answers it.  HTTP Range is
honoured on every file, which is what lets the narration be seeked.

Two kinds of noise are deliberately swallowed, because both are ordinary
here and neither is a fault: a client that goes away mid-transfer (seeking
in a 218 MB narration aborts the range request in flight, several times a
minute), and a TLS probe or an abandoned handshake.  Anything else still
prints its traceback: a real bug in a handler should not be silent.
"""
import argparse
import importlib.util
import io
import json
import mimetypes
import os
import re
import shutil
import socket
import socketserver
import ssl
import subprocess
import sys
import sqlite3
import tempfile
import threading
import time
import traceback
import unicodedata
import urllib.parse
import zipfile
from http.server import SimpleHTTPRequestHandler

NAME = "Parseh"
HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = HERE
LIB = os.path.join(ROOT, "lib")
YT = os.path.join(ROOT, "youtube")
YT_LIB = os.path.join(YT, "lib")
STUDIO = os.path.join(ROOT, "markdown")
STUDIO_APP = os.path.join(STUDIO, "app")
TLS_DIR = os.path.join(ROOT, ".tls")
DEFAULT_PORT = 8765

for _p in (LIB, YT_LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import books as booklib     # noqa: E402  where the books are
import lookup              # noqa: E402  the dictionary behind an unglossed chunk
import decomposition      # local optional component trees
import corpus             # noqa: E402  and the sentences somebody translated
import getmt              # noqa: E402  and the model that runs in the page
import lookuppage         # noqa: E402  the page that sets the dictionaries up
import languages            # noqa: E402  the registry: names, folders, the CSS tokens
import make_index           # noqa: E402  what a built reader says about itself
import mobile               # noqa: E402  the mobile interface's own pages (/m/books/)
import notices              # noqa: E402  the licences page: Parseh's, and its fonts' and data's
import newbook              # noqa: E402  the "add a book" recipe page
import anki_store           # noqa: E402  the shared card store
import ytpages              # noqa: E402  the video player's pages + Anki endpoints
import timestamp as tstamp  # noqa: E402  the aligner: its transcript parser, for the panel
import bundle              # noqa: E402  a book or a video as one file, out and back
import shelf               # noqa: E402  a whole shelf of either, backed up and put back
import texwrite            # noqa: E402  one chunk of a chapter, edited in place
import reading              # noqa: E402  what somebody decided about the text itself
import structure            # noqa: E402  a chapter's name and the sections inside it
import bookmeta             # noqa: E402  a book's title, author and the like, edited in place
import chunker            # noqa: E402  the two ways a draft may be cut
import bookbuild          # noqa: E402  a book built from a page, as a job the page polls
import activity           # noqa: E402  what the server is busy with, for every page to show
import draft               # noqa: E402  an empty book or video, to author from nothing
import annwrite            # noqa: E402  one chunk of a video's annotations, edited
import captimes            # noqa: E402  a caption's start, moved in every file that carries it
import wordline            # noqa: E402  a Japanese or Chinese chunk's word line, read
import words               # noqa: E402  and one proposed, where the analyzers are installed
import audiofile           # noqa: E402  what a recording is, and ffmpeg's three jobs on one
import clips               # noqa: E402  the tray a card's recording is cut into
import guidebuild          # noqa: E402  the HTML guide: its files, and its compile as a job

ANKI = ytpages.ANKI


def _load_studio():
    """The studio's server module, loaded from its file.

    It is called server.py -- too generic a name to import by name from
    here -- and it puts its own app/ and exlex/ directories on sys.path
    when it loads, which is all its route functions need.
    """
    spec = importlib.util.spec_from_file_location(
        "parseh_studio", os.path.join(STUDIO_APP, "server.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


studio = _load_studio()
STUDIO_BASE = "/studio"
studio.set_base(STUDIO_BASE)


class _AtRoot(object):
    directory = ROOT                    # what Handler serves (directory=ROOT)


def book_dir(url_path):
    """The book a URL path such as /books/<folder>/<slug> names -- the
    directory Handler.translate_path gives, when it holds a book.json -- or
    None.

    translate_path decodes and normalises before it looks, so an encoded
    climb (`/books/%2e%2e%2ftests/...`) would resolve outside books/.  A path
    whose decoding changes its shape names nothing, and the result must lie
    on the shelf."""
    decoded = urllib.parse.unquote(url_path).split("/")
    if len(decoded) != len(url_path.split("/")) or any(p in (".", "..") for p in decoded):
        return None
    book = SimpleHTTPRequestHandler.translate_path(_AtRoot(), url_path)
    # abspath, not realpath: a book kept elsewhere and linked into books/ is on the shelf
    shelf = os.path.abspath(os.path.join(_AtRoot.directory, "books"))
    if not os.path.abspath(book).startswith(shelf + os.sep):
        return None
    return book if os.path.isfile(os.path.join(book, "book.json")) else None


def video_dir(vid):
    """The directory of a video by its id, or None -- the same lookup the
    player page does, so an id that shows a page has a directory here."""
    if not vid or ".." in vid or "/" in vid:
        return None
    found = ytpages.find_video(vid)
    return found[1] if found else None


def notes_library(prefix):
    """The notes directory a notes page's prefix stands for, or None.

    The exercise decks ask it (deckroutes.set_notes_resolver, below) before
    a note's page offers "+ Deck" and before a copy reads a note.  It makes
    the lookups the notes routes make before they serve anything -- a book
    by its path with its book.json, a video by its id -- so a prefix that
    shows no notes page copies nothing."""
    if not isinstance(prefix, str):
        return None
    m = re.fullmatch(r"(/books/[^/]+(?:/[^/]+)?)/notes", prefix)
    if m:
        book = book_dir(m.group(1))
        return studio.notes.dir_for(book) if book else None
    m = re.fullmatch(re.escape(ytpages.BASE) + r"/v/([^/]+)/notes", prefix)
    if m:
        d = video_dir(m.group(1))
        return studio.notes.dir_for(d) if d else None
    return None


# the studio alone has no books or videos: only this server can say
studio.deckroutes.set_notes_resolver(notes_library)


def notes_came_back(item_dir):
    """The notes of a book or a video that has just come in -- a bundle
    brought back, a shelf's backup restored -- brought up to names at once
    (store.migrate_once, again): they come as they were written, two notes
    of one name and links by uid included, and they may have replaced
    notes this process opened, and so migrated, before -- whose next
    opening would not look again.  Never a reason to fail the install;
    migrate_links says on the console what it renamed."""
    notes_dir = studio.notes.dir_for(item_dir)
    if not notes_dir.is_dir():
        return None
    was = studio.store.use_library(notes_dir)
    try:
        return studio.store.migrate_once(again=True)
    except Exception as e:           # noqa: BLE001 -- the install stands
        sys.stderr.write("[notes] %s: links not brought up to names (%s)\n" % (item_dir, e))
        return None
    finally:
        studio.store.use_library(was)


# A client that goes away mid-transfer is ordinary traffic, not a fault.
GONE = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError,
        TimeoutError)

mimetypes.add_type("audio/webm", ".webm")
mimetypes.add_type("font/woff2", ".woff2")
# WebAssembly.instantiateStreaming REFUSES anything but this type, and the
# engine in mt/ is loaded that way; without the line the reader's
# translation worker fails at load with a message about the MIME type.
mimetypes.add_type("application/wasm", ".wasm")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("text/javascript", ".js")

# What may be fetched as a plain file.  Everything else on disk -- the
# sources, the tools, the card store, this program, the private key -- is
# not on the web, whatever the URL.
STATIC_PREFIXES = ("/lib/fonts/", "/lib/mathjax/", "/audiobook/", "/books/",
                   "/youtube/videos/",
                   # the translation engine and its models: read by the
                   # reader's own worker, never written through the server
                   "/mt/")
STATIC_FILES = {"/lib/parseh.css", "/lib/parseh.js", "/lib/llm.js", "/lib/mt.js",
                # what the server is working on, drawn on every page (loaded
                # by parseh.js, and by its own tag on the studio's pages)
                "/lib/activity.js",
                # the mobile interface's sheet (docs/mobile.md), and the layer
                # parseh.js loads into every book's reader for it
                "/lib/mobile.css", "/lib/mobilereader.js",
                # the mobile interface installed as an app: its icons
                # (lib/icons/make.mjs drew them; /manifest.webmanifest names them)
                "/lib/icons/parseh-192.png", "/lib/icons/parseh-512.png",
                "/lib/icons/parseh-maskable-512.png", "/lib/icons/apple-touch-icon.png",
                "/lib/decomposition.js", "/lib/decomposition.css", "/lib/wordline.js",
                # the card kit: the cut editor and the card sheet's three
                # destinations, shared by the reader and the player
                "/lib/cardkit.js", "/lib/cardkit.css",
                # the timeline: where one piece of text stops being said and
                # the next starts, moved over a picture of the sound --
                # shared by the reader and the player for the same reason
                "/lib/timeline.js", "/lib/timeline.css",
                # maths: the wrapper here, and MathJax itself under
                # /lib/mathjax/ (a prefix, below), fetched only by a page
                # that turns out to have a formula on it
                "/lib/mathjax.js", "/lib/mathjax.css",
                "/youtube/lib/style.css", "/youtube/lib/player.js",
                # the add page's transcript editor, which opens the cut
                # editor over the video it is about to add
                "/youtube/lib/subedit.js", "/youtube/lib/subedit.css"}
BODY_METHODS = ("POST", "PUT", "PATCH", "DELETE")
MAX_BODY = 32 * 1024 * 1024             # a JSON body: an edit, a chunk, an answer

# THE DOORS A FILE OF YOUR OWN COMES IN BY HAVE NO CEILING.  A narration, a
# film, a bundle carrying either, a deck with its media: these are the user's
# own files on the user's own machine, and a number written here could only
# ever be smaller than one of them.  They are streamed to disk in megabyte
# pieces and never held in memory, so the size that can arrive is the size of
# the disk, which is the only limit that was ever true.  MAX_BODY still holds
# for the ordinary JSON routes, where a body of that size is a mistake and
# not a film.
UPLOAD_ROUTES = ("/anki/sync/upload", "/books/__upload", "/exercises/api/import",
                 # a whole library put back from a backup: streamed to disk,
                 # because it is as big as everything somebody has written
                 "/studio/api/library/zip",
                 # and the same for the three other shelves.  A shelf is
                 # strictly bigger than any one thing on it, and a shelf of
                 # books carries the narrations: this is the largest body
                 # this toolbox ever takes.
                 "/exercises/api/restore", "/books/__restore",
                 ytpages.BASE + "/api/restore")
AUDIO_EXTS = (".mp3", ".m4a", ".mp4", ".aac", ".webm", ".ogg", ".oga", ".opus",
              ".wav", ".flac")


def have_ffmpeg():
    return bool(shutil.which("ffmpeg")) or os.path.exists(tstamp.FFMPEG)


NARR_FORMAT = "parseh-narration/1"       # the export's manifest says what it is


def audio_files(d):
    """The audio files directly inside a directory, sorted."""
    try:
        names = sorted(os.listdir(d))
    except OSError:
        return []
    return [os.path.join(d, n) for n in names
            if os.path.splitext(n)[1].lower() in AUDIO_EXTS
            and os.path.isfile(os.path.join(d, n))]


def timings_info(b):
    """What timings.json holds: how many subparagraphs, how many fixed by
    hand, and which audio it was made against."""
    out = {"subs": 0, "manual": 0, "audio": None}
    if not os.path.isfile(b.timings):
        return out
    try:
        with open(b.timings, encoding="utf-8") as f:
            doc = json.load(f)
    except ValueError:
        return out
    subs = doc.get("subs") or {}
    out["subs"] = len(subs)
    out["manual"] = sum(1 for v in subs.values()
                        if isinstance(v, dict) and v.get("src") == "manual")
    out["audio"] = doc.get("audio")
    return out


def narration_candidates(b):
    """Audio files that could be this book's narration, in the places earlier
    layouts of the toolbox kept them: the file timings.json names, the old
    audiobook/ directory at the root, the book's own directory, its audio/.
    Paths relative to the root, so the page can name one back and the
    server can check it is on this very list -- a path from outside never
    chooses a file."""
    seen, out = set(), []
    # EVERY RECORDING THE BOOK ALREADY HAS, not only the scalar -- which names
    # the FIRST record, so a book read in parts was offered its own second file
    # back under "found elsewhere", as though it were a stray somebody had left
    # in audio/.  Using it would have pointed book.json's audio at a file the
    # list already names.
    declared = {os.path.normpath(b.audio)} if b.audio else set()
    for n in b.narrations:
        if n["audio"]:
            declared.add(os.path.normpath(n["audio"]))

    def add(path, where):
        path = os.path.normpath(path)
        if path in seen or path in declared or not os.path.isfile(path):
            return
        if not (path + os.sep).startswith(ROOT + os.sep):
            return
        if os.path.splitext(path)[1].lower() not in AUDIO_EXTS:
            return
        seen.add(path)
        out.append({"path": os.path.relpath(path, ROOT).replace(os.sep, "/"),
                    "bytes": os.path.getsize(path), "where": where})
    ti = timings_info(b)
    if ti["audio"]:
        add(os.path.join(b.dir, ti["audio"]), "the file timings.json was made against")
    for f in audio_files(os.path.join(ROOT, "audiobook")):
        add(f, "the old audiobook/ directory")
    for f in audio_files(b.dir):
        add(f, "the book's own directory")
    for f in audio_files(os.path.join(b.dir, "audio")):
        add(f, "the book's audio/ directory")
    return out


def narration_id(records):
    """A name for a new recording that no other in the list wears."""
    used = {r.get("id") for r in records}
    k = 1
    while ("n%d" % k) in used:
        k += 1
    return "n%d" % k


def set_narrations(b, records):
    """Write book.json's list of recordings, and keep the old scalar true.

    THE SCALARS STILL MEAN WHAT THEY MEANT.  "audio" and "transcript" go on
    naming the first recording, so every tool that has only ever known one --
    Book.audio, has_audio, the library card, the bundle's three shapes --
    reads a book recorded in parts exactly as it reads a book recorded in one
    sitting.  A book left with a single whole-book recording is written back
    with no list at all, so its book.json is the file it always was.
    """
    recs = [{"id": r["id"], "audio": r.get("audio") or "",
             "transcript": r.get("transcript") or "",
             "from": r.get("from") or "", "to": r.get("to") or ""}
            for r in records]
    first = recs[0] if recs else None
    fields = {"audio": (first or {}).get("audio") or None}
    # THE TRANSCRIPT SCALAR IS WRITTEN ONLY WHEN THE FIRST RECORD HAS ONE, and
    # is otherwise not mentioned at all: set_book_meta updates the keys it is
    # given and leaves every other alone.  It used to be recomputed from the
    # first record on every write, and no door wrote a record's transcript, so
    # saving what a recording covers -- or removing another one -- quietly set
    # book.json's transcript back to null while the file sat there on disk.
    # Asking instead whether ANY record has one is the same bug a size smaller:
    # a transcript given to the SECOND recording would still blank the scalar.
    if (first or {}).get("transcript"):
        fields["transcript"] = first["transcript"]
    one_whole = (len(recs) == 1 and not recs[0]["from"] and not recs[0]["to"])
    fields["narrations"] = [] if one_whole else recs
    set_book_meta(b.dir, **fields)
    return recs


def set_book_meta(book_dir, **fields):
    """book.json with these fields set -- e.g. where the narration is."""
    p = os.path.join(book_dir, "book.json")
    with open(p, encoding="utf-8") as f:
        meta = json.load(f)
    meta.update(fields)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, p)

def chunk_way(body):
    """Which way a request asked for its text to be cut.

    A body that says nothing gets the way this toolbox has always cut a draft
    -- one chunk per sentence -- because that is what every book and video
    made before this existed holds, and a default that quietly re-chunked
    them would be handing somebody a different edition than the one they had.
    """
    want = (body or {}).get("how") or chunker.DEFAULT_WAY
    return want if want in chunker.WAYS else chunker.DEFAULT_WAY


# How much of a chunk's text one lookup reads, and how much one word line
# proposal will cut.  A chunk is a phrase; a paragraph pasted into one is
# looked up this far and no further, and is not handed to an analyzer whole.
LOOKUP_TEXT = 400
PROPOSE_TEXT = 4000
# The analyzers behind a proposal are one tokenizer each, cached in lib/words.py
# and shared by every request thread, and none of them promises to be safe for
# two threads at once; a proposal is a click, so they take turns.
WORDS_LOCK = threading.Lock()


def word_pieces(line, cap=LOOKUP_TEXT):
    """A chunk's word line as lookup's pieces: [{"word": surface, "at": k}]
    in written order, `k` the word's place among the line's words, or None
    where there is no line to go by -- not text, empty, or not a word line
    at all, which is then looked up as if it were absent.

    A word with no letter, mark or figure in it (`、`, `「`) is left out: it
    is nothing to look up -- which is why a piece carries `at`, since its
    own index no longer says which word it is.  The words are kept as far as
    LOOKUP_TEXT characters of text reach, the same cap the text itself is
    given.
    """
    if not isinstance(line, str) or len(line) > PROPOSE_TEXT * 10:
        return None                     # longer than any chunk's, readings and all
    try:
        pairs = wordline.parse(line)
    except wordline.WordsError:
        return None
    if not pairs:
        return None
    out, used = [], 0
    for k, (surface, _reading) in enumerate(pairs):
        used += len(surface)
        if used > cap:
            break
        if any(unicodedata.category(ch)[0] in "LMN" for ch in surface):
            out.append({"word": surface, "at": k})
    return out


ADDRESSES = []                          # filled at startup, shown on the hub


def static_ok(path):
    """May this address be answered with a file off the disk?

    ASKED OF THE DECODED PATH, because that is the one the file is finally
    found by.  This used to split the address as it arrived on the wire,
    where `%2e%2e` is not a component beginning with a dot and passed the
    test -- and then `translate_path` unquoted it, `posixpath.normpath`
    collapsed `/youtube/videos/../../serve.py` to `/serve.py`, and the
    result was resolved against the toolbox root.  Every file in the project
    was readable that way, `.tls/key.pem` included, while the same address
    written without the encoding was refused.  A guard and a resolver that
    disagree about what the path says are a guard that does not hold.
    """
    dec = urllib.parse.unquote(path)
    parts = [p for p in dec.split("/") if p]
    if any(p.startswith(".") or p == "__pycache__" for p in parts):
        return False
    if dec in STATIC_FILES:
        return True
    return dec.startswith(STATIC_PREFIXES)


def esc(s):
    return ytpages.esc(s)


def byte_range(header, size):
    """One `Range: bytes=a-b | a- | -n` against a file of `size` bytes ->
    (first, last) inclusive, or None when nothing of the file is in it (a
    416).  A header that is not a byte range at all raises ValueError, and
    both handlers then IGNORE the header and answer the whole file, as RFC
    9110 14.2 has a server do with a range unit it does not know (and as
    send_file did with every Range before it honoured them).  A list of
    ranges is answered with its first, which is all a media element ever
    asks for."""
    m = re.match(r"bytes=(\d*)-(\d*)", (header or "").strip())
    if not m:
        raise ValueError("not a byte range: %r" % header)
    s, e = m.group(1), m.group(2)
    if s == "":
        start, end = max(0, size - int(e or 0)), size - 1
    else:
        start = int(s)
        end = int(e) if e else size - 1
    end = min(end, size - 1)
    if start > end or start >= size:
        return None
    return start, end


# ------------------------------------------------------------------ the hub
def book_stats():
    """One record per book for the hub: what the built reader says about
    itself, plus the language and the reader's address (the book sits
    under its language folder, so the href is books/<folder>/<slug>/)."""
    out = []
    for b in booklib.all_books():
        st = make_index.stats(b)
        out.append({"slug": b.slug, "title": b.title, "latin": b.title_latin,
                    "lang": b.language, "href": "/books/%s/reader/" % b.rel_from_books(),
                    "built": st.get("built", False), "subs": st.get("subs", 0),
                    "timed": st.get("timed", 0), "audio": b.has_audio})
    return out


def lang_counts(bks, yt, docs, dk=None):
    """How much there is per language, for the hub's chip row and the
    counts on its doors: {code: {"books", "videos", "channels", "docs",
    "decks", "due"}}.

    The videos come from ytpages.stats()["by_lang"]; a stats() without it
    (the player before it learned languages) is read as all-Persian, so the
    hub never shows fewer videos than there are.  A studio document's
    language is its front matter's `target`, Persian when it has none.  The
    exercise decks come from decks.hub_stats()["by_lang"] (`dk`), where a
    deck's language is the folder it lives in."""
    out = {L.code: {"books": 0, "videos": 0, "channels": 0, "docs": 0,
                    "decks": 0, "due": 0}
           for L in languages.LANGS.values()}

    def rec(code):
        return out[languages.get_or_default(code).code]
    for b in bks:
        rec(b["lang"])["books"] += 1
    by = yt.get("by_lang") if isinstance(yt, dict) else None
    if isinstance(by, dict) and by:
        for code, d in by.items():
            d = d if isinstance(d, dict) else {}
            r = rec(code)
            r["videos"] += int(d.get("videos") or 0)
            r["channels"] += int(d.get("channels") or 0)
    else:
        r = rec(languages.DEFAULT)
        r["videos"] += int(yt.get("videos") or 0)
        r["channels"] += int(yt.get("channels") or 0)
    for m in docs:
        rec((m or {}).get("target"))["docs"] += 1
    by = (dk or {}).get("by_lang") if isinstance(dk, dict) else None
    for code, d in (by.items() if isinstance(by, dict) else ()):
        d = d if isinstance(d, dict) else {}
        r = rec(code)
        r["decks"] += int(d.get("decks") or 0)
        r["due"] += int(d.get("due") or 0)
    return out


def n(k, one, many=None):
    many = many or one + "s"
    return "%d %s" % (k, one if k == 1 else many)


def count_tag(counts, key, fmt, total, on=True):
    """A count on a door, told to follow the language chips.

    The tag reads the total, and carries the same count per language in
    data-counts -- {"all": "12 videos", "fa": "3 videos", ...} -- which
    parseh.js writes into it when a chip is picked.  A door used to say its
    total and then, in grey, one tag per language that had any; now the one
    number answers for whichever language is chosen, and says 0 for a
    language with nothing rather than leaving it out.

    `total` is given rather than summed over the languages, because the two
    differ: a channel with videos in two languages is one channel in the
    total and one in each of those languages."""
    per = {"all": fmt(int(total))}
    for L in languages.LANGS.values():
        per[L.code] = fmt(int(counts[L.code][key]))
    return '<span class="tag%s" data-counts="%s">%s</span>' % (
        " on" if on else "", esc(json.dumps(per, sort_keys=True)), esc(per["all"]))


def mode_switch():
    """The switch between the browser and the mobile interface, for a page's
    top bar (lib/mobile.py writes it, for its own pages too)."""
    return mobile.mode_switch()


def hub_page():
    bks = book_stats()
    try:
        yt = ytpages.stats()
    except Exception:
        yt = {"channels": 0, "videos": 0, "decks": 0, "cards": 0}
    try:
        docs = list(studio.store.list_docs())
    except Exception:
        docs = []
    try:
        dk = studio.decks.hub_stats()
    except Exception:
        dk = {"decks": 0, "due": 0, "by_lang": {}}
    counts = lang_counts(bks, yt, docs, dk)
    ndocs = len(docs)

    # the chip row counts everything a language has, over the four doors;
    # selector None: on the hub the chips only record the preference, the
    # index pages behind each door do the filtering
    totals = {c: d["books"] + d["videos"] + d["docs"] + d["decks"] for c, d in counts.items()}
    row = languages.chips_html(totals, selector=None)
    # the mobile layout's own row: the same chips, laid in one line that
    # scrolls sideways (lib/mobile.css reads the second class)
    mrow = languages.chips_html(totals, cls="parseh-langs m-langs", selector=None)
    addrs = "".join("<code>%s</code>" % esc(a) for a in ADDRESSES)
    # The brand and the door glyphs are the toolbox's own name and are
    # Persian whatever is being learned: they say so with data-lang, which
    # is what gives them the nastaliq face now that the stylesheet takes the
    # face from the element's language.
    #
    # TWO LAYOUTS IN ONE PAGE.  Everything marked data-layout="browser" is
    # the hub as it has always been; everything marked data-layout="mobile"
    # is the mobile interface's hub (docs/mobile.md), and lib/mobile.css
    # shows one or the other by <html data-mode>, which parseh.js sets in
    # <head> -- so switching is instant, needs no reload, and never flashes
    # the other layout.  The mobile one is for reading and studying: its
    # doors are the four that open something to read, and nothing on it
    # administers anything (no Anki sync, no clip tray, no dictionary setup,
    # no stop button, no addresses).  The body says data-mobile-page, so in
    # the mobile mode its links go to a page's mobile version wherever one
    # exists (Parseh.mode.route) and to the browser page otherwise.
    # #hub-activity, at the top of the one <main>, is shown in both.
    return """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(name)s</title>
%(apphead)s
<link rel="stylesheet" href="/lib/parseh.css">
<link rel="stylesheet" href="/lib/langs.css">
<link rel="stylesheet" href="/lib/mobile.css">
<script src="/lib/parseh.js"></script>
</head><body class="index" data-mobile-page>
<div class="parseh-bar" data-layout="browser">
  <a class="home" href="/"><span class="glyph" lang="fa">&#x67E;</span><span class="word">%(name)s</span></a>
  <span class="where">the hub</span>
  <span class="sp"></span>
  %(modes)s
  <a class="parseh-btn" href="/guide/" title="the guide: how to use Parseh">guide</a>
  <button type="button" data-parseh-theme title="theme">&#9680;</button>
  <button type="button" class="stop" data-parseh-stop title="stop the server">&#9211;<span class="word"> stop</span></button>
</div>
<div class="parseh-bar m-bar" data-layout="mobile">
  <a class="home" href="/"><span class="glyph" lang="fa">&#x67E;</span><span class="word">%(name)s</span></a>
  <span class="sp"></span>
  %(modes)s
  <button type="button" data-parseh-theme title="theme">&#9680;</button>
</div>
<main class="hub">
  <div id="hub-activity"></div>
  <div class="hub-browser" data-layout="browser">
  <div class="brand"><span class="fa" lang="fa" data-lang="fa">&#x67E;&#x627;&#x631;&#x633;&#x647;</span><span class="lat">%(name)s</span></div>
  <p class="tagline">A Frank-method toolbox: reading
  editions with their narration, glossed video transcripts, and typeset
  answers from an LLM &mdash; with one Anki card store underneath.</p>
  %(row)s
  <div class="doors">
    <a class="door" href="/books/">
      <div class="dfa" lang="fa" data-lang="fa">&#x6A9;&#x62A;&#x627;&#x628;&#x200C;&#x647;&#x627;</div>
      <div class="dname">Books</div>
      <div class="dwhat">Ilya Frank reading editions: the text in small
      chunks, each with its gloss, the audiobook playing in step.</div>
      <div class="tags">%(nbooks)s</div>
    </a>
    <a class="door" href="/youtube/">
      <div class="dfa" lang="fa" data-lang="fa">&#x648;&#x6CC;&#x62F;&#x6CC;&#x648;&#x647;&#x627;</div>
      <div class="dname">Videos</div>
      <div class="dwhat">YouTube videos with the whole transcript underneath,
      every phrase glossed; click a line to replay it.</div>
      <div class="tags">%(nvid)s%(nchan)s</div>
    </a>
    <a class="door" href="/studio/">
      <div class="dfa" lang="fa" data-lang="fa">&#x62F;&#x641;&#x62A;&#x631;</div>
      <div class="dname">Studio</div>
      <div class="dwhat">Answers from an LLM, typeset: a library of notes on the
      language, read on screen, annotated by hover, or built into a verified PDF.</div>
      <div class="tags">%(ndocs)s</div>
    </a>
    <a class="door" href="/exercises/">
      <div class="dfa" lang="fa" data-lang="fa">&#x62A;&#x645;&#x631;&#x6CC;&#x646;&#x200C;&#x647;&#x627;</div>
      <div class="dname">Exercises</div>
      <div class="dwhat">Decks of studio exercises, studied like Anki cards: each
      comes back when it is due, sooner when it was hard.</div>
      <div class="tags">%(nxdecks)s%(nxdue)s</div>
    </a>
  </div>
  <div class="row2">
    <a class="door wide" href="/anki/sync/">
      <div class="dname">&#8646; Anki</div>
      <div class="dwhat">The card store both readers write into. Made cards all
      week? Sync your Anki edits home here <i>before</i> you rebuild a deck.</div>
      <div class="tags"><span class="tag on">%(ncards)s</span><span class="tag">%(ndecks)s</span></div>
    </a>
    <a class="door wide" href="/clips/">
      <div class="dname">&#9986; The clip tray</div>
      <div class="dwhat">The recordings cut for cards and the frames captured
      for them, waiting to go onto one. Play them, and delete the ones no card
      needs any more.</div>
      <div class="tags">%(nclips)s</div>
    </a>
    <a class="door wide" href="/lookup/">
      <div class="dname">&#128269; Reading what nobody has glossed</div>
      <div class="dwhat">A book or a video whose glosses are not written yet is
      still readable: get a dictionary for its language, and look the words of
      a chunk up where nobody has glossed it.</div>
      <div class="tags">%(dicttags)s</div>
    </a>
  </div>
  <div class="foot">
    Reachable at <span class="addr">%(addrs)s</span>
    Every browser warns once about the certificate: it is ours, accept it.<br>
    The &#9211; stop button at the top of a page stops the server. A book is built
    from its card on the library page, and a video added from the video index;
    <a href="/guide/">the guide</a> has the rest.<br>
    %(name)s is free software, under the GNU GPL, version 3 or later; the fonts and
    the data it uses keep their own licences: <a href="/licences/">licences</a>.
  </div>
  </div>
  <div class="hub-mobile" data-layout="mobile">
    <div class="m-brand"><span class="fa" lang="fa" data-lang="fa">&#x67E;&#x627;&#x631;&#x633;&#x647;</span><span class="lat">%(name)s</span></div>
    <p class="m-tagline">A Frank-method toolbox: read, watch, study.</p>
    %(mrow)s
    <nav class="m-doors" aria-label="the toolbox">
      <a class="m-door" href="/books/">
        <div class="m-dtext">
          <div class="m-dname">Books</div>
          <div class="m-dwhat">Reading editions, the narration in step</div>
          <div class="m-tags">%(nbooks)s</div>
        </div>
        <div class="m-dfa" lang="fa" data-lang="fa">&#x6A9;&#x62A;&#x627;&#x628;&#x200C;&#x647;&#x627;</div>
      </a>
      <a class="m-door" href="/youtube/">
        <div class="m-dtext">
          <div class="m-dname">Videos</div>
          <div class="m-dwhat">The transcript under the video, every line glossed</div>
          <div class="m-tags">%(nvid)s%(nchan)s</div>
        </div>
        <div class="m-dfa" lang="fa" data-lang="fa">&#x648;&#x6CC;&#x62F;&#x6CC;&#x648;&#x647;&#x627;</div>
      </a>
      <a class="m-door" href="/studio/">
        <div class="m-dtext">
          <div class="m-dname">Studio</div>
          <div class="m-dwhat">Notes on the language, to read</div>
          <div class="m-tags">%(ndocs)s</div>
        </div>
        <div class="m-dfa" lang="fa" data-lang="fa">&#x62F;&#x641;&#x62A;&#x631;</div>
      </a>
      <a class="m-door" href="/exercises/">
        <div class="m-dtext">
          <div class="m-dname">Exercises</div>
          <div class="m-dwhat">Decks to study, each card when it is due</div>
          <div class="m-tags">%(nxdecks)s%(nxdue)s</div>
        </div>
        <div class="m-dfa" lang="fa" data-lang="fa">&#x62A;&#x645;&#x631;&#x6CC;&#x646;&#x200C;&#x647;&#x627;</div>
      </a>
    </nav>
    <div class="m-more-doors">
    <a class="m-door m-guide" href="/guide/">
      <div class="m-dtext">
        <div class="m-dname">Guide</div>
        <div class="m-dwhat">How the toolbox works</div>
      </div>
      <div class="m-dfa" lang="fa" data-lang="fa">&#x631;&#x627;&#x647;&#x646;&#x645;&#x627;</div>
    </a>
    <!-- installing the mobile interface as an app (lib/mobile.py,
         install_page); not drawn inside the app itself (lib/mobile.css) -->
    <a class="m-door m-guide m-appdoor" href="/m/install/">
      <div class="m-dtext">
        <div class="m-dname">As an app</div>
        <div class="m-dwhat">On the home screen, on the whole screen</div>
      </div>
      <img class="m-dicon" src="/lib/icons/parseh-192.png" width="44" height="44" alt="">
    </a>
    </div>
    <p class="m-foot">Free software, GPL 3 or later &middot; <a href="/licences/">Licences</a></p>
  </div>
</main>
</body></html>
""" % {"name": NAME, "row": row, "mrow": mrow, "modes": mode_switch(), "apphead": mobile.app_head(),
       # The four doors' counts are whole tags, each carrying what every
       # language has: pick a chip and they say that language's number.
       "nbooks": count_tag(counts, "books", lambda k: n(k, "book"), len(bks)),
       "nvid": count_tag(counts, "videos", lambda k: n(k, "video"),
                         int(yt.get("videos") or 0)),
       "nchan": count_tag(counts, "channels", lambda k: n(k, "channel"),
                          int(yt.get("channels") or 0), on=False),
       "ndocs": count_tag(counts, "docs", lambda k: n(k, "document"), ndocs),
       "nxdecks": count_tag(counts, "decks", lambda k: n(k, "deck"),
                            int(dk.get("decks") or 0)),
       "nxdue": count_tag(counts, "due", lambda k: "%d due" % k,
                          int(dk.get("due") or 0), on=False),
       # the card store underneath is one store, not one per language
       "ncards": n(int(yt.get("cards") or 0), "card"),
       "ndecks": n(int(yt.get("decks") or 0), "deck"), "addrs": addrs,
       "dicttags": dict_tags(), "nclips": clip_tags()}


def clip_tags():
    """What the clip tray's door says: how many clips wait in it."""
    try:
        k = len(clips.listing())
    except Exception:
        k = 0
    return '<span class="tag%s">%s</span>' % (" on" if k else "",
                                              n(k, "clip") if k else "the tray is empty")


def clips_page():
    """The clip tray at /clips/: every clip, newest first, to play or look
    at and to delete, one at a time or all at once.  A card, a deck or a
    document a clip went onto keeps its own copy, so nothing already made
    needs the tray; only a card copied as markdown and not pasted yet does."""
    rows = []
    for rec in clips.listing():
        url = esc(rec["url"])
        if rec["kind"] == "audio":
            media = '<audio controls preload="none" src="%s"></audio>' % url
        else:
            media = '<img src="%s" alt="" loading="lazy">' % url
        src = rec.get("source") or {}
        where = esc(src.get("title") or "")
        link = src.get("url") if isinstance(src.get("url"), str) else ""
        # a page of this toolbox, or a video's own address -- nothing else
        if where and (re.match(r"^/(?!/)", link) or link.startswith("https://")):
            where = '<a href="%s">%s</a>' % (esc(link), where)
        size = "%d kB" % max(1, round(rec["size"] / 1024))
        detail = [esc(rec["name"])]
        if rec.get("duration"):
            detail.append("%.1f s" % rec["duration"])
        detail += [x for x in (where, esc(rec["lang"]), size, esc(rec["created"])) if x]
        words = rec["text"] or rec["label"]
        rows.append(
            '<div class="crow" data-name="%s" data-kind="%s">'
            '<div class="cmedia">%s</div>'
            '<div class="cabt"><b dir="auto">%s</b><small>%s</small></div>'
            '<button type="button" class="plain del" title="Delete it from the tray" '
            'aria-label="Delete %s from the tray">&#10005;</button></div>'
            % (esc(rec["name"]), rec["kind"], media, esc(words) or esc(rec["name"]),
               " &middot; ".join(detail), esc(rec["name"])))
    return """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The clip tray &mdash; %(name)s</title>
<link rel="stylesheet" href="/lib/parseh.css">
<link rel="stylesheet" href="/lib/langs.css">
<script src="/lib/parseh.js"></script>
<style>
.tray{border:1px solid var(--rule);border-radius:12px;background:var(--card);overflow:hidden}
.crow{display:flex;align-items:center;gap:12px;padding:10px 14px;border-top:1px solid var(--rule);font-size:13.5px}
.crow:first-child{border-top:none}
.crow .cmedia{flex:none;width:min(300px,100%%)}
.crow audio{display:block;width:100%%;height:36px}
.crow img{display:block;max-width:100%%;max-height:90px;border-radius:6px}
.crow .cabt{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}
.crow .cabt b{font-weight:600;overflow-wrap:anywhere}
.crow .cabt small{color:var(--dim);font-size:12px;overflow-wrap:anywhere}
.crow .cabt a{color:var(--dim)}
button.plain{font:inherit;font-size:13px;background:var(--bg);color:var(--dim);
  border:1px solid var(--rule);border-radius:7px;padding:6px 12px;cursor:pointer}
button.plain:hover{color:var(--accent);border-color:var(--accent)}
button.plain.del:hover{background:var(--danger);border-color:var(--danger);color:var(--danger-fg)}
button.plain[disabled]{opacity:.5;cursor:default}
.trayhead{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 12px}
.trayhead .count{flex:1;color:var(--dim)}
.empty{padding:18px 14px;color:var(--faint)}
@media(max-width:600px){.crow{flex-wrap:wrap}.crow .cmedia{width:100%%}}
</style>
</head><body class="index">
<div class="parseh-bar">
  <a class="home" href="/"><span class="glyph" lang="fa">&#x67E;</span>%(name)s</a>
  <span class="where">the clip tray</span>
  <span class="sp"></span>
  <a class="parseh-btn" href="/guide/" target="_blank" title="the guide: how to use Parseh">guide</a>
  <button type="button" data-parseh-theme title="theme">&#9680;</button>
  <button type="button" class="stop" data-parseh-stop title="stop the server">&#9211; stop</button>
</div>
<main>
<h1 class="idx">the clip tray</h1>
<p class="sub">A recording cut from a book's narration or a film, or recorded
from a YouTube video playing in its tab, and a frame captured from a video,
wait here between the card sheet they were made on and the Anki card, the
exercise deck or the studio document they go onto. Each of those keeps its own
copy, so a clip deleted here is gone from nothing already made; only a card
copied as markdown and not pasted yet still needs its clips.</p>
<div class="trayhead"><span class="count" id="count"></span>
<button type="button" class="plain" id="empty-tray">Empty the tray</button></div>
<div class="tray" id="tray">%(rows)s<div class="empty" id="none" hidden>The tray is empty.</div></div>
</main>
<script>
(function () {
  var tray = document.getElementById('tray'), none = document.getElementById('none');
  var count = document.getElementById('count'), emptyBtn = document.getElementById('empty-tray');
  function rows() { return tray.querySelectorAll('.crow'); }
  function tell() {
    var k = rows().length;
    count.textContent = k ? k + (k === 1 ? ' clip' : ' clips') + ' in the tray' : '';
    none.hidden = k > 0;
    emptyBtn.disabled = k === 0;
  }
  function said(r) {
    return r.json().catch(function () { return {}; }).then(function (j) {
      // gone already (another page took it) is what was asked for
      if (!r.ok && r.status !== 404) throw new Error(j.error || r.status + ' ' + r.statusText);
      return j;
    });
  }
  tray.addEventListener('click', function (e) {
    var b = e.target.closest('button.del');
    if (!b) return;
    var row = b.closest('.crow'), name = row.dataset.name;
    if (!confirm('Delete \u201c' + name + '\u201d from the clip tray? A card, a deck or a document it already went onto keeps its own copy.')) return;
    b.disabled = true;
    fetch('/clips/api/' + encodeURIComponent(name), {method: 'DELETE'}).then(said).then(function () {
      row.querySelectorAll('audio').forEach(function (a) { a.pause(); });
      row.remove();
      tell();
    }).catch(function (err) {
      b.disabled = false;
      alert('Could not delete ' + name + ': ' + err.message);
    });
  });
  emptyBtn.addEventListener('click', function () {
    var k = rows().length;
    if (!k || !confirm('Delete all ' + k + (k === 1 ? ' clip' : ' clips') + ' in the tray? Cards, decks and documents keep their own copies; a card copied as markdown and not pasted yet loses its recording and its frame.')) return;
    emptyBtn.disabled = true;
    fetch('/clips/api/empty', {method: 'POST'}).then(said).then(function () {
      rows().forEach(function (row) { row.querySelectorAll('audio').forEach(function (a) { a.pause(); }); row.remove(); });
      tell();
    }).catch(function (err) {
      alert('Could not empty the tray: ' + err.message);
      tell();
    });
  });
  tell();
})();
</script>
</body></html>
""" % {"name": NAME, "rows": "".join(rows)}


def dict_tags():
    """What the hub's last door says about itself: which languages can already
    be looked up.  A door that says `0` is doing its job -- it is telling
    somebody there is something here they have not switched on."""
    have = [L.code for L in languages.LANGS.values() if lookup.available(L.code)]
    out = ['<span class="tag%s">%s</span>'
           % (" on" if have else "",
              ("%d dictionar%s" % (len(have), "y" if len(have) == 1 else "ies"))
              if have else "no dictionary yet")]
    out += ['<span class="tag" data-lang="%s">%s</span>' % (c, c) for c in have]
    return "".join(out)


def not_found_page(msg=""):
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>not found &mdash; %s</title>
<link rel="stylesheet" href="/lib/parseh.css"><link rel="stylesheet" href="/lib/langs.css">
<script src="/lib/parseh.js"></script>
</head><body class="index">
<div class="parseh-bar"><a class="home" href="/"><span class="glyph" lang="fa">&#x67E;</span>%s</a>
<span class="where">not found</span></div>
<main><h1 class="idx">nothing here</h1>
<p class="sub">%s</p>
<p class="sub"><a class="crumb" href="/">&lsaquo; the hub</a> &nbsp;
<a class="crumb" href="/books/">books</a> &nbsp;
<a class="crumb" href="/youtube/">videos</a> &nbsp;
<a class="crumb" href="/studio/">studio</a> &nbsp;
<a class="crumb" href="/exercises/">exercises</a></p>
</main></body></html>
""" % (NAME, NAME, esc(msg) or "That address is not part of the toolbox.")


# ------------------------------------------------------------------ handler
# What each language's dictionary build is doing, for the page to poll.  A
# module global and not a thread-local: the browser asking about it is not the
# thread doing it.  Every job below also carries when it started and when it
# finished, which is what the activity list on every other page reads them by
# (activity_now).
DICT_JOBS = {}
DECOMPOSITION_JOBS = {}
DECOMPOSITION_LOCK = threading.Lock()
# the same, for the parallel corpora: keyed "<code>-<gloss>"
CORPUS_JOBS = {}
# and for the translation models, keyed the same way
MT_JOBS = {}
# the synonym table is ONE file, not one per language or pair, so this is
# a single job {running, say, error}, not a dict of them
SYN_JOB = {}


# ------------------------------------------------------------------ activity
# WHAT COUNTS AS WORK, for the list every page shows (lib/activity.py, drawn
# by lib/activity.js): the requests that pack, unpack, build, align or carry
# a file of somebody's own.  Asked of the address alone, before the body is
# read -- so the upload itself is on the list, not only what is done with it
# afterwards -- and answered with (kind, label, after): `after` is what the
# entry says it is doing once the body is in.
#
# THE SAME ADDRESSES lib/activity.js hooks a download link by (DOWNLOAD
# there): a link it marks with ?job= must land on a request registered here,
# or the page would wait for an entry that never comes.
#
# A picture or a recording put into one document or one deck is a click
# like any other, and counts only past BIG_BODY; everything else here is
# long by what it does, whatever its size.
BIG_BODY = 4 * 1024 * 1024
SHAPE_WORDS = {"text": "the text alone", "linked": "everything but the recording",
               "full": "all of it"}
NARRATION_WORK = {
    "audio": "Uploading the recording %(file)s for %(book)s",
    "import": "Importing the narration file %(file)s into %(book)s",
    "align": "Aligning the narration of %(book)s",
    "spread": "Spreading a recording over its stretch of %(book)s",
    "region": "Moving a recording's stretch in %(book)s",
    "remove": "Taking a recording off %(book)s",
    "restore": "Putting the narration of %(book)s back",
    "transcript": "Saving a transcript for %(book)s",
}


def named(title):
    """A title inside an English sentence, quoted and ISOLATED (U+2068 ...
    U+2069): a Persian or an Arabic one would otherwise pull the words
    around it into its own direction and the sentence would read backwards."""
    return "\u201c\u2068%s\u2069\u201d" % title


def _book_named(url_path):
    """The book an address inside it belongs to, as a quoted title -- or
    "a book" where there is none (the refusal is the route's to give)."""
    m = re.match(r"^(/books/.+?)(?:/reader)?/(?:__|notes(?:/|$))", url_path)
    book = book_dir(m.group(1)) if m else None
    if not book:
        return "a book"
    try:
        b = booklib.Book(book)
        return named(b.title_latin or b.title or os.path.basename(book))
    except Exception:
        return named(os.path.basename(book))


def _video_named(vid):
    try:
        found = ytpages.find_video(vid)
    except Exception:
        found = None
    meta = (found or [None])[0] or {}
    return named(meta.get("title") or meta.get("title_native") or vid)


def _doc_named(doc_id):
    """A studio document by its title -- in the studio's own library; a
    note's title is not looked up (its library is the request's to point
    at), and its id says enough."""
    try:
        meta, _md = studio.store.get(doc_id)
        return named(meta.get("title") or doc_id)
    except Exception:
        return named(doc_id)


def _deck_named(folder, slug):
    try:
        return named(studio.decks.get_deck(folder, slug)["name"])
    except Exception:
        return named(slug)


def _studio_work(method, sub, whose, length, file):
    """The studio's long routes, for the studio itself (whose None) or for
    the notes of a book or a video (whose() names them).

    `whose` is ASKED ONLY ONCE THE ADDRESS IS ONE OF THESE: naming a video
    walks the video shelf, and every request under a notes mount comes
    through here -- each script, stylesheet and picture of a note's page --
    while nearly none of them is long work."""
    def of():
        return "the notes on " + whose() if whose else "the studio library"
    if method == "GET" and sub == "/api/export":
        return "backup", "Packing the backup of " + of(), None
    if method == "POST" and sub == "/api/download":
        return "download", ("Packing notes on %s to download" % whose() if whose
                            else "Packing documents to download"), None
    m = re.match(r"^/download/([a-z0-9\-]+)/(zip|pdf)$", sub)
    if method == "GET" and m:
        doc = named(m.group(1)) if whose else _doc_named(m.group(1))
        return ("download", ("Packing %s to download" if m.group(2) == "zip"
                             else "Sending the PDF of %s") % doc, None)
    if method == "POST" and sub == "/api/docs/zip":
        return "upload", "Importing %s into %s" % (file, of()), "importing"
    if method == "POST" and sub == "/api/library/zip":
        return "restore", "Restoring %s from %s" % (of(), file), "putting it back"
    m = re.match(r"^/api/docs/([a-z0-9\-]+)/build$", sub)
    if method == "POST" and m:
        doc = named(m.group(1)) if whose else _doc_named(m.group(1))
        return "compile", "Building the PDF of " + doc, None
    if method == "POST" and length > BIG_BODY:
        if sub == "/api/docs":
            return "upload", "Uploading a document into " + of(), "saving"
        m = re.match(r"^/api/docs/([a-z0-9\-]+)/(images|audio)$", sub)
        if m:
            return "upload", "Uploading %s into %s" % (file, of()), "saving"
    return None


def _decks_work(method, sub, length, file):
    """The exercise decks' long routes (markdown/app/deckroutes.py)."""
    F, S = r"([a-z]+)", r"([a-z0-9][a-z0-9-]*)"
    if method == "GET" and sub == "/api/backup":
        return "backup", "Packing the backup of every deck", None
    m = re.match(r"^/api/decks/%s/%s/export$" % (F, S), sub)
    if method == "GET" and m:
        return "download", "Exporting the deck " + _deck_named(*m.groups()), None
    if method == "POST" and sub == "/api/import":
        return "upload", "Importing the deck " + file, "importing"
    if method == "POST" and sub == "/api/restore":
        return "restore", "Restoring the decks from " + file, "putting them back"
    if method == "POST" and length > BIG_BODY and \
            re.match(r"^/api/decks/%s/%s/(images|audio)$" % (F, S), sub):
        return "upload", "Uploading %s into a deck" % file, "saving"
    return None


def long_work(method, path, query, length=0):
    """-> (kind, label, after) for a request worth an entry on the activity
    list, or None for everything else -- which is nearly every request."""
    q = lambda k: (query.get(k) or [""])[0]
    # what the page says the file is called (the bundle doors, the Anki
    # inbox and the narration's upload are sent ?name=), and its size, which
    # is the Content-Length and never the page's word
    fname = re.sub(r"[\x00-\x1f]", "", os.path.basename(q("name")))[:80]
    size = activity.size(length) if length else ""
    file = (named(fname) if fname else "a file") + (" (%s)" % size if size else "")
    yt = ytpages.BASE
    decks_base = studio.deckroutes.BASE
    if path.startswith(STUDIO_BASE + "/"):
        return _studio_work(method, path[len(STUDIO_BASE):], None, length, file)
    m = re.match(r"^(/books/[^/]+(?:/[^/]+)?)/notes(/.*)?$", path)
    if m:
        return _studio_work(method, m.group(2) or "/", lambda: _book_named(path),
                            length, file)
    m = re.match(r"^%s/v/([^/]+)/notes(/.*)?$" % re.escape(yt), path)
    if m:
        vid = m.group(1)
        return _studio_work(method, m.group(2) or "/", lambda: _video_named(vid),
                            length, file)
    if path.startswith(decks_base + "/"):
        return _decks_work(method, path[len(decks_base):], length, file)
    if method == "GET":
        if path == "/books/__backup":
            return "backup", "Packing the backup of every book", None
        if path == yt + "/api/backup":
            return "backup", "Packing the backup of every video", None
        if path.startswith("/books/") and path.rstrip("/").endswith("/__download"):
            shape = SHAPE_WORDS.get(q("audio").strip().lower())
            return "download", "Packing %s to download%s" % (
                _book_named(path), " (%s)" % shape if shape else ""), None
        if path.startswith("/books/") and path.endswith("/__narration/export"):
            return "download", "Packing the narration of " + _book_named(path), None
        m = re.match(r"^%s/v/([^/]+)/__download/?$" % re.escape(yt), path)
        if m:
            return "download", "Packing the video %s to download" % _video_named(m.group(1)), None
        m = re.match(r"^/anki/build/(?:[a-z]+/)?([a-z0-9][a-z0-9-]*)\.apkg$", path)
        if m:
            return "build", "Building the Anki deck " + named(m.group(1)), None
        return None
    if method != "POST":
        return None
    if path == "/books/__upload":
        return "upload", "Uploading " + file, "installing"
    if path == "/books/__restore":
        return "restore", "Restoring books from " + file, "putting them back"
    if path == "/books/__empty":
        return "build", "Writing a new book", None
    if path.startswith("/books/"):
        if re.match(r"^/books/.+/__append/?$", path):
            return "build", "Adding text to " + _book_named(path), None
        m = re.search(r"/__narration/([a-z]+)/?$", path)
        if m:
            say = NARRATION_WORK.get(m.group(1), "Working on the narration of %(book)s")
            # once an upload is in, the file is put in its place and the
            # reader built again: that is what the entry then says
            return "narration", say % {"book": _book_named(path), "file": file}, \
                {"audio": "rebuilding the reader", "import": "unpacking"}.get(m.group(1))
        if path.rstrip("/").endswith("/__save/subtimes.json"):
            return "narration", "Saving the times set by hand in " + _book_named(path), None
        return None
    if path == yt + "/api/upload":
        return "upload", "Uploading " + file, "installing"
    if path == yt + "/api/restore":
        return "restore", "Restoring videos from " + file, "putting them back"
    if path == yt + "/api/local":
        return "install", "Adding a video from a file on this machine", None
    if path == yt + "/api/add":
        return "install", "Adding a video", None
    if path == yt + "/api/prepare":
        return "compile", "Preparing the prompt for a video", None
    if path == "/anki/sync/upload":
        return "upload", "Uploading %s to the Anki inbox" % file, "saving"
    if path == "/anki/sync/run":
        return "install", "Syncing an Anki export with the card store", None
    if path == "/anki/sync/bootstrap":
        return "install", "Bringing decks in from an Anki export", None
    return None


# what each of the lookup page's job tables is called on the list: its
# name among the entries, and the sentence (%s is the language, the pair or
# the pack).  The tables are read afresh each time, never copied.
LOOKUP_WORK = (
    ("dict", lambda: DICT_JOBS, "Getting the %s dictionary"),
    ("corpus", lambda: CORPUS_JOBS, "Getting the %s parallel sentences"),
    ("model", lambda: MT_JOBS, "Getting the %s translation model"),
    ("components", lambda: DECOMPOSITION_JOBS, "Getting the %s component pack"),
    ("synonyms", lambda: {"": SYN_JOB} if SYN_JOB else {}, "Getting the synonym table"),
)


def _lang_pair(key):
    """"fa-en" -> "Persian-English", "fa" -> "Persian"; a code the registry
    does not know is shown as it is."""
    names = []
    for code in str(key).split("-"):
        L = languages.LANGS.get(code)
        if L is None:
            try:
                L = languages.gloss(code)
            except KeyError:
                L = None
        names.append(L.name if L else code)
    return "\u2013".join(names)


def build_entry(book, started):
    """The name of one build of a book on the activity list: the book and
    WHEN -- a page that saw the last build of it finish must still hear
    about the next one, and a name used twice would already be "seen"."""
    return "build:%s@%.3f" % (on_shelf(book), started or 0)


def guide_entry(started):
    """The name of one compile of the HTML guide on the activity list: like
    a book's build, named by WHEN, so the next compile is news again."""
    return "guide:compile@%.3f" % (started or 0)


def on_shelf(book):
    """A book's directory as its address under /books/ names it: english/mini-en,
    or mini-en for a book from before languages.  The shelf's own view, and
    not build.sh's (bookbuild.book_arg): the address is what the list links
    to and what names the build's entry."""
    shelf = os.path.realpath(os.path.join(_AtRoot.directory, "books"))
    return os.path.relpath(os.path.realpath(book), shelf).replace(os.sep, "/")


def activity_now():
    """What /__activity answers: every long request (lib/activity.py) and,
    merged in at the moment of asking, every book being built, the HTML
    guide being compiled, and every dictionary, corpus, model, component
    pack or synonym table being fetched -- running, or finished within
    activity.KEEP seconds."""
    extra, now = [], time.time()
    for book, job in bookbuild.jobs():
        if job["state"] not in ("running", "done", "failed"):
            continue
        # a build over for longer than the list keeps finished work is not
        # looked at again: the job table keeps every build since the server
        # started, and every page asks this every few seconds
        if job["state"] != "running" and now - (job["finished"] or 0) > activity.KEEP:
            continue
        try:
            b = booklib.Book(book)
            title = b.title_latin or b.title or os.path.basename(book)
        except Exception:
            title = os.path.basename(book)
        arg = on_shelf(book)
        # a book's own page is its reader, once it has one; the library page
        # (where its card is) until then
        page = ("/books/%s/reader/" % arg
                if os.path.isfile(os.path.join(book, "reader", "index.html")) else "/books/")
        last = next((ln.strip() for ln in reversed(job["log"]) if ln.strip()), None)
        extra.append(activity.entry(
            build_entry(book, job["started"]), "build",
            ("Building the PDF of %s" if job["what"] == "pdf"
             else "Rebuilding the reader of %s") % named(title),
            job["started"], stage=last, page=page,
            finished=job["finished"] if job["state"] != "running" else None,
            ok=job["state"] == "done"))
    # the guide's compile (lib/guidebuild.py), started from its front page:
    # that page says so in its own box, and every other page -- the hub
    # above all -- hears of it only from here
    job = guidebuild.job()
    if job.get("started") and job.get("state") in ("running", "done", "failed") \
            and (job["state"] == "running" or now - (job.get("finished") or 0) <= activity.KEEP):
        last = next((ln.strip() for ln in reversed(job["log"]) if ln.strip()), None)
        extra.append(activity.entry(
            guide_entry(job["started"]), "compile", "Compiling the guide", job["started"],
            stage=last, page="/guide/",
            finished=job.get("finished") if job["state"] != "running" else None,
            ok=job["state"] == "done"))
    for name, table, say in LOOKUP_WORK:
        # the component packs' table is the one written under a lock; the
        # others are replaced whole or changed a key at a time, and a copy
        # of the items is enough to read them without one
        with DECOMPOSITION_LOCK:
            rows = [(k, dict(v)) for k, v in list(table().items())]
        for key, job in rows:
            running = bool(job.get("running"))
            if not job.get("started") or not (running or job.get("finished")) \
                    or (not running and now - job["finished"] > activity.KEEP):
                continue
            what = (decomposition.PACKS.get(key, {}).get("name", key)
                    if name == "components" else _lang_pair(key))
            extra.append(activity.entry(
                "lookup:%s:%s@%.3f" % (name, key, job["started"]), "lookup",
                say % what if "%s" in say else say, job["started"],
                stage=job.get("say") or None, page="/lookup/",
                finished=None if running else job.get("finished"),
                ok=not job.get("error")))
    return dict(activity.snapshot(extra), ok=True)


class Handler(SimpleHTTPRequestHandler):
    server_version = NAME + "/1.0"
    protocol_version = "HTTP/1.1"       # keep-alive: one TLS handshake per tab
    timeout = 90                        # an idle keep-alive connection is reaped

    def __init__(self, *a, **kw):
        self._head = False
        self._raw = b""
        self._cc = False
        self._act = None                # this request's entry on the activity list
        self._status = 0
        self.query = {}
        super().__init__(*a, directory=ROOT, **kw)

    # ---- quiet logging: errors and writes only
    def log_request(self, code="-", size="-"):
        try:
            code = int(code)
        except (TypeError, ValueError):
            code = 0
        if code >= 400 or self.command not in ("GET", "HEAD"):
            self.log_message('"%s" %s', self.requestline, code)

    def log_error(self, fmt, *args):
        if fmt.startswith("Request timed out"):
            return                      # an idle keep-alive connection closing
        self.log_message(fmt, *args)

    def log_message(self, fmt, *args):
        # A log line is never worth a request: a detached job's dead
        # terminal raises EIO here, and the request must still be answered.
        try:
            sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))
            sys.stderr.flush()
        except Exception:
            pass

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except GONE:
            self.close_connection = True

    def send_error(self, *a, **kw):
        try:
            super().send_error(*a, **kw)
        except GONE:
            self.close_connection = True

    # ---- headers: nothing here is worth caching except the fonts and the
    # one library that is bigger than all of them
    def send_response(self, code, message=None):
        self._cc = False
        self._status = code             # the activity list's "ok" is this < 400
        self._code = code
        super().send_response(code, message)

    def send_header(self, key, value):
        if key.lower() == "cache-control":
            self._cc = True
        super().send_header(key, value)

    def end_headers(self):
        if not self._cc:
            # no path at all when the request line itself was refused (a
            # TLS hello sent to --http, say): the 400 still goes out
            p = (getattr(self, "path", None) or "").split("?", 1)[0]
            # MathJax is two megabytes and changes only when the checkout
            # does.  Everything else here is a page or a script somebody is
            # editing, and `no-store` is why a reload shows the edit -- but
            # answering two megabytes afresh on every page that carries a
            # formula, to a phone over a tunnel, is the one place that rule
            # costs more than it is worth.
            # A font or MathJax that IS there, that is: a 404 kept for a day
            # would outlive the file's arrival -- the guide's front page asks
            # for fonts its first compile has not made yet, and would go on
            # drawing without them long after the compile made them.
            if (p.endswith((".woff2", ".ttf", ".otf")) or p.startswith("/lib/mathjax/")) \
                    and getattr(self, "_code", 200) in (200, 206, 304):
                self.send_header("Cache-Control", "max-age=86400")
            else:
                self.send_header("Cache-Control", "no-store")
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    # ---- the answer helpers every route set expects
    def send_bytes(self, data, ctype, code=200, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self._head:
            return
        try:
            act = getattr(self, "_act", None)
            if not act or len(data) <= (1 << 20):
                self.wfile.write(data)
                return
            # a bundle packed in memory, on the activity list: written in
            # megabyte slices so the list can say how much has gone
            view = memoryview(data)
            for at in range(0, len(data), 1 << 20):
                self.wfile.write(view[at:at + (1 << 20)])
                activity.progress(act, done=min(at + (1 << 20), len(data)),
                                  total=len(data), stage="sending")
        except GONE:
            self.close_connection = True
            self._failed = True

    def _pour(self, f, count=None):
        """A file object onto the socket in megabyte pieces -- `count` bytes
        of it, or all of it -- saying how far it has got when the request is
        on the activity list."""
        act = getattr(self, "_act", None)
        sent = 0
        while count is None or sent < count:
            piece = f.read(1 << 20 if count is None else min(1 << 20, count - sent))
            if not piece:
                break
            self.wfile.write(piece)
            sent += len(piece)
            if act:
                activity.progress(act, done=sent, total=count, stage="sending")

    def send_json(self, obj, code=200):
        # {"ok": false} with a 200 is a refusal all the same (the narration
        # doors answer a failed run that way): the activity list must not
        # call it done -- nor a download the browser gave up on (GONE, below)
        if isinstance(obj, dict) and obj.get("ok") is False:
            self._failed = True
        self.send_bytes(json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                        "application/json; charset=utf-8", code)

    def send_html(self, text, code=200):
        self.send_bytes(text.encode("utf-8"), "text/html; charset=utf-8", code)

    send_page = send_html                # what the player's pages call it
    _json = send_json                    # what the book endpoints call it

    def send_file(self, path, download_name=None, inline_type=None):
        """A file the studio, the decks or the clip tray serve -- a picture,
        a font, a recording.  RANGE-AWARE whenever it is not a download: a
        recording in a document, a deck or the tray is played by an <audio>
        that seeks (`#t=`, a clip's window, a click on the scrubber), and a
        whole file answered to a Range request is not a seek.  Streamed in
        pieces, never read whole."""
        path = str(path)
        if not os.path.isfile(path):
            return self.send_json({"error": "not found"}, 404)
        ctype = inline_type or audiofile.mime_for(path) \
            or mimetypes.guess_type(path)[0] or "application/octet-stream"
        extra = {"Cache-Control": "no-cache"}
        ext = os.path.splitext(path)[1].lower()
        if ext in (".ttf", ".otf", ".woff2"):
            extra = {"Cache-Control": "max-age=86400"}
        if ext in (".svg", ".pdf"):
            # an uploaded SVG can carry scripts, and so can a PDF: both are
            # inert where the pages use them, but neutralise a direct visit
            if ext == ".svg":
                ctype = "image/svg+xml"
            extra["Content-Security-Policy"] = \
                "default-src 'none'; style-src 'unsafe-inline'"
        if download_name:
            extra["Content-Disposition"] = (
                'attachment; filename="%s"' % download_name)
        size = os.path.getsize(path)
        code, first, count = 200, 0, size
        rng = None if download_name else self.headers.get("Range")
        if rng:
            try:
                got = byte_range(rng, size)
            except ValueError:
                got = False              # not a byte range: the whole file
            if got is None:
                self.send_response(416)
                self.send_header("Content-Range", "bytes */%d" % size)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if got:
                code, first, count = 206, got[0], got[1] - got[0] + 1
                extra["Content-Range"] = "bytes %d-%d/%d" % (got[0], got[1], size)
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(count))
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        if self._head:
            return
        with open(path, "rb") as f:
            f.seek(first)
            try:
                self._pour(f, count)
            except GONE:
                self.close_connection = True
                self._failed = True

    def _body(self):
        return self._raw

    def _json_body(self):
        return json.loads(self._raw.decode("utf-8")) if self._raw else {}

    def _redirect(self, where, code=302):
        self.send_response(code)
        self.send_header("Location", where)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _not_found(self, msg=""):
        self.send_html(not_found_page(msg), 404)

    def _method_not_allowed(self):
        self.send_json({"ok": False, "error": "method not allowed"}, 405)

    # ---- dispatch
    def do_GET(self):
        self._dispatch("GET")

    def do_HEAD(self):
        self._dispatch("HEAD")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def _dispatch(self, method):
        """One request, and -- when it is long work (long_work) -- its entry
        on the activity list: put there BEFORE the body is read, so an
        upload is on the list while it arrives, and taken off in the
        `finally`, after the last byte of the answer has been written, so a
        download is on it while it is packed and while it is sent."""
        self._act, self._after, self._status, self._failed = None, None, 0, False
        if method != "HEAD":
            try:
                parsed = urllib.parse.urlsplit(self.path)
                query = urllib.parse.parse_qs(parsed.query)
                try:
                    length = int(self.headers.get("Content-Length") or 0) \
                        if method in BODY_METHODS else 0
                except ValueError:
                    length = 0
                work = long_work(method, parsed.path, query, length)
                if work:
                    kind, label, self._after = work
                    # a body is counted as it arrives when it is a file's
                    # worth; a few kilobytes of JSON are in before anybody
                    # could see a percentage of them
                    counted = length > (1 << 20)
                    self._act = activity.begin(
                        kind, label, page=activity.clean_page(self.headers.get("Referer")),
                        job=(query.get("job") or [""])[0],
                        total=length if counted else None,
                        stage="receiving" if counted else None)
            except Exception:
                # the list is a courtesy: a label that cannot be made must
                # never cost the request itself
                traceback.print_exc()
                self._act = None
        try:
            self._dispatch_request(method)
        finally:
            if self._act:
                activity.end(self._act, ok=0 < self._status < 400 and not self._failed)
                self._act = None

    def _received(self):
        """The body is in: the entry stops saying "receiving" and says what
        is being done with it (long_work's `after`), or nothing."""
        act = getattr(self, "_act", None)
        if act:
            activity.progress(act, stage=getattr(self, "_after", None) or "")

    def _dispatch_request(self, method):
        self._head = method == "HEAD"
        self._raw = b""
        self._spool = None            # a body too big to hold, spooled to disk
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        self.query = urllib.parse.parse_qs(parsed.query)
        if method in BODY_METHODS:
            # The body is read ONCE, here, whatever route answers: a body
            # left on the socket would be parsed as the next request.
            te = (self.headers.get("Transfer-Encoding") or "").lower()
            if "chunked" in te:
                self.close_connection = True
                return self.send_json({"error": "chunked bodies are not supported"}, 411)
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                self.close_connection = True
                return self.send_json({"error": "bad Content-Length"}, 400)
            if method == "POST" and path.endswith(("/__narration/audio", "/__narration/import")):
                # an audiobook is hundreds of megabytes: it goes straight to
                # a file, never through the buffer below or its cap
                self._raw = b""
                try:
                    return self._narration_stream(n, path.rsplit("/", 1)[1])
                except GONE:
                    self.close_connection = True
                    return
                except Exception as e:
                    traceback.print_exc()
                    self.close_connection = True   # the body may be half-read
                    try:
                        self.send_json({"ok": False, "error": "%s: %s"
                                        % (type(e).__name__, e)}, 500)
                    except Exception:
                        pass
                    return
            # A BUNDLE MAY BE THE WHOLE OF A FILM.  The two bundle doors used
            # to take the Anki wizard's 400 MB cap and read the body into a
            # bytearray, which meant the download button here handed somebody
            # a 438 MB zip that this same toolbox then refused with `request
            # body too large` -- a video that could leave and not come back.
            # They are streamed to a file instead, exactly as a narration
            # upload is, and take the budget lib/bundle.py already keeps for
            # the media inside them.
            big = path in UPLOAD_ROUTES + (ytpages.BASE + "/api/upload",)
            if n < 0:
                self.close_connection = True
                return self.send_json({"error": "bad Content-Length"}, 400)
            if not big and n > MAX_BODY:
                self.close_connection = True
                return self.send_json({"error": "request body too large"}, 413)
            if big and n > MAX_BODY:
                # to disk, in pieces, never into memory
                fd, spool = tempfile.mkstemp(prefix="parseh-upload-", suffix=".zip")
                got = 0
                try:
                    with os.fdopen(fd, "wb") as f:
                        while got < n:
                            chunk = self.rfile.read(min(1 << 20, n - got))
                            if not chunk:
                                break
                            f.write(chunk)
                            got += len(chunk)
                            activity.progress(self._act, done=got)
                except Exception:
                    os.unlink(spool)
                    raise
                if got != n:
                    os.unlink(spool)
                    self.close_connection = True
                    return self.send_json({"error": "request body cut short"}, 400)
                self._received()
                self._spool = spool
                self.rfile = io.BytesIO(b"")
                try:
                    self._route(method, path)
                finally:
                    self._spool = None
                    try:
                        os.unlink(spool)
                    except OSError:
                        pass
                return
            buf = bytearray()
            while len(buf) < n:            # a big upload arrives in pieces
                chunk = self.rfile.read(min(1 << 20, n - len(buf)))
                if not chunk:
                    break
                buf += chunk
                activity.progress(self._act, done=len(buf))
            if len(buf) != n:
                self.close_connection = True
                return self.send_json({"error": "request body cut short"}, 400)
            self._received()
            self._raw = bytes(buf)
        orig = self.rfile
        # every handler that reads its body off rfile gets the same bytes
        self.rfile = io.BytesIO(self._raw)
        try:
            self._route("GET" if method == "HEAD" else method, path)
        except GONE:
            self.close_connection = True
            self._failed = True
        except Exception as e:
            # never let a request die without an answer: the page can print
            # a JSON error, but "NetworkError" names neither cause nor file
            traceback.print_exc()
            try:
                self.send_json({"ok": False, "applied": 0,
                                "error": "%s: %s" % (type(e).__name__, e)}, 500)
            except Exception:
                self.close_connection = True
        finally:
            self.rfile = orig

    def _route(self, method, path):
        if path == "/":
            if method != "GET":
                return self._method_not_allowed()
            return self.send_html(hub_page())
        if path == "/index.html":
            return self._redirect("/")
        if path == "/__shutdown":
            if method != "POST":
                return self._method_not_allowed()
            return self._shutdown()
        if path == "/__activity":
            # what the server is busy with, polled by lib/activity.js on
            # every page: cheap, never on the list itself, never cached
            # (end_headers sends no-store for everything but the fonts)
            if method != "GET":
                return self._method_not_allowed()
            return self.send_json(activity_now())
        if path == "/guide":
            return self._redirect("/guide/")
        if path.startswith("/guide/"):
            return self._guide(method, path[len("/guide/"):])
        if path == "/guide.pdf":
            # the PDF manual's old address, kept in somebody's bookmarks: the
            # manual is the guide now, and there is no PDF of it
            return self._redirect("/guide/")
        # the licences (lib/notices.py): the page, and the GPL's own text from
        # the file at the top of the checkout -- nothing else of the checkout
        # is served by this, whatever follows /licences/
        if path in ("/licences", "/licences/", "/licences/index.html",
                    "/licenses", "/licenses/"):
            if method != "GET":
                return self._method_not_allowed()
            if path != "/licences/":
                return self._redirect("/licences/")
            return self.send_html(notices.page())
        if path == "/licences/LICENSE":
            if method != "GET":
                return self._method_not_allowed()
            return self.send_bytes(notices.licence_text(), "text/plain; charset=utf-8")
        if path in ("/lookup", "/lookup/"):
            if method != "GET":
                return self._method_not_allowed()
            return self.send_html(lookuppage.page())
        if path.startswith("/lookup/api/"):
            if method != "POST":
                return self._method_not_allowed()
            return self._lookup_api(path.split("/api/", 1)[1])
        if path.startswith("/anki/"):
            return self._anki(method, path)
        if path == "/clips" or path.startswith("/clips/"):
            return self._clips(method, path)
        if path == STUDIO_BASE:
            return self._redirect(STUDIO_BASE + "/")
        if path.startswith(STUDIO_BASE + "/"):
            return self._studio(method, path[len(STUDIO_BASE):])
        # the exercise decks: studio exercises, under their own address and
        # with their own route table (markdown/app/deckroutes.py), which maps
        # its own errors -- the same one the studio run alone mounts
        decks_base = studio.deckroutes.BASE
        if path == decks_base:
            return self._redirect(decks_base + "/")
        if path.startswith(decks_base + "/"):
            return studio.deckroutes.dispatch(self, method, path[len(decks_base):])
        if path == ytpages.BASE:
            return self._redirect(ytpages.BASE + "/")
        if path.startswith(ytpages.BASE + "/"):
            return self._youtube(method, path[len(ytpages.BASE):])
        if path.startswith(("/v/", "/c/")):      # the player's old addresses
            return self._redirect(ytpages.BASE + path)
        if path == "/books":
            return self._redirect("/books/")
        # the mobile interface's book shelf (docs/mobile.md): written from the
        # shelf on every request, where the library page is a file on disk
        if path in ("/m/books", "/m/books/", "/m/books/index.html"):
            if method != "GET":
                return self._method_not_allowed()
            if path != "/m/books/":
                return self._redirect("/m/books/")
            return self.send_html(mobile.books_page())
        # THE MOBILE INTERFACE AS AN APP (docs/mobile.md): its description,
        # its service worker -- at the top of the site, so that its scope is
        # all of it -- the page it keeps for when this server cannot be
        # reached, and the page that installs it, with the certificate a
        # phone is told to trust
        if path == "/manifest.webmanifest":
            if method != "GET":
                return self._method_not_allowed()
            return self.send_bytes(json.dumps(mobile.manifest(), ensure_ascii=False).encode("utf-8"),
                                   "application/manifest+json; charset=utf-8",
                                   extra={"Cache-Control": "no-cache"})
        if path == "/sw.js":
            if method != "GET":
                return self._method_not_allowed()
            with open(os.path.join(LIB, "sw.js"), "rb") as f:
                return self.send_bytes(f.read(), "text/javascript; charset=utf-8",
                                       extra={"Cache-Control": "no-cache"})
        if path in ("/m/offline", "/m/offline/"):
            if method != "GET":
                return self._method_not_allowed()
            if path != "/m/offline/":
                return self._redirect("/m/offline/")
            return self.send_html(mobile.offline_page())
        if path in ("/m/install", "/m/install/", "/m/install/index.html"):
            if method != "GET":
                return self._method_not_allowed()
            if path != "/m/install/":
                return self._redirect("/m/install/")
            tls = "http" if self.server.ssl_ctx is None else \
                "authority" if authority_der() else "own"
            return self.send_html(mobile.install_page(tls))
        if path == "/m/install/parseh-ca.crt":
            if method != "GET":
                return self._method_not_allowed()
            der = authority_der() if self.server.ssl_ctx is not None else None
            if der is None:
                return self.send_json({"error": "this server has no authority of its own to hand over"}, 404)
            # the authority's certificate and nothing else -- never a key.
            # Its own type, which is what makes an iPhone offer to install it
            # and an Android phone save it for Settings to install
            return self.send_bytes(der, "application/x-x509-ca-cert", extra={
                "Content-Disposition": 'inline; filename="Parseh-CA.crt"',
                "Cache-Control": "no-cache"})
        if path in ("/books/add", "/books/add/"):
            if method != "GET":
                return self._method_not_allowed()
            return self.send_html(newbook.page())
        if path == "/lib/langs.css":
            # generated from the registry on every request (it is tiny, and
            # no-store like every page), never a file on disk
            if method != "GET":
                return self._method_not_allowed()
            return self.send_bytes(languages.css().encode("utf-8"),
                                   "text/css; charset=utf-8")
        if path in ("/books/__upload", "/books/__empty", "/books/__restore"):
            if method != "POST":
                return self._method_not_allowed()
            if path.endswith("restore"):
                return self._shelf_restore("book")
            return (self._bundle_upload("book") if path.endswith("upload")
                    else self._book_empty())
        if path == "/books/__backup":
            if method != "GET":
                return self._method_not_allowed()
            return self._shelf_backup("book")
        # one segment or two: a book from before languages lies directly
        # under books/, is still read and still served (lib/books.py), and its
        # seams must not offer a + with no route behind it
        m = re.match(r"^(/books/[^/]+(?:/[^/]+)?)/__delete/?$", path)
        if m:
            if method != "POST":
                return self._method_not_allowed()
            book = book_dir(m.group(1))
            if not book:
                return self.send_json({"ok": False, "error": "no book here"}, 404)
            return self._book_delete(book)
        # more text onto the end of a book that is already here.  Addressed
        # the way __delete is -- by the book's own path, resolved and then
        # checked for a book.json -- so a slug never travels in a body and
        # can never name a directory outside books/.
        m = re.match(r"^(/books/[^/]+(?:/[^/]+)?)/__append/?$", path)
        if m:
            if method != "POST":
                return self._method_not_allowed()
            book = book_dir(m.group(1))
            if not book:
                return self.send_json({"ok": False, "error": "no book here"}, 404)
            return self._book_append(book)
        # a book built from a page: the PDF and the reader (./build.sh), or
        # the reader alone, as a job the page polls (lib/bookbuild.py).
        # Addressed by the book's own path like __delete -- from the library
        # page, and from inside the book's reader/, which asks relative to
        # itself -- and resolved by book_dir, so nothing off the shelf builds
        m = re.match(r"^(/books/.+?)(?:/reader)?/__build(/status)?/?$", path)
        if m:
            book = book_dir(m.group(1))
            if not book:
                return self.send_json({"ok": False, "error": "no book here"}, 404)
            if m.group(2):
                if method != "GET":
                    return self._method_not_allowed()
                return self.send_json(dict(bookbuild.status(book), ok=True))
            if method != "POST":
                return self._method_not_allowed()
            return self._book_build(book)
        m = re.match(r"^(/books/[^/]+(?:/[^/]+)?)/notes(/.*)?$", path)
        if m:
            # book_dir, as notes_library looks it up for a "+ Deck" copy
            book = book_dir(m.group(1))
            if not book:
                return self._not_found("no book here")
            return self._notes(method, book, m.group(1) + "/notes",
                               m.group(2) or "/")
        if path.startswith(("/books/", "/audiobook/", "/lib/", "/mt/")):
            if method == "GET" and path.rstrip("/").endswith("/__download"):
                return self._book_download()
            if method == "POST" and ("/__save/" in path or "/__narration/" in path
                                     or "/__edit/" in path or "/__divide/" in path
                                     or "/__reading/" in path
                                     or "/__struct/" in path or "/__clip/" in path
                                     or "/__lookup" in path or "/__words/" in path):
                return self._books_post(path)
            if method == "GET" and path.endswith("/__narration/status"):
                return self._narration_status()
            if method == "GET" and path.endswith("/__narration/export"):
                return self._narration_export()
            if method != "GET":
                return self._method_not_allowed()
            return self._static(path)
        self._not_found()

    # ---- the HTML guide
    def _guide(self, method, rel):
        """/guide/<rel>: the guide's front page, its assets and its compiled
        pages as plain files (lib/guidebuild.py says which), and the two
        routes the front page's "Compile the guide" button uses -- a POST that
        starts the compile and the status it polls."""
        if rel == "__status":
            if method not in ("GET", "HEAD"):
                return self._method_not_allowed()
            return self.send_json(guidebuild.status())
        if rel == "__compile":
            if method != "POST":
                return self._method_not_allowed()
            job, started = guidebuild.start()
            # a second press while it runs is answered with the compile
            # already running, which the page simply goes on following --
            # and its name on the activity list (activity_now), so the page
            # shows its own entry once and not twice
            return self.send_json(dict(job, ok=True, started=started,
                                       activity=guide_entry(job.get("started"))))
        if method not in ("GET", "HEAD"):
            return self._method_not_allowed()
        path = guidebuild.file_for(urllib.parse.unquote(rel))
        if path is None:
            # a page of a guide never compiled: its front page says why, and
            # compiles it (a script or a picture is simply not there yet)
            if rel.startswith("site/") and rel.endswith((".html", "/")) and not guidebuild.built()[0]:
                return self._redirect("/guide/")
            return self._not_found()
        return self.send_file(path)

    # ---- plain files, with Range
    def _static(self, path):
        if not static_ok(path):
            return self._not_found()
        # A FILM IS VIDEO, WHATEVER THE EXTENSION MEANS ELSEWHERE.  `.webm`
        # is registered as audio/webm here because that is what a book's
        # narration is; the same container holding a video's film was then
        # announced as audio to a <video> element, which played it only
        # because the browser sniffed past the label.
        # ONE REQUEST'S OVERRIDE, and not the connection's.  extensions_map is
        # a class attribute and a handler instance serves every request on a
        # keep-alive connection, so an override left on the instance would
        # follow the connection: a reader that had just fetched a film would
        # then be handed a book's narration as video.
        base = os.path.basename(urllib.parse.unquote(path))
        self.__dict__.pop("extensions_map", None)
        if bundle.is_media_name(base):
            ext = os.path.splitext(base)[1].lower()
            self.extensions_map = dict(type(self).extensions_map)
            self.extensions_map[ext] = "video/" + {
                ".m4v": "mp4", ".mkv": "x-matroska", ".ogv": "ogg",
                ".avi": "x-msvideo"}.get(ext, ext.lstrip("."))
        fs = self.translate_path(path)
        if os.path.isdir(fs):
            if not path.endswith("/"):
                return self._redirect(path + "/")
            if not os.path.isfile(os.path.join(fs, "index.html")):
                if os.path.isfile(os.path.join(fs, "reader", "index.html")):
                    return self._redirect(path + "reader/")
                m = re.match(r"^/books/([^/]+)/$", path)
                if m and languages.by_folder(m.group(1)):
                    # a language folder (books/persian/) has no page of its
                    # own: the library page lists every language
                    return self._redirect("/books/")
                if path == "/books/":
                    # NOT WRITTEN YET -- a fresh copy of the toolbox, before
                    # any book was built -- and it is only the list of what is
                    # on the shelf, so it is written now, from here, rather
                    # than sending anybody to a terminal to make it
                    lib = self._write_library()
                    if lib["ok"] and os.path.isfile(os.path.join(fs, "index.html")):
                        return self._redirect(path)
                    return self._not_found("the book library page could not be written: "
                                           + (lib["error"] or "make_index.py wrote nothing"))
                return self._not_found()
        elif not os.path.isfile(fs):
            return self._not_found()
        f = self.send_head()
        if f:
            try:
                if not self._head:
                    self.copyfile(f, self.wfile)
            except GONE:
                self.close_connection = True
            finally:
                f.close()

    def guess_type(self, path):
        # A licence without an extension (lib/mathjax/LICENSE, which the
        # licences page links to) is text to read, not a file to download.
        if os.path.basename(path) in ("LICENSE", "COPYING"):
            return "text/plain; charset=utf-8"
        return super().guess_type(path)

    def list_directory(self, path):
        # there is no listing of anything: a directory without its page is
        # simply not there
        self.send_html(not_found_page(), 404)
        return None

    def send_head(self):
        rng = self.headers.get("Range")
        if not rng:
            return super().send_head()
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(404)
            return None
        size = os.fstat(f.fileno()).st_size
        try:
            got = byte_range(rng, size)
        except ValueError:
            f.close()                    # not a byte range: the whole file
            return super().send_head()
        if got is None:
            f.close()
            self.send_response(416)
            self.send_header("Content-Range", "bytes */%d" % size)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        start, end = got
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        f.seek(start)
        return _Limited(f, end - start + 1)

    def _book_delete(self, book):
        """Take one book off the shelf.

        Moved to books/.trash/, not removed: a reading edition is weeks of
        glossing and may have a recording beside it that exists nowhere else,
        so the one gesture that ends it puts it somewhere still reachable.
        The answer says where, in as many words, because a person who has
        just pressed a red button wants to be told.

        The library page is rewritten afterwards, the way the reader is after
        an edit: it is a file on disk, and a page still listing a book that
        is gone is a link to a 404.
        """
        try:
            gone = booklib.trash_book(book)
        except OSError as e:
            return self.send_json({"ok": False, "error":
                                   "the book could not be moved to the trash "
                                   "(%s); nothing was changed" % e}, 500)
        r = subprocess.run([sys.executable, os.path.join(LIB, "make_index.py")],
                           cwd=ROOT, capture_output=True, text=True)
        out = {"ok": True, "dir": os.path.relpath(book, ROOT),
               "trash": os.path.relpath(gone, ROOT),
               "index": r.returncode == 0,
               "note": "it is in %s -- move it back and rebuild if this "
                       "was a mistake" % os.path.relpath(gone, ROOT)}
        if r.returncode != 0:
            # the book is off the shelf either way -- it was moved before
            # this ran -- but the page about to reload is the stale one,
            # still listing it, and a link on it now leads nowhere.  Say so
            # rather than let the reader think the button did nothing.
            out["warn"] = ("the book was moved, but the library page could "
                           "not be rewritten (%s); the next build of any book "
                           "rewrites it" % ((r.stderr or r.stdout or "").strip()
                                            .splitlines() or ["make_index.py failed"])[-1])
        self.send_json(out)

    def _book_build(self, book):
        """Start building one book: {"what": "pdf"}, the PDF and the reader
        (the default), or {"what": "html"}, the reader alone.  The answer
        comes at once, with the job; the page polls __build/status for the
        build's log and its end.  A book already building answers 409 with
        that build, so a second press never starts a second lualatex over the
        same .aux."""
        try:
            body = self._json_body()
        except ValueError:
            return self.send_json({"ok": False, "error": "the body is not JSON"}, 400)
        what = (body.get("what") if isinstance(body, dict) else None) or "pdf"
        if what not in bookbuild.WAYS:
            return self.send_json({"ok": False, "error": "no such build: %r (%s)"
                                   % (what, ", ".join(bookbuild.WAYS))}, 400)
        job, started = bookbuild.start(book, what)
        # the name of this build on the activity list (activity_now), so the
        # page that asked can show its own entry once and not twice -- the
        # build already running, when that is the answer
        act = build_entry(book, job.get("started"))
        if not started:
            return self.send_json(dict(job, ok=False, activity=act,
                                       error="it is already being built"), 409)
        self.send_json(dict(job, ok=True, activity=act))

    def _video_delete(self):
        """Take one video off the shelf, into videos/.trash/ -- the very
        directory a replaced video already goes to (ytpages.trash_video), so
        there is one place to look and one rule about what is in it."""
        body = self._json_body()
        if body is None:
            return
        d = self._video_dir(body.get("video") or "")
        if not d:
            return self.send_json({"ok": False, "error": "no such video"}, 404)
        try:
            gone = ytpages.trash_video(d)
        except OSError as e:
            return self.send_json({"ok": False, "error":
                                   "the video could not be moved to the trash "
                                   "(%s); nothing was changed" % e}, 500)
        self.send_json({"ok": True, "dir": os.path.relpath(d, ROOT),
                        "trash": os.path.relpath(gone, ROOT),
                        "note": "it is in %s -- move it back if this was a "
                                "mistake" % os.path.relpath(gone, ROOT)})

    # ---- the dictionary behind a chunk nobody has glossed
    def _lookup(self, code, body=None, gloss="en"):
        """What a dictionary has to say about the words of one chunk.

        Read-only, in every sense: it opens the language's dict/<code>.db
        read-only, it writes nothing anywhere, and what it answers is marked
        in both readers as a dictionary and not as a gloss.  NOTHING IN THE
        READING PANEL TURNS AN ENTRY INTO A GLOSS -- there has been no `use`
        button there for a while.  That happens only in the chunk editor,
        whose sources column (the book's #chside, the player's .eside) has a
        button per hit that puts an entry into the edit box and nothing more:
        a \\dw, or for a verb the \\vb below.  Nothing is written until the
        chunk is saved, down the ordinary edit route with the ordinary
        checkers on it, like any other edit.

        A VERB HIT CARRIES ITS \\vb (`hit["vb"]`), built by lib/verbs from the
        dictionary's own conjugation table wherever the language has a
        recipe: TeX for a book's vocabulary line, plain text for a video's, a
        short line for the panel.  Both routes come through here -- the
        book's `__lookup` and the player's /youtube/api/lookup -- so both
        readers get it from this one call.  It is an extra on the answer and
        never a condition of it: a failure is told on stderr once per
        language and the words go back without it.  `gloss` goes with it
        because Wiktionary's senses are English, and a book glossed in
        another language is given a \\vb with no meaning in it rather than an
        English one.

        Two shapes of question, because a page has to know whether to draw
        the button before it has anything to look up:

            {"about": 1}          what is installed for this language
            {"text": "..."}       and what does it say about this chunk
            {"text", "words"}     ... divided where the chunk's word line
                                  divides it, one row per word, `i` its
                                  place among the line's words
            {"text", "senses": "all"}
                                  ... with every sense of each hit, the
                                  ones past the first three as `more`

        THREE THINGS, INDEPENDENTLY.  The dictionary and the parallel corpus
        are separate downloads and either can be here without the other, so
        each is reported and each is asked separately.  This used to consult
        the corpus only where a dictionary was installed and to gate the whole
        panel on the dictionary alone -- which meant a language with a corpus
        and no dictionary had a corpus it could not reach.  (The third, the
        translation model, is not the server's to report: it is files under
        mt/ that the reader fetches itself.)

        `available: false` is a perfectly good answer and not an error: a
        language with none of them is read exactly as it is read today.
        """
        if body is None:
            body = self._json_body()
            if body is None:
                return
        have = lookup.available(code)
        has_corpus = corpus.available(code, gloss)
        out = {"ok": True, "lang": code, "gloss": gloss,
               "available": have,
               "corpus_available": has_corpus,
               # is there anything at all behind the switch, so the reader
               # can draw a button nobody presses in vain
               "help": bool(have or has_corpus),
               # WHETHER ITS SENSES ARE DEFINITIONS: a dictionary explaining
               # its words in their own language -- English's -- whose senses
               # both readers keep behind a switch of their own
               "definitions": bool(have and lookup.defines(code)),
               "source": lookup.about(code) or {},
               "corpus": corpus.about(code, gloss) if has_corpus else {}}
        text = (body.get("text") or "")[:LOOKUP_TEXT]
        if not body.get("about") and text.strip():
            corpus_only = bool(body.get("corpus_only"))
            if have and not corpus_only:
                # THE CHUNK'S OWN WORDS, where it has a word line (Japanese,
                # Chinese: `住んでいました(すんでいました) 。`).  A person divided
                # the text there, so each word is looked up as written, one
                # row each with its place in the line, and none is cut again
                # by longest match.  A line that does not parse is no word
                # line, and the text is looked up as it always was.
                pieces = word_pieces(body.get("words"))
                if pieces is None:
                    r = lookup.look_up(code, text)
                else:
                    r = lookup.look_up(code, text, pieces=pieces, authoritative=True)
                    # look_up's `i` is the row's place in the PIECES, which
                    # leave the punctuation out and stop at the cap; a page
                    # holds the LINE, so it is given the word's place there
                    # -- parse(line)[i], in any of the three parsers -- and
                    # has nothing of this filter to repeat, no Unicode table
                    # and no count of characters that might not be its own
                    for w in (r or {}).get("words") or []:
                        w["i"] = pieces[w["i"]]["at"]
                # THE VERB ENTRIES MAY COST THE \vb AND NEVER THE LOOKUP.
                # verbs.attach already swallows a recipe's own failure; this
                # is the second guard, for a bug in the core itself -- and the
                # import is here rather than at the top of the file so that
                # even a package that will not import costs a verb's \vb and
                # not the server.  Told once per language: the reader's
                # look-ahead asks ten chunks at a time, and the first
                # traceback is the one worth reading.
                # THE SENTENCE GOES WITH IT, where the reader sent one (the
                # book's and the player's both do): a chunk is often less
                # than a clause, and German leaves a separable verb's prefix
                # at the clause's end -- `und stand langsam` is stehen, its
                # sentence `... und stand langsam von seinem Stuhl auf.` is
                # aufstehen.
                sentence = body.get("sentence")
                sentence = sentence[:1000] if isinstance(sentence, str) else ""
                try:
                    import verbs
                    verbs.attach(r, code, text, gloss, sentence=sentence)
                except Exception:
                    told = getattr(Handler, "_verbs_told", None)
                    if told is None:
                        told = Handler._verbs_told = set()
                    if code not in told:
                        told.add(code)
                        sys.stderr.write("lookup: the \\vb entries for %r failed; "
                                         "the words go back without them "
                                         "(said once)\n" % code)
                        traceback.print_exc()
                # THE WHOLE ENTRY, where the page asks for it (`"senses":
                # "all"`): a reader with the definitions switched on is given
                # every sense and not the first three -- as `more`, beside
                # `senses`, which stay what they were for all that reads them
                if body.get("senses") == "all" and r:
                    lookup.more_senses(r)
                out["words"] = (r or {}).get("words") or []
            # AND WHAT SOMEBODY HAS ALREADY TRANSLATED.  The dictionary says
            # what a word can mean and cannot say which; a sentence a person
            # translated, holding the same rare words, can -- so it rides
            # back on the same request rather than costing the panel a
            # second round trip.
            if has_corpus:
                try:
                    offset = max(0, int(body.get("corpus_offset") or 0))
                    limit = max(1, min(50, int(body.get("corpus_limit") or
                                                corpus.MAX_PAIRS)))
                except (TypeError, ValueError):
                    offset, limit = 0, corpus.MAX_PAIRS
                try:
                    m = corpus.look_up(code, gloss, text, limit=limit,
                                       offset=offset)
                except Exception:
                    m = {}
                out["pairs"] = m.get("pairs") or []
                out["pairs_more"] = bool(m.get("more"))
                out["pairs_offset"] = offset
        return self.send_json(out)

    # ---- a word line proposed, for a chunk that has none
    def _words_propose(self, code, body=None):
        """How a machine would divide one chunk's text into words and read
        them -- lib/words.py's proposal, for the chunk editor to put in front
        of the person who corrects it.

            {"text": "山へ柴刈りに"}  ->  {"ok", "words", "available", "python"}

        Read-only, like _lookup: nothing is written anywhere, and a line
        reaches the document only when somebody saves the chunk down the
        ordinary edit route, with the ordinary checkers on it.  `available:
        false` with no words is the ordinary answer on a Python without the
        analyzers -- serve.sh falls back to the machine's python3 -- and
        `python` names that Python, because "not installed" means not
        installed in the one that is running.
        """
        if body is None:
            body = self._json_body()
            if body is None:
                return
        text = body.get("text")
        if not isinstance(text, str):
            return self.send_json({"ok": False, "error": "text must be the "
                                   "chunk's text"}, 400)
        if len(text) > PROPOSE_TEXT:
            return self.send_json({"ok": False, "error": "text is %d characters: a "
                                   "proposal is made for one chunk, of at most %d"
                                   % (len(text), PROPOSE_TEXT)}, 400)
        # the chunk's own kana (or pinyin) as the editor holds it, if any:
        # each word is given its stretch of it (lib/words.py)
        reading = body.get("reading")
        if reading is not None and not isinstance(reading, str):
            return self.send_json({"ok": False, "error": "reading must be the "
                                   "chunk's reading, as text"}, 400)
        if reading and len(reading) > 8 * PROPOSE_TEXT:
            return self.send_json({"ok": False, "error": "reading is %d characters: "
                                   "too long for one chunk" % len(reading)}, 400)
        L = languages.get_or_default(code if isinstance(code, str) else "")
        have = bool(L.words) and words.available(L.code)
        line = ""
        if have and text.strip():
            with WORDS_LOCK:
                line = words.line(text, L.code, reading or "")
        return self.send_json({"ok": True, "words": line, "available": have,
                               "python": sys.executable})

    def _lookup_api(self, what):
        """What the /lookup/ page asks: list the dictionaries, build one,
        throw one away.

        The whole of what `python3 lib/getdict.py <code>` did, which is the
        right comparison, because a command nobody finds is a feature nobody
        has.  Building runs in a thread and reports through DICT_JOBS, so the
        page can draw a bar rather than a hung request.
        """
        body = self._json_body()
        if body is None:
            return
        if what == "decompositions":
            with DECOMPOSITION_LOCK:
                jobs = {key: dict(value) for key, value in DECOMPOSITION_JOBS.items()}
            return self.send_json({"ok": True, "packs": decomposition.packs(), "jobs": jobs})
        if what == "decompose":
            try:
                result = decomposition.character_tree(body.get("code"), body.get("character"))
            except (ValueError, TypeError):
                return self.send_json({"ok": False, "error": "select one Japanese or Chinese character"}, 400)
            except (OSError, sqlite3.Error) as e:
                return self.send_json({"ok": False, "error": "The local component data could not be read. Reinstall it from setup."}, 500)
            return self.send_json(result)
        if what in ("getdecomposition", "dropdecomposition"):
            source = body.get("source")
            if not isinstance(source, str) or source not in decomposition.PACKS:
                return self.send_json({"ok": False, "error": "unknown decomposition source"}, 400)
            with DECOMPOSITION_LOCK:
                if DECOMPOSITION_JOBS.get(source, {}).get("running"):
                    return self.send_json({"ok": False, "error": "this component pack is being installed"}, 409)
                if what == "dropdecomposition":
                    try:
                        decomposition.path_for(source).unlink(missing_ok=True)
                    except OSError as e:
                        return self.send_json({"ok": False, "error": str(e)}, 500)
                    DECOMPOSITION_JOBS.pop(source, None)
                    return self.send_json({"ok": True})
                state = {"running": True, "say": "Starting…", "error": "",
                         "started": time.time()}
                DECOMPOSITION_JOBS[source] = state

            def work():
                import getdecomposition
                def update(**values):
                    with DECOMPOSITION_LOCK:
                        state.update(values)
                try:
                    getdecomposition.build(source, say=lambda message: update(say=message))
                except Exception as e:
                    update(error=str(e))
                finally:
                    update(running=False, finished=time.time())
            threading.Thread(target=work, daemon=True).start()
            return self.send_json({"ok": True})
        if what == "models":
            return self.send_json({"ok": True,
                                   "models": lookuppage.models(),
                                   "engine": getmt.engine_ready(),
                                   "jobs": dict(MT_JOBS)})
        if what == "getmodel":
            return self._getmodel(body.get("code") or "", body.get("gloss") or "en")
        if what == "dropmodel":
            code = (body.get("code") or "").strip()
            gloss = (body.get("gloss") or "").strip()
            if code not in languages.LANGS or gloss not in languages.LANGS:
                return self.send_json({"ok": False, "error": "no such language"}, 404)
            job = MT_JOBS.get("%s-%s" % (code, gloss))
            if job and job.get("running"):
                return self.send_json({"ok": False, "error":
                                       "it is being fetched right now"}, 409)
            d = getmt.path_for(code, gloss)
            try:
                if os.path.isdir(d):
                    for n in os.listdir(d):
                        os.unlink(os.path.join(d, n))
                    os.rmdir(d)
            except OSError as e:
                return self.send_json({"ok": False, "error": str(e)}, 500)
            return self.send_json({"ok": True})
        if what == "corpora":
            return self.send_json({"ok": True,
                                   "corpora": lookuppage.corpora(),
                                   "jobs": dict(CORPUS_JOBS)})
        if what == "getcorpus":
            return self._getcorpus(body.get("code") or "",
                                   body.get("gloss") or "en")
        if what == "dropcorpus":
            code = (body.get("code") or "").strip()
            gloss = (body.get("gloss") or "").strip()
            if code not in languages.LANGS or gloss not in languages.LANGS:
                return self.send_json({"ok": False, "error": "no such language"}, 404)
            job = CORPUS_JOBS.get("%s-%s" % (code, gloss))
            if job and job.get("running"):
                return self.send_json({"ok": False, "error":
                                       "it is being built right now"}, 409)
            try:
                p = corpus.path_for(code, gloss)
                if os.path.isfile(p):
                    os.unlink(p)
            except OSError as e:
                return self.send_json({"ok": False, "error": str(e)}, 500)
            return self.send_json({"ok": True})
        if what == "syn":
            return self.send_json({"ok": True, "syn": lookuppage.synonym_table(),
                                   "job": dict(SYN_JOB)})
        if what == "getsyn":
            return self._getsyn()
        if what == "dropsyn":
            if SYN_JOB.get("running"):
                return self.send_json({"ok": False, "error":
                                       "it is being fetched right now"}, 409)
            try:
                import getsyn
                getsyn.remove()
            except OSError as e:
                return self.send_json({"ok": False, "error": str(e)}, 500)
            return self.send_json({"ok": True})
        if what == "dicts":
            return self.send_json({"ok": True, "dicts": lookuppage.dictionaries(),
                                   "jobs": dict(DICT_JOBS)})
        if what == "getdict":
            return self._getdict(body.get("code") or "")
        if what == "dropdict":
            code = (body.get("code") or "").strip()
            if code not in languages.LANGS:
                return self.send_json({"ok": False, "error": "no such language"}, 404)
            # the page hides the button while a build runs; this is the other
            # half of that, because deleting a file being written to is a
            # half-built dictionary that reports itself as whole
            job = DICT_JOBS.get(code)
            if job and job.get("running"):
                return self.send_json({"ok": False, "error":
                                       "it is being built right now"}, 409)
            try:
                p = lookup.path_for(code)
                if os.path.isfile(p):
                    os.unlink(p)
            except OSError as e:
                return self.send_json({"ok": False, "error": str(e)}, 500)
            return self.send_json({"ok": True})
        return self.send_json({"ok": False, "error": "nothing to POST here"}, 404)

    def _getdict(self, code):
        """Fetch and build one language's dictionary, in the background.

        It is a download of tens of megabytes and a minute or two of work, so
        it cannot be done inside a request: the thread reports into DICT_JOBS
        and the page polls.  One at a time per language, because pressing the
        button twice should not fetch it twice.
        """
        code = (code or "").strip()
        if code not in languages.LANGS:
            return self.send_json({"ok": False, "error": "no such language"}, 404)
        job = DICT_JOBS.get(code)
        if job and job.get("running"):
            return self.send_json({"ok": True, "already": True})

        def work():
            import getdict
            state = {"running": True, "say": "starting…", "error": "",
                     "started": time.time()}
            DICT_JOBS[code] = state
            try:
                getdict.build(code, say=lambda m: state.__setitem__("say", m.strip()))
                state["say"] = "done"
            except SystemExit as e:
                state["error"] = str(e)
            except Exception as e:
                state["error"] = "%s: %s" % (type(e).__name__, e)
            finally:
                state["finished"] = time.time()
                state["running"] = False

        threading.Thread(target=work, daemon=True).start()
        return self.send_json({"ok": True})

    def _getsyn(self):
        """Fetch and build the aligner's synonym table, in the background.

        The same arrangement as _getdict, with no code and no gloss: there
        is one file, not one per language, so there is one job to poll
        rather than a dict of them.
        """
        if SYN_JOB.get("running"):
            return self.send_json({"ok": True, "already": True})

        def work():
            import getsyn
            state = {"running": True, "say": "starting…", "error": "",
                     "started": time.time()}
            SYN_JOB.clear()
            SYN_JOB.update(state)
            try:
                getsyn.get(say=lambda m: SYN_JOB.__setitem__("say", m.strip()),
                          force=True)
                SYN_JOB["say"] = "done"
            except SystemExit as e:
                SYN_JOB["error"] = str(e)
            except Exception as e:
                SYN_JOB["error"] = "%s: %s" % (type(e).__name__, e)
            finally:
                SYN_JOB["finished"] = time.time()
                SYN_JOB["running"] = False

        threading.Thread(target=work, daemon=True).start()
        return self.send_json({"ok": True})

    def _getmodel(self, code, gloss):
        """Fetch one pair's translation model, in the background.

        Twenty megabytes and an engine of five, so it cannot happen inside a
        request; the same job table and the same polling as the dictionaries.
        """
        code = (code or "").strip()
        gloss = (gloss or "").strip()
        if code not in languages.LANGS or gloss not in languages.LANGS:
            return self.send_json({"ok": False, "error": "no such language"}, 404)
        if code == gloss:
            return self.send_json({"ok": False, "error":
                                   "a language translated into itself is a copy"},
                                  400)
        key = "%s-%s" % (code, gloss)
        job = MT_JOBS.get(key)
        if job and job.get("running"):
            return self.send_json({"ok": True, "already": True})

        def work():
            state = {"running": True, "say": "starting…", "error": "",
                     "started": time.time()}
            MT_JOBS[key] = state
            try:
                getmt.build(code, gloss,
                            say=lambda m: state.__setitem__("say", m.strip()))
                state["say"] = "done"
            except SystemExit as e:
                state["error"] = str(e)
            except Exception as e:
                state["error"] = "%s: %s" % (type(e).__name__, e)
            finally:
                state["finished"] = time.time()
                state["running"] = False

        threading.Thread(target=work, daemon=True).start()
        return self.send_json({"ok": True})

    def _getcorpus(self, code, gloss):
        """Fetch and build one pair's corpus, in the background.

        The same arrangement as _getdict and for the same reason -- the
        English export alone is 25 MB and has to be read through -- with the
        pair as the key, because Persian glossed in English and Persian
        glossed in Italian are two different files.
        """
        code = (code or "").strip()
        gloss = (gloss or "").strip()
        if code not in languages.LANGS or gloss not in languages.LANGS:
            return self.send_json({"ok": False, "error": "no such language"}, 404)
        if code == gloss:
            return self.send_json({"ok": False, "error":
                                   "a language glossed in itself has nothing "
                                   "to translate"}, 400)
        key = "%s-%s" % (code, gloss)
        job = CORPUS_JOBS.get(key)
        if job and job.get("running"):
            return self.send_json({"ok": True, "already": True})

        def work():
            import getcorpus
            state = {"running": True, "say": "starting…", "error": "",
                     "started": time.time()}
            CORPUS_JOBS[key] = state
            try:
                getcorpus.build(code, gloss,
                                say=lambda m: state.__setitem__("say", m.strip()))
                state["say"] = "done"
            except SystemExit as e:
                state["error"] = str(e)
            except Exception as e:
                state["error"] = "%s: %s" % (type(e).__name__, e)
            finally:
                state["finished"] = time.time()
                state["running"] = False

        threading.Thread(target=work, daemon=True).start()
        return self.send_json({"ok": True})

    # ---- the notes beside a book or a video, under their own prefix
    def _notes(self, method, content_dir, prefix, sub):
        """The studio, serving one content's own `markdown/` directory.

        Not a second editor and not a copy of one: these are the studio's
        very routes, run with two things pointed elsewhere for the length of
        the request -- the library (store.use_library) and the prefix its
        links carry (server.use_mount) -- and with the build, the PDF and the
        LaTeX download refused, because a note is read on its page and
        nowhere else.  Everything else the studio can do, a note can have:
        the same marks, the same hover tools, the same renderer.

        Both are thread-local and both are put back in the `finally`, so a
        request cannot leave this thread pointing at somebody's book.
        """
        was_lib = studio.store.use_library(studio.notes.dir_for(content_dir))
        was_mount = studio.use_mount(prefix, html_only=True)
        try:
            # notes written before names: told apart and their links by
            # uid written by name, the first time this process opens them
            try:
                studio.store.migrate_once()
            except Exception as e:   # noqa: BLE001 -- never fails the request
                sys.stderr.write("[notes] %s: links not brought up to names (%s)\n"
                                 % (prefix, e))
            m = re.match(r"^/api/marks/?$", sub or "/")
            if m:
                if method == "GET":
                    return self._notes_marks(content_dir)
                if method == "POST":
                    return self._notes_new(content_dir)
                return self._method_not_allowed()
            return self._studio(method, sub)
        finally:
            studio.restore_mount(was_mount)
            studio.store.use_library(was_lib)

    def _notes_marks(self, content_dir):
        """Every note beside this content, for the marks a page draws."""
        self.send_json({"ok": True, "notes": studio.notes.index(content_dir)})

    def _notes_new(self, content_dir):
        """A new empty note in one of the gaps.  The page says which gap; the
        language is the content's own, so a note opens in the same face and
        direction the text beside it is set in."""
        body = self._json_body()
        if body is None:
            return
        side, kind, at = body.get("side"), body.get("kind"), body.get("at")
        target = body.get("target") or languages.DEFAULT
        try:
            studio.notes.format_anchor(side, kind, at)   # refuse before writing
            meta = studio.notes.create(content_dir, side, kind, at, target)
        except (ValueError, OSError) as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        self.send_json({"ok": True, "note": {
            "id": meta["id"], "title": meta.get("title") or "",
            "anchor": {"side": side, "kind": kind, "at": str(at)}}})

    # ---- the studio, under its prefix
    def _studio(self, method, sub):
        sub = sub or "/"
        for m, pattern, fn in studio.ROUTES:
            if m != method:
                continue
            match = re.match(pattern, sub)
            if not match:
                continue
            try:
                return fn(self, *match.groups())
            except KeyError:
                return self.send_json({"error": "document not found"}, 404)
            except json.JSONDecodeError:
                return self.send_json({"error": "bad JSON body"}, 400)
            except studio.store.StoreError as e:
                return self.send_json({"error": str(e)}, 400)
            except GONE:
                raise
            except Exception as e:      # surface, don't crash the thread
                traceback.print_exc()
                return self.send_json({"error": str(e)}, 500)
        if method == "GET":
            return self.send_html(studio.render_template("404.html", {}), 404)
        return self.send_json({"error": "no such endpoint"}, 404)

    # ---- the video player, under its prefix
    def _youtube(self, method, sub):
        # a video's own notes, before anything else claims the path
        m = re.match(r"^/v/([^/]+)/notes(/.*)?$", sub or "/")
        if m:
            d = self._video_dir(m.group(1))
            if not d:
                return self.send_json({"ok": False, "error": "no such video"}, 404)
            return self._notes(method, d,
                               ytpages.BASE + "/v/%s/notes" % m.group(1),
                               m.group(2) or "/")
        if method == "POST":
            if sub == "/api/transcript":
                return ytpages.api_transcript(self)
            if sub == "/api/prepare":
                return ytpages.api_prepare(self)
            if sub == "/api/add":
                return ytpages.api_add(self)
            if sub == "/api/upload":
                return self._bundle_upload("video")
            if sub == "/api/restore":
                return self._shelf_restore("video")
            if sub == "/api/empty":
                return self._video_empty()
            if sub == "/api/local":
                return self._video_local()
            if sub == "/api/edit":
                return self._video_edit_chunk()
            if sub == "/api/editmeta":
                return self._video_edit_meta()
            if sub == "/api/divide":
                return self._video_divide_chunk()
            if sub == "/api/times":
                return self._video_times()
            if sub == "/api/waveform":
                return self._video_waveform()
            if sub == "/api/delete":
                return self._video_delete()
            if sub == "/api/clip":
                return self._video_clip("cut")
            if sub == "/api/peaks":
                return self._video_clip("peaks")
            if sub == "/api/lookup":
                body = self._json_body()
                if body is None:
                    return
                d = self._video_dir(body.get("video") or "")
                if not d:
                    return self.send_json({"ok": False, "error": "no such video"}, 404)
                meta = json.load(io.open(os.path.join(d, "video.json"), encoding="utf-8"))
                return self._lookup(meta.get("language") or "",
                                    body, meta.get("gloss") or "en")
            if sub == "/api/words":
                body = self._json_body()
                if body is None:
                    return
                vid = body.get("video")
                d = self._video_dir(vid if isinstance(vid, str) else "")
                if not d:
                    return self.send_json({"ok": False, "error": "no such video"}, 404)
                with io.open(os.path.join(d, "video.json"), encoding="utf-8") as f:
                    meta = json.load(f)
                return self._words_propose(meta.get("language") or "", body)
            return self.send_json({"ok": False, "error": "nothing to POST here"}, 404)
        if method != "GET":
            return self._method_not_allowed()
        if sub == "/api/backup":
            return self._shelf_backup("video")
        m = re.match(r"^/v/([^/]+)/__download/?$", sub)
        if m:
            return self._video_download(m.group(1))
        if sub == "/":
            return self.send_html(ytpages.index_page())
        if sub in ("/add", "/add/"):
            return self.send_html(ytpages.add_page())
        m = re.match(r"^/c/([^/]+)/?$", sub)
        if m:
            page = ytpages.channel_page(m.group(1))
            if page is None:
                return self.send_html(ytpages.not_found_page(
                    "no such channel", ytpages.BASE + "/", "all channels"), 404)
            return self.send_html(page)
        m = re.match(r"^/v/([^/]+)/?$", sub)
        if m:
            vid = m.group(1)
            page = None if ".." in vid else ytpages.player_page(vid)
            if page is None:
                return self.send_html(ytpages.not_found_page(
                    "no such video: no youtube/videos/<language>/%s/video.json" % vid,
                    ytpages.BASE + "/", "all channels"), 404)
            return self.send_html(page)
        if sub.startswith(("/lib/", "/videos/")):
            return self._static(ytpages.BASE + sub)
        self._not_found()

    # ---- the Anki store, shared by both readers
    def _anki(self, method, path):
        if method == "GET":
            if path == "/anki/decks":
                return ytpages.anki_decks(self)
            if path in ("/anki/sync", "/anki/sync/"):
                return self.send_html(ytpages.sync_page())
            if path == "/anki/sync/inbox":
                return ytpages.sync_inbox(self)
            # a deck lives under its language: /anki/build/<folder>/<slug>.apkg.
            # The one-level form is what the pages sent before the languages
            # (and what a bookmark still holds): it is answered whenever the
            # slug names one deck, and refused with the candidates when two
            # languages share it -- see ytpages.anki_build
            m = re.match(r"^/anki/build/([a-z]+)/([a-z0-9][a-z0-9-]*)\.apkg$", path)
            if m:
                return ytpages.anki_build(self, m.group(2), m.group(1))
            m = re.match(r"^/anki/build/([a-z0-9][a-z0-9-]*)\.apkg$", path)
            if m:
                return ytpages.anki_build(self, m.group(1))
            return self._not_found()
        if method == "POST":
            if path == "/anki/cards":
                return ytpages.anki_add_card(self)
            if path == "/anki/preview":
                return ytpages.anki_preview(self)
            if path == "/anki/sync/upload":
                return ytpages.sync_upload(self)
            if path == "/anki/sync/run":
                return ytpages.sync_run(self)
            if path == "/anki/sync/bootstrap":
                return ytpages.sync_bootstrap(self)
            return self.send_json({"ok": False, "error": "nothing to POST here"}, 404)
        self._method_not_allowed()

    # ---- the clip tray: what a card's recording is cut into (lib/clips.py)
    def _clips(self, method, path):
        q = lambda k: (self.query.get(k) or [""])[0]
        if path == "/clips":
            return self._redirect("/clips/")
        if path == "/clips/":
            if method != "GET":
                return self._method_not_allowed()
            return self.send_html(clips_page())
        m = re.match(r"^/clips/media/(?:(audio|images)/)?([^/]+)$", path)
        if m:
            if method != "GET":
                return self._method_not_allowed()
            name = urllib.parse.unquote(m.group(2))
            want = {"audio": "audio", "images": "image"}.get(m.group(1))
            try:
                if want and clips.kind_of(name) != want:
                    raise KeyError(name)
                return self.send_file(clips.path(name))
            except KeyError:
                return self.send_json({"ok": False, "error": "no such clip"}, 404)
        if path == "/clips/api/status":
            if method != "GET":
                return self._method_not_allowed()
            have = audiofile.have_ffmpeg()
            return self.send_json({"ok": True, "ffmpeg": have,
                                   "format": audiofile.best_output()[0] if have else None})
        if path == "/clips/api/list":
            if method != "GET":
                return self._method_not_allowed()
            kind = q("kind")
            if kind not in ("", "audio", "image"):
                return self.send_json({"ok": False, "error": "kind is audio or image"}, 400)
            return self.send_json({"ok": True, "clips": clips.listing(q("lang") or None,
                                                                      kind or None)})
        if path == "/clips/api/upload":
            if method != "POST":
                return self._method_not_allowed()
            kind = q("kind") or "audio"
            if kind not in ("audio", "image"):
                return self.send_json({"ok": False, "error": "kind is audio or image"}, 400)
            try:
                source = json.loads(q("source")) if q("source") else {}
            except (ValueError, RecursionError):   # not JSON, or nested past reading
                source = {}
            meta = {"lang": q("lang"), "label": q("label"), "text": q("text"),
                    "source": source if isinstance(source, dict) else {}}
            try:
                save = clips.save_audio if kind == "audio" else clips.save_image
                rec = save(self._raw, q("hint"), meta)
            except clips.ClipError as e:
                return self.send_json({"ok": False, "error": str(e)}, 400)
            return self.send_json({"ok": True, "clip": rec}, 201)
        if path == "/clips/api/preview":
            if method != "POST":
                return self._method_not_allowed()
            return self._clips_preview()
        if path == "/clips/api/empty":
            if method != "POST":
                return self._method_not_allowed()
            return self.send_json({"ok": True, "deleted": clips.empty()})
        m = re.match(r"^/clips/api/([^/]+)$", path)
        if m:
            if method != "DELETE":
                return self._method_not_allowed()
            try:
                clips.delete(urllib.parse.unquote(m.group(1)))
            except KeyError:
                return self.send_json({"ok": False, "error": "no such clip"}, 404)
            return self.send_json({"ok": True})
        return self.send_json({"ok": False, "error": "nothing here"}, 404)

    def _clips_preview(self):
        """A card's markdown rendered by the studio's own renderer, the way a
        deck or a document will show it -- its recordings and pictures still
        in the tray, so the asset base is the tray's, and its `[…](doc:Name)`
        links resolved in the studio's library, where a deck resolves them."""
        body = self._json_body()
        if body is None:
            return
        md = body.get("markdown")
        if not isinstance(md, str) or len(md) > 200000:
            return self.send_json({"ok": False, "error": "markdown must be text"}, 400)
        L = languages.get(body.get("lang") if isinstance(body.get("lang"), str) else "",
                          languages.DEFAULT)
        if not md.startswith("---\n"):
            md = "---\ntarget: %s\n---\n\n%s" % (L.code, md)
        try:
            doc = studio.htmlgen.render_document(md, colophon=False, asset_base=clips.URL,
                                                 docs=studio.store.doc_index(),
                                                 editor_preview=False)
        except Exception as e:           # a half-written card is not a server fault
            return self.send_json({"ok": False, "error": "%s: %s" % (type(e).__name__, e)}, 400)
        self.send_json({"ok": True, "html": doc["html"]})

    def _book_clip(self, what):
        """`<reader>/__clip/cut` and `__clip/peaks`: one of the book's own
        recordings, named by its id (`n1`...; none named is the first), cut
        into the tray or read as a waveform."""
        b = self._narration_book()
        if not b:
            return self.send_json({"ok": False, "error": "no book here"}, 404)
        body = self._json_body()
        if body is None:
            return
        nid = body.get("narration") or ""
        if not isinstance(nid, str):
            return self.send_json({"ok": False, "error": "narration is a recording's id"}, 400)
        recs = b.narrations
        rec = b.narration(nid) if nid else (recs[0] if recs else None)
        if rec is None:
            return self.send_json({"ok": False, "error": "this book has no recording %s"
                                   % (repr(nid) if nid else "at all")}, 400)
        if not rec["audio"] or not os.path.isfile(rec["audio"]):
            return self.send_json({"ok": False, "error": "the recording %s is not on this machine"
                                   % (rec["audio_rel"] or rec["id"])}, 400)
        where = "/" + os.path.relpath(b.dir, ROOT).replace(os.sep, "/")
        return self._clip_from(what, rec["audio"], body, b.lang.code,
                               {"kind": "book", "book": where, "narration": rec["id"],
                                "url": where + "/reader/"})

    def _video_clip(self, what):
        """`/youtube/api/clip` and `/youtube/api/peaks`: the same two, out of a
        video's own film.  A YouTube video has no file here to cut."""
        body = self._json_body()
        if body is None:
            return
        vid = body.get("video")
        d = self._video_dir(vid if isinstance(vid, str) else "")
        if not d:
            return self.send_json({"ok": False, "error": "no such video"}, 404)
        film = bundle.film_at(d)
        if not film:
            return self.send_json({"ok": False,
                                   "error": "only a film on this machine can be cut"}, 400)
        try:
            with io.open(os.path.join(d, "video.json"), encoding="utf-8") as f:
                meta = json.load(f)
        except (OSError, ValueError):
            meta = {}
        lang = meta.get("language") if isinstance(meta.get("language"), str) else ""
        return self._clip_from(what, os.path.join(d, film), body, lang,
                               {"kind": "film", "video": vid,
                                "title": meta.get("title") if isinstance(meta.get("title"), str) else ""})

    def _clip_from(self, what, src, body, lang, source):
        """Cut [start, end] of `src` into the tray (201 with the record), or
        answer its waveform.  Without ffmpeg: 409 with `record: true`, which
        tells the page to record the clip in the browser instead."""
        try:
            start, end = clips.span(body.get("start"), body.get("end"))
        except clips.ClipError as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        if not audiofile.have_ffmpeg():
            return self.send_json({"ok": False, "error": "ffmpeg is not installed",
                                   "record": True}, 409)
        if what == "peaks":
            # anything but a finite number (NaN, Infinity, 1e400 all parse)
            # draws the default
            n = clips.number(body.get("buckets", 400))
            n = 400 if n is None else n
            try:
                peaks = audiofile.peaks(src, start, end, max(1, min(4000, int(n))))
            except audiofile.AudioError as e:
                return self.send_json({"ok": False, "error": str(e)}, 400)
            return self.send_json({"ok": True, "peaks": peaks, "start": start, "end": end})

        def text(k):
            v = body.get(k)
            return v if isinstance(v, str) else ""
        if source.get("kind") == "film":
            source["url"] = ytpages.BASE + "/v/%s/#t=%d" % (source["video"], int(start))
        meta = {"lang": text("lang") or lang, "label": text("label"), "text": text("text"),
                "source": dict(source, start=start, end=end)}
        try:
            rec = clips.cut(src, start, end, text("hint") or text("label"), meta)
        except clips.ClipError as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        self.send_json({"ok": True, "clip": rec}, 201)

    # ---- the book reader's two writes
    def _books_post(self, path):
        p = path.rstrip("/")
        if p.endswith("__save/review-corrections.json"):
            return self._save()
        if p.endswith("__save/subtimes.json"):
            return self._subtimes()
        if p.endswith("__narration/transcript"):
            return self._narration_transcript()
        if p.endswith("__narration/align"):
            return self._narration_align()
        if p.endswith("__narration/restore"):
            return self._narration_restore()
        if p.endswith("__narration/spread"):
            return self._narration_spread()
        if p.endswith("__narration/region"):
            return self._narration_region()
        if p.endswith("__narration/remove"):
            return self._narration_remove()
        if p.endswith("__reading/free"):
            return self._book_reading("free")
        if p.endswith("__reading/fold"):
            return self._book_reading("fold")
        if p.endswith("__struct/section"):
            return self._book_structure("section")
        if p.endswith("__struct/chapter"):
            return self._book_structure("chapter")
        if p.endswith("__edit/chunk"):
            return self._book_edit_chunk()
        if p.endswith("__edit/meta"):
            return self._book_edit_meta()
        if p.endswith("__divide/chunk"):
            return self._book_divide_chunk()
        if p.endswith("__clip/cut"):
            return self._book_clip("cut")
        if p.endswith("__clip/peaks"):
            return self._book_clip("peaks")
        if p.endswith("__lookup"):
            book = self._book_dir()
            if not book:
                return self.send_json({"ok": False, "error": "no book here"}, 404)
            b = booklib.Book(book)
            return self._lookup(b.lang.code, None, b.gloss_lang.code)
        if p.endswith("__words/propose"):
            book = self._book_dir()
            if not book:
                return self.send_json({"ok": False, "error": "no book here"}, 404)
            return self._words_propose(booklib.Book(book).lang.code)
        self.send_json({"ok": False, "error": "nothing to POST here"}, 404)

    def _book_dir(self):
        """The book this request belongs to: the nearest ancestor of the
        request path holding a book.json, which is how the rest of the
        project finds a book too."""
        p = self.translate_path(self.path.split("?")[0])
        d = p if os.path.isdir(p) else os.path.dirname(p)
        while d.startswith(ROOT):
            if os.path.isfile(os.path.join(d, "book.json")):
                return d
            up = os.path.dirname(d)
            if up == d:
                break
            d = up
        return None

    def _save(self):
        book = self._book_dir()
        if not book:
            return self.send_json({"ok": False, "error": "no book here"}, 404)
        try:
            json.loads(self._raw.decode("utf-8"))
        except Exception:
            return self.send_json({"ok": False, "error": "not JSON"}, 400)
        with open(os.path.join(book, "review-corrections.json"), "wb") as f:
            f.write(self._raw)
        self.send_json({"ok": True})

    # ---- authoring: the bundle out and back, the empty draft, one edited chunk
    # The four modules under lib/ do the work and know nothing about HTTP;
    # what lives here is the mapping from a request to one of their calls and
    # from their refusals to a status code.  Their exceptions are the error
    # messages: they were written to be read by whoever pressed the button.
    def _json_body(self):
        """The body as a dict, or None having already answered."""
        try:
            body = json.loads(self._raw.decode("utf-8"))
        except Exception:
            self.send_json({"ok": False, "error": "not JSON"}, 400)
            return None
        if not isinstance(body, dict):
            self.send_json({"ok": False, "error": "expected a JSON object"}, 400)
            return None
        return body

    def _send_bundle(self, data, name):
        # Content-Disposition is what makes the browser save it rather than
        # try to display a zip; the name is a slug or a video id, so ASCII,
        # but quote it anyway -- a filename with a quote in it would end the
        # header value early and the browser would save it under something else
        self.send_bytes(data, "application/zip", extra={
            "Content-Disposition": 'attachment; filename="%s"'
                                   % name.replace('"', "")})

    def _book_download(self):
        """The reading edition as one zip, in one of three shapes.

        ?audio= says how much of the narration comes with it: `text` none of
        it and nothing left pointing at one, `linked` everything but the
        recording (put audio/ back and the book is whole), `full` all of it.
        A book with no narration gives the same bytes whichever is asked
        for.  An unknown value is a refusal rather than a guess: a bundle
        that quietly carried more or less than was meant is the one mistake
        here somebody could lose a recording to.
        """
        book = self._book_dir()
        if not book:
            return self.send_json({"ok": False, "error": "no book here"}, 404)
        mode = (self.query.get("audio", [""])[0] or "").strip().lower()
        try:
            data, name = (bundle.pack_book(book, audio=mode) if mode
                          else bundle.pack_book(book))
        except bundle.BundleError as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        except (TypeError, ValueError) as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        self._send_bundle(data, name)

    def _shelf_backup(self, kind):
        """A whole shelf as one zip: the Backup button, for books or videos.

        Streamed off a temporary file rather than answered from memory: a
        shelf may hold large bundles, and the file is gone again before this
        returns whatever happens."""
        try:
            path, name = shelf.pack(kind)
        except shelf.ShelfError as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        try:
            self.send_file(path, download_name=name)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def _shelf_restore(self, kind):
        """A backup put back.  ?replace=1 overwrites what is already here;
        without it such a one is kept and named in the answer, so a restore
        never quietly eats work that is newer than the backup."""
        body = self._spool or self._raw
        if not body:
            return self.send_json({"ok": False, "error": "nothing to restore: send "
                                   "the backup zip as the body"}, 400)
        replace = (self.query.get("replace", ["0"])[0] or "") in ("1", "true", "yes")
        try:
            out = shelf.restore(kind, body, replace=replace)
        except shelf.ShelfError as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        for d in out.pop("dirs", []):
            notes_came_back(os.path.join(ROOT, d))
        # the shelf page is a file this writes: once at the end, not once a
        # book, or a restore of forty would rebuild it forty times
        if kind == "book" and out["restored"]:
            out["library"] = self._write_library()
        self.send_json(dict(out, ok=True), 201)

    def _bundle_upload(self, want):
        """A bundle posted back, for the door that asked for it.

        `want` is the kind that door deals in: a video bundle dropped on the
        book library is a slip worth naming, not something to install quietly
        somewhere the user is not looking.
        """
        replace = (self.query.get("replace", ["0"])[0] or "") in ("1", "true", "yes")
        # the bytes, or the file they were spooled into: lib/bundle.py reads
        # either, and a film-sized bundle is never held in memory
        body = self._spool or self._raw
        try:
            what = bundle.inspect(body)
            if what.get("kind") != want:
                return self.send_json(
                    {"ok": False, "error": "that is a %s bundle; this is where a %s "
                                           "goes" % (what.get("kind"), want)}, 400)
            r = bundle.install(body, replace=replace)
            if r.get("ok") and r.get("dir"):
                notes_came_back(os.path.join(ROOT, r["dir"]))
            # A BOOK IS ON THE SHELF THE MOMENT IT IS INSTALLED.  The library
            # page is a file make_index writes, so until it is written again
            # the book is on disk and on no page -- which is what "it does
            # not appear" was.  Written here, the book is among the others
            # the next time the list is loaded, grey like any book nobody has
            # built yet, and its own card's `build` button builds it: one way
            # to build a book instead of two.
            if r.get("ok") and r.get("kind") == "book":
                r["library"] = self._write_library()
            return self.send_json(r)
        except bundle.Exists as e:
            # the one refusal a page answers with a "replace it" checkbox
            return self.send_json({"ok": False, "exists": True, "error": str(e)}, 409)
        except bundle.BundleError as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)

    def _book_empty(self):
        """A book with the text in it and every gloss blank, to author by hand."""
        body = self._json_body()
        if body is None:
            return
        try:
            r = draft.book_from_text(
                body.get("text") or "", body.get("lang") or "",
                body.get("title") or "", gloss=body.get("gloss") or "",
                slug=(body.get("slug") or None),
                author=body.get("author") or "",
                title_latin=body.get("title_latin") or "",
                title_en=body.get("title_en") or "",
                author_latin=body.get("author_latin") or "",
                year=body.get("year") or "", blurb=body.get("blurb") or "",
                into=booklib.BOOKS_DIR,
                how=chunk_way(body))
        except ValueError as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        # a book is nothing to the reader until tex2html has written one, and
        # nothing to the library page until make_index has written its card
        r["reader"] = self._rebuild_reader(r["dir"])
        r["library"] = self._write_library()
        self.send_json(dict(r, ok=True))

    def _book_append(self, book):
        """More text onto the end of a book that is already here.

        Everything `__empty` does except decide what the book IS: the
        language, the gloss language and the title are the book's already,
        so this asks for the text, where to put it and how to cut it, and
        nothing else.  `chapter` is `new` (its own \\chapopen and its own
        \\input line) or `last` (more paragraphs of the last chapter,
        numbered on from what is there).

        Nothing already written is touched: the old chapters are read only to
        be numbered from.  The reader is rebuilt because the .tex has grown
        and the page must not be behind it, and the PDF is stale for the same
        reason it is after a divide.
        """
        body = self._json_body()
        if body is None:
            return
        try:
            r = draft.add_to_book(book, body.get("text") or "",
                                  how=chunk_way(body),
                                  chapter=body.get("chapter") or "new")
        except ValueError as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        except OSError as e:
            return self.send_json({"ok": False, "error": "the book's own files "
                                   "could not all be written (%s)" % e}, 400)
        r["reader"] = self._rebuild_reader(book)
        # the card counts the chapters and the subparagraphs the reader has
        r["library"] = self._write_library()
        r["pdf_stale"] = True
        self.send_json(dict(r, ok=True))

    def _rebuild_reader(self, book):
        """Regenerate reader/index.html so the page and the .tex agree.

        A subprocess, not an import: tex2html is a script with a main() built
        round argparse, and a book that makes it raise must fail this one
        request rather than the server.  It takes a tenth of a second even on
        the whole Persian book, so an edit can afford to wait for it and the
        file on disk is never behind what the reader is showing.
        """
        try:
            r = subprocess.run([sys.executable, os.path.join(LIB, "tex2html.py"),
                                "--book", book],
                               capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as e:
            return {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
        return {"ok": r.returncode == 0,
                "error": (r.stderr or r.stdout or "").strip()[-400:]
                         if r.returncode else ""}

    def _write_library(self):
        """Rewrite books/index.html, the library page -> {"ok", "error"}.

        After whatever puts a book on the shelf or changes what its card says
        -- a book started empty, text added to one -- and when the page has
        never been written at all: the card is then there the next time the
        page opens, and not after a build nobody was told to run.  A
        subprocess, as the reader's rebuild is, so a book that makes it raise
        fails this one step and not the request.
        """
        try:
            r = subprocess.run([sys.executable, os.path.join(LIB, "make_index.py")],
                               cwd=ROOT, capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.SubprocessError) as e:
            return {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
        return {"ok": r.returncode == 0,
                "error": ((r.stderr or r.stdout or "").strip().splitlines() or ["it failed"])[-1]
                         if r.returncode else ""}

    def _book_reading(self, what):
        """What somebody has decided about the text itself: reading.json.

        Two decisions, both about paragraphs and both kept with the book
        (lib/reading.py).  `free` takes a paragraph out of the source check --
        the reader's own way of saying an edit is meant -- and `fold` folds a
        run of them away, so the text is not shown and reading walks past it.

        A paragraph is named the way the page names it, <chapter>:<paragraph>,
        which is the data-p the build wrote on every .para.  The reader is
        rebuilt afterwards, so the next open has the decision in it.
        """
        book = self._book_dir()
        if not book:
            return self.send_json({"ok": False, "error": "no book here"}, 404)
        body = self._json_body()
        if body is None:
            return
        on = bool(body.get("on", True))
        try:
            if what == "free":
                k = reading.split(str(body.get("para") or ""))
                if not k:
                    return self.send_json({"ok": False, "error": "which paragraph? "
                                           "<chapter>:<paragraph>"}, 400)
                doc = reading.set_free(book, k[0], k[1], on)
            else:
                first = str(body.get("from") or "")
                last = str(body.get("to") or first)
                doc = reading.collapse(book, first, last, on)
        except (ValueError, OSError) as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        return self.send_json({"ok": True, "reading": doc,
                               "reader": self._rebuild_reader(book)})

    def _book_structure(self, what):
        r"""A chapter's name, and the sections inside it (lib/structure.py).

        Both are written into the book's OWN .tex -- \chapname after
        \chapopen, \secmark on its own line between two paragraphs -- and not
        into a sidecar beside it.  That is what makes them travel: bundle.py
        carries every .tex by a rule that is already there, while a new JSON
        file would have to be named in bundle.SHAPE or be dropped on the way
        out and again on the way in.  A book downloaded and brought back keeps
        its sections.

        A section is named by the paragraph it opens at,
        <chapter>:<paragraph> -- the data-p the build wrote on every .para,
        and the same name reading.json uses.  `on` false takes it away.

        NOTHING IS RENUMBERED.  structure.py re-reads the file after every
        write and refuses unless every paragraph number, every subparagraph
        label and every chunk came back exactly as it was.

        The reader is rebuilt afterwards, so the next open has it in.
        """
        book = self._book_dir()
        if not book:
            return self.send_json({"ok": False, "error": "no book here"}, 404)
        body = self._json_body()
        if body is None:
            return
        title = body.get("title") or ""
        try:
            if what == "chapter":
                ch = body.get("chapter")
                if ch is None or not str(ch).strip():
                    return self.send_json({"ok": False, "error":
                                           "which chapter?"}, 400)
                done = structure.set_chapter_name(book, int(ch), title)
            else:
                k = reading.split(str(body.get("para") or ""))
                if not k:
                    return self.send_json({"ok": False, "error": "which paragraph? "
                                           "<chapter>:<paragraph>"}, 400)
                done = structure.set_section(book, k[0], k[1], title,
                                             bool(body.get("on", True)))
        except (structure.Refused, ValueError, OSError) as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        return self.send_json({"ok": True, "what": what, "done": done,
                               "structure": structure.read(book),
                               "reader": self._rebuild_reader(book)})

    def _book_edit_chunk(self):
        """One chunk of one chapter, rewritten where the author can see it.

        The page addresses a chunk by the number the reader gave it, which is
        book-wide (data-c); the chapter files each hold a run of those, so
        book_chapters says which file owns it and what to subtract.
        """
        book = self._book_dir()
        if not book:
            return self.send_json({"ok": False, "error": "no book here"}, 404)
        body = self._json_body()
        if body is None:
            return
        index, fields = body.get("index"), body.get("fields")
        if not isinstance(index, int) or index < 0:
            return self.send_json({"ok": False, "error": "index must be the chunk's "
                                                         "number in the reader"}, 400)
        if not isinstance(fields, dict) or not fields:
            return self.send_json({"ok": False, "error": "nothing to change"}, 400)
        try:
            here = self._chapter_owning(book, index)
            if not isinstance(here, dict):
                return self.send_json(here[0], here[1])
            r = texwrite.edit_chunk(here["path"], index - here["first"], fields)
        except texwrite.Refused as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        r["file"] = here["file"]
        r["index"] = index                      # answer in the page's own numbering
        r["reader"] = self._rebuild_reader(book)
        # the PDF is built by LaTeX and nothing here can do that
        r["pdf_stale"] = bool(r.get("changed"))
        self.send_json(dict(r, ok=True))

    def _book_edit_meta(self):
        """The book's own title, author, year, blurb -- not a chunk, book.json
        itself (and main.tex's title page, bookmeta.edit_meta's own concern
        to keep in step).  The reader is rebuilt the same way a chunk edit
        rebuilds it, so the tab title and the contents panel pick up the new
        title at once; the PDF is stale until the next ./build.sh, same as a
        chunk edit leaves it."""
        book = self._book_dir()
        if not book:
            return self.send_json({"ok": False, "error": "no book here"}, 404)
        body = self._json_body()
        if body is None:
            return
        fields = body.get("fields")
        try:
            meta = bookmeta.edit_meta(book, fields)
        except (bookmeta.Refused, ValueError) as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        reader = self._rebuild_reader(book)
        self.send_json({"ok": True, "meta": meta, "reader": reader,
                        "pdf_stale": bool(set(fields) & set(bookmeta.MAINTEX_MACRO))})

    def _chapter_owning(self, book, index):
        """The chapter file that owns a book-wide chunk number, or the answer
        to send instead.  The page addresses a chunk by the number the reader
        gave it (data-c), which runs across the whole book; the chapter files
        each hold a run of those, and book_chapters says which owns which."""
        chapters = texwrite.book_chapters(book)
        # a chapter file holding no chunks at all -- a book still being
        # written, a chapter of nothing but scaffolding -- has first and
        # last None, and it owns no number the reader could send
        numbered = [c for c in chapters if c["first"] is not None]
        here = next((c for c in numbered
                     if c["first"] <= index <= c["last"]), None)
        if here is None:
            last = numbered[-1]["last"] if numbered else -1
            return ({"ok": False, "error": "no chunk %d in this book (it has %d)"
                     % (index, last + 1)}, 404)
        return here

    @staticmethod
    def _still_says(chunks, i, want, which):
        """Whether the page is looking at the chunk it says it is.

        Dividing renumbers every chunk after it, so a page left open across
        one addresses the wrong chunk with a number that is still in range --
        and the edit would be made, correctly, to the wrong text.  The page
        sends the text it is showing and this compares it; nothing else in the
        request can tell a stale number from a fresh one.
        """
        if want is None:
            return None
        got = chunks[i].get("fa") if 0 <= i < len(chunks) else None
        if got == want:
            return None
        return ("the page is showing the %s chunk as %r and the file has %r -- "
                "reload the reader before dividing: somebody has changed the "
                "book underneath it" % (which, want, got))

    def _book_divide_chunk(self):
        """Where a chunk ends, moved: two joined into one, or one cut in two.

        Three actions on one route.  `preview` works out every place the chunk
        divides and what joining it to the next one would give, and writes
        nothing; `split` and `merge` are what comes back after somebody has
        looked at that and typed over it.  Both of those renumber every chunk
        after them, so the reader is rebuilt and the page reloads -- the
        per-chunk repaint cannot be right after a count has changed.
        """
        book = self._book_dir()
        if not book:
            return self.send_json({"ok": False, "error": "no book here"}, 404)
        body = self._json_body()
        if body is None:
            return
        action, index = body.get("action"), body.get("index")
        if action not in ("preview", "split", "merge"):
            return self.send_json({"ok": False, "error": "action must be "
                                   "preview, split or merge"}, 400)
        if not isinstance(index, int) or isinstance(index, bool) or index < 0:
            return self.send_json({"ok": False, "error": "index must be the "
                                   "chunk's number in the reader"}, 400)
        try:
            here = self._chapter_owning(book, index)
            if not isinstance(here, dict):
                return self.send_json(here[0], here[1])
            local = index - here["first"]
            if action == "preview":
                r = texwrite.divide_preview(here["path"], local)
            else:
                chunks = texwrite.read_chunks(here["path"])
                stale = self._still_says(chunks, local, body.get("expect"), "first")
                if not stale and action == "merge":
                    stale = self._still_says(chunks, local + 1,
                                             body.get("expect_next"), "second")
                if stale:
                    return self.send_json({"ok": False, "error": stale}, 409)
                if action == "split":
                    r = texwrite.split_chunk(here["path"], local,
                                             body.get("first") or {},
                                             body.get("second") or {})
                else:
                    r = texwrite.merge_chunks(here["path"], local,
                                              body.get("fields"))
        except texwrite.Refused as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        except (OSError, ValueError) as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        r["file"] = here["file"]
        r["index"] = index                      # answer in the page's numbering
        if action != "preview":
            r["reader"] = self._rebuild_reader(book)
            r["pdf_stale"] = True
        self.send_json(dict(r, ok=True))

    def _video_dir(self, vid):
        """The directory of a video by its id, or None (video_dir)."""
        return video_dir(vid)

    def _video_download(self, vid):
        """The video and its glossed transcript as one zip.

        ?media= says whether the film comes with it, for a video that IS a
        file on this machine: `full` (the default, and what the button asks
        for) carries it, `text` leaves it behind.  A video on YouTube has no
        film here and the choice does not arise.
        """
        d = self._video_dir(vid)
        if not d:
            return self.send_json({"ok": False, "error": "no such video"}, 404)
        want = (self.query.get("media") or self.query.get("audio") or [""])[0] or None
        try:
            data, name = bundle.pack_video(d, want)
        except bundle.BundleError as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        except OSError as e:
            # a film the process cannot read -- permissions, a dangling link,
            # a disk that went away -- is a sentence about that film, not a
            # traceback out of the download button
            return self.send_json({"ok": False, "error": "this video's own files "
                                   "could not all be read (%s)" % e}, 400)
        self._send_bundle(data, name)

    def _video_empty(self):
        """A video whose captions are chunked and whose glosses are all blank."""
        body = self._json_body()
        if body is None:
            return
        try:
            r = draft.video_from_transcript(
                # The add page invites a .srt or .vtt to be pasted whole, and
                # all FOUR of its doors must honour that.  as_transcript's own
                # docstring says "all three of its buttons" -- prepare, add and
                # local translated it and this one passed the text straight
                # through, so the same subtitle file that made a video one way
                # was told "no captions found -- paste the transcript as
                # YouTube shows it" the other.  This is the fourth.
                ytpages.as_transcript(body.get("transcript") or ""),
                body.get("lang") or "",
                gloss=body.get("gloss") or "",
                video_id=(body.get("video") or body.get("url") or None),
                url=body.get("url") or "", title=body.get("title") or "",
                title_native=body.get("title_native") or "",
                channel=body.get("channel") or "",
                level=body.get("level") or "beginner",
                blurb=body.get("blurb") or "", into=ytpages.VIDEOS,
                how=chunk_way(body))
        except ValueError as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        self.send_json(dict(r, ok=True))

    def _video_local(self):
        """A video that is a FILE ON THIS MACHINE, drafted from its subtitles.

        The same road as `Start it empty` and the same result -- captions cut
        into chunks with every gloss blank -- with the film put beside them.
        The transcript may be the panel YouTube shows or a .srt/.vtt subtitle
        file, which is translated into the first so that everything
        downstream still reads one format.
        """
        body = self._json_body()
        if body is None:
            return
        taken = [name for _f, name, _p in ytpages.video_dirs()]
        try:
            ytpages.one_source(body)
            path, _ext, vid = ytpages.local_target(body, taken)
        except ValueError as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        text = body.get("transcript") or ""
        if ytpages.looks_like_subtitles(text):
            text = ytpages.subtitles_to_transcript(text)
            if not text.strip():
                return self.send_json({"ok": False, "error": "that subtitle file "
                                       "holds no cues this could read"}, 400)
        seed = (body.get("title") or "").strip() or \
            os.path.splitext(os.path.basename(path))[0]
        try:
            r = draft.video_from_transcript(
                text, body.get("lang") or "", gloss=body.get("gloss") or "",
                video_id=vid, url="", title=(body.get("title") or "").strip() or seed,
                title_native=body.get("title_native") or "",
                channel=(body.get("channel") or "").strip() or "on this machine",
                level=body.get("level") or "beginner",
                blurb=body.get("blurb") or "", into=ytpages.VIDEOS,
                how=chunk_way(body))
        except ValueError as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        try:
            got = ytpages.attach_film(r["dir"], path)
        except (ValueError, OSError) as e:
            shutil.rmtree(r["dir"], ignore_errors=True)
            return self.send_json({"ok": False, "error": "the film could not be put "
                                   "beside the transcript (%s)" % e}, 400)
        return self.send_json(dict(r, ok=True, id=vid,
                                   where=ytpages.BASE + "/v/%s/" % vid, **got))

    def _video_times(self):
        """Where some captions of an added video start.

        The one door that moves a start after a video is on the shelf.  It
        writes annotations.json, transcript.txt and the batches together --
        captimes says why that is allowed where an editor of the TEXT is not
        -- and refuses, in the checker's own words, anything that would
        leave the video in a state the checker would not pass.

        Nothing to rebuild, as for the other video writers: the player reads
        annotations.json itself the next time it loads.
        """
        body = self._json_body()
        if body is None:
            return
        d = self._video_dir(body.get("video") or "")
        if not d:
            return self.send_json({"ok": False, "error": "no such video"}, 404)
        moves = body.get("moves")
        if not isinstance(moves, list) or not moves:
            return self.send_json({"ok": False,
                                   "error": "nothing was asked to move"}, 400)
        try:
            r = captimes.move(d, moves)
        except ValueError as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        out = {"ok": True}
        out.update(r)
        self.send_json(out)

    def _video_waveform(self):
        """The SHAPE of a YouTube video's sound, recorded from a tab.

        A film on this machine needs none of this: the server reads the film
        with ffmpeg, window by window (/youtube/api/peaks).  A YouTube video
        has no file anybody here can read, so the only picture of its sound
        is one the browser made while the video played in a shared tab -- and
        what is kept is the shape and not the sound: one number every 50 ms,
        a few hundred kilobytes for an hour, where the audio itself would be
        hundreds of megabytes and a copy of somebody else's recording.

        Written beside the video as waveform.json and read back by the player
        straight off the static route, so a video is recorded once and drawn
        on every later visit.
        """
        body = self._json_body()
        if body is None:
            return
        d = self._video_dir(body.get("video") or "")
        if not d:
            return self.send_json({"ok": False, "error": "no such video"}, 404)
        peaks, rate = body.get("peaks"), body.get("rate")
        if not isinstance(peaks, list) or not peaks:
            return self.send_json({"ok": False, "error": "no waveform was sent"}, 400)
        if len(peaks) > 2000000:
            return self.send_json({"ok": False,
                                   "error": "that waveform is too fine to keep"}, 400)
        try:
            rate = float(rate)
        except (TypeError, ValueError):
            return self.send_json({"ok": False,
                                   "error": "a waveform says how many numbers a second it has"}, 400)
        if not 1 <= rate <= 200:
            return self.send_json({"ok": False,
                                   "error": "a waveform carries between 1 and 200 numbers a second"}, 400)
        out = []
        for v in peaks:
            try:
                f = float(v)
            except (TypeError, ValueError):
                f = 0.0
            out.append(round(min(1.0, max(0.0, f)), 3))
        path = os.path.join(d, "waveform.json")
        tmp = path + ".tmp"
        with io.open(tmp, "w", encoding="utf-8") as f:
            json.dump({"rate": rate, "peaks": out}, f, ensure_ascii=False)
        os.replace(tmp, path)
        self.send_json({"ok": True, "rate": rate, "buckets": len(out)})

    def _video_edit_chunk(self):
        """One chunk of one segment of annotations.json.

        Unlike a book there is nothing to rebuild: the player reads the file
        the edit just wrote, so the answer is the chunk as it now stands.
        """
        body = self._json_body()
        if body is None:
            return
        d = self._video_dir(body.get("video") or "")
        if not d:
            return self.send_json({"ok": False, "error": "no such video"}, 404)
        seg, chunk, fields = body.get("segment"), body.get("chunk"), body.get("fields")
        if not isinstance(seg, int) or not isinstance(chunk, int):
            return self.send_json({"ok": False, "error":
                                   "segment and chunk must be numbers"}, 400)
        if not isinstance(fields, dict) or not fields:
            return self.send_json({"ok": False, "error": "nothing to change"}, 400)
        try:
            r = annwrite.edit_chunk(d, seg, chunk, fields)
        except ValueError as e:
            # annwrite refuses with the checker's own words, which is what
            # the page should show: it names the rule, not the exception
            return self.send_json({"ok": False, "error": str(e)}, 400)
        self.send_json({"ok": True, "segment": seg, "chunk": chunk, "chunk_now": r})

    def _video_edit_meta(self):
        """The video's own title, channel, level and blurb -- not a chunk,
        video.json itself.  The concrete case this exists for: api_add's
        YouTube lookup (oembed, or the LLM's answer) got the title or the
        channel wrong, and there was no way to fix it short of hand-editing
        video.json.  Unlike a book there is nothing to rebuild: the player
        reads the file the edit just wrote."""
        body = self._json_body()
        if body is None:
            return
        d = self._video_dir(body.get("video") or "")
        if not d:
            return self.send_json({"ok": False, "error": "no such video"}, 404)
        fields = body.get("fields")
        try:
            meta = ytpages.edit_meta(d, fields)
        except (texwrite.Refused, ValueError) as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        self.send_json({"ok": True, "meta": meta})

    def _video_divide_chunk(self):
        """Where a chunk of a caption ends, moved.  The books' route with the
        video's own addressing (segment and chunk instead of one running
        number) and nothing to rebuild: the player is handed the caption's
        whole new chunk list and redraws that caption from it, because every
        chunk after the change has moved and a patch would leave the page
        pointing at the wrong ones."""
        body = self._json_body()
        if body is None:
            return
        d = self._video_dir(body.get("video") or "")
        if not d:
            return self.send_json({"ok": False, "error": "no such video"}, 404)
        action = body.get("action")
        seg, chunk = body.get("segment"), body.get("chunk")
        if action not in ("preview", "split", "merge"):
            return self.send_json({"ok": False, "error": "action must be "
                                   "preview, split or merge"}, 400)
        if not isinstance(seg, int) or not isinstance(chunk, int) \
                or isinstance(seg, bool) or isinstance(chunk, bool):
            return self.send_json({"ok": False, "error":
                                   "segment and chunk must be numbers"}, 400)
        try:
            if action != "preview":
                look = annwrite.divide_preview(d, seg, chunk)
                stale = self._still_says([look["chunk"]], 0, body.get("expect"),
                                         "first")
                if not stale and action == "merge":
                    stale = self._still_says([look["next"] or {}], 0,
                                             body.get("expect_next"), "second")
                if stale:
                    return self.send_json({"ok": False, "error": stale}, 409)
            if action == "preview":
                r = annwrite.divide_preview(d, seg, chunk)
            elif action == "split":
                r = annwrite.split_chunk(d, seg, chunk, body.get("first") or {},
                                         body.get("second") or {})
            else:
                r = annwrite.merge_chunks(d, seg, chunk, body.get("fields"))
        except ValueError as e:
            return self.send_json({"ok": False, "error": str(e)}, 400)
        except OSError:
            return self.send_json({"ok": False, "error":
                                   "this video has no annotations.json yet"}, 404)
        self.send_json(dict(r, ok=True))

    def _subtimes(self):
        """Timestamps edited in the page, made persistent.

        Merged into timings.json as `manual` (so a later --force
        re-alignment leaves them alone), then the .tex comments and the
        reader are rewritten from it, so the edit survives a rebuild.
        """
        book = self._book_dir()
        if not book:
            return self.send_json({"ok": False, "error": "no book here"}, 404)
        try:
            edits = json.loads(self._raw.decode("utf-8"))
            assert isinstance(edits, dict)
        except Exception:
            return self.send_json({"ok": False, "error": "not JSON"}, 400)
        side = os.path.join(book, "timings.json")
        doc = {"subs": {}}
        if os.path.exists(side):
            with open(side, encoding="utf-8") as f:
                doc = json.load(f)
        subs = doc.setdefault("subs", {})
        applied = 0
        for k, v in edits.items():
            try:
                t0, t1 = float(v["t0"]), float(v["t1"])
            except Exception:
                continue
            if t1 <= t0:
                continue
            rec = subs.get(k, {})
            rec.update({"t0": round(t0, 3), "t1": round(t1, 3),
                        "conf": 1.0, "src": "manual"})
            subs[k] = rec
            applied += 1
        with open(side, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
        # Write through to the .tex AND the reader page: the page has SUBS
        # baked in, so without this a reload shows the old numbers even
        # though the edit is safely on disk.  The tools expect to run from
        # inside the book, with the conda interpreter (rapidfuzz).
        err = ""
        for cmd in ([os.path.join(LIB, "timestamp.py"), "--from-sidecar"],
                    [os.path.join(LIB, "tex2html.py")]):
            try:
                r = subprocess.run([sys.executable] + cmd, cwd=book,
                                   capture_output=True, text=True, timeout=300)
                if r.returncode:
                    err = ("%s: %s" % (os.path.basename(cmd[0]), r.stderr or ""))[-300:]
                    break
            except Exception as e:
                err = "%s: %s" % (cmd[0], e)
                break
        self.send_json({"ok": not err, "applied": applied, "error": err})

    # ---- the narration: what the reader's "add a narration" panel talks to
    # Every URL is relative to the reader page (__narration/...), so the
    # book is the one the page belongs to, the way __save/ works.  The files
    # land in books/<slug>/audio/ -- yours, never committed -- and book.json
    # is pointed at them; the alignment is lib/timestamp.py, the same tool
    # as on the command line, then the reader and the library page rebuilt.
    def _narration_book(self):
        d = self._book_dir()
        return booklib.Book(d) if d else None

    def _narration_stream(self, n, kind):
        """A big upload -- the narration itself, or a narration file (the
        zip the export makes) -- streamed into a file beside its
        destination, never into memory.  The browser hands over the bytes;
        the server names the file (a name from outside never chooses a
        path)."""
        b = self._narration_book()
        raw = (self.query.get("name") or [""])[0]
        name = re.sub(r"[^A-Za-z0-9._ -]", "_", os.path.basename(raw)).strip(" ._")
        ext = os.path.splitext(name)[1].lower()
        # no ceiling: a recording is a file of the reader's own, streamed to
        # disk below in megabyte pieces, and the disk is the only limit that
        # was ever true of it
        why = ("no book here" if not b else
               "empty upload" if n <= 0 else
               "name the file with its extension (mp3, m4a, webm, ogg, wav ...)"
               if kind == "audio" and ext not in AUDIO_EXTS else "")
        # A STRETCH THE BOOK DOES NOT HAVE is refused before the file is
        # read, not after a recording of an hour has arrived to be thrown away
        if not why and kind == "audio":
            first = (self.query.get("from") or [""])[0].strip()
            last = (self.query.get("to") or [""])[0].strip()
            if first or last:
                why = self._region_error(b, first, last) or ""
        if why:
            self.close_connection = True          # the body stays unread
            return self.send_json({"ok": False, "error": why}, 400)
        adir = os.path.join(b.dir, "audio")
        os.makedirs(adir, exist_ok=True)
        tmp = os.path.join(adir, (name if kind == "audio" else "import.zip") + ".part")
        got = 0
        try:
            with open(tmp, "wb") as f:
                while got < n:
                    chunk = self.rfile.read(min(1 << 20, n - got))
                    if not chunk:
                        break
                    f.write(chunk)
                    got += len(chunk)
                    activity.progress(getattr(self, "_act", None), done=got)
            if got != n:
                raise IOError("the upload was cut short (%d of %d bytes)" % (got, n))
            self._received()
        except Exception as e:
            self.close_connection = True
            try:
                os.unlink(tmp)
            except OSError:
                pass
            return self.send_json({"ok": False, "error": str(e)}, 400)
        if kind == "audio":
            path = os.path.join(adir, name)
            os.replace(tmp, path)                 # never a half file under a real name
            # WHICH STRETCH OF TEXT THIS RECORDING IS OF.  Given, the file
            # joins the book's list of recordings and covers those
            # subparagraphs; not given, it is the whole book's narration and
            # replaces what was there, which is what this door has always
            # done and what a book recorded in one sitting still wants.
            first = (self.query.get("from") or [""])[0].strip()
            last = (self.query.get("to") or [""])[0].strip()
            recs = list(b.narrations)
            if first or last or len(recs) > 1:
                keep = [{"id": r["id"], "audio": r["audio_rel"],
                         "transcript": r["transcript_rel"],
                         "from": r["from"], "to": r["to"]}
                        for r in recs if r["audio_rel"] != "audio/" + name]
                keep.append({"id": narration_id(keep), "audio": "audio/" + name,
                             "transcript": "", "from": first, "to": last})
                set_narrations(b, keep)
            else:
                set_book_meta(b.dir, audio="audio/" + name)
            # A FILE THAT CANNOT BE ALIGNED YET STILL GETS TIMES.  With a
            # stretch of text named and no transcript to align against, the
            # recording is shared out over that stretch in proportion to the
            # length of each subparagraph -- so it plays from the moment it
            # lands, and what drifts is nudged by ear instead of waiting for a
            # transcript that may never be written.  Only where nothing there
            # has a time yet: a guess never pushes out somebody's work.
            guessed, guess_log = 0, ""
            fresh = booklib.Book(b.dir)
            rec = fresh.narration(keep[-1]["id"]) if (first or last) else None
            if rec and not (rec["transcript"] and os.path.exists(rec["transcript"])):
                gok, guess_log, _gerr = self._run_steps(
                    [("estimate", [os.path.join(LIB, "timestamp.py"), "--spread",
                                   "--narration", rec["id"]], b.dir)])
                m = re.search(r"spread [\d.]+ s of \S+ over the (\d+)", guess_log or "")
                guessed = int(m.group(1)) if (gok and m) else 0
            # the reader has the audio's address baked in: rebuilt at once,
            # so that with the audio alone the timings can be stamped by hand
            ok, log, err = self._rebuild(b)
            st = make_index.stats(b)
            return self.send_json({"ok": True, "file": name, "bytes": got,
                                   "audio": "audio/" + name, "rebuilt": ok,
                                   "log": (guess_log + "\n" + log).strip(),
                                   "spread": guessed,
                                   "error": err, "timed": st.get("timed", 0),
                                   "subs": st.get("subs", 0)})
        try:
            return self._narration_import(b, tmp)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def _narration_import(self, b, path):
        """A narration file -- the export's zip: the audio, timings.json, the
        transcript, a manifest -- unpacked into its places, then the reader
        rebuilt.  The times inside take over; the old timings.json is kept."""
        try:
            z = zipfile.ZipFile(path)
        except zipfile.BadZipFile:
            return self.send_json({"ok": False, "error": "that is not a narration file "
                                   "(the export makes a zip; this is not one)"}, 400)
        log = []
        with z:
            names = {os.path.basename(n): n for n in z.namelist() if not n.endswith("/")}
            man = {}
            if "manifest.json" in names:
                try:
                    man = json.loads(z.read(names["manifest.json"]).decode("utf-8"))
                except Exception:
                    man = {}
            if man.get("book") and man["book"] != b.slug:
                return self.send_json({"ok": False, "error": "this narration is for the book "
                                       "'%s', not for %s" % (man["book"], b.slug)}, 400)
            audio = man.get("audio") if man.get("audio") in names else next(
                (n for n in names if os.path.splitext(n)[1].lower() in AUDIO_EXTS), None)
            tr = man.get("transcript") if man.get("transcript") in names else next(
                (n for n in names if n.startswith("transcript.")
                 and os.path.splitext(n)[1].lower() in (".txt", ".srt", ".vtt", ".json")), None)
            has_times = "timings.json" in names
            if not audio and not has_times:
                return self.send_json({"ok": False, "error": "nothing usable inside: no audio "
                                       "file and no timings.json"}, 400)
            adir = os.path.join(b.dir, "audio")
            os.makedirs(adir, exist_ok=True)
            fields = {}
            if audio:
                safe = re.sub(r"[^A-Za-z0-9._ -]", "_", audio).strip(" ._") or "narration"
                dst = os.path.join(adir, safe)
                with z.open(names[audio]) as src, open(dst + ".part", "wb") as out:
                    shutil.copyfileobj(src, out, 1 << 20)
                os.replace(dst + ".part", dst)
                fields["audio"] = "audio/" + safe
                log.append("audio: audio/%s (%.1f MB)" % (safe, os.path.getsize(dst) / 1e6))
            if tr:
                ext = os.path.splitext(tr)[1].lower()
                dst = os.path.join(adir, "transcript" + ext)
                with z.open(names[tr]) as src, open(dst, "wb") as out:
                    shutil.copyfileobj(src, out)
                fields["transcript"] = "audio/transcript" + ext
                log.append("transcript: audio/transcript" + ext)
            if has_times:
                data = z.read(names["timings.json"])
                try:
                    n_subs = len((json.loads(data.decode("utf-8")) or {}).get("subs") or {})
                except Exception:
                    return self.send_json({"ok": False, "error": "the timings.json inside is "
                                           "not readable"}, 400)
                if os.path.isfile(b.timings):
                    kept = os.path.join(adir, "timings.before-import.json")
                    shutil.copy(b.timings, kept)
                    log.append("the previous timings.json is kept as audio/timings.before-import.json")
                with open(b.timings + ".tmp", "wb") as out:
                    out.write(data)
                os.replace(b.timings + ".tmp", b.timings)
                log.append("timings.json: %d subparagraphs%s" % (
                    n_subs, " (from %s)" % man.get("exported", "")[:10] if man.get("exported") else ""))
        if fields:
            set_book_meta(b.dir, **fields)
        ok, rlog, err = self._rebuild(b)
        st = make_index.stats(b)
        return self.send_json({"ok": ok, "log": "\n".join(log) + "\n" + rlog, "error": err,
                               "rebuilt": ok, "timed": st.get("timed", 0),
                               "subs": st.get("subs", 0)})

    def _narration_restore(self):
        """Point the book at a narration found where an earlier layout kept
        it.  The times already in timings.json (and the .tex) are kept:
        nothing is re-aligned, the reader is simply rebuilt with the audio."""
        b = self._narration_book()
        if not b:
            return self.send_json({"ok": False, "error": "no book here"}, 404)
        try:
            want = (self._json_body() or {}).get("path")
        except Exception:
            want = None
        hit = next((c for c in narration_candidates(b) if c["path"] == want), None)
        if not hit:
            return self.send_json({"ok": False, "error": "that is not one of the files found; "
                                   "the list may have changed -- reopen the panel"}, 400)
        abspath = os.path.join(ROOT, hit["path"])
        rel = os.path.relpath(abspath, b.dir).replace(os.sep, "/")
        set_book_meta(b.dir, audio=rel)
        ok, log, err = self._rebuild(b)
        st = make_index.stats(b)
        return self.send_json({"ok": ok, "log": "audio: %s\n%s" % (rel, log), "error": err,
                               "rebuilt": ok, "audio": rel,
                               "timed": st.get("timed", 0), "subs": st.get("subs", 0)})

    def _sub_labels(self, b, subkeys=False):
        """Every subparagraph of the book in reading order: its label, the
        printed number of its chapter in Latin digits, and the two together,
        "2:4.3" -- the name no other subparagraph answers to (a label alone
        is unique only within its chapter), which is what the reader's
        outline writes when somebody says which stretch a recording covers.
        With `subkeys`, also the key timings.json files its times under.
        """
        try:
            import texparse as T
            chapters = T.parse_book(b.main, b.lang)
        except Exception:
            return []
        out = []
        for ch in chapters:
            for pp in ch.paragraphs:
                for s in pp.subs:
                    e = {"label": s.num, "chapter": T.chapter_of(s), "key": T.qualified(s)}
                    if subkeys:
                        e["subkey"] = tstamp.subkey(s)
                    out.append(e)
        return out

    def _region_error(self, b, first, last, labels=None):
        """None when `first` and `last` name a stretch of this book -- either
        end a label, "4.3", or a label with its chapter, "2:4.3" -- and
        otherwise what is wrong with them, said so it can be shown."""
        import texparse as T
        labels = self._sub_labels(b) if labels is None else labels
        try:
            T.region_bounds([(e["chapter"], e["label"]) for e in labels], first, last)
        except ValueError as e:
            return str(e)
        return None

    def _narration_spread(self):
        """A recording with no transcript, shared out over the text it covers.

        The stretch is known and so is how long the file runs, so every
        subparagraph in it can be given a slice in proportion to its own
        length: a first guess to play and to nudge with `edit times`, rather
        than a recording that sits there until somebody writes a transcript.
        The times say what they are -- `spread`, at a low confidence -- so a
        real alignment later replaces them without being asked twice.
        """
        b = self._narration_book()
        if not b:
            return self.send_json({"ok": False, "error": "no book here"}, 404)
        try:
            opts = self._json_body()
        except Exception:
            opts = {}
        cmd = [os.path.join(LIB, "timestamp.py"), "--spread"]
        want = str(opts.get("narration") or "").strip()
        if want:
            if not b.narration(want):
                return self.send_json({"ok": False, "error":
                                       "no recording called %r here" % want}, 400)
            cmd += ["--narration", want]
        if opts.get("force"):
            cmd.append("--force")
        ok, log, err = self._run_steps(
            [("estimate", cmd, b.dir),
             ("reader", [os.path.join(LIB, "tex2html.py")], b.dir),
             ("library page", [os.path.join(LIB, "make_index.py")], ROOT)])
        st = make_index.stats(b)
        m = re.search(r"spread [\d.]+ s of \S+ over the (\d+)", log or "")
        self.send_json({"ok": ok, "log": log, "error": err,
                        "spread": int(m.group(1)) if m else 0,
                        "subs": st.get("subs", 0), "timed": st.get("timed", 0)})

    def _narration_region(self):
        """Which stretch of the text a recording covers -- the from/to a
        panel row carries.  The times already measured are not touched: what
        changes is which subparagraphs the next align will re-time."""
        b = self._narration_book()
        if not b:
            return self.send_json({"ok": False, "error": "no book here"}, 404)
        body = self._json_body() or {}
        want = str(body.get("id") or "").strip()
        recs = list(b.narrations)
        hit = next((r for r in recs if r["id"] == want), None)
        if not hit:
            return self.send_json({"ok": False, "error":
                                   "no recording called %r here" % want}, 400)
        keep = []
        for r in recs:
            rec = {"id": r["id"], "audio": r["audio_rel"],
                   "transcript": r["transcript_rel"], "from": r["from"], "to": r["to"]}
            if r["id"] == want:
                rec["from"] = str(body.get("from") or "").strip()
                rec["to"] = str(body.get("to") or "").strip()
                bad = self._region_error(b, rec["from"], rec["to"])
                if bad:
                    return self.send_json({"ok": False, "error": bad}, 400)
                if "transcript" in body:
                    rec["transcript"] = str(body.get("transcript") or "").strip()
            keep.append(rec)
        out = set_narrations(b, keep)
        ok, log, err = self._rebuild(b)
        return self.send_json({"ok": ok, "narrations": out, "log": log, "error": err})

    def _narration_remove(self):
        """Take a recording off the book.  The FILE STAYS on the shelf -- a
        recording cannot be made again, and this door is for saying "this one
        is not part of the book", not for throwing work away."""
        b = self._narration_book()
        if not b:
            return self.send_json({"ok": False, "error": "no book here"}, 404)
        want = str((self._json_body() or {}).get("id") or "").strip()
        recs = list(b.narrations)
        if not any(r["id"] == want for r in recs):
            return self.send_json({"ok": False, "error":
                                   "no recording called %r here" % want}, 400)
        keep = [{"id": r["id"], "audio": r["audio_rel"],
                 "transcript": r["transcript_rel"], "from": r["from"], "to": r["to"]}
                for r in recs if r["id"] != want]
        if keep:
            out = set_narrations(b, keep)
        else:
            out = []
            set_book_meta(b.dir, audio=None, transcript=None, narrations=[])
        ok, log, err = self._rebuild(b)
        return self.send_json({"ok": ok, "narrations": out, "log": log, "error": err})

    def _narration_export(self):
        """One file -- the audio, timings.json, the transcript, a manifest --
        to keep with the book or to hand to another reader of the edition."""
        b = self._narration_book()
        if not b or not b.has_audio:
            return self.send_json({"ok": False, "error": "there is no narration to export"}, 404)
        ti = timings_info(b)
        aname = os.path.basename(b.audio)
        tname = os.path.basename(b.transcript) if b.has_transcript else None
        manifest = {"format": NARR_FORMAT, "software": NAME, "book": b.slug,
                    "title": b.title, "title_latin": b.title_latin,
                    "audio": aname, "transcript": tname,
                    "timings": "timings.json" if ti["subs"] else None,
                    "subs": ti["subs"], "manual": ti["manual"],
                    "exported": time.strftime("%Y-%m-%dT%H:%M:%S")}
        fd, tmp = tempfile.mkstemp(suffix=".zip")
        os.close(fd)
        try:
            with zipfile.ZipFile(tmp, "w") as z:
                z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1),
                           compress_type=zipfile.ZIP_DEFLATED)
                z.write(b.audio, aname, compress_type=zipfile.ZIP_STORED)   # already compressed
                if ti["subs"]:
                    z.write(b.timings, "timings.json", compress_type=zipfile.ZIP_DEFLATED)
                if tname:
                    z.write(b.transcript, tname, compress_type=zipfile.ZIP_DEFLATED)
            self._send_file(tmp, "application/zip", "%s-narration.zip" % b.slug)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def _send_file(self, path, ctype, download_name):
        size = os.path.getsize(path)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Content-Disposition", 'attachment; filename="%s"' % download_name)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self._head:
            return
        with open(path, "rb") as f:
            try:
                self._pour(f, size)
            except GONE:
                self.close_connection = True
                self._failed = True

    def _run_steps(self, steps):
        """The lib/ tools, one after another, under this same interpreter;
        the first failure stops the run and names itself."""
        log = []
        for what, c, cwd in steps:
            log.append("== " + what)
            try:
                r = subprocess.run([sys.executable] + c, cwd=cwd, capture_output=True,
                                   text=True, timeout=3600)
            except Exception as e:
                log.append("%s: %s" % (os.path.basename(c[0]), e))
                return False, "\n".join(log), "%s did not run" % what
            log.append((r.stdout + r.stderr).strip())
            if r.returncode:
                return False, "\n".join(log), "%s failed (%s)" % (what, os.path.basename(c[0]))
        return True, "\n".join(log), ""

    def _rebuild(self, b):
        """What every change to the narration ends with: the .tex comments
        from timings.json when there is one, then the reader, then the
        library page."""
        steps = []
        if os.path.isfile(b.timings):
            steps.append(("times from timings.json",
                          [os.path.join(LIB, "timestamp.py"), "--from-sidecar"], b.dir))
        steps += [("reader", [os.path.join(LIB, "tex2html.py")], b.dir),
                  ("library page", [os.path.join(LIB, "make_index.py")], ROOT)]
        return self._run_steps(steps)

    def _narration_transcript(self):
        """The transcript with its timestamps, saved beside the audio.

        ONE RECORDING'S, when ?narration= names one: audio/transcript-<id>.<ext>,
        written into that record rather than into the book.  A book recorded in
        parts has a transcript per part -- the aligner has always preferred a
        record's own over the book's scalars, books.py has always read the
        field, and __narration/region has always persisted it -- and this was
        the one door that could not write one, so every row's `align` was dead
        for ever and the panel offered a book-wide transcript for a thing that
        is not book-wide.  Without the parameter it stays exactly as it was:
        audio/transcript.<ext> and book.json's scalar.
        """
        b = self._narration_book()
        if not b:
            return self.send_json({"ok": False, "error": "no book here"}, 404)
        raw = (self.query.get("name") or [""])[0]
        ext = os.path.splitext(raw)[1].lower()
        if ext not in (".txt", ".srt", ".vtt", ".json"):
            ext = ".txt"
        nid = (self.query.get("narration") or [""])[0].strip()
        rec = b.narration(nid) if nid else None
        if nid and not rec:
            return self.send_json({"ok": False,
                                   "error": "no recording called %r here" % nid}, 400)
        text = self._raw.decode("utf-8-sig", errors="replace").strip()
        if not text:
            return self.send_json({"ok": False, "error": "the transcript is empty"}, 400)
        adir = os.path.join(b.dir, "audio")
        os.makedirs(adir, exist_ok=True)
        stem = ("transcript-" + nid) if nid else "transcript"
        path = os.path.join(adir, stem + ext)
        tmp = path + ".part"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        try:
            segs = tstamp.parse_transcript(tmp)
        except Exception as e:
            segs = []
            err = str(e)
        else:
            err = ""
        if not segs:
            os.unlink(tmp)
            return self.send_json(
                {"ok": False, "error": "no timestamps found in it" + (": " + err if err else "")
                 + " -- it must carry clock lines (0:00, 1:23:45), .srt/.vtt cues, "
                 "or whisper's segments"}, 400)
        os.replace(tmp, path)
        for old in (".txt", ".srt", ".vtt", ".json"):   # one transcript, not four
            if old != ext:
                try:
                    os.unlink(os.path.join(adir, stem + old))
                except OSError:
                    pass
        rel = "audio/" + stem + ext
        if rec:
            # into the record, through the one writer of the list, so the
            # scalars stay true to the first recording as they always have.
            # Built from transcript_rel throughout -- `transcript` is the
            # absolute path and is None where there is none, and mixing the
            # two is how a relative field ends up holding an absolute path.
            set_narrations(b, [{"id": r["id"], "audio": r["audio_rel"],
                                "transcript": rel if r["id"] == rec["id"]
                                              else r["transcript_rel"],
                                "from": r["from"], "to": r["to"]}
                               for r in b.narrations])
        else:
            set_book_meta(b.dir, transcript=rel)
        self.send_json({"ok": True, "file": stem + ext, "narration": nid,
                        "segments": len(segs), "span": round(segs[-1][1], 1)})

    def _narration_status(self):
        b = self._narration_book()
        if not b:
            return self.send_json({"ok": False, "error": "no book here"}, 404)
        st = make_index.stats(b)

        def finfo(declared, path):
            # WHETHER THIS FILE IS THERE, asked of this file.  It used to be
            # b.has_audio, which is true when ANY recording is there: a book
            # recorded in parts whose first file was missing then had its size
            # read off that missing path, and the FileNotFoundError was a 500
            # that took the narration panel and the download sheet with it.
            there = bool(path) and os.path.isfile(path)
            return {"declared": declared, "path": declared, "exists": there,
                    "bytes": os.path.getsize(path) if there else 0}
        audio = finfo(b.meta.get("audio"), b.audio)
        tr = finfo(b.meta.get("transcript"), b.transcript)
        if b.has_transcript:
            try:
                segs = tstamp.parse_transcript(b.transcript)
                tr["segments"] = len(segs)
                tr["span"] = round(segs[-1][1], 1) if segs else 0
            except Exception:
                tr["segments"] = 0
        labels = self._sub_labels(b, subkeys=True)
        def nrec(n):
            there = bool(n["audio"] and os.path.exists(n["audio"]))
            # has_transcript is written either way, never left absent: a panel
            # that reads three fields to decide whether a row may be aligned
            # cannot tell "no transcript" from "the server did not say"
            out = {"id": n["id"], "audio": n["audio_rel"],
                   "transcript": n["transcript_rel"],
                   "from": n["from"], "to": n["to"], "exists": there,
                   "bytes": os.path.getsize(n["audio"]) if there else 0,
                   "timed": 0, "has_transcript": False, "segments": 0}
            if n["transcript"] and os.path.exists(n["transcript"]):
                out["has_transcript"] = True
                try:
                    segs = tstamp.parse_transcript(n["transcript"])
                    out["segments"] = len(segs)
                    # what the row says about it: "42 timestamps over 1:12:30"
                    out["span"] = round(segs[-1][1], 1) if segs else 0
                except Exception:
                    out["segments"] = 0
            return out

        # HOW MANY SUBPARAGRAPHS EACH RECORDING HAS TIMED.  By the sidecar's
        # "n" where it is there, and BY REGION where it is not -- which is the
        # common case and not an odd one.  timestamp.py attributes a time only
        # once a book has more than one recording, and the hand-stamping door
        # (__save/subtimes.json) never attributes at all, so the times of a
        # book's first recording carry no id and every time stamped by ear is
        # unattributed for ever.  Counting only by "n" therefore reported 0
        # against a recording that plainly plays, beside a summary saying most
        # of the book was timed -- two numbers on one panel contradicting each
        # other.  Falling back to the region is not a guess: it is what the
        # reader itself does to decide which file to play (narrFor), and the
        # ordered label list is already in hand for the pickers.
        # WHERE EACH STRETCH IS, read the way the aligner reads it
        # (texparse.region_bounds): an end named with its chapter, "2:4.3", is
        # exactly one subparagraph, and a bare label the first or the last
        # wearing it.  A stretch that names a label the book no longer has
        # has no span, and its row says so rather than counting against
        # somebody else's subparagraphs.
        import texparse as T
        pairs = [(e["chapter"], e["label"]) for e in labels]
        spans, span_of = [], {}
        for n in b.narrations:
            try:
                lo, hi = T.region_bounds(pairs, n["from"], n["to"])
            except ValueError:
                continue
            spans.append((n["id"], lo, hi))
            span_of[n["id"]] = (lo, hi)
        # a timed subparagraph is found by the key its time is filed under,
        # which is unique; the label it also carries is not
        at_key = {e["subkey"]: i for i, e in enumerate(labels)}
        # HOW BIG EACH STRETCH IS, so a row can say "21 of 21 timed" rather
        # than a count with nothing to measure it against, and how many of its
        # times were stamped by ear -- which is what a reader wants to know
        # before letting an alignment start over on top of them.
        size = {i: (hi - lo + 1) for i, lo, hi in spans}
        timed, hand = {}, {}
        try:
            with open(b.timings, encoding="utf-8") as f:
                for key, rec in (json.load(f).get("subs") or {}).items():
                    if not isinstance(rec, dict) or rec.get("t0") is None:
                        continue
                    # "N OF M TIMED" IS ABOUT THOSE M SUBPARAGRAPHS.  A time
                    # counts for a recording only inside the stretch it
                    # covers: by the id it carries, or -- carrying none -- by
                    # being inside exactly one stretch.  Not a time filed
                    # under a key the book no longer has (its text changed
                    # since; the build writes nothing from it), and not one a
                    # recording's id carries elsewhere -- an estimate once
                    # spread over a stretch read too widely, which made nine
                    # recordings of chapter 1 claim times in chapters 3 to 5.
                    at = at_key.get(key)
                    if at is None:
                        continue
                    hit = [i for i, lo, hi in spans if lo <= at <= hi]
                    nid = rec.get("n") or ""
                    whose = (nid if nid in hit else "") if nid else \
                        (hit[0] if len(hit) == 1 else "")
                    if whose:
                        timed[whose] = timed.get(whose, 0) + 1
                        if rec.get("src") == "manual":
                            hand[whose] = hand.get(whose, 0) + 1
        except (OSError, ValueError):
            pass
        narrs = []
        for n in b.narrations:
            r = nrec(n)
            r["timed"] = timed.get(n["id"], 0)
            r["subs"] = size.get(n["id"], 0)
            r["manual"] = hand.get(n["id"], 0)
            # the subparagraphs it covers, first and last, as indices into
            # `labels` (null when its ends name nothing in this book): what
            # the reader's outline marks each chapter with
            r["lo"], r["hi"] = span_of.get(n["id"], (None, None))
            narrs.append(r)
        self.send_json({
            "ok": True, "slug": b.slug, "title_latin": b.title_latin,
            "audio": audio, "transcript": tr,
            "narrations": narrs,
            "labels": [{k: v for k, v in e.items() if k != "subkey"} for e in labels],
            # WHAT EACH OF THE THREE DOWNLOADS CARRIES, summed from what
            # lib/bundle.py will pack: the download sheet says how big each
            # is, and "all of it" is every recording under audio/ -- not the
            # first one, which is all `audio` above is about
            "bundle": {m: bundle.payload("book", b.dir, m) for m in bundle.MODES},
            "timings": timings_info(b), "candidates": narration_candidates(b),
            "built": bool(st.get("built")), "subs": st.get("subs", 0),
            "timed": st.get("timed", 0),
            "audio_dir": "books/%s/audio/" % b.rel_from_books(),
            "tools": {"rapidfuzz": importlib.util.find_spec("rapidfuzz") is not None,
                      "ffmpeg": have_ffmpeg(), "python": sys.executable}})

    def _narration_align(self):
        """lib/timestamp.py, then the reader and the library page -- what the
        command line does, from a button."""
        b = self._narration_book()
        if not b:
            return self.send_json({"ok": False, "error": "no book here"}, 404)
        try:
            opts = self._json_body()
        except Exception:
            opts = {}
        # WHICH FILES THIS RUN NEEDS.  Aligning one recording asks after that
        # recording's own audio and transcript: the book-wide scalars name the
        # FIRST one, and judging a second by them refused a run whose files
        # were both sitting there.
        asked = str(opts.get("narration") or "").strip()
        rec = b.narration(asked) if asked else None
        if rec:
            have_audio = bool(rec["audio"] and os.path.exists(rec["audio"]))
            have_tr = bool(rec["transcript"] and os.path.exists(rec["transcript"]))
        else:
            have_audio, have_tr = b.has_audio, b.has_transcript
        if not have_audio or not have_tr:
            return self.send_json({"ok": False, "error": "the audio and the transcript "
                                   "both have to be there first"}, 400)
        cmd = [os.path.join(LIB, "timestamp.py")]
        # one recording at a time: only the text it covers is re-timed, and
        # every other stretch keeps the times it has
        want = str(opts.get("narration") or "").strip()
        if want:
            if not b.narration(want):
                return self.send_json({"ok": False, "error":
                                       "no recording called %r here" % want}, 400)
            cmd += ["--narration", want]
        if opts.get("force"):
            cmd.append("--force")
        if not have_ffmpeg():
            cmd.append("--no-snap")
        ok, log, err = self._run_steps(
            [("align", cmd, b.dir),
             ("reader", [os.path.join(LIB, "tex2html.py")], b.dir),
             ("library page", [os.path.join(LIB, "make_index.py")], ROOT)])
        st = make_index.stats(b)
        self.send_json({"ok": ok, "log": log, "error": err,
                        "subs": st.get("subs", 0), "timed": st.get("timed", 0)})

    def _shutdown(self):
        self.send_json({"ok": True, "stopping": True})
        # answer first, then stop from another thread so the reply is delivered
        threading.Thread(target=self.server.shutdown, daemon=True).start()


class _Limited:
    """A file object that stops after n bytes, for copyfile()."""
    def __init__(self, f, n):
        self.f, self.n = f, n

    def read(self, size=-1):
        if self.n <= 0:
            return b""
        if size < 0 or size > self.n:
            size = self.n
        b = self.f.read(size)
        self.n -= len(b)
        return b

    def close(self):
        self.f.close()


# ------------------------------------------------------------------ the server
class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 64

    def __init__(self, addr, handler, ssl_ctx=None):
        self.ssl_ctx = ssl_ctx
        super().__init__(addr, handler)

    def handle_error(self, request, client_address):
        """socketserver prints a full traceback for anything that escapes a
        handler.  A client that went away, a TLS probe or an abandoned
        handshake are weather, not faults; everything else still gets its
        traceback, because a real bug in a handler should not be silent."""
        err = sys.exc_info()[1]
        if isinstance(err, GONE + (ssl.SSLError,)):
            return
        super().handle_error(request, client_address)

    def finish_request(self, request, client_address):
        """Wrap the connection in TLS HERE, in the worker thread.

        Wrapping the listening socket instead would run every handshake in
        the accept loop, where one slow or abandoned client stalls all the
        others.  Before the handshake, one peek at the first byte tells a
        TLS ClientHello (0x16) from a plain-http request line, which gets a
        redirect to the https address rather than a cryptic failure.
        """
        if self.ssl_ctx is None:
            return super().finish_request(request, client_address)
        try:
            request.settimeout(15)
            head = request.recv(8, socket.MSG_PEEK)
        except OSError:
            head = b""
        if not head:
            return _close(request)
        if head[:1] != b"\x16":
            return self._plain_http(request, head)
        tls = None
        try:
            tls = self.ssl_ctx.wrap_socket(request, server_side=True,
                                           do_handshake_on_connect=False)
            tls.do_handshake()
        except (ssl.SSLError, OSError):
            return _close(tls or request)
        try:
            self.RequestHandlerClass(tls, client_address, self)
        finally:
            _close(tls)

    def _plain_http(self, request, head):
        if re.match(rb"^[A-Z]{3,7} ", head):
            try:
                data = request.recv(4096)
            except OSError:
                data = b""
            line = data.split(b"\r\n", 1)[0].decode("latin-1", "replace")
            m = re.match(r"^[A-Z]+ (\S+) HTTP/", line)
            target = m.group(1) if m else "/"
            hm = re.search(rb"\r\nHost:[ \t]*([^\r\n]+)", data, re.I)
            host = hm.group(1).decode("latin-1", "replace").strip() if hm else ""
            host = host.rsplit(":", 1)[0] if re.search(r":\d+$", host) else host
            if not host:
                host = self.server_address[0]
            where = "https://%s:%d%s" % (host, self.server_address[1], target)
            body = ("<!doctype html><title>https</title><p>%s is served over "
                    "https: <a href=\"%s\">%s</a>" % (NAME, where, where)).encode()
            try:
                request.sendall(
                    b"HTTP/1.1 301 Moved Permanently\r\n"
                    b"Location: " + where.encode() + b"\r\n"
                    b"Content-Type: text/html; charset=utf-8\r\n"
                    b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                    b"Connection: close\r\n\r\n" + body)
            except OSError:
                pass
        _close(request)


def _close(sock):
    try:
        sock.close()
    except OSError:
        pass


# ------------------------------------------------------------------ the certificate
def cert_names():
    """Every name and address this machine answers to, for the SAN."""
    host = socket.gethostname()
    names = ["localhost", host]
    ips = ["127.0.0.1"]

    def add_ip(ip):
        if ip and "." in ip and ":" not in ip and ip not in ips:
            ips.append(ip)

    try:
        for info in socket.getaddrinfo(host, None, socket.AF_INET):
            add_ip(info[4][0])
    except OSError:
        pass
    for cmd in (["hostname", "-I"], ["tailscale", "ip", "-4"]):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
            for ip in out.stdout.split():
                add_ip(ip)
        except Exception:
            pass
    try:                                # the tailnet name, if there is one
        out = subprocess.run(["tailscale", "status", "--json"],
                             capture_output=True, text=True, timeout=4)
        m = re.search(r'"DNSName":\s*"([^"]+)"', out.stdout)
        if m:
            dns = m.group(1).rstrip(".")
            if dns and dns not in names:
                names.append(dns)
    except Exception:
        pass
    return names, ips


# WHAT A PHONE CAN BE TOLD TO TRUST.  A browser tab accepts a certificate
# nobody vouches for after one warning; an app does not -- a phone installs
# the mobile interface as an app (docs/mobile.md, "Parseh as an app") only
# from a server whose certificate it trusts.  So the certificate is two:
#   ca.pem / ca-key.pem   an authority of this machine's own, made once and
#                         kept.  It is what a phone is told to trust, once
#                         (/m/install/ hands it over, lib/mobile.py).
#   cert.pem / key.pem    the server's, signed by it for every name and
#                         address the machine has, 825 days at a time (the
#                         most an iPhone accepts), made again as it nears its
#                         end or when --cert asks -- and trusted wherever the
#                         authority is, with nothing installed again.
# THE AUTHORITY CAN VOUCH FOR THIS MACHINE AND NOTHING ELSE.  An authority on
# a phone vouches for every site it signs for, so this one is made unable to
# sign for any site at all (nameConstraints): only localhost, this machine's
# own name, a .local or tailnet (.ts.net) name, and the private and Tailscale
# address ranges.  Were its key ever copied off this machine, it would still
# be good for nothing on the internet.
TLS_DAYS = 825
TLS_RENEW = 30 * 86400              # made again when it has less left than this
TLS_PERMITTED = {
    "DNS": ["localhost", "local", "ts.net"],
    # 127/8, the three private ranges, and Tailscale's 100.64/10
    "IP": ["127.0.0.0/255.0.0.0", "10.0.0.0/255.0.0.0", "172.16.0.0/255.240.0.0",
           "192.168.0.0/255.255.0.0", "100.64.0.0/255.192.0.0"],
}


def _ip_permitted(ip):
    import ipaddress
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for r in TLS_PERMITTED["IP"]:
        net, mask = r.split("/")
        if a in ipaddress.ip_network("%s/%s" % (net, mask)):
            return True
    return False


def _openssl(args, what):
    r = subprocess.run(["openssl"] + args, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("openssl could not make %s:\n%s" % (what, r.stderr))
    return r.stdout


def _cfg(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def _made_here(cert):
    """Was this certificate made by make_cert before it had an authority --
    self-signed, O=Parseh -- rather than put in .tls/ by hand?"""
    try:
        r = subprocess.run(["openssl", "x509", "-in", cert, "-noout", "-subject", "-issuer",
                            "-nameopt", "RFC2253"], capture_output=True, text=True, timeout=10)
    except Exception:
        return False
    said = dict(line.split("=", 1) for line in r.stdout.splitlines() if "=" in line)
    subject, issuer = said.get("subject", "").strip(), said.get("issuer", "").strip()
    return bool(subject) and subject == issuer and ("O=%s" % NAME) in subject.split(",")


def _ends_soon(cert):
    r = subprocess.run(["openssl", "x509", "-in", cert, "-noout", "-checkend", str(TLS_RENEW)],
                       capture_output=True, text=True)
    return r.returncode != 0


def make_authority():
    """The machine's own authority, ca.pem and ca-key.pem (see above)."""
    host = socket.gethostname() or "this machine"
    ca, ca_key = os.path.join(TLS_DIR, "ca.pem"), os.path.join(TLS_DIR, "ca-key.pem")
    permitted = ["permitted;DNS.%d = %s" % (i, n) for i, n in enumerate(TLS_PERMITTED["DNS"] + [host])]
    permitted += ["permitted;IP.%d = %s" % (i, r) for i, r in enumerate(TLS_PERMITTED["IP"])]
    cfg = _cfg(os.path.join(TLS_DIR, "ca.cnf"), """[req]
distinguished_name = dn
prompt = no
x509_extensions = ext
[dn]
CN = %s local authority (%s)
O = %s
[ext]
basicConstraints = critical,CA:TRUE,pathlen:0
keyUsage = critical,keyCertSign,cRLSign
subjectKeyIdentifier = hash
nameConstraints = critical,@permitted
[permitted]
%s
""" % (NAME, host, NAME, "\n".join(permitted)))
    try:
        _openssl(["req", "-x509", "-config", cfg, "-newkey", "rsa:2048", "-sha256", "-days", "3650",
                  "-nodes", "-keyout", ca_key, "-out", ca], "the authority")
    finally:
        os.remove(cfg)
    os.chmod(ca_key, 0o600)
    print("a local authority for this machine written to %s/ca.pem: a phone told to trust it "
          "can install the mobile interface as an app" % TLS_DIR)
    return ca, ca_key


def make_server_cert(ca, ca_key):
    """cert.pem (the server's, then the authority's: the chain it sends) and
    key.pem, for every name and address the machine has that the authority
    may vouch for."""
    names, ips = cert_names()
    names = [n for n in names if n == names[1] or n == "localhost" or n.endswith((".local", ".ts.net"))]
    ips = [i for i in ips if _ip_permitted(i)]
    san = ",".join(["DNS:%s" % n for n in names] + ["IP:%s" % i for i in ips])
    cert, key = os.path.join(TLS_DIR, "cert.pem"), os.path.join(TLS_DIR, "key.pem")
    csr, leaf = os.path.join(TLS_DIR, "server.csr"), os.path.join(TLS_DIR, "server.pem")
    cfg = _cfg(os.path.join(TLS_DIR, "server.cnf"), """[req]
distinguished_name = dn
prompt = no
[dn]
CN = %s
O = %s
[ext]
basicConstraints = critical,CA:FALSE
keyUsage = critical,digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = %s
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
""" % (names[1] if len(names) > 1 else names[0], NAME, san))
    try:
        _openssl(["req", "-new", "-config", cfg, "-newkey", "rsa:2048", "-nodes",
                  "-keyout", key, "-out", csr], "the certificate")
        # a serial nobody else's is: 16 random bytes, the first bit clear
        serial = "0x%032x" % (int.from_bytes(os.urandom(16), "big") >> 1)
        _openssl(["x509", "-req", "-in", csr, "-CA", ca, "-CAkey", ca_key, "-set_serial", serial,
                  "-days", str(TLS_DAYS), "-sha256", "-extfile", cfg, "-extensions", "ext",
                  "-out", leaf], "the certificate")
        with open(leaf, encoding="utf-8") as a, open(ca, encoding="utf-8") as b, \
                open(cert, "w", encoding="utf-8") as out:
            out.write(a.read() + b.read())
    finally:
        for p in (cfg, csr, leaf):
            if os.path.exists(p):
                os.remove(p)
    os.chmod(key, 0o600)
    with open(os.path.join(TLS_DIR, "names.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(names + ips) + "\n")
    print("certificate written to %s/ (valid for: %s)" % (TLS_DIR, san))
    return cert, key


def make_cert(force=False):
    """The certificate the server speaks TLS with, in .tls/, made once and
    reused (see WHAT A PHONE CAN BE TOLD TO TRUST, above): the server's own,
    made again when it nears its end or `force` asks, under an authority
    made once.  A certificate made here before there was an authority (one
    self-signed, O=Parseh) is replaced by the pair once -- each browser warns
    about the new one once, as it did about the old.  One put in .tls/ by
    hand -- Tailscale's, or Let's Encrypt's -- is used as it is and never
    touched."""
    cert = os.path.join(TLS_DIR, "cert.pem")
    key = os.path.join(TLS_DIR, "key.pem")
    ca, ca_key = os.path.join(TLS_DIR, "ca.pem"), os.path.join(TLS_DIR, "ca-key.pem")
    have = os.path.isfile(cert) and os.path.isfile(key)
    have_ca = os.path.isfile(ca) and os.path.isfile(ca_key)
    if have and not force:
        if not shutil.which("openssl"):
            return cert, key
        if not have_ca and not _made_here(cert):
            return cert, key                    # somebody's own: used as it is
        if have_ca and not _ends_soon(cert):
            return cert, key
    if not shutil.which("openssl"):
        raise SystemExit(
            "openssl is needed to make the certificate (apt install openssl),\n"
            "or run with --http to serve without TLS")
    os.makedirs(TLS_DIR, exist_ok=True)
    if not have_ca:
        ca, ca_key = make_authority()
    return make_server_cert(ca, ca_key)


def authority_der():
    """The authority's certificate, DER-encoded, for a phone to install; None
    when there is none (plain http, or a certificate put in .tls/ by hand)."""
    try:
        with open(os.path.join(TLS_DIR, "ca.pem"), encoding="ascii") as f:
            return ssl.PEM_cert_to_DER_cert(f.read())
    except (OSError, ValueError):
        return None


def addresses():
    """Every address this machine can be reached on, Tailscale first."""
    out = []
    try:
        ts = subprocess.run(["tailscale", "ip", "-4"], capture_output=True,
                            text=True, timeout=4).stdout.split()
        out += [(ip, "tailscale") for ip in ts if ip]
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip.startswith("100.") and not any(ip == a for a, _ in out):
                out.append((ip, "tailscale"))
            elif not ip.startswith("127.") and not any(ip == a for a, _ in out):
                out.append((ip, "local network"))
    except Exception:
        pass
    out.append(("localhost", "this machine"))
    return out


def main():
    ap = argparse.ArgumentParser(description="%s -- the whole toolbox, one server" % NAME)
    ap.add_argument("port", nargs="?", type=int, default=DEFAULT_PORT)
    ap.add_argument("--port", dest="port_opt", type=int)
    ap.add_argument("--host", default=None,
                    help="bind one address only (e.g. your Tailscale IP)")
    ap.add_argument("--local", action="store_true", help="bind 127.0.0.1 only")
    ap.add_argument("--http", action="store_true",
                    help="plain http, no TLS (screen capture and the clipboard "
                         "then work on localhost only)")
    ap.add_argument("--cert", action="store_true",
                    help="make a fresh certificate in .tls/ and exit")
    args = ap.parse_args()
    if args.cert:
        make_cert(force=True)
        return
    port = args.port_opt or args.port
    host = "127.0.0.1" if args.local else (args.host or "0.0.0.0")
    scheme = "http" if args.http else "https"

    ctx = None
    if not args.http:
        cert, key = make_cert()
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(cert, key)

    all_bks = booklib.all_books()
    if all_bks:
        print("books:")
    for b in all_bks:
        b.check_placement()                # a book filed under the wrong language folder
        print("  %-36s %s%s" % (b.rel_from_books(), b.lang.name,
                                "" if b.has_audio else "  (no narration)"))
        if b.audio and not b.has_audio:    # a declared narration that is not there
            print("!! %s declares a narration at %s, which is missing -- the reader's "
                  "narration panel says so" % (b.slug, os.path.relpath(b.audio, ROOT)))

    # the studio's own start-up: fonts into its static/, whatever example
    # documents exlex/examples/ holds (none at present), the hyphenation
    # patterns -- all idempotent, all quiet
    studio.ensure_web_fonts()
    studio.seed_example()
    studio.migrate_library()
    # the built readers link lib/langs.css relatively: keep the file on disk
    # in step with the registry (make_index.py writes it at build time too)
    try:
        languages.write_css()
    except OSError as e:
        print("!! could not write lib/langs.css: %s (the route still answers)" % e)
    studio.ensure_build_env_async()

    os.chdir(ROOT)
    httpd = Server((host, port), Handler, ctx)
    studio.SERVER["instance"] = httpd     # so the studio's stop button works too
    if host == "0.0.0.0":
        ADDRESSES[:] = ["%s://%s:%d/" % (scheme, ip, port) for ip, _ in addresses()]
    else:
        ADDRESSES[:] = ["%s://%s:%d/" % (scheme, host, port)]
    print("%s: serving %s on %s:%d (%s)\n" % (NAME, ROOT, host, port, scheme))
    if host == "0.0.0.0":
        for (ip, what), url in zip(addresses(), ADDRESSES):
            print("  %-42s (%s)" % (url, what))
    else:
        print("  " + ADDRESSES[0])
    print("\n  /books/  /youtube/  /studio/  /exercises/  /anki/sync/")
    if ctx:
        print("\nself-signed certificate: each browser warns once -- accept it.")
    print("Ctrl-C, or any of the page's stop buttons, to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    print("stopped.")


if __name__ == "__main__":
    main()
