#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Isolated, offline PhoneticXeus audio crops -> estimated heard IPA.

This child uses only the independently installed pinned runtime.  No transcript,
candidate spelling or language prompt is input to the recognizer.  It loads the
575M-parameter model once, with the fixed self-conditioning layers from the
pinned September 2026 upstream correction, and strictly loads safetensors.
"""
import contextlib
import hashlib
import json
import math
import numbers
import os
from pathlib import Path
import sys
import time

SAMPLE_RATE = 16000
PAD_SECONDS = .5
MAX_TARGETS = 200000
MAX_SPEC = 32 << 20
MAX_TEXT = 4000
SAYS = {
    'bad-spec': 'The heard-IPA job could not be started.',
    'source-gone': 'The source recording is no longer readable.',
    'model-incomplete': 'PhoneticXeus is incomplete or changed. Reinstall its model in Settings.',
    'runtime-missing': 'The separate PhoneticXeus program is unavailable. Install it in Settings.',
    'unsupported-device': 'This PhoneticXeus program uses CPU. Choose Automatic or CPU.',
    'model-load': 'PhoneticXeus could not load. Check available memory and reinstall its model if needed.',
    'no-memory': 'There is not enough memory for PhoneticXeus. Whisper’s transcript is still available.',
    'audio-unreadable': 'The audio around this word could not be read.',
    'empty-audio': 'There is no usable audio at this word’s timestamp.',
    'invalid-timing': 'This word has no usable audio timestamp.',
    'no-phones': 'PhoneticXeus did not detect usable phones in this crop.',
    'word-failed': 'Heard IPA could not be estimated for this word.',
}


class Refused(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def send(value):
    try:
        sys.stdout.write(json.dumps(value, ensure_ascii=True, allow_nan=False) + '\n')
        sys.stdout.flush()
    except (OSError, ValueError):
        os._exit(3)


def finite(value):
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (OverflowError, TypeError, ValueError):
        return None


def read_spec(path):
    p = Path(path)
    try:
        if p.stat().st_size > MAX_SPEC:
            raise Refused('bad-spec')
        value = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise Refused('bad-spec')
    if not isinstance(value, dict) or value.get('audio_kind') not in ('pcm16', 'media'):
        raise Refused('bad-spec')
    for key in ('source_path', 'model_path'):
        if (not isinstance(value.get(key), str) or not value[key] or '\0' in value[key]
                or not Path(value[key]).is_absolute()):
            raise Refused('bad-spec')
    if value.get('processing', 'auto') not in ('auto', 'cpu', 'cuda'):
        raise Refused('bad-spec')
    targets = value.get('targets')
    if not isinstance(targets, list) or len(targets) > MAX_TARGETS:
        raise Refused('bad-spec')
    identities = set()
    import re
    for target in targets:
        if (not isinstance(target, dict) or set(target) != {'word_id', 'start', 'end'}
                or not isinstance(target.get('word_id'), str)
                or not re.fullmatch(r's[0-9]+w[0-9]+', target['word_id'])):
            raise Refused('bad-spec')
        ident = target['word_id']
        if ident in identities:
            raise Refused('bad-spec')
        identities.add(ident)
        start, end = finite(target.get('start')), finite(target.get('end'))
        if start is None or end is None or start < 0 or end <= start or end - start > 20:
            # Invalid timings fail locally, rather than preventing valid targets.
            target['invalid_timing'] = True
        else:
            target['start'], target['end'] = start, end
    return value


def verify_model(folder):
    from phoneticpins import MODEL
    root = Path(folder)
    for name, (sha, size) in MODEL['files'].items():
        p = root / name
        try:
            if p.is_symlink() or not p.is_file() or p.stat().st_size != size:
                raise Refused('model-incomplete')
            h = hashlib.sha256()
            with p.open('rb') as f:
                for block in iter(lambda: f.read(1 << 20), b''):
                    h.update(block)
            if h.hexdigest() != sha:
                raise Refused('model-incomplete')
        except OSError:
            raise Refused('model-incomplete')
    return MODEL


def load_model(folder, processing):
    # These imports happen exclusively in this child process.  Verify source
    # *before* adding the optional checkpoint tree to sys.path.
    if processing == 'cuda':
        raise Refused('unsupported-device')
    pin = verify_model(folder)
    try:
        import torch
        from safetensors.torch import load_file
        sys.path.insert(0, folder)
        from pxeus.model.xeusphoneme.builders import build_xeus_pr_from_hf
    except (ImportError, OSError):
        raise Refused('runtime-missing')
    try:
        root = Path(folder)
        config = json.loads((root / 'config.json').read_text(encoding='utf-8'))
        if (config.get('sampling_rate') != SAMPLE_RATE or config.get('interctc_layer_idx') != [4, 8, 12]
                or config.get('interctc_use_conditioning') is not True):
            raise Refused('model-incomplete')
        # Use the audited builder in its explicit no-download/no-pickle mode.
        # This is equivalent to the upstream AutoModel wrapper's initialization.
        with contextlib.redirect_stdout(sys.stderr):
            model = build_xeus_pr_from_hf(work_dir=folder, hf_repo=None, load_ckpt=False,
                config_file=str(root / config['config_yaml']), vocab_file=str(root / config['vocab_file']),
                interctc_layer_idx=config['interctc_layer_idx'], interctc_use_conditioning=True)
        tensors = load_file(str(root / 'model.safetensors'), device='cpu')
        if not tensors or any(not key.startswith('model.') for key in tensors):
            raise Refused('model-incomplete')
        model.load_state_dict({key[6:]: tensor for key, tensor in tensors.items()}, strict=True)
        del tensors
        model.to(device='cpu', dtype=torch.float32).eval()
        from pxeus.model.xeusphoneme.xeuspr_inference import XeusPRInference
        return XeusPRInference(model, device='cpu', dtype='float32'), pin
    except (MemoryError, RuntimeError) as error:
        if isinstance(error, MemoryError) or 'memory' in str(error).lower():
            raise Refused('no-memory')
        raise Refused('model-load')
    except (OSError, ValueError, KeyError, AssertionError):
        raise Refused('model-load')


def audio_crop(path, kind, start, end):
    """Return exact original 16-kHz audio interval, with a disclosed small pad.

    Media seek/decoding is bounded to this crop.  Frame times are shifted by the
    stream's origin to match Whisper's audio clock; no caption/video remapping
    or replacement word timing is calculated here.
    """
    import numpy as np
    lo, hi = max(0., start - PAD_SECONDS), end + PAD_SECONDS
    first, last = int(round(lo * SAMPLE_RATE)), int(round(hi * SAMPLE_RATE))
    lo, hi = first / SAMPLE_RATE, last / SAMPLE_RATE
    if kind == 'pcm16':
        try:
            count = last - first
            with open(path, 'rb') as f:
                f.seek(first * 2)
                raw = f.read(count * 2)
            audio = np.frombuffer(raw[:len(raw) // 2 * 2], dtype='<i2').astype(np.float32) / 32768.
        except (OSError, ValueError):
            raise Refused('audio-unreadable')
        hi = lo + len(audio) / SAMPLE_RATE
    else:
        import av
        try:
            with av.open(path, metadata_errors='ignore') as container:
                if not container.streams.audio:
                    raise Refused('empty-audio')
                stream = container.streams.audio[0]
                origin = float((stream.start_time or 0) * stream.time_base)
                if lo > 0:
                    container.seek(int(max(0., lo + origin - .5) * av.time_base), backward=True)
                resampler = av.audio.resampler.AudioResampler(format='flt', layout='mono', rate=SAMPLE_RATE)
                samples = np.zeros(max(0, last - first), dtype=np.float32)
                covered = np.zeros(len(samples), dtype=bool)
                clock = 0.

                def collect(resampled, when):
                    stamp = float(resampled.time) - origin if resampled.time is not None else when
                    data = resampled.to_ndarray().reshape(-1)
                    dest = int(round((stamp - lo) * SAMPLE_RATE))
                    a, b = max(0, dest), min(len(samples), dest + len(data))
                    if b > a:
                        samples[a:b] = data[a - dest:b - dest]
                        covered[a:b] = True

                for frame in container.decode(stream):
                    when = float(frame.time) - origin if frame.time is not None else clock
                    clock = when + frame.samples / frame.sample_rate
                    if when > hi + .5:
                        break
                    for resampled in resampler.resample(frame):
                        collect(resampled, when)
                else:
                    for resampled in resampler.resample(None):
                        collect(resampled, clock)
                a = max(0, int(round((start - lo) * SAMPLE_RATE)))
                b = max(a + 1, int(round((end - lo) * SAMPLE_RATE)))
                if b > len(covered) or not covered[a:b].all():
                    raise Refused('empty-audio')
                occupied = np.flatnonzero(covered)
                if len(occupied):
                    begin, finish = int(occupied[0]), int(occupied[-1]) + 1
                    audio = samples[begin:finish]
                    hi = lo + finish / SAMPLE_RATE
                    lo += begin / SAMPLE_RATE
                else:
                    audio = np.empty(0, dtype=np.float32)
        except Refused:
            raise
        except Exception:
            raise Refused('audio-unreadable')
    if len(audio) < int(.08 * SAMPLE_RATE) or hi < end or not np.isfinite(audio).all():
        raise Refused('empty-audio')
    return audio, lo, hi


def interpret(output):
    if not isinstance(output, list) or len(output) != 1 or not isinstance(output[0], dict):
        raise Refused('word-failed')
    ipa, phones = output[0].get('processed_transcript'), output[0].get('predicted_transcript')
    if (not isinstance(ipa, str) or not ipa.strip() or not isinstance(phones, str)
            or len(ipa) > MAX_TEXT or len(phones) > MAX_TEXT
            or any(ord(c) < 32 for c in ipa + phones)):
        raise Refused('no-phones')
    return ipa.strip(), phones


def run(spec):
    from phoneticpins import MODEL
    total = len(spec['targets'])
    send({'event': 'loading', 'total': total, 'revision': MODEL['revision'], 'device': 'cpu'})
    inference, pin = load_model(spec['model_path'], spec.get('processing', 'auto'))
    done, failed = 0, 0
    for target in spec['targets']:
        begun = time.monotonic()
        try:
            if target.get('invalid_timing'):
                raise Refused('invalid-timing')
            audio, lo, hi = audio_crop(spec['source_path'], spec['audio_kind'], target['start'], target['end'])
            with contextlib.redirect_stdout(sys.stderr):
                ipa, phones = interpret(inference(audio))
            evidence = {'state': 'complete', 'ipa': ipa, 'phones': phones,
                        'audio_start': lo, 'audio_end': hi, 'attribution': 'context-crop',
                        'target_start': target['start'], 'target_end': target['end'],
                        'model_revision': pin['revision'], 'elapsed_seconds': round(time.monotonic() - begun, 3)}
        except Exception as error:
            code = error.code if isinstance(error, Refused) else 'word-failed'
            evidence = {'state': 'failed', 'reason': SAYS.get(code, SAYS['word-failed']),
                        'code': code, 'model_revision': pin['revision']}
            failed += 1
        done += 1
        send({'event': 'word', 'word_id': target['word_id'], 'phonetic': evidence})
        send({'event': 'progress', 'completed': done, 'total': total})
    send({'event': 'done', 'completed': done, 'total': total, 'failed': failed,
          'revision': pin['revision'], 'device': 'cpu'})


def main():
    try:
        if len(sys.argv) != 2:
            raise Refused('bad-spec')
        run(read_spec(sys.argv[1]))
    except Exception as error:
        code = error.code if isinstance(error, Refused) else 'model-load'
        send({'event': 'error', 'code': code, 'say': SAYS.get(code, SAYS['model-load'])})
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
