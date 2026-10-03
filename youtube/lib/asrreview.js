// SPDX-License-Identifier: GPL-3.0-or-later
/* Pending browser review. All text is textContent; source offsets are Unicode code points. */
(function () {
  'use strict';
  function el(tag, text, cls) { var n = document.createElement(tag); if (text != null) n.textContent = text; if (cls) n.className = cls; return n; }
  function btn(text, fn) { var b = el('button', text, 'wbtn small quiet'); b.type = 'button'; b.addEventListener('click', fn); return b; }
  function time(n) { return typeof n === 'number' ? n.toFixed(2) + ' s' : 'unavailable'; }
  function estimate(n) { return typeof n === 'number' ? n.toFixed(2) : 'unavailable'; }
  function captionTime(n) {
    if (typeof n !== 'number') return 'Time unavailable';
    var total = Math.max(0, Math.round(n * 100)), seconds = Math.floor(total / 100), fraction = total % 100;
    var minutes = Math.floor(seconds / 60), hours = Math.floor(minutes / 60);
    function two(value) { return String(value).padStart(2, '0'); }
    return (hours ? hours + ':' + two(minutes % 60) : String(minutes)) + ':' + two(seconds % 60) + (fraction ? '.' + two(fraction) : '');
  }
  function mount(root, opts) {
    var result = null, phase = '', config = null, decisions = {}, manualEdits = {}, suggestions = {}, words = {}, selected = null;
    var choice, inspect, details, preview, status, use, responses, retry, useSkill = false, useBusy = false, disabledBefore = [];
    var wordButtons = {}, captions = {}, captionRows = [], filter = 'all', search = '', summary, activeCaption = null;
    var dictionaryCache = new Map();
    function suspect(w) { return w.low_asr_score || w.dictionary_miss; }
    function dictionaryCard(box, data) {
      box.textContent = '';
      if (!data || data.state === 'failed') { box.appendChild(el('p', 'Dictionary lookup could not finish.')); return; }
      if (data.state === 'unavailable') { box.appendChild(el('p', 'No dictionary is installed for this language.')); return; }
      if (data.state === 'not-word') { box.appendChild(el('p', 'No lexical word to look up.')); return; }
      if (data.state === 'missing') box.appendChild(el('p', '◇ No meaning found. Names and rare words may be absent from this dictionary.'));
      (data.words || []).forEach(function (row) {
        (row.hits || []).forEach(function (hit) {
          var title = el('p'), head = el('bdi', hit.headword); head.dir = 'auto'; title.appendChild(head);
          if (hit.pos) title.appendChild(document.createTextNode(' · ' + hit.pos)); box.appendChild(title);
          if (hit.note) box.appendChild(el('p', hit.note, 'fieldnote'));
          var senses = el('ul'); (hit.senses || []).forEach(function (sense) { var meaning = el('li', sense); meaning.dir = 'auto'; senses.appendChild(meaning); }); box.appendChild(senses);
        });
        if (!row.hits.length && row.tried.length) box.appendChild(el('p', 'Forms checked: ' + row.tried.join(', '), 'fieldnote'));
      });
      if (data.source) box.appendChild(el('p', data.source + ' · Meanings in ' + data.senses_language, 'fieldnote'));
    }
    function dictionaryDetails(w, originalBox, candidateBoxes, proposal) {
      if (!opts.dictionary) { dictionaryCard(originalBox, null); return; }
      var key = result.review.evidence.source_sha256 + ':' + w.word_id + ':' + JSON.stringify(proposal && proposal.candidates || []);
      var promise = dictionaryCache.get(key);
      if (!promise) {
        promise = opts.dictionary(w.word_id).catch(function () { return null; });
        dictionaryCache.set(key, promise);
        if (dictionaryCache.size > 200) dictionaryCache.delete(dictionaryCache.keys().next().value);
      }
      promise.then(function (data) {
        if (!root.contains(originalBox)) return;
        dictionaryCard(originalBox, data && data.original);
        candidateBoxes.forEach(function (box, i) { dictionaryCard(box, data && data.candidates[i]); });
      });
    }

    function skillControls() {
      var box = el('details'); box.setAttribute('data-review-disclosure', 'skill'); box.appendChild(el('summary', 'Correction skill'));
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
        disabledBefore = Array.prototype.slice.call(root.querySelectorAll('button, input, select')).filter(function (b) { return b.id !== 'stt_review_cancel'; })
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
      var applied = {}, suppressed = {};
      Object.keys(decisions).concat(Object.keys(manualEdits)).forEach(function (id) {
        var ids = idsFor(id), manual = manualEdits[id];
        applied[id] = manual != null ? typeof manual === 'object' ? manual.text : manual : suggestions[id].candidates[decisions[id]].text;
        ids.slice(1).forEach(function (member) { suppressed[member] = true; });
      });
      Object.keys(wordButtons).forEach(function (id) {
        var button = wordButtons[id], changed = applied[id] != null || suppressed[id];
        button.classList.toggle('asr-accepted', !!changed);
        button.hidden = !!suppressed[id];
        button.textContent = applied[id] == null ? words[id].text : applied[id];
        button.setAttribute('aria-label', words[id].text + (applied[id] != null ? ', changed in draft to ' + applied[id] : '') +
          (words[id].low_asr_score ? ', low Whisper ASR score' : '') + (suggestions[id] ? ', LLM edit proposed' : ''));
        if (words[id].dictionary_miss) button.setAttribute('aria-label', button.getAttribute('aria-label') + ', no dictionary meaning found');
      });
      if (retry) { var remaining = retryWords(); retry.textContent = 'Retry remaining suspect words (' + remaining.length + ')'; retry.disabled = phase !== 'review' || !remaining.length || !config || !config.configured; }
      var all = Object.keys(words), low = all.filter(function (id) { return words[id].low_asr_score; }).length;
      var missing = all.filter(function (id) { return words[id].dictionary_miss; }).length;
      if (summary) summary.textContent = low + ' low-score words · ' + missing + ' dictionary misses · ' + Object.keys(suggestions).length + ' words with proposals · ' +
        (Object.keys(decisions).length + Object.keys(manualEdits).length) + ' edits saved';
      applyFilter();
    }
    function retryWords() { return Object.keys(words).filter(function (id) { return words[id].reviewable && (suspect(words[id]) || result.review.result && (result.review.result.failed_word_ids || []).indexOf(id) >= 0) && !accepted(id); }); }
    function detail(w, hover) {
      if (!w || useBusy) return;
      if (!hover) {
        if (selected && wordButtons[selected]) wordButtons[selected].removeAttribute('aria-current');
        selected = w.word_id;
        if (wordButtons[selected]) wordButtons[selected].setAttribute('aria-current', 'true');
        if (opts.select && captions[selected]) opts.select(w, captions[selected], false);
      }
      details.textContent = '';
      var heading = el('h3', 'Word details'); heading.tabIndex = -1;
      details.appendChild(heading);
      var original = el('bdi', w.text); original.dir = 'auto'; details.appendChild(original);
      if (opts.select && captions[w.word_id]) details.appendChild(btn('Listen to this word', function () { detail(w); opts.select(w, captions[w.word_id], true); }));
      details.appendChild(el('p', 'Whisper timestamp: ' + time(w.start) + ' – ' + time(w.end) +
        ' · Whisper ASR score: ' + estimate(w.asr_confidence)));
      if (w.low_asr_score) details.appendChild(el('p', '⚠ Low ASR score: below ' + result.review.evidence.low_score_threshold + '. This is recognition evidence, not proof the word is wrong.'));
      if (w.dictionary_miss) details.appendChild(el('p', '◇ No meaning found in the installed dictionary. This word is also a suspect-word review target. Names and rare words can be valid.'));
      if (w.asr_confidence == null) details.appendChild(el('p', 'Whisper supplied no word score.'));
      if (!w.alternatives_available) details.appendChild(el('p', 'ASR alternatives are unavailable from this recognizer.'));
      else {
        details.appendChild(el('p', 'Native Whisper alternatives. Sequence log scores rank complete hypotheses; they are not word probabilities.'));
        var list = el('ul');
        w.asr_alternatives.forEach(function (a) { list.appendChild(el('li', a.text + ' · ' + (a.sequence_score == null ? 'Word score: ' + estimate(a.score) : 'Sequence log score: ' + estimate(a.sequence_score)))); });
        if (!w.asr_alternatives.length) list.appendChild(el('li', 'No unambiguous word alternatives returned.'));
        details.appendChild(list);
      }
      if (!w.reviewable) details.appendChild(el('p', 'This word could not be matched to an exact transcript span. Review it manually.'));
      var s = suggestions[w.word_id], manualKey = Object.keys(manualEdits).find(function (key) { return idsFor(key).indexOf(w.word_id) >= 0; });
      var originalDictionary = el('div', 'Looking up the Whisper word…', 'stt-review-dictionary'), candidateDictionaries = [];
      originalDictionary.setAttribute('role', 'status');
      details.appendChild(el('h4', 'Whisper dictionary meanings')); details.appendChild(originalDictionary);
      var editId = s ? s.word_id : manualKey || w.word_id, editIds = s && s.word_ids || (manualKey ? idsFor(manualKey) : [w.word_id]);
      var sourceSpan = Array.from(result.text).slice(words[editIds[0]].span_start, words[editIds[editIds.length - 1]].span_end).join('');
      if (s && phase === 'review') {
        if (editIds.length > 1) { details.appendChild(el('p', 'Proposed source span: ' + s.original)); (s.asr_evidence || []).forEach(function (piece) { details.appendChild(el('p', piece.text + ' · Whisper ASR score: ' + estimate(piece.asr_confidence) + ' · ' + time(piece.start) + ' – ' + time(piece.end))); }); }
        details.appendChild(el('p', '✎ LLM word substitution' + (s.error_likelihood == null ? '' : ' · Error likelihood (model estimate): ' + estimate(s.error_likelihood))));
        if (s.reason) details.appendChild(el('p', s.reason));
        var alternatives = el('ol');
        s.candidates.forEach(function (c, i) {
          var li = el('li'), surface = el('bdi', c.text); surface.dir = 'auto'; li.appendChild(surface);
          if (c.confidence != null || c.reason) li.appendChild(el('p', (c.confidence == null ? '' : 'Confidence (model estimate): ' + estimate(c.confidence) + '. ') + (c.reason || '')));
          var candidateDictionary = el('div', 'Looking up this alternative…', 'stt-review-dictionary'); candidateDictionary.setAttribute('role', 'status');
          li.appendChild(candidateDictionary); candidateDictionaries.push(candidateDictionary);
          li.appendChild(btn(decisions[editId] === i ? 'Accepted in draft' : 'Accept this alternative', function () {
            clearOverlaps(editIds); decisions[editId] = i; updateDraft(); detail(w);
          }));
          alternatives.appendChild(li);
        });
        details.appendChild(alternatives);
        details.appendChild(btn('Reject this edit / keep Whisper word', function () { delete decisions[editId]; updateDraft(); detail(w); }));
      } else if (suspect(w)) details.appendChild(el('p', 'No LLM edit is proposed for this word. It stays unchanged.'));
      dictionaryDetails(w, originalDictionary, candidateDictionaries, s);
      if (w.reviewable && phase === 'review') {
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
      if (phase !== 'review') details.appendChild(el('p', phase === 'correcting' ? 'You can listen and inspect the evidence while the model works. Editing becomes available when this review finishes.' : 'Choose Whisper-only or LLM review above to start editing.'));
    }
    function applyFilter() {
      var query = search.trim().toLocaleLowerCase(), visible = 0;
      captionRows.forEach(function (item) {
        var seg = item.segment, relevant = filter === 'all' || seg.words.some(function (w) {
          return filter === 'proposals' ? !!suggestions[w.word_id] : suspect(w) || !!suggestions[w.word_id] ||
            result.review.result && (result.review.result.failed_word_ids || []).indexOf(w.word_id) >= 0;
        });
        item.row.hidden = !relevant || !!query && seg.text.toLocaleLowerCase().indexOf(query) < 0;
        if (!item.row.hidden) visible++;
      });
      var empty = root.querySelector('.stt-review-empty');
      if (empty) empty.hidden = !captionRows.length || visible > 0;
    }
    function navigateIssue(direction) {
      var ids = Object.keys(wordButtons).filter(function (id) {
        return !wordButtons[id].hidden && !wordButtons[id].closest('.stt-caption').hidden && (suspect(words[id]) || suggestions[id]);
      });
      if (!ids.length) return;
      var at = ids.indexOf(selected), next = ids[(at < 0 ? direction > 0 ? 0 : ids.length - 1 : (at + direction + ids.length) % ids.length)];
      wordButtons[next].focus({preventScroll: true});
      wordButtons[next].scrollIntoView({block: 'nearest'});
      detail(words[next]);
      if (opts.select) opts.select(words[next], captions[next], true);
    }
    function render() {
      var scroll = inspect ? inspect.scrollTop : 0, opened = {};
      Array.prototype.forEach.call(root.querySelectorAll('[data-review-disclosure]'), function (box) { opened[box.getAttribute('data-review-disclosure')] = box.open; });
      root.textContent = ''; root.hidden = false; wordButtons = {}; captions = {}; captionRows = []; activeCaption = null;
      var top = el('div', null, 'stt-review-head');
      top.appendChild(el('h3', phase === 'choice' ? 'Choose your review' : phase === 'correcting' ? 'Review in progress' : 'Review transcript'));
      summary = el('p', '', 'fieldnote'); top.appendChild(summary); root.appendChild(top);
      choice = el('div', null, 'stt-review-choices');
      var llm = btn('Review suspect words with the LLM', function () { opts.choose('llm', useSkill, 'suspect'); });
      var audit = btn('Review the whole text with the LLM', function () { opts.choose('llm', useSkill, 'full'); }); audit.id = 'stt_review_full';
      audit.disabled = !config || !config.configured || phase === 'correcting';
      llm.id = 'stt_review_llm'; llm.disabled = !config || !config.configured || phase === 'correcting';
      var whisper = btn('Review Whisper result without the LLM', function () { opts.choose('whisper'); });
      whisper.id = 'stt_review_whisper'; whisper.disabled = phase === 'correcting';
      [whisper, llm, audit].forEach(function (button) { choice.appendChild(button); });
      if (phase === 'choice') root.appendChild(choice);
      else {
        var another = el('details', null, 'stt-review-options'); another.setAttribute('data-review-disclosure', 'method');
        another.appendChild(el('summary', 'Change review method')); another.appendChild(choice); root.appendChild(another);
      }
      var destination = el('p', config && config.configured ? 'Send text to ' + config.base_url + ' · Audio is never sent.' : 'No LLM configured. Whisper-only review is available.', 'stt-review-destination');
      var settings = el('a', 'LLM settings'); settings.href = '/settings/llm/'; settings.target = '_blank'; settings.rel = 'noopener';
      destination.appendChild(document.createTextNode(' ')); destination.appendChild(settings); root.appendChild(destination);
      var advanced = el('details', null, 'stt-review-options'); advanced.setAttribute('data-review-disclosure', 'options');
      advanced.appendChild(el('summary', 'Models, preferences & skills'));
      root.appendChild(advanced);
      if (config && config.configured) ['suspect', 'full'].forEach(function (task) {
        var setting = config.review_models && config.review_models[task];
        advanced.appendChild(el('p', (task === 'full' ? 'Whole-text review' : 'Suspect-word review') + ': ' + (setting ? setting.model_id : config.selected_model) +
          (setting && setting.profile_id ? ' · Saved Studio profile loads when this review starts.' : '')));
      });
      var remember = el('label', 'Remember my default review choice in this browser '), check = el('input');
      check.type = 'checkbox'; check.id = 'stt_review_remember'; remember.appendChild(check); advanced.appendChild(remember);
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
      // Marking the preference never dispatches a request.
      skillControls(); advanced.appendChild(root.lastChild);
      var c = result.review && result.review.correction || {};
      if (c.error) root.appendChild(el('p', c.error + ' Retry LLM review or continue with Whisper.', 'warn'));
      var reviewed = result.review && result.review.result;
      if (reviewed && reviewed.failed_word_ids && reviewed.failed_word_ids.length) root.appendChild(el('p', 'LLM review had problems with ' + reviewed.failed_word_ids.length + ' words. Their Whisper text is intact. Retry unresolved words or edit them yourself.', 'warn'));
      if (reviewed && !reviewed.suggestions.length) root.appendChild(el('p', reviewed.assessment === 'no_flagged_words' ? 'No reviewable words had a low ASR score or a dictionary miss. No text was sent to the LLM.' : reviewed.failed_word_ids && reviewed.failed_word_ids.length ? 'Some sentences could not be reviewed. Their words remain unchanged.' : reviewed.assessment === 'uncertain' ? 'The model could not determine a correction. No words have changed.' : 'The model kept the words unchanged. This does not establish that they are correct.'));
      var toolbar = el('div', null, 'stt-review-tools');
      var filterLabel = el('label', 'Show '), picker = el('select'); picker.id = 'stt_review_filter';
      [['all', 'All captions'], ['attention', 'Needs attention'], ['proposals', 'LLM proposals']].forEach(function (option) { var n = el('option', option[1]); n.value = option[0]; picker.appendChild(n); });
      picker.value = filter; picker.addEventListener('change', function () { filter = picker.value; applyFilter(); }); filterLabel.appendChild(picker);
      var searchBox = el('input'); searchBox.type = 'search'; searchBox.placeholder = 'Find text…'; searchBox.value = search;
      searchBox.setAttribute('aria-label', 'Find text in captions'); searchBox.addEventListener('input', function () { search = searchBox.value; applyFilter(); });
      toolbar.appendChild(filterLabel); toolbar.appendChild(searchBox);
      toolbar.appendChild(btn('Previous issue', function () { navigateIssue(-1); })); toolbar.appendChild(btn('Next issue', function () { navigateIssue(1); })); root.appendChild(toolbar);
      var legend = el('p', '⚠ Low ASR score · ◇ No dictionary meaning · ✎ LLM proposal · ✓ Saved edit. Click a word to listen briefly and inspect; Enter opens its editor.', 'stt-review-legend'); root.appendChild(legend);
      if (result.review.evidence.dictionary && result.review.evidence.dictionary.failed) root.appendChild(el('p', 'Some dictionary lookups could not finish. Those failures do not flag words as incorrect.', 'fieldnote'));
      var body = el('div', null, 'stt-review-body');
      inspect = el('div', null, 'stt-review-text'); inspect.setAttribute('role', 'region'); inspect.setAttribute('aria-label', 'Timestamped transcript');
      details = el('aside', 'Select any word to inspect its evidence or enter a correction.', 'stt-review-details');
      details.id = 'stt_review_details'; details.setAttribute('role', 'region'); details.setAttribute('aria-label', 'Word evidence and proposed edits');
      var evidence = result.review && result.review.evidence;
      if (evidence) inspect.lang = evidence.language;
      if (evidence) evidence.segments.forEach(function (seg) {
        var row = el('div', null, 'stt-caption'), timestamp = btn(captionTime(seg.start), function () {
          if (seg.words.length && opts.select) { detail(seg.words[0]); opts.select(seg.words[0], seg, false); }
          if (opts.seek) opts.seek(seg.start, true, typeof seg.end === 'number' ? seg.end + .6 : null);
        });
        timestamp.className = 'stt-review-clock'; timestamp.setAttribute('aria-label', 'Play caption at ' + time(seg.start));
        row.appendChild(timestamp); row.setAttribute('data-review-segment', seg.segment_id);
        var text = el('p'), cursor = 0; text.dir = 'auto';
        seg.words.forEach(function (w) {
          var at = seg.text.indexOf(w.text, cursor); if (at < 0) return;
          text.appendChild(document.createTextNode(seg.text.slice(cursor, at)));
          var s = suggestions[w.word_id];
          if (w.reviewable || suspect(w) || s) {
            var b = btn(w.text, function () { detail(w); if (opts.select) opts.select(w, seg, true); });
            b.className = 'stt-review-word' + (w.low_asr_score ? ' asr-low' : '') + (w.dictionary_miss ? ' asr-dictionary' : '') + (s ? ' asr-proposal' : '');
            b.setAttribute('data-review-word', w.word_id); b.setAttribute('aria-controls', details.id);
            b.addEventListener('focus', function () { detail(w); });
            b.addEventListener('keydown', function (e) {
              if (e.key === 'Enter') {
                e.preventDefault(); detail(w); if (opts.select) opts.select(w, seg, true);
                var target = details.querySelector('input') || details.querySelector('h3'); if (target) target.focus();
              }
            });
            b.addEventListener('mouseenter', function () { if (!details.contains(document.activeElement)) detail(w, true); });
            b.addEventListener('mouseleave', function () { if (selected && words[selected] && !details.contains(document.activeElement)) detail(words[selected]); });
            wordButtons[w.word_id] = b; captions[w.word_id] = seg; text.appendChild(b);
          } else text.appendChild(document.createTextNode(w.text));
          cursor = at + w.text.length;
        });
        text.appendChild(document.createTextNode(seg.text.slice(cursor))); row.appendChild(text); inspect.appendChild(row);
        captionRows.push({row: row, segment: seg});
      });
      else inspect.appendChild(el('pre', result.text));
      var empty = el('p', 'No captions match this filter. Choose All captions or clear the search.', 'stt-review-empty'); empty.hidden = true; inspect.appendChild(empty);
      body.appendChild(inspect); body.appendChild(details); root.appendChild(body);
      var footer = el('div', null, 'stt-review-footer');
      status = el('p', '', 'stt-review-status'); status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite'); footer.appendChild(status);
      var actions = el('div', null, 'stt-review-actions');
      var cancelled = btn(phase === 'correcting' ? 'Cancel LLM review' : 'Discard review', opts.cancel); cancelled.id = 'stt_review_cancel'; actions.appendChild(cancelled);
      retry = btn('Retry remaining suspect words', function () { if (opts.retry) opts.retry(retryWords(), useSkill, result.review.result && result.review.result.task || 'suspect'); }); retry.id = 'stt_review_retry'; actions.appendChild(retry);
      use = btn('Use this transcript', function () { opts.use(Object.assign({}, decisions), Object.assign({}, manualEdits)); }); use.id = 'stt_use'; use.classList.add('go'); use.disabled = phase !== 'review'; actions.appendChild(use);
      footer.appendChild(actions); root.appendChild(footer);
      var previewBox = el('details', null, 'stt-review-options'); previewBox.setAttribute('data-review-disclosure', 'draft'); previewBox.appendChild(el('summary', 'Preview the complete pending transcript'));
      preview = el('pre'); preview.dir = 'auto'; previewBox.appendChild(preview); root.appendChild(previewBox);
      responses = el('details', null, 'stt-llm-responses'); responses.id = 'stt_llm_responses'; responses.setAttribute('data-review-disclosure', 'responses'); root.appendChild(responses);
      showResponses(result.review && result.review.diagnostics || [], result.review && result.review.diagnostics_clipped);
      updateDraft();
      if (phase === 'choice') status.textContent = 'Choose a review above. The transcript box has not changed.';
      if (phase === 'correcting') status.textContent = 'The model is reviewing the transcript. You can listen and inspect the Whisper evidence while it works.';
      Array.prototype.forEach.call(root.querySelectorAll('[data-review-disclosure]'), function (box) { box.open = !!opened[box.getAttribute('data-review-disclosure')]; });
      inspect.scrollTop = scroll;
      if (selected && words[selected]) detail(words[selected]);
      if (useBusy) disableControls(true);
    }
    return {
      show: function (res, state, connection) {
        var before = result && result.review && result.review.evidence && result.review.evidence.source_sha256;
        var after = res.review && res.review.evidence && res.review.evidence.source_sha256;
        if (before !== after) { decisions = {}; manualEdits = {}; selected = null; }
        if (before !== after) { filter = 'all'; search = ''; }
        var previousSuggestions = suggestions; result = res; phase = state; config = connection; suggestions = {}; words = {};
        ((res.review && res.review.result && res.review.result.suggestions) || []).forEach(function (s) { (s.word_ids || [s.word_id]).forEach(function (id) { suggestions[id] = s; }); });
        ((res.review && res.review.evidence && res.review.evidence.segments) || []).forEach(function (s) { s.words.forEach(function (w) { words[w.word_id] = w; }); });
        Object.keys(decisions).forEach(function (id) { if (JSON.stringify(previousSuggestions[id]) !== JSON.stringify(suggestions[id])) delete decisions[id]; });
        render();
      },
      playhead: function (at) {
        var item = captionRows.find(function (entry) { return at >= entry.segment.start && at < entry.segment.end; });
        var next = item && item.row;
        if (next === activeCaption) return;
        if (activeCaption) activeCaption.classList.remove('asr-playing');
        activeCaption = next; if (next) next.classList.add('asr-playing');
      },
      progress: function (say) { if (status) status.textContent = say; },
      diagnostics: function (history, clipped) { showResponses(history || [], clipped); },
      resetProposals: function () { decisions = {}; },
      disableUse: function (on) { useBusy = on; disableControls(on); },
      clear: function () { result = null; decisions = {}; manualEdits = {}; dictionaryCache.clear(); useBusy = false; disabledBefore = []; root.textContent = ''; root.hidden = true; }
    };
  }
  window.ParsehAsrReview = {mount: mount};
})();
