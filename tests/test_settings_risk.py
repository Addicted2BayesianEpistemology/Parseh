# SPDX-License-Identifier: GPL-3.0-or-later
"""Who may change what, and the reading help's home in Settings (TO-DO §11.10).

    python3 -m unittest tests/test_settings_risk.py

WHO MAY SAVE IS A PROPERTY OF THE SETTING (the owner, 2026-09-24): one table
in lib/settingspage.py names every setting, and for each risky one the part
of the sentence it trips -- "a setting is risky when it changes who may
reach Parseh, what Parseh exposes, or what Parseh will run".  Here, as tests:

  * the table is complete: every route serve.py answers under /settings/api/
    and /lookup/api/ is in it, and every route in it is answered -- a route
    somebody adds without writing it down fails this file, and is refused
    at run time for everybody;
  * a phone let in over the Wi-Fi is refused a Network change, in the words
    of the setting's own entry, and may get and remove a download;
  * the live pairing code is on the computer's page and not on a phone's;
  * /lookup/ answers with a redirect that keeps the fragment, forever, and
    the API stays where it was;
  * a download reports how far it has got, can be stopped, says what it
    costs before it starts, is refused when the disk has no room, and "get
    everything" runs one step at a time on the server -- all through the job
    tables, with the downloaders stubbed (lib/download.py's interface: build
    and plan, with say, progress and cancel).

The real server, over plain http on a free port, with the dictionaries,
corpora, models and packs pointed at a temporary folder and the network
settings with them: nothing here writes the checkout's dict/ or config/.
"""
import ast
import http.client
import json
import os
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in ("markdown/exlex", "markdown/app", "lib", "youtube/lib", "."):
    sys.path.insert(0, str(ROOT / p))
import network                                                 # noqa: E402
import settingspage                                            # noqa: E402


def routes_in_serve():
    """Every route serve.py answers under /settings/api/ and /lookup/api/,
    read from its source: the /settings/api/ addresses it names anywhere,
    and each name _lookup_api compares `what` with or _reading_key maps."""
    tree = ast.parse((ROOT / "serve.py").read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and node.value.startswith("/settings/api/") and len(node.value) > 14:
            found.add(node.value)
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name == "_lookup_api":
            for c in ast.walk(node):
                if isinstance(c, ast.Compare) and isinstance(c.left, ast.Name) \
                        and c.left.id == "what":
                    for comp in c.comparators:
                        values = comp.elts if isinstance(comp, (ast.Tuple, ast.List, ast.Set)) else [comp]
                        for v in values:
                            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                                found.add("/lookup/api/" + v.value)
        if node.name == "_reading_key":
            for c in ast.walk(node):
                if isinstance(c, ast.Tuple) and len(c.elts) == 3 \
                        and all(isinstance(e, ast.Constant) for e in c.elts):
                    found.add("/lookup/api/" + c.elts[1].value)
                    found.add("/lookup/api/" + c.elts[2].value)
    return found


class Table(unittest.TestCase):
    def test_every_route_serve_answers_is_in_the_table(self):
        found = routes_in_serve()
        self.assertGreater(len(found), 20, "the reading help's and Network's routes were found")
        missing = sorted(found - set(settingspage.ROUTES))
        self.assertEqual(missing, [], "a route serve.py answers must be written into "
                                      "lib/settingspage.py ROUTES, with who may use it")
        # and the table names nothing serve.py has stopped answering
        self.assertEqual(sorted(set(settingspage.ROUTES) - found), [])

    def test_every_setting_a_route_names_is_a_setting(self):
        for route, what in settingspage.ROUTES.items():
            if what in (settingspage.READ, settingspage.KNOCK):
                continue
            for setting in what:
                self.assertIn(setting, settingspage.SETTINGS, route)

    def test_what_is_risky_is_decided_by_the_sentence(self):
        S = settingspage.SETTINGS
        for key in ("network.doors", "network.extra", "network.port", "network.code",
                    "network.forget"):
            self.assertEqual(S[key][0], settingspage.REACH, key)
        self.assertEqual(S["network.cert"][0], settingspage.EXPOSE)
        self.assertEqual(S["parseh.update"][0], settingspage.RUN)
        for key in ("reading.get", "reading.remove", "reading.stop"):
            self.assertIsNone(S[key][0], key)

    def test_a_phone_may_what_is_not_risky_and_the_computer_everything(self):
        for key in settingspage.SETTINGS:
            self.assertTrue(settingspage.may(key, network.SELF), key)
            risky = settingspage.SETTINGS[key][0] is not None
            for where in (network.LAN, network.VPN):
                self.assertEqual(settingspage.may(key, where), not risky, (key, where))
        self.assertFalse(settingspage.may("network.nothing", network.SELF),
                         "a setting nobody wrote down is refused, even to the computer")

    def test_a_route_nobody_wrote_down_is_refused(self):
        ok, why = settingspage.may_post("/lookup/api/getsomethingnew", network.SELF)
        self.assertFalse(ok)
        self.assertIn("not in the table", why)

    def test_the_refusal_names_the_part_of_the_sentence(self):
        said = settingspage.refusal("network.port")
        self.assertIn("changed on the computer Parseh runs on", said)
        self.assertIn(settingspage.REACH, said)
        self.assertIn(settingspage.SETTINGS["network.port"][1], said)


# ---------------------------------------------------------------- a server
def fake_downloader(name, plan, steps=20, pause=0.02, log=None, write=None):
    """A stand-in for one of lib/getdict.py and its siblings, with the
    interface lib/download.py gives them: build(..., say, progress, cancel)
    reporting its download and then its build, raising download.Cancelled
    when asked to stop; plan(..., probe) answering `plan`."""
    import download
    import importlib
    mod = types.ModuleType(name)
    # its constants are the real downloader's -- the page names the source
    # and the licence of each row from them (lib/notices.py credits)
    real = importlib.import_module(name)
    for attr in dir(real):
        if attr.isupper():
            setattr(mod, attr, getattr(real, attr))

    def run(args, say, progress, cancel):
        if log is not None:
            log.append(("start", name, args, time.time()))
        total = 100 * steps
        for i in range(steps + 1):
            if cancel is not None and (cancel.is_set() if hasattr(cancel, "is_set") else cancel()):
                raise download.Cancelled()
            if progress:
                progress(i * 100, total, "download")
            if say:
                say("%d of %d" % (i * 100, total))
            time.sleep(pause)
        if progress:
            progress(1, 1, "build")
        if write:
            write(*args)
        if log is not None:
            log.append(("end", name, args, time.time()))

    def build(*args, say=None, progress=None, cancel=None, **kw):
        run(args, say, progress, cancel)

    def get(say=None, force=False, progress=None, cancel=None):
        run((), say, progress, cancel)

    mod.build = build
    mod.get = get
    mod.plan = lambda *args, probe=True, **kw: dict(plan)
    return mod


class Served(unittest.TestCase):
    """The real server, with the reading help's folders and the network
    settings in a temporary tree."""

    @classmethod
    def setUpClass(cls):
        import serve
        import lookup
        import corpus
        import getmt
        import decomposition
        cls.serve = serve
        cls._td = tempfile.TemporaryDirectory()
        tmp = Path(cls._td.name)
        cls.tmp = tmp
        cls.patches = [
            patch.object(serve.Handler, "log_request", lambda *a, **k: None),
            patch.object(network, "STORE", str(tmp / "config" / "network.json")),
            patch.object(lookup, "DICT_DIR", str(tmp / "dict")),
            patch.object(corpus, "CORPUS_DIR", str(tmp / "corpus")),
            patch.object(getmt, "MT_DIR", str(tmp / "mt")),
            patch.object(getmt, "ENGINE_DIR", str(tmp / "mt" / "engine")),
            patch.object(decomposition, "DATA_DIR", tmp / "components"),
        ]
        for p in cls.patches:
            p.start()
        network._CACHE.update({"key": None, "doc": None})
        cls.srv = serve.Server(("127.0.0.1", 0), serve.Handler, None)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        for p in reversed(cls.patches):
            p.stop()
        network._CACHE.update({"key": None, "doc": None})
        cls._td.cleanup()

    def setUp(self):
        s = self.serve
        for table in (s.DICT_JOBS, s.CORPUS_JOBS, s.MT_JOBS, s.DECOMPOSITION_JOBS, s.SYN_JOB,
                      s.PLANS, s.QUEUES, s.CANCELS):
            table.clear()
        del s.QUEUE[:]

    def ask(self, method, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.srv.server_address[1], timeout=60)
        data = None if body is None else json.dumps(body).encode("utf-8")
        c.request(method, path, body=data,
                  headers={"Content-Type": "application/json"} if data is not None else {})
        r = c.getresponse()
        raw = r.read()
        c.close()
        try:
            got = json.loads(raw.decode("utf-8"))
        except ValueError:
            got = raw.decode("utf-8", "replace")
        return r.status, r.getheader("Location") or "", got

    def as_phone(self):
        """This test's requests come from a phone let in over the Wi-Fi: the
        address is judged the Wi-Fi's, the door is open, and the device's
        cookie is one the computer gave it."""
        return [patch.object(network, "where", lambda ip, doc=None: network.LAN),
                patch.object(network, "may_connect", lambda ip, doc=None: True),
                patch.object(network, "let_in", lambda *a, **k: True)]

    def stubbed(self, **mods):
        return patch.dict(sys.modules, mods)

    def wait(self, test, what, limit=10):
        end = time.time() + limit
        while time.time() < end:
            if test():
                return
            time.sleep(0.02)
        self.fail("gave up waiting for " + what)

    # ---- the move
    def test_the_old_address_answers_with_a_redirect_forever(self):
        for path in ("/lookup/", "/lookup", "/lookup/index.html"):
            status, to, _ = self.ask("GET", path)
            self.assertEqual(status, 302, path)
            self.assertTrue(to.endswith("/settings/reading-help/"), (path, to))
            # NO FRAGMENT IN THE LOCATION: the browser then keeps the one it
            # was asked for, so /lookup/#character-components lands on that
            # section of the new page (RFC 9110 10.2.2)
            self.assertNotIn("#", to)
        status, to, _ = self.ask("GET", "/lookup/?from=old")
        self.assertEqual((status, to.rsplit("/settings/", 1)[-1]), (302, "reading-help/?from=old"))
        self.assertEqual(self.ask("POST", "/lookup/", {})[0], 405, "a page is not posted to")

    def test_the_new_page_and_the_api_where_it_was(self):
        status, _, page = self.ask("GET", "/settings/reading-help/")
        self.assertEqual(status, 200)
        self.assertIn('id="rh-state"', page)
        self.assertIn("/lookup/api/", page, "its buttons post where the API has always been")
        self.assertIn('data-mobile-page', page)
        self.assertIn('data-layout="mobile"', page, "the phone's bar, like its sibling Network")
        self.assertIn('href="/settings/network/"', page, "Settings' doors, in a row")
        self.assertIn("#how-the-reading-help-works", page, "the long prose is in the guide")
        status, to, _ = self.ask("GET", "/settings/reading-help")
        self.assertEqual((status, to.rsplit(":%d" % self.srv.server_address[1], 1)[-1]),
                         (302, "/settings/reading-help/"))
        status, _, got = self.ask("POST", "/lookup/api/status", {})
        self.assertEqual(status, 200)
        self.assertEqual(len(got["languages"]), len(__import__("languages").LANGS))
        self.assertIn("dict:tr", got["sizes"])

    def test_settings_shows_the_version_and_both_doors(self):
        import version
        status, _, page = self.ask("GET", "/settings/")
        self.assertEqual(status, 200)
        self.assertIn(version.VERSION, page)
        self.assertIn('href="/settings/reading-help/"', page)
        self.assertIn("any device let in", page)
        self.assertIn("changed on the computer only", page)

    # ---- who may
    def test_a_phone_is_refused_a_network_change_in_the_entry_s_words(self):
        ps = self.as_phone()
        for p in ps:
            p.start()
        try:
            status, _, got = self.ask("POST", "/settings/api/network", {"lan": True})
            self.assertEqual(status, 403)
            self.assertEqual(got["error"], settingspage.refusal("network.doors"))
            self.assertIn(settingspage.REACH, got["error"])
            status, _, got = self.ask("POST", "/settings/api/code", {})
            self.assertEqual((status, got["error"]), (403, settingspage.refusal("network.code")))
            status, _, got = self.ask("POST", "/settings/api/forget", {"all": True})
            self.assertEqual((status, got["error"]), (403, settingspage.refusal("network.forget")))
            # a route nobody wrote down is refused whoever asks
            status, _, got = self.ask("POST", "/lookup/api/getsomethingnew", {})
            self.assertEqual(status, 404)
        finally:
            for p in reversed(ps):
                p.stop()
        # the computer itself may
        status, _, got = self.ask("POST", "/settings/api/code", {})
        self.assertEqual(status, 200)
        self.assertTrue(got["ok"])

    def test_a_phone_may_get_and_remove_a_download(self):
        import download
        import lookup
        made = []

        def write(code):
            os.makedirs(lookup.DICT_DIR, exist_ok=True)
            Path(lookup.path_for(code)).write_bytes(b"not really a dictionary")
            made.append(code)
        fake = fake_downloader("getdict", download.plan(download=2000, measured=True, kept=100),
                               steps=3, write=write)
        ps = self.as_phone()
        for p in ps:
            p.start()
        try:
            with self.stubbed(getdict=fake):
                status, _, got = self.ask("POST", "/lookup/api/getdict", {"code": "tr"})
                self.assertEqual((status, got.get("ok")), (200, True), got)
                self.wait(lambda: not self.serve.DICT_JOBS["tr"].get("running"), "the build")
                self.assertEqual(made, ["tr"])
                self.assertTrue(os.path.isfile(lookup.path_for("tr")))
                status, _, got = self.ask("POST", "/lookup/api/dropdict", {"code": "tr"})
                self.assertEqual((status, got.get("ok")), (200, True), got)
                self.assertFalse(os.path.exists(lookup.path_for("tr")))
        finally:
            for p in reversed(ps):
                p.stop()

    def test_the_pairing_code_is_on_the_computer_only(self):
        live = network.say_code(network.code()["code"])
        status, _, page = self.ask("GET", "/settings/network/")
        self.assertEqual(status, 200)
        self.assertIn(live, page, "the computer sees the code")
        self.assertIn("data-fresh-code", page)
        ps = self.as_phone()
        for p in ps:
            p.start()
        try:
            status, _, page = self.ask("GET", "/settings/network/")
        finally:
            for p in reversed(ps):
                p.stop()
        self.assertEqual(status, 200)
        self.assertFalse(live in page, "a phone is never shown the live code")
        self.assertFalse('<div class="code" data-code>' in page)
        self.assertFalse('data-fresh-code>' in page)
        self.assertIn("The code is shown on the computer only.", page)
        self.assertFalse("data-save>" in page, "no dead Save button: the lock lines say why")
        self.assertIn(settingspage.SETTINGS["network.port"][1].replace("'", "&#x27;"), page)

    # ---- how far, and stopping
    def test_a_download_says_how_far_it_has_got_and_can_be_stopped(self):
        import download
        fake = fake_downloader("getdict", download.plan(download=4000, measured=True, kept=10),
                               steps=400, pause=0.01)
        with self.stubbed(getdict=fake):
            self.assertEqual(self.ask("POST", "/lookup/api/getdict", {"code": "de"})[0], 200)
            job = self.serve.DICT_JOBS["de"]
            self.wait(lambda: job.get("done", 0) >= 500, "some progress")
            self.assertEqual((job["phase"], job["total"]), ("download", 40000))
            self.assertTrue(job["running"])
            # the page's own view says the same
            _, _, got = self.ask("POST", "/lookup/api/status", {})
            self.assertTrue(got["jobs"]["dict"]["de"]["running"])
            self.assertGreater(got["jobs"]["dict"]["de"]["done"], 0)
            # and so does the activity list, with the bytes
            entry = [e for e in self.serve.activity_now()["running"]
                     if e["id"].startswith("lookup:dict:de@")]
            self.assertEqual(len(entry), 1)
            self.assertEqual(entry[0]["total"], 40000)
            status, _, got = self.ask("POST", "/lookup/api/stop", {"kind": "dict", "key": "de"})
            self.assertEqual((status, got["stopped"]), (200, True))
            self.wait(lambda: not job.get("running"), "the stop")
        self.assertTrue(job["stopped"])
        self.assertEqual(job["error"], "", "stopping is not failing")
        self.assertLess(job["done"], 40000)

    def test_what_it_costs_is_said_before_it_starts(self):
        import download
        fake = fake_downloader("getcorpus", download.plan(download=5_000_000, measured=False,
                                                          kept=2_000_000, have=1_000_000))
        with self.stubbed(getcorpus=fake):
            status, _, got = self.ask("POST", "/lookup/api/plan", {"kind": "corpus", "key": "fa-en"})
        self.assertEqual(status, 200, got)
        self.assertEqual((got["download"], got["kept"], got["have"]), (5_000_000, 2_000_000, 1_000_000))
        self.assertFalse(got["measured"])
        self.assertEqual(got["room"], "")
        self.assertGreater(got["free"], 0)
        self.assertEqual(got["named"], "the Persian–English translated sentences")
        status, _, got = self.ask("POST", "/lookup/api/plan", {"kind": "corpus", "key": "fa-fa"})
        self.assertEqual(status, 400)

    def test_nothing_starts_that_the_disk_has_no_room_for(self):
        import download
        fake = fake_downloader("getmt", download.plan(download=10, measured=True, kept=10,
                                                      peak=10 ** 18))
        with self.stubbed(getmt=fake):
            status, _, got = self.ask("POST", "/lookup/api/getmodel", {"code": "fa", "gloss": "en"})
        self.assertEqual(status, 507)
        self.assertIn("not enough room", got["error"])
        self.assertIn("free", got["error"])
        self.assertNotIn("fa-en", self.serve.MT_JOBS, "nothing was started")

    def test_get_everything_runs_on_the_server_one_step_at_a_time(self):
        import download
        import lookup
        log, made = [], []
        plan = download.plan(download=1000, measured=True, kept=500)
        mods = {name: fake_downloader(name, plan, steps=5, log=log)
                for name in ("getdict", "getdecomposition", "getcorpus", "getmt")}
        # the stand-in dictionary is "there" once its step has run: Japanese's
        # sentences are refused until it is
        mods["getdict"] = fake_downloader("getdict", plan, steps=5, log=log,
                                          write=lambda code: made.append(code))
        with self.stubbed(**mods), patch.object(lookup, "available", lambda code: code in made):
            status, _, got = self.ask("POST", "/lookup/api/plan", {"all": "ja", "gloss": "en"})
            self.assertEqual(status, 200)
            self.assertEqual([s["kind"] for s in got["steps"]],
                             ["dict", "components", "corpus", "model"],
                             "the dictionary first: Japanese's sentences are cut into words with it")
            self.assertEqual(got["download"], 4000)
            status, _, got = self.ask("POST", "/lookup/api/getall", {"code": "ja", "gloss": "en"})
            self.assertEqual((status, got["ok"]), (200, True), got)
            entry = [e for e in self.serve.activity_now()["running"]
                     if e["id"].startswith("lookup:all:ja@")]
            self.assertEqual([e["label"] for e in entry], ["Getting everything for Japanese"])
            self.wait(lambda: not self.serve.QUEUE_WORKER["running"], "the queue", 20)
        starts = [x for x in log if x[0] == "start"]
        self.assertEqual([x[1] for x in starts], ["getdict", "getdecomposition", "getcorpus", "getmt"])
        # ONE AT A TIME: each step started after the one before it ended
        ends = [x for x in log if x[0] == "end"]
        for before, after in zip(ends, starts[1:]):
            self.assertLessEqual(before[3], after[3])
        self.assertFalse(self.serve.QUEUES["ja"]["running"])

    def test_stopping_everything_empties_the_queue(self):
        import download
        plan = download.plan(download=1000, measured=True, kept=500)
        mods = {name: fake_downloader(name, plan, steps=300, pause=0.01)
                for name in ("getdict", "getcorpus", "getmt")}
        with self.stubbed(**mods):
            self.assertEqual(self.ask("POST", "/lookup/api/getall", {"code": "it", "gloss": "en"})[0], 200)
            self.wait(lambda: self.serve.DICT_JOBS.get("it", {}).get("running"), "the first step")
            self.assertEqual(self.serve.CORPUS_JOBS["it-en"]["waiting"], True)
            self.ask("POST", "/lookup/api/stop", {"all": "it"})
            self.wait(lambda: not self.serve.QUEUE_WORKER["running"], "the queue", 20)
        self.assertTrue(self.serve.DICT_JOBS["it"]["stopped"])
        self.assertNotIn("it-en", self.serve.CORPUS_JOBS, "a step that never ran is not a job")
        self.assertEqual(self.serve.QUEUE, [])


if __name__ == "__main__":
    unittest.main()
