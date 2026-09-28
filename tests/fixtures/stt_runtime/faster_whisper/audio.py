# SPDX-License-Identifier: GPL-3.0-or-later
"""The decoder of the stand-in faster-whisper: a WAV under any name.

The real decode_audio hands a film to PyAV and gets back float32 mono at the
rate asked for.  This one reads a 16-bit WAV with the standard library and
gives the same array, so a test's "film" is a few seconds of tone in a file
called film.mp4; a file that is not a WAV fails the way an undecodable film
does (PyAV raises whatever it raises; the worker takes any Exception for it).
"""
import wave

import numpy as np


def decode_audio(input_file, sampling_rate=16000, split_stereo=False):
    try:
        with wave.open(str(input_file), "rb") as w:
            channels, width, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
            raw = w.readframes(w.getnframes())
    except (wave.Error, EOFError) as e:
        raise RuntimeError("Invalid data found when processing input: %s" % e)
    if width != 2:
        raise RuntimeError("only 16-bit WAV is decoded here")
    pcm = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        pcm = pcm.reshape(-1, channels).mean(axis=1)
    if rate != sampling_rate:
        raise RuntimeError("this stand-in does not resample (%d Hz)" % rate)
    return pcm.astype(np.float32)
