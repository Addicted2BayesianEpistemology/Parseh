// SPDX-License-Identifier: GPL-3.0-or-later
/* Pending browser review. All text is textContent; source offsets are Unicode code points. */
(function () {
  'use strict';
  function el(tag, text, cls) { var n = document.createElement(tag); if (text != null) n.textContent = text; if (cls) n.className = cls; return n; }
  function btn(text, fn) { var b = el('button', text, 'wbtn small quiet'); b.type = 'button'; b.addEventListener('click', fn); return b; }
  function time(n) { return typeof n === 'number' ? n.toFixed(2) + ' s' : 'unavailable'; }
  function estimate(n) { return typeof n === 'number' ? n.toFixed(2) : 'unavailable'; }
  function mount(root, opts) {
    var result = null, phase = '', config = null, decisions = {}, suggestions = {}, words = {}, selected = null;
    var choice, inspect, details, preview, status, use, useBusy = false, disabledBefore = [];
    function disableControls(on) {
      if (on) {
        disabledBefore = Array.prototype.slice.call(root.querySelectorAll('button')).filter(function (b) { return b.id !== 'stt_review_cancel'; })
          .map(function (b) { var old = [b, b.disabled]; b.disabled = true; return old; });
      } else {
        disabledBefore.forEach(function (old) { old[0].disabled = old[1]; }); disabledBefore = [];
      }
    }
    function draft() {
      var chars = Array.from(result.text), edits = [];
      Object.keys(decisions).forEach(function (id) {
        var w = words[id], s = suggestions[id];
        if (w && s) edits.push({a: w.span_start, b: w.span_end, text: s.candidates[decisions[id]].text});
      });
      edits.sort(function (a, b) { return b.a - a.a; });
      edits.forEach(function (e) { chars.splice.apply(chars, [e.a, e.b - e.a].concat(Array.from(e.text))); });
      return chars.join('');
    }
    function updateDraft() {
      preview.textContent = draft();
      status.textContent = Object.keys(decisions).length + ' edits accepted in this draft. The transcript box has not changed.';
      Object.keys(suggestions).forEach(function (id) {
        var button = root.querySelector('[data-review-word="' + id + '"]');
        if (button) button.classList.toggle('asr-accepted', decisions[id] != null);
      });
    }
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
      var s = suggestions[w.word_id];
      if (s) {
        details.appendChild(el('p', '✎ LLM proposal · Error likelihood (model estimate): ' + estimate(s.error_likelihood)));
        details.appendChild(el('p', s.reason));
        var alternatives = el('ol');
        s.candidates.forEach(function (c, i) {
          var li = el('li'), surface = el('bdi', c.text); surface.dir = 'auto'; li.appendChild(surface);
          li.appendChild(el('p', 'Confidence (model estimate): ' + estimate(c.confidence) + '. ' + c.reason));
          li.appendChild(btn(decisions[w.word_id] === i ? 'Accepted in draft' : 'Accept this alternative', function () {
            decisions[w.word_id] = i; updateDraft(); detail(w);
          }));
          alternatives.appendChild(li);
        });
        details.appendChild(alternatives);
        details.appendChild(btn('Reject this edit / keep Whisper word', function () { delete decisions[w.word_id]; updateDraft(); detail(w); }));
      } else if (w.low_asr_score) details.appendChild(el('p', 'No LLM edit is proposed for this word. It stays unchanged.'));
    }
    function render() {
      root.textContent = ''; root.hidden = false;
      root.appendChild(el('h3', phase === 'choice' ? 'Choose how to review the Whisper transcript' : 'Review transcript'));
      choice = el('div', null, 'row');
      var llm = btn('Review with the selected LLM', function () { opts.choose('llm'); });
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
      choice.appendChild(llm); choice.appendChild(whisper); choice.appendChild(remember); root.appendChild(choice);
      root.appendChild(el('p', config && config.configured ? 'LLM destination: ' + config.base_url + ' · Selected model: ' + config.selected_model + '. Choosing LLM review sends bounded text and Whisper evidence; audio is never sent.' : 'LLM Integration is unconfigured. Whisper-only review sends nothing to an LLM.'));
      var settings = el('a', 'LLM Integration settings'); settings.href = '/settings/llm/'; settings.target = '_blank'; settings.rel = 'noopener'; root.appendChild(settings);
      var c = result.review && result.review.correction || {};
      if (c.error) root.appendChild(el('p', c.error + ' Retry LLM review or continue with Whisper.', 'warn'));
      status = el('p', '', 'stt-review-status'); status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite'); root.appendChild(status);
      var cancelled = btn(phase === 'correcting' ? 'Cancel LLM review' : 'Cancel review', opts.cancel);
      cancelled.id = 'stt_review_cancel'; root.appendChild(cancelled);
      if (phase === 'choice' || phase === 'correcting') return;
      root.appendChild(el('p', '⚠ = low Whisper ASR score. ✎ = LLM edit proposal. Accepted edits are underlined. Focus, hover or tap a marked word for details. Model scores are estimates.'));
      var reviewed = result.review.result;
      if (reviewed && !reviewed.suggestions.length) root.appendChild(el('p', reviewed.assessment === 'uncertain' ? 'The model cannot tell whether a correction is needed. No words have been changed.' : 'The model reported no likely recognition error. No words have been changed.'));
      inspect = el('div', null, 'stt-review-text'); inspect.dir = 'auto';
      details = el('aside', 'Select a marked word for its evidence and alternatives.', 'stt-review-details');
      details.id = 'stt_review_details'; details.setAttribute('role', 'region'); details.setAttribute('aria-label', 'Word evidence and proposed edits'); details.setAttribute('aria-live', 'polite');
      var evidence = result.review.evidence;
      if (evidence) evidence.segments.forEach(function (seg) {
        var row = el('p'), clock = el('span', time(seg.start) + '  ', 'stt-review-clock'); row.appendChild(clock);
        var text = el('span'), cursor = 0; text.dir = 'auto';
        seg.words.forEach(function (w) {
          var at = seg.text.indexOf(w.text, cursor); if (at < 0) return;
          text.appendChild(document.createTextNode(seg.text.slice(cursor, at)));
          var s = suggestions[w.word_id];
          if (w.low_asr_score || s) {
            var b = btn((w.low_asr_score ? '⚠ ' : '') + (s ? '✎ ' : '') + w.text, function () { detail(w); });
            b.className = 'stt-review-word' + (w.low_asr_score ? ' asr-low' : '') + (s ? ' asr-proposal' : '');
            b.setAttribute('data-review-word', w.word_id); b.setAttribute('aria-controls', details.id);
            b.setAttribute('aria-label', w.text + (w.low_asr_score ? ', low Whisper ASR score' : '') + (s ? ', LLM edit proposed' : ''));
            b.addEventListener('focus', function () { detail(w); });
            b.addEventListener('mouseenter', function () { detail(w); });
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
      use = btn('Use this transcript', function () { opts.use(Object.assign({}, decisions)); }); use.id = 'stt_use';
      root.appendChild(use); updateDraft();
      if (selected && words[selected]) detail(words[selected]);
      if (useBusy) disableControls(true);
    }
    return {
      show: function (res, state, connection) {
        var before = result && result.review && result.review.evidence && result.review.evidence.source_sha256;
        var after = res.review && res.review.evidence && res.review.evidence.source_sha256;
        if (before !== after || state === 'choice') { decisions = {}; selected = null; }
        result = res; phase = state; config = connection; suggestions = {}; words = {};
        ((res.review && res.review.result && res.review.result.suggestions) || []).forEach(function (s) { suggestions[s.word_id] = s; });
        ((res.review && res.review.evidence && res.review.evidence.segments) || []).forEach(function (s) { s.words.forEach(function (w) { words[w.word_id] = w; }); });
        render();
      },
      progress: function (say) { if (status) status.textContent = say; },
      disableUse: function (on) { useBusy = on; disableControls(on); },
      clear: function () { result = null; decisions = {}; useBusy = false; disabledBefore = []; root.textContent = ''; root.hidden = true; }
    };
  }
  window.ParsehAsrReview = {mount: mount};
})();
