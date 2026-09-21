"""English explained in English: a dictionary that defines its words in their
own language, and the whole of an entry for a reader who asks for it.

    python3 -m unittest discover -s tests -p test_definitions.py

Standard library only, under any Python.  The dictionaries are a few rows
each, built here as tests/test_wordserver.py builds its own, with
lib/lookup.py pointed at them so that nothing is read from dict/; the
server's lookup is asked through its handler, with nothing listening.
"""
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
LIB = os.path.join(ROOT, "lib")
for _p in (LIB, ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import lookup  # noqa: E402

# Wiktionary's `run`, cut down: six senses and their tags, one of them obsolete
RUN = [("To move swiftly.", "intransitive"),
       ("To flee.", "obsolete"),
       ("To go at a fast pace.", "intransitive"),
       ("To cover a distance by running.", "transitive"),
       ("To compete in a race.", "intransitive,transitive"),
       ("To manage a business.", "transitive")]
HOUSE = [("A structure serving as an abode of human beings.", "countable"),
         ("A household.", "countable")]


def _dict(path, code, rows, meta=()):
    c = lookup.create(path)
    for head, pos, senses in rows:
        cur = c.execute("INSERT INTO entry (headword, pos, sense, sense_tags) "
                        "VALUES (?,?,?,?)",
                        (head, pos, "\n".join(s for s, _t in senses),
                         "\n".join(t for _s, t in senses)))
        c.execute("INSERT INTO form (form, entry_id, note) VALUES (?,?,?)",
                  (head, cur.lastrowid, ""))
    c.executemany("INSERT INTO meta (key, value) VALUES (?,?)",
                  [("lang", code), ("source", "a fixture"), ("licence", "none")]
                  + list(meta))
    c.commit()
    c.close()


def _forget():
    for conn, _stamp in (getattr(lookup._CONNS, "map", None) or {}).values():
        if conn is not None:
            conn.close()
    lookup._CONNS.map = {}


class Definitions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        td = tempfile.TemporaryDirectory()
        cls.addClassCleanup(td.cleanup)
        _dict(os.path.join(td.name, "en.db"), "en",
              [("run", "verb", RUN), ("house", "noun", HOUSE)])
        _dict(os.path.join(td.name, "it.db"), "it",
              [("casa", "noun", [("house", ""), ("home", "")])])
        # a dictionary from another edition, saying what its senses are in
        _dict(os.path.join(td.name, "fr.db"), "fr",
              [("maison", "noun", [("Bâtiment servant d'habitation.", "")])],
              meta=[("senses_lang", "fr")])
        was = lookup.DICT_DIR
        lookup.DICT_DIR = td.name
        _forget()

        def back():
            lookup.DICT_DIR = was
            _forget()
        cls.addClassCleanup(back)

    def test_a_dictionary_defines_its_words_only_in_their_own_language(self):
        self.assertTrue(lookup.defines("en"), "English, explained in English")
        self.assertFalse(lookup.defines("it"), "Italian explained in English is translated")
        self.assertTrue(lookup.defines("fr"), "an edition that says its senses are French")
        self.assertFalse(lookup.defines("de"), "and no dictionary defines nothing")
        self.assertIsNone(lookup.senses_language("de"))
        self.assertEqual(lookup.senses_language("it"), "en")

    def test_the_rest_of_an_entry_is_ranked_as_its_first_three_were(self):
        r = lookup.look_up("en", "run")
        hit = r["words"][0]["hits"][0]
        first = ["To move swiftly.", "To go at a fast pace.", "To cover a distance by running."]
        self.assertEqual((hit["senses"], hit["buried"]), (first, 3))
        self.assertNotIn("more", hit, "nothing past the first three unless asked")
        self.assertIs(lookup.more_senses(r), r)
        self.assertEqual(hit["senses"], first, "and the first three stay as they were")
        self.assertEqual(hit["more"], ["To compete in a race.", "To manage a business.", "To flee."],
                         "the rest in rank order: the obsolete sense last")
        self.assertEqual(hit["more_marks"], ["intransitive,transitive", "transitive", "obsolete"])
        house = lookup.more_senses(lookup.look_up("en", "house"))["words"][0]["hits"][0]
        self.assertNotIn("more", house, "an entry with nothing buried gains nothing")
        self.assertIsNone(lookup.more_senses(None))

    def test_the_server_says_so_and_sends_the_rest_only_when_asked(self):
        import serve
        h = object.__new__(serve.Handler)
        sent = []
        h.send_json = lambda payload, status=200: sent.append(payload)
        quiet = types.SimpleNamespace(attach=lambda *a, **k: None)
        with mock.patch.dict(sys.modules, {"verbs": quiet}):
            h._lookup("en", {"about": 1}, "it")
            self.assertTrue(sent[-1]["definitions"], "English, glossed in Italian")
            h._lookup("it", {"about": 1}, "en")
            self.assertFalse(sent[-1]["definitions"])
            h._lookup("de", {"about": 1}, "en")
            self.assertFalse(sent[-1]["definitions"], "no dictionary at all")
            h._lookup("en", {"text": "run"}, "it")
            self.assertNotIn("more", sent[-1]["words"][0]["hits"][0])
            h._lookup("en", {"text": "run", "senses": "all"}, "it")
            hit = sent[-1]["words"][0]["hits"][0]
            self.assertEqual(len(hit["senses"]), 3)
            self.assertEqual(sorted(hit["senses"] + hit["more"]), sorted(s for s, _t in RUN))


if __name__ == "__main__":
    unittest.main()
