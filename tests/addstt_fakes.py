# SPDX-License-Identifier: GPL-3.0-or-later
"""A computer that has speech to text, for the add page's browser suites.

    sys.modules["getstt"] = addstt_fakes.make(root)     # before `import serve`
    addstt_fakes.configure(root, runtime=False)         # or edit root/state.json

tests/stt_fakes.py is the stand-in Lane C's tests use for lib/getstt.py -- the
names the transcription job reads.  The ADD PAGE reads one more: the slim slice
(`summary`, POST /lookup/api/speech), which the real module computes from the
folder it keeps and from a probe of the graphics card.  A browser suite must
not depend on what THIS machine has (a card, a program, two gigabytes of
models), so the slice is made here from the same small state file the job's
stand-in reads, and CAN BE CHANGED WHILE A PAGE IS OPEN (the suites write the
file): an install "in another tab" is one write.

The slice keeps the real one's shape.  Its texts -- the models' labels, tags and
hints -- are the real module's own (stt_fakes copies its constants), and
tests/test_addstt.py holds the two shapes to each other, so this cannot drift.

state.json:
    runtime   bool     the speech program is installed
    models    [id]     the models that are installed
    cuda      {ready, name, why}   the card: ready, or found and not, or none (name "")
    no_lang   [code]   languages Whisper does not know (a person's own, say)
    busy      bool     an install or a transcription is running elsewhere
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import stt_fakes                                              # noqa: E402

MODELS = stt_fakes.MODELS
NOT_READY = ("The graphics card is not ready for speech to text: it needs cuBLAS for CUDA 12 "
             "(libcublas.so.12 was not found). CPU transcription still works.")
NO_CARD = "There is no NVIDIA graphics card to use. CPU transcription works without one."


def configure(root, runtime=None, models=None, cuda=None, no_lang=None, busy=None, fake=None):
    """Change what the computer reports; whatever is left out is kept."""
    os.makedirs(root, exist_ok=True)
    stt_fakes.configure(root, runtime=runtime, models=models, fake=fake)
    state = stt_fakes._read(root, "state.json", {})
    if cuda is not None:
        state["cuda"] = dict(state.get("cuda") or {}, **cuda)
    if no_lang is not None:
        state["no_lang"] = list(no_lang)
    if busy is not None:
        state["busy"] = bool(busy)
    with open(os.path.join(root, "state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f)


def make(root):
    """stt_fakes' getstt, and the slice.  A computer that was never described has
    no graphics card (stt_fakes' own default is a card that is not ready)."""
    fresh = not os.path.exists(os.path.join(root, "state.json"))
    mod = stt_fakes.make(root)
    if fresh:
        configure(root, cuda={"ready": False, "name": "", "why": ""})

    def state():
        return stt_fakes._read(root, "state.json", {})

    def summary(where=None):
        st = state()
        cuda = dict({"ready": False, "name": "", "why": ""}, **(st.get("cuda") or {}))
        runtime = bool(st.get("runtime", True))
        have = [k for k in MODELS if runtime and k in (st.get("models") or [])]
        ready = bool(cuda["ready"])
        why = "" if ready else (NOT_READY if cuda["name"] else NO_CARD)
        info = mod.MODEL_INFO
        no = set(st.get("no_lang") or [])
        return {"ok": True,
                "installed": bool(runtime and have),
                "runtime": {"state": "ready" if runtime else "absent",
                            "version": "1.2.1" if runtime else "", "why": ""},
                "models": [{"id": k, "label": info[k]["label"], "tag": info[k]["tag"],
                            "hint": info[k]["hint"], "have": k in have, "ready": k in have,
                            "size": 1 << 30 if k in have else 0,
                            "download": 1 << 30} for k in MODELS],
                "default_model": have[0] if have else None,
                "processing": [
                    {"id": "auto", "ready": True, "now": "cuda" if ready else "cpu",
                     "say": "Automatic — recommended."},
                    {"id": "cpu", "ready": True,
                     "say": "CPU. Always works, on every computer (4 cores here, int8)."},
                    {"id": "cuda", "ready": ready, "name": cuda["name"],
                     "memory": (8 << 30) if cuda["name"] else 0,
                     "why": "" if ready else (cuda["why"] or why)}],
                "languages": {c: (c not in no and v) for c, v in mod.speech_languages().items()},
                "busy": bool(st.get("busy")) or bool(mod._using),
                "settings": "/settings/speech/"}
    mod.summary = summary
    return mod
