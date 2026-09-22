#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""exlex — markdown -> XeLaTeX -> verified PDF for linguistic documents
that mix a prose language with a target language.  Which target languages
there are is the registry's business alone (lib/languages.json); the
document's `target:` front matter says which of them this one teaches.

    python3 exlex.py build  answer.md  [-o OUTDIR] [--no-verify] [--scale S]
                                        [--size 11|14|17|20] [--mono]
    python3 exlex.py verify OUT/main.pdf OUT/main.tex
    python3 exlex.py inspect OUT/main.pdf PAGE     # visual-order debug dump
    python3 exlex.py setup                          # env prep only

Exit codes: 0 ok · 1 verification failed · 2 usage/compile error.
"""
import argparse
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import envsetup            # noqa: E402
import mdparser            # noqa: E402
import texgen              # noqa: E402
import verify as verifier  # noqa: E402


def _xelatex(outdir, passes=2):
    log = ""
    for _ in range(passes):
        r = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error",
             "main.tex"],
            cwd=outdir, capture_output=True, text=True)
        log = r.stdout + r.stderr
        if r.returncode != 0:
            return False, log
    return True, log


def cmd_build(a):
    src = Path(a.input)
    if not src.exists():
        print(f"error: {src} not found"); return 2
    outdir = Path(a.output or f"out-{src.stem}")
    outdir.mkdir(parents=True, exist_ok=True)

    env = envsetup.ensure_all(verbose=not a.quiet)
    shutil.copytree(env["fonts"], outdir / "fonts", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("*.part"))
    # a document's figures live in images/ beside it, exactly as they do in
    # the library, and the .tex points at images/<name> either way
    try:
        envsetup.stage_images(src.parent / "images", outdir)
    except Exception as e:
        print(f"error: could not prepare the images: {e}")
        return 2

    fm, blocks = mdparser.parse(src.read_text(encoding="utf-8"))
    tex = texgen.generate(fm, blocks, fa_scale=a.scale,
                          font_size=a.size, mono=a.mono)
    (outdir / "main.tex").write_text(tex, encoding="utf-8")

    ok, log = _xelatex(outdir)
    if not ok:
        (outdir / "compile-error.log").write_text(log, encoding="utf-8")
        for line in log.splitlines():
            if line.startswith("!"):
                print("compile error:", line)
        print(f"full log: {outdir/'compile-error.log'}")
        return 2

    pdf, texf = outdir / "main.pdf", outdir / "main.tex"
    final = outdir / (src.stem + ".pdf")
    shutil.copy(pdf, final)
    print(f"built: {final}")

    if a.no_verify:
        return 0
    ok_n, failures = verifier.check(pdf, texf)
    over = verifier.scan_log(outdir / "main.log")
    print(f"verify: {ok_n}/{ok_n + len(failures)} target strings correct"
          + (f", {len(over)} overfull hbox(es) > 10pt" if over else ""))
    for s, kind in failures:
        print(f"  FAIL {s!r}: {kind}")
    return 1 if failures else 0


def cmd_verify(a):
    return verifier.main(["verify", a.pdf, a.tex])


def cmd_inspect(a):
    """Dump each line of PAGE as right-to-left islands in visual L->R
    order (a bidi debugging aid; meaningful for RTL targets)."""
    import pymupdf

    def rtl(c):
        return unicodedata.bidirectional(c) in ("R", "AL", "AN")

    doc = pymupdf.open(a.pdf)
    page = doc[a.page - 1]
    chars = []
    for b in page.get_text("rawdict")["blocks"]:
        if b.get("type") != 0:
            continue
        for l in b["lines"]:
            for sp in l["spans"]:
                for ch in sp["chars"]:
                    chars.append((round(ch["origin"][1], 1),
                                  ch["bbox"][0], ch["c"]))
    buckets = {}
    for y, x, c in chars:
        k = next((k for k in buckets if abs(k - y) <= 2.5), y)
        buckets.setdefault(k, []).append((x, c))
    for y in sorted(buckets):
        row = sorted(buckets[y], key=lambda t: t[0])
        if not any(rtl(c) for _, c in row):
            continue
        parts, cur = [], []
        for _, c in row:
            if rtl(c) or unicodedata.category(c) == "Mn" or (cur and c in " \u200c"):
                cur.append(c)
            else:
                if cur:
                    parts.append("[%s]" % "".join(
                        verifier._debase(z) for z in reversed(cur)).strip())
                    cur = []
                parts.append(c)
        if cur:
            parts.append("[%s]" % "".join(
                verifier._debase(z) for z in reversed(cur)).strip())
        print(f"y={y:7.1f}  {''.join(parts)}")
    return 0


def main():
    p = argparse.ArgumentParser(prog="exlex", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="markdown -> verified PDF")
    b.add_argument("input")
    b.add_argument("-o", "--output")
    b.add_argument("--scale", default=None,
                   help="target-script size relative to Latin (default per "
                        "language: 1.52 Arabic script, 1.20 CJK, 1.00 Latin)")
    # the studio's "PDF options": both doors write the same .tex
    b.add_argument("--size", type=int, choices=texgen.PRINT_SIZES,
                   default=texgen.DEFAULT_PRINT_SIZE,
                   help="print size in points: 11 (normal), 14, 17 or 20 "
                        "(large print, for readers with low vision; "
                        "exercises are set a step larger still)")
    b.add_argument("--mono", action="store_true",
                   help="black and white: no colour and no grey anywhere "
                        "but in the pictures (for the photocopier)")
    b.add_argument("--no-verify", action="store_true")
    b.add_argument("-q", "--quiet", action="store_true")
    b.set_defaults(fn=cmd_build)

    v = sub.add_parser("verify", help="re-run bidi check on a built PDF")
    v.add_argument("pdf"); v.add_argument("tex")
    v.set_defaults(fn=cmd_verify)

    i = sub.add_parser("inspect", help="visual-order dump of one page")
    i.add_argument("pdf"); i.add_argument("page", type=int)
    i.set_defaults(fn=cmd_inspect)

    s = sub.add_parser("setup", help="prepare environment only")
    s.set_defaults(fn=lambda a: (envsetup.ensure_all(), 0)[1])

    a = p.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
