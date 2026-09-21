#!/usr/bin/env python3
"""The book pipeline's readers and checkers, on chunks that carry words.

    python3 tests/test_wordbook_parsers.py

\\chw{col}{fa}{tr}{voc}{en}{words} and \\chrw{col}{fa}{kana}{tr}{voc}{en}{words}
are \\ch and \\chr with a word line added LAST (lib/wordline.py).  The failure
worth a test is the silent one: a reader whose list of macro names misses one
of the two does not complain, it simply never sees the chunk -- texparse
loses it from the reader, verify_book reports a mismatch nobody can explain,
inject_parstart writes an empty incipit.  So every reader is made to count.

The fixture editions are copied to a scratch directory and edited there, a
few chunks of each rewritten with a word line; nothing under tests/fixtures/
is written.  Standard library only, and nothing here needs an analyzer, so
system python3 runs it.
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

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
sys.path.insert(0, LIB)
import books            # noqa: E402
import bundle           # noqa: E402
import inject_parstart  # noqa: E402
import texparse         # noqa: E402
import verify_book      # noqa: E402
import words as analyzers                                        # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures", "books")

# fixture -> {a chunk's fa: the word line it is given}.  Two chunks in the
# first paragraph, which check_batch and assemble are run on, and one in the
# second, so verify_book and inject_parstart see words in both.
WORDS = {
    "japanese/mini-ja": {
        "むかしむかし、": "むかし むかし 、",
        "山へ柴刈りに、": "山(やま) へ 柴刈り(しばかり) に 、",
        "大切に育てました。": "大切(たいせつ) に 育てました(そだてました) 。",
    },
    "chinese/mini-zh": {
        "从前，": "从前(cóngqián) ，",
        "有一个小村子。": "有(yǒu) 一(yí) 个(ge) 小(xiǎo) 村子(cūnzi) 。",
        "打水。": "打(dǎ) 水(shuǐ) 。",
    },
}
# a line of each language that cannot be set (the 、/， is missing, so the words
# do not rejoin the text), and one that can but is doubted (a word of
# characters with no reading, which the chunk's reading then disagrees with)
BAD = {"japanese/mini-ja": ("山へ柴刈りに、", "山(やま) へ 柴刈り(しばかり) に"),
       "chinese/mini-zh": ("从前，", "从前(cóngqián)")}
DOUBTED = {"japanese/mini-ja": ("山へ柴刈りに、", "山 へ 柴刈り(しばかり) に 、"),
           "chinese/mini-zh": ("从前，", "从前 ，")}


def with_words(tex, words):
    """The chapter with every chunk named in `words` rewritten as \\chw or
    \\chrw: the same arguments, and the word line after them."""
    out = []
    for line in tex.split("\n"):
        m = re.match(r"\\(chr|ch)\{", line)
        if m and inject_parstart.arg_at(line, 1) in words:
            line = "\\%sw%s{%s}" % (m.group(1), line[m.end() - 1:],
                                    words[inject_parstart.arg_at(line, 1)])
        out.append(line)
    return "\n".join(out)


def run(*args, cwd=None):
    p = subprocess.run([sys.executable] + list(args), cwd=cwd,
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


class WordBook(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.td = td.name

    def book(self, which, words=None, reorders=False):
        """A scratch copy of a fixture, its chapter given word lines.  Each
        copy gets its own directory, still named <folder>/<slug>."""
        self.copies = getattr(self, "copies", 0) + 1
        d = os.path.join(self.td, "copy%d" % self.copies, which)
        shutil.copytree(os.path.join(FIXTURES, which), d)
        ch = os.path.join(d, "ch1.tex")
        with open(ch, encoding="utf-8") as f:
            tex = f.read()
        with open(ch, "w", encoding="utf-8") as f:
            f.write(with_words(tex, WORDS[which] if words is None else words))
        if reorders:
            with open(os.path.join(d, "book.json"), encoding="utf-8") as f:
                meta = json.load(f)
            meta["reorders"] = True
            with open(os.path.join(d, "book.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False)
        return books.Book(d)

    def para0(self, b, **change):
        """Paragraph 0 in the annotator's JSON, "words" where a chunk has
        them; `change` maps a chunk's fa to the words it is given instead."""
        para = texparse.parse_book(b.main, b.lang)[0].paragraphs[0]
        sents = []
        for s in para.subs:
            out = []
            for c in s.chunks:
                d = {"fa": c.fa, "tr": c.tr, "voc": c.voc, "en": c.en}
                if c.kana:
                    d["kana"] = c.kana
                if c.fa in change:
                    d["words"] = change[c.fa]
                elif c.wordline:
                    d["words"] = c.wordline
                out.append(d)
            sents.append({"chunks": out})
        return {"idx": 0, "ch": 1, "ann": {"sentences": sents}}

    # --- the readers --------------------------------------------------------
    def test_texparse_reads_every_chunk(self):
        for which, words in WORDS.items():
            with self.subTest(which):
                plain = books.Book(os.path.join(FIXTURES, which))
                b = self.book(which)
                old = texparse.all_chunks(texparse.parse_book(plain.main, plain.lang))
                new = texparse.all_chunks(texparse.parse_book(b.main, b.lang))
                with open(os.path.join(b.dir, "ch1.tex"), encoding="utf-8") as f:
                    macro = "\\chrw{" if b.lang.reading else "\\chw{"
                    self.assertEqual(f.read().count(macro), len(words))
                self.assertEqual(len(new), len(old))
                for o, n in zip(old, new):
                    # every positional argument keeps its number
                    self.assertEqual((o.col, o.fa, o.kana, o.tr, o.voc, o.en, o.glossed, o.line),
                                     (n.col, n.fa, n.kana, n.tr, n.voc, n.en, n.glossed, n.line))
                    self.assertEqual(n.wordline, words.get(n.fa, ""))
                self.assertEqual(sum(1 for c in new if c.wordline), len(words))
                # the chunk's own split into words is still the language's
                self.assertEqual([c.words for c in old], [c.words for c in new])

    def test_texparse_refuses_a_blank_word_line(self):
        for which in WORDS:
            with self.subTest(which):
                fa = next(iter(WORDS[which]))
                b = self.book(which, words={fa: "  "})
                with self.assertRaises(ValueError) as e:
                    texparse.parse_book(b.main, b.lang)
                self.assertIn("without words", str(e.exception))

    def test_verify_book_reproduces_the_source(self):
        for which in WORDS:
            with self.subTest(which):
                b = self.book(which)
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    rc = verify_book.main(b.dir)
                self.assertEqual(rc, 0, out.getvalue())
                self.assertIn(" 0 mismatched", out.getvalue())

    def test_inject_parstart_reads_the_words_chunks(self):
        for which in WORDS:
            with self.subTest(which):
                b = self.book(which)
                path = os.path.join(b.dir, "ch1.tex")
                with open(path, encoding="utf-8") as f:
                    tex = f.read()
                want = re.findall(r"^\\parstart\{.*\}$", tex, re.M)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(re.sub(r"^\\parstart\{.*\}\n", "", tex, flags=re.M))
                added, kept = inject_parstart.process(path, b.lang, False)
                self.assertEqual((added, kept), (len(want), 0))
                with open(path, encoding="utf-8") as f:
                    got = re.findall(r"^\\parstart\{.*\}$", f.read(), re.M)
                self.assertEqual(got, want)
                self.assertTrue(all(not g.endswith("{}") for g in got), got)

    # --- the checkers -------------------------------------------------------
    def check_batch(self, b, pj):
        pp = os.path.join(self.td, "ch1_p00.json")
        with open(pp, "w", encoding="utf-8") as f:
            json.dump(pj, f, ensure_ascii=False)
        return run(os.path.join(LIB, "check_batch.py"), pp, "--book", b.dir, cwd=b.dir)

    def test_check_batch(self):
        for which in WORDS:
            with self.subTest(which):
                b = self.book(which)
                rc, out = self.check_batch(b, self.para0(b))
                self.assertEqual(rc, 0, out)
                self.assertIn("0 errors, 0 warnings", out)
                fa, line = BAD[which]
                rc, out = self.check_batch(b, self.para0(b, **{fa: line}))
                self.assertEqual(rc, 1, out)
                self.assertIn("ERROR words of %r: the words do not reproduce the text" % fa, out)
                rc, out = self.check_batch(b, self.para0(b, **{fa: ""}))
                self.assertEqual(rc, 1, out)
                self.assertIn("ERROR blank words for %r" % fa, out)
                # LaTeX's specials are wordline's to refuse, as a book's
                rc, out = self.check_batch(b, self.para0(b, **{fa: WORDS[which][fa] + " {x}"}))
                self.assertEqual(rc, 1, out)
                self.assertIn("LaTeX reads it as an instruction", out)
                fa, line = DOUBTED[which]
                rc, out = self.check_batch(b, self.para0(b, **{fa: line}))
                self.assertEqual(rc, 0, out)
                self.assertIn("warn  words of %r: " % fa, out)
                self.assertIn("has no reading", out)

    def test_check_batch_reads_reorders(self):
        for which in WORDS:
            with self.subTest(which):
                b = self.book(which, reorders=True)
                self.assertTrue(b.reorders)
                fa, line = DOUBTED[which]
                rc, out = self.check_batch(b, self.para0(b, **{fa: line}))
                self.assertEqual(rc, 0, out)
                self.assertIn("0 errors, 0 warnings", out)
        self.assertFalse(books.Book(os.path.join(FIXTURES, "japanese/mini-ja")).reorders)

    def assemble(self, b, pj):
        batch = os.path.join(self.td, "batch.json")
        with open(batch, "w", encoding="utf-8") as f:
            json.dump({"paragraphs": [pj]}, f, ensure_ascii=False)
        outtex = os.path.join(self.td, "out.tex")
        rc, out = run(os.path.join(LIB, "assemble.py"), batch,
                      os.path.join(b.source_dir, "src_ch1.json"), "1", outtex,
                      "--partial", "--book", b.dir, cwd=b.dir)
        with open(outtex, encoding="utf-8") as f:
            return rc, out, f.read(), outtex

    def test_assemble(self):
        for which, words in WORDS.items():
            with self.subTest(which):
                b = self.book(which)
                w, wo = ("\\chrw{", "\\chr{") if b.lang.reading else ("\\chw{", "\\ch{")
                # a line broken over two is written on one, and means the same
                fa = BAD[which][0]
                broken = words[fa].replace(" ", "\n", 1)
                rc, out, tex, path = self.assemble(b, self.para0(b, **{fa: broken}))
                self.assertEqual(rc, 0, out)
                self.assertIn("ALL PARAGRAPHS CLEAN", out)
                pj = self.para0(b)
                n_words = sum(1 for s in pj["ann"]["sentences"] for c in s["chunks"] if "words" in c)
                n_all = sum(len(s["chunks"]) for s in pj["ann"]["sentences"])
                self.assertEqual(tex.count(w) + tex.count(wo), n_all)
                # with the analyzers the chunks the batch left without words
                # are proposed theirs by assemble.py; without them, none are
                if analyzers.available(b.lang.code):
                    self.assertGreaterEqual(tex.count(w), n_words)
                else:
                    self.assertEqual(tex.count(w), n_words)
                back = texparse.all_chunks([texparse.parse_chapter(path, b.lang)])
                self.assertEqual(len(back), n_all)
                self.assertEqual({c.fa: c.wordline for c in back if c.fa in words},
                                 {k: v for k, v in words.items()
                                  if k in {c.fa for c in back}})
                # refused: a problem, in wordline's words
                bad_fa, line = BAD[which]
                rc, out, _tex, _ = self.assemble(b, self.para0(b, **{bad_fa: line}))
                self.assertEqual(rc, 1, out)
                self.assertIn("words of %r: the words do not reproduce the text" % bad_fa, out)
                self.assertIn("1 PROBLEMS", out)
                # doubted: printed, and the batch is clean
                d_fa, line = DOUBTED[which]
                rc, out, _tex, _ = self.assemble(b, self.para0(b, **{d_fa: line}))
                self.assertEqual(rc, 0, out)
                self.assertIn("ALL PARAGRAPHS CLEAN", out)
                self.assertIn("warn  words of %r: " % d_fa, out)

    def test_bundle(self):
        for which in WORDS:
            with self.subTest(which):
                b = self.book(which)
                data, _name = bundle.pack_book(b.dir)
                root = os.path.join(self.td, "toolbox-" + b.slug)
                os.makedirs(os.path.join(root, "books"))
                r = bundle.install(data, root=root)
                self.assertTrue(r["ok"], r)
                self.assertFalse([n for n in r["notes"] if "word lines" in n], r["notes"])
                fa, line = BAD[which]
                bad = self.book(which, words=dict(WORDS[which], **{fa: line}))
                shutil.rmtree(root)
                os.makedirs(os.path.join(root, "books"))
                data, _name = bundle.pack_book(bad.dir)
                with self.assertRaises(bundle.BundleError) as e:
                    bundle.install(data, root=root)
                self.assertIn("word line(s) cannot be set", str(e.exception))
                self.assertIn("ch1.tex line", str(e.exception))

    # --- the branches the fixture editions do not reach ----------------------
    def test_every_pattern_reads_both_w_forms(self):
        # the regexes themselves, on one line of each form: the fa is the
        # second argument whatever the name, and no name is lost
        import check_batch
        for line, name, fa in (
                ("\\chrw{}{山へ}{やまへ}{yama e}{}{to the hill}{山(やま) へ}", "rw", "山へ"),
                ("\\chw{}{从前，}{cóngqián}{}{once}{从前(cóngqián) ，}", "w", "从前，")):
            with self.subTest(name):
                self.assertEqual(check_batch.CHUNK_RE.findall(line), [(name, "", fa)])
                self.assertEqual(verify_book.CHUNK_RE.findall(line), [("", fa)])
                self.assertTrue(inject_parstart.CHUNK.match(line))
                self.assertEqual(inject_parstart.arg_at(line, 1), fa)

    def test_texparse_a_line_over_two_lines_and_a_missing_one(self):
        def chapter(body):
            p = os.path.join(self.td, "ch1.tex")
            with open(p, "w", encoding="utf-8") as f:
                f.write("\\chapopen{1}\n\\parnum{1.1}\n\\begin{frank}\n%s\n"
                        "\\end{frank}\n\\chapend\n" % body)
            return texparse.parse_chapter(p, "zh")
        c = chapter("\\chw{}{从前，}{cóngqián}{}{once}{从前(cóngqián)\n ，}\n"
                    "\\ch{}{有}{yǒu}{}{there is}")
        self.assertEqual([(x.fa, x.wordline, x.en) for x in c.subs[0].chunks],
                         [("从前，", "从前(cóngqián)\n ，", "once"), ("有", "", "there is")])
        # a \chw without its word line must not take the next chunk's
        # colour for it and carry on: it stops, as a short \ch always has
        with self.assertRaises((AssertionError, ValueError)):
            chapter("\\chw{}{从前，}{cóngqián}{}{once}\n\\ch{}{有}{yǒu}{}{there is}")

    def test_check_batch_words_that_are_no_line(self):
        for which in WORDS:
            with self.subTest(which):
                b = self.book(which)
                fa = BAD[which][0]
                rc, out = self.check_batch(b, self.para0(b, **{fa: None}))
                self.assertEqual(rc, 1, out)
                self.assertIn("ERROR blank words for %r" % fa, out)
                rc, out = self.check_batch(b, self.para0(b, **{fa: [fa]}))
                self.assertEqual(rc, 1, out)
                self.assertIn("ERROR words of %r: words must be text" % fa, out)
        # a language with no word layer carries no words at all
        b = self.book("persian/mini-fa", words={})
        fa = texparse.parse_book(b.main, b.lang)[0].paragraphs[0].subs[0].chunks[0].fa
        rc, out = self.check_batch(b, self.para0(b, **{fa: fa}))
        self.assertNotEqual(rc, 0, out)
        self.assertIn("ERROR words of %r: Persian has no word layer" % fa, out)

    def test_check_batch_draft_still_refuses_a_line(self):
        # a draft forgives an unwritten GLOSS; a word line the PDF cannot set
        # is not a gloss, and stays an error
        for which in WORDS:
            with self.subTest(which):
                b = self.book(which)
                meta = dict(b.meta, draft=True)
                with open(os.path.join(b.dir, "book.json"), "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False)
                b = books.Book(b.dir)
                fa, line = BAD[which]
                pj = self.para0(b, **{fa: line})
                for c in (c for s in pj["ann"]["sentences"] for c in s["chunks"]):
                    if c["fa"] == fa:
                        c.update(tr="", voc="", en="", kana="")
                rc, out = self.check_batch(b, pj)
                self.assertEqual(rc, 1, out)
                self.assertIn("ERROR words of %r: the words do not reproduce" % fa, out)
                self.assertIn("have no gloss written yet", out)

    def test_assemble_blank_words_and_the_warning_count(self):
        for which in WORDS:
            with self.subTest(which):
                b = self.book(which)
                fa = BAD[which][0]
                rc, out, tex, _ = self.assemble(b, self.para0(b, **{fa: "  "}))
                self.assertEqual(rc, 1, out)
                self.assertIn("blank words for %r" % fa, out)
                # never a w-macro with nothing in it, which nothing can read
                line = next(l for l in tex.split("\n") if "{%s}" % fa in l and l.startswith("\\ch"))
                self.assertTrue(line.startswith("\\chr{" if b.lang.reading else "\\ch{"), line)
                d_fa, d_line = DOUBTED[which]
                rc, out, _tex, _ = self.assemble(b, self.para0(b, **{d_fa: d_line}))
                self.assertEqual(rc, 0, out)
                self.assertRegex(out, r"P0 .*  OK  \(\d+ warning\(s\)\)")

    def test_bundle_installs_a_doubted_line_with_a_note(self):
        for which in WORDS:
            with self.subTest(which):
                fa, line = DOUBTED[which]
                b = self.book(which, words=dict(WORDS[which], **{fa: line}))
                data, _name = bundle.pack_book(b.dir)
                root = os.path.join(self.td, "toolbox-doubted-" + b.slug)
                os.makedirs(os.path.join(root, "books"))
                r = bundle.install(data, root=root)
                self.assertTrue(r["ok"], r)
                self.assertTrue([n for n in r["notes"] if "warning(s) on the word lines" in n],
                                r["notes"])


if __name__ == "__main__":
    unittest.main()
