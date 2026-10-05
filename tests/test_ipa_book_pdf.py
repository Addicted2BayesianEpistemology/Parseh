# SPDX-License-Identifier: GPL-3.0-or-later
"""A book whose transliteration is IPA is set in the PDF with the letters its main face lacks
(lib/frank-preamble.tex, the roman's glyph fallback), whatever the language of the book.

    python3 -m unittest tests/test_ipa_book_pdf.py

TeX Gyre Pagella has ə æ ð θ ŋ and none of ʃ ʒ ɒ ɔ ɪ ʊ ɑ ʌ ɡ ɾ ʔ ˈ ː, and the transliteration line of a reading
edition is set in it: an IPA line would print boxes where the letters are missing, and LuaLaTeX says so only in the log
("Missing character") while the build goes on.  The roman falls back, glyph by glyph, to DejaVu Serif where it has one
(the preamble says why and what stays as it was), and this holds it for a Persian edition, whose transliteration is a
Latin line inside a right-to-left book -- the case nobody wrote IPA for before the setting existed.  The book is the
fixture's, copied into a temporary tree, its first three chunks given IPA for `tr`, and built by the real lualatex; what
is read is the log and the PDF's own text (pdftotext).  Needs lualatex, poppler, the fonts the preamble names and DejaVu
Serif; without any of them the test says so and is skipped."""
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "lib")]
import texwrite                                                     # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "books" / "persian" / "mini-fa"


def has_font(name):
    fc = shutil.which("fc-list")
    return bool(fc and subprocess.run([fc, name], capture_output=True, text=True).stdout.strip())


TOOLS = all(shutil.which(t) for t in ("lualatex", "pdftotext"))
# a line of Persian in IPA, with the letters the roman lacks -- and the stress and length marks
LINES = ("ˈʃoɾuːʔ ʒɒːle ɡæɾm", "ˈtʃeʃm ɪn ʊ ɔ ʌ ɑː", "xejli ˈχub e ɒːn")
MISSING = "ʃʒɒɔɪʊɑʌɡɾʔˈː"


@unittest.skipUnless(TOOLS, "needs lualatex and pdftotext")
@unittest.skipUnless(has_font("DejaVu Serif"), "DejaVu Serif is not installed: the roman has no fallback face here")
class AnIpaEditionInThePdf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.td.cleanup)
        root = Path(cls.td.name)
        (root / "lib").symlink_to(ROOT / "lib")
        # the fixture's main.tex reaches lib/ by climbing five levels from the book: two more than the tree
        # of the books has under its root, so the book stands two levels down
        cls.book = root / "a" / "b" / "books" / "persian" / "mini-fa"
        shutil.copytree(FIXTURE, cls.book, ignore=shutil.ignore_patterns("reader", "*.pdf", "*.aux", "*.log", "*.toc", "*.out"))
        chunks = [r for r in texwrite.read_chunks(str(cls.book / "ch1.tex")) if r["macro"] != "chp"]
        for r, line in zip(chunks, LINES):
            texwrite.edit_chunk(str(cls.book / "ch1.tex"), r["index"], {"tr": line})
        cls.built = subprocess.run(["lualatex", "-interaction=nonstopmode", "main.tex"], cwd=str(cls.book),
                                 capture_output=True, text=True, timeout=900)
        cls.log = (cls.book / "main.log").read_text(encoding="utf-8", errors="replace") if (cls.book / "main.log").exists() else ""

    def test_it_builds(self):
        self.assertTrue((self.book / "main.pdf").exists(), self.built.stdout[-1500:])

    def test_no_letter_of_the_ipa_is_a_hole_in_the_page(self):
        holes = [l for l in self.log.splitlines() if l.startswith("Missing character")]
        mine = [l for l in holes if any(c in l for c in MISSING)]
        self.assertEqual(mine, [], "the roman has no glyph for these and nothing took over:\n" + "\n".join(mine[:6]))

    def test_the_letters_are_in_the_pdfs_text(self):
        text = subprocess.run(["pdftotext", "-layout", str(self.book / "main.pdf"), "-"], capture_output=True, text=True).stdout
        flat = re.sub(r"\s+", "", text)
        for c in "ʃʒɒɔɪʊɑʌɡɾʔː":
            self.assertIn(c, flat, "%r is not in the PDF" % c)


if __name__ == "__main__":
    unittest.main()
