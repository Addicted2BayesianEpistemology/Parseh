// SPDX-License-Identifier: GPL-3.0-or-later
import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=/path/to/python3 deno run --allow-all tests/audio_video.mjs
//      AUDIO_VIDEO_SHOTS=<dir> also saves screenshots (1280 and 390 px, the three themes)
//
// A SOUND IN PLACE OF A VIDEO (W8), driven in a real browser against the REAL hub: serve.main() on a
// temporary toolbox, a real mp3, m4a and wma made by ffmpeg at run time, nothing stubbed but YouTube.
//
//  a) the add page, BY PATH: the path box is looked at when it is left (a sound with no picture; a wma
//     says a playable copy will be made), "Start it empty" makes the video, and the player opens on a
//     sound: <html data-kind=audio>, an <audio id=film>, NO iframe and NO <video>, a bar whose waveform
//     is really painted (read back off the canvas), a press on the bar goes there, the transcript follows
//     the sound, the controls that need a picture (the grip, the side-by-side button) are not drawn
//  b) BY UPLOAD: a file chosen on the page is asked about before it is sent (its size, the room), sent
//     with a bar, its speed and the time left (the upload is slowed so that there is time to see it),
//     and can be stopped -- nothing is kept; sent whole it puts its path in the same box, and the video
//     is made through the very door a typed path uses; the waiting copy is gone afterwards
//  c) a card from a sound: the sheet has no frame row, "cut the audio…" cuts the recording out of the
//     sound, the exercise deck's item names the recording and no picture
//  d) the phone's player: the same page in the mobile mode: the bar fills the video's place inside the
//     screen, held upright and sideways, the dock's play button drives the sound, the box that sends a
//     film again is not drawn
//  e) a video whose film is not there any more is offered the file again, and a sound sent to it plays
//  f) the shelf: the card says it is a sound; a film is still a film (control)
//  g) three themes and two widths, looked at (shots)
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('AUDIO_VIDEO_SHOTS') || '';
const TMP = await Deno.makeTempDir({prefix: 'parseh-audio-video-'});
const td = new TextDecoder();
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const eq = (got, want, m) => assert(JSON.stringify(got) === JSON.stringify(want),
                                    m + (JSON.stringify(got) === JSON.stringify(want) ? '' : ': got ' + JSON.stringify(got) + ' want ' + JSON.stringify(want)));
const near = (a, b, tol) => Math.abs(a - b) <= tol;
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, what, ms = 15000) {
  const t = Date.now();
  for (;;) {
    const v = await fn();
    if (v) return v;
    if (Date.now() - t > ms) throw Error('FAIL: timed out: ' + what);
    await sleep(80);
  }
}
async function run(cmd, args, opts = {}) {
  const o = await new Deno.Command(cmd, {args, cwd: root, stdout: 'piped', stderr: 'piped', ...opts}).output();
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
async function walk(dir) {
  const out = [];
  try {
    for await (const e of Deno.readDir(dir)) {
      if (e.isDirectory) out.push(...await walk(dir + '/' + e.name));
      else out.push(dir + '/' + e.name);
    }
  } catch (_) {}
  return out.sort();
}
const readJson = async p => JSON.parse(await Deno.readTextFile(p));
function freePort() {
  const l = Deno.listen({hostname: '127.0.0.1', port: 0});
  const p = l.addr.port;
  l.close();
  return p;
}

/* ---------------------------------------------------------------- the files, made here */
const MEDIA = TMP + '/media';
await Deno.mkdir(MEDIA, {recursive: true});
// a tone that swells and falls, so that a waveform has a SHAPE to be wrong about
const swell = (hz, secs) => ['-f', 'lavfi', '-i',
  `aevalsrc=sin(2*PI*${hz}*t)*(0.12+0.88*abs(sin(2*PI*0.35*t))):d=${secs}:s=22050`];
await ff(...swell(220, 44), '-c:a', 'libmp3lame', MEDIA + '/lesson.mp3');
await ff(...swell(330, 44), '-c:a', 'aac', MEDIA + '/lesson.m4a');
await ff(...swell(260, 44), MEDIA + '/sent.mp3');
await ff(...swell(180, 44), MEDIA + '/again.mp3');
let HAVE_WMA = true;
try { await ff(...swell(200, 44), MEDIA + '/radio.wma'); } catch (_) { HAVE_WMA = false; }
await ff('-f', 'lavfi', '-i', 'testsrc=duration=44:size=320x180:rate=10', '-f', 'lavfi', '-i',
         'sine=frequency=440:duration=44', '-shortest', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', MEDIA + '/picture.mp4');
// a long one to send slowly: 13 MB of 22 kHz sound
await ff('-f', 'lavfi', '-i', 'sine=frequency=300:duration=300:sample_rate=22050', MEDIA + '/long.wav');
const TRANSCRIPT = await Deno.readTextFile('tests/fixtures/videos/english/eN5wX7zA9bC/transcript.txt');

/* ---------------------------------------------------------------- the hub */
const ROOT = TMP + '/root', VIDEOS = ROOT + '/youtube/videos', INCOMING = VIDEOS + '/.incoming';
const TRAY = TMP + '/tray', EXERCISES = TMP + '/exercises', ANKI = TMP + '/anki';
await Deno.mkdir(ROOT + '/youtube', {recursive: true});
await Deno.symlink(root + '/lib', ROOT + '/lib');
await Deno.symlink(root + '/youtube/lib', ROOT + '/youtube/lib');
for (const d of [TRAY, EXERCISES, ANKI, TMP + '/library']) await Deno.mkdir(d, {recursive: true});
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
# WHAT THIS MACHINE KEEPS, into the temporary tree: a suite must never read or write the owner's own
import prefs
import network
prefs.STORE = str(tmp / "config" / "prefs.json")
network.STORE = str(tmp / "config" / "network.json")
import latexthemes, latexdraw, texpackages
latexthemes.STORE = str(tmp / "config" / "latex.json")
import prompts
prompts.STORE = str(tmp / "config" / "prompts.json")
latexdraw.DRAWN = str(tmp / "latex-drawn")
texpackages.TREE = str(tmp / "texmf")
import offline
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
const post = async (path, body) => {
  const r = await fetch(BASE + path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  return {status: r.status, json: await r.json()};
};
// a video made through the very door the add page's "Start it empty" uses
async function makeVideo(path, id, title) {
  const r = await post('/youtube/api/local', {path, id, title, lang: 'en', gloss: 'en', transcript: TRANSCRIPT});
  if (!r.json.ok) throw Error('could not make a video: ' + JSON.stringify(r.json));
  return r.json;
}

/* ---------------------------------------------------------------- the browser */
const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true,
  args: ['--autoplay-policy=no-user-gesture-required']});
const errors = [];
async function newPage(opts = {viewport: {width: 1280, height: 800}}, phone = false) {
  const context = await browser.newContext(opts);
  if (phone) {
    await context.addCookies([{name: 'parseh_mode', value: 'mobile', url: BASE}]);
    await context.addInitScript(() => localStorage.setItem('parseh_mode', 'mobile'));
  }
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: BASE});
  const page = await context.newPage();
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push('console: ' + m.text()); });
  page.on('response', r => {
    const u = new URL(r.url());
    if (u.host === `127.0.0.1:${port}` && r.status() >= 400 && r.status() !== 409 && r.status() !== 507
        && /^\/(clips|exercises\/api|anki|youtube\/api)/.test(u.pathname))
      errors.push(r.status() + ' ' + r.request().method() + ' ' + u.pathname);
  });
  await context.route(/^https?:\/\/(?!127\.0\.0\.1)/, route => route.abort());
  return {context, page};
}
async function shot(page, name) {
  if (!SHOTS) return;
  await Deno.mkdir(SHOTS, {recursive: true});
  await page.screenshot({path: `${SHOTS}/${name}.png`});
}
const theme = (page, t) => page.evaluate(t => {
  if (t === 'light') document.documentElement.removeAttribute('data-theme');
  else document.documentElement.setAttribute('data-theme', t);
}, t);
// drawn: a box of some size on the page, whatever its `hidden` says
const shown = (page, sel) => page.evaluate(sel => {
  const el = document.querySelector(sel);
  return !!el && [...el.getClientRects()].some(r => r.width > 0 && r.height > 0) &&
         getComputedStyle(el).visibility !== 'hidden';
}, sel);
const inside = (page, sel) => page.evaluate(sel => {
  const r = document.querySelector(sel).getBoundingClientRect();
  return r.width > 0 && r.height > 0 && r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight;
}, sel);
// how much of the bar is really painted: pixels with something in them, and in how many columns
const painted = page => page.evaluate(() => {
  const cv = document.querySelector('#sndwave');
  if (!cv || !cv.width) return {pixels: 0, columns: 0, w: 0, h: 0};
  const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
  let px = 0; const cols = new Set();
  for (let i = 3; i < d.length; i += 4) if (d[i] > 0) { px++; cols.add(((i - 3) / 4) % cv.width); }
  return {pixels: px, columns: cols.size, w: cv.width, h: cv.height};
});
async function openVideo(page, id) {
  await page.goto(`${BASE}/youtube/v/${id}/`);
  await page.waitForSelector('.seg .fa .w');
}
const soundReady = page => until(() => page.evaluate(() => {
  const f = document.querySelector('#film');
  return f && f.tagName === 'AUDIO' && f.readyState >= 1 && f.duration > 30;
}), 'the sound loads');
const waveReady = page => until(async () => (await page.evaluate(() => document.querySelector('#sndwave').getAttribute('data-shape'))) === 'wave', 'the waveform is drawn from the shape of the sound');

try {
/* ================================================================ a) the add page, by path */
const {context: ctxA, page} = await newPage();
await page.goto(`${BASE}/youtube/add/?src=film&by=empty`);
await page.waitForSelector('#path');
assert(await shown(page, '#src-film') && await shown(page, '#filmsend'), 'the film field is drawn, and the option to send beside it');
eq(await page.evaluate(() => ({label: document.querySelector('#src-film label').textContent.trim().split('\n')[0],
                              card: document.querySelector('#q1 [data-src=film] b').textContent})),
   {label: 'The video or sound', card: 'A video or a sound on this machine'}, 'the words say "video or sound" where they said film');
await page.fill('#path', MEDIA + '/lesson.mp3');
await page.press('#path', 'Tab');
await until(() => page.evaluate(() => /A sound with no picture \(mp3, /.test(document.querySelector('#filmlook').textContent)), 'the page says what the path names');
const look = await page.evaluate(() => document.querySelector('#filmlook').textContent);
assert(/0:44/.test(look) && /waveform/.test(look) && !/playable copy/.test(look), 'its length, the bar that stands for a picture, no warning: ' + look);
if (HAVE_WMA) {
  await page.fill('#path', MEDIA + '/radio.wma');
  await page.press('#path', 'Tab');
  await until(() => page.evaluate(() => /playable copy is made/.test(document.querySelector('#filmlook').textContent)), 'a wma says a playable copy will be made');
  eq(await page.evaluate(() => document.querySelector('#filmlook').classList.contains('warn')), true, 'and says it as a warning');
}
await page.fill('#path', MEDIA + '/nothing-here.mp3');
await page.press('#path', 'Tab');
await until(() => page.evaluate(() => /no file at /.test(document.querySelector('#filmlook').textContent)), 'a path that is not there is said in words');
await page.fill('#path', MEDIA + '/lesson.mp3');
await page.press('#path', 'Tab');
await until(() => page.evaluate(() => /A sound with no picture/.test(document.querySelector('#filmlook').textContent)), 'the sound again');
await page.locator('#src-film').scrollIntoViewIfNeeded();
await shot(page, 'add-by-path-desktop');
await page.selectOption('#lang', 'en');
await page.fill('#transcript', TRANSCRIPT);
await page.click('#empty');
await page.waitForURL(/\/youtube\/v\/[^/]+\/$/);
await page.waitForSelector('.seg .fa .w');
const ID_A = new URL(page.url()).pathname.split('/')[3];
const dirA = (await walk(VIDEOS)).filter(p => p.includes('/' + ID_A + '/'));
eq(dirA.map(p => p.split('/').pop()).sort(), ['annotations.json', 'media.mp3', 'transcript.txt', 'video.json'], 'the video is made as any is, with media.mp3 beside it');
eq((await readJson(dirA.find(p => p.endsWith('video.json')))).kind, 'audio', 'video.json says it is a sound, once');

/* ---- the player, on a sound */
await soundReady(page);
await waveReady(page);
eq(await page.evaluate(() => ({kind: document.documentElement.getAttribute('data-kind'), media: document.querySelector('#film').tagName,
                              iframe: document.querySelectorAll('#vid iframe').length, video: document.querySelectorAll('video').length,
                              cfg: window.YTFRANK.kind, local: window.YTFRANK.local})),
   {kind: 'audio', media: 'AUDIO', iframe: 0, video: 0, cfg: 'audio', local: true},
   'the page is told it is a sound; an <audio> is the film; no frame of YouTube, no <video>');
const box = await page.evaluate(() => { const r = document.querySelector('#vid').getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; });
assert(box[1] < 190 && box[0] > 400, 'the bar fills the video\'s place and is not a 16:9 box: ' + box.join('×'));
const pa = await painted(page);
assert(pa.columns > 0.6 * pa.w && pa.pixels > 2000, `the waveform is really painted: ${pa.columns} of ${pa.w} columns, ${pa.pixels} pixels`);
eq(await page.evaluate(() => ['#grip', '#sbs', '#ashotrow'].map(s => { const e = document.querySelector(s); return !e || getComputedStyle(e).display; })),
   ['none', 'none', 'none'], 'what needs a picture is not drawn: the resize grip, the side-by-side button, the card\'s frame row');
await shot(page, 'player-light-desktop');
// a press on the bar goes there: the middle of a 44 s sound
const rect = await page.locator('#sndwave').boundingBox();
await page.mouse.click(rect.x + rect.width * 0.5, rect.y + rect.height / 2);
await until(() => page.evaluate(() => Math.abs(document.querySelector('#film').currentTime - document.querySelector('#film').duration / 2) < 1.2), 'a press on the bar goes to the middle');
const pa2 = await painted(page);
assert(pa2.pixels > 0, 'and the bar is drawn again with the playhead there');
// a drag scrubs
await page.mouse.move(rect.x + rect.width * 0.2, rect.y + 20);
await page.mouse.down();
await page.mouse.move(rect.x + rect.width * 0.8, rect.y + 20, {steps: 6});
await page.mouse.up();
await until(() => page.evaluate(() => Math.abs(document.querySelector('#film').currentTime - document.querySelector('#film').duration * 0.8) < 1.5), 'a drag scrubs');
// the transcript follows the sound
await page.evaluate(() => { ParsehPlayer.seek(7); ParsehPlayer.play(); });
await until(() => page.evaluate(() => !document.querySelector('#film').paused && document.querySelector('#film').currentTime > 7.5), 'the sound plays');
await until(() => page.evaluate(() => { const on = document.querySelector('#segs .seg.on-air'); return on && +on.dataset.i >= 1; }), 'the caption being said is marked as the sound goes');
await page.evaluate(() => ParsehPlayer.pause());
eq(await page.evaluate(() => [ParsehPlayer.kind(), ParsehPlayer.ready(), document.querySelector('#film').playbackRate]), ['film', true, 1],
   'the handle the controls outside the page use is the one a film has');
// the download names the sound, not a film
assert(/the sound itself and its glosses/.test(await page.evaluate(() => document.querySelector('#dl').title)), 'the download button says it carries the sound');
for (const t of ['dark', 'sepia']) { await theme(page, t); await sleep(500); await shot(page, `player-${t}-desktop`); }
await theme(page, 'light');
// the timings door draws its strip from the sound, as it does from a film
await page.click('#captimes');
await until(() => shown(page, '.tl-root'), 'the timings sheet opens on a sound');
await page.waitForSelector('.tl-strip.tl-drawn', {timeout: 25000});
assert(await page.evaluate(() => {
  const c = document.querySelector('.tl-wave'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  let lit = 0;
  for (let k = 3; k < d.length; k += 4) if (d[k] > 0) lit++;
  return lit;
}) > 500, 'the timings draw the sound\'s own waveform, read by the server with ffmpeg: no recording to make first');
eq(await page.evaluate(() => document.querySelectorAll('.tl-band').length > 3), true, 'with a block for each caption');
await shot(page, 'timings-sound-desktop');
await page.keyboard.press('Escape');
await until(() => page.evaluate(() => !document.querySelector('.tl-root') || document.querySelector('.tl-root').hidden), 'and it closes');

/* ================================================================ f) the shelf */
{
  await makeVideo(MEDIA + '/picture.mp4', 'a-film-control-a1b2c3', 'A film');
  const shelf = await (await fetch(BASE + '/youtube/c/on-this-machine/')).text();
  const cards = shelf.split('<a class="book').slice(1);
  const mine = cards.find(c => c.includes('/v/' + ID_A + '/')), film = cards.find(c => c.includes('/v/a-film-control-a1b2c3/'));
  assert(mine && /&#9834; a sound/.test(mine), 'the shelf card of the sound says it is one');
  assert(film && !/a sound/.test(film), 'and the card of a film does not');
  const m = await (await fetch(BASE + '/m/videos/on-this-machine/')).text();
  assert(/&#9834; a sound/.test(m), 'the phone\'s shelf says it too');
  // the control is still a film: <video>, a frame, the grip
  const {context: cv, page: pv} = await newPage();
  await openVideo(pv, 'a-film-control-a1b2c3');
  eq(await pv.evaluate(() => [document.documentElement.getAttribute('data-kind'), document.querySelector('#film').tagName,
                              !!document.querySelector('#sndbar'), getComputedStyle(document.querySelector('#grip')).display !== 'none']),
     ['video', 'VIDEO', false, true], 'a film is still a film: a <video>, no bar, its grip');
  const vb = await pv.evaluate(() => { const r = document.querySelector('#vid').getBoundingClientRect(); return r.height / r.width; });
  assert(near(vb, 9 / 16, 0.03), 'and still 16:9: ' + vb.toFixed(3));
  await cv.close();
}

/* ================================================================ without ffmpeg the bar is a plain track */
{
  const {context: c, page: p} = await newPage();
  await p.route('**/youtube/api/film/wave', r => r.fulfill({status: 409, contentType: 'application/json',
    body: JSON.stringify({ok: false, error: 'ffmpeg is not installed on this computer, so there is no picture of the sound to draw'})}));
  await openVideo(p, ID_A);
  await soundReady(p);
  await until(() => p.evaluate(() => document.querySelector('#sndwave').getAttribute('data-shape') === 'plain' && document.querySelector('.sndsay').textContent.length > 0),
              'the bar becomes a plain track, and says why');
  const say = await p.evaluate(() => document.querySelector('.sndsay').textContent);
  assert(/ffmpeg is not installed/.test(say) && /plain track/.test(say), 'in words: ' + say);
  const bar = await p.locator('#sndwave').boundingBox();
  await p.mouse.click(bar.x + bar.width * 0.75, bar.y + bar.height / 2);
  await until(() => p.evaluate(() => Math.abs(document.querySelector('#film').currentTime - document.querySelector('#film').duration * 0.75) < 1.5), 'it still goes where it is pressed');
  await shot(p, 'player-plain-track-desktop');
  await c.close();
}

/* ================================================================ b) the add page, by upload */
const {context: ctxB, page: pb} = await newPage();
const aboutToSend = [];
pb.on('request', r => { if (r.url().includes('/api/film') && r.method() === 'POST') aboutToSend.push(new URL(r.url()).pathname + new URL(r.url()).search.slice(0, 30)); });
await pb.goto(`${BASE}/youtube/add/?src=film&by=empty`);
await pb.waitForSelector('#filmsend input[type=file]', {state: 'attached'});
await pb.setInputFiles('#filmsend input[type=file]', MEDIA + '/sent.mp3');
await until(() => shown(pb, '#filmsend .filmgo'), 'the Send button appears once the computer has answered');
const said = await pb.evaluate(() => document.querySelector('#filmsend .filmsay').textContent);
assert(/sent\.mp3 is \d/.test(said) && /a sound/.test(said) && /free/.test(said) && /depends on the connection/.test(said),
       'the size, the kind and the room are said BEFORE anything is sent: ' + said);
eq(aboutToSend.filter(u => u.includes('/api/film?')), [], 'and not one byte has been sent yet');
await pb.locator('#filmsend').scrollIntoViewIfNeeded();
await shot(pb, 'add-by-upload-chosen-desktop');
await pb.click('#filmsend .filmgo');
await until(() => pb.evaluate(() => /^Sent: sent\.mp3/.test(document.querySelector('#filmsend .filmsay').textContent)), 'the file is sent');
const sentPath = await pb.inputValue('#path');
assert(sentPath.startsWith(INCOMING + '/') && sentPath.endsWith('/sent.mp3'), 'the path of what arrived is put in the very box a path is typed in: ' + sentPath);
assert((await Deno.stat(sentPath)).size === (await Deno.stat(MEDIA + '/sent.mp3')).size, 'and the file is whole');
eq((await walk(INCOMING)).map(p => p.split('/').pop()), ['sent.mp3'], 'and it is the one thing waiting, with no .part beside it');
await until(() => pb.evaluate(() => /A sound with no picture \(mp3, /.test(document.querySelector('#filmlook').textContent)), 'the page says what the sent file is, as it does for a path');
await pb.selectOption('#lang', 'en');
await pb.fill('#transcript', TRANSCRIPT);
await pb.click('#empty');
await pb.waitForURL(/\/youtube\/v\/[^/]+\/$/);
await pb.waitForSelector('.seg .fa .w');
const ID_B = new URL(pb.url()).pathname.split('/')[3];
eq((await walk(INCOMING)), [], 'the video took the file: nothing waits in .incoming any more');
eq(((await walk(VIDEOS)).filter(p => p.includes('/' + ID_B + '/'))).map(p => p.split('/').pop()).sort(),
   ['annotations.json', 'media.mp3', 'transcript.txt', 'video.json'], 'the video is the one a path makes');
eq(await pb.evaluate(() => [document.documentElement.getAttribute('data-kind'), document.querySelector('#film').tagName]), ['audio', 'AUDIO'], 'and it plays as a sound');
// the bytes the person sent are the bytes of the film
const sentBytes = await Deno.readFile(MEDIA + '/sent.mp3'), keptBytes = await Deno.readFile((await walk(VIDEOS)).find(p => p.includes('/' + ID_B + '/media.mp3')));
assert(sentBytes.length === keptBytes.length && sentBytes.every((b, i) => b === keptBytes[i]), 'byte for byte');

// the LLM way takes the same path: prepare names the sound in the prompt as a recording
await pb.goto(`${BASE}/youtube/add/?src=film&by=llm`);
await pb.setInputFiles('#filmsend input[type=file]', MEDIA + '/again.mp3');
await until(() => shown(pb, '#filmsend .filmgo'), 'the Send button (the LLM way)');
await pb.click('#filmsend .filmgo');
await until(() => pb.evaluate(() => /^Sent: again\.mp3/.test(document.querySelector('#filmsend .filmsay').textContent)), 'sent (the LLM way)');
await pb.selectOption('#lang', 'en');
await pb.fill('#transcript', TRANSCRIPT);
await pb.click('#prepare');
await until(() => pb.evaluate(() => document.querySelector('#prompt').value.length > 500), 'the prompt is prepared');
assert(/a recording on the reader's own machine, not on YouTube/.test(await pb.inputValue('#prompt')), 'the prompt says "a recording on the reader\'s own machine, not on YouTube"');
assert(!/a film on the reader's own machine/.test(await pb.inputValue('#prompt')), 'and not "a film"');

// slowed, so that there is time to see it: the bar, the speed, the time left -- and Stop
await pb.goto(`${BASE}/youtube/add/?src=film&by=empty`);
await pb.setInputFiles('#filmsend input[type=file]', MEDIA + '/long.wav');
await until(() => shown(pb, '#filmsend .filmgo'), 'the Send button (the long file)');
const pathBefore = await pb.inputValue('#path');
const cdp = await ctxB.newCDPSession(pb);
await cdp.send('Network.enable');
await cdp.send('Network.emulateNetworkConditions', {offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: 2 * 1024 * 1024});
await pb.click('#filmsend .filmgo');
await until(() => pb.evaluate(() => /Sending long\.wav: \d+ % of .* · .*\/s · about .* left/.test(document.querySelector('#filmsend .filmsay').textContent)), 'the page says how far, how fast and how long is left', 40000);
const prog = await pb.evaluate(() => ({text: document.querySelector('#filmsend .filmsay').textContent, bar: document.querySelector('.filmfill').style.width,
                                       barShown: !document.querySelector('.filmbar').hidden, stop: !document.querySelector('.filmstop').hidden,
                                       choose: document.querySelector('.filmpick').disabled}));
assert(parseFloat(prog.bar) > 0 && parseFloat(prog.bar) < 100 && prog.barShown && prog.stop && prog.choose, 'a bar that has moved, a way to stop it, and no second file while this goes: ' + JSON.stringify(prog));
await shot(pb, 'add-by-upload-sending-desktop');
assert((await walk(INCOMING)).some(p => p.endsWith('long.wav.part')), 'the server is writing it to a .part, which no listing reads as media');
await pb.click('#filmsend .filmstop');
await until(() => pb.evaluate(() => /^Stopped/.test(document.querySelector('#filmsend .filmsay').textContent)), 'Stop stops it');
await until(async () => (await walk(INCOMING)).filter(p => /long\.wav/.test(p)).length === 0, 'and nothing of it is kept: whole or not at all', 20000);
eq(await pb.inputValue('#path'), pathBefore, 'the path box was not touched');
await cdp.send('Network.emulateNetworkConditions', {offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1});

// refused, in words, before anything is sent
await Deno.writeTextFile(MEDIA + '/notes.txt', 'not a sound');
await pb.setInputFiles('#filmsend input[type=file]', MEDIA + '/notes.txt');
await until(() => pb.evaluate(() => /name the file with its extension/.test(document.querySelector('#filmsend .filmsay').textContent)), 'a text is refused in words, at the choosing');
eq(await shown(pb, '#filmsend .filmgo'), false, 'and there is nothing to send');
await ctxB.close();

// from another device: a phone's browser, the add page in the browser interface, 390 px wide
{
  const {context: cx, page: px} = await newPage({viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true});
  await px.goto(`${BASE}/youtube/add/?src=film&by=empty`);
  await px.waitForSelector('#filmsend input[type=file]', {state: 'attached'});
  await px.setInputFiles('#filmsend input[type=file]', MEDIA + '/sent.mp3');
  await until(() => shown(px, '#filmsend .filmgo'), 'the Send button, on a phone');
  await px.locator('#filmsend').scrollIntoViewIfNeeded();
  const fit = await px.evaluate(() => ({scroll: document.documentElement.scrollWidth, width: innerWidth,
    boxes: ['#path', '#filmsend .filmpick', '#filmsend .filmgo', '#filmsend .filmsay'].map(s => {
      const r = document.querySelector(s).getBoundingClientRect();
      return [s, Math.round(r.left), Math.round(r.right), Math.round(r.height)];
    })}));
  assert(fit.scroll <= fit.width + 1 && fit.boxes.every(b => b[1] >= 0 && b[2] <= fit.width), 'no sideways scroll, and every part of the film field inside a 390 px screen: ' + JSON.stringify(fit));
  assert(fit.boxes.filter(b => /filmpick|filmgo/.test(b[0])).every(b => b[3] >= 30), 'the two buttons are tall enough to press: ' + JSON.stringify(fit.boxes));
  await shot(px, 'add-by-upload-chosen-phone');
  await px.locator('#filmsend .filmgo').tap();
  await until(() => px.evaluate(() => /^Sent: sent\.mp3/.test(document.querySelector('#filmsend .filmsay').textContent)), 'sent from a phone-sized browser');
  assert((await walk(INCOMING)).some(p => p.endsWith('/sent.mp3')), 'and it is on the computer');
  await shot(px, 'add-by-upload-sent-phone');
  await cx.close();
  // what was sent and not used is swept by the next time anybody sends, after two days; here it is taken away by hand
  await Deno.remove(INCOMING, {recursive: true}).catch(() => {});
}

/* ================================================================ c) a card from a sound */
await page.goto(`${BASE}/youtube/v/${ID_A}/`);
await page.waitForSelector('.seg .fa .w');
await soundReady(page);
await page.evaluate(() => { localStorage.setItem('yt_card_target', 'deck'); const f = document.querySelector('#film'); f.currentTime = 7.5; return f.play(); });
await until(() => page.evaluate(() => !document.querySelector('#film').paused), 'the sound plays');
await page.mouse.move(2, 2);
await page.locator('.seg[data-i="2"] .w[data-j="0"] .wd >> nth=0').click({modifiers: ['Alt']});
await until(() => page.evaluate(() => { const b = document.querySelector('#anki'); return b && !b.hidden && b.getBoundingClientRect().height > 100; }), 'the card sheet opens');
eq(await page.evaluate(() => document.querySelector('#film').paused), true, 'the sound pauses under it, as a film does');
eq(await shown(page, '#ashotrow'), false, 'the sheet has no frame row for a sound: it steps aside');
eq(await page.evaluate(() => document.querySelector('#ashot').disabled && document.querySelector('#ashotwhy').textContent), 'this is a sound: there is no picture',
   'and the button, were it asked, says why');
eq(await page.evaluate(() => document.querySelector('#asnd').disabled), false, 'the recording is cut from the sound, so that button is live');
await shot(page, 'card-sound-desktop');
await page.click('#atdeck');
await until(() => page.evaluate(() => document.querySelector('#asavelab').textContent === 'add to deck'), 'the exercise decks list');
await page.fill('#adecknew', 'Il suono');
await page.click('#asnd');
await until(() => shown(page, '.pc-cut'), 'the cut editor opens over the sheet');
await page.click('.pc-cut .pc-save');
await until(() => page.evaluate(() => { const s = document.querySelector('.pc-saved'); return s && !s.hidden && /saved/.test(document.querySelector('.pc-stat').textContent); }), 'the clip is cut out of the sound', 30000);
await page.click('.pc-cut .pc-use');
await until(() => page.evaluate(() => !document.querySelector('.pc-root') && !document.querySelector('#asndprev').hidden), 'the editor closes on the clip');
const clip = await page.evaluate(() => document.querySelector('#asndname').textContent.split(' · ')[0]);
assert(/^[a-z0-9][a-z0-9._-]*\.(mp3|m4a|wav)$/.test(clip) && await exists(`${TRAY}/${clip}`), 'the clip is in the tray: ' + clip);
await page.click('#asave');
await until(() => page.evaluate(() => /^added ✓/.test(document.querySelector('#astat').textContent)), 'the card goes into the deck', 20000);
let deck = '';
for await (const e of Deno.readDir(EXERCISES + '/english')) if (e.isDirectory && !e.name.startsWith('.')) deck = e.name;
const DECK = `${EXERCISES}/english/${deck}`;
const item = await readJson(`${DECK}/items/${(await names(DECK + '/items', /\.json$/))[0]}`);
assert(/front-audio: audio\/|back-audio: audio\//.test(item.markdown) && !/image/.test(item.markdown), 'the exercise names the recording and no picture:\n' + item.markdown);
assert((await names(DECK + '/audio')).length === 1 && (await names(DECK + '/images')).length === 0, 'the deck holds the clip and no image');
eq(item.origin && item.origin.url.endsWith(`/youtube/v/${ID_A}/#t=${Math.floor(item.origin.time)}`), true, 'its origin is this player, at its second');
await ctxA.close();

/* ================================================================ d) the phone */
{
  const {context: cp, page: pp} = await newPage({viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true}, true);
  await openVideo(pp, ID_A);
  await soundReady(pp);
  await waveReady(pp);
  eq(await pp.evaluate(() => [document.documentElement.getAttribute('data-mode'), document.documentElement.classList.contains('m-player'),
                              document.documentElement.getAttribute('data-kind')]), ['mobile', true, 'audio'], 'the phone\'s page is the mobile mode, on a sound');
  assert(await inside(pp, '#vid') && await inside(pp, '#sndwave'), 'the bar is inside the screen');
  const w = await pp.evaluate(() => [document.querySelector('#vid').getBoundingClientRect().width, innerWidth, document.documentElement.scrollWidth]);
  assert(w[0] <= w[1] && w[2] <= w[1] + 1, `no sideways scroll, the bar as wide as the screen allows: ${w.join(' / ')}`);
  const pcol = await painted(pp);
  assert(pcol.columns > 0.6 * pcol.w, `its waveform is painted on the phone: ${pcol.columns} of ${pcol.w} columns`);
  assert(await shown(pp, '.nc-dock'), 'the dock\'s controls are there');
  const before = await pp.evaluate(() => ParsehPlayer.paused());
  await pp.locator('.nc-dock .nc-play').tap();
  await until(() => pp.evaluate(() => !document.querySelector('#film').paused), 'the dock\'s middle button plays the sound');
  assert(before === true, 'it was paused, and now plays');
  await pp.locator('.nc-dock .nc-play').tap();
  await until(() => pp.evaluate(() => document.querySelector('#film').paused), 'and pauses it');
  eq(await shown(pp, '#novid .novid-send'), false, 'nothing here writes: no box that sends a film again');
  await shot(pp, 'player-light-phone');
  await theme(pp, 'dark'); await sleep(500); await shot(pp, 'player-dark-phone');
  await theme(pp, 'sepia'); await sleep(500); await shot(pp, 'player-sepia-phone');
  await theme(pp, 'light');
  // a tap on the bar goes there, with a finger
  const bb = await pp.locator('#sndwave').boundingBox();
  await pp.touchscreen.tap(bb.x + bb.width * 0.25, bb.y + bb.height / 2);
  await until(() => pp.evaluate(() => Math.abs(document.querySelector('#film').currentTime - document.querySelector('#film').duration * 0.25) < 1.5), 'a tap on the bar goes a quarter in');
  // sideways: the bar stays above the text, and the whole screen carries the subtitles over it
  await pp.setViewportSize({width: 844, height: 390});
  await sleep(500);
  eq(await pp.evaluate(() => document.body.classList.contains('sbs')), false, 'held sideways a sound is not put beside the text: there is no picture to put there');
  assert(await inside(pp, '#vid'), 'the bar is inside the screen held sideways');
  await shot(pp, 'player-light-phone-sideways');
  // the whole screen, with the line being said under the bar
  await until(() => shown(pp, 'header .m-vfull'), 'the whole-screen button is drawn held sideways');
  await pp.evaluate(() => { ParsehPlayer.seek(7.5); });
  await pp.locator('header .m-vfull').tap();
  await until(() => pp.evaluate(() => document.documentElement.classList.contains('m-vfullon')), 'the whole screen opens');
  await until(() => shown(pp, '.m-subs .m-subline .w'), 'the line being said is laid on it as subtitles');
  assert(await inside(pp, '#vid') && await inside(pp, '#sndwave') && await inside(pp, '.m-subs'),
         'the bar and the subtitles are inside the screen');
  const wide = await pp.evaluate(() => document.querySelector('#vid').getBoundingClientRect().width);
  assert(wide > 400 && wide <= 640 + 1, 'the bar takes the width a bar wants on the whole screen: ' + Math.round(wide));
  await shot(pp, 'player-whole-screen-phone');
  await pp.locator('#playerwrap .m-vout').tap();
  await until(() => pp.evaluate(() => !document.documentElement.classList.contains('m-vfullon')), 'and it closes');
  await cp.close();
}

/* ================================================================ e) a film that is not there any more */
{
  const lost = await makeVideo(MEDIA + '/picture.mp4', 'lost-film-a1b2c3', 'Lost');
  const dir = (await walk(VIDEOS)).find(p => p.endsWith('/lost-film-a1b2c3/media.mp4'));
  await Deno.remove(dir);
  const {context: c, page: p} = await newPage();
  await p.goto(`${BASE}/youtube/v/${lost.id}/`);
  await p.waitForSelector('.seg .fa .w');
  await until(() => shown(p, '#novid'), 'the page says the film is gone');
  assert(/the film \(or sound\) that belongs to this video is not here any more/.test(await p.evaluate(() => document.querySelector('#novid').textContent)), 'in words');
  assert(await shown(p, '#novid .novid-again'), 'and offers to have it sent again');
  await shot(p, 'film-missing-desktop');
  await p.setInputFiles('#novid input[type=file]', MEDIA + '/again.mp3');
  await p.waitForURL(`${BASE}/youtube/v/${lost.id}/`, {timeout: 20000}).catch(() => {});
  await until(() => p.evaluate(() => document.documentElement.getAttribute('data-kind') === 'audio' && document.querySelector('#film') && document.querySelector('#film').tagName === 'AUDIO'),
              'the page opens again on what was sent, a sound', 30000);
  eq((await walk(VIDEOS)).filter(q => q.includes('/lost-film-a1b2c3/') && /media/.test(q)).map(q => q.split('/').pop()), ['media.mp3'], 'the folder holds the sound that was sent');
  eq((await readJson((await walk(VIDEOS)).find(q => q.endsWith('/lost-film-a1b2c3/video.json')))).kind, 'audio', 'video.json now says it is one');
  // and a sound whose file goes is still a sound: a small box saying so, not a black frame with nothing in it
  await Deno.remove((await walk(VIDEOS)).find(q => q.endsWith('/lost-film-a1b2c3/media.mp3')));
  await p.reload();
  await p.waitForSelector('.seg .fa .w');
  await until(() => shown(p, '#novid .novid-again'), 'the page of a sound that is gone offers it again');
  const gone = await p.evaluate(() => ({kind: document.documentElement.getAttribute('data-kind'), h: document.querySelector('#vid').getBoundingClientRect().height}));
  assert(gone.kind === 'audio' && gone.h < 190, 'a small box, not a 16:9 frame: ' + JSON.stringify(gone));
  await shot(p, 'sound-missing-desktop');
  await c.close();
}

/* ================================================================ a playable copy, by path, in the browser */
if (HAVE_WMA) {
  const w = await makeVideo(MEDIA + '/radio.wma', 'radio-sound-a1b2c3', 'Radio');
  assert(w.converted && w.film === 'media.mp3' && w.original === 'media-orig.wma', 'a wma is added with a playable copy: ' + w.film + ' and ' + w.original);
  const {context: c, page: p} = await newPage();
  await openVideo(p, w.id);
  await soundReady(p);
  await p.evaluate(() => document.querySelector('#film').play());
  await until(() => p.evaluate(() => { const f = document.querySelector('#film'); return !f.paused && f.currentTime > 0.5; }), 'the copy plays in the browser');
  assert(!(await p.evaluate(() => !!document.querySelector('#film').error)), 'with no error from the browser');
  await c.close();
}

assert(errors.length === 0, 'no page error, no console error, no failed request in all of it' + (errors.length ? ': ' + errors.join(' | ') : ''));
console.log(`\n${passed} ok`);
} catch (e) {
  console.log('\n' + (e && e.stack || e));
  console.log('\nhub log:\n' + log.join('').slice(-3000));
  Deno.exitCode = 1;
} finally {
  try { await browser.close(); } catch (_) {}
  try { hub.kill(); } catch (_) {}
  try { await hub.status; } catch (_) {}
  await Deno.remove(TMP, {recursive: true}).catch(() => {});
}
