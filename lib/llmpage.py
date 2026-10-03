# SPDX-License-Identifier: GPL-3.0-or-later
"""Browser Settings -> LLM Integration; endpoint runtime remains its owner's."""
import llmconfig
import settingspage

PAGE = "/settings/llm/"


def page(where):
    can = settingspage.may("llm.connection", where)
    lock = settingspage.lockline("llm.connection", where)
    main = '''<main class="settings" data-layout="browser">
%s
<h1 class="idx">LLM Integration</h1>
<p class="sub">One reusable connection for Parseh features. Connect to an endpoint you already run.</p>
%s
<form id="llm_form" data-configure="%s">
<fieldset %s>
<legend>Connection</legend>
<p><label>API adapter <select id="llm_adapter"><option value="openai-compatible">OpenAI-compatible text</option>
<option value="unsloth-agent-skills">Unsloth Agent Skills + compatible text</option></select></label></p>
<p class="why">Use the Skills adapter when your Unsloth version supports Agent Skills. It can invoke the installed correction skill with only its read_skill tool.</p>
<p><label>Provider <select id="llm_provider"><option value="ollama">Ollama</option>
<option value="unsloth">Unsloth</option><option value="generic">Generic OpenAI-compatible</option></select></label></p>
<p><label>HTTP(S) API base URL <input id="llm_url" type="url" maxlength="2048" required placeholder="http://127.0.0.1:11434/v1"></label></p>
<p><label>API key <select id="llm_key_action"><option value="keep">Keep saved key</option>
<option value="replace">Replace key</option><option value="clear">Clear key</option></select></label>
<input id="llm_key" type="password" maxlength="4096" autocomplete="new-password" aria-label="Replacement API key" hidden>
<span id="llm_key_status"></span></p>
<p><label>Request timeout (seconds) <input id="llm_timeout" type="number" min="1" max="300" value="60" required></label></p>
<p><label>Endpoint context budget (tokens) <input id="llm_context" type="number" min="4096" max="131072" value="8192" required></label></p>
<p class="why">Match the context length configured in your endpoint. Parseh uses a conservative UTF-8 byte budget and reserves room for the instructions and sentence answer.</p>
<details><summary>Import Unsloth run settings</summary>
<p><label>Studio share link <input id="llm_link" type="url" maxlength="4096"></label>
<button type="button" class="plain" id="llm_import">Read settings link</button></p>
<p id="llm_import_note">The link supplies the endpoint and model hint. GGUF and KV-cache settings are applied in Unsloth Studio; Parseh does not load or download models.</p>
<a id="llm_studio" target="_blank" rel="noopener noreferrer" hidden>Open these settings in Unsloth Studio</a>
</details>
<p><button class="go" type="submit">Save connection</button>
<button class="plain" type="button" id="llm_reset">Clear connection</button></p>
</fieldset>
<fieldset><legend>Model selection</legend>
<p>Select a model from any device admitted to Parseh. Endpoint and credential changes are made on the host.</p>
<p><button type="button" class="plain" id="llm_models">Refresh models</button>
<label>Installed / served models <select id="llm_model_list"><option value="">Enter a model ID below</option></select></label></p>
<p><label>Exact model ID <input id="llm_model" type="text" maxlength="512" required></label></p>
<p class="why">A small quantized multilingual Qwen model is a starting point; select the actual ID your endpoint exposes. Listing is advisory: the endpoint may unload a model later.</p>
<p><button type="button" class="go" id="llm_select_model">Save model selection</button>
<button class="plain" type="button" id="llm_test">Test saved connection</button></p>
</fieldset></form>
<p id="llm_destination"></p>
<p id="llm_status" role="status" aria-live="polite"></p>
<p id="llm_last_test"></p>
<section><h2>Where feature inputs go</h2>
<p>Each feature sends only its required inputs to the saved destination. Transcript correction sends a short sentence with its suspect words and only their available Whisper hints. Audio, file paths, video IDs, cookies and unrelated history are never sent. A connection test asks for a short text response and says nothing about linguistic accuracy.</p>
<p>Credentials stay on this Parseh host and are never returned after saving. Unsloth and Ollama control their own CPU/GPU, quantization and cache settings. Nothing is installed or started by Parseh.</p></section>
</main><p data-layout="mobile">LLM Integration is configured in the Browser interface. Switch to Browser using the interface control above.</p>''' % (settingspage.settings_doors(PAGE), lock, "true" if can else "false", "" if can else "disabled")
    return settingspage.frame("LLM Integration — Parseh", "Settings", "Settings", "/guide/", main,
                              style=".settings fieldset {border:1px solid var(--rule);border-radius:.6rem;padding:1rem;} .settings input[type=url] {width:min(35rem,100%);font:inherit;} .settings select {font:inherit;} .settings input[type=password] {font:inherit;}",
                              extra_head='<script defer src="/lib/llmsettings.js"></script>')
