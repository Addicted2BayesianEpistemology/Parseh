#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The skills for a chatbot (lib/skills.py, brief §9 of a0.4.2).

    python3 -m unittest tests/test_skills.py

WHAT IS HELD:

  * EACH SKILL IS A VALID Agent Skill by the rules the vendors' own documents give (docs/prompt-kit.md, the
    checked facts): the front matter has `name` and `description` and nothing else, the description is short and
    free of angle brackets, SKILL.md is under 500 lines and names every reference;
  * THE ZIP is unpacked and checked again (one top-level folder named like the skill, SKILL.md in capitals, only
    references/ beside it), and the same files give the same bytes;
  * THE TWO ROADS ARE ONE, the test the brief asks for: for every request a page can make -- every surface and
    mode of a stretch, every language and every choice of the options, every box set the studio can produce,
    every exercise type, and a book's method -- what the skill tells a model to read (its files, their marks
    settled from the request's header alone, by lib/skills.py `read_*`) is exactly what the prompt road makes of
    the same request.  The comparison is shown to bite: a word changed in a file, or in a source, is seen;
  * THE SHORT REQUEST carries the hash of the skill built now, the header parses and goes round, a person's
    prompt of kind `added` follows it and one that replaces Parseh's is refused in words;
  * THE ASR SKILLS are none of this module's: nothing here reads them, and no sentence counts the skills.
"""
import difflib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in ("lib", "markdown/app", "markdown/exlex", "markdown", "youtube/lib"):
    sys.path.insert(0, os.path.join(ROOT, _p))
import glossregion                                                  # noqa: E402
import languages                                                    # noqa: E402
import promptboxes                                                  # noqa: E402
import promptkit                                                    # noqa: E402
import promptlab                                                    # noqa: E402
import skills                                                       # noqa: E402
import server as studio                                             # noqa: E402

PAGE = "---\ntitle: T\ntarget: %s\n---\n\nLesson"
METHOD = ("# The method\n\nYou make a book in {{BOOK_DIR}} with {{PYTHON}}. Its language is {{LANGUAGE}}, its meanings "
          "{{GLOSS_LANGUAGE}}.\n\n{{?marks}}Write the short vowels.{{/marks}}{{?nomarks}}Leave `fa` as it is."
          "{{/nomarks}}{{?ipa}} Write IPA.{{/ipa}}\n\n{{LANG_CONVENTIONS}}\n\n{{MEANING_RULE}}\n\nSee batches.md.\n")
BATCHES = "# Batches\n\nTen paragraphs a batch, in {{BOOK_DIR}}.\n"
SKILLS = {}
TMP = None


def setUpModule():
    global TMP
    TMP = tempfile.mkdtemp(prefix="skills-test-")
    # lane H's docs/book-method/ is another lane's: its contract (method.md is the entry, every other *.md a
    # reference) is held here with a folder of the test's own
    for n, t in (("method.md", METHOD), ("batches.md", BATCHES)):
        with open(os.path.join(TMP, n), "w", encoding="utf-8") as f:
            f.write(t)
    SKILLS["parseh-gloss"] = skills._build_gloss()
    SKILLS["parseh-markdown"] = skills._build_markdown()
    SKILLS["parseh-book"] = skills.build("parseh-book", TMP)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def diff(a, b, n=8):
    return "\n".join(l[:200] for l in list(difflib.unified_diff(a.split("\n"), b.split("\n"), lineterm="", n=0))[:n])


class SkillsAreValid(unittest.TestCase):
    def test_each_skill_passes_the_rules(self):
        for name, sk in SKILLS.items():
            with self.subTest(skill=name):
                self.assertEqual(skills.validate(sk), [])
                self.assertEqual(sk.name, name)
                self.assertLess(len(sk.files["SKILL.md"].split("\n")), skills.MAX_LINES)

    def test_the_description_is_the_trigger(self):
        for name, sk in SKILLS.items():
            d = re.search(r'^description: "(.*)"$', sk.files["SKILL.md"], re.M).group(1)
            self.assertLessEqual(len(d), 200)
            self.assertNotRegex(d, r"[<>]")
            self.assertIn("Use when a message begins 'Parseh request · %s'" % name, d)
            # the front matter is name and description, nothing else
            fm = re.match(r"---\n(.*?)\n---\n", sk.files["SKILL.md"], re.S).group(1).split("\n")
            self.assertEqual([l.split(":")[0] for l in fm], ["name", "description"])

    def test_the_validator_refuses_what_the_tools_refuse(self):
        sk = SKILLS["parseh-gloss"]
        files = dict(sk.files)
        bad = skills.Skill("parseh-gloss", dict(files, **{"SKILL.md": files["SKILL.md"].replace(
            "---\nname", "---\nargument-hint: x\nname", 1)}), "", "")
        self.assertTrue(any("front matter" in p for p in skills.validate(bad)))
        bad = skills.Skill("parseh-gloss", dict(files, **{"SKILL.md": files["SKILL.md"].replace(
            "Glosses the chunks", "Glosses <b>the</b> chunks", 1)}), "", "")
        self.assertTrue(any("description" in p for p in skills.validate(bad)))
        bad = skills.Skill("parseh-gloss", dict(files, **{"references/loose.md": "x"}), "", "")
        self.assertTrue(any("not named" in p for p in skills.validate(bad)))
        bad = skills.Skill("claude-gloss", {"SKILL.md": files["SKILL.md"].replace("name: parseh-gloss",
                                                                                    "name: claude-gloss")}, "", "")
        self.assertTrue(any("reserved" in p for p in skills.validate(bad)))

    def test_every_box_and_every_type_has_its_file_and_is_named(self):
        # the catalogue is data: a box the studio gains (colourparts of a0.4.3 among them) comes out of the
        # generator with its file, and SKILL.md says which `features:` value opens it
        sk = SKILLS["parseh-markdown"]
        for b in promptboxes.BOXES:
            self.assertIn("references/features/%s.md" % b.id, sk.files)
            self.assertIn("| %s | " % b.id, sk.files["SKILL.md"])
        for t in promptboxes.TYPES:
            self.assertIn("references/exercises/%s.md" % t.id, sk.files)
            self.assertIn("references/exercises/%s.md" % t.id, sk.files["SKILL.md"])
        self.assertIn("colourparts", promptboxes.BOX_IDS)

    def test_a_request_naming_a_feature_points_the_reader_at_it(self):
        sk = SKILLS["parseh-markdown"]
        for b in promptboxes.BOXES:
            L = languages.get("fa")
            if b.id not in promptboxes.shown_ids(L):
                continue
            with_it = skills.read_markdown(sk.files, skills.render_header(
                "parseh-markdown", sk.version, sk.hash, skills.WHAT["studio-doc"], "fa",
                fields=[("features", b.id), ("level", "not said"), ("length", "not said")]))
            without = skills.read_markdown(sk.files, skills.render_header(
                "parseh-markdown", sk.version, sk.hash, skills.WHAT["studio-doc"], "fa",
                fields=[("features", "none"), ("level", "not said"), ("length", "not said")]))
            # what the file says before its first mark (a name or a condition) is in the rules once the feature is named
            body = skills.body_of(sk.files["references/features/%s.md" % b.id]).strip()
            first = re.split(r"[⟦⟨]", body)[0]
            if len(first) > 15:
                self.assertIn(first, with_it["instructions"], b.id)
            self.assertNotEqual(with_it["instructions"], without["instructions"], b.id)

    def test_the_colour_inside_a_word_box_is_in_the_always_in_reserved_list(self):
        sk = SKILLS["parseh-markdown"]
        none = skills.read_markdown(sk.files, skills.render_header(
            "parseh-markdown", sk.version, sk.hash, skills.WHAT["studio-doc"], "it",
            fields=[("features", "none"), ("level", "not said"), ("length", "not said")]))
        self.assertIn("[[ab[cd]{teal}ef]]", none["instructions"])
        self.assertNotIn("**Colour inside a word.**", none["instructions"])


class TheZip(unittest.TestCase):
    def test_unpacked_it_is_laid_out_as_the_tools_want(self):
        for name, sk in SKILLS.items():
            with self.subTest(skill=name):
                data = sk.zip_bytes()
                self.assertEqual(skills.check_zip(name, data), [])
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    names = z.namelist()
                self.assertTrue(all(n.startswith(name + "/") for n in names))
                self.assertIn(name + "/SKILL.md", names)
                self.assertEqual({n.split("/")[1] for n in names if n != name + "/SKILL.md"}, {"references"})
                self.assertFalse([n for n in names if re.search(r"__pycache__|\.pyc|\.DS_Store", n)])

    def test_the_same_files_give_the_same_bytes_and_the_same_hash(self):
        a = skills._build_gloss()
        b = skills._build_gloss()
        self.assertEqual(a.zip_bytes(), b.zip_bytes())
        self.assertEqual(a.hash, b.hash)
        self.assertEqual(skills.build("parseh-gloss").hash, a.hash)
        self.assertIn("`%s`" % a.hash, a.files["SKILL.md"])

    def test_one_changed_word_of_a_source_changes_the_hash(self):
        # the meaning rule is a part of every gloss prompt: change one word in a copy of it
        with open(promptkit.MEANING_RULE, encoding="utf-8") as f:
            text = f.read()
        alt = os.path.join(TMP, "meaning-rule.md")
        with open(alt, "w", encoding="utf-8") as f:
            f.write(text.replace("gloss", "glose", 1))
        before = skills._build_gloss().hash
        with mock.patch.object(promptkit, "MEANING_RULE", alt):
            after = skills._build_gloss().hash
        self.assertNotEqual(before, after)
        # and a request made for the old one is seen to be stale by what the header says
        line = skills.render_header("parseh-gloss", "a0.4.2", before, skills.WHAT["video-region"], ("fa", "en"), "fill")
        self.assertNotEqual(skills.parse_header(line)["hash"], after)

    def test_a_cache_is_rebuilt_when_a_source_changes(self):
        a = skills.build("parseh-markdown")
        self.assertIs(a, skills.build("parseh-markdown"))
        with mock.patch.object(skills, "_fingerprint", return_value=("changed",)):
            self.assertIsNot(a, skills.build("parseh-markdown"))
        skills._CACHE.clear()


class TheRequestHeader(unittest.TestCase):
    def test_a_header_goes_round(self):
        for line, want in [
            (skills.render_header("parseh-gloss", "a0.4.2", "k7f3", "a stretch of a video", ("fa", "en"), "regloss"),
             {"what": "a stretch of a video", "lang": "fa", "gloss": "en", "mode": "regloss"}),
            (skills.render_header("parseh-gloss", "a0.4.2", "k7f3", "a video from scratch", ("ja", "it"), None,
                                  [("translit", "ipa")]),
             {"what": "a video from scratch", "lang": "ja", "gloss": "it", "translit": "ipa"}),
            (skills.render_header("parseh-markdown", "a0.4.2", "k7f3", "a document", "fa",
                                  fields=[("features", "vocab, gloss"), ("level", "not said"),
                                          ("length", "about a page"), ("custom", "mine")]),
             {"what": "a document", "lang": "fa", "features": "vocab, gloss", "length": "about a page",
              "custom": "mine"})]:
            got = skills.parse_header(line)
            for k, v in want.items():
                self.assertEqual(got[k], v)
            self.assertEqual(got["hash"], "k7f3")
            # the first line only, and what follows ` — ` is no field
            self.assertEqual(skills.parse_header(line + "\n\n{data}")["what"], want["what"])
            self.assertIn(" — no skill called", line)

    def test_what_is_not_a_header_is_refused_in_words(self):
        for bad in ("hello", "Parseh request · parseh-nothing · a0.4.2 · k7f3 · a document",
                    "Parseh prompt · video-region · fa → en · a0.4.2",
                    "Parseh request · parseh-gloss · a0.4.2 · k7f3 · a stretch of a video · fa → en · nonsense"):
            with self.assertRaises(skills.SkillError):
                skills.parse_header(bad)

    def test_the_header_of_a_request_is_not_the_version_line_of_a_prompt(self):
        a = promptlab.build("video-region", "fa", "fill", None, {})
        self.assertTrue(a.header.startswith("Parseh prompt · "))
        r = skills.for_region("video-region", a, languages.get("fa"), languages.gloss_or_default("en"), "fill")
        self.assertTrue(r["text"].startswith("Parseh request · parseh-gloss · "))
        self.assertEqual(skills.parse_header(r["text"])["skill"], "parseh-gloss")


def compare(case, got, expected, what):
    if got != expected:
        case.fail("%s\n%s" % (what, diff(expected, got)))


class TheTwoRoadsAreOneForTheGlossSkill(unittest.TestCase):
    """A stretch of a book or of a video in every language, mode and choice of the options; a video from scratch."""

    def road(self, surface, code, mode, gloss, translit, marks):
        L = languages.get(code)
        opts = {"translit": translit, "marks": marks}
        if surface != "video-new" and gloss not in (None, "en"):
            # a stretch is glossed in its book's or its video's own gloss language (its record): the prompt of one
            # whose meanings are in another language, made without a fixture
            ctx = skills._region_ctx(surface.split("-")[0], L, languages.gloss_or_default(gloss))
            a, _n = glossregion.assembled(ctx, [], {"fill": "fill", "perfield": "perfield", "regloss": "regloss"}[mode],
                                          options=opts)
        else:
            a = promptlab.build(surface, code, mode, gloss, opts)
        expected = promptkit.squeeze("\n\n".join(x for x in (a.instructions, a.contract) if x))
        header = skills.render_header("parseh-gloss", "a0.4.2", SKILLS["parseh-gloss"].hash, skills.WHAT[surface],
                                      (code, gloss or "en"), mode if surface != "video-new" else None,
                                      skills._fields_of(surface, L, translit, marks))
        return skills.read_gloss(SKILLS["parseh-gloss"].files, header), expected

    def test_every_stretch_in_every_language_and_mode(self):
        sk = SKILLS["parseh-gloss"]
        n = 0
        for L in languages.LANGS.values():
            for translit, marks in skills._variants("video-region", L):
                for surface in ("book-region", "video-region"):
                    for mode in skills.MODES:
                        got, expected = self.road(surface, L.code, mode, "en", translit, marks)
                        compare(self, got, expected, "%s %s %s %s %s" % (surface, L.code, mode, translit, marks))
                        n += 1
        self.assertGreater(n, 100)
        self.assertEqual(sk.name, "parseh-gloss")

    def test_the_language_the_meanings_are_in_is_the_headers(self):
        for gloss in languages.GLOSS_CODES:
            got, expected = self.road("video-region", "fa", "regloss", gloss, "classic", "nomarks")
            compare(self, got, expected, "gloss " + gloss)

    def test_a_video_from_scratch_in_every_language(self):
        for L in languages.LANGS.values():
            for translit, marks in skills._variants("video-new", L):
                got, expected = self.road("video-new", L.code, None, "en", translit, marks)
                compare(self, got, expected, "video-new %s %s %s" % (L.code, translit, marks))

    def test_a_video_from_scratch_in_another_gloss_language(self):
        got, expected = self.road("video-new", "ja", None, "it", "classic", "nomarks")
        compare(self, got, expected, "video-new ja it")

    def test_the_comparison_bites(self):
        sk = SKILLS["parseh-gloss"]
        got, expected = self.road("video-region", "it", "fill", "en", "classic", "nomarks")
        files = dict(sk.files)
        path = "references/stretch/it.md"
        files[path] = files[path].replace("chunk", "chink", 1)
        header = skills.render_header("parseh-gloss", "a0.4.2", sk.hash, skills.WHAT["video-region"], ("it", "en"),
                                      "fill", [])
        self.assertNotEqual(skills.read_gloss(files, header), expected)
        # a mode's words the reader takes for another: the file no longer says what the prompt says
        header = skills.render_header("parseh-gloss", "a0.4.2", sk.hash, skills.WHAT["video-region"], ("it", "en"),
                                      "regloss", [])
        self.assertNotEqual(skills.read_gloss(sk.files, header), expected)

    def test_every_language_of_the_registry_has_its_files(self):
        sk = SKILLS["parseh-gloss"]
        for L in languages.LANGS.values():
            self.assertIn("references/stretch/%s.md" % L.code, sk.files)
            self.assertIn("references/scratch/%s.md" % L.code, sk.files)
            self.assertIn("`%s`" % L.code, sk.files["SKILL.md"])

    def test_a_language_a_person_added_has_files_too(self):
        # the skill is made from this machine's registry: a language added to it (lib/newlang.py writes the personal
        # store) comes out the same way, with the files the options give it
        base = languages.get("it")
        rec = dict(base.__dict__)
        extra = languages.Lang("xx", {"name": "Testish", "native": "Testish", "folder": "testish", "script": "latin"})
        with mock.patch.dict(languages.LANGS, {"xx": extra}):
            sk = skills._build_gloss()
            self.assertIn("references/stretch/xx.md", sk.files)
            self.assertIn("references/scratch/xx-ipa.md", sk.files)
            self.assertEqual(skills.validate(sk), [])
            self.assertTrue(rec)


class TheTwoRoadsAreOneForTheMarkdownSkill(unittest.TestCase):
    def doc_road(self, code, boxes, level, length, translit):
        L = languages.get(code)
        sk = SKILLS["parseh-markdown"]
        a = studio.studio_prompt(L, boxes=boxes, level=level, length=length, translit=translit)
        named = skills._named(L, promptboxes.ticked(boxes), False)
        fields = [("features", ", ".join(named) or "none"), ("level", skills._level_name(level)),
                  ("length", skills._length_name(length))] + \
            [tuple(f.split(": ", 1)) for f in promptkit.header_fields("studio-doc", L, {"translit": translit})]
        got = skills.read_markdown(sk.files, skills.render_header("parseh-markdown", "a0.4.2", sk.hash,
                                                                  skills.WHAT["studio-doc"], code, fields=fields))
        # the real prompt after its version line and its target line, in its three parts
        expected = {"instructions": a.instructions.split("\n\n", 1)[1], "contract": a.contract, "data": a.data}
        for k in expected:
            compare(self, got[k], expected[k], "%s %s %s %s" % (code, k, boxes, translit))

    def test_every_box_alone_in_every_language(self):
        for L in languages.LANGS.values():
            for b in promptboxes.BOX_IDS:
                self.doc_road(L.code, [b], "", "", "classic")

    def test_the_presets_and_all_and_none_in_every_language(self):
        for L in languages.LANGS.values():
            for p in promptboxes.PRESETS:
                for translit, _m in skills._variants("studio-doc", L):
                    self.doc_road(L.code, list(p.boxes), "intermediate", "page", translit)

    def test_the_default_boxes_and_a_level_and_a_length(self):
        for level in [i for i, _n, _l in promptboxes.LEVELS]:
            for length in [i for i, _n, _l in promptboxes.LENGTHS]:
                self.doc_road("it", None, level, length, "classic")

    def test_every_exercise_type_in_every_language(self):
        sk = SKILLS["parseh-markdown"]
        for L in languages.LANGS.values():
            for types in [[t] for t in promptboxes.TYPE_IDS] + [list(promptboxes.TYPE_IDS)]:
                for boxes in ([], ["lists", "colourparts", "colours"], list(promptboxes.BOX_IDS)):
                    for translit, _m in skills._variants("studio-exercises", L)[:2]:
                        a, _rows = studio.exercise_prompt(PAGE % L.code, (), boxes=boxes, types=types,
                                                          translit=translit)
                        named = skills._named(L, a.boxes, True)
                        fields = [("features", ", ".join(named) or "none"), ("types", ", ".join(a.types)),
                                  ("level", "not said"), ("length", "not said")] + \
                            [tuple(f.split(": ", 1)) for f in promptkit.header_fields("studio-exercises", L,
                                                                                      {"translit": translit})]
                        got = skills.read_markdown(sk.files, skills.render_header(
                            "parseh-markdown", "a0.4.2", sk.hash, skills.WHAT["studio-exercises"], L.code,
                            fields=fields))
                        options = promptkit.resolve("studio-exercises", L, {"translit": translit})
                        ex = promptkit.assemble("studio-exercises", L, options=options,
                                                flags=promptboxes.flags(L, a.boxes, a.types, exercising=True))
                        expected = {
                            "instructions": "\n\n".join(x for x in (ex.instructions, ex.contract) if x),
                            "dialect": promptboxes.dialect_text(L, a.boxes, a.types, options),
                            "conventions": promptkit.language_text("studio-exercises", L, options=options),
                            "guidance": studio._rtl_markdown_guidance(L, exercises=True) if L.dir == "rtl" else ""}
                        for k, v in expected.items():
                            compare(self, got[k], v, "exercises %s %s %s %s" % (L.code, k, types, boxes))
                            # and each part is a part of the prompt the page would have handed out
                            if k != "instructions" and v:
                                self.assertIn(v, a.instructions)
                        self.assertIn(ex.instructions, a.instructions)
                        self.assertEqual(ex.contract, a.contract)

    def test_the_comparison_bites(self):
        sk = SKILLS["parseh-markdown"]
        files = dict(sk.files)
        files["references/features/vocab.md"] = files["references/features/vocab.md"].replace("headword", "headwurd")
        h = skills.render_header("parseh-markdown", "a0.4.2", sk.hash, skills.WHAT["studio-doc"], "it",
                                 fields=[("features", "vocab"), ("level", "not said"), ("length", "not said")])
        a = studio.studio_prompt(languages.get("it"), boxes=["vocab"])
        self.assertNotEqual(skills.read_markdown(files, h)["instructions"], a.instructions.split("\n\n", 1)[1])


class TheTwoRoadsAreOneForTheBookSkill(unittest.TestCase):
    """Against a folder of method files of the test's own: lane H's docs/book-method/ is read by the same code."""

    def values(self, L, G):
        return {"BOOK_DIR": "/x/books/b", "PYTHON": "/usr/bin/python3"}

    def test_the_method_and_what_it_points_at_are_what_the_prompt_road_makes(self):
        sk = SKILLS["parseh-book"]
        for code in ("fa", "it", "ja", "ar"):
            L = languages.get(code)
            G = languages.gloss_or_default("en")
            for translit, marks in skills._variants("book-new", L):
                r = skills.for_book(L, G, {"translit": translit, "marks": marks}, self.values(L, G), 1000,
                                    sources=TMP)
                self.assertTrue(r["available"], r)
                header = r["text"].split("\n")[0]
                data = json.loads(r["text"].split("```json\n")[1].split("\n```")[0])
                got = skills.read_book(sk.files, header, data)
                options = promptkit.resolve("book-new", L, {"translit": translit, "marks": marks})
                values = dict(promptkit._common("book-new", L, G, options), **self.values(L, G))
                flags = dict(promptkit.surface_flags("book-new", L, options))
                conv = promptkit.language_text("book-new", L, options=options)
                meaning = promptkit.render(promptkit._meaning_rule(), flags, values, {}, "meaning")
                inc = {"LANG_CONVENTIONS": conv, "MEANING_RULE": meaning}
                expected = promptkit.squeeze(promptkit.render(METHOD, flags, values, inc, "method"))
                compare(self, got, expected, "book %s %s %s" % (code, translit, marks))

    def test_what_the_method_says_that_nothing_in_a_request_decides_is_refused(self):
        d = tempfile.mkdtemp(dir=TMP)
        with open(os.path.join(d, "method.md"), "w", encoding="utf-8") as f:
            f.write("# M\n\n{{?something_new}}x{{/something_new}}\n")
        with self.assertRaises(skills.SkillError):
            skills.build("parseh-book", d)

    def test_a_tree_without_the_method_has_no_book_skill_and_says_why(self):
        d = tempfile.mkdtemp(dir=TMP)
        r = skills.for_book(languages.get("fa"), languages.gloss_or_default("en"), {}, {}, 10, sources=d)
        self.assertFalse(r["available"])
        self.assertIn("method.md", r["why"])


class TheShortRequest(unittest.TestCase):
    def test_a_stretch_carries_the_hash_and_the_data_and_is_smaller_than_the_prompt(self):
        L, G = languages.get("fa"), languages.gloss_or_default("en")
        a = promptlab.build("video-region", "fa", "regloss", None, {"translit": "ipa", "marks": "marks"})
        r = skills.for_region("video-region", a, L, G, "regloss")
        self.assertTrue(r["available"])
        head, rest = r["text"].split("\n\n", 1)
        h = skills.parse_header(head)
        self.assertEqual(h["hash"], skills.build("parseh-gloss").hash)
        self.assertEqual((h["translit"], h["marks"], h["mode"], h["lang"], h["gloss"]), ("ipa", "on", "regloss", "fa", "en"))
        self.assertEqual(rest.strip(), a.data.strip())
        self.assertLess(r["chars"], r["prompt_chars"] / 2)
        self.assertEqual(r["prompt_chars"], len(a.text))

    def test_a_prompt_of_the_persons_added_to_parsehs_follows_the_header_and_one_in_its_place_cannot_travel(self):
        L, G = languages.get("it"), languages.gloss_or_default("en")
        a = promptlab.build("video-region", "it", "fill", None, {})
        added = mock.Mock(kind="added", text="Prefer British spellings.", name="mine")
        added.name = "mine"
        r = skills.for_region("video-region", a, L, G, "fill", added)
        self.assertIn(skills.ADDED_LEAD + "\nPrefer British spellings.", r["text"])
        self.assertEqual(skills.parse_header(r["text"])["custom"], "mine")
        self.assertLess(r["text"].index("Prefer British"), r["text"].index(a.data[:20]))
        replaced = mock.Mock(kind="replace", text="Do it my way.")
        replaced.name = "mine"
        r = skills.for_region("video-region", a, L, G, "fill", replaced)
        self.assertFalse(r["available"])
        self.assertIn("copy the prompt", r["why"])

    def test_a_studio_request_is_the_header_alone_and_names_the_boxes(self):
        L = languages.get("fa")
        a = studio.studio_prompt(L, boxes=["vocab", "reading"], level="beginner", length="short")
        r = skills.for_studio(L, a, ["vocab", "reading"], "beginner", "short")
        h = skills.parse_header(r["text"])
        self.assertEqual((h["features"], h["level"], h["length"]), ("vocab", "beginner", "short"))   # fa has no reading
        self.assertLess(r["chars"], 700)

    def test_an_exercise_request_holds_the_page_and_not_the_level_lines_twice(self):
        L = languages.get("it")
        a, _rows = studio.exercise_prompt(PAGE % "it", (), boxes=["lists"], types=["flashcard"], level="advanced",
                                          length="short")
        r = skills.for_exercises(L, a, a.boxes, a.types, "advanced", "short")
        self.assertIn("```markdown", r["text"])
        self.assertNotIn("Write for a learner at the advanced level.", r["text"])
        self.assertEqual(skills.parse_header(r["text"])["types"], "flashcard")

    def test_a_video_from_scratch_with_a_word_list_is_not_offered_the_skill(self):
        import ytpages
        L, G = languages.get("ja"), languages.gloss_or_default("en")
        a = ytpages.assembled_full("fA6bK2mQ8sT", {"title": "T", "channel": "C"}, [], None, L, G)
        self.assertTrue(skills.for_new_video(a, L, G)["available"])
        self.assertFalse(skills.for_new_video(a, L, G, glossary="ci-stories")["available"])


class FakeHandler(object):
    """What a route function of the studio asks of its handler: the query, a JSON body, and a way to answer."""

    def __init__(self, query=None, body=None):
        self.query, self.body, self.path = query or {}, body or {}, "/api/x"
        self.sent = None

    def _json_body(self):
        return self.body

    def send_json(self, obj, code=200):
        self.sent = (code, obj)


class TheRoutesHandOutTheRequestBesideThePrompt(unittest.TestCase):
    def test_a_stretch_of_a_video_and_of_a_book(self):
        for kind, make in (("videos", lambda p: glossregion.video_prompt(p, 0, 3, regloss=True)),
                           ("books", lambda p: glossregion.book_prompt(p, 0, 5, perfield=True))):
            path, tmp = promptlab._fixture(kind, languages.get("fa"))
            try:
                got = make(path)
            finally:
                if tmp:
                    shutil.rmtree(tmp, ignore_errors=True)
            k = got["skill"]
            self.assertTrue(k["available"], k)
            h = skills.parse_header(k["text"])
            self.assertEqual((h["skill"], h["lang"], h["mode"]), ("parseh-gloss", "fa", "regloss" if kind == "videos" else "perfield"))
            self.assertEqual(h["what"], skills.WHAT["video-region" if kind == "videos" else "book-region"])
            self.assertLess(k["chars"], len(got["prompt"]))

    def test_the_studio_page_and_the_exercise_dialog(self):
        h = FakeHandler({"target": ["fa"], "boxes": ["vocab,gloss"], "level": ["beginner"]})
        studio.api_prompt_get(h)
        code, out = h.sent
        self.assertEqual(code, 200)
        self.assertTrue(out["skill"]["available"])
        self.assertEqual(skills.parse_header(out["skill"]["text"])["features"], "vocab, gloss")
        h = FakeHandler(body={"markdown": PAGE % "it", "boxes": ["lists"], "types": ["flashcard"]})
        studio.api_exercise_prompt(h)
        code, out = h.sent
        self.assertEqual(code, 200)
        self.assertEqual(skills.parse_header(out["skill"]["text"])["types"], "flashcard")
        self.assertIn("```markdown", out["skill"]["text"])

    def test_a_fault_in_making_the_request_never_takes_the_prompt_with_it(self):
        with mock.patch.object(skills, "build", side_effect=skills.SkillError("the method is not here")):
            h = FakeHandler({"target": ["fa"]})
            studio.api_prompt_get(h)
        code, out = h.sent
        self.assertEqual(code, 200)
        self.assertTrue(out["prompt"])
        self.assertFalse(out["skill"]["available"])
        self.assertIn("the method is not here", out["skill"]["why"])


class ThePersonsOwnAreNotThisModulesToList(unittest.TestCase):
    """R6 of the a0.4.3 merge: the owner's own skills (lib/asrskill/) are none of this lane's."""

    def test_nothing_reads_them_and_nothing_counts_the_skills(self):
        with open(os.path.join(ROOT, "lib", "skills.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("asrskill", src)
        self.assertNotRegex(src, r"(?i)\b(three|two|four|\d+) skills\b")
        self.assertEqual(skills.NAMES, ("parseh-gloss", "parseh-markdown", "parseh-book"))
        for sk in SKILLS.values():
            self.assertNotRegex(sk.files["SKILL.md"], r"(?i)\b(three|two|four|\d+) skills\b")

    def test_the_catalog_is_this_modules_skills_only(self):
        names = [c["name"] for c in skills.catalog()]
        self.assertTrue(set(names) <= set(skills.NAMES))
        for c in skills.catalog():
            self.assertTrue({"name", "what", "files", "chars", "skill_md", "biggest", "zip", "version", "hash",
                             "file"} <= set(c))


if __name__ == "__main__":
    unittest.main()
