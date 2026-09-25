# SPDX-License-Identifier: GPL-3.0-or-later
"""The downloads of the reading help: resumed, stopped, measured, checked.

    python3 -m unittest tests/test_download.py

lib/download.py is what every optional download goes through -- a
dictionary's extract, a corpus's exports, a translation model and its
engine, WordNet, a component pack -- and the promises it makes are each
held here against a real HTTP server started by the test, on this machine,
that can cut a connection half way, change its file between two requests,
refuse a HEAD, give no validator, or lie about which file a range came from:

  RESUMES     a cut connection keeps its .part and sidecar, and the next
              fetch asks for the rest (Range, If-Range) and ends whole;
  NO STITCH   a file changed since answers whole and is taken whole; a 206
              from a file that is not the one recorded is thrown away; a
              digest that fails after a resume is fetched whole once more;
  STOPS       cancel (an Event or a callable) raises Cancelled mid-stream,
              keeping what came, and a second fetch carries on;
  SAYS        progress(done, total, phase) from the first byte to the last,
              never more than about four times a second;
  CHECKED     a wrong SHA-256 is refused and nothing is left behind;
  PROBES      a size is read from a HEAD, or from a one-byte GET where HEAD
              is refused, and None where the server does not say.

And each of the five downloaders is held to the interface the Settings page
builds on: plan() answers in the one shape, from the MEASURED table where it
has the size and from a probe where it does not; its build entry passes
`progress` and `cancel` through to the download AND reports its own build
phase; and Stop in the build leaves the download for the next try and no
half-built file behind.  Their downloads are stubbed there -- nothing in this
file reaches the network, and nothing is written outside a temporary folder.
"""
import bz2
import email.utils
import hashlib
import http.server
import io
import json
import os
import socket
import sqlite3
import sys
import tarfile
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import download                                              # noqa: E402

PLAN_KEYS = {"download", "measured", "disk_peak", "kept", "have"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------- the test server
class Served:
    """One file the test server serves, and how it misbehaves."""

    def __init__(self, body, etag='"v1"', modified=True, length=True,
                 ranges=True, head=True, cut=None, trickle=0.0,
                 range_etag=None, if_range=True):
        self.body = body
        self.etag = etag
        self.modified = (email.utils.formatdate(1_700_000_000, usegmt=True)
                         if modified else None)
        self.length = length          # announce Content-Length
        self.ranges = ranges          # honour Range at all
        self.head = head              # answer HEAD (else 405)
        self.cut = cut                # the next GET sends this many bytes and hangs up
        self.trickle = trickle        # seconds to sleep between 16 kB blocks
        self.range_etag = range_etag  # the ETag a 206 claims (a lying server)
        self.if_range = if_range      # honour If-Range (else: a range of whatever it has now)

    def change(self, body, etag):
        self.body, self.etag = body, etag
        self.modified = email.utils.formatdate(1_800_000_000, usegmt=True)


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"     # one request a connection: a cut is a close

    def log_message(self, *a):
        pass

    def do_HEAD(self):
        self._answer(head=True)

    def do_GET(self):
        self._answer(head=False)

    def _answer(self, head):
        srv = self.server
        srv.seen.append((self.command, self.path, dict(self.headers)))
        f = srv.files.get(self.path)
        if f is None:
            self.send_error(404)
            return
        if head and not f.head:
            self.send_error(405)
            return
        body, status, first = f.body, 200, 0
        want = self.headers.get("Range")
        if want and f.ranges and not head:
            cond = self.headers.get("If-Range")
            if not cond or not f.if_range or cond in (f.etag, f.modified):
                first = int(want.split("=")[1].split("-")[0])
                if first >= len(body):
                    self.send_response(416)
                    self.send_header("Content-Range", "bytes */%d" % len(body))
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                status = 206
        part = body[first:]
        self.send_response(status)
        if status == 206:
            self.send_header("Content-Range", "bytes %d-%d/%d"
                             % (first, len(body) - 1, len(body)))
        etag = f.range_etag if (status == 206 and f.range_etag) else f.etag
        if etag:
            self.send_header("ETag", etag)
        if f.modified:
            self.send_header("Last-Modified", f.modified)
        if f.length:
            self.send_header("Content-Length", str(len(part)))
        self.end_headers()
        if head:
            return
        if f.cut is not None:
            part, f.cut = part[:f.cut], None
        for i in range(0, len(part), 16384):
            try:
                self.wfile.write(part[i:i + 16384])
                self.wfile.flush()
            except OSError:
                return
            if f.trickle:
                time.sleep(f.trickle)


class Server:
    def __init__(self):
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.files = {}
        self.httpd.seen = []
        self.thread = threading.Thread(target=self.httpd.serve_forever,
                                       daemon=True)
        self.thread.start()

    def url(self, path):
        return "http://127.0.0.1:%d%s" % (self.httpd.server_address[1], path)

    def serve(self, path, served):
        self.httpd.files[path] = served
        return self.url(path)

    def gets(self, path):
        return [h for m, p, h in self.httpd.seen if m == "GET" and p == path]

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


BODY = bytes(range(256)) * 4096                 # 1 MiB, every offset tellable


class ServerCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = Server()

    @classmethod
    def tearDownClass(cls):
        cls.srv.close()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = os.path.join(self.tmp.name, "file.bin")

    def tearDown(self):
        self.tmp.cleanup()

    def left(self):
        return sorted(os.listdir(self.tmp.name))


# ------------------------------------------------------------ download.py
class FetchTests(ServerCase):
    def test_a_whole_download_lands_whole_and_says_how_far(self):
        url = self.srv.serve("/whole", Served(BODY))
        calls, said = [], []
        download.fetch(url, self.dest, progress=lambda *c: calls.append(c),
                       say=said.append)
        self.assertEqual(Path(self.dest).read_bytes(), BODY)
        self.assertEqual(self.left(), ["file.bin"], "no .part or sidecar left")
        self.assertEqual(calls[0], (0, len(BODY), "download"))
        self.assertEqual(calls[-1], (len(BODY), len(BODY), "download"))
        self.assertTrue(all(b[0] >= a[0] for a, b in zip(calls, calls[1:])))
        self.assertEqual(said[-1].strip(), "1 MB", said)

    def test_the_phase_is_the_callers(self):
        url = self.srv.serve("/phase", Served(BODY[:1000]))
        calls = []
        download.fetch(url, self.dest, progress=lambda *c: calls.append(c),
                       phase="engine")
        self.assertEqual({c[2] for c in calls}, {"engine"})

    def test_progress_is_at_most_about_four_calls_a_second(self):
        url = self.srv.serve("/slow", Served(BODY[:320 * 1024], trickle=0.06))
        calls = []
        t0 = time.monotonic()
        download.fetch(url, self.dest, progress=lambda *c: calls.append(c))
        spent = time.monotonic() - t0
        self.assertGreater(spent, 1.0, "the trickle made it take a while")
        # four a second, and the first and the last call on top
        self.assertLessEqual(len(calls), 4 * spent + 3, (len(calls), spent))
        self.assertGreaterEqual(len(calls), 4, "and it did report on the way")

    def test_a_cut_connection_is_resumed_where_it_stopped(self):
        served = Served(BODY, cut=300_000)
        url = self.srv.serve("/cut", served)
        with self.assertRaises(download.Incomplete):
            download.fetch(url, self.dest)
        self.assertFalse(os.path.exists(self.dest), "never a half file at dest")
        self.assertEqual(os.path.getsize(self.dest + ".part"), 300_000)
        side = json.loads(Path(self.dest + ".part.json").read_text())
        self.assertEqual((side["url"], side["etag"], side["size"]),
                         (url, '"v1"', len(BODY)))
        self.assertEqual(download.leftover(self.dest), 300_000)
        calls, said = [], []
        download.fetch(url, self.dest, progress=lambda *c: calls.append(c),
                       say=said.append)
        self.assertEqual(Path(self.dest).read_bytes(), BODY)
        second = self.srv.gets("/cut")[-1]
        self.assertEqual(second.get("Range"), "bytes=300000-")
        self.assertEqual(second.get("If-Range"), '"v1"')
        self.assertEqual(calls[0][0], 300_000, "the bar starts where it stopped")
        self.assertIn("carrying on from 0.3 MB of 1 MB", said[0])
        self.assertEqual(self.left(), ["file.bin"])

    def test_a_file_changed_since_is_fetched_whole_not_stitched(self):
        served = Served(BODY, cut=300_000)
        url = self.srv.serve("/changed", served)
        with self.assertRaises(download.Incomplete):
            download.fetch(url, self.dest)
        new = bytes(reversed(BODY))
        served.change(new, '"v2"')
        download.fetch(url, self.dest)
        self.assertEqual(Path(self.dest).read_bytes(), new)
        self.assertEqual(self.srv.gets("/changed")[-1].get("If-Range"), '"v1"',
                         "asked for the rest only if it was still v1")

    def test_a_206_for_another_version_is_thrown_away(self):
        # a server that ignores If-Range and answers the range of its NEW
        # file: the ETag on the 206 gives it away, and the rest is not
        # appended to the old start
        served = Served(BODY, cut=300_000)
        url = self.srv.serve("/liar", served)
        with self.assertRaises(download.Incomplete):
            download.fetch(url, self.dest)
        new = bytes(reversed(BODY))
        served.change(new, '"v2"')
        served.modified, served.if_range = None, False
        download.fetch(url, self.dest)
        self.assertEqual(Path(self.dest).read_bytes(), new)
        gets = self.srv.gets("/liar")
        self.assertEqual(gets[-2].get("Range"), "bytes=300000-")
        self.assertNotIn("Range", gets[-1], "and it started again, whole")

    def test_a_stitch_the_headers_hide_is_caught_by_the_digest(self):
        # the worst server: it changed its file and still calls every answer
        # v1.  The digest fails after the resume, and the file is fetched
        # whole once more rather than refused.
        served = Served(BODY, cut=300_000)
        url = self.srv.serve("/stitch", served)
        with self.assertRaises(download.Incomplete):
            download.fetch(url, self.dest, sha256=sha(BODY))
        new = bytes(reversed(BODY))
        served.body = new                     # same ETag, same date
        said = []
        download.fetch(url, self.dest, sha256=sha(new), say=said.append)
        self.assertEqual(Path(self.dest).read_bytes(), new)
        self.assertTrue(any("did not match" in s for s in said), said)
        self.assertNotIn("Range", self.srv.gets("/stitch")[-1])

    def test_no_validator_means_no_resume(self):
        served = Served(BODY, etag=None, modified=False, cut=300_000)
        url = self.srv.serve("/novalid", served)
        with self.assertRaises(download.Incomplete):
            download.fetch(url, self.dest)
        download.fetch(url, self.dest)
        self.assertEqual(Path(self.dest).read_bytes(), BODY)
        self.assertNotIn("Range", self.srv.gets("/novalid")[-1],
                         "nothing to tell its versions apart by: whole again")

    def test_a_server_that_cannot_resume_is_taken_whole(self):
        served = Served(BODY, cut=300_000, ranges=False)
        url = self.srv.serve("/norange", served)
        with self.assertRaises(download.Incomplete):
            download.fetch(url, self.dest)
        download.fetch(url, self.dest)
        self.assertEqual(Path(self.dest).read_bytes(), BODY)

    def test_a_part_cut_just_before_its_rename_is_whole(self):
        url = self.srv.serve("/done", Served(BODY))
        Path(self.dest + ".part").write_bytes(BODY)
        Path(self.dest + ".part.json").write_text(json.dumps(
            {"url": url, "etag": '"v1"', "last_modified": "", "size": len(BODY)}))
        download.fetch(url, self.dest, sha256=sha(BODY))
        self.assertEqual(Path(self.dest).read_bytes(), BODY)
        self.assertEqual(self.left(), ["file.bin"])

    def test_a_part_from_another_url_is_not_resumed(self):
        url = self.srv.serve("/other", Served(BODY))
        Path(self.dest + ".part").write_bytes(b"x" * 1000)
        Path(self.dest + ".part.json").write_text(json.dumps(
            {"url": url + "?old", "etag": '"v1"', "last_modified": "",
             "size": len(BODY)}))
        download.fetch(url, self.dest)
        self.assertEqual(Path(self.dest).read_bytes(), BODY)
        self.assertNotIn("Range", self.srv.gets("/other")[-1])

    def test_stop_mid_stream_keeps_what_came_and_carries_on(self):
        url = self.srv.serve("/stop", Served(BODY))
        asked = []

        def cancel():                 # Stop, pressed after the fifth block
            asked.append(1)
            return len(asked) > 5
        with self.assertRaises(download.Cancelled):
            download.fetch(url, self.dest, cancel=cancel)
        self.assertFalse(os.path.exists(self.dest))
        have = os.path.getsize(self.dest + ".part")
        self.assertEqual(have, 4 * download.BLOCK,
                         "stopped between blocks, the ones read kept")
        stop = threading.Event()
        download.fetch(url, self.dest, cancel=stop)
        self.assertEqual(Path(self.dest).read_bytes(), BODY)
        self.assertEqual(self.srv.gets("/stop")[-1].get("Range"),
                         "bytes=%d-" % have)

    def test_stop_by_an_event(self):
        url = self.srv.serve("/event", Served(BODY, trickle=0.02))
        stop = threading.Event()

        def progress(done, total, phase):
            if done >= 100_000:
                stop.set()
        with self.assertRaises(download.Cancelled):
            download.fetch(url, self.dest, progress=progress, cancel=stop)
        self.assertTrue(0 < os.path.getsize(self.dest + ".part") < len(BODY))
        self.assertTrue(os.path.isfile(self.dest + ".part.json"))

    def test_a_wrong_digest_is_refused_and_leaves_nothing(self):
        url = self.srv.serve("/wrong", Served(BODY))
        with self.assertRaises(download.Mismatch) as caught:
            download.fetch(url, self.dest, sha256=sha(b"something else"))
        self.assertIsInstance(caught.exception, ValueError)
        self.assertIn(sha(BODY), str(caught.exception))
        self.assertEqual(self.left(), [], "not renamed into place, not kept")

    def test_the_right_digest_is_accepted(self):
        url = self.srv.serve("/right", Served(BODY))
        download.fetch(url, self.dest, sha256=sha(BODY).upper())
        self.assertEqual(Path(self.dest).read_bytes(), BODY)

    def test_a_file_over_its_limit_is_refused(self):
        url = self.srv.serve("/big", Served(BODY))
        with self.assertRaises(ValueError):
            download.fetch(url, self.dest, limit=100_000)
        self.assertEqual(self.left(), [])
        url = self.srv.serve("/big2", Served(BODY, length=False))
        with self.assertRaises(ValueError):
            download.fetch(url, self.dest, limit=100_000)
        self.assertEqual(self.left(), [])

    def test_no_length_uses_the_size_parseh_knows_for_the_bar(self):
        url = self.srv.serve("/nolen", Served(BODY, length=False))
        calls = []
        download.fetch(url, self.dest, size=len(BODY),
                       progress=lambda *c: calls.append(c))
        self.assertEqual(calls[0], (0, len(BODY), "download"))
        self.assertEqual(Path(self.dest).read_bytes(), BODY)

    def test_resume_false_starts_again(self):
        served = Served(BODY, cut=300_000)
        url = self.srv.serve("/fresh", served)
        with self.assertRaises(download.Incomplete):
            download.fetch(url, self.dest)
        download.fetch(url, self.dest, resume=False)
        self.assertNotIn("Range", self.srv.gets("/fresh")[-1])
        self.assertEqual(Path(self.dest).read_bytes(), BODY)

    def test_an_error_is_urllibs_own(self):
        import urllib.error
        with self.assertRaises(urllib.error.HTTPError) as caught:
            download.fetch(self.srv.url("/nothing-here"), self.dest)
        self.assertEqual(caught.exception.code, 404)
        self.assertEqual(self.left(), [])

    def test_two_jobs_wanting_one_file_do_not_mix_their_bytes(self):
        url = self.srv.serve("/shared", Served(BODY, trickle=0.004))
        errors = []

        def job():
            try:
                download.fetch(url, self.dest)
            except Exception as e:          # noqa: BLE001 -- reported below
                errors.append(e)
        jobs = [threading.Thread(target=job) for _ in range(2)]
        for t in jobs:
            t.start()
        for t in jobs:
            t.join(60)
        self.assertEqual(errors, [])
        self.assertEqual(Path(self.dest).read_bytes(), BODY)
        self.assertEqual(self.left(), ["file.bin"])

    def test_discard(self):
        url = self.srv.serve("/discard", Served(BODY, cut=1000))
        with self.assertRaises(download.Incomplete):
            download.fetch(url, self.dest)
        download.discard(self.dest)
        self.assertEqual(self.left(), [])
        self.assertEqual(download.leftover(self.dest), 0)


class ProbeTests(ServerCase):
    def test_from_a_head(self):
        url = self.srv.serve("/p1", Served(BODY))
        self.assertEqual(download.probe(url), len(BODY))
        self.assertEqual([m for m, p, h in self.srv.httpd.seen if p == "/p1"],
                         ["HEAD"], "no body asked for")

    def test_from_one_byte_where_head_is_refused(self):
        url = self.srv.serve("/p2", Served(BODY, head=False))
        self.assertEqual(download.probe(url), len(BODY))
        self.assertEqual(self.srv.gets("/p2")[-1].get("Range"), "bytes=0-0")

    def test_none_where_the_server_does_not_say(self):
        url = self.srv.serve("/p3", Served(BODY, length=False, ranges=False))
        self.assertIsNone(download.probe(url))

    def test_none_where_nobody_answers(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        self.assertIsNone(download.probe("http://127.0.0.1:%d/x" % port,
                                         timeout=5))


class MeterTests(unittest.TestCase):
    def test_throttled_ended_and_stopped(self):
        calls = []
        m = download.Meter(lambda *c: calls.append(c), total=1000)
        for i in range(10_000):
            m.at(i % 1000)
        self.assertEqual(len(calls), 1, "four a second at most")
        m.end()
        self.assertEqual(calls[-1], (1000, 1000, "build"))
        stop = threading.Event()
        m = download.Meter(None, stop, total=10)
        m.at(1)
        stop.set()
        with self.assertRaises(download.Cancelled):
            m.at(2)

    def test_shares_are_one_bar(self):
        calls = []
        m = download.Meter(lambda *c: calls.append(c))
        first, second = m.share(0, 0.25), m.share(0.25, 1.0)
        first(1.0)
        time.sleep(download.TICK + 0.01)
        second(0.5)
        self.assertEqual(calls, [(250, 1000, "build"), (625, 1000, "build")])

    def test_shifted(self):
        calls = []
        f = download.shifted(lambda *c: calls.append(c), 100, 300)
        f(50, 200, "download")
        self.assertEqual(calls, [(150, 300, "download")])
        self.assertIsNone(download.shifted(None, 0, 10))

    def test_plan_shape(self):
        p = download.plan(1000, measured=True, kept=400, have=300)
        self.assertEqual(p, {"download": 1000, "measured": True,
                             "disk_peak": 1100, "kept": 400, "have": 300})
        p = download.plan(None, measured=True)
        self.assertFalse(p["measured"], "a size nobody has is not measured")
        self.assertIsNone(p["disk_peak"])


# ------------------------------------------------- the five downloaders
class Recorder:
    """A stand-in for download.fetch: writes what the test says each URL
    holds, reports it as the real one does, honours Stop, and remembers what
    it was handed."""

    def __init__(self, contents):
        self.contents = contents              # url basename -> bytes
        self.calls = []

    def __call__(self, url, dest, **kw):
        self.calls.append((url, dest, kw))
        download.check(kw.get("cancel"))
        body = self.contents[url.rsplit("/", 1)[-1]]
        if kw.get("sha256"):
            self.test_sha = kw["sha256"]
        progress = kw.get("progress")
        if progress:
            progress(len(body) // 2, len(body), kw.get("phase", "download"))
            progress(len(body), len(body), kw.get("phase", "download"))
        with open(dest, "wb") as f:
            f.write(body)
        return dest


class Watch:
    """progress and cancel for a build: records the phases, and presses
    Stop at the first report of the phase named."""

    def __init__(self, stop_in=None):
        self.calls, self.stop_in, self.asked = [], stop_in, 0

    def progress(self, done, total, phase):
        self.calls.append((done, total, phase))

    def cancel(self):
        self.asked += 1
        return bool(self.stop_in and any(c[2] == self.stop_in for c in self.calls))

    def phases(self):
        return [p for i, (_d, _t, p) in enumerate(self.calls)
                if i == 0 or self.calls[i - 1][2] != p]


class DownloaderCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def assertPlan(self, p):
        self.assertEqual(set(p), PLAN_KEYS, p)
        for k in ("download", "disk_peak", "kept"):
            self.assertTrue(p[k] is None or isinstance(p[k], int), (k, p))
        self.assertIsInstance(p["measured"], bool)


JSONL = "\n".join(json.dumps(o, ensure_ascii=False) for o in [
    {"word": "کتاب", "lang_code": "fa", "pos": "noun",
     "senses": [{"glosses": ["book"]}]},
    {"word": "خانه", "lang_code": "fa", "pos": "noun",
     "senses": [{"glosses": ["house"]}]},
    {"word": "کتاب‌ها", "lang_code": "fa", "pos": "noun",
     "senses": [{"glosses": ["plural of کتاب"], "form_of": [{"word": "کتاب"}]}]},
]).encode("utf-8") + b"\n"


class GetdictTests(DownloaderCase):
    def setUp(self):
        super().setUp()
        import getdict
        import lookup
        self.getdict = getdict
        self.dicts = patch.object(lookup, "DICT_DIR", str(self.dir / "dict"))
        self.dicts.start()
        self.out = str(self.dir / "out" / "fa.db")

    def tearDown(self):
        self.dicts.stop()
        super().tearDown()

    def test_plan(self):
        g = self.getdict
        p = g.plan("tr", probe=False)
        self.assertPlan(p)
        self.assertEqual((p["download"], p["measured"], p["kept"]),
                         (431_000_000, True, 306_000_000))
        self.assertEqual(p["disk_peak"], 737_000_000,
                         "the extract and the dictionary side by side")
        with patch.object(download, "probe", return_value=91_000_000) as asked:
            p = g.plan("fa")
        self.assertEqual((p["download"], p["measured"], p["kept"]),
                         (91_000_000, False, 21_000_000))
        self.assertIn("kaikki.org", asked.call_args[0][0])
        with patch.object(download, "probe", return_value=50_000_000):
            p = g.plan("ar")
        self.assertEqual(p["disk_peak"], 100_000_000,
                         "unmeasured: room for a dictionary as big as its extract")
        self.assertIsNone(g.plan("ar", probe=False)["download"])
        self.assertEqual(g.plan("tr", keep=True, probe=False)["kept"],
                         737_000_000)

    def test_build_passes_progress_and_stop_through(self):
        fake = Recorder({"kaikki.org-dictionary-Persian.jsonl": JSONL})
        w = Watch()
        with patch.object(download, "fetch", fake):
            n = self.getdict.build("fa", out=self.out, say=lambda m: None,
                                   progress=w.progress, cancel=w.cancel)
        self.assertEqual(n, 2)
        kw = fake.calls[0][2]
        self.assertEqual(kw["progress"], w.progress)
        self.assertEqual(kw["cancel"], w.cancel)
        self.assertEqual(w.phases(), ["download", "build"])
        self.assertEqual(w.calls[-1], (len(JSONL), len(JSONL), "build"))
        self.assertGreater(w.asked, 2, "Stop was asked during the build too")

    def test_stop_in_the_build_keeps_the_download_and_the_old_dictionary(self):
        os.makedirs(os.path.dirname(self.out))
        Path(self.out).write_bytes(b"the dictionary that was here")
        fake = Recorder({"kaikki.org-dictionary-Persian.jsonl": JSONL})
        w = Watch(stop_in="build")
        with patch.object(download, "fetch", fake), \
                self.assertRaises(download.Cancelled):
            self.getdict.build("fa", out=self.out, say=lambda m: None,
                               progress=w.progress, cancel=w.cancel)
        self.assertEqual(Path(self.out).read_bytes(),
                         b"the dictionary that was here")
        self.assertFalse(os.path.exists(self.out + ".part"), "no half-built file")
        extract = self.dir / "dict" / "fa.jsonl"
        self.assertTrue(extract.is_file(), "the download is kept")
        said = []
        with patch.object(download, "fetch", fake):
            self.getdict.build("fa", out=self.out, say=said.append)
        self.assertEqual(len(fake.calls), 1, "and used, not fetched again")
        self.assertTrue(any("already here" in s for s in said))
        self.assertFalse(extract.exists(), "and deleted once built")

    def test_discard(self):
        extract = self.dir / "dict" / "fa.jsonl"
        extract.parent.mkdir()
        extract.write_bytes(b"x" * 10)
        Path(str(extract) + ".part").write_bytes(b"y" * 5)
        Path(str(extract) + ".part.json").write_text("{}")
        self.assertEqual(self.getdict.plan("fa", probe=False)["have"], 10)
        self.assertEqual(self.getdict.discard("fa"), 15)
        self.assertEqual(list(extract.parent.iterdir()), [])


def _bz2(text):
    return bz2.compress(text.encode("utf-8"))


EXPORTS = {
    "ita-eng_links.tsv.bz2": _bz2("1\t11\n2\t12\n3\t13\n"),
    "ita_sentences.tsv.bz2": _bz2("1\tita\tIl gatto dorme.\n"
                                  "2\tita\tLa casa è grande.\n"
                                  "3\tita\tIl cane corre.\n"),
    "eng_sentences.tsv.bz2": _bz2("11\teng\tThe cat sleeps.\n"
                                  "12\teng\tThe house is big.\n"
                                  "13\teng\tThe dog runs.\n"),
}


class GetcorpusTests(DownloaderCase):
    def setUp(self):
        super().setUp()
        import corpus
        import getcorpus
        self.getcorpus = getcorpus
        self.corpora = patch.object(corpus, "CORPUS_DIR", str(self.dir / "corpus"))
        self.corpora.start()

    def tearDown(self):
        self.corpora.stop()
        super().tearDown()

    def test_plan(self):
        g = self.getcorpus
        p = g.plan("it", "en", probe=False)
        self.assertPlan(p)
        self.assertEqual((p["download"], p["measured"], p["kept"]),
                         (38_200_000, True, 182_600_000))
        with patch.object(download, "probe", return_value=1_000_000) as asked:
            p = g.plan("ar", "en")
        self.assertEqual(asked.call_count, 3, "the three exports asked")
        self.assertEqual((p["download"], p["measured"], p["kept"]),
                         (3_000_000, False, None))
        self.assertEqual(p["disk_peak"], 3_000_000 + g.BOUND * 3_000_000)
        with patch.object(download, "probe", return_value=None):
            self.assertIsNone(g.plan("ar", "en")["download"])

    def test_build_is_one_bar_then_a_build(self):
        fake = Recorder(EXPORTS)
        sizes = {k: len(v) for k, v in EXPORTS.items()}
        w = Watch()
        with patch.object(download, "fetch", fake), \
                patch.object(download, "probe",
                             side_effect=lambda url, *a, **k: sizes[url.rsplit("/", 1)[-1]]):
            n = self.getcorpus.build("it", "en", say=lambda m: None,
                                     progress=w.progress, cancel=w.cancel)
        self.assertEqual(n, 3)
        self.assertTrue(all(c[2]["cancel"] == w.cancel for c in fake.calls))
        self.assertEqual(w.phases(), ["download", "build"])
        dl = [c for c in w.calls if c[2] == "download"]
        whole = sum(sizes.values())
        self.assertEqual({t for _d, t, _p in dl}, {whole}, "one bar, three files")
        self.assertEqual(dl[-1][0], whole)
        self.assertEqual(w.calls[-1][0], w.calls[-1][1], "the build ends full")

    def test_stop_in_the_build(self):
        fake = Recorder(EXPORTS)
        w = Watch(stop_in="build")
        with patch.object(download, "fetch", fake), \
                patch.object(download, "probe", return_value=None), \
                self.assertRaises(download.Cancelled):
            self.getcorpus.build("it", "en", say=lambda m: None,
                                 progress=w.progress, cancel=w.cancel)
        folder = self.dir / "corpus"
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ["_dl"],
                         "no corpus and no half-built one")
        self.assertEqual(sorted(p.name for p in (folder / "_dl").iterdir()),
                         sorted(EXPORTS), "the downloads are kept")
        self.assertEqual(self.getcorpus.plan("it", "en", probe=False)["have"],
                         sum(len(b) for b in EXPORTS.values()))
        self.assertEqual(self.getcorpus.discard("it", "en"),
                         sum(len(b) for b in EXPORTS.values()))
        self.assertEqual(list((folder / "_dl").iterdir()), [])


class GetmtTests(DownloaderCase):
    FILES = {"model.faen.bin": b"M" * 5000, "lex.faen.bin": b"L" * 300,
             "vocab.faen.spm": b"V" * 200}

    def setUp(self):
        super().setUp()
        import getmt
        self.getmt = getmt
        self.patches = [patch.object(getmt, "MT_DIR", str(self.dir / "mt")),
                        patch.object(getmt, "ENGINE_DIR", str(self.dir / "mt" / "engine")),
                        patch.object(getmt, "_records", lambda say=print: self.records())]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        super().tearDown()

    def records(self):
        kinds = {"model.faen.bin": "model", "lex.faen.bin": "lex",
                 "vocab.faen.spm": "vocab"}
        return [{"fromLang": "fa", "toLang": "en", "fileType": kinds[n],
                 "version": "1.0",
                 "attachment": {"location": "loc/" + n, "filename": n,
                                "hash": sha(b), "size": len(b)}}
                for n, b in self.FILES.items()]

    def engine_here(self):
        os.makedirs(self.getmt.ENGINE_DIR)
        for f in self.getmt.ENGINE_FILES:
            Path(self.getmt.ENGINE_DIR, f).write_bytes(b"engine")

    def test_the_engine_is_pinned(self):
        pins = self.getmt.ENGINE_SHA256
        self.assertEqual(set(pins), set(self.getmt.ENGINE_FILES))
        for name, (digest, size) in pins.items():
            self.assertRegex(digest, r"^[0-9a-f]{64}$", name)
            self.assertGreater(size, 0)

    def test_an_engine_that_is_not_the_pinned_one_is_refused(self):
        srv = Server()
        try:
            for f in self.getmt.ENGINE_FILES:
                srv.serve("/worker/" + f, Served(b"not bergamot: " + f.encode()))
            with patch.object(self.getmt, "ENGINE_BASE", srv.url("/worker")), \
                    self.assertRaises(SystemExit) as caught:
                self.getmt.get_engine(say=lambda m: None)
        finally:
            srv.close()
        self.assertIn("SHA-256", str(caught.exception))
        self.assertFalse(self.getmt.engine_ready())
        self.assertEqual(os.listdir(self.getmt.ENGINE_DIR), [],
                         "nothing installed, nothing half kept")

    def test_plan(self):
        g = self.getmt
        p = g.plan("fa", "en", probe=False)
        self.assertPlan(p)
        engine = sum(size for _d, size in g.ENGINE_SHA256.values())
        self.assertEqual((p["download"], p["measured"]),
                         (21_900_000 + engine, True), "the engine counted once")
        self.engine_here()
        p = g.plan("fa", "en", probe=False)
        self.assertEqual(p["download"], p["kept"])
        self.assertEqual(p["download"], 21_900_000)
        with patch.object(g, "MEASURED", {}):
            p = g.plan("fa", "en")
        self.assertEqual((p["download"], p["measured"]),
                         (sum(len(b) for b in self.FILES.values()), False),
                         "read from the service's own list")
        with patch.object(g, "MEASURED", {}):
            self.assertIsNone(g.plan("fa", "en", probe=False)["download"])

    def test_build_is_one_bar_checked_and_resumed(self):
        self.engine_here()
        fake = Recorder(dict(self.FILES))
        w = Watch()
        stop = {"after": 1}

        def cancel():                 # Stop once the first file is in
            return len(fake.calls) > stop["after"]
        with patch.object(download, "fetch", fake), \
                self.assertRaises(download.Cancelled):
            self.getmt.build("fa", "en", say=lambda m: None,
                             progress=w.progress, cancel=cancel)
        part = Path(self.getmt.path_for("fa", "en") + ".part")
        self.assertEqual(len(list(part.iterdir())), 1, "the first file kept")
        self.assertFalse(self.getmt.available("fa", "en"))
        stop["after"] = 99
        with patch.object(download, "fetch", fake):
            self.getmt.build("fa", "en", say=lambda m: None,
                             progress=w.progress, cancel=cancel)
        self.assertEqual(len(fake.calls), 1 + 1 + 2,
                         "stopped at the second; the first not fetched again")
        for url, dest, kw in fake.calls:
            self.assertEqual(kw["sha256"], sha(self.FILES[os.path.basename(dest)]),
                             "every model file checked against its record")
        whole = sum(len(b) for b in self.FILES.values())
        self.assertEqual({t for _d, t, _p in w.calls}, {whole})
        self.assertEqual(w.calls[-1][0], whole)
        self.assertTrue(self.getmt.available("fa", "en"))
        self.assertFalse(part.exists())

    def test_discard(self):
        part = Path(self.getmt.path_for("fa", "en") + ".part")
        part.mkdir(parents=True)
        (part / "model.faen.bin.part").write_bytes(b"x" * 10)
        self.assertEqual(self.getmt.discard("fa", "en"), 10)
        self.assertFalse(part.exists())


def _wordnet():
    """A four-part-of-speech WordNet archive as small as one can be."""
    buf = io.BytesIO()
    files = {
        "dict/index.verb": "begin v 1 0 1 1 00000001  \nstart v 1 0 1 1 00000001  \n",
        "dict/data.verb": "00000001 03 v 02 begin 0 start 0 000 | x  \n",
        "dict/index.noun": "", "dict/data.noun": "",
        "dict/index.adj": "", "dict/data.adj": "",
        "dict/index.adv": "", "dict/data.adv": ""}
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, text in files.items():
            b = text.encode("latin-1")
            info = tarfile.TarInfo(name)
            info.size = len(b)
            tf.addfile(info, io.BytesIO(b))
    return buf.getvalue()


class GetsynTests(DownloaderCase):
    def setUp(self):
        super().setUp()
        import getsyn
        self.getsyn = getsyn
        self.patches = [patch.object(getsyn, "MT_DIR", str(self.dir)),
                        patch.object(getsyn, "OUT", str(self.dir / "synonyms.en.json"))]
        for p in self.patches:
            p.start()
        self.fake = Recorder({"wn3.1.dict.tar.gz": _wordnet()})

    def tearDown(self):
        for p in self.patches:
            p.stop()
        super().tearDown()

    def test_plan(self):
        p = self.getsyn.plan()
        self.assertPlan(p)
        self.assertEqual((p["download"], p["measured"]), self.getsyn.MEASURED[:1] + (True,))
        with patch.object(download, "fetch", self.fake):
            self.getsyn.get(say=lambda m: None)
        p = self.getsyn.plan()
        self.assertEqual((p["download"], p["disk_peak"]), (0, 0),
                         "installed: nothing to do")
        self.assertEqual(self.getsyn.plan(force=True)["download"],
                         self.getsyn.MEASURED[0])

    def test_get_passes_progress_and_stop_through(self):
        w = Watch()
        with patch.object(download, "fetch", self.fake):
            self.assertTrue(self.getsyn.get(say=lambda m: None, force=True,
                                            progress=w.progress, cancel=w.cancel))
        self.assertEqual(self.fake.calls[0][2]["cancel"], w.cancel)
        self.assertEqual(w.phases(), ["download", "build"])
        self.assertEqual(w.calls[-1][0], w.calls[-1][1])
        table = json.loads(Path(self.getsyn.OUT).read_text())["synonyms"]
        self.assertEqual(table["begin"], ["start"])
        self.assertEqual(sorted(os.listdir(self.dir)), ["synonyms.en.json"],
                         "the archive goes once the table is written")

    def test_stop_in_the_build(self):
        w = Watch(stop_in="build")
        with patch.object(download, "fetch", self.fake), \
                self.assertRaises(download.Cancelled):
            self.getsyn.get(say=lambda m: None, progress=w.progress,
                            cancel=w.cancel)
        self.assertFalse(self.getsyn.installed(), "no table, not half of one")
        self.assertEqual(os.listdir(self.dir), ["wn3.1.dict.tar.gz"])
        with patch.object(download, "fetch", self.fake):
            self.getsyn.get(say=lambda m: None)
        self.assertEqual(len(self.fake.calls), 1, "the archive kept is used")
        self.assertTrue(self.getsyn.installed())

    def test_discard(self):
        archive = self.dir / "wn3.1.dict.tar.gz"
        archive.write_bytes(b"x" * 7)
        self.assertEqual(self.getsyn.plan()["have"], 7)
        self.assertEqual(self.getsyn.discard(), 7)
        self.assertEqual(os.listdir(self.dir), [])


# four hundred characters: the build reports every two hundred entries
MMAH = "".join(json.dumps({"character": chr(0x4E00 + i), "decomposition": "⿰木目"}) + "\n"
               for i in range(400)).encode()


class GetdecompositionTests(DownloaderCase):
    def setUp(self):
        super().setUp()
        import decomposition
        import getdecomposition
        self.g = getdecomposition
        repo, rev, name, _digest = getdecomposition.SOURCES["makemeahanzi"]
        self.patches = [
            patch.object(decomposition, "DATA_DIR", self.dir / "components"),
            patch.dict(getdecomposition.SOURCES,
                       {"makemeahanzi": (repo, rev, name, sha(MMAH))}),
            patch.dict(getdecomposition.MEASURED,
                       {"makemeahanzi": (len(MMAH), 20, 9000, 400)})]
        for p in self.patches:
            p.start()
        self.fake = Recorder({"dictionary.txt": MMAH, "COPYING": b"copying",
                              "LGPL": b"lgpl"})

    def tearDown(self):
        for p in self.patches:
            p.stop()
        super().tearDown()

    def test_plan(self):
        for source in self.g.SOURCES:
            p = self.g.plan(source)
            self.assertPlan(p)
            self.assertTrue(p["measured"], source)
        self.assertEqual(self.g.plan("makemeahanzi", "local.txt")["download"], 0)
        self.assertEqual(self.g.plan("kanjivg")["download"], 23_497_394,
                         "the pinned archive's own size")

    def test_build_checks_reports_and_stops(self):
        w = Watch(stop_in="build")
        with patch.object(download, "fetch", self.fake), \
                self.assertRaises(download.Cancelled):
            self.g.build("makemeahanzi", say=lambda m: None,
                         progress=w.progress, cancel=w.cancel)
        main = self.fake.calls[0][2]
        self.assertEqual(main["sha256"], sha(MMAH), "the pinned digest is asked for")
        self.assertEqual(main["progress"], w.progress)
        components = self.dir / "components"
        self.assertEqual(sorted(p.name for p in components.iterdir()),
                         [".download-makemeahanzi-dictionary.txt"],
                         "the download kept, no pack, no build folder")
        w = Watch()
        with patch.object(download, "fetch", self.fake):
            self.assertEqual(self.g.build("makemeahanzi", say=lambda m: None,
                                          progress=w.progress, cancel=w.cancel), 400)
        self.assertEqual([c[0].rsplit("/", 1)[-1] for c in self.fake.calls[1:]],
                         ["COPYING", "LGPL", "COPYING", "LGPL"],
                         "the data itself not fetched again")
        self.assertEqual(w.calls[-1], (400, 400, "build"))
        self.assertEqual(sorted(p.name for p in components.iterdir()),
                         ["makemeahanzi.db"])

    def test_discard(self):
        folder = self.dir / "components"
        folder.mkdir()
        left = folder / ".download-makemeahanzi-dictionary.txt.part"
        left.write_bytes(b"x" * 9)
        Path(str(left) + ".json").write_text("{}")
        self.assertEqual(self.g.plan("makemeahanzi")["have"], 9)
        self.assertEqual(self.g.discard("makemeahanzi"), 9)
        self.assertEqual(list(folder.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
