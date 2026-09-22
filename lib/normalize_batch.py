#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Apply the edition's settled spellings to a fresh annotation batch.

    python3 normalize_batch.py <workflow-output.json> <out.json> [--book <dir-or-slug>]

Every rule here exists because a batch got it wrong at least once.  Run it
before assemble.py; it is idempotent, so running it twice is harmless.

The rules are the Persian edition's (NOTES section 4: /ey/ as kasra+ya,
chashm, budan's stem, the malformed \\bw), so they run only when the book is
Persian.  For any other language the batch is copied unchanged -- the tool
stays in the pipeline so the recipe is the same for every book, and says
what it did.  Which book: --book, else $FRANK_BOOK, else the book the
current directory is in (books.find_book).
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from books import find_book                                     # noqa: E402

# /ey/ is kasra + ya in this edition.  The two cases are different:
#   - fa has fatha but tr says "ey"  -> the sweep in assemble.py catches it
#   - fa AND tr agree on /ay/        -> nothing catches it, so list the words
EY_FA = {"پَیدا": "پِیدا", "خَیلی": "خِیلی", "بَین": "بِین", "مَیل": "مِیل",
         "کَیف": "کِیف", "عَین": "عِین", "هَیکَل": "هِیکَل", "غَیر": "غِیر",
         "پَی": "پِی", "شَیء": "شِیء", "طَی": "طِی", "حَیف": "حِیف"}
EY_TR = {"paydā": "peydā", "xayli": "xeyli", "bayn": "beyn", "mayl": "meyl",
         "kayf": "keyf", "ayn": "eyn", "haykal": "heykal", "qayr": "qeyr",
         "šay'": "šey'", "tayy": "teyy", "hayf": "heyf"}

# \bw{x}{y} meaning...  -- LaTeX would swallow the next CHARACTER as the third
# argument and print 'j'olt.  Wrap the phrase.
BW = re.compile(r"(\\bw\{[^{}]*\}\{[^{}]*\})[ \t]+([^{\;][^;\\]*?)(?=\s*(?:;|\\|$))")

# بودن's present stem is باش; هست is the suppletive existential
VB_BUDAN = re.compile(r"(\\vb\{بودن\}\{[^}]*\}\{)هست(\}\{)hast(\})")


def normalize(doc):
    n = {"ey": 0, "eye": 0, "budan": 0, "bw": 0}
    for para in doc["paragraphs"]:
        for sent in para["ann"]["sentences"]:
            for c in sent["chunks"]:
                fa = c["fa"]
                for a, b in EY_FA.items():
                    if a in fa:
                        fa = fa.replace(a, b)
                        n["ey"] += 1
                if "ey" in c.get("tr", "") and "َی" in fa:
                    fa = fa.replace("َی", "ِی")
                    n["ey"] += 1
                if "چَشم" in fa:                       # Tehrani /tʃeʃm/
                    fa = fa.replace("چَشم", "چِشم")
                    n["eye"] += 1
                c["fa"] = fa
                for f in ("tr", "voc"):
                    v = c.get(f, "")
                    if not v:
                        continue
                    for a, b in EY_TR.items():
                        if re.search(r"\b" + re.escape(a), v):
                            v = re.sub(r"\b" + re.escape(a), b, v)
                            n["ey"] += 1
                    if "čašm" in v:
                        v = v.replace("čašm", "češm")
                        n["eye"] += 1
                    c[f] = v
                voc = c.get("voc", "")
                v2 = VB_BUDAN.sub(r"\1باش\2bāš\3", voc)
                n["budan"] += v2 != voc
                v3 = BW.sub(lambda m: m.group(1) + "{" + m.group(2).strip() + "}", v2)
                n["bw"] += v3 != v2
                c["voc"] = v3
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="the batch as the workflow wrote it")
    ap.add_argument("dst", help="where the normalised batch goes")
    ap.add_argument("--book", default=None, help="book directory, slug or <folder>/<slug>")
    a = ap.parse_args()
    lang = find_book(a.book or os.environ.get("FRANK_BOOK") or None).lang
    blob = json.load(open(a.src, encoding="utf-8"))
    doc = blob.get("result", blob)
    if lang.code != "fa":
        json.dump(doc, open(a.dst, "w", encoding="utf-8"), ensure_ascii=False)
        print("%d paragraphs; %s has no settled spellings to apply -- copied unchanged"
              % (len(doc["paragraphs"]), lang.name))
        sys.exit(0)
    n = normalize(doc)
    json.dump(doc, open(a.dst, "w", encoding="utf-8"), ensure_ascii=False)
    print("%d paragraphs; fixed %d /ey/, %d چشم, %d بودن stems, %d malformed \\bw"
          % (len(doc["paragraphs"]), n["ey"], n["eye"], n["budan"], n["bw"]))
