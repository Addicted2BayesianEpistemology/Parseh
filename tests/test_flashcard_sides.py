# SPDX-License-Identifier: GPL-3.0-or-later
"""Where a vocab or opposites card draws its `context`, `notes` and `source`:
on the side the flip REVEALS, unless `<field>-side: question` puts one on the
side shown first (mdparser.card_extras, the one rule; htmlgen and texgen read
it, the page's random draw moves what it marks).

A card turned round (`direction: reverse`) asks its meaning and answers with
the word, so on it the example, the notes and the source are the word's.  The
table below is the rule written out, once, as a person reads it; every test
that follows holds a renderer to it.  The browser half (the draw, the editor's
toggle, a deck's study page, an export) is tests/flashcard_sides.mjs."""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "markdown" / "exlex", ROOT / "markdown" / "app",
               ROOT / "lib", ROOT / "youtube" / "lib"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import decks      # noqa: E402
import htmlgen    # noqa: E402
import mdparser   # noqa: E402
import store      # noqa: E402
import texgen     # noqa: E402

ALL = ("context", "notes", "source")
Q = "question"
# (direction, what the card says of its fields' sides, the keys that go with
# the WORD -- its target, reading and transliteration -- and the keys that go
# with the MEANING), each in the order they are drawn.  The halves are where
# the card is composed, before `reverse` turns it round: so on a card shown
# meaning first the word's half is the one revealed.
VOCAB = [
    (None,          {},                                       ((), ALL)),
    ("forward",     {},                                       ((), ALL)),
    ("reverse",     {},                                       (ALL, ())),
    ("both-random", {},                                       ((), ALL)),
    ("both-repeat", {},                                       ((), ALL)),
    ("Reverse",     {},                                       (ALL, ())),
    ("forward",     {"context": Q, "notes": Q, "source": Q},  (ALL, ())),
    ("reverse",     {"context": Q, "notes": Q, "source": Q},  ((), ALL)),
    ("both-random", {"context": Q, "notes": Q, "source": Q},  (ALL, ())),
    ("both-repeat", {"context": Q, "notes": Q, "source": Q},  (ALL, ())),
    ("forward",     {"notes": Q},                             (("notes",), ("context", "source"))),
    ("reverse",     {"notes": Q},                             (("context", "source"), ("notes",))),
    ("both-random", {"notes": Q},                             (("notes",), ("context", "source"))),
    ("reverse",     {"context": Q, "source": Q},              (("notes",), ("context", "source"))),
    ("forward",     {"context": Q, "source": Q},              (("context", "source"), ("notes",))),
    # read in any case and with a space round it; `answer` said out is the default said
    ("reverse",     {"notes": " Question "},                  (("context", "source"), ("notes",))),
    ("reverse",     {"notes": "ANSWER", "context": "answer"}, (ALL, ())),
    ("forward",     {"source": "Answer"},                     ((), ALL)),
]
# an opposites card has no `context`: only its notes and its source
OPPOSITES = [
    (None,          {},                                       ((), ("notes", "source"))),
    ("forward",     {},                                       ((), ("notes", "source"))),
    ("reverse",     {},                                       (("notes", "source"), ())),
    ("both-random", {},                                       ((), ("notes", "source"))),
    ("both-repeat", {},                                       ((), ("notes", "source"))),
    ("forward",     {"notes": Q, "source": Q},                (("notes", "source"), ())),
    ("reverse",     {"notes": Q, "source": Q},                ((), ("notes", "source"))),
    ("reverse",     {"source": Q},                            (("notes",), ("source",))),
    ("forward",     {"notes": Q},                             (("notes",), ("source",))),
    # `context-side` means nothing on a card that has no context, and is no error
    ("reverse",     {"context": Q},                           (("notes", "source"), ())),
]
TOKENS = {"target": "WORD", "reading": "READING", "transliteration": "TRANSLIT",
          "meaning": "MEANING", "opposite": "OPPOSITE", "opposite-reading": "OREADING",
          "opposite-transliteration": "OTRANSLIT",
          "context": "CONTEXT", "notes": "NOTES", "source": "SOURCE"}
FIELDS = {"vocab": ("target", "reading", "transliteration", "meaning", "context", "notes", "source"),
          "opposites": ("target", "reading", "transliteration", "opposite", "opposite-reading",
                        "opposite-transliteration", "notes", "source")}


def card(kind="vocab", direction=None, sides=None, extra="", target="en", fields=None):
    """A document of one card whose every field says its own name in capitals."""
    lines = ["card-type: %s" % kind]
    for key in (fields or FIELDS[kind]):
        lines.append("%s: %s" % (key, TOKENS[key]))
    if direction is not None:
        lines.append("direction: %s" % direction)
    for key, value in (sides or {}).items():
        lines.append("%s-side: %s" % (key, value))
    return ("---\ntitle: T\ntarget: %s\n---\n\n:::exercise flashcard\n%s\n%s:::\n"
            % (target, "\n".join(lines), extra))


def block(md):
    return [b for b in mdparser.parse(md)[1] if b["type"] == "exercise"][0]


def html_halves(md, **kw):
    """The fields each half of the card's HTML draws, in the order of the page:
    (the half shown first, the half revealed), as lists of text."""
    html = htmlgen.render_document(md, **kw)["html"]
    a = html.index('<div class="ex-card-front">')
    b = html.index('<div class="ex-card-back"', a)
    c = html.index('<small class="ex-card-hint">', b)

    def fields(part):
        return [re.sub(r"<[^>]+>", "", m) for m in
                re.findall(r'<div class="ex-card-field[^"]*"[^>]*>(.*?)</div>', part)]
    return fields(html[a:b]), fields(html[b:c])


def tex_group(tex, at):
    """The brace group that starts at tex[at] == "{", and where it ends."""
    depth, i = 0, at
    while True:
        c = tex[i]
        if c == "\\":
            i += 2
            continue
        depth += c == "{"
        depth -= c == "}"
        i += 1
        if not depth:
            return tex[at + 1:i - 1], i


def tex_halves(md):
    """(the left half, the right half) of the card printed on paper, as the
    words each says in order -- the half shown first is the left one."""
    tex = texgen.generate(*mdparser.parse(md), colophon=False)
    tex = tex[tex.index("\\begin{document}"):]
    at = tex.index("\\expapercard{") + len("\\expapercard")
    _head, at = tex_group(tex, at)
    left, at = tex_group(tex, at)
    right, _ = tex_group(tex, at)
    words = lambda part: re.findall(r"[A-Z]{4,}", part)
    return words(left), words(right)


def word_of(key):
    return TOKENS[key]


class TheRuleTable(unittest.TestCase):
    """mdparser.card_extras, read off the table."""

    def rows(self):
        for kind, table in (("vocab", VOCAB), ("opposites", OPPOSITES)):
            for direction, sides, want in table:
                yield kind, direction, sides, want

    def test_the_table_is_what_the_parser_says(self):
        for kind, direction, sides, (word, meaning) in self.rows():
            fields = block(card(kind, direction, sides))["fields"]
            self.assertEqual((word, meaning), mdparser.card_extras(fields), (kind, direction, sides))

    def test_it_reads_a_card_that_says_nothing_as_a_vocab_card_going_forward(self):
        self.assertEqual(((), ALL), mdparser.card_extras({}))
        self.assertEqual(((), ALL), mdparser.card_extras({"card-type": "VOCAB"}))
        self.assertEqual((ALL, ()), mdparser.card_extras({"direction": " Reverse "}))

    def test_a_jolly_card_has_none_and_an_unknown_kind_neither(self):
        for kind in ("jolly", "mystery"):
            self.assertEqual(((), ()), mdparser.card_extras({"card-type": kind, "notes-side": "question"}), kind)

    def test_a_custom_back_replaces_them_all_as_it_always_did(self):
        for direction in (None, "reverse", "both-random"):
            for sides in ({}, {"context": Q, "notes": Q, "source": Q}):
                fields = block(card("vocab", direction, sides, fields=("target", "context", "notes", "source"),
                                    extra="back: CUSTOM\n"))["fields"]
                self.assertEqual(((), ()), mdparser.card_extras(fields), (direction, sides))
        # but an opposites card has no `back`, and a stray one takes nothing from it
        self.assertEqual(((), ("notes", "source")), mdparser.card_extras(
            {"card-type": "opposites", "back": "stray"}))

    def test_a_custom_front_keeps_them(self):
        fields = block(card("vocab", "reverse", fields=("meaning", "context", "notes"),
                            extra="front: CUSTOM\n"))["fields"]
        self.assertEqual((ALL, ()), mdparser.card_extras(fields))


class ThePageFollowsTheTable(unittest.TestCase):
    def check(self, kind, first, second, direction, sides, want, where):
        """first and second are the halves as the page draws them (the one
        shown first, the one revealed), whatever drew them."""
        word, meaning = want
        main = {"vocab": ("target", "meaning"), "opposites": ("target", "opposite")}[kind]
        wordhalf = first if TOKENS[main[0]] in first else second
        meaninghalf = first if TOKENS[main[1]] in first else second
        self.assertIsNot(wordhalf, meaninghalf, (kind, direction, sides))
        for key in word:
            self.assertIn(TOKENS[key], wordhalf, (where, kind, direction, sides, key, "goes with the word"))
            self.assertNotIn(TOKENS[key], meaninghalf, (where, kind, direction, sides, key))
        for key in meaning:
            self.assertIn(TOKENS[key], meaninghalf, (where, kind, direction, sides, key, "goes with the meaning"))
            self.assertNotIn(TOKENS[key], wordhalf, (where, kind, direction, sides, key))
        # the extras come last on a half, and in the order context, notes, source
        for half, keys in ((wordhalf, word), (meaninghalf, meaning)):
            tail = [x for x in half if x in {TOKENS[k] for k in ALL}]
            self.assertEqual([TOKENS[k] for k in keys], tail, (where, kind, direction, sides))
            self.assertEqual(half[len(half) - len(tail):], tail, (where, kind, direction, sides, "last"))
        # said the other way, which is what the rule is for: whatever turns the
        # card round, an extra that says nothing is on the half the flip
        # reveals and one that says `question` is on the half shown first
        for key in word + meaning:
            asked = (sides.get(key) or "").strip().lower() == "question"
            self.assertIs(asked, TOKENS[key] in first, (where, kind, direction, sides, key))
        # and the card is turned round only by `reverse`: the half shown first
        # holds the meaning on a reverse card and the word on every other
        reverse = (direction or "").strip().lower() == "reverse"
        self.assertIs(reverse, first is meaninghalf, (where, kind, direction, sides))

    def test_the_page(self):
        for kind, table in (("vocab", VOCAB), ("opposites", OPPOSITES)):
            for direction, sides, want in table:
                first, second = html_halves(card(kind, direction, sides))
                self.check(kind, first, second, direction, sides, want, "page")

    def test_the_editors_preview_shows_both_sides_and_they_are_the_same(self):
        for kind, table in (("vocab", VOCAB), ("opposites", OPPOSITES)):
            for direction, sides, want in table:
                md = card(kind, direction, sides)
                self.assertEqual(html_halves(md), html_halves(md, editor_preview=True), (kind, direction, sides))

    def test_a_deck_draws_it_the_same(self):
        for kind, table in (("vocab", VOCAB), ("opposites", OPPOSITES)):
            for direction, sides, want in table:
                first, second = html_halves(card(kind, direction, sides), in_deck=True)
                self.check(kind, first, second, direction, sides, want, "deck")

    def test_paper(self):
        for kind, table in (("vocab", VOCAB), ("opposites", OPPOSITES)):
            for direction, sides, want in table:
                left, right = tex_halves(card(kind, direction, sides))
                self.check(kind, left, right, direction, sides, want, "paper")

    def test_paper_prints_a_both_random_card_front_first_and_so_the_answers_stay_on_the_back(self):
        for sides in ({}, {"notes": Q}):
            plain = tex_halves(card("vocab", "forward", sides))
            self.assertEqual(plain, tex_halves(card("vocab", "both-random", sides)), sides)
            self.assertEqual(plain, tex_halves(card("vocab", "both-repeat", sides)), sides)
        left, right = tex_halves(card("vocab", "both-random"))
        self.assertEqual(["WORD", "READING", "TRANSLIT"], left)
        self.assertEqual(["MEANING", "CONTEXT", "NOTES", "SOURCE"], right)

    def test_paper_for_every_target_language_alike(self):
        # the rule is not a language's: a right-to-left and two CJK targets draw as English does
        for target in ("fa", "ar", "ja", "zh", "hi"):
            for direction, sides, want in VOCAB[:6] + VOCAB[6:10]:
                md = card("vocab", direction, sides, target=target)
                first, second = html_halves(md)
                self.check("vocab", first, second, direction, sides, want, "page " + target)
                left, right = tex_halves(md)
                self.check("vocab", left, right, direction, sides, want, "paper " + target)


class WhatTheRandomDrawMoves(unittest.TestCase):
    """A both-random card is composed forward, and each of its extras says it
    is one (data-extra): app.js drawFirstSide moves them with the draw.  Every
    other card is drawn as it always was, with nothing added."""

    def test_only_a_both_random_card_marks_its_extras(self):
        for kind, table in (("vocab", VOCAB), ("opposites", OPPOSITES)):
            for direction, sides, (word, meaning) in table:
                html = htmlgen.render_document(card(kind, direction, sides))["html"]
                marked = re.findall(r' data-extra="([a-z]+)"', html)
                if (direction or "").lower() == "both-random":
                    # as it is composed: the word's half, then the meaning's
                    self.assertEqual(list(word + meaning), marked, (kind, sides))
                else:
                    self.assertEqual([], marked, (kind, direction, sides))

    def test_the_marked_fields_are_the_extras_and_nothing_else(self):
        html = htmlgen.render_document(card("vocab", "both-random"))["html"]
        fields = re.findall(r'<div class="ex-card-field ([^"]*)"([^>]*)>(.*?)</div>', html)
        self.assertEqual(7, len(fields))
        for cls, rest, text in fields:
            self.assertEqual(text in ("CONTEXT", "NOTES", "SOURCE"), "data-extra" in rest, (text, rest))
        # as the card was composed: the word's half then the meaning's, every extra on the meaning's
        a = html.index('<div class="ex-card-front">')
        b = html.index('<div class="ex-card-back" hidden>')
        self.assertNotIn("data-extra", html[a:b])
        self.assertEqual(3, html[b:].count("data-extra"))
        self.assertIn('data-card-type="vocab" data-first="random" aria-label="Flip flashcard"', html)

    def test_a_card_that_says_nothing_of_it_is_drawn_exactly_as_it_always_was(self):
        # a forward card: its fields on the back, no attribute added, and a side said out is no change
        md = card("vocab", "forward")
        html = htmlgen.render_document(md)["html"]
        self.assertNotIn("data-extra", html)
        said = card("vocab", "forward", {"context": "answer", "notes": "answer", "source": "answer"})
        # (but for how many lines of the source the card takes)
        same = lambda md: re.sub(r' data-src-end="\d+"', "", htmlgen.render_document(md)["html"])
        self.assertEqual(same(card("vocab", "forward")), same(said))
        self.assertEqual(same(card("vocab", "forward")), same(card("vocab", None)))

    def test_question_puts_a_reverse_card_back_as_it_was(self):
        # what a reverse card was: the forward card's two sides, turned round whole
        forward = html_halves(card("vocab", "forward"))
        every = {"context": Q, "notes": Q, "source": Q}
        self.assertEqual(forward[::-1], html_halves(card("vocab", "reverse", every)))
        forward = html_halves(card("opposites", "forward"))
        self.assertEqual(forward[::-1], html_halves(card("opposites", "reverse", {"notes": Q, "source": Q})))
        # and without it the meaning opens the card alone
        first, second = html_halves(card("vocab", "reverse"))
        self.assertEqual(["MEANING"], first)
        self.assertEqual(["WORD", "READING", "TRANSLIT", "CONTEXT", "NOTES", "SOURCE"], second)


class TheCardsOwnFields(unittest.TestCase):
    def test_the_pictures_and_recordings_stay_on_the_side_that_names_them(self):
        extra = "front-image: images/a.png\nback-image: images/b.png\nfront-audio: audio/a.mp3\nback-audio: audio/b.mp3\n"
        for direction in ("forward", "reverse"):
            md = card("vocab", direction, extra=extra)
            html = htmlgen.render_document(md)["html"]
            first = html[html.index('<div class="ex-card-front">'):html.index('<div class="ex-card-back"')]
            second = html[html.index('<div class="ex-card-back"'):]
            a, b = ("a", "b") if direction == "forward" else ("b", "a")
            self.assertIn("images/%s.png" % a, first)
            self.assertIn("audio/%s.mp3" % a, first)
            self.assertIn("images/%s.png" % b, second)
            self.assertIn("audio/%s.mp3" % b, second)
            # the picture, then the recording, then the text
            for half in (first, second):
                self.assertLess(half.index("images/"), half.index("audio/"))
                self.assertLess(half.index("audio/"), half.index("ex-card-field"))

    def test_a_custom_front_is_the_words_half_and_its_extras_come_after_it(self):
        md = card("vocab", "reverse", fields=("meaning", "context", "notes", "source"), extra="front: CUSTOM\n")
        first, second = html_halves(md)
        self.assertEqual(["MEANING"], first)
        self.assertEqual(["CUSTOM", "CONTEXT", "NOTES", "SOURCE"], second)
        first, second = html_halves(card("vocab", "forward", {"notes": Q},
                                         fields=("meaning", "context", "notes", "source"), extra="front: CUSTOM\n"))
        self.assertEqual(["CUSTOM", "NOTES"], first)
        self.assertEqual(["MEANING", "CONTEXT", "SOURCE"], second)

    def test_a_custom_back_shows_none_of_them_on_either_side(self):
        # `back` replaces the meaning, the example, the notes and the source: they were never drawn
        for direction in (None, "reverse", "both-random"):
            for sides in ({}, {"context": Q, "notes": Q, "source": Q}):
                md = card("vocab", direction, sides, fields=("target", "context", "notes", "source"),
                          extra="back: CUSTOM\n")
                first, second = html_halves(md)
                self.assertEqual(sorted([["WORD"], ["CUSTOM"]]), sorted([first, second]), (direction, sides))
                left, right = tex_halves(md)
                self.assertEqual(sorted([["WORD"], ["CUSTOM"]]), sorted([left, right]), (direction, sides))

    def test_an_opposites_card_draws_no_context_and_context_side_changes_nothing(self):
        plain = html_halves(card("opposites", "reverse"))
        said = html_halves(card("opposites", "reverse", {"context": Q}, extra="context: STRAY\n"))
        self.assertEqual(plain, said)
        self.assertNotIn("STRAY", "".join(said[0] + said[1]))

    def test_a_jolly_card_is_untouched(self):
        jolly = ("---\ntitle: T\ntarget: en\n---\n\n:::exercise flashcard\ncard-type: jolly\n"
                 "front-primary: A\nfront-secondary: B\nback-primary: C\nback-secondary: D\n%s%s:::\n")
        same = lambda md: re.sub(r' data-src-end="\d+"', "", htmlgen.render_document(md)["html"])
        for direction in ("", "direction: reverse\n", "direction: both-random\n"):
            plain = same(jolly % (direction, ""))
            said = same(jolly % (direction, "notes-side: question\ncontext-side: answer\n"))
            self.assertEqual(plain, said)
            self.assertNotIn("data-extra", said)

    def test_a_field_with_nothing_in_it_leaves_no_trace(self):
        md = card("vocab", "reverse", {"notes": Q}, fields=("target", "meaning", "context", "source"))
        first, second = html_halves(md)
        self.assertEqual(["MEANING"], first)
        self.assertEqual(["WORD", "CONTEXT", "SOURCE"], second)


class AValueThatIsNeitherIsTheCardsError(unittest.TestCase):
    def test_the_parser_names_the_field(self):
        for key in ALL:
            for value in ("banana", "front", "back", "both", "1", "answers"):
                for kind in ("vocab", "opposites"):
                    b = block(card(kind, None, {key: value}))
                    self.assertEqual(["%s-side must be answer or question" % key], b["errors"], (kind, key, value))
        self.assertEqual(["context-side must be answer or question", "source-side must be answer or question"],
                         block(card("vocab", None, {"context": "x", "notes": "question", "source": "y"}))["errors"])

    def test_in_any_case_both_values_are_sound(self):
        for value in ("answer", "Answer", "ANSWER", "question", "Question", " question "):
            self.assertEqual([], block(card("vocab", None, {"notes": value}))["errors"], value)

    def test_an_empty_one_says_nothing(self):
        self.assertEqual([], block(card("vocab", extra="notes-side:\n"))["errors"])

    def test_the_card_is_then_not_drawn_and_says_why(self):
        html = htmlgen.render_document(card("vocab", None, {"notes": "banana"}))["html"]
        self.assertIn("Exercise needs attention.", html)
        self.assertIn("notes-side must be answer or question", html)
        self.assertNotIn("ex-flashcard", html)

    def test_a_jolly_card_is_told_too_since_the_value_is_wrong_wherever_it_stands(self):
        jolly = ("---\ntitle: T\ntarget: en\n---\n\n:::exercise flashcard\ncard-type: jolly\n"
                 "front-primary: A\nback-primary: B\nnotes-side: banana\n:::\n")
        self.assertEqual(["notes-side must be answer or question"], block(jolly)["errors"])

    def test_the_other_values_of_a_direction_are_not_a_side(self):
        # `direction` has its own words; a side is only ever answer or question
        for value in ("forward", "reverse"):
            self.assertTrue(block(card("vocab", None, {"notes": value}))["errors"], value)


class InADeck(unittest.TestCase):
    """A both-repeat card goes into a deck as two, one a direction; each is
    drawn by the rule for its own, and what is stored says nothing new."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        root = Path(self.td.name)
        self.old = (decks.set_dir(root / "exercises"), store.use_library(root / "library"),
                    decks.set_clips_dir(root / "clips"))
        s = decks.create_deck("Sides", "en")
        self.fs = (s["folder"], s["slug"])

    def tearDown(self):
        decks.set_dir(self.old[0])
        store.use_library(self.old[1])
        decks.set_clips_dir(self.old[2])
        self.td.cleanup()

    def exercise(self, kind="vocab", sides=None):
        return card(kind, "both-repeat", sides).split("---\n\n", 1)[1].rstrip("\n")

    def drawn(self, item):
        html = decks.render_item({"lang": "en"}, item, None)
        a = html.index('<div class="ex-card-front">')
        b = html.index('<div class="ex-card-back"', a)
        c = html.index('<small class="ex-card-hint">', b)
        text = lambda part: [re.sub(r"<[^>]+>", "", m) for m in
                             re.findall(r'<div class="ex-card-field[^"]*"[^>]*>(.*?)</div>', part)]
        return text(html[a:b]), text(html[b:c])

    def test_each_of_the_two_cards_follows_its_own_direction(self):
        for kind, sides in (("vocab", {}), ("vocab", {"notes": Q}), ("vocab", {"context": Q, "source": Q}),
                            ("opposites", {}), ("opposites", {"source": Q})):
            made = decks.add_item(*self.fs, self.exercise(kind, sides), force=True)["items"]
            forward, reverse = (decks.get_item(*self.fs, i["id"]) for i in made)
            self.assertEqual(("forward", "reverse"), (forward["direction"], reverse["direction"]))
            # the sides the author wrote are kept on both, and nothing else is added
            for item in (forward, reverse):
                for key, value in sides.items():
                    self.assertIn("%s-side: %s\n" % (key, value), item["markdown"])
                self.assertEqual(len(sides), item["markdown"].count("-side:"))
            extras = ALL if kind == "vocab" else ("notes", "source")
            meaning = "MEANING" if kind == "vocab" else "OPPOSITE"
            # whichever asks, a field that says nothing is on what answers and `question` is on what asks
            for item, asks in ((forward, "WORD"), (reverse, meaning)):
                ask, tell = self.drawn(item)
                self.assertEqual(asks, ask[0], (kind, sides, item["direction"]))
                for key in extras:
                    self.assertIn(TOKENS[key], ask if key in sides else tell, (kind, sides, item["direction"], key))
                    self.assertNotIn(TOKENS[key], tell if key in sides else ask, (kind, sides, item["direction"], key))


class ThePromptSaysSo(unittest.TestCase):
    def test_the_exercise_prompt_names_the_three_fields_and_where_they_go(self):
        prompt = (ROOT / "markdown" / "exlex" / "EXERCISES_PROMPT.md").read_text(encoding="utf-8")
        card_part = prompt[prompt.index("{{?type_flashcard}}"):prompt.index("{{/type_flashcard}}")]
        for words in ("`context-side: question`", "`notes-side: question`", "`source-side: question`",
                      "(the default, `answer`, is never written)"):
            self.assertIn(words, card_part)
        flat = " ".join(card_part.split())
        self.assertIn("go on the side the card turns to", flat)
        self.assertEqual(("answer", "question"), mdparser.CARD_SIDES)
        self.assertEqual(("context", "notes", "source"), mdparser.CARD_EXTRAS["vocab"])
        self.assertEqual(("notes", "source"), mdparser.CARD_EXTRAS["opposites"])


if __name__ == "__main__":
    unittest.main()
