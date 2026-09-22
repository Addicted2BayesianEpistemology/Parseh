# SPDX-License-Identifier: GPL-3.0-or-later
"""How big a download will be, said before it is packed.

    python3 -m unittest discover -s tests -p test_bundle_size.py

lib/bundle.py's payload() sums what a bundle of each shape will carry --
the list _pack walks -- and serve.py's __narration/status hands the three
sums to the reader's download sheet.  The sheet used to say the size of the
book's FIRST recording as the size of "all of it", which for a book read in
nine parts was a fraction of the zip; and a book whose first recording was
missing answered the status with a 500.  Checked here on a book read in
three parts, with a fourth file left on the shelf from a recording since
replaced, against the zip the real route packs.

And each figure is the ZIP's, not the disk's: the text is deflated in the
zip, and on a Persian book the files on disk are three times what goes out
-- the sheet said "about 2.3 MB" of a 0.7 MB `text` download.  So every
fixture book, in every language and every shape, is packed and compared.
"""
import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import zipfile
import io
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for folder in ("markdown/exlex", "markdown/app", "youtube/lib", "lib", "."):
    sys.path.insert(0, str(ROOT / folder))
import bundle  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "books"
MINI_EN = FIXTURES / "english" / "mini-en"
MINI_FA = FIXTURES / "persian" / "mini-fa"
# recordings: random bytes, which no compressor can shrink -- as an mp3 is
PARTS = {"part1.mp3": 300_000, "part2.mp3": 1_200_000, "part3.mp3": 700_000,
         "old-take.mp3": 250_000}


def narrated_book(root, missing_first=False, fixture=MINI_EN):
    book = Path(root) / "books" / fixture.parent.name / fixture.name
    shutil.copytree(fixture, book, ignore=shutil.ignore_patterns("reader"))
    audio = book / "audio"
    audio.mkdir()
    for name, n in PARTS.items():
        if missing_first and name == "part1.mp3":
            continue
        (audio / name).write_bytes(os.urandom(n))
    (audio / "transcript-n2.txt").write_text("0:00 The old man\n0:03 wound the clock\n",
                                             encoding="utf-8")
    meta = json.loads((book / "book.json").read_text(encoding="utf-8"))
    meta["audio"] = "audio/part1.mp3"
    meta["narrations"] = [
        {"id": "n1", "audio": "audio/part1.mp3", "transcript": "", "from": "1.1", "to": "1.2"},
        {"id": "n2", "audio": "audio/part2.mp3", "transcript": "audio/transcript-n2.txt",
         "from": "2.1", "to": ""},
        {"id": "n3", "audio": "audio/part3.mp3", "transcript": "", "from": "", "to": ""}]
    (book / "book.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (book / "timings.json").write_text(json.dumps({"subs": {}}), encoding="utf-8")
    # the aligner's time comments above a subparagraph, which the `text`
    # shape takes out on the way into the zip -- and so out of its figure
    for tex in sorted(book.glob("ch*.tex"))[:1]:
        lines = tex.read_text(encoding="utf-8").split("\n")
        tex.write_text("\n".join("%% @par 1.%d %d.00 %d.50 0.91 auto\n%s" % (i, i, i, ln)
                                 if i % 4 == 0 else ln for i, ln in enumerate(lines)),
                       encoding="utf-8")
    return book


class Payload(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.book = narrated_book(td.name)

    def test_all_of_it_is_every_recording_not_the_first(self):
        full = bundle.payload("book", str(self.book), "full")
        self.assertEqual(full["media"], len(PARTS), "every recording under audio/, the old take too")
        self.assertEqual(full["media_bytes"], sum(PARTS.values()))
        self.assertGreater(full["bytes"], full["media_bytes"], "and the text and the transcript beside them")
        self.assertEqual(bundle.payload_bytes("book", str(self.book), "full"), full["bytes"])

    def test_the_other_shapes_carry_no_recording(self):
        sizes = {m: bundle.payload("book", str(self.book), m) for m in bundle.MODES}
        self.assertEqual((sizes["text"]["media"], sizes["linked"]["media"]), (0, 0))
        self.assertLess(sizes["text"]["bytes"], sizes["linked"]["bytes"],
                        "linked also carries timings.json")
        self.assertLess(sizes["linked"]["bytes"], sizes["full"]["bytes"])
        with self.assertRaises(bundle.BundleError):
            bundle.payload("book", str(self.book), "most of it")

    def test_the_figure_is_the_zip_the_route_packs(self):
        with tempfile.TemporaryDirectory() as td:
            persian = narrated_book(td, fixture=MINI_FA)
            for book in (self.book, persian):
                for mode in bundle.MODES:
                    with self.subTest(book=book.name, mode=mode):
                        data, _name = bundle.pack_book(str(book), audio=mode)
                        said = bundle.payload_bytes("book", str(book), mode)
                        # the recordings are stored byte for byte, the text is
                        # counted deflated and every header is counted: what is
                        # left is the manifest's few bytes
                        self.assertLess(abs(len(data) - said), 0.01 * len(data) + 64,
                                        "%s: said %d, packed %d" % (mode, said, len(data)))
                        with zipfile.ZipFile(io.BytesIO(data)) as z:
                            carried = [i for i in z.infolist()
                                       if i.filename.split("/", 1)[-1].startswith("audio/")
                                       and i.filename.endswith(".mp3")]
                        self.assertEqual(len(carried),
                                         bundle.payload("book", str(book), mode)["media"], mode)

    def test_every_language_is_sized_as_the_zip_not_the_disk(self):
        """The text alone is the whole of a book without a recording, and the
        zip deflates it: a Persian one to a third.  The figure must be the
        zip's in every language and every shape -- the sum of the files on
        disk said nearly three times the download."""
        books = sorted(p for p in FIXTURES.glob("*/*") if (p / "book.json").is_file())
        self.assertGreaterEqual(len(books), 11, "a fixture book per language")
        for book in books:
            for mode in bundle.MODES:
                with self.subTest(book=book.name, mode=mode):
                    data, _name = bundle.pack_book(str(book), audio=mode)
                    said = bundle.payload_bytes("book", str(book), mode)
                    self.assertLess(abs(len(data) - said), 0.01 * len(data) + 64,
                                    "%s %s: said %d, packed %d" % (book.name, mode, said, len(data)))

    def test_a_changed_file_is_sized_again(self):
        """The deflated sizes are kept between two askings -- the sheet and the
        player ask often -- but never past a change to the file."""
        before = bundle.payload_bytes("book", str(self.book), "text")
        tex = sorted(self.book.glob("ch*.tex"))[0]
        with open(tex, "a", encoding="utf-8") as f:
            f.write("\n%% %s\n" % os.urandom(3000).hex())      # 6 kB nothing can shrink much
        after = bundle.payload_bytes("book", str(self.book), "text")
        data, _name = bundle.pack_book(str(self.book), audio="text")
        self.assertGreater(after, before + 2000)
        self.assertLess(abs(len(data) - after), 0.01 * len(data) + 64)

    def test_a_film_is_counted_in_the_shape_that_carries_it(self):
        with tempfile.TemporaryDirectory() as td:
            v = Path(td) / "clip-abc123"
            v.mkdir()
            (v / "video.json").write_text(json.dumps({"id": "clip-abc123", "language": "en",
                                                      "gloss": "en"}), encoding="utf-8")
            (v / "annotations.json").write_text(json.dumps({"segments": []}), encoding="utf-8")
            (v / "media.mp4").write_bytes(os.urandom(500_000))
            full = bundle.payload("video", str(v), "full")
            text = bundle.payload("video", str(v), "text")
            self.assertEqual((full["media"], full["media_bytes"]), (1, 500_000))
            self.assertEqual(text["media"], 0)
            import ytpages
            self.assertEqual(ytpages.bundle_bytes(str(v)), full["bytes"],
                             "the player's download is the film's shape")
            data, _n = bundle.pack_video(str(v))
            self.assertLess(abs(len(data) - full["bytes"]), 0.03 * len(data) + 4_000)


class Status(unittest.TestCase):
    """__narration/status over real HTTP, as the reader asks it."""

    @classmethod
    def setUpClass(cls):
        import serve
        cls.serve = serve
        cls.patches = [mock.patch.object(serve.Handler, "log_request", lambda *a, **k: None)]
        for p in cls.patches:
            p.start()
        cls.srv = serve.Server(("127.0.0.1", 0), serve.Handler)
        cls.port = cls.srv.server_address[1]
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        for p in reversed(cls.patches):
            p.stop()

    def status(self, missing_first):
        with tempfile.TemporaryDirectory() as td:
            narrated_book(td, missing_first)
            with mock.patch.object(self.serve, "ROOT", td), \
                    mock.patch.object(self.serve._AtRoot, "directory", td):
                c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
                c.request("GET", "/books/english/mini-en/reader/__narration/status")
                r = c.getresponse()
                raw = r.read()
                c.close()
        return r.status, json.loads(raw)

    def test_the_three_sizes_are_in_the_status(self):
        status, j = self.status(False)
        self.assertEqual(status, 200, j)
        self.assertEqual(sorted(j["bundle"]), sorted(bundle.MODES))
        self.assertEqual(j["bundle"]["full"]["media"], len(PARTS))
        self.assertEqual(j["bundle"]["full"]["media_bytes"], sum(PARTS.values()))
        # `audio` stays what it was, the FIRST recording, for the panel
        self.assertEqual((j["audio"]["exists"], j["audio"]["bytes"]), (True, PARTS["part1.mp3"]))

    def test_a_missing_first_recording_is_said_not_a_500(self):
        status, j = self.status(True)
        self.assertEqual(status, 200, j)
        self.assertEqual((j["audio"]["exists"], j["audio"]["bytes"]), (False, 0))
        self.assertEqual(j["audio"]["declared"], "audio/part1.mp3")
        self.assertEqual(j["bundle"]["full"]["media"], len(PARTS) - 1,
                         "the recordings that ARE there are still what all of it carries")


if __name__ == "__main__":
    unittest.main()
