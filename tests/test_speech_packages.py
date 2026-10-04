# SPDX-License-Identifier: GPL-3.0-or-later
"""Tiny pinned ZIPs exercise prepared-model ingress without conversion or weights."""
import contextlib
import hashlib
import http.client
import io
from pathlib import Path
import stat
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[1]
for relative in ('lib', 'youtube/lib', 'tests', '.'):
    sys.path.insert(0, str(ROOT / relative))
import download
import getstt
import speechmodels
import speechpackages
import test_settings_risk as risk

FILES = {'config.json': b'{"task":"transcribe"}', 'model.bin': b'tiny fake CT2 bytes',
         'tokenizer.json': b'{}', 'vocabulary.json': b'[]',
         'preprocessor_config.json': b'{"sampling_rate":16000}', 'LICENSE.txt': b'MIT fixture'}


def bundle(files=FILES, modes=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for name, data in files.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = ((modes or {}).get(name, stat.S_IFREG | 0o644)) << 16
            archive.writestr(info, data)
    return stream.getvalue()


def package(archive):
    return {'distribution': 'local-package', 'repo':'fixtures/fa-fast', 'revision': '1' * 40,
            'package_name': 'parseh-fa-fast-fixture.zip', 'package_size': len(archive),
            'package_sha256': hashlib.sha256(archive).hexdigest(),
            'files': {name: (hashlib.sha256(data).hexdigest(), len(data))
                      for name, data in FILES.items()}}


class Packages(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.archive = bundle()
        self.pin = package(self.archive)
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(getstt, 'STT_DIR', str(self.root / 'stt')))
        self.stack.enter_context(patch.object(speechpackages, 'PREPARED_ROOT', self.root / 'maintainer'))
        self.stack.enter_context(patch.dict(speechmodels.MODEL_PINS, {'fa-fast': self.pin}))
        # Semantic CT2 assets have their own catalogue tests; this tiny ingress
        # fixture deliberately contains no real weights or executable assets.
        self.validator = self.stack.enter_context(patch.object(speechmodels, 'validate_assets'))

    def imported(self):
        return speechpackages.cache_root() / 'fa-fast' / self.pin['revision']

    def clean(self):
        self.assertEqual(list((speechpackages.cache_root() / 'fa-fast').glob('.import-*')), [])

    def test_valid_package_hashes_every_asset_and_atomically_publishes_offline_files(self):
        events = []
        speechpackages.import_stream('fa-fast', io.BytesIO(self.archive), len(self.archive),
                                     progress=lambda done, total, phase: events.append((done, total, phase)))
        self.validator.assert_called_once()
        self.assertTrue(speechpackages.available('fa-fast'))
        for name, data in FILES.items():
            self.assertEqual((self.imported() / name).read_bytes(), data)
        self.assertIn('upload', [event[2] for event in events])
        self.assertIn('verify', [event[2] for event in events])
        self.assertFalse((self.imported() / '.upload.zip').exists())
        self.clean()

    def test_imported_model_installs_offline_and_frees_only_temporary_import_files(self):
        speechpackages.import_stream('fa-fast', io.BytesIO(self.archive), len(self.archive))
        size = sum(map(len, FILES.values()))
        with patch.dict(getstt.MEASURED, {'fa-fast': size}), \
                patch.object(getstt, 'runtime_ready', return_value=True), \
                patch.object(speechmodels, 'bundled_file', return_value=None), \
                patch.object(download, 'fetch', side_effect=AssertionError('local package must not fetch')):
            self.assertEqual(getstt.plan('fa-fast')['download'], 0)
            getstt._install_model('fa-fast', lambda *_: None, None, None)
        self.assertTrue(getstt.model_info('fa-fast')['ready'])
        for name, body in FILES.items():
            self.assertEqual((Path(getstt.model_dir('fa-fast')) / name).read_bytes(), body)
        self.assertFalse(speechpackages.available('fa-fast'))

    def test_wrong_archive_checksum_keeps_previous_package_intact_and_cleans_stage(self):
        speechpackages.import_stream('fa-fast', io.BytesIO(self.archive), len(self.archive))
        tampered = self.archive[:-1] + bytes([self.archive[-1] ^ 1])
        with self.assertRaisesRegex(speechpackages.PackageError, 'checksum'):
            speechpackages.import_stream('fa-fast', io.BytesIO(tampered), len(tampered))
        self.assertEqual((self.imported() / 'model.bin').read_bytes(), FILES['model.bin'])
        self.clean()

    def test_pinned_archive_with_corrupt_asset_still_fails_its_individual_hash(self):
        corrupt = dict(FILES, **{'model.bin': b'x' * len(FILES['model.bin'])})
        raw = bundle(corrupt)
        self.pin.update(package_sha256=hashlib.sha256(raw).hexdigest(), package_size=len(raw))
        with self.assertRaisesRegex(speechpackages.PackageError, 'checksum'):
            speechpackages.import_stream('fa-fast', io.BytesIO(raw), len(raw))
        self.assertFalse(speechpackages.available('fa-fast'))
        self.clean()

    def test_path_traversal_and_symlink_entries_are_rejected_before_publication(self):
        for raw in (bundle(dict(FILES, **{'../escape.txt': b'no'})),
                    bundle(modes={'model.bin': stat.S_IFLNK | 0o777})):
            with self.subTest(size=len(raw)):
                self.pin.update(package_sha256=hashlib.sha256(raw).hexdigest(), package_size=len(raw))
                with self.assertRaises(speechpackages.PackageError):
                    speechpackages.import_stream('fa-fast', io.BytesIO(raw), len(raw))
                self.assertFalse(speechpackages.available('fa-fast'))
                self.clean()
        self.assertFalse((self.root / 'escape.txt').exists())

    def test_duplicate_members_are_rejected_even_when_archive_checksum_is_pinned(self):
        stream = io.BytesIO(self.archive)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(stream, 'a') as archive:
                archive.writestr('model.bin', FILES['model.bin'])
        raw = stream.getvalue()
        self.pin.update(package_sha256=hashlib.sha256(raw).hexdigest(), package_size=len(raw))
        with self.assertRaisesRegex(speechpackages.PackageError, 'unexpected or missing'):
            speechpackages.import_stream('fa-fast', io.BytesIO(raw), len(raw))
        self.assertFalse(speechpackages.available('fa-fast'))
        self.clean()

    def test_prepared_directory_is_detected_without_creating_stt_or_copying_weights(self):
        prepared = speechpackages.PREPARED_ROOT / 'fa-fast' / self.pin['revision']
        prepared.mkdir(parents=True)
        for name, data in FILES.items():
            (prepared / name).write_bytes(data)
        self.assertEqual(speechpackages.folder('fa-fast'), prepared)
        self.assertTrue(speechpackages.available('fa-fast'))
        self.assertFalse(Path(getstt.STT_DIR).exists())

    def test_truncated_upload_and_cancellation_discard_incomplete_stage(self):
        with self.assertRaisesRegex(speechpackages.PackageError, 'did not finish'):
            speechpackages.import_stream('fa-fast', io.BytesIO(self.archive[:-20]), len(self.archive))
        self.clean()
        cancel = threading.Event()
        def stop(done, total, phase):
            cancel.set()
        with self.assertRaises(download.Cancelled):
            speechpackages.import_stream('fa-fast', io.BytesIO(self.archive), len(self.archive),
                                         cancel=cancel, progress=stop)
        self.assertFalse(speechpackages.available('fa-fast'))
        self.clean()

    def test_unsupported_assets_are_not_published_as_compatible(self):
        self.validator.side_effect = speechmodels.CatalogueError('Required timestamp metadata is invalid.')
        with self.assertRaisesRegex(speechmodels.CatalogueError, 'timestamp'):
            speechpackages.import_stream('fa-fast', io.BytesIO(self.archive), len(self.archive))
        self.assertFalse(speechpackages.available('fa-fast'))
        self.clean()

    def test_local_copy_resumes_and_refuses_a_corrupt_partial_prefix(self):
        source = self.root / 'source.bin'
        source.write_bytes(FILES['model.bin'])
        destination = self.root / 'model.bin'
        partial = self.root / 'model.bin.part'
        sha = hashlib.sha256(source.read_bytes()).hexdigest()
        partial.write_bytes(source.read_bytes()[:5])
        speechpackages.copy_verified(source, destination, sha, source.stat().st_size)
        self.assertEqual(destination.read_bytes(), source.read_bytes())
        destination.unlink()
        partial.write_bytes(b'wrong')
        with self.assertRaisesRegex(speechpackages.PackageError, 'checksum'):
            speechpackages.copy_verified(source, destination, sha, source.stat().st_size)
        self.assertFalse(destination.exists())
        self.assertFalse(partial.exists())

    def test_corrupt_local_source_cannot_replace_existing_destination(self):
        source = self.root / 'source.bin'
        source.write_bytes(b'x' * len(FILES['model.bin']))
        destination = self.root / 'model.bin'
        destination.write_bytes(b'previous complete model')
        sha = hashlib.sha256(FILES['model.bin']).hexdigest()
        with self.assertRaisesRegex(speechpackages.PackageError, 'checksum'):
            speechpackages.copy_verified(source, destination, sha, len(FILES['model.bin']))
        self.assertEqual(destination.read_bytes(), b'previous complete model')
        self.assertFalse((self.root / 'model.bin.part').exists())

    def test_failed_final_model_rename_restores_old_complete_model(self):
        final, staged = self.root / 'model', self.root / 'model.part'
        final.mkdir()
        staged.mkdir()
        (final / 'model.bin').write_bytes(b'previous complete model')
        (staged / 'model.bin').write_bytes(b'new complete model')
        replace = getstt.os.replace
        def fail_once(source, destination):
            if source == str(staged) and destination == str(final):
                raise OSError('Simulated Windows rename failure')
            return replace(source, destination)
        with patch.object(getstt.os, 'replace', side_effect=fail_once):
            with self.assertRaises(OSError):
                getstt._publish_model(str(staged), str(final))
        self.assertEqual((final / 'model.bin').read_bytes(), b'previous complete model')
        self.assertEqual((staged / 'model.bin').read_bytes(), b'new complete model')
        self.assertEqual(list(self.root.glob('.old-*')), [])


class Starts(unittest.TestCase):
    """Two browsers must not replace an install's event or staging writer."""
    setUpClass = classmethod(risk.Served.setUpClass.__func__)
    tearDownClass = classmethod(risk.Served.tearDownClass.__func__)

    def setUp(self):
        risk.Served.setUp(self)

    def test_simultaneous_starts_share_one_job_and_cancellation_event(self):
        planning, continue_plan, building = threading.Event(), threading.Event(), threading.Event()
        seen, answers = [], []
        def plan(*_args, **_kw):
            planning.set()
            self.assertTrue(continue_plan.wait(3))
            return {'download': 10, 'disk_peak': 10}
        def build(*_args, cancel=None, **_kw):
            seen.append(cancel)
            building.set()
            self.assertTrue(cancel.wait(3))
            raise download.Cancelled()
        fake = types.SimpleNamespace(plan=plan, build=build)
        with patch.object(self.serve, '_reading_module', return_value=fake), \
                patch.object(self.serve, 'disk_free', return_value=1 << 30), \
                patch.object(getstt, 'unavailable_reason', return_value=''):
            first = threading.Thread(target=lambda: answers.append(self.serve.reading_start('speech', 'fa-fast')))
            second = threading.Thread(target=lambda: answers.append(self.serve.reading_start('speech', 'fa-fast')))
            first.start()
            self.assertTrue(planning.wait(3))
            second.start()
            continue_plan.set()
            self.assertTrue(building.wait(3))
            first.join(3); second.join(3)
            self.assertFalse(first.is_alive() or second.is_alive())
            self.assertEqual(len(seen), 1)
            self.assertEqual(sum(answer.get('already', False) for answer, _code in answers), 1)
            self.assertIs(self.serve.CANCELS[('speech', 'fa-fast')], seen[0])
            self.assertTrue(self.serve.reading_stop('speech', 'fa-fast'))
            deadline = time.monotonic() + 3
            while self.serve.STT_JOBS['fa-fast']['running'] and time.monotonic() < deadline:
                time.sleep(.01)
        self.assertTrue(self.serve.STT_JOBS['fa-fast']['stopped'])
        self.assertFalse(self.serve.STT_JOBS['fa-fast']['running'])

    def test_installed_model_restores_missing_runtime_without_copying_weights(self):
        ready = [False]
        def install(*_args, **_kw):
            ready[0] = True
        with patch.object(getstt, 'unavailable_reason', return_value=''), \
                patch.object(getstt, 'model_ready', return_value=True), \
                patch.object(getstt, 'model_info', return_value={'size':123}), \
                patch.object(getstt, 'runtime_ready', side_effect=lambda: ready[0]), \
                patch.object(getstt, '_runtime_plan', return_value=(10,20)), \
                patch.object(getstt, '_install_runtime', side_effect=install) as runtime, \
                patch.object(getstt, '_install_model') as weights:
            self.assertEqual(getstt.build('fa-fast', say=lambda *_: None), 123)
        runtime.assert_called_once()
        weights.assert_not_called()


class ImportAPI(unittest.TestCase):
    setUpClass = classmethod(risk.Served.setUpClass.__func__)
    tearDownClass = classmethod(risk.Served.tearDownClass.__func__)
    as_phone = risk.Served.as_phone

    def setUp(self):
        risk.Served.setUp(self)
        self.archive = bundle()
        self.pin = package(self.archive)
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(speechmodels.MODEL_PINS, {'fa-fast': self.pin}))
        self.stack.enter_context(patch.object(speechmodels, 'validate_assets'))
        self.stack.enter_context(patch.object(getstt, 'STT_DIR', str(self.tmp / 'imports' / self._testMethodName)))
        self.stack.enter_context(patch.object(speechpackages, 'PREPARED_ROOT', self.tmp / 'no-maintainer-models'))
        self.stack.enter_context(patch.object(self.serve, 'disk_free', return_value=1 << 30))
        self.install = self.stack.enter_context(patch.object(self.serve, 'reading_start',
                                                           return_value=({'ok': True}, 200)))

    def ask(self, path, data=None, method='POST', headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.srv.server_address[1], timeout=5)
        connection.request(method, path, body=self.archive if data is None else data,
                           headers={'Content-Type': 'application/zip', **(headers or {})})
        response = connection.getresponse()
        import json
        answer = json.loads(response.read())
        connection.close()
        return response.status, answer

    def test_admitted_remote_device_imports_only_pinned_zip_then_starts_normal_install(self):
        with contextlib.ExitStack() as stack:
            for mocked in self.as_phone():
                stack.enter_context(mocked)
            status, answer = self.ask('/settings/api/speech/import-package?model=fa-fast')
        self.assertEqual(status, 200, answer)
        self.install.assert_called_once()
        self.assertEqual(self.install.call_args.args, ('speech', 'fa-fast'))
        self.assertIsInstance(self.install.call_args.kwargs.get('_import_cancel'), threading.Event)
        self.assertTrue(speechpackages.available('fa-fast'))
        self.assertNotIn(('speech', 'fa-fast'), self.serve.CANCELS)

    def test_unadmitted_device_cannot_upload_or_start_install(self):
        import network
        with contextlib.ExitStack() as stack:
            for mocked in self.as_phone():
                stack.enter_context(mocked)
            stack.enter_context(patch.object(network, 'let_in', return_value=False))
            status, answer = self.ask('/settings/api/speech/import-package?model=fa-fast')
        self.assertEqual(status, 403, answer)
        self.install.assert_not_called()
        self.assertFalse(speechpackages.available('fa-fast'))
        self.assertNotIn('fa-fast', self.serve.STT_JOBS)

    def test_cross_site_package_upload_is_refused_before_staging(self):
        status, answer = self.ask('/settings/api/speech/import-package?model=fa-fast',
                                  headers={'Sec-Fetch-Site': 'cross-site'})
        self.assertEqual(status, 403, answer)
        self.install.assert_not_called()
        self.assertFalse(speechpackages.available('fa-fast'))
        self.assertNotIn('fa-fast', self.serve.STT_JOBS)

    def test_unknown_model_duplicate_model_or_path_override_never_start_install(self):
        for query in ('model=unlisted', 'model=fa-fast&model=fa-fast',
                      'model=fa-fast&path=%2Felsewhere', 'model=large-v3', 'model=fa-fast&url=https://elsewhere.invalid'):
            with self.subTest(query=query):
                status, answer = self.ask('/settings/api/speech/import-package?' + query)
                self.assertEqual(status, 400, answer)
                self.assertFalse(answer['ok'])
        self.install.assert_not_called()

    def test_size_and_checksum_failures_cannot_publish_or_install(self):
        for data in (self.archive[:-1], self.archive[:-1] + bytes([self.archive[-1] ^ 1])):
            with self.subTest(size=len(data)):
                status, answer = self.ask('/settings/api/speech/import-package?model=fa-fast', data)
                self.assertEqual(status, 400, answer)
                self.assertFalse(answer['ok'])
        self.install.assert_not_called()
        self.assertFalse(speechpackages.available('fa-fast'))
        self.assertFalse(self.serve.STT_JOBS['fa-fast']['running'])

    def test_active_install_and_insufficient_disk_are_rejected_before_streaming(self):
        self.serve.STT_JOBS['fa-fast'] = {'running': True}
        status, answer = self.ask('/settings/api/speech/import-package?model=fa-fast')
        self.assertEqual(status, 409, answer)
        self.serve.STT_JOBS.clear()
        with patch.object(self.serve, 'disk_free', return_value=0):
            status, answer = self.ask('/settings/api/speech/import-package?model=fa-fast')
        self.assertEqual(status, 507, answer)
        self.install.assert_not_called()
        self.assertFalse(self.serve.STT_JOBS['fa-fast']['running'])

    def test_get_is_not_an_import_and_configuration_is_not_sent_back(self):
        status, answer = self.ask('/settings/api/speech/import-package?model=fa-fast', b'', method='GET')
        self.assertEqual(status, 405, answer)
        self.assertNotIn('package', answer)
        self.assertNotIn('path', answer)
        self.install.assert_not_called()


if __name__ == '__main__':
    unittest.main()
