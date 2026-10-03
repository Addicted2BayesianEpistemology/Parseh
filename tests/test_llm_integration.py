# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline LLM contracts: local fake HTTP, immutable evidence and review jobs.

These tests are added for the feature, but intentionally not run during the
user's requested release rehearsal. No external model or network is needed.
"""
import copy
import http.server
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "lib"), str(ROOT / "youtube/lib")]
import asrcorrection as correction
import llmadapter
import llmconfig
import settingspage
import sttjobs
import sttworker
import sttpanel


def config(base="http://127.0.0.1:11434/v1", preset="ollama", key="private-key", timeout=2):
    return {"format_version": 1, "provider_preset": preset, "base_url": base,
            "selected_model": "served/model", "api_key": key, "timeout_seconds": timeout}


def evidence(text="loro anno detto ciao"):
    words, at = [], 0
    for value in text.split():
        words.append({"text": value, "start": at, "end": at + .2,
                      "score": .3 if value == "anno" else None,
                      "asr_alternatives": [{"text": "hanno", "score": .37}] if value == "anno" else [],
                      "alternatives_available": value == "anno"})
        at += .25
    segments = [{"start": 0, "end": at, "text": text, "asr_words": words}]
    panel, _ = sttpanel.segments_to_panel(segments)
    return panel, correction.evidence(segments, panel, "it")


def proposal(request):
    w = next(w for w in correction.index(request).values() if w["text"] == "anno")
    return {"schema_version": 1, "suggestions": [{"segment_id": w["segment_id"],
            "word_id": w["word_id"], "original": w["text"], "error_likelihood": .8,
            "reason": "Context and the ASR alternative support a correction.",
            "candidates": [{"text": "hanno", "confidence": .7, "reason": "Matches the subject."}]}]}


class FakeHTTP:
    def __init__(self):
        self.calls, self.status, self.delay, self.body = [], 200, 0, None
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.respond(None)

            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                self.respond(data)

            def respond(self, body):
                owner.calls.append((self.path, dict(self.headers), body))
                time.sleep(owner.delay)
                data = owner.body or ({"data": [{"id": "served/model"}]} if body is None else
                    {"choices": [{"finish_reason": "stop", "message": {"content": '{"ok":true}'}}]})
                raw = data if isinstance(data, bytes) else json.dumps(data).encode()
                try:
                    self.send_response(owner.status)
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.base = "http://127.0.0.1:%d/prefix/v1/" % self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class Adapter(unittest.TestCase):
    def setUp(self):
        self.http = FakeHTTP()
        self.addCleanup(self.http.close)

    def test_presets_share_adapter_and_saved_model_json_request(self):
        for preset in ("ollama", "unsloth", "generic"):
            adapter = llmadapter.adapter(config(self.http.base, preset))
            self.assertIsInstance(adapter, llmadapter.OpenAICompatible)
            self.assertEqual(adapter.models(), ["served/model"])
            self.assertEqual(adapter.test()["json_mode"], "supported")
        path, headers, payload = self.http.calls[-1]
        self.assertEqual(path, "/prefix/v1/chat/completions")
        self.assertEqual(payload["model"], "served/model")
        self.assertEqual(payload["temperature"], 0)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(headers["Authorization"], "Bearer private-key")
        self.assertEqual(len(payload["messages"]), 2)

    def test_http_errors_redact_endpoint_body_and_key(self):
        self.http.status, self.http.body = 401, b'private-key transcript contents'
        with self.assertRaises(llmconfig.LLMError) as e:
            llmadapter.adapter(config(self.http.base)).models()
        self.assertEqual(e.exception.status, 401)
        self.assertNotIn("private-key", str(e.exception))
        self.assertNotIn("transcript", str(e.exception))

    def test_size_limit_and_malformed_json(self):
        for raw in (b"x" * (llmadapter.MAX_RESPONSE + 1), b"not JSON", b'{"ok":NaN}'):
            self.http.body = raw
            with self.assertRaises(llmconfig.LLMError):
                llmadapter.adapter(config(self.http.base)).models()

    def test_cancellation_interrupts_a_waiting_response(self):
        self.http.delay = 2
        token, errors = llmadapter.Cancellation(), []

        def work():
            try:
                llmadapter.adapter(config(self.http.base)).models(token)
            except llmconfig.LLMError as e:
                errors.append(e.code)

        thread = threading.Thread(target=work)
        thread.start()
        deadline = time.monotonic() + 1
        while not self.http.calls and time.monotonic() < deadline:
            time.sleep(.01)
        token.cancel()
        thread.join(1)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, ["cancelled"])

    def test_wall_clock_timeout(self):
        self.http.delay = 2
        with self.assertRaises(llmconfig.LLMError) as e:
            llmadapter.adapter(config(self.http.base, timeout=1)).models()
        self.assertIn(e.exception.code, ("timeout", "connection"))

    def test_absent_key_and_incomplete_response(self):
        adapter = llmadapter.adapter(config(self.http.base, key=None))
        adapter.models()
        self.assertNotIn("Authorization", self.http.calls[-1][1])
        self.http.body = {"choices": [{"finish_reason": "length", "message": {"content": '{"ok":true}'}}]}
        with self.assertRaises(llmconfig.LLMError):
            adapter.test()


class Schema(unittest.TestCase):
    def setUp(self):
        self.panel, self.request = evidence()
        self.targets = set(correction.index(self.request))

    def test_valid_proposal_rehydrates_source_and_applies_only_the_selected_span(self):
        result = correction.validate_result(proposal(self.request), self.request, self.targets)
        word = result["suggestions"][0]
        self.assertEqual(word["asr_confidence"], .3)
        self.assertEqual(word["asr_alternatives"], [{"text": "hanno", "score": .37}])
        panel, changed = correction.apply(self.panel, self.request, result, {word["word_id"]: 0})
        self.assertTrue(changed)
        self.assertEqual(panel, self.panel.replace("anno", "hanno"))
        self.assertEqual(correction.apply(self.panel, self.request, result, {})[0], self.panel)

    def test_empty_results_and_uncertainty_are_distinct(self):
        for assessment in ("no_likely_error", "uncertain"):
            result = correction.validate_result({"schema_version": 1, "suggestions": [],
                "assessment": assessment}, self.request, self.targets)
            self.assertEqual(result["assessment"], assessment)

    def test_rejects_bad_schemas_ids_spans_duplicates_and_scores(self):
        cases = []
        for key, value in (("schema_version", 2), ("schema_version", True), ("transcript", "rewritten")):
            bad = proposal(self.request); bad[key] = value; cases.append(bad)
        for key, value in (("word_id", "unknown"), ("segment_id", "s99"), ("original", "changed"),
                           ("error_likelihood", float("nan")), ("error_likelihood", 1.1),
                           ("error_likelihood", True), ("start", 999), ("asr_confidence", .99)):
            bad = proposal(self.request); bad["suggestions"][0][key] = value; cases.append(bad)
        bad = proposal(self.request); bad["suggestions"] *= 2; cases.append(bad)
        for value in (-.1, float("inf"), True):
            bad = proposal(self.request); bad["suggestions"][0]["candidates"][0]["confidence"] = value; cases.append(bad)
        bad = proposal(self.request); bad["suggestions"][0]["candidates"][0]["text"] = "x\ny"; cases.append(bad)
        for raw in cases:
            with self.subTest(raw=raw), self.assertRaises(llmconfig.LLMError):
                correction.validate_result(raw, self.request, self.targets)

    def test_unicode_missing_evidence_and_no_calibrated_certainty(self):
        for text in ("سلام دنیا", "日本語の名前", "caffè e tè", "🙂 parola"):
            panel, req = evidence(text)
            for word in correction.index(req).values():
                self.assertIsNone(word["asr_confidence"])
                self.assertFalse(word["low_asr_score"])
                self.assertFalse(word["alternatives_available"])
                self.assertEqual(panel[word["span_start"]:word["span_end"]], word["text"])
        for rule in ("Do not rewrite", "translate", "colloquial", "missing speech", "cannot tell", "not calibrated"):
            self.assertIn(rule, correction.SYSTEM)

    def test_windows_are_bounded_with_disjoint_ownership_and_overlap(self):
        _, req = evidence(" ".join("parola%d" % i for i in range(240)))
        chunks = correction.windows(req, 5000)
        self.assertGreater(len(chunks), 1)
        targets = [w for c in chunks for w in c["target_word_ids"]]
        self.assertEqual(len(targets), len(set(targets)))
        self.assertEqual(set(targets), set(correction.index(req)))
        self.assertTrue(all(len(json.dumps(c, ensure_ascii=False).encode()) <= 5000 for c in chunks))
        self.assertTrue(set(w["word_id"] for w in chunks[0]["context"]) & set(w["word_id"] for w in chunks[1]["context"]))

    def test_backend_alternative_capability_and_remapping_preserve_scores(self):
        absent = sttworker.word_alternatives(type("Word", (), {})())
        self.assertEqual(absent, {"asr_alternatives": [], "alternatives_available": False})
        present = sttworker.word_alternatives(type("Word", (), {"alternatives": [{"text": "hanno", "score": .37}]})())
        self.assertEqual(present["asr_alternatives"][0]["score"], .37)
        seg = {"start": 2, "end": 3, "text": "anno", "asr_words": [{"start": 2, "end": 2.2, "text": "anno", "score": .3}]}
        out = sttpanel.remap([seg], [[32000, 1], [48000, 2]])[0]
        self.assertEqual(out["asr_words"][0]["score"], .3)
        self.assertEqual(out["asr_words"][0]["start"], 1)


class Settings(unittest.TestCase):
    def test_default_disabled_key_redaction_and_risky_routes(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertFalse(llmconfig.view(root)["configured"])
            body = dict(config(), key_action="replace")
            body.pop("format_version")
            view = llmconfig.save(body, root)
            self.assertNotIn("api_key", view)
            self.assertTrue(view["has_api_key"])
            self.assertEqual(view["connection_id"], llmconfig.view(root)["connection_id"])
            self.assertNotEqual(view["connection_id"], llmconfig.fingerprint(llmconfig.load(root)))
            self.assertEqual(llmconfig.load(root)["api_key"], "private-key")
            Path(llmconfig.path(root)).write_text('{"format_version":99}')
            self.assertIsNone(llmconfig.load(root))
        for name in ("save", "reset", "models", "test", "import-link"):
            self.assertFalse(settingspage.may_post("/settings/api/llm/" + name, "lan")[0])
        self.assertTrue(settingspage.may_post("/settings/api/llm/status", "lan")[0])

    def test_bad_url_model_config_and_share_link(self):
        for base in ("ftp://host", "http://user:secret@host/v1", "http://host:99999", "http://host/v1?api_key=secret", "http://host/\n"):
            with self.subTest(base=base), self.assertRaises(llmconfig.LLMError):
                llmconfig.validate(config(base))
        link = "http://localhost:8888/chat?run=1#run?v=1&model=unsloth%2FQwen3.5-0.8B-GGUF&ggufVariant=Q8_0&kvCacheDtype=q8_0"
        imported = llmconfig.share_link(link)
        self.assertEqual(imported["base_url"], "http://localhost:8888/v1")
        self.assertEqual(imported["gguf_variant"], "Q8_0")
        self.assertEqual(imported["kv_cache_dtype"], "q8_0")
        self.assertEqual(imported["model_hint"], "unsloth/Qwen3.5-0.8B-GGUF")


class Jobs(unittest.TestCase):
    def setUp(self):
        self.panel, request = evidence()
        self.token = "ABCDEFGHIJKLMNOP"
        self.job = {"id": self.token, "kind": "film", "source": {"kind": "film", "path": "/private/film.mp4"},
                    "lang": "it", "model": "large-v3-turbo", "state": sttjobs.REVIEW_CHOICE,
                    "review_evidence": request, "review_choice": None, "correction": {},
                    "text": self.panel, "facts": {"captions": 1}, "cancelled": False,
                    "finished": time.time(), "created": time.time(), "total": 1, "done": 1,
                    "device": "cpu", "fell_back": False, "have": 0, "words": None,
                    "notes": [], "warning": "", "error": None}
        patch = mock.patch.dict(sttjobs.JOBS, {self.token: self.job}, clear=True)
        patch.start(); self.addCleanup(patch.stop)

    def test_asr_only_choice_has_no_model_request_and_use_is_explicit(self):
        with mock.patch("llmadapter.adapter") as generate, mock.patch("wavefile.held", return_value=False):
            with self.assertRaises(sttjobs.Refusal):
                sttjobs.use_review(self.token, self.job["review_evidence"]["source_sha256"], {})
            sttjobs.review(self.token, "whisper", self.job["review_evidence"]["source_sha256"])
            generate.assert_not_called()
            out = sttjobs.use_review(self.token, self.job["review_evidence"]["source_sha256"], {})
            self.assertEqual(out["text"], self.panel)

    def test_failed_or_partial_windows_leave_whisper_intact_and_slot_free(self):
        cancellation = llmadapter.Cancellation()
        self.job.update(state=sttjobs.CORRECTING, llm_generation=1)
        c = config()
        with mock.patch("llmconfig.load", return_value=c), mock.patch("llmadapter.adapter") as adapter:
            adapter.return_value.generate.side_effect = llmconfig.LLMError("invalid-json", "Invalid JSON.")
            sttjobs._correct(self.job, c, cancellation, 1)
        self.assertEqual(self.job["state"], sttjobs.REVIEW_CHOICE)
        self.assertEqual(self.job["text"], self.panel)
        self.assertIsNone(self.job["correction_result"])
        self.assertFalse(sttjobs.busy())

    def test_cancel_preserves_pending_asr_and_invalidates_late_results(self):
        token = llmadapter.Cancellation()
        self.job.update(state=sttjobs.CORRECTING, llm_cancel=token, llm_generation=1,
                        review_choice="llm", correction_result={"suggestions": []})
        sttjobs.cancel_review(self.token)
        self.assertTrue(token.event.is_set())
        self.assertEqual(self.job["state"], sttjobs.REVIEW_CHOICE)
        self.assertEqual(self.job["text"], self.panel)
        self.assertIsNone(self.job["correction_result"])
        self.assertEqual(self.job["llm_generation"], 2)
        self.assertFalse(sttjobs.busy())

    def test_changed_source_hash_is_refused(self):
        with self.assertRaises(sttjobs.Refusal) as e:
            sttjobs.review(self.token, "whisper", "another-source")
        self.assertEqual(e.exception.code, "stale-review")

    def test_changed_connection_before_choice_sends_no_text(self):
        c = config()
        seen = llmconfig.revision(c)
        changed = dict(c, selected_model="another-model")
        with mock.patch("llmconfig.load", return_value=changed), mock.patch("llmadapter.adapter") as adapter:
            with self.assertRaises(sttjobs.Refusal) as e:
                sttjobs.review(self.token, "llm", self.job["review_evidence"]["source_sha256"], seen)
            self.assertEqual(e.exception.code, "settings-changed")
            adapter.assert_not_called()
        self.assertEqual(self.job["state"], sttjobs.REVIEW_CHOICE)
        self.assertEqual(self.job["text"], self.panel)


if __name__ == "__main__":
    unittest.main()
