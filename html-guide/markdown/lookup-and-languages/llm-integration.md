---
title: LLM Integration
weight: 9
description: A reusable host-local OpenAI-compatible connection, model discovery and explicit transcript correction review in the browser.
---

**Settings → LLM Integration** (`/settings/llm/`) connects browser features
to an endpoint you already run. It starts unconfigured. Whisper and manual
transcript entry work without it. Parseh installs no LLM software, downloads
no weights and starts no model server.

## Configure the connection

Choose **Ollama**, **Unsloth** or **Generic OpenAI-compatible**. The labels
supply defaults; all three use the same chat-completions adapter. Ollama
prefills `http://127.0.0.1:11434/v1`. For Unsloth, enter your installation's
address with `/v1`; installations can use different ports. A remote HTTP(S)
endpoint is possible too. The address is reached by the Parseh host, so
`localhost` means that host.

The **API key** control keeps an existing key, replaces it with the masked
field, or clears it explicitly. A saved key is never returned to the browser.
It lives only in the host's `config/llm.json`, outside Git, releases and synced
preferences. Endpoint, credentials and model changes are permitted only on
the computer Parseh runs on, as the Settings door says.

**Refresh models** asks the endpoint for the models it advertises. Select one
or enter an exact model ID manually if discovery is unavailable. Listing is
advisory: a model may disappear before a later request. A small quantized
multilingual Qwen model is a starting point, rather than a required provider
or model family.

Set the request timeout and the endpoint's context budget. Match the context
length you configured in the endpoint; Parseh splits text into bounded,
overlapping windows, reserves space for the instructions and answer, and uses
a conservative UTF-8 byte estimate without installing a tokenizer.

**Save connection** stores the settings. **Test saved connection** sends a
small synthetic request to the selected model and checks JSON output and
authentication. It does not measure linguistic accuracy. The last result is
shown for these settings during the current server session. **Clear
connection** removes this connection only; speech runtimes and models stay.

## Unsloth share links

Under **Import Unsloth run settings**, paste a version 1 Chat run-settings
share link and press **Read settings link**. Parseh reads its endpoint origin,
model hint, GGUF variant and KV-cache type without fetching the link. Confirm
the advertised model ID before saving.

**Open these settings in Unsloth Studio** lets you apply quantization and
hardware choices there. A link's `run=1` does not become an automatic request
by Parseh. GGUF, GPU and KV-cache settings belong to the endpoint: they are
not portable chat-completions parameters.

In Unsloth Studio, an API key is created from the avatar at the bottom left
under **Settings → API**. Name the key, press **Create** and copy it while it
is shown; Studio shows the key only once.

## Review a Whisper result

When [speech to text](speech-to-text.md) finishes on
[Add a video](../videos/adding-a-video.md#speech-to-text), the transcript box
stays as it was. Choose **Review with the selected LLM** or **Review Whisper
result without the LLM**. The LLM button shows the saved destination and model
before use. An unconfigured connection offers Whisper-only review and a link
to this Settings door. Remembering a browser default only marks a button;
every LLM request still requires a click.

Both routes open review. **⚠** marks available Whisper scores below **0.5**;
this is a low ASR score, not proof a word is wrong. Missing scores stay
missing. **✎** marks an LLM proposal. Hover, keyboard focus or tap/click on a
marked word exposes its original text, timestamps, ASR score, available
alternatives, suggested replacements and reasons. LLM likelihood and
confidence values are explicitly model estimates, not calibrated
probabilities. A word flagged only by Whisper stays unchanged.

Accept individual alternatives or reject them to keep Whisper's word. Edits
affect the pending draft, and **Pending transcript draft** shows the result.
Only **Use this transcript** writes it into the existing box, with an
overwrite confirmation when necessary. Cancel leaves the box untouched. A
source, language, Whisper-model or transcript-box change discards stale
review. Caption boundaries and their video-clock timings are preserved.
Changed word timing is carried through the existing timing editor as
estimated and needs review; the audio has already been deleted, so automatic
re-alignment is not claimed.

## Progress, cancellation and privacy

Multiple LLM windows report completed-window progress. A single request has
an indeterminate bar and elapsed time. **Cancel LLM review** aborts the HTTP
work, discards proposals and keeps the Whisper result available. Failure,
timeout or invalid model JSON likewise offers retry or Whisper-only review;
partial suggestions are never presented as complete.

Correction sends only bounded text, language and ASR evidence with stable
word and segment IDs. Audio, waveforms, file paths, video identifiers,
cookies and unrelated history are never sent. Whisper scores and genuine
ASR alternatives retain their meaning. The current faster-whisper backend
does not expose per-word N-best alternatives, so requests explicitly report
them as unavailable. An optional timing aligner's score is never used as a
Whisper score.

This feature belongs to the browser authoring flow. It adds no mobile reader
or mobile app feature. ASR hardware choices remain in Speech to text; LLM
hardware is controlled by the endpoint's owner.
