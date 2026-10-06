# SPDX-License-Identifier: GPL-3.0-or-later
"""WHAT FOLLOWS A PERSON, A0.5.0: "keep going" AND THE LEVELS' NAMES.

    python3 -m unittest tests/test_prefs_levels.py

lib/prefs.py keeps the settings that follow a person from one device to
another, and lib/prefs.js asks for them at load and tells the toolbox of every
change.  Two things joined them in a0.5.0:

- `bk_cont`, "keep going" (the recording goes on into the next line): "1" or
  "0", on every device, as `bk_stopbnd` is;
- the names a person gave the levels of a book, one key per language and per
  level, `bk_lvl:<language code>:<pass key>` (`bk_lvl:fa:vocal`) -- the only
  key the toolbox knows by its BEGINNING, which is why the whole key is held
  to a strict pattern and the value to 12 characters ("never a risky key").

Held here: the server side (what is accepted, what is refused, the last change
winning), the page side driven in Deno over the real lib/prefs.js with a
stand-in for the browser (a value brought is stored, worn and announced as
`parseh:pref`; what the page writes is sent, and only what the toolbox would
keep), and the two sides agreeing on the key, the limit and the list.

NOTHING HERE WRITES config/: every store is a temporary file.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
LIB = os.path.join(ROOT, "lib")
sys.path.insert(0, LIB)
import languages                                               # noqa: E402
import prefs                                                   # noqa: E402

DENO = shutil.which("deno") or os.path.expanduser("~/miniconda3/envs/ilya-frank/bin/deno")
PREFS_JS = os.path.join(LIB, "prefs.js")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Store(unittest.TestCase):
    """lib/prefs.py over a temporary file."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory(prefix="parseh-prefs-")
        self.path = os.path.join(self._td.name, "config", "prefs.json")
        p = mock.patch.object(prefs, "STORE", self.path)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self._td.cleanup)

    def put(self, key, v, at=None, by="a computer"):
        return prefs.set_settings({key: {"v": v, "at": at if at is not None else time.time()}}, by)

    def kept(self):
        return prefs.settings()


class Keys(Store):
    def test_the_exact_keys(self):
        for key in ("bk_rate", "bk_gap", "bk_skip", "bk_stopbnd", "bk_cont", "parseh_theme"):
            with self.subTest(key=key):
                self.assertTrue(prefs.follows(key))
        self.assertIn("bk_cont", prefs.KEYS)

    def test_a_level_name_key(self):
        for key in ("bk_lvl:fa:vocal", "bk_lvl:ja:aloud", "bk_lvl:zh:alt", "bk_lvl:ko:chunks",
                    "bk_lvl:nap:bare", "bk_lvl:fa:a1_b2"):
            with self.subTest(key=key):
                self.assertTrue(prefs.follows(key))

    def test_no_other_key_follows(self):
        for key in ("bk_lvl:", "bk_lvl:fa", "bk_lvl:fa:", "bk_lvl::vocal", "bk_lvl:../x",
                    "bk_lvl:fa:../x", "bk_lvl:fa:vocal/x", "bk_lvl:fa:vocal ", " bk_lvl:fa:vocal",
                    "bk_lvl:FA:vocal", "bk_lvl:fa:Vocal", "bk_lvl:f:vocal", "bk_lvl:fran:vocal",
                    "bk_lvl:fa:1vocal", "bk_lvl:fa:" + "a" * 17, "bk_lvl:fa:vocal:x",
                    "bk_lvl:fa:vocal\n", "xbk_lvl:fa:vocal", "bk_lvl:fa:vo cal",
                    "bk_no1", "bk_nogloss", "bk_typo", "bk_pos:/books/x/", "bk_hoverpause",
                    "parseh_zoom", "", None, 7):
            with self.subTest(key=key):
                self.assertFalse(prefs.follows(key))

    def test_the_stale_comment_is_mended(self):
        """The note on KEYS named a key that never existed (bk_p1): which
        levels are hidden is kept as bk_no1 ... bk_no5."""
        text = read(os.path.join(LIB, "prefs.py"))
        self.assertNotIn("bk_p1", text)
        self.assertIn("bk_no1 ... bk_no5", text)


class Accepting(Store):
    def test_keep_going_is_remembered_as_one_or_nought(self):
        self.put("bk_cont", "0")
        self.assertEqual(self.kept()["bk_cont"]["v"], "0")
        self.put("bk_cont", "1", at=time.time() + 5)
        self.assertEqual(self.kept()["bk_cont"]["v"], "1")
        # a number a page wrote as a number is the same thing
        self.put("bk_cont", 0, at=time.time() + 10)
        self.assertEqual(self.kept()["bk_cont"]["v"], "0")

    def test_keep_going_refuses_anything_else(self):
        self.put("bk_cont", "1")
        for bad in ("2", "yes", "true", "", None, "10", "on"):
            with self.subTest(value=bad):
                self.put("bk_cont", bad, at=time.time() + 30)
                self.assertEqual(self.kept()["bk_cont"]["v"], "1")

    def test_a_level_name_is_kept_with_its_moment_and_its_device(self):
        now = time.time()
        out = self.put("bk_lvl:fa:vocal", "Mine", at=now, by="Android phone · Chrome")
        self.assertEqual(out["bk_lvl:fa:vocal"], {"v": "Mine", "at": now, "by": "Android phone · Chrome"})
        with open(self.path, encoding="utf-8") as f:
            doc = json.load(f)
        self.assertEqual(set(doc), {"settings", "places"})
        self.assertEqual(doc["settings"]["bk_lvl:fa:vocal"]["v"], "Mine")
        # and the toolbox hands it to a page asking for everything
        self.assertEqual(prefs.all_of()["settings"]["bk_lvl:fa:vocal"]["v"], "Mine")

    def test_a_name_is_trimmed_and_may_be_in_any_script(self):
        self.put("bk_lvl:fa:vocal", "  با‌اعراب  ")
        self.assertEqual(self.kept()["bk_lvl:fa:vocal"]["v"], "با‌اعراب")
        self.put("bk_lvl:ja:vocal", "ふりがな", at=time.time() + 1)
        self.assertEqual(self.kept()["bk_lvl:ja:vocal"]["v"], "ふりがな")

    def test_twelve_characters_is_the_most(self):
        self.put("bk_lvl:fa:chunks", "Twelve chars")
        self.assertEqual(self.kept()["bk_lvl:fa:chunks"]["v"], "Twelve chars")
        self.put("bk_lvl:fa:bare", "Thirteen char")
        self.assertNotIn("bk_lvl:fa:bare", self.kept())
        # measured once trimmed: spaces round a name do not count against it
        self.put("bk_lvl:fa:alt", "   Twelve chars   ")
        self.assertEqual(self.kept()["bk_lvl:fa:alt"]["v"], "Twelve chars")
        # and in characters, not in the bytes or the UTF-16 units a language counts them by
        wide = "\U0001D4D0"
        self.put("bk_lvl:ja:vocal", wide * 12)
        self.assertEqual(self.kept()["bk_lvl:ja:vocal"]["v"], wide * 12)
        self.put("bk_lvl:ja:aloud", wide * 13)
        self.assertNotIn("bk_lvl:ja:aloud", self.kept())

    def test_an_empty_name_is_a_value_and_means_the_registry_s_own_again(self):
        self.put("bk_lvl:fa:vocal", "Mine", at=time.time() - 10)
        self.put("bk_lvl:fa:vocal", "", at=time.time())
        self.assertEqual(self.kept()["bk_lvl:fa:vocal"]["v"], "")
        # kept, so that a device that still has the old name cannot undo it
        self.put("bk_lvl:fa:vocal", "Mine", at=time.time() - 5)
        self.assertEqual(self.kept()["bk_lvl:fa:vocal"]["v"], "")
        self.put("bk_lvl:fa:vocal", "   ", at=time.time() + 5)
        self.assertEqual(self.kept()["bk_lvl:fa:vocal"]["v"], "")

    def test_a_line_break_becomes_a_space_as_for_every_setting(self):
        self.put("bk_lvl:fa:vocal", "two\nlines")
        self.assertEqual(self.kept()["bk_lvl:fa:vocal"]["v"], "two lines")


class Refusing(Store):
    def test_a_key_nobody_follows_is_ignored_as_it_always_was(self):
        for key in ("bk_lvl:../x", "bk_lvl:fa:vocal/../../x", "bk_lvl:fa", "bk_lvl:", "bk_no1",
                    "bk_typo", "evil", "", "bk_lvl:fa:vocal\n", "BK_CONT"):
            with self.subTest(key=key):
                self.put(key, "x")
        self.assertEqual(self.kept(), {})
        self.assertFalse(os.path.exists(self.path), "nothing accepted, nothing written")

    def test_a_value_that_is_not_a_table_is_ignored(self):
        prefs.set_settings({"bk_lvl:fa:vocal": "Mine", "bk_cont": 1, "bk_rate": ["1"]})
        self.assertEqual(self.kept(), {})

    def test_an_over_long_name_is_refused_and_the_old_name_stays(self):
        self.put("bk_lvl:fa:vocal", "Mine", at=time.time() - 10)
        self.put("bk_lvl:fa:vocal", "This is far too long for a button", at=time.time())
        self.assertEqual(self.kept()["bk_lvl:fa:vocal"]["v"], "Mine")

    def test_a_document_is_not_a_name(self):
        self.put("bk_lvl:fa:vocal", "x" * 5000)
        self.assertNotIn("bk_lvl:fa:vocal", self.kept())

    def test_a_ceiling_on_how_many_names(self):
        with mock.patch.object(prefs, "MAX_LEVEL_KEYS", 3):
            for i, code in enumerate(("aa", "bb", "cc", "dd")):
                self.put("bk_lvl:%s:vocal" % code, "N%d" % i)
            self.assertEqual(sorted(k for k in self.kept() if k.startswith("bk_lvl:")),
                             ["bk_lvl:aa:vocal", "bk_lvl:bb:vocal", "bk_lvl:cc:vocal"])
            # a name already kept may still change, and the other keys are not counted
            self.put("bk_lvl:aa:vocal", "Changed", at=time.time() + 5)
            self.put("bk_rate", "1.25")
            self.assertEqual(self.kept()["bk_lvl:aa:vocal"]["v"], "Changed")
            self.assertEqual(self.kept()["bk_rate"]["v"], "1.25")


class LastChangeWins(Store):
    def test_the_newer_change_wins_for_the_new_keys_as_for_the_old(self):
        base = time.time() - 100
        for key, first, second in (("bk_cont", "1", "0"), ("bk_lvl:fa:vocal", "Old", "New"),
                                   ("bk_stopbnd", "1", "0")):
            with self.subTest(key=key):
                self.put(key, first, at=base)
                self.put(key, second, at=base + 10)
                self.assertEqual(self.kept()[key]["v"], second)
                # a device that was away comes back with its older change
                self.put(key, first, at=base + 5)
                self.assertEqual(self.kept()[key]["v"], second)
                self.assertEqual(self.kept()[key]["at"], base + 10)

    def test_each_name_wins_on_its_own(self):
        base = time.time() - 100
        self.put("bk_lvl:fa:vocal", "A", at=base + 10)
        self.put("bk_lvl:fa:chunks", "B", at=base + 1)
        # a change to one level says nothing about another's, nor about another language's
        self.put("bk_lvl:fa:chunks", "C", at=base + 2)
        self.put("bk_lvl:de:vocal", "D", at=base)
        self.assertEqual({k: v["v"] for k, v in self.kept().items()},
                         {"bk_lvl:fa:vocal": "A", "bk_lvl:fa:chunks": "C", "bk_lvl:de:vocal": "D"})

    def test_a_moment_from_the_future_is_taken_as_now(self):
        out = self.put("bk_cont", "1", at=time.time() + 10 ** 6)
        self.assertLess(out["bk_cont"]["at"], time.time() + 120)


class Shape(Store):
    def test_the_file_has_the_shape_it_always_had(self):
        """New keys inside `settings` are not a change of the file's shape: the
        number lib/version.py reports is the one it was, and a Parseh from
        before reads the file as it did."""
        self.assertEqual(prefs.STORE_FORMAT, 1)
        self.put("bk_cont", "1")
        self.put("bk_lvl:fa:vocal", "Mine")
        prefs.set_place("/books/english/x/reader/", 3, "1.2", 40, "a computer")
        with open(self.path, encoding="utf-8") as f:
            doc = json.load(f)
        self.assertEqual(set(doc), {"settings", "places"})
        for entry in doc["settings"].values():
            self.assertEqual(set(entry), {"v", "at", "by"})
        import version
        self.assertEqual(version.formats()["parseh-prefs"], 1)

    def test_an_older_parseh_keeps_what_it_does_not_know(self):
        """What the Parseh before this one does with such a file: it reads the
        whole document, changes the keys it knows and writes the whole document
        back, so the new keys survive a visit from it.  (Its KEYS, played here
        by a patched list, is what makes it ignore them.)"""
        self.put("bk_lvl:fa:vocal", "Mine")
        older = tuple(k for k in prefs.KEYS if k != "bk_cont")
        with mock.patch.object(prefs, "KEYS", older), \
                mock.patch.object(prefs, "LEVEL_KEY", re.compile(r"(?!)")):
            self.put("bk_rate", "1.5")
            self.put("bk_cont", "0")                # ignored by the old one
            self.put("bk_lvl:fa:vocal", "Theirs", at=time.time() + 5)
        self.assertEqual(self.kept()["bk_lvl:fa:vocal"]["v"], "Mine")
        self.assertEqual(self.kept()["bk_rate"]["v"], "1.5")
        self.assertNotIn("bk_cont", self.kept())


class Agreement(unittest.TestCase):
    """The page's copy of the rules is the server's."""

    JS = read(PREFS_JS)

    def test_the_exact_keys_are_the_same_list(self):
        m = re.search(r"var KEYS = \[([^\]]*)\];", self.JS)
        self.assertIsNotNone(m)
        self.assertEqual(re.findall(r"'([^']+)'", m.group(1)), list(prefs.KEYS))

    def test_the_level_key_is_the_same_pattern(self):
        m = re.search(r"var LEVEL = /\^(.*)\$/;", self.JS)
        self.assertIsNotNone(m, "prefs.js has no LEVEL pattern")
        self.assertEqual(m.group(1), prefs.LEVEL_KEY.pattern)
        self.assertTrue(prefs.LEVEL_KEY.pattern.startswith(re.escape(prefs.LEVEL_PREFIX)))

    def test_the_limit_is_the_same_number(self):
        m = re.search(r"var LEVEL_MAX = (\d+);", self.JS)
        self.assertEqual(int(m.group(1)), prefs.MAX_LEVEL_NAME)
        self.assertEqual(prefs.MAX_LEVEL_NAME, languages.LEVEL_NAME_MAX)

    def test_the_page_asks_follows_and_not_the_list(self):
        """changed(), the storage listener, sweep() and apply() all ask
        follows() / ours(), so a level's name is heard everywhere a key is --
        the old tests of the list by itself are gone from them."""
        self.assertIn("function follows(key) { return KEYS.indexOf(key) >= 0 || LEVEL.test(key); }",
                      self.JS)
        changed = self.JS[self.JS.index("function changed("):self.JS.index("/* ---- a reader's place")]
        self.assertIn("if (follows(key)) {", changed)
        self.assertNotIn("KEYS.indexOf(key)", changed)
        listen = self.JS[self.JS.index("function listen()"):self.JS.index("var last = {};")]
        self.assertIn("if (follows(e.key) || (here && e.key === here.key)) changed(", listen)
        self.assertIn("if (follows(e.key)) tell(e.key, e.newValue || '');", listen)
        self.assertNotIn("KEYS.indexOf", listen)
        sweep = self.JS[self.JS.index("function sweep()"):self.JS.index("function start()")]
        self.assertIn("ours().concat(here ? [here.key] : [])", sweep)
        apply = self.JS[self.JS.index("function apply(doc)"):self.JS.index("// a setting the toolbox brought")]
        self.assertIn("var names = ours();", apply)
        self.assertIn("follows(k) && names.indexOf(k) < 0", apply)
        self.assertNotIn("KEYS.forEach", apply)
        self.assertIn("follows: follows", self.JS)

    def test_a_value_brought_is_worn_then_announced_for_every_key(self):
        wear = self.JS[self.JS.index("function wear(key, v)"):self.JS.index("/* ---- hearing every write")]
        self.assertRegex(wear, r"try \{ wearHere\(key, v\); \} catch \(e\) \{\}\s+tell\(key, v\);")
        self.assertIn("new CustomEvent('parseh:pref', {detail: {key: key, value: v}})", wear)
        self.assertIn("document.dispatchEvent(", wear)
        # "keep going" presses the page's own #cont button when it says otherwise, as #stopbnd is
        self.assertRegex(wear, r"if \(key === 'bk_cont'\) \{\s+var c = document\.getElementById\('cont'\);")
        self.assertIn("if (c && (c.classList.contains('on') !== (v === '1'))) c.click();", wear)
        self.assertIn("var b = document.getElementById('stopbnd');", wear)

    def test_what_stays_on_the_device_is_still_not_followed(self):
        """The touch habit of hover pause is not the toolbox's on purpose
        (tests/test_mobile_pages.py holds that); neither is any key of what is
        SHOWN."""
        for key in ("bk_hoverpause", "bk_no1", "bk_no5", "bk_nogloss", "parseh_typo", "parseh_zoom"):
            self.assertFalse(prefs.follows(key), key)
            self.assertNotIn("'%s'" % key, self.JS)


# The page side, driven over the real lib/prefs.js.  A stand-in for the
# browser (localStorage over a Map, a document that is an EventTarget, a fetch
# that serves a document and records what is posted) is all it needs; the
# script is the one the browser runs.
HARNESS = r"""
const input = JSON.parse(Deno.args[0]);
const store = new Map(Object.entries(input.local || {}));
const localStorage = {
  getItem: k => store.has(k) ? store.get(k) : null,
  setItem: (k, v) => { store.set(String(k), String(v)); },
  removeItem: k => { store.delete(k); },
  key: i => Array.from(store.keys())[i] ?? null,
  get length() { return store.size; },
};
const state = {cont: input.contOn !== false, clicks: []};
const els = input.noCont ? {} : {cont: {
  classList: {contains: c => c === 'on' && state.cont},
  click() { state.clicks.push('cont'); state.cont = !state.cont; },
}};
const events = [], posts = [];
const doc = new EventTarget();
Object.assign(doc, {
  readyState: 'complete', visibilityState: 'visible', body: {appendChild() {}},
  getElementById: id => els[id] || null, querySelector: () => null,
  createElement: () => ({setAttribute() {}, appendChild() {}, addEventListener() {}, remove() {}, style: {}}),
});
doc.addEventListener('parseh:pref', e => events.push({key: e.detail.key, value: e.detail.value}));
// Deno has a localStorage and a location of its own (accessors that need flags): the page's are put over them
const give = (name, value) => Object.defineProperty(globalThis, name, {value, configurable: true, writable: true});
give('window', globalThis);
give('localStorage', localStorage);
give('document', doc);
give('location', {protocol: 'http:', pathname: input.reader ? '/books/persian/mini-fa/reader/' : '/'});
give('fetch', async (url, init) => {
  if (init && init.method === 'POST') { posts.push(JSON.parse(init.body)); return {ok: true, json: async () => ({ok: true})}; }
  return {ok: true, json: async () => input.server};
});
const tick = (ms = 30) => new Promise(r => setTimeout(r, ms));
const out = {};
const sent = () => { const n = posts.length; ParsehPrefs.send(); return posts.slice(n).map(p => p.settings || {}); };

await import(input.src);
await tick();
out.afterLoad = {local: Object.fromEntries(store), clicks: state.clicks.slice(), events: events.slice(),
                 contOn: state.cont, exposed: typeof ParsehPrefs.follows};
out.firstPost = sent();

// what the page writes itself afterwards
events.length = 0;
for (const [k, v] of input.writes || []) localStorage.setItem(k, v);
out.writes = sent();
out.writeEvents = events.slice();

// another tab of this browser
events.length = 0;
for (const [k, v] of input.storage || []) {
  const e = new Event('storage'); e.key = k; e.newValue = v; globalThis.dispatchEvent(e);
}
out.storageEvents = events.slice();
out.storagePost = sent();
out.clicksAfterStorage = state.clicks.slice();

// a browser whose setItem is its own: the sweep, on the page coming to the front
for (const [k, v] of input.quiet || []) { if (v === null) store.delete(k); else store.set(k, v); }
doc.dispatchEvent(new Event('visibilitychange'));
out.sweepPost = sent();
out.places = posts.map(p => p.place).filter(Boolean);
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(os.path.exists(DENO), "no deno")
class PageSide(unittest.TestCase):
    def drive(self, **spec):
        spec.setdefault("src", "file://" + PREFS_JS)
        with tempfile.TemporaryDirectory(prefix="parseh-prefsjs-") as td:
            script = os.path.join(td, "drive.mjs")
            with open(script, "w", encoding="utf-8") as f:
                f.write(HARNESS)
            r = subprocess.run([DENO, "run", "--quiet", "--allow-read", script, json.dumps(spec)],
                               capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout.strip().split("\n")[-1])

    SERVER = {"ok": True, "places": {}, "settings": {
        "bk_lvl:fa:vocal": {"v": "Mine", "at": 2e9, "by": "a computer"},
        "bk_lvl:fa:chunks": {"v": "x" * 13, "at": 2e9},        # too long: a hand-edited file
        "bk_lvl:../x": {"v": "bad", "at": 2e9},
        "bk_lvl:fa:vocal/x": {"v": "bad", "at": 2e9},
        "evil": {"v": "bad", "at": 2e9},
        "bk_no1": {"v": "1", "at": 2e9},                       # what is shown is the device's
        "bk_cont": {"v": "0", "at": 2e9},
        "bk_rate": {"v": "1.5", "at": 2e9}}}

    def test_a_value_the_toolbox_brings_is_stored_worn_and_announced(self):
        got = self.drive(server=self.SERVER, local={"bk_lvl:de:vocal": "Mein"})["afterLoad"]
        local = got["local"]
        # stored: the level's name, "keep going", and the speed
        self.assertEqual(local["bk_lvl:fa:vocal"], "Mine")
        self.assertEqual(local["bk_cont"], "0")
        self.assertEqual(local["bk_rate"], "1.5")
        # never stored: a name too long, a key that is no key, a key nobody follows
        for key in ("bk_lvl:fa:chunks", "bk_lvl:../x", "bk_lvl:fa:vocal/x", "evil", "bk_no1"):
            self.assertNotIn(key, local)
        self.assertEqual(local["bk_lvl:de:vocal"], "Mein")        # this device's own, left alone
        # worn: "keep going" was on, the toolbox says off, and the page's own button was pressed
        self.assertEqual(got["clicks"], ["cont"])
        self.assertFalse(got["contOn"])
        # announced on the document, for every key that came and only those
        by_key = {e["key"]: e["value"] for e in got["events"]}
        self.assertEqual(by_key, {"bk_lvl:fa:vocal": "Mine", "bk_cont": "0", "bk_rate": "1.5"})
        self.assertEqual(len(got["events"]), 3, "once for each: " + json.dumps(got["events"]))
        self.assertEqual(got["exposed"], "function")

    def test_a_page_without_the_button_has_nothing_to_press(self):
        got = self.drive(server=self.SERVER, noCont=True)["afterLoad"]
        self.assertEqual(got["clicks"], [])
        self.assertEqual(got["local"]["bk_cont"], "0")           # kept, for a page that has one
        self.assertIn({"key": "bk_cont", "value": "0"}, got["events"])

    def test_nothing_is_pressed_when_the_page_already_says_so(self):
        got = self.drive(server=self.SERVER, contOn=False)["afterLoad"]
        self.assertEqual(got["clicks"], [])

    def test_this_device_knows_better_when_its_name_is_newer_or_the_toolbox_has_none(self):
        out = self.drive(server={"ok": True, "settings": {}, "places": {}},
                         local={"bk_lvl:de:vocal": "Mein", "bk_lvl:fa:chunks": "x" * 13,
                                "bk_lvl:../x": "1", "bk_nogloss": "1", "bk_cont": "0"})
        sent = {}
        for s in out["firstPost"]:
            sent.update(s)
        self.assertEqual(sorted(sent), ["bk_cont", "bk_lvl:de:vocal"])
        self.assertEqual(sent["bk_lvl:de:vocal"]["v"], "Mein")
        self.assertEqual(out["afterLoad"]["events"], [])         # nothing came, nothing is announced

    def test_what_the_page_writes_is_sent_when_the_toolbox_would_keep_it(self):
        out = self.drive(server={"ok": True, "settings": {}, "places": {}}, writes=[
            ["bk_lvl:es:vocal", "Frase"], ["bk_lvl:es:chunks", "x" * 13], ["bk_lvl:es:bare", ""],
            ["bk_lvl:../x", "1"], ["bk_nogloss", "1"], ["bk_cont", "1"], ["bk_cont", "maybe"],
            ["bk_stopbnd", "1"]])
        sent = {}
        for s in out["writes"]:
            sent.update(s)
        self.assertEqual({k: v["v"] for k, v in sent.items()},
                         {"bk_lvl:es:vocal": "Frase", "bk_lvl:es:bare": "", "bk_cont": "1",
                          "bk_stopbnd": "1"})
        self.assertTrue(all(v["at"] > 0 for v in sent.values()))
        # what the page writes itself is not announced back to it
        self.assertEqual(out["writeEvents"], [])

    def test_a_name_is_counted_in_characters_as_the_toolbox_counts_them(self):
        """Twelve letters outside the basic plane are twelve characters for the
        toolbox (and the registry), though JavaScript's .length says twenty-four."""
        wide = "\U0001D4D0"                     # MATHEMATICAL BOLD SCRIPT CAPITAL A: two UTF-16 units
        out = self.drive(server={"ok": True, "settings": {}, "places": {}}, writes=[
            ["bk_lvl:es:vocal", wide * 12], ["bk_lvl:es:chunks", wide * 13]])
        sent = {}
        for s in out["writes"]:
            sent.update(s)
        self.assertEqual(list(sent), ["bk_lvl:es:vocal"])
        self.assertEqual(len(sent["bk_lvl:es:vocal"]["v"]), 12)

    def test_a_change_in_another_tab_is_sent_and_announced(self):
        out = self.drive(server={"ok": True, "settings": {}, "places": {}}, storage=[
            ["bk_lvl:it:vocal", "Frase"], ["bk_cont", "0"], ["bk_nogloss", "1"],
            ["bk_lvl:../x", "1"]])
        self.assertEqual([(e["key"], e["value"]) for e in out["storageEvents"]],
                         [("bk_lvl:it:vocal", "Frase"), ("bk_cont", "0")])
        sent = {}
        for s in out["storagePost"]:
            sent.update(s)
        self.assertEqual({k: v["v"] for k, v in sent.items()},
                         {"bk_lvl:it:vocal": "Frase", "bk_cont": "0"})
        # announced, not worn: the other tab's switch is not pressed in this one
        self.assertEqual(out["clicksAfterStorage"], [])

    def test_a_browser_that_will_not_have_its_setitem_wrapped_is_swept(self):
        """The fallback when the page comes back to the front: a level's name
        found in localStorage that the page did not have at load, one changed,
        and one taken away -- the last as an empty name, "the default again"."""
        out = self.drive(server={"ok": True, "settings": {}, "places": {}},
                         local={"bk_lvl:fr:vocal": "Avant"},
                         quiet=[["bk_lvl:ja:vocal", "Ruby"], ["bk_lvl:fr:vocal", None],
                                ["bk_lvl:fr:chunks", "x" * 13]])
        sent = {}
        for s in out["sweepPost"]:
            sent.update(s)
        self.assertEqual({k: v["v"] for k, v in sent.items()},
                         {"bk_lvl:ja:vocal": "Ruby", "bk_lvl:fr:vocal": ""})

    def test_on_a_reader_the_place_is_still_told_and_the_names_are_not_mistaken_for_it(self):
        out = self.drive(reader=True, server=self.SERVER,
                         local={"bk_pos:/books/persian/mini-fa/reader/": json.dumps({"i": 4})})
        self.assertEqual(out["afterLoad"]["local"]["bk_lvl:fa:vocal"], "Mine")
        # the toolbox had no place for this book: the one this device read is told, once
        self.assertEqual([(p["path"], p["i"]) for p in out["places"]],
                         [("/books/persian/mini-fa/reader/", 4)])
        # and a name written on a reader is a name, not a place
        wrote = self.drive(reader=True, server={"ok": True, "settings": {}, "places": {}},
                           writes=[["bk_lvl:fa:chunks", "Pieces"]])
        self.assertEqual(wrote["places"], [])
        self.assertEqual({k: v["v"] for s in wrote["writes"] for k, v in s.items()},
                         {"bk_lvl:fa:chunks": "Pieces"})


if __name__ == "__main__":
    unittest.main()
