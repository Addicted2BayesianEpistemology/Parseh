#!/usr/bin/env python3
"""Fetch the synonym table the meaning-based aligner uses: `mt/synonyms.en.json`.

    python3 lib/getsyn.py              get it (or say it is already there)
    python3 lib/getsyn.py --rebuild    fetch WordNet again and build fresh
    python3 lib/getsyn.py --remove     take it off disk

WHAT IT IS FOR.  `lib/mt.js`'s aligner marks the words of a machine's reading
that are a chunk's, by what the dictionary says the chunk's words mean in
English.  Where the model chose a different English word for the same idea --
`begin` where the dictionary says `start`, `help` where it says `aid` -- an
exact-word match finds nothing.  This file is that other word's list: for a
stem the aligner already computes, the OTHER stems that are the same word in
one of its senses.  A synonym match is real evidence and is used, but it is
weaker evidence than the word itself, so `lib/mt.js` scores it below an exact
or an inflected match (`SYN_Q` there) -- never above it.

WHERE IT COMES FROM.  Princeton WordNet 3.1, whose synsets already ARE what
this needs: a set of words a lexicographer judged interchangeable in one
sense.  It is not a translation resource and it is not paraphrase data mined
from a model -- it is the same kind of dictionary judgement `dict/<code>.db`
already carries, in English, without senses or a language attached.  Public
domain-adjacent: WordNet's own licence (in every one of its data files)
allows redistribution and modification without royalty, on condition its
copyright notice travels with it, which the built file's `licence` key does.

ONE SENSE, NOT EVERY SENSE.  A synset is worth using only where BOTH of its
words treat it as their OWN FIRST-LISTED sense (WordNet's own index files
order a word's senses, most frequent first) -- not where either word merely
appears in it. Skipping that test was measured to pollute `mountain` (a land
mass) with `heap`, `batch`, `lot` and a dozen other words for the *quantity*
idiom "a mountain of paperwork", because `heap`'s own first sense IS that
idiom -- even though it is nowhere near `mountain`'s.  Requiring the synset to
be the first sense of BOTH words drops that whole cluster and keeps
`begin`<->`start`, `help`<->`aid`, `small`<->`little`: 101,880 candidate pairs
falls to 64,206 once each side has to agree, and the biggest group shrinks
from 74 words to 26.

NOTHING IS COMMITTED.  It is built into `mt/`, which is gitignored for the
reason `dict/` is: somebody else's work, downloaded once.  A machine with
none of it gets marks by the dictionary's own words alone, exactly as before
this file existed -- `lib/mt.js` asks for it once and is not offered a switch
that cannot work if the fetch 404s.
"""
import argparse
import collections
import gzip
import io
import json
import os
import re
import sys
import tarfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

MT_DIR = os.path.join(ROOT, "mt")
OUT = os.path.join(MT_DIR, "synonyms.en.json")

WORDNET_URL = "https://wordnetcode.princeton.edu/wn3.1.dict.tar.gz"
SOURCE = "WordNet 3.1 (Princeton University)"
LICENCE = "WordNet 3.0 licence (free redistribution and modification)"
UA = "Parseh/1.0 (+https://github.com/Addicted2BayesianEpistemology/Parseh)"

# Which of WordNet's four part-of-speech files to read, and the index file
# that gives each of their words its senses in frequency order.
POS = {"noun": ("dict/data.noun", "dict/index.noun"),
       "verb": ("dict/data.verb", "dict/index.verb"),
       "adj": ("dict/data.adj", "dict/index.adj"),
       "adv": ("dict/data.adv", "dict/index.adv")}

_LEMMA_LINE = re.compile(r"^\d{8} ")
_WORD = re.compile(r"^[a-zA-Z]+$")

# The irregular English forms lib/mt.js's `stem` corrects before it strips a
# suffix -- copied from there, because a table built under a different set
# of stems is a table whose keys the aligner can never ask for.  Keep the two
# lists identical; `tests/smoke.py`'s `test_getsyn` checks they agree.
_IRREGULAR_PAIRS = (
    "arose:arise arisen:arise ate:eat eaten:eat awoke:awake bade:bid began:begin "
    "begun:begin bent:bend bit:bite bitten:bite blew:blow blown:blow bore:bear "
    "born:bear borne:bear bought:buy bound:bind bred:breed brought:bring "
    "broke:break broken:break built:build burnt:burn came:come caught:catch "
    "chose:choose chosen:choose clung:cling crept:creep dealt:deal did:do "
    "done:do drank:drink drunk:drink drew:draw drawn:draw drove:drive "
    "driven:drive dug:dig dwelt:dwell fed:feed fell:fall fallen:fall felt:feel "
    "fled:flee flew:fly flown:fly fought:fight found:find forbade:forbid "
    "forgave:forgive forgot:forget forgotten:forget froze:freeze frozen:freeze "
    "gave:give given:give went:go gone:go got:get gotten:get grew:grow "
    "grown:grow ground:grind hung:hang heard:hear held:hold hid:hide "
    "hidden:hide kept:keep knelt:kneel knew:know known:know laid:lay led:lead "
    "leapt:leap learnt:learn left:leave lent:lend lay:lie lain:lie lit:light "
    "lost:lose made:make meant:mean met:meet mistook:mistake paid:pay "
    "rode:ride ridden:ride rang:ring rung:ring rose:rise risen:rise ran:run "
    "said:say saw:see seen:see sought:seek sold:sell sent:send shook:shake "
    "shaken:shake shone:shine shot:shoot showed:show shown:show shrank:shrink "
    "sang:sing sung:sing sank:sink sunk:sink sat:sit slept:sleep slid:slide "
    "slung:sling spoke:speak spoken:speak spent:spend spun:spin spat:spit "
    "sprang:spring stood:stand stole:steal stolen:steal stuck:stick "
    "stung:sting strode:stride struck:strike strove:strive swore:swear "
    "sworn:swear swept:sweep swam:swim swum:swim swung:swing took:take "
    "taken:take taught:teach tore:tear torn:tear told:tell thought:think "
    "threw:throw thrown:throw trod:tread understood:understand woke:wake "
    "woken:wake wore:wear worn:wear wove:weave woven:weave wept:weep won:win "
    "wound:wind wrote:write written:write men:man women:woman children:child "
    "feet:foot teeth:tooth mice:mouse geese:goose grey:gray").split(" ")
IRREGULAR = dict(p.split(":") for p in _IRREGULAR_PAIRS)


def stem(word):
    """The same word lib/mt.js's `stem(w, true)` would compute -- the key
    both the aligner's live matching and this table use.  Ported by hand,
    rule for rule; the two are checked against each other in tests/smoke.py."""
    w = word.lower()
    w = re.sub(r"['’]s$", "", w)
    w = w.replace("'", "").replace("’", "")
    if len(w) < 3:
        return w
    if w in IRREGULAR:
        w = IRREGULAR[w]
    w = re.sub(r"our(?=(s|ed|ing|ful|less)?$)", "or", w)
    w = re.sub(r"([^aeiou])tre(?=s?$)", r"\1ter", w)
    w = re.sub(r"is(?=(e|es|ed|ing|ation|ations)$)", "iz", w)
    s = w
    if re.search(r"(ness|less)$", s) and len(s) > 6:
        s = s[:-4]
    elif re.search(r"ful$", s) and len(s) > 5:
        s = s[:-3]
    elif re.search(r"ies$", s) and len(s) > 4:
        s = s[:-3] + "y"
    elif re.search(r"ied$", s) and len(s) > 4:
        s = s[:-3] + "y"
    elif re.search(r"ing$", s) and len(s) > 5:
        s = s[:-3]
    elif re.search(r"ed$", s) and len(s) > 4:
        s = s[:-2]
    elif re.search(r"(ss|sh|ch|x|z)es$", s) and len(s) > 4:
        s = s[:-2]
    elif re.search(r"[^s]s$", s) and len(s) > 3:
        s = s[:-1]
    if s != w and re.search(r"([^aeiouls])\1$", s):
        s = s[:-1]
    if re.search(r"y$", s) and len(s) > 3:
        s = s[:-1] + "i"
    if re.search(r"e$", s) and len(s) > 3:
        s = s[:-1]
    return s


def _get(url, say=print):
    say("  %s" % url.rsplit("/", 1)[-1])
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            buf, got, t0 = io.BytesIO(), 0, time.time()
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                buf.write(chunk)
                got += len(chunk)
                if got % (1 << 22) < (1 << 16) and got > (1 << 22):
                    say("    %.0f MB (%.0fs)" % (got / 1e6, time.time() - t0))
            return buf.getvalue()
    except urllib.error.HTTPError as e:
        raise SystemExit("getsyn: could not download %s (%s)" % (url, e))
    except OSError as e:
        raise SystemExit("getsyn: could not download (%s)" % e)


def _index_primary(text):
    """lemma -> the offset of its FIRST-listed synset, one WordNet index file.

    An index line is `lemma pos synset_cnt p_cnt [ptr...] sense_cnt
    tagsense_cnt offset [offset...]`; WordNet orders a lemma's offsets most
    frequent first, so the first one is the sense a reader meets the word in
    most often.  Skips a multiword lemma (`fall_back`): the aligner never
    builds one to look up."""
    out = {}
    for line in text.splitlines():
        if line.startswith((" ", "\t")) or not line.strip():
            continue
        toks = line.split()
        if len(toks) < 4:
            continue
        lemma = toks[0]
        if "_" in lemma or not _WORD.match(lemma):
            continue
        try:
            syn_cnt, p_cnt = int(toks[2]), int(toks[3])
        except ValueError:
            continue
        i = 4 + p_cnt
        if i + 1 >= len(toks):
            continue
        i += 2                                # sense_cnt, tagsense_cnt
        offsets = toks[i:i + syn_cnt]
        if offsets:
            out[lemma] = offsets[0]
    return out


def _synsets(text):
    """offset -> the synset's single-word lemmas, one WordNet data file.

    A data line is `offset lex_filenum pos w_cnt (word lex_id){w_cnt} p_cnt
    ... | gloss`; only the word list is read.  A multiword lemma
    (`about_face`) and one with an apostrophe or digit are dropped, because
    the aligner's tokens are never those either."""
    out = {}
    for line in text.splitlines():
        if not _LEMMA_LINE.match(line):
            continue
        toks = line.split(" | ", 1)[0].split(" ")
        offset = toks[0]
        w_cnt = int(toks[3], 16)
        words, idx = [], 4
        for _ in range(w_cnt):
            w = toks[idx]
            idx += 2
            if _WORD.match(w):
                words.append(w.lower())
        out[offset] = sorted(set(words))
    return out


def build_from(archive_bytes, say=print):
    """The synonym table, from the WordNet tarball's bytes.  {stem: [stem,
    ...]}, sorted, every list a set of stems that share a first sense with
    the key -- see the module docstring for why both sides must agree."""
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tf:
        members = {m.name: m for m in tf.getmembers()}
        adjacency = collections.defaultdict(set)
        pairs = 0
        for pos, (data_name, index_name) in POS.items():
            data_m, index_m = members.get(data_name), members.get(index_name)
            if data_m is None or index_m is None:
                raise SystemExit("getsyn: %s is missing %s or %s -- the "
                                 "archive's layout changed" % (WORDNET_URL, data_name, index_name))
            data_text = tf.extractfile(data_m).read().decode("latin-1")
            index_text = tf.extractfile(index_m).read().decode("latin-1")
            primary = _index_primary(index_text)
            synsets = _synsets(data_text)
            say("  %-4s %d synsets, %d indexed words"
                % (pos, len(synsets), len(primary)))
            for offset, words in synsets.items():
                if len(words) < 2:
                    continue
                for a in words:
                    if primary.get(a) != offset:
                        continue
                    sa = stem(a)
                    for b in words:
                        if b == a or primary.get(b) != offset:
                            continue
                        sb = stem(b)
                        if sa != sb:
                            adjacency[sa].add(sb)
                            pairs += 1
    say("  %d mutual first-sense pairs, %d stems" % (pairs, len(adjacency)))
    return {k: sorted(v) for k, v in sorted(adjacency.items())}


def installed():
    return os.path.isfile(OUT)


def get(say=print, force=False):
    """Fetch WordNet, build the table, write `mt/synonyms.en.json`.  Returns
    False without doing anything if the file is already there and `force`
    is not set -- the same rule getdict.py's `rebuild` button overrides."""
    if installed() and not force:
        return False
    os.makedirs(MT_DIR, exist_ok=True)
    say("  %s" % SOURCE)
    archive = _get(WORDNET_URL, say)
    table = build_from(archive, say)
    part = OUT + ".part"
    io.open(part, "w", encoding="utf-8").write(
        json.dumps({"source": SOURCE, "licence": LICENCE,
                    "built": time.strftime("%Y-%m-%d"), "synonyms": table},
                   separators=(",", ":"), ensure_ascii=False))
    os.replace(part, OUT)                     # atomic: a reader mid-fetch never sees a half file
    say("  %s, %.1f MB" % (os.path.relpath(OUT, ROOT), os.path.getsize(OUT) / 1e6))
    return True


def remove(say=print):
    if not installed():
        return False
    os.unlink(OUT)
    say("  removed %s" % os.path.relpath(OUT, ROOT))
    return True


def status(say=print):
    if not installed():
        say("no synonym table -- python3 lib/getsyn.py to fetch it")
        return
    meta = json.load(io.open(OUT, encoding="utf-8"))
    say("%s -- %s entries, %.1f MB, built %s, %s"
        % (os.path.relpath(OUT, ROOT), "{:,}".format(len(meta.get("synonyms") or {})),
           os.path.getsize(OUT) / 1e6, meta.get("built", "?"), meta.get("source", "?")))


def main():
    p = argparse.ArgumentParser(prog="getsyn", description=__doc__.splitlines()[0])
    p.add_argument("--rebuild", action="store_true",
                   help="fetch WordNet again even if the table is already there")
    p.add_argument("--remove", action="store_true", help="take it off disk")
    a = p.parse_args()
    if a.remove:
        if not remove():
            print("nothing to remove")
        return 0
    if a.rebuild or not installed():
        get(force=a.rebuild)
    status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
