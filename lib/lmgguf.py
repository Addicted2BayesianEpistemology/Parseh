# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only GGUF validation and installed-weight discovery. No model installs.

Tensor sizes follow ggml's GGML_QUANT_SIZES; runtime loading is a second,
independent compatibility check. A filename extension is never consulted.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import stat
import struct
import time
import urllib.parse
import urllib.request


class ScoringError(Exception):
    def __init__(self, code, say):
        super().__init__(say)
        self.code, self.say = code, say


QUANTS = {0: (1, 4), 1: (1, 2), 2: (32, 18), 3: (32, 20),
          6: (32, 22), 7: (32, 24), 8: (32, 34), 9: (32, 36),
          10: (256, 84), 11: (256, 110), 12: (256, 144), 13: (256, 176),
          14: (256, 210), 15: (256, 292), 16: (256, 66), 17: (256, 74),
          18: (256, 98), 19: (256, 50), 20: (32, 18), 21: (256, 110),
          22: (256, 82), 23: (256, 136), 24: (1, 1), 25: (1, 2),
          26: (1, 4), 27: (1, 8), 28: (1, 8), 29: (256, 56),
          30: (1, 2), 34: (256, 54), 35: (256, 66),
          39: (32, 17), 40: (64, 36), 41: (128, 18), 42: (64, 18)}
SCALARS = {0: '<B', 1: '<b', 2: '<H', 3: '<h', 4: '<I', 5: '<i',
           6: '<f', 7: '<?', 10: '<Q', 11: '<q', 12: '<d'}


def identity(path):
    try:
        real = Path(path).expanduser().resolve(strict=True)
        st = real.stat()
        if not stat.S_ISREG(st.st_mode):
            raise OSError()
        with real.open('rb') as f:
            signature = hashlib.sha256(f.read(65536)).hexdigest()
    except (OSError, ValueError, TypeError):
        raise ScoringError('model-inaccessible', 'The model file is missing or unreadable on the scoring worker’s host. A remote manager path is not a local file.')
    return {'path': str(real), 'size': st.st_size, 'mtime_ns': st.st_mtime_ns,
            'device': st.st_dev, 'inode': st.st_ino, 'header_sha256': signature}


def revalidate(model):
    if identity(model.get('source_path', model['path'])) != model['identity']:
        raise ScoringError('model-changed', 'The selected model file was deleted or replaced. Discover and select it again.')


def inspect(path, allow_projector=False):
    ident = identity(path)
    size = ident['size']
    try:
        with open(ident['path'], 'rb') as f:
            def read(n):
                if n < 0 or f.tell() + n > size or f.tell() + n > 256 << 20:
                    raise ValueError()
                b = f.read(n)
                if len(b) != n:
                    raise ValueError()
                return b

            def number(fmt):
                return struct.unpack(fmt, read(struct.calcsize(fmt)))[0]

            def string(keep=True):
                n = number('<Q')
                if n > 16 << 20:
                    raise ValueError()
                b = read(n)
                return b.decode('utf-8') if keep else None

            def value(kind, keep=True):
                if kind in SCALARS:
                    v = number(SCALARS[kind])
                    return v if keep else None
                if kind == 8:
                    return string(keep)
                if kind == 9:
                    sub, n = number('<I'), number('<Q')
                    if sub == 9 or n > 1000000:
                        raise ValueError()
                    for _ in range(n):
                        value(sub, False)
                    return None
                raise ValueError()

            if read(4) != b'GGUF':
                raise ScoringError('not-gguf', 'This file is not GGUF. Install a complete text-generation GGUF model in your model manager.')
            version, tensors, fields = number('<I'), number('<Q'), number('<Q')
            if version not in (2, 3) or not 1 <= tensors <= 100000 or fields > 100000:
                raise ValueError()
            meta, keys = {}, set()
            for _ in range(fields):
                key, kind = string(), number('<I')
                if key in keys:
                    raise ValueError()
                keys.add(key)
                v = value(kind, keep=kind != 9)
                if kind != 9:
                    meta[key] = v
            arch = meta.get('general.architecture')
            projector = allow_projector and arch == 'clip' and meta.get('general.type', 'model') in ('model', 'mmproj')
            if (meta.get('split.count', 1) != 1 or meta.get('split.no', 0) != 0
                    or meta.get('general.type', 'model') != 'model' and not projector
                    or any(k.startswith(('adapter.', 'lora.')) for k in keys)):
                raise ScoringError('unsupported-model', 'Split GGUF models and models requiring adapters are unsupported. Select a complete standalone GGUF.')
            if not projector and (not isinstance(arch, str) or arch in ('clip', 'bert', 'nomic-bert', 't5', 't5encoder', 'wavtokenizer', 'whisper')
                    or not meta.get(arch + '.block_count') or 'tokenizer.ggml.tokens' not in keys
                    or meta.get(arch + '.attention.causal', True) is False or meta.get(arch + '.pooling_type', 0) not in (0, None)):
                raise ScoringError('unsupported-model', 'Select a GGUF causal text-generation model with a tokenizer. This model is unsupported.')
            entries, names = [], set()
            for _ in range(tensors):
                name, dims = string(), number('<I')
                if name in names or not 1 <= dims <= 4:
                    raise ValueError()
                names.add(name)
                shape = [number('<Q') for _ in range(dims)]
                kind, offset = number('<I'), number('<Q')
                if kind not in QUANTS:
                    raise ScoringError('unsupported-quantization', 'This GGUF uses a tensor format unsupported by Parseh’s validator. Select a supported quantization.')
                block, width = QUANTS[kind]
                if any(n < 1 or n > 10000000 for n in shape) or shape[0] % block:
                    raise ValueError()
                entries.append((offset, math.prod(shape) // block * width))
            alignment = meta.get('general.alignment', 32)
            if type(alignment) is not int or alignment < 1 or alignment > 4096 or alignment & (alignment - 1):
                raise ValueError()
            data = (f.tell() + alignment - 1) // alignment * alignment
            end = 0
            for offset, length in sorted(entries):
                if offset % alignment or offset < end or data + offset + length > size:
                    raise ValueError()
                end = offset + length
            if not projector and 'token_embd.weight' not in names:
                raise ScoringError('unsupported-model', 'This GGUF does not contain a standalone text-generation model.')
    except ScoringError:
        raise
    except (ValueError, UnicodeError, OverflowError, struct.error, OSError):
        raise ScoringError('incomplete-gguf', 'The GGUF header or tensor data is invalid or incomplete. Finish installing the model in its manager.')
    return {'path': ident['path'], 'source_path': os.path.abspath(os.path.expanduser(path)), 'identity': ident, 'architecture': arch,
            'name': meta.get('general.name') or Path(path).name,
            'format': 'GGUF', 'format_version': version, 'tensors': tensors,
            'training_context': meta.get(arch + '.context_length'),
            'auxiliary_kind': 'vision-projector' if projector else None}


def url(raw):
    if not isinstance(raw, str) or len(raw) > 2048 or any(ord(c) < 33 for c in raw):
        raise ScoringError('bad-url', 'Enter an HTTP(S) model-manager URL without credentials.')
    try:
        p = urllib.parse.urlsplit(raw)
        _ = p.port
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password or p.query or p.fragment:
            raise ValueError()
    except ValueError:
        raise ScoringError('bad-url', 'Enter an HTTP(S) model-manager URL without credentials.')
    return raw.rstrip('/')


def metadata_request(base, route, body=None):
    # These are manager INVENTORY APIs, never inference, pull or load APIs.
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url(base) + '/' + route, data=data,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            payload = response.read((2 << 20) + 1)
            if len(payload) > 2 << 20:
                raise ValueError()
        return json.loads(payload)
    except Exception:
        raise ScoringError('discovery-failed', 'The model manager’s local inventory could not be read. Use its local GGUF path instead.')


def ollama_model(row, shown):
    if (not isinstance(row, dict) or not isinstance(row.get('name'), str)
            or not row['name'] or len(row['name']) > 1024
            or not isinstance(shown, dict) or not isinstance(shown.get('capabilities', ['completion']), list)
            or 'completion' not in shown.get('capabilities', ['completion'])
            or not isinstance(shown.get('modelfile'), str)):
        raise ScoringError('unsupported-model', 'Ollama did not expose a standalone text-generation model.')
    paths, multiline = [], False
    for line in shown['modelfile'].splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        # Generated TEMPLATE/SYSTEM/MESSAGE strings can span lines and contain
        # unmatched shell quotes or text that resembles model directives.
        # Only actual FROM/ADAPTER metadata matters to read-only discovery.
        if multiline:
            if stripped.count('"""') % 2:
                multiline = False
            continue
        directive = stripped.split(None, 1)[0].upper()
        if directive == 'ADAPTER':
            raise ScoringError('unsupported-model', 'This Ollama model requires an adapter; standalone scoring does not support it.')
        if directive == 'FROM':
            try:
                parts = shlex.split(stripped, comments=True)
            except ValueError:
                raise ScoringError('model-inaccessible', 'Ollama returned an invalid backing-file path. Enter its local GGUF path on this host.')
            paths.append(parts[1] if len(parts) == 2 else '')
        elif stripped.count('"""') % 2:
            multiline = True
    if len(paths) != 1 or not os.path.isabs(paths[0]):
        raise ScoringError('model-inaccessible', 'Ollama did not expose an absolute backing-file path. Enter the local GGUF path on this host.')
    model = inspect(paths[0])
    model.update(source='ollama', model_id=row['name'], manager_digest=row.get('digest'))
    return model


def discover(source, manager_url='', manifests=None):
    rows, errors = [], []
    deadline = time.monotonic() + 20
    if source == 'ollama':
        listing = metadata_request(manager_url, 'api/tags')
        items = listing.get('models', []) if isinstance(listing, dict) else None
        if not isinstance(items, list) or len(items) > 2000:
            raise ScoringError('discovery-failed', 'Ollama’s model inventory is invalid or oversized.')
        for row in items:
            if time.monotonic() >= deadline:
                errors.append({'model_id': 'Remaining models', 'code': 'inventory-timeout', 'error': 'The bounded inventory scan stopped. Refresh again or use an explicit local GGUF path.'})
                break
            try:
                if not isinstance(row, dict) or not isinstance(row.get('name'), str) or not row['name'] or len(row['name']) > 1024:
                    raise ScoringError('discovery-failed', 'Ollama returned an invalid model inventory entry.')
                rows.append(ollama_model(row, metadata_request(manager_url, 'api/show', {'model': row['name']})))
            except ScoringError as e:
                name = row.get('name') if isinstance(row, dict) else None
                errors.append({'model_id': name[:1024] if isinstance(name, str) else 'Unknown model', 'code': e.code, 'error': e.say})
    elif source == 'unsloth':
        # Studio's own installation manifests include Hub location, revision,
        # exact expected files and sizes. Follow these, not guessed filenames.
        root = Path(manifests) if manifests else Path.home() / '.unsloth/studio/cache/hub-state/manifests'
        for p in sorted(root.glob('**/*.json'))[:2000]:
            if time.monotonic() >= deadline:
                errors.append({'model_id': 'Remaining models', 'code': 'inventory-timeout', 'error': 'The bounded local inventory scan stopped. Use an explicit local GGUF path for an unlisted model.'})
                break
            try:
                if p.stat().st_size > 2 << 20:
                    continue
                m = json.loads(p.read_text())
                if not isinstance(m, dict):
                    continue
                files = [f for f in m.get('expected_files', []) if isinstance(f, dict) and str(f.get('path', f.get('filename', ''))).lower().endswith('.gguf')]
                # Studio versions use `path` or `filename` in expected_files.
                if not files:
                    continue
                cache = Path(m['hub_cache']) / ('models--' + m['repo_id'].replace('/', '--'))
                primary, auxiliaries = [], []
                for entry in files:
                    filename = entry.get('path', entry.get('filename'))
                    revision = m.get('commit_hash')
                    matches = [cache / 'snapshots' / revision / filename] if revision else list(cache.glob('snapshots/*/' + filename))
                    matches = list({str(p.resolve()): p for p in matches if p.is_file()}.values())
                    if len(matches) != 1:
                        raise ScoringError('model-inaccessible', 'The installed variant has no unambiguous local file. Enter its exact local GGUF path.')
                    path = matches[0]
                    if not path.is_file() or path.stat().st_size != entry['size']:
                        raise ScoringError('model-inaccessible', 'The installed variant is incomplete or unavailable on this host. Finish its installation in Studio.')
                    parsed = inspect(path, allow_projector=True)
                    if parsed['auxiliary_kind'] == 'vision-projector':
                        auxiliaries.append(filename)
                    else:
                        primary.append(parsed)
                if len(primary) != 1:
                    raise ScoringError('unsupported-model', 'The variant does not contain exactly one complete standalone text model. Split, adapter and multi-model configurations are unsupported.')
                model = primary[0]
                model.update(source='unsloth', model_id=m['repo_id'] + ' / ' + str(m.get('variant', '')))
                if auxiliaries:
                    # Explicit supported configuration: complete text decoder
                    # only. Separate CLIP projectors serve vision inputs, which
                    # this probability worker never accepts or needs.
                    model.update(text_only=True, unused_vision_projectors=auxiliaries)
                    model['model_id'] += ' (text only)'
                rows.append(model)
            except ScoringError as e:
                errors.append({'model_id': m.get('repo_id', p.name), 'code': e.code, 'error': e.say})
            except (OSError, ValueError, KeyError, TypeError):
                continue
    else:
        raise ScoringError('bad-source', 'Choose installed Unsloth, installed Ollama or an explicit local GGUF file.')
    unique = {r['path']: r for r in rows}
    return list(unique.values()), errors
