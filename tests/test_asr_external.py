# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline copy/paste contracts. No endpoint, recognizer or code execution.

Added for the next check run; the current user request defers the rehearsal
and does not run test suites.
"""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "lib"), str(ROOT / "youtube/lib")]
import asrcorrection as correction
import asrexternal
import asrworkspace
import llmconfig
import sttjobs
import sttpanel


def source(*texts, language="it"):
    segments = []
    for i, text in enumerate(texts or ("Loro anno detto ciao.",)):
        words = [{"text": word, "start": i * 5 + j * .3, "end": i * 5 + j * .3 + .2,
                  "score": .2 if word == "anno" else .9,
                  "asr_alternatives": [{"text": "hanno", "score": None, "sequence_score": -2.5,
                      "score_kind": "sequence_log_score"}] if word == "anno" else [],
                  "alternatives_available": word == "anno"}
                 for j, word in enumerate(text.split())]
        segments.append({"start": i * 5, "end": i * 5 + 4, "text": text, "asr_words": words})
    panel, _ = sttpanel.segments_to_panel(segments)
    return panel, correction.evidence(segments, panel, language)


class ExternalAnswers(unittest.TestCase):
    def test_three_prompt_contracts_keep_evidence_and_threshold(self):
        _, request = source()
        original = copy.deepcopy(request)
        for task in asrexternal.TASKS:
            with self.subTest(task=task):
                units = asrexternal.batches(request, task)[0]
                text = asrexternal.prompt(request, task, units)
                self.assertIn("Language: Italian (it).", text)
                self.assertIn("hanno", text)
                self.assertIn("sequence", text)
                self.assertIn("Never translate", text)
                self.assertNotIn("{{", text)
                self.assertLessEqual(len(text.encode("utf-8")), asrexternal.MAX_PROMPT)
        self.assertEqual(request, original)
        self.assertEqual(correction.LOW_SCORE, .5)

    def test_sentence_answers_offer_local_edits_without_applying_them(self):
        panel, request = source()
        for task in ("suspect", "full"):
            units = asrexternal.batches(request, task)[0]
            result = asrexternal.parse(request, task, units, "```text\nsentence0: Loro hanno detto ciao.\n```")
            self.assertEqual(result["suggestions"][0]["original"], "anno")
            self.assertIsNone(result["suggestions"][0]["candidates"][0]["confidence"])
            unchanged, _ = correction.apply(panel, request, result, {})
            self.assertEqual(unchanged, panel)
            edited, _ = correction.apply(panel, request, result, {"s0w1": 0})
            self.assertIn("Loro hanno detto ciao.", edited)
        empty = asrexternal.parse(request, "suspect", units, "sentence0: Loro anno detto ciao.")
        self.assertEqual(empty["suggestions"], [])

    def test_missing_and_invalid_sentence_do_not_lose_valid_sentences(self):
        _, request = source("Loro anno detto ciao.", "Loro anno detto ciao.")
        units = asrexternal.batches(request, "suspect")[0]
        result = asrexternal.parse(request, "suspect", units, "sentence0: Loro hanno detto ciao.")
        self.assertEqual(len(result["suggestions"]), 1)
        self.assertEqual(result["failed_word_ids"], ["s1w1"])
        invalid = 'sentence0: Loro hanno detto ciao.\nsentence1: {"rewritten": "invalid answer format"}'
        result = asrexternal.parse(request, "suspect", units, invalid)
        self.assertEqual(len(result["suggestions"]), 1)
        self.assertEqual(result["failed_word_ids"], ["s1w1"])
        for answer in ("sentence99: Wrong label.", "sentence0: Loro anno detto ciao.\nsentence0: Duplicate.",
                       "Here are the corrections:\nsentence0: Loro hanno detto ciao.", "", "x" * (asrexternal.MAX_ANSWER + 1), "\ud800"):
            with self.subTest(answer=answer[:40]), self.assertRaises(llmconfig.LLMError):
                asrexternal.parse(request, "suspect", units, answer)

    def test_unicode_and_missing_scores_in_whole_text_review(self):
        _, request = source("او به مدرسه رفت.", language="fa")
        for word in correction.index(request).values():
            word.update(asr_confidence=None, low_asr_score=False)
        units = asrexternal.batches(request, "full")[0]
        result = asrexternal.parse(request, "full", units, "sentence0: او به مدرسه رفت.")
        self.assertEqual(result["suggestions"], [])
        self.assertEqual(len(result["reviewed_word_ids"]), 4)
        self.assertEqual(asrexternal.batches(request, "suspect"), [])

    def test_workspace_csv_is_validated_and_never_executed(self):
        _, request = source()
        units = asrexternal.batches(request, "workspace")[0]
        row = {"word_ids": "s0w1", "original": "anno", "replacement": "hanno", "reason": "Context, optionally supported by Whisper."}
        with mock.patch("asrworkspace.Workspace.python", side_effect=AssertionError("Must never execute pasted code")):
            result = asrexternal.parse(request, "workspace", units, asrworkspace._csv([row], asrworkspace.FIELDS))
        self.assertEqual(result["suggestions"][0]["candidates"][0]["text"], "hanno")
        self.assertEqual(result["failed_word_ids"], [])
        for rows in ([row, row], [dict(row, word_ids="unknown")], [dict(row, original="different")]):
            with self.assertRaises(llmconfig.LLMError):
                asrexternal.parse(request, "workspace", units, asrworkspace._csv(rows, asrworkspace.FIELDS))
        missing = asrexternal.parse(request, "workspace", units, "word_ids,original,replacement,reason\n")
        self.assertEqual(missing["failed_word_ids"], ["s0w1"])

    def test_workspace_zip_is_text_only_with_fixed_names(self):
        _, request = source()
        units = asrexternal.batches(request, "workspace")[0]
        with zipfile.ZipFile(io.BytesIO(asrexternal.bundle(request, units, asrexternal.prompt(request, "workspace", units)))) as archive:
            self.assertIn("parseh-review/PROMPT.txt", archive.namelist())
            self.assertIn("parseh-review/review.py", archive.namelist())
            self.assertTrue(all(name.startswith("parseh-review/") and ".." not in name for name in archive.namelist()))
            text = "\n".join(archive.read(name).decode("utf-8") for name in archive.namelist())
            self.assertIn("Loro [1] detto ciao.", text)
            self.assertNotIn("0:00", text)
            self.assertNotIn("/private/", text)
            self.assertNotIn("api_key", text)

    def test_hint_heavy_batches_cover_source_words_once(self):
        _, request = source(" ".join("anno" for _ in range(48)))
        for word in correction.index(request).values():
            word["asr_alternatives"] = [{"text": "a" * 400, "score": None} for _ in range(10)]
        batches = asrexternal.batches(request, "suspect")
        all_ids = [ident for batch in batches for ident in asrexternal.ids(batch)]
        self.assertEqual(len(all_ids), 48)
        self.assertEqual(len(set(all_ids)), 48)
        for batch in batches:
            self.assertLessEqual(len(asrexternal.prompt(request, "suspect", batch).encode("utf-8")), asrexternal.MAX_PROMPT)


class ExternalJobs(unittest.TestCase):
    def setUp(self):
        private = tempfile.TemporaryDirectory()
        self.addCleanup(private.cleanup)
        videos = mock.patch('ytpages.VIDEOS', private.name)
        videos.start(); self.addCleanup(videos.stop)
        self.panel, self.request = source(*("Loro anno detto ciao." for _ in range(13)))
        self.token = "ABCDEFGHIJKLMNOP"
        self.job = {"id": self.token, "kind": "film", "source": {"kind": "film", "path": "/private/film.mp4"},
                    "lang": "it", "model": "large-v3-turbo", "state": sttjobs.REVIEW_CHOICE,
                    "review_evidence": self.request, "review_choice": None, "correction": {},
                    "text": self.panel, "facts": {}, "cancelled": False, "finished": time.time(),
                    "device": "cpu", "fell_back": False, "words": None, "notes": [], "warning": ""}
        for patch in (mock.patch.dict(sttjobs.JOBS, {self.token: self.job}, clear=True),
                      mock.patch("wavefile.held", return_value=False), mock.patch("wordtimes.load", return_value=None),
                      mock.patch("llmadapter.adapter", side_effect=AssertionError("No endpoint request")),
                      mock.patch("llmconfig.load", return_value=None)):
            patch.start(); self.addCleanup(patch.stop)
        self.hash = self.request["source_sha256"]

    def test_import_and_finish_leave_source_intact_until_explicit_use(self):
        view = sttjobs.external_start(self.token, self.hash, "suspect")
        ext = view["review"]["external"]
        self.assertEqual(ext["batches"], 2)
        self.assertNotIn(self.job["state"], sttjobs.ACTIVE)
        with self.assertRaises(sttjobs.Refusal):
            sttjobs.use_review(self.token, self.hash, {})
        view = sttjobs.external_action(self.token, self.hash, ext["id"], "answer", 0, "sentence0: Loro hanno detto ciao.")
        self.assertEqual(self.job["text"], self.panel)
        self.assertEqual(len(view["review"]["result"]["suggestions"]), 1)
        with self.assertRaises(sttjobs.Refusal):
            sttjobs.external_action(self.token, self.hash, ext["id"], "answer", 1, "An explanation instead of the answer")
        self.assertEqual(len(self.job["correction_result"]["suggestions"]), 1)
        view = sttjobs.external_action(self.token, self.hash, ext["id"], "finish")
        self.assertIn("s12w1", view["review"]["result"]["failed_word_ids"])
        used = sttjobs.use_review(self.token, self.hash, {"s0w1": 0})
        self.assertIn("Loro hanno detto ciao.", used["text"])
        self.assertEqual(self.job["text"], self.panel)
        retry = sttjobs.external_start(self.token, self.hash, "suspect", ["s12w1"])
        self.assertEqual(len(retry["review"]["result"]["suggestions"]), 1)

    def test_three_methods_work_without_config_and_bad_prepare_is_atomic(self):
        for task in asrexternal.TASKS:
            view = sttjobs.external_start(self.token, self.hash, task)
            self.assertIn("asr-" + task, view["review"]["external"]["prompt"])
        original = copy.deepcopy(self.job)
        with mock.patch("asrexternal.prompt", side_effect=llmconfig.LLMError("too-large", "Oversized prompt.")):
            with self.assertRaises(sttjobs.Refusal):
                sttjobs.external_start(self.token, self.hash, "full")
        self.assertEqual(self.job["correction_result"], original["correction_result"])
        self.assertEqual(self.job["external_review"]["id"], original["external_review"]["id"])

    def test_stale_session_source_and_cancel_preserve_whisper(self):
        ext = sttjobs.external_start(self.token, self.hash, "workspace")["review"]["external"]
        for session, hash_value in ((None, self.hash), ("replaced", self.hash), (ext["id"], "changed")):
            with self.assertRaises(sttjobs.Refusal):
                sttjobs.external_action(self.token, hash_value, session, "finish")
        with mock.patch("sttjobs._review_source_current", return_value=False), self.assertRaises(sttjobs.Refusal):
            sttjobs.external_files(self.token, self.hash, ext["id"], 0)
        cancelled = sttjobs.external_action(self.token, self.hash, ext["id"], "cancel")
        self.assertIsNone(cancelled["review"]["external"])
        self.assertEqual(cancelled["text"], self.panel)
        self.assertEqual(self.job["state"], sttjobs.REVIEW_CHOICE)

    def test_open_external_review_refreshes_retention_without_inference(self):
        ext = sttjobs.external_start(self.token, self.hash, "full")["review"]["external"]
        before = self.job["finished"]
        with mock.patch("sttjobs._now", return_value=before + 600):
            sttjobs.external_action(self.token, self.hash, ext["id"], "keep-alive")
        self.assertEqual(self.job["finished"], before + 600)
        self.assertNotIn(self.job["state"], sttjobs.ACTIVE)

    def test_pasted_diagnostics_redact_saved_credentials(self):
        ext = sttjobs.external_start(self.token, self.hash, "workspace")["review"]["external"]
        key = 'private-"key'
        answer = asrworkspace._csv([{"word_ids": "s0w1", "original": "anno", "replacement": "hanno", "reason": key}], asrworkspace.FIELDS)
        with mock.patch("llmconfig.load", return_value={"api_key": key}):
            sttjobs.external_action(self.token, self.hash, ext["id"], "answer", 0, answer)
        self.assertNotIn(key, str(self.job["llm_diagnostics"]))
        self.assertNotIn(key, json.dumps(self.job["llm_diagnostics"], ensure_ascii=False))
        self.assertIn("[redacted credential]", str(self.job["llm_diagnostics"]))


if __name__ == "__main__":
    unittest.main()
