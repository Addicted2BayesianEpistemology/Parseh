#!/usr/bin/env python3
"""The word layer in the PDF and in the passes: the reading pass, \\chw and
\\chrw, and the registry and the reader agreeing with them.

    python3 tests/test_wordbook_tex.py               the quick checks
    PARSEH_PDF=1 python3 tests/test_wordbook_tex.py  and lualatex over copies
                                                     of mini-ja and mini-zh

What tests/smoke.py does not reach yet: the "aloud" section of
tests/fixtures/wordline.json run through all three parsers (the PDF's pass
reads wordline.lua, the reader's wordline.py, a page will read wordline.js),
and the pass that section feeds.  Standard library only.
"""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
LIB = os.path.join(ROOT, "lib")
sys.path.insert(0, LIB)
import languages                                               # noqa: E402
import newlang                                                 # noqa: E402
import wordline as W                                           # noqa: E402


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


FIX = json.loads(read(os.path.join(ROOT, "tests", "fixtures", "wordline.json")))
BOOKS = os.path.join(ROOT, "tests", "fixtures", "books")
DENO = shutil.which("deno") or os.path.expanduser("~/miniconda3/envs/ilya-frank/bin/deno")
TEXLUA = shutil.which("texlua")
PREAMBLE = read(os.path.join(LIB, "frank-preamble.tex"))


def lua_str(s):
    return '"' + "".join("\\%d" % b for b in s.encode("utf-8")) + '"'


def run(cmd, cwd=None, env=None, timeout=900):
    r = subprocess.run(cmd, cwd=cwd, env=dict(os.environ, **(env or {})),
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


class Aloud(unittest.TestCase):
    """One chunk as the reading pass reads it, the same in all three."""

    def test_python(self):
        for c in FIX["aloud"]:
            with self.subTest(fa=c["fa"], reading=c["reading"]):
                self.assertEqual(W.aloud(c["reading"], c["fa"]), c["aloud"])

    @unittest.skipUnless(TEXLUA, "no texlua")
    def test_lua(self):
        lines = ["local W = dofile(%s)" % lua_str(os.path.join(LIB, "wordline.lua"))]
        lines += ["print(W.aloud(%s, %s))" % (lua_str(c["reading"]), lua_str(c["fa"]))
                  for c in FIX["aloud"]]
        # what the preamble prints: the reading in \FrankAloudText, the closing
        # punctuation after it as TeX would print its source -- a syntax
        # character as \char, an escaped one as the one character it stands
        # for, a control symbol that prints none left out -- and a chunk
        # without a reading as its text
        said = [("やまへ", "山へ、", "\\FrankAloudText{やまへ}、"),
                ("x", "a%#", "\\FrankAloudText{x}\\char37 \\char35 "),
                (" ", "ab", "ab"),
                ("wǔshí", "占50\\%。", "\\FrankAloudText{wǔshí}\\char37 。"),
                ("x", "「おい\\,」", "\\FrankAloudText{x}」"),
                ("x", "a~」", "\\FrankAloudText{x}」"),
                ("x", "{おい！}", "\\FrankAloudText{x}！\\char125 ")]
        lines += ["print(W.tex_aloud(%s, %s))" % (lua_str(r), lua_str(fa)) for r, fa, _ in said]
        with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False, encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        try:
            rc, out = run([TEXLUA, f.name], timeout=60)
        finally:
            os.unlink(f.name)
        self.assertEqual(rc, 0, out)
        got = out.split("\n")
        for k, c in enumerate(FIX["aloud"]):
            with self.subTest(fa=c["fa"], reading=c["reading"]):
                self.assertEqual(got[k], c["aloud"])
        n = len(FIX["aloud"])
        self.assertEqual(got[n:n + len(said)], [want for _, _, want in said])

    @unittest.skipUnless(TEXLUA, "no texlua")
    def test_lua_tex_keeps_punctuation_with_its_word(self):
        """No \\FrankWordSep before closing punctuation nor after an opening
        bracket: beside a ruby box that break was a line beginning with 。.  The
        marks ride inside their word, as \\FrankWordP, so the preamble can
        measure the word and its marks together: set as two boxes, a long word
        and its comma ran past the chunk column."""
        script = ("local W = dofile(%s)\nprint(W.tex(%s, %s))\nprint(W.tex(%s, %s))\n"
                  % (lua_str(os.path.join(LIB, "wordline.lua")),
                     lua_str("「おい」と行きました。"), lua_str("「 おい 」 と 行きました(いきました) 。"),
                     lua_str("山へ"), lua_str("山(やま) へ")))
        with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False, encoding="utf-8") as f:
            f.write(script)
        try:
            rc, out = run([TEXLUA, f.name], timeout=60)
        finally:
            os.unlink(f.name)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out.split("\n")[:2], [
            "\\FrankWordP{「}{おい}{}{」}{}\\FrankWordSep "
            "\\FrankWord{と}{}\\FrankWordSep \\FrankWordP{}{行きました}{いきました}{}{。}",
            "\\FrankWord{山}{やま}\\FrankWordSep \\FrankWord{へ}{}"])

    @unittest.skipUnless(os.path.exists(DENO), "no deno")
    def test_js(self):
        js = ("await import(%s);\nconst W = globalThis.ParsehWordline, F = %s;\n"
              "console.log(JSON.stringify(F.map(c => W.aloud(c.reading, c.fa))));\n"
              % (json.dumps("file://" + os.path.join(LIB, "wordline.js")), json.dumps(FIX["aloud"])))
        with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, encoding="utf-8") as f:
            f.write(js)
        try:
            rc, out = run([DENO, "run", "--quiet", "--allow-read", f.name], timeout=120)
        finally:
            os.unlink(f.name)
        self.assertEqual(rc, 0, out)
        got = json.loads(out.strip().split("\n")[-1])
        for g, c in zip(got, FIX["aloud"]):
            with self.subTest(fa=c["fa"], reading=c["reading"]):
                self.assertEqual(g, c["aloud"])


class Registry(unittest.TestCase):
    def test_words_languages_have_five_passes(self):
        for code in languages.CODES:
            L = languages.get(code)
            with self.subTest(code=code):
                if L.words:
                    self.assertEqual(L.pass_keys, ["vocal", "aloud", "chunks", "bare", "alt"])
                    self.assertEqual([p["label"] for p in L.passes], ["1", "2", "3", "4", "5"])
                else:
                    self.assertNotIn("aloud", L.pass_keys)
        self.assertEqual(languages.get("ja").passes[1]["title"], "the reading alone, in kana")
        self.assertEqual(languages.get("zh").passes[1]["title"], "the reading alone, in pinyin")

    def test_pass_classes_are_not_renumbered(self):
        import tex2html
        got = {k: tex2html.pass_class({"key": k}) for k in ("vocal", "chunks", "bare", "aloud")}
        self.assertEqual(got, {"vocal": "p1", "chunks": "p2", "bare": "p3", "aloud": "p5"})
        self.assertEqual(tex2html.pass_class({"key": "alt", "kind": "vertical"}), "p4 vert")

    def test_check_agrees(self):
        rc, out = run([sys.executable, os.path.join(LIB, "newlang.py"), "--check"], cwd=ROOT)
        self.assertEqual(rc, 0, out[-1500:])
        self.assertIn("passes vocal/aloud/chunks/bare/alt: the registry and the .tex agree", out)

    def test_check_faults_a_disagreement(self):
        """A .tex that does not switch on the reading pass its registry entry
        lists, and an entry that lists it without its words, are both faults."""
        real_switches, real_entries = newlang.tex_switches, newlang.entries

        def no_aloud(code):
            got = real_switches(code)
            if code == "zh":
                got["Aloud"] = False
            return got

        def no_words(reg):
            langs = dict(real_entries(reg))
            langs["ja"] = dict(langs["ja"], words=False)
            return langs

        for patch, want in (
                (mock.patch.object(newlang, "tex_switches", no_aloud),
                 "lib/lang/zh.tex switches aloud the other way"),
                (mock.patch.object(newlang, "entries", no_words),
                 "words is False and the passes are vocal/aloud/chunks/bare/alt")):
            with self.subTest(want=want):
                buf = io.StringIO()
                with patch, contextlib.redirect_stdout(buf):
                    rc = newlang.check()
                self.assertEqual(rc, 1)
                self.assertIn(want, buf.getvalue())

    def test_newlang_derives_the_order(self):
        """A language scaffolded with --words gets the passes ja and zh have."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            newlang.main(["qx", "--name", "Testish", "--native", "Testish", "--script", "cjk",
                          "--words", "--vertical", "--translit-label", "pinyin", "--dry-run"])
        text = buf.getvalue()
        entry = json.loads(text[text.index("\n{") + 1:text.index("\n--dry-run")])["qx"]
        self.assertTrue(entry["words"])
        self.assertEqual([p["key"] for p in entry["passes"]], languages.get("zh").pass_keys)
        self.assertEqual([p["label"] for p in entry["passes"]], ["1", "2", "3", "4", "5"])
        self.assertEqual(entry["passes"][1]["title"], "the reading alone, in pinyin")
        tex = newlang.render_tex("qx", entry)
        self.assertIn("\\FrankHasAloudtrue", tex)
        self.assertIn("\\FrankHasBaretrue", tex)
        self.assertIn("Every passage comes five times.", tex)
        # and nothing changes for a language without words
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            newlang.main(["qy", "--name", "Testy", "--native", "Testy", "--dry-run"])
        text = buf.getvalue()
        entry = json.loads(text[text.index("\n{") + 1:text.index("\n--dry-run")])["qy"]
        self.assertEqual([(p["key"], p["label"]) for p in entry["passes"]],
                         [("vocal", "1"), ("chunks", "2")])
        self.assertIn("\\FrankHasAloudfalse", newlang.render_tex("qy", entry))

    def test_words_refused_for_a_spaced_language(self):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                newlang.main(["qy", "--name", "Testy", "--native", "Testy", "--words",
                              "--dry-run"])
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("--words on a language written with spaces", err.getvalue())


class Preamble(unittest.TestCase):
    def macro(self, name):
        m = re.search(r"\\newcommand\{\\%s\}\[(\d)\]\{%%\n(.*?)\n\n" % name, PREAMBLE + "\n\n", re.S)
        self.assertIsNotNone(m, "\\%s is not defined" % name)
        return int(m.group(1)), m.group(2)

    def test_the_two_new_chunks(self):
        self.assertEqual(self.macro("chw")[0], 6)
        self.assertEqual(self.macro("chrw")[0], 7)
        self.assertIn("\\FrankNeedWords{\\chw}{\\ch}{#2}{#6}", self.macro("chw")[1])
        self.assertIn("\\FrankNeedWords{\\chrw}{\\chr}{#2}{#7}", self.macro("chrw")[1])
        # the pass-1 copy is appended unexpanded, never with \xappto
        for name, words in (("chw", "#6"), ("chrw", "#7")):
            body = self.macro(name)[1]
            self.assertIn("\\FrankVocAppend{#1}{\\FrankWords{#2}{%s}}" % words, body)
            self.assertNotIn("\\xappto\\FrankVocBuf", body)
            self.assertIn("\\FrankChunkRow{\\FrankWords{#2}{%s}}" % words, body)

    def test_every_chunk_feeds_the_reading_pass(self):
        want = {"ch": "{}{#3}{#2}", "chr": "{#3}{#4}{#2}", "chp": "{}{}{#2}",
                "chw": "{}{#3}{#2}", "chrw": "{#3}{#4}{#2}"}
        for name, args in want.items():
            with self.subTest(macro=name):
                self.assertIn("\\FrankAloudAppend" + args, self.macro(name)[1])
        self.assertIn("\\gdef\\FrankAloudBuf{}", PREAMBLE)
        self.assertIn("\\FrankVocalPass\n  \\ifFrankHasAloud\\FrankAloudPass\\fi\n", PREAMBLE)
        self.assertEqual(PREAMBLE.count("dofile("), 1)

    def test_language_files(self):
        ja = read(os.path.join(LIB, "lang", "ja.tex"))
        zh = read(os.path.join(LIB, "lang", "zh.tex"))
        for code in ("ja", "zh"):
            self.assertEqual(newlang.tex_switches(code), {"Bare": True, "Aloud": True, "Vert": True})
        self.assertIn("\\newcommand{\\FrankRuby}[2]", zh)
        self.assertIn("\\newcommand{\\FrankAloudText}[1]{\\FrankRoman{#1}}", zh)
        for text in (ja, zh):
            self.assertIn("Every passage comes five times.", text)


class Reader(unittest.TestCase):
    """The reading pass in the built reader: a p5 block right after each p1,
    its own toggle, and nothing at all in a language without words."""

    def build(self, rel):
        td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, td, True)
        d = os.path.join(td, os.path.basename(rel))
        shutil.copytree(os.path.join(BOOKS, rel), d,
                        ignore=shutil.ignore_patterns("reader", "*.pdf", "*.log", "*.aux",
                                                      "*.toc", "*.out"))
        # the copy's main.tex keeps the relative \FrankLib, which the reader
        # does not read
        rc, out = run([sys.executable, os.path.join(LIB, "tex2html.py"), "--book", d], cwd=d)
        self.assertEqual(rc, 0, out[-1500:])
        return read(os.path.join(d, "reader", "index.html"))

    def test_words_languages(self):
        import texparse as T
        for rel, code in (("japanese/mini-ja", "ja"), ("chinese/mini-zh", "zh")):
            with self.subTest(code=code):
                html = self.build(rel)
                p1 = html.count('<div class="pass p1"')
                self.assertGreater(p1, 0)
                self.assertEqual(html.count('<div class="pass p5"'), p1)
                self.assertEqual(len(re.findall(r'<div class="pass p1"[^>]*>.*?</div>\n'
                                                r'<div class="pass p5"', html, re.S)), p1)
                self.assertIn('<button data-toggle="no5" title="the reading alone, in', html)
                self.assertIn("body.no5 .p5{display:none}", html)
                # Hover mode brings the text passes back -- but not over a
                # toggle switched off WHILE it is on: reading the hoverable
                # text alone is exactly what the others are turned off for.
                self.assertIn("body.hovermode:not(.no5) .p5{display:block}", html)
                # and the toggles come out as one group, named once for the
                # group rather than each button explaining itself
                self.assertIn('<span class="pgrp"', html)
                self.assertIn('which passes you see', html)
                self.assertIn('title="the text alone (passes 1, 2 and 4)', html)
                L = languages.get(code)
                chs = T.parse_book(os.path.join(BOOKS, rel, "main.tex"))
                first = chs[0].subs[0].chunks[0]
                said = W.aloud(first.kana if L.reading else first.tr, first.fa)
                self.assertIn('<span class="w" data-c="0">%s</span>' % said, html)
        self.assertIn("cóngqián，", said)

    def test_a_language_without_words(self):
        html = self.build("persian/mini-fa")
        self.assertNotIn('class="pass p5"', html)
        self.assertNotIn('data-toggle="no5"', html)
        self.assertIn('title="the text alone (passes 1 and 3)', html)


JA_WORDS = {"山へ柴刈りに、": "山(やま) へ 柴刈り(しばかり) に 、",
            "住んでいました。": "住んでいました(すんでいました) 。",
            "むかしむかし、": "むかし むかし 、"}
ZH_WORDS = {"从前，": "从前(cóngqián) ，",
            "有一个小村子。": "有(yǒu) 一个(yí ge) 小(xiǎo) 村子(cūnzi) 。"}


def flat(txt):
    """pdftotext's words run together: a line may break anywhere in kana, and
    a page's number may fall inside a pass."""
    return re.sub(r"[\s0-9]", "", txt)


@unittest.skipUnless(os.environ.get("PARSEH_PDF") and shutil.which("lualatex"),
                     "PARSEH_PDF=1 and lualatex run the PDF builds")
class Pdf(unittest.TestCase):
    """lualatex as build.sh runs it, over copies of the two fixture editions
    with a few chunks given their words by hand."""

    def build(self, rel, words, name, flow=False, rewrite=None):
        td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, td, True)
        d = os.path.join(td, name)
        shutil.copytree(os.path.join(BOOKS, rel), d,
                        ignore=shutil.ignore_patterns("reader", "*.pdf", "*.log", "*.aux",
                                                      "*.toc", "*.out"))
        main = os.path.join(d, "main.tex")
        s = read(main)
        s = re.sub(r"\\newcommand\{\\FrankLib\}\{[^}]*\}",
                   lambda m: "\\newcommand{\\FrankLib}{%s}" % LIB, s)
        if flow:                                         # the inline-gloss layout
            s = s.replace("\\input{\\FrankLib/frank-preamble.tex}",
                          "\\input{\\FrankLib/frank-preamble.tex}\n\\FrankFlowtrue")
        write(main, s)
        ch = os.path.join(d, "ch1.tex")
        lines = []
        for ln in read(ch).split("\n"):
            m = re.match(r"\\(chr|ch)\{\}\{([^}]*)\}", ln)
            if m and m.group(2) in words:
                ln = "\\%sw%s{%s}" % (m.group(1), ln[len(m.group(1)) + 1:], words[m.group(2)])
            lines.append(ln)
        write(ch, "\n".join(rewrite(lines) if rewrite else lines))
        osf = "%s/fonts:/usr/share/fonts:/usr/local/share/fonts:%s/.local/share/fonts" % (
            LIB, os.path.expanduser("~"))
        run(["lualatex", "-interaction=nonstopmode", "main.tex"], cwd=d, env={"OSFONTDIR": osf})
        log = read(os.path.join(d, "main.log"))
        txt = ""
        if os.path.exists(os.path.join(d, "main.pdf")) and shutil.which("pdftotext"):
            txt = run(["pdftotext", os.path.join(d, "main.pdf"), "-"])[1]
        return log, txt

    def clean(self, log):
        bang = [l for l in log.splitlines() if l.startswith("!")]
        lua = [l for l in log.splitlines() if l.startswith("[\\directlua]") or "attempt to " in l]
        self.assertIn("Output written on", log)
        self.assertEqual(bang + lua, [])

    def test_japanese(self):
        log, txt = self.build("japanese/mini-ja", JA_WORDS, "mini-ja")
        self.clean(log)
        self.assertIn("やまへしばかりに、", flat(txt))     # the kana alone, its 、 given back
        self.assertIn("いきました。", flat(txt))           # a \chr's reading, in the same pass

    def test_chinese(self):
        log, txt = self.build("chinese/mini-zh", ZH_WORDS, "mini-zh")
        self.clean(log)
        self.assertIn("cūnzi。", flat(txt))

    def test_japanese_flow_and_a_chw(self):
        """The inline layout, and a Japanese chunk with words and no kana:
        its reading pass gives back its text."""
        def chw(lines):
            return [re.sub(r"^\\chr\{\}\{川へ洗濯に\}\{[^}]*\}(.*)$",
                           lambda m: "\\chw{}{川へ洗濯に}%s{川 へ 洗濯 に}" % m.group(1), ln)
                    for ln in lines]
        log, txt = self.build("japanese/mini-ja", JA_WORDS, "mini-ja-flow", flow=True, rewrite=chw)
        self.clean(log)
        self.assertIn("やまへしばかりに、おばあさんは川へ洗濯にいきました。", flat(txt))

    def test_chinese_flow_a_chrw_and_an_escape(self):
        """The inline layout, a \\chrw in a language with no reading (its tr is
        the pass's), and a chunk closing on 50\\% -- a percent in the reading
        pass, not a backslash and a percent."""
        def crossed(lines):
            out = []
            for ln in lines:
                m = re.match(r"^\\ch\{\}\{从前，\}(.*)$", ln)
                if m:
                    ln = "\\chrw{}{从前，}{}%s{从前(cóngqián) ，}" % m.group(1)
                out.append(ln)
                if "{有一个小村子。}" in ln:
                    out.append("\\ch{}{占50\\%。}{zhàn wǔshí}{}{half of it.}")
            return out
        words = {"有一个小村子。": ZH_WORDS["有一个小村子。"]}
        log, txt = self.build("chinese/mini-zh", words, "mini-zh-flow", flow=True, rewrite=crossed)
        self.clean(log)
        self.assertIn("cóngqián，", flat(txt))
        self.assertIn("zhànwǔshí%。", flat(txt))
        self.assertNotIn("\\%", txt)

    def test_blank_words_is_refused(self):
        log, _ = self.build("chinese/mini-zh", {"从前，": ""}, "mini-zh-blank")
        self.assertIn("\\chw has blank words", log)
        self.assertIn("use \\ch, which is this chunk without words", log)
        log, _ = self.build("japanese/mini-ja", {"山へ柴刈りに、": ""}, "mini-ja-blank")
        self.assertIn("\\chrw has blank words", log)
        self.assertIn("use \\chr, which is this chunk without words", log)


if __name__ == "__main__":
    unittest.main()
