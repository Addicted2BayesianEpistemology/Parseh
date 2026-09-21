#!/usr/bin/env python3
"""Fetch a translation model that runs in the reader's own browser.

    python3 lib/getmt.py                 what is installed
    python3 lib/getmt.py fa en           Persian to English
    python3 lib/getmt.py --engine        just the engine, without a model

WHAT THIS IS, AND WHAT IT IS NOT.  It is a TRANSLATION model: one job, no
prompt, no endpoint, no key, no conversation, and the same answer every time
for the same sentence.  It is not a chat model and there is no server to talk
to -- the engine is WebAssembly and it runs inside the page, so a chunk being
translated never leaves the machine, and the toolbox gains no Python
dependency at all.

THE ENGINE is bergamot-translator, the same one Firefox's own translations
feature uses, under the MPL 2.0.  THE MODELS are Mozilla's, distributed
through the service Firefox itself fetches them from, and they are tiny:
around 20 MB for a language pair, against gigabytes for a general model.

NOTHING IS COMMITTED.  Engine and models are downloaded into `mt/`, which is
gitignored for the reason `dict/` is: somebody else's work, under somebody
else's licence, and megabytes of it.  A pair with no model installed is read
exactly as it is read today -- the button simply is not offered.

ONLY TO AND FROM ENGLISH.  Mozilla trains its pairs against English and not
against each other, so a book in Persian glossed in English has a model and
the same book glossed in Italian has none -- there is no fa-it model to
fetch, and `trainable()` below is what the page asks before it offers the
choice.

AND NOT ALWAYS UNDER THE CODE THE REGISTRY USES.  The service names Chinese
by its script -- `zh-Hans` for the simplified characters Parseh's `zh`
teaches, `zh-Hant` for the traditional ones -- so the code is translated on
the way out.  That is a fact about the service's spelling and not about the
language, which is why it lives here and not in the registry.
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import languages                                              # noqa: E402

MT_DIR = os.path.join(ROOT, "mt")
ENGINE_DIR = os.path.join(MT_DIR, "engine")

# The engine, pinned.  An unpinned dependency that reaches over the network is
# a dependency that changes under a reader without anybody deciding to change
# it, so the version is written here and moved by hand.
ENGINE_VERSION = "0.4.9"
ENGINE_BASE = ("https://cdn.jsdelivr.net/npm/@browsermt/bergamot-translator@%s/worker"
               % ENGINE_VERSION)
ENGINE_FILES = ("translator-worker.js", "bergamot-translator-worker.js",
                "bergamot-translator-worker.wasm")
ENGINE_SOURCE = "bergamot-translator %s (MPL 2.0)" % ENGINE_VERSION

# Where Firefox itself gets its models.  The records carry the pair, the file
# type, a version and an attachment; the attachment's `location` hangs off the
# CDN below.
RECORDS = ("https://firefox.settings.services.mozilla.com/v1/buckets/main"
           "/collections/translations-models/records")
ATTACH = "https://firefox-settings-attachments.cdn.mozilla.net/"
MODEL_SOURCE = "Mozilla Firefox Translations models"
MODEL_LICENCE = "CC BY-SA 4.0"

# What a pair needs.  `lex` is the shortlist, `vocab` the sentencepiece
# vocabulary; a few pairs split the vocabulary in two and name the halves
# separately, which is why both spellings are looked for.
WANT = ("model", "lex", "vocab", "srcvocab", "trgvocab")
UA = "Parseh/1.0 (+https://github.com/Addicted2BayesianEpistemology/Parseh)"


def _get(url, dest, say=print):
    say("    %s" % os.path.basename(dest))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=180) as r, io.open(dest, "wb") as f:
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
        raise SystemExit("getmt: could not download %s (%s)" % (url, e))
    except OSError as e:
        raise SystemExit("getmt: could not download (%s)" % e)


def engine_ready():
    return all(os.path.isfile(os.path.join(ENGINE_DIR, f)) for f in ENGINE_FILES)


def get_engine(say=print, force=False):
    """The WebAssembly engine, once, shared by every pair."""
    if engine_ready() and not force:
        return False
    os.makedirs(ENGINE_DIR, exist_ok=True)
    say("  the engine, %s" % ENGINE_SOURCE)
    for f in ENGINE_FILES:
        _get("%s/%s" % (ENGINE_BASE, f), os.path.join(ENGINE_DIR, f), say)
    io.open(os.path.join(ENGINE_DIR, "meta.json"), "w", encoding="utf-8").write(
        json.dumps({"source": ENGINE_SOURCE, "version": ENGINE_VERSION,
                    "built": time.strftime("%Y-%m-%d")}, indent=1))
    return True


# What the service calls a language, where that is not what the registry
# calls it.  Simplified characters are what `zh` teaches (lib/lang/zh.chunk.json
# and docs/lang/zh.md say so), so `zh-Hans` is the pair to fetch.
_SERVICE = {"zh": "zh-Hans"}


def service_code(code):
    """The name the model service knows this language by."""
    return _SERVICE.get(code, code)


def trainable(a, b):
    """Could a model for this pair exist at all?

    Mozilla trains every pair against English rather than against each other,
    so `fa-en` and `en-it` exist and `fa-it` does not, and no amount of
    asking will produce one.  The /lookup/ page asks this before it offers a
    gloss, because a choice that can only fail is worse than no choice.
    """
    if a == b:
        return False
    return "en" in (a, b)


def path_for(a, b):
    return os.path.join(MT_DIR, "%s-%s" % (a, b))


def available(a, b):
    """A pair is usable when the engine and its three files are all here."""
    d = path_for(a, b)
    if not engine_ready() or not os.path.isdir(d):
        return False
    have = set(os.listdir(d))
    return "meta.json" in have and any(n.startswith("model.") for n in have)


def about(a, b):
    try:
        return json.load(io.open(os.path.join(path_for(a, b), "meta.json"),
                                 encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _records(say=print):
    req = urllib.request.Request(RECORDS, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8")).get("data") or []
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise SystemExit("getmt: could not read the model list (%s)" % e)


def _stable(version):
    """A version with no letters in it is a release; `1.0a1` is not.

    Sorting on the string alone would prefer `1.0a1` over `1.0`, which is the
    alpha of the very thing it beats.
    """
    return not any(ch.isalpha() for ch in (version or ""))


def _pick(recs, a, b):
    """The newest stable record of each file type this pair needs."""
    best = {}
    for r in recs:
        if r.get("fromLang") != a or r.get("toLang") != b:
            continue
        kind = r.get("fileType")
        if kind not in WANT:
            continue
        att = r.get("attachment") or {}
        if not att.get("location"):
            continue
        key = (_stable(r.get("version")), r.get("version") or "")
        if kind not in best or key > best[kind][0]:
            best[kind] = (key, r)
    return {k: v[1] for k, v in best.items()}


def pairs(say=print):
    """Every pair the service has, as (from, to)."""
    got = set()
    for r in _records(say):
        a, b = r.get("fromLang"), r.get("toLang")
        if a and b:
            got.add((a, b))
    return sorted(got)


def build(a, b, say=print):
    """Download the engine if it is missing, then this pair's model."""
    A = languages.get_or_default(a)
    B = languages.get_or_default(b)
    if A.code == B.code:
        raise SystemExit("getmt: a language translated into itself is a copy")
    get_engine(say)
    say("  %s to %s, from %s" % (A.name, B.name, MODEL_SOURCE))
    recs = _records(say)
    want = _pick(recs, service_code(A.code), service_code(B.code))
    if "model" not in want:
        raise SystemExit(
            "getmt: there is no %s-to-%s model.\n"
            "  Mozilla trains its pairs against English rather than against\n"
            "  each other, so %s-en and en-%s exist where %s-%s does not.\n"
            "  `python3 lib/getmt.py --pairs` lists what there is."
            % (A.code, B.code, A.code, B.code, A.code, B.code))
    d = path_for(A.code, B.code)
    part = d + ".part"
    if os.path.isdir(part):
        for n in os.listdir(part):
            os.unlink(os.path.join(part, n))
    os.makedirs(part, exist_ok=True)
    try:
        names = {}
        for kind, r in sorted(want.items()):
            att = r["attachment"]
            name = att.get("filename") or "%s.bin" % kind
            _get(ATTACH + att["location"], os.path.join(part, name), say)
            names[kind] = name
        meta = {"from": A.code, "to": B.code, "files": names,
                "version": (want["model"].get("version") or ""),
                "source": MODEL_SOURCE, "licence": MODEL_LICENCE,
                "engine": ENGINE_SOURCE,
                "built": time.strftime("%Y-%m-%d")}
        io.open(os.path.join(part, "meta.json"), "w", encoding="utf-8").write(
            json.dumps(meta, indent=1))
        # beside the old one and moved over it, for the reason getdict.py does
        if os.path.isdir(d):
            for n in os.listdir(d):
                os.unlink(os.path.join(d, n))
            os.rmdir(d)
        os.replace(part, d)
    except BaseException:
        if os.path.isdir(part):
            for n in os.listdir(part):
                try:
                    os.unlink(os.path.join(part, n))
                except OSError:
                    pass
            try:
                os.rmdir(part)
            except OSError:
                pass
        raise
    size = sum(os.path.getsize(os.path.join(d, n)) for n in os.listdir(d))
    say("  %s-%s: %.1f MB" % (A.code, B.code, size / 1e6))
    return size


def installed():
    """Every pair on this machine, as (from, to)."""
    out = []
    try:
        names = sorted(os.listdir(MT_DIR))
    except OSError:
        return out
    for n in names:
        if n == "engine" or "-" not in n:
            continue
        a, _, b = n.partition("-")
        if a in languages.LANGS and b in languages.LANGS and available(a, b):
            out.append((a, b))
    return out


def status(say=print):
    say("Translation models, in %s/" % os.path.relpath(MT_DIR, ROOT))
    say("")
    say("  engine: %s" % ("installed" if engine_ready() else "not here yet"))
    have = installed()
    if not have:
        say("  no pair installed")
    for a, b in have:
        m = about(a, b)
        size = sum(os.path.getsize(os.path.join(path_for(a, b), n))
                   for n in os.listdir(path_for(a, b)))
        say("  %s -> %s   %.1f MB  %s  built %s"
            % (a, b, size / 1e6, m.get("source", ""), m.get("built", "?")))
    say("")
    say("  build one:  python3 lib/getmt.py <from> <to>")


def main():
    p = argparse.ArgumentParser(prog="getmt", description=__doc__.splitlines()[0])
    p.add_argument("src", nargs="?", help="the language to translate FROM")
    p.add_argument("dst", nargs="?", default="en", help="and INTO (default en)")
    p.add_argument("--engine", action="store_true", help="just the engine")
    p.add_argument("--pairs", action="store_true", help="every pair on offer")
    a = p.parse_args()
    if a.engine:
        if get_engine():
            print("  the engine is here")
        else:
            print("  the engine was already here")
        return 0
    if a.pairs:
        got = pairs()
        print("%d pairs on offer:" % len(got))
        mine = {L.code for L in languages.LANGS.values()}
        for x, y in got:
            if x in mine or y in mine:
                print("  %s -> %s" % (x, y))
        return 0
    if not a.src:
        status()
        return 0
    if a.src not in languages.LANGS or a.dst not in languages.LANGS:
        raise SystemExit("getmt: %r or %r is not a language in the registry"
                         % (a.src, a.dst))
    build(a.src, a.dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
