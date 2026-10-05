# SPDX-License-Identifier: GPL-3.0-or-later
"""Versioned language choices and optional second pass, with isolated host state."""
import contextlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for relative in ('lib', 'youtube/lib', 'tests', '.'):
    sys.path.insert(0, str(ROOT / relative))
import speechconfig
import test_settings_risk as risk


class Preferences(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'config' / 'speech.json'
        patched = patch.object(speechconfig, 'CONFIG', self.path)
        patched.start()
        self.addCleanup(patched.stop)

    def test_previous_second_pass_format_gains_empty_language_choices(self):
        self.path.parent.mkdir()
        self.path.write_text(json.dumps({'format_version': 1, 'second_pass': False}))
        loaded = speechconfig.load()
        self.assertFalse(loaded['second_pass'])
        self.assertEqual(loaded['models_by_language'], {})

    def test_obsolete_optional_tool_setting_does_not_reset_whisper_preferences(self):
        self.path.parent.mkdir()
        self.path.write_text(json.dumps({'format_version': 1, 'second_pass': False,
                                        'phonetic_enabled': 'obsolete',
                                        'models_by_language': {'fa': 'fa-fast'}}))
        loaded = speechconfig.load()
        self.assertEqual(loaded, {'format_version': 1, 'second_pass': False,
                                  'models_by_language': {'fa': 'fa-fast'}})
        saved = speechconfig.save({'second_pass': True})
        self.assertEqual(saved, {'format_version': 1, 'second_pass': True,
                                 'models_by_language': {'fa': 'fa-fast'}})
        self.assertEqual(json.loads(self.path.read_text()), saved)

    def test_partial_preferences_preserve_each_other_and_language_choices(self):
        speechconfig.select('fa', 'fa-fast')
        speechconfig.select('hi', 'hi-accuracy')
        speechconfig.save({'second_pass': False})
        loaded = speechconfig.load()
        self.assertEqual(loaded['models_by_language'], {'fa': 'fa-fast', 'hi': 'hi-accuracy'})
        self.assertFalse(loaded['second_pass'])
        speechconfig.select('fa', '')
        self.assertEqual(speechconfig.load()['models_by_language'], {'hi': 'hi-accuracy'})
        self.assertEqual(list(self.path.parent.glob('speech-*.tmp')), [])

    def test_language_selection_rejects_unknown_wrong_language_or_non_string_model(self):
        for language, model in [('fa', 'hi-fast'), ('it', 'unknown-model'), ('fa', None),
                                ('../../fa', 'large-v3'), ('Persian', 'fa-fast'), ('FA', '')]:
            with self.subTest(language=language, model=model):
                with self.assertRaises(ValueError):
                    speechconfig.select(language, model)
        self.assertEqual(speechconfig.load()['models_by_language'], {})

    def test_preferences_reject_runtime_model_path_or_truthy_boolean_overrides(self):
        for raw in [{'second_pass': 1}, {'second_pass': 'yes'},
                    {'second_pass': False, 'path': '/model'}, {'model': 'fa-fast'},
                    {'models_by_language': []}, {'models_by_language': {'it': 'fa-fast'}},
                    {'models_by_language': {'fa': 'unlisted'}}, {}]:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    speechconfig.save(raw)
        self.assertTrue(speechconfig.load()['second_pass'])

    def test_unknown_malformed_or_oversized_store_falls_back_without_rewriting_it(self):
        self.path.parent.mkdir()
        for raw in ['{bad', 'x' * 17000,
                    json.dumps({'format_version': 99, 'second_pass': False}),
                    json.dumps({'format_version': 1, 'second_pass': 1}),
                    json.dumps({'format_version': 1, 'second_pass': False,
                                'models_by_language': {'it': 'fa-fast'}})]:
            self.path.write_text(raw)
            self.assertTrue(speechconfig.load()['second_pass'])
            self.assertEqual(self.path.read_text(), raw)

    def test_atomic_save_failure_keeps_old_settings_and_removes_temporary_file(self):
        speechconfig.select('fa', 'fa-fast')
        previous = self.path.read_bytes()
        with patch.object(speechconfig.os, 'replace', side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):
                speechconfig.save({'second_pass': False})
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(list(self.path.parent.glob('speech-*.tmp')), [])

    def test_concurrent_language_selections_merge_without_losing_other_choices(self):
        threads = [threading.Thread(target=speechconfig.select, args=(code, 'large-v3'))
                   for code in ('fa', 'ar', 'it', 'ja', 'fr', 'de', 'tr', 'en', 'hi', 'es', 'zh')]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(speechconfig.load()['models_by_language']), len(threads))
        self.assertEqual(list(self.path.parent.glob('speech-*.tmp')), [])


class SettingsAPI(unittest.TestCase):
    # Reuse the existing isolated real server fixture without inheriting its tests.
    setUpClass = classmethod(risk.Served.setUpClass.__func__)
    tearDownClass = classmethod(risk.Served.tearDownClass.__func__)
    ask = risk.Served.ask
    as_phone = risk.Served.as_phone

    def setUp(self):
        risk.Served.setUp(self)
        self.path = self.tmp / 'config' / 'speech-preferences-test.json'
        self.path.unlink(missing_ok=True)
        patched = patch.object(speechconfig, 'CONFIG', self.path)
        patched.start()
        self.addCleanup(patched.stop)

    def test_admitted_remote_device_can_choose_language_model_and_toggle_second_pass(self):
        with contextlib.ExitStack() as stack:
            for mocked in self.as_phone():
                stack.enter_context(mocked)
            status, _, answer = self.ask('POST', '/settings/api/speech/select-model',
                                        {'language': 'fa', 'model': 'fa-fast'})
            self.assertEqual(status, 200, answer)
            self.assertEqual(answer['preferences']['models_by_language'], {'fa': 'fa-fast'})
            for preference in ('second_pass',):
                status, _, answer = self.ask('POST', '/settings/api/speech/save', {preference: False})
                self.assertEqual(status, 200, answer)
            self.assertFalse(answer['preferences']['second_pass'])
            self.assertEqual(answer['preferences']['models_by_language'], {'fa': 'fa-fast'})

    def test_invalid_route_bodies_cannot_override_endpoint_audio_path_or_model_identity(self):
        invalid = [('/settings/api/speech/select-model', {'language': 'fa', 'model': 'fa-fast',
                                                        'path': '/other/model'}),
                   ('/settings/api/speech/select-model', {'language': 'fa', 'model': 'hi-fast'}),
                   ('/settings/api/speech/save', {'second_pass': 1}),
                   ('/settings/api/speech/save', {'endpoint': 'https://elsewhere.invalid'}),
                   ('/settings/api/speech/save', {'models_by_language': {'fa': 'unknown'}})]
        for route, body in invalid:
            with self.subTest(route=route, body=body):
                status, _, answer = self.ask('POST', route, body)
                self.assertEqual(status, 400, answer)
                self.assertFalse(answer['ok'])
        self.assertFalse(self.path.exists())

    def test_preference_routes_require_post_and_clear_only_one_language(self):
        for route in ('/settings/api/speech/save', '/settings/api/speech/select-model'):
            status, _, _ = self.ask('GET', route)
            self.assertEqual(status, 405)
        speechconfig.select('fa', 'fa-fast')
        speechconfig.select('hi', 'hi-fast')
        status, _, answer = self.ask('POST', '/settings/api/speech/select-model',
                                    {'language': 'fa', 'model': ''})
        self.assertEqual(status, 200, answer)
        self.assertEqual(answer['preferences']['models_by_language'], {'hi': 'hi-fast'})


if __name__ == '__main__':
    unittest.main()
