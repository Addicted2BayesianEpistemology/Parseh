// SPDX-License-Identifier: GPL-3.0-or-later
/* Pending browser review. All text is textContent; source offsets are Unicode code points. */
(function () {
  'use strict';
  function el(tag, text, cls) { var n = document.createElement(tag); if (text != null) n.textContent = text; if (cls) n.className = cls; return n; }
  function btn(text, fn) { var b = el('button', text, 'wbtn small quiet'); b.type = 'button'; b.addEventListener('click', fn); return b; }
  function time(n) { return typeof n === 'number' ? n.toFixed(2) + ' s' : 'unavailable'; }
  function estimate(n) { return typeof n === 'number' ? n.toFixed(2) : 'unavailable'; }
  function mount(root, opts) {
    var result = null, phase = '', config = null, decisions = {}, manualEdits = {}, suggestions = {}, words = {}, selected = null;
    var choice, inspect, details, preview, status, use, responses, retry, useSkill = false, useBusy = false, disabledBefore = [];

    function skillControls() {
      var box = el('details'); box.appendChild(el('summary', 'Correction skill'));
      var download = el('a', 'Download suspect-word correction skill'); download.href = '/lib/asrskill/parseh-asr-correction.zip'; download.download = 'parseh-asr-correction.zip'; box.appendChild(download);
      var auditDownload = el('a', 'Download whole-text review skill'); auditDownload.href = '/lib/asrskill/parseh-asr-audit.zip'; auditDownload.download = 'parseh-asr-audit.zip'; box.appendChild(el('p')).appendChild(auditDownload);
      var skillTask = el('select'); ['Suspect words', 'Whole text'].forEach(function (label, i) { var op = el('option', label); op.value = i ? 'audit-' : ''; skillTask.appendChild(op); }); var skillLabel = el('label', 'Skill to check or install '); skillLabel.appendChild(skillTask); box.appendChild(skillLabel);
      box.appendChild(el('p', 'For Unsloth Studio, extract the skill folder into .agents/skills on the endpoint computer, or install it below. Enable it in Studio. Other software must support Agent Skills through its API.'));
      var enabled = !!(config && config.configured && config.adapter === 'unsloth-agent-skills');
      if (!enabled) useSkill = false;
      var label = el('label', 'Use installed skill for the chosen review '), check = el('input'); check.id = 'stt_use_skill'; check.type = 'checkbox'; check.checked = useSkill;
      check.disabled = !enabled || phase === 'correcting'; check.addEventListener('change', function () { useSkill = check.checked; }); label.appendChild(check); box.appendChild(label);
      box.appendChild(el('p', enabled ? 'Skill requests ask Unsloth to load @parseh-asr-correction; only read_skill is enabled, with MCP off. Skills supply instructions to the same model.' : 'Select the Unsloth Agent Skills adapter in LLM Integration to use an installed skill. The short prompt remains available.'));
      var state = el('p'); state.setAttribute('role', 'status'); state.setAttribute('aria-live', 'polite');
      var inspectSkill, install;
      function operation(name) {
        inspectSkill.disabled = install.disabled = true; state.textContent = name === 'skill-install' ? 'Installing the correction skill at the saved endpoint…' : 'Checking the installed skill…';
        fetch('/settings/api/llm/' + skillTask.value + name, {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})
          .then(function (r) { return r.json(); }).then(function (j) {
            if (!j.ok) throw new Error(j.error);
            state.textContent = j.ready ? 'Selected skill is installed and enabled. Select Use installed skill before starting its review.' : j.installed ? 'Skill exists; enable it in Unsloth Studio.' : 'Selected skill is not installed.';
          }).catch(function (e) { state.textContent = e.message || 'The endpoint did not answer.'; })
          .finally(function () { inspectSkill.disabled = !enabled || phase === 'correcting' || useBusy; install.disabled = !enabled || !config.can_install_skill || phase === 'correcting' || useBusy; });
      }
      inspectSkill = btn('Check installed skill', function () { operation('skill-status'); }); inspectSkill.disabled = !enabled || phase === 'correcting'; box.appendChild(inspectSkill);
      install = btn('Install in saved endpoint', function () { operation('skill-install'); }); install.disabled = !enabled || !config.can_install_skill || phase === 'correcting'; box.appendChild(install);
      box.appendChild(state); root.appendChild(box);
    }

    function showResponses(history, clipped) {
      if (!responses) return;
      var open = {};
      Array.prototype.forEach.call(responses.querySelectorAll('[data-response-key]'), function (n) { open[n.getAttribute('data-response-key')] = n.open; });
      responses.textContent = '';
      responses.appendChild(el('summary', 'LLM responses (' + history.length + ')'));
      responses.appendChild(el('p', 'Actual prompts and model output for this review. Kept temporarily with this job; never written to logs or synced. Reasoning is shown separately when the endpoint supplies it.'));
      if (clipped) responses.appendChild(el('p', 'Older or oversized diagnostics were clipped to keep this review bounded.'));
      if (!history.length) responses.appendChild(el('p', phase === 'correcting' ? 'Waiting for the first model response…' : 'No model responses for this review.'));
      history.forEach(function (trace, i) {
        var entry = el('details');
        var traceKey = trace.run + ':' + trace.sentence_id + ':' + trace.attempt;
        entry.setAttribute('data-response-key', traceKey); entry.open = !!open[traceKey];
        entry.appendChild(el('summary', 'Response ' + (i + 1) + ' · ' + (trace.word_ids || []).length + ' suspect words · ' + trace.state +
          ' · ' + (trace.elapsed_seconds == null ? '' : trace.elapsed_seconds + ' s') + (trace.finish_reason ? ' · finish: ' + trace.finish_reason : '')));
        if (trace.error) entry.appendChild(el('p', trace.error, 'warn'));
        entry.appendChild(el('h4', 'Whisper region'));
        var original = el('pre', trace.source || ''); original.dir = 'auto'; entry.appendChild(original);
        entry.appendChild(el('h4', 'Final answer'));
        var answer = el('pre', trace.answer || '(No final answer returned)'); answer.dir = 'auto'; entry.appendChild(answer);
        if (trace.raw_answer && trace.raw_answer !== trace.answer) {
          var raw = el('details'); raw.appendChild(el('summary', 'Raw answer content'));
          var rawText = el('pre', trace.raw_answer); rawText.dir = 'auto'; raw.appendChild(rawText); entry.appendChild(raw);
        }
        if (trace.reasoning) {
          var reasoning = el('details'); reasoning.appendChild(el('summary', 'Reasoning returned by the endpoint'));
          var thought = el('pre', trace.reasoning); thought.dir = 'auto'; reasoning.appendChild(thought); entry.appendChild(reasoning);
        }
        var prompt = el('details'); prompt.appendChild(el('summary', 'Exact short prompt'));
        (trace.prompt || []).forEach(function (message) { prompt.appendChild(el('h4', message.role)); var text = el('pre', message.content); text.dir = 'auto'; prompt.appendChild(text); });
        entry.appendChild(prompt);
        if (trace.ignored_edits && trace.ignored_edits.length) {
          entry.appendChild(el('p', trace.ignored_edits.length + ' changes outside flagged words or across ambiguous spans were ignored. Caption text is only changed by accepted word edits.'));
          trace.ignored_edits.forEach(function (edit) { entry.appendChild(el('p', edit.original + ' → ' + edit.replacement + ' · ' + edit.reason)); });
        }
        if (trace.response_clipped) entry.appendChild(el('p', 'Long raw output was clipped for display.'));
        responses.appendChild(entry);
      });
    }
    function disableControls(on) {
      if (on) {
        disabledBefore = Array.prototype.slice.call(root.querySelectorAll('button, input')).filter(function (b) { return b.id !== 'stt_review_cancel'; })
          .map(function (b) { var old = [b, b.disabled]; b.disabled = true; return old; });
      } else {
        disabledBefore.forEach(function (old) { old[0].disabled = old[1]; }); disabledBefore = [];
      }
    }
    function idsFor(id) {
      var manual = manualEdits[id];
      return manual != null ? typeof manual === 'object' ? manual.word_ids : [id] : suggestions[id] && suggestions[id].word_ids || [id];
    }
    function clearOverlaps(ids) {
      Object.keys(decisions).forEach(function (id) { if (idsFor(id).some(function (member) { return ids.indexOf(member) >= 0; })) delete decisions[id]; });
      Object.keys(manualEdits).forEach(function (id) { if (idsFor(id).some(function (member) { return ids.indexOf(member) >= 0; })) delete manualEdits[id]; });
    }
    function accepted(id) {
      return Object.keys(decisions).concat(Object.keys(manualEdits)).some(function (key) { return idsFor(key).indexOf(id) >= 0; });
    }
    function draft() {
      var chars = Array.from(result.text), edits = [];
      Object.keys(decisions).forEach(function (id) {
        var w = words[id], s = suggestions[id];
        if (w && s) edits.push({a: s.span_start == null ? w.span_start : s.span_start, b: s.span_end == null ? w.span_end : s.span_end, text: s.candidates[decisions[id]].text});
      });
      Object.keys(manualEdits).forEach(function (id) {
        var w = words[id];
        if (w) { var value = manualEdits[id], ids = idsFor(id); edits.push({a: w.span_start, b: words[ids[ids.length - 1]].span_end, text: typeof value === 'object' ? value.text : value}); }
      });
      edits.sort(function (a, b) { return b.a - a.a; });
      edits.forEach(function (e) { chars.splice.apply(chars, [e.a, e.b - e.a].concat(Array.from(e.text))); });
      return chars.join('');
    }
    function updateDraft() {
      preview.textContent = draft();
      status.textContent = Object.keys(decisions).length + ' LLM edits accepted and ' + Object.keys(manualEdits).length + ' manual edits in this draft. The transcript box has not changed.';
      Object.keys(words).forEach(function (id) {
        var button = root.querySelector('[data-review-word="' + id + '"]');
        if (button) button.classList.toggle('asr-accepted', accepted(id));
      });
      if (retry) { var remaining = retryWords(); retry.textContent = 'Retry all remaining suspect words (' + remaining.length + ')'; retry.disabled = !remaining.length || !config || !config.configured; }
    }
    function retryWords() { return Object.keys(words).filter(function (id) { return words[id].reviewable && (words[id].low_asr_score || result.review.result && (result.review.result.failed_word_ids || []).indexOf(id) >= 0) && !accepted(id); }); }
    function detail(w) {
      if (!w || useBusy) return;
      selected = w.word_id;
      details.textContent = '';
      var heading = el('h3', 'Word details'); heading.tabIndex = -1;
      details.appendChild(heading);
      var original = el('bdi', w.text); original.dir = 'auto'; details.appendChild(original);
      details.appendChild(el('p', 'Whisper timestamp: ' + time(w.start) + ' – ' + time(w.end) +
        ' · Whisper ASR score: ' + estimate(w.asr_confidence)));
      if (w.low_asr_score) details.appendChild(el('p', '⚠ Low ASR score: below ' + result.review.evidence.low_score_threshold + '. This is recognition evidence, not proof the word is wrong.'));
      if (w.asr_confidence == null) details.appendChild(el('p', 'Whisper supplied no word score.'));
      if (!w.alternatives_available) details.appendChild(el('p', 'ASR alternatives are unavailable from this recognizer.'));
      else {
        details.appendChild(el('p', 'Available ASR alternatives (ASR scores):'));
        var list = el('ul');
        w.asr_alternatives.forEach(function (a) { list.appendChild(el('li', a.text + ' · ' + estimate(a.score))); });
        details.appendChild(list);
      }
      if (!w.reviewable) details.appendChild(el('p', 'This word could not be matched to an exact transcript span. Review it manually.'));
      var s = suggestions[w.word_id], manualKey = Object.keys(manualEdits).find(function (key) { return idsFor(key).indexOf(w.word_id) >= 0; });
      var editId = s ? s.word_id : manualKey || w.word_id, editIds = s && s.word_ids || (manualKey ? idsFor(manualKey) : [w.word_id]);
      var sourceSpan = Array.from(result.text).slice(words[editIds[0]].span_start, words[editIds[editIds.length - 1]].span_end).join('');
      if (s) {
        if (editIds.length > 1) { details.appendChild(el('p', 'Proposed source span: ' + s.original)); (s.asr_evidence || []).forEach(function (piece) { details.appendChild(el('p', piece.text + ' · Whisper ASR score: ' + estimate(piece.asr_confidence) + ' · ' + time(piece.start) + ' – ' + time(piece.end))); }); }
        details.appendChild(el('p', '✎ LLM word substitution' + (s.error_likelihood == null ? '' : ' · Error likelihood (model estimate): ' + estimate(s.error_likelihood))));
        if (s.reason) details.appendChild(el('p', s.reason));
        var alternatives = el('ol');
        s.candidates.forEach(function (c, i) {
          var li = el('li'), surface = el('bdi', c.text); surface.dir = 'auto'; li.appendChild(surface);
          if (c.confidence != null || c.reason) li.appendChild(el('p', (c.confidence == null ? '' : 'Confidence (model estimate): ' + estimate(c.confidence) + '. ') + (c.reason || '')));
          li.appendChild(btn(decisions[editId] === i ? 'Accepted in draft' : 'Accept this alternative', function () {
            clearOverlaps(editIds); decisions[editId] = i; updateDraft(); detail(w);
          }));
          alternatives.appendChild(li);
        });
        details.appendChild(alternatives);
        details.appendChild(btn('Reject this edit / keep Whisper word', function () { delete decisions[editId]; updateDraft(); detail(w); }));
      } else if (w.low_asr_score) details.appendChild(el('p', 'No LLM edit is proposed for this word. It stays unchanged.'));
      if (w.reviewable) {
        var label = el('label', editIds.length > 1 ? 'Enter the correct short span ' : 'Enter the correct word '), input = el('input');
        input.type = 'text'; input.id = 'stt_manual_word'; input.dir = 'auto'; input.maxLength = 200;
        var manual = manualEdits[editId]; input.value = manual != null ? typeof manual === 'object' ? manual.text : manual : s ? s.original : sourceSpan; label.appendChild(input); details.appendChild(label);
        var note = el('p', 'Manual edits change only the selected word or span in the pending draft.'); note.setAttribute('role', 'status'); details.appendChild(note);
        function saveManual() {
          var value = input.value.trim();
          if (!value || editIds.length === 1 && /\s/.test(value) || Array.from(value).length > 200 || /[\x00-\x1f]/.test(value)) { note.textContent = 'Enter a nonempty word or selected short span, without line breaks.'; return; }
          clearOverlaps(editIds);
          if (value !== (s ? s.original : sourceSpan)) manualEdits[editId] = editIds.length > 1 ? {text: value, word_ids: editIds.slice()} : value;
          updateDraft(); note.textContent = 'Word saved in the pending draft.';
        }
        input.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); saveManual(); } });
        details.appendChild(btn('Save word in draft', saveManual));
        details.appendChild(btn('Restore Whisper word', function () { clearOverlaps(editIds); updateDraft(); detail(w); }));
      }
    }
    function render() {
      root.textContent = ''; root.hidden = false;
      root.appendChild(el('h3', phase === 'choice' ? 'Choose how to review the Whisper transcript' : 'Review transcript'));
      choice = el('div', null, 'row');
      var llm = btn('Review suspect words with the LLM', function () { opts.choose('llm', useSkill, 'suspect'); });
      var audit = btn('Review the whole text with the LLM', function () { opts.choose('llm', useSkill, 'full'); }); audit.id = 'stt_review_full'; audit.disabled = !config || !config.configured || phase === 'correcting';
      llm.id = 'stt_review_llm'; llm.disabled = !config || !config.configured || phase === 'correcting';
      var whisper = btn('Review Whisper result without the LLM', function () { opts.choose('whisper'); });
      whisper.id = 'stt_review_whisper'; whisper.disabled = phase === 'correcting';
      var remember = el('label', 'Remember my default choice in this browser '), check = el('input');
      check.type = 'checkbox'; check.id = 'stt_review_remember';
      remember.appendChild(check);
      var preferred = '';
      try { preferred = localStorage.getItem('yt_asr_review_default') || ''; } catch (e) {}
      check.checked = !!preferred;
      function preference(mode) {
        try { if (check.checked) localStorage.setItem('yt_asr_review_default', mode); else localStorage.removeItem('yt_asr_review_default'); } catch (e) {}
      }
      llm.addEventListener('click', function () { preference('llm'); });
      whisper.addEventListener('click', function () { preference('whisper'); });
      check.addEventListener('change', function () { if (!check.checked) { try { localStorage.removeItem('yt_asr_review_default'); } catch (e) {} } });
      if (preferred === 'llm') llm.classList.add('go'); else if (preferred === 'whisper') whisper.classList.add('go');
      // Preference only marks a button. It never dispatches a request.
      choice.appendChild(llm); choice.appendChild(audit); choice.appendChild(whisper); choice.appendChild(remember); root.appendChild(choice);
      root.appendChild(el('p', config && config.configured ? 'LLM destination: ' + config.base_url + ' · Selected model: ' + config.selected_model + '. Choosing LLM review sends bounded text and Whisper evidence; audio is never sent.' : 'LLM Integration is unconfigured. Whisper-only review sends nothing to an LLM.'));
      if (config && config.configured) ['suspect', 'full'].forEach(function (task) { var setting = config.review_models && config.review_models[task]; root.appendChild(el('p', (task === 'full' ? 'Whole-text review' : 'Suspect-word review') + ': ' + (setting ? setting.model_id : config.selected_model) + (setting && setting.profile_id ? ' · Saved Studio profile will be loaded when this review starts.' : ''))); });
      var settings = el('a', 'LLM Integration settings'); settings.href = '/settings/llm/'; settings.target = '_blank'; settings.rel = 'noopener'; root.appendChild(settings);
      skillControls();
      var c = result.review && result.review.correction || {};
      if (c.error) root.appendChild(el('p', c.error + ' Retry LLM review or continue with Whisper.', 'warn'));
      status = el('p', '', 'stt-review-status'); status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite'); root.appendChild(status);
      var cancelled = btn(phase === 'correcting' ? 'Cancel LLM review' : 'Cancel review', opts.cancel);
      cancelled.id = 'stt_review_cancel'; root.appendChild(cancelled);
      responses = el('details', null, 'stt-llm-responses'); responses.id = 'stt_llm_responses'; root.appendChild(responses);
      showResponses(result.review && result.review.diagnostics || [], result.review && result.review.diagnostics_clipped);
      if (phase === 'choice' || phase === 'correcting') return;
      root.appendChild(el('p', '⚠ = low Whisper ASR score. ✎ = LLM edit proposal. Accepted and manual edits are underlined. Focus, hover or tap any word for details or to edit it.'));
      var reviewed = result.review && result.review.result;
      if (reviewed && reviewed.failed_word_ids && reviewed.failed_word_ids.length) root.appendChild(el('p', 'LLM review had problems with ' + reviewed.failed_word_ids.length + ' words. Other sentences were processed normally. Their Whisper words remain available; retry remaining suspect words or edit them yourself.', 'warn'));
      if (reviewed && !reviewed.suggestions.length) root.appendChild(el('p', reviewed.assessment === 'no_flagged_words' ? 'Whisper had no words below the ASR score threshold that could be reviewed. No text was sent to the LLM.' : reviewed.failed_word_ids && reviewed.failed_word_ids.length ? 'Some sentences could not be reviewed. Their words remain as Whisper returned them.' : reviewed.assessment === 'kept_original' ? 'The model kept the suspect words unchanged. This does not establish that they are correct; review their Whisper evidence.' : reviewed.assessment === 'uncertain' ? 'The model cannot tell whether a correction is needed. No words have been changed.' : 'The model reported no likely recognition error. No words have been changed.'));
      inspect = el('div', null, 'stt-review-text'); inspect.dir = 'auto';
      details = el('aside', 'Select a marked word for its evidence and alternatives.', 'stt-review-details');
      details.id = 'stt_review_details'; details.setAttribute('role', 'region'); details.setAttribute('aria-label', 'Word evidence and proposed edits'); details.setAttribute('aria-live', 'polite');
      var evidence = result.review && result.review.evidence;
      if (evidence) evidence.segments.forEach(function (seg) {
        var row = el('p'), clock = el('span', time(seg.start) + '  ', 'stt-review-clock'); row.appendChild(clock);
        var text = el('span'), cursor = 0; text.dir = 'auto';
        seg.words.forEach(function (w) {
          var at = seg.text.indexOf(w.text, cursor); if (at < 0) return;
          text.appendChild(document.createTextNode(seg.text.slice(cursor, at)));
          var s = suggestions[w.word_id];
          if (w.reviewable || w.low_asr_score || s) {
            var b = btn((w.low_asr_score ? '⚠ ' : '') + (s ? '✎ ' : '') + w.text, function () { detail(w); });
            b.className = 'stt-review-word' + (w.low_asr_score ? ' asr-low' : '') + (s ? ' asr-proposal' : '');
            b.setAttribute('data-review-word', w.word_id); b.setAttribute('aria-controls', details.id);
            b.setAttribute('aria-label', w.text + (w.low_asr_score ? ', low Whisper ASR score' : '') + (s ? ', LLM edit proposed' : ''));
            b.addEventListener('focus', function () { detail(w); });
            b.addEventListener('keydown', function (e) {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault(); detail(w);
                var target = details.querySelector('input') || details.querySelector('h3');
                if (target) target.focus();
              }
            });
            b.addEventListener('mouseenter', function () { if (!details.contains(document.activeElement)) detail(w); });
            text.appendChild(b);
          } else text.appendChild(document.createTextNode(w.text));
          cursor = at + w.text.length;
        });
        text.appendChild(document.createTextNode(seg.text.slice(cursor))); row.appendChild(text); inspect.appendChild(row);
      });
      else inspect.appendChild(el('pre', result.text));
      root.appendChild(inspect); root.appendChild(details);
      var previewBox = el('details'); previewBox.appendChild(el('summary', 'Pending transcript draft'));
      preview = el('pre'); preview.dir = 'auto'; previewBox.appendChild(preview); root.appendChild(previewBox);
      retry = btn('Retry all remaining suspect words', function () { if (opts.retry) opts.retry(retryWords(), useSkill, result.review.result && result.review.result.task || 'suspect'); }); retry.id = 'stt_review_retry'; root.appendChild(retry);
      use = btn('Use this transcript', function () { opts.use(Object.assign({}, decisions), Object.assign({}, manualEdits)); }); use.id = 'stt_use';
      root.appendChild(use); updateDraft();
      if (selected && words[selected]) detail(words[selected]);
      if (useBusy) disableControls(true);
    }
    return {
      show: function (res, state, connection) {
        var before = result && result.review && result.review.evidence && result.review.evidence.source_sha256;
        var after = res.review && res.review.evidence && res.review.evidence.source_sha256;
        if (before !== after || state === 'choice') { decisions = {}; manualEdits = {}; selected = null; }
        var previousSuggestions = suggestions; result = res; phase = state; config = connection; suggestions = {}; words = {};
        ((res.review && res.review.result && res.review.result.suggestions) || []).forEach(function (s) { (s.word_ids || [s.word_id]).forEach(function (id) { suggestions[id] = s; }); });
        ((res.review && res.review.evidence && res.review.evidence.segments) || []).forEach(function (s) { s.words.forEach(function (w) { words[w.word_id] = w; }); });
        Object.keys(decisions).forEach(function (id) { if (JSON.stringify(previousSuggestions[id]) !== JSON.stringify(suggestions[id])) delete decisions[id]; });
        render();
      },
      progress: function (say) { if (status) status.textContent = say; },
      diagnostics: function (history, clipped) { showResponses(history || [], clipped); },
      resetProposals: function () { decisions = {}; },
      disableUse: function (on) { useBusy = on; disableControls(on); },
      clear: function () { result = null; decisions = {}; manualEdits = {}; useBusy = false; disabledBefore = []; root.textContent = ''; root.hidden = true; }
    };
  }
  window.ParsehAsrReview = {mount: mount};
})();
