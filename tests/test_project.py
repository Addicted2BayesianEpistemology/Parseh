# SPDX-License-Identifier: GPL-3.0-or-later
"""Where Parseh lives (lib/project.py, a0.4.4): one module says it, and the tree agrees.

    python3 -m unittest tests/test_project.py

A move is a decision, and the first test is where it is written down: it pins
the LITERAL addresses.  The rest hold the tree to them -- the old place is
gone from every tracked file but the ones that describe it, no address of the
project is spelt a little differently somewhere, the update road and every
download read the module, and the site the addresses name is a site that
really has those pages and those icons (the real assembly, `build.py --pages`;
never `git ls-files`, which is a property standing in for the thing).
"""
import ast
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in ("markdown/exlex", "markdown/app", "lib", "youtube/lib", "html-guide", "."):
    sys.path.insert(0, str(ROOT / p))
import project                                                 # noqa: E402

BINARY = (".png", ".gif", ".jpg", ".jpeg", ".ico", ".woff", ".woff2", ".ttf", ".otf", ".pdf", ".zip", ".mp3",
          ".ogg", ".wav", ".mp4", ".webm", ".gz", ".xz", ".db", ".pyc", ".bin", ".onnx", ".ckpt", ".sha256")

# the files that DESCRIBE the old place, and so may name it
DESCRIBE_OLD = {
    "tests/test_project.py",
    "docs/releasing.md",        # "Where Parseh lives": the old address, and what GitHub does with it
}
# the address of the repository the personal account held, and of its Pages site (any case)
OLD = re.compile(r"Addicted2BayesianEpistemology/Parseh|addicted2bayesianepistemology\.github\.io", re.I)
# where a stranger's name for the organisation's own Pages address may stand
GITHUB_IO = "parseh-io.github.io"
DESCRIBE_GITHUB_IO = {
    "tests/test_project.py",
    "docs/releasing.md",
    "lib/release.py",                          # `links` reports what it answers
    "tests/test_release_links.py",
    "lib/project.py",                          # says that this address redirects to the domain, and why a machine never fetches it
    "html-guide/README.md",                    # where the project's own guide is published from
    "html-guide/markdown/writing-this-guide/compiling.md",
    ".github/workflows/guide-pages.yml",
    "html-guide/engine/bar.py",                # the bar is the site's twin: it says whose repository that is
    "tests/test_guide_published.py",
}


def tracked_text():
    """(path, text) of every tracked text file; the compiled guide's pages included."""
    out = subprocess.run(["git", "ls-files", "-z"], cwd=str(ROOT), capture_output=True).stdout.decode("utf-8")
    for rel in out.split("\0"):
        if not rel or rel.lower().endswith(BINARY):
            continue
        path = ROOT / rel
        try:
            if path.is_symlink() or not path.is_file():
                continue
            yield rel, path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue


class TheAddressesArePinned(unittest.TestCase):
    def test_the_literals(self):
        self.assertEqual((project.ORG, project.NAME, project.REPO), ("parseh-io", "Parseh", "parseh-io/Parseh"))
        self.assertEqual(project.GITHUB_URL, "https://github.com/parseh-io/Parseh")
        self.assertEqual(project.RELEASES_URL, "https://github.com/parseh-io/Parseh/releases")
        self.assertEqual(project.LATEST_URL, "https://github.com/parseh-io/Parseh/releases/latest")
        self.assertEqual(project.FEED, "https://api.github.com/repos/parseh-io/Parseh/releases/latest")
        self.assertEqual(project.WEBSITE_URL, "https://parseh.io/")
        self.assertEqual(project.GUIDE_URL, "https://parseh.io/guide")
        self.assertEqual(project.SITE, "https://parseh.io/guide/")
        self.assertEqual(project.ICONS_URL, "https://parseh.io/guide/lib/icons/")
        self.assertEqual((project.GUIDE_REPO, project.SITE_REPO), ("parseh-io/guide", "parseh-io/parseh-io.github.io"))
        self.assertEqual(project.agent("a0.4.4"), "Parseh/a0.4.4 (+https://github.com/parseh-io/Parseh)")

    def test_it_is_standard_library_only_and_names_no_version(self):
        src = (ROOT / "lib" / "project.py").read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module]
                for n in names:
                    self.assertIn(n.split(".")[0], sys.stdlib_module_names, "project.py imports " + n)
        self.assertEqual(re.findall(r"\ba\d+\.\d+\.\d+\b", src), [], "a version is `agent()`'s argument, never written here")


class TheOldPlaceIsGone(unittest.TestCase):
    def test_nothing_tracked_names_it_but_what_describes_it(self):
        stray = [rel for rel, text in tracked_text() if rel not in DESCRIBE_OLD and OLD.search(text)]
        self.assertEqual(stray, [], "the old repository and its Pages address belong to lib/project.py's one edit")

    def test_the_organisations_own_pages_address_is_named_by_nothing_else(self):
        # parseh-io.github.io redirects to the domain: a person is never given it, and a machine never fetches it
        stray = [rel for rel, text in tracked_text() if rel not in DESCRIBE_GITHUB_IO
                 and GITHUB_IO in text.lower()]
        self.assertEqual(stray, [])

    def test_every_address_of_the_project_is_spelt_as_the_constants_spell_it(self):
        # no typo, no stray case, no other scheme or host for the same place: the project's repository is
        # github.com/parseh-io/Parseh (other repositories of the organisation are other things and may be named),
        # the feed is the API's, and the domain is the bare https://parseh.io
        github = re.compile(r"https?://(?:www\.)?github\.com/parseh-io/([A-Za-z0-9_.-]+)", re.I)
        api = re.compile(r"https?://api\.github\.com/repos/parseh-io/([A-Za-z0-9_.-]+)", re.I)
        domain = re.compile(r"(https?://)((?:www\.)?parseh\.io)(?![A-Za-z0-9.-])([^\s\"'<>)\]`]*)", re.I)
        wrong = []
        for rel, text in tracked_text():
            if rel in DESCRIBE_OLD or rel.startswith("html-guide/site/"):
                continue
            for pat in (github, api):
                for m in pat.finditer(text):
                    repo = m.group(1)
                    if repo.lower() == project.NAME.lower() and (repo != project.NAME or not m.group(0).startswith(
                            ("https://github.com/", "https://api.github.com/repos/"))):
                        wrong.append("%s: %s" % (rel, m.group(0)))
            for m in domain.finditer(text):
                if m.group(1) != "https://" or m.group(2) != "parseh.io":
                    wrong.append("%s: %s" % (rel, m.group(0)))
        self.assertEqual(wrong, [], "\n".join(wrong[:20]))


class TheReadersRead(unittest.TestCase):
    def test_the_update_road(self):
        import os
        import updater
        old = os.environ.pop("PARSEH_UPDATE_FEED", None)
        try:
            self.assertEqual(updater.feed_url(), project.FEED)
            os.environ["PARSEH_UPDATE_FEED"] = "http://127.0.0.1:1/feed"
            self.assertEqual(updater.feed_url(), "http://127.0.0.1:1/feed", "a test's own feed stands in for GitHub")
        finally:
            os.environ.pop("PARSEH_UPDATE_FEED", None)
            if old is not None:
                os.environ["PARSEH_UPDATE_FEED"] = old
        for gone in ("REPO", "FEED", "RELEASES_PAGE"):
            self.assertFalse(hasattr(updater, gone), "updater.%s is lib/project.py's now" % gone)

    def test_a_git_checkout_is_sent_to_the_releases_page_of_the_new_home(self):
        import updater
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / ".git").mkdir()
            said = updater.installed(td)["refused"]
        self.assertIn(project.RELEASES_URL, said)

    def test_the_helper_imports_nothing_of_parseh_s_at_the_top(self):
        # lib/updater.py is also the helper run on its own from .parseh-update/, beside an install that may be
        # half replaced: its top level is the standard library, and project is read inside the functions that
        # want an address
        tree = ast.parse((ROOT / "lib" / "updater.py").read_text(encoding="utf-8"))
        top = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        for node in top:
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module]
            for n in names:
                self.assertIn(n.split(".")[0], sys.stdlib_module_names, "updater.py imports %s at its top" % n)
        src = (ROOT / "lib" / "updater.py").read_text(encoding="utf-8")
        self.assertNotIn("Addicted2", src)
        self.assertNotIn("github.com/", src.replace("https://api.github.com", ""), "no address is written in the updater")

    def test_every_download_introduces_itself_with_the_projects_line(self):
        import version
        import getarasaac
        import getcorpus
        import getmt
        import getstt
        import getsyn
        want = project.agent(version.VERSION)
        for mod in (getarasaac, getcorpus, getmt, getstt, getsyn):
            self.assertEqual(mod.UA, want, mod.__name__)

    def test_the_foot_of_an_exported_page_links_the_project_and_its_guide(self):
        import webexport
        links = re.findall(r'href="([^"]+)"', webexport._footer())
        self.assertEqual(links, [project.GITHUB_URL, project.GUIDE_URL])

    def test_the_feet_of_the_hub_the_settings_hub_and_the_guide_link_the_project_not_the_person(self):
        # lib/author.py is standard library only and cannot read this module, so each page that draws a foot
        # hands it the address (the owner, 2026-10-06): a move of the project is this module's one edit
        import author
        import settingspage
        page = settingspage.hub()
        foot = re.search(r'<p class="foot">(.*?)</p>', page[page.index('<main class="settings">'):], re.S).group(1)
        self.assertEqual(re.findall(r'href="(https?://[^"]*)"', foot), [project.GITHUB_URL, project.WEBSITE_URL, author.SITE_URL])
        self.assertIn('aria-label="%s on GitHub"' % project.NAME, foot)
        self.assertNotIn(author.GITHUB_URL, page)
        front = (ROOT / "html-guide" / "index.html").read_text(encoding="utf-8")
        guide_foot = re.search(r'<footer class="g-foot">(.*?)</footer>', front, re.S).group(1)
        self.assertEqual(re.findall(r'href="(https?://[^"]*)"', guide_foot), [project.GITHUB_URL, project.WEBSITE_URL, author.SITE_URL])
        # and the author line, where his name stands, is his profile
        self.assertEqual(re.findall(r'href="(https?://[^"]*)"', author.links()), [author.GITHUB_URL, author.SITE_URL])

    def test_the_phone_app_fetches_its_icons_from_under_the_domain(self):
        import mobile
        self.assertEqual(mobile.PUBLIC_ICONS, project.ICONS_URL)


class TheSiteIsWhatTheAddressesSay(unittest.TestCase):
    """The real assembly, once: `build.py --pages`, as the workflow of the guide's repository runs it."""

    @classmethod
    def setUpClass(cls):
        import build
        cls._td = tempfile.TemporaryDirectory()
        cls.site = Path(cls._td.name) / "guide"
        cls.report = build.assemble_pages(cls.site)

    @classmethod
    def tearDownClass(cls):
        cls._td.cleanup()

    def present(self, url):
        """Whether an address under SITE is a file of the assembly (a folder is its index.html)."""
        rel = re.split(r"[#?]", url[len(project.SITE):], 1)[0]
        path = self.site / rel
        return path.is_file() or (path.is_dir() and (path / "index.html").is_file()) or rel == ""

    def test_every_link_to_the_guide_in_the_documents_is_a_page_the_site_has(self):
        pat = re.compile(re.escape(project.GUIDE_URL) + r"/[^\s\"'<>)\]`]*")
        missing = []
        for rel, text in tracked_text():
            if not (rel == "README.md" or rel.startswith("docs/") or rel.startswith("html-guide/markdown/")):
                continue
            for url in pat.findall(text):
                if url.endswith(("/", ".")) and url.rstrip("/.") == project.GUIDE_URL:
                    continue
                if not self.present(url):
                    missing.append("%s: %s" % (rel, url))
        self.assertEqual(missing, [], "\n".join(missing[:20]))

    def test_the_icons_the_phone_app_is_given_are_published_with_the_site(self):
        import mobile
        named = mobile.manifest("Mozilla/5.0 (Linux; Android 14) Chrome/126.0.0.0 Mobile")["icons"]
        outside = [i for i in named if i["src"].startswith(project.ICONS_URL)]
        self.assertEqual(len(outside), 3, named)
        for icon in outside:
            path = self.site / "lib" / "icons" / icon["src"][len(project.ICONS_URL):]
            self.assertTrue(path.is_file(), "%s is named for the phone and the site does not carry it" % icon["src"])
            data = path.read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n", icon["src"])
            w, h = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
            self.assertEqual("%dx%d" % (w, h), icon["sizes"], icon["src"])


if __name__ == "__main__":
    unittest.main()
