# SPDX-License-Identifier: GPL-3.0-or-later
"""The guide as it is PUBLISHED -- the layout `html-guide/build.py --pages`
assembles, which a hand-run workflow in parseh-io/guide puts at
https://parseh.io/guide (project.GUIDE_URL).

    python3 -m unittest tests/test_guide_published.py

Two things set that layout apart from the guide an install carries (the
committed html-guide/site/, read from the computer, often with no network):

  * the phone app's icons: Chrome's WebAPK server fetches them from the
    internet, from project.ICONS_URL, so the published site holds them, and
    only them (lib/icons/*.png: not make.mjs, which says how they were made);
  * the slim BAR at the top of every page, with the Parseh logo and a link to
    project.WEBSITE_URL (html-guide/engine/bar.py).  The installed guide has
    none, and a guide exported into somebody's own project has none: the bar
    is Parseh's, and only Parseh's own layout wears it.

ONE assembly is made for the whole class (a compile of the real guide), not a
stand-in for it: what is checked is the folder GitHub Pages would be given.
The browser half -- the bar drawn, where it sits, the contents and the search
under it, at a phone's width and a desktop's, served from a folder named
guide -- is tests/html_guide.mjs.
"""
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "html-guide"
sys.path.insert(0, str(GUIDE))
sys.path.insert(0, str(ROOT / "lib"))
import project  # noqa: E402
from engine.site import Site  # noqa: E402

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def png_size(data):
    """(width, height) of a PNG, read from its IHDR."""
    assert data[:8] == PNG_MAGIC and data[12:16] == b"IHDR", "not a PNG"
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def html_files(folder):
    return sorted(p for p in Path(folder).rglob("*.html") if p.is_file())


def is_redirect(text):
    """A page that only sends a visitor on (a Hugo alias): no chrome of its own."""
    return 'http-equiv="refresh"' in text


class PublishedLayout(unittest.TestCase):
    """build.py --pages, assembled once."""

    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.mkdtemp(prefix="guide-published-")
        cls.site = Path(cls.td) / "_site"
        spec = importlib.util.spec_from_file_location("guide_build", GUIDE / "build.py")
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        cls.report = build.assemble_pages(cls.site)
        cls.pages = {}
        cls.redirects = []
        for p in html_files(cls.site):
            text = p.read_text(encoding="utf-8")
            if is_redirect(text):
                cls.redirects.append(p)
            else:
                cls.pages[p] = text

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.td, ignore_errors=True)

    # ---------------------------------------------------------------- the pages
    def test_the_layout_has_the_front_page_and_the_compiled_pages(self):
        self.assertEqual(self.report.errors, [])
        rel = {p.relative_to(self.site).as_posix() for p in self.pages}
        self.assertIn("index.html", rel)
        self.assertIn("site/showcase.html", rel)
        self.assertGreater(len(self.pages), 100, "the whole guide, not a few pages")

    def test_every_page_wears_the_bar_once_and_its_link_is_the_website(self):
        for p, text in self.pages.items():
            rel = p.relative_to(self.site).as_posix()
            self.assertEqual(text.count('<header class="ps-bar"'), 1, rel)
            home = re.findall(r'<a class="ps-home" href="([^"]*)"', text)
            self.assertEqual(home, [project.WEBSITE_URL], rel)

    def test_the_bar_comes_before_the_guide_s_own_header(self):
        for p, text in self.pages.items():
            self.assertLess(text.index('<header class="ps-bar"'), text.index('<header class="g-top"'),
                            p.relative_to(self.site).as_posix())

    def test_the_bar_is_the_site_s_with_guide_marked_as_where_one_is(self):
        # the site's own bar (parseh-io.github.io, <header class="bar alone">):
        # the same three links in the same order, and the flag; Guide leads
        # to the guide's front page wherever the guide is served from (a
        # relative address), the others to the site
        front = (self.site / "index.html").resolve()
        for p, text in self.pages.items():
            rel = p.relative_to(self.site).as_posix()
            nav = re.search(r'<nav class="ps-nav"[^>]*>(.*?)</nav>', text, re.S)
            self.assertIsNotNone(nav, rel)
            links = re.findall(r'<a href="([^"]*)"([^>]*)>([^<]*)</a>', nav.group(1))
            self.assertEqual([l[2] for l in links], ["Guide", "Examples", "Downloads"], rel)
            self.assertEqual([("aria-current" in l[1]) for l in links], [True, False, False], rel)
            self.assertEqual((p.parent / links[0][0]).resolve(), front, rel)
            self.assertEqual([l[0] for l in links[1:]],
                             [project.WEBSITE_URL + "examples/", project.WEBSITE_URL + "downloads/"], rel)
            self.assertEqual(len(re.findall(r'<button class="ps-lang"', text)), 1, rel)
            self.assertIn(">Parseh</span>", text, rel)

    def test_the_bar_fetches_nothing_from_another_host(self):
        # the only addresses in it are the links a person follows; the letter
        # is set in a face the guide's own stylesheet loads from the
        # published site; the flag is inline; the style and the script name
        # no host at all; and it all works with scripts off
        wanted = [project.WEBSITE_URL, project.WEBSITE_URL + "examples/", project.WEBSITE_URL + "downloads/"]
        for p, text in self.pages.items():
            rel = p.relative_to(self.site).as_posix()
            bar = re.search(r'<header class="ps-bar".*?</header>', text, re.S).group(0)
            absolute = re.findall(r'(?:href|src)="((?:[a-z]+:)?//[^"]*|https?:[^"]*)"', bar)
            self.assertEqual(absolute, wanted, rel)
            self.assertNotIn("<img", bar, rel)
            self.assertEqual(re.findall(r'<span class="ps-glyph"[^>]*><i>(.)</i>', bar), ["\u067e"], rel)
            css = re.search(r'<style id="ps-bar-css">(.*?)</style>', text, re.S)
            self.assertIsNotNone(css, rel)
            script = re.search(r'<script id="ps-bar-js">(.*?)</script>', text, re.S)
            self.assertIsNotNone(script, rel)
            for what in (css.group(1), script.group(1)):
                self.assertNotRegex(what, r"https?:|//[a-z]|@import|fetch\(|XMLHttpRequest|url\(", rel)

    def test_the_letter_of_the_logo_has_its_face_in_the_layout(self):
        # guide.css, which every page links, names Noto Nastaliq Urdu at an
        # address relative to itself: that file is in the published folder
        css = (self.site / "assets" / "guide.css").read_text(encoding="utf-8")
        m = re.search(r"@font-face\{font-family:'Noto Nastaliq Urdu';\s*src:url\(([^)]+)\)", css)
        self.assertIsNotNone(m)
        font = (self.site / "assets" / m.group(1)).resolve()
        self.assertTrue(font.is_file(), str(font))
        self.assertEqual(font.read_bytes()[:4], b"wOF2")

    def test_a_redirect_stub_is_a_stub_and_nothing_else_lacks_the_bar(self):
        # the Hugo aliases are one line of HTML that sends the visitor on; any
        # other page of the layout is a page of the guide
        for p in self.redirects:
            self.assertNotIn("ps-bar", p.read_text(encoding="utf-8"))
        for p, text in self.pages.items():
            self.assertIn('class="guide', text, p.relative_to(self.site).as_posix())

    def test_the_pages_address_the_site_by_relative_links(self):
        # the published guide stands at /guide/ and not at the root: a page
        # that wrote an address from the root would look in parseh.io's own
        # folders (the site's 404) instead of the guide's.  The hub's
        # "Parseh" button (href="/") is the one exception: hidden, and shown
        # only to a page Parseh itself served (guide.js)
        for p, text in self.pages.items():
            for attr in re.findall(r'\s(?:href|src)="(/[^"]*)"', text):
                self.assertEqual(attr, "/", p.relative_to(self.site).as_posix())
            self.assertNotRegex(text, r"""url\(\s*['"]?/(?!/)""", p.relative_to(self.site).as_posix())

    # ---------------------------------------------------------------- the icons
    def test_the_phone_app_s_icons_are_published_where_the_manifest_names_them(self):
        real = sorted(p for p in (ROOT / "lib" / "icons").glob("*.png"))
        self.assertEqual({p.name for p in real},
                         {"parseh-192.png", "parseh-512.png", "parseh-maskable-512.png",
                          "apple-touch-icon.png"})
        # project.ICONS_URL is the site's address plus the folder in the layout
        self.assertTrue(project.ICONS_URL.startswith(project.SITE))
        folder = self.site / project.ICONS_URL[len(project.SITE):]
        self.assertEqual(folder, self.site / "lib" / "icons")
        for p in real:
            got = folder / p.name
            self.assertTrue(got.is_file(), p.name)
            data = got.read_bytes()
            self.assertEqual(data, p.read_bytes(), p.name)
            self.assertEqual(png_size(data), png_size(p.read_bytes()), p.name)
        sizes = {p.name: png_size((folder / p.name).read_bytes()) for p in real}
        self.assertEqual(sizes["parseh-192.png"], (192, 192))
        self.assertEqual(sizes["parseh-512.png"], (512, 512))
        self.assertEqual(sizes["parseh-maskable-512.png"], (512, 512))

    def test_only_the_pngs_are_published_not_the_script_that_drew_them(self):
        folder = self.site / "lib" / "icons"
        self.assertFalse((folder / "make.mjs").exists())
        self.assertEqual(sorted(os.listdir(folder)),
                         sorted(p.name for p in (ROOT / "lib" / "icons").glob("*.png")))
        self.assertFalse((self.site / "lib" / "parseh.css").exists(), "nothing else of lib/ goes along")
        self.assertEqual(sorted(p.name for p in (self.site / "lib").iterdir()), ["icons"])


class TheInstalledGuideHasNoBar(unittest.TestCase):
    """The committed html-guide/site/ ships in every install and is read from
    the computer: the bar is the published layout's alone."""

    def test_the_committed_pages_have_no_bar(self):
        files = html_files(GUIDE / "site") + [GUIDE / "index.html"]
        self.assertGreater(len(files), 100)
        for p in files:
            text = p.read_text(encoding="utf-8")
            self.assertNotIn("ps-bar", text, str(p.relative_to(ROOT)))

    def test_a_plain_compile_has_no_bar(self):
        # the switch is off unless assemble_pages turns it on: the compile
        # that makes html-guide/site/ and the one the front page's button runs
        with tempfile.TemporaryDirectory(prefix="guide-plain-") as td:
            out = Path(td) / "site"
            report = Site(GUIDE).build(out)
            self.assertEqual(report.errors, [])
            files = html_files(out)
            self.assertGreater(len(files), 100)
            for p in files:
                self.assertNotIn("ps-bar", p.read_text(encoding="utf-8"), str(p.relative_to(out)))

    def test_the_front_page_of_a_plain_layout_has_no_bar_either(self):
        # (and the hand-written front page is copied, not changed: it is
        # the file in the repository that shows up in every install)
        self.assertNotIn("ps-bar", (GUIDE / "index.html").read_text(encoding="utf-8"))


class AnExportIsNotParseh(unittest.TestCase):
    """`build.py --export` copies the guide into somebody's own project, whose
    pages workflow runs `build.py --pages`: it must not put Parseh's bar, and
    a link to Parseh's site, on a guide that is not Parseh's."""

    def test_an_exported_copy_lays_out_pages_with_no_bar_and_no_icons(self):
        with tempfile.TemporaryDirectory(prefix="guide-export-") as td:
            dest = Path(td) / "website"
            r = subprocess.run([sys.executable, str(GUIDE / "build.py"), "--export", str(dest), "-q"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            env = {"PATH": os.environ.get("PATH", ""), "HOME": td}
            out = Path(td) / "_site"
            r = subprocess.run([sys.executable, str(dest / "build.py"), "--pages", str(out), "-q"],
                               capture_output=True, text=True, env=env, cwd=td)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            files = html_files(out)
            self.assertGreater(len(files), 100)
            for p in files:
                text = p.read_text(encoding="utf-8")
                self.assertNotIn("ps-bar", text, str(p.relative_to(out)))
                self.assertNotIn('class="ps-home"', text, str(p.relative_to(out)))
            self.assertFalse((out / "lib").exists())


if __name__ == "__main__":
    unittest.main()
