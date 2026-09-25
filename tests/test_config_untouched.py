# SPDX-License-Identifier: GPL-3.0-or-later
"""THE UNIT SUITE LEAVES config/ AS IT FOUND IT (TO-DO §2.25).

    python3 -m unittest discover -s tests -p "test_*.py"

This file is found by that line like any other, and what it adds is not
where it is found.  Its `load_tests` hands the loader a suite class of its
own, `Guarded`, which discovery then uses for the suite it returns -- the one
that holds every module.  That outermost suite takes a snapshot of config/
before the first test, and when the last module has torn itself down it
runs one test more, `ConfigAsItWas`, which FAILS and says what moved if
anything under config/ did (tests/configguard.py says what is compared and
why).

WHY THE WHOLE RUN, AND NOT A TEST OF ITS OWN.  A test in this file would run
where the alphabet put it, and every module after it would go unwatched.
And why a failing test rather than a printed warning: a run that leaves the
owner's settings changed must not end "OK".

WHAT IT DOES NOT WATCH.  A module run alone (`-p test_offline_notes.py`)
never loads this file and is not guarded; the full run is the one that must
be clean before a version is cut, and that is the one that looks.
"""
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                   # run as tests/test_config_untouched.py
    sys.path.insert(0, str(HERE))
import configguard                              # noqa: E402


class ConfigAsItWas(unittest.TestCase):
    """The last test of a guarded run, put there by `Guarded` -- never where
    discovery would find it, which is why `load_tests` leaves it out."""

    folder = before = None

    def test_config_is_as_the_run_found_it(self):
        if self.before is None:
            self.skipTest("run by the guarded suite, after every other test")
        said = configguard.report(self.before, configguard.snapshot(self.folder), self.folder)
        if said:
            self.fail(said)


class Guarded(unittest.TestSuite):
    """A suite that, when it is the outermost one, watches `folder` for the
    whole of its run.

    EVERY SUITE MADE AFTER THIS FILE IS LOADED IS ONE OF THESE -- each
    module's, each class's -- because the loader is handed the class, not one
    suite.  All but the outermost pass straight through: which one is
    outermost is marked on the result, the one thing every suite of a run is
    handed, the way unittest marks its own top-level run.
    """

    folder = configguard.CONFIG

    def run(self, result, debug=False):
        if getattr(result, "parseh_config_guarded", False):
            return super().run(result, debug)
        result.parseh_config_guarded = True
        check = ConfigAsItWas("test_config_is_as_the_run_found_it")
        check.folder, check.before = self.folder, configguard.snapshot(self.folder)
        super().run(result, debug)
        # AFTER THE LAST MODULE'S TEARDOWN: the outermost TestSuite.run closes
        # the module it ended in before it returns, and a store written by a
        # tearDownModule is as much the owner's as any other
        if debug:
            check.debug()
        else:
            check(result)
        return result


def load_tests(loader, standard_tests, pattern):
    loader.suiteClass = Guarded
    return loader.loadTestsFromTestCase(TheGuardItself)


class TheGuardItself(unittest.TestCase):
    """DRIVEN ON A FOLDER OF ITS OWN: a guarded run over a scratch folder,
    with tests that write into it, read back from the result a real run
    prints.  Never on config/ itself, which is the one thing here that must
    not be written."""

    def scratch(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        folder = Path(td.name) / "config"
        folder.mkdir()
        (folder / ".gitkeep").write_text("")
        (folder / "prefs.json").write_text(json.dumps({"theme": "light"}))
        (folder / "digests.json").write_text(json.dumps({"/home/b/lib/a.js": {"sha": "0" * 64}}))
        return folder

    def run_guarded(self, folder, *bodies):
        """Each body a test of its own, run in one guarded suite as discovery
        would run the tests directory -> the result."""
        tests = [unittest.FunctionTestCase(body) for body in bodies]
        suite = Guarded([Guarded(tests)])
        suite.folder = folder
        result = unittest.TestResult()
        suite.run(result)
        return result

    def test_a_run_that_leaves_the_folder_alone_passes(self):
        folder = self.scratch()
        reads = lambda: json.loads((folder / "prefs.json").read_text())
        result = self.run_guarded(folder, reads, reads)
        self.assertEqual(result.testsRun, 3, "the two tests and the check after them")
        self.assertTrue(result.wasSuccessful(), result.failures + result.errors)

    def test_a_test_that_writes_the_folder_fails_the_run_and_names_what(self):
        folder = self.scratch()

        def dark():
            (folder / "prefs.json").write_text(json.dumps({"theme": "dark"}))

        def learns():
            got = json.loads((folder / "digests.json").read_text())
            got["/tmp/tmpq1w2e3/books/persian/kelile/book.json"] = {"sha": "1" * 64}
            (folder / "digests.json").write_text(json.dumps(got))

        def litters():
            (folder / "wheres.json").write_text("{}")

        result = self.run_guarded(folder, dark, learns, litters)
        self.assertEqual(result.testsRun, 4)
        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.failures), 1, "the three writers pass; the run does not")
        test, said = result.failures[0]
        self.assertIsInstance(test, ConfigAsItWas)
        self.assertIn('prefs.json changed', said)
        self.assertIn('theme ("light" -> "dark")', said,
                      "a preference's old value is said, so it can be put back")
        self.assertIn("1 added, e.g. /tmp/tmpq1w2e3/books/persian/kelile/book.json", said,
                      "a store's new entries are named: the test's own paths")
        self.assertIn("wheres.json appeared (2 bytes)", said)
        self.assertIn("tests/decks_harness.py", said, "and the way to do it right")

    def test_a_write_in_a_modules_teardown_is_seen_too(self):
        """The check runs after the last module has been closed, not after
        its last test."""
        folder = self.scratch()
        name = "parseh_config_guard_teardown_probe"
        module = types.ModuleType(name)
        module.tearDownModule = lambda: (folder / "prefs.json").write_text("{}")

        class Probe(unittest.TestCase):
            def test_nothing(self):
                pass
        Probe.__module__ = name
        sys.modules[name] = module
        self.addCleanup(sys.modules.pop, name, None)
        suite = Guarded([Guarded([Probe("test_nothing")])])
        suite.folder = folder
        result = unittest.TestResult()
        suite.run(result)
        self.assertEqual(len(result.failures), 1, result.failures)
        self.assertIn("prefs.json changed", result.failures[0][1])

    def test_discovery_hands_back_a_guarded_suite(self):
        """The wiring, through unittest's own discovery of this directory: the
        suite it returns -- the one `python3 -m unittest discover` runs -- is
        a `Guarded`, watching the checkout's own config/."""
        loader = unittest.TestLoader()
        suite = loader.discover(str(HERE), pattern="test_config_untouched.py",
                                top_level_dir=str(HERE))
        # by name: run as tests/test_config_untouched.py, this file is loaded
        # a second time by the discovery below, with a Guarded of its own
        self.assertEqual(type(suite).__qualname__, "Guarded")
        self.assertEqual(Path(suite.folder), HERE.parent / "config")
