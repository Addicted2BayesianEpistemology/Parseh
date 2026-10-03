# SPDX-License-Identifier: GPL-3.0-or-later
"""Browser-only standalone scoring settings, separate from chat generation."""
import settingspage

PAGE = '/settings/lm-likelihood/'


def page(where):
    can = settingspage.may('likelihood.worker', where)
    main = '''<main class="settings" data-layout="browser">%s
<h1 class="idx">LM likelihood · experimental</h1>
<p>Use an installed GGUF as a numerical probability engine. This method uses raw tokens and logits, with no chatbot prompts or responses. It searches for additional candidate words, then ranks the original, every Whisper alternative and those new candidates.</p>
%s
<form id="likelihood_form" data-host="%s"><fieldset %s><legend>Model source and worker · host only</legend>
<p><label>Model source <select id="lm_source"><option value="unsloth">Installed Unsloth GGUF</option><option value="ollama">Installed Ollama model</option><option value="path">Explicit local GGUF path</option></select></label></p>
<p><label>Ollama manager URL <input id="lm_manager_url" type="url" maxlength="2048"></label></p>
<p>Unsloth discovery reads Studio’s installation manifests and local cache metadata. Ollama discovery calls only its inventory and model-metadata APIs. Neither starts, unloads or downloads a manager’s model.</p>
<p>A model labeled “text only” has a complete standalone text decoder; its separately validated optional vision projectors are unused. Split weights and required adapters are refused.</p>
<p><label>Explicit GGUF path on this host <input id="lm_path" type="text" maxlength="4096" placeholder="Optional; overrides model source on save"></label></p>
<p><label>Isolated worker Python <input id="lm_python" type="text" maxlength="4096"></label></p>
<p><label>Runtime backend <select id="lm_backend"><option value="cpu">CPU</option><option value="cuda">NVIDIA CUDA</option><option value="metal">Apple Metal</option><option value="vulkan">Vulkan</option></select></label>
<label>GPU layers <input id="lm_gpu_layers" type="number" min="-1" max="1000"></label> (0 = CPU; −1 = all layers)</p>
<p><label>GPU device index within this backend <input id="lm_gpu_device" type="number" min="0" max="63"></label></p>
<p><label>CUDA host C++ compiler (optional absolute path) <input id="lm_cuda_host_compiler" type="text" maxlength="4096"></label>
<label>CUDA build architectures <input id="lm_cuda_architectures" type="text" maxlength="80"></label> (native, e.g. 75;86, or 61-virtual;80-virtual)</p>
<p><label><input id="lm_cuda_force_mmq" type="checkbox"> Force CUDA quantized matrix kernels (MMQ)</label>
For GTX 1650/1660 cards without tensor cores, llama.cpp recommends 61-virtual;80-virtual with MMQ enabled. Use a CUDA toolkit that supports those architectures.</p>
<p><label>CPU threads <input id="lm_threads" type="number" min="1" max="128"></label>
<label>Context tokens <input id="lm_context_tokens" type="number" min="128" max="16384"></label></p>
<p><label>Preceding characters <input id="lm_preceding_chars" type="number" min="0" max="8000"></label>
<label>Following characters <input id="lm_following_chars" type="number" min="1" max="8000"></label></p>
<p><label>Beam width <input id="lm_beam_width" type="number" min="1" max="16"></label>
<label>Additional candidates <input id="lm_candidate_count" type="number" min="1" max="64"></label></p>
<p><label>Search replacement tokens <input id="lm_replacement_tokens" type="number" min="1" max="16"></label>
<label>Search replacement characters <input id="lm_replacement_chars" type="number" min="1" max="200"></label></p>
<p>Search limits affect only model-derived candidates. The original and all supplied Whisper alternatives remain mandatory. Token limits are not a word-boundary test.</p>
<p><label>Scoring budget per word (seconds) <input id="lm_target_seconds" type="number" min="1" max="600"></label>
<label>Model load timeout (seconds) <input id="lm_load_seconds" type="number" min="1" max="600"></label></p>
<p><button class="go" type="submit">Save worker settings</button>
<button type="button" class="plain" id="lm_install">Install / rebuild isolated runtime</button></p>
<p>Runtime installation builds llama-cpp-python 0.3.35 and its dependencies for this computer only. CPU needs a C/C++ compiler; GPU builds also need their backend SDK. CUDA needs an NVIDIA driver and a host compiler supported by its toolkit. The optional CUDA compiler path handles systems whose default compiler is too new; a compatible compiler already supplied under llm-scoring/toolchain is used when the field is empty. Install model weights yourself through Studio, Ollama or another manager. Parseh reuses them read-only and never copies or converts them.</p>
</fieldset></form>
<section><h2>Installed model selection</h2><p>Any admitted browser may select a model already discovered on this host. Source, file path and executable settings are host-only.</p>
<p><button class="plain" id="lm_refresh" type="button">Refresh installed models</button>
<label>Model <select id="lm_models"><option value="">Refresh to discover local weights</option></select></label>
<button class="go" id="lm_select" type="button">Use selected model</button></p>
<p id="lm_selected"></p><p id="lm_inventory"></p>
<p id="lm_devices"></p>
<button class="plain" id="lm_unload" type="button">Cancel scoring and unload worker</button></section>
<p id="lm_status" role="status" aria-live="polite"></p>
<p>The worker loads once per review and unloads at completion or cancellation. It needs its own RAM/GPU allocation even when another application is already using the same file. Parseh never unloads another application to free memory. Only complete single-file causal text-generation GGUF models are supported; split models and required adapters are refused.</p>
<p>Score: log P(candidate + fixed following text | original preceding text), summed over supplied tokens. Each target uses immutable Whisper context. Scores are not calibrated probabilities of correct transcription; the best candidate is only the winner among those evaluated. Raw sums can favor different token lengths. Review and accept substitutions yourself.</p>
<p><a href="/settings/llm/">Chat-generation LLM Integration</a> remains a separate configuration.</p>
</main><p data-layout="mobile">LM likelihood is available in the Browser interface. Switch to Browser using the interface control above.</p>''' % (settingspage.settings_doors(PAGE), settingspage.lockline('likelihood.worker', where),
    'true' if can else 'false', '' if can else 'disabled')
    return settingspage.frame('LM likelihood — Parseh', 'Settings', 'Settings', '/guide/', main,
        style='.settings fieldset {border:1px solid var(--rule);border-radius:.6rem;padding:1rem;} .settings input[type=text],.settings input[type=url] {width:min(35rem,100%);font:inherit;} .settings input[type=number] {width:7rem;} .settings select {font:inherit;}',
        extra_head='<script defer src="/lib/lmlikelihoodsettings.js"></script>')
