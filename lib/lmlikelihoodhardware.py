# SPDX-License-Identifier: GPL-3.0-or-later
"""Pinned ggml device interface, used only in the standalone scoring child."""
import ctypes
from pathlib import Path
import sys

from lmgguf import ScoringError


def devices(C):
    # llama-cpp-python 0.3.35 exposes its linked ggml device API through _lib.
    # Match the bundled ggml-backend.h, never infer devices from build strings.
    signatures = {
        'ggml_backend_dev_count': (ctypes.c_size_t, []),
        'ggml_backend_dev_get': (ctypes.c_void_p, [ctypes.c_size_t]),
        'ggml_backend_dev_type': (ctypes.c_int, [ctypes.c_void_p]),
        'ggml_backend_dev_backend_reg': (ctypes.c_void_p, [ctypes.c_void_p]),
        'ggml_backend_reg_name': (ctypes.c_char_p, [ctypes.c_void_p]),
        'ggml_backend_dev_name': (ctypes.c_char_p, [ctypes.c_void_p]),
        'ggml_backend_dev_description': (ctypes.c_char_p, [ctypes.c_void_p]),
        'ggml_backend_dev_memory': (None, [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]),
    }
    api = C._lib
    if not hasattr(api, 'ggml_backend_dev_count'):
        # Windows DLL lookup does not search dependency exports as Linux does.
        # Bind the matching ggml library beside this exact pinned llama DLL.
        filename = 'ggml-base.dll' if sys.platform == 'win32' else 'libggml-base.dylib' if sys.platform == 'darwin' else 'libggml-base.so'
        api = ctypes.CDLL(str(Path(C._lib._name).parent / filename))
    for name, (result, args) in signatures.items():
        call = getattr(api, name)
        call.restype, call.argtypes = result, args
    found = []
    for i in range(min(api.ggml_backend_dev_count(), 64)):
        handle = api.ggml_backend_dev_get(i)
        if not handle or api.ggml_backend_dev_type(handle) not in (1, 2):
            continue  # dedicated GPU or integrated GPU, not CPU/BLAS/meta
        reg = api.ggml_backend_dev_backend_reg(handle)
        backend = (api.ggml_backend_reg_name(reg) or b'').decode('utf-8', 'replace').lower()
        if backend not in ('cuda', 'metal', 'vulkan'):
            continue
        free, total = ctypes.c_size_t(), ctypes.c_size_t()
        api.ggml_backend_dev_memory(handle, ctypes.byref(free), ctypes.byref(total))
        found.append({'handle': handle, 'backend': backend,
                      'name': (api.ggml_backend_dev_name(handle) or b'').decode('utf-8', 'replace')[:200],
                      'description': (api.ggml_backend_dev_description(handle) or b'').decode('utf-8', 'replace')[:300],
                      'free_bytes': free.value, 'total_bytes': total.value})
    return found


def public(found):
    indexes = {}
    out = []
    for device in found:
        backend = device['backend']
        index = indexes.get(backend, 0)
        indexes[backend] = index + 1
        out.append(dict({k: v for k, v in device.items() if k != 'handle'}, index=index))
    return out


def model_devices(C, config, found, params):
    """Use ONLY the selected GPU; an empty device list forces CPU execution."""
    selected = None
    if config['gpu_layers']:
        matching = [d for d in found if d['backend'] == config['backend']]
        index = config.get('gpu_device', 0)
        if index >= len(matching):
            raise ScoringError('backend-unavailable', 'The selected GPU device is unavailable to this runtime. Check the backend, device index and driver, or explicitly choose CPU.')
        selected = matching[index]
    pointers = (ctypes.c_void_p * (2 if selected else 1))()
    if selected:
        pointers[0] = selected['handle']
    params.devices = ctypes.cast(pointers, ctypes.c_void_p).value
    params.split_mode = C.LLAMA_SPLIT_MODE_NONE
    params.main_gpu = 0  # exactly one device in our explicit list
    params.n_gpu_layers = config['gpu_layers']
    return pointers, selected


def context_devices(config, params):
    # Zero layers is an explicit CPU run, even with a GPU-capable binary.
    enabled = bool(config['gpu_layers'])
    params.offload_kqv = enabled
    params.op_offload = enabled


def verify_offload(requested, actual, model_layers):
    minimum = model_layers if requested < 0 else min(requested, model_layers)
    if actual < minimum or requested == 0 and actual != 0:
        raise ScoringError('backend-unavailable', 'The requested model-layer offload was not achieved. Check device support and resources, or explicitly choose another layer count/CPU.')
