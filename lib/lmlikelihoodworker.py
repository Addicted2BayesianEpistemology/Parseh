#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Standalone llama.cpp scoring process. Only the low-level C binding is used.

JSON lines are OUR process protocol, never generated/model JSON. stdin:
{op:load,config}, {op:target,request}, {op:unload}. No network or chat APIs.
"""
import ctypes
import importlib.metadata
import json
import math
import os
from pathlib import Path
import sys
import signal
import re

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lmgguf import ScoringError, inspect, revalidate
from lmlikelihoodcore import target
import lmlikelihoodhardware as hardware


class Backend:
    def __init__(self, config):
        # Import ONLY inside this child. No high-level Llama/chat constructor.
        try:
            from llama_cpp import llama_cpp as C
            import numpy as np
        except (ImportError, OSError, RuntimeError):
            raise ScoringError('runtime-missing', 'The isolated llama.cpp library or its native dependencies are unavailable. Install the matching scoring runtime on this host.')
        if importlib.metadata.version('llama-cpp-python') != '0.3.35':
            raise ScoringError('runtime-version', 'The scoring worker requires llama-cpp-python 0.3.35.')
        self.C, self.np, self.model, self.ctx = C, np, None, None
        self.failure = None
        self.offloaded_layers = 0
        def native_log(level, text, data):
            # Native log text may contain filenames; keep only categories.
            if text:
                match = re.search(rb'offloaded\s+(\d+)\s*/\s*\d+\s+layers', text)
                if match:
                    self.offloaded_layers = int(match.group(1))
            if level >= 4 and text:
                raw = text.lower()
                if any(s in raw for s in (b'out of memory', b'failed to allocate', b'cannot allocate', b'allocation failed')):
                    self.failure = 'resources'
                elif any(s in raw for s in (b'missing tensor', b'wrong shape', b'truncated', b'unexpected end')):
                    self.failure = 'incomplete'
                elif b'unknown architecture' in raw or b'unknown model architecture' in raw or b'unsupported' in raw:
                    self.failure = 'unsupported'
        self.log_callback = C.llama_log_callback(native_log)
        C.llama_log_set(self.log_callback, None)
        C.llama_backend_init()
        revalidate(config['model'])
        inspect(config['model']['path'])
        if config['gpu_layers'] and not C.llama_supports_gpu_offload():
            raise ScoringError('backend-unavailable', 'This scoring runtime has no GPU backend. Install the selected backend or choose CPU and zero GPU layers.')
        params = C.llama_model_default_params()
        self.device_pointers, device = hardware.model_devices(C, config, hardware.devices(C), params)
        params.use_mmap = True
        self.model = C.llama_model_load_from_file(os.fsencode(config['model']['path']), params)
        if not self.model:
            self.load_error()
        if config['gpu_layers'] and not self.offloaded_layers:
            self.close()
            raise ScoringError('backend-unavailable', 'The model was not offloaded to a GPU. Check the selected backend, device/driver availability and resources, or explicitly choose CPU.')
        model_layers = C.llama_model_n_layer(self.model)
        try:
            hardware.verify_offload(config['gpu_layers'], self.offloaded_layers, model_layers)
        except ScoringError:
            self.close(); raise
        if C.llama_model_has_encoder(self.model) or not C.llama_model_has_decoder(self.model):
            self.close()
            raise ScoringError('unsupported-model', 'Only standalone causal decoder text-generation models are supported.')
        self.vocab = C.llama_model_get_vocab(self.model)
        self.vocab_size = C.llama_vocab_n_tokens(self.vocab)
        # Some tokenizers add a dummy initial space to supplied text. Infer
        # that convention from a fixed round trip, without stripping actual
        # source whitespace or the leading space of a continuation token.
        self.prefix_space = self.decode(self.tokenize('x')) == b' x'
        params = C.llama_context_default_params()
        params.n_ctx = config['context_tokens']
        params.n_batch = params.n_ubatch = min(128, config['context_tokens'])
        params.n_threads = params.n_threads_batch = config['threads']
        params.flash_attn_type = 0
        hardware.context_devices(config, params)
        self.ctx = C.llama_init_from_model(self.model, params)
        if not self.ctx:
            self.close(); self.load_error()
        self.context_tokens = min(config['context_tokens'], C.llama_n_ctx(self.ctx))
        self.position = 0
        self.hardware = {'backend': config['backend'] if device else 'cpu',
                         'gpu_device': config.get('gpu_device', 0) if device else None,
                         'device': {k: v for k, v in device.items() if k != 'handle'} if device else None,
                         'requested_gpu_layers': config['gpu_layers'], 'offloaded_layers': self.offloaded_layers,
                         'model_layers': model_layers, 'context_tokens': self.context_tokens}

    def load_error(self):
        if self.failure == 'resources':
            raise ScoringError('insufficient-resources', 'The scoring worker could not allocate model/context memory. It needs its own RAM/GPU allocation; unload other applications yourself or choose smaller settings.')
        if self.failure == 'incomplete':
            raise ScoringError('incomplete-model', 'The native loader found missing or invalid model tensors. Finish installing a complete standalone GGUF in its manager.')
        if self.failure == 'unsupported':
            raise ScoringError('unsupported-model', 'The pinned scoring runtime does not support this model architecture or tensor configuration. Select a compatible installed GGUF.')
        raise ScoringError('model-load-failed', 'llama.cpp could not load this model. Check runtime/model compatibility and available RAM/GPU memory.')

    def tokenize(self, text):
        C = self.C
        raw = text.encode('utf-8')
        capacity = len(raw) + 16
        buf = (C.llama_token * capacity)()
        n = C.llama_tokenize(self.vocab, raw, len(raw), buf, capacity, False, False)
        if n < 0:
            capacity = -n
            buf = (C.llama_token * capacity)()
            n = C.llama_tokenize(self.vocab, raw, len(raw), buf, capacity, False, False)
        if n < 0:
            raise ScoringError('tokenization-failed', 'The model could not tokenize supplied text.')
        tokens = list(buf[:n])
        # Respect the model tokenizer's BOS convention, never invent a BOS.
        if C.llama_vocab_get_add_bos(self.vocab):
            tokens.insert(0, C.llama_vocab_bos(self.vocab))
        return tokens

    def decode(self, tokens):
        C = self.C
        parts = []
        for t in tokens:
            if C.llama_vocab_is_control(self.vocab, t):
                continue
            b = ctypes.create_string_buffer(128)
            n = C.llama_token_to_piece(self.vocab, t, b, 128, 0, False)
            if n < 0:
                b = ctypes.create_string_buffer(-n)
                n = C.llama_token_to_piece(self.vocab, t, b, len(b), 0, False)
            if n < 0:
                raise ScoringError('decode-failed', 'A model token could not be decoded.')
            parts.append(b.raw[:n])
        return b''.join(parts)

    def decode_prefix(self, tokens):
        """Decode a stream beginning at the supplied text's start.

        decode() remains raw for beam continuations, including UTF-8 pieces.
        Only the verified tokenizer-added first space is removed here.
        """
        raw = self.decode(tokens)
        return raw[1:] if self.prefix_space and raw.startswith(b' ') else raw

    def is_eog(self, token):
        return self.C.llama_vocab_is_eog(self.vocab, token)

    def begin(self, tokens):
        # llama_decode can enqueue GPU work. Finish it BEFORE clearing/reusing
        # inference memory, including the last decode of another candidate.
        self.C.llama_synchronize(self.ctx)
        self.C.llama_memory_clear(self.C.llama_get_memory(self.ctx), True)
        self.position = 0
        if len(tokens) >= self.context_tokens:
            raise ScoringError('context-limit', 'Token search exceeds the configured context limit.')
        for at in range(0, len(tokens), 128):
            self._eval(tokens[at:at + 128])

    def _eval(self, tokens):
        C = self.C
        if self.position + len(tokens) > self.context_tokens:
            raise ScoringError('context-limit', 'Supplied text exceeds the configured context limit.')
        batch = C.llama_batch_init(len(tokens), 0, 1)
        try:
            batch.n_tokens = len(tokens)
            for i, token in enumerate(tokens):
                batch.token[i] = token
                batch.pos[i] = self.position + i
                batch.n_seq_id[i] = 1
                batch.seq_id[i][0] = 0
                batch.logits[i] = i == len(tokens) - 1
            if C.llama_decode(self.ctx, batch) != 0:
                raise ScoringError('evaluation-failed', 'llama.cpp could not evaluate supplied tokens; check memory and context settings.')
            self.position += len(tokens)
        finally:
            C.llama_batch_free(batch)

    def push(self, token):
        self._eval([token])

    def logits(self):
        self.C.llama_synchronize(self.ctx)
        pointer = self.C.llama_get_logits_ith(self.ctx, -1)
        if not pointer:
            raise ScoringError('missing-logits', 'No logits are available for the preceding supplied token.')
        return self.np.ctypeslib.as_array(pointer, shape=(self.vocab_size,)).astype(self.np.float64, copy=True)

    def log_probability(self, logits, token):
        np = self.np
        if np.isnan(logits).any() or np.isposinf(logits).any() or not math.isfinite(float(logits[token])):
            raise ScoringError('invalid-logits', 'The model produced invalid or unscorable logits.')
        peak = float(np.max(logits))
        return float(logits[token]) - peak - math.log(float(np.exp(logits - peak).sum()))

    def top_tokens(self, logits, n):
        # Full-vocabulary raw ranking. Token-ID order resolves numerical ties.
        if self.np.isnan(logits).any() or self.np.isposinf(logits).any():
            raise ScoringError('invalid-logits', 'The model produced invalid numerical logits.')
        n = min(n, self.vocab_size)
        # Select a cutoff over the full vocabulary, then sort only the top
        # group including ALL cutoff ties. This gives the identical ordering
        # as a full sort; it changes no probabilities or search branches.
        cutoff = self.np.partition(logits, self.vocab_size - n)[self.vocab_size - n]
        selected = self.np.flatnonzero(logits >= cutoff)
        order = self.np.lexsort((selected, -logits[selected]))[:n]
        return selected[order].tolist()

    def close(self):
        if self.ctx:
            self.C.llama_synchronize(self.ctx)
            self.C.llama_free(self.ctx); self.ctx = None
        if self.model:
            self.C.llama_model_free(self.model); self.model = None


def main():
    if sys.platform.startswith('linux'):
        parent = os.getppid()
        ctypes.CDLL(None).prctl(1, signal.SIGKILL, 0, 0, 0)
        if os.getppid() != parent or parent == 1:
            return
    # Separate protocol fd from all native/Python library output.
    protocol = os.fdopen(os.dup(sys.stdout.fileno()), 'w', encoding='utf-8', buffering=1)
    sink = os.open(os.devnull, os.O_WRONLY)
    os.dup2(sink, 1); os.dup2(sink, 2); os.close(sink)
    def send(data):
        protocol.write(json.dumps(data, ensure_ascii=True, allow_nan=False) + '\n')
    if '--probe' in sys.argv:
        try:
            from llama_cpp import llama_cpp as C
            callback = C.llama_log_callback(lambda *args: None)
            C.llama_log_set(callback, None)
            C.llama_backend_init()
            found = hardware.public(hardware.devices(C))
            send({'available': True, 'version': importlib.metadata.version('llama-cpp-python'),
                  'gpu_supported': bool(found), 'gpu_devices': found})
        except Exception:
            send({'available': False, 'say': 'The isolated llama.cpp scoring dependency is unavailable.'})
        return
    backend = None
    try:
        for line in sys.stdin:
            if len(line.encode()) > 4 << 20:
                raise ScoringError('request-size', 'The scoring request exceeds the worker’s bounded input size.')
            try:
                body = json.loads(line)
                if body['op'] == 'load' and backend is None:
                    config = body['config']
                    backend = Backend(config)
                    send({'op': 'loaded', 'context_tokens': backend.context_tokens, 'hardware': backend.hardware})
                elif body['op'] == 'target' and backend:
                    result = target(backend, body['request'], config)
                    result['hardware'] = backend.hardware
                    send({'op': 'target', 'result': result})
                elif body['op'] == 'unload':
                    break
                else:
                    raise ScoringError('bad-protocol', 'The scoring worker received an invalid lifecycle request.')
            except ScoringError as e:
                send({'op': 'error', 'code': e.code, 'error': e.say})
            except (ImportError, ModuleNotFoundError):
                send({'op': 'error', 'code': 'runtime-missing', 'error': 'The isolated scoring runtime is unavailable. Install it on the host.'})
            except Exception:
                send({'op': 'error', 'code': 'worker-failed', 'error': 'The scoring worker failed. The Whisper result is intact.'})
    finally:
        if backend:
            backend.close()
        send({'op': 'unloaded'})


if __name__ == '__main__':
    main()
