# SPDX-License-Identifier: GPL-3.0-or-later
"""Original-audio IPA evidence integrated after Whisper, without real models."""
import copy
import csv
import io
import json
import os
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for rel in ('tests', 'lib', 'youtube/lib'):
    sys.path.insert(0, str(ROOT / rel))
import asrcorrection
import asrdictionary
import asrexternal
import asrpending
import asrworkspace
import getphonetic
import phonetic
import speechconfig
import sttjobs
import stt_fakes
import wordtimes
from test_stt_jobs import Base


class PhoneticJobs(Base):
    def setUp(self):
        super().setUp()
        speechconfig.save({'second_pass': False, 'phonetic_enabled': True})
        self.calls, self.before, self.before_tape = [], None, None
        for patched in (
                mock.patch.object(getphonetic, 'status', return_value={'ready':True, 'revision':'fake-revision'}),
                mock.patch.object(phonetic, 'run', side_effect=self.runner),
                mock.patch.object(asrdictionary.Resolver, 'word', side_effect=lambda text, *args:
                    {'state':'missing' if text == 'strano' else 'found', 'words':[]})):
            patched.start(); self.addCleanup(patched.stop)
        self.fake(segments=[[0,4,' loro anno detto strano']], word_evidence={
            'anno': {'score': .2, 'alternatives': [{'text':'hanno','score':.3}]},
            'strano': {'score': .95, 'alternatives': [{'text':'strana','score':None}]}})

    def evidence(self, target, failed=False):
        return {'word_id':target['word_id'], 'phonetic':
            {'state':'failed', 'reason':'No usable phones.'} if failed else {
                'state':'complete', 'ipa':'ɾə', 'phones':'ɾ/ə', 'attribution':'context-crop',
                'target_start':target['start'], 'target_end':target['end'],
                'audio_start':max(0,target['start']-.5), 'audio_end':target['end']+.5,
                'model_revision':'fake-revision'}}

    def runner(self, source, audio_kind, targets, processing='auto', **callbacks):
        job = next(j for j in sttjobs.JOBS.values() if j['state'] == sttjobs.PHONETIC)
        self.assertEqual(self.gs.in_use(), [], 'Whisper model hold is released before IPA')
        self.assertTrue(all(p.poll() is not None for p in self.gs._procs), 'Whisper child has exited')
        self.before = copy.deepcopy(job['review_evidence'])
        self.before_tape = wordtimes.load(job['id'])
        self.calls.append({'source':source, 'kind':audio_kind, 'targets':copy.deepcopy(targets),
                           'processing':processing, 'job':job})
        output = []
        for target in targets:
            item = self.evidence(target)
            output.append(item)
            callbacks['on_word'](item)
            callbacks['progress'](len(output), len(targets))
        return {'state':'complete', 'words':output, 'completed':len(output), 'total':len(targets),
                'failed':0, 'revision':'fake-revision', 'device':'cpu'}

    def ready(self):
        token = self.start_film(lang='it', seconds=4)['job']
        self.assertEqual(self.done(token)['state'], 'done')
        return token, sttjobs.result(token)

    def assert_source_unchanged(self, result):
        now = copy.deepcopy(result['review']['evidence'])
        now.pop('phonetic', None)
        for word in asrcorrection.index(now).values():
            word.pop('phonetic', None)
        self.assertEqual(now, self.before)
        self.assertEqual(wordtimes.load(self.calls[-1]['job']['id']), self.before_tape)

    def test_fixed_first_suspects_and_source_evidence_unchanged(self):
        token, result = self.ready()
        self.assertEqual(len(self.calls), 1)
        targets = self.calls[0]['targets']
        self.assertEqual([w['word_id'] for w in targets], ['s0w1','s0w3'])
        self.assertTrue(all(set(w) == {'word_id','start','end'} for w in targets))
        self.assertEqual(self.calls[0]['kind'], 'media')
        self.assert_source_unchanged(result)
        words = asrcorrection.index(result['review']['evidence'])
        self.assertEqual(words['s0w1']['asr_confidence'], .2)
        self.assertEqual(words['s0w3']['asr_confidence'], .95)
        self.assertFalse(words['s0w3']['low_asr_score'])
        self.assertTrue(words['s0w3']['dictionary_miss'])
        self.assertNotIn('phonetic', words['s0w0'])
        self.assertNotIn('phonetic', words['s0w2'])
        self.assertEqual(result['review']['evidence']['phonetic']['done'], 2)
        self.assertEqual(len(self.records('transcribe')), 1)
        self.assertIsNone(result['review']['choice'])
        self.assertNotIn('ɾə', result['text'])

    def test_missing_installation_and_disabled_preference_skip_without_requests(self):
        for ready, enabled in ((False, True), (True, False)):
            speechconfig.save({'phonetic_enabled':enabled})
            with mock.patch.object(getphonetic, 'status', return_value={'ready':ready, 'revision':'fake'}):
                _, result = self.ready()
            self.assertNotIn('phonetic', result['review']['evidence'])
        self.assertFalse(self.calls)

    def test_individual_failure_keeps_other_evidence_and_finishes_asr(self):
        def partial(source, kind, targets, processing='auto', **callbacks):
            self.runner(source, kind, targets, processing, **callbacks)
            rows = [self.evidence(target, failed=i==1) for i,target in enumerate(targets)]
            return {'state':'partial','words':rows,'revision':'fake-revision','device':'cpu'}
        with mock.patch.object(phonetic, 'run', side_effect=partial):
            _, result = self.ready()
        self.assert_source_unchanged(result)
        words = asrcorrection.index(result['review']['evidence'])
        self.assertEqual(words['s0w1']['phonetic']['state'], 'complete')
        self.assertEqual(words['s0w3']['phonetic']['state'], 'failed')
        self.assertEqual(result['review']['evidence']['phonetic']['state'], 'partial')
        self.assertEqual(result['review']['evidence']['phonetic']['failed'], 1)
        self.assertTrue(any('unavailable for 1' in n for n in result['notes']))

    def test_all_ipa_failures_are_distinct_and_keep_whisper_usable(self):
        with mock.patch.object(phonetic, 'run', side_effect=RuntimeError('private diagnostic must stay private')):
            _, result = self.ready()
        status = result['review']['evidence']['phonetic']
        self.assertEqual(status['state'], 'failed')
        self.assertEqual((status['done'],status['total'],status['failed']), (2,2,2))
        self.assertEqual(result['text'].splitlines()[-1], 'loro anno detto strano')
        self.assertNotIn('private diagnostic', json.dumps(result))
        self.assertNotIn('private diagnostic', self.log.getvalue())

    def test_runs_after_optional_second_pass_without_recursive_targets(self):
        speechconfig.save({'second_pass':True})
        self.fake(segments=[[0,4,' loro anno detto strano']],
                  word_evidence={'anno':{'score':.2}},
                  second_pass=[{'segments':[[0,4,' loro hanno detto strano']]},
                               {'segments':[[0,4,' loro anno detto strana']]}])
        token, result = self.ready()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual([t['word_id'] for t in self.calls[0]['targets']], ['s0w1','s0w3'])
        self.assertEqual(len(self.records('transcribe')), 3)
        self.assertEqual(self.before['second_pass']['done'], 2)
        self.assertIn('hanno', [a['text'] for a in asrcorrection.index(self.before)['s0w1']['asr_alternatives']])
        self.assert_source_unchanged(result)

    def test_ctc_alignment_does_not_redirect_original_audio_targets(self):
        runtime = Path(self.root)/'align-runtime'; runtime.mkdir()
        (runtime/'ctcalign.py').write_text('''
def align_segments(audio, segments, folder, progress=None):
    out = []
    for segment in segments:
        row = dict(segment)
        row['words'] = [dict(w, start=w['start']+.05, end=w['end']-.05, score=.98)
                        for w in segment['words']]
        out.append(row)
    return out, sum(len(s['words']) for s in out), 0
''')
        aligner = Path(self.root)/'aligner'; aligner.mkdir()
        (aligner/'model.int8.onnx').write_bytes(b'offline fixture')
        env = self.gs.worker_env(); env['PYTHONPATH'] = str(runtime)+os.pathsep+env['PYTHONPATH']
        with mock.patch.object(self.gs,'worker_env',return_value=env), \
             mock.patch.object(self.gs,'aligner_ready',return_value=True), \
             mock.patch.object(self.gs,'aligner_path',return_value=str(aligner)):
            token, result = self.ready()
        self.assertEqual(result['words']['source'], 'aligner')
        atom = self.before_tape['atoms'][1]
        self.assertEqual((atom['start'],atom['end']), (1.05,1.95))
        target = self.calls[0]['targets'][0]
        self.assertEqual((target['start'],target['end']), (1.,2.))
        self.assertEqual(asrcorrection.index(result['review']['evidence'])['s0w1']['asr_confidence'], .2)
        self.assert_source_unchanged(result)

    def test_missing_raw_timestamp_is_unavailable_and_other_words_continue(self):
        derive = sttjobs._derive_phonetic
        def missing(job):
            raw = job['whisper_source']['segments'][0]['asr_words'][1]
            raw['start'] = None
            return derive(job)
        with mock.patch.object(sttjobs,'_derive_phonetic',side_effect=missing):
            token, result = self.ready()
        self.assertEqual([t['word_id'] for t in self.calls[0]['targets']], ['s0w3'])
        words = asrcorrection.index(result['review']['evidence'])
        self.assertEqual(words['s0w1']['phonetic']['state'], 'unavailable')
        self.assertEqual(words['s0w3']['phonetic']['state'], 'complete')
        self.assertEqual(words['s0w1']['start'], 1.)
        self.assertEqual(result['review']['evidence']['phonetic']['failed'], 1)
        self.assert_source_unchanged(result)

    def test_pending_ipa_survives_restart_without_rerunning_recognizer(self):
        token, result = self.ready()
        self.until(lambda:not sttjobs.CHILDREN,'Whisper runner cleanup')
        before = copy.deepcopy(result['review']['evidence'])
        sttjobs.stop_all(); sttjobs.JOBS.clear()
        restored = sttjobs.result(token)
        self.assertEqual(restored['review']['evidence'], before)
        self.assertEqual(len(self.calls), 1)

    def test_stage_prevents_done_until_ipa_finishes_and_preference_is_snapshotted(self):
        entered, finish = threading.Event(), threading.Event()
        def paused(*args, **kwargs):
            entered.set(); self.assertTrue(finish.wait(3))
            return self.runner(*args, **kwargs)
        with mock.patch.object(phonetic, 'run', side_effect=paused):
            token = self.start_film(lang='it', seconds=4)['job']
            self.assertTrue(entered.wait(3))
            speechconfig.save({'phonetic_enabled':False})
            state = sttjobs.status(token)
            self.assertEqual(state['state'], sttjobs.PHONETIC)
            self.assertEqual(state['phonetic']['done'], 0)
            self.assertEqual(state['phonetic']['total'], 2)
            self.assertTrue(sttjobs.busy())
            with self.assertRaises(sttjobs.Refusal): sttjobs.result(token)
            finish.set()
            self.assertEqual(self.done(token)['state'], 'done')
        self.assertEqual(len(self.calls), 1)

    def test_cancel_discards_staged_ipa_and_never_completes(self):
        entered = threading.Event()
        def paused(source, kind, targets, processing='auto', **callbacks):
            callbacks['on_word'](self.evidence(targets[0]))
            entered.set()
            self.assertTrue(callbacks['cancel'].wait(3))
            return {'words':[self.evidence(t) for t in targets], 'revision':'fake', 'device':'cpu'}
        with mock.patch.object(phonetic, 'run', side_effect=paused):
            token = self.start_film(lang='it', seconds=4)['job']
            self.assertTrue(entered.wait(3))
            job = sttjobs.JOBS[token]
            sttjobs.cancel(token)
            self.assertEqual(self.done(token)['state'], 'cancelled')
            self.until(lambda: 'phonetic_cancel' not in job, 'IPA cancellation cleanup')
            self.assertFalse(any('phonetic' in w for w in asrcorrection.index(job['review_evidence']).values()))
            self.assertFalse(asrpending.path(token).exists())

    def test_stale_film_discards_every_staged_word(self):
        def changed(source, kind, targets, processing='auto', **callbacks):
            callbacks['on_word'](self.evidence(targets[0]))
            with Path(source).open('ab') as file: file.write(b'changed')
            self.assertFalse(callbacks['source_check']())
            return {'words':[self.evidence(t) for t in targets], 'revision':'fake', 'device':'cpu'}
        with mock.patch.object(phonetic, 'run', side_effect=changed):
            token = self.start_film(lang='it', seconds=4)['job']
            self.assertEqual(self.done(token)['state'], 'failed')
        job = sttjobs.JOBS[token]
        self.assertEqual(job['error']['code'], 'film-changed')
        self.assertFalse(any('phonetic' in w for w in asrcorrection.index(job['review_evidence']).values()))
        with self.assertRaises(sttjobs.Refusal): sttjobs.result(token)

    def test_youtube_uses_original_audio_clock_and_private_retained_capture(self):
        self.fake(segments=[[10.3,11.7,' stall'],[13,14.6,' loro anno detto']],
                  word_evidence={'anno':{'score':.2}})
        token = self.start_yt(lang='it')['job']
        sttjobs.marks(token, [[4000*i,100+i/4-.4-(2 if i/4 >=12 else 0)] for i in range(81) if not 10 <=i/4<12])
        sttjobs.audio(token,0,stt_fakes.pcm(20),True)
        self.assertEqual(self.done(token)['state'], 'done')
        result = sttjobs.result(token)
        self.assertEqual(self.calls[0]['kind'], 'pcm16')
        self.assertEqual(self.calls[0]['source'], str(asrpending.audio_path(token)))
        self.assertTrue(Path(self.calls[0]['source']).is_file())
        words = asrcorrection.index(result['review']['evidence'])
        self.assertEqual((words['s0w1']['start'],words['s0w1']['end']), (111.133,111.667))
        target = self.calls[0]['targets'][0]
        self.assertEqual((target['word_id'],target['start'],target['end']), ('s0w1',13.533,14.067))
        self.assert_source_unchanged(result)


class WorkspaceIPA(unittest.TestCase):
    def request(self):
        text = 'Their anno is unusual.'
        request = asrcorrection.evidence([{'text':text,'start':0,'end':4,'words':[
            {'text':word,'start':i,'end':i+.5,'score':.2 if word=='anno' else .9}
            for i,word in enumerate(text.split())]}],text,'it')
        word = asrcorrection.index(request)['s0w1']
        word['phonetic'] = {'state':'complete','ipa':'tʰɾɑ̃','phones':'tʰ/ɾ/ɑ̃',
            'attribution':'context-crop','target_start':62.75,'target_end':62.89,
            'audio_start':62.25,'audio_end':63.39,'model_revision':'source-pin'}
        return request

    def test_csv_preserves_context_ipa_and_original_audio_bounds(self):
        request = self.request(); before = copy.deepcopy(request)
        _, rows, _, _, _ = asrworkspace._files(request)
        self.assertEqual(rows[0]['heard_ipa'], 'tʰɾɑ̃')
        self.assertEqual(rows[0]['ipa_attribution'], 'context-crop')
        self.assertEqual(rows[0]['ipa_target_start'], 62.75)
        self.assertEqual(rows[0]['ipa_audio_start'], 62.25)
        self.assertEqual(request, before)
        units = asrexternal.batches(request, 'workspace')[0]
        files = asrexternal.workspace_files(request, units)
        result = list(csv.DictReader(io.StringIO(files['input/suspects.csv'])))[0]
        self.assertEqual(result['heard_ipa'], 'tʰɾɑ̃')
        self.assertEqual(float(result['ipa_audio_end']), 63.39)
        self.assertIn('not\nan exact alignment', files['SKILL.md'])
        self.assertIn('Original audio crop', files['review.py'])
        prompt = asrexternal.prompt(request, 'workspace', units)
        self.assertIn('Treat it as uncertain supporting evidence.', prompt)
        self.assertIn('ipa_attribution', prompt)

    def test_failed_or_absent_ipa_is_not_inferred_from_guess(self):
        for state in ('failed', 'unavailable'):
            request = self.request()
            asrcorrection.index(request)['s0w1']['phonetic']['state'] = state
            row = asrworkspace._files(request)[1][0]
            self.assertEqual(row['heard_ipa'], '')
            self.assertEqual(row['ipa_audio_start'], '')
            self.assertEqual(row['ipa_state'], state)
        request = self.request(); asrcorrection.index(request)['s0w1'].pop('phonetic')
        row = asrworkspace._files(request)[1][0]
        self.assertEqual(row['ipa_state'], 'unavailable')
        self.assertEqual(row['heard_ipa'], '')


if __name__ == '__main__':
    unittest.main()
