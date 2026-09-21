"""The way the editor writes a document's source by default: the prose
language of its front matter (`lang:`), which the editor page and every
preview carry as a record (markdown/app/server.py prose_record).  The
browser side -- the ⇤ RTL editor button, the choice remembered per
document, the face, the panes lined up -- is tests/editor_dir.mjs.

    python3 -m unittest discover -s tests -p test_studio_editor_dir.py

No socket: the routes are driven through a fake handler, in a temporary
studio library (store.use_library)."""
import json
import re
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "markdown" / "exlex", ROOT / "markdown" / "app",
               ROOT / "lib", ROOT / "youtube" / "lib"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import languages  # noqa: E402
import server     # noqa: E402
import store      # noqa: E402


def doc(lang_line, target="en"):
    return "---\ntitle: A note\n%starget: %s\n---\n\nSome prose.\n" % (lang_line, target)


class Fake:
    """What the page and preview routes use of a handler."""

    def __init__(self, body=None, query=""):
        self.body = body
        self.query = urllib.parse.parse_qs(query)
        self.sent = None

    def _json_body(self):
        return self.body

    def send_html(self, text, code=200):
        self.sent = (code, text)

    def send_json(self, payload, status=200):
        self.sent = (status, payload)


def embedded(html):
    m = re.search(r'<script id="prose-lang" type="application/json">(.*?)</script>', html)
    return json.loads(m.group(1)) if m else None


class ProseRecordTests(unittest.TestCase):
    def test_every_language_is_written_the_way_the_registry_writes_it(self):
        for code in languages.LANGS:
            rec = server.prose_record(code)
            self.assertEqual((rec["code"], rec["dir"], rec["taught"]),
                             (code, languages.get(code).dir, True))
        self.assertEqual(server.prose_record("fa")["dir"], "rtl")
        self.assertEqual(server.prose_record("ar")["dir"], "rtl")

    def test_a_prose_language_the_toolbox_does_not_teach_or_does_not_know(self):
        self.assertEqual((server.prose_record("pt")["dir"], server.prose_record("pt")["taught"]),
                         ("ltr", False))
        # spelled the way a writer might, or not at all: English, as a gloss is
        self.assertEqual(server.prose_record("ITA")["code"], "it")
        self.assertEqual(server.prose_record("xx")["code"], "en")
        self.assertEqual(server.prose_record(None)["dir"], "ltr")


class PageTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        was = store.use_library(Path(td.name))
        self.addCleanup(store.use_library, was)

    def edit_page(self, markdown):
        meta = store.create(markdown)
        h = Fake()
        server.page_edit(h, meta["id"])
        self.assertEqual(h.sent[0], 200)
        self.assertNotIn("{{", h.sent[1], "every value of the template is filled in")
        return h.sent[1]

    def test_the_editor_page_carries_the_documents_prose_language(self):
        html = self.edit_page(doc("lang: fa\n"))
        self.assertEqual((embedded(html)["code"], embedded(html)["dir"]), ("fa", "rtl"))
        self.assertIn('id="btn-editor-dir"', html)
        self.assertEqual(embedded(self.edit_page(doc("lang: ar\n", "fr")))["dir"], "rtl")
        self.assertEqual(embedded(self.edit_page(doc("lang: en\n", "fa")))["dir"], "ltr")
        self.assertEqual(embedded(self.edit_page(doc("", "ja")))["dir"], "ltr")

    def test_a_new_document_carries_its_starters(self):
        for target in languages.LANGS:
            h = Fake(query="target=" + target)
            server.page_new(h)
            self.assertNotIn("{{", h.sent[1])
            starter = server.new_template(target)
            lang = re.search(r"^lang:\s*(\S+)", starter, re.M)
            self.assertEqual(embedded(h.sent[1])["code"],
                             server.prose_record(lang and lang.group(1))["code"], target)

    def test_a_preview_follows_a_lang_typed_into_the_front_matter(self):
        for lang_line, want in (("lang: fa\n", "rtl"), ("lang: ar\n", "rtl"),
                                ("lang: en\n", "ltr"), ("lang: pt\n", "ltr"), ("", "ltr")):
            h = Fake({"markdown": doc(lang_line), "doc_id": ""})
            server.api_preview(h)
            status, answer = h.sent
            self.assertEqual((status, answer["ok"]), (200, True))
            self.assertEqual(answer["doc"]["prose"]["dir"], want, lang_line)


if __name__ == "__main__":
    unittest.main()
