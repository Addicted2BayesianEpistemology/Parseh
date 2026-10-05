# SPDX-License-Identifier: GPL-3.0-or-later
"""THE SCREEN A PAGE SHOWS ONCE PARSEH HAS STOPPED never tells a person to type a command.

Every action is done from the pages or by clicking Parseh's own launcher (a Windows computer has no `./serve.sh`, and a
phone that is looking at the page cannot start anything): the shared screen (lib/parseh.js, `stopNow`) and the seven
studio pages' own (markdown/app/templates/*.html, #shutdown-overlay) say to start Parseh again on the computer it runs
on, the way it was started before, and name the two launchers that are clicked.  The guide quotes the shared screen
(html-guide/markdown/reference/troubleshooting.md): it is held to the same words.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ("deck", "decks", "doc", "edit", "index", "prompt", "study")
LAUNCHERS = ("Parseh.command", "serve.bat")


def shared_screen():
    text = (ROOT / "lib" / "parseh.js").read_text(encoding="utf-8")
    m = re.search(r"function stopNow\(.*?\n  \}\n", text, re.S)
    assert m, "lib/parseh.js has no stopNow()"
    return m.group(0)


def studio_screen(name):
    text = (ROOT / "markdown" / "app" / "templates" / ("%s.html" % name)).read_text(encoding="utf-8")
    m = re.search(r'<div id="shutdown-overlay".*?</div>\s*</div>', text, re.S)
    assert m, "%s.html has no #shutdown-overlay" % name
    return m.group(0)


class TheShutdownScreens(unittest.TestCase):
    def test_none_tells_a_person_to_type_a_command_or_to_find_a_directory(self):
        screens = {"lib/parseh.js": shared_screen()}
        screens.update({"%s.html" % n: studio_screen(n) for n in TEMPLATES})
        for where, text in screens.items():
            with self.subTest(where):
                self.assertNotRegex(text, r"serve\.sh|project directory|terminal|<code>")

    def test_each_names_the_two_launchers_that_are_clicked(self):
        screens = {"lib/parseh.js": shared_screen()}
        screens.update({"%s.html" % n: studio_screen(n) for n in TEMPLATES})
        for where, text in screens.items():
            with self.subTest(where):
                for launcher in LAUNCHERS:
                    self.assertIn(launcher, text)

    def test_the_shared_screen_says_to_reload_the_page_and_the_guide_quotes_it(self):
        self.assertIn("reload this page", shared_screen())
        row = [l for l in (ROOT / "html-guide" / "markdown" / "reference" / "troubleshooting.md").read_text(encoding="utf-8").splitlines()
               if l.startswith("| *Parseh stopped.")]
        self.assertEqual(len(row), 1, "the troubleshooting page quotes the screen once")
        for launcher in LAUNCHERS:
            self.assertIn(launcher, row[0])
        self.assertNotIn("serve.sh", row[0].split("|")[1], "what it quotes of the screen has no command in it")


if __name__ == "__main__":
    unittest.main()
