# SPDX-License-Identifier: GPL-3.0-or-later
"""An inline LaTeX drawing's depth (TO-DO §8.39's L8): the second, small
compile lib/latexdraw.py runs only for `inline=True`, which boxes the same
notation rather than typesetting it, to learn where its own baseline sits.
Real xelatex, real PyMuPDF: without either, this says so and is skipped
(python312_base, this checkout's own quick-test env, had neither until this
round -- see TO-DO-a0.4.0-latex.md's top note). Never runs two blocks at
once; `latexdraw.DRAWN` is redirected, so nothing here is markdown/latex/."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for folder in (ROOT / "lib", ROOT / "markdown" / "exlex"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import latexdraw    # noqa: E402
import latexthemes  # noqa: E402

TOOLS = bool(shutil.which("xelatex"))
try:
    import pymupdf   # noqa: F401
except ImportError:
    try:
        import fitz  # noqa: F401
    except ImportError:
        TOOLS = False


@unittest.skipUnless(TOOLS, "needs xelatex and PyMuPDF")
class InlineDepth(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.was = latexthemes.STORE, latexdraw.DRAWN
        latexthemes.STORE = os.path.join(self.tmp.name, "config", "latex.json")
        latexdraw.DRAWN = os.path.join(self.tmp.name, "latex")

    def tearDown(self):
        latexthemes.STORE, latexdraw.DRAWN = self.was
        self.tmp.cleanup()

    def test_an_inline_drawing_carries_a_depth_a_block_never_has(self):
        tex = r"$\displaystyle\frac{1}{1+x^2}$"
        block = latexdraw.draw(tex, "default", limit=25)
        inline = latexdraw.draw(tex, "default", limit=25, inline=True)
        self.assertTrue(block["ok"] and inline["ok"])
        self.assertIsNone(block["d"])
        self.assertIsInstance(inline["d"], float)
        # the SAME picture either way (the owner, 2026-09-27: "same picture
        # as the screen" on paper too) -- only the meta differs, never what
        # is drawn, and a block's own key must not answer an inline request
        self.assertEqual((block["w"], block["h"]), (inline["w"], inline["h"]))
        self.assertNotEqual(block["key"], inline["key"])
        # the depth is a real fraction of the picture's own height: a
        # display fraction sits with more of itself above the line than
        # below, never the whole height and never nothing
        self.assertTrue(0 < inline["d"] < inline["h"])

    def test_the_probe_never_touches_the_kept_drawing_itself(self):
        tex = r"\ce{2H2 + O2 -> 2H2O}"
        r = latexdraw.draw(tex, "chemistry", limit=25, inline=True)
        if not r["ok"]:
            self.skipTest("chemistry's own packages are not on this computer: %s" % r.get("said"))
        with open(r["pdf"], "rb") as fh:
            head = fh.read(5)
        self.assertEqual(head, b"%PDF-")   # the KEPT pdf, the real drawing -- not the probe's

    def test_a_probe_that_cannot_compile_still_lets_the_drawing_through(self):
        # a drawing that compiles fine on its own can still be one the boxed
        # probe cannot (an exotic edge case, not tried here) -- reproduced by
        # asking the probe for a theme with no such compiler, which _compile
        # never even reaches for the drawing itself, only to prove _inline_depth
        # degrades to None rather than raising when its own compile fails
        info = latexdraw.compiler("xelatex")
        resolved = latexthemes.resolve("default")
        with tempfile.TemporaryDirectory() as work:
            depth = latexdraw._inline_depth(r"\undefinedcommandxyz", resolved, info, work, 20)
        self.assertIsNone(depth)
