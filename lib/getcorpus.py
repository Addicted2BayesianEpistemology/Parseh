#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build one parallel corpus: sentences somebody has already translated.

    python3 lib/getcorpus.py                  what is installed
    python3 lib/getcorpus.py fa               Persian, glossed in English
    python3 lib/getcorpus.py fa it            Persian, glossed in Italian
    python3 lib/getcorpus.py --all            every language, glossed in English

THE SOURCE IS TATOEBA, whose sentences are written and translated by people
and released under CC BY 2.0 FR.  It is the same arrangement as the
dictionary: somebody else's work, downloaded once, kept in one file per
language pair under `corpus/`, and never shipped with the toolbox.  Nothing
here is required, nothing is sent anywhere, and a language with no corpus is
read exactly as it is read today.

WHAT IS DOWNLOADED, and why it is three files.  Tatoeba exports sentences per
language and the LINKS between them separately, because a sentence may be
translated into thirty languages and is stored once.  So a Persian-English
corpus is `pes_sentences`, `eng_sentences` and `pes-eng_links` -- and only
the English sentences the links actually name are kept, which is why the
24 MB English export does not become 24 MB of Persian corpus.

THE INDEX IS BUILT HERE, not asked for at read time.  Two tables: which
sentences hold which word, and how many sentences hold each word.  The
second is what makes a match mean anything (lib/corpus.py weights by it),
and it is a count, so it costs one pass and no judgement.
"""
import argparse
import bz2
import io
import os
import sys
import time
import urllib.error

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import corpus                                                 # noqa: E402
import languages                                              # noqa: E402
import lookup                                                 # noqa: E402
import version                                                # noqa: E402  who is asking: UA
import download       # noqa: E402  resumable, stoppable, and says how far

SOURCE = "Tatoeba (tatoeba.org)"
LICENCE = "CC BY 2.0 FR"
BASE = "https://downloads.tatoeba.org/exports/per_language"
UA = "Parseh/%s (+https://github.com/Addicted2BayesianEpistemology/Parseh)" % version.VERSION

# WHAT A CORPUS COSTS, MEASURED: (its three exports' download, the built
# corpus), in bytes, for the pairs somebody has built.  Read by plan(), so
# the Reading help page can say how big before anybody presses a button.
# The built sizes are the corpora built on 2026-09-24 (and docs/languages.md's
# Spanish-English, 83 MB); the downloads were read from Tatoeba's own
# Content-Length on 2026-09-25 -- the English export alone is 25 MB, which is
# why every pair with English costs at least that to fetch, however few
# sentences it keeps (Persian-English: 25 MB fetched, 3 MB kept).  Tatoeba
# re-exports every week and grows, so these are "about".  A pair not here is
# asked: plan() reads the three sizes from Tatoeba before anything is
# fetched.
MEASURED = {
    ("it", "en"): (38_200_000, 182_600_000),
    ("en", "it"): (38_200_000, 178_600_000),
    ("tr", "en"): (37_700_000, 191_300_000),
    ("fa", "en"): (25_400_000, 3_300_000),
    ("es", "en"): (None, 83_000_000),
}

# NO CORPUS MEASURED BUILT BIGGER THAN ABOUT FIVE TIMES ITS DOWNLOAD
# (Italian-English 4.8, Turkish-English 5.1: the exports are bzip2, and the
# index adds a row per word of every sentence kept).  A pair whose size is
# not in MEASURED is given room for six times its download before the build
# starts -- a bound, stated as one, not a measurement.
BOUND = 6

# A sentence longer than this is not an illustration of a chunk, it is a
# paragraph; and the index it would add is mostly common words.
MAX_LEN = 300


def _url(iso, name):
    return "%s/%s/%s" % (BASE, iso, name)


def _fetch(url, dest, say=print, progress=None, cancel=None):
    """Download to `dest`, reporting as it goes.  The files are kilobytes
    to 25 MB, and the three of a pair used to be fetched whole each time;
    now lib/download.py resumes whichever of them a dropped line or Stop
    cut short, and `dest` is only ever a whole file -- which is what lets
    build() trust one it finds already here."""
    say("    %s" % url.rsplit("/", 1)[-1])
    try:
        download.fetch(url, dest, say=say, progress=progress, cancel=cancel,
                       headers={"User-Agent": UA})
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise SystemExit(
                "getcorpus: Tatoeba has no %s.\n"
                "  It keys its exports by ISO 639-3, which the registry holds "
                "as `iso3`." % url.rsplit("/", 1)[-1])
        raise SystemExit("getcorpus: could not download (%s)" % e)
    except OSError as e:
        raise SystemExit("getcorpus: could not download (%s).  What came is "
                         "kept: the next try carries on from there." % e)


def _lines(path, at=None):
    """The lines of a bzip2 export, telling `at` (a fraction, 0 to 1) how
    much of the FILE has been read -- the compressed bytes, the one count
    known before reading starts."""
    size = float(os.path.getsize(path) or 1)
    with io.open(path, "rb") as raw, \
            bz2.open(raw, "rt", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            if at is not None and i % 1000 == 0:
                at(raw.tell() / size)
            yield line


def _sentences(path, want=None, at=None):
    """{id: text} out of a Tatoeba sentences export, keeping only `want`.

    The English export is a million and a half sentences and the links name
    a few thousand of them; reading the whole file is unavoidable but
    keeping the whole file is not.
    """
    out = {}
    for line in _lines(path, at):
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            continue
        sid = parts[0]
        if want is not None and sid not in want:
            continue
        text = parts[2].strip()
        if text and len(text) <= MAX_LEN:
            out[sid] = text
    return out


def _links(path, at=None):
    """[(src id, dst id)] out of a Tatoeba links export."""
    out = []
    for line in _lines(path, at):
        parts = line.rstrip("\n").split("\t")
        if len(parts) >= 2 and parts[0] and parts[1]:
            out.append((parts[0], parts[1]))
    return out


def _known(code, what):
    """The registry's language, or a refusal naming what it does not know.

    NOT get_or_default.  That one answers Persian for anything it does not
    recognise, which is right for a book written before languages were
    declared and wrong here: `getcorpus.py it pt` means Italian glossed in
    Portuguese, and it quietly downloaded Persian instead, built
    `corpus/it-fa.db`, and reported it built -- a file whose name is a claim
    about what is in it.  Refused here, where the build begins, so that the
    button on the reading-help page is answered the same as the command
    line."""
    L = languages.LANGS.get((code or "").strip().lower())
    if L is None:
        raise SystemExit("getcorpus: %r is not a language Parseh knows (%s): "
                         "the %s was not understood, and nothing was built"
                         % (code, ", ".join(languages.CODES), what))
    return L


def _files(L, G):
    """The three exports a pair is built from, as (iso3 folder, name):
    the links, the language's sentences, the gloss language's."""
    return [(L.iso3, "%s-%s_links.tsv.bz2" % (L.iso3, G.iso3)),
            (L.iso3, "%s_sentences.tsv.bz2" % L.iso3),
            (G.iso3, "%s_sentences.tsv.bz2" % G.iso3)]


def _download_dir():
    return os.path.join(corpus.CORPUS_DIR, "_dl")


def plan(code, gloss="en", keep=False, *, probe=True):
    """What building this corpus will cost, before anything is fetched:
    lib/download.py's plan() shape.  The same arguments as build(), and
    `probe=False` for an answer that sends nothing anywhere.

    THE DOWNLOAD IS THE THREE EXPORTS, less any already here (a whole one
    is reused, a cut one resumed); the peak is what is still to come plus
    the corpus built beside the old one; the exports are deleted after,
    unless `keep`.  A pair MEASURED does not ask Tatoeba; any other asks
    for the three sizes, and is given room for BOUND times them."""
    L = _known(code, "language")
    G = _known(gloss, "gloss language")
    dl, kept = MEASURED.get((L.code, G.code), (None, None))
    measured = dl is not None
    have, sizes = 0, []
    for iso, name in _files(L, G):
        dest = os.path.join(_download_dir(), name)
        if os.path.isfile(dest):
            sizes.append(os.path.getsize(dest))
            have += sizes[-1]
        else:
            have += download.leftover(dest)
            sizes.append(download.probe(_url(iso, name), {"User-Agent": UA})
                         if probe and not measured else None)
    if not measured:
        dl = None if None in sizes else sum(sizes)
    peak = None
    if dl is not None:
        built = kept if kept is not None else BOUND * dl
        peak = max(dl - have, 0) + built
        if keep and kept is not None:
            kept += dl
    return download.plan(dl, measured=measured, kept=kept, have=have,
                         peak=peak)


def discard(code, gloss="en"):
    """Throw away this pair's three exports, cut short or whole, left by a
    build that was stopped.  Returns the bytes freed; the corpus itself is
    untouched.  (The gloss language's export is shared by every pair glossed
    in it: another pair that wants it fetches it again.)"""
    L = _known(code, "language")
    G = _known(gloss, "gloss language")
    freed = 0
    for _iso, name in _files(L, G):
        dest = os.path.join(_download_dir(), name)
        with download.lock(dest):
            freed += download.leftover(dest)
            download.discard(dest)
            if os.path.isfile(dest):
                freed += os.path.getsize(dest)
                os.unlink(dest)
    return freed


# HOW A BUILD'S TIME DIVIDES, for the bar: the links, the language's
# sentences and the gloss language's are read, then the pairs and their index
# are written.  Reading goes at the pace of the exports' own bytes; writing at
# the pace of the pairs, which are about as many as the links export is big.
# Measured on Italian-English (2026-09-25): the three exports (38 MB) read in
# 5.1 s, 720 543 pairs written in 9.2 s, from a links export of 3.8 MB -- so
# writing weighs about 18 times its links export's bytes.  Persian-English is
# the other way about: 25 MB to read, 8 454 pairs to write.
WRITE_WEIGHT = 18


def _shares(f_links, f_src, f_dst):
    """Each step's share of the build's bar, from the three exports' sizes."""
    w = [os.path.getsize(f) for f in (f_links, f_src, f_dst)]
    w.append(WRITE_WEIGHT * w[0])
    whole = float(sum(w) or 1)
    return [x / whole for x in w]


def build(code, gloss="en", keep=False, say=print, progress=None,
          cancel=None):
    """Download and build corpus/<code>-<gloss>.db.  Returns the pair count.

    `progress(done, total, phase)` hears the three downloads as one bar
    ("download") and then the build ("build"); `cancel` stops either, as
    download.Cancelled: a cut download is kept to be resumed, a whole one
    kept to be reused, and a half-built corpus removed.
    """
    L = _known(code, "language")
    G = _known(gloss, "gloss language")
    if not L.iso3 or not G.iso3:
        raise SystemExit("getcorpus: %s or %s has no `iso3` in the registry"
                         % (L.code, G.code))
    if L.code == G.code:
        raise SystemExit("getcorpus: a language glossed in itself has nothing "
                         "to translate")
    # A LANGUAGE WITH NO WORD SEPARATOR NEEDS ITS DICTIONARY FIRST.  The index
    # is per word, and finding the words of 我喜欢喝茶 means cutting it, which
    # only the dictionary's own word list can do (lib/corpus.words_of ->
    # lookup._segment).  Without one every sentence indexes zero words and the
    # corpus is built, reported as built, and can never match anything --
    # which is what happened to Chinese the first time.  Better to refuse and
    # say what is missing.
    if not L.spaced and not lookup.available(L.code):
        raise SystemExit(
            "getcorpus: %s is written without spaces between its words, so a\n"
            "  corpus of it has to be cut into words before it can be indexed,\n"
            "  and the dictionary's own word list is what cuts it.  Get the\n"
            "  %s dictionary first (Settings, Reading help), then this."
            % (L.name, L.name))
    os.makedirs(corpus.CORPUS_DIR, exist_ok=True)
    db = corpus.path_for(L.code, G.code)
    tmp = _download_dir()
    os.makedirs(tmp, exist_ok=True)
    got = []
    files = _files(L, G)

    # ONE BAR FOR THE THREE DOWNLOADS, which needs their sizes before the
    # first starts: asked of Tatoeba (a HEAD each, no body) only when
    # somebody is watching a bar.  Where one does not say, each file
    # reports its own bar instead of one bar guessing.
    sizes = {}
    if progress is not None:
        for iso, name in files:
            dest = os.path.join(tmp, name)
            sizes[name] = (os.path.getsize(dest) if os.path.isfile(dest) else
                           download.probe(_url(iso, name), {"User-Agent": UA}))
    whole = (sum(sizes.values()) if sizes and None not in sizes.values()
             else None)
    before = [0]

    def grab(iso, name):
        dest = os.path.join(tmp, name)
        with download.lock(dest):         # another pair may be fetching it
            if os.path.isfile(dest):
                say("    already here: %s" % name)
            else:
                _fetch(_url(iso, name), dest, say,
                       progress=download.shifted(progress, before[0], whole),
                       cancel=cancel)
        before[0] += sizes.get(name) or 0
        got.append(dest)
        return dest

    say("  %s glossed in %s, from %s" % (L.name, G.name, SOURCE))
    f_links, f_src, f_dst = [grab(iso, name) for iso, name in files]

    meter = download.Meter(progress, cancel)
    step, at = [], 0.0
    for share in _shares(f_links, f_src, f_dst):
        step.append(meter.share(at, at + share))
        at += share
    say("  reading the links")
    links = _links(f_links, step[0])
    if not links:
        say("  Tatoeba has no %s-%s pairs at all." % (L.iso3, G.iso3))
    src_want = {a for a, _b in links}
    dst_want = {b for _a, b in links}
    say("  reading %s (%d wanted)" % (os.path.basename(f_src), len(src_want)))
    src = _sentences(f_src, src_want, step[1])
    say("  reading %s (%d wanted)" % (os.path.basename(f_dst), len(dst_want)))
    dst = _sentences(f_dst, dst_want, step[2])

    # BUILT BESIDE THE OLD ONE AND MOVED OVER IT, for the reason getdict.py
    # does it: a download that fails halfway must not cost somebody the
    # corpus they already had.
    part = db + ".part"
    say("  building %s" % os.path.relpath(db, ROOT))
    c = corpus.create(part)
    try:
        n = seen_pairs = 0
        df = {}
        t0 = time.time()
        done = set()
        every = float(len(links) or 1)
        for i, (a, b) in enumerate(links):
            if i % 1000 == 0:
                step[3](i / every)
            s, d = src.get(a), dst.get(b)
            if not s or not d:
                continue
            key = (s, d)
            if key in done:                 # the same pair reached twice
                continue
            done.add(key)
            cur = c.execute("INSERT INTO pair (src, dst) VALUES (?,?)", (s, d))
            pid = cur.lastrowid
            words = corpus.words_of(L.code, s)
            if words:
                c.executemany("INSERT INTO tok (word, pair_id) VALUES (?,?)",
                              [(w, pid) for w in words])
                for w in words:
                    df[w] = df.get(w, 0) + 1
            n += 1
            seen_pairs += 1
            if n % 20000 == 0:
                say("    %d pairs (%.0fs)" % (n, time.time() - t0))
        c.executemany("INSERT INTO df (word, n) VALUES (?,?)", sorted(df.items()))
        for k, v in (("source", SOURCE), ("licence", LICENCE),
                     ("lang", L.code), ("gloss", G.code),
                     ("pairs", str(seen_pairs)), ("words", str(len(df))),
                     ("built", time.strftime("%Y-%m-%d")),
                     ("url", _url(L.iso3, "%s-%s_links.tsv.bz2" % (L.iso3, G.iso3)))):
            c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)", (k, v))
        c.commit()
        c.close()
        os.replace(part, db)
        meter.end()
    except BaseException:
        try:
            c.close()
        except Exception:
            pass
        if os.path.isfile(part):
            os.unlink(part)
        raise

    if not keep:
        for p in got:
            try:
                os.unlink(p)
            except OSError:
                pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass
    say("  %s-%s: %s pairs, %s words, %.1f MB"
        % (L.code, G.code, "{:,}".format(seen_pairs).replace(",", " "),
           "{:,}".format(len(df)).replace(",", " "),
           os.path.getsize(db) / 1e6))
    return seen_pairs


def status(say=print):
    say("Corpora, in %s/" % os.path.relpath(corpus.CORPUS_DIR, ROOT))
    say("")
    have = dict.fromkeys(corpus.installed())
    for L in languages.LANGS.values():
        rows = [(a, b) for (a, b) in have if a == L.code]
        if rows:
            for a, b in rows:
                m = corpus.about(a, b)
                say("  %-3s -> %-3s  %8s pairs  %s  built %s"
                    % (a, b, m.get("pairs", "?"), m.get("source", ""),
                       m.get("built", "?")))
        else:
            say("  %-3s        --" % L.code)
    say("")
    say("  build one:  python3 lib/getcorpus.py <code> [gloss]")


def main():
    p = argparse.ArgumentParser(prog="getcorpus",
                                description=__doc__.splitlines()[0])
    p.add_argument("code", nargs="?", help="the language, or --all")
    p.add_argument("gloss", nargs="?", default="en",
                   help="the language its glosses are written in (default en)")
    p.add_argument("--all", action="store_true",
                   help="every language in the registry, glossed in `gloss`")
    p.add_argument("--keep", action="store_true",
                   help="keep the downloaded exports")
    a = p.parse_args()
    # the gloss is checked before anything is downloaded, and before --all
    # starts on eleven languages with a gloss that was never understood
    _known(a.gloss, "gloss language")
    if a.all:
        for L in languages.LANGS.values():
            if L.code == a.gloss:
                continue
            print("== %s" % L.name)
            try:
                build(L.code, a.gloss, keep=a.keep)
            except SystemExit as e:
                print("  %s" % e)
        return 0
    if not a.code:
        status()
        return 0
    _known(a.code, "language")
    build(a.code, a.gloss, keep=a.keep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
