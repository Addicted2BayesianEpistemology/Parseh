# SPDX-License-Identifier: GPL-3.0-or-later
"""TeX packages got from Settings -> LaTeX drawings (lib/texpackages.py): what a
failed run says, and what a removal leaves behind.  No TeX is run and nothing
is fetched: tlmgr's own words are fed in, and the folder is a temporary one.

Found by driving the real page on 2026-09-25: a package that could not be got
said only tlmgr's last line, "An error has occurred. See above messages.
Exiting." (nothing is above it on the page), and a package that was removed
went on being listed as "installed" beneath a table that no longer held it."""
import os
import sys
import tempfile
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

    def test_the_page_lists_only_a_job_that_runs_or_failed(self):
        page = (ROOT / "lib" / "latexpage.py").read_text(encoding="utf-8")
        self.assertIn("jobs[n].running || jobs[n].error", page,
                      "a finished job is in the table; a line for it is a second, stale answer")


if __name__ == "__main__":
    unittest.main()
