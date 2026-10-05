# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline application catalogue and package-integrity checks; no models."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import speechmodels


class Catalogue(unittest.TestCase):
    def test_all_requested_sources_are_pinned_and_retain_standard_models(self):
        self.assertEqual(len(speechmodels.MODELS), 15)
        self.assertEqual(speechmodels.MODELS[:2], ("large-v3-turbo", "large-v3"))
        expected = {"vhdm/whisper-large-fa-v1", "nezamisafa/whisper-persian-v4",
                    "oddadmix/whisper-large-v3-turbo-arabic-dialectal-v2",
                    "Corviinuss/whisper-large-v3-turbo-italian-lora", "kotoba-tech/kotoba-whisper-v2.0",
                    "bofenghuang/whisper-large-v3-french-distil-dec4", "primeline/whisper-large-v3-turbo-german",
                    "selimc/whisper-large-v3-turbo-turkish", "distil-whisper/distil-large-v3.5",
                    "Tachyeon/whisper-large-v3-turbo-hindi-lora", "collabora/whisper-medium-hindi",
                    "adriszmar/whisper-large-v3-turbo-es", "BELLE-2/Belle-whisper-large-v3-turbo-zh"}
        self.assertEqual({speechmodels.MODEL_INFO[x]["source"] for x in speechmodels.MODELS[2:]}, expected)
        for model in speechmodels.MODELS:
            self.assertRegex(speechmodels.MODEL_INFO[model]["revision"], r"^[0-9a-f]{40}$")
            self.assertTrue(speechmodels.MODEL_INFO[model]["licence"])
        self.assertEqual(speechmodels.MODEL_PINS["large-v3-turbo"]["revision"],
                         "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf")
        self.assertEqual(speechmodels.MODEL_PINS["large-v3"]["files"]["model.bin"][0],
                         "69f74147e3334731bc3a76048724833325d2ec74642fb52620eda87352e3d4f1")
        self.assertEqual(len(speechmodels.MODEL_PINS["large-v3"]["files"]), 5)

    def test_language_filter_and_decoding_profiles_do_not_change_second_pass(self):
        self.assertEqual(set(speechmodels.choices("fa")),
                         {"large-v3-turbo", "large-v3", "fa-fast", "fa-accuracy"})
        self.assertFalse(speechmodels.compatible("ja-kotoba-v2", "zh"))
        self.assertFalse(speechmodels.compatible([], "fa"))
        self.assertFalse(speechmodels.decoding("en-distil-v3.5")["condition_on_previous_text"])
        for model in speechmodels.MODELS:
            profile = speechmodels.decoding(model, second_pass=True)
            self.assertEqual(profile["beam_size"], 10)
            self.assertEqual(profile["temperature"], 0)
            self.assertEqual(profile["task"], "transcribe")
            self.assertFalse(profile["condition_on_previous_text"])
            self.assertTrue(profile["word_timestamps"])

    def test_download_identity_and_no_unverified_compatibility_claim(self):
        for model in speechmodels.MODELS[2:]:
            row = speechmodels.entry(model)
            self.assertFalse(row["fully_compatible"])
            if row["package"]:
                self.assertEqual(set(("config.json", "model.bin", "tokenizer.json", "preprocessor_config.json", "vocabulary.json")) - row["package"]["files"].keys(), set())
                self.assertEqual(speechmodels.MODEL_INFO[model]["download"],
                                 sum(value["size"] for value in row["package"]["files"].values()))
                for pin in row["package"]["files"].values():
                    self.assertRegex(pin["sha256"], r"^[a-f0-9]{64}$")
            else:
                self.assertFalse(speechmodels.installable(model))
                self.assertIn("verified", row["availability_reason"])
        url = speechmodels.file_url("fr-distil-dec4", "model.bin")
        self.assertIn("/ctranslate2/model.bin", url)
        self.assertIn(speechmodels.MODEL_PINS["fr-distil-dec4"]["revision"], url)
        card = speechmodels.file_url("de-turbo", "SOURCE-MODEL-CARD.md")
        self.assertIn("primeline/whisper-large-v3-turbo-german/resolve/", card)

    def test_kotoba_repair_is_pinned_valid_and_reported(self):
        path = speechmodels.bundled_file("ja-kotoba-v2", "config.json")
        pin = speechmodels.MODEL_PINS["ja-kotoba-v2"]["files"]["config.json"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), pin[0])
        self.assertEqual(path.stat().st_size, pin[1])
        heads = json.loads(path.read_text())["alignment_heads"]
        self.assertEqual(heads, [[1, h] for h in range(20)])
        self.assertIsNone(speechmodels.file_url("ja-kotoba-v2", "config.json"))
        provenance = speechmodels.provenance("ja-kotoba-v2")
        self.assertGreater(max(h[0] for h in provenance["alignment_repair"]["original_heads"]), 1)
        self.assertFalse(provenance["fully_compatible"])

    def test_six_conversions_use_pinned_hub_downloads_and_retain_weight_licences(self):
        for model in ("fa-fast", "fa-accuracy", "ar-dialectal", "it-turbo", "hi-fast", "es-turbo"):
            row = speechmodels.entry(model)
            package = row["package"]
            self.assertNotIn("distribution", package)
            self.assertTrue(package["repo"].startswith("parseh/whisper-"))
            self.assertRegex(package["revision"], r"^[a-f0-9]{40}$")
            self.assertNotEqual(package["revision"], row["revision"])
            for name in ("LICENSE-MIT.txt", "LICENSE-" + row["licence"] + ".txt",
                         "SOURCE-MODEL-CARD.md", "NOTICE.txt", "README.md", "PACKAGE-PROVENANCE.json"):
                self.assertIn(name, package["files"])
                self.assertEqual(speechmodels.file_url(model, name),
                    "https://huggingface.co/" + package["repo"] + "/resolve/" + package["revision"] + "/" + name)

    def test_manifest_rejects_bad_pins_paths_missing_assets_and_duplicate_ids(self):
        original = deepcopy(speechmodels._DOCUMENT)
        cases = []
        bad = deepcopy(original); bad["format_version"] = 999; cases.append(bad)
        bad = deepcopy(original); bad["models"].append(bad["models"][0]); cases.append(bad)
        bad = deepcopy(original); bad["models"][0]["revision"] = None; cases.append(bad)
        bad = deepcopy(original); bad["models"][0]["package"]["files"].pop("tokenizer.json"); cases.append(bad)
        bad = deepcopy(original); bad["models"][0]["package"]["files"]["../x"] = {"sha256": "a" * 64, "size": 2}; cases.append(bad)
        bad = deepcopy(original); bad["models"][0]["package"]["files"]["model.bin"]["sha256"] = None; cases.append(bad)
        bad = deepcopy(original); bad["models"][0]["package"]["revision"] = "main"; cases.append(bad)
        for document in cases:
            with self.subTest(document=document.get("format_version")):
                with self.assertRaises(speechmodels.CatalogueError):
                    speechmodels.validate_manifest(document)

    def test_lora_recipes_pin_adapter_and_base_with_verified_weights(self):
        for model in ("it-turbo", "hi-fast"):
            recipe = speechmodels.entry(model)["conversion"]
            self.assertTrue(recipe["merge_lora"])
            self.assertEqual(recipe["base"]["repo"], "openai/whisper-large-v3-turbo")
            self.assertEqual(recipe["base"]["revision"], recipe["base_files"]["revision"])
            self.assertIn("adapter_model.safetensors", recipe["source_files"]["files"])
            self.assertIn("model.safetensors", recipe["base_files"]["files"])
            for source in (recipe["source_files"], recipe["base_files"]):
                for pin in source["files"].values():
                    self.assertRegex(pin["sha256"], r"^[a-f0-9]{64}$")


class Assets(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.row = speechmodels.entry("ja-kotoba-v2")
        vocabulary = ["a", "<|startoftranscript|>", "<|transcribe|>", "<|endoftext|>", "<|0.00|>", "<|ja|>"]
        self.values = {"config.json": {"alignment_heads": [[1, 0]]},
                       "preprocessor_config.json": {"sampling_rate": 16000, "feature_size": 128,
                                                    "hop_length": 160, "n_fft": 400},
                       "tokenizer.json": {"model": {"vocab": {"a": 0}}, "added_tokens":
                                          [{"content": value, "id": index} for index, value in enumerate(vocabulary[1:], 1)]},
                       "vocabulary.json": vocabulary}
        self.rewrite()
        patcher = patch.dict(speechmodels._ROWS, {"ja-kotoba-v2": self.row})
        patcher.start(); self.addCleanup(patcher.stop)

    def rewrite(self):
        files = {}
        for name, value in self.values.items():
            body = json.dumps(value, ensure_ascii=False).encode()
            (self.folder / name).write_bytes(body)
            files[name] = {"sha256": hashlib.sha256(body).hexdigest(), "size": len(body)}
        body = b"fake numerical-engine file"
        (self.folder / "model.bin").write_bytes(body)
        files["model.bin"] = {"sha256": hashlib.sha256(body).hexdigest(), "size": len(body)}
        self.row["package"]["files"] = files

    def test_structurally_complete_offline_assets(self):
        result = speechmodels.validate_assets("ja-kotoba-v2", self.folder, checksums=True)
        self.assertEqual(result["vocabulary_size"], 6)
        self.assertFalse(result["fully_compatible"])

    def test_invalid_alignment_or_audio_preprocessing_is_not_silently_ignored(self):
        for key, value in [("config.json", {"alignment_heads": [[31, 0]]}),
                           ("config.json", {"alignment_heads": []}),
                           ("preprocessor_config.json", {"sampling_rate": 8000, "feature_size": 128}),
                           ("preprocessor_config.json", {"sampling_rate": 16000, "feature_size": 80}),
                           ("config.json", [])]:
            original = self.values[key]
            self.values[key] = value; self.rewrite()
            with self.assertRaises(speechmodels.CatalogueError):
                speechmodels.validate_assets("ja-kotoba-v2", self.folder)
            self.values[key] = original

    def test_tokenizer_vocabulary_mismatch_and_missing_timestamp_capability(self):
        self.values["vocabulary.json"][0] = "wrong"
        self.rewrite()
        with self.assertRaises(speechmodels.CatalogueError):
            speechmodels.validate_assets("ja-kotoba-v2", self.folder)
        self.values["vocabulary.json"][0] = "a"
        self.values["vocabulary.json"][4] = "different"
        self.values["tokenizer.json"]["added_tokens"][3]["content"] = "different"
        self.rewrite()
        with self.assertRaisesRegex(speechmodels.CatalogueError, "timestamp"):
            speechmodels.validate_assets("ja-kotoba-v2", self.folder)

    def test_checksum_change_and_truncated_weight_file_are_rejected(self):
        path = self.folder / "model.bin"
        path.write_bytes(b"x" * path.stat().st_size)
        with self.assertRaisesRegex(speechmodels.CatalogueError, "checksum"):
            speechmodels.validate_assets("ja-kotoba-v2", self.folder, checksums=True)
        path.write_bytes(b"short")
        with self.assertRaisesRegex(speechmodels.CatalogueError, "incomplete"):
            speechmodels.validate_assets("ja-kotoba-v2", self.folder)


if __name__ == "__main__":
    unittest.main()
