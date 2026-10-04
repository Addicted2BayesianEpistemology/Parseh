# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded PhoneticXeus child lifecycle; safe source mapping and cancellation."""
import json
import math
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time

import download
import getphonetic
from phoneticpins import MODEL

MAX_LINE = 65536
LOAD_SECONDS = 300
TARGET_SECONDS = 120
MAX_TEXT = 4000


class SourceChanged(getphonetic.PhoneticError):
    def __init__(self):
        super().__init__('source-changed', 'The transcript source changed. Heard-IPA results were discarded.')


def _check(cancel, source_check):
    if cancel is not None:
        if hasattr(cancel, 'check'):
            cancel.check()
        download.check(getattr(cancel, 'event', cancel))
    if source_check is not None and source_check() is False:
        raise SourceChanged()


def validate_word(item, targets):
    ident, evidence = item.get('word_id'), item.get('phonetic')
    if ident not in targets or not isinstance(evidence, dict):
        raise getphonetic.PhoneticError('worker-protocol', 'The heard-IPA worker returned an invalid source word.')
    if evidence.get('state') not in ('complete', 'failed') or evidence.get('model_revision') != MODEL['revision']:
        raise getphonetic.PhoneticError('worker-protocol', 'The heard-IPA worker returned invalid evidence.')
    if evidence['state'] == 'complete':
        for name in ('ipa', 'phones'):
            value = evidence.get(name)
            if (not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXT
                    or any(ord(c) < 32 for c in value)):
                raise getphonetic.PhoneticError('worker-protocol', 'The heard-IPA worker returned invalid text.')
        a, b = evidence.get('audio_start'), evidence.get('audio_end')
        if (isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, (int, float))
                or not isinstance(b, (int, float)) or not math.isfinite(a) or not math.isfinite(b)
                or a < 0 or b <= a or evidence.get('attribution') != 'context-crop'
                or a > targets[ident]['start'] or b < targets[ident]['end']):
            raise getphonetic.PhoneticError('worker-protocol', 'The heard-IPA crop does not cover its source word.')
        for name in ('start', 'end'):
            if 'target_' + name in evidence and evidence['target_' + name] != targets[ident][name]:
                raise getphonetic.PhoneticError('worker-protocol', 'The heard-IPA target no longer matches its source timestamp.')
    else:
        if not isinstance(evidence.get('reason'), str) or len(evidence['reason']) > 400:
            raise getphonetic.PhoneticError('worker-protocol', 'The heard-IPA worker returned an invalid error.')
    return {'word_id': ident, 'phonetic': evidence}


def run(source_path, audio_kind, targets, processing='auto', *, cancel=None,
        progress=None, on_word=None, source_check=None):
    """Estimate IPA for original timestamp crops, reusing one loaded model.

    Result events are tied to supplied immutable IDs.  Cancellation/source
    changes raise and kill native loading/inference, leaving publication to the
    caller's generation guard.  Per-word errors are retained locally.  Ordinary
    logs never receive transcripts, source paths, phones or model exceptions.
    """
    _check(cancel, source_check)
    if not getphonetic.runtime_ready() or not getphonetic.model_ready():
        raise getphonetic.PhoneticError('not-installed', 'Install the separate PhoneticXeus program and model in Speech to text Settings.')
    if processing not in ('auto', 'cpu', 'cuda') or audio_kind not in ('pcm16', 'media'):
        raise getphonetic.PhoneticError('bad-spec', 'Choose valid audio and processing settings for heard IPA.')
    source = Path(source_path)
    if not source.is_absolute() or not source.is_file():
        raise getphonetic.PhoneticError('source-gone', 'The original recording is no longer available for heard IPA.')
    if (not isinstance(targets, list) or len(targets) > 200000
            or any(not isinstance(t, dict) or set(t) != {'word_id', 'start', 'end'}
                   or not isinstance(t['word_id'], str)
                   or not re.fullmatch(r's[0-9]+w[0-9]+', t['word_id']) for t in targets)):
        raise getphonetic.PhoneticError('bad-spec', 'Heard IPA accepts only source word IDs and original audio timestamps.')
    target_map = {t['word_id']: t for t in targets}
    if len(target_map) != len(targets):
        raise getphonetic.PhoneticError('bad-spec', 'The heard-IPA target list contains duplicate words.')
    total = len(targets)
    if not total:
        return {'state': 'complete', 'completed': 0, 'total': 0, 'failed': 0,
                'revision': MODEL['revision'], 'device': 'cpu', 'words': []}
    if progress:
        progress(0, total)
    private = getphonetic.DIRECTORY / 'tmp'
    private.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix='ipa-', suffix='.json', dir=private)
    proc = None
    messages = queue.Queue(maxsize=4)
    closed = threading.Event()
    words, seen, done, failure = [], set(), 0, None
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump({'source_path': str(source), 'audio_kind': audio_kind, 'targets': targets,
                       'processing': processing, 'model_path': str(getphonetic.model_dir())}, f, allow_nan=False)
        with getphonetic.using():
            proc = subprocess.Popen([sys.executable, '-s', '-u', str(getphonetic.WORKER), name],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                env=getphonetic.worker_env(), start_new_session=os.name != 'nt')
            getphonetic.track(proc)

            def reader():
                try:
                    while not closed.is_set():
                        raw = proc.stdout.readline(MAX_LINE + 1)
                        if not raw:
                            break
                        if len(raw) > MAX_LINE:
                            break
                        item = json.loads(raw)
                        while not closed.is_set():
                            try:
                                messages.put(item, timeout=.1)
                                break
                            except queue.Full:
                                pass
                except (OSError, ValueError):
                    pass
                finally:
                    while not closed.is_set():
                        try:
                            messages.put(None, timeout=.1)
                            break
                        except queue.Full:
                            pass

            thread = threading.Thread(target=reader, name='heard-ipa-protocol', daemon=True)
            thread.start()
            deadline = time.monotonic() + LOAD_SECONDS
            while True:
                _check(cancel, source_check)
                if time.monotonic() >= deadline:
                    failure = 'Heard IPA exceeded its time limit. Other transcript review tools remain available.'
                    break
                try:
                    item = messages.get(timeout=.1)
                except queue.Empty:
                    continue
                if item is None:
                    failure = 'The heard-IPA worker stopped before all words were processed.'
                    break
                if not isinstance(item, dict):
                    raise getphonetic.PhoneticError('worker-protocol', 'The heard-IPA worker returned an invalid message.')
                if item.get('event') == 'word':
                    value = validate_word(item, target_map)
                    if value['word_id'] in seen:
                        raise getphonetic.PhoneticError('worker-protocol', 'The heard-IPA worker repeated a source word.')
                    _check(cancel, source_check)
                    seen.add(value['word_id'])
                    words.append(value)
                    done += 1
                    if on_word:
                        on_word(value)
                    if progress:
                        progress(done, total)
                    deadline = time.monotonic() + TARGET_SECONDS
                elif item.get('event') == 'error':
                    # Only known canned categories cross this boundary; raw
                    # exception strings never become application/job output.
                    from phoneticworker import SAYS
                    failure = SAYS.get(item.get('code'), SAYS['word-failed'])
                    break
                elif item.get('event') == 'done':
                    if done != total or item.get('completed') != total or item.get('total') != total:
                        failure = 'Heard-IPA processing finished with incomplete word coverage.'
                    break
            _check(cancel, source_check)
    finally:
        closed.set()
        if proc is not None:
            getphonetic.terminate(proc)
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            getphonetic.untrack(proc)
            if proc.stdout:
                proc.stdout.close()
        Path(name).unlink(missing_ok=True)
    if failure:
        for ident in target_map:
            if ident not in seen:
                _check(cancel, source_check)
                value = {'word_id': ident, 'phonetic': {'state': 'failed', 'reason': failure,
                        'code': 'worker-incomplete', 'model_revision': MODEL['revision']}}
                words.append(value)
                if on_word:
                    on_word(value)
    _check(cancel, source_check)
    failed = sum(w['phonetic']['state'] != 'complete' for w in words)
    return {'state': ('failed' if failed == total else 'partial') if failed else 'complete',
            'completed': len(words), 'total': total, 'failed': failed,
            'revision': MODEL['revision'], 'device': 'cpu', 'words': words,
            **({'reason': failure} if failure else {})}
