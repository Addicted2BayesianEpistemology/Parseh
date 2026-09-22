// SPDX-License-Identifier: GPL-3.0-or-later
/* The word line, read in the page: lib/wordline.py's grammar in JavaScript.
 *
 *   山(やま) へ 柴刈り(しばかり) に 、
 *
 * Both readers load this beside parseh.js.  The book reader and the player
 * draw a chunk a word at a time from it, the word strip edits it, and check()
 * runs under the strip as the person types, so the server's refusal is never
 * the first they hear of a mistake.  lib/wordline.py is the authority and
 * lib/wordline.lua the PDF's copy; tests/fixtures/wordline.json holds all
 * three to the same codes.
 *
 *   ParsehWordline.parse(line)        -> [[surface, reading], ...]  (throws {code, message})
 *   ParsehWordline.render(words)      -> line
 *   ParsehWordline.align(fa, words)   -> [[text, reading, k|null], ...]
 *   ParsehWordline.check(fa, line, lang, reading, reorders, door)
 *                                     -> {errors: [{code, message}], warnings: [...]}
 *   ParsehWordline.key(surface, reading) -> the word's identity, its own token
 *   ParsehWordline.aloud(reading, fa) -> the chunk as the aloud pass reads it
 *
 * `lang` is the registry record a page embeds (LANG, CFG.lang).  Everything
 * iterates by code point, never by UTF-16 unit, so a character outside the
 * basic plane is one character here as it is in Python.
 */
(function (root) {
  'use strict';

  // Python's str.isspace, exactly: JavaScript's \s is not the same set.
  var SPACE = {};
  [9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 0x85, 0xA0, 0x1680,
   0x2028, 0x2029, 0x202F, 0x205F, 0x3000].forEach(function (c) { SPACE[c] = true; });
  for (var s0 = 0x2000; s0 <= 0x200A; s0++) SPACE[s0] = true;
  function isSpace(ch) { return !!SPACE[ch.codePointAt(0)]; }

  var TEX_SPECIALS = '\\{}$%&#_^~';
  var NOT_TEXT = /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]/;
  var HAN = /[々〆㐀-䶿一-鿿豈-﫿\u{20000}-\u{3FFFF}]/u;
  var SCRIPT = /[ぁ-ゖゝゞァ-ヺー々〆㐀-䶿一-鿿豈-﫿\u{20000}-\u{3FFFF}]/u;
  var HIRA_TAIL = /[ぁ-ゖゝゞ]+$/;
  var HIRA_RUN = /^[ぁ-ゖゝゞ]+$/;
  var PUNCT = /\p{P}/u;

  function WordsError(code, message) {
    var e = new Error(message);
    e.code = code;
    return e;
  }

  function words(s) {                     // str.split()
    var out = [], cur = '';
    Array.from(s || '').forEach(function (ch) {
      if (isSpace(ch)) { if (cur) { out.push(cur); cur = ''; } }
      else cur += ch;
    });
    if (cur) out.push(cur);
    return out;
  }

  function parse(line) {
    if (typeof line !== 'string') throw WordsError('type', 'a word line is text');
    var t = Array.from(line), n = t.length;
    var pairs = [], surf = '', read = '', state = 0, start = 0, i = 0;

    function shown(end) { return "'" + t.slice(start, end).join('').trim() + "'"; }
    function finish(end) {
      if (state === 1) throw WordsError('unclosed', shown(end) + ' opens a reading and never closes it');
      var r = words(read).join(' ');
      if (surf) {
        if (state === 2 && !r)
          throw WordsError('empty_reading', shown(end) + ' has empty parentheses: a word with no reading is written without them');
        if (surf.indexOf('（') >= 0 && surf.slice(-1) === '）' && surf[0] !== '（')
          throw WordsError('fullwidth', shown(end) + ' puts its reading in the fullwidth parentheses （ ）: a reading is written in the ASCII ( ), and the fullwidth pair is part of the text');
        if (surf.slice(-1) === '(' || r[0] === '(')
          throw WordsError('unwritable', shown(end) + " ends in a literal '(', which cannot be written back: a word may not end in one nor a reading begin with one");
        pairs.push([surf, r]);
      }
      surf = ''; read = ''; state = 0;
    }

    while (i < n) {
      var c = t[i];
      if (state === 2) {
        if (isSpace(c)) { finish(i); i++; start = i; continue; }
        var j = i;
        while (j < n && !isSpace(t[j])) j++;
        var tail = t.slice(i, j).join('');
        if (HIRA_RUN.test(tail))
          throw WordsError('joined', shown(i) + ' is followed by ' + tail + ' with no space: if ' + tail +
            ' belongs to the word the reading covers it too, ' + surf + tail + '(' + read + tail +
            '), and if it is a word of its own put a space before it');
        throw WordsError('joined', 'a reading ends its word: put a space between ' + shown(i) + " and '" + tail + "'");
      }
      if ((c === '(' || c === ')') && t[i + 1] === c) {
        if (state === 1) read += c; else surf += c;
        i += 2;
        continue;
      }
      if (state === 0 && isSpace(c)) { finish(i); i++; start = i; continue; }
      if (c === '(') {
        if (state === 1) throw WordsError('second_open', 'a second ( inside ' + shown(n) + ': a literal parenthesis is written twice, ((');
        if (!surf) throw WordsError('no_word', 'a reading with no word in front of it, in ' + shown(n));
        state = 1;
      } else if (c === ')') {
        if (state === 0) throw WordsError('stray_close', shown(n) + ' closes a parenthesis it never opened: a literal one is written twice, ))');
        state = 2;
      } else if (state === 1) read += c;
      else surf += c;
      i++;
    }
    finish(n);
    return pairs;
  }

  function esc(s) { return s.replace(/\(/g, '((').replace(/\)/g, '))'); }

  function token(surface, reading) {
    reading = words(reading || '').join(' ');
    if (!surface) throw WordsError('no_text', 'a word with no text');
    if (Array.from(surface).some(isSpace))
      throw WordsError('space_in_word', "'" + surface + "' has a space in it: words are parted by spaces, so no word can hold one");
    if (surface.slice(-1) === '(' || reading[0] === '(')
      throw WordsError('unwritable', "'" + surface + "' cannot be written: a word may not end in '(' nor a reading begin with one");
    return esc(surface) + (reading ? '(' + esc(reading) + ')' : '');
  }

  function render(pairs) {
    return pairs.map(function (p) { return token(p[0], p[1]); }).join(' ');
  }

  function align(fa, pairs) {
    var t = Array.from(fa || ''), n = t.length, i = 0, out = [];
    function mismatch() {
      throw WordsError('reproduce', 'the words do not reproduce the text: the words give ' +
        pairs.map(function (p) { return p[0]; }).join('') + ' and the text is ' + t.join(''));
    }
    pairs.forEach(function (p, k) {
      var j = i;
      while (j < n && isSpace(t[j])) j++;
      if (j > i) out.push([t.slice(i, j).join(''), '', null]);
      i = j;
      var begin = i;
      Array.from(p[0]).forEach(function (ch) {
        while (i < n && isSpace(t[i])) i++;
        if (i >= n || t[i] !== ch) mismatch();
        i++;
      });
      out.push([t.slice(begin, i).join(''), p[1], k]);
    });
    for (var k = i; k < n; k++) if (!isSpace(t[k])) mismatch();
    if (i < n) out.push([t.slice(i).join(''), '', null]);
    return out;
  }

  // The chunk read aloud: wordline.py's trailing() and aloud(), on the same
  // code points (TRAIL), whitespace inside the closing run skipped.
  var TRAIL = [[0x21, 0x2F], [0x3A, 0x40], [0x5B, 0x60], [0x7B, 0x7E], [0xA1, 0xBF],
               [0x2010, 0x2027], [0x2030, 0x205E], [0x3001, 0x3003], [0x3008, 0x3011],
               [0x3014, 0x301F], [0x30FB, 0x30FB], [0xFF01, 0xFF0F], [0xFF1A, 0xFF20],
               [0xFF3B, 0xFF40], [0xFF5B, 0xFF65]];
  function trails(ch) {
    var c = ch.codePointAt(0);
    return TRAIL.some(function (r) { return c >= r[0] && c <= r[1]; });
  }

  function trailing(fa) {
    var t = Array.from(fa || ''), out = [];
    for (var i = t.length - 1; i >= 0; i--) {
      if (isSpace(t[i])) continue;
      if (!trails(t[i])) break;
      out.unshift(t[i]);
    }
    return out.join('');
  }

  function aloud(reading, fa) {
    var r = Array.from(reading || ''), i = 0, j = r.length;
    while (i < j && isSpace(r[i])) i++;
    while (j > i && isSpace(r[j - 1])) j--;
    if (i >= j) return fa || '';
    var s = r.slice(i, j).join(''), p = Array.from(trailing(fa)), k = p.length;
    while (k && !s.endsWith(p.slice(0, k).join(''))) k--;
    return s + p.slice(k).join('');
  }

  function sounds(pairs) {
    return pairs.filter(function (p) { return p[1] || !HAN.test(p[0]); })
                .map(function (p) { return p[1] || p[0]; });
  }

  function kanaKey(s) {
    return Array.from(s.normalize('NFC')).filter(function (ch) {
      return !isSpace(ch) && !PUNCT.test(ch);
    }).join('');
  }

  function romanKey(s) {
    return s.normalize('NFD').toLowerCase().replace(/[^a-z0-9]/g, '');
  }

  function agrees(pairs, reading, lang) {
    if (!(reading || '').trim() || !pairs.length) return null;
    var key = lang.reading ? kanaKey : romanKey;
    return key(sounds(pairs).join('')) === key(reading);
  }

  // code point by code point, never normalised: wordline.py's norm() says why
  function norm(s, lang) {
    s = s || '';
    if (lang.strip) s = s.replace(new RegExp('[' + lang.strip + ']', 'g'), '');
    return lang.word_sep ? words(s).join(' ') : words(s).join('');
  }

  function diff(got, want) {
    var a = Array.from(got), b = Array.from(want), k = 0;
    while (k < a.length && k < b.length && a[k] === b[k]) k++;
    function at(x) { return k < x.length ? 'U+' + x[k].codePointAt(0).toString(16).toUpperCase().padStart(4, '0') + ' ' + x[k] : 'nothing'; }
    return 'the words give ' + got + ' and the text is ' + want + ': at character ' + k +
      ' the words have ' + at(a) + ' and the text has ' + at(b);
  }

  function check(fa, line, lang, reading, reorders, door) {
    var errors = [], warnings = [];
    function note(list, code, message) { list.push({code: code, message: message}); }
    door = door || 'book';
    if (typeof line !== 'string') { note(errors, 'type', 'words must be text'); return {errors: errors, warnings: warnings}; }
    if (!lang.words) { note(errors, 'no_layer', lang.name + ' has no word layer, so a chunk carries no words'); return {errors: errors, warnings: warnings}; }
    var m = NOT_TEXT.exec(line);
    if (m) note(errors, 'control', 'words carries a character that is not text, at character ' + m.index);
    if (door === 'book') {
      var bad = Array.from(new Set(Array.from(line).filter(function (ch) { return TEX_SPECIALS.indexOf(ch) >= 0; })));
      if (bad.length) note(errors, 'tex_special', 'words may not contain ' + bad.join(' ') + ': LaTeX reads it as an instruction');
      if (/\n[ \t]*\n/.test(line)) note(errors, 'blank_line', 'a blank line inside words ends the paragraph');
    }
    if (errors.length) return {errors: errors, warnings: warnings};
    var pairs;
    try { pairs = parse(line); }
    catch (e) { note(errors, e.code || 'parse', e.message); return {errors: errors, warnings: warnings}; }
    if (!pairs.length) { note(errors, 'empty', 'words is empty: a chunk without words is written without the field'); return {errors: errors, warnings: warnings}; }
    var got = norm(pairs.map(function (p) { return p[0]; }).join(lang.word_sep || ''), lang), want = norm(fa, lang);
    if (got !== want) { note(errors, 'reproduce', 'the words do not reproduce the text: ' + diff(got, want)); return {errors: errors, warnings: warnings}; }

    var isReading = lang.reading_chars ? new RegExp('^[' + lang.reading_chars + '\\s]+$') : null;
    var hasScript = lang.chars ? new RegExp('[' + lang.chars + ']') : null;
    pairs.forEach(function (p) {
      var s = p[0], r = p[1];
      if (!r && HAN.test(s) && !reorders) note(warnings, 'no_reading', s + ' has no reading');
      if (r && lang.reading && !(isReading && isReading.test(r.trim())))
        note(warnings, 'reading_script', 'the reading of ' + s + ', ' + r + ', is not written in ' + (lang.reading_label || "the reading's script"));
      if (r && !lang.reading && hasScript && hasScript.test(r))
        note(warnings, 'reading_script', 'the reading of ' + s + ', ' + r + ', has ' + lang.name + ' characters in it');
      var tail = HIRA_TAIL.exec(s);
      if (lang.reading && r && tail && HAN.test(s) && r.slice(-tail[0].length) !== tail[0])
        note(warnings, 'okurigana', s + '(' + r + '): the reading should cover the whole word, ending with its okurigana ' + tail[0]);
      if (SCRIPT.test(s) && Array.from(s).some(function (ch) { return PUNCT.test(ch); }))
        note(warnings, 'punctuation', s + ' runs punctuation into a word: the punctuation is a word of its own');
    });
    if (!reorders && agrees(pairs, reading, lang) === false)
      note(warnings, 'disagrees', 'the words read ' + sounds(pairs).join(lang.reading ? '' : ' ') +
        " and the chunk's reading is " + reading + ': a text read out of its written order (kanbun) is marked "reorders": true, and anything else is a reading to correct');
    return {errors: errors, warnings: warnings};
  }

  root.ParsehWordline = {
    parse: parse, render: render, token: token, key: token, align: align,
    check: check, sounds: sounds, agrees: agrees, HAN: HAN,
    trailing: trailing, aloud: aloud
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
