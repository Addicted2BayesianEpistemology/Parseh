# SPDX-License-Identifier: GPL-3.0-or-later
"""`python3 lib/release.py links`: the live check of every address Parseh names.

    python3 -m unittest tests/test_release_links.py

The command asks the internet, by hand, and is never run by the unit suite or
by a workflow.  What is held here is everything about it that does not need
the internet:

  * the JUDGING is pure.  `release.fetch` is injected, so every rule of the
    brief's list (the feed's tag, the guide ending at the domain, the icons
    with no redirect at all, the deep link's bar, a stale link in a document,
    the addresses that are only reported) is driven passing and failing
    against a table of answers, offline;
  * the HOP-FOLLOWING is driven both ways: offline, through `fetch`'s own
    loop with the one-request step replaced (the hop limit, a loop, a
    relative Location), and against REAL SOCKETS -- a local http.server on
    127.0.0.1 serving 301, 302, 404, a hanging answer and a PNG -- which also
    proves the output's format and the exit code end to end.

The address strings come from lib/project.py and from release.py's own
constants, never written out here: a test that forbids the old place in the
tree (tests/test_project.py) must not find it in this file.
"""
import ast
import contextlib
import http.server
import io
import json
import os
import re
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import project  # noqa: E402
import release  # noqa: E402

TAG = "a0.4.4"
REAL_FETCH = release.fetch          # kept: a test that patches release.fetch must not make Web recurse
# the four icons the phone app is installed with, and the size each one is
SIZES = {"parseh-192.png": 192, "parseh-512.png": 512, "parseh-maskable-512.png": 512,
         "apple-touch-icon.png": 180}
DEEP = project.SITE + "site/reference/whats-new.html"
# the guide as a person may type it: with http, and with www
HTTP_GUIDE = "http://" + project.GUIDE_URL[len("https://"):]
WWW_SITE = "https://www." + project.SITE[len("https://"):]
# where GitHub's own Pages address of the organisation's site is, and the
# path the Parseh repository's own Pages would have under the domain
PAGES_DEFAULT = "https://%s/%s/" % (project.SITE_REPO.split("/")[1], project.GUIDE_REPO.split("/")[1])
PAGES_PARSEH = project.WEBSITE_URL + project.NAME + "/"
# the old account's name, in halves: the old place must not be in this tree
OLD_ACCOUNT = "Addicted2" + "Bayesian" + "Epistemology"


def png(width, height):
    """The first bytes of a PNG: its signature and its IHDR (what a check of size reads)."""
    return (b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height)
            + b"\x08\x06\x00\x00\x00" + b"\0\0\0\0")


def page(version=TAG, bar=True, filler=0):
    """A compiled guide page: a long head, a body that starts with the bar, and What's new."""
    head = "<!doctype html><html><head><title>What changed</title><style>%s</style></head>" % ("x{}" * 200)
    barred = ('<header class="bar"><a class="logo" href="%s"><img alt="Parseh" src="../../lib/icons/parseh-192.png"></a>'
              '<a href="../../index.html">Guide</a></header>' % project.WEBSITE_URL) if bar else ""
    return ("%s<body class=\"guide\">%s%s<main><h2>%s &mdash; 5 October 2026</h2></main></body></html>"
            % (head, "<p>%s</p>" % ("." * filler) if filler else "", barred, version)).encode()


class Web:
    """A table of single answers, url -> (status, where, body): where is the Location of a
    redirect and the Content-Type of anything else.  `once` is release.fetch's one-request
    step, so the hop-following under test is the real one."""

    def __init__(self, table):
        self.table = dict(table)
        self.asked = []      # every request, hop by hop
        self.fetched = []    # every address asked for, once each however many hops it took
        self.agents = []

    def once(self, url, keep=0, agent=None, timeout=15):
        self.asked.append(url)
        entry = self.table.get(url)
        if isinstance(entry, Exception):
            raise entry
        if entry is None:
            return release.Hop(url, None, None, "", "not in the fake web"), b""
        status, where, body = (tuple(entry) + (b"",))[:3]
        if 300 <= status < 400:
            return release.Hop(url, status, where, "", None), b""
        # the media type is read as the real request reads it
        return release.Hop(url, status, None, release._ctype({"Content-Type": where or ""}), None), body[:keep]

    def fetch(self, url, keep=0, agent=None):
        self.agents.append(agent)
        self.fetched.append(url)
        return REAL_FETCH(url, keep, agent, once=self.once)


def healthy(tag=TAG):
    """Every address of the brief, answering as it should once the move is done."""
    table = {
        project.FEED: (200, "application/json", json.dumps({"tag_name": tag, "assets": []}).encode()),
        project.LATEST_URL: (302, project.RELEASES_URL + "/tag/" + tag),
        project.RELEASES_URL + "/tag/" + tag: (200, "text/html"),
        project.WEBSITE_URL: (200, "text/html", b"<html>Parseh</html>"),
        project.GUIDE_URL: (301, project.SITE),
        project.SITE: (200, "text/html", b"<html>the guide</html>"),
        HTTP_GUIDE: (301, project.GUIDE_URL),
        WWW_SITE: (301, project.SITE),
        DEEP: (200, "text/html; charset=utf-8", page(tag)),
        # what is only reported
        PAGES_DEFAULT: (301, project.SITE),
        PAGES_PARSEH: (404, "text/html", b"not found"),
        # where the old repository's redirect ends
        project.GITHUB_URL: (200, "text/html"),
    }
    for name, size in SIZES.items():
        table[project.ICONS_URL + name] = (200, "image/png", png(size, size))
    return table


def failed(results):
    return [r.label for r in results if r.failed]


def labelled(results, label):
    found = [r for r in results if r.label == label]
    assert len(found) == 1, "%r: %d results in %r" % (label, len(found), [r.label for r in results])
    return found[0]


def plant(root, files):
    for rel, text in files.items():
        p = Path(root) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


class Tree(unittest.TestCase):
    """A scratch checkout with a VERSION and nothing else, for the tests that need a root."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="parseh-links-test-")
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name
        plant(self.root, {"VERSION": "a9.9.9\n"})


class Fetching(unittest.TestCase):
    """fetch(): the chain, followed by hand, hop by hop."""

    def follow(self, table, url, keep=0):
        web = Web(table)
        return release.fetch(url, keep, "Parseh/test", once=web.once), web

    def test_a_plain_answer_is_one_hop(self):
        ans, _ = self.follow({"http://x/a": (200, "text/html", b"hello")}, "http://x/a")
        self.assertEqual(len(ans.hops), 1)
        self.assertEqual((ans.hops[0].status, ans.hops[0].ctype, ans.hops[0].error), (200, "text/html", None))

    def test_every_hop_of_a_chain_is_kept_with_its_status_and_its_location(self):
        ans, _ = self.follow({"http://x/a": (301, "http://x/b"), "http://x/b": (302, "http://x/c"),
                              "http://x/c": (200, "text/plain", b"end")}, "http://x/a", keep=10)
        self.assertEqual([(h.url, h.status, h.location) for h in ans.hops],
                         [("http://x/a", 301, "http://x/b"), ("http://x/b", 302, "http://x/c"),
                          ("http://x/c", 200, None)])
        self.assertEqual(ans.body, b"end")

    def test_a_relative_location_is_joined_to_the_address_it_came_from(self):
        ans, _ = self.follow({"http://x/dir/a": (301, "b"), "http://x/dir/b": (301, "/top"),
                              "http://x/top": (200, "text/html")}, "http://x/dir/a")
        self.assertEqual([h.url for h in ans.hops], ["http://x/dir/a", "http://x/dir/b", "http://x/top"])

    def test_six_redirects_are_followed_and_a_seventh_is_a_fault(self):
        for n, ends in ((6, 200), (7, None)):
            table = {"http://x/%d" % i: (302, "http://x/%d" % (i + 1)) for i in range(n)}
            table["http://x/%d" % n] = (200, "text/html")
            ans, _ = self.follow(table, "http://x/0")
            with self.subTest(redirects=n):
                if ends:
                    self.assertEqual((len(ans.hops), ans.hops[-1].status, ans.hops[-1].error), (7, 200, None))
                else:
                    self.assertEqual(len(ans.hops), 7)
                    self.assertIn("more than 6 redirects", ans.hops[-1].error)

    def test_a_loop_stops_at_once_and_says_so(self):
        ans, web = self.follow({"http://x/a": (302, "http://x/b"), "http://x/b": (302, "http://x/a")}, "http://x/a")
        self.assertIn("loop", ans.hops[-1].error)
        self.assertLessEqual(len(web.asked), 3)

    def test_a_redirect_without_a_location_ends_the_chain_with_a_reason(self):
        ans, _ = self.follow({"http://x/a": (301, None)}, "http://x/a")
        self.assertEqual(len(ans.hops), 1)
        self.assertIn("Location", ans.hops[0].error)

    def test_no_answer_is_a_hop_with_a_reason_and_ends_the_chain(self):
        ans, _ = self.follow({"http://x/a": (301, "http://x/gone")}, "http://x/a")
        self.assertEqual([h.status for h in ans.hops], [301, None])
        self.assertTrue(ans.hops[-1].error)

    def test_the_body_is_kept_only_when_asked_for_and_only_as_far_as_asked(self):
        table = {"http://x/a": (200, "text/html", b"0123456789")}
        self.assertEqual(self.follow(table, "http://x/a")[0].body, b"")
        self.assertEqual(self.follow(table, "http://x/a", keep=4)[0].body, b"0123")

    def test_the_agent_reaches_every_request(self):
        seen = []

        def once(url, keep=0, agent=None, timeout=15):
            seen.append(agent)
            return (release.Hop(url, 301, "http://x/b", "", None) if url.endswith("a")
                    else release.Hop(url, 200, None, "text/html", None)), b""
        release.fetch("http://x/a", 0, "Parseh/test (+https://example.org)", once=once)
        self.assertEqual(seen, ["Parseh/test (+https://example.org)"] * 2)


class Judging(Tree):
    """The brief's list, each rule passing and failing, against a table of answers."""

    def drive(self, table=None, expect=None, old=False, **kw):
        self.web = Web(healthy() if table is None else table)
        return release.live_checks(self.root, expect, old, self.web.fetch, project, "Parseh/test", 0, **kw)

    def broken(self, url, entry):
        table = healthy()
        if entry is None:
            table.pop(url, None)
        else:
            table[url] = entry
        return table

    # ---------------------------------------------------------------- all well
    def test_every_address_well_is_green_with_and_without_a_tag(self):
        for expect in (None, TAG):
            with self.subTest(expect=expect):
                results = self.drive(expect=expect)
                self.assertEqual(failed(results), [])
                self.assertEqual({"feed", "latest", "site", "guide", "guide/", "deep link"} - {r.label for r in results}, set())

    def test_the_old_addresses_are_not_asked_without_the_flag(self):
        results = self.drive()
        self.assertEqual([r.label for r in results if r.label.startswith("old ")], [])
        self.assertFalse(any(OLD_ACCOUNT.lower() in u.lower() for u in self.web.asked))

    # ---------------------------------------------------------------- the update road
    def test_the_feed_must_be_the_release_expected(self):
        table = self.broken(project.FEED, (200, "application/json", json.dumps({"tag_name": "a0.4.3"}).encode()))
        results = self.drive(table, expect=TAG)
        self.assertEqual(failed(results), ["feed"])
        self.assertTrue(any("a0.4.3" in p and TAG in p for p in labelled(results, "feed").problems))
        # asked of nothing in particular, the feed's tag is only said
        results = self.drive(table)
        self.assertEqual(failed(results), [])
        self.assertTrue(any("a0.4.3" in n for n in labelled(results, "feed").notes))

    def test_a_tag_given_as_a_ref_is_the_tag(self):
        self.assertEqual(failed(self.drive(expect="refs/tags/" + TAG)), [])

    def test_the_feed_fails_when_it_is_not_there_is_not_json_or_is_not_a_release(self):
        for entry in ((404, "application/json", b"{}"), (200, "text/html", b"<html>"),
                      (200, "application/json", b"[1, 2]"), (200, "application/json", b'{"name": "x"}'),
                      None):
            with self.subTest(entry=entry):
                self.assertEqual(failed(self.drive(self.broken(project.FEED, entry))), ["feed"])

    def test_the_feed_may_not_lean_on_a_redirect(self):
        # a renamed repository: GitHub redirects the API, and the road would die the day the old name is taken
        table = self.broken(project.FEED, (301, "https://api.github.com/repositories/1/releases/latest"))
        table["https://api.github.com/repositories/1/releases/latest"] = (
            200, "application/json", json.dumps({"tag_name": TAG}).encode())
        results = self.drive(table, expect=TAG)
        self.assertEqual(failed(results), ["feed"])
        self.assertTrue(any("redirect" in p for p in labelled(results, "feed").problems))

    def test_the_latest_release_page_ends_in_200_and_with_a_tag_names_it(self):
        self.assertEqual(failed(self.drive(self.broken(project.LATEST_URL, (404, "text/html")))), ["latest"])
        stale = self.broken(project.LATEST_URL, (302, project.RELEASES_URL + "/tag/a0.4.3"))
        stale[project.RELEASES_URL + "/tag/a0.4.3"] = (200, "text/html")
        self.assertEqual(failed(self.drive(stale, expect=TAG)), ["latest"])
        self.assertEqual(failed(self.drive(stale)), [])

    # ---------------------------------------------------------------- the site and the guide
    def test_the_site_answers_200_where_it_is_written(self):
        self.assertEqual(failed(self.drive(self.broken(project.WEBSITE_URL, (404, "text/html")))), ["site"])
        self.assertEqual(failed(self.drive(self.broken(project.WEBSITE_URL, None))), ["site"])
        moved = self.broken(project.WEBSITE_URL, (301, project.SITE))
        self.assertEqual(failed(self.drive(moved)), ["site"])

    def test_the_guide_ends_at_the_guide_with_200_after_githubs_own_slash(self):
        results = self.drive()
        guide = labelled(results, "guide")
        self.assertEqual([h.status for h in guide.answer.hops], [301, 200])
        self.assertEqual(guide.answer.hops[-1].url, project.SITE)
        self.assertEqual(labelled(results, "guide/").answer.hops[-1].status, 200)

    def test_a_guide_that_ends_on_githubs_own_address_fails(self):
        table = self.broken(project.GUIDE_URL, (301, PAGES_DEFAULT))
        table[PAGES_DEFAULT] = (200, "text/html", b"the guide, on the wrong host")
        results = self.drive(table)
        self.assertEqual(failed(results), ["guide", "guide typed with http"])
        problems = " ".join(labelled(results, "guide").problems)
        self.assertIn(urlsplit(PAGES_DEFAULT).netloc, problems)

    def test_a_guide_that_is_not_there_fails_at_every_way_of_asking(self):
        results = self.drive(self.broken(project.SITE, (404, "text/html")))
        self.assertEqual(failed(results), ["guide", "guide/", "guide typed with http", "guide typed with www"])

    def test_a_guide_sent_on_to_any_other_page_fails(self):
        table = self.broken(project.GUIDE_URL, (301, project.SITE + "index.html"))
        table[project.SITE + "index.html"] = (200, "text/html")
        results = self.drive(table)
        self.assertIn("guide", failed(results))
        self.assertTrue(any("index.html" in p for p in labelled(results, "guide").problems))

    def test_a_guide_that_leaves_the_domain_on_the_way_and_comes_back_fails(self):
        table = self.broken(project.GUIDE_URL, (301, "https://elsewhere.example/guide"))
        table["https://elsewhere.example/guide"] = (301, project.SITE)
        self.assertIn("guide", failed(self.drive(table)))

    def test_a_guide_sent_to_another_page_of_the_domain_and_back_fails_at_that_hop(self):
        table = self.broken(project.GUIDE_URL, (301, project.WEBSITE_URL + "elsewhere"))
        table[project.WEBSITE_URL + "elsewhere"] = (301, project.SITE)
        results = self.drive(table)
        self.assertIn("guide", failed(results))
        self.assertTrue(any("elsewhere" in p for p in labelled(results, "guide").problems))

    def test_a_guide_that_steps_down_to_http_on_the_way_fails_even_if_it_ends_well(self):
        down = "http://" + project.SITE[len("https://"):]
        table = self.broken(project.GUIDE_URL, (301, down))
        table[down] = (301, project.SITE)
        self.assertIn("guide", failed(self.drive(table)))

    def test_the_guide_typed_with_http_is_sent_to_https_first_and_may_then_add_its_slash(self):
        results = self.drive()
        hops = labelled(results, "guide typed with http").answer.hops
        self.assertEqual([h.url for h in hops], [HTTP_GUIDE, project.GUIDE_URL, project.SITE])
        # both at once, in one hop, is still those two things and nothing else
        table = self.broken(HTTP_GUIDE, (301, project.SITE))
        self.assertEqual(failed(self.drive(table)), [])

    def test_the_guide_typed_with_http_that_stays_on_http_or_goes_elsewhere_fails(self):
        stays = self.broken(HTTP_GUIDE, (200, "text/html", b"unencrypted"))
        self.assertEqual(failed(self.drive(stays)), ["guide typed with http"])
        away = self.broken(HTTP_GUIDE, (301, PAGES_DEFAULT))
        away[PAGES_DEFAULT] = (200, "text/html")
        self.assertEqual(failed(self.drive(away)), ["guide typed with http"])

    def test_the_guide_typed_with_www_is_sent_to_the_bare_domain_or_fails(self):
        self.assertEqual(failed(self.drive()), [])
        stays = self.broken(WWW_SITE, (200, "text/html", b"on www"))
        self.assertEqual(failed(self.drive(stays)), ["guide typed with www"])
        self.assertEqual(failed(self.drive(self.broken(WWW_SITE, None))), ["guide typed with www"])

    def test_the_variants_are_left_out_where_the_guide_is_not_on_an_https_domain(self):
        # a stand-in project on plain http, as the real-socket test has
        stand = types.SimpleNamespace(**{k: getattr(project, k) for k in dir(project) if k.isupper()})
        stand.agent = project.agent
        stand.SITE = "http://127.0.0.1:9/guide/"
        stand.GUIDE_URL = "http://127.0.0.1:9/guide"
        web = Web({})
        labels = [r.label for r in release.live_checks(self.root, None, False, web.fetch, stand, "a", 0)]
        self.assertNotIn("guide typed with http", labels)
        self.assertNotIn("guide typed with www", labels)

    def test_the_deep_link_answers_at_its_own_address_with_the_bar_and_the_version(self):
        results = self.drive(expect=TAG)
        deep = labelled(results, "deep link")
        self.assertEqual(deep.problems, [])
        self.assertEqual(deep.answer.hops[0].url, DEEP)
        self.assertEqual(len(deep.answer.hops), 1)

    def test_a_deep_link_that_is_missing_or_redirected_fails(self):
        self.assertEqual(failed(self.drive(self.broken(DEEP, (404, "text/html")))), ["deep link"])
        moved = self.broken(DEEP, (301, project.SITE))
        self.assertEqual(failed(self.drive(moved)), ["deep link"])

    def test_a_page_without_the_bar_fails_only_when_a_tag_is_given(self):
        table = self.broken(DEEP, (200, "text/html", page(bar=False)))
        self.assertEqual(failed(self.drive(table)), [])
        results = self.drive(table, expect=TAG)
        self.assertEqual(failed(results), ["deep link"])
        self.assertTrue(any("no bar" in p for p in labelled(results, "deep link").problems))
        self.assertTrue(any("no bar" in n for n in labelled(self.drive(table), "deep link").notes))

    def test_the_bar_is_the_link_to_the_site_and_in_the_first_part_of_the_page(self):
        far = self.broken(DEEP, (200, "text/html", page(filler=20000)))
        self.assertEqual(failed(self.drive(far, expect=TAG)), ["deep link"])
        # a link to the guide's own front page is not the bar
        other = page(bar=False).replace(b"<main>", b'<header><a href="../../index.html">Guide</a></header><main>')
        self.assertEqual(failed(self.drive(self.broken(DEEP, (200, "text/html", other)), expect=TAG)), ["deep link"])

    def test_a_guide_that_does_not_name_the_release_is_an_older_publication(self):
        table = self.broken(DEEP, (200, "text/html", page("a0.4.3")))
        results = self.drive(table, expect=TAG)
        self.assertEqual(failed(results), ["deep link"])
        self.assertTrue(any(TAG in p for p in labelled(results, "deep link").problems))
        self.assertEqual(failed(self.drive(table)), [])
        # a0.4.40 is not a0.4.4
        longer = self.broken(DEEP, (200, "text/html", page("a0.4.40")))
        self.assertEqual(failed(self.drive(longer, expect=TAG)), ["deep link"])

    # ---------------------------------------------------------------- the icons
    def test_each_icon_must_be_a_png_of_its_size_answered_with_no_redirect_at_all(self):
        results = self.drive()
        for name in SIZES:
            with self.subTest(name):
                r = labelled(results, "icon " + name)
                self.assertEqual((r.problems, len(r.answer.hops), r.answer.hops[0].status), ([], 1, 200))
                self.assertEqual(r.answer.hops[0].ctype, "image/png")

    def test_an_icon_behind_a_redirect_fails_even_when_the_end_is_a_fine_png(self):
        for name, size in SIZES.items():
            with self.subTest(name):
                table = self.broken(project.ICONS_URL + name, (301, "https://elsewhere.example/" + name))
                table["https://elsewhere.example/" + name] = (200, "image/png", png(size, size))
                results = self.drive(table)
                self.assertEqual(failed(results), ["icon " + name])
                self.assertTrue(any("redirect" in p for p in labelled(results, "icon " + name).problems))

    def test_an_icon_that_is_missing_or_not_a_png_or_the_wrong_size_fails(self):
        name = "parseh-512.png"
        for what, entry in (("404", (404, "text/html", b"")), ("html", (200, "text/html", b"<html>")),
                            ("octet", (200, "application/octet-stream", png(512, 512))),
                            ("bytes", (200, "image/png", b"<html>not a png at all, with the right header</html>")),
                            ("size", (200, "image/png", png(192, 192))), ("gone", None)):
            with self.subTest(what):
                self.assertEqual(failed(self.drive(self.broken(project.ICONS_URL + name, entry))), ["icon " + name])

    def test_a_content_type_with_a_charset_or_in_capitals_is_still_png(self):
        entry = (200, "Image/PNG; charset=binary", png(512, 512))
        self.assertEqual(failed(self.drive(self.broken(project.ICONS_URL + "parseh-512.png", entry))), [])

    # ---------------------------------------------------------------- the addresses in the documents
    def test_the_scan_reads_the_documents_the_guide_sources_and_nothing_compiled(self):
        S = project.SITE
        plant(self.root, {
            "README.md": "[a](%ssite/a.html) and <%ssite/b.html>.\n" % (S, S),
            "CHANGELOG.md": "see %ssite/c.html,\n" % S,
            "docs/releasing.md": "**%ssite/d.html**\n" % S,
            "docs/deeper/x.txt": "%ssite/e.html\n" % S,
            "html-guide/markdown/getting-started/a.md": "[x](%ssite/f.html#top)\n" % S,
            "html-guide/README.md": "%ssite/g.html\n" % S,
            "html-guide/index.html": '<a href="%ssite/h.html">h</a>\n' % S,
            # not scanned: what is compiled, what is code, what is somebody's copy
            "html-guide/site/getting-started/a.html": "%ssite/compiled.html\n" % S,
            "lib/x.py": '"%ssite/code.html"\n' % S,
            "tests/t.py": '"%ssite/test.html"\n' % S,
            ".claude/worktrees/w/README.md": "%ssite/copy.html\n" % S,
        })
        found = release.scan_links(self.root, project)
        self.assertEqual(sorted(found), [S + "site/%s.html" % c for c in "abcdefgh"])
        self.assertEqual(found[S + "site/a.html"], ["README.md"])
        self.assertEqual(found[S + "site/f.html"], ["html-guide/markdown/getting-started/a.md"])

    def test_an_address_a_document_names_without_promising_a_page_is_not_asked(self):
        # met live on 2026-10-06: the icons' folder has no page, and Parseh's own Pages path is MEANT to be 404
        S = project.SITE
        plant(self.root, {"docs/x.md": "%s and `%s%s/` and %ssite/a.html\n"
                          % (project.ICONS_URL, project.WEBSITE_URL, project.NAME, S)})
        self.assertEqual(list(release.scan_links(self.root, project)), [S + "site/a.html"])

    def test_an_address_is_asked_once_however_often_it_is_written_and_whatever_its_anchor(self):
        S = project.SITE
        plant(self.root, {"README.md": "%ssite/a.html#one %ssite/a.html#two\n" % (S, S),
                          "docs/x.md": "%ssite/a.html\n" % S})
        found = release.scan_links(self.root, project)
        self.assertEqual(list(found), [S + "site/a.html"])
        self.assertEqual(sorted(found[S + "site/a.html"]), ["README.md", "docs/x.md"])
        table = healthy()
        table[S + "site/a.html"] = (200, "text/html")
        self.drive(table)
        self.assertEqual(self.web.asked.count(S + "site/a.html"), 1)

    def test_an_address_the_checks_asked_already_is_not_asked_again_for_the_documents(self):
        plant(self.root, {"README.md": "%s and %s\n" % (project.SITE, project.WEBSITE_URL)})
        self.drive()
        for url in (project.SITE, project.WEBSITE_URL):
            self.assertEqual(self.web.fetched.count(url), 1, url)

    def test_punctuation_markup_placeholders_and_other_places_are_not_addresses_of_the_project(self):
        G, S = project.GITHUB_URL, project.SITE
        plant(self.root, {"README.md": "\n".join([
            "(%ssite/p.html)." % S,
            "**%ssite/q.html**, and" % S,
            "see \"%ssite/r.html\";" % S,
            "`%s/releases/download/<version>/parseh-<version>.zip`" % G,
            "%s/releases/download/${TAG}/parseh.zip" % G,
            "%s/releases/..." % G,
            "%s/releases/…" % G,
            "%s-fork/issues" % G,
            "https://example.org/%s" % S,
            "https://github.com/someone-else/%s/issues" % project.NAME,
            "%s/issues." % G]) + "\n"})
        self.assertEqual(sorted(release.scan_links(self.root, project)),
                         sorted([S + "site/p.html", S + "site/q.html", S + "site/r.html", G + "/issues"]))

    def test_the_site_domain_is_scanned_too_not_only_the_guide(self):
        plant(self.root, {"README.md": "%sdownloads/ and %s\n" % (project.WEBSITE_URL, project.WEBSITE_URL)})
        self.assertEqual(sorted(release.scan_links(self.root, project)),
                         sorted([project.WEBSITE_URL + "downloads/", project.WEBSITE_URL]))

    def test_a_stale_link_in_a_document_fails_and_names_the_file(self):
        S, G = project.SITE, project.GITHUB_URL
        plant(self.root, {"README.md": "%ssite/good.html\n" % S,
                          "docs/releasing.md": "%s/releases and %ssite/stale.html\n" % (G, S),
                          "html-guide/markdown/reference/commands.md": "%s/blob/main/docs/nope.md\n" % G})
        table = healthy()
        table[S + "site/good.html"] = (200, "text/html")
        table[G + "/releases"] = (200, "text/html")
        table[S + "site/stale.html"] = (404, "text/html")
        results = self.drive(table)
        links = {r.url: r for r in results if r.label == "link"}
        self.assertEqual(sorted(u for u, r in links.items() if r.failed),
                         [G + "/blob/main/docs/nope.md", S + "site/stale.html"])
        self.assertTrue(any("docs/releasing.md" in n for n in links[S + "site/stale.html"].notes))
        self.assertFalse(links[S + "site/good.html"].failed)
        self.assertEqual(failed(results), ["link", "link"])

    def test_a_link_that_redirects_to_a_page_that_answers_passes_and_a_dead_one_fails(self):
        G = project.GITHUB_URL
        plant(self.root, {"README.md": "%s/releases/latest\n%s/wiki\n" % (G, G)})
        table = healthy()
        # G/wiki is not in the fake web at all: no answer
        results = self.drive(table)
        links = {r.url: r for r in results if r.label == "link"}
        self.assertFalse(links[project.LATEST_URL].failed)
        self.assertTrue(links[G + "/wiki"].failed)

    # ---------------------------------------------------------------- what is only reported
    def test_the_reported_addresses_are_the_default_pages_address_and_the_old_path(self):
        results = self.drive()
        reported = {r.url: r for r in results if r.report}
        self.assertEqual(sorted(reported), sorted([PAGES_DEFAULT, PAGES_PARSEH]))
        self.assertTrue(all("expected" in " ".join(r.notes) for r in reported.values()))

    def test_what_is_only_reported_never_fails_whatever_it_answers(self):
        for entry in ((200, "text/html", b"a page"), (500, "text/html"), (404, "text/html"), None,
                      (301, "http://x.example/")):
            with self.subTest(entry=entry):
                table = self.broken(PAGES_DEFAULT, entry)
                table = {**table, PAGES_PARSEH: entry} if entry else {k: v for k, v in table.items() if k != PAGES_PARSEH}
                results = self.drive(table)
                self.assertEqual(failed(results), [])
                self.assertTrue(all(r.report for r in results if r.url in (PAGES_DEFAULT, PAGES_PARSEH)))

    def test_a_reported_address_whose_check_blows_up_is_still_only_a_note(self):
        results = self.drive(self.broken(PAGES_DEFAULT, RuntimeError("boom")))
        self.assertEqual(failed(results), [])
        self.assertIn("boom", " ".join(labelled(results, "default Pages address").notes))

    def test_the_old_addresses_are_asked_with_the_flag_and_never_fail(self):
        results = self.drive(old=True)
        old = [r for r in results if r.label.startswith("old ")]
        self.assertEqual(len(old), 3)
        urls = {r.label: r.url for r in old}
        self.assertEqual(urls["old repository"], "https://github.com/%s/%s" % (OLD_ACCOUNT, project.NAME))
        self.assertEqual(urls["old feed"],
                         "https://api.github.com/repos/%s/%s/releases/latest" % (OLD_ACCOUNT, project.NAME))
        self.assertEqual(urls["old guide address"], "https://%s.github.io/%s/" % (OLD_ACCOUNT.lower(), project.NAME))
        self.assertTrue(all(r.report for r in old))
        # what GitHub does after a transfer, and what it does not do for Pages
        table = healthy()
        table[urls["old repository"]] = (301, project.GITHUB_URL)
        table[urls["old feed"]] = (301, "https://api.github.com/repositories/7/releases/latest")
        table["https://api.github.com/repositories/7/releases/latest"] = (
            200, "application/json", json.dumps({"tag_name": TAG}).encode())
        table[urls["old guide address"]] = (404, "text/html", b"")
        results = self.drive(table, old=True, expect=TAG)
        self.assertEqual(failed(results), [])
        feed = labelled(results, "old feed")
        self.assertEqual([h.status for h in feed.answer.hops], [301, 200])
        self.assertTrue(any(TAG in n for n in feed.notes))
        self.assertEqual(labelled(results, "old guide address").answer.hops[0].status, 404)
        # and when none of them answers at all, still nothing fails
        self.assertEqual(failed(self.drive({**healthy(), **{u: None for u in urls.values()}}, old=True)), [])

    # ---------------------------------------------------------------- one failure does not stop the rest
    def test_a_check_that_blows_up_is_a_failure_and_the_others_still_run(self):
        table = healthy()
        table[project.ICONS_URL + "parseh-192.png"] = RuntimeError("boom")
        results = self.drive(table)
        self.assertEqual(failed(results), ["icon parseh-192.png"])
        self.assertIn("boom", " ".join(labelled(results, "icon parseh-192.png").problems))
        self.assertEqual(labelled(results, "icon apple-touch-icon.png").problems, [])
        self.assertIn("deep link", [r.label for r in results])

    def test_several_failures_are_all_found(self):
        table = self.broken(project.FEED, None)
        table[project.WEBSITE_URL] = (500, "text/html")
        table[project.ICONS_URL + "parseh-512.png"] = (404, "text/html")
        self.assertEqual(failed(self.drive(table)), ["feed", "site", "icon parseh-512.png"])


class Printing(Tree):
    """links(): the lines, the summary and the exit code."""

    def run_links(self, table, **kw):
        web = Web(table)
        lines = []
        code = release.links(self.root, kw.pop("expect", None), kw.pop("old", False), web.fetch, project,
                             kw.pop("agent", None), lines.append, 0, **kw)
        self.web = web
        return code, lines

    def test_green_exits_zero_and_every_address_gets_its_chain(self):
        code, lines = self.run_links(healthy(), expect=TAG)
        text = "\n".join(lines)
        self.assertEqual(code, 0, text)
        self.assertNotIn("FAIL", text)
        self.assertRegex(text, r"(?m)^\s*ok\s+feed\s+%s$" % re.escape(project.FEED))
        # the guide: its first hop, and where it ends
        i = next(i for i, l in enumerate(lines) if re.match(r"\s*ok\s+guide\s+%s$" % re.escape(project.GUIDE_URL), l))
        self.assertIn("301 -> " + project.SITE, lines[i + 1])
        self.assertIn("200 text/html", lines[i + 2])
        self.assertIn("1 redirect", lines[i + 2])
        # an icon: no redirect, said
        j = next(i for i, l in enumerate(lines) if "icon parseh-192.png" in l)
        self.assertIn("200 image/png", lines[j + 1])
        self.assertIn("no redirect", lines[j + 1])
        self.assertRegex(text, r"(?m)^\s*info\s+default Pages address")
        self.assertIn("0 failed", text)

    def test_a_failure_exits_one_prints_why_and_is_named_again_at_the_end(self):
        table = healthy()
        table[project.ICONS_URL + "parseh-512.png"] = (301, "https://elsewhere.example/p.png")
        table["https://elsewhere.example/p.png"] = (200, "image/png", png(512, 512))
        code, lines = self.run_links(table, expect=TAG)
        text = "\n".join(lines)
        self.assertEqual(code, 1)
        self.assertRegex(text, r"(?m)^\s*FAIL\s+icon parseh-512.png\s+")
        self.assertRegex(text, r"(?m)^\s*!\s+.*redirect")
        self.assertIn("1 failed", text)
        self.assertRegex(lines[-1], r"FAIL\s+icon parseh-512.png")

    def test_every_request_carries_the_agent_built_from_the_version_file(self):
        self.run_links(healthy())
        self.assertEqual(set(self.web.agents), {project.agent("a9.9.9")})
        self.assertTrue(project.agent("a9.9.9").startswith("Parseh/a9.9.9 (+"))

    def test_the_tag_and_the_agent_are_said_at_the_top(self):
        _, lines = self.run_links(healthy(), expect=TAG)
        self.assertIn(project.agent("a9.9.9"), lines[0])
        self.assertTrue(any(TAG in l and "expect" in l.lower() for l in lines[:4]))


class Wiring(Tree):
    """The command line: main(), refusals before any request, and the file's own promises."""

    def test_the_subcommand_is_listed_and_documented(self):
        for args in (["--help"], ["links", "--help"]):
            r = subprocess.run([sys.executable, str(ROOT / "lib" / "release.py"), *args],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("links", r.stdout)
        self.assertIn("--expect", r.stdout)
        self.assertIn("--old", r.stdout)
        doc = release.__doc__
        self.assertIn("python3 lib/release.py links", doc)

    def test_a_rehearsals_tag_or_a_non_version_is_refused_before_anything_is_asked(self):
        for tag in ("a0.4.4-rc1", "refs/tags/a0.4.4-rc2", "latest", "release-4"):
            with self.subTest(tag):
                err = io.StringIO()
                with mock.patch.object(release, "fetch", side_effect=AssertionError("asked the internet")), \
                        contextlib.redirect_stderr(err):
                    self.assertEqual(release.main(["links", "--expect", tag]), 1)
                self.assertTrue(err.getvalue().strip())

    def test_main_runs_the_checks_over_this_checkouts_files_and_returns_the_exit_code(self):
        plant(self.root, {"README.md": "%ssite/stale.html\n" % project.SITE})
        for table, want in ((healthy(), 1), ({**healthy(), project.SITE + "site/stale.html": (200, "text/html")}, 0)):
            web = Web(table)
            out = io.StringIO()
            with mock.patch.object(release, "ROOT", self.root), mock.patch.object(release, "fetch", web.fetch), \
                    mock.patch.object(release, "PAUSE", 0), contextlib.redirect_stdout(out):
                code = release.main(["links", "--expect", TAG])
            self.assertEqual(code, want, out.getvalue())
            self.assertIn(project.agent("a9.9.9"), set(web.agents))

    def test_the_old_account_is_written_in_halves_and_nowhere_whole(self):
        needle = ("Addicted2" + "Bayesian").lower()
        for path in (ROOT / "lib" / "release.py", Path(__file__)):
            self.assertNotIn(needle, path.read_text(encoding="utf-8").lower(), path.name)
        # nor the organisation site's own Pages address: it is derived from project.SITE_REPO
        self.assertNotIn("parseh-io" + ".github.io", (ROOT / "lib" / "release.py").read_text(encoding="utf-8"))
        self.assertEqual(release.OLD_ACCOUNT, OLD_ACCOUNT)

    def test_release_py_still_imports_nothing_of_parsehs_but_what_it_always_did_and_project(self):
        tree = ast.parse((ROOT / "lib" / "release.py").read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names.add(node.module.split(".")[0])
        own = {n for n in names if n not in sys.stdlib_module_names}
        self.assertEqual(own, {"version", "changelog", "project"})
        # and at the top, only the standard library: CI runs the other commands with a bare Python
        top = {a.name.split(".")[0] for n in tree.body if isinstance(n, ast.Import) for a in n.names}
        self.assertEqual({n for n in top if n not in sys.stdlib_module_names}, set())

    def test_the_icons_it_asks_for_are_the_icons_there_are_and_the_ones_the_phone_app_names(self):
        self.assertEqual(dict(release.ICON_FILES), SIZES)
        icons = ROOT / "lib" / "icons"
        files = {p.name for p in icons.glob("*.png")}
        self.assertEqual(files, set(SIZES))
        for name, size in SIZES.items():
            head = (icons / name).read_bytes()[:24]
            self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n", name)
            self.assertEqual(struct.unpack(">II", head[16:24]), (size, size), name)
        named = set(re.findall(r"[\"']((?:parseh|apple)[\w-]*\.png)[\"']", (ROOT / "lib" / "mobile.py").read_text(encoding="utf-8")))
        self.assertEqual(named, set(SIZES))

    def test_no_workflow_runs_it(self):
        for wf in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
            self.assertNotIn("release.py links", wf.read_text(encoding="utf-8"), wf.name)


# ---------------------------------------------------------------------- real sockets
def _route(server, path):
    """What the local server answers: (status, headers, body)."""
    base = "http://127.0.0.1:%d" % server.server_port
    html = {"Content-Type": "text/html; charset=utf-8"}
    if path == "/ok":
        return 200, html, b"<html>hello</html>"
    if path == "/moved":
        return 301, {"Location": "/ok"}, b""
    if path == "/found":
        return 302, {"Location": base + "/moved"}, b""
    if path == "/relative":
        return 302, {"Location": "ok"}, b""
    if path == "/gone":
        return 404, html, b"not here"
    if path == "/loop":
        return 302, {"Location": "/loop"}, b""
    m = re.fullmatch(r"/chain/(\d+)", path)
    if m:
        return 302, {"Location": "/chain/%d" % (int(m.group(1)) + 1)}, b""
    if path == "/nowhere":
        return 301, {}, b""
    if path == "/hang":
        time.sleep(1.5)
        return 200, html, b"late"
    if path == "/big":
        return 200, html, b"x" * 200000
    if path == "/img.png":
        return 200, {"Content-Type": "image/png"}, png(8, 8)
    # the project's own addresses, in the shape the real ones have
    if path == "/feed":
        return 200, {"Content-Type": "application/json"}, json.dumps({"tag_name": TAG}).encode()
    if path == "/gh":
        return 200, html, b"repository"
    if path == "/gh/releases/latest":
        return 302, {"Location": "/gh/releases/tag/" + TAG}, b""
    if path == "/gh/releases/tag/" + TAG:
        return 200, html, b"release"
    if path == "/":
        return 200, html, b"<html>Parseh</html>"
    if path == "/guide":
        return 301, {"Location": "/guide/"}, b""
    if path == "/guide/":
        return 200, html, b"<html>guide</html>"
    if path == "/guide/site/reference/whats-new.html":
        return 200, html, page(TAG).replace(project.WEBSITE_URL.encode(), (base + "/").encode())
    m = re.fullmatch(r"/guide/lib/icons/([\w.-]+)", path)
    if m and m.group(1) in SIZES:
        if m.group(1) == server.redirected_icon:
            return 301, {"Location": "/elsewhere/" + m.group(1)}, b""
        return 200, {"Content-Type": "image/png"}, png(SIZES[m.group(1)], SIZES[m.group(1)])
    m = re.fullmatch(r"/elsewhere/([\w.-]+)", path)
    if m and m.group(1) in SIZES:
        return 200, {"Content-Type": "image/png"}, png(SIZES[m.group(1)], SIZES[m.group(1)])
    if path == "/pages-guide/":
        return 301, {"Location": "/guide/"}, b""
    if path == "/old/":
        return 404, html, b"not found"
    return 404, html, b"no such page"


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.seen.append((urlsplit(self.path).path, self.headers.get("User-Agent")))
        status, headers, body = _route(self.server, urlsplit(self.path).path)
        try:
            self.send_response(status)
            for k, v in headers.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass            # a client that gave up on /hang


class OverTheWire(Tree):
    """Real sockets: one local server, 127.0.0.1, answering what the internet would."""

    @classmethod
    def setUpClass(cls):
        # never through a proxy this machine has set for the internet
        cls._env = {k: os.environ.get(k) for k in ("NO_PROXY", "no_proxy")}
        os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.daemon_threads = True
        cls.server.seen = []
        cls.server.redirected_icon = None
        cls.base = "http://127.0.0.1:%d" % cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.project = types.SimpleNamespace(
            NAME="Parseh", REPO="o/Parseh", GITHUB_URL=cls.base + "/gh", RELEASES_URL=cls.base + "/gh/releases",
            LATEST_URL=cls.base + "/gh/releases/latest", FEED=cls.base + "/feed", WEBSITE_URL=cls.base + "/",
            GUIDE_URL=cls.base + "/guide", SITE=cls.base + "/guide/", ICONS_URL=cls.base + "/guide/lib/icons/",
            GUIDE_REPO="o/guide", SITE_REPO="o/o.github.io", agent=project.agent)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        for k, v in cls._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def setUp(self):
        super().setUp()
        self.server.seen.clear()
        self.server.redirected_icon = None

    def url(self, path):
        return self.base + path

    def test_fetch_follows_by_hand_over_a_real_socket(self):
        ans = release.fetch(self.url("/found"), 100, "Parseh/test-agent")
        self.assertEqual([(h.status, urlsplit(h.url).path) for h in ans.hops], [(302, "/found"), (301, "/moved"), (200, "/ok")])
        self.assertEqual(ans.hops[0].location, self.url("/moved"))
        self.assertEqual(ans.hops[1].location, "/ok")
        self.assertEqual((ans.hops[-1].ctype, ans.body), ("text/html", b"<html>hello</html>"))
        self.assertEqual(urlsplit(release.fetch(self.url("/relative")).hops[-1].url).path, "/ok")
        # the agent went to every hop
        self.assertEqual({a for _, a in self.server.seen[:3]}, {"Parseh/test-agent"})
        # a 404 is a hop with a status and nothing else wrong
        gone = release.fetch(self.url("/gone"))
        self.assertEqual((len(gone.hops), gone.hops[0].status, gone.hops[0].error), (1, 404, None))
        self.assertEqual(gone.hops[0].ctype, "text/html")
        # the body is only read when asked for, and only as far as asked
        self.assertEqual(release.fetch(self.url("/big")).body, b"")
        self.assertEqual(len(release.fetch(self.url("/big"), 1000).body), 1000)
        self.assertEqual(release.fetch(self.url("/img.png"), 64).hops[0].ctype, "image/png")

    def test_loops_endless_chains_redirects_to_nowhere_silence_and_refusal_are_hops_with_reasons(self):
        loop = release.fetch(self.url("/loop"))
        self.assertIn("loop", loop.hops[-1].error)
        self.server.seen.clear()
        endless = release.fetch(self.url("/chain/0"))
        self.assertEqual(len(endless.hops), 7)
        self.assertIn("more than 6", endless.hops[-1].error)
        self.assertEqual(len(self.server.seen), 7)
        nowhere = release.fetch(self.url("/nowhere"))
        self.assertEqual((nowhere.hops[0].status, "Location" in nowhere.hops[0].error), (301, True))
        silent = release.fetch(self.url("/hang"), timeout=0.3)
        self.assertEqual((len(silent.hops), silent.hops[0].status), (1, None))
        self.assertIn("no answer", silent.hops[0].error)
        with socket.socket() as s:          # a port nobody listens on
            s.bind(("127.0.0.1", 0))
            dead = "http://127.0.0.1:%d/" % s.getsockname()[1]
        refused = release.fetch(dead, timeout=2)
        self.assertEqual(refused.hops[0].status, None)
        self.assertTrue(refused.hops[0].error)
        for odd in ("file:///etc/passwd", "ftp://example.org/x", "not an address"):
            self.assertIn("http", release.fetch(odd).hops[0].error, odd)

    def run_links(self, **kw):
        lines = []
        code = release.links(self.root, TAG, kw.pop("old", False), None, self.project, None, lines.append, 0,
                             reports=[("default Pages address", self.url("/pages-guide/"), "a redirect to the guide"),
                                      ("Parseh's Pages path", self.url("/Parseh/"), "404")],
                             olds=[("old guide address", self.url("/old/"), "404")], **kw)
        return code, lines

    def test_links_end_to_end_over_real_sockets_green(self):
        plant(self.root, {"README.md": "%s/releases/latest and %s\n" % (self.project.GITHUB_URL, self.project.SITE)})
        code, lines = self.run_links(old=True)
        text = "\n".join(lines)
        self.assertEqual(code, 0, text)
        self.assertNotIn("FAIL", text)
        for label in ("feed", "latest", "site", "guide", "guide/", "deep link", "icon parseh-192.png",
                      "icon apple-touch-icon.png", "link"):
            self.assertRegex(text, r"(?m)^\s*ok\s+%s\s+http://127\.0\.0\.1:" % re.escape(label))
        self.assertRegex(text, r"(?m)^\s*info\s+default Pages address\s+")
        self.assertRegex(text, r"(?m)^\s*info\s+old guide address\s+")
        self.assertIn("301 -> %s" % self.project.SITE, text)
        self.assertIn("404", text)
        # the agent that the version file gave went over the wire
        self.assertEqual({a for _, a in self.server.seen}, {project.agent("a9.9.9")})

    def test_links_end_to_end_over_real_sockets_with_an_icon_behind_a_redirect_and_a_dead_link(self):
        self.server.redirected_icon = "parseh-512.png"
        plant(self.root, {"docs/x.md": "%s/nothing-here\n" % self.project.GITHUB_URL})
        code, lines = self.run_links()
        text = "\n".join(lines)
        self.assertEqual(code, 1, text)
        self.assertRegex(text, r"(?m)^\s*FAIL\s+icon parseh-512\.png\s+http://127\.0\.0\.1:")
        self.assertRegex(text, r"(?m)^\s*FAIL\s+link\s+%s/nothing-here" % re.escape(self.project.GITHUB_URL))
        self.assertIn("301 -> %s/elsewhere/parseh-512.png" % self.base, text)
        self.assertIn("200 image/png, 1 redirect", text)
        self.assertIn("2 failed", text)
        # the others went on being asked
        self.assertRegex(text, r"(?m)^\s*ok\s+icon apple-touch-icon\.png")


if __name__ == "__main__":
    unittest.main()
