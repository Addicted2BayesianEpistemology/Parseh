"""The studio's PDF has a face for the IPA its body face lacks
(markdown/exlex/template.tex, "GLYPH FALLBACK").

    python3 -m unittest discover -s tests -p test_studio_pdf_glyphs.py

TeX Gyre Pagella and Heros have ə æ ð θ ŋ and none of ʊ ɪ ɑ ʃ ʒ ɛ ɔ ʌ ˈ ː, and
XeTeX has no glyph fallback of its own: a jolly card copied from an English
book -- whose second line is IPA -- printed boxes, the log said "Missing
character", and the build still reported its target strings verified.
Each document here is built by the real `exlex.py build` in a temporary
directory, and what is read is what the build leaves: its exit code, the
log, the PDF's text (pdftotext), the PDF's fonts (pdffonts), its pages
(pdftoppm).  Needs xelatex, poppler, DejaVu Serif and PyMuPDF; without any of them
the tests say so and are skipped."""
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXLEX = ROOT / "markdown" / "exlex" / "exlex.py"
TOOLS = all(shutil.which(t) for t in ("xelatex", "pdftotext", "pdffonts", "pdftoppm"))


def has_font(name):
    fc = shutil.which("fc-list")
    if not fc:
        return False
    out = subprocess.run([fc, name], capture_output=True, text=True).stdout
    return bool(out.strip())


DEJAVU = has_font("DejaVu Serif")

# exlex.py build verifies the PDF with verify.py, which needs PyMuPDF in the
# Python that runs it (sys.executable)
try:
    import pymupdf  # noqa: F401
    HAVE_PYMUPDF = True
except ImportError:
    HAVE_PYMUPDF = False

# what the book reader's jolly prefill puts on the clipboard for an English
# book (the IPA line in front-secondary), pasted into a document as it is
IPA_DOC = """---
title: Clock words
lang: en
target: en
---

## The vowels /ʊ/ and /ɪ/

[window]{tl} is said ˈwɪndoʊ; **bold ʃ**, *italic ʒ*, and in code `ʊ ɪ ɑː`.

A nasal ɑ̃, a stress mark and a length mark: ˈɑː.

:::exercise flashcard
card-type: jolly
front-primary: [wound]{tl}
front-secondary: waʊnd ðə klɑk
back-primary: |
  turned the key of the clock

  | form | sound |
  |---|---|
  | wound | waʊnd |
  | wind | wɪnd |
back-secondary: wound the clock
:::
"""

# the characters of an English transcription Pagella HAS, and nothing else
PLAIN_DOC = """---
title: Plain words
lang: en
target: en
---

## Nothing to fall back on

[the]{tl} is ðə, [thin]{tl} is θin, [sing]{tl} ends in ŋ and [cat]{tl} has æ.

:::exercise flashcard
card-type: jolly
front-primary: [the]{tl}
front-secondary: ðə
back-primary: **the**, the article
back-secondary: θ ŋ æ ə
:::
"""

FALLBACK_START = "% ----------------------- GLYPH FALLBACK"
FALLBACK_END = "  \\XeTeXinterchartokenstate=1\n}{}\n"


def build(md, out):
    src = out / "doc.md"
    src.write_text(md, encoding="utf-8")
    r = subprocess.run([sys.executable, str(EXLEX), "build", str(src), "-o", str(out / "out"), "-q"],
                       cwd=str(ROOT / "markdown"), capture_output=True, text=True, timeout=600)
    return r, out / "out"


def fonts(pdf):
    out = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True).stdout
    return {re.sub(r"^[A-Z]{6}\+", "", line.split()[0]) for line in out.splitlines()[2:] if line.strip()}


def text(pdf):
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout


def missing(outdir):
    log = (outdir / "main.log").read_text(encoding="utf-8", errors="replace")
    return [l for l in log.splitlines() if l.startswith("Missing character")]


@unittest.skipUnless(TOOLS, "needs xelatex, pdftotext, pdffonts and pdftoppm")
@unittest.skipUnless(DEJAVU, "DejaVu Serif is not installed: the studio's PDF has no fallback face here")
@unittest.skipUnless(HAVE_PYMUPDF, "PyMuPDF is not installed in this Python: exlex.py build cannot verify")
class GlyphFallback(unittest.TestCase):

    def test_ipa_prints_in_every_face(self):
        with tempfile.TemporaryDirectory(prefix="parseh-ipa-pdf-") as td:
            r, out = build(IPA_DOC, Path(td))
            self.assertEqual(0, r.returncode, r.stdout + r.stderr)
            self.assertRegex(r.stdout, r"verify: (\d+)/\1 ")
            self.assertEqual([], missing(out), "the log names characters the PDF has no glyph for")
            words = text(out / "main.pdf")
            for s in ("waʊnd ðə klɑk", "waʊnd", "wɪnd", "ˈwɪndoʊ", "/ʊ/", "/ɪ/", "bold ʃ", "italic ʒ", "ʊ ɪ ɑː", "ɑ̃", "ˈɑː"):
                self.assertIn(s, words)
            used = fonts(out / "main.pdf")
            # body text, a sans heading and a code span each fall back to the
            # DejaVu of their own kind, bold and italic to its bold and italic
            for face in ("DejaVuSerif", "DejaVuSerif-Bold", "DejaVuSerif-Italic", "DejaVuSans-Bold", "DejaVuSansMono"):
                self.assertIn(face, used)

    def test_a_document_without_them_sets_exactly_as_before(self):
        with tempfile.TemporaryDirectory(prefix="parseh-ipa-pdf-") as td:
            r, out = build(PLAIN_DOC, Path(td))
            self.assertEqual(0, r.returncode, r.stdout + r.stderr)
            self.assertEqual([], missing(out))
            self.assertFalse({f for f in fonts(out / "main.pdf") if f.startswith("DejaVuSerif")},
                             "no character needed the fallback, and none was set in it")
            # the same .tex with the fallback taken out, built beside it: the
            # pages are the same pixels
            tex = (out / "main.tex").read_text(encoding="utf-8")
            i = tex.index(FALLBACK_START)
            j = tex.index(FALLBACK_END, i) + len(FALLBACK_END)
            bare = Path(td) / "bare"
            shutil.copytree(out / "fonts", bare / "fonts")
            (bare / "main.tex").write_text(tex[:i] + tex[j:], encoding="utf-8")
            for _ in range(2):
                b = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                                   cwd=str(bare), capture_output=True, text=True)
                self.assertEqual(0, b.returncode, b.stdout[-2000:])
            (out / "pages").mkdir()
            (bare / "pages").mkdir()
            for d in (out, bare):
                subprocess.run(["pdftoppm", "-r", "100", str(d / "main.pdf"), str(d / "pages" / "p")], check=True)
            with_fb = sorted((out / "pages").iterdir())
            without = sorted((bare / "pages").iterdir())
            self.assertTrue(with_fb)
            self.assertEqual([p.name for p in without], [p.name for p in with_fb])
            for a, b in zip(with_fb, without):
                self.assertEqual(a.read_bytes(), b.read_bytes(), "page %s differs with the fallback in" % a.name)
            self.assertEqual(text(bare / "main.pdf"), text(out / "main.pdf"))



# A Latin word inside the target's own text, in a mark, a tinted block, a
# block of lines, an exercise and the title.  Noto Naskh Arabic and the
# Devanagari faces have no Latin letters: the word was a blank on paper.
LATIN_IN = {
    "ar": """---
title: Probe [ملف PDF]{tl}
lang: en
target: ar
---

A mark: [أرسلت ملف PDF إلى المعلم]{tl}, and two words in one: [قال Good morning لي]{tl}.

[هذا ملف PDF جديد]{tl bg=sage}

[
السطر الأول مع Python هنا⏎
السطر الثاني مع e-mail، ثم (PDF) والنهاية
]{tl}

:::exercise true-false
prompt: True or false?
- [أرسلت ملف PDF]{tl} => true
:::
""",
    "hi": """---
title: Probe [मैंने PDF भेजा]{tl}
lang: en
target: hi
---

A mark: [मैंने PDF भेजा]{tl}, and a phrase: [उसने Good morning कहा]{tl}.

[यह नई PDF फ़ाइल है]{tl bg=sage}

:::exercise true-false
prompt: True or false?
- [मैंने PDF भेजा]{tl} => true
:::
""",
    # Vazirmatn has Latin letters, the nastaliq face has none -- and a
    # nastaliq block with no tint did not build at all
    "fa": """---
title: Probe
lang: en
target: fa
---

A mark: [یک فایل PDF جدید]{tl}, and two words: [گفت Good morning به من]{tl}.
""",
    "fa-nastaliq": """---
title: Probe
lang: en
target: fa
---

[این یک فایل PDF است]{tl font=nastaliq}
""",
}


def glyphs(pdf):
    """Every glyph of the PDF: (page, character, bbox, font), as PyMuPDF reads it."""
    with pymupdf.open(str(pdf)) as d:
        return [(page.number, c["c"], c["bbox"], s["font"]) for page in d
                for b in page.get_text("rawdict")["blocks"] for l in b.get("lines", [])
                for s in l["spans"] for c in s["chars"]]


def word_faces(got, word):
    """The faces the letters of `word` are set in, wherever it is printed."""
    lines = {}
    for n, c, b, font in got:
        lines.setdefault((n, round(b[3])), []).append((b[0], c, font))
    faces = set()
    for line in lines.values():
        line.sort()
        chars = "".join(c for _x, c, _f in line)
        at = chars.find(word)
        while at >= 0:
            faces |= {f for _x, _c, f in line[at:at + len(word)]}
            at = chars.find(word, at + 1)
    return faces


@unittest.skipUnless(TOOLS, "needs xelatex, pdftotext, pdffonts and pdftoppm")
@unittest.skipUnless(HAVE_PYMUPDF, "PyMuPDF is not installed in this Python: exlex.py build cannot verify")
class LatinInTheTargetsText(unittest.TestCase):

    def built(self, code, td):
        r, out = build(LATIN_IN[code], Path(td))
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"verify: (\d+)/\1 ")
        self.assertEqual([], missing(out), code)
        return out

    def test_a_latin_word_prints_in_a_face_that_has_its_letters(self):
        for code in ("ar", "hi", "fa", "fa-nastaliq"):
            with tempfile.TemporaryDirectory(prefix="parseh-latin-pdf-") as td:
                out = self.built(code, td)
                words = text(out / "main.pdf")
                for s in ("PDF",) + (("Good morning",) if code != "fa-nastaliq" else ()) + (
                        ("Python", "e-mail") if code == "ar" else ()):
                    self.assertIn(s, words, code)
                faces = word_faces(glyphs(out / "main.pdf"), "PDF")
                if code.startswith("fa"):
                    # Vazirmatn's own letters, as they always were, and in
                    # the nastaliq block the face it was entered from
                    self.assertEqual({"Vazirmatn-Regular"}, faces, code)
                else:
                    # the prose's serif in the text, the title's sans above it
                    self.assertTrue({"TeXGyrePagella-Regular", "TeXGyreHeros-Bold"} <= faces, (code, faces))
                    self.assertFalse([f for f in faces if "Naskh" in f or "Devanagari" in f], code)

    def test_latin_words_in_right_to_left_text_keep_their_order_and_spaces(self):
        with tempfile.TemporaryDirectory(prefix="parseh-latin-pdf-") as td:
            out = self.built("fa", td)
            got = [(n, c, b) for n, c, b, _f in glyphs(out / "main.pdf") if c.strip()]
            # "Good morning", left to right: one island, not two in the
            # right-to-left order of the line ("morningGood")
            first = next(b for n, c, b in got if c == "G")
            line = sorted((b[0], b[2], c) for n, c, b in got if n == 0 and abs(b[1] - first[1]) < 2)
            self.assertIn("Goodmorning", "".join(c for _x0, _x1, c in line))
            # and the word after an island stands clear of it: it was set
            # against it, "PDFجدید"
            p = next(i for i, (_x0, _x1, c) in enumerate(line) if c == "P")
            self.assertGreater(line[p][0] - line[p - 1][1], 1.0, line[p - 1:p + 1])

    def test_only_a_document_with_one_carries_the_macro(self):
        with tempfile.TemporaryDirectory(prefix="parseh-latin-pdf-") as td:
            out = self.built("ar", td)
            self.assertIn("\\protected\\def\\tllatin", (out / "main.tex").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="parseh-latin-pdf-") as td:
            r, out = build(LATIN_IN["ar"].replace("PDF", "ملف").replace("Python", "بايثون")
                           .replace("Good morning", "صباح الخير").replace("e-mail", "بريد"), Path(td))
            self.assertEqual(0, r.returncode, r.stdout + r.stderr)
            self.assertNotIn("tllatin", (out / "main.tex").read_text(encoding="utf-8"))


class BundledFaces(unittest.TestCase):
    """A face the toolbox carries (lib/fonts) is in every build's fonts/:
    the generator writes the ./fonts/ path of any face it finds there, and
    Noto Serif Devanagari was not copied -- a Hindi PDF was set in the
    system's Noto Sans Devanagari, or on a machine without one in none."""

    def test_every_face_the_generator_names_is_in_the_build(self):
        for folder in (ROOT / "markdown" / "exlex", ROOT / "lib"):
            if str(folder) not in sys.path:
                sys.path.insert(0, str(folder))
        import envsetup
        import languages
        import texgen
        fonts = envsetup.copy_bundled_fonts(verbose=False)
        named = 0
        for code in languages.CODES:
            tex = languages.get(code).tex
            for name in [tex.get("main"), tex.get("alt")] + list(tex.get("main_fallbacks") or []):
                files = name and texgen.bundled_font_files(name)
                if files:
                    named += 1
                    for f in files:
                        if f:
                            self.assertTrue((fonts / f).exists(), (code, name, f))
        self.assertGreaterEqual(named, 5)       # Vazirmatn, Naskh (twice), Nastaliq, Devanagari

    def test_builds_starting_together_on_a_fresh_install_each_get_every_face(self):
        # The server's provisioning thread and every build's request thread
        # copy the bundled faces, and each build then copies the folder whole
        # (server.build_pdf).  With one <name>.part shared in the folder, six
        # at once crashed on a .part another had renamed, or copied the
        # folder before the Devanagari face was in it.
        from concurrent.futures import ThreadPoolExecutor
        from unittest import mock
        for folder in (ROOT / "markdown" / "exlex", ROOT / "lib"):
            if str(folder) not in sys.path:
                sys.path.insert(0, str(folder))
        import envsetup
        with tempfile.TemporaryDirectory(prefix="parseh-fonts-") as td:
            with mock.patch.object(envsetup, "HERE", Path(td) / "alone"):
                fonts = envsetup.copy_bundled_fonts(verbose=False)
                want = sorted((p.name, p.stat().st_size) for p in fonts.iterdir())
            self.assertIn(("NotoSerifDevanagari-Regular.ttf",
                           (envsetup.LIB_FONTS / "NotoSerifDevanagari-Regular.ttf").stat().st_size), want)
            for n in range(20):
                here = Path(td) / str(n)

                def build(k):
                    fonts = envsetup.copy_bundled_fonts(verbose=False)
                    out = here / "builds" / str(k)
                    shutil.copytree(fonts, out, ignore=shutil.ignore_patterns("*.part"))
                    return sorted((p.name, p.stat().st_size) for p in out.iterdir())
                with mock.patch.object(envsetup, "HERE", here), ThreadPoolExecutor(6) as pool:
                    got = list(pool.map(build, range(6)))
                self.assertEqual([want] * 6, got, n)
                # and no copy on its way is left behind
                self.assertEqual([], [p.name for p in (here / "assets").iterdir() if p.name != "fonts"], n)

    @unittest.skipUnless(TOOLS, "needs xelatex, pdftotext, pdffonts and pdftoppm")
    @unittest.skipUnless(HAVE_PYMUPDF, "PyMuPDF is not installed in this Python: exlex.py build cannot verify")
    def test_a_hindi_pdf_is_set_in_the_face_that_comes_with_the_toolbox(self):
        with tempfile.TemporaryDirectory(prefix="parseh-hindi-pdf-") as td:
            r, out = build("---\ntitle: T\nlang: en\ntarget: hi\n---\n\nSay नमस्ते; **बहुत अच्छा** is very good.\n",
                           Path(td))
            self.assertEqual(0, r.returncode, r.stdout + r.stderr)
            used = fonts(out / "main.pdf")
            self.assertIn("NotoSerifDevanagari-Regular", used)
            self.assertIn("NotoSerifDevanagari-Bold", used)


# Devanagari as the Hindi starter prints it: the vowel sign i (ि) drawn
# before the consonants it follows in writing, र् drawn as a hook over the
# end of the cluster it begins.  The verifier read that order as it was
# drawn: a correct PDF of the starter was 34 strings "missing" (88/122).
@unittest.skipUnless(TOOLS, "needs xelatex, pdftotext, pdffonts and pdftoppm")
@unittest.skipUnless(HAVE_PYMUPDF, "PyMuPDF is not installed in this Python: exlex.py build cannot verify")
class DevanagariVerified(unittest.TestCase):

    def test_the_hindi_starter_verifies_and_a_pdf_without_the_shaping_does_not(self):
        for folder in (ROOT / "markdown" / "exlex", ROOT / "lib"):
            if str(folder) not in sys.path:
                sys.path.insert(0, str(folder))
        import verify
        starters = ROOT / "markdown" / "exlex" / "starters"
        with tempfile.TemporaryDirectory(prefix="parseh-hindi-verify-") as td:
            shutil.copytree(starters / "assets" / "images", Path(td) / "images")
            r, out = build((starters / "hi.md").read_text(encoding="utf-8"), Path(td))
            self.assertEqual(0, r.returncode, r.stdout + r.stderr)
            got = re.search(r"verify: (\d+)/(\d+) ", r.stdout)
            self.assertEqual(got.group(1), got.group(2), r.stdout)
            self.assertGreater(int(got.group(2)), 100)
            # the same PDF read in the order it is drawn: the old verdict
            real = verify._written_order
            verify._written_order = lambda s, L: s
            try:
                _ok, drawn = verify.check(str(out / "main.pdf"), str(out / "main.tex"))
            finally:
                verify._written_order = real
            self.assertGreater(len(drawn), 20)
            # A PDF set without the script's shaping draws ि after its
            # consonant, where it is written: here each one is cut from its
            # consonant (\kern0pt), which leaves it to be drawn so.  Every
            # string with one in it is reported, and no other.
            tex = (out / "main.tex").read_text(encoding="utf-8")
            at = tex.index("\\begin{document}")
            broken = tex[:at] + re.sub("(?<=[\u0915-\u0939\u093C])\u093F", "\\\\kern0pt \u093F", tex[at:])
            self.assertNotEqual(tex, broken)
            (out / "main.tex").write_text(broken, encoding="utf-8")
            for _ in range(2):
                b = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                                   cwd=str(out), capture_output=True, text=True, timeout=600)
                self.assertEqual(0, b.returncode, b.stdout[-2000:])
            ok, failures = verify.check(str(out / "main.pdf"), str(out / "main.tex"))
            self.assertGreater(len(failures), 20)
            self.assertEqual([], [a for a, _kind in failures if "\u093F" not in a])
            self.assertTrue(ok)

    # Everyday words with a reph, as a note uses them: over a cluster with a
    # consonant after it (दर्शक), over a syllable with ि (धार्मिक, drawn as one
    # glyph with it), over a cluster before a ि of the next one (मर्यादित),
    # over a ो the face cuts in two (धर्मों).  A correct PDF of them was
    # "9 text FAIL"; and words without one, to show a cut reph fails alone.
    REPH_WORDS = ("दर्शक कार्यक्रम कर्मचारी धार्मिक अर्थव्यवस्था पर्यटक वर्षगांठ मार्गदर्शन "
                  "आशीर्वाद मार्च सर्दी शर्मिंदा कीर्ति पूर्णिमा निर्माण मर्यादित धर्मनिरपेक्ष "
                  "सर्वप्रिय धर्मों वर्षों सर्वोच्च").split()
    PLAIN_WORDS = "किताब नमस्ते स्थिति अच्छा".split()

    def test_words_with_a_reph_verify_and_a_reph_drawn_as_written_does_not(self):
        for folder in (ROOT / "markdown" / "exlex", ROOT / "lib"):
            if str(folder) not in sys.path:
                sys.path.insert(0, str(folder))
        import verify
        words = self.REPH_WORDS + self.PLAIN_WORDS
        md = ("---\ntitle: Reph\nlang: en\ntarget: hi\n---\n\n## Words\n\n"
              + "\n\n".join("Word %d: %s, **%s**." % (n, w, w) for n, w in enumerate(words)) + "\n")
        with tempfile.TemporaryDirectory(prefix="parseh-hindi-reph-") as td:
            r, out = build(md, Path(td))
            self.assertEqual(0, r.returncode, r.stdout + r.stderr)
            self.assertIn("verify: %d/%d " % (2 * len(words), 2 * len(words)), r.stdout)
            # A PDF set without the script's shaping draws र् where it is
            # written, before its consonant: here each one is cut from the
            # consonant after it (\kern0pt), which leaves it to be drawn so.
            # Every word with one is reported, and no other.
            tex = (out / "main.tex").read_text(encoding="utf-8")
            at = tex.index("\\begin{document}")
            broken = tex[:at] + re.sub("\u0930\u094D(?=[\u0915-\u0939])", "\u0930\u094D\\\\kern0pt ", tex[at:])
            self.assertNotEqual(tex, broken)
            (out / "main.tex").write_text(broken, encoding="utf-8")
            for _ in range(2):
                b = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                                   cwd=str(out), capture_output=True, text=True, timeout=600)
                self.assertEqual(0, b.returncode, b.stdout[-2000:])
            ok, failures = verify.check(str(out / "main.pdf"), str(out / "main.tex"))
            self.assertEqual(sorted(2 * self.REPH_WORDS),
                             sorted(re.sub(r"\\kern0pt ", "", a) for a, _kind in failures))
            self.assertEqual(2 * len(self.PLAIN_WORDS), ok)

if __name__ == "__main__":
    unittest.main()
