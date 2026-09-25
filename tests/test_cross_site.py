# SPDX-License-Identifier: GPL-3.0-or-later
"""Only Parseh's own pages may change anything in it (lib/crosssite.py, TO-DO §3.1).

    python3 -m unittest tests/test_cross_site.py

A page on another site, open in the same browser, used to be able to post
to any route that writes -- stop the server, delete a book, replace Parseh
itself.  Now every request that is not a read is asked, once and before its
body is read, where it came from.  Here, as tests:

  * the rule itself, header by header: Sec-Fetch-Site `same-origin` and
    `none` pass, `same-site` (another port on localhost) and `cross-site` do
    not; with no Sec-Fetch-Site, an Origin that is not the request's own
    address is refused, `null` included; with neither header -- curl,
    serve.sh's stop, the launcher, the tests' own clients -- it passes;
  * THROUGH THE REAL SERVER, every header combination on a sample of the
    routes that write (Network, forgetting a device, the reading place,
    stopping the server, a dictionary's download and removal, an edit to a
    chunk, every upload door, the studio's and the decks' PUT, PATCH and
    DELETE, the pairing knock, the guide's compile), with the routes behind
    the check stood in for, so that each answer is the check's alone;
  * and with the routes themselves: a refused write changes nothing (the
    devices let in, the reading place, the server still running, no
    download started) and the same write from Parseh's own page does;
  * a refused body is never read as the next request on the connection;
  * every writing verb the handler answers is held to it, so a verb added
    later is too;
  * reads are untouched: a GET or a HEAD from another site is answered;
  * the studio run on its own (markdown/app/server.py) asks the same.

The real server, over plain http on a free port, with the network settings,
the reading place, the kept-file memories and the reading help's folders in
a temporary tree: nothing here writes the checkout's config/ or dict/.
"""
import http.client
import http.server
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in ("markdown/exlex", "markdown/app", "lib", "youtube/lib", "."):
    sys.path.insert(0, str(ROOT / p))
import crosssite                                               # noqa: E402
import network                                                 # noqa: E402

EVIL = "https://evil.example"


# ---------------------------------------------------------------- the rule
class Rule(unittest.TestCase):
    HOST = "127.0.0.1:7654"
    OWN = "https://127.0.0.1:7654"

    def said(self, **h):
        h = {k.replace("_", "-"): v for k, v in h.items()}
        h.setdefault("Host", self.HOST)
        return crosssite.refusal(h)

    def test_what_the_browser_says_of_the_site(self):
        self.assertIsNone(self.said(Sec_Fetch_Site="same-origin", Origin=self.OWN))
        self.assertIsNone(self.said(Sec_Fetch_Site="none"))
        self.assertIsNone(self.said(Sec_Fetch_Site="Same-Origin"), "the case is the browser's")
        for site in ("cross-site", "same-site", "something-new"):
            why = self.said(Sec_Fetch_Site=site)
            self.assertIn("another site", why, site)
            self.assertIn('"%s"' % site, why, "the refusal says what the browser said")
            self.assertIn("only Parseh's own pages may change anything", why)

    def test_another_port_on_this_computer_is_another_site(self):
        # a program on localhost:3000 is `same-site` to Parseh on :7654
        self.assertIsNotNone(self.said(Sec_Fetch_Site="same-site",
                                       Origin="https://127.0.0.1:3000"))
        # and, to a browser too old to say so, an Origin with another port
        self.assertIsNotNone(self.said(Origin="https://127.0.0.1:3000"))
        self.assertIsNotNone(self.said(Origin="http://127.0.0.1"))
        self.assertIsNotNone(self.said(Origin="https://localhost:7654"),
                             "another name for this computer is another origin")

    def test_with_no_sec_fetch_site_the_origin_decides(self):
        self.assertIsNone(self.said(Origin=self.OWN))
        self.assertIsNone(self.said(Origin="https://LOCALHOST:7654", Host="localhost:7654"))
        self.assertIsNone(self.said(Origin="https://[::1]:7654", Host="[::1]:7654"))
        # a port that is the scheme's own is written by neither, or by one
        self.assertIsNone(self.said(Origin="https://laptop.example", Host="laptop.example"))
        self.assertIsNone(self.said(Origin="https://laptop.example", Host="laptop.example:443"))
        why = self.said(Origin=EVIL)
        self.assertIn(EVIL, why)
        self.assertIsNotNone(self.said(Origin=EVIL, Host=""), "no Host: nothing to be the same as")
        self.assertIsNotNone(self.said(Origin="https://127.0.0.1:7654.evil.example"))
        self.assertIsNotNone(self.said(Origin="not an address"))

    def test_a_page_with_no_address_of_its_own_is_refused(self):
        # a file opened from the disk, or a sandboxed frame
        why = self.said(Origin="null")
        self.assertIn("no address of its own", why)

    def test_the_browser_is_believed_before_the_origin(self):
        # Parseh's own page asking for no referrer sends `Origin: null` on its
        # own writes; the browser has said, in the header only it writes,
        # that the request is same-origin
        self.assertIsNone(self.said(Sec_Fetch_Site="same-origin", Origin="null"))

    def test_neither_header_is_not_a_browser(self):
        # curl (serve.sh stop), urllib (the launcher), http.client and Deno's
        # fetch (the suites): none of them could be made to send this by a
        # page on another site
        self.assertIsNone(self.said())
        self.assertIsNone(crosssite.refusal({}))

    def test_what_only_reads_is_not_asked(self):
        self.assertEqual(crosssite.SAFE, ("GET", "HEAD"))


# ---------------------------------------------------------------- the real server
REFUSED = (
    ("another site", {"Sec-Fetch-Site": "cross-site", "Origin": EVIL}),
    ("another port on this computer", {"Sec-Fetch-Site": "same-site",
                                       "Origin": "http://127.0.0.1:{other}"}),
    ("an old browser on another site", {"Origin": EVIL}),
    ("an old browser on another port", {"Origin": "http://127.0.0.1:{other}"}),
    ("a file opened from the disk", {"Origin": "null"}),
)
ALLOWED = (
    ("curl, serve.sh's stop, the launcher, a test", {}),
    ("Parseh's own page", {"Sec-Fetch-Site": "same-origin", "Origin": "http://127.0.0.1:{port}"}),
    ("the person, typing the address", {"Sec-Fetch-Site": "none"}),
    ("an old browser on Parseh's own page", {"Origin": "http://127.0.0.1:{port}"}),
    ("Parseh's own page asking for no referrer", {"Sec-Fetch-Site": "same-origin",
                                                  "Origin": "null"}),
)
# A sample of what writes, one of each kind: settings that decide who may
# reach Parseh, the reading place, the stop, the reading help, an edit, every
# door a file comes in by, and the studio's and the decks' other verbs.
WRITES = (
    ("POST", "/settings/api/network"),
    ("POST", "/settings/api/forget"),
    ("POST", "/settings/api/code"),
    ("POST", "/settings/api/pair"),
    ("POST", "/__prefs"),
    ("POST", "/__shutdown"),
    ("POST", "/lookup/api/getdict"),
    ("POST", "/lookup/api/dropdict"),
    ("POST", "/books/english/mini-en/__edit/chunk"),
    ("POST", "/books/__delete"),
    ("POST", "/books/__upload"),
    ("POST", "/books/__restore"),
    ("POST", "/anki/sync/upload"),
    ("POST", "/exercises/api/import"),
    ("POST", "/youtube/api/upload"),
    ("POST", "/clips/api/upload"),
    ("DELETE", "/clips/api/some-clip.wav"),
    ("POST", "/studio/api/docs/zip"),
    ("PUT", "/studio/api/docs/some-doc"),
    ("DELETE", "/studio/api/docs/some-doc"),
    ("PATCH", "/exercises/api/decks/english/some-deck"),
    ("POST", "/settings/api/update/upload?name=x.zip"),
    ("POST", "/guide/__compile"),
)


def headers_for(h, port):
    return {k: v.format(port=port, other=port + 1 if port < 65535 else port - 1)
            for k, v in h.items()}


class Served(unittest.TestCase):
    """serve.py's own Handler on a free port, its stores in a temporary tree."""

    @classmethod
    def setUpClass(cls):
        import serve
        import prefs
        import offline
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
            patch.object(prefs, "STORE", str(tmp / "config" / "prefs.json")),
            patch.object(offline, "DIGESTS", str(tmp / "config" / "digests.json")),
            patch.object(offline, "WHERES", str(tmp / "config" / "wheres.json")),
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
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        for p in reversed(cls.patches):
            p.stop()
        network._CACHE.update({"key": None, "doc": None})
        cls._td.cleanup()

    def ask(self, method, path, headers=None, body=b"{}"):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        h = {"Content-Type": "application/json"}
        h.update(headers or {})
        c.request(method, path, body=body if method not in ("GET", "HEAD") else None, headers=h)
        r = c.getresponse()
        raw = r.read()
        c.close()
        try:
            got = json.loads(raw.decode("utf-8"))
        except ValueError:
            got = raw.decode("utf-8", "replace")
        return r.status, got

    def stood_in(self):
        """Everything behind the check, stood in for: the route is not run,
        and an answer of 200 {"reached": path} says the check let it by."""
        reached = []

        def behind(handler, method):
            n = int(handler.headers.get("Content-Length") or 0)
            if n:
                handler.rfile.read(n)
            reached.append((method, handler.path))
            handler.send_json({"ok": True, "reached": handler.path})
        p = patch.object(self.serve.Handler, "_dispatch_request", behind)
        p.start()
        self.addCleanup(p.stop)
        return reached

    # ---- the check alone, on every route of the sample
    def test_every_write_from_another_site_is_refused_before_its_route(self):
        reached = self.stood_in()
        for method, path in WRITES:
            for what, h in REFUSED:
                status, got = self.ask(method, path, headers_for(h, self.port))
                self.assertEqual(status, 403, (method, path, what))
                self.assertFalse(got["ok"])
                self.assertIn("only Parseh's own pages may change anything", got["error"],
                              (method, path, what))
        self.assertEqual(reached, [], "no refused request reached a route")

    def test_every_write_from_parsehs_own_page_goes_on(self):
        reached = self.stood_in()
        for method, path in WRITES:
            for what, h in ALLOWED:
                del reached[:]
                status, got = self.ask(method, path, headers_for(h, self.port))
                self.assertEqual((status, got.get("reached")), (200, path), (method, path, what))
                self.assertEqual(reached, [(method, path)])

    def test_every_writing_verb_the_handler_answers_is_asked(self):
        # the verbs are found, not listed: one added later is held to it too
        verbs = sorted(n[3:] for n in dir(self.serve.Handler) if n.startswith("do_"))
        writing = [v for v in verbs if v not in crosssite.SAFE]
        self.assertTrue({"POST", "PUT", "PATCH", "DELETE"} <= set(writing), verbs)
        reached = self.stood_in()
        for verb in writing:
            status, got = self.ask(verb, "/anything", {"Sec-Fetch-Site": "cross-site"})
            self.assertEqual(status, 403, verb)
            status, got = self.ask(verb, "/anything", {"Sec-Fetch-Site": "same-origin"})
            self.assertEqual(status, 200, verb)
        self.assertEqual([m for m, _p in reached], writing)

    # ---- reads
    def test_reads_are_not_asked(self):
        for h in [h for _w, h in REFUSED] + [{"Sec-Fetch-Site": "cross-site", "Origin": EVIL}]:
            h = headers_for(h, self.port)
            for path in ("/__activity", "/__prefs", "/licences/"):
                status, _got = self.ask("GET", path, h)
                self.assertEqual(status, 200, (path, h))
            c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
            c.request("HEAD", "/__activity", headers=h)
            r = c.getresponse()
            r.read()
            c.close()
            self.assertEqual(r.status, 200, h)

    # ---- the routes themselves
    def test_a_device_is_forgotten_only_from_parsehs_own_page(self):
        store = Path(network.STORE)
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text(json.dumps({"devices": {"a1b2c3d4e5f6": {"name": "a phone", "at": 1.0}}}),
                         encoding="utf-8")
        network._CACHE.update({"key": None, "doc": None})
        self.addCleanup(store.unlink)
        for _what, h in REFUSED:
            status, got = self.ask("POST", "/settings/api/forget", headers_for(h, self.port),
                                   json.dumps({"all": True}).encode())
            self.assertEqual(status, 403)
            self.assertIn("a1b2c3d4e5f6", network.settings()["devices"], "still let in")
        status, got = self.ask("POST", "/settings/api/forget",
                               headers_for(ALLOWED[1][1], self.port),
                               json.dumps({"all": True}).encode())
        self.assertEqual((status, got), (200, {"ok": True, "forgotten": 1}))
        self.assertEqual(network.settings()["devices"], {})

    def test_the_reading_place_is_written_only_from_parsehs_own_page(self):
        import prefs
        store = Path(prefs.STORE)
        body = json.dumps({"settings": {"parseh_theme": {"v": "dark"}}, "by": "a test"}).encode()
        for _what, h in REFUSED:
            status, _got = self.ask("POST", "/__prefs", headers_for(h, self.port), body)
            self.assertEqual(status, 403)
            self.assertFalse(store.exists(), "nothing was written")
        self.addCleanup(lambda: store.exists() and store.unlink())
        status, got = self.ask("POST", "/__prefs", headers_for(ALLOWED[1][1], self.port), body)
        self.assertEqual(status, 200)
        self.assertEqual(got["settings"]["parseh_theme"]["v"], "dark")
        self.assertTrue(store.exists())

    def test_the_server_is_stopped_only_by_its_own_pages_and_its_own_commands(self):
        stops = []

        def stop(handler):
            stops.append(handler.path)
            handler.send_json({"ok": True, "stopping": True})
        p = patch.object(self.serve.Handler, "_shutdown", stop)
        p.start()
        self.addCleanup(p.stop)
        for _what, h in REFUSED:
            status, _got = self.ask("POST", "/__shutdown", headers_for(h, self.port), b"")
            self.assertEqual(status, 403)
        self.assertEqual(stops, [])
        self.assertEqual(self.ask("GET", "/__activity")[0], 200, "still running")
        # serve.sh's `stop` is curl with no header at all; the page's button
        # is Parseh's own page
        for h in ({}, {"Sec-Fetch-Site": "same-origin"}):
            status, got = self.ask("POST", "/__shutdown", h, b"")
            self.assertEqual((status, got["stopping"]), (200, True))
        self.assertEqual(len(stops), 2)

    def test_a_download_is_not_started_from_another_site(self):
        s = self.serve
        s.DICT_JOBS.clear()
        body = json.dumps({"code": "en"}).encode()
        for _what, h in REFUSED:
            status, _got = self.ask("POST", "/lookup/api/getdict", headers_for(h, self.port), body)
            self.assertEqual(status, 403)
        self.assertEqual(dict(s.DICT_JOBS), {}, "no download was started")
        self.assertEqual(os.listdir(self.tmp / "dict") if (self.tmp / "dict").exists() else [], [])

    def test_the_updater_says_the_same_and_keeps_its_own_kind_of_body(self):
        # its own door asks for a zip or JSON as well (Handler._cross_site)
        status, got = self.ask("POST", "/settings/api/update/upload?name=x.zip",
                               {"Sec-Fetch-Site": "cross-site", "Content-Type": "application/zip"},
                               b"PK\x03\x04")
        self.assertEqual(status, 403)
        self.assertIn("another site", got["error"])
        status, got = self.ask("POST", "/settings/api/update/daily",
                               {"Content-Type": "text/plain"}, b"{}")
        self.assertEqual(status, 403)
        self.assertIn("application/json", got["error"])

    def test_a_refused_body_is_never_read_as_the_next_request(self):
        """The body of a refused request is left unread, so the connection
        is closed after the answer: were it kept, the body -- here, a whole
        second request -- would be read as the next one."""
        stops = []
        p = patch.object(self.serve.Handler, "_shutdown",
                         lambda h: (stops.append(1), h.send_json({"ok": True})))
        p.start()
        self.addCleanup(p.stop)
        inner = b"POST /__shutdown HTTP/1.1\r\nHost: x\r\nContent-Length: 0\r\n\r\n"
        outer = (b"POST /__prefs HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nSec-Fetch-Site: cross-site\r\n"
                 b"Content-Type: application/json\r\nContent-Length: %d\r\n\r\n"
                 % (self.port, len(inner))) + inner
        with socket.create_connection(("127.0.0.1", self.port), timeout=10) as sk:
            sk.sendall(outer)
            got = b""
            end = time.time() + 10
            while time.time() < end:
                try:
                    piece = sk.recv(65536)
                except (ConnectionResetError, socket.timeout):
                    break
                if not piece:
                    break
                got += piece
        self.assertTrue(got.startswith(b"HTTP/1.1 403"), got[:80])
        self.assertEqual(got.count(b"HTTP/1.1 "), 1, "one answer, and the connection closed")
        self.assertEqual(stops, [], "the body was not taken for a request")


# ---------------------------------------------------------------- the studio on its own
class StudioAlone(unittest.TestCase):
    """markdown/app/server.py's own Handler, as `python3 app/server.py` runs it."""

    @classmethod
    def setUpClass(cls):
        import serve
        cls.studio = serve.studio
        cls.quiet = patch.object(cls.studio.Handler, "log_message", lambda *a, **k: None)
        cls.quiet.start()
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), cls.studio.Handler)
        cls.srv.daemon_threads = True
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.quiet.stop()

    def ask(self, method, path, headers):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        c.request(method, path, body=b"{}" if method not in ("GET", "HEAD") else None,
                  headers=dict({"Content-Type": "application/json"}, **headers))
        r = c.getresponse()
        raw = r.read()
        c.close()
        return r.status, raw

    def test_its_writes_are_asked_and_its_reads_are_not(self):
        verbs = sorted(n[3:] for n in dir(self.studio.Handler) if n.startswith("do_"))
        writing = [v for v in verbs if v not in crosssite.SAFE]
        self.assertTrue({"POST", "PUT", "PATCH", "DELETE"} <= set(writing), verbs)
        for verb in writing:
            for _what, h in REFUSED:
                status, raw = self.ask(verb, "/api/no-such-thing", headers_for(h, self.port))
                self.assertEqual(status, 403, (verb, h))
                self.assertIn("only Parseh's own pages may change anything",
                              json.loads(raw)["error"])
            for _what, h in ALLOWED:
                # past the check, to a route that is not there
                status, _raw = self.ask(verb, "/api/no-such-thing", headers_for(h, self.port))
                self.assertEqual(status, 404, (verb, h))
        for verb in ("GET", "HEAD"):
            status, _raw = self.ask(verb, "/api/no-such-thing",
                                    {"Sec-Fetch-Site": "cross-site", "Origin": EVIL})
            self.assertEqual(status, 404, verb)


if __name__ == "__main__":
    unittest.main()
