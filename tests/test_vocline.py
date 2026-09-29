# SPDX-License-Identifier: GPL-3.0-or-later
"""A vocabulary line, read and drawn twice and held equal: lib/texparse.py
(parse_voc, voc_text) and lib/tex2html.py (render_voc) in Python, which the
reader and the PDF go by, and lib/vocline.js, which a video's player draws a
macro line with.

    python3 -m unittest tests/test_vocline.py

tests/fixtures/vocline.json holds the cases, as tests/fixtures/wordline.json
holds the word line's; the Python side is run here, the JavaScript side under
deno.  Beyond the fixture, every vocabulary line of every fixture book and
video is read by both, so an equality that holds only for the lines somebody
thought of would not pass.  Standard library only.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import chunkdiv        # noqa: E402
import languages       # noqa: E402
import tex2html as X   # noqa: E402
import texparse as T   # noqa: E402
import texwrite        # noqa: E402

FIXTURE = json.loads((ROOT / "tests" / "fixtures" / "vocline.json").read_text(encoding="utf-8"))
CASES = FIXTURE["cases"]
DENO = shutil.which("deno") or os.path.expanduser("~/miniconda3/envs/ilya-frank/bin/deno")
VOCLINE = ROOT / "lib" / "vocline.js"


def read_in_python(voc, code):
    """What the reader's own code makes of one line, in the fixture's shape."""
    L = languages.get(code)
    was = T._LANG, X.LANG
    T.set_lang(L)
    X.set_lang(L)
    try:
        return {"runs": [list(r) for r in T.parse_voc(voc, L)],
                "html": X.render_voc(voc), "text": T.voc_text(voc, L),
                "macro": chunkdiv.is_macro_line(voc)}
    except (AssertionError, IndexError):        # a group missing, or none left to read
        return {"error": "groups", "macro": chunkdiv.is_macro_line(voc)}
    except ValueError:                          # read_group: a { never closed
        return {"error": "unclosed", "macro": chunkdiv.is_macro_line(voc)}
    finally:
        T._LANG, X.LANG = was


def read_in_javascript(lines):
    """[{lang, voc}] -> what lib/vocline.js makes of each, run under deno."""
    codes = sorted({x["lang"] for x in lines})
    js = """
await import(%s);
const V = globalThis.ParsehVocline, LINES = %s, LANGS = %s, out = [];
for (const c of LINES) {
  const L = LANGS[c.lang], r = {macro: V.isMacro(c.voc)};
  try { r.runs = V.parse(c.voc, L); r.html = V.render(c.voc, L); r.text = V.flatten(c.voc, L); }
  catch (e) { r.error = e.code; }
  out.push(r);
}
console.log(JSON.stringify(out));
""" % (json.dumps("file://" + str(VOCLINE)), json.dumps(lines),
       json.dumps({c: languages.get(c).as_json() for c in codes}))
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, encoding="utf-8") as f:
        f.write(js)
    try:
        r = subprocess.run([DENO, "run", "--quiet", "--allow-read", f.name],
                           capture_output=True, text=True, timeout=120)
    finally:
        os.unlink(f.name)
    if r.returncode:
        raise AssertionError("deno failed: " + (r.stderr or r.stdout)[-600:])
    return json.loads(r.stdout.strip().split("\n")[-1])


def fixture_lines():
    """Every vocabulary line the fixture books and videos hold, with its
    language: what a real edition and a real video write, not what a test
    thought of."""
    import books
    out = []
    for d in sorted(glob.glob(str(ROOT / "tests" / "fixtures" / "books" / "*" / "*"))):
        if not os.path.isfile(os.path.join(d, "book.json")):
            continue
        code = books.Book(d).lang.code
        for path in sorted(glob.glob(os.path.join(d, "ch*.tex"))):
            out += [{"lang": code, "voc": c["voc"]} for c in texwrite.read_chunks(path) if c["voc"].strip()]
    for fx in sorted(glob.glob(str(ROOT / "tests" / "fixtures" / "videos" / "*" / "*" / "video.json"))):
        code = languages.get_or_default(json.loads(Path(fx).read_text(encoding="utf-8")).get("language")).code
        ann = json.loads((Path(fx).parent / "annotations.json").read_text(encoding="utf-8"))
        out += [{"lang": code, "voc": ch["voc"]} for sg in ann["segments"]
                for ch in (sg.get("chunks") or []) if isinstance(ch.get("voc"), str) and ch["voc"].strip()]
    return out


class Fixture(unittest.TestCase):
    def test_every_case_says_what_it_expects(self):
        for c in CASES:
            with self.subTest(voc=c["voc"]):
                self.assertIn(c["lang"], languages.CODES)
                self.assertIsInstance(c["macro"], bool)
                if "error" in c:
                    self.assertIn(c["error"], ("groups", "unclosed"))
                else:
                    self.assertEqual(sorted(k for k in c if not k.startswith("_")),
                                     ["html", "lang", "macro", "runs", "text", "voc"])

    def test_it_covers_what_it_is_for(self):
        """A fixture that has lost a kind of line has stopped guarding it:
        both labels of a \\vb, a pair left blank, a \\bw without its braces, a
        \\pw inside a meaning, a slash beside a macro, a \\textit,
        right-to-left, Japanese, a plain line -- and a line that cannot be
        read, of each of the two kinds."""
        def labels(c):
            L = languages.get(c["lang"])
            return {lab for lab in L.vb_labels
                    if any(k == "txt" and t == " · %s " % lab for k, t in c.get("runs", []))}
        kinds = {
            "both labels of a \\vb": lambda c: "\\vb{" in c["voc"] and len(labels(c)) == 2,
            "a pair left blank": lambda c: "\\vb{" in c["voc"] and len(labels(c)) == 1 and "{}{}" in c["voc"],
            "a \\bw without its braces": lambda c: "error" not in c and bool(
                re.search(r"\\bw\{[^{}]*\}\{[^{}]*\}[ \t]*[^{ \t]", c["voc"])),
            "a \\pw in a meaning": lambda c: "error" not in c and bool(
                re.search(r"\\vb(\{[^{}]*\}){6}\{[^{}]*\\pw\{", c["voc"])),
            "a slash beside a macro": lambda c: "}/\\pw{" in c["voc"] and "error" not in c,
            "a \\textit": lambda c: "\\textit{" in c["voc"] and "error" not in c,
            "Persian, right to left": lambda c: c["lang"] == "fa" and 'dir="rtl"' in c.get("html", ""),
            "Arabic, right to left": lambda c: c["lang"] == "ar" and 'dir="rtl"' in c.get("html", ""),
            "Japanese": lambda c: c["lang"] == "ja" and "error" not in c,
            "a plain line": lambda c: not c["macro"] and "error" not in c,
            "a macro short of its braces": lambda c: c.get("error") == "groups",
            "a brace never closed": lambda c: c.get("error") == "unclosed",
        }
        missing = [name for name, has in kinds.items() if not any(has(c) for c in CASES)]
        self.assertEqual(missing, [])
        # and every language of the registry has a \\vb of its own in it
        wrote = {c["lang"] for c in CASES if "\\vb{" in c["voc"] and "error" not in c}
        self.assertEqual(sorted(set(languages.CODES) - wrote), [])


class Python(unittest.TestCase):
    def test_the_reader_reads_the_fixture(self):
        for c in CASES:
            with self.subTest(voc=c["voc"]):
                got = read_in_python(c["voc"], c["lang"])
                want = {k: c[k] for k in ("runs", "html", "text", "error") if k in c}
                want["macro"] = c["macro"]
                self.assertEqual(got, want)


@unittest.skipUnless(os.path.exists(DENO), "no deno")
class JavaScript(unittest.TestCase):
    def test_the_page_reads_the_fixture(self):
        got = read_in_javascript([{"lang": c["lang"], "voc": c["voc"]} for c in CASES])
        self.assertEqual(len(got), len(CASES), "one answer for every case")
        for c, g in zip(CASES, got):
            with self.subTest(voc=c["voc"]):
                want = {k: c[k] for k in ("runs", "html", "text", "error") if k in c}
                want["macro"] = c["macro"]
                self.assertEqual(g, want)

    def test_and_every_line_of_every_fixture_edition_and_video(self):
        lines = fixture_lines()
        self.assertGreater(len(lines), 100, "the fixture books and videos hold vocabulary lines")
        got = read_in_javascript(lines)
        self.assertEqual(len(got), len(lines), "one answer for every line")
        for c, g in zip(lines, got):
            with self.subTest(lang=c["lang"], voc=c["voc"]):
                self.assertEqual(g, read_in_python(c["voc"], c["lang"]))


if __name__ == "__main__":
    unittest.main()
