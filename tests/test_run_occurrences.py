# SPDX-License-Identifier: GPL-3.0-or-later
"""The page's hover editors name what they edit by position, and the store
finds it in the source by counting the same way
(markdown/app/htmlgen.py, markdown/app/store.py, markdown/exlex/mdparser.py).

    python3 -m unittest discover -s tests -p test_run_occurrences.py

A run of the target language is named by (text, occurrence): the colour
palette, the transliteration and the reading all send it, and
store._run_matches finds the n-th run with that text in the source.  A
target-language block is named by (kind, content, occurrence), which the
target-text overlay sends to store.tl_edit_markdown.  Whenever the page and
the source count differently, an edit lands on the wrong copy of the word.

Every construct below is a place the two used to count differently: a note
holding a mark, a note's indented lines, a list item going on over a line,
a run wrapped over a line break, a sentence with blanks in an exercise, the
order an exercise is drawn in, what an exercise does not draw, a lemma's
headword in a `{tl}` mark, a front matter's other keys, a dropped `#`
heading, a formula.  Each is checked the way the palette uses it: every run
the page offers is coloured through the store, the page drawn again, and
exactly that run must have come out in the new colour -- in the reading view
and in the editor's preview, which draws exercises solved."""
import re
import sys
import unittest
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "markdown" / "exlex", ROOT / "markdown" / "app", ROOT / "lib"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import htmlgen    # noqa: E402
import mdparser   # noqa: E402
import store      # noqa: E402

MARK = "#ABCDEF"          # a colour no document here uses


def doc(body, target="fa"):
    return "---\ntitle: T\nlang: en\ntarget: %s\n---\n\n%s\n" % (target, body)


_TAG = re.compile(r"<(/?)([a-z0-9]+)((?:[^>\"]|\"[^\"]*\")*)>")
_ATTR = re.compile(r'([a-z-]+)="([^"]*)"')
_VOID = {"br", "img", "hr", "input", "meta", "link", "source", "wbr"}


class page:
    """The runs and target blocks the page offers, in document order: a run
    as (text, occurrence, whether it is drawn in MARK), a block as (kind,
    content, occurrence).  htmlgen writes every attribute value quoted and
    escaped, so its tags are read with a pattern."""

    def __init__(self, md, preview=False):
        html = htmlgen.render_document(md, editor_preview=preview)["html"]
        stack, self.runs, self.blocks = [], [], []
        for m in _TAG.finditer(html):
            close, tag = m.group(1), m.group(2)
            if tag in _VOID:
                continue
            if close:
                while stack and stack.pop()[0] != tag:
                    pass
                continue
            a = {k: unescape(v) for k, v in _ATTR.findall(m.group(3))}
            coloured = a.get("data-color") == MARK
            if "data-fa" in a and "data-occ" in a:
                self.runs.append((a["data-fa"], int(a["data-occ"]),
                                  coloured or any(c for _, c in stack)))
            if "data-tl-kind" in a and "data-tl-src" in a:
                self.blocks.append((a["data-tl-kind"], a["data-tl-src"], int(a["data-tl-occ"])))
            stack.append((tag, coloured))


def drift(md, preview=False):
    """tests/smoke.py occurrence_drift: every run the page numbers, against
    the number of hits the store finds for its text."""
    store._target_of(md)
    numbers = {}
    for text, occ, _ in page(md, preview).runs:
        numbers.setdefault(text, []).append(occ)
    return ["%s: page %s, source %d" % (t, occs, len(store._run_matches(md, t)))
            for t, occs in numbers.items()
            if sorted(occs) != list(range(len(store._run_matches(md, t))))]


def misplaced_colours(md, preview=False, only=None, skip=(), before=None):
    """Colour every run the page offers (or those with the text `only`, but
    not the (text, occurrence) pairs in `skip`) through the store, one at a
    time, and say where each did not land on that run and on it alone.
    `before` is the page's runs when the caller has them already."""
    before = before or page(md, preview).runs
    out = []
    for text, occ, _ in before:
        if (only is not None and text != only) or (text, occ) in skip:
            continue
        try:
            after = page(store.recolor_markdown(md, text, occ, MARK), preview).runs
        except store.StoreError as e:
            out.append("%s #%d: %s" % (text, occ, e))
            continue
        marked = [(t, o) for t, o, m in after if m]
        if [(text, occ)] != [x for x in marked if x[0] == text] or len(after) != len(before):
            out.append("%s #%d: coloured %s" % (text, occ, marked))
    return out


def changed(before, after):
    return [b for a, b in zip(before.split("\n"), after.split("\n")) if a != b]


class RunNumberingTests(unittest.TestCase):

    def assertAgree(self, md, word=None):
        for preview in (False, True):
            self.assertEqual([], drift(md, preview), "preview" if preview else "reader")
            self.assertEqual([], misplaced_colours(md, preview, word),
                             "preview" if preview else "reader")

    def test_a_note_holding_a_mark_is_one_note(self):
        # the Arabic and German starters: a note with a mark inside, over two
        # lines; the words after the mark used to be counted in the source
        for target, body, word in (
                ("fa", "Its vowels^[a note: [کتاب]{translit:ketâb} and کتاب\nin it.] and کتاب here.\n\n"
                       "Then کتاب again.", "کتاب"),
                ("de", "A letter [ß]{tl}.^[Its name is [das Eszett]{tl}. Swiss\n"
                       "spelling writes [Strasse]{tl} for [Straße]{tl}.] Then [Straße]{tl}\n"
                       "and [Straße]{tl} again.", "Straße")):
            md = doc(body, target)
            self.assertAgree(md, word)
            html = htmlgen.render_document(md)["html"]
            self.assertEqual(2, len(re.findall(r'data-fa="%s"' % word, html)), target)

    def test_a_note_definition_goes_on_over_its_indented_lines(self):
        # the Italian, French and Spanish starters
        for target, body, word in (
                ("it", "The article[^1] and [gli]{tl}.\n\n[^1]: Only the singular: [l'amica]{tl}.\n"
                       "  Older books write [gl'Italiani]{tl}, today [gli]{tl}.\n\n"
                       "Then [gli]{tl} again.", "gli"),
                ("fa", "> A box with a note[^b] and کتاب.\n>\n> [^b]: defined in the box, کتاب\n"
                       ">   and going on with کتاب.\n\nThen کتاب.", "کتاب")):
            self.assertAgree(doc(body, target), word)
        md = doc("A note[^1] and [gli]{tl}.\n\n[^1]: first line\n  [gli]{tl} on the second.\n\n"
                 "Then [gli]{tl} again.", "it")
        new = store.recolor_markdown(md, "gli", 1, "teal")
        self.assertEqual(["Then [gli]{teal} again."], changed(md, new))

    def test_a_list_item_going_on_over_a_line_is_one_item(self):
        # the English starter: an item's second line that is nothing but a
        # mark was taken for a paragraph of that mark, a block, and skipped
        md = doc("- **Noun** the stress: [a record]{tl},\n  [a world record]{tl}\n"
                 "- **Verb** [to record]{tl}\n\nAnd [a world record]{tl} again.", "en")
        self.assertAgree(md)
        new = store.recolor_markdown(md, "a world record", 1, "teal")
        self.assertEqual(["And [a world record]{teal} again."], changed(md, new))
        # a line of nothing but the script, likewise
        self.assertAgree(doc("- **Family** كَتَبَ, كَاتِب,\n  كُتُب كُتُب\n- next كُتُب\n\n"
                             "The end كُتُب.", "ar"), "كُتُب")

    def test_a_run_wrapped_over_a_line_break_is_one_run(self):
        md = doc("It ends with من به\nمدرسه می‌روم and more.\n\n"
                 "> A box with من به\n> مدرسه می‌روم in it.\n\n"
                 "- An item with من به\n  مدرسه می‌روم on two lines.\n\n"
                 "A word at the end کتاب\nthen کتاب.")
        self.assertAgree(md)
        self.assertEqual(3, len(store._run_matches(md, "من به مدرسه می‌روم")))
        # the mark keeps the line break, and the box its mark
        new = store.recolor_markdown(md, "من به مدرسه می‌روم", 1, "teal")
        self.assertEqual(["> A box with [من به", "> مدرسه می‌روم]{teal} in it."],
                         changed(md, new))
        self.assertIn('data-fa="من به مدرسه می‌روم"', htmlgen.render_document(new)["html"])
        # and a Latin mark wrapped the same way
        md = doc("A wrapped [das\nBuch]{tl} and [das Buch]{tl}.", "de")
        self.assertAgree(md)
        new = store.recolor_markdown(md, "das Buch", 0, "teal")
        self.assertEqual(["Buch]{teal} and [das Buch]{tl}."], changed(md, new))
        self.assertIn("\nA wrapped [das\nBuch]{teal}", new)

    def test_a_sentence_with_blanks_is_cut_where_the_page_cuts_it(self):
        # the Italian, French, German, English and Spanish starters: every
        # piece of the sentence is a run of its own on the page
        md = doc(":::exercise fill-blanks\nprompt: Complete.\n"
                 "text: [Gestern [[aux]] ich nach Hamburg [[verb]].]{tl}\n"
                 "- [aux] [bin]{tl}\n- [verb] [gefahren]{tl}\n:::\n\n"
                 "Later [Gestern]{tl} and [.]{tl}.", "de")
        self.assertAgree(md)
        self.assertEqual(2, len(store._run_matches(md, "Gestern")))
        # colouring a piece writes the sentence out as its pieces, which the
        # parser makes of it anyway: the page is the same, the piece coloured
        new = store.recolor_markdown(md, "ich nach Hamburg", 0, "teal")
        self.assertEqual(["text: [Gestern]{tl} [[aux]] [ich nach Hamburg]{teal} [[verb]][.]{tl}"],
                         changed(md, new))
        # the Hindi starter: for a script language each piece is a `{tl}`
        # stretch, which offers no word
        md = doc(":::exercise fill-blanks\ntext: [मैं छात्र [[am]] और बहन [[is]]।]{tl}\n"
                 "- [am] हूँ\n- [is] है\n:::\n\nA danda । here.", "hi")
        self.assertAgree(md)
        self.assertEqual(1, len(store._run_matches(md, "।")))

    def test_an_exercise_is_numbered_in_the_order_it_is_written(self):
        for target, w, v in (("fa", "کتاب", "دفتر"), ("de", "[Buch]{tl}", "[Heft]{tl}")):
            md = doc(":::exercise single-choice\nprompt: Which is %(w)s?\n"
                     "explanation-correct: %(w)s is it.\n- [x] %(w)s\n- [ ] %(v)s\n:::\n\n"
                     ":::exercise match-translations\n- %(v)s => %(w)s\n- %(w)s => book\n:::\n\n"
                     ":::exercise match-opposites\ndirection: translation-to-target\n"
                     "- %(w)s => %(v)s\n- %(v)s => %(w)s\n:::\n\n"
                     ":::exercise fill-blanks\ntext: A %(v)s [[b]] and [[a]].\n"
                     "- [a] %(w)s\n- [b] %(v)s\n- [ ] %(w)s\n:::\n\n"
                     ":::exercise order-sentences\n- [2] %(w)s %(v)s\n- [1] %(v)s\n- [3] %(w)s\n:::\n\n"
                     ":::exercise flashcard\ncard-type: vocab\ndirection: reverse\n"
                     "target: %(w)s\nmeaning: a %(w)s\n:::\n\nThe end %(w)s." % {"w": w, "v": v},
                     target)
            self.assertAgree(md)
        # the explanation written above the rows is counted above them
        md = doc(":::exercise single-choice\nexplanation-correct: کتاب is it.\n- [x] کتاب\n"
                 "- [ ] دفتر\n:::")
        new = store.recolor_markdown(md, "کتاب", 0, "teal")
        self.assertEqual(["explanation-correct: [کتاب]{teal} is it."], changed(md, new))
        html = htmlgen.render_document(md)["html"]
        self.assertLess(html.index('data-fa="کتاب" data-occ="1"'), html.index('data-fa="کتاب" data-occ="0"'))

    def test_what_an_exercise_does_not_draw_is_not_counted(self):
        md = doc(":::exercise single-choice\nprompt: About کتاب\nhint: a field nobody reads کتاب\n"
                 "<!-- a comment کتاب -->\n- کتاب without its mark\n:::\n\n"
                 ":::exercise flashcard\ncard-type: vocab\nfront: کتاب front\ntarget: کتاب hidden\n"
                 "meaning: book\n:::\n\n"
                 ":::exercise single-choice\nexplanation: کتاب old\nexplanation-correct: کتاب new\n"
                 "- [x] دفتر\n:::\n\nThe end کتاب.")
        self.assertAgree(md)
        self.assertEqual(4, len(store._run_matches(md, "کتاب")))
        new = store.recolor_markdown(md, "کتاب", 3, "teal")
        self.assertEqual(["The end [کتاب]{teal}."], changed(md, new))

    def test_a_lemma_headword_in_a_target_mark_is_a_run(self):
        md = doc("## [کتاب]{tl} | ketâb | Arabic\n\nA کتاب after it.\n\n"
                 "## [دفتر]{fa} | daftar | Greek\n\nA دفتر and [دفتر]{tl}.")
        self.assertAgree(md)

    def test_what_is_drawn_as_no_words_is_not_counted(self):
        md = ("---\ntitle: Misc کتاب\nsubtitle: sub کتاب\ntags: کتاب\n---\n\n"
              "# A heading the title drops کتاب\n\nText کتاب.\n\n"
              ":::math\n\\text{کتاب} = x\n:::\n\n"
              "Inline [\\text{کتاب}]{math} maths, then کتاب after.\n\n"
              "> # A box's heading, dropped کتاب\n>\n> Box text کتاب.\n\n"
              "![A caption with کتاب](images/a.png)\n\nThe end کتاب.")
        self.assertAgree(md, "کتاب")
        fm, _ = mdparser.parse(md)
        # the fences and `tags:`, the dropped heading, the formula, the box's heading
        self.assertEqual([0, 3, 4, 6, 10, 11, 12, 16], fm["_silent_lines"])
        self.assertEqual([1, 2], fm["_title_lines"])
        # no title: the subtitle and the note are drawn nowhere either
        fm, _ = mdparser.parse("---\nsubtitle: s\nnote: n\n---\n\ntext")
        self.assertEqual([0, 1, 2, 3], fm["_silent_lines"])

    def test_the_starters_colour_every_repeated_run_where_it_is(self):
        # every language's starter is a tour of the whole dialect; a run
        # that appears more than once is coloured through the store at its
        # first, its second and its last place -- a count that is off by one
        # anywhere before shows at one of them
        for path in sorted((ROOT / "markdown" / "exlex" / "starters").glob("*.md")):
            md = path.read_text(encoding="utf-8")
            self.assertEqual([], drift(md), path.name)
            runs, words = page(md).runs, {}
            for text, occ, _ in runs:
                words[text] = words.get(text, 0) + 1
            for word, n in sorted(words.items()):
                if n < 2:
                    continue
                skip = {(word, k) for k in range(2, n - 1)}
                self.assertEqual([], misplaced_colours(md, False, word, skip, runs),
                                 "%s: %s" % (path.name, word))


class TargetBlockNumberingTests(unittest.TestCase):
    """The target-text overlay sends the block's kind, its text and the
    occurrence the page gave it (data-tl-occ); tl_edit_markdown must
    replace exactly that block."""

    def assertEachBlockIsItself(self, md, preview=False):
        before = page(md, preview).blocks
        for i, (kind, content, occ) in enumerate(before):
            new = store.tl_edit_markdown(md, kind, content, occ, ["ZZ%d" % i])
            after = page(new, preview).blocks
            self.assertEqual(len(before), len(after), (kind, content, occ))
            self.assertIn("ZZ%d" % i, after[i][1], (kind, content, occ))

    def test_a_latin_target_counts_only_its_whole_paragraph_blocks(self):
        # an inline `[…]{tl}` is a run for a Latin-script target, no block
        md = doc("An inline [Buch]{tl} first.\n\n[Buch]{tl}\n\n[Buch]{tl}", "de")
        self.assertEqual([("mark", "Buch", 0), ("mark", "Buch", 1)], page(md).blocks)
        self.assertEachBlockIsItself(md)
        self.assertEqual(["[Neu]{tl}"],
                         changed(md, store.tl_edit_markdown(md, "mark", "Buch", 0, ["Neu"])))

    def test_a_piece_of_a_sentence_with_blanks_is_a_block(self):
        md = doc(":::exercise fill-blanks\ntext: [من [[a]] را خواندم]{tl}\n- [a] کتاب\n:::\n\n"
                 "Then [را خواندم]{tl}.")
        self.assertEachBlockIsItself(md)
        new = store.tl_edit_markdown(md, "mark", "را خواندم", 0, ["را دیدم"])
        self.assertEqual(["text: [من]{tl} [[a]] [را دیدم]{tl}"], changed(md, new))

    def test_blocks_of_an_exercise_are_numbered_in_the_order_they_are_written(self):
        md = doc(":::exercise match-translations\nexplanation-correct: It is [کتاب!]{tl} here.\n"
                 "- [دفتر!]{tl} => [کتاب!]{tl}\n- [کتاب!]{tl} => book\n:::\n\n"
                 ":::exercise flashcard\ncard-type: vocab\ndirection: reverse\n"
                 "target: [کتاب!]{tl}\nmeaning: [کتاب!]{tl} again\n:::\n\nAfter: [کتاب!]{tl}")
        for preview in (False, True):
            self.assertEachBlockIsItself(md, preview)

    def test_notes_headwords_struck_forms_and_undrawn_rows_hold_no_block(self):
        md = doc("## [دفتر]{fa} | daftar | Greek\n\nA note^[with [دفتر]{tl} in\nit] and "
                 "✗[دفتر]{tl} struck, then [دفتر]{tl}.\n\n"
                 ":::exercise single-choice\nprompt: Broken\n- [دفتر]{tl}\n:::\n\nAnd [دفتر]{tl}.")
        self.assertEqual([("mark", "دفتر", 0), ("mark", "دفتر", 1)], page(md).blocks)
        self.assertEachBlockIsItself(md)

    def test_a_list_items_line_of_script_is_no_block(self):
        md = doc("- an item\n  سلام دنیا!\n\nسلام دنیا!")
        self.assertEqual([("auto", "سلام دنیا!", 0)], page(md).blocks)
        new = store.tl_edit_markdown(md, "auto", "سلام دنیا!", 0, ["درود"])
        self.assertEqual(["درود"], changed(md, new))

    def test_a_latin_block_in_a_list_item_is_no_block(self):
        md = doc("- an item\n  [A Latin block]{la}\n\n[A Latin block]{la}")
        new = store.la_layout_markdown(md, "A Latin block", 0, 50, 0, "center", None)
        self.assertEqual(["[A Latin block]{la align=center width=50}"], changed(md, new))


if __name__ == "__main__":
    unittest.main()
