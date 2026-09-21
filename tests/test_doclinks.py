"""Links between documents, by NAME (markdown/exlex/texgen.py for the
grammar and the resolver, markdown/app/htmlgen.py and notes.py for the three
ways a link is shown, markdown/app/store.py for the library it resolves in).

    python3 -m unittest discover -s tests -p test_doclinks.py

No socket: the store runs in a temporary library (store.use_library), as in
tests/test_studio_files.py."""
import contextlib
import io
import json
import re
import sys
import tempfile
import time
import unittest
import urllib.parse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "markdown" / "exlex", ROOT / "markdown" / "app",
               ROOT / "lib", ROOT / "youtube" / "lib"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import htmlgen  # noqa: E402
import languages  # noqa: E402
import mdparser  # noqa: E402
import notes    # noqa: E402
import server   # noqa: E402
import store    # noqa: E402
import texgen   # noqa: E402

# names a title can be: spaces, parentheses that pair up and ones that do
# not, a backslash, other scripts, brackets and braces, and one that happens
# to look like a uid
NAMES = ["Plain", "Table 7-6 - Irrigation Withdrawals (percentages)", "a)b", "(a",
         "((a))", "(((a)))", "a\\b", "ends in a backslash\\", "x (y (z) w) v",
         "x (y (z (q) r) w) v", ")(", "شکل کلمهٔ فارسی", "日本語のノート",
         "हिंदी के नोट्स", "[bracket] {brace}", "trailing (", "a\\)b", "9f3c1a7b20de"]


def zip_of(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


def library_zip(root):
    """a library as the Backup button writes it (server.api_export)"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(Path(root).rglob("*")):
            if f.is_file() and not f.relative_to(root).parts[0].startswith("."):
                zf.write(f, str(f.relative_to(root)))
    return buf.getvalue()


def doc(title, body="Text.", target="en"):
    return ("---\ntitle: %s\nsubtitle:\nnote:\nlang: en\ntarget: %s\n---\n\n%s\n"
            % (title, target, body))


class GrammarTests(unittest.TestCase):
    def test_every_name_round_trips_through_the_writer_and_the_parser(self):
        for name in NAMES:
            written = texgen.escape_doc_name(name)
            text = "see [a label](doc:%s) and [out](https://example.org)." % written
            m = texgen.DOCLINK_RE.search(text)
            self.assertIsNotNone(m, name)
            self.assertEqual(m.group(1), "a label", name)
            self.assertEqual(m.group(2), written, "the link closes where it should: %r" % name)
            self.assertEqual(texgen.unescape_doc_name(m.group(2)), name)
            self.assertEqual(texgen.doclink_markdown("", name), "[](doc:%s)" % written)

    def test_only_what_would_break_the_link_is_escaped(self):
        self.assertEqual(texgen.escape_doc_name("Table 7-6 (percentages)"),
                         "Table 7-6 (percentages)", "a pair is written as it is")
        self.assertEqual(texgen.escape_doc_name("Notes (draft"), "Notes \\(draft")
        self.assertEqual(texgen.escape_doc_name("a\\b"), "a\\\\b")
        self.assertEqual(texgen.escape_doc_name("two\nlines"), "two lines",
                         "no name holds a line break")

    def test_the_name_key_is_case_and_blank_blind(self):
        self.assertEqual(texgen.doc_name_key("  Verbs  of\tMOTION "), "verbs of motion")
        self.assertEqual(texgen.doc_name_key("Straße"), texgen.doc_name_key("STRASSE"))
        # NFC: a precomposed é and e + a combining accent are one name
        self.assertEqual(texgen.doc_name_key("Caf\u00e9"), texgen.doc_name_key("Cafe\u0301"))
        self.assertNotEqual(texgen.doc_name_key("Verbs"), texgen.doc_name_key("Verbs 2"))

    def test_a_link_does_not_run_into_the_next_one_or_across_a_line(self):
        text = "[a](doc:One) and [b](doc:Two (2)) then\n[c](doc:Three"
        got = [(m.group(1), texgen.unescape_doc_name(m.group(2)))
               for m in texgen.DOCLINK_RE.finditer(text)]
        self.assertEqual(got, [("a", "One"), ("b", "Two (2)")],
                         "an unclosed link on the last line is no link")

    def test_a_formula_paragraphs_away_hides_no_link(self):
        """A mark is found within one paragraph, as the page finds it: an
        interval's `[` in one and a formula's `]{math}` two paragraphs on
        are no formula, and the link between them is one the page shows,
        and a rename rewrites (read whole, the text hid it from both)."""
        md = doc("T", "An interval [0, 1) opens here.\n\nSee [the notes](doc:Notes (draft)).\n\n"
                      "And [x^2]{math} closes there.")
        page = htmlgen.render_document(md, docs=INDEX)["html"]
        self.assertEqual(page.count('href="/doc/notes-222222"'), 1, page)
        self.assertEqual([l.target for l in texgen.find_doclinks(md, "en")], ["Notes (draft)"])
        self.assertIn("[the notes](doc:Notes 2)",
                      store.rewrite_links(md, lambda label, name: "Notes 2")[0])


INDEX = {
    "aaaaaaaaaaaa": {"id": "shape-111111", "title": "شکل کلمه", "created": "2024-01-01T00:00:00"},
    "bbbbbbbbbbbb": {"id": "notes-222222", "title": "Notes (draft)", "created": "2024-01-01T00:00:00"},
    "cccccccccccc": {"id": "hexname-333333", "title": "dddddddddddd", "created": "2024-01-01T00:00:00"},
    "dddddddddddd": {"id": "other-444444", "title": "Other", "created": "2024-01-01T00:00:00"},
}


class ResolveTests(unittest.TestCase):
    def setUp(self):
        self.index = texgen.prepare_doc_index(INDEX)

    def find(self, target):
        info = texgen.lookup_doclink(texgen.escape_doc_name(target), self.index)
        return info and info["id"]

    def test_a_name_finds_its_document_case_and_blank_blind(self):
        self.assertEqual(self.find("Notes (draft)"), "notes-222222")
        self.assertEqual(self.find("notes   (DRAFT)"), "notes-222222")
        self.assertEqual(self.find("شکل کلمه"), "shape-111111")
        self.assertIsNone(self.find("Notes"))

    def test_a_uid_link_still_finds_its_document_unless_a_document_has_that_name(self):
        self.assertEqual(self.find("aaaaaaaaaaaa"), "shape-111111", "the uid fallback")
        self.assertEqual(self.find("AAAAAAAAAAAA"), "shape-111111")
        self.assertEqual(self.find("dddddddddddd"), "hexname-333333",
                         "a document CALLED that wins over the uid it spells")
        self.assertIsNone(self.find("eeeeeeeeeeee"))

    def test_what_a_link_shows(self):
        r = lambda target, label: texgen.resolve_doclink(texgen.escape_doc_name(target), label,
                                                          self.index)
        self.assertEqual(r("notes (draft)", ""), ("Notes (draft)", "notes-222222"),
                         "no label: the target's current title, as it spells it")
        self.assertEqual(r("Notes (draft)", " mine "), ("mine", "notes-222222"))
        self.assertEqual(r("Gone for now", ""), ("Gone for now", None),
                         "no document: the name it is waiting for")
        self.assertEqual(r("eeeeeeeeeeee", ""), ("doc:eeeeeeeeeeee", None),
                         "a uid link to nothing reads as it always did")

    def test_of_two_legacy_documents_sharing_a_name_the_older_holds_it(self):
        idx = texgen.prepare_doc_index({
            "111111111111": {"id": "late-1", "title": "Twin", "created": "2025-01-01T00:00:00"},
            "222222222222": {"id": "early-2", "title": "twin", "created": "2023-01-01T00:00:00"}})
        self.assertEqual(texgen.lookup_doclink("Twin", idx)["id"], "early-2")


class RenderTests(unittest.TestCase):
    MD = doc("T", "See [](doc:شکل کلمه), [the notes](doc:notes  (DRAFT)), "
                  "[](doc:aaaaaaaaaaaa), [gone](doc:Gone one), [](doc:Nothing) "
                  "and فارسی.", target="fa")

    def test_the_page_links_what_is_there_and_marks_what_is_not(self):
        html = htmlgen.render_document(self.MD, docs=INDEX)["html"]
        self.assertIn('<a class="doclink" href="/doc/notes-222222" data-name="notes  (DRAFT)">'
                      'the notes</a>', html)
        self.assertEqual(html.count('href="/doc/shape-111111"'), 2,
                         "by its name and by its old uid alike")
        self.assertIn('<span class="doclink-dead" data-name="Gone one" title="No document named '
                      '“Gone one” in this library — create or upload one with this name and this '
                      'link will work again">gone</span>', html)
        self.assertRegex(html, r'<span class="doclink-dead" data-name="Nothing"[^>]*>Nothing</span>')

    def test_a_title_shown_for_an_empty_label_is_not_counted(self):
        """The hover tools find the n-th run of a word in the SOURCE; a title
        shown in place of an empty label is not in the source there, and a
        name is never on the page: neither may be counted, or every later
        occurrence of the same word is edited in the wrong place."""
        md = doc("T", "[](doc:شکل کلمه) and [شکل](doc:شکل کلمه) and شکل کلمه.", target="fa")
        html = htmlgen.render_document(md, docs=INDEX)["html"]
        counted = re.findall(r'data-fa="([^"]+)" data-occ="(\d+)"', html)
        self.assertEqual(counted, [("شکل", "0"), ("شکل کلمه", "0")], html)
        store._target_of(md)
        self.assertEqual(len(store._run_matches(md, "شکل کلمه")), 1,
                         "the source counts the same: the names are blanked")
        self.assertEqual(len(store._run_matches(md, "شکل")), 1)

    def test_an_empty_label_shows_a_title_holding_brackets_as_a_link(self):
        """The title an empty label shows goes into the link whole: a
        bracket in it, or a mark, could otherwise break the link around it
        (it did: "[bracket] {brace}" came out as literal text, no link)."""
        idx = {"111111111111": {"id": "br-1", "title": "[bracket] {brace}", "created": ""},
               "222222222222": {"id": "mk-2", "title": "A [x]{teal} word", "created": ""},
               "333333333333": {"id": "fa-3", "title": "کتاب [نو]{teal}", "created": ""},
               # two titles each showing the other: drawn once, not forever
               "444444444444": {"id": "p-4", "title": "See [](doc:Pong)", "created": ""},
               "555555555555": {"id": "q-5", "title": "Pong", "created": ""}}
        md = doc("T", "One [](doc:\\[bracket] {brace}), two [](doc:A [x]{teal} word), "
                      "three [](doc:کتاب [نو]{teal}), four [](doc:See [](doc:Pong)) and کتاب.",
                 target="fa")
        html = htmlgen.render_document(md, docs=idx)["html"]
        self.assertIn('<a class="doclink" href="/doc/br-1" data-name="[bracket] {brace}">'
                      '[bracket] {brace}</a>', html)
        self.assertIn('<a class="doclink" href="/doc/mk-2" data-name="A [x]{teal} word">'
                      'A <span class="fac fac-teal" data-color="teal">x</span> word</a>', html,
                      "the title drawn as the page draws a title")
        self.assertRegex(html, r'<a class="doclink" href="/doc/fa-3" [^>]*><span class="fa"[^>]*>'
                               r'کتاب</span> <span class="fac fac-teal"')
        self.assertIn('href="/doc/p-4"', html)
        self.assertEqual(re.findall(r'data-fa="([^"]+)" data-occ="(\d+)"', html), [("کتاب", "0")],
                         "a title's runs are drawn, not counted")
        fm, blocks = mdparser.parse(md)
        tex = texgen.generate(fm, blocks, docs=idx)
        self.assertIn(r"One \textcolor{linkc}{[bracket] \{brace\}}", tex)
        self.assertIn(r"two \textcolor{linkc}{A \textcolor{fateal}{x} word}", tex)

    def test_the_pdf_sets_the_resolved_text_in_the_link_colour(self):
        fm, blocks = mdparser.parse(self.MD)
        tex = texgen.generate(fm, blocks, docs=INDEX)
        self.assertIn(r"\textcolor{linkc}{the notes}", tex)
        self.assertIn(r"\textcolor{linkc}{gone}", tex)
        self.assertIn(r"\textcolor{linkc}{Nothing}", tex)

    def test_without_a_library_a_link_shows_its_own_words(self):
        """the command line's build: no library, so the label, or the name"""
        fm, blocks = mdparser.parse(self.MD)
        tex = texgen.generate(fm, blocks)
        self.assertIn(r"\textcolor{linkc}{gone}", tex)
        self.assertIn(r"\textcolor{linkc}{Nothing}", tex)
        self.assertIn(r"\textcolor{linkc}{doc:aaaaaaaaaaaa}", tex)

    def test_the_plain_text_of_a_note_says_the_same(self):
        md = doc("T", "See [](doc:notes (draft)) and [mine](doc:Other) and [](doc:Gone one).")
        self.assertEqual(notes.excerpt(md, docs=INDEX),
                         "See Notes (draft) and mine and Gone one.")


class LibraryCase(unittest.TestCase):
    """A temporary library of this thread's own, as test_studio_files.py's."""

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.lib = Path(td.name)
        was = store.use_library(self.lib)
        self.addCleanup(store.use_library, was)

    def make(self, title, body="Text.", target="en"):
        return store.create(doc(title, body, target))

    def legacy(self, title, body="Text.", created="2020-01-01T00:00:00"):
        """a document as a library from before names could hold one: its
        title shared with others, never checked"""
        meta = store._create(doc(title, body), [])
        d = store.doc_dir(meta["id"])
        meta["created"] = created
        store._write_meta(d, meta)
        return meta

    def source(self, doc_id):
        return store.get(doc_id)[1]

    def made(self):
        return sorted(p.parent.name for p in self.lib.rglob("source.md"))

    def title_line(self, doc_id):
        return re.search(r"(?m)^title: (.*)$", self.source(doc_id)).group(1)

    def page(self, doc_id):
        return htmlgen.render_document(self.source(doc_id), docs=store.doc_index())["html"]


class NamingTests(LibraryCase):
    def test_a_name_already_taken_is_made_unique_in_the_front_matter_too(self):
        a = self.make("Cats")
        b = self.make("cats")               # one name, case-blind
        c = self.make("Cats 2")
        self.assertEqual((a["title"], b["title"]), ("Cats", "cats 2"))
        self.assertEqual(self.title_line(b["id"]), "cats 2", "the front matter agrees")
        self.assertEqual(c["title"], "Cats 2 2", "and so on, whatever is taken")

    def test_no_title_is_untitled_and_unique(self):
        a = store.create("just some text")
        b = store.create("---\ntitle:\ntarget: en\n---\n\nmore")
        self.assertEqual((a["title"], b["title"]), ("Untitled", "Untitled 2"))
        self.assertEqual(self.title_line(b["id"]), "Untitled 2")
        self.assertTrue(self.source(a["id"]).endswith("just some text\n"))

    def test_a_duplicate_is_named_as_a_copy_in_its_meta_and_its_front_matter(self):
        a = self.make("Verbs")
        c1 = store.duplicate(a["id"])
        c2 = store.duplicate(a["id"])
        self.assertEqual((c1["title"], c2["title"]), ("Verbs (copy)", "Verbs (copy 2)"))
        self.assertEqual(self.title_line(c2["id"]), "Verbs (copy 2)")
        self.assertEqual(store.get(c2["id"])[0]["title"], "Verbs (copy 2)",
                         "the meta says what the text says")

    def test_a_new_note_gets_a_name_of_its_own(self):
        with tempfile.TemporaryDirectory() as content:
            with notes.library(content):
                first = notes.create(content, "after", "sub", "1.1-abc", "fa")
                second = notes.create(content, "before", "cap", "6", "fa")
                self.assertEqual((first["title"], second["title"]), ("A note", "A note 2"))
                self.assertEqual(notes.anchor_of(self.source(second["id"])),
                                 {"side": "before", "kind": "cap", "at": "6"},
                                 "the rest of its header is as the starter wrote it")

    def test_a_deleted_document_leaves_its_links_hanging_until_its_name_is_back(self):
        target = self.make("The ezafe")
        linker = self.make("Grammar", "See [the ezafe](doc:The ezafe) and [](doc:the EZAFE).")
        self.assertEqual(self.page(linker["id"]).count('href="/doc/%s"' % target["id"]), 2)
        store.delete(target["id"])
        self.assertIn("[the ezafe](doc:The ezafe) and [](doc:the EZAFE)", self.source(linker["id"]),
                      "the links are left as they were")
        page = self.page(linker["id"])
        self.assertEqual(page.count('class="doclink-dead"'), 2)
        again = self.make("the Ezafe", "Written again.")
        page = self.page(linker["id"])
        self.assertEqual(page.count('href="/doc/%s"' % again["id"]), 2,
                         "a document of that name is what they point at again")
        self.assertIn(">the Ezafe</a>", page, "an empty label shows its title as it is now")


class MigrationTests(LibraryCase):
    def migrate(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            out = store.migrate_links()
        return out, err.getvalue()

    def test_legacy_duplicate_names_are_told_apart_the_oldest_keeping_its_own(self):
        late = self.legacy("A note", created="2024-03-01T00:00:00")
        early = self.legacy("A note", created="2023-01-01T00:00:00")
        mid = self.legacy("a NOTE", created="2023-06-01T00:00:00")
        taken = self.legacy("A note 2", created="2025-01-01T00:00:00")
        out, err = self.migrate()
        self.assertEqual(out["renamed"], [(mid["id"], "a NOTE", "a NOTE 3"),
                                          (late["id"], "A note", "A note 4")])
        self.assertEqual(self.title_line(early["id"]), "A note")
        self.assertEqual(self.title_line(taken["id"]), "A note 2", "a name nobody shared is kept")
        self.assertEqual((self.title_line(mid["id"]), store.get(mid["id"])[0]["title"]),
                         ("a NOTE 3", "a NOTE 3"))
        self.assertEqual(len(err.strip().split("\n")), 2, "one line each: " + err)
        self.assertIn("renamed 'A note' to 'A note 4'", err)
        self.assertEqual(self.migrate()[0], {"renamed": [], "links": {}}, "idempotent")

    def test_uid_links_are_written_by_name_and_keep_their_labels(self):
        target = self.make("Shape of a word")
        body = ("[](doc:%s), [its label](doc:%s) and [gone](doc:0123456789ab), "
                "a [URL](https://example.org)." % (target["uid"], target["uid"].upper()))
        linker = self.make("Grammar", body)
        before = self.page(linker["id"])
        updated = store.get(linker["id"])[0]["updated"]
        out, _ = self.migrate()
        self.assertEqual(out["links"], {linker["id"]: 2})
        self.assertIn("[](doc:Shape of a word), [its label](doc:Shape of a word) and "
                      "[gone](doc:0123456789ab), a [URL](https://example.org).",
                      self.source(linker["id"]), "an unknown uid is left for a restore to answer")
        drop = lambda html: re.sub(r' data-name="[^"]*"', "", html)
        self.assertEqual(drop(self.page(linker["id"])), drop(before),
                         "the page is what it was, save the name each link now spells")
        self.assertEqual(store.get(linker["id"])[0]["updated"], updated,
                         "a link put right is not an edit of the document")
        self.assertEqual(self.migrate()[0]["links"], {}, "idempotent")

    def test_a_name_that_looks_like_a_uid_is_a_name(self):
        hexa = self.make("aaaaaaaaaaaa")
        other = self.make("Other")
        linker = self.make("L", "[x](doc:aaaaaaaaaaaa) [y](doc:%s)" % other["uid"])
        store.migrate_links()
        self.assertIn("[x](doc:aaaaaaaaaaaa) [y](doc:Other)", self.source(linker["id"]))
        self.assertIn('href="/doc/%s"' % hexa["id"], self.page(linker["id"]))

    def test_a_link_in_the_front_matter_is_not_touched(self):
        target = self.make("T")
        md = "---\ntitle: See [x](doc:%s)\ntarget: en\n---\n\n[y](doc:%s)\n" % (
            target["uid"], target["uid"])
        linker = store.create(md)
        store.migrate_links()
        self.assertEqual(self.source(linker["id"]),
                         md.replace("[y](doc:%s)" % target["uid"], "[y](doc:T)"))

    def test_links_by_uid_that_come_in_are_written_by_name(self):
        target = self.make("Verbs")
        up = store.import_zip(zip_of({"a.md": doc("Nouns", "[](doc:%s)" % target["uid"])}))
        self.assertIn("[](doc:Verbs)", self.source(up["docs"][0]["id"]))
        # a backup brings back a document that others here link to by uid
        with tempfile.TemporaryDirectory() as other:
            was = store.use_library(Path(other))
            try:
                gone = self.make("Adjectives")
                backup = library_zip(Path(other))
            finally:
                store.use_library(was)
        linker = self.make("L", "[see](doc:%s)" % gone["uid"])
        self.assertIn('class="doclink-dead"', self.page(linker["id"]))
        store.import_library(backup)
        self.assertIn("[see](doc:Adjectives)", self.source(linker["id"]))
        self.assertIn('href="/doc/%s"' % gone["id"], self.page(linker["id"]))

    def test_the_migration_runs_once_per_library_and_process(self):
        self.legacy("Twin")
        self.legacy("Twin", created="2021-01-01T00:00:00")
        with contextlib.redirect_stderr(io.StringIO()):
            first = store.migrate_once()
            second = store.migrate_once()
        self.assertEqual(len(first["renamed"]), 1)
        self.assertIsNone(second)

    def test_a_library_put_back_whole_where_one_was_met_is_migrated_again(self):
        """A book's notes brought back by a bundle or a backup lie where the
        notes it had lay, and are not the ones met there (serve.py,
        notes_came_back)."""
        with contextlib.redirect_stderr(io.StringIO()):
            store.migrate_once()
            self.legacy("Twin")
            self.legacy("Twin", created="2021-01-01T00:00:00")
            self.assertIsNone(store.migrate_once())
            again = store.migrate_once(again=True)
        self.assertEqual(len(again["renamed"]), 1)

    def test_the_cards_count_the_same_before_and_after_the_migration(self):
        """The name a link spells is never on the page: a link by uid
        written by name must not add the name's words, or its runs of the
        target language, to the counts on the library's card."""
        target = self.make("شکل کلمهٔ فارسی and a long English name of many words", target="fa")
        linker = self.make("Grammar", "[the shape](doc:%s) and فارسی." % target["uid"], target="fa")
        before = store.get(linker["id"])[0]["stats"]
        self.migrate()
        self.assertIn("(doc:شکل کلمهٔ فارسی and a long", self.source(linker["id"]))
        self.assertEqual(store.get(linker["id"])[0]["stats"], before)
        counts = set()
        for name in ("9f3c1a7b20de", "02 - Persian نا and ن", "Some long english name with many words"):
            md = doc("T", "Plain [link](doc:%s) here and فارسی." % name, target="fa")
            got = htmlgen.stats(md, mdparser.parse(md)[1], target="fa")
            counts.add((got["words"], got["fa_runs"]))
        self.assertEqual(len(counts), 1, "whatever the name: %s" % counts)


class PropagationTests(LibraryCase):
    """A rename followed like Obsidian follows one: every link that named
    the document by its old name names it by its new one."""

    def setUp(self):
        super().setUp()
        self.target = self.make("Verbs of motion", "Self: [me](doc:Verbs of motion) and "
                                "[](doc:verbs OF motion).")
        self.linker = self.make("Grammar", "[see](doc:Verbs of motion), [](doc:verbs of MOTION), "
                                "[other](doc:Nouns) and [keep](doc:%s)." % self.target["uid"])
        store.set_build(self.linker["id"], {"status": "ok", "pages": 1})
        self.before = store.get(self.linker["id"])[0]

    def rename(self, title):
        text = self.source(self.target["id"]).replace("title: Verbs of motion", "title: " + title)
        return store.save(self.target["id"], text)

    def test_a_save_that_changes_the_title_rewrites_every_link_to_it(self):
        meta, written = self.rename("Motion verbs")
        self.assertEqual(meta["title"], "Motion verbs")
        self.assertIn("[see](doc:Motion verbs), [](doc:Motion verbs), [other](doc:Nouns) and "
                      "[keep](doc:%s)." % self.target["uid"], self.source(self.linker["id"]),
                      "labels kept; a link to another name, or by uid, left alone")
        self.assertIn("Self: [me](doc:Motion verbs) and [](doc:Motion verbs).", written,
                      "its own links to itself too, in the text the save answers")
        self.assertEqual(self.source(self.target["id"]), written)
        after = store.get(self.linker["id"])[0]
        self.assertEqual(after["updated"], self.before["updated"],
                         "another document's rename is not an edit of this one")
        self.assertTrue(after["build"].get("stale"), "but its PDF no longer says what it says")
        self.assertEqual(self.page(self.linker["id"]).count('href="/doc/%s"' % self.target["id"]), 3)

    def test_a_change_of_case_or_spacing_is_a_rename_too(self):
        self.rename("Verbs of  Motion")
        self.assertIn("[see](doc:Verbs of  Motion), [](doc:Verbs of  Motion)",
                      self.source(self.linker["id"]), "a link spells the name as it is")

    def test_an_unchanged_title_rewrites_nothing(self):
        store.save(self.target["id"], self.source(self.target["id"]) + "\nMore.\n")
        self.assertIn("[](doc:verbs of MOTION)", self.source(self.linker["id"]))
        self.assertEqual(store.get(self.linker["id"])[0]["build"].get("stale"), None)

    def test_the_meta_route_renames_as_a_save_does(self):
        store.update_meta(self.target["id"], {"title": "Motion verbs", "tags": ["x"]})
        self.assertEqual(self.title_line(self.target["id"]), "Motion verbs")
        self.assertIn("[see](doc:Motion verbs)", self.source(self.linker["id"]))
        self.assertEqual(store.get(self.target["id"])[0]["tags"], ["x"])

    def test_a_link_left_hanging_by_a_name_comes_back_to_whatever_takes_the_name(self):
        waiting = self.make("W", "[](doc:Motion verbs)")
        self.assertIn('class="doclink-dead"', self.page(waiting["id"]))
        self.rename("Motion verbs")
        self.assertIn('href="/doc/%s"' % self.target["id"], self.page(waiting["id"]))

    def test_names_swapped_in_one_go_swap_their_links(self):
        a, b = self.make("Alpha"), self.make("Beta")
        linker = self.make("L", "[to a](doc:Alpha) [to b](doc:Beta)")
        store.rename_links({"alpha": "Beta", "beta": "Alpha"})
        self.assertIn("[to a](doc:Beta) [to b](doc:Alpha)", self.source(linker["id"]),
                      "each link rewritten once, by what it said before")

    def test_the_decks_exercises_follow_a_rename_in_the_studio_library(self):
        import decks
        with tempfile.TemporaryDirectory() as ex:
            was_dir = decks.set_dir(Path(ex))
            self.addCleanup(decks.set_dir, was_dir)
            was_lib, store.LIB = store.LIB, self.lib        # the studio's own library
            self.addCleanup(setattr, store, "LIB", was_lib)
            store.use_library(None)
            self.addCleanup(store.use_library, self.lib)
            store.follow_renames(decks.rename_doc_links)
            self.addCleanup(store._FOLLOWERS.remove, decks.rename_doc_links)
            deck = decks.create_deck("Motion", "en")
            card = (":::exercise flashcard\nfront: go\nback: see [](doc:Verbs of motion)[^1] "
                    "and [[go]{tl}](doc:Verbs of motion)\n:::")
            decks.add_item(deck["folder"], deck["slug"], card,
                           footnotes="[^1]: and [this](doc:verbs of motion)")
            self.rename("Motion verbs")
            item = decks.list_items(deck["folder"], deck["slug"])[0]
            got = decks.get_item(deck["folder"], deck["slug"], item["id"])
            self.assertIn("back: see [](doc:Motion verbs)[^1] and [[go]{tl}](doc:Motion verbs)",
                          got["markdown"], "a label holding a mark included")
            self.assertEqual(got["footnotes"], "[^1]: and [this](doc:Motion verbs)")

    def test_a_notes_library_tells_no_deck(self):
        told = []
        store.follow_renames(told.append)
        self.addCleanup(store._FOLLOWERS.remove, told.append)
        self.rename("Motion verbs")                 # this library is not the studio's
        self.assertEqual(told, [])


class OpenEditorTests(LibraryCase):
    """An editor sends its whole text at every save: a rename made
    elsewhere while it was open must not be undone by it (store.save's
    `since`, the edit page's names mark)."""

    def setUp(self):
        super().setUp()
        self.verbs = self.make("Verbs of motion", "Self: [me](doc:Verbs of motion).")
        self.grammar = self.make("Grammar", "[see](doc:Verbs of motion) and [](doc:Alpha).")
        self.alpha = self.make("Alpha")

    def retitled(self, doc_id, title):
        return re.sub(r"(?m)^title: .*$", "title: " + title, self.source(doc_id), count=1)

    def test_a_save_from_an_editor_left_open_follows_a_rename_made_since(self):
        _meta, text, mark = store.edit_view(self.grammar["id"])       # tab 1 opens it
        store.save(self.verbs["id"], self.retitled(self.verbs["id"], "Motion verbs"))   # tab 2
        self.assertIn("[see](doc:Motion verbs)", self.source(self.grammar["id"]))
        _meta, written = store.save(self.grammar["id"], text + "\nMore.\n", since=mark)
        self.assertIn("[see](doc:Motion verbs) and [](doc:Alpha).\n\nMore.", written,
                      "the rename made meanwhile is followed in what tab 1 sends")
        self.assertEqual(self.source(self.grammar["id"]), written)
        self.assertEqual([e["title"] for e in store.backlinks(self.verbs["id"])], ["Grammar"],
                         "and it is still linked from there")
        # without the mark (a page from before this), a save is what it was
        _meta, written = store.save(self.grammar["id"], text)
        self.assertIn("[see](doc:Verbs of motion)", written)

    def test_renames_are_followed_in_turn_a_swap_once(self):
        _meta, text, mark = store.edit_view(self.grammar["id"])
        store.save(self.verbs["id"], self.retitled(self.verbs["id"], "Motion verbs"))
        store.save(self.verbs["id"], self.retitled(self.verbs["id"], "Beta"),
                   {"existing": {self.alpha["id"]: "Motion verbs"},
                    "incoming": {self.verbs["id"]: "Beta"}})
        store.rename_links({"beta": "Alpha", "motion verbs": "Beta"})     # a swap, once
        _meta, written = store.save(self.grammar["id"], text, since=mark)
        self.assertIn("[see](doc:Alpha) and [](doc:Beta).", written,
                      "Verbs → Motion verbs → Beta → Alpha; Alpha → Motion verbs → Beta")

    def test_the_document_renamed_meanwhile_keeps_its_new_name(self):
        """the other document of a names dialog, renamed while its own
        editor was open: that editor's title says the old name, which is
        not a rename back"""
        _meta, text, mark = store.edit_view(self.alpha["id"])
        store.save(self.verbs["id"], self.retitled(self.verbs["id"], "Alpha"),
                   {"existing": {self.alpha["id"]: "Alpha (old)"},
                    "incoming": {self.verbs["id"]: "Alpha"}})
        meta, written = store.save(self.alpha["id"], text + "\nSee [me](doc:Alpha (old)).\n",
                                   since=mark)
        self.assertEqual((meta["title"], self.title_line(self.alpha["id"])),
                         ("Alpha (old)", "Alpha (old)"))
        self.assertIn("See [me](doc:Alpha (old)).", written, "its own new link stays")
        self.assertIn("[see](doc:Alpha) and [](doc:Alpha (old)).", self.source(self.grammar["id"]),
                      "each link followed its own document")
        # a title the editor did change is the editor's
        _meta, text, mark = store.edit_view(self.alpha["id"])
        store.save(self.grammar["id"], self.retitled(self.grammar["id"], "Grammar notes"))
        meta, _ = store.save(self.alpha["id"], re.sub(r"(?m)^title: .*$", "title: Alpha, mine", text),
                             since=mark)
        self.assertEqual(meta["title"], "Alpha, mine")

    def test_a_mark_of_another_server_is_no_mark(self):
        _meta, text, mark = store.edit_view(self.grammar["id"])
        store.save(self.verbs["id"], self.retitled(self.verbs["id"], "Motion verbs"))
        _meta, written = store.save(self.grammar["id"], text, since="0000beef:0")
        self.assertIn("[see](doc:Verbs of motion)", written, "nothing is known of before it")

    def test_a_new_document_follows_them_too(self):
        mark = store.names_mark()                   # the + New page opens
        store.save(self.verbs["id"], self.retitled(self.verbs["id"], "Motion verbs"))
        meta = store.create(doc("New one", "[see](doc:Verbs of motion)"), strict=True, since=mark)
        self.assertIn("[see](doc:Motion verbs)", self.source(meta["id"]))

    def test_the_pages_carry_the_mark(self):
        h = Fake()
        server.page_edit(h, self.grammar["id"])
        mark = re.search(r'data-names-mark="([^"]*)"', h.sent[1]).group(1)
        self.assertEqual(mark, store.names_mark())
        store.save(self.verbs["id"], self.retitled(self.verbs["id"], "Motion verbs"))
        h = Fake({"markdown": self.source(self.grammar["id"]).replace(
            "Motion verbs", "Verbs of motion"), "since": mark})
        server.api_save(h, self.grammar["id"])
        self.assertEqual(h.sent[0], 200)
        self.assertIn("[see](doc:Motion verbs)", h.sent[1]["markdown"])
        self.assertEqual(h.sent[1]["names_mark"], store.names_mark(),
                         "the answer says the mark the text now stands at")
        h = Fake()
        server.page_new(h)
        self.assertIn('data-names-mark="%s"' % store.names_mark(), h.sent[1])


class MarkedLabelTests(LibraryCase):
    """A label may hold a mark -- `[[il nome]{tl}](doc:…)` is what the Doc
    link picker writes when the words selected are one, `[[کتاب]{teal}](…)`
    what the hover tools write when a word of a label is recoloured -- and
    such a link is a link wherever links are read: on the page, in a
    rename, in "Linked from", in the migration, and to the hover tools,
    which must never take its name for words on the page."""

    LINES = {
        "it": ["A [[la casa]{tl}](doc:Casa) b [the [verbs]{teal}](doc:Casa) c",
               "[[y]{translit:yy}](doc:Gone) and [[z]{kana:x}](doc:Z (1))",
               "Noted^[see [the note](doc:Casa) and [[m]{tl}](doc:Casa)] and "
               "[a ^[quiet] word](doc:Casa)",
               "[[x]{tl} [w]{amber}](doc:Two marks) but [a [b] c](doc:Not one) and "
               "[[q]{nocolour}](doc:Q)"],
        "fa": ["Read [[کتاب نو]{tl}](doc:RC Notes: کتاب), then کتاب again.",
               "[[کتاب]{teal}](doc:Casa), [[کتاب]{red}](doc:Casa) and [[x]{it}](doc:Casa)",
               "✗[غلط]{teal} [فعل ✗[غلط]{teal}](doc:Casa)"],
    }

    def test_the_source_has_the_links_the_page_shows_and_no_other(self):
        for code, lines in self.LINES.items():
            for line in lines:
                md = doc("T", line, target=code)
                page = htmlgen.render_document(md, docs=INDEX)["html"]
                shown = [htmlgen_unesc(n) for n in re.findall(
                    r'class="doclink(?:-dead)?"[^>]*data-name="([^"]*)"', page)]
                found = [texgen.unescape_doc_name(l.target)
                         for l in texgen.find_doclinks(md, code)]
                self.assertEqual(sorted(found), sorted(shown), "%s: %s" % (code, line))
                self.assertTrue(found, line)
                for l in texgen.find_doclinks(md, code):
                    self.assertEqual(md[l.start:l.end],
                                     "[%s](doc:%s)" % (l.label, l.target), "offsets into the source")

    # a word of each language's own script, where it has one
    WORDS = {"fa": "کتاب", "ar": "كتاب", "ja": "漢字", "zh": "汉字", "hi": "किताब"}

    def test_every_language_finds_the_links_its_page_shows(self):
        """the `{tl}` markers are each language's own (`{ja}` in a Japanese
        document, `{fa}` and `{rtl}` in a Persian one)"""
        for code in languages.LANGS:
            w = self.WORDS.get(code, "casa")
            line = ("A [[%s]{tl}](doc:Casa), [[%s]{%s}](doc:Casa), [the [%s]{teal}](doc:Casa) "
                    "and [%s](doc:Casa)." % (w, w, code, w, w))
            md = doc("T", line, target=code)
            page = htmlgen.render_document(md, docs=INDEX)["html"]
            shown = re.findall(r'class="doclink(?:-dead)?"[^>]*data-name="([^"]*)"', page)
            found = [l.target for l in texgen.find_doclinks(md, code)]
            self.assertEqual((len(shown), found), (4, ["Casa"] * 4), code)

    def setUp(self):
        super().setUp()
        self.target = self.make("Nomi", "The nouns.", target="it")
        self.italian = self.make("Frasi", "La parola [[il nome]{tl}](doc:Nomi) e "
                                 "[the [nouns]{teal}](doc:nomi).", target="it")
        self.persian = self.make("شکل کلمه", "در [[کتاب نو]{tl}](doc:Nomi) و "
                                 "[[کتاب]{teal}](doc:Nomi) دیده می‌شوند.", target="fa")

    def test_a_rename_follows_it_and_keeps_its_label(self):
        text = self.source(self.target["id"]).replace("title: Nomi", "title: Sostantivi")
        store.save(self.target["id"], text)
        self.assertIn("La parola [[il nome]{tl}](doc:Sostantivi) e [the [nouns]{teal}]"
                      "(doc:Sostantivi).", self.source(self.italian["id"]))
        self.assertIn("در [[کتاب نو]{tl}](doc:Sostantivi) و [[کتاب]{teal}](doc:Sostantivi)",
                      self.source(self.persian["id"]))
        for linker in (self.italian, self.persian):
            page = self.page(linker["id"])
            self.assertEqual(page.count('href="/doc/%s"' % self.target["id"]), 2, page)
            self.assertNotIn("doclink-dead", page)

    def test_a_link_in_a_footnote_in_a_label_follows_as_the_link_around_it(self):
        inner = self.make("Inner", "In.", target="it")
        linker = self.make("Nest", "X [a ^[see [b](doc:Inner)] c](doc:Nomi) Y", target="it")
        self.assertEqual(self.page(linker["id"]).count('class="doclink"'), 3,
                         "the link, and the one in its footnote (the cloud and the notes' list)")
        # both renamed in one go, as a names dialog may: each name rewritten
        # where it stands (the inner one first), neither spliced into the other
        store.rename_links({"inner": "Inner two", "nomi": "Nomi two"})
        self.assertIn("X [a ^[see [b](doc:Inner two)] c](doc:Nomi two) Y", self.source(linker["id"]))
        for d, title in ((inner, "Inner two"), (self.target, "Nomi two")):
            store.save(d["id"], re.sub(r"(?m)^title: .*$", "title: " + title, self.source(d["id"])))
        self.assertEqual(self.page(linker["id"]).count('class="doclink"'), 3)

    def test_linked_from_lists_it_with_the_words_it_shows(self):
        found = store.backlinks(self.target["id"])
        links = dict((e["title"], [s["link"] for s in e["snippets"]]) for e in found)
        self.assertEqual(links, {"Frasi": ["il nome", "the nouns"],
                                 "شکل کلمه": ["کتاب نو", "کتاب"]})

    def test_the_migration_writes_it_by_name(self):
        legacy = store._create(doc("Vecchio", "[[la casa]{tl}](doc:%s) ^[and [[x]{tl}](doc:%s)]"
                                   % (self.target["uid"], self.target["uid"]), target="it"), [])
        store.migrate_links()
        self.assertIn("[[la casa]{tl}](doc:Nomi) ^[and [[x]{tl}](doc:Nomi)]",
                      self.source(legacy["id"]))

    def counted(self, md):
        page = htmlgen.render_document(md, docs=store.doc_index())["html"]
        return re.findall(r'data-fa="([^"]+)" data-occ="(\d+)"', page)

    def test_the_hover_tools_never_take_its_name_for_words_on_the_page(self):
        md = doc("T", "Read [[کتاب نو]{tl}](doc:RC Notes: کتاب), then کتاب again.", target="fa")
        self.assertEqual(self.counted(md), [("کتاب", "0")], "the page has one کتاب to colour")
        store._target_of(md)
        self.assertEqual(len(store._run_matches(md, "کتاب")), 1, "and so has the source")
        out = store.recolor_markdown(md, "کتاب", 0, "teal")
        self.assertIn("Read [[کتاب نو]{tl}](doc:RC Notes: کتاب), then [کتاب]{teal} again.", out,
                      "the word on the page is coloured, the link's name untouched")

    def test_a_word_of_a_label_recoloured_leaves_a_link(self):
        for code, md, word in (
                ("fa", doc("T", "[کتاب](doc:Nomi) and کتاب", target="fa"), "کتاب"),
                ("it", doc("T", "[[la casa]{tl}](doc:Nomi) and [casa]{tl}", target="it"), "la casa")):
            store._target_of(md)
            out = store.recolor_markdown(md, word, 0, "amber")
            self.assertIn("[[%s]{amber}](doc:Nomi)" % word, out, code)
            page = htmlgen.render_document(out, docs=store.doc_index())["html"]
            self.assertRegex(page, r'<a class="doclink" href="/doc/%s" data-name="Nomi">'
                                   r'<span class="fac fac-amber"' % self.target["id"], code)
            fm, blocks = mdparser.parse(out)
            self.assertIn(r"\textcolor{linkc}{\textcolor{faamber}{", texgen.generate(
                fm, blocks, docs=store.doc_index()), code)


def htmlgen_unesc(s):
    return s.replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


class Fake:
    """What the studio's routes use of a handler, recording the answer."""

    def __init__(self, body=None, query="", raw=b""):
        self.body, self.raw = body, raw
        self.query = urllib.parse.parse_qs(query)
        self.sent = None

    def _json_body(self):
        return self.body

    def _body(self):
        return self.raw

    def send_json(self, payload, status=200):
        self.sent = (status, payload)

    def send_html(self, text, status=200):
        self.sent = (status, text)


def renames_query(renames):
    return "renames=" + urllib.parse.quote(json.dumps(renames))


class ConflictTests(LibraryCase):
    """A name already taken is asked about, and nothing is written until the
    names given in answer are all free (store.plan_names, the 409 routes)."""

    def setUp(self):
        super().setUp()
        self.alpha = self.make("Alpha", "Self: [](doc:Alpha).")
        self.beta = self.make("Beta")
        self.gamma = self.make("Gamma")
        self.linker = self.make("Links", "[to alpha](doc:Alpha) [to beta](doc:Beta)")

    def save(self, doc_id, markdown, renames=None):
        h = Fake({"markdown": markdown, **({"renames": renames} if renames else {})})
        server.api_save(h, doc_id)
        return h.sent

    def retitled(self, doc_id, title):
        return re.sub(r"(?m)^title: .*$", "title: " + title, self.source(doc_id), count=1)

    def test_a_save_that_takes_a_name_is_asked_about_and_writes_nothing(self):
        before = self.source(self.alpha["id"])
        status, answer = self.save(self.alpha["id"], self.retitled(self.alpha["id"], "beta"))
        self.assertEqual(status, 409)
        self.assertEqual(answer["name_conflicts"], [{
            "incoming": {"ref": self.alpha["id"], "title": "beta", "file": None},
            "existing": {"id": self.beta["id"], "title": "Beta"}}])
        self.assertEqual(answer["problems"], {})
        self.assertEqual(self.source(self.alpha["id"]), before, "nothing written")
        self.assertIn("[to beta](doc:Beta)", self.source(self.linker["id"]))

    def test_the_two_may_swap_names_and_every_link_follows_its_own(self):
        status, answer = self.save(
            self.alpha["id"], self.retitled(self.alpha["id"], "Beta"),
            {"existing": {self.beta["id"]: "Alpha"}, "incoming": {self.alpha["id"]: "Beta"}})
        self.assertEqual(status, 200, answer)
        self.assertEqual((store.get(self.alpha["id"])[0]["title"],
                          store.get(self.beta["id"])[0]["title"]), ("Beta", "Alpha"))
        self.assertEqual(self.title_line(self.beta["id"]), "Alpha", "its front matter too")
        self.assertIn("[to alpha](doc:Beta) [to beta](doc:Alpha)", self.source(self.linker["id"]))
        self.assertIn("Self: [](doc:Beta).", answer["markdown"], "its own link follows it")
        page = self.page(self.linker["id"])
        self.assertIn('<a class="doclink" href="/doc/%s" data-name="Beta">to alpha</a>'
                      % self.alpha["id"], page)

    def test_the_document_being_saved_may_take_another_name_instead(self):
        status, answer = self.save(self.alpha["id"], self.retitled(self.alpha["id"], "Beta"),
                                   {"incoming": {self.alpha["id"]: "Alpha and beta"},
                                    "existing": {self.beta["id"]: "Beta"}})
        self.assertEqual(status, 200, answer)
        self.assertIn("title: Alpha and beta\n", answer["markdown"], "the title line it was given")
        self.assertEqual(self.source(self.alpha["id"]), answer["markdown"])
        self.assertIn("[to alpha](doc:Alpha and beta) [to beta](doc:Beta)",
                      self.source(self.linker["id"]))

    def test_names_given_that_are_taken_or_empty_are_asked_for_again(self):
        text = self.retitled(self.alpha["id"], "Beta")
        before = self.source(self.alpha["id"])
        status, answer = self.save(self.alpha["id"], text,
                                   {"incoming": {self.alpha["id"]: "gamma"},
                                    "existing": {self.beta["id"]: "Beta"}})
        self.assertEqual(status, 409)
        self.assertEqual(answer["problems"], {
            "incoming:" + self.alpha["id"]:
                "“gamma” is already the name of another document — choose another name"})
        status, answer = self.save(self.alpha["id"], text,
                                   {"incoming": {self.alpha["id"]: "Beta"},
                                    "existing": {self.beta["id"]: "BETA"}})
        self.assertEqual((status, sorted(answer["problems"])),
                         (409, ["existing:" + self.beta["id"], "incoming:" + self.alpha["id"]]),
                         "both left on one name: both asked again")
        status, answer = self.save(self.alpha["id"], text,
                                   {"incoming": {self.alpha["id"]: "  "},
                                    "existing": {self.beta["id"]: "Beta"}})
        self.assertEqual(answer["problems"], {"incoming:" + self.alpha["id"]:
                                              "A document needs a name — give it one"})
        self.assertEqual(self.source(self.alpha["id"]), before, "nothing written, ever")
        self.assertEqual(store.get(self.beta["id"])[0]["title"], "Beta")

    def test_a_name_holding_a_bar_is_refused_as_it_would_split_a_table_cell(self):
        table = self.make("Table", "| word | see |\n|---|---|\n| هم | [link](doc:Alpha) |\n")
        before = (self.source(self.alpha["id"]), self.source(table["id"]))
        status, answer = self.save(self.alpha["id"], self.retitled(self.alpha["id"], "Alpha | ham"))
        self.assertEqual((status, answer["name_conflicts"]), (409, []))
        self.assertEqual(answer["problems"], {"incoming:" + self.alpha["id"]: store._NO_BAR})
        self.assertEqual(answer["fields"], {"incoming:" + self.alpha["id"]: {
            "title": "Alpha | ham", "name": "Alpha | ham", "file": None}},
            "what the dialog needs to ask for a field of its own")
        self.assertEqual((self.source(self.alpha["id"]), self.source(table["id"])), before,
                         "nothing written: no link in a table was given a bar")
        status, answer = self.save(self.alpha["id"], self.retitled(self.alpha["id"], "Beta"),
                                   {"incoming": {self.alpha["id"]: "Beta"},
                                    "existing": {self.beta["id"]: "Beta | old"}})
        self.assertEqual((status, answer["problems"]),
                         (409, {"existing:" + self.beta["id"]: store._NO_BAR}),
                         "nor may a name given in the dialog hold one")
        h = Fake({"markdown": doc("Uploaded | file")})
        server.api_create(h)
        self.assertEqual((h.sent[0], h.sent[1]["problems"]), (409, {"incoming:new": store._NO_BAR}))
        status, answer = self.save(self.alpha["id"], self.retitled(self.alpha["id"], "Alpha, ham"))
        self.assertEqual(status, 200, answer)
        page = self.page(table["id"])
        self.assertRegex(page, r'<td class="a-l"><a class="doclink" href="/doc/%s" data-name="Alpha, ham">'
                               r'link</a></td>' % self.alpha["id"], "the cell holds its link whole")

    def test_the_migration_leaves_a_link_by_uid_to_a_name_holding_a_bar(self):
        old = self.legacy("Old | name")
        md = doc("Table", "| a | b |\n|---|---|\n| x | [see](doc:%s) |\n" % old["uid"])
        linker = self.legacy("Linker", md[md.index("\n\n") + 2:])
        with contextlib.redirect_stderr(io.StringIO()):
            store.migrate_links()
        self.assertIn("[see](doc:%s)" % old["uid"], self.source(linker["id"]),
                      "the uid reaches it, and splits no cell")
        self.assertIn('<a class="doclink" href="/doc/%s"' % old["id"], self.page(linker["id"]))

    def test_a_new_document_or_a_pasted_one_is_asked_about_too(self):
        h = Fake({"markdown": doc("beta", "About [me](doc:beta).")})
        server.api_create(h)
        self.assertEqual(h.sent[0], 409)
        self.assertEqual(h.sent[1]["name_conflicts"][0]["incoming"]["ref"], store.NEW_REF)
        self.assertEqual(len(self.made()), 4, "nothing made")
        h = Fake({"markdown": doc("beta", "About [me](doc:beta)."),
                  "renames": {"existing": {self.beta["id"]: "Beta (old)"},
                              "incoming": {store.NEW_REF: "beta"}}})
        server.api_create(h)
        self.assertEqual(h.sent[0], 201, h.sent)
        new = h.sent[1]["meta"]["id"]
        self.assertEqual(self.title_line(self.beta["id"]), "Beta (old)")
        self.assertIn("[to beta](doc:Beta (old))", self.source(self.linker["id"]),
                      "the library's links follow the document renamed")
        self.assertIn("About [me](doc:beta).", self.source(new),
                      "the new text's own link was written for it, and stays with it")

    def test_an_upload_asks_for_its_header_first_then_for_a_name(self):
        text = "# Gamma\n\nSee [this](doc:Gamma).\n"
        h = Fake({"markdown": text, "check_header": True, "name": "gamma.md"})
        server.api_create(h)
        self.assertEqual(h.sent[0], 422)
        header = {"title": "Gamma", "subtitle": "", "note": "", "lang": "en", "target": "en"}
        h = Fake({"markdown": text, "header": header, "name": "gamma.md"})
        server.api_create(h)
        self.assertEqual((h.sent[0], h.sent[1]["name_conflicts"][0]["incoming"]["file"]),
                         (409, "gamma.md"))
        h = Fake({"markdown": text, "header": header, "name": "gamma.md",
                  "renames": {"incoming": {store.NEW_REF: "Gamma, uploaded"},
                              "existing": {self.gamma["id"]: "Gamma"}}})
        server.api_create(h)
        self.assertEqual(h.sent[0], 201, h.sent)
        self.assertIn("See [this](doc:Gamma, uploaded).", self.source(h.sent[1]["meta"]["id"]))

    def test_a_zip_is_asked_about_names_taken_here_and_within_it(self):
        data = zip_of({"a.md": doc("Beta", "[the twin](doc:Twin)"),
                       "b.md": doc("Twin", "first"), "c.md": doc("twin", "second")})
        up = Fake(raw=data)
        server.api_import_zip(up)
        self.assertEqual(up.sent[0], 409)
        self.assertEqual(up.sent[1]["name_conflicts"], [
            {"incoming": {"ref": "a.md", "title": "Beta", "file": "a.md"},
             "existing": {"id": self.beta["id"], "title": "Beta"}},
            {"incoming": {"ref": "c.md", "title": "twin", "file": "c.md"},
             "existing": {"incoming_ref": "b.md", "title": "Twin", "file": "b.md"}}])
        self.assertEqual(len(self.made()), 4, "nothing made")
        answer = {"incoming": {"a.md": "Beta, zipped", "b.md": "Twin one", "c.md": "Twin two"},
                  "existing": {self.beta["id"]: "Beta"}}
        up = Fake(raw=data, query=renames_query(answer))
        server.api_import_zip(up)
        self.assertEqual(up.sent[0], 201, up.sent)
        made = dict((m["title"], m["id"]) for m in up.sent[1]["docs"])
        self.assertEqual(sorted(made), ["Beta, zipped", "Twin one", "Twin two"])
        self.assertIn("[the twin](doc:Twin one)", self.source(made["Beta, zipped"]),
                      "a link between two of its files follows the one it named")
        up = Fake(raw=data, query="renames=not-json")
        server.api_import_zip(up)
        self.assertEqual(up.sent[0], 400)

    def backup_of(self, *docs):
        """a backup of another library holding these (title, body) documents"""
        with tempfile.TemporaryDirectory() as other:
            was = store.use_library(Path(other))
            try:
                made = [self.make(t, b) for t, b in docs]
                return library_zip(Path(other)), made
            finally:
                store.use_library(was)

    def restore(self, data, replace=False, renames=None):
        h = Fake(raw=data, query="&".join(
            ["replace=1"] * bool(replace) + ([renames_query(renames)] if renames else [])))
        server.api_import_library(h)
        return h.sent

    def test_a_backup_asks_about_another_document_with_a_name_taken(self):
        data, (shared, other) = self.backup_of(("Gamma", "backed up"),
                                               ("Other", "[see](doc:Gamma)"))
        status, answer = self.restore(data)
        self.assertEqual(status, 409)
        self.assertEqual(answer["name_conflicts"], [{
            "incoming": {"ref": shared["id"], "title": "Gamma",
                         "file": "english/" + shared["id"]},
            "existing": {"id": self.gamma["id"], "title": "Gamma"}}])
        self.assertEqual(len(self.made()), 4, "nothing written")
        renames = {"incoming": {shared["id"]: "Gamma (backup)"},
                   "existing": {self.gamma["id"]: "Gamma"}}
        status, answer = self.restore(data, renames=renames)
        self.assertEqual((status, sorted(answer["restored"])), (201, sorted([shared["id"], other["id"]])))
        self.assertEqual(self.title_line(shared["id"]), "Gamma (backup)")
        self.assertEqual(store.get(shared["id"])[0]["uid"], shared["uid"], "still the same document")
        self.assertIn("[see](doc:Gamma (backup))", self.source(other["id"]),
                      "the backup's link follows the backup's document")
        # the same documents again: the SAME ids, so kept, then replaced --
        # which the same answer names alike
        status, answer = self.restore(data, renames=renames)
        self.assertEqual((status, answer["restored"], sorted(answer["kept"])),
                         (201, [], sorted([shared["id"], other["id"]])))
        status, answer = self.restore(data, replace=True, renames=renames)
        self.assertEqual((status, sorted(answer["restored"])), (201, sorted([shared["id"], other["id"]])))
        self.assertEqual(self.title_line(shared["id"]), "Gamma (backup)")
        self.assertEqual(self.title_line(self.gamma["id"]), "Gamma")

    def test_the_replace_pass_of_a_backup_asks_about_the_names_its_first_pass_gave(self):
        """Pass 1 renamed the backup's Delta to the name its kept Alpha had
        -- free then, Alpha being called Gamma now; pass 2 (Replace) brings
        that Alpha back under its old name, and the same answer clashes.
        The 409 must pair the two, so a dialog opened on it alone has a
        field for each (it had none: a names dialog to cancel, no more)."""
        data, (alpha, delta) = self.backup_of(("RB Alpha", "[the delta](doc:RB Delta)"),
                                              ("RB Delta", "delta"))
        with tempfile.TemporaryDirectory() as other:     # restore into a fresh library
            was = store.use_library(Path(other))
            self.addCleanup(store.use_library, was)
            self.assertEqual(self.restore(data)[0], 201)
            store.save(alpha["id"], self.retitled(alpha["id"], "RB Gamma"))
            store.delete(delta["id"])
            newer = self.make("RB Delta", "a new one")
            status, answer = self.restore(data)
            self.assertEqual((status, answer["name_conflicts"][0]["existing"]["id"]),
                             (409, newer["id"]))
            given = {"incoming": {delta["id"]: "RB Alpha"}, "existing": {newer["id"]: "RB Delta"}}
            status, answer = self.restore(data, renames=given)
            self.assertEqual((status, answer["kept"]), (201, [alpha["id"]]))
            status, answer = self.restore(data, replace=True, renames=given)
            self.assertEqual(status, 409)
            self.assertEqual(answer["problems"], {"incoming:" + delta["id"]:
                             "“RB Alpha” is already the name of another document — choose another name"})
            self.assertEqual(answer["name_conflicts"], [{
                "incoming": {"ref": delta["id"], "title": "RB Delta", "name": "RB Alpha",
                             "file": "english/" + delta["id"]},
                "existing": {"incoming_ref": alpha["id"], "title": "RB Alpha",
                             "file": "english/" + alpha["id"]}}],
                "the name refused, paired with the document that wants it too")
            self.assertEqual(answer["fields"], {"incoming:" + delta["id"]: {
                "title": "RB Delta", "name": "RB Alpha", "file": "english/" + delta["id"]}})
            given["incoming"][delta["id"]] = "RB Delta, backed up"
            status, answer = self.restore(data, replace=True, renames=given)
            self.assertEqual(status, 201, answer)
            self.assertEqual([store.get(d)[0]["title"] for d in (alpha["id"], delta["id"], newer["id"])],
                             ["RB Alpha", "RB Delta, backed up", "RB Delta"])
            self.assertIn("[the delta](doc:RB Delta, backed up)", self.source(alpha["id"]),
                          "the backup's link follows the backup's document")

    def test_a_backup_holding_two_documents_of_one_name_is_asked_about(self):
        with tempfile.TemporaryDirectory() as other:
            was = store.use_library(Path(other))
            try:
                one = store._create(doc("Delta", "one"), [])
                two = store._create(doc("delta", "two"), [])      # as a legacy library had
                data = library_zip(Path(other))
            finally:
                store.use_library(was)
        status, answer = self.restore(data)
        self.assertEqual(status, 409)
        pair = answer["name_conflicts"][0]
        self.assertEqual({pair["incoming"]["ref"], pair["existing"]["incoming_ref"]},
                         {one["id"], two["id"]})

    def test_a_notes_library_asks_the_same(self):
        with tempfile.TemporaryDirectory() as content:
            with notes.library(content):
                first = notes.create(content, "after", "sub", "1.1-a", "en")
                second = notes.create(content, "after", "sub", "1.2-b", "en")
                text = self.source(second["id"]).replace("title: A note 2", "title: A note")
                status, answer = self.save(second["id"], text)
                self.assertEqual((status, answer["name_conflicts"][0]["existing"]["id"]),
                                 (409, first["id"]))
            self.assertEqual(store.get(self.alpha["id"])[0]["title"], "Alpha",
                             "and the studio's library is none of its business")


class LongChapterTests(LibraryCase):
    """A long chapter -- the studio's own run to a hundred kilobytes, with a
    thousand brackets and a formula or two -- is read in no time wherever
    its links are looked for: a rename, a new document, the migration (at
    every start), "Linked from" (on every document page), the hover tools
    and the card's counts.  Each of those reads every document of the
    library, and the formula regex, run over a whole chapter, looked for
    its `]{math}` from every `[` to the end of the text: seconds a chapter,
    seconds a save.  The limit is generous for a slow machine; it was
    seconds, it is a millisecond or two."""

    PARAS = 200
    LIMIT = 0.5

    def chapter(self, title, links=(), target="en"):
        para = ("Paragraph %d holds [a word]{teal}, an interval [0, 1) and a [bracketed] "
                "aside, a [link out](https://example.org/%d), [another]{amber} mark and a "
                "table reference [7-6] of the kind a long chapter has.")
        paras = [para % (n, n) for n in range(self.PARAS)]
        paras[0] += " A formula first, [x^2 + y^2]{math}."
        for n, name in links:
            paras[n] += " See [the other one](doc:%s)." % name
        return doc(title, "\n\n".join(paras), target)

    def timed(self, what, fn, limit=LIMIT):
        t = time.perf_counter()
        out = fn()
        took = time.perf_counter() - t
        self.assertLess(took, limit, "%s took %.3f s" % (what, took))
        return out

    # A GLOSSARY OR A TABLE HAS NO BLANK LINE IN IT, however long it grows,
    # and a paragraph at a time it was still one piece: five hundred items
    # took a third of a second a read, every read of the library (a new
    # document, a rename, "Linked from" on every page, every start) paid it,
    # and a formula in the last item hid the link of an earlier one from all
    # of them, though the page shows it.  inline() is handed an item and a
    # cell on its own, and so they are read here: a millisecond.  The limits
    # are tight -- one text read, 50 ms; a library of three such, 0.2 s --
    # and the old reading takes a third of a second for either.
    ITEMS = 500
    READ_LIMIT = 0.05
    LIBRARY_LIMIT = 0.2

    def glossary(self, title, name, formula=False):
        items = ["- [کتاب]{translit:ketab} = *book* (see [note %d])" % n
                 for n in range(self.ITEMS)]
        items[self.ITEMS // 2] += " and [the lesson](doc:%s)" % name
        if formula:
            items[-1] += " with [x^2]{math}"
        return doc(title, "\n".join(items), "fa")

    def long_table(self, title, name, formula=False):
        rows = ["| [واژه]{translit:važe} %d | (see [n %d]) |" % (n, n)
                for n in range(self.ITEMS)]
        rows[self.ITEMS // 2] = "| [the lesson](doc:%s) | (see [n]) |" % name
        if formula:
            rows[-1] = "| [y^2]{math} | z |"
        return doc(title, "| a | b |\n|---|---|\n" + "\n".join(rows), "fa")

    def test_a_long_list_or_table_is_read_an_item_and_a_cell_at_a_time(self):
        for shape in (self.glossary, self.long_table):
            for formula in (False, True):
                md = shape("G", "Two", formula)
                what = shape.__name__ + (" ending in a formula" if formula else "")
                found = self.timed(what, lambda: texgen.find_doclinks(md, "fa"), self.READ_LIMIT)
                self.assertEqual([l.target for l in found], ["Two"], what)
                blocks = mdparser.parse(md)[1]
                self.timed(what + ": the card's counts",
                           lambda: htmlgen.stats(md, blocks, "fa"), self.READ_LIMIT)
                store._target_of(md)
                self.timed(what + ": the hover tools' runs",
                           lambda: store._run_matches(md, "کتاب"), self.READ_LIMIT)

    def test_a_formula_further_on_hides_no_link_the_page_shows(self):
        """a later item, cell, row or line of a box is not the piece the
        link is in; a paragraph's next line and an item's indented one are,
        and a formula there hides it on the page and here alike"""
        shown_and_found = [
            "- see [n] here\n- and [it](doc:Two)\n- where [x^2]{math}",
            "1. see [n] here\n2. and [it](doc:Two)\n   more\n3. where [x^2]{math}",
            "| a | b | c |\n|---|---|---|\n| [n] | [it](doc:Two) | [y^2]{math} |",
            "| a | b |\n|---|---|\n| [n] | [it](doc:Two) |\n| [y^2]{math} | z |",
            "## A [heading] and [it](doc:Two)\nthen [z]{math}",
            "> - see [n]\n> - [it](doc:Two)\n> - [z]{math}",
            "> see [n] and [it](doc:Two)\n> > then [z]{math}",
            "Text[^1].\n[^1]: see [n] and [it](doc:Two)\n- then [z]{math}",
            "see [a\nlabel](doc:Two) here",
            "- a [long\n  label](doc:Two)\n- [z]{math}",
        ]
        hidden_on_both = [
            "see [n] and [it](doc:Two)\nthen [z]{math}",
            "- see [n] and [it](doc:Two)\n  then [z]{math}",
            "Text[^1].\n[^1]: see [n] and [it](doc:Two)\n  then [z]{math}",
        ]
        for body in shown_and_found + hidden_on_both:
            md = doc("T", body)
            page = htmlgen.render_document(md, docs=INDEX)["html"]
            shown = sorted(set(re.findall(r'class="doclink(?:-dead)?"[^>]*data-name="([^"]*)"', page)))
            found = [l.target for l in texgen.find_doclinks(md, "en")]
            want = ["Two"] if body in shown_and_found else []
            self.assertEqual((shown, found), (want, want), body)

    def test_a_library_of_long_lists_and_tables_is_renamed_created_and_migrated_quickly(self):
        target = self.make("Two", "The lesson linked to.")
        made = [self.timed("a glossary made", lambda: store.create(
                    self.glossary("Glossary", "Two")), self.LIBRARY_LIMIT),
                self.timed("one ending in a formula", lambda: store.create(
                    self.glossary("Glossary ending in a formula", "Two", True)), self.LIBRARY_LIMIT),
                self.timed("a table ending in one", lambda: store.create(
                    self.long_table("Table", "Two", True)), self.LIBRARY_LIMIT)]
        self.timed("a new document", lambda: store.create(doc("Four"), strict=True),
                   self.LIBRARY_LIMIT)
        self.timed("the migration", store.migrate_links, self.LIBRARY_LIMIT)
        linked = self.timed("a page's Linked from", lambda: store.backlinks(target["id"]),
                            self.LIBRARY_LIMIT)
        self.assertEqual([e["title"] for e in linked],
                         ["Glossary", "Glossary ending in a formula", "Table"])
        text = self.source(target["id"]).replace("title: Two", "title: Two bis")
        self.timed("a rename", lambda: store.save(target["id"], text), self.LIBRARY_LIMIT)
        for meta in made:
            self.assertEqual(re.findall(r"\(doc:([^)]*)\)", self.source(meta["id"])), ["Two bis"],
                             "%s: its link followed it" % meta["title"])

    def test_the_links_of_a_long_chapter_are_found_quickly(self):
        md = self.chapter("One", [(100, "Two"), (150, "Three")])
        found = self.timed("find_doclinks", lambda: texgen.find_doclinks(md, "en"))
        self.assertEqual([l.target for l in found], ["Two", "Three"])
        self.assertEqual(self.timed("rewrite_links", lambda: store.rewrite_links(
            md, lambda label, name: name + " bis"))[1], 2)
        self.timed("the card's counts", lambda: htmlgen.stats(md, mdparser.parse(md)[1], "en"))
        store._target_of(md)
        self.timed("the hover tools' runs", lambda: store._run_matches(md, "a word"))

    def test_a_library_of_long_chapters_is_renamed_created_and_migrated_quickly(self):
        target = self.make("Two", "The chapter linked to.")
        linking = self.timed("a long chapter made", lambda: store.create(
            self.chapter("One", [(100, "Two"), (150, "Two")])))
        self.timed("another made", lambda: store.create(self.chapter("Three")))
        self.timed("a new document", lambda: store.create(doc("Four"), strict=True))
        self.timed("the migration", store.migrate_links)
        self.timed("a page's Linked from", lambda: store.backlinks(target["id"]))
        text = self.source(target["id"]).replace("title: Two", "title: Two bis")
        self.timed("a rename", lambda: store.save(target["id"], text))
        self.assertEqual(self.source(linking["id"]).count("(doc:Two bis)"), 2,
                         "and the long chapter's links followed it")


class BacklinksTests(LibraryCase):
    """The document page's "Linked from": every document of the library whose
    text links here, found as the page finds a link's document."""

    def setUp(self):
        super().setUp()
        self.verbs = self.make("Verbs of motion", "Self: [me](doc:Verbs of motion).")
        self.grammar = self.make("Grammar", "## About [the verbs](doc:verbs OF motion)\n\n"
                                 "- The first chapter is about a great many things, among them, "
                                 "and not the least of them, the ones in [](doc:Verbs of motion), "
                                 "and then it goes on for a good while, and on, and on, and on, until the end.\n\n"
                                 "| a | b ⏎[x](doc:Verbs of motion) | c |\n")
        self.persian = self.make("شکل کلمه", "کلمه‌ها در [فعل‌های حرکتی](doc:Verbs of motion) "
                                             "هم دیده می‌شوند.", target="fa")
        self.legacy = store._create(doc("Old links", "Before names: [old](doc:%s)." % self.verbs["uid"]), [])
        self.elsewhere = self.make("Elsewhere", "[not here](doc:Grammar)")

    def test_every_document_that_links_here_by_name_or_old_uid(self):
        found = store.backlinks(self.verbs["id"])
        self.assertEqual([e["title"] for e in found], ["Grammar", "Old links", "شکل کلمه"],
                         "by title; not itself, not a document linking elsewhere")
        grammar = found[0]["snippets"]
        self.assertEqual(grammar[0], {"before": "About ", "link": "the verbs", "after": ""})
        self.assertEqual(grammar[1]["link"], "Verbs of motion", "an empty label shows the title")
        self.assertTrue(grammar[1]["before"].startswith("…") and grammar[1]["after"].endswith("…"),
                        "the words around it, cut between two words: %r" % grammar[1])
        self.assertLessEqual(len(grammar[1]["before"]), store.BACKLINK_CONTEXT + 1)
        self.assertEqual(grammar[2], {"before": "a · b ", "link": "x", "after": " · c"},
                         "a table row reads as its cells, on one line")
        self.assertEqual(found[1]["snippets"], [{"before": "Before names: ", "link": "old",
                                                 "after": "."}])
        self.assertEqual(found[2]["snippets"], [{"before": "کلمه‌ها در ", "link": "فعل‌های حرکتی",
                                                 "after": " هم دیده می‌شوند."}])
        self.assertEqual(store.backlinks(self.elsewhere["id"]), [])

    def test_a_deleted_document_is_linked_from_nothing_until_its_name_is_back(self):
        store.delete(self.verbs["id"])
        again = self.make("Verbs of motion", "Written again.")
        self.assertEqual([e["title"] for e in store.backlinks(again["id"])], ["Grammar", "شکل کلمه"],
                         "the links by name reach it; the old uid is the old document's")

    def page(self, doc_id):
        h = Fake()
        server.page_doc(h, doc_id)
        self.assertEqual(h.sent[0], 200)
        return h.sent[1]

    def test_the_page_offers_the_drawer_with_the_count(self):
        page = self.page(self.verbs["id"])
        self.assertIn('id="btn-backlinks"', page)
        self.assertIn("↩ Linked from (3)", page)
        drawer = page[page.index('id="linkspane"'):]
        self.assertIn('<a class="link-doc" dir="auto" href="/doc/%s">Grammar</a>' % self.grammar["id"],
                      drawer)
        self.assertIn('<p class="link-snippet" dir="auto">About <mark>the verbs</mark></p>', drawer)
        empty = self.page(self.elsewhere["id"])
        self.assertIn("↩ Linked from (0)", empty)
        self.assertIn('<p class="links-empty">No document links here yet.</p>', empty)

    def test_a_notes_drawer_links_inside_the_notes(self):
        with tempfile.TemporaryDirectory() as content:
            with notes.library(content):
                first = notes.create(content, "after", "sub", "1.1-a", "en")
                second = notes.create(content, "after", "sub", "1.2-b", "en")
                store.save(second["id"], self.source(second["id"]) + "\nSee [the first](doc:A note).\n")
                was = server.use_mount("/books/english/b/notes", html_only=True)
                try:
                    page = self.page(first["id"])
                finally:
                    server.restore_mount(was)
        self.assertIn("↩ Linked from (1)", page)
        self.assertIn('href="/books/english/b/notes/doc/%s">A note 2</a>' % second["id"], page)


if __name__ == "__main__":
    unittest.main()
