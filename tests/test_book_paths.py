"""serve.book_dir: a book's URL path names a book on the shelf and nothing else.

    python3 -m unittest discover -s tests -p test_book_paths.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import serve  # noqa: E402


class BookDirTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        for rel in ("books/persian/tale", "tests/fixtures/books/english/mini-en"):
            (self.root / rel).mkdir(parents=True)
            (self.root / rel / "book.json").write_text(json.dumps({"slug": rel.rsplit("/", 1)[1]}))
        patcher = mock.patch.object(serve._AtRoot, "directory", str(self.root))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_book_on_the_shelf(self):
        self.assertEqual(os.path.realpath(self.root / "books" / "persian" / "tale"),
                         os.path.realpath(serve.book_dir("/books/persian/tale")))
        self.assertIsNone(serve.book_dir("/books/persian/nothing"))

    def test_a_book_linked_onto_the_shelf_is_on_it(self):
        elsewhere = self.root / "elsewhere" / "linked"
        elsewhere.mkdir(parents=True)
        (elsewhere / "book.json").write_text("{}")
        try:
            os.symlink(elsewhere, self.root / "books" / "persian" / "linked")
        except (OSError, NotImplementedError):
            self.skipTest("this filesystem makes no symlinks")
        self.assertIsNotNone(serve.book_dir("/books/persian/linked"))

    def test_an_encoded_climb_names_nothing(self):
        # translate_path decodes and normalises before it looks: each of these
        # used to resolve to the fixture book outside books/
        for path in ("/books/%2e%2e%2ftests%2ffixtures%2fbooks%2fenglish/mini-en",
                     "/books/..%2ftests%2ffixtures%2fbooks%2fenglish/mini-en",
                     "/books/%2E%2E%2Ftests%2Ffixtures%2Fbooks%2Fenglish/mini-en",
                     "/books/../tests/fixtures/books/english/mini-en"):
            with self.subTest(path=path):
                self.assertIsNone(serve.book_dir(path))
                self.assertIsNone(serve.notes_library(path + "/notes"))


if __name__ == "__main__":
    unittest.main()
