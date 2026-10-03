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

**Saved Unsloth model profiles** retains up to eight Studio share links.
Paste a link and profile name, then **Save profile link**. **Load selected
profile** uses Studio's API to load an already installed GGUF variant with
its KV-cache type, optional context length and vision option. Missing files
and unsupported link options are refused without downloading anything.
Vision defaults off when omitted; speculative decoding and thinking are off.
Studio controls hardware placement; Parseh reads the loaded context budget.

Profiles and model selection are available from any admitted browser. Profile
links must use the saved endpoint; changing that destination or its key remains
host-only. A failed or unconfirmed load blocks inference until you retry the
profile or deliberately select a loaded model.

Under **Models for transcript review**, choose separate profiles or exact model
IDs for **suspect-word correction** and **whole-text review**. An empty ID uses
the general selection. Starting a review explicitly loads its assigned installed
Studio profile first. It never loads a model on opening a page. Compatible
servers without Studio's native API use saved model IDs directly.

**Import Unsloth run settings** is a separate host-only convenience for reading
an endpoint/model hint. It does not execute the link. Use saved profiles to apply
options through the API, or open the link in Studio.

Create an Unsloth API key using the avatar's **Settings → API** page. Name it,
press **Create** and copy it while shown; Studio shows the key once.

## Review a Whisper result

When [speech to text](speech-to-text.md) finishes on
[Add a video](../videos/adding-a-video.md#speech-to-text), the transcript box
stays unchanged. Choose **Review suspect words with the LLM**, **Review the whole text with the
LLM**, or **Review Whisper result without the LLM**. The saved destination/model are shown before sending.
Whisper-only review sends nothing. Remembering a browser default marks a
button and never makes an unattended request.

**⚠** marks an available Whisper score below **0.5**, not proof a word is wrong.
Missing scores stay missing. **◇** marks a word with no meaning in the installed
language dictionary, using the readers' normalization, base-form and prefix
rules. A dictionary miss is also a suspect-word target, even with a high ASR
score; names and rare words can be valid. An absent or failing dictionary does
not flag words. The word inspector shows dictionary meanings for Whisper's
original, each native Whisper alternative and each proposed LLM alternative,
so you can compare them before
accepting an edit. Meanings use the installed dictionary's language, normally
English, independently of the video's gloss language.

**✎** marks a proposed LLM substitution. Focus, hover or tap any word to inspect
evidence or edit it. Only suspect words' available alternatives are sent as
readable hints. The same faster-whisper backend now retains up to five native
beam hypotheses and exposes substitutions that map unambiguously to a source
word. Their **sequence log scores** rank complete recognition hypotheses;
alternative-word probabilities stay unavailable. An empty list means no
unambiguous word alternative was returned, not that the word is correct.
There is no extra recognizer or model download. The model may choose a
better word beyond those hints. Its answer is a complete sentence; Parseh maps
only unambiguous substitutions for suspect words back to their exact spans.
Whole-text review checks every mapped word, including confident words, and can
propose a short contiguous span covering several ASR pieces. The two reviews
have separate prompts and skills. Nearby captions provide bounded read-only
context and are never included in the replaceable target.

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

Expand **Correction skill** in the review page to download the suspect-word
skill (`parseh-asr-correction`) or whole-text skill (`parseh-asr-audit`). Each zip
contains its skill folder and `SKILL.md`. In Unsloth, extract the folder under the endpoint user's
`.agents/skills/`, or create the skill in Studio and enable it. It can then be
selected with `@parseh-asr-correction` in a Studio chat.

For API review, select **Unsloth Agent Skills + compatible text** as the saved
adapter on the host. **Install in saved endpoint** creates this exact skill
through Unsloth's authenticated Skills API; it never overwrites an existing
skill. **Check installed skill** checks whether it is enabled and valid.
Choose which skill to check/install and enable **Use installed skill for the
chosen review** before starting LLM review. Parseh
sends the skill invocation and sentence evidence; Unsloth loads the installed
instructions with its `read_skill` tool. Other tools and MCP are disabled.

Other software needs its own skill-capable API to invoke installed skills.
Generic compatible endpoints use Parseh's short prompt. A skill supplies reusable
instructions to the same model; it does not train it or ensure better accuracy.

## Progress, failures and diagnosis

Progress counts ASR words processed, including failed attempts, rather than
sentences. Whole-text review counts every mapped word; suspect review counts
selected low-score words and dictionary misses. If one request times out or returns an invalid answer, its words stay
unchanged and the remaining sentences continue. Failed and unresolved words can
be edited manually or sent again with **Retry all remaining suspect words**.
Manual edits remain in the draft. Suspect-word retry excludes accepted words.
Whole-text retry rechecks the affected captions; an acceptance is retained only
when its exact proposal is unchanged. Neither route changes the transcript box.

**LLM responses** shows actual prompts, raw/final answers, supplied reasoning,
finish status and elapsed time. Output-limit failures are visible here. Long
outputs/history are bounded and may be clipped. These records remain temporary
with this job; they are never written to logs or synced. A model leaving a word
unchanged does not establish that it is correct.

**Cancel LLM review** aborts the HTTP work and retains the Whisper result.
Audio, waveforms, paths, video IDs, cookies and unrelated history are never sent.
ASR hardware remains in Speech to text; LLM hardware belongs to the endpoint.
This feature adds no mobile reader or mobile app behavior.
