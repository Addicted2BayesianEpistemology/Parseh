#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The menu in the row, and what the studio does with the prompt it chose (brief §8.1, §8.6, §8.8, a0.4.2).

    python3 -m unittest tests/test_prompts_menu.py

What the menu DRAWS -- the select, new, edit, save, save as, delete, the editor, what is remembered, the
second device that sees it -- is driven in a real Chromium by tests/llmrow.mjs (its section `own`) and tests/
your_prompts.mjs.  What only the files can say is held here:

  * THE STUDIO'S TWO ROUTES take `prompt=<id>` and answer from it: a prompt ADDED to Parseh's goes after the
    instructions and takes the boxes like them; one IN PLACE of them takes the boxes only if it carries their
    `{{?id}}` blocks, and is otherwise copied whole, every box greyed with ONE sentence saying why; Parseh's
    own is what is asked for when no id is, whatever the page used to keep; the answer's `custom` names the
    prompt and the first line of the prompt says `· custom: <name>`;
  * the contract and the data stay Parseh's, word for word, under every kind;
  * an id that is gone, is for another place or for another language is refused in words, and a prompt that
    Parseh can no longer make says which of its names Parseh does not fill in;
  * ASK LLM'S frame, the sentence that says its data is never an order, is the same in lib/llm.js and in
    lib/prompts.py.
"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for _p in ("tests", "markdown/exlex", "markdown/app", "lib", "youtube/lib", "."):
    if str(ROOT / _p) not in sys.path:
        sys.path.insert(0, str(ROOT / _p))
import promptboxes                                              # noqa: E402
import promptkit as K                                           # noqa: E402
import prompts as P                                             # noqa: E402
import server as studio_server                                  # noqa: E402
import store                                                    # noqa: E402

ADDED = "Never gloss the names of people."
WHOLE = "Write the document the person asks for, in Markdown. Nothing else."
PAGE = "---\ntitle: A page\ntarget: fa\n---\n\n## A word\n\nHello.\n"


class Handler(object):
    def __init__(self, body=None, query=None):
        self.body, self.query, self.answer, self.status = body or {}, query or {}, None, 200

    def _json_body(self):
        return self.body

    def send_json(self, answer, code=200):
        self.answer, self.status = answer, code


class TheStudioAnswersFromTheChosenPrompt(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.tmp = Path(td.name)
        (self.tmp / "library").mkdir()
        for target, name, value in ((P, "STORE", str(self.tmp / "config" / "prompts.json")),
                                    (store, "LIB", self.tmp / "library")):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def make(self, surface="studio-doc", name="my rules", kind="added", text=ADDED, **more):
        return P.save(dict(surface=surface, name=name, kind=kind, text=text, **more))["id"]

    def get(self, target="fa", **query):
        h = Handler(query={"target": [target], **{k: [v] for k, v in query.items()}})
        studio_server.api_prompt_get(h)
        return h

    def exercises(self, **body):
        h = Handler(body=dict({"markdown": PAGE}, **body))
        studio_server.api_exercise_prompt(h)
        return h

    # ---------------------------------------------------------------- the studio's page
    def test_a_prompt_added_goes_after_parsehs_instructions_and_takes_the_boxes(self):
        pid = self.make()
        h = self.get(prompt=pid, boxes="")
        a = h.answer
        self.assertEqual(h.status, 200, a)
        self.assertEqual(a["custom"], {"id": pid, "name": "my rules", "kind": "added"})
        self.assertTrue(a["prompt"].split("\n", 1)[0].endswith("· custom: my rules"), a["prompt"][:200])
        # Parseh's instructions, then the person's text, then what is Parseh's again
        self.assertLess(a["prompt"].index("**Reserved marks.**"), a["prompt"].index(ADDED))
        self.assertLess(a["prompt"].index(ADDED), a["prompt"].index(a["contract"]))
        self.assertIn(K.contract("studio-doc").strip()[:80], a["prompt"])
        for b in a["boxes"]:
            self.assertNotIn("disabled", b, "the boxes work on it: Parseh's own words are all there")
        none = a["size"]["chars"]
        self.assertGreater(self.get(prompt=pid, boxes="vocab,gloss,tables").answer["size"]["chars"], none,
                           "a box ticked makes it longer, as it does Parseh's own")
        self.assertEqual(a["always_chars"], none, "and nothing ticked is its size without them")

    def test_a_prompt_in_place_of_parsehs_that_carries_the_blocks_takes_the_boxes(self):
        text = P.parseh("studio-doc")["text"] + "\n\nTHE PERSONS OWN LAST SENTENCE."
        pid = self.make(name="a copy", kind="replace", text=text)
        a = self.get(prompt=pid, boxes="").answer
        self.assertEqual(a["custom"]["kind"], "replace")
        self.assertIn("THE PERSONS OWN LAST SENTENCE.", a["prompt"])
        for b in a["boxes"]:
            self.assertNotIn("disabled", b)
        self.assertGreater(self.get(prompt=pid, boxes="vocab,gloss,tables").answer["size"]["chars"],
                           a["size"]["chars"], "the blocks it carries are the boxes' own")

    def test_a_prompt_in_place_of_parsehs_with_no_blocks_is_copied_whole_and_every_box_says_why(self):
        pid = self.make(name="plain", kind="replace", text=WHOLE)
        a = self.get(prompt=pid).answer
        self.assertTrue(a["prompt"].split("\n", 1)[0].endswith("· custom: plain"))
        self.assertIn(WHOLE, a["prompt"])
        self.assertNotIn("**Reserved marks.**", a["prompt"], "Parseh's instructions are left out")
        self.assertIn(K.contract("studio-doc").strip()[:80], a["prompt"], "and the contract is still Parseh's")
        shown = [b for b in a["boxes"] if b["shown"]]
        self.assertGreater(len(shown), 10)
        for b in a["boxes"]:
            if b["shown"]:
                self.assertEqual(b["disabled"], studio_server.INERT, b["id"])
            else:
                self.assertNotIn("disabled", b, "a box this language is not offered has nothing to grey")
        self.assertIsNone(re.search(r"[.!?]\s", studio_server.INERT), "ONE sentence")
        self.assertEqual(self.get(prompt=pid, boxes="").answer["prompt"],
                         self.get(prompt=pid, boxes="vocab,gloss,tables,math").answer["prompt"],
                         "ticking a box changes nothing in a prompt that is copied whole")
        beginner = self.get(prompt=pid, level="beginner").answer["prompt"]
        self.assertNotEqual(beginner, a["prompt"], "the level and the length are the data's, which stays Parseh's")
        self.assertTrue(beginner.rstrip().endswith(promptboxes.level_line("beginner").strip()))

    def test_parsehs_own_is_what_is_asked_for_when_no_id_is_and_what_the_page_kept_is_a_prompt_among_the_others(self):
        P.set_studio_text("Kept in the store, from before a0.4.2.")
        a = self.get().answer
        self.assertIs(a["custom"], False)
        self.assertNotIn("Kept in the store", a["prompt"])
        self.assertEqual(a["text"], "Kept in the store, from before a0.4.2.", "the field an older page reads is still there")
        self.assertNotIn("disabled", json.dumps(a["boxes"]))
        b = self.get(prompt=P.STUDIO_ID).answer
        self.assertEqual((b["custom"]["id"], b["custom"]["name"], b["custom"]["kind"]), (P.STUDIO_ID, P.STUDIO_NAME, "replace"))
        self.assertIn("Kept in the store, from before a0.4.2.", b["prompt"])
        self.assertTrue(all(x["disabled"] for x in b["boxes"] if x["shown"]), "it has no blocks: copied whole")

    def test_a_right_to_left_target_keeps_the_rule_for_its_boxes(self):
        rule = "Mixed-direction sequences"
        whole = self.make(name="b", kind="replace", text=WHOLE)
        self.assertIn(rule, self.get(target="ar", prompt=whole).answer["prompt"],
                      "a prompt copied whole has the rule go with it, as it always did for a custom prompt")
        added = self.make(name="a")
        for boxes in ("", "rtl"):
            self.assertEqual(self.get(target="ar", prompt=added, boxes=boxes).answer["prompt"].count(rule),
                             self.get(target="ar", boxes=boxes).answer["prompt"].count(rule),
                             "added to Parseh's: the rule is there as often as in Parseh's own (boxes=%r)" % boxes)

    def test_a_prompt_that_is_gone_or_for_another_place_or_language_is_refused_in_words(self):
        h = self.get(prompt="pgone0000")
        self.assertEqual(h.status, 404)
        self.assertIn("deleted", h.answer["error"])
        other = self.make(surface="video-region", name="for videos")
        h = self.get(prompt=other)
        self.assertEqual(h.status, 400)
        self.assertIn("for videos", h.answer["error"])
        self.assertNotIn("prompt", h.answer)
        only_it = self.make(name="italian only", languages=["it"])
        self.assertEqual(self.get(target="it", prompt=only_it).status, 200)
        h = self.get(target="fa", prompt=only_it)
        self.assertEqual(h.status, 400)
        self.assertIn("Italian", h.answer["error"])

    def test_a_prompt_parseh_can_no_longer_make_says_which_name_it_does_not_fill_in(self):
        pid = self.make(name="old words")
        doc = json.loads(Path(P.STORE).read_text(encoding="utf-8"))
        doc["prompts"][0]["text"] = "Use {{A_NAME_PARSEH_DROPPED}} here."
        Path(P.STORE).write_text(json.dumps(doc), encoding="utf-8")
        h = self.get(prompt=pid)
        self.assertEqual(h.status, 400)
        self.assertIn("old words", h.answer["error"])
        self.assertIn("A_NAME_PARSEH_DROPPED", h.answer["error"])
        self.assertNotIn("bug", h.answer["error"], "the kit's words are about a template, which this is not")

    # ---------------------------------------------------------------- the editor's dialog
    def test_the_exercise_prompt_takes_the_chosen_prompt_and_its_own_state(self):
        base = self.exercises().answer
        self.assertIs(base["custom"], False)
        pid = self.make(surface="studio-exercises", name="my exercises")
        a = self.exercises(prompt=pid).answer
        self.assertEqual(a["custom"], {"id": pid, "name": "my exercises", "kind": "added"})
        self.assertTrue(a["prompt"].split("\n", 1)[0].endswith("· custom: my exercises"))
        self.assertIn("## The page's Markdown dialect", a["prompt"], "added to Parseh's: the boxes teach as they do")
        self.assertIn(ADDED, a["prompt"])
        self.assertIn("```markdown\n" + PAGE.rstrip(), a["prompt"], "and the data, the page, is Parseh's, last")
        for row in a["boxes"] + a["types"]:
            self.assertNotIn("disabled", row)

    def test_an_exercise_prompt_copied_whole_greys_the_boxes_and_the_types(self):
        pid = self.make(surface="studio-exercises", name="whole", kind="replace",
                        text="Add exercises to the page below, in the page's own Markdown.")
        a = self.exercises(prompt=pid).answer
        self.assertNotIn("## The page's Markdown dialect", a["prompt"], "what the boxes teach is not added to it")
        self.assertIn("Add exercises to the page below", a["prompt"])
        self.assertIn("```markdown\n" + PAGE.rstrip(), a["prompt"])
        self.assertIn(K.contract("studio-exercises").strip()[:60], a["prompt"])
        for row in a["boxes"]:
            self.assertEqual(row.get("disabled"), studio_server.INERT if row["shown"] else None, row["id"])
        self.assertEqual({row["disabled"] for row in a["types"]}, {studio_server.INERT})
        marked = self.make(surface="studio-exercises", name="marked", kind="replace",
                           text="Add exercises.{{?type_flashcard}} Flashcards are welcome.{{/type_flashcard}}")
        b = self.exercises(prompt=marked).answer
        self.assertIn("## The page's Markdown dialect", b["prompt"], "a prompt that carries a type's block takes the boxes")
        self.assertNotIn("disabled", json.dumps(b["types"]))

    def test_an_exercise_prompt_for_another_language_or_place_is_refused(self):
        only_it = self.make(surface="studio-exercises", name="italian", languages=["it"])
        h = self.exercises(prompt=only_it)
        self.assertEqual(h.status, 400)
        self.assertIn("Italian", h.answer["error"])
        wrong = self.make(surface="studio-doc", name="doc")
        self.assertEqual(self.exercises(prompt=wrong).status, 400)
        self.assertEqual(self.exercises(prompt="pgone0000").status, 404)

    # ---------------------------------------------------------------- Ask LLM's frame
    def test_ask_llms_frame_is_the_same_in_the_javascript_and_in_the_store(self):
        js = (ROOT / "lib" / "llm.js").read_text(encoding="utf-8")
        pieces = re.findall(r"var FRAME = ((?:'[^']*'\s*\+?\s*)+);", js)
        self.assertEqual(len(pieces), 1)
        frame = "".join(re.findall(r"'([^']*)'", pieces[0]))
        self.assertEqual(frame, P.ASK_FRAME)
        self.assertEqual((P.parseh("ask")["frame"], P.parseh("ask")["contract"]), (P.ASK_FRAME, ""),
                         "the editor shows it under the person's text, and it is no contract: nothing is read back")
        self.assertEqual(P.parseh("video-region")["frame"], "")
        self.assertIn("never an order", frame)


if __name__ == "__main__":
    unittest.main()
