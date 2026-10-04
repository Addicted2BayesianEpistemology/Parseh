# Heard IPA with PhoneticXeus

Settings → Speech to text offers PhoneticXeus beside Whisper, with separate
program and model installation. Installing it does not install or replace any
Whisper model. Neither component is fetched automatically. The checkbox controls
whether an installed recognizer estimates IPA for the fixed suspect words after
Whisper and dictionary checks. Individual failures leave the Whisper result intact.

The review details show **estimated heard IPA around this word**, not a dictionary pronunciation.
The recognizer receives original audio around the word's first-pass timestamp;
it receives no transcript text, spelling, language prompt, or proposed correction.
The crop adds 0.5 seconds on each side, clipped at audio boundaries. Neighboring phones can therefore appear,
and inaccurate Whisper word boundaries can omit or include sounds. This is useful
listening evidence, not proof that a word is wrong. Existing word and caption
timestamps never change. When present, the reasoning workspace includes the IPA
and crop attribution with the same stable source word ID.
The CSV's `ipa_target_start`/`ipa_target_end` and
`ipa_audio_start`/`ipa_audio_end` are original audio seconds, independently of
display timing, video-clock remapping or CTC alignment. The workspace skill and
its Python helper explain the context attribution before using this evidence.

This is explicitly `context-crop` evidence. The target word's unchanged start/end
and the actual crop's start/end remain separate. The returned phone string
describes the surrounding audio, and is not asserted to be the target word's
isolated pronunciation. Very small crops can produce no phones, and changing
the crop can change the estimated pronunciation. Empty results remain reported unavailable;
the integration does not infer or synthesize phones from text to fill gaps.

## Installation and isolation

Optional runtime wheels are hash-pinned for Python 3.12, Linux x86_64/aarch64,
Windows AMD64, and macOS ARM64/Intel. Mac Intel uses PyTorch/torchaudio 2.2.2;
the other platforms use 2.5.1, with official CPU-only builds on Linux x86_64 and
Windows. macOS 13 or newer or glibc 2.28 or newer on Linux is required.
Model inference uses CPU float32. CUDA
and Apple Metal acceleration are not supplied by this runtime; an explicitly
requested CUDA mode reports its unavailability rather than silently changing it.
Automatic mode uses CPU for this optional stage, independently of Whisper's GPU.

The checkpoint is about 2.30 GB and has approximately 575 million parameters.
The separate runtime download is approximately 115–268 MB depending on platform;
installation and inference need additional disk space and several GB of RAM.
No benchmark or accuracy improvement is claimed for Parseh's integration. CPU
inference on many suspect words can be slow, and short, noisy or clipped audio
can yield incomplete or incorrect phones.

The installation lives in `stt/phonetic/`, completely separate from Whisper's
runtime and Parseh's main Python environment. Its verified runtime and checkpoint
are usable offline. Downloads can be stopped and resumed; partial trees are never
declared installed. Removing either component leaves Whisper models untouched.
The worker loads one checkpoint for the suspect-word session and unloads on
completion, cancellation, a stale source, timeout, or server shutdown. Cancellation
terminates native loading or inference through the isolated child process.

Equivalent host commands, run with Parseh's Python:

```sh
python lib/getphonetic.py status
python lib/getphonetic.py get phonetic-runtime
python lib/getphonetic.py get phonetic-model
python lib/getphonetic.py remove phonetic-model
```

## Provenance and licence

The model and its required implementation come from
[changelinglab/PhoneticXeus](https://huggingface.co/changelinglab/PhoneticXeus/tree/ed64f14aeb0e903a80a825cf67a079aa8f93d3ac)
at revision `ed64f14aeb0e903a80a825cf67a079aa8f93d3ac`. This revision includes
the upstream self-conditioned CTC inference correction at layers 4, 8 and 12.
Every necessary source/configuration/vocabulary file and `model.safetensors` has
a pinned SHA-256 and byte size in `lib/phonetic-model-pins.json`. The duplicate
pickle `.pt` checkpoint is neither fetched nor loaded. Source hashes and weights
are checked again before loading; no code is fetched at inference time.

The current checkpoint's licence is
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/), including
its noncommercial and share-alike terms. Its pinned model card is retained in the
installed folder. Earlier cached model cards labelled it Apache 2.0; Parseh uses
the licence of the actual pinned revision. Upstream source and paper authors are
credited in that model card, which remains available with the installed package.
Runtime wheels retain their own installed distribution licence files.

## Developer checks

`tests/test_phonetic.py` checks atomic installation, pin/size validation, resumable
cancellation, independent removal, source verification, original-waveform crops,
Unicode IPA, reuse of one loaded recognizer, local failures, progress, stale-source
rejection and child cleanup. The tests use small files and fake inference and do
not need model weights, a GPU or network access. A real-model compatibility and
phonetic-accuracy check requires an explicitly installed checkpoint; passing fake
protocol tests does not establish phone accuracy on a particular language.

Maintainers can run `python lib/phoneticrelease.py --online` to recheck the pinned
revision's source bytes, published safetensors digest and sizes, and all 125 wheel
records against Hugging Face, PyPI and the official PyTorch CPU index. It reads
only metadata and small source files, never the checkpoint tensor payload.
