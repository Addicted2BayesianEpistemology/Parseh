// SPDX-License-Identifier: GPL-3.0-or-later
(function () {
  'use strict';
  var form = document.getElementById('likelihood_form'); if (!form) return;
  var host = form.dataset.host === 'true', status = document.getElementById('lm_status'), modelList = document.getElementById('lm_models'), timer;
  var strings = ['source', 'manager_url', 'python', 'backend', 'cuda_host_compiler', 'cuda_architectures'];
  var numbers = ['gpu_layers', 'gpu_device', 'threads', 'context_tokens', 'preceding_chars', 'following_chars', 'beam_width', 'candidate_count', 'replacement_tokens', 'replacement_chars', 'target_seconds', 'load_seconds', 'minimum_candidate_probability', 'phonetic_similarity'];
  var probabilityPreset = document.getElementById('lm_probability_preset'), probabilityInput = document.getElementById('lm_minimum_candidate_probability');
  function cutoffChoice() {
    var custom = probabilityPreset.value === 'custom';
    document.getElementById('lm_probability_custom').hidden = !custom;
    probabilityInput.required = custom;
    if (!custom && probabilityPreset.value !== '') probabilityInput.value = probabilityPreset.value;
  }
  probabilityPreset.addEventListener('change', cutoffChoice);
  function ask(action, body) {
    return fetch('/settings/api/lm-likelihood/' + action, {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body || {})}).then(function (r) { return r.json(); }).then(function (data) { if (!data.ok) throw new Error(data.error || 'The action failed.'); return data; });
  }
  function paint(data) {
    if (data.settings && host) strings.concat(numbers).forEach(function (key) { document.getElementById('lm_' + key).value = data.settings[key]; });
    if (data.settings && host) ['cuda_force_mmq', 'phonetic_filter'].forEach(function (key) { document.getElementById('lm_' + key).checked = data.settings[key]; });
    if (data.settings && host) {
      var cutoff = data.settings.minimum_candidate_probability;
      probabilityPreset.value = cutoff === 0 ? '0' : cutoff === 0.1 ? '0.1' : 'custom';
      cutoffChoice();
    }
    document.getElementById('lm_selected').textContent = data.model ? 'Selected: ' + data.model : 'No model selected yet.';
    document.getElementById('lm_devices').textContent = (data.runtime.gpu_devices || []).map(function (d) { return d.backend.toUpperCase() + ' device ' + d.index + ': ' + d.description + ' · ' + (d.free_bytes / 1073741824).toFixed(2) + ' GiB free / ' + (d.total_bytes / 1073741824).toFixed(2) + ' GiB total'; }).join(' · ') || 'No supported GPU device was detected by the isolated runtime.';
    status.textContent = data.error || (data.install.state === 'installing' ? 'Installing runtime dependencies…' : data.install.state === 'failed' ? data.install.error : data.available ? 'Ready to review words.' : data.runtime.say || 'Choose installed weights before reviewing.');
    if (timer) clearTimeout(timer);
    if (data.install.state === 'installing') timer = setTimeout(refresh, 2000);
  }
  function fail(error) { status.textContent = error.message; }
  function refresh() { return ask('status').then(paint, fail); }
  function inventory() {
    status.textContent = 'Reading installed-model metadata…';
    return ask('models').then(function (data) {
      modelList.textContent = '';
      data.models.forEach(function (m) { var option = document.createElement('option'); option.value = m.id; option.textContent = m.model_id; modelList.appendChild(option); });
      document.getElementById('lm_select').disabled = !modelList.value;
      document.getElementById('lm_inventory').textContent = data.errors.map(function (e) { return e.model_id + ': ' + e.error; }).join(' ');
      status.textContent = data.models.length ? 'Choose a model, then press Use selected model.' : 'No supported model file was found. Enter a local GGUF path in Local worker setup on the Parseh computer.';
    }, fail);
  }
  form.addEventListener('submit', function (event) {
    event.preventDefault(); if (!host) return;
    var body = {}; strings.forEach(function (key) { body[key] = document.getElementById('lm_' + key).value; });
    numbers.forEach(function (key) { body[key] = Number(document.getElementById('lm_' + key).value); });
    ['cuda_force_mmq', 'phonetic_filter'].forEach(function (key) { body[key] = document.getElementById('lm_' + key).checked; });
    var path = document.getElementById('lm_path').value.trim(); if (path) body.path = path;
    ask('save', body).then(paint, fail);
  });
  document.getElementById('lm_refresh').addEventListener('click', inventory);
  document.getElementById('lm_select').disabled = !modelList.value;
  modelList.addEventListener('change', function () { document.getElementById('lm_select').disabled = !modelList.value; });
  document.getElementById('lm_select').addEventListener('click', function () { if (modelList.value) ask('select', {id: modelList.value}).then(paint, fail); });
  document.getElementById('lm_unload').addEventListener('click', function () { ask('unload').then(paint, fail); });
  document.getElementById('lm_install').addEventListener('click', function () { if (host) ask('install').then(paint, fail); });
  refresh();
})();
