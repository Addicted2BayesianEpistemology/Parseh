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
import urllib.request

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import corpus                                                 # noqa: E402
import languages                                              # noqa: E402
import lookup                                                 # noqa: E402

SOURCE = "Tatoeba (tatoeba.org)"
LICENCE = "CC BY 2.0 FR"
BASE = "https://downloads.tatoeba.org/exports/per_language"
UA = "Parseh/1.0 (+https://github.com/Addicted2BayesianEpistemology/Parseh)"

# A sentence longer than this is not an illustration of a chunk, it is a
# paragraph; and the index it would add is mostly common words.
MAX_LEN = 300


def _url(iso, name):
    return "%s/%s/%s" % (BASE, iso, name)


def _fetch(url, dest, say=print):
    """Download to `dest`, reporting as it goes.  The files are small
    (kilobytes to 25 MB), so this is one request and no resume."""
    say("    %s" % url.rsplit("/", 1)[-1])
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=120) as r, \
                io.open(dest, "wb") as f:
            got, t0 = 0, time.time()
            while True:
                buf = r.read(1 << 16)
                if not buf:
                    break
                f.write(buf)
                got += len(buf)
                if got % (1 << 22) < (1 << 16) and got > (1 << 22):
                    say("      %.0f MB (%.0fs)" % (got / 1e6, time.time() - t0))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise SystemExit(
                "getcorpus: Tatoeba has no %s.\n"
                "  It keys its exports by ISO 639-3, which the registry holds "
                "as `iso3`." % url.rsplit("/", 1)[-1])
        raise SystemExit("getcorpus: could not download (%s)" % e)
    except OSError as e:
        raise SystemExit("getcorpus: could not download (%s)" % e)


def _sentences(path, want=None):
    """{id: text} out of a Tatoeba sentences export, keeping only `want`.

    The English export is a million and a half sentences and the links name
    a few thousand of them; reading the whole file is unavoidable but
    keeping the whole file is not.
    """
    out = {}
    with bz2.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
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


def _links(path):
    """[(src id, dst id)] out of a Tatoeba links export."""
    out = []
    with bz2.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
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


def build(code, gloss="en", keep=False, say=print):
    """Download and build corpus/<code>-<gloss>.db.  Returns the pair count."""
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
            "  dictionary first:\n"
            "      python3 lib/getdict.py %s\n"
            "  or press `get it` beside %s on /lookup/."
            % (L.name, L.code, L.name))
    os.makedirs(corpus.CORPUS_DIR, exist_ok=True)
    db = corpus.path_for(L.code, G.code)
    tmp = os.path.join(corpus.CORPUS_DIR, "_dl")
    os.makedirs(tmp, exist_ok=True)
    got = []

    def grab(iso, name):
        dest = os.path.join(tmp, name)
        if os.path.isfile(dest):
            say("    already here: %s" % name)
        else:
            _fetch(_url(iso, name), dest, say)
        got.append(dest)
        return dest

    say("  %s glossed in %s, from %s" % (L.name, G.name, SOURCE))
    f_links = grab(L.iso3, "%s-%s_links.tsv.bz2" % (L.iso3, G.iso3))
    f_src = grab(L.iso3, "%s_sentences.tsv.bz2" % L.iso3)
    f_dst = grab(G.iso3, "%s_sentences.tsv.bz2" % G.iso3)

    say("  reading the links")
    links = _links(f_links)
    if not links:
        say("  Tatoeba has no %s-%s pairs at all." % (L.iso3, G.iso3))
    src_want = {a for a, _b in links}
    dst_want = {b for _a, b in links}
    say("  reading %s (%d wanted)" % (os.path.basename(f_src), len(src_want)))
    src = _sentences(f_src, src_want)
    say("  reading %s (%d wanted)" % (os.path.basename(f_dst), len(dst_want)))
    dst = _sentences(f_dst, dst_want)

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
        for a, b in links:
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
