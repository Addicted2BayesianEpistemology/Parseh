// SPDX-License-Identifier: GPL-3.0-or-later
(function () {
  'use strict';
  function id(s) { return document.getElementById('llm_' + s); }
  var status = id('status'), busy = false, version = 0;
  var canConfigure = id('form').getAttribute('data-configure') === 'true';
  function say(s) { status.textContent = s; }
  function request(name, body) {
    var ctl = new AbortController(), timer = setTimeout(function () { ctl.abort(); }, name === 'test' ? 620000 : 310000);
    return fetch('/settings/api/llm/' + name, {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body || {}), signal: ctl.signal}).then(function (r) { return r.json(); })
      .then(function (j) { clearTimeout(timer); if (!j.ok) throw new Error(j.error); return j; },
        function () { clearTimeout(timer); throw new Error('Parseh did not answer.'); });
  }
  function fields() {
    var b = {provider_preset: id('provider').value, adapter: id('adapter').value, base_url: id('url').value.trim(),
      selected_model: id('model').value.trim(), timeout_seconds: Number(id('timeout').value),
      context_tokens: Number(id('context').value),
      key_action: id('key_action').value, studio_link: id('link').value.trim()};
    if (b.key_action === 'replace') b.api_key = id('key').value;
    return b;
  }
  function draw(s) {
    id('destination').textContent = s.configured ? 'Saved destination: ' + s.base_url + ' · Model: ' + s.selected_model : 'Unconfigured. Whisper review works without an LLM.';
    id('key_status').textContent = s.has_api_key ? 'A key is saved on the host.' : 'No key is saved.';
    if (s.configured) {
      id('provider').value = s.provider_preset; id('url').value = s.base_url;
      id('adapter').value = s.adapter || 'openai-compatible';
      id('model').value = s.selected_model; id('timeout').value = s.timeout_seconds;
      id('context').value = s.context_tokens || 8192;
      id('link').value = s.studio_link || '';
    } else {
      id('provider').value = 'ollama'; id('url').value = 'http://127.0.0.1:11434/v1';
      id('adapter').value = 'openai-compatible';
      id('model').value = id('link').value = '';
    }
    id('key').value = ''; id('key_action').value = 'keep'; id('key').hidden = true;
    id('last_test').textContent = s.last_test ? 'Last connection test: ' + s.last_test.say : 'No connection test for these settings in this server session.';
    studio(s.studio_link);
  }
  function studio(link) {
    id('studio').hidden = !link;
    if (link) id('studio').href = link; else id('studio').removeAttribute('href');
  }
  function refresh() {
    var current = ++version;
    id('model_list').textContent = '';
    var op = document.createElement('option'); op.value = ''; op.textContent = 'Enter a model ID below'; id('model_list').appendChild(op);
    say('Asking this endpoint for its installed / served models…');
    return request(canConfigure ? 'models' : 'models-saved', canConfigure ? fields() : {}).then(function (j) {
      if (current !== version) return;
      j.models.forEach(function (m) { var o = document.createElement('option'); o.value = m; o.textContent = m; id('model_list').appendChild(o); });
      id('model_list').value = j.models.indexOf(id('model').value) >= 0 ? id('model').value : '';
      say(j.models.length + ' models advertised. Select one or enter its exact ID.');
    }, function (e) { if (current === version) say(e.message + ' Manual model-ID entry remains available.'); });
  }
  function operation(message, fn) {
    if (busy) return; busy = true; say(message);
    var controls = Array.prototype.slice.call(id('form').querySelectorAll('button'));
    controls.forEach(function (e) { e.disabled = true; });
    return fn().then(function () { busy = false; controls.forEach(function (e) { e.disabled = false; }); },
      function (e) { busy = false; controls.forEach(function (x) { x.disabled = false; }); say(e.message); });
  }
  id('key_action').addEventListener('change', function () { id('key').hidden = this.value !== 'replace'; if (this.value !== 'replace') id('key').value = ''; });
  id('provider').addEventListener('change', function () {
    id('url').value = this.value === 'ollama' ? 'http://127.0.0.1:11434/v1' : '';
    id('model_list').textContent = ''; version++; say('Enter your endpoint URL. Unsloth installations may use different ports.');
  });
  id('url').addEventListener('change', function () { if (this.value.trim()) refresh(); });
  id('models').addEventListener('click', refresh);
  id('select_model').addEventListener('click', function () { operation('Saving the selected model…', function () {
    return request('select-model', {selected_model: id('model').value.trim()}).then(function (j) { draw(j); say('Model selection saved. Review asks before sending text.'); });
  }); });
  id('model_list').addEventListener('change', function () { if (this.value) id('model').value = this.value; });
  id('import').addEventListener('click', function () {
    request('import-link', {link: id('link').value}).then(function (j) {
      id('provider').value = 'unsloth'; id('url').value = j.base_url; id('model').value = j.model_hint;
      id('link').value = j.studio_link; studio(j.studio_link);
      id('import_note').textContent = 'Model hint: ' + j.model_hint + ' · GGUF: ' + (j.gguf_variant || 'unspecified') + ' · KV cache: ' + (j.kv_cache_dtype || 'unspecified') + '. Apply hardware settings in Studio. Confirm the exact advertised model ID below.';
      refresh();
    }, function (e) { say(e.message); });
  });
  id('form').addEventListener('submit', function (e) {
    e.preventDefault(); operation('Saving the connection on the Parseh host…', function () {
      return request('save', fields()).then(function (j) { draw(j); say('Connection saved. Features ask before sending their inputs.'); });
    });
  });
  id('test').addEventListener('click', function () { operation('Testing the saved model with a short text response…', function () {
    return request('test').then(function (j) { draw(j); say(j.last_test.say); });
  }); });
  id('reset').addEventListener('click', function () { operation('Clearing the connection…', function () {
    return request('reset').then(function (j) { id('url').value = id('model').value = id('link').value = ''; draw(j); say('Connection cleared.'); });
  }); });
  request('status').then(draw, function (e) { say(e.message); });
})();
