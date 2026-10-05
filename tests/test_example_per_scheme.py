# SPDX-License-Identifier: GPL-3.0-or-later
"""The worked example of every language file (brief 6.4): `## Example` of docs/lang/<code>.md, which the
prompts that gloss carry in place of a video of the shelf -- and, with the transliteration set to IPA, the
same example written in IPA, because a model imitates the example it is shown over the rule it was told
(lane T found it with a stand-in chatbot).

What is held here, over every language whose file has an Example:

  * the example is valid as an ANSWER: one fenced JSON block, a list of chunks, each of them accepted by the
    video's checker (youtube/lib/check_annotations.py) and its `voc` by the book's (lib/texwrite.py,
    lib/texparse.py), in both schemes and in all four prompts that gloss;
  * under IPA the example never shows the usual scheme: one that is the same in both schemes is a language
    whose example has no sound that depends on the scheme (SCHEME_FREE), and where a language names one
    string of the usual scheme (USUAL_IN_THE_EXAMPLE) the IPA prompt may not carry it;
  * the same for the examples of the Vocabulary section that show a sound (USUAL_IN_THE_VOCABULARY);
  * a language the owner cannot review says in a note that is never sent that no speaker has reviewed it.
"""
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
for _p in ("markdown/app", "markdown/exlex", "markdown", "youtube/lib", "lib"):
    sys.path.insert(0, os.path.join(ROOT, _p))
import check_annotations                                            # noqa: E402
import languages                                                    # noqa: E402
import promptkit as K                                               # noqa: E402
import texparse                                                     # noqa: E402
import texwrite                                                     # noqa: E402

GLOSSING = ("video-region", "book-region", "video-new", "book-new")
OWNER_READS = ("fa", "it", "en")      # the files that say nothing of a review: he reviews them
CHUNK_KEYS = {"fa", "tr", "voc", "en", "kana", "words"}

# ONE STRING OF THE USUAL SCHEME that the example shows and an IPA prompt must not, for a language that writes
# its example twice: a test cannot know the usual scheme of a language, so a language names its own (one that
# names none is held only to differ)
USUAL_IN_THE_EXAMPLE = {"it": "mòlto", "fr": "mõ frèr", "de": "'münçen", "es": "aʝer vi"}
# a language whose example has no sound that depends on the scheme: English's usual scheme already is IPA,
# Turkish's example has one `tr`, the stress, written the same in both, and its sound slots are empty
SCHEME_FREE = ("en", "tr")
# strings of the Vocabulary section's own examples, in the usual scheme: sounds in the slots of a macro
USUAL_IN_THE_VOCABULARY = {
    "it": ("{prèndere}",),
    "fr": ("{falwar}", "{prãdr}", "{alé}", "{regard}{regardé}", "{avwar}", "{ʒurnal}", "{euy}", "{travay}", "{venü}"),
}


def raw(code):
    with open(os.path.join(K.LANG_DOCS, code + ".md"), encoding="utf-8") as f:
        return f.read()


def has_example(code):
    return os.path.exists(os.path.join(K.LANG_DOCS, code + ".md")) and re.search(r"^## Example$", raw(code), re.M) is not None


def example_text(surface, code, ipa=False):
    options = K.resolve(surface, code, {"translit": "ipa"} if ipa else None)
    return dict(K.language_sections(surface, code, options=options)).get("Example")


def answer_of(text):
    fences = re.findall(r"```json\n(.*?)\n```", text, re.S)
    if len(fences) != 1:
        raise AssertionError("%d json fences in the example, not one" % len(fences))
    return json.loads(fences[0])


def with_an_example():
    return [c for c in languages.CODES if has_example(c)]


class TheWorkedExample(unittest.TestCase):
    def schemes(self, code):
        return (False, True) if languages.get(code).ipa == "offered" else (False,)

    def test_it_is_a_valid_answer_in_every_prompt_and_every_scheme(self):
        seen = 0
        for code in with_an_example():
            L = languages.get(code)
            for ipa in self.schemes(code):
                for surface in GLOSSING:
                    where = "%s %s%s" % (code, surface, " ipa" if ipa else "")
                    text = example_text(surface, code, ipa)
                    self.assertIsNotNone(text, "%s: no Example in the prompt" % where)
                    self.assertNotIn("{{", text, where)
                    chunks = answer_of(text)["chunks"]
                    self.assertTrue(2 <= len(chunks) <= 6, "%s: %d chunks" % (where, len(chunks)))
                    for n, ch in enumerate(chunks):
                        at = "%s chunk %d" % (where, n)
                        self.assertLessEqual(set(ch), CHUNK_KEYS, at)
                        for key in ("fa", "en"):
                            self.assertTrue(isinstance(ch.get(key), str) and ch[key].strip(), "%s: no %s" % (at, key))
                        self.assertEqual(ch["fa"], ch["fa"].strip(), at)
                        errs, warns = [], []
                        check_annotations.check_chunk(ch, at, errs.append, warns.append, lang=code)
                        self.assertEqual((errs, warns), ([], []), at)
                        if ch.get("voc"):
                            texwrite._check_voc(ch["voc"], at)            # the book's checker refuses in words
                            self.assertTrue(texparse.parse_voc(ch["voc"], code), at)
                    self.assertTrue((L.word_sep or "").join(c["fa"] for c in chunks).strip())
                    seen += 1
        self.assertTrue(seen, "no language file has an Example: the check ran on nothing")

    def test_a_language_the_owner_cannot_read_says_in_a_note_never_sent_that_nobody_reviewed_it(self):
        seen = 0
        for code in with_an_example():
            noted = re.search(r"\{\{\?note\}\}.*?reviewed.*?\{\{/note\}\}", raw(code), re.S) is not None
            if code not in OWNER_READS:
                self.assertTrue(noted, "docs/lang/%s.md: the example says nowhere that no speaker has reviewed it" % code)
            for ipa in self.schemes(code):
                for surface in GLOSSING:
                    options = K.resolve(surface, code, {"translit": "ipa"} if ipa else None)
                    sent = K.language_text(surface, code, options=options)
                    self.assertNotIn("reviewed", sent, "%s %s: the maintainer's note is sent" % (code, surface))
            seen += 1
        self.assertTrue(seen, "no language file has an Example: the check ran on nothing")

    def test_under_ipa_the_example_never_shows_the_usual_scheme(self):
        seen = 0
        for code in with_an_example():
            if languages.get(code).ipa != "offered":
                continue
            for surface in GLOSSING:
                usual, ipa = example_text(surface, code), example_text(surface, code, ipa=True)
                if usual == ipa:
                    self.assertIn(code, SCHEME_FREE, "%s %s: the example is the same in both schemes: write its IPA "
                                  "twin ({{?ipa}}), or name the language in SCHEME_FREE and say why" % (code, surface))
                else:
                    mark = USUAL_IN_THE_EXAMPLE.get(code)
                    if mark is not None:
                        self.assertTrue(mark in usual, (code, surface, mark))
                        self.assertTrue(mark not in ipa, "%s %s: an IPA prompt shows %r of the usual scheme in its example"
                                        % (code, surface, mark))
                seen += 1
        self.assertTrue(seen, "no language file with an IPA setting has an Example: the check ran on nothing")

    def test_under_ipa_the_vocabulary_examples_never_show_a_sound_of_the_usual_scheme(self):
        for code, marks in USUAL_IN_THE_VOCABULARY.items():
            for surface in GLOSSING:
                usual = K.language_text(surface, code)
                ipa = K.language_text(surface, code, options={"translit": "ipa"})
                for mark in marks:
                    self.assertTrue(mark in usual, "%s %s: the usual scheme's example %r is gone" % (code, surface, mark))
                    self.assertTrue(mark not in ipa, "%s %s: an IPA prompt shows %r of the usual scheme" % (code, surface, mark))

if __name__ == "__main__":
    unittest.main()
