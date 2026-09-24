// SPDX-License-Identifier: GPL-3.0-or-later
import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=/path/to/python3 deno run --allow-all tests/player_cards.mjs
//      PLAYER_CARDS_SHOTS=<dir> also saves the card sheet in each destination,
//      at desktop and at phone width
//
// The video player's card sheet (youtube/lib/player.js, player.html) making
// its three cards -- Anki, an exercise deck, markdown -- with a recording cut
// out of the film, against the REAL hub: serve.main() on a temporary toolbox
// whose videos are copies of tests/fixtures/videos with a film of their own
// (ffmpeg, a tone), beside a fixture left as the YouTube video it is.  Nothing
// is stubbed but YouTube itself, whose iframe API is refused so the page loads
// offline.  Every file the sheet makes is read back off the disk.
//
//  a) an Italian film: alt-click a word of a caption in the middle, the film
//     playing -- the sheet opens on it and the film pauses; the destination
//     is Anki until another is picked, and the pick is remembered
//  b) the exercise deck: the deck list of the video's language, a new deck
//     (each destination keeps the new deck's name typed for it);
//     "cut the audio…" opens the kit's editor with its edges where the word's
//     share of the caption puts them (computed here from the fixture, apart
//     from the page), the film paused under it; the clip is saved and plays
//     in the sheet; a frame is captured (the tab, for real: Chrome's
//     --auto-accept-this-tab-capture); the preview draws the card and turns
//     it; add to deck: the item on disk with front-audio and back-image, both
//     files in the deck, the origin; the sheet stays, saying what went in with
//     a link to the deck; the same card again: the deck says it has it, the
//     button reads "add it again" (no dialog), a change to the card asks
//     again, and "add it again" adds a duplicate; the deck page's link opens
//     this player at the card's second
//  c) Anki: the same sheet saves a note with the recording on the side asked
//     for (snd_back, the file in the deck's media/) and the frame, and closes,
//     and the film plays on
//  d) another word, of a caption the film is not in: the card's moment is
//     that caption's (a deck's link back, the source); markdown: another cut
//     (its edges checked too); the clipboard's text read by the real parser
//     with no error; jolly, prefilled, the clip a line in the back's main
//     text, then a clip cut again going into the box the cursor was last in;
//     that card read by the parser and drawn by the preview with the new clip
//     in it; the line taken out by hand stays out of the copy, the preview and
//     a return to jolly; a browser that will not put the markdown on the
//     clipboard: the markdown shown in the sheet, selected, and its clip kept
//     in the tray
//  e) a Japanese film: a word of a chunk's word line, whose share is counted
//     in the line's own words
//  f) the YouTube fixture, its player never loaded (YouTube is refused here):
//     nothing to cut, and the button says why; its exercise decks list all the
//     same (recording a YouTube video's sound: tests/youtube_capture.mjs)
//  g) THE SHEET KEEPS WHAT WAS PRESSED, as the book reader's does: a clip
//     nobody used leaves the tray when the sheet closes, one a card took stays;
//     the sheet closed while "add to deck" is still out and opened again on
//     another word -- the deck gets the first word's card with its recording,
//     the answer comes as a toast, the second sheet is neither told nor
//     closed; an Anki save answered while the cut editor is open does not
//     close the sheet under it, and the clip cut there lands on the card; a
//     clip cut before jolly is picked goes into the jolly box the cursor was
//     last in, typed in or not
//  h) the card kit did not load: "cut the audio…", an exercise deck and
//     markdown each say so, in the book reader's words
// Rows are looked at as drawn (their boxes on the page), not by their
// `hidden` property.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('PLAYER_CARDS_SHOTS') || '';
const TMP = await Deno.makeTempDir({prefix: 'parseh-player-cards-'});
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
async function py(code, ...args) {
  const r = await run(PY, ['-c', code, ...args]);
  if (r.code) throw Error(r.err || r.out);
  return r.out;
}
async function ff(...args) {
  const r = await run('ffmpeg', ['-y', '-loglevel', 'error', ...args]);
  if (r.code) throw Error('ffmpeg: ' + r.err);
}
async function duration(path) {
  const r = await run('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path]);
  if (r.code) throw Error('ffprobe: ' + r.err);
  return parseFloat(r.out);
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

/* ---------------------------------------------------------------- the tree */
// Two films on this machine (their ids local ones: a slug and six hex, no
// YouTube address) copied from the fixtures, and the Italian fixture itself
// as the YouTube video it is.
const IT_FIX = 'tests/fixtures/videos/italian/kL9mN1oP3qR';
const JA_FIX = 'tests/fixtures/videos/japanese/aB3dE5fG7hI';
const IT = 'al-mercato-a1b2c3', JA = 'kyou-no-tenki-d4e5f6', YT = 'kL9mN1oP3qR';
const ROOT = TMP + '/root', VIDEOS = ROOT + '/youtube/videos';
const TRAY = TMP + '/tray', EXERCISES = TMP + '/exercises', ANKI = TMP + '/anki';
// the Japanese caption 2's second chunk carries a word line
const JA_LINE = '天気(てんき) が';

async function copyVideo(fix, folder, id, film, edit) {
  const d = `${VIDEOS}/${folder}/${id}`;
  await Deno.mkdir(d + '/parts', {recursive: true});
  const meta = await readJson(fix + '/video.json');
  Object.assign(meta, {id}, film ? {url: ''} : {});
  await Deno.writeTextFile(d + '/video.json', JSON.stringify(meta, null, 1));
  const ann = await readJson(fix + '/annotations.json');
  ann.video = id;
  if (edit) edit(ann);
  await Deno.writeTextFile(d + '/annotations.json', JSON.stringify(ann, null, 1));
  if (film)
    await ff('-f', 'lavfi', '-i', 'testsrc=duration=40:size=320x180:rate=10', '-f', 'lavfi', '-i',
             'sine=frequency=440:duration=40', '-shortest', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
             '-c:a', 'aac', d + '/media.mp4');
  return ann;
}
await Deno.mkdir(ROOT + '/youtube', {recursive: true});
await Deno.symlink(root + '/lib', ROOT + '/lib');
await Deno.symlink(root + '/youtube/lib', ROOT + '/youtube/lib');
for (const d of [TRAY, EXERCISES, ANKI, TMP + '/library']) await Deno.mkdir(d, {recursive: true});
const itAnn = await copyVideo(IT_FIX, 'italian', IT, true);
const jaAnn = await copyVideo(JA_FIX, 'japanese', JA, true, ann => {
  const ch = ann.segments[2].chunks[1];
  ann.segments[2].chunks[1] = Object.fromEntries(Object.entries(ch).flatMap(([k, v]) => k === 'fa' ? [[k, v], ['words', JA_LINE]] : [[k, v]]));
});
await copyVideo(IT_FIX, 'italian', YT, false);
assert(await py('import sys; sys.path.insert(0, "youtube/lib"); sys.path.insert(0, "lib"); import ytpages; ' +
                'print(ytpages.is_local_id(sys.argv[1]) and ytpages.is_local_id(sys.argv[2]) and not ytpages.is_local_id(sys.argv[3]))',
                IT, JA, YT) === 'True\n', 'the two films have local ids, the YouTube fixture does not');

/* ---------------------------------------------------------------- the hub */
// serve.main() with every store it writes pointed into the temporary tree
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

/* ---------------------------------------------------------------- the guess, apart from the page */
// SPEC §7/§8: a caption lasts from its start to the next caption's; a chunk
// starts after the chunks before it and their separators, a word after the
// words before it; the edges are the stretch's share of the caption, 0.12 s
// wider each side, rounded by the editor to the hundredth.  Code points.
const cps = s => [...(s || '')].length;
function expected(ann, i, j, k, sep, line) {
  const sg = ann.segments[i], t0 = sg.start, t1 = ann.segments[i + 1].start;
  const chunks = sg.chunks;
  const units = cps(chunks.map(c => c.fa).join(sep));
  let pre = 0;
  for (let m = 0; m < j; m++) pre += cps(chunks[m].fa) + cps(sep);
  let a, b;
  if (line) {
    // the line's words are the chunk's text in order: the k-th starts after
    // the surfaces before it
    const surf = line.trim().split(/\s+/).map(w => w.replace(/\(.*\)$/, ''));
    a = surf.slice(0, k).reduce((n, w) => n + cps(w), 0);
    b = a + cps(surf[k]);
  } else {
    const words = chunks[j].fa.split(sep);
    a = words.slice(0, k).reduce((n, w) => n + cps(w) + cps(sep), 0);
    b = a + cps(words[k]);
  }
  const lo = Math.max(0, t0 - 0.3), hi = t1 + 0.3, clamp = x => Math.min(hi, Math.max(lo, x));
  const s = clamp(t0 + (t1 - t0) * (pre + a) / units - 0.12);
  const e = clamp(t0 + (t1 - t0) * (pre + b) / units + 0.12);
  return {context: [t0, t1], s: Math.round(s * 100) / 100, e: Math.round(e * 100) / 100};
}

/* ---------------------------------------------------------------- the browser */
const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true,
  args: ['--autoplay-policy=no-user-gesture-required', '--auto-accept-this-tab-capture']});
const errors = [];
async function newPage(width = 1280, height = 900) {
  const context = await browser.newContext({viewport: {width, height}});
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: BASE});
  const page = await context.newPage();
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push('console: ' + m.text()); });
  page.on('response', r => {
    const u = new URL(r.url());
    if (u.host === `127.0.0.1:${port}` && r.status() >= 400 && r.status() !== 409
        && /^\/(clips|exercises\/api|anki|youtube\/api|lib\/cardkit|studio\/static)/.test(u.pathname.slice(0)))
      errors.push(r.status() + ' ' + r.request().method() + ' ' + u.pathname);
  });
  // YouTube is not here: its API script is refused, as it is offline
  await context.route(/^https?:\/\/(?!127\.0\.0\.1)/, route => route.abort());
  return {context, page};
}
async function openVideo(page, id) {
  await page.goto(`${BASE}/youtube/v/${id}/`);
  await page.waitForSelector('.seg .fa .w');
}
const filmReady = page => until(() => page.evaluate(() => { const f = document.querySelector('#film'); return f && f.readyState >= 1 && f.duration > 30; }), 'the film loads');
// drawn: a box of some size on the page, whatever its `hidden` says
const shown = (page, sel) => page.evaluate(sel => {
  const el = document.querySelector(sel);
  return !!el && [...el.getClientRects()].some(r => r.width > 0 && r.height > 0) &&
         getComputedStyle(el).visibility !== 'hidden';
}, sel);
const KIT_GONE = 'the card kit (lib/cardkit.js) did not load: reload the page';
const INTO = 'in the jolly box the cursor was last in (the back\'s main text until one has been)';
// the sheet really on screen: inside the viewport, and what is at its middle is it
const sheetOnScreen = page => page.evaluate(() => {
  const box = document.querySelector('#anki'), r = box.getBoundingClientRect();
  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + 30);
  return !box.hidden && r.top >= 0 && r.left >= 0 && r.right <= innerWidth && r.bottom <= innerHeight + 1 && box.contains(hit);
});
const value = (page, sel) => page.evaluate(sel => document.querySelector(sel).value, sel);
const text = (page, sel) => page.evaluate(sel => document.querySelector(sel).textContent, sel);
async function altClick(page, sel) {
  await page.mouse.move(2, 2);
  await page.locator(sel).click({modifiers: ['Alt']});
  await until(() => sheetOnScreen(page), 'the card sheet opens on screen');
}
async function shot(page, name) {
  if (!SHOTS) return;
  await Deno.mkdir(SHOTS, {recursive: true});
  await page.screenshot({path: `${SHOTS}/${name}.png`});
}
// the cut editor: open it, read its edges, check them against the fixture
async function openCutter(page, want, what) {
  await page.click('#asnd');
  await until(() => shown(page, '.pc-cut'), 'the cut editor opens');
  const got = await page.evaluate(() => ({
    s: +document.querySelector('.pc-cut input.e0').value, e: +document.querySelector('.pc-cut input.e1').value,
    who: document.querySelector('.pc-cut .who').textContent, said: document.querySelector('.pc-what').textContent,
    film: document.querySelector('#film').paused,
    on: (() => { const r = document.querySelector('.pc-cut').getBoundingClientRect();
                 return r.top >= 0 && r.bottom <= innerHeight + 1 && document.querySelector('.pc-cut').contains(document.elementFromPoint(r.left + r.width / 2, r.top + 20)); })()
  }));
  assert(got.on, what + ': the cut editor is on screen, over the sheet');
  assert(near(got.s, want.s, 0.01) && near(got.e, want.e, 0.01),
         `${what}: its edges are the word's share of the caption: ${got.s}–${got.e} (expected ${want.s}–${want.e})`);
  assert(got.film, what + ': the film stays paused under it');
  return got;
}
async function cutAndUse(page, what) {
  await page.click('.pc-cut .pc-save');
  await until(() => page.evaluate(() => { const s = document.querySelector('.pc-saved'); return s && !s.hidden && /saved/.test(document.querySelector('.pc-stat').textContent); }),
              what + ': the clip is saved', 30000);
  const e0 = +(await value(page, '.pc-cut input.e0')), e1 = +(await value(page, '.pc-cut input.e1'));
  await page.click('.pc-cut .pc-use');
  await until(() => page.evaluate(() => !document.querySelector('.pc-root') && !document.querySelector('#asndprev').hidden), what + ': the editor closes on the clip');
  const clip = await page.evaluate(() => ({name: document.querySelector('#asndname').textContent.split(' · ')[0],
                                           src: document.querySelector('#asndaudio').getAttribute('src')}));
  assert(/^[a-z0-9][a-z0-9._-]*\.(mp3|m4a|wav)$/.test(clip.name) && clip.src === '/clips/media/' + clip.name,
         `${what}: the sheet shows the clip ${clip.name}, an <audio> of the tray's ${clip.src}`);
  const d = await duration(`${TRAY}/${clip.name}`);
  assert(near(d, e1 - e0, 0.08), `${what}: the tray's file lasts the clip, ${d.toFixed(3)} s for ${e0}–${e1}`);
  return clip;
}
async function playsInSheet(page, what) {
  await page.evaluate(() => { const a = document.querySelector('#asndaudio'); a.currentTime = 0; return a.play(); });
  await until(() => page.evaluate(() => { const a = document.querySelector('#asndaudio'); return a.readyState >= 2 && !a.paused && a.currentTime > 0.15; }),
              what + ': the clip plays in the sheet');
  await page.evaluate(() => document.querySelector('#asndaudio').pause());
  assert(true, what + ': the clip plays in #asndprev (readyState >= 2, currentTime past 0.15 s)');
}
async function clipboard(page) { return page.evaluate(() => navigator.clipboard.readText()); }
// the markdown through mdparser: the exercise blocks, with their errors
async function parsed(md) {
  return JSON.parse(await py(
    'import json, sys; sys.path.insert(0, "markdown/exlex"); sys.path.insert(0, "lib"); import mdparser\n' +
    'fm, blocks = mdparser.parse(sys.argv[1], target="it")\n' +
    'print(json.dumps([{"type": b["type"], "subtype": b.get("subtype"), "errors": b.get("errors"), "fields": b.get("fields"), "raw": b.get("raw_fields")} for b in blocks]))', md));
}

try {
/* ================================================================ a) the Italian film */
const {context, page} = await newPage();
await page.goto(BASE + '/');
await page.evaluate(() => localStorage.clear());
await openVideo(page, IT);
await filmReady(page);
eq(await page.evaluate(() => [typeof window.ParsehCards, !!document.querySelector('link[href="/lib/cardkit.css"]')]),
   ['object', true], 'the player links the card kit, and it is on the page');
// the film playing from the caption, a word of it: "chilo," of "al chilo,"
await page.evaluate(() => { const f = document.querySelector('#film'); f.currentTime = 16.2; return f.play(); });
await until(() => page.evaluate(() => !document.querySelector('#film').paused), 'the film plays');
await altClick(page, '.seg[data-i="3"] .w[data-j="1"] .wd >> nth=1');
eq(await page.evaluate(() => ({fa: document.querySelector('#afa').value, film: document.querySelector('#film').paused,
                               on: [...document.querySelectorAll('.atarget button.on')].map(b => b.id),
                               title: document.querySelector('#ahtitle').textContent, save: document.querySelector('#asavelab').textContent,
                               cut: document.querySelector('#asnd').disabled})),
   {fa: 'chilo', film: true, on: ['atanki'], title: 'anki card', save: 'save card', cut: false},
   'the sheet opens on the word, the film paused, for Anki as it always did ("anki card"), the cut enabled');
eq([await shown(page, '#akjolly'), await shown(page, '#asndwhy')], [false, false], 'no jolly for Anki, and nothing to say under the cut');
await shot(page, 'sheet-anki-desktop');
// a name for a new Anki deck, typed before another destination is picked
await until(() => shown(page, '#adecknew'), 'no Anki deck yet: the new deck\'s name is asked');
await page.fill('#adecknew', 'Italiano::Video');

/* ================================================================ b) an exercise deck */
await page.click('#atdeck');
await until(() => page.evaluate(() => document.querySelector('#adeck').options.length > 0 && document.querySelector('#asavelab').textContent === 'add to deck'), 'the exercise decks list');
eq(await page.evaluate(() => ({on: [...document.querySelectorAll('.atarget button.on')].map(b => b.id),
                               kept: localStorage.getItem('yt_card_target'),
                               options: [...document.querySelector('#adeck').options].map(o => o.textContent),
                               typed: document.querySelector('#adecknew').value, title: document.querySelector('#ahtitle').textContent,
                               save: document.querySelector('#asavelab').textContent})),
   {on: ['atdeck'], kept: 'deck', options: ['+ new deck…'], typed: '', title: 'exercise card', save: 'add to deck'},
   'exercise deck: picked and remembered, no deck yet so "+ new deck…" with an empty name (the Anki name stays Anki\'s), "exercise card", "add to deck"');
eq([await shown(page, '#adecknew'), await shown(page, '#akjolly'), await shown(page, '#atagsrow'), await shown(page, '#abuild')],
   [true, true, false, false], 'drawn: the new deck\'s name box and jolly; tags and build are not');
await page.fill('#adecknew', 'Al mercato');
// each destination keeps the name typed for it
await page.click('#atanki');
await until(async () => await text(page, '#asavelab') === 'save card' && await shown(page, '#adecknew'), 'Anki again');
eq(await value(page, '#adecknew'), 'Italiano::Video', 'back on Anki, the new deck\'s name is the one typed for Anki');
await page.click('#atdeck');
await until(() => page.evaluate(() => document.querySelector('#asavelab').textContent === 'add to deck'), 'the exercise deck again');
eq(await value(page, '#adecknew'), 'Al mercato', 'and on the exercise deck, the one typed for it');

const want1 = expected(itAnn, 3, 1, 1, ' ');
eq(want1.context, [15, 20], 'the caption lasts from its start to the next caption\'s');
const cut1 = await openCutter(page, want1, 'the word "chilo,"');
eq([cut1.who, cut1.said], ['0:15', 'chilo'], 'the editor names the caption\'s moment and the word');
await shot(page, 'cutter-desktop');
const clip1 = await cutAndUse(page, 'the word "chilo,"');
await playsInSheet(page, 'the word "chilo,"');

// a frame of the film, captured from the tab itself
await page.click('#ashot');
await until(() => page.evaluate(() => { const i = document.querySelector('#ashotimg'); return !document.querySelector('#ashotprev').hidden && i.naturalWidth > 100; }),
            'the frame is captured', 40000);
const frameSize = await page.evaluate(() => [document.querySelector('#ashotimg').naturalWidth, document.querySelector('#ashotimg').naturalHeight]);
assert(frameSize[0] > 100 && near(frameSize[0] / frameSize[1], 16 / 9, 0.08),
       'a frame of the video area alone is captured, ' + frameSize.join('×'));

// the preview draws the card the deck will draw, and it turns
await page.click('#apreview');
await until(() => shown(page, '#apvrow'), 'the preview shows');
const frame = page.frameLocator('#apvframe');
await frame.locator('.ex-flashcard').waitFor();
const pv = await page.evaluate(() => {
  const d = document.querySelector('#apvframe').contentDocument;
  return {audio: [...d.querySelectorAll('.ex-card-audio audio')].map(a => a.getAttribute('src')),
          img: [...d.querySelectorAll('img.ex-card-image')].map(i => i.getAttribute('src')),
          target: d.querySelector('.ex-card-front').textContent.includes('chilo'),
          note: document.querySelector('#apvnote').textContent};
});
const frameName = (await names(TRAY, /\.(png|jpe?g)$/))[0];
assert(frameName, 'the frame went to the tray to be named: ' + frameName);
eq([pv.audio, pv.img, pv.target], [['/clips/media/audio/' + clip1.name], ['/clips/media/images/' + frameName], true],
   'the preview is the deck\'s card: the word, the recording and the frame, from the tray');
await frame.locator('.ex-card-front').click();
await until(() => page.evaluate(() => document.querySelector('#apvframe').contentDocument.querySelector('.ex-flashcard').classList.contains('flipped')), 'the previewed card turns');
assert(true, 'a click turns the previewed card');
await shot(page, 'sheet-deck-desktop');

await page.click('#asave');
await until(() => page.evaluate(() => /^added ✓/.test(document.querySelector('#astat').textContent)), 'the card goes into the deck', 20000);
let deckSlug = '';
for await (const e of Deno.readDir(EXERCISES + '/italian')) if (e.isDirectory && !e.name.startsWith('.')) deckSlug = e.name;
const DECK = `${EXERCISES}/italian/${deckSlug}`;
eq((await readJson(DECK + '/deck.json')).name, 'Al mercato', 'the new deck is made, in the video\'s language');
const items1 = await names(DECK + '/items', /\.json$/);
eq(items1.length, 1, 'one exercise in it');
const item = await readJson(`${DECK}/items/${items1[0]}`);
assert(item.markdown.includes('front-audio: audio/' + clip1.name) && item.markdown.includes('back-image: images/' + frameName)
       && /target: \[chilo\]\{tl\}/.test(item.markdown),
       'the exercise names the recording on the front and the frame on the back, its Latin-script word marked:\n' + item.markdown);
assert(await exists(`${DECK}/audio/${clip1.name}`) && await exists(`${DECK}/images/${frameName}`),
       'the deck has both files, brought from the tray');
const t0 = item.origin && item.origin.time;
assert(t0 >= 16.2 && t0 < 17.5, 'the card\'s moment is the film\'s when the sheet opened, inside the word\'s caption: ' + t0);
eq(item.origin && {video: item.origin.video, label: item.origin.label, url: item.origin.url, title: item.origin.title},
   {video: IT, label: `0:${String(Math.floor(t0)).padStart(2, '0')}`, url: `/youtube/v/${IT}/#t=${Math.floor(t0)}`,
    title: 'Italian at the market: a short dialogue for beginners'},
   'its origin: the video, the moment, the link back, the title');
eq(await page.evaluate(() => [document.querySelector('#astat').textContent, document.querySelector('#astat a').getAttribute('href')]),
   ['added ✓ — a vocabulary card for “chilo”, with its recording and its frame, to “Al mercato” — open the deck', `/exercises/deck/italian/${deckSlug}/`],
   'the sheet says what went in, with a link to the deck');
await sleep(1300);
assert(await sheetOnScreen(page), 'and it stays open, for the link to be followed');
await shot(page, 'sheet-deck-added-desktop');
await until(() => page.evaluate(() => [...document.querySelector('#adeck').options].filter(o => o.selected).map(o => o.textContent).join() === 'Al mercato (1 exercise)'),
            'the deck is picked, with its count');
assert(true, 'and the deck is picked now, with its count: Al mercato (1 exercise)');

// the same card again: asked on the sheet, and added only when the person
// says so -- no dialog
const dialogs = [];
const onDialog = d => { dialogs.push(d.message()); d.dismiss(); };
page.on('dialog', onDialog);
await page.click('#asave');
await until(() => page.evaluate(() => document.querySelector('#asavelab').textContent === 'add it again'), 'the duplicate is asked about');
await shot(page, 'sheet-deck-duplicate-desktop');
eq([await text(page, '#astat'), (await names(DECK + '/items', /\.json$/)).length, dialogs],
   ['this exercise is already in "Al mercato" — press “add it again” to add a second one', 1, []],
   'a second add: the deck says it has it, nothing is added, the button reads "add it again", no dialog');
// a change to the card asks again
await page.click('#akvocab');
eq(await text(page, '#asavelab'), 'add to deck', 'a click on the card\'s type puts the button back to "add to deck"');
await page.click('#asave');
await until(() => page.evaluate(() => document.querySelector('#asavelab').textContent === 'add it again'), 'asked again');
await page.click('#asave');
await until(async () => (await names(DECK + '/items', /\.json$/)).length === 2, 'a duplicate added when asked for');
await until(() => page.evaluate(() => /^added ✓/.test(document.querySelector('#astat').textContent)), 'the duplicate says it went in');
eq([await text(page, '#asavelab'), dialogs], ['add to deck', []], '"add it again" adds the second one, and the button is "add to deck" again');
page.off('dialog', onDialog);

// the deck page links the exercise back to this player, at its second
{
  const {context: c2, page: p2} = await newPage();
  await p2.goto(`${BASE}/exercises/deck/italian/${deckSlug}/`);
  const a = p2.locator('.dk-origin a').first();
  await a.waitFor();
  eq(await a.getAttribute('href'), `/youtube/v/${IT}/#t=${Math.floor(t0)}`, 'the deck page links the exercise to the player at its second');
  await a.click();
  await p2.waitForURL(new RegExp(`/youtube/v/${IT}/#t=`));
  await until(() => p2.evaluate(t => { const f = document.querySelector('#film'); return f && f.readyState >= 1 && Math.abs(f.currentTime - t) < 0.6; }, Math.floor(t0)),
              'the player opens at that second');
  assert(true, 'following it opens the player with the film at ' + Math.floor(t0) + ' s');
  await c2.close();
}

/* ================================================================ c) Anki */
await page.click('#atanki');
await until(() => page.evaluate(() => document.querySelector('#adeck').options.length > 0 && !document.querySelector('#abuild').hidden), 'the Anki decks list');
eq(await page.evaluate(() => [[...document.querySelector('#adeck').options].map(o => o.textContent), document.querySelector('#asavelab').textContent,
                               document.querySelector('#ahtitle').textContent]),
   [['+ new deck…'], 'save card', 'anki card'], 'Anki again: its own decks, "save card", "anki card"');
eq([await shown(page, '#abuild'), await shown(page, '#akjolly'), await shown(page, '#asndprev'), await shown(page, '#asndsides')],
   [true, false, true, true], 'drawn: build, no jolly, the clip still on the card with its sides');
eq(await value(page, '#adecknew'), 'Italiano::Video', 'back on Anki once the exercise deck is made: the name is still the one typed for Anki');
await page.check('input[name=asndside][value=back]');
await page.click('#apreview');
await until(() => shown(page, '#apvrow'), 'the Anki preview shows');
{
  const [sandbox, srcs] = await page.evaluate(() => [document.querySelector('#apvframe').getAttribute('sandbox'),
    [...document.querySelector('#apvframe').contentDocument.querySelectorAll('audio')].map(a => a.getAttribute('src'))]);
  assert(sandbox === 'allow-same-origin' && srcs.length >= 1 && srcs.every(s => s === '/clips/media/' + clip1.name),
         'the Anki preview plays the clip from the tray, in a frame that runs no script: ' + JSON.stringify([sandbox, srcs]));
}
await shot(page, 'sheet-anki-clip-desktop');
await page.click('#asave');
await until(async () => !(await shown(page, '#anki')), 'the Anki card is saved and the sheet closes', 20000);
let ankiSlug = '';
for await (const e of Deno.readDir(ANKI + '/italian')) if (e.isDirectory) ankiSlug = e.name;
const ADECK = `${ANKI}/italian/${ankiSlug}`;
const cards = await names(ADECK + '/cards', /\.json$/);
eq(cards.length, 1, 'one note in the Anki deck');
const note = await readJson(`${ADECK}/cards/${cards[0]}`);
assert(note.fa === 'chilo' && note.snd_front === null && /-back-audio\.(mp3|m4a|wav)$/.test(note.snd_back || '')
       && /-back\.jpg$/.test(note.img_back || ''), 'the note: the word, the recording on the back as asked, the frame: ' +
       JSON.stringify({fa: note.fa, snd_front: note.snd_front, snd_back: note.snd_back, img_back: note.img_back}));
const media = await Deno.readFile(`${ADECK}/media/${note.snd_back}`), trayClip = await Deno.readFile(`${TRAY}/${clip1.name}`);
assert(media.length === trayClip.length && media.every((b, i) => b === trayClip[i]), 'its media/ holds the clip, byte for byte');
await until(() => page.evaluate(() => !document.querySelector('#film').paused), 'the film plays on once the sheet closes');
assert(true, 'the film paused under the sheet plays on when it closes');
await page.evaluate(() => document.querySelector('#film').pause());

/* ================================================================ d) markdown, and jolly */
// the film stands in another caption (the last, from 0:28): the card's moment
// is the start of the caption its word is in (0:11), not the film's
await page.evaluate(() => { document.querySelector('#film').currentTime = 33; });
await until(() => page.evaluate(() => { const f = document.querySelector('#film'); return !f.seeking && Math.abs(f.currentTime - 33) < 0.1; }), 'the film stands at 0:33');
await altClick(page, '.seg[data-i="2"] .w[data-j="1"] .wd >> nth=1');
eq([await page.evaluate(() => document.querySelector('#afa').value), await page.evaluate(() => [...document.querySelectorAll('.atarget button.on')].map(b => b.id)),
    await shown(page, '#asndprev'), await shown(page, '#ashotprev')],
   ['mele', ['atanki'], false, false], 'another word: the sheet remembers Anki, and starts without a clip or a frame');
eq(await page.evaluate(() => [document.querySelector('#atime').textContent, document.querySelector('#asrc').value, Math.round(document.querySelector('#film').currentTime)]),
   ['0:11', 'Italian at the market: a short dialogue for beginners — 0:11', 33],
   'the film at 0:33, a word of the caption at 0:11: the card\'s moment and its source are the caption\'s');
// into the deck: its link goes back to where the word is said
{
  const before = await names(DECK + '/items', /\.json$/);
  await page.click('#atdeck');
  await until(() => page.evaluate(() => [...document.querySelector('#adeck').options].filter(o => o.selected).map(o => o.textContent).join() === 'Al mercato (2 exercises)'),
              'the deck used last is picked');
  await page.click('#asave');
  await until(() => page.evaluate(() => /^added ✓/.test(document.querySelector('#astat').textContent)), 'the word goes into the deck', 20000);
  const added = (await names(DECK + '/items', /\.json$/)).filter(n => !before.includes(n));
  eq(added.length, 1, 'one more exercise in the deck');
  const it3 = await readJson(`${DECK}/items/${added[0]}`);
  eq({time: it3.origin.time, label: it3.origin.label, url: it3.origin.url}, {time: 11, label: '0:11', url: `/youtube/v/${IT}/#t=11`},
     'its origin is the caption\'s moment, not the film\'s');
}
await page.click('#atmd');
eq([await shown(page, '#adeckrow'), await page.evaluate(() => [document.querySelector('#asavelab').textContent, document.querySelector('#ahtitle').textContent,
                                                                localStorage.getItem('yt_card_target')])],
   [false, ['copy markdown', 'card markdown', 'md']], 'markdown: no deck drawn, "copy markdown", "card markdown", remembered');
const want2 = expected(itAnn, 2, 1, 1, ' ');
await openCutter(page, want2, 'the word "mele"');
const clip2 = await cutAndUse(page, 'the word "mele"');
await shot(page, 'sheet-md-desktop');
await page.click('#asave');
await until(() => page.evaluate(() => /^copied ✓/.test(document.querySelector('#astat').textContent)), 'the markdown is copied');
eq(await text(page, '#astat'),
   'copied ✓ — a vocabulary card for “mele”. Paste it into a studio document or a deck’s “Add exercise”: the recording comes along from the clip tray when it is pasted there',
   'the sheet says where to paste it, and that the recording comes along from the tray');
const md1 = await clipboard(page);
const b1 = (await parsed(md1)).filter(b => b.type === 'exercise');
eq(b1.map(b => [b.subtype, b.errors, b.fields['front-audio'], b.fields.target, b.fields.meaning, b.fields.source]),
   [['flashcard', [], 'audio/' + clip2.name, '[mele]{tl}', 'the apples today',
     `[Italian at the market: a short dialogue for beginners — 0:11](${BASE}/youtube/v/${IT}/#t=11)`]],
   'the clipboard holds one flashcard the parser reads with no error, the recording on its front, its source linking the caption\'s moment');

// jolly: prefilled from the word, the clip a line of the back's main text
await page.click('#akjolly');
const jolly = () => page.evaluate(() => ['#ajfp', '#ajfs', '#ajbp', '#ajbs'].map(s => document.querySelector(s).value));
eq([await shown(page, '#ajollyrow'), await shown(page, '#afarow'), await shown(page, '#aenrow'), await shown(page, '#asndsides'),
    await shown(page, '#asndprev .ajollyinto'), await text(page, '#asndprev .ajollyinto')],
   [true, false, false, false, true, INTO], 'jolly: its four fields drawn instead of the vocabulary\'s, and the clip goes into a box rather than on a side, which the sheet says');
eq(await jolly(), ['[mele]{tl}', '', 'the apples today\n![](audio/' + clip2.name + ')', 'le mele oggi'],
   'prefilled: the word marked, the meaning with the clip under it, the context');
await shot(page, 'sheet-jolly-desktop');
// the person writes in the front's small field, and cuts again
await page.click('#ajfs');
await page.keyboard.type('le mele');
await openCutter(page, want2, 'the word "mele" again');
await page.click('.pc-cut [data-e="e+"]');
await sleep(100);
const clip3 = await cutAndUse(page, 'the word "mele", cut a little longer');
assert(clip3.name !== clip2.name, 'a new clip');
eq(await jolly(), ['[mele]{tl}', 'le mele\n![](audio/' + clip3.name + ')', 'the apples today', 'le mele oggi'],
   'the new clip goes under the line the cursor was on, in the box it was last in, and the old one leaves the card');
assert(await exists(`${TRAY}/${clip2.name}`), 'the old clip stays in the tray: the markdown copied before names it');
await page.click('#asave');
await until(async () => /^copied ✓/.test(await text(page, '#astat')) && (await clipboard(page)) !== md1, 'the jolly card is copied');
const md2 = await clipboard(page);
const b2 = (await parsed(md2)).filter(b => b.type === 'exercise');
eq(b2.map(b => [b.subtype, b.errors, b.fields['card-type'], (b.raw || {})['front-secondary']]),
   [['flashcard', [], 'jolly', 'le mele\n![](audio/' + clip3.name + ')']],
   'the jolly card reads with no error, the clip a line of its front\'s small field');
await page.click('#apreview');
await until(() => page.evaluate(() => !document.querySelector('#apvrow').hidden &&
  !!document.querySelector('#apvframe').contentDocument.querySelector('.ex-flashcard audio')), 'the jolly preview');
eq(await page.evaluate(() => [...document.querySelector('#apvframe').contentDocument.querySelectorAll('.ex-flashcard audio')].map(a => a.getAttribute('src'))),
   ['/clips/media/audio/' + clip3.name], 'the preview draws the jolly card with the recording in it');
await shot(page, 'sheet-jolly-preview-desktop');

// the person takes the clip's line out of the field by hand: it stays out --
// the copy, the fields and the preview go without it, and the sheet says so
await page.fill('#ajfs', 'le mele');
eq(await text(page, '#astat'), '', 'the preview left the status line empty');
await page.click('#asave');
await until(async () => /^copied ✓/.test(await text(page, '#astat')), 'the jolly card is copied again');
const md3 = await clipboard(page);
eq(await jolly(), ['[mele]{tl}', 'le mele', 'the apples today', 'le mele oggi'], 'a line taken out by hand is not put back by the copy');
const b3 = (await parsed(md3)).filter(b => b.type === 'exercise');
eq([b3.map(b => [b.errors, b.fields['card-type'], b.fields['front-secondary']]), md3.includes('audio/')],
   [[[[], 'jolly', 'le mele']], false], 'the copied card reads with no error and names no recording:\n' + md3);
eq(await text(page, '#astat'),
   'copied ✓ — a jolly card. Paste it into a studio document or a deck’s “Add exercise” — the recording is not on the card: its line was taken out of the fields',
   'the sheet says the recording is not on the card');
await page.click('#apreview');
await until(() => page.evaluate(() => { const d = document.querySelector('#apvframe').contentDocument;
  return !document.querySelector('#apvrow').hidden && d && d.querySelector('.ex-flashcard') && /le mele/.test(d.querySelector('.ex-card-front').textContent) &&
         !d.querySelector('audio'); }), 'the preview draws the card without the recording');
eq((await jolly())[1], 'le mele', 'nor does the preview put the line back');
await page.click('#akvocab');
await page.click('#akjolly');
eq(await jolly(), ['[mele]{tl}', 'le mele', 'the apples today', 'le mele oggi'], 'nor does picking vocabulary and jolly again');

// removing the clip takes its line out; a clip nothing was made with leaves the tray
await openCutter(page, want2, 'the word "mele", a third time');
const clip4 = await cutAndUse(page, 'the word "mele", a third time');
assert((await jolly()).join('\n').includes('audio/' + clip4.name), 'the third clip is on the card');
await page.click('#asnddel');
await until(async () => !(await exists(`${TRAY}/${clip4.name}`)), 'a clip removed before anything used it leaves the tray');
assert(!(await jolly()).join('\n').includes('audio/') && !(await shown(page, '#asndprev')),
       'removed: its line is gone and the sheet shows no clip');
assert(await exists(`${TRAY}/${clip3.name}`), 'the clip the copied card names stays in the tray');

// a browser that will not put the markdown on the clipboard -- the API
// refuses, and so does the old copy command: the markdown is shown in the
// sheet, selected, to copy by hand, and the clip it names stays in the tray
await openCutter(page, want2, 'the word "mele", for a copy the browser refuses');
const clip5 = await cutAndUse(page, 'the word "mele", for a copy the browser refuses');
await page.evaluate(() => {
  navigator.clipboard.writeText = () => Promise.reject(new DOMException('not allowed', 'NotAllowedError'));
  document.execCommand = () => false;
});
await page.click('#asave');
await until(() => page.evaluate(() => /not copied|would not/.test(document.querySelector('#astat').textContent)), 'the copy is refused');
{
  const got = await page.evaluate(() => { const o = document.querySelector('#amdout');
    return {md: o.value, focused: document.activeElement === o, selected: o.selectionStart === 0 && o.selectionEnd === o.value.length}; });
  await shot(page, 'sheet-markdown-by-hand-desktop');
  eq([await shown(page, '#amdrow'), got.focused, got.selected, await text(page, '#astat')],
     [true, true, true, 'not copied — the browser would not put it on the clipboard: the markdown is below, to copy by hand'],
     'refused: the sheet shows the markdown, focused and selected, and says so');
  const b5 = (await parsed(got.md)).filter(b => b.type === 'exercise');
  assert(b5.length === 1 && b5[0].errors.length === 0 && got.md.includes('audio/' + clip5.name),
         'the markdown shown is the card, naming its clip, and reads with no error');
}
await page.keyboard.press('Escape');
await sleep(1000);
assert(await exists(`${TRAY}/${clip5.name}`), 'closed: the clip the markdown to copy by hand names stays in the tray');

// the destination is remembered across a reload
await page.keyboard.press('Escape');
await page.reload();
await page.waitForSelector('.seg .fa .w');
await altClick(page, '.seg[data-i="3"] .w[data-j="2"] .wd');
eq(await page.evaluate(() => [...document.querySelectorAll('.atarget button.on')].map(b => b.id)), ['atmd'], 'after a reload the sheet opens on markdown');
await page.keyboard.press('Escape');

/* ---- the phone ---- */
{
  const {context: cp, page: pp} = await newPage(400, 820);
  await pp.goto(BASE + '/');
  await pp.evaluate(() => localStorage.setItem('yt_card_target', 'deck'));
  await openVideo(pp, IT);
  await filmReady(pp);
  await pp.evaluate(() => document.querySelector('.seg[data-i="3"]').scrollIntoView({block: 'center'}));
  await altClick(pp, '.seg[data-i="3"] .w[data-j="1"] .wd >> nth=1');
  await until(() => pp.evaluate(() => [...document.querySelector('#adeck').options].some(o => /Al mercato/.test(o.textContent))), 'the phone lists the deck');
  const fits = () => pp.evaluate(() => {
    const box = document.querySelector('#anki');
    const bad = [...box.querySelectorAll('button, input, select, textarea, audio, .atarget')].filter(el => {
      if (el.closest('[hidden]')) return false;
      const r = el.getBoundingClientRect();
      return r.width && (r.left < 0 || r.right > innerWidth);
    }).map(el => el.id || el.className);
    return {bad, scroll: document.documentElement.scrollWidth <= innerWidth + 1, box: box.getBoundingClientRect().right <= innerWidth};
  });
  eq(await fits(), {bad: [], scroll: true, box: true}, 'at 400 px the deck sheet fits the screen');
  await shot(pp, 'sheet-deck-phone');
  await pp.click('#asnd');
  await until(() => shown(pp, '.pc-cut'), 'the cut editor on the phone');
  await shot(pp, 'cutter-phone');
  await pp.keyboard.press('Escape');
  await until(() => pp.evaluate(() => !document.querySelector('.pc-root')), 'cancelled');
  await pp.click('#atmd');
  await pp.click('#akjolly');
  eq(await fits(), {bad: [], scroll: true, box: true}, 'at 400 px the jolly sheet fits the screen');
  await shot(pp, 'sheet-jolly-phone');
  await pp.click('#atanki');
  eq(await fits(), {bad: [], scroll: true, box: true}, 'at 400 px the Anki sheet fits the screen');
  await shot(pp, 'sheet-anki-phone');
  if (SHOTS) {
    // and in the dark: the sheet's new rows take the page's tokens
    await pp.click('#atdeck');
    await pp.evaluate(() => document.documentElement.setAttribute('data-theme', 'dark'));
    await shot(pp, 'sheet-deck-phone-dark');
  }
  await cp.close();
}
await context.close();

/* ================================================================ e) a word of a word line */
{
  const {context: cj, page: pj} = await newPage();
  await openVideo(pj, JA);
  await filmReady(pj);
  await altClick(pj, '.seg[data-i="2"] .w[data-j="1"] .wd[data-k="0"]');
  eq(await value(pj, '#afa'), '天気', 'Japanese: the sheet opens on the line\'s word');
  const wantJa = expected(jaAnn, 2, 1, 0, '', JA_LINE);
  await openCutter(pj, wantJa, 'the word 天気 of the line ' + JA_LINE);
  await pj.keyboard.press('Escape');
  await until(() => pj.evaluate(() => !document.querySelector('.pc-root')), 'cancelled');
  // and a whole chunk from the cloud's button: the chunk's share
  await pj.keyboard.press('Escape');
  await pj.mouse.move(2, 2);
  await pj.locator('.seg[data-i="3"] .w[data-j="2"]').hover();
  await until(() => shown(pj, '#cloud .mkcard'), 'the cloud opens');
  eq(await text(pj, '#cloud .mkcard'), '+ card', 'the gloss cloud\'s button reads "+ card", for whichever destination');
  await pj.click('#cloud .mkcard');
  await until(() => sheetOnScreen(pj), 'the sheet opens from the cloud');
  const sg = jaAnn.segments[3], units = cps(sg.chunks.map(c => c.fa).join('')), pre = cps(sg.chunks[0].fa) + cps(sg.chunks[1].fa);
  const r2 = x => Math.round(x * 100) / 100;
  const wantChunk = {s: r2(14 + 6 * pre / units - 0.12), e: r2(14 + 6 * (pre + cps(sg.chunks[2].fa)) / units + 0.12)};
  await openCutter(pj, wantChunk, 'the chunk コーヒーを from the cloud');
  await pj.keyboard.press('Escape');
  await cj.close();
}

/* ================================================================ f) the YouTube video */
{
  const {context: cy, page: py2} = await newPage();
  await openVideo(py2, YT);
  await altClick(py2, '.seg[data-i="3"] .w[data-j="1"] .wd >> nth=1');
  eq(await py2.evaluate(() => {
    const b = document.querySelector('#asnd'), h = document.querySelector('#asndwhy');
    return [b.disabled, b.title, [...h.getClientRects()].some(r => r.height > 0), !!document.querySelector('#film'), document.querySelector('#afa').value];
  }), [true, 'the YouTube player has not loaded, so there is no sound to record', true, false, 'chilo'],
     'YouTube: the sheet opens, and "cut the audio…" is disabled while there is no player to record, saying why');
  eq(await text(py2, '#atime'), '0:15', 'YouTube, its player not ready: the card\'s moment is the caption\'s, as for a film');
  await py2.click('#atdeck');
  await until(() => py2.evaluate(() => [...document.querySelector('#adeck').options].some(o => o.textContent === 'Al mercato (3 exercises)')), 'the deck lists');
  assert(true, 'YouTube: the exercise decks of its language list all the same');
  await cy.close();
}

/* ================================================================ g) what was pressed is kept */
{
  const {context: cg, page: pg} = await newPage();
  // the answers to making a deck, to an add and to an Anki save come late, as
  // over a slow link
  await cg.route(u => /^\/(exercises\/api\/decks(\/.+\/items)?|anki\/cards)$/.test(new URL(u).pathname), async route => {
    if (route.request().method() === 'POST') await sleep(700);
    await route.continue();
  });
  await pg.goto(BASE + '/');
  await pg.evaluate(() => localStorage.setItem('yt_card_target', 'deck'));
  await openVideo(pg, IT);
  await filmReady(pg);
  const want = expected(itAnn, 3, 1, 1, ' ');
  const toast = () => pg.evaluate(() => { const t = document.querySelector('#parseh-toast');
    return t && t.classList.contains('show') ? t.textContent : ''; });

  // a clip cut and never used leaves the tray when the sheet closes
  await altClick(pg, '.seg[data-i="3"] .w[data-j="1"] .wd >> nth=1');
  await openCutter(pg, want, 'a clip for nobody');
  const unused = await cutAndUse(pg, 'a clip for nobody');
  await pg.keyboard.press('Escape');
  await until(async () => !(await exists(`${TRAY}/${unused.name}`)), 'the unused clip leaves the tray when the sheet closes');
  assert(true, 'closed without a card: the clip cut for it left the tray (' + unused.name + ')');
  assert(await exists(`${TRAY}/${clip3.name}`) && await exists(`${TRAY}/${clip1.name}`), 'the clips cards were made with stay in the tray');

  // the sheet closed while its add is out -- the new deck still being made --
  // and opened on another word
  await altClick(pg, '.seg[data-i="3"] .w[data-j="1"] .wd >> nth=1');
  await until(() => pg.evaluate(() => [...document.querySelector('#adeck').options].some(o => /Al mercato/.test(o.textContent))), 'the decks list');
  await pg.selectOption('#adeck', '');
  await pg.fill('#adecknew', 'Closed early');
  await openCutter(pg, want, 'the clip of an add cut short');
  const outClip = await cutAndUse(pg, 'the clip of an add cut short');
  await pg.click('#asave');
  await pg.keyboard.press('Escape');
  await altClick(pg, '.seg[data-i="2"] .w[data-j="1"] .wd >> nth=1');
  const told = await until(toast, 'the answer comes as a toast');
  eq(told, 'added ✓ — a vocabulary card for “chilo”, with its recording, to “Closed early”', 'the answer to the closed sheet comes as a toast over the page, in the book reader\'s words');
  const EARLY = `${EXERCISES}/italian/closed-early`, added = await names(EARLY + '/items', /\.json$/);
  const it = await readJson(`${EARLY}/items/${added[0]}`);
  assert(added.length === 1 && /target: \[chilo\]\{tl\}/.test(it.markdown) && it.markdown.includes('front-audio: audio/' + outClip.name),
         'the deck got the card that was pressed, the first word with its recording, not the word the sheet is open on now:\n' + it.markdown);
  eq({time: it.origin.time, label: it.origin.label}, {time: 15, label: '0:15'}, 'and its origin is the pressed word\'s moment, not the second sheet\'s (0:11)');
  assert(await exists(`${EARLY}/audio/${outClip.name}`) && await exists(`${TRAY}/${outClip.name}`),
         'the recording is in the deck, and still in the tray: closing the sheet did not take it away');
  eq([await value(pg, '#afa'), await shown(pg, '#anki'), await text(pg, '#astat')],
     ['mele', true, ''], 'the sheet open on the second word is neither told nor closed');
  await sleep(1200);
  eq(await shown(pg, '#anki'), true, '…nor closed a moment later');

  // an Anki save answered while the cut editor is open: the sheet stays
  await pg.click('#atanki');
  await until(() => pg.evaluate(() => !document.querySelector('#abuild').hidden && document.querySelector('#adeck').options.length > 0), 'Anki');
  await pg.click('#asave');
  // the editor opened from the keyboard: no click in the sheet to put off its closing
  await pg.focus('#asnd');
  await pg.keyboard.press('Enter');
  await until(() => shown(pg, '.pc-cut'), 'the cut editor opens while the save is out');
  await until(() => pg.evaluate(() => /^saved ✓/.test(document.querySelector('#astat').textContent)), 'the Anki save is answered under the editor');
  await sleep(1500);
  eq([await shown(pg, '#anki'), await pg.evaluate(() => !!document.querySelector('.pc-root'))], [true, true],
     'the sheet does not close itself under the open cut editor');
  const late = await cutAndUse(pg, 'a clip cut while the save was answered');
  eq([await shown(pg, '#anki'), await pg.evaluate(() => document.querySelector('#asndname').textContent.split(' · ')[0])],
     [true, late.name], 'the clip cut there lands on the card, on the sheet still open');

  // a clip cut before jolly is picked: into the jolly box the cursor was last
  // in -- written in one box, then only clicked in another
  await pg.click('#atmd');
  await pg.click('#akjolly');
  await pg.click('#ajbs');
  await pg.keyboard.press('End');
  await pg.keyboard.type(' (written here last)');
  await pg.click('#ajfs');
  await pg.click('#akvocab');
  await openCutter(pg, expected(itAnn, 2, 1, 1, ' '), 'a clip cut on the vocabulary card');
  const beforeJolly = await cutAndUse(pg, 'a clip cut on the vocabulary card');
  await pg.click('#akjolly');
  const fields = await pg.evaluate(() => ['#ajfp', '#ajfs', '#ajbp', '#ajbs'].map(s => document.querySelector(s).value));
  assert(fields[1].endsWith('![](audio/' + beforeJolly.name + ')') && fields.filter(v => v.includes('audio/')).length === 1
         && fields[3].endsWith(' (written here last)'),
         'picked afterwards, jolly takes the clip into the box the cursor was last in, not the one last written in: ' + JSON.stringify(fields));
  await pg.keyboard.press('Escape');
  await until(async () => !(await exists(`${TRAY}/${beforeJolly.name}`)) && !(await exists(`${TRAY}/${late.name}`)),
              'the unused clips leave the tray');
  assert(true, 'the clip it replaced left the tray then, and this one with the sheet');
  await cg.close();
}

/* ================================================================ h) no card kit */
{
  const {context: ck, page: pk} = await newPage();
  await ck.route(/\/lib\/cardkit\.js$/, route => route.abort());
  await openVideo(pk, IT);
  await altClick(pk, '.seg[data-i="3"] .w[data-j="1"] .wd >> nth=1');
  eq([await pk.evaluate(() => [typeof window.ParsehCards, document.querySelector('#asnd').disabled, document.querySelector('#asnd').title]),
      await shown(pk, '#asndwhy'), await text(pk, '#asndwhy')],
     [['undefined', true, KIT_GONE], true, KIT_GONE], 'no card kit: "cut the audio…" is disabled, and says why under it');
  const said = [];
  for (const t of ['#atdeck', '#atmd']) {
    await pk.click(t);
    said.push(await text(pk, '#astat'));
    await pk.click('#asave');
    said.push(await text(pk, '#astat'));
  }
  await pk.click('#atanki');
  said.push(await text(pk, '#astat'));
  eq(said, [KIT_GONE, KIT_GONE, KIT_GONE, KIT_GONE, ''], 'an exercise deck and markdown say so when picked and when pressed; Anki does not');
  await ck.close();
}

assert(errors.length === 0, 'no page error and no failed request: ' + JSON.stringify(errors));
assert(!/Traceback/.test(log.join('')), 'no traceback in the hub\'s log');
console.log(`\nplayer_cards: ${passed} checks passed`);
} catch (e) {
  console.log(e.stack || e);
  console.log('page errors:', JSON.stringify(errors));
  console.log('hub log tail:\n' + log.join('').slice(-3000));
  Deno.exitCode = 1;
} finally {
  await browser.close();
  try { hub.kill('SIGTERM'); await hub.status; } catch (_) {}
  await Deno.remove(TMP, {recursive: true}).catch(() => {});
}
