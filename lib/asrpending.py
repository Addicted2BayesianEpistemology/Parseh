# SPDX-License-Identifier: GPL-3.0-or-later
"""Private, atomic, bounded drafts and original capture audio for review tools."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import threading

FORMAT = 1
LIMIT = 16 << 20
TOTAL_LIMIT = 256 << 20
RECORD_LIMIT = 100
TOTAL_AUDIO_LIMIT = 2 << 30
TOKEN = re.compile(r'^[A-Za-z0-9_-]{16}\Z')
LOCK = threading.RLock()
FIELDS = ('id', 'kind', 'source', 'film', 'lang', 'wlang', 'model', 'mode', 'aligner',
          'planned', 'device', 'device_name', 'threads', 'fell_back', 'created', 'touched',
          'started', 'finished', 'have', 'sealed', 'hint', 'marks', 'total', 'done', 'text',
          'notes', 'words', 'facts', 'warning', 'review_evidence', 'review_choice',
          'correction', 'correction_result', 'llm_generation', 'llm_diagnostics',
          'llm_diagnostics_clipped', 'llm_diagnostics_bytes', 'llm_config_fingerprint',
          'likelihood_revision', 'review_draft', 'external_review', 'whisper_source',
          'automatic_second_pass', 'first_suspect_word_ids', 'second_pass',
          'last_method', 'last_word_ids', 'second_pass_previous', 'model_revision')


def folder():
    import ytpages
    return Path(ytpages.VIDEOS) / '.pending-transcriptions'


def path(token):
    if not isinstance(token, str) or not TOKEN.fullmatch(token):
        raise ValueError('Invalid pending transcription token')
    return folder() / (token + '.json')


def audio_path(token):
    return path(token).with_suffix('.pcm')


def retain_audio(job):
    """Keep a captured YouTube recording only until the review is used/discarded."""
    if job['kind'] != 'youtube':
        return
    source = Path(job['pcm'])
    dest = audio_path(job['id'])
    with LOCK:
        if job.get('cancelled'):
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(dest.parent, 0o700)
        size = source.stat().st_size
        if size + sum(p.stat().st_size for p in dest.parent.glob('*.pcm') if p != dest) > TOTAL_AUDIO_LIMIT:
            raise ValueError('Pending review audio storage is full')
        os.chmod(source, 0o600)
        shutil.move(str(source), str(dest))


def _current_audio_evidence(job):
    """Retire removed audio-to-IPA data without changing a saved review draft."""
    job = copy.deepcopy({k: job[k] for k in FIELDS if k in job})

    def clean(value):
        if isinstance(value, dict):
            value.pop('phonetic', None)
            value.pop('automatic_phonetic', None)
            for item in value.values():
                clean(item)
        elif isinstance(value, list):
            for item in value:
                clean(item)

    # Prepared copy/paste prompts may contain the retired CSV evidence as text.
    # Regenerate those sessions with the current format; keep the user's draft.
    external = job.get('external_review')
    if external and any(marker in json.dumps(external, ensure_ascii=False)
                        for marker in ('heard_ipa', 'ipa_attribution', 'ipa_audio_start',
                                       'Heard IPA', 'PhoneticXeus')):
        job.pop('external_review', None)
    clean(job)
    return job


def save(job):
    if not job.get('review_evidence') or job.get('review_used'):
        return
    import wordtimes
    import wavefile
    record = {'format_version': FORMAT, 'job': _current_audio_evidence(job),
              'timings': wordtimes.load(job['id']), 'wave': None}
    wave_path = wavefile.hold_path(job['id'])
    wave = wavefile.read(wave_path) if wave_path and os.path.isfile(wave_path) else None
    if wave:
        record['wave'] = {'rate': wave[0], 'peaks': wave[1]}
    raw = json.dumps(record, ensure_ascii=False, allow_nan=False).encode('utf-8')
    if len(raw) > LIMIT:
        raise ValueError('This pending review is too large to save')
    p = path(job['id'])
    with LOCK:
        p.parent.mkdir(parents=True, exist_ok=True)
        records = list(p.parent.glob('*.json'))
        if p not in records and len(records) >= RECORD_LIMIT:
            raise ValueError('Use or discard a pending transcription before saving another')
        if sum(other.stat().st_size for other in records if other != p) + len(raw) > TOTAL_LIMIT:
            raise ValueError('Pending transcription storage is full')
        os.chmod(p.parent, 0o700)
        tmp = p.with_suffix('.json.tmp')
        with tmp.open('wb') as f:
            os.chmod(tmp, 0o600)
            f.write(raw)
        os.replace(tmp, p)


def load(token):
    p = path(token)
    if p.stat().st_size > LIMIT:
        raise ValueError('Pending review exceeds storage bounds')
    record = json.loads(p.read_text(encoding='utf-8'))
    j = record['job']
    if (record.get('format_version') != FORMAT or j['id'] != token
            or not isinstance(j.get('text'), str) or j.get('kind') not in ('film', 'youtube')
            or hashlib.sha256(j['text'].encode()).hexdigest() != j['review_evidence']['source_sha256']):
        raise ValueError('Pending review is invalid')
    record['job'] = j = _current_audio_evidence(j)
    ext = j.get('external_review')
    if ext:
        for name in ('answers', 'attempts'):
            ext[name] = {int(index): value for index, value in ext.get(name, {}).items()}
    return record


def remove(token):
    with LOCK:
        path(token).unlink(missing_ok=True)
        audio_path(token).unlink(missing_ok=True)


def listing():
    rows = []
    for p in folder().glob('*.json'):
        try:
            j = load(p.stem)['job']
            rows.append({'job': j['id'], 'title': Path(j['source']['path']).name if j['kind'] == 'film' else j['source']['id'],
                         'lang': j['lang'], 'saved': p.stat().st_mtime})
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return sorted(rows, key=lambda r: r['saved'], reverse=True)[:RECORD_LIMIT]
