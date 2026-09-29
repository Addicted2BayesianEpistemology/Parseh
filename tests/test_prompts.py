# SPDX-License-Identifier: GPL-3.0-or-later
"""The prompt tests (brief 3.8): every prompt Parseh hands to a chatbot, in every
language of the registry and in one added with lib/newlang.py, as a chatbot
receives it -- built by the lab (lib/promptlab.py), which builds each one the
way its own page does -- and the kit that makes them (lib/promptkit.py).

Three things are held here:

  * THE KIT: the marks of a template ({{?flag}} blocks, {{NAME}} placeholders),
    a template's three parts, what a person's own instructions may and may not
    do, the version line, the cut of a language's conventions;
  * THE PROMPTS: a table of checks (CHECKS) run over every surface x language x
    mode -- no `{{` left, the language named, a size budget, the parts in their
    order, and the drift the owner has met: a book's rules in a video's prompt, a
    correction sent to `note`, a harakat rule in the studio's;
  * THE ASSEMBLERS: every route that hands out a prompt keeps its shape and hands
    out what the kit made.

A CHECK THAT CANNOT PASS YET is a row marked PENDING("D") or PENDING("E"): the
lane that rewrites the words it is about (D: the gloss prompts and the
language files, E: the studio's) makes it true and takes the mark off.  A row
never silently disappears: while it is pending it is a skipped test that names
its lane, says why and says how many prompts still fail it -- and the day it
passes on all of them it fails, until the mark is taken off.
"""
import collections
import contextlib
import io
import math
import os
import random
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
for _p in ("markdown/app", "markdown/exlex", "markdown", "youtube/lib", "lib"):
    sys.path.insert(0, os.path.join(ROOT, _p))
import glossregion                                              # noqa: E402
import languages                                                # noqa: E402
import newbook                                                  # noqa: E402
import newlang                                                  # noqa: E402
import promptkit as K                                           # noqa: E402
import promptlab                                                # noqa: E402
import server as studio_server                                  # noqa: E402
import tidy as tidier                                           # noqa: E402
import version                                                  # noqa: E402
import ytpages                                                  # noqa: E402

# THE SIZE BUDGETS, in characters, of every prompt on the lab's fixtures, and
# what was measured beside each: (measured, budget), the budget being the
# measured size with 15 % to spare, rounded up to a hundred.  A region prompt is
# its largest mode.  One table, so that a lane that makes a prompt longer or
# shorter does it on purpose: change the measured number and its budget together
# (test_the_budgets_keep_to_their_rule) and say why in the commit.  What a
# person's own text or a language they added adds is theirs; these are Parseh's.
SIZES = {
    #        studio-doc     studio-exercises  video-new      video-region   book-region    transcript-tidy  book-new
    "fa": ((21274, 24500), (33749, 38900), (30695, 35300), (20604, 23700), (21276, 24500), (2696, 3200), (32808, 37800)),
    "ar": ((21945, 25300), (34419, 39600), (30569, 35200), (21027, 24200), (20705, 23900), (2687, 3100), (32685, 37600)),
    "it": ((22104, 25500), (30335, 34900), (30602, 35200), (21032, 24200), (20710, 23900), (2747, 3200), (32652, 37600)),
    "ja": ((22748, 26200), (30978, 35700), (33877, 39000), (24592, 28300), (24866, 28600), (2636, 3100), (34581, 39800)),
    "fr": ((26105, 30100), (34337, 39500), (38721, 44600), (26973, 31100), (26605, 30600), (2795, 3300), (40715, 46900)),
    "de": ((25652, 29500), (33884, 39000), (39098, 45000), (27027, 31100), (26485, 30500), (2758, 3200), (41124, 47300)),
    "tr": ((23877, 27500), (32108, 37000), (39560, 45500), (28881, 33300), (28618, 33000), (2746, 3200), (41614, 47900)),
    "en": ((28074, 32300), (36305, 41800), (41797, 48100), (30411, 35000), (29982, 34500), (2811, 3300), (43779, 50400)),
    "hi": ((23605, 27200), (31838, 36700), (33993, 39100), (23691, 27300), (23945, 27600), (2692, 3100), (36086, 41500)),
    "es": ((23771, 27400), (32002, 36900), (39886, 45900), (28935, 33300), (29167, 33600), (2664, 3100), (41928, 48300)),
    "zh": ((24414, 28100), (32645, 37600), (42340, 48700), (29741, 34300), (29847, 34400), (2620, 3100), (43126, 49600)),
}
MEASURED = ("studio-doc", "studio-exercises", "video-new", "video-region", "book-region",
            "transcript-tidy", "book-new")
GLOSSED = ("video-new", "video-region", "book-region", "book-new")
REGIONS = ("video-region", "book-region")
STUDIO = ("studio-doc", "studio-exercises")
ROOM = 1.15


def budget_of(measured):
    return int(math.ceil(measured * ROOM / 100.0)) * 100


Ctx = collections.namedtuple("Ctx", "surface code mode L G")
Check = collections.namedtuple("Check", "name why applies pending test")


# --- the checks: each is a function of a prompt, and says what is wrong ---
def _flat(text):
    return " ".join(text.split())


def no_placeholder_left(a, c):
    return ["carries `{{`: %s" % ", ".join(sorted(set(re.findall(r"\{\{\S{0,30}", a.text)))[:4])] \
        if "{{" in a.text else []


# WHERE EACH PROMPT SAYS WHICH LANGUAGE IT IS ABOUT, and which the meanings are written in: a language's
# name is in every prompt by accident (Persian's file speaks of a book glossed in Italian), so the
# check looks at the place the prompt says it on purpose.
def _says(surface, L, G):
    name, code = re.escape(L.name), re.escape(L.code)
    if surface == "studio-doc":
        return [r"this document is about %s:" % name]
    if surface == "studio-exercises":
        return [r"^# %s — the annotation conventions" % name]
    if surface in REGIONS or surface == "video-new":
        return [r"^- language: %s \(`%s`\)" % (name, code),
                r"^- gloss language: \*\*%s\*\* \(`%s`\)" % (re.escape(G.name), re.escape(G.code))]
    if surface == "transcript-tidy":
        return [r"transcript of a video in %s," % name]
    return [r"in %s, glossed in %s" % (name, re.escape(G.name))]


def names_the_language(a, c):
    return ["never says %r" % p for p in _says(c.surface, c.L, c.G)
            if not re.search(p, a.text, re.M)]


def within_its_budget(a, c):
    budget = SIZES[c.code][MEASURED.index(c.surface)][1]
    return ["%d characters, budget %d" % (len(a.text), budget)] if len(a.text) > budget else []


def opens_with_its_version_line(a, c):
    line = K.version_line(c.surface, c.L, c.G if c.surface in GLOSSED else None, c.mode)
    first = a.text.split("\n", 2)
    out = [] if first[0] == line else ["opens with %r, not %r" % (first[0][:70], line)]
    if version.VERSION not in first[0]:
        out.append("the version line does not carry %s" % version.VERSION)
    if len(first) < 2 or first[1] != "":
        out.append("no blank line after the version line")
    return out


def has_its_three_parts_in_order(a, c):
    out = []
    at = [a.text.find(x) if x else -2 for x in (a.instructions, a.contract, a.data)]
    if c.surface in K.READS_BACK and not a.contract.strip():
        out.append("no answer contract")
    if not a.instructions.strip():
        out.append("no instructions")
    seen = [i for i in at if i >= 0]
    if seen != sorted(seen) or -1 in at:
        out.append("the parts are not in the order instructions, contract, data: %s" % at)
    if a.data and not a.text.rstrip("\n").endswith(a.data.rstrip("\n")[-40:]):
        out.append("the data is not last")
    # the contract comes after EVERYTHING that is instruction, the language's conventions included
    if c.surface in K.KIND and a.contract:
        conventions = K.language_text(c.surface, c.L)
        if conventions and conventions[-60:] in a.text \
                and a.text.index(a.contract[:60]) < a.text.index(conventions[-60:]):
            out.append("the answer contract comes before the language's conventions end")
    return out


def has_no_tex_specials_rule(a, c):
    return ["says %r" % p for p in (r"None of `\$ % & # _ \^ ~` may appear", r"`voc` is \*\*LaTeX\*\*")
            if re.search(p, a.text)]


def has_no_harakat_rule_of_a_reading_edition(a, c):
    return ["says %r" % p for p in (r"harakat", r"tashkil", r"reading edition `fa` carries")
            if re.search(p, a.text)]


# the template's own words about the `note` it never reads from an answer
_OWN_NOTE = ("this answer writes no", "is thrown away", "do not apply here")


def sends_no_correction_to_note(a, c):
    out = []
    for s in re.split(r"(?<=[.!?])\s+", _flat(a.text)):
        if "`note`" in s and "correction" in s and not any(w in s for w in _OWN_NOTE):
            out.append("sends a correction to `note`: %s" % s[:100])
    return out


def has_no_harakat_rule(a, c):
    return ["has a rule about %r" % p for p in ("harakat", "tashkil", "short vowel")
            if re.search(p, a.text, re.I)]


def has_no_continuous_prose(a, c):
    return ["says \"continuous prose\""] if "continuous prose" in a.text else []


# THE MEANING RULE is Lane D's words (docs/meaning-rule.md, brief 6.1): its heading is
# what a prompt that asks for `en` carries exactly once.  D changes this line if the
# owner's final words change the heading.
MEANING_RULE = "is a gloss, not a translation"


def has_the_meaning_rule_once(a, c):
    n = a.text.count(MEANING_RULE)
    return [] if n == 1 else ["the meaning rule (%r) stands %d times" % (MEANING_RULE, n)]


def has_no_sidebar_paragraph(a, c):
    return ["documents the sources sidebar's button"] if "sources sidebar" in a.text else []


def has_no_avoid_math(a, c):
    return ["still says to avoid math"] if re.search(r"avoid[^.]*\bmath\b", a.text) else []


ALL_SURFACES = tuple(K.SURFACES[:-1])          # `ask` is JavaScript's
PROJECT = "youtube/PROMPT.md"                    # handed over as a file, as it is
CHECKS = (
    Check("no_placeholder_left", "a resolved prompt never carries `{{` (brief 3.2)",
          ALL_SURFACES, {}, no_placeholder_left),
    Check("names_the_language_and_the_gloss_language",
          "the language and the gloss language are named (brief 3.8)",
          ALL_SURFACES, {}, names_the_language),
    Check("stays_within_its_size_budget", "each prompt is under its budget (brief 3.8)",
          ALL_SURFACES, {}, within_its_budget),
    Check("opens_with_its_version_line", "every copied prompt opens with the version line (brief 3.4)",
          ALL_SURFACES, {}, opens_with_its_version_line),
    Check("has_its_three_parts_in_order",
          "instructions, then the answer contract, then the data (brief 3.1)",
          ALL_SURFACES, {}, has_its_three_parts_in_order),
    Check("has_no_harakat_rule_in_a_studio_prompt",
          "a document carries no marks a reading edition writes (brief 3.8)",
          STUDIO, {}, has_no_harakat_rule),
    Check("has_no_continuous_prose",
          "the meaning lines are a gloss, not \"continuous prose\" (brief 3.8, 6.1)",
          ALL_SURFACES + (PROJECT,), {}, has_no_continuous_prose),
    Check("has_no_tex_specials_rule_in_a_video",
          "the TeX specials are a book's: a video never reaches LaTeX (brief 3.8, 4.3)",
          ("video-region", "video-new"), {}, has_no_tex_specials_rule),
    # --- rows that wait for the lane that rewrites the words they are about ---
    Check("has_no_harakat_rule_of_a_reading_edition_in_a_video",
          "a reading edition's harakat are a book's (brief 3.8); the language files still say them in "
          "unmarked paragraphs (the text field, the sources sidebar's) which D marks {{?book}} or moves",
          ("video-region", "video-new"), {"video-region": "D", "video-new": "D"},
          has_no_harakat_rule_of_a_reading_edition),
    Check("sends_no_correction_to_note",
          "a region prompt never sends a correction to `note`, which its answer never writes; "
          "the language files' verbatim paragraph still says so, which D rewrites (brief 3.8, 6.6)",
          REGIONS, {"video-region": "D", "book-region": "D"}, sends_no_correction_to_note),
    Check("has_the_meaning_rule_once",
          "the meaning rule once in every prompt that asks for `en` (brief 6.1)",
          GLOSSED, {}, has_the_meaning_rule_once),
    Check("has_no_sidebar_paragraph",
          "the sources sidebar's paragraph is documentation of a button and leaves every language "
          "file for the guide (brief 6.5); the studio's prompts no longer receive it",
          ALL_SURFACES, {s: "D" for s in GLOSSED}, has_no_sidebar_paragraph),
    Check("has_no_avoid_math",
          "the studio's rule 14 no longer says to avoid math (brief 7.3)",
          STUDIO, {s: "E" for s in STUDIO}, has_no_avoid_math),
)


def build_everything(codes=None, gloss=None):
    """[(Ctx, Assembled)] for every surface the lab builds, in every language,
    every mode a region has."""
    out = []
    for code in codes or languages.CODES:
        L = languages.get(code)
        G = languages.gloss_or_default(gloss)
        for surface in ALL_SURFACES:
            for mode in ((None, "perfield", "regloss") if surface in REGIONS else (None,)):
                out.append((Ctx(surface, code, mode, L, G),
                            promptlab.build(surface, code, mode, gloss)))
    return out


def machine_patches():
    """What a prompt depends on that is this machine's and not Parseh's: the
    example of a video from scratch is a video on the shelf, and the studio's
    prompt may be one the person wrote (library/_prompt.md).  Neither, so that
    the prompts are the same on every machine."""
    return [mock.patch.object(ytpages, "video_dirs", lambda: []),
            mock.patch.object(studio_server.store, "get_prompt",
                              lambda: {"text": studio_server.store.default_prompt(), "custom": False})]


class ControlledMachine(unittest.TestCase):
    def setUp(self):
        for p in machine_patches():
            p.start()
            self.addCleanup(p.stop)


# --- the prompts, everywhere ---------------------------------------------
class EveryPrompt(ControlledMachine):
    built = None

    @classmethod
    def setUpClass(cls):
        patches = machine_patches()
        for p in patches:
            p.start()
        try:
            cls.built = build_everything()
        finally:
            for p in patches:
                p.stop()
        # the prompt Parseh hands over as a file, as it is: one more thing to check
        with open(os.path.join(ROOT, "youtube", "PROMPT.md"), encoding="utf-8") as f:
            text = f.read()
        cls.built.append((Ctx(PROJECT, "-", None, None, None), K.Assembled(PROJECT, "", text, "", "")))

    def run_check(self, check):
        seen = 0
        for ctx, a in self.built:
            if ctx.surface not in check.applies or ctx.surface in check.pending:
                continue
            seen += 1
            with self.subTest(surface=ctx.surface, language=ctx.code, mode=ctx.mode):
                self.assertEqual(check.test(a, ctx), [], "%s [%s]" % (check.why, a.header))
        self.assertTrue(seen, "%s ran on nothing" % check.name)

    def wait_for(self, check):
        """A row that waits for a lane: it is run all the same, and skipped with
        its reason while it still fails.  When it passes everywhere the lane has
        done its work and forgot the mark: that is a failure, so the row is
        flipped on and can never fail silently afterwards."""
        lane = "/".join(sorted(set(check.pending.values())))
        waited = [(c, a) for c, a in self.built if c.surface in check.pending]
        failing = sum(1 for c, a in waited if check.test(a, c))
        if not failing:
            self.fail("PENDING(%s) %s passes on all %d prompts it waited for: take the mark "
                      "off its row in CHECKS, so that it is checked from now on" % (lane, check.name, len(waited)))
        self.skipTest("PENDING(%s): %s -- still fails on %d of %d prompts (%s)" % (
            lane, check.why, failing, len(waited), ", ".join(sorted(check.pending))))


def _make_tests():
    for check in CHECKS:
        if [s for s in check.applies if s not in check.pending]:
            setattr(EveryPrompt, "test_" + check.name, lambda self, check=check: self.run_check(check))
        if check.pending:
            lane = "_".join(sorted(set(check.pending.values())))
            setattr(EveryPrompt, "test_%s__PENDING_%s" % (check.name, lane),
                    lambda self, check=check: self.wait_for(check))


_make_tests()


class Budgets(ControlledMachine):
    def test_the_budgets_keep_to_their_rule(self):
        # measured beside budget, so that a lane changing a size does it on purpose
        for code, row in SIZES.items():
            self.assertEqual(len(row), len(MEASURED), code)
            for surface, (measured, budget) in zip(MEASURED, row):
                self.assertEqual(budget, budget_of(measured), (code, surface))

    def test_every_language_of_the_registry_has_its_row(self):
        self.assertEqual(sorted(SIZES), sorted(languages.CODES))

    def test_the_measured_numbers_are_the_sizes_of_today_within_five_percent(self):
        # else a prompt that shrank or grew on purpose leaves a budget that says nothing (or forbids
        # what was meant): 5 % is what a machine without a word segmenter changes a Japanese or
        # Chinese prompt by, and less than any change a lane makes on purpose
        largest = {}
        for ctx, a in build_everything():
            key = (ctx.code, ctx.surface)
            largest[key] = max(largest.get(key, 0), len(a.text))
        for code, row in SIZES.items():
            for surface, (measured, _budget) in zip(MEASURED, row):
                today = largest[(code, surface)]
                self.assertLessEqual(abs(today - measured), 0.05 * measured,
                                     "%s %s is %d characters today, the table says %d: "
                                     "change the measured number and its budget together" % (code, surface, today, measured))


# --- a language added with newlang.py, in a temporary store ---------------
class AddedLanguage(ControlledMachine):
    """Esperanto, added the way a person adds one: its row in the store, its
    conventions written from docs/lang/_template.md.  Every prompt has to be
    made for it as for the languages that ship."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="promptkit-eo-")
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        shipped = os.path.join(cls.tmp, "lib", "languages.json")
        personal = os.path.join(cls.tmp, "config", "languages.json")
        lang_tex = os.path.join(cls.tmp, "lib", "lang")
        lang_docs = os.path.join(cls.tmp, "docs", "lang")
        os.makedirs(os.path.dirname(shipped))
        shutil.copy(os.path.join(ROOT, "lib", "languages.json"), shipped)
        shutil.copytree(os.path.join(ROOT, "lib", "lang"), lang_tex)
        shutil.copytree(os.path.join(ROOT, "docs", "lang"), lang_docs)
        patches = [mock.patch.object(newlang, n, v) for n, v in (
            ("REGISTRY", shipped), ("PERSONAL", personal), ("LANG_TEX", lang_tex),
            ("LANG_DOCS", lang_docs), ("ROOT", cls.tmp),
            ("STUDIO", os.path.join(cls.tmp, "markdown")))]
        for p in patches:
            p.start()
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                rc = newlang.main(["eo", "--name", "Esperanto", "--native", "Esperanto"])
        finally:
            for p in patches:
                p.stop()
        assert rc == 0, "newlang could not add the language: %s" % out.getvalue()[-400:]
        langs, problems = languages._load(shipped, personal)
        assert "eo" in langs and not problems, problems
        for p in [mock.patch.dict(languages.LANGS, {"eo": langs["eo"]}),
                  mock.patch.dict(languages.FOLDERS, {langs["eo"].folder: "eo"}),
                  mock.patch.object(K, "LANG_DOCS", lang_docs)] + machine_patches():
            p.start()
            cls.addClassCleanup(p.stop)
        cls.built = [(Ctx(s, "eo", m, languages.get("eo"), languages.gloss_or_default(None)),
                      promptlab.build(s, "eo", m))
                     for s in ALL_SURFACES
                     for m in ((None, "perfield", "regloss") if s in REGIONS else (None,))]

    def test_every_prompt_is_made_for_it(self):
        self.assertEqual(len(self.built), len(ALL_SURFACES) + 4)
        for ctx, a in self.built:
            with self.subTest(surface=ctx.surface, mode=ctx.mode):
                for check in CHECKS:
                    # its size is its own (there is no budget for a language nobody ships)
                    if (ctx.surface in check.applies and ctx.surface not in check.pending
                            and check.test is not within_its_budget):
                        self.assertEqual(check.test(a, ctx), [], check.why)

    def test_the_studio_takes_its_note_on_writing_the_script_from_chunking(self):
        # newlang writes the note into Chunking, which the studio does not take:
        # it is found by what it says
        note = "Runs of Esperanto are **marked** in the studio"
        by = {(c.surface, c.mode): a for c, a in self.built}
        self.assertIn(note, by[("studio-doc", None)].text)
        self.assertIn(note, by[("studio-exercises", None)].text)
        self.assertNotIn(note, by[("video-region", None)].text)
        self.assertIn(note, by[("video-new", None)].text)
        self.assertIn("## The text field", K.language_text("studio-doc", "eo"))


# --- the kit's marks -------------------------------------------------------
def _old_blocks(tpl, flags):
    """glossregion._blocks as it was, the oracle for the kit's resolver."""
    pat = re.compile(r"\{\{\?(\w+)\}\}((?:(?!\{\{\?).)*?)\{\{/\1\}\}", re.S)
    while True:
        new = pat.sub(lambda m: m.group(2) if flags.get(m.group(1)) else "", tpl)
        if new == tpl:
            return tpl
        tpl = new


class Marks(unittest.TestCase):
    def test_a_block_is_kept_where_its_flag_is_true_and_gone_where_it_is_not(self):
        t = "a{{?x}}b{{/x}}c"
        self.assertEqual(K.blocks(t, {"x": True}), "abc")
        self.assertEqual(K.blocks(t, {"x": False}), "ac")

    def test_a_note_to_the_maintainer_is_never_sent_to_any_surface(self):
        t = "a{{?note}}no speaker has reviewed this yet{{/note}}b"
        for surface in K.SURFACES:
            self.assertEqual(K.blocks(t, K.surface_flags(surface)), "ab", surface)

    def test_a_block_may_hold_a_block(self):
        t = "1{{?a}}2{{?b}}3{{/b}}4{{/a}}5"
        self.assertEqual(K.blocks(t, {"a": True, "b": True}), "12345")
        self.assertEqual(K.blocks(t, {"a": True, "b": False}), "1245")
        self.assertEqual(K.blocks(t, {"a": False, "b": True}), "15")

    def test_the_kit_resolves_the_region_template_as_glossregion_always_did(self):
        with open(K.TEMPLATES["video-region"], encoding="utf-8") as f:
            tpl = f.read()
        plain = re.sub(r"\{\{[?/](contract|data)\}\}", "", tpl)
        names = sorted(set(re.findall(r"\{\{\?(\w+)\}\}", plain)))
        self.assertIn("keep", names)
        rng = random.Random(4)
        for _ in range(300):
            flags = {n: rng.random() < 0.5 for n in names}
            self.assertEqual(K.blocks(tpl, flags), _old_blocks(plain, flags), flags)

    def test_a_block_whose_flag_nobody_gave_is_refused_not_dropped(self):
        with self.assertRaises(K.PromptError) as e:
            K.blocks("a{{?vidoe}}b{{/vidoe}}", {"video": True})
        self.assertIn("vidoe", str(e.exception))

    def test_a_block_left_open_or_closed_twice_or_crossed_is_refused_in_words(self):
        for text, said in (("{{?a}}x", "never closed"), ("x{{/a}}", "never opened"),
                           ("{{?a}}{{?b}}x{{/a}}{{/b}}", "was due")):
            with self.assertRaises(K.PromptError) as e:
                K.blocks(text, {"a": True, "b": True})
            self.assertIn(said, str(e.exception), text)

    def test_the_marks_of_the_parts_are_not_flags_and_keep_their_words_in_place(self):
        t = "a{{?contract}}B{{/contract}}c{{?data}}D{{/data}}"
        self.assertEqual(K.flat(t), "aBcD")
        self.assertEqual(K.blocks(t, {}), "aBcD")

    def test_the_instructions_of_a_text_leave_the_contract_and_the_data_out(self):
        self.assertEqual(K.instructions_of("a{{?contract}}B{{/contract}}c{{?data}}D{{/data}}"), "ac")
        self.assertEqual(K.instructions_of("no marks {{ at all }}"), "no marks {{ at all }}")

    def test_every_template_taken_apart_and_put_together_has_the_words_it_had(self):
        """Each part resolved on its own, together, has the words the whole
        template has, whichever flags are on: nothing is lost in the split."""
        rng = random.Random(9)
        for surface in ("video-region", "video-new", "studio-doc", "studio-exercises", "book-new"):
            with open(K.TEMPLATES[surface], encoding="utf-8") as f:
                whole = f.read()
            if surface == "studio-doc":
                whole = K._template(surface)
            names = sorted(set(re.findall(r"\{\{\?(\w+)\}\}", whole)) - set(K._MARKS))
            given = K.parts(surface)
            for _ in range(40):
                flags = {n: rng.random() < 0.5 for n in names}
                got = collections.Counter()
                for part in given:
                    got.update(K.blocks(part, flags).split())
                self.assertEqual(got, collections.Counter(K.blocks(whole, flags).split()),
                                 (surface, flags))

    def test_flat_takes_the_marks_out_and_nothing_else(self):
        for surface, flags in (("video-new", {"example": True}), ("studio-exercises", {}), ("book-new", {})):
            with open(K.TEMPLATES[surface], encoding="utf-8") as f:
                text = f.read()
            stripped = re.sub(r"\{\{[?/](contract|data|example)\}\}", "", text)
            self.assertNotIn("{{?contract}}", stripped)
            self.assertEqual(K.flat(text, flags), stripped, surface)


class Parts(unittest.TestCase):
    T = ("Do it{{?x}} well{{/x}}.\n\n{{?contract}}Answer in a fence.{{/contract}}\n\n"
         "More rules.\n\n{{?contract}}{{?x}}Several messages.{{/x}}{{/contract}}\n\n"
         "{{?data}}The data: {{DATA}}{{/data}}\n")

    def test_a_template_is_split_into_instructions_contract_and_data(self):
        p = K.parts("studio-doc", template=self.T)
        self.assertEqual(p.instructions, "Do it{{?x}} well{{/x}}.\n\nMore rules.")
        self.assertEqual(p.contract, "Answer in a fence.\n\n{{?x}}Several messages.{{/x}}")
        self.assertEqual(p.data, "The data: {{DATA}}")

    def test_a_flag_block_that_holds_the_words_of_two_parts_is_kept_around_each(self):
        t = "{{?x}}I{{?contract}}C{{/contract}}J{{/x}}"
        p = K.parts("studio-doc", template=t)
        self.assertEqual((p.instructions, p.contract), ("{{?x}}IJ{{/x}}", "{{?x}}C{{/x}}"))

    def test_the_parts_do_not_nest(self):
        with self.assertRaises(K.PromptError):
            K.parts("studio-doc", template="{{?contract}}{{?data}}x{{/data}}{{/contract}}")

    def test_every_prompt_parseh_reads_back_has_a_contract_in_its_template(self):
        for surface in K.READS_BACK:
            self.assertTrue(K.contract(surface, template=(
                tidier.PROMPT if surface == "transcript-tidy" else None)).strip(), surface)

    def test_the_contract_and_the_data_of_the_region_template_are_the_end_of_the_prompt(self):
        p = K.parts("video-region")
        self.assertIn("## What you answer", p.contract)
        self.assertIn("You receive **one JSON document**", p.contract)
        self.assertNotIn("## What you answer", p.instructions)
        self.assertTrue(p.data.startswith("{{ABOUT}}") and p.data.endswith("nothing else."))

    def test_the_transcript_tidy_template_is_registered_by_the_module_that_has_it(self):
        self.assertEqual(K.parts("transcript-tidy").data.split("\n")[0], "THE TRANSCRIPT:")

    def test_ask_has_no_template_here(self):
        with self.assertRaises(K.PromptError):
            K.parts("ask")


class Assembling(unittest.TestCase):
    def test_a_persons_instructions_replace_parseh_s_and_the_contract_stays(self):
        a = K.assemble("studio-doc", "it", instructions="My rules for {{LANGUAGE}}.\n{{?studio}}studio only{{/studio}}",
                       custom="mine")
        self.assertEqual(a.instructions, "My rules for Italian.\nstudio only")
        self.assertIn("creating a markdown file", a.contract)
        self.assertEqual(a.text.split("\n")[0], "Parseh prompt · studio-doc · it · %s · custom: mine" % version.VERSION)
        order = [a.text.index(x) for x in ("My rules", "creating a markdown file")]
        self.assertEqual(order, sorted(order))

    def test_instructions_cannot_carry_the_contract_or_the_data(self):
        for mark in ("contract", "data"):
            with self.assertRaises(K.PromptError):
                K.assemble("studio-doc", "fa", instructions="x {{?%s}}y{{/%s}}" % (mark, mark))

    def test_a_placeholder_nothing_fills_is_refused_in_words(self):
        with self.assertRaises(K.PromptError) as e:
            K.assemble("studio-doc", "fa", instructions="Say {{NOTHING_FILLS_THIS}}.")
        self.assertIn("NOTHING_FILLS_THIS", str(e.exception))
        self.assertIn("bug", str(e.exception))

    def test_a_block_left_over_in_the_result_is_refused_too(self):
        with self.assertRaises(K.PromptError):
            K.assemble("studio-doc", "fa", instructions="{{?nope}}x{{/nope}}")

    def test_what_is_data_may_say_double_braces_and_is_never_looked_into(self):
        a = K.assemble("studio-doc", "fa", instructions="rules", data="Explain {{this}} and {{?that}} for me. {{DATA}}",
                       verbatim={"X": "{{LANGUAGE}}"})
        self.assertIn("Explain {{this}} and {{?that}} for me. {{DATA}}", a.data)
        b = K.assemble("studio-doc", "fa", instructions="Title: {{TITLE_HERE}}", verbatim={"TITLE_HERE": "{{a book}} {{LANGUAGE}}"})
        self.assertIn("Title: {{a book}} {{LANGUAGE}}", b.instructions)

    def test_the_kit_fills_what_it_holds_and_what_the_caller_gives(self):
        a = K.assemble("book-region", "it", "fr", template="{{LANGUAGE}}|{{GLOSS_LANGUAGE}}|{{LANGUAGE_CODE}}|{{GLOSS_CODE}}|{{X}}",
                       values={"X": "ok"})
        self.assertEqual(a.instructions, "Italian|French|it|fr|ok")

    def test_an_include_is_filled_like_the_template_and_may_not_hold_itself(self):
        a = K.assemble("studio-doc", "fa", template="a {{INNER}} b", includes={"INNER": "[{{LANGUAGE}}]"})
        self.assertEqual(a.instructions, "a [Persian] b")
        with self.assertRaises(K.PromptError):
            K.assemble("studio-doc", "fa", template="{{LOOP}}", includes={"LOOP": "again {{LOOP}}"})

    def test_lead_and_extras_are_the_callers_own_words_before_and_after_the_instructions(self):
        a = K.assemble("studio-doc", "fa", template="middle {{?contract}}C{{/contract}}", lead="first", extras=["last", "{{kept}}"])
        self.assertEqual(a.instructions, "first\n\nmiddle\n\nlast\n\n{{kept}}")
        self.assertEqual((a.contract, a.data), ("C", ""))

    def test_the_data_frame_of_the_template_comes_before_the_data_given_whole(self):
        a = K.assemble("studio-doc", "fa", template="i{{?data}}frame{{/data}}", data="the data")
        self.assertEqual(a.data, "frame\n\nthe data")
        self.assertEqual(a.text.rstrip().split("\n\n")[-2:], ["frame", "the data"])

    def test_the_text_is_the_header_then_the_parts_and_ends_with_one_newline(self):
        a = K.assemble("studio-doc", "fa", template="i{{?contract}}c{{/contract}}{{?data}}d{{/data}}")
        self.assertEqual(a.text, "%s\n\ni\n\nc\n\nd\n" % a.header)
        self.assertEqual(a.sizes()["total"], len(a.text))
        self.assertEqual(str(a), a.text)

    def test_a_surface_the_kit_does_not_know_is_refused(self):
        with self.assertRaises(K.PromptError):
            K.assemble("the-moon", "fa")
        with self.assertRaises(K.PromptError):
            K.parts("the-moon")


class VersionLine(unittest.TestCase):
    def test_its_shape(self):
        v = version.VERSION
        self.assertEqual(K.version_line("video-region", "fa", "en"), "Parseh prompt · video-region · fa → en · " + v)
        self.assertEqual(K.version_line("studio-doc", "it"), "Parseh prompt · studio-doc · it · " + v)
        self.assertEqual(K.version_line("book-region", "ja", "it", "regloss"),
                         "Parseh prompt · book-region · ja → it · %s · re-gloss" % v)
        self.assertEqual(K.version_line("book-region", "ja", "it", "perfield"),
                         "Parseh prompt · book-region · ja → it · %s · per field" % v)
        self.assertEqual(K.version_line("video-region", "fa", "en", "fill"),
                         "Parseh prompt · video-region · fa → en · " + v)
        self.assertEqual(K.version_line("video-new", "fa", "en", None, "my rules"),
                         "Parseh prompt · video-new · fa → en · %s · custom: my rules" % v)
        self.assertEqual(K.version_line("studio-doc", "fa", None, None, True),
                         "Parseh prompt · studio-doc · fa · %s · custom" % v)

    def test_the_version_is_read_when_the_line_is_made_and_no_template_carries_one(self):
        with mock.patch.object(version, "VERSION", "a9.9.9"):
            self.assertTrue(K.version_line("ask", "fa").endswith("a9.9.9"))
        files = list(K.TEMPLATES.values()) + [os.path.join(ROOT, "youtube", "docs", "conventions.md")]
        files += [os.path.join(K.LANG_DOCS, f) for f in os.listdir(K.LANG_DOCS)]
        for path in files:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            self.assertNotIn(version.VERSION, text, path)
            self.assertIsNone(re.search(r"\ba\d\.\d+\.\d+\b", text), path)
        self.assertIsNone(re.search(r"\ba\d\.\d+\.\d+\b", tidier.PROMPT))


class Placeholders(unittest.TestCase):
    def test_every_placeholder_a_template_names_is_published_for_its_surface(self):
        for surface in K.SURFACES:
            if surface == "ask":
                continue
            given = {n for n, _ in K.placeholders(surface)}
            template = tidier.PROMPT if surface == "transcript-tidy" else K._template(surface)
            names = set(re.findall(r"\{\{([A-Z_0-9]+)\}\}", template))
            self.assertEqual(sorted(names - given), [], surface)

    def test_the_names_the_kit_fills_itself_are_the_ones_it_publishes_and_no_others(self):
        given = ("LANGUAGE", "LANGUAGE_NATIVE", "LANGUAGE_CODE", "TR_LABEL", "LANG_CONVENTIONS",
                 "GLOSS_LANGUAGE", "GLOSS_CODE")
        for surface in ALL_SURFACES:
            published = {n for n, _ in K.placeholders(surface)}
            for name in given:
                tpl = "x {{%s}}" % name
                if name in published:
                    a = K.assemble(surface, "fa", "en" if surface in GLOSSED else None, template=tpl)
                    self.assertNotIn("{{", a.instructions, (surface, name))
                else:
                    with self.assertRaises(K.PromptError, msg=(surface, name)):
                        K.assemble(surface, "fa", "en" if surface in GLOSSED else None, template=tpl)

    def test_each_has_a_one_line_meaning(self):
        for name, meaning in K.placeholders():
            self.assertTrue(meaning and "\n" not in meaning and len(meaning) < 110, name)

    def test_what_is_published_for_one_surface_is_not_for_another(self):
        studio = {n for n, _ in K.placeholders("studio-doc")}
        self.assertIn("LANGUAGE", studio)
        self.assertNotIn("GLOSS_LANGUAGE", studio)
        self.assertNotIn("ADDRESS", studio)
        self.assertIn("ADDRESS", {n for n, _ in K.placeholders("video-region")})
        with self.assertRaises(K.PromptError):
            K.placeholders("the-moon")


# --- the language's conventions, cut per prompt -----------------------------
def _file(code):
    with open(os.path.join(K.LANG_DOCS, code + ".md"), encoding="utf-8") as f:
        return f.read()


def _headings(text):
    fenced, out = False, []
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("## "):
            out.append(line[3:].strip())
    return out


def _names(surface, code):
    return [n for n, _ in K.language_sections(surface, code)]


class LanguageCut(unittest.TestCase):
    CODES = languages.CODES

    def test_every_section_of_every_file_is_in_the_table(self):
        # a section nobody lists goes everywhere: which is right for a language
        # somebody adds, and a surprise for a shipped file -- so list it, on purpose
        for code in self.CODES + ["_template"]:
            for h in _headings(_file(code)):
                self.assertIn(h, K.SECTIONS, "%s: `## %s` is in no row of promptkit.SECTIONS" % (code, h))

    def test_the_prompts_that_take_everything_get_the_file_as_it_is(self):
        for code in self.CODES:
            raw = _file(code)
            self.assertEqual(K.language_text("book-new", code), raw.strip(), code)
            self.assertEqual(K.language_text("video-new", code),
                             re.sub(r"^# .*\n+", "", raw, count=1).strip(), code)

    def test_the_studio_takes_the_transliteration_the_reading_and_the_script_note(self):
        for code in self.CODES:
            for surface in STUDIO:
                names = _names(surface, code)
                self.assertEqual(names[0], "(title)")
                self.assertTrue({"Reading", "Transliteration"} <= set(names), (code, names))
                self.assertFalse({"Vocabulary", "Never gloss", "Chunking", "Words", "Example", "(opening)"} & set(names),
                                 (code, names))
                self.assertLessEqual(set(names) - {"(title)", "Reading", "Transliteration"}, {"The text field"})

    def test_a_region_prompt_takes_all_but_chunking_and_only_the_verbatim_paragraph(self):
        for code in self.CODES:
            secs = dict(K.language_sections("video-region", code))
            self.assertNotIn("Chunking", secs)
            self.assertNotIn("(title)", secs)
            self.assertIn("Vocabulary", secs)
            self.assertEqual(sorted(K.language_sections("video-region", code)),
                             sorted(K.language_sections("book-region", code)))
            field = secs["The text field"]
            self.assertEqual(field.count("\n\n"), 1, code)
            self.assertIn("reproduces the source **verbatim**", field, code)
            self.assertEqual(("Words" in secs), languages.get(code).words, code)

    def test_the_note_on_writing_the_script_is_found_where_it_stands(self):
        for code in ("it", "de", "fr", "es", "en"):
            text = K.language_text("studio-doc", code)
            self.assertIn("[…]{tl}", text, code)
            self.assertIn("## The text field", text, code)
            self.assertNotIn("{tl}", K.language_text("video-region", code), code)
            self.assertIn("{tl}", K.language_text("video-new", code), code)
        tr = K.language_text("studio-doc", "tr")
        self.assertIn("Runs of Turkish are **marked** in the studio", tr)
        self.assertTrue(tr.index("## The text field") < tr.index("Runs of Turkish"))
        self.assertNotIn("Chunking", tr)
        for code in ("fa", "ar", "hi", "ja", "zh"):
            self.assertNotIn("The text field", _names("studio-doc", code), code)

    def test_a_cut_only_deletes_every_paragraph_of_it_is_a_paragraph_of_the_file(self):
        for code in self.CODES:
            raw = [_flat(p) for p in re.split(r"\n\s*\n", _file(code))]
            for surface in ("studio-doc", "video-region", "book-region"):
                for name, text in K.language_sections(surface, code):
                    for p in re.split(r"\n\s*\n", text):
                        if _flat(p) not in raw and not re.match(r"^#+ ", p):
                            self.fail("%s %s: a paragraph of %s is not the file's: %s" % (code, surface, name, p[:80]))

    def test_headings_go_down_one_level_in_a_region_prompt_and_not_inside_a_fence(self):
        text = K.language_text("video-region", "fa")
        self.assertIn("\n### The text field\n", "\n" + text)
        self.assertNotIn("\n## ", "\n" + text)
        self.assertNotIn("\n### ", "\n" + K.language_text("studio-doc", "fa"))
        self.assertIn("\n## Transliteration\n", "\n" + K.language_text("studio-doc", "fa"))

    def test_the_cuts_take_out_what_the_brief_expects_of_them(self):
        # the studio prompt loses 10 - 15 K of the language file (9.8 K in Italian, 18 K in Chinese:
        # the files differ); a region prompt loses Chunking and most of The text field -- what
        # D's marking of the sources sidebar's paragraph and the opening adds is D's
        for code in self.CODES:
            whole = len(K.language_text("book-new", code))
            self.assertGreater(whole - len(K.language_text("studio-doc", code)), 9500, code)
            self.assertLess(whole - len(K.language_text("studio-doc", code)), 18500, code)
            self.assertGreater(whole - len(K.language_text("video-region", code)), 500, code)
            self.assertGreater(whole - len(K.language_text("video-region", code)), 0.04 * whole, code)

    def test_the_flags_of_a_language_file_are_resolved_per_surface(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "fa.md"), "w", encoding="utf-8") as f:
                f.write("# Persian\n\nOpen.\n\n## Vocabulary\n\n{{?book}}Book rule.{{/book}}{{?video}}Video rule.{{/video}}\n\n"
                        "## Reading\n\n{{?studio}}Studio only.{{/studio}}{{?new}}From scratch.{{/new}}{{?region}}Region.{{/region}}\n")
            with mock.patch.object(K, "LANG_DOCS", td):
                self.assertIn("Book rule.", K.language_text("book-region", "fa"))
                self.assertNotIn("Video rule.", K.language_text("book-region", "fa"))
                self.assertIn("Video rule.", K.language_text("video-new", "fa"))
                self.assertNotIn("Book rule.", K.language_text("video-new", "fa"))
                self.assertIn("Studio only.", K.language_text("studio-doc", "fa"))
                self.assertNotIn("Vocabulary", K.language_text("studio-doc", "fa"))
                self.assertIn("From scratch.", K.language_text("book-new", "fa"))
                self.assertIn("Region.", K.language_text("video-region", "fa"))
                self.assertNotIn("Studio only.", K.language_text("video-region", "fa"))
            # a flag the kit does not know is refused, in the file it is in
            with open(os.path.join(td, "fa.md"), "w", encoding="utf-8") as f:
                f.write("# P\n\n## Reading\n\n{{?nonsense}}x{{/nonsense}}\n")
            with mock.patch.object(K, "LANG_DOCS", td), self.assertRaises(K.PromptError):
                K.language_text("video-region", "fa")

    def test_a_section_nobody_listed_goes_everywhere_and_an_empty_one_goes_nowhere(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "fa.md"), "w", encoding="utf-8") as f:
                f.write("# Persian\n\n## Numbers\n\nCount.\n\n## Chunking\n\n{{?book}}Only a book.{{/book}}\n")
            with mock.patch.object(K, "LANG_DOCS", td):
                for surface in ("studio-doc", "video-region", "book-new"):
                    self.assertIn("Count.", K.language_text(surface, "fa"), surface)
                self.assertNotIn("Chunking", K.language_text("video-new", "fa"))
                self.assertIn("Only a book.", K.language_text("book-new", "fa"))

    def test_an_oddly_written_file_is_cut_by_the_same_rules(self):
        # no title of its own, a `## ` inside a code fence, one section twice, the studio's note in a
        # section the studio does not take, a text field of one paragraph: none of it breaks the cut
        odd = ("Opening words.\n\n## Reading\n\n```\n## not a heading\n\nnor this\n```\n\nAfter the fence.\n\n"
               "## The text field\n\n`fa` reproduces the source **verbatim**.\n\n## Reading\n\nAgain.\n\n"
               "## Vocabulary\n\nA rule.\n\nRuns are marked as `[x]{tl}` in the studio.\n")
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "fa.md"), "w", encoding="utf-8") as f:
                f.write(odd)
            with mock.patch.object(K, "LANG_DOCS", td):
                studio = K.language_text("studio-doc", "fa")
                self.assertEqual(studio.count("## Reading"), 2)
                self.assertIn("## not a heading\n\nnor this", studio)
                self.assertNotIn("Opening words.", studio)
                self.assertNotIn("A rule.", studio)
                self.assertIn("Runs are marked as `[x]{tl}` in the studio.", studio)
                self.assertTrue(studio.startswith("## Reading"), "no title of its own to keep")
                self.assertLess(studio.index("The text field"), studio.rindex("## Reading"), "the note stands where the file's text field does")
                region = K.language_text("video-region", "fa")
                self.assertIn("Opening words.", region)
                self.assertIn("### The text field\n\n`fa` reproduces the source **verbatim**.", region)
                self.assertIn("A rule.", region)
                self.assertNotIn("{tl}", region)
                self.assertIn("## not a heading", region, "a heading inside a fence is not one, and is not moved down")
                self.assertEqual(K.language_text("book-new", "fa"), odd.strip())

    def test_a_language_with_no_file_says_what_each_prompt_has_always_said(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(K, "LANG_DOCS", td):
            self.assertEqual(K.language_text("studio-doc", "it"), "")
            self.assertEqual(K.language_text("studio-exercises", "it"), "")
            self.assertTrue(K.language_text("video-region", "it").endswith("Use a standard, consistent romanisation.)"))
            self.assertTrue(K.language_text("video-new", "it").endswith("say which in a note.)"))
            self.assertIn("Ask for them before annotating.", K.language_text("book-new", "it"))
            self.assertEqual(K.language_sections("video-region", "it"), None)
            with self.assertRaises(K.PromptError):
                K.language_text("transcript-tidy", "it")


# --- the assemblers and their routes ------------------------------------------
class Handler(object):
    def __init__(self, body=None, query=None):
        self.body, self.query, self.answer = body or {}, query or {}, None

    def _json_body(self):
        return self.body

    def send_json(self, answer, code=200):
        self.answer = answer


class Assemblers(ControlledMachine):
    def test_the_readers_of_a_language_file_all_read_through_the_kit(self):
        for code in languages.CODES:
            L = languages.get(code)
            self.assertEqual(ytpages.lang_conventions(L), K.language_text("video-new", code))
            self.assertEqual(newbook.conventions(L), K.language_text("book-new", code))
            self.assertEqual(studio_server.lang_block(code), K.language_text("studio-doc", code))
        # and none keeps a path of its own to the files it used to read
        for module, name in ((glossregion, "LANG_DOCS"), (ytpages, "LANG_DOCS"), (studio_server, "DOCS_LANG")):
            self.assertFalse(hasattr(module, name), "%s still has its own %s" % (module.__name__, name))

    def test_the_studio_route_keeps_its_shape_and_adds_the_kits(self):
        h = Handler(query={"target": ["it"]})
        studio_server.api_prompt_get(h)
        a = h.answer
        for key in ("text", "custom", "target", "target_name", "lang_block"):
            self.assertIn(key, a)
        self.assertFalse(a["custom"])
        self.assertNotIn("{{", a["text"])
        self.assertIn("creating a markdown file", a["text"], "the page's own composition has the contract, in place")
        self.assertEqual(a["lang_block"], K.language_text("studio-doc", "it"))
        built = studio_server.studio_prompt(languages.get("it"))
        self.assertEqual((a["prompt"], a["header"], a["contract"]), (built.text, built.header, built.contract))
        self.assertTrue(a["prompt"].startswith(K.version_line("studio-doc", "it") + "\n\ntarget: it — this document is about Italian"))
        self.assertTrue(a["prompt"].rstrip().endswith(a["contract"].rstrip()))
        self.assertLess(a["prompt"].index(a["lang_block"][:60]), a["prompt"].index(a["contract"][:60]))

    def test_the_studio_route_for_a_custom_prompt_is_the_persons_text_whole_and_still_has_the_contract_after_it(self):
        with mock.patch.object(studio_server.store, "get_prompt", lambda: {"text": "Custom rules.", "custom": True}):
            h = Handler(query={"target": ["ar"]})
            studio_server.api_prompt_get(h)
        a = h.answer
        self.assertEqual(a["text"], "Custom rules.")
        self.assertIn("Mixed-direction sequences for Arabic — binding", a["lang_block"])
        self.assertTrue(a["header"].endswith(" · custom"))
        self.assertLess(a["prompt"].index("Custom rules."), a["prompt"].index("creating a markdown file"))
        self.assertNotIn("prompt_error", a)

    def test_a_custom_prompt_the_kit_refuses_is_told_and_the_page_keeps_its_text(self):
        with mock.patch.object(studio_server.store, "get_prompt", lambda: {"text": "Say {{THIS}}.", "custom": True}):
            h = Handler(query={"target": ["fa"]})
            studio_server.api_prompt_get(h)
        self.assertEqual(h.answer["text"], "Say {{THIS}}.")
        self.assertIn("THIS", h.answer["prompt_error"])
        self.assertNotIn("prompt", h.answer)

    def test_the_exercise_route_keeps_its_shape_and_the_authoring_prompts_contract_is_not_in_it(self):
        h = Handler({"markdown": "---\ntitle: T\ntarget: fa\n---\n\nLesson", "decks": []})
        studio_server.api_exercise_prompt(h)
        self.assertEqual(sorted(h.answer), ["prompt", "vocabulary"])
        p = h.answer["prompt"]
        self.assertTrue(p.startswith(K.version_line("studio-exercises", "fa")))
        self.assertIn("Return the complete updated Markdown document in one fenced", p)
        self.assertNotIn("actual `.md` file", p)
        self.assertTrue(p.rstrip().endswith("```"))

    def test_the_region_routes_hand_out_the_prompt_the_lab_builds(self):
        for surface, fn, args in (("video-region", glossregion.video_prompt,
                                   (promptlab._fixture("videos", languages.get("fa"))[0], 0, 3)),
                                  ("book-region", glossregion.book_prompt,
                                   (promptlab._fixture("books", languages.get("fa"))[0], 0, 5))):
            for kw, mode in (({}, None), ({"regloss": True}, "regloss"), ({"perfield": True}, "perfield")):
                r = fn(*args, **kw)
                self.assertEqual(r["prompt"], promptlab.build(surface, "fa", mode).text)
                self.assertTrue(r["prompt"].startswith(K.version_line(surface, "fa", "en", mode)))

    def test_a_prompt_the_kit_refuses_is_a_refusal_in_words_not_a_crash(self):
        book = promptlab._fixture("books", languages.get("fa"))[0]
        with mock.patch.object(glossregion.promptkit, "assemble", side_effect=K.PromptError("it still carries {{X}}")):
            with self.assertRaises(glossregion.Refused) as e:
                glossregion.book_prompt(book, 0, 5)
        self.assertIn("the prompt could not be made", str(e.exception))

    def test_a_title_that_says_double_braces_is_a_title(self):
        # the book's and the video's own words are put in as they are, never taken for a placeholder
        book = promptlab._fixture("books", languages.get("it"))[0]
        with tempfile.TemporaryDirectory() as td:
            copy = os.path.join(td, "italian", "mini-it")
            shutil.copytree(book, copy)
            path = os.path.join(copy, "book.json")
            with open(path, encoding="utf-8") as f:
                text = f.read()
            with open(path, "w", encoding="utf-8") as f:
                f.write(text.replace("Il pezzo di legno", "Il {{DATA}} e {{LANGUAGE}}"))
            r = glossregion.book_prompt(copy, 0, 5)
        self.assertIn("- title: Il {{DATA}} e {{LANGUAGE}}", r["prompt"])

    def test_a_language_file_that_names_what_nothing_fills_is_refused_by_every_route_in_words(self):
        # a language file whose text says {{GLOSS_LANGUAGE}} where no gloss language is known
        # (the studio's, or the new-book page's, which fills the rest in a browser)
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "fa.md"), "w", encoding="utf-8") as f:
                f.write("# Persian\n\n## Reading\n\nGloss it in {{GLOSS_LANGUAGE}}, for {{LANGUAGE}}.\n")
            with mock.patch.object(K, "LANG_DOCS", td):
                self.assertEqual(K.language_text("studio-doc", "fa").splitlines()[-1],
                                 "Gloss it in {{GLOSS_LANGUAGE}}, for Persian.")
                self.assertIn("in English, for Persian", K.language_text("video-new", "fa", gloss="en"))
                h = Handler({"markdown": "---\ntitle: T\ntarget: fa\n---\n\nx", "decks": []})
                studio_server.api_exercise_prompt(h)
                self.assertIn("GLOSS_LANGUAGE", h.answer["error"])
                h = Handler(query={"target": ["fa"]})
                studio_server.api_prompt_get(h)
                self.assertIn("GLOSS_LANGUAGE", h.answer["prompt_error"])
                self.assertNotIn("prompt", h.answer)

    def test_the_conventions_the_new_book_page_embeds_have_no_placeholder_left(self):
        # the page fills its template in a browser and never looks into what it embeds
        for code in languages.CODES:
            self.assertNotIn("{{", newbook.conventions(languages.get(code)), code)

    def test_the_video_prompt_before_and_with_its_captions(self):
        before = ytpages.chat_prompt(None, "fa")
        self.assertEqual(before, ytpages.assembled_chat(None, "fa").text)
        self.assertTrue(before.startswith(K.version_line("video-new", "fa", "en")))
        caps = [{"start": 3, "text": "سلام {{x}}", "plain": False}]
        full = ytpages.full_prompt("fA6bK2mQ8sT", {"title": "T {{t}}", "channel": "C"}, caps, None, "fa", "en")
        self.assertTrue(full.startswith(before))
        self.assertIn("سلام {{x}}", full)
        self.assertIn("- title: T {{t}}", full)
        self.assertTrue(full.rstrip().endswith("Now answer with the JSON, and nothing else."))

    def test_the_video_prompt_without_an_example_has_no_hole_and_with_one_has_it(self):
        self.assertNotIn("## An example, from a video already in the player", ytpages.chat_prompt(None, "fa"))
        example = ("[0] 3s  سلام", '{"captions": []}', "")
        with mock.patch.object(ytpages, "_example", lambda L: example):
            p = ytpages.chat_prompt(None, "fa")
        self.assertIn("## An example, from a video already in the player", p)
        self.assertIn("Received:\n\n```\n[0] 3s  سلام\n```", p)
        self.assertNotIn("\n\n\n", p)

    def test_the_tidy_prompt(self):
        caps = [{"start": 1, "text": "سلام {{x}} سلام"}]
        p = tidier.prompt(caps, "fa")
        self.assertTrue(p.startswith(K.version_line("transcript-tidy", "fa")))
        self.assertIn("سلام {{x}} سلام", p)
        self.assertTrue(p.rstrip().endswith("```"))
        self.assertLess(p.index("WHAT TO GIVE BACK"), p.index("THE TRANSCRIPT:"))
        self.assertLess(p.index("THE RULES"), p.index("WHAT TO GIVE BACK"), "the contract comes after the rules")

    def test_the_new_book_template_has_no_marks_once_its_parts_are_taken_out(self):
        tpl = K.flat(K._template("book-new"))
        self.assertNotIn("{{?", tpl)
        self.assertNotIn("{{/", tpl)
        self.assertIn("{{WORDS_STEP}}", tpl)
        self.assertIn("### The per-paragraph JSON", tpl)


class StudioPromptRoutes(unittest.TestCase):
    """The routes that edit the studio's prompt, on a temporary library: the page
    edits and copies a text and knows no marks, so none is ever handed to it."""

    def test_none_of_them_hands_out_the_mark_of_a_part_and_a_custom_text_is_kept_whole(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(studio_server.store, "LIB", studio_server.Path(td)):
            h = Handler(query={"target": ["fa"]})
            studio_server.api_prompt_get(h)
            self.assertFalse(h.answer["custom"])
            self.assertNotIn("{{", h.answer["text"])
            self.assertIn("creating a markdown file", h.answer["text"])
            h = Handler({"text": "My own prompt."})
            studio_server.api_prompt_put(h)
            self.assertEqual(h.answer, {"text": "My own prompt.", "custom": True})
            h = Handler(query={"target": ["fa"]})
            studio_server.api_prompt_get(h)
            self.assertEqual((h.answer["text"], h.answer["custom"]), ("My own prompt.", True))
            self.assertTrue(h.answer["prompt"].startswith(K.version_line("studio-doc", "fa", None, None, True)))
            h = Handler()
            studio_server.api_prompt_delete(h)
            self.assertFalse(h.answer["custom"])
            self.assertNotIn("{{", h.answer["text"])
            self.assertIn("creating a markdown file", h.answer["text"])
            self.assertEqual(h.answer["text"], studio_server.promptkit.flat(studio_server.store.default_prompt()))
            self.assertFalse(os.path.exists(os.path.join(td, "_prompt.md")))


if __name__ == "__main__":
    unittest.main()
