#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The prompt lab: a prompt of Parseh's as a chatbot receives it, and what it is made of.

    python3 lib/promptlab.py <surface> <language> [--mode fill|perfield|regloss]
                             [--gloss <code>] [--sizes]

A DEVELOPER'S TOOL, not a page: nothing a person does needs it.  It builds the
prompt of one surface in one language the way that surface's own page would,
on the fixtures the tests use (a stretch of a video or a book, the transcript
of a video, a page of the studio), prints it, and prints under it a table of
the sizes of its parts -- the version line, the instructions, each section of
the language's conventions in them, the answer contract, the data -- in
characters and in tokens as a chatbot counts them.  --sizes prints the table
alone.  The sizes are what a lane that changes a prompt reads before and after.

    build(surface, language, mode, gloss)   the promptkit.Assembled of that prompt
    sizes(assembled, surface, language)     the table's rows, [(label, chars)]

tests/test_prompts.py drives build() over every surface and every language.
`ask` is assembled in the browser (lib/llm.js) and has nothing to print here.
"""
import argparse
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "youtube", "lib"), os.path.join(ROOT, "markdown", "app"),
           os.path.join(ROOT, "markdown")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import glossregion                                              # noqa: E402
import languages                                                # noqa: E402
import promptkit                                                # noqa: E402

FIXTURES = os.path.join(ROOT, "tests", "fixtures")
# the language whose fixtures stand in for one that has none (a language
# somebody added): Latin script, no reading, so any code fits its text
STAND_IN = "it"
PAGE = "---\ntitle: T\ntarget: %s\n---\n\nLesson"


class LabError(ValueError):
    """What the lab cannot build, and why."""


def _fixture(kind, L):
    """The fixture book or video of a language, and where it lives:
    (path, folder to remove after).  A language with none gets the stand-in's,
    filed under its own folder and saying its own code."""
    top = os.path.join(FIXTURES, kind, L.folder)
    if os.path.isdir(top):
        return os.path.join(top, sorted(os.listdir(top))[0]), None
    src = os.path.join(FIXTURES, kind, languages.get(STAND_IN).folder)
    src = os.path.join(src, sorted(os.listdir(src))[0])
    tmp = tempfile.mkdtemp(prefix="promptlab-")
    dst = os.path.join(tmp, kind, L.folder, os.path.basename(src))
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("reader", "*.pdf", "*.aux", "*.log", "*.toc"))
    for name in ("book.json", "video.json", "annotations.json"):
        p = os.path.join(dst, name)
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                text = f.read()
            with open(p, "w", encoding="utf-8") as f:
                f.write(text.replace('"language": "%s"' % STAND_IN, '"language": "%s"' % L.code))
    return dst, tmp


def _captions(L):
    """The captions of a language's fixture video, as the add page parses them."""
    import ytpages
    path, tmp = _fixture("videos", L)
    try:
        with open(os.path.join(path, "transcript.txt"), encoding="utf-8") as f:
            return ytpages.parse_transcript_text(ytpages.as_transcript(f.read()), L)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def build(surface, lang, mode=None, gloss=None):
    """The prompt of a surface in a language, built the way its page builds it.
    `mode` is a region's: fill (the default), perfield or regloss.
    -> promptkit.Assembled"""
    L = languages.get_or_default(lang) if isinstance(lang, str) else lang
    G = languages.gloss_or_default(gloss)
    if surface not in promptkit.SURFACES:
        raise LabError("%r is not a surface (they are: %s)" % (surface, ", ".join(promptkit.SURFACES)))
    if surface == "ask":
        raise LabError("`ask` is assembled in the browser (lib/llm.js): there is nothing to print here")
    if mode not in (None, "fill", "perfield", "regloss"):
        raise LabError("a mode is fill, perfield or regloss")
    if surface in ("studio-doc", "studio-exercises"):
        import server as studio
        return studio.studio_prompt(L) if surface == "studio-doc" else studio.exercise_prompt(PAGE % L.code)[0]
    if surface == "video-new":
        import ytpages
        return ytpages.assembled_full("fA6bK2mQ8sT", {"title": "T", "channel": "C"}, _captions(L),
                                      None, L, G)
    if surface == "transcript-tidy":
        import tidy
        return tidy.assembled(_captions(L), L.code)
    if surface == "book-new":
        # the page fills the template in the browser: the names of the two
        # languages are put in, and every other name it fills shows as itself,
        # which also proves the kit knows them all
        known = {"LANG_NAME": L.name, "LANG_NATIVE": L.native, "LANG": L.code,
                 "GLOSS_NAME": G.name, "GLOSS_NATIVE": G.native, "GLOSS": G.code}
        values = {n: known.get(n, "<%s>" % n) for n, _ in promptkit.placeholders(surface)
                  if n not in ("LANGUAGE", "LANGUAGE_NATIVE", "LANGUAGE_CODE", "TR_LABEL",
                               "LANG_CONVENTIONS", "GLOSS_LANGUAGE", "GLOSS_CODE")}
        return promptkit.assemble(surface, L, G, values=values)
    kind = "books" if surface == "book-region" else "videos"
    path, tmp = _fixture(kind, L)
    try:
        regloss, perfield = mode == "regloss", mode == "perfield"
        m = glossregion._mode(regloss, perfield)
        if kind == "books":
            ctx, units, _f, _k = glossregion._book_units(path, 0, 5)
        else:
            ctx, units, _s = glossregion._video_units(path, 0, 3)
        return glossregion.assembled(ctx, units, m)[0]
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def _tokens(text):
    """A chatbot's count, roughly: about 4 characters a token in Latin script
    and about 2 in Arabic script, CJK and Devanagari."""
    wide = sum(1 for c in text if "؀" <= c <= "ۿ" or "ݐ" <= c <= "ݿ"
               or "ﭐ" <= c <= "﻿" or "ऀ" <= c <= "ॿ"
               or "　" <= c <= "鿿" or "豈" <= c <= "￯")
    return int((len(text) - wide) / 4 + wide / 2 + 0.5)


def sizes(a, surface, lang):
    """The rows of the size table: [(label, characters)], the whole last."""
    L = languages.get_or_default(lang) if isinstance(lang, str) else lang
    rows = [("version line", len(a.header))]
    language = promptkit.language_text(surface, L) if surface in promptkit.KIND else ""
    inside = language and language in a.instructions
    rows.append(("instructions" + (", without the language's" if inside else ""),
                 len(a.instructions) - (len(language) if inside else 0)))
    if inside:
        for name, text in promptkit.language_sections(surface, L) or []:
            rows.append(("  language: %s" % name, len(text)))
    rows += [("answer contract", len(a.contract)), ("data", len(a.data)), ("the whole", len(a.text))]
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(prog="promptlab.py", description=__doc__.split("\n")[0])
    ap.add_argument("surface", nargs="?", choices=promptkit.SURFACES)
    ap.add_argument("language", nargs="?", help="a code of the registry: %s" % " ".join(languages.CODES))
    ap.add_argument("--mode", help="a region's: fill, perfield or regloss")
    ap.add_argument("--gloss", help="the language the meanings are written in (default %s)" % languages.DEFAULT_GLOSS)
    ap.add_argument("--sizes", action="store_true", help="the table alone")
    args = ap.parse_args(argv)
    if not (args.surface and args.language):
        ap.error("name a surface and a language")
    if args.language not in languages.LANGS:
        ap.error("%r is not a language of the registry (%s)" % (args.language, " ".join(languages.CODES)))
    try:
        a = build(args.surface, args.language, args.mode, args.gloss)
    except (LabError, promptkit.PromptError) as e:
        print("promptlab: %s" % e, file=sys.stderr)
        return 2
    if not args.sizes:
        print(a.text)
        print("=" * 70)
    for label, n in sizes(a, args.surface, args.language):
        print("%-46s %8d chars" % (label, n))
    print("%-46s %8d tokens, about" % ("", _tokens(a.text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
