# SPDX-License-Identifier: GPL-3.0-or-later
"""A stand-in for faster-whisper, for the tests of lib/sttworker.py.

It is put on the worker's PYTHONPATH by tests/stt_fakes.py, where the real
one would be (stt/runtime/...): the worker cannot tell them apart.  It is as
faithful to the parts the worker uses as the pinned 1.2.1 is:

  * WhisperModel(path, device=, compute_type=, cpu_threads=, local_files_only=)
    RECORDS what it was built with (one JSON line in $STT_FAKE_LOG, with its
    process id), and can be told, by $STT_FAKE, to refuse:
        cuda_load_error       a RuntimeError when built on the card
        cuda_reject_compute   compute types the card "does not do" (a ValueError)
        cuda_lazy_error       built fine, then a RuntimeError while the
                              segments are being made -- exactly how a missing
                              libcublas shows itself
        cpu_load_error        a RuntimeError when built on the CPU
        cpu_lazy_error        the same, while iterating
  * transcribe(audio, language=, beam_size=, vad_filter=, task=) returns
    (a generator, info) at once and does its work -- and its failing -- only
    as the generator is consumed, with `info.duration` known up front.
  * the segments come from $STT_FAKE["segments"] ([[start, end, text], ...])
    or are made up, two seconds apart, with `delay` seconds between them.
"""
import json
import os
import sys
import time

CONFIG = json.loads(os.environ.get("STT_FAKE") or "{}")
LOG = os.environ.get("STT_FAKE_LOG")

__version__ = "0.0-parseh-test"


def _log(kind, **fields):
    if not LOG:
        return
    fields.update(kind=kind, pid=os.getpid())
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(fields) + "\n")


class Word:
    def __init__(self, start, end, word, config=None):
        self.start, self.end, self.word, self.probability = start, end, word, 0.9
        if (CONFIG if config is None else config).get('leading_word_spaces'):
            self.word = ' '+word
        evidence = (CONFIG if config is None else config).get("word_evidence", {}).get(word, {})
        if "score" in evidence:
            self.probability = evidence["score"]
        if "alternatives" in evidence:
            self.alternatives = evidence["alternatives"]
        scalar_type = (CONFIG if config is None else config).get('numpy_word_scalars')
        if scalar_type:
            import numpy as np
            scalar = {'float32': np.float32, 'float64': np.float64}[scalar_type]
            self.start, self.end = scalar(start), scalar(end)
            self.probability = scalar(self.probability) if self.probability is not None else None


class Segment:
    def __init__(self, start, end, text, words=None):
        self.start, self.end, self.text = start, end, text
        self.words = words or []


class TranscriptionInfo:
    def __init__(self, language, duration):
        self.language = language
        self.language_probability = 1.0
        self.duration = duration
        self.duration_after_vad = duration


class WhisperModel:
    def __init__(self, model_size_or_path, device="auto", device_index=0,
                 compute_type="default", cpu_threads=0, num_workers=1,
                 download_root=None, local_files_only=False, files=None, **rest):
        _log("construct", path=str(model_size_or_path), device=device,
             compute_type=compute_type, cpu_threads=cpu_threads,
             local_files_only=local_files_only, rest=sorted(rest),
             env={k: os.environ.get(k) for k in ("PYTHONPATH", "HF_HUB_OFFLINE",
                                                 "PYTHONNOUSERSITE", "PYTHONSAFEPATH")})
        time.sleep(float(CONFIG.get("load_delay") or 0))
        if device == "cuda":
            if compute_type in (CONFIG.get("cuda_reject_compute") or []):
                raise ValueError("Requested %s compute type, but the target device or backend "
                                 "do not support efficient %s computation."
                                 % (compute_type, compute_type))
            if CONFIG.get("cuda_load_error"):
                raise RuntimeError(CONFIG["cuda_load_error"])
        elif device == "cpu" and CONFIG.get("cpu_load_error"):
            raise RuntimeError(CONFIG["cpu_load_error"])
        self.device = device
        self.second_calls = 0

    def transcribe(self, audio, language=None, beam_size=5, vad_filter=False,
                   task="transcribe", **rest):
        config = CONFIG
        if beam_size == 10:
            requests = CONFIG.get('second_pass', [])
            if self.second_calls < len(requests):
                config = dict(CONFIG, **requests[self.second_calls])
            self.second_calls += 1
        _log("transcribe", language=language, beam_size=beam_size, vad_filter=vad_filter,
             task=task, samples=len(audio), audio_type=type(audio).__name__,
             dtype=str(getattr(audio, "dtype", "")), rest=sorted(rest), device=self.device,
             options=rest,
             peak=float(max(abs(float(audio.max())), abs(float(audio.min())))) if len(audio)
             else 0.0)
        duration = len(audio) / 16000.0
        made = config.get("segments")
        if made is None:
            made = []
            t = 0.0
            while t < duration and len(made) < 8:
                made.append([t, min(duration, t + 1.9), " fake words %d" % (len(made) + 1)])
                t += 2.0
        delay = float(config.get("delay") or 0)
        lazy = CONFIG.get("cuda_lazy_error") if self.device == "cuda" else CONFIG.get("cpu_lazy_error")

        want_words = bool(rest.get("word_timestamps"))
        def generate():
            if config.get('second_exit'):
                os._exit(17)
            if config.get('second_error'):
                raise RuntimeError('fake crop failure')
            if lazy:
                raise RuntimeError(lazy)
            for start, end, text in made:
                time.sleep(delay)
                bits = text.split()
                span = float(end) - float(start)
                words = [Word(float(start) + span * i / len(bits),
                              float(start) + span * (i + 1) / len(bits), bit, config)
                         for i, bit in enumerate(bits)] if want_words and bits and not config.get('no_words') else []
                yield Segment(float(start), float(end), text, words)
        return generate(), TranscriptionInfo(language, duration)
