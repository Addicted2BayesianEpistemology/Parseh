# SPDX-License-Identifier: GPL-3.0-or-later
"""A release: lib/release.py, what .gitattributes leaves out of it, and the
workflow that makes one on GitHub.

    python3 -m unittest tests/test_release.py

The builder is DRIVEN, not read.  Each test that builds makes a small git
repository in a scratch folder -- a Parseh in miniature, carrying this
checkout's own .gitattributes, .gitignore, environment.yml, lib/release.py,
lib/runtime.py, lib/changelog.py and lib/version.py, with every data format's
constant written into the file lib/version.py's FORMATS names for it and a
What's new of its own -- commits it, runs `python3 lib/release.py build` in
it the way a developer does, and opens the zip that comes out: what
export-ignore left out, what it kept, the .bat files' CRLF, the modes, and
the manifest against the bytes.  Git runs with no configuration but the
repository's own, so the owner's ~/.gitconfig changes nothing here.  Nothing
is written outside the scratch folders.

A rehearsal (the owner, 2026-09-25) is driven the same way: `check` passes
aX.Y.Z-rcN while the headings are undated and refuses the version's own tag
until both are dated, `build --tag` names the zip and the manifest by the
tag.  The guide check is driven in a scratch copy of what a compile of the
guide reads, never on this checkout's own guide, which other work may leave
out of step at any moment.

The workflow's shape is held as tests/test_html_guide.py holds
guide-pages.yml: the strings it must say and the order it says them in.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import changelog  # noqa: E402
import release    # noqa: E402
import runtime    # noqa: E402
import version    # noqa: E402

HAVE_GIT = shutil.which("git") is not None

# git with nothing of this machine's: no ~/.gitconfig, no /etc/gitconfig, a
# fixed author and a fixed time, so a commit is the same commit every run
GIT_ENV = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="test@example.org",
               GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="test@example.org",
               GIT_AUTHOR_DATE="2026-01-02T03:04:05Z", GIT_COMMITTER_DATE="2026-01-02T03:04:05Z")

V = "a0.0.1"          # the miniature's version: any version, never this checkout's

# the data formats' constants, as the files lib/version.py's FORMATS names
# hold them -- {path: the lines to write} -- so that the miniature's
# lib/version.py can be this checkout's own, with its one rule for what a
# version is, and still say its formats
FORMAT_LINES = {}
for _fmt, (_rel, _name, _what) in version.FORMATS.items():
    FORMAT_LINES.setdefault(_rel, []).append(
        "%s = %r\n" % (_name, version._constant(str(ROOT / _rel), _name)))

RUNNABLE = ("install.sh", "serve.sh", "build.sh", "Parseh.command", "serve.py")

# what the owner decided a release leaves out (TO-DO §16.13, and his own
# additions when releases began): each one is committed in the miniature and
# must not come out of the build
LEFT_OUT = ("tests/test_x.py", "tests/fixtures/a.txt", "docs/demo-books.gif",
            ".github/workflows/release.yml", ".gitattributes", ".gitignore", ".nojekyll",
            "index.html", "lib/icons/make.mjs", "youtube/docs/glossary-ci-stories.md",
            "lib/wavealign_lab.py", "youtube/.gitignore", "youtube/serve.py", "youtube/serve.sh",
            "dist/parseh-old.zip")
# and what must come out, beside them: the folders Parseh writes into, and
# neighbours of what was left out, which prove the rules are not too wide
KEPT = ("clips/README.md", "exercises/README.md", "config/.gitkeep", "dict/.gitkeep",
        "books/persian/.gitkeep", "youtube/videos/persian/.gitkeep",
        "markdown/library/persian/.gitkeep", "youtube/anki/README.md",
        "html-guide/index.html", "html-guide/site/showcase.html",
        "html-guide/site/images/flashcard.gif", "docs/lang/persian.md", "docs/notes.md",
        "lib/icons/icon.svg", "youtube/docs/conventions.md", "youtube/lib/player.js",
        "lib/fonts/OFL.txt", "lib/fonts/GUST-FONT-LICENSE.txt", "lib/mathjax/tex-svg.js",
        "LICENSE", "VERSION", "README.md", "CHANGELOG.md", "environment.yml",
        "install.bat", "serve.bat", "lib/env.sh", "lib/release.py", "lib/runtime.py",
        "lib/changelog.py", "lib/version.py") + RUNNABLE


def whats_new(*headings):
    """The guide's What's new, as a page saying HEADINGS ("a0.0.1 — 2
    January 2026", ...) and "Before" the last of them."""
    return "---\ntitle: What changed\n---\n\n" + "".join(
        "## %s\n\nwhat it brought\n\n" % h for h in headings) + \
        "## Before %s\n\nwhat came first\n" % headings[-1].split(" ")[0]


def miniature(version=V):
    """{path: text or bytes}: a Parseh in miniature, as committed."""
    files = {p: "%s\n" % p for p in LEFT_OUT + KEPT}
    for rel, lines in FORMAT_LINES.items():
        files[rel] = files.get(rel, "") + "".join(lines)
    files.update({
        "VERSION": version + "\n",
        "CHANGELOG.md": "## [%s] - 2026-01-02\n### Added\n- all of it\n" % version,
        changelog.GUIDE_PAGE: whats_new("%s — 2 January 2026" % version),
        ".gitattributes": (ROOT / ".gitattributes").read_bytes(),
        ".gitignore": (ROOT / ".gitignore").read_bytes(),
        "environment.yml": (ROOT / "environment.yml").read_bytes(),
        "lib/release.py": (ROOT / "lib" / "release.py").read_bytes(),
        "lib/runtime.py": (ROOT / "lib" / "runtime.py").read_bytes(),
        "lib/changelog.py": (ROOT / "lib" / "changelog.py").read_bytes(),
        "lib/version.py": (ROOT / "lib" / "version.py").read_bytes(),
        "install.sh": "#!/bin/sh\necho install\n",
        # LF in the working tree, and CRLF: git keeps both as LF, and the
        # archive must give both back as CRLF
        "install.bat": "@echo off\necho install\n",
        "serve.bat": b"@echo off\r\necho serve\r\n",
    })
    return files


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=GIT_ENV)
    if r.returncode:
        raise AssertionError("git %s: %s" % (" ".join(args), r.stderr))
    return r.stdout


def make_repo(files, runnable=RUNNABLE, forced=("dist/parseh-old.zip",)):
    """A committed scratch repository holding FILES -> its path.  The
    runnable ones are committed executable whatever the disk can say, and
    the FORCED ones are added past .gitignore."""
    repo = Path(tempfile.mkdtemp(prefix="parseh-release-test-"))
    for rel, body in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body if isinstance(body, bytes) else body.encode("utf-8"))
        p.chmod(0o755 if rel in runnable else 0o644)
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    present = [f for f in forced if f in files]
    if present:
        git(repo, "add", "-f", *present)
    exe = [f for f in runnable if f in files]
    if exe:
        git(repo, "add", "--chmod=+x", *exe)
    git(repo, "commit", "-q", "-m", "the miniature")
    return repo


def run(repo, *args):
    """lib/release.py in REPO, as a developer runs it there."""
    return subprocess.run([sys.executable, "lib/release.py", *args], cwd=str(repo),
                          capture_output=True, text=True, env=GIT_ENV)


def sha(data):
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(HAVE_GIT, "git is not on PATH")
class TheBuild(unittest.TestCase):
    """One miniature, built once; each test reads the zip."""

    @classmethod
    def setUpClass(cls):
        cls.repo = make_repo(miniature())
        cls.r = run(cls.repo, "build")
        cls.dist = cls.repo / "dist"
        cls.zip_path = cls.dist / ("parseh-%s.zip" % V)
        cls.prefix = "parseh-%s/" % V
        cls.commit = git(cls.repo, "rev-parse", "HEAD").strip()
        if cls.r.returncode == 0:
            cls.z = zipfile.ZipFile(cls.zip_path)
            cls.names = cls.z.namelist()
            cls.files = {n[len(cls.prefix):]: cls.z.getinfo(n) for n in cls.names if not n.endswith("/")}
            cls.manifest = json.loads(cls.z.read(cls.prefix + release.MANIFEST))

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "z"):
            cls.z.close()
        shutil.rmtree(cls.repo, ignore_errors=True)

    def setUp(self):
        self.assertEqual(self.r.returncode, 0, self.r.stdout + self.r.stderr)

    def test_it_says_what_it_built(self):
        self.assertIn("Built dist/parseh-%s.zip" % V, self.r.stdout)
        self.assertIn(sha(self.zip_path.read_bytes()), self.r.stdout)
        self.assertNotIn("NOT IN THIS BUILD", self.r.stdout)       # all of it committed

    def test_what_export_ignore_leaves_out_is_not_there(self):
        for rel in LEFT_OUT:
            self.assertNotIn(rel, self.files, rel)
        for folder in ("tests/", ".github/", "dist/"):
            self.assertFalse([n for n in self.names if n.startswith(self.prefix + folder)], folder)

    def test_what_a_release_keeps_is_there(self):
        for rel in KEPT:
            self.assertIn(rel, self.files, rel)
        # every folder Parseh writes into, as a folder of the zip
        for folder in ("books/", "youtube/videos/", "clips/", "exercises/", "config/", "dict/",
                       "markdown/library/"):
            self.assertIn(self.prefix + folder, self.names, folder)

    def test_everything_is_in_one_folder_named_by_the_version(self):
        self.assertTrue(all(n.startswith(self.prefix) for n in self.names))
        self.assertEqual(self.names[0], self.prefix)
        self.assertEqual(self.z.comment.decode(), self.commit)     # as git's own zip has it

    def test_the_bat_files_are_crlf(self):
        # git itself holds them as LF ...
        self.assertEqual(git(self.repo, "show", "HEAD:install.bat"), "@echo off\necho install\n")
        self.assertEqual(git(self.repo, "show", "HEAD:serve.bat"), "@echo off\necho serve\n")
        # ... and the release gives cmd.exe CRLF, and hashes what it gives
        for rel, want in (("install.bat", b"@echo off\r\necho install\r\n"),
                          ("serve.bat", b"@echo off\r\necho serve\r\n")):
            data = self.z.read(self.prefix + rel)
            self.assertEqual(data, want, rel)
            self.assertEqual(self.manifest["files"][rel]["sha256"], sha(want), rel)

    def test_the_modes_are_kept(self):
        for rel, info in self.files.items():
            if rel == release.MANIFEST:
                continue
            want = 0o755 if rel in RUNNABLE else 0o644
            self.assertEqual(info.create_system, 3, rel)             # Unix: unzip applies them
            self.assertEqual((info.external_attr >> 16) & 0o777, want, rel)
            self.assertEqual(self.manifest["files"][rel]["mode"], "%04o" % want, rel)
        folder = self.z.getinfo(self.prefix + "books/")
        self.assertEqual((folder.external_attr >> 16) & 0o777, 0o755)

    def test_the_manifest_hashes_the_bytes_as_archived(self):
        for rel, want in self.manifest["files"].items():
            data = self.z.read(self.prefix + rel)
            self.assertEqual(want["sha256"], sha(data), rel)
            self.assertEqual(want["size"], len(data), rel)

    def test_the_manifests_paths_are_the_zips_files(self):
        self.assertEqual(set(self.manifest["files"]), set(self.files) - {release.MANIFEST})
        self.assertEqual(self.names[-1], self.prefix + release.MANIFEST)

    def test_the_manifest_says_what_the_release_is(self):
        m = self.manifest
        self.assertEqual(m["format"], "parseh-release/1")
        self.assertEqual(m["version"], V)
        self.assertEqual(m["commit"], self.commit)
        self.assertEqual(m["built"], "2026-01-02T03:04:05Z")          # the commit's time
        self.assertEqual(m["data_formats"], version.formats())         # the tree's own formats()
        spec = runtime.env_spec(str(ROOT / "environment.yml"))
        self.assertEqual(m["environment"], {k: dict(v) for k, v in spec.items()})
        self.assertIn("numpy", m["environment"]["pip"])
        self.assertEqual(m["environment"]["conda"]["python"], "python=3.12")

    def test_the_checksum_and_the_manifest_beside_the_zip(self):
        data = self.zip_path.read_bytes()
        self.assertEqual((self.dist / ("parseh-%s.zip.sha256" % V)).read_text(encoding="utf-8"),
                         "%s  parseh-%s.zip\n" % (sha(data), V))
        self.assertEqual((self.dist / ("parseh-%s.manifest.json" % V)).read_bytes(),
                         self.z.read(self.prefix + release.MANIFEST))

    def test_two_builds_of_one_commit_are_the_same(self):
        with tempfile.TemporaryDirectory() as td:
            r = run(self.repo, "build", "--out", td)
            self.assertEqual(r.returncode, 0, r.stderr)
            again = Path(td) / ("parseh-%s.zip" % V)
            with zipfile.ZipFile(again) as z:
                self.assertEqual(json.loads(z.read(self.prefix + release.MANIFEST)), self.manifest)
            # on one machine the zlib is one zlib: the very same bytes
            self.assertEqual(again.read_bytes(), self.zip_path.read_bytes())
            r = run(self.repo, "compare", str(self.zip_path), str(again))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("They agree", r.stdout)
            self.assertIn("byte for byte the same", r.stdout)

    def test_a_windows_git_builds_the_same_release(self):
        # core.autocrlf=true is Git for Windows' default: it would make every
        # text file of an archive CRLF; the builder switches it off
        clone = Path(tempfile.mkdtemp(prefix="parseh-release-test-"))
        try:
            git(clone, "clone", "-q", "--no-local", str(self.repo), "w")
            w = clone / "w"
            git(w, "config", "core.autocrlf", "true")
            git(w, "config", "core.eol", "crlf")
            git(w, "config", "tar.umask", "0077")
            r = run(w, "build", "--out", str(clone / "out"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            got, problems = release.read_manifest(str(clone / "out" / ("parseh-%s.zip" % V)))
            self.assertEqual(problems, [])
            self.assertEqual(got, self.manifest)
        finally:
            shutil.rmtree(clone, ignore_errors=True)

    def test_compare_names_the_file_that_differs(self):
        with tempfile.TemporaryDirectory() as td:
            # the same zip, one file's bytes changed and its manifest not
            bad = Path(td) / "bad.zip"
            with zipfile.ZipFile(bad, "w") as out:
                for info in self.z.infolist():
                    data = self.z.read(info)
                    if info.filename == self.prefix + "serve.py":
                        data += b"# changed\n"
                    copy = zipfile.ZipInfo(info.filename, info.date_time)   # writestr alters
                    copy.external_attr = info.external_attr                 # the one it is given
                    out.writestr(copy, data)
            ok, said = release.compare(str(self.zip_path), str(bad))
            self.assertFalse(ok)
            self.assertIn("bad.zip: serve.py is not the file its manifest hashed", said)
            # the same bytes packed again as a Windows tool packs them: the
            # modes are gone, and install.sh would not run
            (Path(td) / "w").mkdir()
            again = Path(td) / "w" / self.zip_path.name          # the same name, told apart by path
            with zipfile.ZipFile(again, "w") as out:
                for info in self.z.infolist():
                    copy = zipfile.ZipInfo(info.filename, info.date_time)
                    copy.create_system = 0
                    out.writestr(copy, self.z.read(info))
            ok, said = release.compare(str(self.zip_path), str(again))
            self.assertFalse(ok)
            self.assertIn("%s: install.sh has lost the mode its manifest gives it (0755)" % again, said)
            # two manifests: one path's hash moved, one path gone
            other = json.loads(json.dumps(self.manifest))
            other["files"]["serve.py"]["sha256"] = "0" * 64
            del other["files"]["LICENSE"]
            mine, theirs = Path(td) / "mine.json", Path(td) / "theirs.json"
            mine.write_text(json.dumps(self.manifest), encoding="utf-8")
            theirs.write_text(json.dumps(other), encoding="utf-8")
            r = run(self.repo, "compare", str(mine), str(theirs))
            self.assertEqual(r.returncode, 1)
            self.assertIn("not the same file: serve.py", r.stdout)
            self.assertIn("only in mine.json: LICENSE", r.stdout)


@unittest.skipUnless(HAVE_GIT, "git is not on PATH")
class WhatABuildRefuses(unittest.TestCase):
    def refused(self, files, said, forced=("dist/parseh-old.zip",), runnable=RUNNABLE):
        repo = make_repo(files, runnable=runnable, forced=forced)
        try:
            r = run(repo, "build")
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn(said, r.stderr)
            self.assertEqual([p.name for p in (repo / "dist").iterdir()], ["parseh-old.zip"],
                             "a refused build writes nothing")
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_a_folder_parseh_writes_into_left_out(self):
        files = miniature()
        files[".gitattributes"] += b"/clips/README.md export-ignore\n"
        self.refused(files, "clips/ is missing: git archive keeps no empty folder")

    def test_content_or_settings_committed(self):
        files = miniature()
        files["books/persian/my-book/main.tex"] = "\\chapter{mine}\n"
        self.refused(files, "books/persian/my-book/main.tex is somebody's content")
        files = miniature()
        files["config/prefs.json"] = "{}\n"
        self.refused(files, "config/prefs.json is somebody's content or settings",
                     forced=("dist/parseh-old.zip", "config/prefs.json"))
        files = miniature()
        files[".tls/key.pem"] = "secret\n"
        self.refused(files, ".tls/key.pem must never ship",
                     forced=("dist/parseh-old.zip", ".tls/key.pem"))

    def test_a_bat_with_bare_lf(self):
        files = miniature()
        files[".gitattributes"] = files[".gitattributes"].replace(b"*.bat text eol=crlf", b"")
        self.refused(files, "install.bat has bare LF line endings")

    def test_a_launcher_that_lost_its_executable_bit(self):
        self.refused(miniature(), "install.sh is not executable",
                     runnable=tuple(r for r in RUNNABLE if r != "install.sh"))

    def test_no_version(self):
        files = miniature()
        del files["VERSION"]
        self.refused(files, "has no VERSION file")
        files = miniature()
        files["VERSION"] = "the next one\n"
        self.refused(files, "'the next one' is not a version")
        # nor a rehearsal's name, which is a tag's alone
        files = miniature()
        files["VERSION"] = V + "-rc1\n"
        self.refused(files, "a rehearsal's name")

    def test_a_tree_that_cannot_say_its_data_formats(self):
        files = miniature()
        files["lib/clips.py"] = "INFO_FORMAT = 'one'\n"
        self.refused(files, "could not say its data formats")


@unittest.skipUnless(HAVE_GIT, "git is not on PATH")
class WhatABuildSays(unittest.TestCase):
    def test_work_not_committed_is_named(self):
        repo = make_repo(miniature())
        try:
            (repo / "serve.py").write_text("changed\n", encoding="utf-8")
            (repo / "lib" / "brand_new.py").write_text("new\n", encoding="utf-8")
            r = run(repo, "build")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("NOT IN THIS BUILD", r.stdout)
            self.assertIn("changed  serve.py", r.stdout)
            self.assertIn("new  lib/brand_new.py", r.stdout)
            # and indeed not in it
            with zipfile.ZipFile(repo / "dist" / ("parseh-%s.zip" % V)) as z:
                self.assertEqual(z.read("parseh-%s/serve.py" % V),
                                 miniature()["serve.py"].encode("utf-8"))
                self.assertNotIn("parseh-%s/lib/brand_new.py" % V, z.namelist())
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_a_ref_builds_that_commit(self):
        repo = make_repo(miniature())
        try:
            first = git(repo, "rev-parse", "HEAD").strip()
            git(repo, "tag", V)
            files = miniature("a0.0.2")
            for rel in ("VERSION", "CHANGELOG.md"):
                (repo / rel).write_text(files[rel], encoding="utf-8")
            git(repo, "commit", "-q", "-am", "the next")
            r = run(repo, "build", "--ref", V)
            self.assertEqual(r.returncode, 0, r.stderr)
            got, problems = release.read_manifest(str(repo / "dist" / ("parseh-%s.zip" % V)))
            self.assertEqual((got["version"], got["commit"], problems), (V, first, []))
            r = run(repo, "build")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((repo / "dist" / "parseh-a0.0.2.zip").is_file())
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_a_rehearsal_is_built_under_its_tag(self):
        # the owner, 2026-09-25: parseh-aX.Y.Z-rcN.zip, whose manifest carries
        # the tag as its version -- the same files as the version's own build
        rc = V + "-rc1"
        repo = make_repo(miniature())
        try:
            r = run(repo, "build", "--tag", rc)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("Built dist/parseh-%s.zip" % rc, r.stdout)
            self.assertIn("A rehearsal of %s: its manifest says %s" % (V, rc), r.stdout)
            dist = repo / "dist"
            got, problems = release.read_manifest(str(dist / ("parseh-%s.zip" % rc)))
            self.assertEqual((got["version"], problems), (rc, []))
            with zipfile.ZipFile(dist / ("parseh-%s.zip" % rc)) as z:
                self.assertTrue(all(n.startswith("parseh-%s/" % rc) for n in z.namelist()))
                # the program inside still says the version it rehearses
                self.assertEqual(z.read("parseh-%s/VERSION" % rc), (V + "\n").encode("ascii"))
            data = (dist / ("parseh-%s.zip" % rc)).read_bytes()
            self.assertEqual((dist / ("parseh-%s.zip.sha256" % rc)).read_text(encoding="utf-8"),
                             "%s  parseh-%s.zip\n" % (sha(data), rc))
            self.assertEqual(json.loads((dist / ("parseh-%s.manifest.json" % rc)).read_text(
                encoding="utf-8")), got)
            # the version's own tag names it as VERSION does, and ships the
            # very same files
            r = run(repo, "build", "--tag", "refs/tags/" + V)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotIn("rehearsal", r.stdout)
            mine, problems = release.read_manifest(str(dist / ("parseh-%s.zip" % V)))
            self.assertEqual((mine["version"], problems), (V, []))
            self.assertEqual(mine["files"], got["files"])
            self.assertEqual({k: v for k, v in mine.items() if k != "version"},
                             {k: v for k, v in got.items() if k != "version"})
            # a tag that is not this version's, or no version's, builds nothing
            for tag, said in (("a0.0.2-rc1", "the tag a0.0.2-rc1 rehearses a0.0.2, but VERSION "
                                             "says %s" % V),
                              ("a0.0.2", "the tag is a0.0.2, but VERSION says %s" % V),
                              (V + "-rc0", "is not a version's")):
                r = run(repo, "build", "--tag", tag, "--out", str(repo / "other"))
                self.assertEqual(r.returncode, 1, tag)
                self.assertIn(said, r.stderr)
                self.assertFalse((repo / "other").exists(), tag)
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_the_workflow_s_own_commands_for_a_rehearsal(self):
        # what release.yml runs, in the order it runs it, on a rehearsal's
        # tag: the headings may still be undated
        repo = make_repo(miniature())
        try:
            (repo / "CHANGELOG.md").write_text("## [%s] - unreleased\n### Added\n- all of it\n" % V,
                                               encoding="utf-8")
            (repo / changelog.GUIDE_PAGE).write_text(whats_new("%s — not yet released" % V),
                                                     encoding="utf-8")
            git(repo, "commit", "-q", "-am", "not yet released")
            rc = V + "-rc2"
            r = run(repo, "check", rc)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("%s rehearses %s" % (rc, V), r.stdout)
            r = run(repo, "notes", rc)
            self.assertEqual((r.returncode, r.stdout), (0, "### Added\n- all of it\n"))
            r = run(repo, "prerelease", "refs/tags/" + rc)
            self.assertEqual((r.returncode, r.stdout), (0, "true\n"))
            # and the version's own tag is refused until both are dated
            r = run(repo, "check", V)
            self.assertEqual(r.returncode, 1)
            self.assertIn("still says 'unreleased'", r.stderr)
            self.assertIn("the guide's What's new still says '%s — not yet released'" % V, r.stderr)
            r = run(repo, "prerelease", V)
            self.assertEqual((r.returncode, r.stdout), (0, "false\n"))
            r = run(repo, "prerelease", "not-a-version")
            self.assertEqual(r.returncode, 1)
            self.assertIn("is not a version's", r.stderr)
        finally:
            shutil.rmtree(repo, ignore_errors=True)


class TheChangelog(unittest.TestCase):
    TEXT = ("## [a0.0.2] - unreleased\n### Added\n- the next\n\n"
            "## [a0.0.1] - 2026-01-02\n### Added\n- the first\n### Fixed\n- a bug\n\n"
            "## [a0.0.0] - 2025-12-31\n- the start\n")

    @staticmethod
    def page_for(text):
        """The guide's What's new saying what the changelog TEXT says -- the
        same versions on the same days -- or None when TEXT is no changelog."""
        try:
            sections = changelog.parse(text)
        except changelog.ChangelogError:
            return None
        return whats_new(*("%s — %s" % (s.version, changelog.said(s.date)) for s in sections))

    def tree(self, version, text, page=None):
        """A scratch tree of VERSION, CHANGELOG.md TEXT and the guide's What's
        new: PAGE, or one that agrees with TEXT (None), or none at all (False)."""
        td = tempfile.mkdtemp(prefix="parseh-release-test-")
        self.addCleanup(shutil.rmtree, td, True)
        Path(td, "VERSION").write_text(version + "\n", encoding="utf-8")
        Path(td, "CHANGELOG.md").write_text(text, encoding="utf-8")
        page = self.page_for(text) if page is None else page
        if page:
            dest = Path(td, *changelog.GUIDE_PAGE.split("/"))
            dest.parent.mkdir(parents=True)
            dest.write_text(page, encoding="utf-8")
        return td

    def test_the_notes_are_that_section_alone(self):
        # read by lib/changelog.py, the one reader, and given word for word
        root = self.tree("a0.0.1", self.TEXT)
        self.assertEqual(release.notes("a0.0.1", root=root), "### Added\n- the first\n### Fixed\n- a bug\n")
        self.assertEqual(release.notes("a0.0.0", root=root), "- the start\n")
        with self.assertRaisesRegex(release.Refused, "no section for a9.9.9"):
            release.notes("a9.9.9", root=root)

    def test_check_agrees_when_all_three_agree(self):
        root = self.tree("a0.0.1", self.TEXT.split("\n\n", 1)[1])
        self.assertEqual(release.check("a0.0.1", root=root), "a0.0.1")
        self.assertEqual(release.check("refs/tags/a0.0.1", root=root), "a0.0.1")

    def test_check_refuses_unreleased(self):
        root = self.tree("a0.0.2", self.TEXT)
        with self.assertRaisesRegex(release.Refused, "still says 'unreleased'"):
            release.check("a0.0.2", root=root)
        # and a heading spelt some other way is no heading the reader guesses at
        for said in ("Unreleased", "soon", "2026-02-30"):
            with self.subTest(said=said):
                with self.assertRaises(release.Refused):
                    release.check("a0.0.2", root=self.tree("a0.0.2", self.TEXT.replace("unreleased", said)))

    def test_check_refuses_any_disagreement(self):
        dated = self.TEXT.replace("unreleased", "2026-02-03")
        cases = (("a0.0.3", "a0.0.2", dated, "the tag is a0.0.3, but VERSION says a0.0.2"),
                 ("a0.0.1", "a0.0.1", dated, "newest section is a0.0.2, but VERSION says a0.0.1"),
                 ("a0.0.2", "a0.0.2", "no headings\n", "has no version's heading"),
                 ("a0.0.2", "a0.0.2", dated.replace("- the next\n", ""), "section is empty"),
                 ("a0.0.2", "a0.0.2", dated + "## [a0.0.1] - 2025-01-01\n- again\n",
                  "a0.0.1 has a section already"))
        for tag, version, text, said in cases:
            with self.subTest(said=said):
                with self.assertRaises(release.Refused) as cm:
                    release.check(tag, root=self.tree(version, text))
                self.assertIn(said, str(cm.exception))
        # and every disagreement at once, not the first alone
        with self.assertRaises(release.Refused) as cm:
            release.check("a0.0.3", root=self.tree("a0.0.1", self.TEXT))
        for said in ("the tag is a0.0.3", "newest section is a0.0.2", "still says 'unreleased'"):
            self.assertIn(said, str(cm.exception))

    def test_the_notes_of_a_rehearsal_are_its_version_s(self):
        root = self.tree("a0.0.2", self.TEXT)
        self.assertEqual(release.notes("a0.0.2-rc1", root=root), "### Added\n- the next\n")
        self.assertEqual(release.notes("refs/tags/a0.0.2-rc3", root=root), "### Added\n- the next\n")

    def test_a_rehearsal_passes_before_the_day_is_written(self):
        # the owner, 2026-09-25: VERSION and the headings say a0.0.2, still
        # "unreleased", and a0.0.2-rcN is the tag it is rehearsed under
        root = self.tree("a0.0.2", self.TEXT)
        self.assertEqual(release.check("a0.0.2-rc1", root=root), "a0.0.2")
        self.assertEqual(release.check("refs/tags/a0.0.2-rc12", root=root), "a0.0.2")
        # and once the day is written, too
        dated = self.tree("a0.0.2", self.TEXT.replace("unreleased", "2026-02-03"))
        self.assertEqual(release.check("a0.0.2-rc2", root=dated), "a0.0.2")
        self.assertEqual(release.check("a0.0.2", root=dated), "a0.0.2")
        # while the version's own tag waits for the day
        with self.assertRaisesRegex(release.Refused, "still says 'unreleased'"):
            release.check("a0.0.2", root=root)

    def test_a_rehearsal_is_held_to_everything_but_the_day(self):
        without = whats_new("a0.0.1 — 2 January 2026", "a0.0.0 — 31 December 2025")
        cases = (("a0.0.3-rc1", "a0.0.2", self.TEXT, None,
                  "the tag a0.0.3-rc1 rehearses a0.0.3, but VERSION says a0.0.2"),
                 ("a0.0.1-rc1", "a0.0.1", self.TEXT, None,
                  "newest section is a0.0.2, but VERSION says a0.0.1"),
                 ("a0.0.2-rc1", "a0.0.2", self.TEXT.replace("- the next\n", ""), None,
                  "section is empty"),
                 ("a0.0.2-rc0", "a0.0.2", self.TEXT, None, "the tag a0.0.2-rc0 is not a version's"),
                 ("a0.0.2rc1", "a0.0.2", self.TEXT, None, "the tag a0.0.2rc1 is not a version's"),
                 ("a0.0.2-rc1", "a0.0.2", self.TEXT, without,
                  "the guide's What's new (%s) has no heading for a0.0.2" % changelog.GUIDE_PAGE),
                 ("a0.0.2-rc1", "a0.0.2", self.TEXT, False,
                  "has no %s, the guide's What's new" % changelog.GUIDE_PAGE),
                 ("a0.0.2-rc1", "a0.0.2", self.TEXT.replace("[a0.0.2]", "[a0.0.2-rc1]"), None,
                  "a0.0.2-rc1 is a rehearsal's name"))
        for tag, v, text, page, said in cases:
            with self.subTest(said=said):
                with self.assertRaises(release.Refused) as cm:
                    release.check(tag, root=self.tree(v, text, page))
                self.assertIn(said, str(cm.exception))
        # VERSION itself never names a rehearsal
        with self.assertRaisesRegex(release.Refused, "a rehearsal's name"):
            release.check("a0.0.2-rc1", root=self.tree("a0.0.2-rc1", self.TEXT))

    def test_the_guide_s_day_is_held_for_a_version_s_tag(self):
        # the owner, 2026-09-25: CI runs no test, so the release check itself
        # refuses a guide that still says "not yet released" -- or another
        # day than the changelog's
        dated = self.TEXT.replace("unreleased", "2026-02-03")
        root = self.tree("a0.0.2", dated, page=self.page_for(self.TEXT))
        with self.assertRaises(release.Refused) as cm:
            release.check("a0.0.2", root=root)
        said = str(cm.exception)
        self.assertIn("the guide's What's new still says 'a0.0.2 — not yet released' (%s:5)"
                      % changelog.GUIDE_PAGE, said)
        self.assertNotIn("CHANGELOG.md's a0.0.2 section", said)          # that one is dated
        self.assertEqual(release.check("a0.0.2-rc1", root=root), "a0.0.2")  # a rehearsal may
        root = self.tree("a0.0.2", dated,
                         page=self.page_for(dated).replace("3 February 2026", "4 February 2026"))
        with self.assertRaises(release.Refused) as cm:
            release.check("a0.0.2", root=root)
        self.assertIn("the guide's What's new says a0.0.2 was released on 4 February 2026", str(cm.exception))
        self.assertIn("and CHANGELOG.md says 2026-02-03", str(cm.exception))
        # a heading the reader cannot read is refused, not skipped
        root = self.tree("a0.0.2", dated,
                         page=self.page_for(dated).replace("3 February 2026", "3 Feb 2026"))
        with self.assertRaisesRegex(release.Refused, "neither a day as the guide writes one"):
            release.check("a0.0.2", root=root)

    def test_what_a_tag_is_marked_on_github(self):
        self.assertEqual(release.prerelease("a0.3.2-rc1"), "true")
        self.assertEqual(release.prerelease("refs/tags/a0.3.2-rc10"), "true")
        self.assertEqual(release.prerelease("a0.3.2"), "false")
        self.assertEqual(release.prerelease("refs/tags/b1.0"), "false")
        for bad in ("v0.3.2", "a0.3.2-rc", "latest", ""):
            with self.assertRaisesRegex(release.Refused, "is not a version's"):
                release.prerelease(bad)

    @unittest.skipUnless(HAVE_GIT, "git is not on PATH")
    def test_check_reads_a_commit_when_asked(self):
        repo = make_repo(miniature())
        try:
            (repo / "VERSION").write_text("a0.0.9\n", encoding="utf-8")      # not committed
            r = run(repo, "check", V, "--ref", "HEAD")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("all say %s" % V, r.stdout)
            r = run(repo, "check", V)
            self.assertEqual(r.returncode, 1)
            self.assertIn("the tag is %s, but VERSION says a0.0.9" % V, r.stderr)
        finally:
            shutil.rmtree(repo, ignore_errors=True)


class TheGuideCheck(unittest.TestCase):
    """`release.py guide`, in a scratch copy of what a compile of the guide
    reads: the guide's engine, a page of its own, and the studio's files the
    engine names (html-guide/engine/manifest.py).  The compile's own record,
    site/build.json, is written with the hash the Parseh server's own rule
    gives (lib/guidebuild.py, which the guide's front page asks before it
    offers "Compile the guide"), so the check is held to that rule and not
    to itself."""

    def setUp(self):
        import importlib.util
        self.root = Path(tempfile.mkdtemp(prefix="parseh-release-test-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.guide = self.root / "html-guide"
        shutil.copytree(ROOT / "html-guide" / "engine", self.guide / "engine",
                        ignore=shutil.ignore_patterns("__pycache__", "vendor"))
        spec = importlib.util.spec_from_file_location(
            "parseh_test_guide_manifest", str(ROOT / "html-guide" / "engine" / "manifest.py"))
        manifest = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(manifest)                 # plain data, nothing imported
        for rel in manifest.MODULE_FILES + manifest.RUNTIME_FILES:
            if (ROOT / rel).is_file():
                (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / rel, self.root / rel)
        self.page = self.guide / "markdown" / "reference" / "whats-new.md"
        self.page.parent.mkdir(parents=True)
        self.page.write_text(whats_new("a0.0.1 — not yet released"), encoding="utf-8")
        (self.guide / "markdown" / "shot.png").write_bytes(b"\x89PNG\r\n\x1a\n a picture")
        self.compiled()

    def server(self, ask):
        """lib/guidebuild.py's answer about the scratch guide, from a Python of
        its own: it keeps the engine it loaded first for the life of a
        process, and this one must load the scratch copy's."""
        r = subprocess.run([sys.executable, "-B", "-c",
                            "import json, sys; sys.path.insert(0, sys.argv[1]); import guidebuild; "
                            "g = sys.argv[2]; print(json.dumps(%s))" % ask,
                            str(ROOT / "lib"), str(self.guide)],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def compiled(self, **info):
        """site/build.json as a compile of the scratch guide would write it."""
        (self.guide / "site").mkdir(exist_ok=True)
        (self.guide / "site" / "nav.js").write_text("// the compiled site\n", encoding="utf-8")
        record = {"engine": 1, "errors": 0, "fingerprint": self.server("guidebuild._fingerprint(g)"),
                  "pages": 1, "warnings": 0}
        record.update(info)
        (self.guide / "site" / "build.json").write_text(json.dumps(record), encoding="utf-8")

    def stale(self):
        return self.server("guidebuild.status(g)['stale']")

    def refused(self, said, ref=None):
        with self.assertRaises(release.Refused) as cm:
            release.guide(ref, root=str(self.root))
        self.assertIn(said, str(cm.exception))
        self.assertIn("compile the guide", str(cm.exception))        # and what to do
        return str(cm.exception)

    def test_in_step_it_passes(self):
        self.assertFalse(self.stale())
        self.assertEqual(release.guide(root=str(self.root))["pages"], 1)

    def test_a_page_changed_after_the_compile_is_refused(self):
        self.page.write_text(whats_new("a0.0.1 — 2 January 2026"), encoding="utf-8")
        self.assertTrue(self.stale())
        said = self.refused("the compiled guide (html-guide/site/) is not what the working "
                            "tree's sources compile to")
        self.assertTrue(said.startswith("Not in step: "))
        # compiled again, it passes again
        self.compiled()
        release.guide(root=str(self.root))

    def test_every_kind_of_source_counts(self):
        for rel, change in (("html-guide/markdown/shot.png", b"another picture"),
                            ("html-guide/engine/render.py", b"# the engine\n"),
                            ("markdown/app/htmlgen.py", b"# the studio's renderer\n"),
                            ("html-guide/markdown/new-page.md", b"---\ntitle: New\n---\n")):
            with self.subTest(rel=rel):
                path = self.root / rel
                was = path.read_bytes() if path.exists() else None
                with open(path, "ab") as f:
                    f.write(change)
                self.assertTrue(self.stale())
                self.refused("is not what the working tree's sources compile to")
                if was is None:
                    path.unlink()
                else:
                    path.write_bytes(was)
                release.guide(root=str(self.root))

    def test_a_compile_with_errors_or_none_at_all_is_refused(self):
        self.compiled(errors=2)
        self.refused("its last compile had 2 error(s)")
        (self.guide / "site" / "build.json").unlink()
        self.refused("the working tree has no compiled guide (html-guide/site/build.json is missing)")
        (self.guide / "site" / "build.json").write_text("{half", encoding="utf-8")
        self.refused("cannot be read")

    @unittest.skipUnless(HAVE_GIT, "git is not on PATH")
    def test_a_commit_is_asked_about_as_committed(self):
        git(self.root, "init", "-q")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "compiled")
        self.page.write_text(whats_new("a0.0.1 — 2 January 2026"), encoding="utf-8")   # not committed
        self.refused("is not what the working tree's sources compile to")
        self.assertEqual(release.guide("HEAD", root=str(self.root))["pages"], 1)
        git(self.root, "commit", "-q", "-am", "the page, not compiled")
        commit = git(self.root, "rev-parse", "HEAD").strip()
        self.refused("is not what the commit %s's sources compile to" % commit[:12], ref="HEAD")


class WhatTheCheckoutSays(unittest.TestCase):
    def test_gitattributes_leaves_out_the_owners_list(self):
        rules = {}
        for line in (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                path, *attrs = line.split()
                rules[path] = attrs
        for path in ("/tests", "/docs/*.gif", "/.github", "/.gitattributes", "/.gitignore",
                     "/.nojekyll", "/index.html", "/lib/icons/make.mjs",
                     "/youtube/docs/glossary-ci-stories.md", "/lib/wavealign_lab.py",
                     "/youtube/.gitignore", "/youtube/serve.py", "/youtube/serve.sh", "/dist"):
            self.assertEqual(rules.get(path), ["export-ignore"], path)
        self.assertEqual(rules.get("*.bat"), ["text", "eol=crlf"])

    @unittest.skipUnless(HAVE_GIT, "git is not on PATH")
    def test_git_reads_it_so(self):
        # asked of git itself, against this checkout's .gitattributes.  A
        # folder's rule is the folder's alone (git archive leaves out the
        # folder, and so all of it; check-attr on a file inside it says
        # "unspecified"), so it is the folders that are asked
        def ignored(*paths):
            out = git(ROOT, "check-attr", "export-ignore", "--", *paths)
            return {line.split(": ")[0]: line.split(": ")[-1] for line in out.splitlines()}
        out = ignored("tests", "docs/demo-books.gif", ".github", "dist", "youtube/serve.sh")
        self.assertEqual(set(out.values()) - {"set"}, set(), out)
        never = ("clips/README.md", "exercises/README.md", "config/.gitkeep", "dict/.gitkeep",
                 "books/persian/.gitkeep", "youtube/videos/persian/.gitkeep",
                 "markdown/library/persian/.gitkeep", "html-guide/site", "html-guide/site/index.html",
                 "docs/lang", "docs/mobile.md", "lib/fonts/OFL.txt", "LICENSE", "environment.yml",
                 "lib/mathjax", "html-guide/site/images/flashcard.gif")
        out = ignored(*never)
        self.assertEqual(set(out.values()), {"unspecified"}, out)

    def test_dist_is_ignored(self):
        self.assertIn("/dist/", (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())

    def test_this_checkout_can_say_its_formats_with_a_bare_python(self):
        # what CI's bare Python will be asked of the archived tree: the data
        # formats (lib/version.formats) and the environment, by the tree's
        # own code, with the standard library alone
        said = release.describe(str(ROOT))
        self.assertTrue(said["data_formats"])
        self.assertEqual(said["environment"],
                         {k: dict(v) for k, v in runtime.env_spec().items()})


class TheWorkflow(unittest.TestCase):
    WF = ROOT / ".github" / "workflows" / "release.yml"

    def setUp(self):
        self.wf = self.WF.read_text(encoding="utf-8")

    def runs(self):
        """Every job's steps, in order, each as its text.  A job's steps end
        where a line at the jobs' own depth begins (two spaces: the next
        job, or a comment before it), so no step runs on into the next job's
        header."""
        steps = []
        for part in self.wf.split("\n    steps:\n")[1:]:
            body = re.split(r"(?m)^(?=  ?\S)", part, maxsplit=1)[0]
            steps += re.split(r"(?m)^      - ", body)[1:]
        return steps

    def test_a_tag_or_a_hand_makes_it_run(self):
        self.assertRegex(self.wf, r"(?m)^on:\n  push:\n    tags: \[\"\*\"\]\n  workflow_dispatch:\n"
                                  r"    inputs:\n      tag:\n")
        self.assertRegex(self.wf, r"(?m)^permissions:\n  contents: write\n\n")
        self.assertNotRegex(self.wf, r"(?m)^\s+(pages|id-token|actions|packages): write")

    def test_it_checks_then_builds_then_makes_a_draft(self):
        steps = self.runs()
        order = [next((i for i, s in enumerate(steps) if said in s), None)
                 for said in ("actions/checkout@v4", "actions/setup-python@v5",
                              'python3 lib/release.py check "$TAG"',
                              "python3 lib/release.py guide",
                              'python3 lib/release.py build --tag "$TAG" --out dist',
                              'python3 lib/release.py notes "$TAG" > dist/notes.md',
                              'python3 lib/release.py prerelease "$TAG"',
                              'releases/tags/$TAG', "select(.draft and", "gh release create")]
        self.assertNotIn(None, order, order)
        self.assertEqual(order, sorted(order))
        self.assertEqual(len(set(order)), len(order), "one step each")
        create = steps[order[-1]]
        for said in ('"dist/parseh-$TAG.zip"', '"dist/parseh-$TAG.zip.sha256"', "--draft",
                     '--prerelease="$PRERELEASE"', "--verify-tag", "--notes-file dist/notes.md"):
            self.assertIn(said, create)
        # the one rule for what a rehearsal is decides, never a pattern here;
        # the second flag is the guard's, which only ever takes the mark off
        self.assertEqual(re.findall(r"--prerelease\S*", self.wf),
                         ['--prerelease="$PRERELEASE"', "--prerelease=false"])
        self.assertIn('echo "PRERELEASE=$prerelease" >> "$GITHUB_ENV"', steps[order[6]])
        self.assertNotRegex(self.wf.split("\n    steps:\n", 1)[1], r"-rc|\*rc|rc\*")
        self.assertIn("exit 1", steps[order[7]])          # a published release stops it

    def test_the_guide_check_only_and_no_test_suite(self):
        # the owner, 2026-09-25: the suites run on the developer's machine
        for step in self.runs():
            self.assertNotRegex(step, r"unittest|pytest|tests/|\.mjs|deno|playwright", step)

    def step(self, said):
        """The script of the step whose run: says SAID, as bash is given it:
        a literal block (|) line by line, a folded one (>-) as one line."""
        step = next(s for s in self.runs() if said in s)
        head, body = step.split("run:", 1)
        style, _, block = body.partition("\n")
        # the block is what is indented under `run:` (ten spaces); a comment
        # at the steps' own depth belongs to the step after
        lines = [line.strip() for line in block.split("\n")
                 if line.startswith(" " * 10) and line.strip()]
        self.assertIn(style.strip(), ("|", ">-"), "a run: block, literal or folded")
        return "\n".join(lines) if style.strip() == "|" else " ".join(lines)

    def bash(self, script, **env):
        return subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", script],
                              cwd=str(ROOT), capture_output=True, text=True,
                              env=dict(os.environ, **env), timeout=120)

    @unittest.skipUnless(shutil.which("bash"), "bash is not on PATH")
    def test_the_draft_is_a_prerelease_for_a_rehearsal_and_not_for_a_version(self):
        # the workflow's own two steps, run as the runner runs them (bash -eo
        # pipefail), with a stand-in gh that writes down what it was asked
        kind = self.step("release.py prerelease")
        create = self.step("gh release create")
        with tempfile.TemporaryDirectory() as td:
            gh = Path(td, "gh")
            gh.write_text('#!/bin/sh\nfor a in "$@"; do printf "%s\\n" "$a"; done > "$GH_SAID"\n',
                          encoding="utf-8")
            gh.chmod(0o755)
            for tag, want in (("a0.3.2-rc1", "true"), ("refs/tags/a0.3.2-rc2", "true"),
                              ("a0.3.2", "false"), ("b1.0", "false")):
                with self.subTest(tag=tag):
                    envfile, said = Path(td, "env"), Path(td, "said")
                    envfile.write_text("", encoding="utf-8")
                    r = self.bash(kind, TAG=tag, GITHUB_ENV=str(envfile))
                    self.assertEqual(r.returncode, 0, r.stderr)
                    self.assertEqual(envfile.read_text(encoding="utf-8"), "PRERELEASE=%s\n" % want)
                    r = self.bash(create, TAG=tag, PRERELEASE=want, GH_SAID=str(said),
                                  PATH=td + os.pathsep + os.environ["PATH"])
                    self.assertEqual(r.returncode, 0, r.stderr)
                    args = said.read_text(encoding="utf-8").split("\n")
                    self.assertIn("--prerelease=%s" % want, args)
                    self.assertIn("--draft", args)
                    self.assertIn("dist/parseh-%s.zip" % tag, args)
            # a tag that is no version's fails the step, and says nothing
            envfile.write_text("", encoding="utf-8")
            r = self.bash(kind, TAG="latest", GITHUB_ENV=str(envfile))
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("is not a version's", r.stderr)
            self.assertEqual(envfile.read_text(encoding="utf-8"), "")

    def test_a_published_release_wakes_only_the_guard(self):
        # the owner, 2026-09-25: a version is published as a FULL release;
        # the guard runs when one is published, the builder never does then
        self.assertRegex(self.wf, r"(?m)^  release:\n    types: \[published\]\n")
        self.assertRegex(self.wf, r"(?m)^  release:\n    # [^\n]*\n    if: github\.event_name != 'release'\n")
        self.assertRegex(self.wf, r"(?m)^  full-release:\n    if: github\.event_name == 'release'\n")
        guard = self.wf.split("\n  full-release:\n", 1)[1]
        self.assertIn("TAG: ${{ github.event.release.tag_name }}", guard)
        self.assertIn("MARKED: ${{ github.event.release.prerelease }}", guard)
        self.assertIn('python3 lib/release.py prerelease "$TAG"', guard)
        # it may take the mark off, and nothing else: never delete, never mark
        self.assertNotRegex(guard, r"DELETE|release delete|--prerelease=true|--draft")

    @unittest.skipUnless(shutil.which("bash"), "bash is not on PATH")
    def test_the_guard_takes_the_mark_off_a_version_and_only_a_version(self):
        guard = self.step("gh release edit")
        with tempfile.TemporaryDirectory() as td:
            gh = Path(td, "gh")
            gh.write_text('#!/bin/sh\nfor a in "$@"; do printf "%s\\n" "$a"; done > "$GH_SAID"\n',
                          encoding="utf-8")
            gh.chmod(0o755)
            for tag, marked, edits in (("a0.3.2", "true", True), ("a0.3.2", "false", False),
                                       ("a0.3.2-rc1", "true", False), ("b1.0", "true", True)):
                with self.subTest(tag=tag, marked=marked):
                    said = Path(td, "said")
                    if said.exists():
                        said.unlink()
                    r = self.bash(guard, TAG=tag, MARKED=marked, GH_SAID=str(said),
                                  PATH=td + os.pathsep + os.environ["PATH"])
                    self.assertEqual(r.returncode, 0, r.stderr)
                    self.assertEqual(said.exists(), edits, r.stdout)
                    if edits:
                        self.assertEqual(said.read_text(encoding="utf-8").split("\n")[:5],
                                         ["release", "edit", tag, "--prerelease=false", "--latest"])
                        self.assertIn("the mark is taken off", r.stdout)

    def test_the_tag_never_reaches_a_script_as_an_expression(self):
        # ${{ }} in a run: is a script-injection door: the tag goes by $TAG
        for step in self.runs():
            if "run:" in step:
                self.assertNotIn("${{", step.split("run:", 1)[1], step)

    def test_it_is_in_the_house_style_and_names_no_version(self):
        self.assertTrue(self.wf.startswith("# "))
        header = self.wf.split("\nname:", 1)[0]
        for said in ("DRAFT", "docs/releasing.md", "lib/release.py", "Source code",
                     "A REHEARSAL IS A PRERELEASE, A VERSION IS NOT", "THE GUIDE CHECK ONLY"):
            self.assertIn(said, header)
        for uses in re.findall(r"uses: (\S+)", self.wf):
            self.assertRegex(uses, r"^actions/[a-z-]+@v\d+$")
        self.assertIsNone(re.search(r"\b[ab]?\d+\.\d+\.\d+\b", self.wf))

    def test_the_yaml_itself(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML is not installed; the shape is held above as text")
        doc = yaml.safe_load(self.wf)
        self.assertEqual(doc[True]["push"]["tags"], ["*"])          # `on:` reads as True
        self.assertIn("workflow_dispatch", doc[True])
        self.assertEqual(doc["permissions"], {"contents": "write"})
        job = doc["jobs"]["release"]
        self.assertEqual(job["env"]["TAG"], "${{ inputs.tag || github.ref_name }}")
        self.assertEqual(doc[True]["release"], {"types": ["published"]})
        self.assertEqual(job["if"], "github.event_name != 'release'")
        self.assertEqual(doc["jobs"]["full-release"]["if"], "github.event_name == 'release'")


if __name__ == "__main__":
    unittest.main()
