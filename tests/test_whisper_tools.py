# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional/later Whisper tools against the real worker with fake model/audio."""
import copy
import json
from pathlib import Path
import sys
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for rel in ('tests', 'lib', 'youtube/lib'):
    sys.path.insert(0, str(ROOT / rel))
import asrcorrection
import asrdictionary
import asrpending
import speechconfig
import sttjobs
import stt_fakes
import wordtimes
from test_stt_jobs import Base


class Preferences(unittest.TestCase):
    def test_cancelled_capture_is_not_retained_after_discard(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td, mock.patch.object(asrpending, 'folder', return_value=Path(td)/'pending'):
            audio = Path(td)/'capture.pcm'
            audio.write_bytes(b'captured sound')
            job = {'id':'0123456789abcdef', 'kind':'youtube', 'pcm':str(audio), 'cancelled':True}
            asrpending.remove(job['id'])
            asrpending.retain_audio(job)
            self.assertFalse(asrpending.audio_path(job['id']).exists())

    def test_versioned_boolean_roundtrip_and_malformed_fallback(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td, mock.patch.object(speechconfig, 'CONFIG', Path(td) / 'speech.json'):
            self.assertTrue(speechconfig.load()['second_pass'])
            speechconfig.save({'second_pass':False})
            self.assertFalse(speechconfig.load()['second_pass'])
            for bad in ({'second_pass':1}, {'second_pass':False, 'model':'other'}, {}):
                with self.assertRaises(ValueError):
                    speechconfig.save(bad)
            speechconfig.CONFIG.write_text('{broken')
            self.assertTrue(speechconfig.load()['second_pass'])


class Tools(Base):
    def setUp(self):
        super().setUp()
        speechconfig.save({'second_pass':False})
        p = mock.patch.object(asrdictionary.Resolver, 'word', side_effect=lambda text, *args:
                              {'state':'missing' if text == 'strano' else 'found', 'words':[]})
        p.start(); self.addCleanup(p.stop)
        self.fake(segments=[[0,4,' loro anno detto strano']],
                  word_evidence={'anno':{'score':.2, 'alternatives':[{'text':'existing'+str(i), 'score':None} for i in range(12)]}},
                  second_pass=[{'segments':[[0,4,' loro hanno detto strano']]},
                               {'segments':[[0,4,' loro anno detto strana']]}])

    def ready(self, youtube=False):
        if youtube:
            token = self.start_yt(lang='it', duration=4)['job']
            sttjobs.audio(token, 0, stt_fakes.pcm(4), last=True)
        else:
            token = self.start_film(lang='it', seconds=4)['job']
        self.assertEqual(self.done(token)['state'], 'done')
        result = sttjobs.result(token)
        return token, result, result['review']['evidence']['source_sha256']

    def recheck(self, token, sha, ids=None):
        sttjobs.review_whisper_second(token, sha, ids)
        self.assertEqual(self.done(token)['state'], 'done')
        return sttjobs.result(token)

    def test_disabled_pass_opens_usable_review_and_use_needs_no_method_choice(self):
        token, result, sha = self.ready()
        self.assertEqual(len(self.records('transcribe')), 1)
        self.assertIsNone(result['review']['choice'])
        self.assertTrue(result['review']['second_pass_available'])
        applied = sttjobs.use_review(token, sha, {}, {'s0w1':'hanno'})
        self.assertIn('loro hanno detto strano', applied['text'])
        self.assertEqual(sttjobs.JOBS[token]['text'], result['text'])

    def test_later_pass_covers_fixed_suspects_and_preserves_evidence_timings_and_draft(self):
        token, result, sha = self.ready()
        before = copy.deepcopy(result)
        tape = wordtimes.load(token)
        draft = {'manual_edits':{'s0w0':'Loro'}, 'locked_word_ids':['s0w0']}
        sttjobs.save_review_draft(token, sha, draft)
        after = self.recheck(token, sha)
        self.assertEqual(after['text'], before['text'])
        self.assertEqual(wordtimes.load(token), tape)
        self.assertEqual(after['review']['draft'], draft)
        words = asrcorrection.index(after['review']['evidence'])
        for ident, w in asrcorrection.index(before['review']['evidence']).items():
            self.assertEqual([words[ident][k] for k in ('text','start','end','asr_confidence','span_start','span_end')],
                             [w[k] for k in ('text','start','end','asr_confidence','span_start','span_end')])
        self.assertIn('hanno', [a['text'] for a in words['s0w1']['asr_alternatives']])
        self.assertTrue(all('existing'+str(i) in [a['text'] for a in words['s0w1']['asr_alternatives']] for i in range(12)))
        self.assertIn('strana', [a['text'] for a in words['s0w3']['asr_alternatives']])
        self.assertEqual(after['review']['evidence']['second_pass']['total'], 2)
        self.assertEqual(len(self.records('construct')), 2, 'one shared model for the later batch')
        self.assertEqual([r['beam_size'] for r in self.records('transcribe')], [5,10,10])

    def test_single_word_allows_non_suspects_but_excludes_locked_words(self):
        token, result, sha = self.ready()
        after = self.recheck(token, sha, ['s0w0'])
        self.assertEqual(after['review']['evidence']['second_pass']['total'], 1)
        sttjobs.save_review_draft(token, sha, {'locked_word_ids':['s0w1']})
        with self.assertRaisesRegex(sttjobs.Refusal, 'Unlock'):
            sttjobs.review_whisper_second(token, sha, ['s0w1'])

    def test_later_pass_survives_restart_and_youtube_audio_is_private_then_removed(self):
        token, result, sha = self.ready(youtube=True)
        audio = asrpending.audio_path(token)
        self.assertTrue(audio.is_file())
        sttjobs.stop_all(); sttjobs.JOBS.clear()
        restored = sttjobs.result(token)
        self.assertTrue(restored['review']['second_pass_available'])
        after = self.recheck(token, sha, ['s0w1'])
        self.assertIn('hanno', [a['text'] for a in asrcorrection.index(after['review']['evidence'])['s0w1']['asr_alternatives']])
        sttjobs.use_review(token, sha, {})
        self.assertFalse(audio.exists())

    def test_cancel_later_pass_preserves_prior_results_and_releases_slot(self):
        token, result, sha = self.ready()
        self.fake(segments=[[0,4,' loro anno detto strano']], second_pass=[{'segments':[[0,4,' loro hanno detto strano']], 'delay':3}])
        previous = {'schema_version':1, 'suggestions':[], 'task':'suspect'}
        sttjobs.JOBS[token]['correction_result'] = previous
        sttjobs.review_whisper_second(token, sha, ['s0w1'])
        self.until(lambda: len(self.records('transcribe')) >= 2, 'crop decoding')
        sttjobs.cancel_review(token)
        self.assertEqual(sttjobs.status(token)['state'], 'done')
        self.assertFalse(sttjobs.busy())
        self.assertEqual(sttjobs.result(token)['review']['result'], previous)
        time.sleep(.1)
        self.assertNotIn('hanno', [a['text'] for a in asrcorrection.index(sttjobs.result(token)['review']['evidence'])['s0w1']['asr_alternatives']])

    def test_individual_failure_continues_other_targets(self):
        token, result, sha = self.ready()
        self.fake(segments=[[0,4,' loro anno detto strano']], second_pass=[{'second_error':True}, {'segments':[[0,4,' loro anno detto strana']]}])
        after = self.recheck(token, sha)
        self.assertEqual(after['review']['evidence']['second_pass']['failed'], 1)
        self.assertIn('strana', [a['text'] for a in asrcorrection.index(after['review']['evidence'])['s0w3']['asr_alternatives']])

    def test_unexpected_worker_start_failure_leaves_draft_usable_and_releases_slot(self):
        token, result, sha = self.ready()
        with mock.patch.object(sttjobs, '_spawn', side_effect=RuntimeError('worker could not start')):
            after = self.recheck(token, sha, ['s0w1'])
        self.assertEqual(after['text'], result['text'])
        self.assertEqual(after['review']['evidence']['second_pass']['failed'], 1)
        self.assertEqual(asrcorrection.index(after['review']['evidence'])['s0w1']['second_pass']['reason'], 'worker-stopped')
        self.assertFalse(sttjobs.busy())
        self.assertIn('hanno', sttjobs.use_review(token, sha, {}, {'s0w1':'hanno'})['text'])

    def test_stale_hash_source_and_unknown_words_are_rejected(self):
        token, result, sha = self.ready()
        for digest, ids in [('bad',['s0w1']), (sha,['s99w0'])]:
            with self.assertRaises(sttjobs.Refusal): sttjobs.review_whisper_second(token,digest,ids)
        Path(sttjobs.JOBS[token]['source']['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(sttjobs.Refusal,'changed'): sttjobs.review_whisper_second(token,sha,['s0w1'])

    def test_source_change_during_crop_discards_inflight_candidates(self):
        token, result, sha = self.ready()
        self.fake(segments=[[0,4,' loro anno detto strano']], second_pass=[{'segments':[[0,4,' loro hanno detto strano']], 'delay':.3}])
        sttjobs.review_whisper_second(token, sha, ['s0w1'])
        self.until(lambda: len(self.records('transcribe')) >= 2, 'crop decoding')
        with Path(sttjobs.JOBS[token]['source']['path']).open('ab') as f: f.write(b'changed')
        after = self.done(token)
        self.assertEqual(after['state'], 'done')
        review = sttjobs.result(token)['review']
        self.assertEqual(review['correction']['code'], 'source-changed')
        self.assertNotIn('hanno', [a['text'] for a in asrcorrection.index(review['evidence'])['s0w1']['asr_alternatives']])


if __name__ == '__main__':
    unittest.main()
