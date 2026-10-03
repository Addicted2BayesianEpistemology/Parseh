---
title: LM likelihood · experimental
weight: 10
description: Rank original, Whisper and model-discovered word candidates using raw causal model likelihoods and installed GGUF weights.
---

**Settings → LM likelihood · experimental** configures a separate local
probability worker for browser transcript review. It starts unconfigured.
Whisper and the existing [chat review methods](llm-integration.md) remain
independent.

## Select installed weights

Install the model yourself in Unsloth Studio, Ollama or another application.
Parseh reuses the installed GGUF file **read-only**. It never downloads, copies,
converts or renames model weights.

Choose **Installed Unsloth GGUF** to read Studio’s local installation metadata,
or **Installed Ollama model** with that manager’s URL. Press **Save worker
settings**, **Refresh installed models**, choose a model and press **Use selected
model**. Selection from the discovered list is available to any admitted
browser. Source, file path, executable and hardware settings are host-only.

If discovery is unavailable, enter an **Explicit GGUF path on this host** and
save it. A remote manager’s path must also be readable on the Parseh host.
Ollama’s backing files can have content-addressed names without a `.gguf`
extension; Parseh checks their actual format. Only complete single-file causal
text-generation GGUFs are supported. Split models and required adapters are
refused.
Installed variants with a complete text decoder and separate vision-projector
GGUFs can appear as **text only**. Scoring never uses those projectors or accepts
vision inputs; the complete text model is loaded independently.

## Install the scoring runtime

Choose **CPU** and **0 GPU layers** to start, then press **Save worker settings**
and **Install / rebuild isolated runtime**. This installs llama-cpp-python
0.3.35 and its compatible llama.cpp runtime into a separate folder; it installs
no model weights and changes no packages in Parseh’s ordinary environment.
CPU installation needs a C/C++ compiler. CUDA, Apple Metal and Vulkan builds
also need their hardware SDK/build dependencies. Match the saved backend to
the runtime; GPU layers **−1** requests all layers, and a positive number
requests partial offload.
Choose the **GPU device index** from the backend's detected devices shown on
the page. The worker uses that device only; zero GPU layers disables model and
context offload even with a GPU-capable runtime. Missing devices or incomplete
requested offload produce a clear error. The word inspector reports the actual
device and number of offloaded layers.

CUDA builds need a host C++ compiler supported by the CUDA toolkit. If the
system compiler is too new, enter a compatible compiler's absolute path in
**CUDA host C++ compiler**. A compatible compiler already supplied under
`llm-scoring/toolchain/` is used when that field is empty. **CUDA build
architectures** defaults to `native`, or accepts a list such as `75;86`. The
Settings button builds the runtime for this computer; rebuild it when moving
to another computer.
For this GTX 1650 without tensor cores, llama.cpp recommends
`61-virtual;80-virtual` with **Force CUDA quantized matrix kernels (MMQ)**
enabled. Use a CUDA toolkit that supports those architectures. CPU/GPU
quantized arithmetic can yield different scores or discovered candidates;
compare scores within the selected backend and review close rankings carefully.

CPU threads, context-token limit, preceding/following characters, beam width,
additional candidate count and replacement-search length are explicit settings.
Search bounds affect only additional model-derived words. Every supplied
Whisper alternative and the exact original remain mandatory candidates.

The worker needs its **own RAM/GPU memory**, even when Studio or Ollama already
has the same model loaded. Parseh never unloads another application’s model.
The worker loads once per review and unloads on completion or cancellation.
**Cancel scoring and unload worker** is also available on this settings page.

## Review candidates

After [Whisper finishes](../videos/adding-a-video.md#speech-to-text), choose
**LM likelihood · experimental**. It searches raw next-token probabilities for
additional complete word candidates, then evaluates each supplied substitution
with the same original preceding and following context. It asks no chatbot
question and sends no assistant prompt.

Focus, hover or tap a suspect word. Its inspector shows the original, Whisper
alternatives and model-derived candidates, their origins, ranks, raw log
likelihoods, differences from the original and evaluated token counts. The
score sums the log probabilities of the candidate **and the fixed following
text**. It uses no length adjustment. Tokenization changes at the join can
include a small preceding boundary in the evaluated suffix; diagnostics show
that backoff.

Whisper’s **0.5** threshold and dictionary marking stay unchanged. Acoustic
scores and language-model likelihoods remain separate. These numbers are not
probabilities that a word is correct. A raw sum can favor a different token
length. The winner is the best among evaluated candidates, not proof of the
words spoken.

**Complete** means every mandatory candidate was scored. **Partial** or
**failed** evaluations identify unscored candidates and their reasons. A failure
at one word can leave later words available for review. **Retry remaining
suspect words** retries unaccepted targets. A model, source or settings change
invalidates in-flight results.

Accept or reject candidates in the pending draft, or type a manual correction.
The transcript box stays unchanged until **Use this transcript**, with its
existing overwrite and stale-text guards. Caption boundaries and timing stay
unchanged; changed word timing is marked for review. **Cancel** discards
unaccepted numerical results and keeps Whisper’s original intact.

**LLM responses** also holds the temporary numerical diagnostics for this method:
model identity, bounded context, search limits, coverage and scores. It contains
no vocabulary-sized logit matrices or chatbot responses. Nothing is written
into ordinary logs or synced preferences. Long diagnostic histories are clipped
and visibly marked.

Bounded word search can miss useful alternatives, particularly for scripts with
no whitespace boundaries. Evaluating one target at a time cannot resolve
several interacting mistakes jointly. This experimental method has passed
scoring and runtime checks; improved recognition accuracy has not been measured.
