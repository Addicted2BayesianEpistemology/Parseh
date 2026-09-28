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

And each of the five downloaders -- and speech to text's manager, lib/getstt.py, a
sixth, whose program is installed by pip (a fake one here) and whose models come
through download.fetch -- is held to the interface the Settings page
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


# ---------------------------------------------------------- speech to text
# A FAKE PIP: a child that says what pip says, in pip's order, and makes what pip
# makes -- so the manager's real command, its real reading of the lines and its real
# Stop are driven, and nothing is downloaded.  argv: the folder pip was told to install
# into (--target), a mode, the distributions to leave in it, a file to note its pid in.
FAKE_PIP = r"""
import json, os, sys, time
stage, mode, required, note = sys.argv[1:5]
with open(note, "a") as f:
    f.write("%d started\n" % os.getpid())
older = os.environ.get("FAKE_PIP_OLDER")
if older:
    with open(note, "a") as f:
        f.write("older %s\n" % os.path.isdir(older))
for n in ("faster-whisper==1.2.1", "ctranslate2==4.8.2"):
    print("Collecting %s (from -r stt-requirements.txt (line 1))" % n, flush=True)
    print("  Downloading %s-1-py3-none-any.whl (0.5 kB)" % n.split("==")[0], flush=True)
    for done in (0, 250, 500):
        print("Progress %d of 500" % done, flush=True)
        if mode == "sleep":
            time.sleep(30)
    time.sleep(0.05)
print("Installing collected packages: faster-whisper, ctranslate2", flush=True)
if mode == "fail":
    print("ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE. If you have updated", flush=True)
    sys.exit(1)
if mode == "slow":
    time.sleep(0.6)
dists = json.loads(required)
if mode == "incomplete":
    dists = dists[:1]
for d, v in dists:
    os.makedirs(os.path.join(stage, "%s-%s.dist-info" % (d, v or "1.0")))
print("Successfully installed faster-whisper-1.2.1 ctranslate2-4.8.2", flush=True)
"""


class GetsttTests(DownloaderCase):
    """lib/getstt.py's fetching: the program by pip (a fake one), a model by download.fetch (a
    fake one), each through the interface the Settings page and its runner build on."""

    def setUp(self):
        super().setUp()
        import getstt
        self.g = getstt
        self.stt = self.dir / "stt"
        self.note = self.dir / "pip.log"
        self.mode = "ok"
        self.probe = {"ct2": "4.8.2", "cuda_devices": 0, "cuda_types": [], "cublas": {"loads": False},
                      "smi": None}
        self.pins, self.made = {}, {}
        for key in getstt.MODELS:
            self.made[key] = {n: (key + "/" + n).encode() * 3 for n in getstt.MODEL_PINS[key]["files"]}
            self.pins[key] = {"repo": "example/" + key, "revision": "d" * 40,
                              "files": {n: (sha(b), len(b)) for n, b in self.made[key].items()}}
        self.patches = [
            patch.object(getstt, "STT_DIR", str(self.stt)),
            patch.object(getstt, "MODEL_PINS", self.pins),
            patch.dict(getstt.MEASURED, {k: sum(len(b) for b in self.made[k].values()) for k in getstt.MODELS}),
            patch.object(getstt, "_runtime_plan", lambda: (1000, 3000)),
            patch.object(getstt, "pip_command", self.pip_command),
            patch.object(getstt, "_run_probe", lambda timeout=30: dict(self.probe)),
            patch.object(getstt, "unavailable_reason", lambda: ""),
        ]
        for p in self.patches:
            p.start()
        getstt._SIZES.clear()
        getstt.forget_hardware()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.g.forget_hardware()
        super().tearDown()

    def pip_command(self, stage, requirements=None):
        return [sys.executable, "-c", FAKE_PIP, stage, self.mode, json.dumps(list(self.g.REQUIRED)),
                str(self.note)]

    def runtime_folder(self):
        return self.stt / "runtime" / ("%d-%s" % (self.g.PIN["generation"], self.g.PYTAG))

    def installed_program(self, generation=None):
        g = self.g.PIN["generation"] if generation is None else generation
        folder = self.stt / "runtime" / ("%d-%s" % (g, self.g.PYTAG))
        for d, v in self.g.REQUIRED:
            (folder / ("%s-%s.dist-info" % (d, v or "1.0"))).mkdir(parents=True)
        return folder

    def fetcher(self, key, stop_after=None):
        """download.fetch, faked: writes what the pin's digest is of, and remembers each call."""
        body = {n: b for n, b in self.made[key].items()}
        rec = Recorder({})
        real = rec.__call__

        def fetch(url, dest, **kw):
            rec.calls.append((url, dest, kw))
            download.check(kw.get("cancel"))
            name = os.path.basename(dest)
            data = body[name]
            if kw.get("progress"):
                kw["progress"](len(data) // 2, len(data), "download")
                kw["progress"](len(data), len(data), "download")
            with open(dest, "wb") as f:
                f.write(data)
            return dest
        rec.fetch = fetch
        return rec

    # ---- the plan
    def test_plan_counts_the_program_until_it_is_there(self):
        g = self.g
        p = g.plan("runtime")
        self.assertPlan(p)
        self.assertEqual((p["download"], p["kept"], p["measured"], p["have"]), (1000, 3000, True, 0))
        model = g.MEASURED["large-v3"]
        p = g.plan("large-v3")
        self.assertEqual((p["download"], p["kept"]), (1000 + model, 3000 + model))
        self.assertEqual(p["disk_peak"], max(1000 + 3000, 3000 + model), "the larger of the two moments")
        self.installed_program()
        p = g.plan("large-v3")
        self.assertEqual((p["download"], p["kept"], p["disk_peak"]), (model, model, model))
        self.assertEqual(g.plan("large-v3", probe=False), p, "asks nobody, either way")

    # ---- the program: pip, a bar, Stop, a staged folder
    def test_the_program_is_one_bar_a_build_and_a_folder_made_whole(self):
        older = self.installed_program(generation=self.g.PIN["generation"] - 1)
        w = Watch()
        said = []
        with patch.dict(os.environ, {"FAKE_PIP_OLDER": str(older)}):
            self.g.build("runtime", say=said.append, progress=w.progress, cancel=w.cancel)
        self.assertEqual(w.phases(), ["download", "build", "download"])
        dl = [c for c in w.calls if c[2] == "download"]
        self.assertEqual({t for _d, t, _p in w.calls}, {1000}, "one bar, counted in bytes")
        self.assertEqual([d for d, _t, _p in w.calls], sorted(d for d, _t, _p in w.calls), "it never goes back")
        self.assertEqual(w.calls[0][0], 0)
        self.assertEqual(dl[-1][0], 1000, "and ends full")
        self.assertTrue(any(c[2] == "build" and c[0] == 1000 for c in w.calls),
                        "the unpacking is a phase of its own, at the end of the download")
        self.assertTrue(self.runtime_folder().is_dir())
        self.assertEqual(self.g.runtime()["state"], "ready")
        # the older folder was there while pip ran, and gone only afterwards
        self.assertIn("older True", self.note.read_text())
        self.assertFalse(older.exists())
        self.assertEqual(sorted(p.name for p in (self.stt / "runtime").iterdir()),
                         [self.runtime_folder().name])
        self.assertEqual([p.name for p in self.stt.iterdir() if p.name.startswith("runtime.part")], [],
                         "no staging folder left")
        self.assertEqual(list((self.stt / "tmp").iterdir()), [], "and no scratch of pip's")
        self.assertTrue(any("faster-whisper" in s for s in said))
        self.assertEqual(self.g.in_use(), False)
        self.assertEqual(self.g._CHILDREN, set())

    def test_it_is_installed_by_the_real_command_line(self):
        # the shape of what is run, held: hashes required, nothing resolved, wheels only, into the stage
        cmd = self.g.pip_command.__wrapped__("STAGE") if hasattr(self.g.pip_command, "__wrapped__") else None
        for p in self.patches:
            if getattr(p, "attribute", "") == "pip_command":
                p.stop()
        try:
            cmd = self.g.pip_command("STAGE")
        finally:
            for p in self.patches:
                if getattr(p, "attribute", "") == "pip_command":
                    p.start()
        for flag in ("--require-hashes", "--no-deps", "--only-binary=:all:", "--isolated", "--no-cache-dir",
                     "--progress-bar", "raw", "--no-input"):
            self.assertIn(flag, cmd)
        self.assertEqual(cmd[cmd.index("--target") + 1], "STAGE")
        self.assertEqual(cmd[cmd.index("-r") + 1], str(ROOT / "lib" / "stt-requirements.txt"))
        self.assertEqual(cmd[1:4], ["-u", "-m", "pip"])
        self.assertNotIn("--user", cmd)
        self.assertNotIn("nvidia", " ".join(cmd).lower())
        env = self.g._pip_env(str(self.dir / "scratch"))
        self.assertEqual(env["PIP_USER_AGENT_USER_DATA"], self.g.UA)
        self.assertEqual({env[k] for k in ("TMPDIR", "TEMP", "TMP")}, {str(self.dir / "scratch")})
        self.assertEqual(env["PYTHONNOUSERSITE"], "1")
        self.assertNotIn("PYTHONPATH", env)

    def test_stop_ends_pip_at_once_and_leaves_nothing(self):
        self.mode = "sleep"
        state = {"pid": None}

        def cancel():
            if state["pid"] is None and self.note.exists():
                state["pid"] = int(self.note.read_text().split()[0])
            return state["pid"] is not None
        started = time.time()
        with self.assertRaises(download.Cancelled):
            self.g.build("runtime", say=lambda m: None, progress=None, cancel=cancel)
        self.assertLess(time.time() - started, 15, "pip was told to sleep for a minute: Stop did not wait")
        end = time.time() + 5
        while time.time() < end:
            try:
                os.kill(state["pid"], 0)
            except OSError:
                break
            time.sleep(0.05)
        with self.assertRaises(OSError, msg="the pip is gone: no orphan"):
            os.kill(state["pid"], 0)
        self.assertFalse(self.runtime_folder().exists())
        self.assertEqual([p.name for p in self.stt.iterdir() if p.name.startswith("runtime.part")], [])
        self.assertEqual(self.g.runtime()["state"], "absent")
        self.assertEqual(self.g._CHILDREN, set())
        self.assertFalse(self.g.in_use())

    def test_a_failing_pip_says_why_in_a_sentence_and_installs_nothing(self):
        self.mode = "fail"
        with self.assertRaises(SystemExit) as caught:
            self.g.build("runtime", say=lambda m: None)
        said = str(caught.exception)
        self.assertTrue(said.startswith("getstt: "))
        self.assertIn("not the one Parseh expects", said)
        self.assertNotIn("ERROR", said)
        self.assertFalse(self.runtime_folder().exists())
        self.assertEqual([p.name for p in self.stt.iterdir() if p.name.startswith("runtime.part")], [])

    def test_pips_words_are_turned_into_the_ones_a_person_can_act_on(self):
        words = self.g._pip_words
        self.assertIn("not the one Parseh expects",
                      words(["ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE."]))
        self.assertIn("could not reach the package server",
                      words(["WARNING: Retrying (Retry(total=4)) after connection broken by 'NewConnectionError'",
                             "ERROR: Could not fetch URL https://pypi.org/simple/av/: Max retries exceeded"]))
        with patch.object(self.g, "platform_key", return_value="macOS arm64"):
            said = words(["ERROR: Could not find a version that satisfies the requirement av==18.1.0",
                          "ERROR: No matching distribution found for av==18.1.0"])
        self.assertIn("macOS 14", said)
        self.assertIn("av==18.1.0", said)
        with patch.object(self.g, "platform_key", return_value="linux x86_64"):
            said = words(["ERROR: No matching distribution found for onnxruntime==1.30.0"])
        self.assertIn("no build of", said)
        self.assertIn("this kind of computer", said)
        self.assertIn("no pip", words(["/usr/bin/python3: No module named pip"]))
        self.assertIn("disk filled up", words(["OSError: [Errno 28] No space left on device"]))
        self.assertIn("may not write", words(["PermissionError: [Errno 13] Permission denied"]))
        self.assertIn("pip stopped: ", words(["ERROR: something unforeseen"]))
        self.assertIn("without saying why", words([]))

    def test_a_program_that_is_not_whole_is_not_kept(self):
        self.mode = "incomplete"
        with self.assertRaises(SystemExit) as caught:
            self.g.build("runtime", say=lambda m: None)
        self.assertIn("is not there", str(caught.exception))
        self.assertFalse(self.runtime_folder().exists())
        self.assertEqual([p.name for p in self.stt.iterdir() if p.name.startswith("runtime.part")], [])

    def test_only_one_program_is_installed_at_a_time_and_the_second_finds_it_there(self):
        self.mode = "slow"
        errors = []

        def run():
            try:
                self.g.build("runtime", say=lambda m: None)
            except BaseException as e:                    # noqa: BLE001
                errors.append(e)
        threads = [threading.Thread(target=run) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(60)
        self.assertEqual(errors, [])
        self.assertEqual(self.note.read_text().count("started"), 1, "one pip, not two")
        self.assertEqual(self.g.runtime()["state"], "ready")

    def test_stop_is_heard_while_a_job_waits_behind_another_ones_install(self):
        held, release_it = threading.Event(), threading.Event()

        def hold():
            with self.g._INSTALL:
                held.set()
                release_it.wait(30)
        t = threading.Thread(target=hold)
        t.start()
        held.wait(5)
        said = []
        stop = threading.Event()
        threading.Timer(0.4, stop.set).start()
        started = time.time()
        try:
            with self.assertRaises(download.Cancelled):
                self.g.build("runtime", say=said.append, cancel=stop)
        finally:
            release_it.set()
            t.join(10)
        self.assertLess(time.time() - started, 10)
        self.assertTrue(any("waiting for the speech program" in m for m in said))
        self.assertFalse(self.note.exists(), "it never started a pip of its own")

    def test_a_program_that_is_already_there_is_not_installed_again(self):
        self.installed_program()
        said = []
        self.g.build("runtime", say=said.append)
        self.assertFalse(self.note.exists(), "no pip was started")
        self.assertTrue(any("already installed" in s for s in said))

    def test_where_the_program_cannot_be_installed_nothing_is_started(self):
        with patch.object(self.g, "unavailable_reason", lambda: "There is no speech program for this kind of computer."), \
                patch.object(subprocess_module(), "Popen", side_effect=AssertionError("a child was started")):
            with self.assertRaises(SystemExit) as caught:
                self.g.build("runtime", say=lambda m: None)
            with self.assertRaises(SystemExit):
                self.g.build("large-v3", say=lambda m: None)
        self.assertIn("no speech program for this kind of computer", str(caught.exception))
        self.assertFalse(self.stt.exists())

    # ---- a model: one bar, every file checked, resumed, kept whole
    def test_a_model_is_one_bar_checked_file_by_file_and_put_in_place_by_one_rename(self):
        self.installed_program()
        fake = self.fetcher("large-v3")
        w = Watch()
        held = []

        def fetch(url, dest, **kw):
            held.append(self.g.in_use("large-v3"))
            return fake.fetch(url, dest, **kw)
        with patch.object(download, "fetch", fetch):
            size = self.g.build("large-v3", say=lambda m: None, progress=w.progress, cancel=w.cancel)
        whole = sum(len(b) for b in self.made["large-v3"].values())
        self.assertEqual(size, whole)
        self.assertEqual(len(fake.calls), 5)
        pin = self.pins["large-v3"]
        for url, dest, kw in fake.calls:
            name = os.path.basename(dest)
            self.assertEqual(kw["sha256"], pin["files"][name][0], "every file against its own digest")
            self.assertEqual(kw["size"], pin["files"][name][1])
            self.assertEqual(kw["headers"], {"User-Agent": self.g.UA})
            self.assertEqual(url, "https://huggingface.co/example/large-v3/resolve/%s/%s" % ("d" * 40, name),
                             "the commit, never main")
            self.assertEqual(kw["cancel"], w.cancel)
        self.assertEqual({t for _d, t, _p in w.calls}, {whole}, "one bar, five files")
        self.assertEqual(w.calls[-1][0], whole)
        self.assertEqual(held, [True] * 5, "the part is held while it is fetched: nothing may remove it")
        folder = self.stt / "models" / "large-v3"
        self.assertEqual(sorted(p.name for p in folder.iterdir()),
                         sorted(list(pin["files"]) + ["meta.json"]))
        meta = json.loads((folder / "meta.json").read_text())
        self.assertEqual((meta["revision"], meta["licence"], meta["model"]), ("d" * 40, "MIT", "large-v3"))
        self.assertFalse((self.stt / "models" / "large-v3.part").exists())
        self.assertTrue(self.g.model_ready("large-v3"))
        self.assertFalse(self.g.in_use())

    def test_a_stopped_model_keeps_what_came_and_the_next_press_carries_on(self):
        self.installed_program()
        fake = self.fetcher("large-v3")
        stop = {"after": 2}

        def cancel():
            return len(fake.calls) > stop["after"]
        with patch.object(download, "fetch", fake.fetch), self.assertRaises(download.Cancelled):
            self.g.build("large-v3", say=lambda m: None, cancel=cancel)
        part = self.stt / "models" / "large-v3.part"
        self.assertEqual(len([p for p in part.iterdir() if not p.name.endswith(".part.json")]), 2, "two files kept")
        self.assertFalse(self.g.model_ready("large-v3"))
        self.assertEqual(self.g.plan("large-v3")["have"], sum(p.stat().st_size for p in part.iterdir()))
        fake.calls.clear()
        with patch.object(download, "fetch", fake.fetch):
            self.g.build("large-v3", say=lambda m: None)
        self.assertEqual(len(fake.calls), 3, "the two whole files are not fetched again")
        self.assertTrue(self.g.model_ready("large-v3"))
        self.assertFalse(part.exists())

    def test_a_file_that_arrives_short_is_not_kept_as_a_model(self):
        self.installed_program()
        fake = self.fetcher("large-v3")
        real = fake.fetch

        def short(url, dest, **kw):
            real(url, dest, **kw)
            if dest.endswith("tokenizer.json"):
                with open(dest, "r+b") as f:
                    f.truncate(3)
            return dest
        with patch.object(download, "fetch", short), self.assertRaises(SystemExit) as caught:
            self.g.build("large-v3", say=lambda m: None)
        self.assertIn("tokenizer.json did not arrive whole", str(caught.exception))
        self.assertFalse((self.stt / "models" / "large-v3").exists(),
                         "without tokenizer.json faster-whisper would reach for the network: not installed")

    def test_a_refused_and_a_dropped_download_are_said_in_words(self):
        self.installed_program()

        def mismatch(url, dest, **kw):
            raise download.Mismatch("model.bin is not the file Parseh expects: its SHA-256 is x, not y.  "
                                    "Nothing was installed.")
        with patch.object(download, "fetch", mismatch), self.assertRaises(SystemExit) as caught:
            self.g.build("large-v3", say=lambda m: None)
        self.assertIn("is not the file Parseh expects", str(caught.exception))
        self.assertIn("getstt: ", str(caught.exception))

        def dropped(url, dest, **kw):
            raise download.Incomplete("the connection closed at 1 MB of 3 MB")
        with patch.object(download, "fetch", dropped), self.assertRaises(SystemExit) as caught:
            self.g.build("large-v3", say=lambda m: None)
        self.assertIn("What came is kept", str(caught.exception))
        self.assertFalse((self.stt / "models" / "large-v3").exists())

    def test_a_models_get_installs_the_program_first_under_one_bar(self):
        fake = self.fetcher("large-v3-turbo")
        seen = []

        def fetch(url, dest, **kw):
            seen.append(self.runtime_folder().is_dir())
            return fake.fetch(url, dest, **kw)
        w = Watch()
        with patch.object(download, "fetch", fetch):
            self.g.build("large-v3-turbo", say=lambda m: None, progress=w.progress, cancel=w.cancel)
        model = self.g.MEASURED["large-v3-turbo"]
        self.assertEqual({t for _d, t, _p in w.calls}, {1000 + model}, "the program's bytes and the model's, one bar")
        self.assertEqual([d for d, _t, _p in w.calls], sorted(d for d, _t, _p in w.calls), "monotonic")
        self.assertEqual(w.calls[-1][0], 1000 + model)
        self.assertEqual(w.phases(), ["download", "build", "download"])
        self.assertEqual(seen, [True] * 5, "the program is whole before the first model file is asked for")
        self.assertEqual(self.g.installed(), ["large-v3-turbo"])
        self.assertEqual(self.note.read_text().count("started"), 1)

    def test_a_models_get_does_not_reinstall_a_program_that_is_there(self):
        self.installed_program()
        fake = self.fetcher("large-v3-turbo")
        with patch.object(download, "fetch", fake.fetch):
            self.g.build("large-v3-turbo", say=lambda m: None)
        self.assertFalse(self.note.exists(), "no pip")

    def test_stopping_a_models_get_while_it_installs_the_program_leaves_no_model_part(self):
        self.mode = "sleep"
        fake = self.fetcher("large-v3-turbo")

        def cancel():
            return self.note.exists()
        with patch.object(download, "fetch", fake.fetch), self.assertRaises(download.Cancelled):
            self.g.build("large-v3-turbo", say=lambda m: None, cancel=cancel)
        self.assertEqual(fake.calls, [], "no model file was asked for")
        self.assertFalse(self.runtime_folder().exists())

    def test_discard(self):
        self.installed_program()
        part = self.stt / "models" / "large-v3.part"
        part.mkdir(parents=True)
        (part / "model.bin.part").write_bytes(b"x" * 10)
        (part / "model.bin.part.json").write_text("{}")
        self.assertEqual(self.g.plan("large-v3")["have"], 10)
        self.assertEqual(self.g.discard("large-v3"), 10)
        self.assertFalse(part.exists())
        self.assertTrue(self.runtime_folder().is_dir(), "the program is not a download in progress")
        stage = self.stt / ("runtime.part-%d" % os.getpid())
        stage.mkdir()
        (stage / "x").write_bytes(b"y" * 4)
        self.assertEqual(self.g.discard("runtime"), 4)
        self.assertFalse(stage.exists())


def subprocess_module():
    import subprocess
    return subprocess


if __name__ == "__main__":
    unittest.main()
