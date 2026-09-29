# SPDX-License-Identifier: GPL-3.0-or-later
"""A video's vocabulary line in the books' macros: what checks it, how it is
cut and joined, and what an older Parseh makes of one.

    python3 -m unittest tests/test_video_macros.py

The two renderers of such a line, held equal, are tests/test_vocline.py's.  A
line with none of the six openings (\\dw{ \\vb{ \\bw{ \\pw{ \\textit{ \\emph{)
is plain text and every check here says it is looked at as it always was.
Standard library only.
"""
import copy
import glob
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "youtube" / "lib"))
import annwrite as A            # noqa: E402
import check_annotations as CA  # noqa: E402
import chunkdiv                 # noqa: E402
import languages                # noqa: E402

VIDEOS = sorted(glob.glob(str(ROOT / "tests" / "fixtures" / "videos" / "*" / "*" / "video.json")))
PERSIAN = ROOT / "tests" / "fixtures" / "videos" / "persian" / "fA6bK2mQ8sT"


def errors_of(voc, code="fa"):
    """What check_chunk says about a chunk holding this vocabulary line."""
    errs, warns = [], []
    ch = {"fa": "سلام", "tr": "salām", "en": "hello", "voc": voc}
    CA.check_chunk(ch, "segment 1 chunk 0", errs.append, warns.append, code)
    return errs


class Checking(unittest.TestCase):
    """check_annotations.check_chunk: a macro line is a book's line, minus what only LaTeX minds."""

    def test_a_plain_line_is_checked_as_it_always_was(self):
        for voc in ("سلام salām hello (peace)", "a\\b c", "100% & _ # $ ^ ~ { }", "\\nobreak alone",
                    "\\foo{x} is not a macro line: nothing opens with one of the six",
                    "\\dw {a}{b} a space before the brace does not open a macro"):
            with self.subTest(voc=voc):
                self.assertEqual(errors_of(voc), [])

    def test_a_good_macro_line_is_accepted(self):
        for voc in ("\\dw{کتاب}{ketāb} book; \\dw{قلم}{qalam} pen",
                    "\\vb{دیدن}{didan}{بین}{bin}{دید}{did}{to see}",
                    "\\vb{زدن}{zadan}{زن}{zan}{زد}{zad}{}\\bw{لبخند}{labxand}{to smile}",
                    "\\vb{a}{}{}{}{}{}{a (\\pw{b} \\textit{c}; \\emph{d})}",
                    "\\pw{a} \\nobreak b \\, c \\\\ d",
                    "\\dw{a} {b} whitespace between two groups is read, so it is accepted",
                    "\\dw{a}\n{b} and so is a newline"):
            with self.subTest(voc=voc):
                self.assertEqual(errors_of(voc), [])

    def test_the_specials_of_tex_are_not_refused(self):
        """A book's line may not hold them because LaTeX reads them as
        instructions; a video's never reaches LaTeX."""
        for ch in "%&#_$^~":
            with self.subTest(special=ch):
                self.assertEqual(errors_of("\\dw{a}{b} 100%s 5 %s 3 a%sb" % (ch, ch, ch)), [])

    def test_another_macro_is_refused_in_words(self):
        errs = errors_of("\\dw{a}{b} \\includegraphics{x} \\textbf{y}")
        self.assertEqual(len(errs), 1)
        self.assertIn("segment 1 chunk 0", errs[0])
        self.assertIn("\\includegraphics, \\textbf", errs[0])
        self.assertIn("not one of the books' vocabulary macros", errs[0])
        for m in ("\\bw", "\\dw", "\\emph", "\\nobreak", "\\pw", "\\textit", "\\vb"):
            self.assertIn(m, errs[0], "the line says what it may hold")
        self.assertIn("\\foo, which is not", errors_of("\\pw{a} \\foo")[0])

    def test_braces_that_do_not_balance_are_refused_in_words(self):
        self.assertIn("leaves 1 brace open", "; ".join(errors_of("\\dw{a}{b")))
        self.assertIn("leaves 2 braces open", "; ".join(errors_of("\\dw{a}{b \\pw{c")))
        self.assertIn("closes a brace it never opened", "; ".join(errors_of("\\dw{a}{b}} c")))
        # an escaped brace is a character, not a brace
        self.assertEqual(errors_of("\\dw{a}{b \\{ c}"), [])

    def test_a_macro_short_of_its_groups_is_refused_in_words(self):
        self.assertEqual(len(errors_of("\\vb{a}{b}{c}")), 1)
        self.assertIn("\\vb needs 7 groups in braces and has 3", errors_of("\\vb{a}{b}{c}")[0])
        self.assertIn("\\dw needs 2 groups in braces and has 1", errors_of("\\dw{a} b")[0])
        self.assertIn("\\bw needs 3 groups in braces and has 2", errors_of("\\bw{a}{b} the phrase")[0])
        self.assertIn("\\textit needs 1 group in braces and has 0", errors_of("\\pw{a} \\textit x")[0])
        self.assertIn("\\pw needs 1 group in braces and has 0", errors_of("\\dw{a}{b} \\pw x")[0])
        # every one said once, whatever their number
        self.assertEqual(len(errors_of("\\dw{a} \\dw{b} \\dw{c}")), 1)

    def test_it_says_so_through_the_whole_checker_and_through_the_editor(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / PERSIAN.name
            shutil.copytree(PERSIAN, d)
            ann = json.loads((d / "annotations.json").read_text(encoding="utf-8"))
            si, ci = first_chunk(ann)
            bad = copy.deepcopy(ann)
            bad["segments"][si]["chunks"][ci]["voc"] = "\\dw{a}{b} \\foo{x}"
            errs = []
            CA.check_segments(bad["segments"], None, errs.append, lambda w: None, "fa",
                              half=lambda m: None)
            self.assertEqual(len(errs), 1)
            self.assertIn("\\foo", errs[0])
            # the editor refuses it, writes nothing, and takes a good line
            before = (d / "annotations.json").read_bytes()
            with self.assertRaises(ValueError) as e:
                A.edit_chunk(str(d), si, ci, {"voc": "\\dw{a}{b} \\foo{x}"})
            self.assertIn("\\foo", str(e.exception))
            self.assertEqual((d / "annotations.json").read_bytes(), before)
            A.edit_chunk(str(d), si, ci, {"voc": "\\dw{a}{b} what it means"})
            self.assertEqual(json.loads((d / "annotations.json").read_text(encoding="utf-8"))
                             ["segments"][si]["chunks"][ci]["voc"], "\\dw{a}{b} what it means")


def first_chunk(ann, words=1, lang="fa"):
    """(segment, chunk) of the first chunk with at least `words` words."""
    L = languages.get(lang)
    for si, sg in enumerate(ann["segments"]):
        for ci, ch in enumerate(sg.get("chunks") or []):
            if len(L.split_words(ch.get("fa") or "")) >= words:
                return si, ci
    raise AssertionError("no chunk with %d words" % words)


class Cutting(unittest.TestCase):
    """lib/chunkdiv.py: the style is a line's own, and cut then joined gives back what was taken."""

    FA = languages.get("fa")

    def test_which_lines_are_macro_lines(self):
        for m in ("\\dw{", "\\vb{", "\\bw{", "\\pw{", "\\textit{", "\\emph{"):
            self.assertTrue(chunkdiv.is_macro_line("a " + m + "b} c"), m)
        for plain in ("", "a · b", "a; b", "\\nobreak", "\\dw {a}{b}", "\\foo{x}", None, 3):
            self.assertFalse(chunkdiv.is_macro_line(plain), repr(plain))

    def test_a_macro_line_is_cut_tex_style_and_a_plain_one_plain(self):
        macro = {"fa": "کتاب قلم", "voc": "\\dw{کتاب}{ketāb} book; \\dw{قلم}{qalam} pen"}
        plain = {"fa": "کتاب قلم", "voc": "کتاب ketāb book · قلم qalam pen"}
        a, b, _ = chunkdiv.split(macro, 4, self.FA, chunkdiv.AUTO)
        self.assertEqual((a["voc"], b["voc"]), ("\\dw{کتاب}{ketāb} book", "\\dw{قلم}{qalam} pen"))
        a, b, _ = chunkdiv.split(plain, 4, self.FA, chunkdiv.AUTO)
        self.assertEqual((a["voc"], b["voc"]), ("کتاب ketāb book", "قلم qalam pen"))
        self.assertEqual(chunkdiv.style_of(macro["voc"]), chunkdiv.TEX)
        self.assertEqual(chunkdiv.style_of(plain["voc"]), chunkdiv.PLAIN)
        self.assertEqual(chunkdiv.style_of(plain["voc"], chunkdiv.TEX), chunkdiv.TEX, "an explicit style is kept")

    def test_cut_then_joined_gives_back_what_was_taken_in_both_styles(self):
        for voc in ("\\dw{کتاب}{ketāb} book; \\dw{قلم}{qalam} pen",
                    "کتاب ketāb book · قلم qalam pen",
                    "\\vb{دیدن}{didan}{بین}{bin}{دید}{did}{to see}; \\dw{قلم}{qalam} pen",
                    "\\dw{کتاب}{ketāb} book; \\pw{قلم} pen: \\pw{a}; \\dw{b}{c} d",
                    "دیدن didan · pres. بین bin · past دید did · to see (a · b) · قلم qalam pen"):
            chunk = {"fa": "کتاب قلم", "tr": "ketāb qalam", "voc": voc, "en": "book pen"}
            for c in chunkdiv.cuts(chunk["fa"], self.FA):
                with self.subTest(voc=voc):
                    a, b, _ = chunkdiv.split(chunk, c["at"], self.FA, chunkdiv.AUTO)
                    one, _ = chunkdiv.merge(a, b, self.FA, chunkdiv.AUTO)
                    self.assertEqual(one["voc"], voc)

    def test_the_sides_follow_the_headwords_of_a_macro_line(self):
        chunk = {"fa": "کتاب قلم", "voc": "\\dw{کتاب}{ketāb} book; \\dw{قلم}{qalam} pen"}
        got = chunkdiv.entries_for(chunk, 4, self.FA, chunkdiv.AUTO)
        self.assertEqual(got, [{"text": "\\dw{کتاب}{ketāb} book", "side": "a"},
                               {"text": "\\dw{قلم}{qalam} pen", "side": "b"}])
        # a semicolon inside a group is text, and one before a word is inside an entry
        chunk["voc"] = "\\dw{کتاب}{ketāb} a; b; \\dw{قلم}{qalam} pen"
        got = chunkdiv.entries_for(chunk, 4, self.FA, chunkdiv.AUTO)
        self.assertEqual([e["text"] for e in got], ["\\dw{کتاب}{ketāb} a; b", "\\dw{قلم}{qalam} pen"])

    def test_two_lines_join_as_a_macro_line_when_either_is_one(self):
        both = chunkdiv.merge({"fa": "a", "voc": "\\dw{a}{b} c"}, {"fa": "d", "voc": "\\dw{d}{e} f"},
                              self.FA, chunkdiv.AUTO)[0]
        self.assertEqual(both["voc"], "\\dw{a}{b} c; \\dw{d}{e} f")
        one = chunkdiv.merge({"fa": "a", "voc": "a b"}, {"fa": "d", "voc": "\\dw{d}{e} f"},
                             self.FA, chunkdiv.AUTO)[0]
        self.assertEqual(one["voc"], "a b; \\dw{d}{e} f")
        plain = chunkdiv.merge({"fa": "a", "voc": "a b"}, {"fa": "d", "voc": "d e"},
                               self.FA, chunkdiv.AUTO)[0]
        self.assertEqual(plain["voc"], "a b · d e")
        with self.assertRaises(ValueError):
            chunkdiv.merge({"fa": "a"}, {"fa": "b"}, self.FA, "nonsense")

    def test_every_plain_video_is_cut_and_joined_exactly_as_it_was(self):
        """Every chunk of every fixture video holds a plain line, so AUTO is
        what PLAIN always was: every cut, every join and every chip."""
        n = 0
        for fx in VIDEOS:
            d = Path(fx).parent
            L = languages.get_or_default(json.loads(Path(fx).read_text(encoding="utf-8")).get("language"))
            ann = json.loads((d / "annotations.json").read_text(encoding="utf-8"))
            for sg in ann["segments"]:
                chunks = [c for c in (sg.get("chunks") or []) if isinstance(c, dict)]
                for k, ch in enumerate(chunks):
                    self.assertFalse(chunkdiv.is_macro_line(ch.get("voc")), "a fixture video's line is plain")
                    for c in chunkdiv.cuts(ch.get("fa") or "", L):
                        n += 1
                        self.assertEqual(chunkdiv.split(ch, c["at"], L, chunkdiv.AUTO),
                                         chunkdiv.split(ch, c["at"], L, chunkdiv.PLAIN))
                        self.assertEqual(chunkdiv.entries_for(ch, c["at"], L, chunkdiv.AUTO),
                                         chunkdiv.entries_for(ch, c["at"], L, chunkdiv.PLAIN))
                    if k + 1 < len(chunks) and bool(ch.get("plain")) == bool(chunks[k + 1].get("plain")):
                        self.assertEqual(chunkdiv.merge(ch, chunks[k + 1], L, chunkdiv.AUTO),
                                         chunkdiv.merge(ch, chunks[k + 1], L, chunkdiv.PLAIN))
        self.assertGreater(n, 50, "a good many places to cut were tried")


class InAVideo(unittest.TestCase):
    """youtube/lib/annwrite.py over a real copy of the Persian fixture video."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.dir = Path(self.td.name) / PERSIAN.name
        shutil.copytree(PERSIAN, self.dir)
        self.ann = json.loads((self.dir / "annotations.json").read_text(encoding="utf-8"))
        self.si, self.ci = first_chunk(self.ann, words=2)
        self.fa = self.ann["segments"][self.si]["chunks"][self.ci]["fa"]
        self.words = languages.get("fa").split_words(self.fa)

    def bytes(self):
        return (self.dir / "annotations.json").read_bytes()

    def test_the_divide_sheet_is_told_the_separator_of_the_line_it_cuts(self):
        A.edit_chunk(str(self.dir), self.si, self.ci, {"voc": "\\dw{%s}{a} x; \\dw{%s}{b} y" % tuple(self.words[:2])})
        p = A.divide_preview(str(self.dir), self.si, self.ci)
        self.assertEqual(p["voc_sep"], "; ")
        self.assertEqual([e["side"] for e in p["cuts"][0]["entries"]], ["a", "b"])
        A.edit_chunk(str(self.dir), self.si, self.ci, {"voc": "%s a · %s b" % tuple(self.words[:2])})
        p = A.divide_preview(str(self.dir), self.si, self.ci)
        self.assertEqual(p["voc_sep"], " · ")
        self.assertEqual([e["side"] for e in p["cuts"][0]["entries"]], ["a", "b"])
        A.edit_chunk(str(self.dir), self.si, self.ci, {"voc": ""})
        self.assertEqual(A.divide_preview(str(self.dir), self.si, self.ci)["voc_sep"], " · ",
                         "no line, no macro: the separator a video always had")

    def test_cut_then_joined_the_file_is_the_file_it_was_in_both_styles(self):
        for voc in ("\\dw{%s}{a} x; \\dw{%s}{b} y" % tuple(self.words[:2]),
                    "\\vb{%s}{a}{c}{d}{e}{f}{to see}; \\pw{%s} y" % tuple(self.words[:2]),
                    "%s a · %s b" % tuple(self.words[:2])):
            with self.subTest(voc=voc):
                A.edit_chunk(str(self.dir), self.si, self.ci, {"voc": voc})
                before = self.bytes()
                p = A.divide_preview(str(self.dir), self.si, self.ci)
                cut = p["cuts"][0]
                A.split_chunk(str(self.dir), self.si, self.ci, cut["first"], cut["second"])
                self.assertNotEqual(self.bytes(), before)
                A.merge_chunks(str(self.dir), self.si, self.ci)
                self.assertEqual(self.bytes(), before)

    def test_a_macro_line_survives_the_editor_untouched(self):
        line = "\\vb{a}{b}{c}{d}{e}{f}{to see (\\pw{x} \\textit{y})}; \\dw{g}{h} i"
        A.edit_chunk(str(self.dir), self.si, self.ci, {"voc": "  " + line + "  "})
        got = json.loads(self.bytes().decode("utf-8"))["segments"][self.si]["chunks"][self.ci]["voc"]
        self.assertEqual(got, line, "trimmed, and nothing else done to it")


class Wiring(unittest.TestCase):
    """A door written is not a door reachable: the two scripts are served, kept for a phone and linked."""

    def test_the_two_scripts_are_served_kept_and_linked(self):
        import offline
        import serve
        for name in ("vocline.js", "vocbuttons.js"):
            with self.subTest(name):
                self.assertTrue((ROOT / "lib" / name).is_file())
                self.assertIn("/lib/" + name, serve.STATIC_FILES, "only the files STATIC_FILES names are on the web")
                self.assertIn("/lib/" + name, offline.SHARED, "a kept video and a kept book open offline with it")
        player = (ROOT / "youtube" / "lib" / "player.html").read_text(encoding="utf-8")
        order = [player.index(s) for s in ('/lib/wordline.js', '/lib/vocline.js', '/lib/vocbuttons.js', '/lib/player.js')]
        self.assertEqual(order, sorted(order), "the player's page loads them before player.js, which reads them")
        # a reader, however old, gets both from beside parseh.js
        hub = (ROOT / "lib" / "parseh.js").read_text(encoding="utf-8")
        self.assertIn("['ParsehVocline', 'vocline.js'], ['ParsehVocButtons', 'vocbuttons.js']", hub)


class TheSidebarsEntry(unittest.TestCase):
    """lib/verbs: `tex_video`, the book's \\vb as a video's line takes it."""

    def compose(self, code, **kw):
        import verbs as V
        parts = dict(parts=[("گفتن", "goftan"), ("گو", "gu"), ("گفت", "goft")],
                     meaning="to say", extras_video=[])
        parts.update(kw.pop("parts", {}))
        return V.compose(code, V.Parts(**parts), **kw)

    def test_the_videos_extras_go_inside_the_meanings_parenthesis(self):
        import verbs as V
        vb = self.compose("fa", parts=dict(extras_video=["coll. " + V.tl("می‌گم", "mi-gam")]),
                          word="گفتن", meaning="to say")
        self.assertEqual(vb["tex"], "\\vb{گفتن}{goftan}{گو}{gu}{گفت}{goft}{to say}")
        self.assertEqual(vb["tex_video"],
                         "\\vb{گفتن}{goftan}{گو}{gu}{گفت}{goft}{to say (coll. \\pw{می‌گم} \\textit{mi-gam})}")
        # the books' extras and the video's share the one parenthesis
        vb = self.compose("it", parts=dict(parts=[("andare", ""), ("vado", ""), ("andato", "")],
                                           extras=["aux. " + V.tl("essere")], meaning="to go",
                                           extras_video=["coll. " + V.tl("vo")]))
        self.assertIn("{to go (aux. \\pw{essere}; coll. \\pw{vo})}", vb["tex_video"])
        self.assertIn("{to go (aux. \\pw{essere})}", vb["tex"])

    def test_the_chunks_own_form_follows_the_entry_as_the_books_name_it(self):
        vb = self.compose("fa", word="گفتم", of_form="goftam")
        self.assertEqual(vb["tex_video"], vb["tex"] + "; here \\pw{گفتم} \\textit{goftam}")
        vb = self.compose("fa", word="گفتم")
        self.assertEqual(vb["tex_video"], vb["tex"] + "; here \\pw{گفتم}", "no sound, none named")
        for said in ("گفتن", "گو", "گفت", "گَفت"):
            with self.subTest(word=said):
                vb = self.compose("fa", word=said, of_form="x")
                self.assertEqual(vb["tex_video"], vb["tex"], "a form the \\vb already prints is not named")
        import verbs as V
        vb = self.compose("fa", parts=dict(extras=["coll. " + V.tl("می‌گم")]), word="می‌گم")
        self.assertNotIn("; here", vb["tex_video"], "nor a form its parenthesis names")
        self.assertEqual(self.compose("fa")["tex_video"], self.compose("fa", word="")["tex_video"])

    def test_an_arabic_verb_is_written_bare_as_a_video_writes_it(self):
        import verbs as V
        vb = V.compose("ar", V.Parts(parts=[("خَرَجَ", "ḫaraja (I)"), ("يَخْرُجُ", "yaḫruju"), ("خُرُوج", "ḫurūj")],
                                     meaning="to go out", extras=["+ " + V.tl("مِنْ")]),
                       word="خرجوا", of_form="ḫarajū")
        self.assertIn("\\vb{خَرَجَ}{ḫaraja (I)}{يَخْرُجُ}", vb["tex"], "the book's is vowelled")
        self.assertEqual(vb["tex_video"],
                         "\\vb{خرج}{ḫaraja (I)}{يخرج}{yaḫruju}{خروج}{ḫurūj}{to go out (+ \\pw{من})}"
                         "; here \\pw{خرجوا} \\textit{ḫarajū}")
        # letter for letter one of the forms once the marks are off: nothing to name
        vb = V.compose("ar", V.Parts(parts=[("خَرَجَ", ""), ("يَخْرُجُ", ""), ("خُرُوج", "")]), word="خرج")
        self.assertNotIn("; here", vb["tex_video"])

    def test_a_compound_goes_in_as_one_entry_with_the_light_verbs_video_extras(self):
        import verbs as V
        vb = V.compose("fa", V.Parts(parts=[("کردن", "kardan"), ("کن", "kon"), ("کرد", "kard")], meaning="",
                                     extras_video=["coll. " + V.tl("می‌کنم", "mi-konam")],
                                     compound={"name": "compound verb", "whole": "فکر کردن", "whole_sound": "fekr kardan",
                                               "mean": "to think", "word": "فکر", "word_sound": "fekr"}),
                       word="فکر می‌کنم")
        cp = vb["compound"]
        self.assertEqual(cp["tex"], vb["tex"] + cp["bw"])
        self.assertEqual(cp["tex_video"],
                         "\\vb{کردن}{kardan}{کن}{kon}{کرد}{kard}{(coll. \\pw{می‌کنم} \\textit{mi-konam})}"
                         "\\bw{فکر}{fekr}{to think}")
        self.assertNotIn("; ", cp["tex_video"], "one entry, not two")

    def test_every_language_s_own_cases(self):
        """The eight cases of every recipe, each built into a dictionary of
        one entry (tests/fixtures/verbs/README.md): the video's entry is a
        book's \\vb, reads back as the line the video always had, and a
        video's own check takes it."""
        import lookup as lk
        import texparse
        import texwrite
        import verbs as V
        built = 0
        for code in languages.CODES:
            L = languages.get(code)
            path = ROOT / "tests" / "fixtures" / "verbs" / ("%s.json" % code)
            if not path.is_file():
                continue
            with tempfile.TemporaryDirectory() as td:
                for k, case in enumerate(json.loads(path.read_text(encoding="utf-8"))["cases"]):
                    vb = self.build(lk, V, td, code, k, case)
                    if not vb:
                        continue
                    built += 1
                    with self.subTest(code=code, case=k):
                        tex, head = vb["tex_video"], vb["tex_video"].split("; here ")[0]
                        texwrite._check_voc(tex, "%s case %d" % (code, k))
                        self.assertEqual(errors_of(tex, code), [])
                        if code not in ("fa", "ar"):
                            self.assertEqual(head, vb["tex"], "a video adds nothing to it here")
                        if not vb["reading"]:            # the kana a video prints after the headword
                            self.assertEqual(texparse.voc_text(head, L), vb["plain"])
                        if head != tex:
                            self.assertRegex(tex, r"; here \\pw\{[^{}]+\}( \\textit\{[^{}]+\})?$")
                        cp = vb.get("compound")
                        if cp:
                            self.assertEqual(cp["tex_video"], head + cp["bw"])
        self.assertGreater(built, 60, "the eight cases of every language")

    @staticmethod
    def build(lk, V, td, code, k, case):
        """One case as a dictionary of its own (smoke.py's _verb_case_dict), built."""
        d = os.path.join(td, "%s-%d" % (code, k))
        os.makedirs(d)
        c = lk.create(os.path.join(d, "%s.db" % code))
        e = case["entry"]
        cols = ("headword", "translit", "ipa", "reading", "pos", "sense", "sense_tags", "head")
        eid = c.execute("INSERT INTO entry (%s) VALUES (%s)" % (", ".join(cols), ",".join("?" * len(cols))),
                        [e.get(x) or "" for x in cols]).lastrowid
        for row in case["forms"]:
            form, note, roman, ipa = (list(row) + ["", "", ""])[:4]
            c.execute("INSERT INTO form (form, entry_id, note, roman, ipa) VALUES (?,?,?,?,?)",
                      (form, eid, note or "", roman or "", ipa or ""))
        c.commit()
        c.close()

        def forget():
            for conn, _stamp in (getattr(lk._CONNS, "map", None) or {}).values():
                try:
                    conn and conn.close()
                except Exception:
                    pass
            lk._CONNS.map = {}
            V.clear_cache()
        was = lk.DICT_DIR
        lk.DICT_DIR = d
        forget()
        try:
            return V.build(code, {"entry": eid, "headword": e["headword"], "pos": e.get("pos") or ""},
                           case.get("word") or "", case.get("text") or "", case.get("gloss") or "en")
        finally:
            lk.DICT_DIR = was
            forget()


if __name__ == "__main__":
    unittest.main()
