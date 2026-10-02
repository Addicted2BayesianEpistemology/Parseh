// SPDX-License-Identifier: GPL-3.0-or-later
/* The add page's film field: what the path names is LOOKED AT, and the file may
   be SENT instead of named (the owner, 2026-09-29: "do not change the video
   mechanism, path is correct there, add the OPTION to send").

   This script only adds.  The path box, its checks and every door that takes a
   path are the page's own and are not touched: a file that is sent is written
   whole into the computer's disk by /youtube/api/film, and what comes back is
   its PATH, which goes into the same box and travels from there exactly as a
   path typed there does -- the prompt, the speech to text, "start it empty".  It
   works from another device and on Windows, where there is no path to type.

     -- looking.  When the path box is left, /youtube/api/film/look says what
        the file is: a video, or a sound with no picture; how long and how big;
        and, for a sound a browser cannot play, what will be done about it (a
        playable copy, made when the video is added; the original kept beside it).
     -- sending.  A file is chosen, its size is said and the disk's room is asked
        about BEFORE a byte is sent -- a refusal after the body had started
        would arrive as a broken connection and not as words -- and only then is
        it sent, by the same kind of upload the narration and a book's original
        use, with how far it has got, how fast, and how long is left, and a way
        to stop.

   The page hands over nothing: this reads #path and #filmsend by their ids,
   writes the path back and says it changed (an `input` event), which is the one
   thing the page already listens for.  A speech-to-text job that is running has
   locked #path (addstt.js's class `stt-locked`), and a sent file is not taken
   while it is. */
(function () {
  'use strict';
  if (window.ParsehAddFilm) return;
  window.ParsehAddFilm = {};

  var $ = function (id) { return document.getElementById(id); };

  function mb(n) {
    return n >= 1e9 ? (n / 1e9).toFixed(1) + ' GB'
         : n >= 1e6 ? (n >= 1e8 ? Math.round(n / 1e6) : (n / 1e6).toFixed(1)) + ' MB'
         : Math.max(1, Math.round(n / 1e3)) + ' kB';
  }
  function clock(sec) {
    sec = Math.max(0, Math.round(sec));
    var h = Math.floor(sec / 3600), m = Math.floor(sec / 60) % 60, s = sec % 60;
    return (h ? h + ':' + (m < 10 ? '0' : '') + m : m) + ':' + (s < 10 ? '0' : '') + s;
  }
  function left(sec) {
    if (!isFinite(sec)) return '';
    if (sec < 5) return 'a few seconds';
    if (sec < 90) return Math.round(sec / 5) * 5 + ' seconds';
    return Math.round(sec / 60) + ' minutes';
  }
  function say(el, text, cls) {
    el.textContent = text;
    el.className = 'filmsay' + (cls ? ' ' + cls : '');
    el.hidden = !text;
  }
  function post(base, what, body) {
    return fetch(base + '/api/film' + what, {method: 'POST',
      headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})
      .then(function (r) { return r.json().catch(function () { return null; }); })
      .then(function (j) { return j || {ok: false, error: 'the server answered with nothing readable'}; });
  }

  function start() {
    var mount = $('filmsend'), path = $('path'), look = $('filmlook');
    if (!mount || !path || !look) return;
    var base = mount.getAttribute('data-base') || '/youtube';
    var accept = mount.getAttribute('data-accept') || 'audio/*,video/*';
    var toast = window.Parseh && Parseh.toast ? Parseh.toast : function () {};

    /* ------------------------------------------------ what the path names */
    var asked = 0;
    function looked(why) {
      var value = path.value.trim();
      var mine = ++asked;
      if (!value) { say(look, ''); return; }
      post(base, '/look', {path: value}).then(function (j) {
        if (mine !== asked || path.value.trim() !== value) return;     // a later look is the one
        if (!j.ok) { say(look, j.error || 'that cannot be read', 'warn'); return; }
        var bits = [j.ext.replace(/^\./, ''), mb(j.bytes)];
        if (j.seconds) bits.push(clock(j.seconds));
        say(look, (j.kind === 'audio' ? 'A sound with no picture' : 'A video') + ' (' + bits.join(', ') + ')' +
                  (j.kind === 'audio' ? ': the player shows a bar with its waveform in place of a frame.' : '.') +
                  (j.note ? ' ' + j.note + '.' : ''), j.note ? 'warn' : '');
      }, function () { if (mine === asked) say(look, ''); });
    }
    path.addEventListener('change', looked);
    path.addEventListener('input', function () { asked++; say(look, ''); });
    if (path.value.trim()) looked();

    /* ---------------------------------------------------------- sending */
    mount.innerHTML =
      '<p class="fieldnote filmor">Or <b>send it</b> from this device &mdash; the file is written to this ' +
      'computer\'s disk, and its path is then put in the box above. That is the way to bring a file from ' +
      'another device, or where there is no path to type.</p>' +
      '<div class="row filmrow"><button type="button" class="wbtn quiet filmpick">Choose a video or a sound&hellip;</button>' +
      '<input type="file" hidden>' +
      '<button type="button" class="wbtn filmgo" hidden>Send it</button>' +
      '<button type="button" class="wbtn quiet filmstop" hidden>Stop</button></div>' +
      '<div class="filmbar" hidden><div class="filmfill"></div></div>' +
      '<div class="filmsay" aria-live="polite" hidden></div>';
    var pick = mount.querySelector('input[type=file]'), go = mount.querySelector('.filmgo'),
        choose = mount.querySelector('.filmpick'),
        stop = mount.querySelector('.filmstop'), bar = mount.querySelector('.filmbar'),
        fill = mount.querySelector('.filmfill'), said = mount.querySelector('.filmsay');
    pick.accept = accept;
    choose.addEventListener('click', function () { if (!pick.disabled) pick.click(); });
    var file = null, xhr = null;

    function idle(text, cls) {
      xhr = null;
      bar.hidden = true;
      stop.hidden = true;
      go.hidden = !file;
      go.disabled = false;
      pick.disabled = choose.disabled = false;
      mount.classList.remove('sending');
      say(said, text, cls);
    }
    pick.addEventListener('change', function () {
      file = pick.files && pick.files[0] ? pick.files[0] : null;
      if (!file) { idle(''); return; }
      go.hidden = true;
      say(said, 'Asking the computer about ' + file.name + '…');
      // the size is said, and the kind and the room are asked, before a byte goes
      post(base, '/look', {name: file.name, bytes: file.size}).then(function (j) {
        if (!file || pick.files[0] !== file) return;
        if (!j.ok) { file = null; pick.value = ''; idle(j.error || 'that cannot be sent', 'warn'); return; }
        go.hidden = false;
        say(said, file.name + ' is ' + mb(file.size) + ': ' + (j.kind === 'audio' ? 'a sound' : 'a video') +
                  '. This computer has ' + mb(j.free) + ' free. How long it takes depends on the ' +
                  'connection between this device and the computer; the page counts it as it goes.');
      }, function () { idle('the computer did not answer — nothing was sent', 'warn'); });
    });
    go.addEventListener('click', function () {
      if (!file || xhr) return;
      if (path.classList.contains('stt-locked')) {
        toast('a transcription is running on this video: let it finish, or stop it, first', true);
        return;
      }
      var sent = file, began = Date.now();
      var act = window.Parseh && Parseh.working ? Parseh.working('Sending ' + sent.name) : null;
      var url = base + '/api/film?name=' + encodeURIComponent(sent.name);
      xhr = new XMLHttpRequest();
      var x = xhr;
      x.open('POST', act ? act.url(url) : url);
      x.setRequestHeader('Content-Type', 'application/octet-stream');
      go.hidden = true;
      pick.disabled = choose.disabled = true;
      stop.hidden = false;
      bar.hidden = false;
      fill.style.width = '0%';
      mount.classList.add('sending');
      say(said, 'Sending ' + sent.name + ' (' + mb(sent.size) + ')…');
      x.upload.onprogress = function (e) {
        if (!e.lengthComputable) return;
        var secs = (Date.now() - began) / 1000, rate = secs > 0.5 ? e.loaded / secs : 0;
        fill.style.width = (100 * e.loaded / e.total).toFixed(1) + '%';
        say(said, 'Sending ' + sent.name + ': ' + Math.floor(100 * e.loaded / e.total) + ' % of ' + mb(e.total) +
                  (rate ? ' · ' + mb(rate) + '/s · about ' + left((e.total - e.loaded) / rate) + ' left' : ''));
        if (act) act.progress(e.loaded, e.total);
        if (e.loaded >= e.total) say(said, mb(e.total) + ' is on its way in: the computer is looking at it…');
      };
      x.onload = function () {
        var j = null;
        try { j = JSON.parse(x.responseText); } catch (err) {}
        if (act) act.end(!!(j && j.ok));
        if (!j || !j.ok) {
          idle((j && j.error) || 'the computer refused it (' + x.status + ')', 'warn');
          return;
        }
        file = null;
        pick.value = '';
        path.value = j.path;
        // the box is the page's, and it already listens for its own changes
        path.dispatchEvent(new Event('input', {bubbles: true}));
        path.dispatchEvent(new Event('change', {bubbles: true}));
        idle('Sent: ' + j.name + ' (' + mb(j.bytes) + ') is on this computer, and its path is in the box above. ' +
             'Go on as with any path.');
      };
      x.onerror = function () {
        if (act) act.end(false);
        idle('the computer did not answer — nothing was kept', 'warn');
      };
      x.onabort = function () {
        if (act) act.end(false);
        idle('Stopped — nothing was kept.');
      };
      x.send(sent);
    });
    stop.addEventListener('click', function () { if (xhr) xhr.abort(); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
