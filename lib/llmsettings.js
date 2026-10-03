// SPDX-License-Identifier: GPL-3.0-or-later
(function () {
  'use strict';
  function id(s) { return document.getElementById('llm_' + s); }
  var status = id('status'), busy = false, version = 0, profiles = [], nativeProfiles = false;
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
    id('destination').textContent = s.configured ? 'Saved destination: ' + s.base_url + ' · Model: ' + s.selected_model + (s.pending_profile ? ' · Profile loading is unconfirmed; apply it again before LLM review.' : '') : 'Unconfigured. Whisper review works without an LLM.';
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
    profiles = s.model_profiles || [];
    nativeProfiles = s.adapter === 'unsloth-studio' || s.adapter === 'unsloth-agent-skills';
    id('profile_list').textContent = '';
    var empty = document.createElement('option'); empty.value = ''; empty.textContent = 'Choose a profile'; id('profile_list').appendChild(empty);
    profiles.forEach(function (p) { var o = document.createElement('option'); o.value = p.id; o.textContent = p.name; id('profile_list').appendChild(o); });
    id('profile_list').value = s.saved_profile || s.pending_profile || s.selected_profile || '';
    ['suspect', 'full', 'workspace'].forEach(function (task) {
      var select = id('task_' + task + '_profile'); select.textContent = '';
      var empty = document.createElement('option'); empty.value = ''; empty.textContent = 'Model ID / general selection'; select.appendChild(empty);
      profiles.forEach(function (p) { var option = document.createElement('option'); option.value = p.id; option.textContent = p.name; select.appendChild(option); });
      var setting = s.review_models && s.review_models[task];
      select.value = setting && setting.profile_id || ''; id('task_' + task + '_model').value = setting && setting.model_id || '';
      id('task_' + task + '_model').disabled = !!select.value;
    });
    profileInfo();
  }
  function profileInfo() {
    var p = profiles.find(function (r) { return r.id === id('profile_list').value; });
    id('profile_info').textContent = p ? p.link : 'Save a Studio link, then choose it here.';
    id('profile_apply').disabled = busy || !nativeProfiles || !p;
    id('profile_remove').disabled = busy || !p;
    id('profile_save').disabled = busy;
    if (p) { id('profile_name').value = p.name; id('profile_link').value = p.link; }
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
    var controls = Array.prototype.slice.call(document.querySelectorAll('.settings button'));
    controls.forEach(function (e) { e.disabled = true; });
    return fn().then(function () { busy = false; controls.forEach(function (e) { e.disabled = false; }); profileInfo(); },
      function (e) { busy = false; controls.forEach(function (x) { x.disabled = false; }); profileInfo(); say(e.message); });
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
      if (j.context_tokens) id('context').value = Math.max(4096, Math.min(131072, j.context_tokens));
      id('import_note').textContent = 'Model hint: ' + j.model_hint + ' · GGUF: ' + (j.gguf_variant || 'unspecified') + ' · KV cache: ' + (j.kv_cache_dtype || 'unspecified') + (j.context_tokens ? ' · Studio context: ' + j.context_tokens : '') + '. Apply hardware settings in Studio. Confirm the exact advertised model ID below.';
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
  id('profile_list').addEventListener('change', profileInfo);
  ['suspect', 'full', 'workspace'].forEach(function (task) {
    id('task_' + task + '_profile').addEventListener('change', function () {
      var p = profiles.find(function (p) { return p.id === id('task_' + task + '_profile').value; });
      id('task_' + task + '_model').disabled = !!p;
      if (p) {
        var hash = new URL(p.link).hash.slice(5), params = new URLSearchParams(hash);
        id('task_' + task + '_model').value = params.get('model') || '';
      }
    });
    id('task_' + task + '_save').addEventListener('click', function () {
      operation('Saving the review model…', function () {
        return request('review-model', {task: task, model_id: id('task_' + task + '_model').value.trim(), profile_id: id('task_' + task + '_profile').value || null})
          .then(function (j) { draw(j); say('Review model saved. Starting its review is a deliberate action.'); });
      });
    });
  });
  id('profile_save').addEventListener('click', function () { operation('Saving the model profile link…', function () {
    return request('profile-save', {name: id('profile_name').value.trim(), link: id('profile_link').value.trim()}).then(function (j) { draw(j); say('Profile saved. Select it and press Load selected profile to apply its options.'); });
  }); });
  id('profile_remove').addEventListener('click', function () { operation('Removing the saved profile…', function () {
    return request('profile-remove', {profile_id: id('profile_list').value}).then(function (j) { draw(j); say('Profile removed. The endpoint keeps its current loaded model.'); });
  }); });
  id('profile_apply').addEventListener('click', function () { operation('Loading the installed model and applying its saved options in Unsloth…', function () {
    return request('profile-apply', {profile_id: id('profile_list').value}).then(function (j) { draw(j); say(j.say + ' Context: ' + j.applied_profile.context_tokens + ' tokens.'); }, function (e) {
      return request('status').then(function (j) { draw(j); throw e; }, function () { throw e; });
    });
  }); });
  request('status').then(draw, function (e) { say(e.message); });
})();
