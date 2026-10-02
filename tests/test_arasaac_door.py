# SPDX-License-Identifier: GPL-3.0-or-later
"""Settings -> Pictograms (ARASAAC) as the server answers it (lib/arasaacpage.py, serve.py), a0.4.2.

    python3 -m unittest tests/test_arasaac_door.py

THE REAL SERVER, over plain http on a free port, with arasaac/ and the network settings in a temporary
tree and the two hosts the pictograms come from stood in for (tests/arasaac_fake.py): nothing here
reaches ARASAAC, and nothing is written outside the temporary tree.  What is held:

  * A DOOR WRITTEN IS A DOOR REACHABLE, AND ONLY THAT ONE: the page opens, redirects from its address
    without the slash, is not posted to; every route is answered, and a route nobody wrote into
    lib/settingspage.py ROUTES is refused;
  * ANY DEVICE LET IN may get, update, stop and remove (the owner's rule for downloads of this kind),
    and a device that is not let in gets nothing;
  * EVERY WRITE IS REFUSED FROM ANOTHER SITE (lib/crosssite.py): a page on some other address, open in
    this computer's browser, cannot start a download of 160 MB or take the pictograms away;
  * NOTHING A CLIENT SENDS BECOMES A PATH OR AN ADDRESS: a language that is not ARASAAC's, a size that
    is not one of two, a name with a slash in it, a body that is not an object -- each is a 400 in a
    sentence before anything is made or asked for;
  * THE JOB IS ON THE ACTIVITY LIST, kind `lookup`, linking to this page, and ends when it ends;
  * the licence page and the hub name the pictograms, and the pictograms' credit is the one
    getarasaac.CREDIT says.
"""
import http.client
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in ("markdown/exlex", "markdown/app", "lib", "youtube/lib", ".", "tests"):
    sys.path.insert(0, str(ROOT / p))
import network                                                     # noqa: E402
import getarasaac as ga                                            # noqa: E402
import arasaac_fake                                                # noqa: E402


class Served(unittest.TestCase):
    n = 25

    @classmethod
    def setUpClass(cls):
        import serve
        cls.serve = serve
        cls._td = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._td.name)
        cls.fake = arasaac_fake.Fake(arasaac_fake.World(cls.n, ("en", "fr")))
        cls.patches = [
            patch.object(serve.Handler, "log_request", lambda *a, **k: None),
            patch.object(network, "STORE", str(cls.tmp / "config" / "network.json")),
            patch.object(ga, "ARASAAC_DIR", str(cls.tmp / "arasaac")),
            patch.object(ga, "API", cls.fake.api), patch.object(ga, "STATIC", cls.fake.static),
            patch.object(ga, "MIN_RECORDS", 5), patch.object(ga, "PAUSE", 0.0), patch.object(ga, "RETRIES", (0, 0, 0)),
        ]
        for p in cls.patches:
            p.start()
        network._CACHE.update({"key": None, "doc": None})
        cls.srv = serve.Server(("127.0.0.1", 0), serve.Handler, None)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        ga.stop_all(3)
        cls.srv.shutdown()
        cls.srv.server_close()
        for p in reversed(cls.patches):
            p.stop()
        cls.fake.stop()
        network._CACHE.update({"key": None, "doc": None})
        cls._td.cleanup()

    def setUp(self):
        ga.stop_all(3)
        ga.remove()
        ga.JOB.clear()
        ga._FACTS.clear()
        self.fake.requests.clear()
        self.fake.after.clear()
        self.fake.world.delay = 0.0
        self.fake.world.failures.clear()

    def ask(self, method, path, body=None, headers=None, raw=None):
        c = http.client.HTTPConnection("127.0.0.1", self.srv.server_address[1], timeout=60)
        data = raw if raw is not None else (None if body is None else json.dumps(body).encode("utf-8"))
        h = {"Content-Type": "application/json"} if data is not None else {}
        h.update(headers or {})
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        got = r.read()
        c.close()
        try:
            out = json.loads(got.decode("utf-8"))
        except ValueError:
            out = got.decode("utf-8", "replace")
        return r.status, r.getheader("Location") or "", out

    def as_phone(self):
        return [patch.object(network, "where", lambda ip, doc=None: network.LAN),
                patch.object(network, "may_connect", lambda ip, doc=None: True),
                patch.object(network, "let_in", lambda *a, **k: True)]

    def wait(self, test, what, limit=15):
        end = time.time() + limit
        while time.time() < end:
            if test():
                return
            time.sleep(0.02)
        self.fail("gave up waiting for " + what)

    def installed(self):
        status, _, got = self.ask("POST", "/settings/api/arasaac/state", {})
        return status == 200 and got["arasaac"]["state"] == "installed" and not got["arasaac"]["job"].get("running")

    # ---- the page
    def test_the_page_opens_redirects_and_is_not_posted_to(self):
        status, _, page = self.ask("GET", "/settings/arasaac/")
        self.assertEqual(status, 200)
        self.assertIn('id="ar-state"', page)
        self.assertIn("/settings/api/arasaac/", page, "its buttons post to its own routes")
        self.assertIn('data-layout="mobile"', page, "the phone's bar, like its sibling doors")
        self.assertIn('href="/settings/speech/"', page, "Settings' doors, in a row")
        self.assertIn('<h1 class="idx">pictograms (ARASAAC)</h1>', page)
        for host in ("api.arasaac.org", "static.arasaac.org"):
            self.assertIn(host, page)
        status, to, _ = self.ask("GET", "/settings/arasaac")
        self.assertEqual((status, to.rsplit(":%d" % self.srv.server_address[1], 1)[-1]), (302, "/settings/arasaac/"))
        self.assertEqual(self.ask("POST", "/settings/arasaac/", {})[0], 405, "a page is not posted to")

    def test_the_hub_has_the_card_and_the_licences_page_the_credit(self):
        status, _, hub = self.ask("GET", "/settings/")
        self.assertEqual(status, 200)
        card = hub.split('href="/settings/arasaac/"', 1)[1].split("</a>", 1)[0]
        self.assertIn("Pictograms (ARASAAC)", card)
        self.assertIn("any device let in", card)
        self.assertIn("not installed", card)
        status, _, page = self.ask("GET", "/licences/")
        self.assertEqual(status, 200)
        self.assertIn("ARASAAC pictograms", page)
        self.assertIn("Sergio Palao", page)
        self.assertIn("CC BY-NC-SA 4.0", page)
        self.assertIn('href="https://creativecommons.org/licenses/by-nc-sa/4.0/"', page)

    def test_the_state_is_what_the_page_is_drawn_from(self):
        status, _, got = self.ask("POST", "/settings/api/arasaac/state", {})
        self.assertEqual(status, 200)
        self.assertEqual(got["arasaac"]["state"], "absent")
        self.assertEqual(got["may"], {"arasaac.get": True, "arasaac.remove": True, "arasaac.stop": True})
        langs = {r["code"]: r for r in got["languages"]}
        self.assertEqual(next(iter(got["languages"]))["code"], "en", "English first")
        self.assertTrue(langs["fr"]["offered"])
        self.assertFalse(langs["ja"]["offered"])
        self.assertFalse(langs["hi"]["offered"])
        self.assertEqual(got["credit"]["text"], ga.CREDIT)
        self.assertEqual(got["plan"]["resolution"], 300)
        self.assertEqual(got["hosts"], ["api.arasaac.org", "static.arasaac.org"])
        self.assertIsNotNone(got["free"])
        # a client cannot name the device the page says it is on
        status, _, got = self.ask("POST", "/settings/api/arasaac/state", {"device": "the owner's phone"})
        self.assertNotEqual(got["device"], "the owner's phone")

    def test_a_route_nobody_wrote_down_is_refused_and_a_read_is_not_a_page(self):
        status, _, got = self.ask("POST", "/settings/api/arasaac/everything", {})
        self.assertEqual(status, 404)
        self.assertIn("not in the table", got["error"])
        for route in ("state", "plan", "get", "update", "stop", "remove"):
            self.assertEqual(self.ask("GET", "/settings/api/arasaac/" + route)[0], 405, route)

    # ---- who may
    def test_any_device_let_in_may_get_look_for_changes_stop_and_remove(self):
        ps = self.as_phone()
        for p in ps:
            p.start()
        try:
            status, _, got = self.ask("POST", "/settings/api/arasaac/state", {})
            self.assertEqual(got["where"], "lan")
            self.assertEqual(got["may"], {"arasaac.get": True, "arasaac.remove": True, "arasaac.stop": True})
            status, _, got = self.ask("POST", "/settings/api/arasaac/get", {"locales": ["en"], "resolution": 300})
            self.assertEqual((status, got.get("ok")), (200, True), got)
            self.wait(self.installed, "the download")
            self.assertEqual(ga.pictures_here()[0], self.n)
            status, _, got = self.ask("POST", "/settings/api/arasaac/update", {})
            self.assertEqual((status, got.get("ok")), (200, True), got)
            self.wait(lambda: not ga.running(), "the update")
            self.assertEqual(ga.job()["error"], "")
            status, _, got = self.ask("POST", "/settings/api/arasaac/stop", {})
            self.assertEqual((status, got), (200, {"ok": True, "stopped": False}), "nothing running: said so, not an error")
            status, _, got = self.ask("POST", "/settings/api/arasaac/remove", {"locale": "en"})
            self.assertEqual((status, got.get("ok")), (200, True), got)
            self.assertEqual(ga.locales_here(), [])
            status, _, got = self.ask("POST", "/settings/api/arasaac/remove", {"all": True})
            self.assertEqual((status, got.get("ok")), (200, True), got)
            self.assertFalse((self.tmp / "arasaac").exists())
        finally:
            for p in reversed(ps):
                p.stop()

    def test_a_device_that_has_not_been_let_in_gets_nothing(self):
        ps = [patch.object(network, "where", lambda ip, doc=None: network.LAN),
              patch.object(network, "needs_code", lambda ip, doc=None: True),
              patch.object(network, "let_in", lambda *a, **k: False)]
        for p in ps:
            p.start()
        try:
            for route in ("get", "state", "remove"):
                status, _, got = self.ask("POST", "/settings/api/arasaac/" + route, {"locales": ["en"]})
                self.assertEqual(status, 403, route)
                self.assertIn("this device has not been let in", got["error"])
            status, _, page = self.ask("GET", "/settings/arasaac/")
            self.assertEqual(status, 403)
            self.assertNotIn("ar-state", page, "the locked page, and none of this one")
        finally:
            for p in reversed(ps):
                p.stop()
        self.assertEqual(self.fake.requests, [], "and nothing was fetched on its behalf")

    # ---- another site
    def test_every_write_is_refused_from_another_site(self):
        for route, body in (("get", {"locales": ["en"]}), ("update", {}), ("stop", {}), ("remove", {"all": True}),
                            ("plan", {"locales": ["en"]}), ("state", {})):
            for headers in ({"Sec-Fetch-Site": "cross-site"}, {"Sec-Fetch-Site": "same-site"},
                            {"Origin": "http://evil.example"}, {"Origin": "null"}):
                status, _, got = self.ask("POST", "/settings/api/arasaac/" + route, body, headers)
                self.assertEqual(status, 403, (route, headers))
                self.assertIn("only Parseh's own pages may change anything in it", got["error"])
        self.assertEqual(self.fake.requests, [], "nothing was fetched")
        self.assertFalse((self.tmp / "arasaac").exists(), "and nothing was made")
        # a form's body (text/plain) from another site is the same attack by another door
        status, _, got = self.ask("POST", "/settings/api/arasaac/get", raw=b'{"locales":["en"]}',
                                  headers={"Content-Type": "text/plain", "Sec-Fetch-Site": "cross-site"})
        self.assertEqual(status, 403)
        # Parseh's own page is let through
        status, _, got = self.ask("POST", "/settings/api/arasaac/state", {}, {"Sec-Fetch-Site": "same-origin"})
        self.assertEqual(status, 200)

    # ---- nothing a client sends becomes a path or an address
    def test_names_that_are_not_ARASAACs_are_refused_before_anything_is_made_or_asked(self):
        for body in ({"locales": ["ja"]}, {"locales": ["../../etc"]}, {"locales": ["en/../x"]}, {"locales": "en"},
                     {"locales": [5]}, {"locales": []}, {"locales": ["en"], "resolution": 2500},
                     {"locales": ["en"], "resolution": "300"}, {"locales": ["en"], "resolution": 300.5},
                     {"locales": ["hi"]}, {}):
            status, _, got = self.ask("POST", "/settings/api/arasaac/get", body)
            self.assertEqual(status, 400, body)
            self.assertFalse(got["ok"])
            self.assertTrue(got["error"].strip(), got)
            self.assertNotIn("Traceback", got["error"])
        for body in ({}, {"locale": "../x"}, {"locale": 5}, {"locale": ""}, {"all": "yes"}, {"all": 1}):
            self.assertEqual(self.ask("POST", "/settings/api/arasaac/remove", body)[0], 400, body)
        status, _, got = self.ask("POST", "/settings/api/arasaac/plan", {"locales": ["en", "x"]})
        self.assertEqual(status, 400)
        for raw in (b"[]", b"5", b'"x"', b"null"):
            status, _, got = self.ask("POST", "/settings/api/arasaac/get", raw=raw)
            self.assertIn(status, (200, 400), raw)
            self.assertFalse(got.get("ok") if isinstance(got, dict) else False, raw)
        self.assertEqual(self.fake.requests, [])
        self.assertFalse((self.tmp / "arasaac").exists())

    def test_the_plan_is_the_shipped_table_and_asks_nobody(self):
        status, _, got = self.ask("POST", "/settings/api/arasaac/plan", {"locales": ["en", "fr"], "resolution": 500})
        self.assertEqual(status, 200)
        self.assertTrue(got["measured"])
        self.assertEqual(got["pictures"]["files"], ga.MEASURED["pictograms"])
        self.assertEqual(sorted(got["words"]), ["en", "fr"])
        self.assertEqual(got["resolution"], 500)
        self.assertEqual(got["room"], "")
        self.assertEqual(self.fake.requests, [])

    def test_no_room_is_said_and_nothing_starts(self):
        with patch.object(ga, "disk_free", lambda p: 5 * 1000 * 1000):
            status, _, got = self.ask("POST", "/settings/api/arasaac/get", {"locales": ["en"]})
            self.assertEqual(status, 507)
            self.assertIn("not enough room", got["error"])
            status, _, plan = self.ask("POST", "/settings/api/arasaac/plan", {"locales": ["en"]})
            self.assertIn("not enough room", plan["room"], "and the plan says so before the button is pressed")
        self.assertEqual(self.fake.requests, [])

    # ---- the job
    def test_the_job_is_on_the_activity_list_and_a_second_press_is_the_same_job(self):
        self.fake.world.delay = 0.05
        status, _, got = self.ask("POST", "/settings/api/arasaac/get", {"locales": ["en"]})
        self.assertEqual((status, got), (200, {"ok": True}))
        self.wait(lambda: self.fake.count(r"/pictograms/\d+/") >= 3, "the pictures to begin")
        status, _, got = self.ask("POST", "/settings/api/arasaac/get", {"locales": ["en", "fr"]})
        self.assertEqual((status, got), (200, {"ok": True, "already": True}))
        status, _, act = self.ask("GET", "/__activity")
        mine = [e for e in act["running"] if e["id"].startswith("arasaac:get@")]
        self.assertEqual(len(mine), 1, act)
        self.assertEqual((mine[0]["kind"], mine[0]["label"], mine[0]["page"]),
                         ("lookup", "Getting the ARASAAC pictograms", "/settings/arasaac/"))
        self.assertEqual(mine[0]["total"], self.n)
        status, _, got = self.ask("POST", "/settings/api/arasaac/remove", {"all": True})
        self.assertEqual(status, 409, "nothing is removed while it is being fetched")
        self.assertIn("stop that first", got["error"])
        status, _, got = self.ask("POST", "/settings/api/arasaac/stop", {})
        self.assertEqual((status, got), (200, {"ok": True, "stopped": True}))
        self.wait(lambda: not ga.running(), "the stop")
        status, _, act = self.ask("GET", "/__activity")
        self.assertEqual([e for e in act["running"] if e["id"].startswith("arasaac:get@")], [], "it is not running any more")
        done = [e for e in act.get("finished", []) if e["id"].startswith("arasaac:get@")]
        self.assertTrue(done and done[0]["ok"] is False, "a stopped job is not 'done' and not a failure either: not ok")
        status, _, got = self.ask("POST", "/settings/api/arasaac/state", {})
        self.assertEqual(got["arasaac"]["state"], "partial")
        self.assertTrue(got["arasaac"]["job"]["stopped"])
        self.assertEqual(got["arasaac"]["job"]["error"], "")

    def test_a_failure_is_a_sentence_in_the_state_and_never_a_traceback_in_the_answer(self):
        self.fake.world.fail(r"/pictograms/\d+/", "500", times=999)
        status, _, got = self.ask("POST", "/settings/api/arasaac/get", {"locales": ["en"]})
        self.assertEqual(status, 200)
        self.wait(lambda: not ga.running(), "the failure")
        status, _, got = self.ask("POST", "/settings/api/arasaac/state", {})
        j = got["arasaac"]["job"]
        self.assertIn("after 4 tries", j["error"])
        self.assertFalse(j["stopped"])
        self.assertEqual(got["arasaac"]["state"], "partial")
        self.assertEqual(self.ask("POST", "/settings/api/arasaac/state", {})[0], 200, "the server is still answering")

    def test_the_whole_walk_a_page_would_make(self):
        status, _, plan = self.ask("POST", "/settings/api/arasaac/plan", {"locales": ["en"], "resolution": 300})
        self.assertEqual(status, 200)
        self.assertEqual(self.ask("POST", "/settings/api/arasaac/get", {"locales": ["en", "fr"], "resolution": 300})[0], 200)
        self.wait(self.installed, "the download")
        status, _, got = self.ask("POST", "/settings/api/arasaac/state", {})
        st = got["arasaac"]
        self.assertEqual((st["state"], st["files"], st["pictograms"], st["pending"], st["resolution"]), ("installed", self.n, self.n, 0, 300))
        self.assertEqual(sorted(st["locales"]), ["en", "fr"])
        rows = {r["code"]: r for r in got["languages"]}
        self.assertTrue(rows["en"]["here"] and rows["fr"]["here"] and not rows["es"]["here"])
        self.assertGreater(rows["en"]["kept_bytes"], 0)
        status, _, hub = self.ask("GET", "/settings/")
        card = hub.split('href="/settings/arasaac/"', 1)[1].split("</a>", 1)[0]
        self.assertIn("%d pictograms" % self.n, card)
        self.assertIn(">en<", card)
        self.assertIn(">fr<", card)
        # the credit is in the folder, and it is the credit
        text = (self.tmp / "arasaac" / "LICENSE-ARASAAC.txt").read_text(encoding="utf-8")
        self.assertIn(ga.CREDIT, text)


if __name__ == "__main__":
    unittest.main()
