// SPDX-License-Identifier: GPL-3.0-or-later
/* Parseh — ONE capture of the sound of this tab, shared by everything that wants it.

   A YouTube video's sound reaches no script: its frame belongs to another
   site.  The only way to hear it is to record the TAB while the video plays,
   which Chrome and Edge allow (getDisplayMedia, asked for once, with the
   tab's sound).  This file is that recording and nothing else -- no page, no
   button, no fetch, no toast -- so that whatever needs the tab's sound stands on
   the same code instead of keeping a recorder of its own.  So far that is the
   player's "draw the sound" (the timings sheet, youtube/lib/player.js), which
   keeps the SHAPE of the sound.

     ParsehTabCapture.capability()      -> {ok, why}     why not, in words
     ParsehTabCapture.problem()         -> '' | why      the same, as a string
     ParsehTabCapture.share(want)       -> Promise<MediaStream>   THE getDisplayMedia call
     ParsehTabCapture.share.live(want)  -> MediaStream | null     the share as it stands
     ParsehTabCapture.release()         let the share go (stop its tracks)
     ParsehTabCapture.busy()            -> bool: a recording is under way in this page
     ParsehTabCapture.record(opts)      -> {promise, cancel(), state}

   record(opts):
     player      a YT.Player: getDuration getCurrentTime seekTo playVideo pauseVideo
                 (and getPlaybackRate/setPlaybackRate)
     wave        true (default): the SHAPE, 20 numbers a second (below)
     keepShare   true (default): the share stays live for whatever asks next (the
                 frame capture, the cut editor: one question from Chrome for all);
                 false: its tracks are stopped at the end
     onStart(duration)               playing has begun (once)
     onProgress(seconds, duration)   about once a second of the video
     onPeaks(peaks, rate)            once, at the end: the shape, normalised
     onEnd(reason)                   once, when everything is cleaned up: 'ended'
                                     (the video reached its end), 'stalled' (its
                                     clock stopped for ten seconds), 'share-ended'
                                     (the person stopped sharing), 'cancelled',
                                     'error'
   The promise resolves for ended, stalled and cancelled with {reason, rate, peaks,
   reached, duration}, and rejects with an Error whose message says what to do for
   the rest (its .reason is the reason).

   THE SHAPE.  An Analyser in an AudioContext of the browser's own rate reads the
   tab's sound every 25 ms; the loudest sample of what it holds is filed under
   round(clock * 20) -- THE VIDEO'S CLOCK, not the recording's, so that a video
   that stops to buffer does not slide what follows -- and the whole is divided by
   its loudest and kept to three decimals.  Moved here from player.js as it was:
   tests/youtube_capture.mjs section l plays the ticks itself and holds the
   numbers to a checksum taken before the move.

   WHAT IS ALWAYS TRUE (tests/youtube_capture.mjs holds each):
     . one getDisplayMedia call per share, none if a live share with sound is held
     . a share with no sound fails BEFORE the video plays, in a sentence
     . nothing is ever connected to the speakers, and the microphone is never asked
     . the 'ended' listener on the share is taken off again at the end
     . cancel() -- and every other end -- stops playback and puts the player back
       as it was, closes the context, and leaves no timer and no state: a second
       record() works

   Plain ES2017, no build step, a classic script (no modules) so that the phone's
   copy of the player and its service worker need nothing special: served at
   /youtube/lib/tabcapture.js and kept for offline in lib/offline.py PLAYER_FILES. */
(function () {
  'use strict';
  if (window.ParsehTabCapture) return;

  var WAVE_RATE = 20;              // numbers a second: one every 50 ms
  var TICK_MS = 25;                // the one clock loop
  var STALL_TICKS = 400;           // a clock unmoved for this many ticks (10 s) has stalled
  var END_MARGIN = 0.3;            // seconds from the end at which a video has ended

  /* -------------------------------------------------------------- words */
  // The first three are lib/cardkit.js tabProblem's, word for word: the player's
  // sheets read that one, and tests/youtube_capture.mjs holds the two to each other.
  var SAY_SECURE = 'recording this tab needs the page opened at the toolbox’s https address, in Chrome or Edge';
  var SAY_BROWSER = 'only Chrome and Edge, on a computer, can record the sound of a tab';
  var SAY_READER = 'this browser cannot read the sound of a shared tab';
  var SAY_NO_SHARE = 'capture needs a secure page — open the toolbox over its https address';
  var SAY_NO_SOUND = 'the share came without its sound — share this tab again and ' +
                     'leave “Also allow tab audio” turned on';
  var SAY_NOTHING = 'nothing was heard — the tab was shared without its sound, or the video is muted';
  var SAY_SHARE_ENDED = 'the tab stopped being shared while the sound was being drawn';
  var SAY_BUSY = 'a recording is already under way in this page';
  var SAY_NO_PLAYER = 'the player has not loaded';
  var SAY_NO_LENGTH = 'the video has not said how long it is yet';
  var SAY_NO_AUDIO = 'this browser has no Web Audio';

  /* ------------------------------------------------- what this browser can do */
  // cardkit.js tabProblem, unchanged: '' when this browser can record the sound
  // of its own tab, else why not, in words a person can act on
  function problem() {
    if (!window.isSecureContext) return SAY_SECURE;
    var ua = navigator.userAgentData, md = navigator.mediaDevices;
    var chromium = !!(ua && ua.brands && ua.brands.some(function (b) { return /chromium/i.test(b.brand); }));
    if (!chromium || ua.mobile || !md || !md.getDisplayMedia) return SAY_BROWSER;
    if (!window.MediaStreamTrackProcessor && !(window.AudioContext && window.AudioWorkletNode))
      return SAY_READER;
    return '';
  }
  function capability() {
    var why = problem();
    return {ok: !why, why: why};
  }

  /* ------------------------------------------------------------ the share */
  /* SHARING THIS TAB.  One share, asked for once, serves the frame capture (its
     pictures), the cut editor on a YouTube video (its sound, which lib/cardkit.js
     records while the stretch plays) and this file's recordings: one question
     from Chrome for all of them, however many frames and clips follow.  It is
     asked for with its sound wherever the browser can record that (Chrome, Edge);
     a share given without the sound still serves the pictures, and the sound
     asks again, for a share that takes its place.  A share the person stops
     (Chrome's "Stop sharing") is asked for anew next time.  `want.audio`: the
     share must carry live sound.  (Moved here from youtube/lib/player.js.) */
  var tabShare = null;
  function tabShared(sound) {
    var s = tabShare;
    var live = function (kind) {
      return s.getTracks().some(function (t) {
        return t.kind === kind && t.readyState === 'live';
      });
    };
    return s && live('video') && (!sound || live('audio')) ? s : null;
  }
  function share(want) {
    var sound = !!(want && want.audio), have = tabShared(sound);
    if (have) return Promise.resolve(have);
    if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia)
      return Promise.reject(new Error(SAY_NO_SHARE));
    var withSound = !problem();
    // A share still live but without its sound is let go before asking
    // again: Chrome does not share this tab a second time while the first
    // share's picture is cropped to the video, as the frame capture's is
    // ("Could not start video source", however often it is asked).  Refused,
    // the next frame asks too.
    if (tabShare) {
      tabShare.getTracks().forEach(function (t) { t.stop(); });
      tabShare = null;
    }
    // preferCurrentTab and the rest are Chrome's; Firefox ignores unknown members
    return navigator.mediaDevices.getDisplayMedia({
      video: true,
      audio: withSound ? { echoCancellation: false, noiseSuppression: false, autoGainControl: false } : false,
      preferCurrentTab: true, selfBrowserSurface: 'include', systemAudio: 'exclude'
    }).then(function (s) {
      var old = tabShare;
      tabShare = s;
      if (old && old !== s) old.getTracks().forEach(function (t) { t.stop(); });
      return s;
    });
  }
  // the share as it stands, without asking: what the cut editor reads to know
  // whether Chrome is about to ask
  share.live = function (want) { return tabShared(!!(want && want.audio)); };
  function release() {
    var s = tabShare;
    tabShare = null;
    if (s) s.getTracks().forEach(function (t) { try { t.stop(); } catch (e) {} });
  }

  /* --------------------------------------------------------- the recording */
  var active = null;               // the recording under way: one at a time
  function busy() { return !!active; }
  function call(fn) {
    if (typeof fn !== 'function') return undefined;
    try { return fn.apply(null, Array.prototype.slice.call(arguments, 1)); } catch (e) { return undefined; }
  }
  function refused(opts, reason, message) {
    var err = new Error(message);
    err.reason = reason;
    call(opts.onEnd, reason);
    return {promise: Promise.reject(err), cancel: function () { return Promise.resolve(); }, state: 'done'};
  }

  function record(opts) {
    opts = opts || {};
    var player = opts.player;
    if (active) return refused(opts, 'error', SAY_BUSY);
    if (!player) return refused(opts, 'error', SAY_NO_PLAYER);
    var why = problem();
    if (why) return refused(opts, 'error', why);
    var dur = 0;
    try { dur = player.getDuration ? player.getDuration() : 0; } catch (e) {}
    if (!(dur > 0)) return refused(opts, 'error', SAY_NO_LENGTH);
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return refused(opts, 'error', SAY_NO_AUDIO);

    var keepShare = opts.keepShare !== false;
    var rec = {state: 'sharing', promise: null, cancel: null};
    var settle = {};
    rec.promise = new Promise(function (ok, no) { settle.ok = ok; settle.no = no; });
    active = rec;

    var st = null, track = null, ac = null, an = null, buf = null, peaks = null;
    var timer = 0, over = false, played = false, was = 1;
    var stalled = 0, last = -1, reached = 0;

    // ---- the ways out of it -------------------------------------------------
    function fail(reason, message) {
      var err = new Error(message);
      err.reason = reason;
      finish(reason, err);
    }
    function onShareEnded() { fail('share-ended', SAY_SHARE_ENDED); }
    function finish(reason, err) {
      if (over) return;
      over = true;
      rec.state = 'ending';
      clearInterval(timer);
      // the listener taken off, or a later "Stop sharing" would pause whatever plays then
      if (track) track.removeEventListener('ended', onShareEnded);
      if (played) {
        try { player.pauseVideo(); } catch (e) {}
        try { if (player.setPlaybackRate) player.setPlaybackRate(was); } catch (e) {}
      }
      var closing = null;
      if (ac) { try { closing = ac.close(); } catch (e) {} ac = null; }
      var result = null;
      if (!err && reason !== 'cancelled') {
        var top = 0, k;
        for (k = 0; k < peaks.length; k++) if (peaks[k] > top) top = peaks[k];
        if (!top) {
          err = new Error(SAY_NOTHING);
          err.reason = reason = 'error';
        } else {
          for (k = 0; k < peaks.length; k++) peaks[k] = Math.round(peaks[k] / top * 1000) / 1000;
          result = {reason: reason, rate: WAVE_RATE, peaks: peaks, reached: reached, duration: dur};
        }
      } else if (reason === 'cancelled') {
        result = {reason: 'cancelled', reached: reached, duration: dur};
      }
      Promise.resolve(closing).catch(function () {}).then(function () {
        if (!keepShare) release();
        rec.state = 'done';
        active = null;
        if (result && result.peaks) call(opts.onPeaks, result.peaks, WAVE_RATE);
        call(opts.onEnd, reason);
        if (result) settle.ok(result); else settle.no(err);
      });
    }
    rec.cancel = function () {
      finish('cancelled');
      return rec.promise.then(function () {}, function () {});
    };

    // ---- the clock loop --------------------------------------------------------
    function tick() {
      var v = 0, j, t = 0;
      an.getFloatTimeDomainData(buf);
      for (j = 0; j < buf.length; j++) {
        var a = buf[j] < 0 ? -buf[j] : buf[j];
        if (a > v) v = a;
      }
      try { t = player.getCurrentTime(); } catch (e) {}
      if (!isFinite(t)) return;
      // each number is filed under the VIDEO'S clock
      var slot = Math.round(t * WAVE_RATE);
      if (slot >= 0 && slot < peaks.length && v > peaks[slot]) peaks[slot] = v;
      // a video that has stopped moving for a good while has ended, or has stalled
      // past helping: either way there is no more to hear
      if (Math.abs(t - last) < 0.01) stalled++; else stalled = 0;
      last = t;
      if (t > reached) reached = t;
      if (slot % 20 === 0) call(opts.onProgress, t, dur);
      if (t >= dur - END_MARGIN) finish('ended');
      else if (stalled > STALL_TICKS) finish('stalled');
    }

    // ---- getting started -----------------------------------------------------
    share({audio: true}).then(function (s) {
      if (over) { if (!keepShare) release(); return; }
      st = s;
      // no sound: said now, before anything plays, and not after an hour of silence
      if (!st.getAudioTracks().length) {
        throw Object.assign(new Error(SAY_NO_SOUND), {reason: 'error'});
      }
      track = st.getAudioTracks()[0];
      // the browser's own rate, and nothing connected to the speakers
      ac = new AC();
      var src = ac.createMediaStreamSource(st);
      an = ac.createAnalyser();
      an.fftSize = 2048;
      an.smoothingTimeConstant = 0;
      src.connect(an);               // and to nothing else: it is not played again
      buf = new Float32Array(an.fftSize);
      peaks = [];
      for (var i = 0, n = Math.ceil(dur * WAVE_RATE) + 1; i < n; i++) peaks.push(0);
      // the video plays once, from the start, at its own speed
      try { was = player.getPlaybackRate ? player.getPlaybackRate() : 1; } catch (e) {}
      try { if (player.setPlaybackRate) player.setPlaybackRate(1); } catch (e) {}
      played = true;
      try { player.seekTo(0, true); player.playVideo(); } catch (e) {}
      rec.state = 'listening';
      call(opts.onStart, dur);
      track.addEventListener('ended', onShareEnded, {once: true});
      timer = setInterval(tick, TICK_MS);
    }).then(null, function (err) {
      if (over) return;
      var reason = (err && err.reason) || 'error';
      try { err.reason = reason; } catch (e) {}
      finish(reason, err);
    });
    return rec;
  }

  window.ParsehTabCapture = {
    capability: capability, problem: problem,
    share: share, release: release, busy: busy,
    record: record
  };
})();
