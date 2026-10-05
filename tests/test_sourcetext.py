# SPDX-License-Identifier: GPL-3.0-or-later
"""The one recovery of a file's text (lib/sourcetext.py): a PDF, an epub and a plain text file.

    python3 -m unittest tests/test_sourcetext.py

Every file here is generated, tiny, in a temporary tree: a plain text in several encodings, an epub
built with zipfile (a navigation document, a title, headings, a page number, three documents in its
spine) and a PDF drawn with PyMuPDF.  What is held: each kind comes out as paragraphs; an epub's
headings are reported and are not paragraphs; a page range is a PDF's alone and is counted from 0;
what cannot be read is refused in a sentence; and the numbering onto a book continues what the folder
holds (a new chapter, the last one, a chapter's number) and says when a part may be cut in the middle
of a paragraph.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for p in ("lib",):
    sys.path.insert(0, str(ROOT / p))
import sourcetext                                                  # noqa: E402

try:
    import pymupdf
except ImportError:                                                # an environment without it
    pymupdf = None

TWO = ["Il gatto dorme sul divano tutto il giorno.", "Il cane corre nel giardino con la palla."]
CHAPTER_1 = '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>x</title><style>p{}</style></head><body>' \
            "<h1>Capitolo primo</h1><p>Il gatto dorme <em>sul divano</em> tutto il giorno.</p>" \
            "<p>12</p><p>Il cane corre&nbsp;nel giardino con la palla.</p></body></html>"
CHAPTER_2 = '<html xmlns="http://www.w3.org/1999/xhtml"><body><h2>Capitolo secondo</h2>' \
            "<div><p>Poi arriva la sera.</p>una frase lasciata sola<p>E tutto tace.</p></div></body></html>"


def tmp(test):
    d = tempfile.mkdtemp(prefix="test-sourcetext-", dir=os.environ.get("TMPDIR") or None)
    test.addCleanup(shutil.rmtree, d, ignore_errors=True)
    return d


def write(test, name, data):
    path = os.path.join(tmp(test), name)
    with open(path, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))
    return path


def make_epub(test, documents=(CHAPTER_1, CHAPTER_2), name="a.epub", nav=True):
    path = os.path.join(tmp(test), name)
    manifest = "".join('<item id="d%d" href="text/c%d.xhtml" media-type="application/xhtml+xml"/>' % (i, i)
                       for i in range(len(documents)))
    if nav:
        manifest += '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
    spine = ('<itemref idref="nav"/>' if nav else "") + "".join('<itemref idref="d%d"/>' % i for i in range(len(documents)))
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", '<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                   '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        z.writestr("OEBPS/content.opf", '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0">'
                   "<manifest>%s</manifest><spine>%s</spine></package>" % (manifest, spine))
        z.writestr("OEBPS/nav.xhtml", "<html><body><nav><ol><li>Capitolo primo</li><li>Capitolo secondo</li></ol></nav></body></html>")
        for i, doc in enumerate(documents):
            z.writestr("OEBPS/text/c%d.xhtml" % i, doc)
    return path


def make_pdf(test, pages, name="a.pdf"):
    """One paragraph a page, drawn as a book's page is: the first line indented, the lines full, the
    last one short -- which is what lib/extract_pdf.py reads the paragraph structure from."""
    path = os.path.join(tmp(test), name)
    doc = pymupdf.open()
    for lines in pages:
        page = doc.new_page()
        for i, (x, text) in enumerate(lines):
            page.insert_text((x, 80 + 16 * i), text, fontsize=11)
    doc.save(path)
    doc.close()
    return path


# the full lines end within a point of one another (measured in Helvetica 11), so that only the last line is short
PAGE_A = [(92, "Il gatto dorme sul divano tutto il giorno e non si muove"),
          (72, "mai, nemmeno quando il cane abbaia forte alla porta e poi"), (72, "Si sveglia lentamente.")]
PAGE_B = [(92, "Il cane corre nel giardino con la palla rossa e salta sopra"),
          (72, "sopra la siepe bassa fino alla strada del paese vicino e poi si"), (72, "Tutti sono felici oggi.")]


class PlainText(unittest.TestCase):
    def test_blocks_between_blank_lines_are_the_paragraphs_and_a_blocks_lines_are_joined(self):
        path = write(self, "a.txt", "Il gatto dorme\nsul divano.\n\n\nIl cane\ncorre.\n\n")
        self.assertEqual(sourcetext.recover(path, "it"), ["Il gatto dorme sul divano.", "Il cane corre."])

    def test_with_no_blank_line_a_line_is_a_paragraph(self):
        path = write(self, "a.txt", "\n".join(TWO) + "\n")
        self.assertEqual(sourcetext.recover(path, "it"), TWO)

    def test_a_word_hyphenated_across_a_line_is_one_word_and_japanese_is_joined_with_nothing(self):
        self.assertEqual(sourcetext.recover(write(self, "a.txt", "Il gatto dor-\nme sul divano.\n\nFine.\n"), "it")[0],
                         "Il gatto dorme sul divano.")
        got = sourcetext.recover(write(self, "j.txt", "猫は寝て\nいます。\n\n犬は走る。\n"), "ja")
        self.assertEqual(got, ["猫は寝ています。", "犬は走る。"])

    def test_the_editions_own_spelling_is_kept_and_only_what_is_no_text_goes(self):
        # a Persian text: the Arabic kaf and ye are what the edition has, and the zero-width joiner is a letter's
        text = "كتاب می‌خواهم‎­\u0000\n"
        got = sourcetext.recover(write(self, "fa.txt", text), "fa")
        self.assertEqual(got, ["كتاب می‌خواهم"])

    def test_a_running_header_and_a_page_number_are_not_the_text(self):
        path = write(self, "a.txt", "IL GATTO\n\nIl gatto dorme sul divano.\n\n12\n\nIl cane corre nel giardino.\n")
        self.assertEqual(sourcetext.recover(path, "it", drop=["^IL GATTO$"]),
                         ["Il gatto dorme sul divano.", "Il cane corre nel giardino."])

    def test_a_byte_order_mark_utf_16_and_an_older_encoding_are_read_and_the_last_is_said(self):
        self.assertEqual(sourcetext.recover(write(self, "a.txt", b"\xef\xbb\xbf" + TWO[0].encode("utf-8")), "it"), [TWO[0]])
        self.assertEqual(sourcetext.recover(write(self, "b.txt", TWO[0].encode("utf-16")), "it"), [TWO[0]])
        info = {}
        got = sourcetext.recover(write(self, "c.txt", "Perché è così.\n".encode("cp1252")), "it", info=info)
        self.assertEqual(got, ["Perché è così."])
        self.assertTrue(any("cp1252" in w for w in info["warnings"]), info)

    def test_a_page_range_is_a_pdfs_alone_and_is_said_to_be_ignored(self):
        info = {}
        self.assertEqual(sourcetext.recover(write(self, "a.txt", "\n".join(TWO)), "it", pages=[0, 1], info=info), TWO)
        self.assertTrue(any("page range" in w and "ignored" in w for w in info["warnings"]), info)

    def test_what_cannot_be_read_is_refused_in_a_sentence(self):
        with self.assertRaisesRegex(sourcetext.SourceError, "no file"):
            sourcetext.recover(os.path.join(tmp(self), "nothing.txt"), "it")
        with self.assertRaisesRegex(sourcetext.SourceError, "first not after the last"):
            sourcetext.recover(write(self, "a.txt", "x y z"), "it", pages=[5, 2])


class Epub(unittest.TestCase):
    def test_the_spine_in_order_is_the_paragraphs_and_headings_are_reported_not_paragraphs(self):
        info = {}
        got = sourcetext.recover(make_epub(self), "it", info=info)
        self.assertEqual(got, ["Il gatto dorme sul divano tutto il giorno.", "Il cane corre nel giardino con la palla.",
                               "Poi arriva la sera.", "una frase lasciata sola", "E tutto tace."])
        self.assertEqual(info["headings"], [{"at": 0, "text": "Capitolo primo"}, {"at": 2, "text": "Capitolo secondo"}])
        self.assertEqual(info["documents"], [0, 2], "where each document of the spine begins")
        self.assertEqual(info["kind"], "epub")

    def test_the_navigation_document_is_not_a_chapter_and_a_page_number_is_not_text(self):
        got = sourcetext.recover(make_epub(self), "it")
        self.assertNotIn("Capitolo primo", " ".join(got))
        self.assertNotIn("12", got)

    def test_an_epub_that_is_not_one_is_refused_in_words(self):
        bad = make_epub(self)
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("hello.txt", "hi")
        with self.assertRaisesRegex(sourcetext.SourceError, "table of contents"):
            sourcetext.recover(bad, "it")
        with self.assertRaisesRegex(sourcetext.SourceError, "could not be opened"):
            sourcetext.recover(write(self, "x.epub", b"PK not a zip"), "it")

    def test_the_text_of_an_epub_in_every_language_of_the_registry_is_kept_letter_for_letter(self):
        import languages
        for code in languages.CODES:
            text = "مرحبا دنیا" if code in ("fa", "ar") else "Hello world"
            got = sourcetext.recover(make_epub(self, ['<html><body><p>%s</p></body></html>' % text], nav=False), code)
            self.assertEqual(got, [text], code)


@unittest.skipIf(pymupdf is None, "PyMuPDF is not installed here")
class Pdf(unittest.TestCase):
    def test_a_pdf_goes_through_extract_pdf_and_comes_out_as_paragraphs(self):
        got = sourcetext.recover(make_pdf(self, [PAGE_A, PAGE_B]), "it")
        self.assertEqual(len(got), 2, got)
        self.assertTrue(got[0].startswith("Il gatto dorme sul divano") and got[0].endswith("Si sveglia lentamente."), got)
        self.assertTrue(got[1].startswith("Il cane corre nel giardino"), got)

    def test_the_page_range_is_counted_from_zero_and_includes_its_last_page(self):
        path = make_pdf(self, [PAGE_A, PAGE_B])
        self.assertEqual(len(sourcetext.recover(path, "it", pages=[1, 1])), 1)
        self.assertTrue(sourcetext.recover(path, "it", pages=[1, 1])[0].startswith("Il cane corre"))
        self.assertTrue(sourcetext.recover(path, "it", pages=[0, 0])[0].startswith("Il gatto dorme"))
        self.assertEqual(len(sourcetext.recover(path, "it", pages=[0, 1])), 2)

    def test_a_pdf_with_no_text_says_so_and_a_damaged_one_is_refused(self):
        doc = pymupdf.open()
        doc.new_page()
        empty = os.path.join(tmp(self), "empty.pdf")
        doc.save(empty)
        info = {}
        self.assertEqual(sourcetext.recover(empty, "it", info=info), [])
        self.assertTrue(any("no text layer" in w for w in info["warnings"]), info)
        with self.assertRaisesRegex(sourcetext.SourceError, "PDF could not be read"):
            sourcetext.recover(write(self, "bad.pdf", b"%PDF-1.4\nnot really a pdf\n"), "it")


class Numbering(unittest.TestCase):
    def book(self, chapters):
        """A folder with source/paras for {chapter: paragraphs}."""
        d = tmp(self)
        os.makedirs(os.path.join(d, "source", "paras"))
        for n, count in chapters.items():
            for i in range(count):
                Path(d, "source", "paras", "ch%d_p%02d.txt" % (n, i)).write_text("Frase %d.%d finita.\n" % (n, i), encoding="utf-8")
        return d

    def run_cli(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            code = sourcetext.main(list(args))
        return code, out.getvalue()

    def test_place_continues_what_the_folder_holds(self):
        d = self.book({1: 3, 2: 2})
        self.assertEqual(sourcetext.place(d, "new"), (3, 0))
        self.assertEqual(sourcetext.place(d, "last"), (2, 2))
        self.assertEqual(sourcetext.place(d, 1), (1, 3))
        self.assertEqual(sourcetext.place(d, 9), (9, 0))
        empty = self.book({})
        self.assertEqual((sourcetext.place(empty, "new"), sourcetext.place(empty, "last")), ((1, 0), (1, 0)))

    def test_the_cli_writes_the_paragraphs_on_from_the_last_and_adds_to_clean_txt(self):
        d = self.book({1: 2})
        Path(d, "source", "clean.txt").write_text("Frase 1.0 finita.\nFrase 1.1 finita.\n", encoding="utf-8")
        part = write(self, "part.txt", "\n".join(TWO))
        code, said = self.run_cli(part, "--lang", "it", "--book", d, "--chapter", "new")
        self.assertEqual(code, 0, said)
        self.assertIn("wrote ch2, paragraphs 00-01: ch2_p00.txt ... ch2_p01.txt", said)
        self.assertEqual(Path(d, "source", "paras", "ch2_p01.txt").read_text(encoding="utf-8"), TWO[1] + "\n")
        self.assertEqual(Path(d, "source", "clean.txt").read_text(encoding="utf-8").splitlines()[-2:], TWO)
        code, said = self.run_cli(part, "--lang", "it", "--book", d, "--chapter", "last")
        self.assertIn("wrote ch2, paragraphs 02-03", said)
        self.assertEqual(sorted(os.listdir(os.path.join(d, "source", "paras")))[-1], "ch2_p03.txt")

    def test_a_part_cut_in_the_middle_of_a_paragraph_is_said_both_ways(self):
        d = self.book({1: 1})
        Path(d, "source", "paras", "ch1_p00.txt").write_text("Il gatto dorme sul divano e poi\n", encoding="utf-8")
        code, said = self.run_cli(write(self, "p.txt", "si sveglia lentamente.\n\nPoi mangia."), "--lang", "it", "--book", d)
        self.assertIn("starts with a lowercase letter", said)
        self.assertIn("ends without a full stop", said)
        d = self.book({1: 1})
        code, said = self.run_cli(write(self, "q.txt", "Poi mangia.\n"), "--lang", "it", "--book", d)
        self.assertNotIn("warning", said, "a part that starts a sentence after a sentence's end is nothing to look at")

    def test_look_says_what_is_there_and_where_it_would_go_and_writes_nothing(self):
        d = self.book({1: 2})
        Path(d, "source", "paras", "ch1_p01.txt").write_text("Il gatto dorme sul divano e poi\n", encoding="utf-8")
        before = sorted(os.listdir(os.path.join(d, "source", "paras")))
        for _ in range(2):                              # as often as it is asked: it changes nothing
            code, said = self.run_cli(write(self, "p.txt", "si sveglia lentamente.\n\nPoi mangia."), "--lang", "it",
                                      "--book", d, "--chapter", "last", "--look")
            self.assertEqual(code, 0, said)
        self.assertIn("2 paragraphs", said)
        self.assertIn("nothing written (--look): with --chapter last it would be ch1, paragraphs 02-03", said)
        self.assertIn("starts with a lowercase letter", said)
        self.assertEqual(sorted(os.listdir(os.path.join(d, "source", "paras"))), before)
        self.assertFalse(os.path.exists(os.path.join(d, "source", "clean.txt")))
        # and the same command without --look then writes it, where it said it would
        code, said = self.run_cli(write(self, "p.txt", "si sveglia lentamente.\n\nPoi mangia."), "--lang", "it",
                                  "--book", d, "--chapter", "last")
        self.assertIn("wrote ch1, paragraphs 02-03", said)

    def test_without_a_book_the_cli_writes_where_it_is_told_like_extract_pdf(self):
        out = os.path.join(tmp(self), "clean.txt")
        paras = os.path.join(tmp(self), "paras")
        code, said = self.run_cli(write(self, "p.txt", "\n".join(TWO)), "--lang", "it", "--out", out, "--paras", paras,
                                  "--tag", "ch7", "--start", "5")
        self.assertEqual(code, 0, said)
        self.assertEqual(sorted(os.listdir(paras)), ["ch7_p05.txt", "ch7_p06.txt"])
        self.assertEqual(Path(out).read_text(encoding="utf-8"), "\n".join(TWO) + "\n")

    def test_the_cli_refuses_in_words_and_leaves_the_book_alone(self):
        d = self.book({1: 1})
        err = io.StringIO()
        with mock.patch.object(sys, "stderr", err):
            code, _said = self.run_cli(os.path.join(tmp(self), "nothing.txt"), "--lang", "it", "--book", d)
        self.assertEqual(code, 2)
        self.assertIn("no file to read", err.getvalue())
        self.assertEqual(os.listdir(os.path.join(d, "source", "paras")), ["ch1_p00.txt"])

    def test_the_tool_runs_as_a_program_by_its_full_path(self):
        d = self.book({1: 1})
        r = subprocess.run([sys.executable, str(ROOT / "lib" / "sourcetext.py"), write(self, "p.txt", "\n".join(TWO)),
                            "--lang", "it", "--book", d, "--chapter", "new"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("2 paragraphs", r.stdout)
        self.assertTrue(os.path.isfile(os.path.join(d, "source", "paras", "ch2_p01.txt")))


if __name__ == "__main__":
    unittest.main()
