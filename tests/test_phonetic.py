# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline installer, genuine waveform-only worker, and lifecycle checks."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
import download
import getphonetic as gp
import phonetic
import phoneticpins
import phoneticworker as pw


class Installation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.directory = patch.object(gp, 'DIRECTORY', self.folder / 'phonetic')
        self.directory.start()
        self.data = {'config.json': b'{"sample_rate":16000}', 'pxeus/__init__.py': b'',
                     'model.safetensors': b'pretend-safe-weights'}
        self.pin = dict(phoneticpins.MODEL, files={n: [hashlib.sha256(b).hexdigest(), len(b)]
                         for n, b in self.data.items()})
        self.model = patch.object(gp, 'MODEL', self.pin)
        self.model.start()
        self.size = patch.object(gp, 'MODEL_BYTES', sum(map(len, self.data.values())))
        self.size.start()
        self.calls = []

    def tearDown(self):
        self.size.stop(); self.model.stop(); self.directory.stop(); self.tmp.cleanup()

    def fetch(self, url, destination, **kwargs):
        name = url.split(self.pin['revision'] + '/', 1)[1]
        data = self.data[name]
        self.calls.append(name)
        self.assertEqual(kwargs['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(kwargs['size'], len(data))
        self.assertEqual(kwargs['limit'], len(data))
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        Path(destination).write_bytes(data)

    def test_missing_is_independent_and_does_not_fetch(self):
        with patch.object(download, 'fetch', side_effect=AssertionError('status fetched bytes')):
            self.assertFalse(gp.model_ready())
            self.assertFalse(gp.runtime_ready())
            self.assertFalse(gp.status()['ready'])
            self.assertEqual(gp.status()['licence'], 'cc-by-nc-sa-4.0')

    def test_verified_atomic_offline_model_install(self):
        with patch.object(download, 'fetch', side_effect=self.fetch):
            gp.get('phonetic-model', say=lambda _s: None)
        self.assertTrue(gp.model_ready())
        self.assertFalse(gp.runtime_ready())
        self.assertEqual(set(self.calls), set(self.data))
        with patch.object(download, 'fetch', side_effect=AssertionError('offline retry fetched')):
            gp.get('phonetic-model', say=lambda _s: None)
        self.assertTrue(gp.model_ready())
        self.assertEqual(json.loads((gp.model_dir() / '.parseh.json').read_text())['files'], self.pin['files'])

    def test_cancel_keeps_resume_and_no_partial_publication(self):
        stop = threading.Event()
        def progress(done, total, _phase):
            if done > 0:
                stop.set()
        with patch.object(download, 'fetch', side_effect=self.fetch):
            with self.assertRaises(download.Cancelled):
                gp.get('phonetic-model', stop=stop, progress=progress, say=lambda _s: None)
            self.assertFalse(gp.model_ready())
            self.assertFalse(gp.model_dir().exists())
            first = list(self.calls)
            stop.clear()
            gp.get('phonetic-model', stop=stop, say=lambda _s: None)
        self.assertEqual(self.calls.count(first[0]), 1)
        self.assertTrue(gp.model_ready())

    def test_bad_checksum_never_replaces_installed_model(self):
        with patch.object(download, 'fetch', side_effect=self.fetch):
            gp.get('phonetic-model', say=lambda _s: None)
        old = gp.model_dir() / 'model.safetensors'
        changed = dict(self.pin, files=dict(self.pin['files']))
        changed['files']['config.json'] = [hashlib.sha256(b'new-config').hexdigest(), 10]
        with patch.object(gp, 'MODEL', changed), patch.object(download, 'fetch', side_effect=download.Mismatch('incorrect digest')):
            # Delete only one staged file to trigger a failed refresh.
            with self.assertRaises(download.Mismatch):
                gp.get('phonetic-model', say=lambda _s: None)
        self.assertEqual(old.read_bytes(), self.data['model.safetensors'])
        self.assertTrue(gp.model_ready())

    def test_remove_only_own_installed_component(self):
        with patch.object(download, 'fetch', side_effect=self.fetch):
            gp.get('phonetic-model', say=lambda _s: None)
        runtime = gp.runtime_dir(); runtime.mkdir(parents=True)
        (runtime / 'keep').write_text('runtime')
        unrelated = self.folder / 'whisper-model'; unrelated.write_text('untouched')
        gp.remove('phonetic-model')
        self.assertTrue(runtime.exists())
        self.assertTrue(unrelated.exists())
        with gp.using():
            with self.assertRaises(gp.PhoneticError):
                gp.remove('phonetic-runtime')
        gp.remove('phonetic-runtime')
        self.assertFalse(runtime.exists())

    def test_corrupt_code_rejected_before_import(self):
        with patch.object(download, 'fetch', side_effect=self.fetch):
            gp.get('phonetic-model', say=lambda _s: None)
        (gp.model_dir() / 'config.json').write_bytes(b'x' * len(self.data['config.json']))
        with patch.object(phoneticpins, 'MODEL', self.pin):
            with self.assertRaises(pw.Refused) as held:
                pw.verify_model(gp.model_dir())
        self.assertEqual(held.exception.code, 'model-incomplete')

    def test_runtime_hash_closure_platforms(self):
        phoneticpins.validate()
        self.assertEqual(set(phoneticpins.RUNTIME['platforms']), {'linux x86_64', 'linux aarch64',
                            'windows amd64', 'macOS arm64', 'macOS x86_64'})
        for key, rows in phoneticpins.RUNTIME['platforms'].items():
            packages = {row['package'] for row in rows}
            self.assertTrue({'torch', 'torchaudio', 'numpy', 'safetensors', 'av', 'typeguard'} <= packages)
            self.assertNotIn('transformers', packages)
            if key in ('linux x86_64', 'windows amd64'):
                self.assertTrue(next(row for row in rows if row['package'] == 'torch')['version'].endswith('+cpu'))


class Worker(unittest.TestCase):
    def test_pcm_crop_uses_audio_not_spelling(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'audio.pcm'
            waveform = np.arange(32000, dtype=np.int16)
            path.write_bytes(waveform.astype('<i2').tobytes())
            crop, start, end = pw.audio_crop(str(path), 'pcm16', .5, .8)
        self.assertAlmostEqual(start, 0.)
        self.assertAlmostEqual(end, 1.3)
        self.assertEqual(len(crop), 20800)
        self.assertAlmostEqual(float(crop[0]), 0.)

    def test_worker_reuses_once_and_failure_is_local(self):
        from phoneticpins import MODEL
        import numpy as np
        events, calls = [], []
        def inference(audio):
            calls.append(audio.copy())
            return [{'processed_transcript': 'ɕəŋ', 'predicted_transcript': 'ɕ/ə/ŋ'}]
        spec = {'source_path': '/audio', 'audio_kind': 'pcm16', 'processing': 'cpu',
                'model_path': '/model', 'targets': [
                    {'word_id': 's0w0', 'start': .1, 'end': .3},
                    {'word_id': 's0w1', 'invalid_timing': True},
                    {'word_id': 's0w2', 'start': .8, 'end': 1.0}]}
        with patch.object(pw, 'load_model', return_value=(inference, MODEL)) as load:
            with patch.object(pw, 'audio_crop', return_value=(np.zeros(4000), 0., 1.2)):
                with patch.object(pw, 'send', side_effect=events.append):
                    pw.run(spec)
        self.assertEqual(load.call_count, 1)
        self.assertEqual(len(calls), 2)
        words = [e for e in events if e['event'] == 'word']
        self.assertEqual([w['phonetic']['state'] for w in words], ['complete', 'failed', 'complete'])
        self.assertEqual(words[0]['phonetic']['ipa'], 'ɕəŋ')
        self.assertEqual(events[-1]['failed'], 1)
        self.assertEqual([e['completed'] for e in events if e['event'] == 'progress'], [1, 2, 3])
        self.assertEqual(spec['targets'][0], {'word_id': 's0w0', 'start': .1, 'end': .3})

    def test_unicode_output_and_invalid_output(self):
        self.assertEqual(pw.interpret([{'processed_transcript': 'tʰɾɒ̃', 'predicted_transcript': 'tʰ/ɾ/ɒ̃'}])[0], 'tʰɾɒ̃')
        for result in ([{'processed_transcript': '', 'predicted_transcript': ''}], [],
                       [{'processed_transcript': 'x' * 4001, 'predicted_transcript': 'x'}],
                       [{'processed_transcript': 't\n', 'predicted_transcript': 't'}]):
            with self.assertRaises(pw.Refused):
                pw.interpret(result)

    def test_numpy_timestamps_remain_usable(self):
        import numpy as np
        self.assertEqual(pw.finite(np.float64(.8)), .8)
        self.assertIsNone(pw.finite(True))
        self.assertIsNone(pw.finite(float('nan')))

    def test_no_cuda_claim_in_cpu_runtime(self):
        with self.assertRaises(pw.Refused) as held:
            pw.load_model('/not-read', 'cuda')
        self.assertEqual(held.exception.code, 'unsupported-device')


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.src = self.folder / 'audio.pcm'; self.src.write_bytes(b'\x00\x00' * 16000)
        self.worker = self.folder / 'worker.py'
        self.targets = [{'word_id': 's0w0', 'start': .1, 'end': .2},
                        {'word_id': 's0w1', 'start': .3, 'end': .4}]
        self.patches = [patch.object(gp, 'DIRECTORY', self.folder / 'phonetic'),
                        patch.object(gp, 'WORKER', self.worker),
                        patch.object(gp, 'runtime_ready', return_value=True),
                        patch.object(gp, 'model_ready', return_value=True)]
        for value in self.patches: value.start()

    def tearDown(self):
        for value in reversed(self.patches): value.stop()
        self.temp.cleanup()

    def script(self, footer=''):
        self.worker.write_text('import json,sys,time\ns=json.load(open(sys.argv[1]))\n' +
            'for t in s["targets"]:\n' +
            ' e={"state":"complete","ipa":"ɾə","phones":"ɾ/ə","audio_start":0,"audio_end":1,' +
            '"attribution":"context-crop","model_revision":' + repr(phoneticpins.MODEL['revision']) + '}\n' +
            ' print(json.dumps({"event":"word","word_id":t["word_id"],"phonetic":e}),flush=True)\n' +
            (footer or 'print(json.dumps({"event":"done","completed":len(s["targets"]),"total":len(s["targets"])}),flush=True)\n'))

    def test_complete_progress_and_cleanup(self):
        self.script(); events = []
        result = phonetic.run(self.src, 'pcm16', self.targets, progress=lambda a,b: events.append((a,b)))
        self.assertEqual(result['state'], 'complete')
        self.assertEqual(events, [(0,2), (1,2), (2,2)])
        self.assertFalse(gp.LIVE)
        self.assertFalse(list((gp.DIRECTORY / 'tmp').glob('*.json')))

    def test_missing_runtime_does_not_start_worker(self):
        with patch.object(gp, 'runtime_ready', return_value=False):
            with self.assertRaises(gp.PhoneticError):
                phonetic.run(self.src, 'pcm16', self.targets)
        self.assertFalse(gp.LIVE)

    def test_target_contract_excludes_transcript_and_duplicates(self):
        for targets in ([dict(self.targets[0], text='do not pass spelling')],
                        [self.targets[0], self.targets[0]],
                        [dict(self.targets[0], word_id='bad')]):
            with self.assertRaises(gp.PhoneticError):
                phonetic.run(self.src, 'pcm16', targets)
        self.assertFalse(gp.LIVE)

    def test_cancel_during_native_load_kills_child(self):
        self.worker.write_text('import time\ntime.sleep(30)\n')
        stop = threading.Event()
        threading.Timer(.15, stop.set).start()
        begun = time.monotonic()
        with self.assertRaises(download.Cancelled):
            phonetic.run(self.src, 'pcm16', self.targets, cancel=stop)
        self.assertLess(time.monotonic() - begun, 3)
        self.assertFalse(gp.LIVE)

    def test_stale_after_word_discards_inflight(self):
        self.script(); current = [True]
        with self.assertRaises(phonetic.SourceChanged):
            phonetic.run(self.src, 'pcm16', self.targets, source_check=lambda: current[0],
                         on_word=lambda _w: current.__setitem__(0, False))
        self.assertFalse(gp.LIVE)

    def test_partial_worker_failure_reports_missing_word(self):
        self.targets = self.targets[:1]
        self.script()
        # Simulated second source target remains unprocessed after one valid result.
        base = self.worker.read_text().replace('for t in s["targets"]:', 'for t in s["targets"][:1]:')
        self.worker.write_text(base)
        self.targets.append({'word_id':'s0w1','start':.3,'end':.4})
        result = phonetic.run(self.src, 'pcm16', self.targets)
        self.assertEqual(result['state'], 'partial')
        self.assertEqual(result['failed'], 1)
        self.assertEqual(result['words'][1]['phonetic']['state'], 'failed')

    def test_crops_outside_word_are_rejected(self):
        self.script()
        self.worker.write_text(self.worker.read_text().replace('"audio_start":0', '"audio_start":.8'))
        with self.assertRaises(gp.PhoneticError):
            phonetic.run(self.src, 'pcm16', self.targets)


if __name__ == '__main__':
    unittest.main()
