---
title: LLM Integration
weight: 9
description: An OpenAI-compatible connection, remote model selection, installed correction skills and explicit browser transcript review.
---

**Settings → LLM Integration** connects browser features to an endpoint you
already run. It starts unconfigured. Whisper and manual transcript entry work
without it. Parseh installs no model software, downloads no weights and starts
no endpoint.

## Configure the connection

Choose **Ollama**, **Unsloth** or **Generic OpenAI-compatible**. Presets supply
defaults and share the text adapter. Ollama prefills
`http://127.0.0.1:11434/v1`. For Unsloth use your installation's API address
ending in `/v1`; ports vary. The Parseh host reaches the address, so `localhost`
means that host. Hosted or other-computer HTTP(S) endpoints are also possible.

The **API key** control keeps, replaces or clears the masked key explicitly.
It stays in the host's private `config/llm.json`, outside releases and synced
preferences, and is never returned after saving. Endpoint, credential, adapter
and timeout/context changes are made on the host.

**Model selection is available from any device admitted to Parseh**, in the
Browser interface. **Refresh models** lists advertised models. Choose one or
enter an exact ID, then **Save model selection**. This changes only the model,
retaining the destination and credentials. Listing is advisory: the model may
be unloaded later. A small multilingual Qwen model is a starting point; choose
one that works well for your language and computer.

Set the timeout and context budget to match your endpoint. Parseh reserves
instructions/output space and uses bounded sentences with conservative UTF-8
byte estimates. **Save connection** saves all host controls. **Test saved
connection** asks the saved model for a short synthetic text reply and checks
reachability/authentication. It does not establish correction accuracy.
**Clear connection** leaves all Whisper runtimes and models intact.

## Unsloth share links

Under **Import Unsloth run settings**, paste a version 1 Chat run-settings
link. **Read settings link** imports the endpoint/model hint without fetching
or running it. Confirm the advertised model ID. **Open these settings in
Unsloth Studio** lets you apply quantization, GPU and KV-cache settings there.
Those hardware choices are controlled by Studio, not Parseh's correction API.

Create an Unsloth API key using the avatar's **Settings → API** page. Name it,
press **Create** and copy it while shown; Studio shows the key once.

## Review a Whisper result

When [speech to text](speech-to-text.md) finishes on
[Add a video](../videos/adding-a-video.md#speech-to-text), the transcript box
stays unchanged. Choose **Review with the selected LLM** or **Review Whisper
result without the LLM**. The saved destination/model are shown before sending.
Whisper-only review sends nothing. Remembering a browser default marks a
button and never makes an unattended request.

**⚠** marks an available Whisper score below **0.5**, not proof a word is wrong.
Missing scores stay missing. **✎** marks a proposed LLM substitution. Focus,
hover or tap any word to inspect evidence or edit it. Only suspect words'
available alternatives are sent as readable hints; current faster-whisper does
not expose N-best alternatives, and the page says so. The model may choose a
better word beyond those hints. Its answer is a complete sentence; Parseh maps
only unambiguous substitutions for suspect words back to their exact spans.

Accept or reject individual proposals. Even when no proposal or ASR alternative
exists, **Enter the correct word** and **Save word in draft** lets you type the
correction yourself. Any reviewable word can be edited, including words without
scores. **Restore Whisper word** undoes its edit. **Pending transcript draft**
shows the pending result. Only **Use this transcript** writes it into the box,
after the existing overwrite confirmation if needed. Cancel leaves the box
untouched. Source, language, Whisper-model or box changes discard stale review.
Caption boundaries and video clocks stay unchanged; edited word timings need
review in the existing timing editor because the audio has been deleted.

## Correction skill

Expand **Correction skill** in the review page and **Download correction
skill**. The zip contains `parseh-asr-correction/SKILL.md` and installation
instructions. In Unsloth, extract the folder under the endpoint user's
`.agents/skills/`, or create the skill in Studio and enable it. It can then be
selected with `@parseh-asr-correction` in a Studio chat.

For API review, select **Unsloth Agent Skills + compatible text** as the saved
adapter on the host. **Install in saved endpoint** creates this exact skill
through Unsloth's authenticated Skills API; it never overwrites an existing
skill. **Check installed skill** checks whether it is enabled and valid.
Choose **Use installed correction skill** before starting LLM review. Parseh
sends the skill invocation and sentence evidence; Unsloth loads the installed
instructions with its `read_skill` tool. Other tools and MCP are disabled.

Other software needs its own skill-capable API to invoke installed skills.
Generic compatible endpoints use Parseh's short prompt. A skill supplies reusable
instructions to the same model; it does not train it or ensure better accuracy.

## Progress, failures and diagnosis

Progress counts suspect words processed, including failed attempts, rather than
sentences. If one request times out or returns an invalid answer, its words stay
unchanged and the remaining sentences continue. Failed and unresolved words can
be edited manually or sent again with **Retry all remaining suspect words**.
Accepted and manual edits remain in the draft and are excluded from retry.

**LLM responses** shows actual prompts, raw/final answers, supplied reasoning,
finish status and elapsed time. Output-limit failures are visible here. Long
outputs/history are bounded and may be clipped. These records remain temporary
with this job; they are never written to logs or synced. A model leaving a word
unchanged does not establish that it is correct.

**Cancel LLM review** aborts the HTTP work and retains the Whisper result.
Audio, waveforms, paths, video IDs, cookies and unrelated history are never sent.
ASR hardware remains in Speech to text; LLM hardware belongs to the endpoint.
This feature adds no mobile reader or mobile app behavior.
