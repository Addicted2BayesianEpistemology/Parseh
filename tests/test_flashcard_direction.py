# SPDX-License-Identifier: GPL-3.0-or-later
"""Which side a flashcard shows first: forward, reverse, both-random and
both-repeat.  The parser refuses anything else; HTML marks a random card for
the page to draw and says in a both-repeat card's head, beside its kicker, that
a deck will ask both sides (never in a deck nor in an exported page); paper
prints every value but reverse front first and says nothing."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "markdown" / "exlex", ROOT / "markdown" / "app",
               ROOT / "lib", ROOT / "youtube" / "lib"):
    sys.path.insert(0, str(folder))

import decks
import htmlgen
import mdparser
import texgen

NOTE = "When exported to a deck, both sides will be asked."


def card(direction, target="fa", kind="vocab"):
    fields = {
        "vocab": {"fa": "target: [سلام]{tl}\nmeaning: hello\n",
                  "en": "target: clock\nmeaning: a thing that tells the time\n",
                  "ja": "target: [猫]{tl}\nmeaning: cat\n",
                  "zh": "target: [猫]{tl}\nmeaning: cat\n"},
        "jolly": {t: "front-primary: front side\nback-primary: back side\n"
                  for t in ("fa", "en", "ja", "zh")},
    }[kind][target]
    return ("---\ntitle: T\ntarget: %s\n---\n\n:::exercise flashcard\ncard-type: %s\n%s%s:::\n"
            % (target, kind, fields, ("direction: %s\n" % direction) if direction else ""))


def block(md):
    return [b for b in mdparser.parse(md)[1] if b["type"] == "exercise"][0]


class FlashcardDirectionTests(unittest.TestCase):
    def test_the_four_values_are_sound_in_any_case_and_anything_else_needs_attention(self):
        for value in (None, "forward", "reverse", "both-random", "both-repeat",
                      "Both-Repeat", "BOTH-RANDOM"):
            for kind in ("vocab", "jolly"):
                self.assertEqual([], block(card(value, kind=kind))["errors"], (value, kind))
        for value in ("both", "sideways", "front", "target-to-translation"):
            self.assertEqual(["direction must be forward, reverse, both-random or both-repeat"],
                             block(card(value))["errors"], value)
        html = htmlgen.render_document(card("both"))["html"]
        self.assertIn("Exercise needs attention.", html)
        self.assertNotIn("ex-flashcard", html)

    def test_a_matching_exercises_direction_is_its_own(self):
        md = ("---\ntitle: T\ntarget: en\n---\n\n:::exercise match-translations\n"
              "direction: translation-to-target\n- cat => gatto\n:::\n")
        self.assertEqual([], block(md)["errors"])

    def test_the_old_bidirectional_line_is_read_and_changes_nothing(self):
        md = card("").rstrip()[:-3] + "bidirectional: true\n:::\n"
        b = block(md)
        self.assertEqual([], b["errors"])
        self.assertEqual("true", b["fields"]["bidirectional"])
        html = htmlgen.render_document(md)["html"]
        self.assertNotIn("ex-card-note", html)
        self.assertNotIn("data-first", html)

    def test_forward_and_reverse_are_drawn_as_they_always_were(self):
        for value in (None, "forward"):
            html = htmlgen.render_document(card(value, "en"))["html"]
            self.assertIn('<div class="ex-flashcard" role="button" tabindex="0" data-card-type="vocab" '
                          'aria-label="Flip flashcard" aria-pressed="false">', html)
            self.assertNotIn("ex-card-note", html)
        front = self.first_side(htmlgen.render_document(card("reverse", "en"))["html"])
        self.assertIn("a thing that tells the time", front)
        self.assertNotIn("clock", front)

    @staticmethod
    def first_side(html):
        start = html.index('<div class="ex-card-front">')
        return html[start:html.index('<div class="ex-card-back"', start)]

    def test_both_random_is_marked_for_the_page_to_draw_and_is_front_first_as_sent(self):
        for target in ("fa", "en", "ja", "zh"):
            for kind in ("vocab", "jolly"):
                html = htmlgen.render_document(card("both-random", target, kind))["html"]
                self.assertIn('data-card-type="%s" data-first="random" aria-label="Flip flashcard"' % kind, html)
                self.assertNotIn("ex-card-note", html)
                self.assertNotIn(" hidden", self.first_side(html))
                self.assertRegex(html, r'<div class="ex-card-back" hidden>')
        # a preview shows both sides, so there is nothing to draw
        preview = htmlgen.render_document(card("both-random"), editor_preview=True)["html"]
        self.assertIn('class="ex-flashcard flipped"', preview)
        self.assertIn('data-first="random"', preview)

    def test_both_repeat_says_so_in_the_head_beside_the_kicker_and_not_on_the_card(self):
        head = ('<div class="ex-head"><span class="ex-kicker">Flashcard</span>'
                '<span class="ex-card-note" dir="ltr">%s</span><button type="button" class="ex-card-zoom"' % NOTE)
        for target in ("fa", "en", "ja", "zh"):
            for kind in ("vocab", "jolly"):
                html = htmlgen.render_document(card("both-repeat", target, kind))["html"]
                self.assertNotIn("data-first", html)
                self.assertEqual(1, html.count('class="ex-card-note"'))
                self.assertIn(head, html)
                self.assertNotIn(NOTE, html[html.index('<div class="ex-body"'):], "neither on the card nor under it")
                self.assertNotIn(" hidden", self.first_side(html))
        # front first, as forward
        self.assertEqual(self.first_side(htmlgen.render_document(card("both-repeat", "en"))["html"]),
                         self.first_side(htmlgen.render_document(card("forward", "en"))["html"]))
        # an editor's preview shows it too, before its buttons
        preview = htmlgen.render_document(card("both-repeat"), editor_preview=True)["html"]
        self.assertRegex(preview, r'<span class="ex-kicker">Flashcard</span><span class="ex-card-note" dir="ltr">'
                         + re.escape(NOTE) + r'</span><button type="button" class="ex-card-zoom"[^>]*>[^<]*</button>'
                         r'<button type="button" class="ex-edit"')
        self.assertIn("ex-card-note", htmlgen.render_document(card("both-repeat"), in_deck=False, export=False)["html"])
        # a deck's own drawing and an exported page do not
        self.assertNotIn("ex-card-note", htmlgen.render_document(card("both-repeat"), in_deck=True)["html"])
        self.assertNotIn("ex-card-note", htmlgen.render_document(card("both-repeat"), export=True)["html"])
        self.assertNotIn(NOTE, decks.render_item({"lang": "en"}, {"markdown": card("both-repeat", "en").split("---\n\n", 1)[1]},
                                                 None))
        # a card that needs attention says nothing
        bad = card("both-repeat", "en", "jolly").replace("front-primary: front side\n", "")
        self.assertTrue(block(bad)["errors"])
        self.assertNotIn("ex-card-note", htmlgen.render_document(bad)["html"])

    def test_paper_prints_every_value_but_reverse_front_first_and_says_nothing(self):
        def body(value, target="en"):
            tex = texgen.generate(*mdparser.parse(card(value, target)), colophon=False)
            return tex[tex.index("\\begin{document}"):]

        forward = body("forward")
        self.assertIn("clock", forward)
        self.assertLess(forward.index("clock"), forward.index("a thing that tells the time"))
        for value in ("both-random", "both-repeat", "Both-Repeat"):
            paper = body(value)
            self.assertEqual(forward, paper, value)
            self.assertNotIn("deck", paper.lower())
            self.assertNotIn("asked", paper)
        reverse = body("reverse")
        self.assertLess(reverse.index("a thing that tells the time"), reverse.index("clock"))
        for target in ("fa", "ja", "zh"):
            plain = body("forward", target)
            for value in ("both-random", "both-repeat"):
                self.assertEqual(plain, body(value, target), (target, value))

    def test_the_prompt_given_to_a_model_names_all_four(self):
        prompt = (ROOT / "markdown" / "exlex" / "EXERCISES_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("`direction: forward|reverse|both-random|both-repeat`", prompt)
        self.assertEqual(("forward", "reverse", "both-random", "both-repeat"), mdparser.FLASHCARD_DIRECTIONS)


if __name__ == "__main__":
    unittest.main()
