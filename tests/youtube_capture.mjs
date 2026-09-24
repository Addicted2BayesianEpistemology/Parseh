// SPDX-License-Identifier: GPL-3.0-or-later
import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=/path/to/python3 deno run --allow-all tests/youtube_capture.mjs
//      CHROME_BIN must be the FULL chrome binary (chrome-linux64/chrome): the
//      headless shell cannot capture a tab.
//      YOUTUBE_CAPTURE_SHOTS=<dir> saves the cut editor's record step and its
//      recorded state, at desktop and at phone width.
//      YT_REAL=1 also records two stretches of a real YouTube embed, one from
//      the start of the video (network).
//
// Cutting a YOUTUBE VIDEO'S SOUND (lib/cardkit.js, source kind "tab"; the
// player's card sheet, youtube/lib/player.js): the page cannot read the sound
// of YouTube's frame, so the cut editor records the tab while the stretch
// plays.  Against the REAL hub (serve.main() on a temporary toolbox) with a
// YouTube video in it, and a real tab capture: Chromium with
// --auto-accept-this-tab-capture, and WITHOUT Playwright's --mute-audio (a
// muted browser captures silence).  Only YouTube itself is faked: its
// iframe_api is answered by a script of this test whose YT.Player puts a frame
// of ANOTHER origin (a second server here, http://localhost) in the page,
// which plays a pattern of tones and answers the player's calls by
// postMessage, reporting where it is every animation frame as YouTube's own
// frame does.  The tones make a cut measurable: second k of the file holds a
// tone of 300 + 50k Hz from k.000 to k.500 s, silence after, so where a clip's
// tones start and end -- and which tones they are -- says where it was cut.
//
//  a) the sheet on the video: "cut the audio…" enabled (the kit can record a
//     tab here); an exercise deck; the editor's first step says what Chrome
//     will ask and waits for "record"; recorded: the waveform where the
//     tones are, the page's player put back as it was (paused, its place,
//     volume and speed), nothing sent to the speakers; edges nudged by ear,
//     previewed from the recording; saved: the tray's file holds the tones
//     where [start, end] says, within 25 ms; used, added to the deck: the item
//     names it as front-audio and the deck has the file
//  b) the frame capture takes its picture off the same share (Chrome asked
//     once); Anki: the editor records at once, the page's own audio muted
//     while it does and the muted player unmuted for it and muted again; the
//     note's snd_front is the tray's file, whose tones are where they should be
//  c) no track processor: the AudioWorklet path, as exact
//  d) a player that stops to load halfway: the pass is played again, and the
//     clip is still exact; at 400 px, the record step and the recorded editor
//     fit, the edge inputs show their whole value
//  e) the failures, in plain words and with no clip: a browser that cannot
//     record a tab (not Chrome or Edge) and a page that is not https, where
//     "cut the audio…" is disabled and says which; Chrome not allowed
//     ("press “Allow”"), a share without its sound ("Also allow tab audio"),
//     a video whose sound is off ("no sound was captured — is the video
//     muted?")
//  f) a frame taken off a share given without its sound (its picture
//     cropped to the video): the cut asks again, and records -- the first
//     share let go for the new one, which the next frame uses
//  g) "record again" after "save clip": the saved clip is dimmed as the old
//     recording's, and "use this clip" cuts it again from the new one (a
//     different sound now); the old clip leaves the tray
//  h) the first caption, from 0 s, on a player that says PLAYING only 0.18 s
//     into playing (as YouTube does): recorded, and a clip from 0 s exact
//  i) (YT_REAL=1) a real YouTube embed records a clip with sound in it, from
//     the middle of the video and from its very start
//  j) "reach": record again sent further back than the caption would reach
//  k) the add page's transcript editor: the captions listed, moved a tenth
//     of a second at a time, and the panel that goes back into the box
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('YOUTUBE_CAPTURE_SHOTS') || '';
const REAL = Deno.env.get('YT_REAL') === '1';
const TMP = await Deno.makeTempDir({prefix: 'parseh-youtube-capture-'});
const td = new TextDecoder();
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const eq = (got, want, m) => assert(JSON.stringify(got) === JSON.stringify(want),
                                    m + (JSON.stringify(got) === JSON.stringify(want) ? '' : ': got ' + JSON.stringify(got) + ' want ' + JSON.stringify(want)));
const near = (a, b, tol) => Math.abs(a - b) <= tol;
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, what, ms = 20000) {
  const t = Date.now();
  for (;;) {
    const v = await fn();
    if (v) return v;
    if (Date.now() - t > ms) throw Error('FAIL: timed out: ' + what);
    await sleep(80);
  }
}
async function run(cmd, args) {
  const o = await new Deno.Command(cmd, {args, cwd: root, stdout: 'piped', stderr: 'piped'}).output();
  return {code: o.code, out: td.decode(o.stdout), err: td.decode(o.stderr)};
}
async function ff(...args) {
  const r = await run('ffmpeg', ['-y', '-loglevel', 'error', ...args]);
  if (r.code) throw Error('ffmpeg: ' + r.err);
}
async function exists(p) { try { await Deno.stat(p); return true; } catch (_) { return false; } }
async function names(dir, re = /./) {
  const out = [];
  try { for await (const e of Deno.readDir(dir)) if (e.isFile && re.test(e.name)) out.push(e.name); } catch (_) {}
  return out.sort();
}
const readJson = async p => JSON.parse(await Deno.readTextFile(p));
function freePort() {
  const l = Deno.listen({hostname: '127.0.0.1', port: 0});
  const p = l.addr.port;
  l.close();
  return p;
}

/* ---------------------------------------------------------------- the tones */
// 42 s, 48 kHz mono: second k a tone of 300 + 50k Hz over [k, k + 0.5)
const FAKE = TMP + '/fake';
await Deno.mkdir(FAKE, {recursive: true});
await ff('-f', 'lavfi', '-i', "aevalsrc='if(lt(mod(t\\,1)\\,0.5)\\,0.5*sin(2*PI*(300+50*floor(t))*t)\\,0)':s=48000:d=42",
         '-ac', '1', '-c:a', 'pcm_s16le', FAKE + '/tones.wav');
// A clip's tones, measured: decoded by ffmpeg, the loudness (RMS) of every
// 5 ms, a tone where it passes 0.1; each run's frequency from the zero
// crossings of its middle (its edges hold the codec's noise of the silence
// around).  [[start, end, Hz]] in seconds from the clip's first sample.
const ANALYSE = `
import array, json, math, subprocess, sys
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", sys.argv[1], "-ac", "1", "-ar", "48000", "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
x = array.array("h"); x.frombytes(raw[:len(raw) // 2 * 2])
if sys.byteorder == "big": x.byteswap()
W = 240
loud = [math.sqrt(sum(v * v for v in x[i:i + W]) / W) / 32768 for i in range(0, len(x) - W + 1, W)]
runs, start = [], None
for k, r in enumerate(loud + [0]):
    if r > 0.1 and start is None: start = k
    elif r <= 0.1 and start is not None: runs.append((start, k)); start = None
out = []
for a, b in runs:
    n = (b - a) * W
    seg = x[a * W + n // 5:b * W - n // 5]
    zc = sum(1 for i in range(1, len(seg)) if (seg[i - 1] < 0) != (seg[i] < 0))
    d = max(1, len(seg)) / 48000
    out.append([a * W / 48000, b * W / 48000, round(zc / 2 / d, 1)])
L = 2400
rms50 = [round(math.sqrt(sum(v * v for v in x[i:i + L]) / L) / 32768, 4) for i in range(0, len(x) - L + 1, L)]
print(json.dumps({"duration": len(x) / 48000, "runs": out, "peak": max((abs(v) for v in x), default=0) / 32768, "rms50": rms50}))
`;
async function measure(path) {
  const r = await run(PY, ['-c', ANALYSE, path]);
  if (r.code) throw Error('analysis: ' + r.err);
  return JSON.parse(r.out);
}
// the tones a clip [s, e] of the pattern holds, from its first sample
function expectedTones(s, e) {
  const out = [];
  for (let k = Math.floor(s) - 1; k <= Math.ceil(e); k++) {
    const a = Math.max(k, s), b = Math.min(k + 0.5, e);
    if (b - a >= 0.02) out.push([a - s, b - s, 300 + 50 * k]);
  }
  return out;
}
// every tone within 25 ms of where [s, e] puts it, each the right one
async function clipIsExact(path, s, e, what) {
  const m = await measure(path), want = expectedTones(s, e);
  const got = m.runs.filter(r => r[1] - r[0] >= 0.015);
  const show = x => JSON.stringify(x.map(r => [+r[0].toFixed(3), +r[1].toFixed(3), r[2]]));
  assert(near(m.duration, e - s, 0.03), `${what}: the clip lasts ${m.duration.toFixed(3)} s for ${s.toFixed(2)}–${e.toFixed(2)}`);
  assert(got.length === want.length && want.every((w, i) => near(got[i][0], w[0], 0.025) && near(got[i][1], w[1], 0.025)
                                                    && (w[1] - w[0] < 0.1 || near(got[i][2], w[2], 25))),
         `${what}: its tones start and end within 25 ms of where the edges put them, and are the right ones: ` +
         `got ${show(got)} want ${show(want)}`);
  return m;
}

/* ---------------------------------------------------------------- the fake YouTube */
// The frame YouTube would put in the page, from another origin: a media
// element driven by postMessage, reporting where it is every animation frame.
// ?deaf=1: a video whose sound is off whatever the player is told;
// ?stall=1: the first play stops to load for 400 ms, 1.5 s in;
// ?late=1: every play says BUFFERING for its first 0.18 s of playing, and
// PLAYING only after, as a real YouTube frame was seen to (driven: PLAYING
// first at 0.176 s of a video played from 0).
const CHILD_HTML = `<!doctype html><meta charset="utf-8"><title>not YouTube</title>
<body style="margin:0;background:#1d2733;color:#cde;font:13px sans-serif;display:grid;place-items:center">
<div>a frame of another origin <b id="at">0.00</b></div><audio id="a" preload="auto"></audio>
<script>
const a = document.getElementById('a'), q = new URLSearchParams(location.search);
const deaf = q.get('deaf') === '1', late = q.get('late') === '1';
let stall = q.get('stall') === '1', stallTimer = 0, started = false, waiting = false, lateFrom = null;
a.src = q.get('src') || 'tones.wav';
if (deaf) a.muted = true;
a.addEventListener('waiting', () => { waiting = true; });
a.addEventListener('playing', () => { waiting = false; });
function state() {
  if (lateFrom != null && !a.paused && a.currentTime - lateFrom < 0.18) return 3;
  lateFrom = null;
  return a.ended ? 0 : !started ? 5 : (waiting && !a.paused) ? 3 : a.paused ? 2 : 1;
}
function post() {
  parent.postMessage(JSON.stringify({event: 'infoDelivery', info: {currentTime: a.currentTime, playerState: state(),
    duration: a.duration || 0, muted: deaf ? false : a.muted, volume: Math.round(a.volume * 100), playbackRate: a.playbackRate}}), '*');
}
// its picture changes as it plays, as a video's does (a share of the tab
// sends a picture only when something in it changes)
const at = document.getElementById('at');
(function loop() { post(); at.textContent = a.currentTime.toFixed(2); requestAnimationFrame(loop); })();
addEventListener('message', e => {
  let m; try { m = JSON.parse(e.data); } catch (_) { return; }
  const x = (m.args || [])[0];
  if (m.func === 'seekTo') a.currentTime = x;
  else if (m.func === 'playVideo') {
    started = true;
    if (late) lateFrom = a.currentTime;
    a.play().catch(err => parent.postMessage(JSON.stringify({event: 'onError', info: String(err)}), '*'));
    if (stall) {
      // stops to load, and goes on by itself -- unless it is paused meanwhile
      stall = false;
      stallTimer = setTimeout(() => { a.pause(); waiting = true; post();
                                      stallTimer = setTimeout(() => { waiting = false; a.play(); }, 400); }, 1500);
    }
  }
  else if (m.func === 'pauseVideo') { clearTimeout(stallTimer); waiting = false; a.pause(); }
  else if (m.func === 'mute') a.muted = true;
  else if (m.func === 'unMute') a.muted = deaf;
  else if (m.func === 'setVolume') a.volume = Math.max(0, Math.min(1, x / 100));
  else if (m.func === 'setPlaybackRate') a.playbackRate = x;
  post();
});
a.addEventListener('loadedmetadata', () => parent.postMessage(JSON.stringify({event: 'onReady'}), '*'), {once: true});
</script>`;
// The IFrame API as the page loads it from https://www.youtube.com/iframe_api
const fakeApi = (child, query) => `(function () {
  var CHILD = ${JSON.stringify(child)}, ORIGIN = new URL(CHILD).origin;
  function Player(id, opts) {
    var self = this, el = document.getElementById(id), f = document.createElement('iframe');
    f.id = id; f.setAttribute('allow', 'autoplay');
    f.src = CHILD + '/child.html?' + ${JSON.stringify(query)};
    el.parentNode.replaceChild(f, el);
    var info = {currentTime: 0, playerState: -1, duration: 0, muted: false, volume: 100, playbackRate: 1};
    var ready = false, ev = (opts && opts.events) || {};
    window.addEventListener('message', function (e) {
      if (e.origin !== ORIGIN || e.source !== f.contentWindow) return;
      var m; try { m = JSON.parse(e.data); } catch (x) { return; }
      if (m.event === 'infoDelivery') {
        var was = info.playerState;
        for (var k in m.info) info[k] = m.info[k];
        if (ready && was !== info.playerState && ev.onStateChange) ev.onStateChange({target: self, data: info.playerState});
      } else if (m.event === 'onReady' && !ready) {
        ready = true;
        if (ev.onReady) ev.onReady({target: self});
      }
    });
    function send(func, args) { f.contentWindow.postMessage(JSON.stringify({func: func, args: args || []}), ORIGIN); }
    this.getIframe = function () { return f; };
    this.playVideo = function () { send('playVideo'); };
    this.pauseVideo = function () { send('pauseVideo'); };
    this.seekTo = function (t, ahead) { info.currentTime = t; send('seekTo', [t, ahead]); };
    this.getCurrentTime = function () { return info.currentTime; };
    this.getPlayerState = function () { return info.playerState; };
    this.getDuration = function () { return info.duration; };
    this.isMuted = function () { return info.muted; };
    this.mute = function () { info.muted = true; send('mute'); };
    this.unMute = function () { info.muted = false; send('unMute'); };
    this.getVolume = function () { return info.volume; };
    this.setVolume = function (v) { info.volume = v; send('setVolume', [v]); };
    this.getPlaybackRate = function () { return info.playbackRate; };
    this.setPlaybackRate = function (r) { info.playbackRate = r; send('setPlaybackRate', [r]); };
    (window.__fakeYT = window.__fakeYT || []).push(this);
  }
  window.YT = {Player: Player, PlayerState: {UNSTARTED: -1, ENDED: 0, PLAYING: 1, PAUSED: 2, BUFFERING: 3, CUED: 5}};
  setTimeout(function () { if (window.onYouTubeIframeAPIReady) window.onYouTubeIframeAPIReady(); }, 0);
})();`;
const P2 = freePort();
const TYPES = {html: 'text/html; charset=utf-8', wav: 'audio/wav'};
async function serveFake(req) {
  const u = new URL(req.url), name = u.pathname.replace(/^\/+/, '');
  if (name === 'child.html') return new Response(CHILD_HTML, {headers: {'content-type': TYPES.html}});
  if (name !== 'tones.wav') return new Response('404', {status: 404});
  const data = await Deno.readFile(FAKE + '/tones.wav');
  const h = new Headers({'content-type': TYPES.wav, 'accept-ranges': 'bytes', 'cache-control': 'no-store'});
  const m = /bytes=(\d*)-(\d*)/.exec(req.headers.get('range') || '');
  if (m) {
    const s = m[1] ? +m[1] : data.length - +m[2];
    const e = m[1] && m[2] ? Math.min(+m[2], data.length - 1) : data.length - 1;
    h.set('content-range', `bytes ${s}-${e}/${data.length}`);
    return new Response(data.slice(s, e + 1), {status: 206, headers: h});
  }
  return new Response(data, {headers: h});
}
const fakeServers = new AbortController();
Deno.serve({hostname: '127.0.0.1', port: P2, signal: fakeServers.signal, onListen() {}}, serveFake);
try { Deno.serve({hostname: '::1', port: P2, signal: fakeServers.signal, onListen() {}}, serveFake); } catch (_) {}
const CHILD = `http://localhost:${P2}`;

/* ---------------------------------------------------------------- the tree and the hub */
const IT_FIX = 'tests/fixtures/videos/italian/kL9mN1oP3qR';
const YT = 'kL9mN1oP3qR', REAL_ID = 'jNQXAC9IVRw', ZERO = 'zR0aB1cD2eF';
const ROOT = TMP + '/root', VIDEOS = ROOT + '/youtube/videos';
const TRAY = TMP + '/tray', EXERCISES = TMP + '/exercises', ANKI = TMP + '/anki';
async function copyVideo(id, edit) {
  const d = `${VIDEOS}/italian/${id}`;
  await Deno.mkdir(d + '/parts', {recursive: true});
  const meta = await readJson(IT_FIX + '/video.json');
  meta.id = id;
  meta.url = 'https://www.youtube.com/watch?v=' + id;
  await Deno.writeTextFile(d + '/video.json', JSON.stringify(meta, null, 1));
  const ann = await readJson(IT_FIX + '/annotations.json');
  ann.video = id;
  if (edit) edit(ann);
  await Deno.writeTextFile(d + '/annotations.json', JSON.stringify(ann, null, 1));
}
await Deno.mkdir(ROOT + '/youtube', {recursive: true});
await Deno.symlink(root + '/lib', ROOT + '/lib');
await Deno.symlink(root + '/youtube/lib', ROOT + '/youtube/lib');
for (const d of [TRAY, EXERCISES, ANKI, TMP + '/library']) await Deno.mkdir(d, {recursive: true});
await copyVideo(YT);
// the first caption with words at 0.4 s, so that its stretch starts at 0
const fromZero = ann => { ann.segments.splice(0, 1); ann.segments[0].start = 0.4; };
await copyVideo(ZERO, fromZero);
// the real "Me at the zoo" is 19 s: its captions end before that
if (REAL) await copyVideo(REAL_ID, ann => { ann.segments = ann.segments.filter(s => s.start < 15); fromZero(ann); });

const BOOT = `
import os, sys
from pathlib import Path
REPO = Path(sys.argv[1]); tmp = Path(sys.argv[2]); port = sys.argv[3]
for folder in ("markdown/exlex", "markdown/app", "youtube/lib", "lib", "."):
    sys.path.insert(0, str(REPO / folder))
os.chdir(str(REPO))
import audiofile, clips, decks, store
clips.set_dir(tmp / "tray")
import serve, ytpages
for st in {store, serve.studio.store}:
    st.LIB = tmp / "library"
    st.set_clips_dir(tmp / "tray")
decks.set_dir(tmp / "exercises")
decks.set_clips_dir(tmp / "tray")
# WHAT THIS MACHINE KEEPS, into the temporary tree (lib/prefs.py, and
# lib/network.py since the network settings): a suite must never read the
# owner's own reading places, theme or network doors -- nor write them, which
# is what happened here: a suite turned the theme to dark in the real
# config/prefs.json and every page of the next suite opened dark.
import prefs
import network
prefs.STORE = str(tmp / "config" / "prefs.json")
network.STORE = str(tmp / "config" / "network.json")
import offline  # the phone-keeping memories (lib/offline.py) too
offline.DIGESTS = str(tmp / "config" / "digests.json")
offline.WHERES = str(tmp / "config" / "wheres.json")
serve.ROOT = str(tmp / "root")
serve._AtRoot.directory = str(tmp / "root")
ytpages.VIDEOS = str(tmp / "root" / "youtube" / "videos")
serve.ANKI = ytpages.ANKI = str(tmp / "anki")
ytpages.INBOX = str(tmp / "anki" / "inbox")
sys.argv = ["serve.py", "--http", "--local", port]
serve.main()
`;
const port = freePort(), log = [];
const hub = new Deno.Command(PY, {args: ['-c', BOOT, root, TMP, String(port)], cwd: root,
                                  stdout: 'piped', stderr: 'piped'}).spawn();
for (const s of [hub.stdout, hub.stderr])
  (async () => { for await (const chunk of s.pipeThrough(new TextDecoderStream())) log.push(chunk); })();
const BASE = `http://127.0.0.1:${port}`;
{
  const t = Date.now();
  for (;;) {
    try { const r = await fetch(BASE + '/clips/api/status'); const j = await r.json(); if (r.ok && j.ffmpeg) break; } catch (_) {}
    if (Date.now() - t > 60000) throw Error('the hub did not start:\n' + log.join(''));
    await sleep(250);
  }
}

/* ---------------------------------------------------------------- the browsers */
const ARGS = ['--autoplay-policy=no-user-gesture-required', '--disable-audio-output'];
const launch = args => chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true, args,
                                        // a muted browser captures silence
                                        ignoreDefaultArgs: ['--mute-audio']});
const browser = await launch(['--auto-accept-this-tab-capture', ...ARGS]);
let browserNo = null;
const errors = [];
// A page of the player.  `query` goes to the fake frame; `init` runs in the
// page before its own scripts.  Every getDisplayMedia call is counted, and
// every connection of an audio node to the speakers.
async function newPage(b, {width = 1280, height = 900, query = 'src=tones.wav', init = null, real = false} = {}) {
  const context = await b.newContext({viewport: {width, height}});
  await context.addInitScript(() => {
    window.__asked = [];
    window.__toSpeakers = 0;
    const md = navigator.mediaDevices;
    if (md && md.getDisplayMedia) {
      const ask = md.getDisplayMedia.bind(md);
      md.getDisplayMedia = o => { window.__asked.push(o); return ask(o); };
    }
    if (window.AudioNode) {
      const connect = AudioNode.prototype.connect;
      AudioNode.prototype.connect = function (to, ...rest) {
        if (to instanceof AudioDestinationNode) window.__toSpeakers++;
        return connect.call(this, to, ...rest);
      };
    }
  });
  if (init) await context.addInitScript(init);
  const page = await context.newPage();
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|youtube\.com/.test(m.text())) errors.push('console: ' + m.text()); });
  page.on('response', r => {
    const u = new URL(r.url());
    if (u.host === `127.0.0.1:${port}` && r.status() >= 400
        && /^\/(clips|exercises\/api|anki|youtube\/api|lib\/cardkit|studio\/static)/.test(u.pathname))
      errors.push(r.status() + ' ' + r.request().method() + ' ' + u.pathname);
  });
  if (!real) {
    // nothing leaves the machine: YouTube's API is this test's
    await context.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, route => route.abort());
    await context.route('https://www.youtube.com/iframe_api', route =>
      route.fulfill({status: 200, contentType: 'text/javascript', body: fakeApi(CHILD, query)}));
  }
  return {context, page};
}
// drawn: laid out and visible (whatever its hidden attribute says)
const rendered = (page, sel) => page.evaluate(sel => {
  const el = document.querySelector(sel);
  return !!el && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
}, sel);
const shown = (page, sel) => page.evaluate(sel => {
  const el = document.querySelector(sel);
  if (!el || el.closest('[hidden]')) return false;
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden';
}, sel);
// really on screen: inside the viewport, and what is at its middle is it
const onScreen = (page, sel) => page.evaluate(sel => {
  const el = document.querySelector(sel);
  if (!el || el.closest('[hidden]')) return false;
  const r = el.getBoundingClientRect();
  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  return r.width > 0 && r.left >= 0 && r.top >= 0 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1 && !!hit && el.contains(hit);
}, sel);
const text = (page, sel) => page.evaluate(sel => document.querySelector(sel).textContent, sel);
const value = (page, sel) => page.evaluate(sel => document.querySelector(sel).value, sel);
const stat = page => page.evaluate(() => { const s = document.querySelector('.pc-stat'); return s ? s.textContent : ''; });
async function shot(page, name) {
  if (!SHOTS) return;
  await Deno.mkdir(SHOTS, {recursive: true});
  await page.screenshot({path: `${SHOTS}/${name}.png`});
}
// the fake frame, as the page sees it
const childFrame = page => page.frames().find(f => f.url().startsWith(CHILD));
const childState = page => childFrame(page).evaluate(() => {
  const a = document.querySelector('audio');
  return {t: a.currentTime, paused: a.paused, muted: a.muted, volume: a.volume, rate: a.playbackRate};
});
async function openVideo(page, id = YT) {
  await page.goto(`${BASE}/youtube/v/${id}/`);
  await page.waitForSelector('.seg .fa .w');
  await until(() => page.evaluate(() => window.__fakeYT && __fakeYT[0] && __fakeYT[0].getDuration() > 40), 'the fake player is ready');
}
async function altClick(page, sel) {
  await page.mouse.move(2, 2);
  await page.locator(sel).click({modifiers: ['Alt']});
  await until(() => page.evaluate(() => !document.querySelector('#anki').hidden), 'the card sheet opens');
}
// the editor's record step, then the recording: resolves once the editor
// holds a recording, with the status it says
async function recordIn(page, what, {click = true} = {}) {
  if (click) {
    assert(await onScreen(page, '.pc-cut .pc-record'), what + ': the record button is on screen');
    await page.click('.pc-cut .pc-record');
  }
  await until(async () => {
    // a recording that failed says so at once, in what it said
    if (await page.evaluate(() => document.querySelector('.pc-stat').classList.contains('pc-bad')))
      throw Error('FAIL: ' + what + ': the stretch is not recorded: ' + await stat(page));
    return (await shown(page, '.pc-strip')) && /^recorded /.test(await stat(page)) &&
           await page.evaluate(() => document.querySelector('.pc-strip').classList.contains('pc-drawn'));
  }, what + ': the stretch is recorded (' + await stat(page) + ')', 40000);
  return stat(page);
}
// what the strip shows, [from, to], as the scale under it prints them
const viewOf = page => page.evaluate(() => {
  const sc = document.querySelector('.pc-strip').nextElementSibling;
  return [parseFloat(sc.children[0].textContent), parseFloat(sc.children[2].textContent)];
});
// the waveform's canvas: how much is drawn at the middle of each [t0, t1]
const drawnAt = (page, spans) => page.evaluate(spans => {
  const c = document.querySelector('.pc-wave'), strip = c.parentNode;
  const v0 = parseFloat(strip.nextElementSibling.children[0].textContent), v1 = parseFloat(strip.nextElementSibling.children[2].textContent);
  const x = c.getContext('2d'), k = c.width / strip.clientWidth;
  return spans.map(([a, b]) => {
    const px = Math.round(((a + b) / 2 - v0) / (v1 - v0) * c.width);
    const col = x.getImageData(Math.max(0, px - 2 * k), 0, Math.max(1, 4 * k), c.height).data;
    let on = 0;
    for (let i = 3; i < col.length; i += 4) if (col[i] > 0) on++;
    return on / (col.length / 4);
  });
}, spans);
async function saveAndUse(page, what, video = YT) {
  const s = +(await value(page, '.pc-cut input.e0')), e = +(await value(page, '.pc-cut input.e1'));
  const before = await names(TRAY, /\.(mp3|m4a|wav)$/);
  await page.click('.pc-cut .pc-save');
  await until(async () => /saved to the clip tray/.test(await stat(page)), what + ': the clip is saved', 20000);
  const fresh = (await names(TRAY, /\.(mp3|m4a|wav)$/)).filter(n => !before.includes(n));
  assert(fresh.length === 1, `${what}: one new file in the tray: ${fresh}`);
  const meta = await readJson(`${TRAY}/${fresh[0]}.json`);
  assert(meta.source && meta.source.kind === 'youtube' && meta.source.video === video && near(meta.source.start, s, 0.001),
         `${what}: the tray says where it was cut from: ${JSON.stringify(meta.source)}`);
  await page.click('.pc-cut .pc-use');
  await until(() => page.evaluate(() => !document.querySelector('.pc-root') && !document.querySelector('#asndprev').hidden), what + ': the editor closes on the clip');
  eq(await page.evaluate(() => document.querySelector('#asndname').textContent.split(' · ')[0]), fresh[0], what + ': the sheet shows the clip');
  return {name: fresh[0], s, e};
}

try {
/* ================================================================ a) an exercise deck */
console.log('a) the editor records the stretch, and cuts it');
const {context, page} = await newPage(browser);
await page.goto(BASE + '/');
await page.evaluate(() => localStorage.clear());
await openVideo(page);
eq(await page.evaluate(() => [!!document.querySelector('#film'), document.querySelector('#yt').tagName, ParsehCards.canCaptureTab(), ParsehCards.tabProblem()]),
   [false, 'IFRAME', true, ''], 'a YouTube video: no film, the player\'s frame of another origin, and this Chrome can record the tab');
// the person's own player settings, which the recording must leave as they were
await page.evaluate(() => { __fakeYT[0].setVolume(40); __fakeYT[0].setPlaybackRate(1.25); __fakeYT[0].seekTo(16.2, true); });
await until(async () => { const c = await childState(page); return near(c.volume, 0.4, 0.01) && c.rate === 1.25 && near(c.t, 16.2, 0.05); }, 'the player set up');
await altClick(page, '.seg[data-i="3"] .w[data-j="1"] .wd >> nth=1');
eq(await page.evaluate(() => { const b = document.querySelector('#asnd'); return [document.querySelector('#afa').value, b.disabled, b.title, document.querySelector('#asndwhy').getClientRects().length > 0]; }),
   ['chilo', false, 'record this tab while the video plays the stretch this card is about, cut the clip out of it by ear, and put it on the card', false],
   'the sheet on "chilo": "cut the audio…" enabled on a YouTube video, saying what it does');
await page.click('#atdeck');
await until(() => page.evaluate(() => document.querySelector('#asavelab').textContent === 'add to deck'), 'the exercise deck destination');
await page.fill('#adecknew', 'Dal video');
await page.click('#asnd');
await until(() => shown(page, '.pc-cut .pc-take'), 'the editor opens on its record step');
const step = await page.evaluate(() => ({text: document.querySelector('.pc-take-text').textContent,
  drawn: ['.pc-strip', '.pc-scale', '.pc-rows', '.pc-save', '.pc-use', '.pc-again', '.pc-hint'].map(s => document.querySelector('.pc-cut ' + s).getClientRects().length > 0),
  record: getComputedStyle(document.querySelector('.pc-cut .pc-record')).backgroundColor,
  use: getComputedStyle(document.querySelector('.pc-cut .pc-use')).backgroundColor,
  asked: window.__asked.length}));
eq(step.drawn, [false, false, false, false, false, false, false], 'before a recording the editor draws no strip, no rows and nothing to save');
eq(step.record, step.use, '"record" is drawn as the step\'s one action, in the colour of "use this clip"');
assert(/sound is cut from a recording of this tab/.test(step.text) && /14\.00–21\.00 s plays once, sound on/.test(step.text) &&
       /press “Allow”, and leave “Also allow tab audio” turned on/.test(step.text) && step.asked === 0,
       'it says what happens and what Chrome will ask, and has not asked yet: ' + step.text);
await shot(page, 'record-step-desktop');
await recordIn(page, '"chilo"');
const asked = await page.evaluate(() => window.__asked.map(o => ({audio: !!o.audio, preferCurrentTab: o.preferCurrentTab, video: o.video})));
eq(asked, [{audio: true, preferCurrentTab: true, video: true}], 'Chrome was asked once, for this tab with its sound');
const after1 = await childState(page);
assert(after1.paused && near(after1.t, 16.2, 0.1) && near(after1.volume, 0.4, 0.01) && after1.rate === 1.25 && !after1.muted,
       'the player is put back as it was: paused at its place, its volume and its speed: ' + JSON.stringify(after1));
eq(await page.evaluate(() => window.__toSpeakers), 0, 'nothing of the recording was connected to the speakers');
const v1 = await page.evaluate(() => [document.querySelector('.pc-cut input.e0').value, document.querySelector('.pc-cut input.e1').value,
                                     document.querySelector('.pc-scale').textContent]);
eq(v1.slice(0, 2), ['17.62', '18.83'], 'the edges start at the word\'s share of the caption');
eq(await page.evaluate(() => ['.pc-take', '.pc-strip', '.pc-rows', '.pc-again', '.pc-save', '.pc-use'].map(s => document.querySelector('.pc-cut ' + s).getClientRects().length > 0)),
   [false, true, true, true, true, true], 'recorded: the first step gives way to the strip, the rows, "record again", save and use');
const drawn = await drawnAt(page, [[16, 16.5], [16.5, 17], [19, 19.5], [19.5, 20]]);
assert(drawn[0] > 0.25 && drawn[1] < 0.05 && drawn[2] > 0.25 && drawn[3] < 0.05,
       'the waveform is drawn from the recording: the tones are there, the silences empty: ' + JSON.stringify(drawn.map(x => +x.toFixed(2))));
await shot(page, 'recorded-desktop');
// by ear: the start half a second earlier, the end a tenth later; each nudge
// plays from the recording
await page.click('.pc-cut [data-e="s-5"]');
await until(() => page.evaluate(() => { const p = document.querySelector('.pc-play'); return !p.paused && p.currentTime > 0.1; }), 'the start nudge plays');
const heard = await page.evaluate(() => { const p = document.querySelector('.pc-play'); return [p.src.slice(0, 5), p.readyState]; });
assert(heard[0] === 'blob:' && heard[1] >= 2, 'the nudge is played from the recording itself: ' + heard);
await page.click('.pc-cut [data-e="e+"]');
eq([await value(page, '.pc-cut input.e0'), await value(page, '.pc-cut input.e1')], ['17.12', '18.93'], 'the edges moved');
const clipA = await saveAndUse(page, '"chilo"');
await clipIsExact(`${TRAY}/${clipA.name}`, clipA.s, clipA.e, '"chilo"');
await page.click('#asave');
await until(() => page.evaluate(() => /^added ✓/.test(document.querySelector('#astat').textContent)), 'the card goes into the deck', 20000);
{
  let slug = '';
  for await (const e of Deno.readDir(EXERCISES + '/italian')) if (e.isDirectory && !e.name.startsWith('.')) slug = e.name;
  const DECK = `${EXERCISES}/italian/${slug}`, items = await names(DECK + '/items', /\.json$/);
  const item = await readJson(`${DECK}/items/${items[0]}`);
  assert(items.length === 1 && item.markdown.includes('front-audio: audio/' + clipA.name) && await exists(`${DECK}/audio/${clipA.name}`),
         'the deck\'s exercise names the recording as front-audio, and the deck has the file:\n' + item.markdown);
  eq(await text(page, '#astat'), 'added ✓ — a vocabulary card for “chilo”, with its recording, to “Dal video” — open the deck', 'the sheet says it went in with its recording');
}

/* ================================================================ b) the frame, and Anki */
console.log('b) the frame capture shares the tab; Anki');
await page.click('#ashot');
await until(() => page.evaluate(() => { const i = document.querySelector('#ashotimg'); return !document.querySelector('#ashotprev').hidden && i.naturalWidth > 100; }),
            'the frame is captured', 40000).catch(async e => { throw Error(e.message + ': ' + await text(page, '#astat')); });
eq(await page.evaluate(() => window.__asked.length), 1, 'the frame is taken off the same share: Chrome was not asked again');
await page.keyboard.press('Escape');
await until(() => page.evaluate(() => document.querySelector('#anki').hidden), 'the sheet closes');
// the person had muted the player: it is unmuted for the recording and muted again
await page.evaluate(() => __fakeYT[0].mute());
await until(async () => (await childState(page)).muted, 'the player muted');
await altClick(page, '.seg[data-i="2"] .w[data-j="1"] .wd >> nth=1');
await page.click('#atanki');
await until(() => page.evaluate(() => document.querySelector('#asavelab').textContent === 'save card'), 'Anki');
await page.fill('#adecknew', 'Italiano::YouTube');
// a sound of the page's own: it must not be heard in the tab's recording
await page.evaluate(name => {
  const a = document.createElement('audio');
  a.id = 'pagesound'; a.loop = true; a.src = '/clips/media/' + name;
  document.body.appendChild(a);
  return a.play();
}, clipA.name);
await page.click('#asnd');
const during = await until(() => page.evaluate(() => {
  const s = document.querySelector('.pc-stat'), a = document.querySelector('#pagesound');
  return s && /^recording .*: \d/.test(s.textContent) ? {muted: a.muted, paused: a.paused, stat: s.textContent, record: document.querySelector('.pc-take').getClientRects().length > 0} : null;
}), 'the recording starts by itself: the tab is shared already');
assert(during.muted && during.paused && during.record, 'it records at once, with the page\'s own audio muted and stopped meanwhile: ' + JSON.stringify(during));
const childDuring = await childState(page);
assert(!childDuring.muted && childDuring.volume === 1 && childDuring.rate === 1, 'the player plays unmuted, at full volume and normal speed while it records: ' + JSON.stringify(childDuring));
await recordIn(page, '"mele"', {click: false});
const after2 = await childState(page);
assert(after2.muted && near(after2.volume, 0.4, 0.01) && after2.rate === 1.25 && after2.paused,
       'the muted player is muted again after it: ' + JSON.stringify(after2));
eq(await page.evaluate(() => [window.__asked.length, document.querySelector('#pagesound').muted]), [1, false], 'still one question from Chrome, and the page\'s audio is unmuted again');
await page.evaluate(() => document.querySelector('#pagesound').remove());
const clipB = await saveAndUse(page, '"mele"');
await clipIsExact(`${TRAY}/${clipB.name}`, clipB.s, clipB.e, '"mele"');
await page.click('#asave');
await until(() => page.evaluate(() => document.querySelector('#anki').hidden), 'the Anki card is saved and the sheet closes', 20000);
{
  let slug = '';
  for await (const e of Deno.readDir(ANKI + '/italian')) if (e.isDirectory) slug = e.name;
  const cards = await names(`${ANKI}/italian/${slug}/cards`, /\.json$/);
  const note = await readJson(`${ANKI}/italian/${slug}/cards/${cards[0]}`);
  assert(note.fa === 'mele' && /-front-audio\.(mp3|m4a|wav)$/.test(note.snd_front || '') && note.snd_back === null,
         'the Anki note carries the recording on the front: ' + JSON.stringify({fa: note.fa, snd_front: note.snd_front, snd_back: note.snd_back}));
  const media = await Deno.readFile(`${ANKI}/italian/${slug}/media/${note.snd_front}`), tray = await Deno.readFile(`${TRAY}/${clipB.name}`);
  assert(media.length === tray.length && media.every((b, i) => b === tray[i]), 'its media/ holds the tray\'s clip, byte for byte');
}
await page.evaluate(() => __fakeYT[0].unMute());
await context.close();

/* ================================================================ c) the worklet path */
console.log('c) no track processor: an AudioWorklet');
{
  const {context: cw, page: pw} = await newPage(browser, {init: () => {
    delete window.MediaStreamTrackProcessor;
    window.__worklets = 0;
    const add = AudioWorklet.prototype.addModule;
    AudioWorklet.prototype.addModule = function (...a) { window.__worklets++; return add.apply(this, a); };
  }});
  await openVideo(pw);
  await altClick(pw, '.seg[data-i="5"] .w[data-j="1"] .wd');
  await pw.click('#asnd');
  await until(() => shown(pw, '.pc-cut .pc-record'), 'the record step');
  await recordIn(pw, 'the worklet');
  eq(await pw.evaluate(() => [typeof MediaStreamTrackProcessor, window.__worklets, window.__toSpeakers]), ['undefined', 1, 0],
     'recorded through an AudioWorklet, which is connected to no speaker');
  await pw.click('.pc-cut [data-e="s-5"]');
  const clipW = await saveAndUse(pw, 'the worklet');
  await clipIsExact(`${TRAY}/${clipW.name}`, clipW.s, clipW.e, 'the worklet');
  await cw.close();
}

/* ================================================================ d) a stall, and the phone */
console.log('d) a player that stops to load; the phone');
{
  const {context: cp, page: pp} = await newPage(browser, {width: 400, height: 820, query: 'src=tones.wav&stall=1'});
  await openVideo(pp);
  await pp.evaluate(() => document.querySelector('.seg[data-i="3"]').scrollIntoView({block: 'center'}));
  await altClick(pp, '.seg[data-i="3"] .w[data-j="1"] .wd >> nth=1');
  await pp.click('#asnd');
  await until(() => shown(pp, '.pc-cut .pc-record'), 'the record step on the phone');
  assert(await onScreen(pp, '.pc-cut .pc-take') && await pp.evaluate(() => document.querySelector('.pc-cut').scrollWidth <= document.querySelector('.pc-cut').clientWidth),
         'at 400 px the record step is on screen, nothing wider than the editor');
  await shot(pp, 'record-step-phone');
  await pp.click('.pc-cut .pc-record');
  await until(async () => /once more/.test(await stat(pp)), 'the stall is noticed and the stretch played once more', 30000);
  assert(true, 'the player stopped to load: ' + await stat(pp));
  await recordIn(pp, 'after the stall', {click: false});
  for (const sel of ['.pc-strip', '.pc-cut [data-e="s-1"]', '.pc-cut [data-e="e+1"]', '.pc-cut [data-e="rv"]',
                     '.pc-cut input.pc-r0', '.pc-cut input.pc-r1',
                     '.pc-cut .pc-again', '.pc-cut .pc-save', '.pc-cut .pc-use'])
    assert(await onScreen(pp, sel), `at 400 px ${sel} is on screen`);
  // the edges' inputs show their whole value, a long video's too: an input
  // whose text is cut scrolls, wider than it is (spin buttons and all)
  const fit = async () => pp.evaluate(() => [...document.querySelectorAll('.pc-cut .edit input')].map(inp => [inp.value, inp.scrollWidth, inp.clientWidth]));
  const f1 = await fit();
  assert(f1.map(f => f[0]).join() === '17.62,18.83,0,0' && f1.every(([, sw, cw]) => sw <= cw),
         'at 400 px each edge\'s input, and the two reach boxes, show their whole value ' +
         '(scrollWidth within clientWidth): ' + JSON.stringify(f1));
  await pp.evaluate(() => { const i = document.querySelector('.pc-cut input.e0'); i.value = '1234.56'; });
  const f2 = await fit();
  assert(f2[0][1] <= f2[0][2], 'and a value of an hour-long video, 1234.56: ' + JSON.stringify(f2[0]));
  await pp.evaluate(() => { document.querySelector('.pc-cut input.e0').value = '17.62'; });
  assert(await pp.evaluate(() => document.documentElement.scrollWidth <= innerWidth && document.querySelector('.pc-cut').scrollWidth <= document.querySelector('.pc-cut').clientWidth),
         'at 400 px nothing is wider than the phone');
  await shot(pp, 'recorded-phone');
  const clipS = await saveAndUse(pp, 'after the stall');
  await clipIsExact(`${TRAY}/${clipS.name}`, clipS.s, clipS.e, 'after the stall');
  await cp.close();
}

/* ================================================================ e) failures */
console.log('e) failures, said in plain words');
// a clip must not come of any of them
const trayBefore = await names(TRAY);
browserNo = await launch(ARGS);
{
  // where no tab can be recorded, the button says why, and which it is
  const why = async (init, what) => {
    const {context: cx, page: px} = await newPage(browserNo, {init});
    await openVideo(px);
    await altClick(px, '.seg[data-i="3"] .w[data-j="1"] .wd >> nth=1');
    const r = await px.evaluate(() => { const b = document.querySelector('#asnd'), h = document.querySelector('#asndwhy');
      return [b.disabled, b.title, h.getClientRects().length > 0 ? h.textContent : null]; });
    await cx.close();
    return r;
  };
  // Firefox and Safari: no userAgentData, which only Chromium has
  eq(await why(() => { Object.defineProperty(Navigator.prototype, 'userAgentData', {get: () => undefined}); }),
     [true, 'a YouTube video’s sound is cut from a recording of this tab, and only Chrome and Edge, on a computer, can record the sound of a tab',
      'a YouTube video’s sound is cut from a recording of this tab, and only Chrome and Edge, on a computer, can record the sound of a tab'],
     'not Chrome or Edge: "cut the audio…" is disabled, and says so under it');
  eq(await why(() => { Object.defineProperty(window, 'isSecureContext', {get: () => false}); }),
     [true, 'a YouTube video’s sound is cut from a recording of this tab, and recording this tab needs the page opened at the toolbox’s https address, in Chrome or Edge',
      'a YouTube video’s sound is cut from a recording of this tab, and recording this tab needs the page opened at the toolbox’s https address, in Chrome or Edge'],
     'not https: disabled, saying to open the https address');
}
{
  // Chrome's question answered "Cancel"
  const {context: c1, page: p1} = await newPage(browserNo, {init: () => {
    navigator.mediaDevices.getDisplayMedia = () => Promise.reject(new DOMException('Permission denied', 'NotAllowedError'));
  }});
  await openVideo(p1);
  await altClick(p1, '.seg[data-i="3"] .w[data-j="1"] .wd >> nth=1');
  await p1.click('#asnd');
  await p1.click('.pc-cut .pc-record');
  await until(async () => /press “Allow”/.test(await stat(p1)), 'the refusal is said');
  const r1 = await p1.evaluate(() => ({stat: document.querySelector('.pc-stat').textContent, bad: document.querySelector('.pc-stat').classList.contains('pc-bad'),
                                       again: !document.querySelector('.pc-take').hidden && document.querySelector('.pc-record').getAttribute('aria-disabled') === 'false',
                                       strip: document.querySelector('.pc-strip').getClientRects().length === 0 &&
                                              document.querySelector('.pc-rows').getClientRects().length === 0}));
  eq(r1, {stat: 'the tab was not shared, so nothing was recorded: press “record” and, when Chrome asks, press “Allow”', bad: true, again: true, strip: true},
     'not allowed: it says to press Allow, and "record" can be pressed again');
  await shot(p1, 'refused-desktop');
  await p1.keyboard.press('Escape');
  await c1.close();

  // shared without its sound
  const {context: c2, page: p2} = await newPage(browserNo, {init: () => {
    navigator.mediaDevices.getDisplayMedia = () => {
      const c = document.createElement('canvas');
      c.width = 64; c.height = 36;
      c.getContext('2d').fillRect(0, 0, 64, 36);
      return Promise.resolve(c.captureStream(5));
    };
  }});
  await openVideo(p2);
  await altClick(p2, '.seg[data-i="3"] .w[data-j="1"] .wd >> nth=1');
  await p2.click('#asnd');
  await p2.click('.pc-cut .pc-record');
  await until(async () => /Also allow tab audio/.test(await stat(p2)), 'the missing sound is said');
  eq(await stat(p2), 'the tab was shared without its sound: press “record” and, when Chrome asks, leave “Also allow tab audio” turned on',
     'no sound in the share: it says to leave "Also allow tab audio" on');
  await c2.close();
}
{
  // a video whose sound is off
  const {context: c3, page: p3} = await newPage(browser, {query: 'src=tones.wav&deaf=1'});
  await openVideo(p3);
  await altClick(p3, '.seg[data-i="2"] .w[data-j="1"] .wd >> nth=1');
  await p3.click('#asnd');
  await p3.click('.pc-cut .pc-record');
  await until(async () => /no sound was captured/.test(await stat(p3)), 'the silence is said', 40000);
  eq(await stat(p3), 'no sound was captured — is the video muted? Turn its sound on and record again', 'silence: it asks whether the video is muted');
  assert(await p3.evaluate(() => document.querySelector('.pc-strip').getClientRects().length === 0 && document.querySelector('.pc-rows').getClientRects().length === 0) &&
         await rendered(p3, '.pc-cut .pc-record'),
         'and offers "record" again, with nothing to cut');
  await c3.close();
}
eq(await names(TRAY), trayBefore, 'none of the failures put anything in the tray');

/* ================================================================ f) a share without its sound */
console.log('f) a frame off a share without its sound, then a cut');
{
  // the first time Chrome asked, "Also allow tab audio" was turned off
  const {context: cf, page: pf} = await newPage(browser, {init: () => {
    const md = navigator.mediaDevices, ask = md.getDisplayMedia.bind(md);
    window.__shares = [];
    md.getDisplayMedia = o => ask(window.__shares.length ? o : Object.assign({}, o, {audio: false}))
      .then(s => { window.__shares.push(s); return s; });
  }});
  await openVideo(pf);
  await altClick(pf, '.seg[data-i="3"] .w[data-j="1"] .wd >> nth=1');
  const frame = async what => {
    await pf.evaluate(() => document.querySelector('#ashotimg').removeAttribute('src'));
    await pf.click('#ashot');
    await until(() => pf.evaluate(() => { const i = document.querySelector('#ashotimg'); return !document.querySelector('#ashotprev').hidden && i.naturalWidth > 100; }),
                what, 40000).catch(async e => { throw Error(e.message + ': ' + await text(pf, '#astat')); });
  };
  await frame('the frame is captured off a share without sound');
  eq(await pf.evaluate(() => __shares.map(s => s.getTracks().map(t => t.kind + ':' + t.readyState).sort().join())), ['video:live'],
     'the frame came off a share with no sound in it');
  await pf.click('#asnd');
  await until(() => shown(pf, '.pc-cut .pc-take'), 'the record step');
  assert(/Chrome asks first/.test(await text(pf, '.pc-take-text')) && !/^recording/.test(await stat(pf)),
         'the share has no sound: the editor says Chrome will ask, and waits for "record"');
  await recordIn(pf, 'after a frame off a share without sound');
  eq(await pf.evaluate(() => [__asked.map(o => !!o.audio), __shares.map(s => s.getTracks().map(t => t.kind + ':' + t.readyState).sort().join())]),
     [[false, true], ['video:ended', 'audio:live,video:live']],
     'Chrome was asked once more, with the sound, and the share without it was let go for the new one');
  const clipF = await saveAndUse(pf, 'after a frame off a share without sound');
  await clipIsExact(`${TRAY}/${clipF.name}`, clipF.s, clipF.e, 'after a frame off a share without sound');
  await frame('the next frame is captured');
  eq(await pf.evaluate(() => __asked.length), 2, 'the next frame is taken off the new share: Chrome was not asked a third time');
  await cf.close();
}

/* ================================================================ g) record again after saving */
console.log('g) "record again" after "save clip"');
{
  const {context: cg, page: pg} = await newPage(browser);
  const uploads = [];
  pg.on('request', r => { if (/\/clips\/api\/upload/.test(r.url())) uploads.push(r.url()); });
  await openVideo(pg);
  await altClick(pg, '.seg[data-i="3"] .w[data-j="1"] .wd >> nth=1');
  await pg.click('#asnd');
  await until(() => shown(pg, '.pc-cut .pc-record'), 'the record step');
  await recordIn(pg, 'the first recording');
  const quiet = await drawnAt(pg, [[16.5, 17]]);
  await pg.click('.pc-cut .pc-save');
  await until(async () => /saved to the clip tray/.test(await stat(pg)), 'the first clip is saved', 20000);
  const first = (await text(pg, '.pc-cut .pc-name')).split(' · ')[0];
  assert(await exists(`${TRAY}/${first}`) && uploads.length === 1 && quiet[0] < 0.05, 'the first recording\'s clip is in the tray: ' + first);
  // the video's sound is now one steady 1000 Hz tone, as if the first take had caught something else
  await childFrame(pg).evaluate(() => {
    const rate = 8000, n = rate * 42, buf = new ArrayBuffer(44 + n * 2), v = new DataView(buf);
    const put = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
    put(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); put(8, 'WAVE'); put(12, 'fmt '); v.setUint32(16, 16, true);
    v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true);
    v.setUint16(32, 2, true); v.setUint16(34, 16, true); put(36, 'data'); v.setUint32(40, n * 2, true);
    for (let i = 0; i < n; i++) v.setInt16(44 + i * 2, Math.round(Math.sin(2 * Math.PI * 1000 * i / rate) * 12000), true);
    const a = document.querySelector('audio');
    a.src = URL.createObjectURL(new Blob([buf], {type: 'audio/wav'}));
    return new Promise(r => a.addEventListener('loadedmetadata', r, {once: true}));
  });
  await pg.click('.pc-cut .pc-again');
  await until(async () => /^recording /.test(await stat(pg)), 'recording again');
  await until(() => pg.evaluate(() => !document.querySelector('.pc-cut').classList.contains('pc-busy')), 'the second recording is made', 40000);
  const loud = await drawnAt(pg, [[16.5, 17]]);
  const ed = await pg.evaluate(() => ({stat: document.querySelector('.pc-stat').textContent,
                                       stale: document.querySelector('.pc-saved').classList.contains('pc-stale'),
                                       opacity: getComputedStyle(document.querySelector('.pc-saved')).opacity}));
  assert(loud[0] > 0.25, 'the strip shows the new recording, sound where the old one was silent: ' + loud[0].toFixed(2));
  eq(ed, {stat: 'the clip saved is of the recording before this one: “use this clip” cuts it again, from this one', stale: true, opacity: '0.55'},
     'the clip saved before is dimmed, and said to be the old recording\'s');
  await shot(pg, 'record-again-after-save');
  await pg.click('.pc-cut .pc-use');
  await until(() => pg.evaluate(() => !document.querySelector('.pc-root') && !document.querySelector('#asndprev').hidden), 'the editor closes on the clip', 20000);
  const used = (await text(pg, '#asndname')).split(' · ')[0];
  assert(used !== first && uploads.length === 2 && await exists(`${TRAY}/${used}`) && !(await exists(`${TRAY}/${first}`)),
         `"use this clip" cut a new clip (${used}) off the new recording, and the old one (${first}) left the tray`);
  const m = await measure(`${TRAY}/${used}`);
  assert(m.runs.length === 1 && near(m.runs[0][0], 0, 0.025) && near(m.runs[0][1], m.duration, 0.025) && near(m.runs[0][2], 1000, 25),
         'the card\'s clip is the new sound, one steady 1000 Hz tone end to end: ' + JSON.stringify(m.runs));
  await cg.close();
}

/* ================================================================ h) from 0 s, PLAYING said late */
console.log('h) the first caption, from 0 s, on a player that says PLAYING late');
{
  const {context: ch, page: ph} = await newPage(browser, {query: 'src=tones.wav&late=1'});
  await openVideo(ph, ZERO);
  // what the kit reads: where the video is by the first PLAYING it hears
  await ph.evaluate(() => {
    const p = __fakeYT[0], get = p.getPlayerState;
    window.__firstPlaying = null;
    p.getPlayerState = function () { const st = get.call(p); if (st === 1 && __firstPlaying == null) __firstPlaying = p.getCurrentTime(); return st; };
  });
  await altClick(ph, '.seg[data-i="0"] .w[data-j="0"] .wd >> nth=0');
  await ph.click('#asnd');
  await until(() => shown(ph, '.pc-cut .pc-record'), 'the record step');
  assert(/the stretch 0\.00–/.test(await text(ph, '.pc-take-text')), 'the stretch starts at the start of the video: ' + await text(ph, '.pc-take-text'));
  const r = await recordIn(ph, 'from 0 s');
  const firstPlaying = await ph.evaluate(() => window.__firstPlaying);
  assert(firstPlaying >= 0.15, `the player said PLAYING first ${firstPlaying.toFixed(3)} s into the video, and the stretch is recorded all the same: ${r}`);
  assert(/^recorded 0\.00–/.test(r), 'the recording holds the video from 0 s: ' + r);
  await ph.fill('.pc-cut input.e0', '0');
  await ph.press('.pc-cut input.e0', 'Enter');
  await ph.fill('.pc-cut input.e1', '1.3');
  await ph.press('.pc-cut input.e1', 'Enter');
  eq([await value(ph, '.pc-cut input.e0'), await value(ph, '.pc-cut input.e1')], ['0.00', '1.30'], 'the edges at 0 and 1.3 s');
  const clipZ = await saveAndUse(ph, 'from 0 s', ZERO);
  await clipIsExact(`${TRAY}/${clipZ.name}`, clipZ.s, clipZ.e, 'from 0 s');
  await ch.close();
}

/* ================================================================ i) a real YouTube embed */
if (REAL) {
  console.log('i) a real YouTube embed (YT_REAL=1)');
  for (const [where, seg] of [['the middle', 1], ['the start', 0]]) {
    const {context: cr, page: pr} = await newPage(browser, {real: true});
    await pr.goto(`${BASE}/youtube/v/${REAL_ID}/`);
    await pr.waitForSelector('.seg .fa .w');
    await altClick(pr, `.seg[data-i="${seg}"] .w[data-j="0"] .wd >> nth=0`);
    await until(() => pr.evaluate(() => !document.querySelector('#asnd').disabled), 'the YouTube player is ready', 30000);
    await pr.click('#asnd');
    await pr.click('.pc-cut .pc-record');
    await until(async () => /^recorded /.test(await stat(pr)) || await pr.evaluate(() => document.querySelector('.pc-stat').classList.contains('pc-bad')),
                'the real embed is recorded', 90000);
    const r = await stat(pr);
    assert(/^recorded /.test(r), `${where} of a real YouTube video is recorded: ${r}`);
    if (seg === 0) {
      assert(/^recorded 0\.00–/.test(r), 'from 0 s');
      await pr.fill('.pc-cut input.e0', '0');
      await pr.press('.pc-cut input.e0', 'Enter');
      await pr.fill('.pc-cut input.e1', '2');
      await pr.press('.pc-cut input.e1', 'Enter');
    }
    const before = await names(TRAY, /\.(mp3|m4a|wav)$/);
    const s = +(await value(pr, '.pc-cut input.e0')), e = +(await value(pr, '.pc-cut input.e1'));
    await pr.click('.pc-cut .pc-save');
    await until(async () => /saved to the clip tray/.test(await stat(pr)), 'saved', 20000);
    const fresh = (await names(TRAY, /\.(mp3|m4a|wav)$/)).filter(n => !before.includes(n));
    const m = await measure(`${TRAY}/${fresh[0]}`);
    assert(fresh.length === 1 && near(m.duration, e - s, 0.03) && m.peak > 0.02,
           `${where}: a real YouTube embed gives a clip of ${m.duration.toFixed(3)} s for ${s}–${e} with sound in it (peak ${m.peak.toFixed(3)})`);
    // the video's first moments are its room noise, not the silence of a
    // recording made before the video played
    if (seg === 0)
      assert(m.rms50.slice(0, 4).every(x => x > 0.003), 'from 0 s, its first 200 ms hold the video\'s sound, not silence: ' + JSON.stringify(m.rms50.slice(0, 6)));
    await cr.close();
  }
}

/* ================================================================ j) reach: record again, further back */
console.log('j) "reach": record again sent further back than the caption');
{
  const {context: cj, page: pj} = await newPage(browser);
  await openVideo(pj);
  await altClick(pj, '.seg[data-i="3"] .w[data-j="1"] .wd >> nth=1');
  await pj.click('#asnd');
  await until(() => shown(pj, '.pc-cut .pc-record'), 'the record step');
  await recordIn(pj, 'the first recording');
  const before = await viewOf(pj);
  eq(await pj.evaluate(() => {
       const r = document.querySelector('.pc-cut .pc-row-r'), i = r.querySelectorAll('input.pc-r');
       return [r.getClientRects().length > 0, i.length, i[0].value, i[1].value,
               [...r.childNodes].map(n => n.textContent).join('|')];
     }),
     [true, 2, '0', '0', 'reach|start||s|end||s'],
     'the reach row stands with the recording, both edges at 0 s');

  // the caption cut the sentence across: the words wanted are two seconds
  // before it.  Type -2 on the start and press Enter -- which records.
  await pj.fill('.pc-cut input.pc-r0', '-2');
  await pj.press('.pc-cut input.pc-r0', 'Enter');
  await until(async () => /^recording /.test(await stat(pj)), 'Enter in the reach box records again');
  await until(() => pj.evaluate(() => !document.querySelector('.pc-cut').classList.contains('pc-busy')),
              'the second recording is made', 40000);
  const after = await viewOf(pj);
  assert(near(after[0], before[0] - 2, 0.1) && near(after[1], before[1], 0.1),
         `the strip reaches two seconds further back and no further on: ${JSON.stringify(before)} -> ${JSON.stringify(after)}`);

  // a half second that was out of reach before: whole seconds hold the tone
  // that says which second of the video it is
  const s0 = Math.ceil(after[0] + 0.01), e0 = s0 + 0.5;
  assert(s0 < before[0], `${s0} s was outside the first recording (it began at ${before[0]})`);
  await pj.fill('.pc-cut input.e0', String(s0));
  await pj.press('.pc-cut input.e0', 'Enter');
  await pj.fill('.pc-cut input.e1', String(e0));
  await pj.press('.pc-cut input.e1', 'Enter');
  eq([await value(pj, '.pc-cut input.e0'), await value(pj, '.pc-cut input.e1')],
     [s0.toFixed(2), e0.toFixed(2)], 'the cursors go where only the reach put sound');
  const used = await saveAndUse(pj, 'the clip from before the caption');
  await clipIsExact(`${TRAY}/${used.name}`, s0, e0,
                    'the card\u2019s clip is the video\u2019s own second ' + s0 + ', out of reach before');
  await cj.close();
}

/* ============================================ k) the add page's transcript editor, by ear */
console.log('k) the transcript edited before the video is added, a tenth of a second at a time');
{
  const {context: ck, page: pk} = await newPage(browser);
  await pk.goto(`${BASE}/youtube/add/`);
  // the body opens once both questions are answered
  await pk.click('.path[data-src="yt"]');
  await pk.click('.path[data-by="llm"]');
  await pk.waitForSelector('#transcript', {state: 'visible'});
  await pk.fill('#url', `https://www.youtube.com/watch?v=${YT}`);
  await pk.selectOption('#lang', 'it');
  await pk.fill('#transcript', '0:10\nPrima frase\n0:14\nSeconda frase\n0:20\nTerza frase\n');
  await pk.click('#subedit');
  await pk.waitForSelector('.se-row');
  eq(await pk.$$eval('.se-row', rs => rs.map(r => [r.querySelector('.se-at').value, r.querySelector('.se-text').value])),
     [['0:10', 'Prima frase'], ['0:14', 'Seconda frase'], ['0:20', 'Terza frase']],
     'the pasted panel opens as its captions');
  assert(await pk.locator('.se-yt iframe').count() === 1, 'the video itself is in the editor');
  eq(await pk.$$eval('.se-row', rs => rs[0].querySelectorAll('.se-when button').length), 6,
     'each caption carries the six steps, three on either side of its time');
  eq(await pk.locator('button[data-a="ear"]').count(), 0, 'and nothing records anything here');
  // The two roads out of a bad transcript.  "tidy up" is there for every
  // language and works once that language's dictionary is installed, so what
  // the button shows must be what the server says about this machine; the
  // prompt needs nothing installed and is always there.
  const says = await (await pk.request.post(`${BASE}/youtube/api/transcript`,
    {data: {transcript: '0:01\nCiao a tutti\n', lang: 'it'}})).json();
  eq(await pk.locator('.se-btn:has-text("tidy up")').isVisible(), !!says.can_tidy,
     `"tidy up" is offered exactly where the dictionary is (can_tidy ${says.can_tidy})`);
  eq(await pk.locator('.se-btn:has-text("or with an LLM")').isVisible(), true,
     'and the prompt is offered whatever is installed');

  // a tenth at a time: the step the panel could not hold before
  const row = pk.locator('.se-row').first();
  await row.locator('button[data-d="-0.1"]').click();
  await row.locator('button[data-d="-0.1"]').click();
  eq(await row.locator('.se-at').inputValue(), '0:09.8', 'two tenths earlier, and the box says so');
  eq(await pk.textContent('.se-box .se-head .se-stat'), 'caption 1 at 0:09.8', 'and the editor says which');
  await row.locator('button[data-d="0.5"]').click();
  await row.locator('button[data-d="1"]').click();
  eq(await row.locator('.se-at').inputValue(), '0:11.3', 'a half and a second later');
  // a time typed with a fraction is read, and one that is whole stays whole
  await pk.locator('.se-row').nth(1).locator('.se-at').fill('0:14.25');
  await pk.locator('.se-row').nth(1).locator('.se-at').press('Enter');
  eq(await pk.$$eval('.se-row .se-at', is => is.map(i => i.value)), ['0:11.3', '0:14.25', '0:20'],
     'the panel holds fractions and whole seconds side by side');

  // the panel goes back into the box, and nothing else on the page moved
  await pk.click('.se-foot .se-use');
  await pk.waitForSelector('.se-box', {state: 'detached'});
  eq(await pk.inputValue('#transcript'),
     '0:11.3\nPrima frase\n0:14.25\nSeconda frase\n0:20\nTerza frase\n',
     'the box holds the edited panel, fractions and all, in the one format everything downstream reads');
  eq(await pk.textContent('#sestat'), 'the transcript was edited', 'and the page says so');

  // and the road on from there still works, from the panel as it now is
  await pk.click('#prepare');
  await until(async () => (await pk.textContent('#pinfo')).includes('captions'), 'the prompt is prepared', 20000);
  const said = await pk.textContent('#pinfo');
  assert(/3 captions/.test(said), 'the prompt is built from the edited panel: ' + said);
  await ck.close();
}

assert(errors.length === 0, 'no page error and no failed request: ' + JSON.stringify(errors));
assert(!/Traceback/.test(log.join('')), 'no traceback in the hub\'s log');
console.log(`\nyoutube_capture: ${passed} checks passed`);
} catch (e) {
  console.log(e.stack || e);
  console.log('page errors:', JSON.stringify(errors));
  console.log('hub log tail:\n' + log.join('').slice(-3000));
  Deno.exitCode = 1;
} finally {
  await browser.close();
  if (browserNo) await browserNo.close();
  fakeServers.abort();
  try { hub.kill('SIGTERM'); await hub.status; } catch (_) {}
  await Deno.remove(TMP, {recursive: true}).catch(() => {});
}
