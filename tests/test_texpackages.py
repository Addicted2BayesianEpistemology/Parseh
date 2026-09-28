# SPDX-License-Identifier: GPL-3.0-or-later
"""TeX packages got from Settings -> LaTeX drawings (lib/texpackages.py): what a
failed run says, and what a removal leaves behind.  No TeX is run and nothing
is fetched: tlmgr's own words are fed in, and the folder is a temporary one.

Found by driving the real page on 2026-09-25: a package that could not be got
said only tlmgr's last line, "An error has occurred. See above messages.
Exiting." (nothing is above it on the page), and a package that was removed
went on being listed as "installed" beneath a table that no longer held it."""
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "lib") not in sys.path:
    sys.path.insert(0, str(ROOT / "lib"))

import texpackages  # noqa: E402

# what tlmgr printed, run by hand on 2026-09-25 (TeX Live 2025 on Debian), for a
# package its historic repository does not have
NOT_THERE = """TeX Live 2025 is frozen
and will no longer be routinely updated.  This happens when a new
release is made, or will be made shortly.

tlmgr install: package nosuchpackage not present in repository.
tlmgr: action install returned an error; continuing.
tlmgr: package repository https://ftp.math.utah.edu/pub/tex/historic/systems/texlive/2025/tlnet-final (not verified: valid signature with expired key)
tlmgr: An error has occurred. See above messages. Exiting.
""".splitlines()

# and for the main repository, which is a year ahead
OTHER_YEAR = """Local TeX Live (2025) is older than remote repository (2026).
Cross release updates are only supported with
  update-tlmgr-latest(.sh/.exe) --update
See https://tug.org/texlive/upgrade.html for details.
tlmgr: An error has occurred. See above messages. Exiting.
""".splitlines()

# a run that fails with nothing that says why
MUTE = ["tlmgr: An error has occurred. See above messages. Exiting."]


def feed(lines):
    """A stand-in for _stream: the lines go through _progress, as they do, and the run fails."""
    def stream(job, name, cmd):
        for line in lines:
            texpackages._progress(job, line + "\n")
        return False
    return stream


class WhyItFailed(unittest.TestCase):
    def test_the_line_that_says_why_is_kept_and_not_the_last_one(self):
        job = {}
        for line in NOT_THERE:
            texpackages._progress(job, line + "\n")
        self.assertEqual(job["why"], "tlmgr install: package nosuchpackage not present in repository.")
        self.assertIn("See above messages", job["say"], "the last line is still what the run said last")

    def test_the_generic_last_line_is_never_the_reason(self):
        job = {}
        for line in MUTE:
            texpackages._progress(job, line + "\n")
        self.assertNotIn("why", job)

    def test_a_failed_run_says_it_in_the_error(self):
        job = {"name": "nosuchpackage", "running": True, "error": None}
        tree = tempfile.TemporaryDirectory()
        self.addCleanup(tree.cleanup)
        os.makedirs(os.path.join(tree.name, "tlpkg"))
        Path(tree.name, "tlpkg", "texlive.tlpdb").write_text("")
        with mock.patch.object(texpackages, "TREE", tree.name), \
                mock.patch.object(texpackages, "distribution",
                                  return_value={"kind": "texlive", "year": 2025, "tool": "tlmgr", "said": "TeX Live 2025"}), \
                mock.patch.object(texpackages, "_stream", feed(NOT_THERE)):
            texpackages._run(job, "nosuchpackage")
        self.assertEqual(job["error"], "nosuchpackage could not be installed: "
                                       "tlmgr install: package nosuchpackage not present in repository.")
        self.assertFalse(job["running"])
        self.assertEqual(job["state"], "failed")

    def test_one_repository_reason_is_not_the_next_ones(self):
        """The main repository is tried first, then the historic one of the installed year: what
        the first said ("a year ahead") must not stand as the reason when the second fails for
        another, or for none."""
        job = {"name": "x", "running": True, "error": None}
        tree = tempfile.TemporaryDirectory()
        self.addCleanup(tree.cleanup)
        os.makedirs(os.path.join(tree.name, "tlpkg"))
        Path(tree.name, "tlpkg", "texlive.tlpdb").write_text("")
        runs = iter([OTHER_YEAR, MUTE])

        def stream(job, name, cmd):
            return feed(next(runs))(job, name, cmd)

        with mock.patch.object(texpackages, "TREE", tree.name), \
                mock.patch.object(texpackages, "distribution",
                                  return_value={"kind": "texlive", "year": 2025, "tool": "tlmgr", "said": "TeX Live 2025"}), \
                mock.patch.object(texpackages, "_stream", stream):
            texpackages._run(job, "x")
        self.assertNotIn("older than remote", job["error"])
        self.assertTrue(job["error"].startswith("x could not be installed: "))


class Plans(unittest.TestCase):
    def test_each_package_is_quoted_once_in_first_seen_order(self):
        with mock.patch.object(texpackages, "distribution",
                               return_value={"kind": None, "year": None, "tool": None,
                                             "said": "no TeX on this computer"}):
            plan = texpackages.plan(["xcolor", "amsmath", "xcolor", "amsmath"])
        self.assertEqual([p["name"] for p in plan["packages"]], ["xcolor", "amsmath"])

    def test_plan_distinguishes_present_and_repository_missing_packages(self):
        info = [
            {"name": "pgf", "available": True, "containersize": 123,
             "cataloguedata": {"license": "fdl"}},
            {"name": "not-there", "available": False},
        ]

        def here(name, doc=None):
            return {"here": "available" if name == "pgf" else "missing", "file": None}

        with mock.patch.object(texpackages, "distribution",
                               return_value={"kind": "texlive", "year": 2026,
                                             "tool": "tlmgr", "said": "TeX Live 2026"}), \
                mock.patch.object(texpackages, "availability", side_effect=here), \
                mock.patch.object(texpackages, "_repositories", return_value=["repo"]), \
                mock.patch.object(texpackages, "_query_tree", return_value="scratch"), \
                mock.patch.object(texpackages, "_tlmgr", return_value=["tlmgr", "info"]), \
                mock.patch.object(texpackages.subprocess, "run",
                                  return_value=mock.Mock(returncode=0, stdout=json.dumps(info))):
            rows = texpackages.plan(["pgf", "not-there"])["packages"]
        self.assertEqual(rows[0]["here"], "available")
        self.assertFalse(rows[0]["can_get"])
        self.assertIn("Already available", rows[0]["why"])
        self.assertEqual(rows[1]["repository"], "unavailable")
        self.assertFalse(rows[1]["can_get"])
        self.assertIn("does not offer", rows[1]["why"])


    def test_a_quote_is_asked_through_a_scratch_tree_and_says_when_nobody_answered(self):
        # found driving the real page: texmf/ holds no tlpdb until a first package is
        # got, and `tlmgr info` refuses such a folder, so a fresh Parseh could never
        # quote a package; and an unreachable repository must not read as "can get it"
        told = []
        answers = {"repo": mock.Mock(returncode=1, stdout="")}

        def run(cmd, **kw):
            told.append(cmd)
            return answers["repo"]

        def tlmgr(args, repo=None, tree=None):
            return ["tlmgr", "--usertree", tree or texpackages.TREE] + list(args)

        with tempfile.TemporaryDirectory() as tree, \
                mock.patch.object(texpackages, "TREE", tree), \
                mock.patch.object(texpackages, "distribution",
                                  return_value={"kind": "texlive", "year": 2026,
                                                "tool": "tlmgr", "said": "TeX Live 2026"}), \
                mock.patch.object(texpackages, "availability",
                                  return_value={"here": "unknown", "file": None}), \
                mock.patch.object(texpackages, "_repositories", return_value=["repo"]), \
                mock.patch.object(texpackages, "_query_tree", return_value="scratch"), \
                mock.patch.object(texpackages, "_tlmgr", side_effect=tlmgr), \
                mock.patch.object(texpackages.subprocess, "run", side_effect=run):
            lost = texpackages.plan(["mhchem"])["packages"][0]
            self.assertEqual(lost["repository"], "unreachable")
            self.assertFalse(lost["can_get"])
            self.assertIn("could not be reached", lost["why"])
            answers["repo"] = mock.Mock(returncode=0, stdout=json.dumps(
                [{"name": "mhchem", "available": True, "containersize": 185132,
                  "cataloguedata": {"license": "lppl1.3c"}}]))
            got = texpackages.plan(["mhchem"])["packages"][0]
            self.assertFalse(os.listdir(tree), "nothing was written into Parseh's own texmf/")
        self.assertEqual((got["repository"], got["size"], got["licence"], got["can_get"]),
                         ("available", 185132, "lppl1.3c", True))
        self.assertTrue(all("scratch" in cmd for cmd in told), "the scratch tree asked, never texmf/")

    def test_a_package_this_tex_already_has_is_not_called_unreachable(self):
        with mock.patch.object(texpackages, "distribution",
                               return_value={"kind": "texlive", "year": 2026,
                                             "tool": "tlmgr", "said": "TeX Live 2026"}), \
                mock.patch.object(texpackages, "availability",
                                  return_value={"here": "available", "file": "x.sty"}), \
                mock.patch.object(texpackages, "_repositories", return_value=["repo"]), \
                mock.patch.object(texpackages, "_query_tree", return_value="scratch"), \
                mock.patch.object(texpackages.subprocess, "run",
                                  return_value=mock.Mock(returncode=1, stdout="")):
            row = texpackages.plan(["xcolor"])["packages"][0]
        self.assertEqual(row["here"], "available")
        self.assertNotEqual(row["repository"], "unreachable")


class ManyFiles(unittest.TestCase):
    """The page checks every file a theme could need at once (L14)."""

    def test_one_kpsewhich_answers_for_all_of_them(self):
        calls = []

        def run(cmd, **kw):
            calls.append(cmd)
            # kpsewhich prints only what it found, each as a whole path
            return mock.Mock(returncode=1, stdout="/usr/share/texmf/tex/latex/base/standalone.cls\n"
                                                  "/home/u/texmf/tex/latex/mhchem/mhchem.sty\n")

        with mock.patch.object(texpackages.shutil, "which", return_value="/usr/bin/kpsewhich"), \
                mock.patch.object(texpackages.subprocess, "run", side_effect=run):
            got = texpackages.installed_many(["standalone.cls", "circuitikz.sty", "mhchem.sty",
                                              "standalone.cls"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1:], ["standalone.cls", "circuitikz.sty", "mhchem.sty"])
        self.assertEqual(got, {"standalone.cls": True, "circuitikz.sty": False, "mhchem.sty": True})

    def test_without_kpsewhich_nothing_is_said_to_be_missing(self):
        with mock.patch.object(texpackages.shutil, "which", return_value=None):
            self.assertEqual(texpackages.installed_many(["a.sty", "b.sty"]), {"a.sty": None, "b.sty": None})

    def test_the_page_state_names_every_catalogue_file_and_what_a_draft_adds(self):
        import latexpage
        import latexthemes
        seen = []

        def many(files):
            seen.append(list(files))
            return {f: f != "circuitikz.sty" for f in files}

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(latexthemes, "STORE", os.path.join(tmp, "latex.json")), \
                mock.patch.object(texpackages, "installed_many", side_effect=many), \
                mock.patch.object(texpackages, "distribution", return_value={"said": "TeX Live test"}), \
                mock.patch.object(latexpage.latexdraw, "compilers", return_value={"xelatex": None}):
            state = latexpage.view("")
        self.assertEqual(len(seen), 1, "ONE batched check, not one kpsewhich a file")
        every = {row["file"] for row in latexthemes.PACKAGES.values()} | \
                {row[1] for row in latexthemes.ALWAYS.values()}
        self.assertEqual(set(seen[0]), every)
        self.assertEqual(set(state["files"]), every, "so an unticked package's file is known too")
        self.assertIs(state["files"]["circuitikz.sty"], False)
        self.assertEqual(state["always"]["fontspec"][1], "fontspec.sty")
        self.assertEqual(state["unicode"], list(latexthemes.UNICODE))


class Queue(unittest.TestCase):
    def test_one_worker_runs_requested_packages_in_order(self):
        entered_first = threading.Event()
        release_first = threading.Event()
        finished = threading.Event()
        seen = []

        def run(job, name):
            seen.append(name)
            if name == "first":
                entered_first.set()
                release_first.wait(2)
            with texpackages._LOCK:
                job.update({"state": "installed", "queued": False, "running": False,
                            "say": "installed", "error": None})
            if len(seen) == 3:
                finished.set()

        missing = {"here": "missing", "file": None}
        with mock.patch.object(texpackages, "JOBS", {}), \
                mock.patch.object(texpackages, "_QUEUE", []), \
                mock.patch.object(texpackages, "_WORKER_RUNNING", False), \
                mock.patch.object(texpackages, "availability", return_value=missing), \
                mock.patch.object(texpackages, "_run", side_effect=run):
            texpackages.start("first")
            self.assertTrue(entered_first.wait(2), "the first job should start")
            self.assertEqual(texpackages.status()["jobs"]["first"]["state"], "running")
            second = texpackages.start("second")
            third = texpackages.start("third")
            self.assertEqual(second["state"], "queued")
            self.assertEqual(third["state"], "queued")
            self.assertEqual(seen, ["first"], "the queue must not start a second tlmgr")
            release_first.set()
            self.assertTrue(finished.wait(2), "all queued jobs should eventually run")
            self.assertEqual(seen, ["first", "second", "third"])
            states = texpackages.status()["states"]
        self.assertEqual(states, {"first": "installed", "second": "installed", "third": "installed"})

    def test_an_already_reachable_package_is_not_enqueued(self):
        known = {"here": "available", "file": "tikz.sty"}
        with mock.patch.object(texpackages, "JOBS", {}), \
                mock.patch.object(texpackages, "_QUEUE", []), \
                mock.patch.object(texpackages, "_WORKER_RUNNING", False), \
                mock.patch.object(texpackages, "availability", return_value=known), \
                mock.patch.object(texpackages, "_run") as run:
            job = texpackages.start("pgf")
            self.assertEqual(job["state"], "available")
            self.assertFalse(job["running"])
            self.assertEqual(texpackages._QUEUE, [])
            run.assert_not_called()

    def test_three_queued_installs_keep_three_removable_manifest_records(self):
        """The regression behind the queue: one user tree, three requests."""
        tree = tempfile.TemporaryDirectory()
        self.addCleanup(tree.cleanup)
        tlpdb = Path(tree.name, "tlpkg", "texlive.tlpdb")
        tlpdb.parent.mkdir()
        tlpdb.write_text("")
        first_started = threading.Event()
        let_first_finish = threading.Event()
        names = ["first", "second", "third"]
        seen = []

        def stream(job, name, cmd):
            seen.append(name)
            if name == "first":
                first_started.set()
                let_first_finish.wait(2)
            with tlpdb.open("a") as fh:
                fh.write("name %s\n" % name)
            return True

        missing = {"here": "missing", "file": None}
        tex = {"kind": "texlive", "year": 2026, "tool": "tlmgr", "said": "TeX Live 2026"}
        import latexdraw
        with mock.patch.object(texpackages, "TREE", tree.name), \
                mock.patch.object(texpackages, "JOBS", {}), \
                mock.patch.object(texpackages, "_QUEUE", []), \
                mock.patch.object(texpackages, "_WORKER_RUNNING", False), \
                mock.patch.object(texpackages, "availability", return_value=missing), \
                mock.patch.object(texpackages, "distribution", return_value=tex), \
                mock.patch.object(texpackages, "_repositories", return_value=["repo"]), \
                mock.patch.object(texpackages, "_tlmgr", side_effect=lambda args, repo=None: ["tlmgr"] + list(args)), \
                mock.patch.object(texpackages, "_stream", side_effect=stream), \
                mock.patch.object(latexdraw, "forget_failures"):
            texpackages.start("first")
            self.assertTrue(first_started.wait(2), "the first install should start")
            texpackages.start("second")
            texpackages.start("third")
            self.assertEqual(seen, ["first"], "no second tlmgr runs beside the first")
            let_first_finish.set()
            for _ in range(200):
                got = texpackages.manifest()["packages"]
                if set(got) == set(names):
                    break
                threading.Event().wait(.01)
            self.assertEqual(seen, names)
            self.assertEqual(set(texpackages.manifest()["packages"]), set(names))

            def remove_run(cmd, **_kw):
                name = cmd[-1]
                tlpdb.write_text(tlpdb.read_text().replace("name %s\n" % name, ""))
                return mock.Mock(returncode=1, stdout="removed with a warning", stderr="")

            with mock.patch.object(texpackages.subprocess, "run", side_effect=remove_run):
                for name in names:
                    texpackages.remove(name)
            self.assertEqual(texpackages.manifest()["packages"], {})


class Removal(unittest.TestCase):
    def test_a_removed_package_leaves_no_job_behind(self):
        tree = tempfile.TemporaryDirectory()
        self.addCleanup(tree.cleanup)
        done = {"name": "tikzmark", "running": False, "done": 1, "total": 1, "say": "done", "error": None}
        with mock.patch.object(texpackages, "TREE", tree.name), \
                mock.patch.dict(texpackages.JOBS, {"tikzmark": done}, clear=False), \
                mock.patch.object(texpackages, "_tlmgr", return_value=["tlmgr", "remove", "tikzmark"]), \
                mock.patch.object(texpackages.subprocess, "run",
                                  return_value=mock.Mock(returncode=0, stdout="", stderr="")):
            texpackages._save_manifest({"packages": {"tikzmark": {"via": "tlmgr", "at": "x", "size": 1}}})
            self.assertIn("tikzmark", texpackages.status()["jobs"])
            texpackages.remove("tikzmark")
            got = texpackages.status()
        self.assertEqual(got["installed"], {})
        self.assertNotIn("tikzmark", got["jobs"], "else the page says \"installed\" beside an empty table")

    def test_tlmgr_exit_one_is_success_when_its_database_says_removed(self):
        tree = tempfile.TemporaryDirectory()
        self.addCleanup(tree.cleanup)
        os.makedirs(os.path.join(tree.name, "tlpkg"))
        Path(tree.name, "tlpkg", "texlive.tlpdb").write_text("name something-else\n")
        with mock.patch.object(texpackages, "TREE", tree.name), \
                mock.patch.object(texpackages, "_tlmgr", return_value=["tlmgr", "remove", "tikzmark"]), \
                mock.patch.object(texpackages.subprocess, "run",
                                  return_value=mock.Mock(returncode=1, stdout="removed with a warning", stderr="")):
            texpackages._save_manifest({"packages": {"tikzmark": {"via": "tlmgr", "at": "x"}}})
            texpackages.remove("tikzmark")
            self.assertEqual(texpackages.manifest()["packages"], {})

    def test_tlmgr_exit_zero_is_not_success_while_database_still_has_package(self):
        tree = tempfile.TemporaryDirectory()
        self.addCleanup(tree.cleanup)
        os.makedirs(os.path.join(tree.name, "tlpkg"))
        Path(tree.name, "tlpkg", "texlive.tlpdb").write_text("name tikzmark\n")
        with mock.patch.object(texpackages, "TREE", tree.name), \
                mock.patch.object(texpackages, "_tlmgr", return_value=["tlmgr", "remove", "tikzmark"]), \
                mock.patch.object(texpackages.subprocess, "run",
                                  return_value=mock.Mock(returncode=0, stdout="", stderr="")):
            texpackages._save_manifest({"packages": {"tikzmark": {"via": "tlmgr", "at": "x"}}})
            with self.assertRaisesRegex(ValueError, "still registered"):
                texpackages.remove("tikzmark")
            self.assertIn("tikzmark", texpackages.manifest()["packages"])

    def test_the_page_has_row_states_for_queued_running_and_failed_jobs(self):
        page = (ROOT / "lib" / "latexpage.py").read_text(encoding="utf-8")
        self.assertIn("state === 'queued'", page)
        self.assertIn("state === 'running'", page)
        self.assertIn("state === 'failed'", page)


if __name__ == "__main__":
    unittest.main()
