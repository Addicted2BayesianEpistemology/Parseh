#!/usr/bin/env python3
"""The notes that come back with a book or a video are brought up to names.

    python3 -m unittest discover -s tests -p test_notes_came_back.py

A book's or a video's notes are a library of their own (markdown/app/
notes.py), and a library from before names -- two notes of one name, links
by uid -- is put right the first time this process opens it
(store.migrate_once).  A bundle brought back ("Bring a book back", "Bring
a video back") and a shelf's "Load from backup" put notes back as they were
written, where notes this process may have opened already lay -- and the
next opening would not look again: they must be put right as they come in,
as a studio upload or backup is (store.migrate_after_import).

Over HTTP, through serve.py's own routes, on a temporary toolbox: a test
that forgot would install into the machine's real books/.
"""
import http.client
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT, ROOT / "lib", ROOT / "youtube" / "lib"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import bundle                                      # noqa: E402
import shelf                                       # noqa: E402
import ytpages                                     # noqa: E402

BOOK = ROOT / "tests" / "fixtures" / "books" / "english" / "mini-en"
VIDEO = ROOT / "tests" / "fixtures" / "videos" / "persian" / "fA6bK2mQ8sT"


class NotesComeBack(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import serve
        cls.serve, cls.store, cls.notes = serve, serve.studio.store, serve.studio.notes
        cls.patches = [
            # the shelf page is written by a subprocess into the real books/
            mock.patch.object(serve.Handler, "_write_library", lambda self: {"ok": True}),
            mock.patch.object(serve.Handler, "log_request", lambda *a, **k: None)]
        for p in cls.patches:
            p.start()
        cls.srv = serve.Server(("127.0.0.1", 0), serve.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        for p in reversed(cls.patches):
            p.stop()

    def setUp(self):
        # a toolbox of each test's own: the notes of one place, once opened,
        # are not looked at again by this process
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        self.book = root / "books" / "english" / "mini-en"
        shutil.copytree(BOOK, self.book, ignore=shutil.ignore_patterns("reader"))
        videos = root / "youtube" / "videos"
        self.video = videos / "persian" / VIDEO.name
        shutil.copytree(VIDEO, self.video)
        self.root = root
        install, inspect, here = bundle.install, bundle.inspect, str(root)
        for p in [mock.patch.object(self.serve, "ROOT", str(root)),
                  mock.patch.object(self.serve._AtRoot, "directory", str(root)),
                  mock.patch.object(ytpages, "VIDEOS", str(videos)),
                  mock.patch.object(self.store, "LIB", root / "library"),
                  # the toolbox a bundle goes into is this one (its default
                  # is the real one, fixed when bundle.py was loaded)
                  mock.patch.object(bundle, "install", lambda data, replace=False, root=here:
                                    install(data, replace, root)),
                  mock.patch.object(bundle, "inspect", lambda data, root=here: inspect(data, root))]:
            p.start()
            self.addCleanup(p.stop)

    def http(self, method, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=120)
        c.request(method, path, body, {"Content-Type": "application/zip"} if body else {})
        r = c.getresponse()
        raw = r.read()
        c.close()
        return r.status, json.loads(raw or b"{}")

    def legacy_notes(self, content_dir, target):
        """Three notes as a library from before names holds them: all "A
        note", the last linking to the second by its uid."""
        with self.notes.library(content_dir):
            made = [self.notes.create(content_dir, "after", "sub", "1.%d-x" % n, target)
                    for n in range(3)]
            for n, meta in enumerate(made):
                d = self.store.doc_dir(meta["id"])
                src = re.sub(r"(?m)^title: .*$", "title: A note", (d / "source.md").read_text("utf-8"))
                if n == 2:
                    src += "See [another](doc:%s).\n" % made[1]["uid"]
                (d / "source.md").write_text(src, encoding="utf-8")
                meta = dict(self.store._read_meta(d), title="A note",
                            created="2020-01-0%dT00:00:00" % (n + 1))
                self.store._write_meta(d, meta)
        return made

    def listed(self, prefix):
        status, j = self.http("GET", prefix + "/api/docs")
        self.assertEqual(status, 200, j)
        return sorted(d["title"] for d in j["docs"])

    def the_link(self, prefix, doc_id):
        status, j = self.http("GET", prefix + "/api/docs/" + doc_id)
        self.assertEqual(status, 200, j)
        return re.search(r"See \[another\]\(doc:([^)]*)\)", j["markdown"]).group(1)

    def came_in_over_opened_notes(self, prefix, notes, bring_back):
        """The notes opened (and so put right once), then brought back as
        they were written: they are put right again."""
        self.assertEqual(self.listed(prefix), ["A note", "A note 2", "A note 3"],
                         "opened, they were put right the first time")
        self.assertEqual(self.the_link(prefix, notes[2]["id"]), "A note 2")
        status, j = bring_back()
        self.assertIn(status, (200, 201), j)
        self.assertEqual(self.listed(prefix), ["A note", "A note 2", "A note 3"],
                         "the notes that came back have names of their own")
        self.assertEqual(self.the_link(prefix, notes[2]["id"]), "A note 2",
                         "and their link by uid is written by name")

    def test_a_book_brought_back_over_notes_already_opened(self):
        notes = self.legacy_notes(self.book, "en")
        data, _name = bundle.pack_book(str(self.book))
        self.came_in_over_opened_notes(
            "/books/english/mini-en/notes", notes,
            lambda: self.http("POST", "/books/__upload?replace=1", data))

    def test_a_video_brought_back_over_notes_already_opened(self):
        notes = self.legacy_notes(self.video, "fa")
        data, _name = bundle.pack_video(str(self.video))
        self.came_in_over_opened_notes(
            ytpages.BASE + "/v/%s/notes" % VIDEO.name, notes,
            lambda: self.http("POST", ytpages.BASE + "/api/upload?replace=1", data))

    def test_a_shelf_restored_over_notes_already_opened(self):
        notes = self.legacy_notes(self.book, "en")
        path, _name = shelf.pack("book", root=str(self.root))
        self.addCleanup(os.unlink, path)
        with open(path, "rb") as f:
            data = f.read()
        self.came_in_over_opened_notes(
            "/books/english/mini-en/notes", notes,
            lambda: self.http("POST", "/books/__restore?replace=1", data))

    def test_a_video_shelf_restored_over_notes_already_opened(self):
        notes = self.legacy_notes(self.video, "fa")
        path, _name = shelf.pack("video", root=str(self.root))
        self.addCleanup(os.unlink, path)
        with open(path, "rb") as f:
            data = f.read()
        self.came_in_over_opened_notes(
            ytpages.BASE + "/v/%s/notes" % VIDEO.name, notes,
            lambda: self.http("POST", ytpages.BASE + "/api/restore?replace=1", data))

    def test_a_book_without_notes_is_given_no_notes_library(self):
        data, _name = bundle.pack_book(str(self.book))
        status, j = self.http("POST", "/books/__upload?replace=1", data)
        self.assertEqual(status, 200, j)
        self.assertFalse((self.book / "markdown").exists(),
                         "nothing to bring up to names, and nothing made for it")


if __name__ == "__main__":
    unittest.main()
