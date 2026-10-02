#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The options of a prompt (lib/promptkit.py OPTIONS, a0.4.2 lane T: brief 3.9 and 3.10): the scheme a
transliteration is written in -- the language's usual one, or IPA -- and whether a Persian or an
Arabic text is given its short vowels.

    python3 -m unittest tests/test_prompt_options.py

WHAT IS HELD here is the MECHANISM, built once for both: the table (what applies where, the defaults,
the words a request may use and the sentence that refuses the others), the flags a text may use, the
placeholders, the version line and the header of a skill's request, the fallback a language with no IPA
note of its own gets, and every door that hands a prompt out taking the choice -- the region doors of a
book and of a video, the add page's prepare and add, the studio's two routes, the book made in place --
and the book's or the video's own record of the scheme (`translit`, which is the default of every prompt
asked for afterwards, and which the checks written for the usual scheme step aside for).  The CONTENT of
an IPA note, language by language, is lane D2's: tests/test_prompts.py holds it as rows that wait for it.

A TEMPORARY TREE in every class that writes (tests/configguard.py watches the whole run).
"""
import contextlib
import http.client
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for _p in ("tests", "markdown/exlex", "markdown/app", "lib", "youtube/lib", "."):
    if str(ROOT / _p) not in sys.path:
        sys.path.insert(0, str(ROOT / _p))
import bookmeta                                                 # noqa: E402
import books                                                    # noqa: E402
import glossregion as GR                                        # noqa: E402
import languages                                                # noqa: E402
import making                                                   # noqa: E402
import network                                                  # noqa: E402
import normalize_batch                                          # noqa: E402
import promptkit as K                                           # noqa: E402
import promptlab                                                # noqa: E402
import prompts as P                                             # noqa: E402
import server as studio_server                                  # noqa: E402
import store                                                    # noqa: E402
import version                                                  # noqa: E402
import ytpages                                                  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
V = version.VERSION
SURFACES = tuple(s for s in K.SURFACES if s != "ask")
GLOSSED = ("video-new", "video-region", "book-region", "book-new")
STUDIO = ("studio-doc", "studio-exercises")
KINDS = {"book-region": "books", "video-region": "videos"}


def copy_of(kind, code, into):
    """A scratch copy of a language's fixture book or video -> its directory."""
    L = languages.get(code)
    top = FIX / kind / L.folder
    src = top / sorted(os.listdir(top))[0]
    dst = Path(into) / kind / L.folder / src.name
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("reader", "*.pdf", "*.aux", "*.log", "*.toc", "*.out"))
    return dst


def says(path, **fields):
    """book.json / video.json with these keys written (None takes one out)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    for k, v in fields.items():
        if v is None:
            doc.pop(k, None)
        else:
            doc[k] = v
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Handler(object):
    """What the studio's route functions ask of their handler, and no more."""

    def __init__(self, body=None, query=None):
        self.body, self.query, self.answer, self.status = body or {}, query or {}, None, 200

    def _json_body(self):
        return self.body

    def send_json(self, answer, code=200):
        self.answer, self.status = answer, code


def ytpages_handler(body):
    """What the add page's doors ask of serve.py's handler, and no more."""
    class H(object):
        query = {}

        def __init__(self):
            self._raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.status = self.sent = None

        def send_json(self, obj, code=200):
            self.status, self.sent = code, obj
    return H()


class Quiet(unittest.TestCase):
    """A prompt that depends on nothing of this machine: no video of the shelf for the example of a
    video from scratch, no custom prompt of the studio's."""

    def setUp(self):
        for p in (mock.patch.object(ytpages, "video_dirs", lambda: []),
                  mock.patch.object(studio_server.store, "get_prompt",
                                    lambda: {"text": studio_server.store.default_prompt(), "custom": False})):
            p.start()
            self.addCleanup(p.stop)


# --- the table --------------------------------------------------------------------------------------
class TheTable(unittest.TestCase):
    def test_two_options_are_registered_in_one_table_and_nothing_else_names_them_by_hand(self):
        self.assertEqual([o.name for o in K.OPTIONS], ["translit", "marks"])
        self.assertEqual([o.values for o in K.OPTIONS], [("classic", "ipa"), ("nomarks", "marks")])
        # the flags are the values: nothing but the table says a flag's name
        self.assertEqual(sorted(K.option_flags("video-region", "fa")), ["classic", "ipa", "marks", "nomarks"])

    def test_what_applies_where_is_the_surface_and_the_languages_record_and_never_its_code(self):
        for surface in SURFACES:
            for code in languages.CODES:
                L = languages.get(code)
                got = K.resolve(surface, L)
                self.assertEqual("translit" in got,
                                 surface in K.OPTIONS[0].surfaces and L.ipa != "none", (surface, code))
                self.assertEqual("marks" in got, surface in GLOSSED and bool(L.strip_range), (surface, code))
        # not asked for on the tidy and on Ask LLM, which ask for no transliteration
        self.assertEqual(K.resolve("transcript-tidy", "fa"), {})
        self.assertEqual(K.resolve("ask", "fa"), {})
        # and not on the studio's prompts, whose Persian carries no harakat rule
        self.assertEqual(K.resolve("studio-doc", "fa"), {"translit": "classic"})

    def test_the_defaults_keep_todays_behaviour(self):
        # a book made in place asks for the marks (a reading edition's first pass is the vowelled
        # attempt); a stretch of a book or a video and a video from scratch never change the text
        self.assertEqual(K.resolve("book-new", "fa"), {"translit": "classic", "marks": "marks"})
        for surface in ("video-new", "video-region", "book-region"):
            self.assertEqual(K.resolve(surface, "ar"), {"translit": "classic", "marks": "nomarks"})
        self.assertEqual(K.resolve("video-region", "it"), {"translit": "classic"})

    def test_the_registry_says_which_language_has_what(self):
        self.assertEqual({c: languages.get(c).ipa for c in languages.CODES if languages.get(c).ipa != "offered"},
                         {"en": "usual", "zh": "none"})
        row = dict(languages.read_rows()[0]["it"], ipa="nonsense")
        self.assertEqual(languages.Lang("it", row).ipa, "offered", "a word it does not know is no refusal of IPA")
        self.assertEqual(languages.get("fa").strip("دَر"), "در", "the condition for the marks is `strip`")

    def test_a_request_is_read_in_the_words_it_may_use_and_refused_in_words_otherwise(self):
        for given, want in (("ipa", "ipa"), (" IPA ", "ipa"), ("classic", "classic"), ("usual", "classic"),
                            ("", None), (None, None)):
            self.assertEqual(K.OPTIONS[0].parse(given), want, given)
        for given, want in (("marks", "marks"), (True, "marks"), ("1", "marks"), ("on", "marks"), ("YES", "marks"),
                            ("nomarks", "nomarks"), (False, "nomarks"), ("0", "nomarks"), ("off", "nomarks")):
            self.assertEqual(K.OPTIONS[1].parse(given), want, given)
        with self.assertRaises(K.OptionError) as e:
            K.resolve("video-region", "fa", {"translit": "klingon"})
        self.assertIn("'klingon'", str(e.exception))
        self.assertIn("classic or ipa", str(e.exception))
        with self.assertRaises(K.OptionError) as e:
            K.resolve("video-region", "fa", {"marks": "maybe"})
        self.assertIn("nomarks or marks", str(e.exception))
        with self.assertRaises(K.OptionError) as e:
            K.resolve("video-region", "fa", {"colour": "red"})
        self.assertIn("is not an option of a prompt", str(e.exception))
        # an option of the kit is a ValueError, which every door already turns into a sentence
        self.assertTrue(issubclass(K.OptionError, K.PromptError) and issubclass(K.PromptError, ValueError))

    def test_a_typo_is_refused_even_where_the_option_does_not_apply(self):
        with self.assertRaises(K.OptionError):
            K.resolve("video-region", "it", {"marks": "maybe"})
        with self.assertRaises(K.OptionError):
            K.resolve("transcript-tidy", "fa", {"translit": "klingon"})

    def test_an_option_that_does_not_apply_is_left_out_and_not_refused(self):
        # what a device remembers of one prompt must not stop another: a remembered `marks` sent for an
        # Italian video, a remembered `ipa` sent for Chinese (whose record offers none)
        self.assertEqual(K.resolve("video-region", "it", {"marks": "1", "translit": "ipa"}), {"translit": "ipa"})
        self.assertEqual(K.resolve("video-region", "zh", {"translit": "ipa", "marks": "1"}), {})
        self.assertEqual(K.resolve("transcript-tidy", "fa", {"translit": "ipa"}), {})
        self.assertEqual(K.resolve("studio-doc", "fa", {"marks": "1"}), {"translit": "classic"})

    def test_the_books_or_the_videos_own_record_is_the_default_and_a_request_wins(self):
        facts = {"translit": "ipa"}
        self.assertEqual(K.resolve("video-region", "fa", None, facts)["translit"], "ipa")
        self.assertEqual(K.resolve("video-region", "fa", {"translit": "classic"}, facts)["translit"], "classic")
        self.assertEqual(K.resolve("video-region", "zh", None, facts), {})
        # a record that says nonsense is data, not a request: passed over
        self.assertEqual(K.resolve("video-region", "fa", None, {"translit": "klingon"})["translit"], "classic")
        self.assertEqual(K.resolve("video-region", "fa", None, {"translit": None})["translit"], "classic")

    def test_the_flags_follow_the_options_and_are_known_to_every_text_of_every_surface(self):
        got = K.surface_flags("video-region", "fa", {"translit": "ipa", "marks": "1"})
        self.assertEqual((got["ipa"], got["classic"], got["marks"], got["nomarks"]), (True, False, True, False))
        got = K.surface_flags("video-region", "fa")
        self.assertEqual((got["ipa"], got["classic"], got["marks"], got["nomarks"]), (False, True, False, True))
        # neither flag of the marks where the language has none, and where the prompt asks none
        for surface, code in (("video-region", "it"), ("studio-doc", "fa"), ("transcript-tidy", "fa")):
            got = K.surface_flags(surface, code, {"marks": "1"})
            self.assertEqual((got["marks"], got["nomarks"]), (False, False), (surface, code))
        # the usual scheme stands where IPA is not offered
        got = K.surface_flags("video-region", "zh", {"translit": "ipa"})
        self.assertEqual((got["ipa"], got["classic"]), (False, True))
        # and with no language, a text may still name them
        got = K.surface_flags("video-region")
        self.assertEqual(sorted(k for k in got if k in ("ipa", "classic", "marks", "nomarks")),
                         ["classic", "ipa", "marks", "nomarks"])
        self.assertEqual((got["classic"], got["marks"], got["nomarks"]), (True, False, False))

    def test_the_version_line_ends_with_what_the_options_say_and_a_persons_own_name_stands_last(self):
        self.assertEqual(K.version_line("video-region", "fa", "en", "regloss", None, {"translit": "ipa", "marks": "1"}),
                         "Parseh prompt · video-region · fa → en · %s · re-gloss · IPA · marks" % V)
        self.assertEqual(K.version_line("video-new", "ar", "en", None, "mine", {"translit": "ipa"}),
                         "Parseh prompt · video-new · ar → en · %s · IPA · no marks · custom: mine" % V)
        self.assertEqual(K.version_line("book-new", "fa", "en"), "Parseh prompt · book-new · fa → en · %s · marks" % V)
        # the usual scheme says nothing, a language with no short vowels says nothing of them
        self.assertEqual(K.version_line("video-region", "it", "en"), "Parseh prompt · video-region · it → en · " + V)
        self.assertEqual(K.version_line("studio-doc", "ja", None, None, None, {"translit": "ipa"}),
                         "Parseh prompt · studio-doc · ja · %s · IPA" % V)
        # IPA is no setting of Chinese: its line does not say so
        self.assertEqual(K.version_line("video-region", "zh", "en", None, None, {"translit": "ipa"}),
                         "Parseh prompt · video-region · zh → en · " + V)

    def test_the_header_of_a_skills_request_is_what_the_options_say_and_nothing_else_says_it(self):
        self.assertEqual(K.header_fields("video-region", "fa", {"translit": "ipa", "marks": "1"}),
                         ["translit: ipa", "marks: on"])
        self.assertEqual(K.header_fields("video-region", "fa"), ["marks: off"])
        self.assertEqual(K.header_fields("video-region", "it"), [])
        self.assertEqual(K.header_fields("studio-doc", "it", {"translit": "ipa"}), ["translit: ipa"])
        self.assertEqual(K.header_fields("transcript-tidy", "fa"), [])

    def test_what_a_page_draws_comes_from_the_server_in_the_languages_own_word(self):
        got = {d["name"]: d for d in K.describe("video-region", "ja")}
        self.assertEqual(sorted(got), ["translit"])
        self.assertEqual((got["translit"]["label"], got["translit"]["value"], got["translit"]["fact"]),
                         ("rōmaji", "classic", False))
        self.assertEqual([c["id"] for c in got["translit"]["choices"]], ["classic", "ipa"])
        self.assertEqual(got["translit"]["remember"], "ja")
        got = {d["name"]: d for d in K.describe("book-region", "fa")}
        self.assertEqual((got["marks"]["label"], got["marks"]["value"], got["marks"]["remember"]),
                         ("short vowels", "nomarks", "book-region"))
        self.assertEqual([c["label"] for c in got["marks"]["choices"]], ["as they are", "write them"])
        # English says that IPA is already its usual scheme; Chinese is offered none
        en = {d["name"]: d for d in K.describe("video-region", "en")}["translit"]
        self.assertEqual([c["label"] for c in en["choices"]], ["IPA (already the usual)", "IPA"])
        self.assertEqual(K.describe("video-region", "zh"), [])
        self.assertEqual(K.describe("transcript-tidy", "fa"), [])
        # the book's own record is what stands, and the descriptor says so
        d = K.describe("book-region", "fa", None, {"translit": "ipa"})[0]
        self.assertEqual((d["value"], d["fact"], d["default"]), ("ipa", True, "classic"))
        d = K.describe("book-region", "fa", {"translit": "classic"}, {"translit": "ipa"})[0]
        self.assertEqual((d["value"], d["fact"]), ("classic", False))

    def test_the_editor_of_a_persons_own_prompt_is_told_the_flags_and_the_placeholders(self):
        for surface in GLOSSED + STUDIO:
            names = [n for n, _m in K.placeholders(surface)]
            self.assertIn("TR_SCHEME", names, surface)
            self.assertEqual("MARKS_RULE" in names, surface in GLOSSED, surface)
        for surface in ("transcript-tidy", "ask"):
            self.assertNotIn("TR_SCHEME", [n for n, _m in K.placeholders(surface)])
        info = P.parseh("video-region")
        self.assertTrue({"ipa", "classic", "marks", "nomarks"} <= set(info["blocks"]), info["blocks"])
        self.assertEqual(sorted(info["block_notes"]), ["classic", "ipa", "marks", "nomarks"])
        info = P.parseh("studio-doc")
        self.assertTrue({"ipa", "classic"} <= set(info["blocks"]) and not {"marks", "nomarks"} & set(info["blocks"]))
        self.assertEqual(sorted(P.parseh("ask")["block_notes"]), [])
        for line in K.flag_meanings().values():
            self.assertTrue(line and "\n" not in line and len(line) < 110, line)


# --- in the prompt --------------------------------------------------------------------------------
# A language file that carries both variants of the two options, as the files of lane D2 will
FILE = ("# Persian\n\nOpening words.\n\n## Reading\n\n{{?marks}}WRITE THE MARKS.{{/marks}}"
        "{{?nomarks}}LEAVE FA AS IT IS.{{/nomarks}}\n\n## Transliteration\n\n"
        "{{?classic}}THE USUAL SCHEME of {{LANGUAGE}}.{{/classic}}{{?ipa}}THE IPA NOTE of {{LANGUAGE}}.{{/ipa}}\n")


class InThePrompt(Quiet):
    def in_files(self, text, code="fa"):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        Path(td.name, code + ".md").write_text(text, encoding="utf-8")
        patcher = mock.patch.object(K, "LANG_DOCS", td.name)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_language_files_two_variants_are_resolved_by_the_options(self):
        self.in_files(FILE)
        for surface in ("video-region", "book-region", "video-new", "book-new"):
            both = K.language_text(surface, "fa", options={"translit": "ipa", "marks": "marks"})
            self.assertIn("THE IPA NOTE of Persian.", both, surface)
            self.assertIn("WRITE THE MARKS.", both, surface)
            self.assertNotIn("USUAL", both)
            self.assertNotIn("LEAVE FA", both)
            neither = K.language_text(surface, "fa", options={"translit": "classic", "marks": "nomarks"})
            self.assertIn("THE USUAL SCHEME of Persian.", neither, surface)
            self.assertIn("LEAVE FA AS IT IS.", neither, surface)
            self.assertNotIn("IPA", neither)
        # the defaults, with nothing said
        self.assertIn("LEAVE FA AS IT IS.", K.language_text("video-region", "fa"))
        self.assertIn("WRITE THE MARKS.", K.language_text("book-new", "fa"))

    def test_a_language_with_no_short_vowels_never_has_either_paragraph_of_them(self):
        self.in_files(FILE, "it")
        got = K.language_text("video-region", "it", options={"marks": "marks"})
        self.assertNotIn("WRITE THE MARKS.", got)
        self.assertNotIn("LEAVE FA AS IT IS.", got)
        self.assertIn("THE USUAL SCHEME of Italian.", got)

    def test_a_language_file_with_no_ipa_note_gets_the_general_paragraph_in_front_and_only_then(self):
        text = "# Italian\n\nOpening.\n\n## Transliteration\n\nThe usual scheme of {{LANGUAGE}}, and no other note.\n"
        self.in_files(text, "it")
        ipa = K.language_text("video-region", "it", options={"translit": "ipa"})
        self.assertTrue(ipa.startswith("**This prompt asks for IPA.**"), ipa[:80])
        self.assertIn("pronunciation scheme of Italian", ipa)
        self.assertIn("`\\dw{word}{sound}`", ipa)
        self.assertIn("no other note", ipa, "the file's own words still follow")
        self.assertNotIn("IPA", K.language_text("video-region", "it"), "the usual scheme says nothing of it")
        # the studio's own words: it has no vocabulary macros
        studio = K.language_text("studio-doc", "it", options={"translit": "ipa"})
        self.assertIn("`[word]{translit:…}`", studio)
        self.assertNotIn("\\dw", studio)
        # a file that has its own note is not given the general one
        self.in_files(FILE, "fa")
        self.assertNotIn("This prompt asks for IPA", K.language_text("video-region", "fa", options={"translit": "ipa"}))

    def test_the_placeholders_say_which_scheme_and_which_rule_this_prompt_has(self):
        def said(surface, code, **options):
            return K.assemble(surface, code, "en" if surface in GLOSSED else None, options=options,
                              template="{{TR_LABEL}}|{{TR_SCHEME}}|{{MARKS_RULE}}" if surface in GLOSSED else
                              "{{TR_LABEL}}|{{TR_SCHEME}}").instructions
        self.assertEqual(said("video-region", "fa"),
                         "transliteration|the usual transliteration scheme for Persian|leave `fa` as it is, with no short vowels added")
        self.assertEqual(said("video-region", "fa", translit="ipa", marks="1"),
                         "IPA|IPA|write the short vowels in `fa`")
        self.assertEqual(said("video-region", "ja", translit="ipa"), "IPA|IPA|")
        self.assertEqual(said("book-region", "ja"), "rōmaji|the usual rōmaji scheme for Japanese|")
        self.assertEqual(said("video-region", "en"), "pronunciation|IPA|", "English's usual scheme already is IPA")
        self.assertEqual(said("studio-doc", "it"), "pronunciation|the usual pronunciation scheme for Italian")
        # a prompt that publishes neither does not take them
        for name in ("TR_SCHEME", "MARKS_RULE"):
            with self.assertRaises(K.PromptError):
                K.assemble("transcript-tidy", "fa", template="x {{%s}}" % name)
        with self.assertRaises(K.PromptError):
            K.assemble("studio-doc", "fa", template="x {{MARKS_RULE}}")

    def test_a_persons_own_prompt_may_say_either_variant_and_the_scheme(self):
        own = "Scheme: {{TR_SCHEME}}.{{?ipa}} Write IPA.{{/ipa}}{{?classic}} Write it the usual way.{{/classic}}"
        # saved: the dry run the store makes of a text knows both flags and the placeholder, for a stretch
        # of a video and for the studio (and refuses a flag nobody gave, in words)
        P.check_text("video-region", own, "fa")
        P.check_text("studio-doc", own, "fa")
        with self.assertRaises(P.PromptsError):
            P.check_text("video-region", "{{?ipaa}}x{{/ipaa}}", "fa")
        text = K.assemble("studio-doc", "fa", instructions=own, options={"translit": "ipa"})
        self.assertTrue(text.instructions.startswith("Scheme: IPA. Write IPA."), text.instructions)
        self.assertTrue(text.header.endswith(" · IPA"))
        usual = K.assemble("studio-doc", "fa", instructions=own)
        self.assertTrue(usual.instructions.startswith("Scheme: the usual transliteration scheme for Persian. Write it the usual way."))
        # and in a person's prompt for a stretch, the marks rule says which state the prompt is in
        rule = "{{MARKS_RULE}}|{{?marks}}M{{/marks}}{{?nomarks}}N{{/nomarks}}"
        for asked, said in (({"marks": "1"}, "write the short vowels in `fa`|M"),
                            ({"marks": "0"}, "leave `fa` as it is, with no short vowels added|N")):
            got = K.assemble("book-new", "fa", "en", template=rule, options=asked)
            self.assertEqual(got.instructions, said)
        self.assertEqual(K.assemble("book-new", "it", "en", template=rule, options={"marks": "1"}).instructions, "|")

    def test_every_prompt_in_every_language_with_the_options_chosen_is_made_and_says_what_was_chosen(self):
        for code in languages.CODES:
            L = languages.get(code)
            for surface in SURFACES:
                for asked in ({"translit": "ipa"}, {"marks": "1"}, {"translit": "ipa", "marks": "0"}):
                    a = promptlab.build(surface, code, None, None, asked)
                    with self.subTest(surface=surface, language=code, asked=asked):
                        self.assertNotIn("{{", a.text)
                        self.assertEqual(a.options, K.resolve(surface, L, asked))
                        self.assertEqual(a.header, K.version_line(surface, L, languages.gloss_or_default(None)
                                                                  if surface in GLOSSED else None, None, None, a.options))
                        words = a.header.split(" · ")
                        self.assertEqual("IPA" in words, a.options.get("translit") == "ipa")
                        self.assertEqual("marks" in words or "no marks" in words, "marks" in a.options)
                        if a.options.get("translit") == "ipa" and surface != "transcript-tidy":
                            self.assertIn("IPA", a.instructions, "the prompt names what it asks for")
                        self.assertEqual(a.text.split("\n")[0], a.header)

    def test_the_options_change_nothing_else_the_defaults_make_the_prompt_they_always_were(self):
        for code in ("fa", "it", "ja", "zh"):
            for surface in SURFACES:
                plain = promptlab.build(surface, code)
                same = promptlab.build(surface, code, None, None, {"translit": "classic"})
                self.assertEqual(plain.text, same.text, (surface, code))
        # IPA is no setting of Chinese: a request for it makes the prompt it always was
        self.assertEqual(promptlab.build("video-region", "zh", None, None, {"translit": "ipa"}).text,
                         promptlab.build("video-region", "zh").text)

    def test_the_marks_setting_changes_the_version_line_and_nothing_else_until_the_language_files_use_it(self):
        # lane D2 marks the harakat paragraphs of fa.md and ar.md with the two flags; until then the words of
        # the prompt are the same whichever is chosen, and the line above them says which was asked for
        for code in ("fa", "ar"):
            on = promptlab.build("video-region", code, None, None, {"marks": "1"})
            off = promptlab.build("video-region", code, None, None, {"marks": "0"})
            self.assertEqual(on.header[:-len("marks")], off.header[:-len("no marks")])
            self.assertTrue(on.header.endswith(" · marks") and off.header.endswith(" · no marks"))

    def test_the_lab_takes_the_options(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = promptlab.main(["video-region", "fa", "--translit", "ipa", "--marks", "1", "--sizes"])
        self.assertEqual(rc, 0, out.getvalue())
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(promptlab.main(["video-region", "fa", "--translit", "ipa"]), 0)
        self.assertEqual(out.getvalue().split("\n")[0], "Parseh prompt · video-region · fa → en · %s · IPA · no marks" % V)
        with contextlib.redirect_stderr(err):
            self.assertEqual(promptlab.main(["video-region", "fa", "--translit", "klingon"]), 2)
        self.assertIn("'klingon'", err.getvalue())

    def test_each_variant_is_within_its_budget(self):
        # the budget of a prompt with an option chosen is the default's and room for what the option adds
        # (the IPA note of a language; the harakat paragraphs): tests/test_prompts.py SIZES
        import test_prompts as T
        for code in languages.CODES:
            for surface in SURFACES:
                budget = T.SIZES[code][T.MEASURED.index(surface)][1]
                for asked in ({"translit": "ipa"}, {"marks": "1"}):
                    a = promptlab.build(surface, code, None, None, asked)
                    with self.subTest(surface=surface, language=code, asked=asked):
                        self.assertLessEqual(len(a.text), budget + T_ROOM[next(iter(asked))], a.header)


# what an option may add to a prompt's budget (characters): the IPA note of a language and the examples
# that show a sound twice (lane D2), the paragraphs of the marks
T_ROOM = {"translit": 4000, "marks": 2500}


# --- the doors of a book and of a video, in-process ---------------------------------------------
class RegionDoors(Quiet):
    def setUp(self):
        super().setUp()
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.td = td.name

    def book(self, code):
        return copy_of("books", code, self.td)

    def video(self, code):
        return copy_of("videos", code, self.td)

    def test_a_stretch_of_a_book_or_a_video_takes_the_choice_and_says_what_it_came_to(self):
        for kind, code in itertools_product(("books", "videos"), ("fa", "ar", "it", "ja", "zh")):
            d = copy_of(kind, code, self.td)
            fn = (lambda **kw: GR.book_prompt(str(d), 0, 5, **kw)) if kind == "books" else \
                 (lambda **kw: GR.video_prompt(str(d), 0, 3, **kw))
            surface = "book-region" if kind == "books" else "video-region"
            with self.subTest(kind=kind, language=code):
                plain = fn()
                self.assertEqual(plain["prompt"].split("\n")[0], K.version_line(surface, code, "en"))
                named = {o["name"]: o for o in plain["options"]}
                self.assertEqual(sorted(named), sorted(K.resolve(surface, code)))
                got = fn(translit="ipa", marks="1")
                want = K.resolve(surface, code, {"translit": "ipa", "marks": "1"})
                self.assertEqual({o["name"]: o["value"] for o in got["options"]}, want)
                self.assertEqual(got["prompt"].split("\n")[0], K.version_line(surface, code, "en", None, None, want))
                if code == "zh":
                    self.assertEqual(got["prompt"], plain["prompt"], "Chinese has no IPA setting yet")
                else:
                    self.assertIn(" · IPA", got["prompt"].split("\n")[0])
                self.assertNotIn("{{", got["prompt"])

    def test_a_value_that_is_none_of_the_options_is_refused_in_words_and_nothing_is_made(self):
        d = self.book("fa")
        with self.assertRaises(GR.Refused) as e:
            GR.book_prompt(str(d), 0, 5, translit="klingon")
        self.assertEqual(str(e.exception), "'klingon' is not a way to write the transliteration: it is classic or ipa")
        with self.assertRaises(GR.Refused) as e:
            GR.video_prompt(str(self.video("fa")), 0, 3, marks="maybe")
        self.assertIn("nomarks or marks", str(e.exception))

    def test_the_books_own_record_of_the_scheme_is_the_default_and_a_request_overrides_it(self):
        for kind, code in (("books", "fa"), ("videos", "ar"), ("books", "ja")):
            d = copy_of(kind, code, self.td)
            says(d / ("book.json" if kind == "books" else "video.json"), translit="ipa")
            fn = (lambda **kw: GR.book_prompt(str(d), 0, 5, **kw)) if kind == "books" else \
                 (lambda **kw: GR.video_prompt(str(d), 0, 3, **kw))
            with self.subTest(kind=kind, language=code):
                got = fn()
                self.assertIn(" · IPA", got["prompt"].split("\n")[0])
                (translit,) = [o for o in got["options"] if o["name"] == "translit"]
                self.assertEqual((translit["value"], translit["fact"]), ("ipa", True))
                # chosen against the record, for this prompt: the person's word wins, and says it did
                got = fn(translit="classic")
                self.assertNotIn(" · IPA", got["prompt"].split("\n")[0])
                (translit,) = [o for o in got["options"] if o["name"] == "translit"]
                self.assertEqual((translit["value"], translit["fact"]), ("classic", False))

    def test_a_record_that_says_nonsense_is_passed_over(self):
        d = self.book("fa")
        says(d / "book.json", translit="ipa")
        self.assertIn(" · IPA", GR.book_prompt(str(d), 0, 5)["prompt"].split("\n")[0], "a record that says IPA is read")
        says(d / "book.json", translit="klingon")
        self.assertNotIn(" · IPA", GR.book_prompt(str(d), 0, 5)["prompt"].split("\n")[0])

    def test_the_chosen_scheme_is_in_the_conventions_the_stretch_carries(self):
        d = self.video("fa")
        ipa = GR.video_prompt(str(d), 0, 3, translit="ipa")["prompt"]
        self.assertIn("the IPA of the chunk", ipa)
        self.assertIn("headword, IPA, meaning", ipa)
        self.assertNotIn("the transliteration of the chunk", ipa)
        usual = GR.video_prompt(str(d), 0, 3)["prompt"]
        self.assertIn("the transliteration of the chunk", usual)


def itertools_product(*lists):
    import itertools
    return itertools.product(*lists)


# --- the add page, the studio, the book made in place -----------------------------------------------
class OtherDoors(Quiet):
    def setUp(self):
        super().setUp()
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.td = td.name
        self.videos = os.path.join(self.td, "videos")
        os.makedirs(self.videos)
        for name, value in (("VIDEOS", self.videos), ("oembed", lambda vid: {})):
            p = mock.patch.object(ytpages, name, value)
            p.start()
            self.addCleanup(p.stop)

    def transcript(self, code):
        top = FIX / "videos" / languages.get(code).folder
        d = top / sorted(os.listdir(top))[0]
        return d, (d / "transcript.txt").read_text(encoding="utf-8")

    def prepare(self, code, **more):
        d, transcript = self.transcript(code)
        h = ytpages_handler(dict({"url": d.name, "lang": code, "gloss": "en", "transcript": transcript}, **more))
        ytpages.api_prepare(h)
        return h

    def test_the_add_pages_prompt_takes_the_choice_and_says_what_it_came_to(self):
        for code in ("fa", "ar", "it", "zh"):
            h = self.prepare(code)
            self.assertEqual(h.status, 200, h.sent)
            self.assertEqual(h.sent["prompt"].split("\n")[0], K.version_line("video-new", code, "en"))
            self.assertEqual([o["name"] for o in h.sent["options"]], list(K.resolve("video-new", code)))
            h = self.prepare(code, translit="ipa", marks="1")
            self.assertEqual(h.status, 200, h.sent)
            want = K.resolve("video-new", code, {"translit": "ipa", "marks": "1"})
            self.assertEqual({o["name"]: o["value"] for o in h.sent["options"]}, want)
            self.assertEqual(h.sent["prompt"].split("\n")[0], K.version_line("video-new", code, "en", None, None, want))

    def test_a_value_that_is_none_of_the_options_is_refused_in_words(self):
        h = self.prepare("fa", translit="klingon")
        self.assertEqual((h.status, h.sent["ok"]), (400, False))
        self.assertEqual(h.sent["error"], "'klingon' is not a way to write the transliteration: it is classic or ipa")

    def test_an_example_made_before_ipa_was_asked_for_says_so(self):
        example = ("[0] 3s  سلام", '{"captions": []}', "")
        with mock.patch.object(ytpages, "_example", lambda L: example):
            ipa = ytpages.chat_prompt(None, "fa", None, {"translit": "ipa"})
            usual = ytpages.chat_prompt(None, "fa")
        self.assertIn("The transliterations in the example are written in the usual scheme of Persian", ipa)
        self.assertIn("write yours in IPA", ipa)
        self.assertNotIn("usual scheme of Persian, which is not", usual)

    def test_a_video_added_after_an_ipa_prompt_keeps_the_scheme_as_its_own(self):
        d, transcript = self.transcript("fa")
        parts = json.loads((d / "parts" / "01.json").read_text(encoding="utf-8"))
        answer = "```json\n%s\n```" % json.dumps(
            {"video": {"level": "beginner"},
             "captions": [{"i": i, "start": p["start"], "chunks": p["chunks"]} for i, p in enumerate(parts)]},
            ensure_ascii=False)
        body = {"url": d.name, "lang": "fa", "gloss": "en", "transcript": transcript, "answer": answer}
        for asked, kept in (({"translit": "ipa"}, "ipa"), ({}, None), ({"translit": "classic"}, None)):
            h = ytpages_handler(dict(body, **asked))
            ytpages.api_add(h)
            self.assertEqual((h.status, h.sent.get("ok")), (200, True), h.sent)
            meta = json.loads(Path(self.videos, "persian", d.name, "video.json").read_text(encoding="utf-8"))
            self.assertEqual(meta.get("translit"), kept, asked)
            shutil.rmtree(os.path.join(self.videos, "persian"))
        h = ytpages_handler(dict(body, translit="klingon"))
        ytpages.api_add(h)
        self.assertEqual((h.status, h.sent["ok"]), (400, False))
        self.assertFalse(os.path.exists(os.path.join(self.videos, "persian")), "nothing was written")

    def test_the_studios_two_prompts_take_the_scheme_and_say_what_it_came_to(self):
        it, fa = languages.get("it"), languages.get("fa")
        self.assertEqual(studio_server.studio_prompt(it).text.split("\n")[0], K.version_line("studio-doc", "it"))
        got = studio_server.studio_prompt(fa, translit="ipa")
        self.assertEqual(got.text.split("\n")[0], "Parseh prompt · studio-doc · fa · %s · IPA" % V)
        self.assertEqual(got.options, {"translit": "ipa"})
        self.assertIn("Write IPA, as the conventions", got.text)
        self.assertNotIn("Use the scholarly scheme", got.text)
        self.assertNotIn("yavâš", got.text, "the example in the usual scheme does not stay in a prompt that asks for IPA")
        usual = studio_server.studio_prompt(fa)
        self.assertIn("Use the scholarly scheme", usual.text)
        self.assertIn("yavâš", usual.text)
        page = "---\ntitle: T\ntarget: fa\n---\n\nLesson"
        a, _rows = studio_server.exercise_prompt(page, translit="ipa")
        self.assertEqual(a.text.split("\n")[0], "Parseh prompt · studio-exercises · fa · %s · IPA" % V)
        self.assertIn("This prompt asks for IPA", a.text, "a file with no IPA note of its own is given the general one")

    def test_the_studios_routes_take_and_refuse_it_and_answer_with_what_the_page_draws(self):
        h = Handler(query={"target": ["fa"], "translit": ["ipa"]})
        studio_server.api_prompt_get(h)
        self.assertEqual(h.status, 200, h.answer)
        self.assertTrue(h.answer["prompt"].split("\n")[0].endswith(" · IPA"))
        self.assertEqual([(o["name"], o["value"]) for o in h.answer["options"]], [("translit", "ipa")])
        self.assertEqual(h.answer["always_chars"], len(studio_server.studio_prompt(
            languages.get("fa"), boxes=[], translit="ipa").text), "the size of what is always there is for the same setting")
        h = Handler(query={"target": ["fa"], "translit": ["klingon"]})
        studio_server.api_prompt_get(h)
        self.assertEqual(h.status, 400)
        self.assertIn("'klingon'", h.answer["error"])
        h = Handler({"markdown": "---\ntitle: T\ntarget: ja\n---\n\nx", "decks": [], "translit": "ipa"})
        studio_server.api_exercise_prompt(h)
        self.assertEqual(h.status, 200, h.answer)
        self.assertEqual([o["name"] for o in h.answer["options"]], ["translit"])
        self.assertIn(" · IPA", h.answer["prompt"].split("\n")[0])
        h = Handler({"markdown": "---\ntitle: T\ntarget: ja\n---\n\nx", "decks": [], "translit": "klingon"})
        studio_server.api_exercise_prompt(h)
        self.assertEqual(h.status, 400)
        # the standalone studio answers what a row mounted with a language asks (serve.py does it in the toolbox)
        h = Handler(query={"surface": ["studio-doc"], "lang": ["ja"]})
        studio_server.serve_prompt_options(h)
        self.assertEqual([(o["name"], o["label"]) for o in h.answer["options"]], [("translit", "rōmaji")])
        h = Handler(query={"surface": ["the-moon"], "lang": ["ja"]})
        studio_server.serve_prompt_options(h)
        self.assertEqual(h.status, 400)

    def test_the_book_made_in_place_keeps_its_scheme_and_its_instructions_ask_for_it(self):
        into = os.path.join(self.td, "books")
        for code, translit, marks in (("fa", "ipa", None), ("it", None, None), ("ar", "ipa", "0")):
            fields = {"lang": code, "gloss": "en", "title": "T", "title_latin": "T", "slug": "t-%s" % code}
            if translit:
                fields["translit"] = translit
            r = making.make(fields, {"name": "t.txt", "data": b"Some text of the book."},
                            {"marks": marks} if marks else {}, into)
            book = Path(r["path"])
            meta = json.loads((book / "book.json").read_text(encoding="utf-8"))
            self.assertEqual(meta.get("translit"), translit, code)
            first = (book / "AGENTS.md").read_text(encoding="utf-8").split("\n")[0]
            self.assertEqual(" · IPA" in first, translit == "ipa", first)
            self.assertEqual(first.endswith(" · marks"), code == "fa", first)
            self.assertEqual(first.endswith(" · no marks"), code == "ar", first)
            self.assertEqual(books.Book(str(book)).translit, translit or "")
        # the page's own preview says the same, and a value that is none of the options is refused
        text = making.instructions_for({"lang": "fa", "translit": "ipa", "title": "T"}, {})
        self.assertIn("IPA", text)
        with self.assertRaises(ValueError) as e:
            making.instructions_for({"lang": "fa", "translit": "klingon", "title": "T"}, {})
        self.assertIn("'klingon'", str(e.exception))

    def test_the_record_may_be_changed_through_the_doors_that_edit_it_and_the_usual_way_is_no_key(self):
        d = copy_of("books", "fa", self.td)
        meta = bookmeta.edit_meta(str(d), {"translit": "ipa"})
        self.assertEqual(meta["translit"], "ipa")
        self.assertEqual(books.Book(str(d)).translit, "ipa")
        meta = bookmeta.edit_meta(str(d), {"translit": "classic"})
        self.assertNotIn("translit", meta)
        self.assertNotIn("translit", json.loads((d / "book.json").read_text(encoding="utf-8")))
        with self.assertRaises(bookmeta.Refused):
            bookmeta.edit_meta(str(d), {"translit": "klingon"})
        v = copy_of("videos", "ar", self.td)
        meta = ytpages.edit_meta(str(v), {"translit": "ipa"})
        self.assertEqual(meta["translit"], "ipa")
        meta = ytpages.edit_meta(str(v), {"translit": ""})
        self.assertNotIn("translit", meta)
        with self.assertRaises(ytpages.texwrite.Refused):
            ytpages.edit_meta(str(v), {"translit": "klingon"})


# --- the checks written for the usual scheme -----------------------------------------------------------
class TheChecks(unittest.TestCase):
    """A Persian book that says its transliteration is IPA is not held to a scheme it does not use."""

    def book(self, **record):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        d = Path(td.name) / "mini-fa"
        shutil.copytree(FIX / "books" / "persian" / "mini-fa", d, ignore=shutil.ignore_patterns("reader"))
        if record:
            says(d / "book.json", **record)
        return d

    def paragraph(self, d):
        """The annotator's JSON for paragraph 1, with a fatha put before a ya of the text (the fidelity
        check strips the marks) and a transliteration that says /ey/: the one thing the usual scheme's
        check refuses."""
        import texparse
        b = books.Book(str(d))
        para = texparse.parse_book(b.main, b.lang)[0].paragraphs[0]
        sents, done = [], False
        for s in para.subs:
            chunks = []
            for c in s.chunks:
                chunk = {"fa": c.fa, "tr": c.tr, "voc": c.voc, "en": c.en}
                if not done and "ی" in c.fa and chunk["tr"].strip():
                    chunk["fa"] = c.fa.replace("ی", "َی", 1)
                    chunk["tr"] = "xeyli"
                    done = True
                chunks.append(chunk)
            sents.append({"chunks": chunks})
        self.assertTrue(done, "the fixture has a chunk with a ya and a transliteration")
        path = d / "para0.json"
        path.write_text(json.dumps({"idx": 0, "ch": 1, "ann": {"sentences": sents}}, ensure_ascii=False),
                        encoding="utf-8")
        return path

    def check(self, d, para):
        r = subprocess.run([sys.executable, str(ROOT / "lib" / "check_batch.py"), str(para), "--book", str(d)],
                           capture_output=True, text=True, cwd=str(d))
        return r.stdout + r.stderr

    def test_the_usual_schemes_ey_check_refuses_it_and_an_ipa_book_is_not_held_to_it(self):
        usual = self.book()
        said = self.check(usual, self.paragraph(usual))
        self.assertIn("/ey/ needs KASRA+ya", said, said)
        ipa = self.book(translit="ipa")
        said = self.check(ipa, self.paragraph(ipa))
        self.assertNotIn("/ey/ needs KASRA+ya", said, said)
        self.assertIn("this book's transliteration is IPA", said, "and it says what it did not check")
        self.assertNotIn("Traceback", said)

    def test_the_checks_of_the_text_run_whichever_scheme_the_transliteration_is_in(self):
        ipa = self.book(translit="ipa")
        path = self.paragraph(ipa)
        blob = json.loads(path.read_text(encoding="utf-8"))
        blob["ann"]["sentences"][0]["chunks"][0]["fa"] += "ْ"      # a sukun: this edition never uses it
        path.write_text(json.dumps(blob, ensure_ascii=False), encoding="utf-8")
        self.assertIn("sukun in", self.check(ipa, path))

    def test_the_settled_spellings_of_the_romanisation_are_left_alone_for_ipa(self):
        def doc():
            return {"paragraphs": [{"ann": {"sentences": [{"chunks": [
                {"fa": "پَیدا", "tr": "paydā", "voc": "\\vb{بودن}{x}{هست}{hast}"}]}]}}]}
        usual, ipa = doc(), doc()
        n = normalize_batch.normalize(usual)
        m = normalize_batch.normalize(ipa, ipa=True)
        chunk = usual["paragraphs"][0]["ann"]["sentences"][0]["chunks"][0]
        self.assertEqual(chunk["tr"], "peydā", "the usual scheme's spelling is mended")
        chunk = ipa["paragraphs"][0]["ann"]["sentences"][0]["chunks"][0]
        self.assertEqual(chunk["tr"], "paydā", "an IPA book's sound group is not read as a romanisation")
        self.assertEqual(chunk["fa"], "پِیدا", "but the text's own spelling is settled all the same")
        self.assertGreater(n["ey"], m["ey"] - 1)

    def test_a_video_in_ipa_passes_the_checker_and_a_book_in_ipa_passes_the_readers_doors(self):
        import check_annotations as CA
        for code, ipa_tr in (("fa", "ɛmruːz hɒːl-e"), ("ar", "ʔalʕarabijja"), ("hi", "ɦɪndiː"), ("ja", "nihoŋɡo")):
            td = tempfile.TemporaryDirectory()
            self.addCleanup(td.cleanup)
            v = copy_of("videos", code, td.name) if (FIX / "videos" / languages.get(code).folder).is_dir() else None
            if v is None:
                continue
            says(v / "video.json", translit="ipa")
            ann = json.loads((v / "annotations.json").read_text(encoding="utf-8"))
            for sg in ann["segments"]:
                for ch in sg.get("chunks") or []:
                    if ch.get("tr"):
                        ch["tr"] = ipa_tr
            (v / "annotations.json").write_text(json.dumps(ann, ensure_ascii=False, indent=2), encoding="utf-8")
            errors, warnings = [], []
            for i, sg in enumerate(ann["segments"]):
                for j, ch in enumerate(sg.get("chunks") or []):
                    CA.check_chunk(ch, "caption %d chunk %d" % (i, j), errors.append, warnings.append, languages.get(code))
            self.assertEqual(errors, [], code)
            self.assertEqual([w for w in warnings if "script inside tr" in w], [], code)


# --- the real server ------------------------------------------------------------------------------------
class TheServer(unittest.TestCase):
    """Parseh's real handler on a temporary tree: the options route and the region doors, over HTTP."""

    @classmethod
    def setUpClass(cls):
        import serve
        cls.serve = serve
        cls._td = tempfile.TemporaryDirectory()
        tmp = cls.tmp = Path(cls._td.name)
        root = tmp / "root"
        for kind, code in itertools_product(("books", "videos"), ("fa", "it")):
            copy_of(kind, code, root / ("youtube" if kind == "videos" else ""))
        cls.fa_video = sorted(os.listdir(root / "youtube" / "videos" / "persian"))[0]
        cls.patches = [
            mock.patch.object(serve.Handler, "log_request", lambda *a, **k: None),
            mock.patch.object(network, "STORE", str(tmp / "config" / "network.json")),
            mock.patch.object(P, "STORE", str(tmp / "config" / "prompts.json")),
            mock.patch.object(store, "LIB", tmp / "library"),
            mock.patch.object(serve, "ROOT", str(root)),
            mock.patch.object(serve._AtRoot, "directory", str(root)),
            mock.patch.object(ytpages, "VIDEOS", str(root / "youtube" / "videos")),
            mock.patch.object(ytpages, "oembed", lambda vid: {}),
            mock.patch.object(books, "BOOKS_DIR", str(root / "books")),
        ]
        for p in cls.patches:
            p.start()
        network._CACHE.update({"key": None, "doc": None})
        cls.srv = serve.Server(("127.0.0.1", 0), serve.Handler, None)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        for p in reversed(cls.patches):
            p.stop()
        network._CACHE.update({"key": None, "doc": None})
        cls._td.cleanup()

    def ask(self, method, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.srv.server_address[1], timeout=60)
        data = None if body is None else json.dumps(body).encode("utf-8")
        c.request(method, path, body=data, headers={"Content-Type": "application/json"} if data else {})
        r = c.getresponse()
        raw = r.read()
        c.close()
        try:
            return r.status, json.loads(raw.decode("utf-8"))
        except ValueError:
            return r.status, raw.decode("utf-8", "replace")

    def test_the_options_route_answers_per_surface_and_language_and_is_read_only(self):
        status, got = self.ask("GET", "/__prompt/options?surface=video-region&lang=fa")
        self.assertEqual(status, 200, got)
        self.assertEqual([(o["name"], o["label"], o["value"]) for o in got["options"]],
                         [("translit", "transliteration", "classic"), ("marks", "short vowels", "nomarks")])
        status, got = self.ask("GET", "/__prompt/options?surface=video-region&lang=it")
        self.assertEqual([o["name"] for o in got["options"]], ["translit"])
        status, got = self.ask("GET", "/__prompt/options?surface=video-region&lang=zh")
        self.assertEqual((status, got["options"]), (200, []))
        status, got = self.ask("GET", "/__prompt/options?surface=the-moon&lang=fa")
        self.assertEqual((status, got["ok"]), (400, False))
        status, got = self.ask("GET", "/__prompt/options?surface=video-region&lang=klingon")
        self.assertEqual((status, got["ok"]), (400, False))
        status, _got = self.ask("POST", "/__prompt/options", {})
        self.assertEqual(status, 405)

    def test_with_a_book_or_a_video_the_options_start_from_its_own_record(self):
        book = self.tmp / "root" / "books" / "persian" / "mini-fa" / "book.json"
        video = self.tmp / "root" / "youtube" / "videos" / "persian" / self.fa_video / "video.json"
        for path, query in ((book, "surface=book-region&lang=fa&book=/books/persian/mini-fa"),
                            (book, "surface=book-region&lang=fa&book=persian/mini-fa"),
                            (video, "surface=video-region&lang=fa&video=" + self.fa_video)):
            says(path, translit=None)
            status, got = self.ask("GET", "/__prompt/options?" + query)
            (translit,) = [o for o in got["options"] if o["name"] == "translit"]
            self.assertEqual((translit["value"], translit["fact"]), ("classic", False), query)
            says(path, translit="ipa")
            status, got = self.ask("GET", "/__prompt/options?" + query)
            (translit,) = [o for o in got["options"] if o["name"] == "translit"]
            self.assertEqual((translit["value"], translit["fact"]), ("ipa", True), query)
        # a book that is not on the shelf says nothing of itself
        status, got = self.ask("GET", "/__prompt/options?surface=book-region&lang=fa&book=/books/persian/none")
        self.assertEqual((status, got["options"][0]["fact"]), (200, False))
        says(book, translit=None)
        says(video, translit=None)

    def test_the_region_doors_take_the_choice_and_the_record_and_refuse_nonsense_in_words(self):
        status, got = self.ask("POST", "/books/persian/mini-fa/__region/prompt",
                               {"first": 0, "last": 5, "translit": "ipa", "marks": "1"})
        self.assertEqual(status, 200, got)
        self.assertEqual(got["prompt"].split("\n")[0].split(" · ")[-2:], ["IPA", "marks"])
        self.assertEqual({o["name"]: o["value"] for o in got["options"]}, {"translit": "ipa", "marks": "marks"})
        status, got = self.ask("POST", "/youtube/api/region/prompt",
                               {"video": self.fa_video, "from": 0, "to": 3, "translit": "ipa"})
        self.assertEqual(status, 200, got)
        self.assertTrue(got["prompt"].split("\n")[0].endswith(" · IPA · no marks"))
        for path, body in (("/books/persian/mini-fa/__region/prompt", {"first": 0, "last": 5}),
                           ("/youtube/api/region/prompt", {"video": self.fa_video, "from": 0, "to": 3})):
            status, got = self.ask("POST", path, dict(body, translit="klingon"))
            self.assertEqual((status, got["ok"]), (400, False), path)
            self.assertIn("'klingon' is not a way to write the transliteration", got["error"])

    def test_the_door_that_edits_the_record_takes_the_scheme(self):
        status, got = self.ask("POST", "/youtube/api/editmeta", {"video": self.fa_video, "fields": {"translit": "ipa"}})
        self.assertEqual((status, got["ok"]), (200, True), got)
        status, got = self.ask("POST", "/youtube/api/region/prompt", {"video": self.fa_video, "from": 0, "to": 3})
        self.assertTrue(got["prompt"].split("\n")[0].endswith(" · IPA · no marks"), "the record is the default now")
        status, got = self.ask("POST", "/youtube/api/editmeta", {"video": self.fa_video, "fields": {"translit": "classic"}})
        self.assertEqual((status, got["ok"]), (200, True), got)
        status, got = self.ask("POST", "/youtube/api/region/prompt", {"video": self.fa_video, "from": 0, "to": 3})
        self.assertTrue(got["prompt"].split("\n")[0].endswith(" · no marks") and " · IPA" not in got["prompt"].split("\n")[0])
        status, got = self.ask("POST", "/youtube/api/editmeta", {"video": self.fa_video, "fields": {"translit": "klingon"}})
        self.assertEqual((status, got["ok"]), (400, False))

    def test_the_instructions_of_a_book_made_in_place_take_the_choice_through_the_page_door(self):
        status, got = self.ask("POST", "/books/__making/instructions",
                               {"book": {"lang": "fa", "title": "T", "translit": "ipa"}, "marks": "0"})
        self.assertEqual((status, got.get("ok")), (200, True), got)
        self.assertIn("IPA", got["text"])
        status, got = self.ask("POST", "/books/__making/instructions",
                               {"book": {"lang": "fa", "title": "T", "translit": "klingon"}})
        self.assertEqual((status, got["ok"]), (400, False))
        self.assertIn("'klingon'", got["error"])


if __name__ == "__main__":
    unittest.main()
