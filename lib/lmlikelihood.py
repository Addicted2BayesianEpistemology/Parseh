# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded isolated worker lifecycle and immutable ASR target mapping."""
import atexit
import json
import math
import os
from pathlib import Path
import queue
import signal
import subprocess
import threading
import time

from lmgguf import ScoringError, revalidate
from lmlikelihoodcore import candidates, replacement

WORKER = Path(__file__).resolve().with_name('lmlikelihoodworker.py')
MAX_LINE = 4 << 20
MAX_REVIEW_BYTES = 4 << 20
LIVE = set()
LOCK = threading.RLock()


def loaded_count():
    with LOCK:
        return len(LIVE)


def unload_all():
    with LOCK:
        sessions = list(LIVE)
    for session in sessions:
        session.close()


atexit.register(unload_all)


class Session:
    def __init__(self, config, check):
        self.config, self.check, self.closed, self.process = config, check, False, None
        self.messages = queue.Queue(maxsize=2)
        revalidate(config['model'])
        check()
        try:
            self.process = subprocess.Popen([config['python'], '-I', '-u', str(WORKER)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                start_new_session=os.name != 'nt')
        except OSError:
            raise ScoringError('runtime-missing', 'The isolated scoring interpreter could not start. Install or configure it on this host.')
        with LOCK:
            LIVE.add(self)
        threading.Thread(target=self._read, daemon=True, name='likelihood-protocol').start()
        try:
            loaded = self.request({'op': 'load', 'config': config}, config['load_seconds'])
            if loaded.get('op') != 'loaded':
                raise ScoringError('worker-protocol', 'The scoring worker did not confirm loading the model.')
        except Exception:
            self.close(); raise

    def _read(self):
        try:
            while not self.closed:
                line = self.process.stdout.readline(MAX_LINE + 1)
                if not line or len(line) > MAX_LINE:
                    break
                item = json.loads(line)
                self.messages.put(item, timeout=1)
        except Exception:
            pass
        try:
            self.messages.put(None, timeout=1)
        except queue.Full:
            pass

    def request(self, body, seconds):
        self.check()
        if self.closed:
            raise ScoringError('worker-unloaded', 'The scoring worker was unloaded. Choose review again.')
        raw = json.dumps(body, ensure_ascii=True, allow_nan=False).encode() + b'\n'
        if len(raw) > MAX_LINE:
            raise ScoringError('request-size', 'This target has more mandatory evidence than the bounded worker input can hold. Coverage is incomplete.')
        try:
            self.process.stdin.write(raw); self.process.stdin.flush()
        except (OSError, ValueError):
            raise ScoringError('worker-failed', 'The scoring worker stopped unexpectedly. Check resources and model compatibility.')
        end = time.monotonic() + seconds
        while True:
            if self.closed:
                raise ScoringError('worker-unloaded', 'The scoring worker was unloaded. Choose review again.')
            try:
                self.check()
            except Exception:
                self.close(); raise
            if time.monotonic() >= end:
                self.close()
                raise ScoringError('worker-timeout', 'The scoring worker exceeded its time limit and was unloaded. This target is incomplete; other targets may continue.')
            try:
                out = self.messages.get(timeout=.1)
            except queue.Empty:
                continue
            if out is None:
                self.close()
                raise ScoringError('worker-failed', 'The scoring worker stopped unexpectedly. It may have insufficient memory or an unsupported model.')
            if out.get('op') == 'error':
                raise ScoringError(out.get('code', 'worker-failed'), out.get('error', 'Scoring failed.'))
            return out

    def close(self):
        if self.closed:
            return
        self.closed = True
        with LOCK:
            LIVE.discard(self)
        p = self.process
        if p is None:
            return
        if p.poll() is None:
            # Kill even while native model load/decode blocks; no HTTP or GPU
            # lock belonging to Whisper or another application is involved.
            try:
                if os.name == 'nt':
                    p.kill()
                else:
                    os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
        try:
            p.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        for stream in (p.stdin, p.stdout):
            if stream:
                stream.close()


def requests(evidence, panel, config, word_ids=None):
    """Bound original text, never an edited draft, around exact source spans."""
    import asrcorrection
    sources = asrcorrection.index(evidence)
    wanted = set(word_ids) if word_ids is not None else {w['word_id'] for w in sources.values() if w['reviewable'] and asrcorrection.suspect(w)}
    if any(ident not in sources or not sources[ident]['reviewable'] or not asrcorrection.suspect(sources[ident]) for ident in wanted):
        raise ScoringError('invalid-target', 'Choose mapped suspect words from the immutable Whisper result.')
    text, mapping, cursor = '', {}, 0
    for seg in evidence['segments']:
        start = panel.find(seg['text'], cursor)
        if start < 0:
            if any(w['word_id'] in wanted for w in seg['words']):
                raise ScoringError('stale-span', 'A source caption no longer matches its immutable Whisper span.')
            continue
        if text:
            text += '\n'
        base = len(text)
        text += seg['text']
        for w in seg['words']:
            if w['word_id'] in wanted:
                a, b = w['span_start'], w['span_end']
                if panel[a:b] != w['text'] or not start <= a < b <= start + len(seg['text']):
                    raise ScoringError('stale-span', 'A word no longer matches its exact original source span.')
                mapping[w['word_id']] = (base + a - start, base + b - start)
        cursor = start + len(seg['text'])
    out = []
    for ident in sources:
        if ident not in wanted:
            continue
        a, b = mapping[ident]
        out.append({'word': sources[ident], 'left': text[max(0, a - config['preceding_chars']):a],
                    'right': text[b:b + config['following_chars']], 'source_sha256': evidence['source_sha256']})
    return out


def failed_target(request, say):
    entries = candidates(request['word'], [])
    for c in entries:
        c.update(error=c['error'] or say, log_likelihood=None, evaluated_tokens=None,
                 delta_original=None, rank=None, applicable=False)
    return {'candidates': entries, 'coverage': {'state': 'failed', 'mandatory_total': len(entries),
            'mandatory_scored': 0, 'omitted': [{'text': c['text'], 'origins': c['origins'], 'reason': c['error']} for c in entries]},
            'original_log_likelihood': None, 'tied_best': [], 'winner_scope': 'evaluated candidates only',
            'elapsed_seconds': 0, 'error': say}


def proposal(request, data, model):
    """Validate worker output again before entering the exact-span apply flow."""
    w = request['word']
    mandatory = candidates(w, [])
    actual = data.get('candidates')
    if not isinstance(actual, list) or len(actual) > len(mandatory) + 64:
        raise ScoringError('worker-protocol', 'The scoring worker returned invalid candidate coverage.')
    by_text = {}
    for c in actual:
        if not isinstance(c, dict) or not isinstance(c.get('text'), str) or c['text'] in by_text:
            raise ScoringError('worker-protocol', 'The scoring worker returned ambiguous candidates.')
        by_text[c['text']] = c
        score = c.get('log_likelihood')
        if score is not None:
            if (type(score) not in (int, float) or not math.isfinite(score) or score > 1e-8
                    or type(c.get('evaluated_tokens')) is not int or c['evaluated_tokens'] < 0
                    or replacement(w['text'], c['text']) != c['text']):
                raise ScoringError('worker-protocol', 'A scored candidate has invalid numbers or changes source punctuation.')
        c['applicable'] = score is not None
        # Preserve mandatory provenance from source, never trust it to a worker.
        known = next((x for x in mandatory if x['text'] == c['text'] and x['error'] is None), None)
        c['origins'] = known['origins'] + ([{'kind': 'lm-beam'}] if any(o.get('kind') == 'lm-beam' for o in c.get('origins', [])) else []) if known else c.get('origins', [])
        c['confidence'] = None
    if any(c['text'] not in by_text for c in mandatory):
        raise ScoringError('worker-protocol', 'The scoring worker omitted a mandatory Whisper candidate from its coverage ledger.')
    original_score = by_text[w['text']].get('log_likelihood')
    data['original_log_likelihood'] = original_score
    ranked = sorted((c for c in actual if c['log_likelihood'] is not None), key=lambda c: (-c['log_likelihood'], c['text']))
    rank, anchor = 0, None
    for i, c in enumerate(ranked):
        if anchor is None or abs(c['log_likelihood'] - anchor) > 1e-9:
            rank, anchor = i + 1, c['log_likelihood']
        c['rank'] = rank
        c['delta_original'] = c['log_likelihood'] - original_score if original_score is not None else None
    for c in actual:
        if c['log_likelihood'] is None:
            c.update(rank=None, delta_original=None, evaluated_tokens=None,
                     error=c.get('error') or 'The worker did not supply a finite complete likelihood for this candidate.')
    actual[:] = ranked + [c for c in actual if c['log_likelihood'] is None]
    data['tied_best'] = [c['text'] for c in ranked if c['rank'] == 1]
    missing = [c for c in mandatory if by_text[c['text']].get('log_likelihood') is None]
    state = 'partial' if missing and any(c['applicable'] for c in actual) else 'failed' if missing else 'complete'
    data['coverage'] = {'state': state, 'mandatory_total': len(mandatory), 'mandatory_scored': len(mandatory) - len(missing),
                        'omitted': [{'text': c['text'], 'origins': c['origins'], 'reason': by_text[c['text']].get('error')} for c in missing]}
    data['winner_scope'] = 'full candidate set' if all(c['applicable'] for c in actual) else 'evaluated candidates only'
    data['model'] = model['model_id']
    if model.get('identity'):
        data['model_identity'] = {'source': model.get('source'), 'architecture': model.get('architecture'),
                                  'bytes': model['identity']['size'], 'header_sha256': model['identity']['header_sha256'],
                                  'runtime_version': '0.3.35'}
    return dict(asr_word=w['text'], word_id=w['word_id'], segment_id=w['segment_id'], original=w['text'],
                span_start=w['span_start'], span_end=w['span_end'], start=w.get('start'), end=w.get('end'),
                asr_confidence=w.get('asr_confidence'), asr_alternatives=w.get('asr_alternatives', []),
                error_likelihood=None, candidates=actual, reason='Experimental raw language-model likelihood; this is not acoustic evidence or calibrated correctness.',
                likelihood={k: v for k, v in data.items() if k != 'candidates'})


def correct(evidence, panel, config, check, progress, diagnostic, word_ids=None):
    targets = requests(evidence, panel, config, word_ids)
    result = {'schema_version': 1, 'task': 'likelihood', 'suggestions': [], 'failed_word_ids': [],
              'uncertain_word_ids': [], 'reviewed_word_ids': [], 'assessment': 'numerical-evaluation',
              'source_sha256': evidence['source_sha256'], 'complete': True, 'model': config['model']['model_id'],
              'storage_failed_word_ids': []}
    progress(0, len(targets), 'loading likelihood model')
    session, kept = None, 0
    try:
        if targets:
            session = Session(config, check)
        for i, req in enumerate(targets):
            check(); revalidate(config['model'])
            progress(i, len(targets), 'searching candidates and scoring supplied text')
            try:
                if session is None or session.closed:
                    session = Session(config, check)
                packet = session.request({'op': 'target', 'request': req}, config['target_seconds'] + 30)
                if packet.get('op') != 'target':
                    raise ScoringError('worker-protocol', 'The scoring worker returned an unexpected message.')
                data = packet['result']
                proposed = proposal(req, data, config['model'])
            except Exception as e:
                if isinstance(e, ScoringError) and e.code in ('source-changed', 'settings-changed', 'model-changed', 'cancelled', 'worker-unloaded'):
                    raise
                # Recheck cancellation/source before classifying a malformed
                # worker packet as a local target failure.
                check()
                data = failed_target(req, e.say if isinstance(e, ScoringError) else 'The worker returned invalid numerical results for this target.')
                proposed = proposal(req, data, config['model'])
            check()
            ident = req['word']['word_id']
            size = len(json.dumps(proposed, ensure_ascii=True).encode())
            if kept + size > MAX_REVIEW_BYTES:
                # Never call a storage-clipped target complete. Source evidence
                # still holds ALL alternatives; it can be retried separately.
                data = failed_target(req, 'Candidate diagnostics exceed the bounded review storage. Retry this target separately.')
                proposed = proposal(req, data, config['model'])
                failure_size = len(json.dumps(proposed, ensure_ascii=True).encode())
                if kept + failure_size <= MAX_REVIEW_BYTES:
                    result['suggestions'].append(proposed)
                    kept += failure_size
                else:
                    result['storage_failed_word_ids'].append(ident)
                result['failed_word_ids'].append(ident)
            else:
                result['suggestions'].append(proposed); kept += size
                if proposed['likelihood']['coverage']['state'] != 'complete':
                    result['failed_word_ids'].append(ident)
            result['reviewed_word_ids'].append(ident)
            diagnostic({'kind': 'likelihood', 'sentence_id': ident, 'word_ids': [ident],
                        'state': proposed['likelihood']['coverage']['state'], 'elapsed_seconds': data.get('elapsed_seconds'),
                        'scores': proposed})
            progress(i + 1, len(targets), 'scoring supplied text')
        result['complete'] = not result['failed_word_ids']
        return result
    finally:
        if session:
            session.close()
