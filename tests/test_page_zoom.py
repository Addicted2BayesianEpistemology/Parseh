# SPDX-License-Identifier: GPL-3.0-or-later
"""The page zoom (lib/pagezoom.js, a0.5.0) as its files say it: the steps and
the rule that bounds them, what is done at 100 % (nothing), how a page gets the
script (lib/parseh.js writes its tag first of all; the studio's templates carry
one), and that it is served, kept for a phone and left out of the pages that are
not zoomed.

    python3 -m unittest discover -s tests -p test_page_zoom.py

Reads the files, and runs the rule's own lines and the viewport rewrite's in
deno where it is on the PATH (as tests/test_mobile_pages.py does for the update
check).  What the pages DO with a zoom -- the shim, every viewport length, the
clouds, the sheets, the strip, a window made narrower -- is driven in a
browser by tests/page_zoom.mjs.
"""
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in ("markdown/exlex", "markdown/app", "lib", "tests", "."):
    sys.path.insert(0, str(ROOT / p))
ZOOM = ROOT / "lib" / "pagezoom.js"
TEMPLATES = ROOT / "markdown" / "app" / "templates"
# the studio's pages that are zoomed; note.html is a bare page by design, and
# the export templates are pages that travel without the toolbox
STUDIO = ("index", "doc", "edit", "prompt", "decks", "deck", "study", "cram")
TAG = '<script src="/lib/pagezoom.js"></script>'


def code(text):
    """The file without its comments, so that what a sentence says about a thing
    is not taken for the thing."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$|\s//\s.*$", "", text)


def function(text, name):
    """One function of the file, its text from `function name(` to the close
    at its own indent (the file's functions are two spaces in)."""
    m = re.search(r"(?ms)^  function %s\(.*?^  \}\n" % re.escape(name), text)
    assert m, "no function %s" % name
    return m.group(0)


def deno(js):
    exe = shutil.which("deno")
    if not exe:
        raise unittest.SkipTest("deno is not on the PATH")
    out = subprocess.run([exe, "eval", js], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


class TheFileTests(unittest.TestCase):
    def setUp(self):
        self.src = ZOOM.read_text(encoding="utf-8")
        self.code = code(self.src)

    def test_a_classic_script_that_needs_nothing(self):
        """It is the first script of a page and loads before anything else
        does: no module, no import, nothing to wait for."""
        self.assertTrue(self.src.startswith("// SPDX-License-Identifier: GPL-3.0-or-later"))
        for no in ("import ", "export ", "require(", "module.exports", "define("):
            self.assertNotIn(no, self.code, no)
        self.assertIn("(function () {\n  'use strict';\n  if (window.ParsehZoom || location.protocol === 'file:') return;", self.src,
                      "once only, and not off the disk")
        self.assertTrue(self.src.rstrip().endswith("})();"))

    def test_it_writes_no_html(self):
        for no in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
            self.assertNotIn(no, self.code, no)

    def test_the_steps_are_the_browsers_and_the_key_is_the_devices(self):
        self.assertIn("var STEPS = [70, 80, 90, 100, 110, 125, 150, 175, 200];", self.src)
        self.assertIn("var KEY = 'parseh_zoom';", self.src)
        self.assertIn("var MIN_WIDTH = 320;", self.src)
        # a fact about this screen: never in what follows a person to another device
        for name in ("prefs.js", "prefs.py"):
            self.assertNotIn("parseh_zoom", (ROOT / "lib" / name).read_text(encoding="utf-8"), name)

    def test_the_api_the_gear_codes_against(self):
        api = self.src[self.src.index("  window.ParsehZoom = {"):]
        for member in ("KEY: KEY", "STEPS: ", "MIN_WIDTH: MIN_WIDTH", "get: chosen", "applied: current", "set: set",
                       "step: function (dir)", "can: can", "allowedMax: function", "reset: function",
                       "onChange: function (fn)", "factor: function", "fits: fits"):
            self.assertIn(member, api, member)
        for sentence in ("this screen is too narrow for more", "this is the smallest size", "this is the largest size"):
            self.assertIn("'%s'" % sentence, self.src)
        self.assertIn("'parseh:zoom'", self.src)
        self.assertIn("setAttribute('data-zoom'", self.src)
        self.assertIn("setProperty('--z'", self.src)
        self.assertIn("window.addEventListener('storage'", self.src)
        self.assertIn("window.addEventListener('resize'", self.src)
        self.assertIn("window.addEventListener('orientationchange'", self.src)

    def test_the_320_rule_and_the_snap_as_pure_functions(self):
        funcs = "\n".join(function(self.src, f) for f in ("fits", "snap", "clampTo", "allowedFor"))
        head = re.search(r"var STEPS = .*?;\n", self.src).group(0) + re.search(r"var MIN_WIDTH = .*?;\n", self.src).group(0)
        cases = {
            # width -> the largest step it allows; a step is allowed where width x 100 >= 320 x step
            "allowed": {"0": 200, "100": 100, "319": 100, "351": 100, "352": 110, "360": 110, "390": 110, "399": 110,
                        "400": 125, "479": 125, "480": 150, "559": 150, "560": 175, "639": 175, "640": 200,
                        "844": 200, "1280": 200},
            "clamp": [[150, 390, 110], [200, 390, 110], [150, 844, 150], [70, 100, 70], [90, 10, 90], [200, 0, 200],
                      [110, 351, 100], [110, 352, 110], [175, 560, 175], [175, 559, 150]],
            "snap": [[113, 110], ["150", 150], ["1.5", 100], [None, 100], ["", 100], ["abc", 100], [49, 100], [301, 100],
                     [300, 200], [127, 125], [87, 90], [1000, 100]],
            "fits": [[110, 352, True], [110, 351.9, False], [125, 400, True], [100, 10, True], [70, 10, True],
                     [200, 0, True], [200, 639, False], [200, 640, True]],
        }
        js = head + funcs + "\nconst C = %s;\n" % json.dumps(cases) + """
const out = {
  allowed: Object.fromEntries(Object.keys(C.allowed).map(w => [w, allowedFor(+w)])),
  clamp: C.clamp.map(([c, w]) => clampTo(c, w)),
  snap: C.snap.map(([v]) => snap(v)),
  fits: C.fits.map(([p, w]) => fits(p, w)),
};
console.log(JSON.stringify(out));"""
        got = deno(js)
        self.assertEqual(got["allowed"], cases["allowed"])
        self.assertEqual(got["clamp"], [c[2] for c in cases["clamp"]])
        self.assertEqual(got["snap"], [c[1] for c in cases["snap"]])
        self.assertEqual(got["fits"], [c[2] for c in cases["fits"]])

    def test_the_viewport_rewrite(self):
        """100vw is the window's width and means Z times too much in a page Z times
        larger; every one is written as a division by --z, once, and not
        what is a string, a url() or part of a name."""
        unit = re.search(r"  var UNIT = .*?;\n", self.src).group(0)
        regex = re.search(r"  var VIEWPORT = new RegExp\(.*?'gi'\);\n", self.src, flags=re.S).group(0)
        js = unit + regex + function(self.src, "rewrite") + """
const cases = %s;
console.log(JSON.stringify(cases.map(v => [rewrite(v), rewrite(rewrite(v))])));""" % json.dumps([
            "100vw", "calc(100vh - 3rem)", "min(430px,100vw)", "12px 10px 60vh", "-50vw", ".5vw", "max(12vh,24px) 20px 24px",
            "0 0 calc(min(460px,94vw) - 26px)", "calc(100dvh * 16 / 9)", "4vh 4vw",
            '"100vw"', "url(a100vw.png)", "url('b 5vh.png') 10vh", "a-10vw", "var(--w10vh)", "100px", "12vhx",
            "calc(82vw / var(--zoom, 1))", "calc(100vw / var(--z, 1))"])
        got = deno(js)
        z = lambda n, u: "calc(%s%s / var(--z, 1))" % (n, u)
        want = [
            z(100, "vw"), "calc(%s - 3rem)" % z(100, "vh"), "min(430px,%s)" % z(100, "vw"), "12px 10px %s" % z(60, "vh"), z(-50, "vw"),
            z(".5", "vw"), "max(%s,24px) 20px 24px" % z(12, "vh"), "0 0 calc(min(460px,%s) - 26px)" % z(94, "vw"),
            "calc(%s * 16 / 9)" % z(100, "dvh"), "%s %s" % (z(4, "vh"), z(4, "vw")),
            '"100vw"', "url(a100vw.png)", "url('b 5vh.png') %s" % z(10, "vh"), "a-10vw", "var(--w10vh)", "100px", "12vhx",
            "calc(%s / var(--zoom, 1))" % z(82, "vw"), "calc(100vw / var(--z, 1))"]
        self.assertEqual([g[0] for g in got], want)
        self.assertEqual([g[1] for g in got], want, "written once: a second pass changes nothing")

    def test_nothing_is_replaced_at_100(self):
        """The shim is made of one function and is started from one place, a
        step to something other than 100; at load only apply() is called, and it
        engages only for a size other than 100."""
        install = function(self.src, "install")
        rest = self.code.replace(code(install), "")
        self.assertNotEqual(rest, self.code, "install() was found in the code")
        for call in ("scaled(", "rectMethod(", "pointMethod(", "scrollMethod(", "swap("):
            # the helpers are defined, and called in install() and in each other, and nowhere else
            uses = [m.start() for m in re.finditer(r"(?<!function )%s" % re.escape(call), rest)]
            if call == "swap(":
                self.assertEqual(len(uses), 4, "swap is called by the four helpers, which install() calls")
            else:
                self.assertEqual(uses, [], "%s is called outside install()" % call)
        self.assertEqual(len(re.findall(r"(?<!un)install\(\);", self.code)), 1, "started from one place")
        engage = function(self.src, "engage")
        self.assertIn("if (first) {\n      install();", engage)
        self.assertIn("var first = shown === 100;", engage)
        self.assertIn("if (want === 100) disengage(); else engage(want);", self.src)
        self.assertIn("if (want === shown) return false;", self.src)
        # what runs when the file is loaded, outside any function: one call
        top = self.src.split("  // a page is opened at the size it was left at, before anything is drawn\n")[1]
        self.assertEqual(top.strip(), "apply(false);\n  told = shown + ':' + chosen();\n})();")
        # and what it puts back
        disengage = function(self.src, "disengage")
        for part in ("unobserve();", "restore();", "uninstall();", "removeProperty('zoom')", "removeProperty('--z')",
                     "removeAttribute('data-zoom')"):
            self.assertIn(part, disengage)

    def test_the_engine_is_asked_before_a_step_and_left_alone_if_it_is_another(self):
        supported = function(self.src, "supported")
        self.assertIn("zoom:2", supported)
        self.assertIn("own === 100 && Math.abs(seen - 200) < 1", supported)
        apply_ = function(self.src, "apply")
        self.assertIn("if (want !== 100 && !supported()) want = 100;", apply_)
        self.assertIn("if (!right()) { disengage(); broken = true; }", function(self.src, "engage"))
        self.assertIn("this browser cannot zoom the page", self.src)

    def test_a_window_is_measured_by_the_glass_not_by_the_page(self):
        """innerWidth is the layout viewport, which a phone widens to fit a page
        that overflows: a rule built on it would allow a bigger zoom the wider
        the page overflowed."""
        real = function(self.src, "realWidth")
        self.assertIn("raw.vvWidth", real)
        self.assertIn("raw.vvScale", real)

    def test_a_print_is_at_its_own_size(self):
        self.assertIn("@media print{:root{zoom:1!important;--z:1!important}}", self.src)

    def test_the_stored_number_is_never_lowered_by_a_clamp(self):
        """keep() is called from set() alone: a resize, a rotation, a storage
        event only re-read it."""
        keeps = [m.start() for m in re.finditer(r"\bkeep\(", self.code)]
        self.assertEqual(len(keeps), 2, "its definition, and the one call in set()")
        self.assertIn("keep(n);", function(self.src, "set"))


class HowAPageGetsItTests(unittest.TestCase):
    def test_parseh_js_writes_the_tag_first_of_all(self):
        src = (ROOT / "lib" / "parseh.js").read_text(encoding="utf-8")
        loader = src.index("THE PAGE ZOOM COMES FIRST OF ALL")
        main = src.index("(function () {\n  'use strict';")
        self.assertLess(loader, main, "before the file's own body, which may throw")
        part = src[loader:main]
        self.assertIn("if (window.ParsehZoom || location.protocol === 'file:') return;", part)
        self.assertIn("replace(/parseh\\.js(?=[?#]|$).*$/, 'pagezoom.js')", part)
        # document.write only where the parser is on this very script
        self.assertIn("if (me && me.async === false && !me.defer && document.readyState === 'loading') {\n    document.write("
                      "'<script src=\"' +", part)
        self.assertIn("<\\/script>", part)
        self.assertIn("s.async = true;", part, "and added the way the other layers are where it cannot be written")
        # and before every other layer it loads
        for later in ("activity.js", "prefs.js", "keep.js", "explain.js", "mobilereader.js"):
            self.assertLess(loader, src.index("'%s'" % later), later)

    def test_the_studios_templates_carry_a_tag_of_their_own_first(self):
        for name in STUDIO:
            html = (TEMPLATES / (name + ".html")).read_text(encoding="utf-8")
            head = html.split("<head>")[1].split("</head>")[0]
            self.assertIn(TAG, head, name)
            self.assertEqual(head.count("pagezoom"), 2, "the tag and the comment that says why: " + name)
            first = head.index("<script")
            self.assertEqual(head.index(TAG), first, "%s: before any other script of the head" % name)
            self.assertIn("<!-- the page zoom (lib/pagezoom.js)", head[:first], name)

    def test_the_pages_that_are_not_zoomed_have_nothing_of_it(self):
        for path in [TEMPLATES / "note.html", TEMPLATES / "export_doc.html", TEMPLATES / "export_deck.html",
                     TEMPLATES / "404.html"] + list((ROOT / "html-guide").rglob("*.html")):
            self.assertNotIn("pagezoom", path.read_text(encoding="utf-8"), str(path))
        # a reader is built as it always was: parseh.js brings the zoom, so a book
        # built before it has it too
        self.assertNotIn("pagezoom", (ROOT / "lib" / "tex2html.py").read_text(encoding="utf-8"))

    def test_it_is_served_and_kept_for_a_phone(self):
        import offline
        import serve
        self.assertTrue(ZOOM.is_file())
        self.assertIn("/lib/pagezoom.js", serve.STATIC_FILES, "or it is a 404")
        self.assertIn("/lib/pagezoom.js", offline.SHARED, "a kept page must open offline with it")
        self.assertIn("/lib/pagezoom.js", offline.SHARED[:offline.SHARED.index("/lib/making.js")],
                      "among what every kept page asks for in its head")


if __name__ == "__main__":
    unittest.main()
