# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline workspace contracts, added but not run in the release rehearsal."""
import copy
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "lib"), str(ROOT / "youtube/lib")]
import asrcorrection
import asrworkspace
import llmadapter
import llmconfig


def evidence():
    text = "Thay anno detto ciao."
    words = [{"text": t, "start": i, "end": i + .5, "score": .2 if t == "anno" else .9}
             for i, t in enumerate(text.split())]
    return text, asrcorrection.evidence([{"text": text, "start": 0, "end": 4, "words": words}], text, "it")


def config():
    return {"format_version": 1, "provider_preset": "unsloth", "adapter": "unsloth-studio",
            "base_url": "http://localhost:8888/v1", "selected_model": "coder",
            "api_key": "dummy-private-key", "timeout_seconds": 60}


class WorkspaceContracts(unittest.TestCase):
    def test_blanks_keep_threshold_scores_and_missing_alternatives(self):
        _, request = evidence()
        original = copy.deepcopy(request)
        transcript, rows, words, captions, slots = asrworkspace._files(request)
        self.assertIn("Thay [1] detto ciao.", transcript)
        self.assertNotIn("0:00", transcript)
        self.assertEqual(rows[0]["whisper_score"], .2)
        self.assertIn("alternatives unavailable", rows[0]["whisper_hints"])
        self.assertEqual(slots, {"s0w1": "1"})
        self.assertEqual(request, original)
        self.assertEqual(asrcorrection.LOW_SCORE, .5)
        request["segments"][0]["words"][0].update(dictionary_miss=True, asr_confidence=None)
        _, rows, _, _, _ = asrworkspace._files(request)
        self.assertEqual(rows[0]["whisper_score"], "unavailable")
        self.assertTrue(rows[0]["dictionary_miss"])

    def test_unicode_spans_and_unavailable_scores_remain_explicit(self):
        text = "彼は 学校に 行く。"
        segment = {"text": text, "start": 0, "end": 3, "words": [
            {"text": "彼は", "score": None}, {"text": "学校に", "score": .4}, {"text": "行く。", "score": .9}]}
        request = asrcorrection.evidence([segment], text, "ja")
        transcript, rows, _, _, _ = asrworkspace._files(request)
        self.assertIn("彼は [1] 行く。", transcript)
        self.assertEqual(rows[0]["guess"], "学校に")
        self.assertIsNone(request["segments"][0]["words"][0]["asr_confidence"])

    def test_external_tools_request_reasoning_without_endpoint_host_tools(self):
        client = llmadapter.UnslothStudio(config())
        call = {"id": "call_1", "type": "function", "function": {"name": "python", "arguments": '{"code":"print(1)"}'}}
        response = {"choices": [{"finish_reason": "tool_calls", "message": {"content": None,
                     "tool_calls": [call], "reasoning_content": "dummy-private-key"}}]}
        traces = []
        with mock.patch.object(client, "request", return_value=response) as request:
            answer = client.agent_turn([{"role": "user", "content": "Synthetic data"}], asrworkspace.TOOLS[1:], observe=traces.append)
        payload = request.call_args.args[1]
        self.assertTrue(payload["enable_thinking"])
        self.assertFalse(payload["enable_tools"])
        self.assertFalse(payload["mcp_enabled"])
        self.assertEqual(payload["temperature"], 0)
        self.assertEqual(answer["tool_calls"], [call])
        self.assertNotIn("dummy-private-key", json.dumps(traces))
        response["choices"][0]["message"]["tool_calls"][0]["function"]["name"] = "terminal"
        with mock.patch.object(client, "request", return_value=response), self.assertRaises(llmconfig.LLMError):
            client.agent_turn([], asrworkspace.TOOLS[1:])

    def test_csv_rejects_unknown_duplicate_and_mismatched_spans(self):
        _, request = evidence()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / "out").mkdir()
            def write(rows):
                (root / "out/result.csv").write_text(asrworkspace._csv(rows, asrworkspace.FIELDS), encoding="utf-8")
            row = {"word_ids": "s0w1", "original": "anno", "replacement": "hanno", "reason": "Fits the sentence."}
            write([row]); proposals, seen = asrworkspace._proposals(root, request, {"s0w1"})
            self.assertEqual(proposals[0]["candidates"][0]["text"], "hanno")
            self.assertIsNone(proposals[0]["error_likelihood"])
            for rows in ([row, row], [dict(row, word_ids="s99w0")], [dict(row, original="other")], [dict(row, replacement="hanno!")]):
                write(rows)
                with self.assertRaises(llmconfig.LLMError):
                    asrworkspace._proposals(root, request, {"s0w1"})

    def test_two_pass_order_failure_salvage_progress_and_cleanup(self):
        text, request = evidence()
        original = copy.deepcopy(request)
        calls, folders, progress = [], [], []
        def phase(workspace, request, adapter, name, allowed, context, diagnostic, key):
            calls.append(name); folders.append(workspace.root)
            self.assertIn("[1]", (workspace.root / "input/transcript.txt").read_text())
            row = {"word_ids": "s0w0", "original": "Thay", "replacement": "They", "reason": "Synthetic fixture"} if name == "skim" else {
                  "word_ids": "s0w1", "original": "anno", "replacement": "hanno", "reason": "Synthetic fixture"}
            (workspace.root / "out/result.csv").write_text(asrworkspace._csv([row], asrworkspace.FIELDS))
            workspace.ran = True
            if name == "resolve":
                raise llmconfig.LLMError("timeout", "Synthetic interrupted phase.")
            return asrworkspace._proposals(workspace.root, request, allowed)
        with mock.patch("asrworkspace.sandbox_status", return_value={"available": True}), mock.patch("asrworkspace._phase", side_effect=phase):
            result = asrworkspace.correct(request, object(), llmadapter.Cancellation(), lambda *p: progress.append(p))
        self.assertEqual(calls, ["skim", "resolve"])
        self.assertEqual(len(result["suggestions"]), 2)
        self.assertEqual(progress[-1][:2], (4, 4))
        self.assertEqual(result["failed_word_ids"], [])
        self.assertTrue(all(not p.exists() for p in folders))
        self.assertEqual(request, original)
        panel, changed = asrcorrection.apply(text, request, result, {"s0w0": 0, "s0w1": 0})
        self.assertEqual(panel, "They hanno detto ciao.")
        self.assertTrue(changed)

    def test_cancellation_cleans_workspace_and_preserves_source(self):
        _, request = evidence()
        folders = []
        cancel = llmadapter.Cancellation()
        def phase(workspace, *args):
            folders.append(workspace.root); cancel.cancel(); cancel.check()
        with mock.patch("asrworkspace.sandbox_status", return_value={"available": True}), mock.patch("asrworkspace._phase", side_effect=phase):
            with self.assertRaises(llmconfig.LLMError) as error:
                asrworkspace.correct(request, object(), cancel, lambda *p: None)
        self.assertEqual(error.exception.code, "cancelled")
        self.assertTrue(all(not p.exists() for p in folders))

    def test_optional_os_sandbox_hides_host_files_and_keeps_inputs_read_only(self):
        if not asrworkspace.sandbox_status()["available"]:
            self.skipTest("Optional OS isolation is unavailable")
        with tempfile.TemporaryDirectory() as outside, tempfile.TemporaryDirectory() as folder:
            secret = Path(outside) / "sentinel"; secret.write_text("not available to the model")
            root = Path(folder); (root / "input").mkdir(); (root / "out").mkdir()
            (root / "input/transcript.txt").write_text("source"); (root / "out/result.csv").touch()
            workspace = asrworkspace.Workspace(root, llmadapter.Cancellation())
            output = workspace.python("from pathlib import Path\nprint(Path(%r).exists())\ntry:\n Path('input/transcript.txt').write_text('modified')\nexcept OSError:\n print('read-only')\nPath('out/result.csv').write_text('allowed')" % str(secret))
            self.assertIn("False", output); self.assertIn("read-only", output)
            self.assertEqual((root / "input/transcript.txt").read_text(), "source")
            self.assertEqual((root / "out/result.csv").read_text(), "allowed")


if __name__ == "__main__":
    unittest.main()
