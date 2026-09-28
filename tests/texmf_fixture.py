# SPDX-License-Identifier: GPL-3.0-or-later
"""A suite's own temporary texmf/, holding what the themes add to the base as
if Parseh had got it (lib/texpackages.py: a theme's packages beyond the base
are drawn only once Parseh has them).  Only Parseh's list is written: the
files themselves are the computer's TeX's, so a suite draws with real TeX and
downloads nothing.  A suite that is about getting them starts without it."""
import json
import os


def pretend_got(texpackages, latexthemes):
    names = sorted({n for p in latexthemes.ORDER if p not in latexthemes.BASE
                    for n in latexthemes.PACKAGES[p]["tl"] if texpackages.own(n)})
    os.makedirs(texpackages.TREE, exist_ok=True)
    doc = {"format": texpackages.MANIFEST_FORMAT,
           "packages": {n: {"at": "suite", "licence": "", "size": 0, "via": "suite"} for n in names}}
    with open(texpackages.manifest_path(), "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    return names
