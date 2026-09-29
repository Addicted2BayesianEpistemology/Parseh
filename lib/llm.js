// SPDX-License-Identifier: GPL-3.0-or-later
/* A HAND-OFF TO AN EXTERNAL CHATBOT, and nothing that runs a model here.

   Both readers use this one prompt builder so the promise made by "Ask LLM"
   cannot drift between books and videos.  It is deliberately given only the
   source sentence, its neighbours, the dictionary rows and the parallel
   corpus rows.  There is no slot for Bergamot output, so a caller cannot
   accidentally put the local model's answer into the prompt.

   The clipboard helper differs from Parseh.copy: a reading chunk is copied as
   one neat line, while a prompt needs to keep its labelled line breaks.

   THREE PARTS, AND A VERSION LINE (a0.4.2, brief §3.1 and §3.4).  Every prompt
   Parseh hands out is assembled from the same three parts in the same order:
   the instructions (how to do the job), the answer contract (the shape of an
   answer Parseh reads back: here there is none, because nothing of this
   answer is read back -- the person pastes a translation and looks at it) and
   the data (the sentences, the dictionary rows, the corpus rows).  The other
   prompts are assembled on the server (lib/promptkit.py); this one stays here
   because it is built from what the sidebar already holds, and `parts` gives
   it the same shape so that a person's own instructions (Lane F, W5) can be
   put in place of Parseh's, or after them, with the data still Parseh's.  The
   first line says which prompt it is and which Parseh wrote it -- and the
   number is asked of the server (`version`, GET /__version) rather than
   written into this script, so a prompt cannot name a Parseh that is not
   the one running. */
(function (root) {
  'use strict';

  function clean(value) {
    return String(value == null ? '' : value).replace(/\r\n?/g, '\n').trim();
  }

  function list(value) {
    return Array.isArray(value) ? value.filter(Boolean).map(clean).filter(Boolean) : [];
  }

  function dictionaryLines(words) {
    var out = [];
    (words || []).forEach(function (word) {
      var hits = (word && word.hits) || [];
      if (!hits.length) {
        out.push('- ' + clean(word && word.word) + ': no result');
        return;
      }
      hits.forEach(function (hit) {
        var head = clean(hit.spelled || hit.headword || (word && word.word));
        var parts = [];
        if (hit.vb && hit.vb.lemma && clean(hit.vb.lemma) !== head)
          head += ' -> ' + clean(hit.vb.lemma);
        if (hit.translit) parts.push(clean(hit.translit));
        if (hit.pos) parts.push(clean(hit.pos));
        if (hit.note) parts.push(clean(hit.note));
        if (hit.of_form) parts.push('here: ' + clean(hit.of_form));
        // The Source sidebar shows the first sense of each hit.  The prompt
        // carries precisely those visible results rather than hidden senses.
        var sense = clean(((hit.senses || [])[0]) || '');
        if (sense) parts.push(sense);
        if (hit.vb && hit.vb.line) parts.push(clean(hit.vb.line));
        list(hit.vb && hit.vb.notes).forEach(function (note) {
          parts.push(note);
        });
        list(hit.vb && hit.vb.missing).forEach(function (missing) {
          parts.push('still to fill: ' + missing);
        });
        out.push('- ' + head + (parts.length ? ': ' + parts.join(' | ') : ''));
      });
    });
    return out.length ? out : ['(none)'];
  }

  function pairLines(pairs) {
    var out = [];
    (pairs || []).forEach(function (pair, i) {
      out.push((i + 1) + '. ' + clean(pair.src));
      out.push('   Translation: ' + clean(pair.dst));
    });
    return out.length ? out : ['(none)'];
  }

  function contextLines(sentences) {
    sentences = list(sentences);
    return sentences.length ? sentences.map(function (s, i) {
      return (i + 1) + '. ' + s;
    }) : ['(none available)'];
  }

  /* THE FIRST LINE: which prompt, for which languages, from which Parseh --
     "Parseh prompt · ask · fa → en · a0.4.2" -- and "· custom: <name>" when
     the instructions are a person's.  Where the number is not known (the
     computer did not answer) the line is still true, and says less. */
  function versionLine(opts) {
    var pair = [clean(opts.sourceCode || opts.sourceName), clean(opts.targetCode || opts.targetName)]
      .filter(Boolean).join(' → ');
    return ['Parseh prompt', 'ask', pair, clean(opts.version),
            opts.custom ? 'custom: ' + clean(opts.custom) : '']
      .filter(Boolean).join(' · ');
  }

  /* THE TWO KINDS OF OWN INSTRUCTIONS (brief §8.2): `added` goes after
     Parseh's, `replace` stands in place of them.  Either way the data below is
     Parseh's and comes last. */
  function parts(opts) {
    opts = opts || {};
    var source = clean(opts.sourceName || opts.sourceCode || 'the source language');
    var target = clean(opts.targetName || opts.targetCode || 'the target language');
    var own = clean(opts.instructions);
    var ours = [
      'Translate the TARGET SENTENCE from ' + source + ' into ' + target + '.',
      'Return ONLY the translation. Do not include an explanation, notes, alternatives, labels, quotation marks, or Markdown formatting.',
      'Translate only the target sentence. Use the surrounding sentences, dictionary results, and Tatoeba examples only as context.'
    ].join('\n');
    return {
      version: versionLine(opts),
      instructions: !own ? ours : opts.instructionsKind === 'replace' ? own : ours + '\n\n' + own,
      // nothing of the answer is read back, so nothing of it is locked
      contract: '',
      data: [
        'SENTENCES BEFORE:',
        contextLines(opts.before).join('\n'),
        '',
        'TARGET SENTENCE:',
        clean(opts.sentence),
        '',
        'SENTENCES AFTER:',
        contextLines(opts.after).join('\n'),
        '',
        'DICTIONARY RESULTS FOR THE CURRENT CHUNK:',
        dictionaryLines(opts.words).join('\n'),
        '',
        'RELEVANT TATOEBA EXAMPLES:',
        pairLines(opts.pairs).join('\n')
      ].join('\n')
    };
  }

  function prompt(opts) {
    var p = parts(opts);
    return [p.version, p.instructions, p.contract, p.data].filter(Boolean).join('\n\n');
  }

  /* WHICH PARSEH THIS IS, asked once and kept.  It waits three seconds at
     the most: a computer gone quiet must not keep the button greyed, and a
     prompt with no number in its first line is still a prompt. */
  var asked = null;
  function version() {
    if (asked) return asked;
    var wait = new Promise(function (ok) { setTimeout(function () { ok(''); }, 3000); });
    var got = typeof root.fetch !== 'function' ? Promise.resolve('') :
      root.fetch('/__version', {cache: 'no-store'})
        .then(function (r) { return r.ok ? r.json() : {}; })
        .then(function (j) { return clean(j && j.version); })
        .catch(function () { return ''; });
    asked = Promise.race([got, wait]).then(function (v) {
      if (!v) asked = null;              // not known yet: the next prompt asks again
      return v;
    });
    return asked;
  }

  function copy(text) {
    text = clean(text);
    if (!text) return Promise.resolve(false);
    var clipboard = root.navigator && root.navigator.clipboard;
    var attempt = clipboard && clipboard.writeText
      ? clipboard.writeText(text)
      : Promise.reject(new Error('no clipboard API'));
    return attempt.then(function () { return true; }).catch(function () {
      try {
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
        document.body.appendChild(ta);
        ta.select();
        var ok = document.execCommand('copy');
        document.body.removeChild(ta);
        return !!ok;
      } catch (_) {
        return false;
      }
    });
  }

  /* Fetch every remaining ranked corpus page only when the prompt is asked
     for.  The sidebar stays compact at three examples; the chatbot still gets
     every relevant example.  A page that claims there is more but adds
     nothing is stopped, so an old or faulty server cannot make the button
     wait forever. */
  function collectPairs(initial, load) {
    initial = initial || {};
    var pairs = ((initial.pairs || []).slice());
    var offset = Math.max(0, Number(initial.pairs_offset) || 0) + pairs.length;
    function next(more) {
      if (!more || typeof load !== 'function') return Promise.resolve(pairs);
      return Promise.resolve(load(offset)).then(function (page) {
        var added = (page && page.pairs) || [];
        if (!added.length) return pairs;
        Array.prototype.push.apply(pairs, added);
        offset += added.length;
        return next(!!page.pairs_more);
      });
    }
    return next(!!initial.pairs_more);
  }

  root.ParsehLLM = {
    prompt: prompt,
    parts: parts,
    version: version,
    copy: copy,
    collectPairs: collectPairs,
    dictionaryLines: dictionaryLines,
    pairLines: pairLines
  };
})(typeof window !== 'undefined' ? window : globalThis);
