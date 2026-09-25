// SPDX-License-Identifier: GPL-3.0-or-later
import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=python3 deno run --allow-all tests/timings.mjs
//
// THE TIMELINE (lib/timeline.js): where one piece of text stops being said
// and the next starts, moved by hand over a picture of the sound.  One editor
// shared by the book reader and the video player, as the card kit is, opened
// from a fourth button on a narration row ("by ear") and from the player's
// header ("the timings").
//
// What has to hold, and is covered nowhere else:
//
//   a) A BOUNDARY IS ONE ACT.  In a book the end of one subparagraph and the
//      start of the next are two numbers, and the whole point of showing the
//      boundary is that moving it is ONE thing: drag it and both numbers
//      become the same new number.  Two edits that have to be made to agree
//      is exactly what this exists to stop.
//   b) UNLESS THEY ARE SPLIT.  A recording that really does pause wants the
//      end of one before the start of the next, with the silence between
//      belonging to neither -- drawn as such, and joinable again.
//   c) A VIDEO HAS NEITHER.  A caption carries a start and nothing else, and
//      the one before it runs until that start, so there is one number per
//      boundary and no split to be had at all.
//   d) THE PICTURE IS THE RECORDING'S OWN SOUND, not a decoration: a tone
//      reads tall and a silence flat, at the second they are actually at.
//      It comes from the server for a book and for a film on this machine
//      (ffmpeg, window by window), and from a recording of this tab for a
//      YouTube video -- which is offered, never assumed, and says what it
//      will cost before anyone presses it.
//   e) IT SAVES THROUGH THE DOORS THAT ALREADY EXIST.  A book's times go out
//      by __save/subtimes.json, the one `save times` has always used; a
//      video's by /youtube/api/times, which moves the start in every file
//      that carries one (tests/test_captimes.py is the proof of that half).
//   i) "ESTIMATE THE REST" GOES BY THE TEXT OR BY THE SOUND, a choice kept
//      on this device.  By the sound asks the server once (lib/wavealign.py
//      behind serve.py) and lays its answer after the line exactly as by the
//      text would -- nothing left of the line moves -- and it is grey, saying
//      why, wherever there is no picture of the sound to go by: a reader
//      built before it, a machine without ffmpeg, a YouTube video whose sound
//      has not been drawn -- and ONLY there: a view too long for the server
//      to draw at once ("all" over a long narration) is not a machine
//      without ffmpeg.  A failure changes nothing and says so.
//
// The hub is REAL (tests/cardkit_harness.py builds a temp toolbox and runs
// serve.main over it) because the waveform comes from a real ffmpeg over a
// real recording; the harness's sound is a tone at every whole second from 1
// to 7, so where the waveform is tall is checkable against where the sound
// actually is.  Only YouTube is faked, and only its iframe API.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const TMP = await Deno.makeTempDir({prefix: 'parseh-timings-'});
const PORT = 8700 + Math.floor(Math.random() * 300);
const VIDEO = 'street-market-a1b2c3';
const YT = 'fA6bK2mQ8sT';

let passed = 0, failed = 0;
const assert = (v, m) => { if (v) { passed++; console.log('  ok', m); } else { failed++; console.log('  FAIL', m); } };
const eq = (a, b, m) => assert(JSON.stringify(a) === JSON.stringify(b), m + ' -- got ' + JSON.stringify(a));
const secs = s => String(s).trim().split(':').reduce((a, b) => a * 60 + +b, 0);
// #captimes is live in the markup before the captions have loaded, so one
// press can land before the player is ready and be refused: press until the
// sheet is up, rather than assume the first one took
async function openSheet(pg, sel) {
  await pg.waitForFunction(() => document.querySelectorAll('.seg').length > 0, null, {timeout: 25000});
  for (let i = 0; i < 30; i++) {
    await pg.click(sel);
    try { await pg.waitForSelector('.tl-root', {timeout: 1000}); return; } catch (_) {}
  }
  throw new Error('the timings sheet never opened');
}

// every piece's two numbers as the strip shows them, read off its lines
// (each line's aria-valuenow) with the view on the whole recording, so that
// reading them takes up no piece and moves no line in hand: [t0], [t1] and
// the silences drawn as said by neither
const linesOf = pg => pg.evaluate(() => {
  const ls = [...document.querySelectorAll('.tl-edge')].map(e =>
    ({i: +e.dataset.i, who: e.dataset.who, t: +e.getAttribute('aria-valuenow')}));
  const n = document.querySelectorAll('.tl-band').length;
  let k = 0;
  const t0 = [ls[k++].t], t1 = [];
  for (let i = 0; i < n; i++) {
    t1.push(ls[k++].t);
    if (i + 1 < n) t0.push(k < ls.length && ls[k].who === 's' ? ls[k++].t : t1[i]);
  }
  return {t0, t1, gaps: document.querySelectorAll('.tl-gap').length};
});
const r2 = x => Math.round(x * 100) / 100;
const tenth = x => Math.round(x * 10) / 10;
const clock = t => { const m = Math.floor(t / 60), s = t - m * 60; return m + ':' + (s < 10 ? '0' : '') + s.toFixed(2); };
const pressedOn = pg => pg.evaluate(() => ['by-text', 'by-sound'].map(x =>
  document.querySelector(`[data-x="${x}"]`).getAttribute('aria-pressed')));
const soundLive = (pg, ms = 15000) => pg.waitForFunction(() => {
  const b = document.querySelector('[data-x="by-sound"]');
  return b && !b.disabled;
}, null, {timeout: ms}).then(() => true, () => false);
const statOf = pg => pg.evaluate(() => {
  const s = document.querySelector('.tl-stat');
  return s ? {text: s.textContent, bad: s.classList.contains('tl-bad')} : null;
});
const settled = (pg, ms = 60000) => pg.waitForFunction(() => {
  const s = document.querySelector('.tl-stat');
  return s && (/estimated from the sound/.test(s.textContent) || s.classList.contains('tl-bad'));
}, null, {timeout: ms}).then(() => true, () => false);
// Is lib/wavealign.py there, and does it import with the Python the hub
// runs?  Only then is the real answer asked for; every other check routes
// the request and makes the answer up, because what they test is the page.
const REAL = new Deno.Command(PY, {
  args: ['-c', 'import sys; sys.path.insert(0, "lib"); import wavealign; wavealign.estimate_pieces'],
  stdout: 'null', stderr: 'null'}).outputSync().code === 0;

const build = new Deno.Command(PY, {args: ['tests/cardkit_harness.py', 'build', TMP]}).outputSync();
if (build.code !== 0) {
  console.log(new TextDecoder().decode(build.stderr));
  Deno.exit(1);
}
// a YouTube video too: no film anywhere, so no waveform for free
await Deno.mkdir(`${TMP}/root/youtube/videos/persian`, {recursive: true});
await new Deno.Command('cp', {args: ['-r', `tests/fixtures/videos/persian/${YT}`,
                                     `${TMP}/root/youtube/videos/persian/${YT}`]}).output();

const hub = new Deno.Command(PY, {
  args: ['tests/cardkit_harness.py', 'serve', TMP, String(PORT)],
  stdout: 'piped', stderr: 'piped',
}).spawn();
const BASE = `http://127.0.0.1:${PORT}`;
for (let i = 0; i < 40; i++) {
  try { await fetch(`${BASE}/books/`); break; } catch (_) { await new Promise(r => setTimeout(r, 250)); }
}

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
const errors = [];
try {
  /* ============ a) a book: the boundary between two subparagraphs ========= */
  const page = await browser.newPage({viewport: {width: 1100, height: 850}});
  page.on('pageerror', e => errors.push('book: ' + e.message));
  const posted = [];
  await page.route('**/__save/subtimes.json', async r => {
    posted.push(JSON.parse(r.request().postData() || '{}'));
    await r.continue();
  });
  await page.goto(`${BASE}/books/english/mini-en/reader/`);
  await page.waitForFunction(() => typeof SUBS !== 'undefined' && document.querySelector('.sub'));

  console.log('a) the fourth button on a narration row');
  await page.click('#narr');
  await page.waitForSelector('#nlist:not([hidden])');
  eq(await page.evaluate(() => [...document.querySelectorAll('#nlist .nitem')[0]
       .querySelectorAll('.nacts button')].map(b => b.textContent)),
     ['align', 'estimate times', 'by ear', 'remove'],
     'it is the fourth, after the two that do it for you and before remove');
  assert(!await page.evaluate(() => document.querySelector('#nlist .nitem [data-x="byear"]').disabled),
         'and it is live, because this recording is timed');

  console.log('   the sheet it opens: the sound, and the text either side of the boundary');
  await page.click('#nlist .nitem [data-x="byear"]');
  await page.waitForSelector('.tl-root');
  await page.waitForFunction(() => document.querySelectorAll('.tl-band').length > 0);
  await page.click('[data-x="all"]');
  const shown = await page.evaluate(() => ({
    bands: [...document.querySelectorAll('.tl-band')].map(b => b.querySelector('.tl-blab').textContent),
    edges: document.querySelectorAll('.tl-edge').length,
    here: document.querySelector('.tl-now .tl-say').textContent,
    before: document.querySelector('.tl-prev .tl-say').textContent,
    after: document.querySelector('.tl-next .tl-say').textContent,
  }));
  eq(shown.bands, ['1.1', '1.2', '2.1', '2.2'], 'one block per subparagraph, each named');
  assert(shown.edges === 5, 'and five boundaries for four joined pieces: ' + shown.edges);
  assert(shown.here.startsWith('1.1') && shown.here.length > 8,
         'the piece being timed shows its words: ' + JSON.stringify(shown.here.slice(0, 40)));
  assert(/nothing before/.test(shown.before), 'the first has nothing before it');
  assert(shown.after.startsWith('1.2'), 'and the one after it is named too');
  // away from the ends it draws the neighbourhood and not the whole recording
  await page.click('[data-x="fit"]');
  assert(await page.evaluate(() => document.querySelectorAll('.tl-band').length) < 4,
         'fitted, it shows the boundary and its neighbours');
  await page.click('[data-x="all"]');

  console.log('d) the waveform is the recording\'s own sound');
  await page.waitForFunction(() => document.querySelector('.tl-strip.tl-drawn'), null, {timeout: 20000});
  const wave = await page.evaluate(() => {
    const c = document.querySelector('.tl-wave'), g = c.getContext('2d');
    const w = c.width, h = c.height;
    const t = [...document.querySelectorAll('.tl-t')].map(n =>
      n.textContent.split(':').reduce((a, b) => a * 60 + +b, 0));
    const at = s => Math.round((s - t[0]) / (t[1] - t[0]) * w);
    const col = x => { let n = 0;
      const d = g.getImageData(Math.max(0, Math.min(w - 1, x)), 0, 1, h).data;
      for (let y = 0; y < h; y++) if (d[y * 4 + 3] > 0) n++; return n; };
    return {loud: col(at(3.3)), quiet: col(at(3.85))};
  });
  // the harness sounds a tone for 0.6 s at every whole second from 1 to 7
  assert(wave.loud > 20, 'a tone at 3.3 s is drawn tall: ' + wave.loud + ' px');
  assert(wave.quiet < wave.loud / 3, 'and the silence at 3.85 s is flat: '
         + wave.quiet + ' against ' + wave.loud);

  console.log('a) moving a boundary moves BOTH numbers, and only them');
  const nums = async i => {
    await page.click(`.tl-band[data-i="${i}"]`);
    return await page.evaluate(() => [...document.querySelectorAll('.tl-at')]
      .map(n => n.value.split(':').reduce((a, b) => a * 60 + +b, 0)));
  };
  const was0 = await nums(0), was1 = await nums(1);
  assert(Math.abs(was0[1] - was1[0]) < 0.001,
         'they start as one number in two places: ' + JSON.stringify([was0[1], was1[0]]));
  const geo = await page.evaluate(() => {
    const s = document.querySelector('.tl-strip').getBoundingClientRect();
    const e = [...document.querySelectorAll('.tl-edge')].map(n => {
      const r = n.getBoundingClientRect();
      return {x: (r.left + r.right) / 2, y: (r.top + r.bottom) / 2, i: n.dataset.i, who: n.dataset.who};
    });
    const t = [...document.querySelectorAll('.tl-t')].map(n =>
      n.textContent.split(':').reduce((a, b) => a * 60 + +b, 0));
    return {width: s.width, edges: e, v0: t[0], v1: t[1]};
  });
  const pps = geo.width / (geo.v1 - geo.v0);
  const grab = geo.edges.find(e => e.who === 'e' && e.i === '0');
  await page.mouse.move(grab.x, grab.y);
  await page.mouse.down();
  await page.mouse.move(grab.x + 40, grab.y, {steps: 5});
  await page.mouse.move(grab.x + 40, grab.y, {steps: 2});
  await page.mouse.up();
  const want = was0[1] + 40 / pps;
  const now0 = await nums(0), now1 = await nums(1);
  assert(Math.abs(now0[1] - want) < 0.15,
         `the first now ends where it was dropped: ${now0[1].toFixed(2)} (wanted ${want.toFixed(2)})`);
  assert(Math.abs(now1[0] - now0[1]) < 0.001,
         'and the second starts at that same number, by the same one act: '
         + JSON.stringify([now0[1], now1[0]]));
  assert(Math.abs(now1[1] - was1[1]) < 0.001, 'while its far end stayed put: ' + now1[1]);

  console.log('b) split leaves the silence to neither, and join takes it back');
  await page.click('.tl-band[data-i="0"]');
  await page.click('[data-x="split"]');
  await page.click('.tl-row[data-edge="e"] [data-e="e-5"]');
  const apart = await page.evaluate(() => ({
    gaps: document.querySelectorAll('.tl-gap').length,
    edges: document.querySelectorAll('.tl-edge').length,
    label: document.querySelector('[data-x="split"]').textContent,
  }));
  assert(apart.gaps === 1, 'the silence said by neither is drawn: ' + apart.gaps);
  assert(apart.edges === 6, 'and the boundary is two lines now, not one: ' + apart.edges);
  assert(apart.label === 'join to the next', 'the button offers to join it back');
  const split0 = await nums(0), split1 = await nums(1);
  assert(split0[1] < split1[0] - 0.4, 'the end really is before the next start: '
         + JSON.stringify([split0[1], split1[0]]));
  await page.click('.tl-band[data-i="0"]');
  await page.click('[data-x="split"]');
  const back0 = await nums(0), back1 = await nums(1);
  assert(Math.abs(back0[1] - back1[0]) < 0.001, 'joined, they are one number again: '
         + JSON.stringify([back0[1], back1[0]]));
  eq(await page.evaluate(() => document.querySelectorAll('.tl-gap').length), 0,
     'and the silence is gone');

  console.log('   zoom, which the strip has and the cut editor never had');
  const z0 = await page.evaluate(() => document.querySelector('.tl-span').textContent);
  await page.click('[data-x="in"]');
  const z1 = await page.evaluate(() => document.querySelector('.tl-span').textContent);
  await page.click('[data-x="all"]');
  const z2 = await page.evaluate(() => document.querySelector('.tl-span').textContent);
  assert(parseFloat(z1) < parseFloat(z0), `in shows less at once: ${z0} -> ${z1}`);
  assert(Math.abs(parseFloat(z2) - 8) < 0.4, `and "all" is the whole 8 s recording: ${z2}`);

  console.log('f) the keys a hand doing this presses over and over');
  const here = () => page.evaluate(() =>
    document.querySelector('.tl-now .tl-say').textContent.slice(0, 3).trim());
  await page.click('.tl-band[data-i="0"]');
  eq(await here(), '1.1', 'it starts on the first piece');
  // the comma and the full stop lead, because [ and ] sit behind AltGr on an
  // Italian or a French keyboard and these do not, anywhere
  for (const [fwd, back, what] of [[',', '.', 'the comma and the full stop'],
                                   ['PageUp', 'PageDown', 'the page keys'],
                                   ['[', ']', 'the brackets']]) {
    await page.keyboard.press(back);
    const on = await here();
    await page.keyboard.press(back);
    const on2 = await here();
    await page.keyboard.press(fwd);
    await page.keyboard.press(fwd);
    eq([on, on2, await here()], ['1.2', '2.1', '1.1'],
       what + ' step on and step back through the pieces');
  }
  // it stops at the ends rather than wrapping or throwing
  await page.keyboard.press(',');
  eq(await here(), '1.1', 'stepping back from the first stays on the first');
  for (let i = 0; i < 6; i++) await page.keyboard.press('.');
  eq(await here(), '2.2', 'and stepping on past the last stays on the last');
  await page.click('.tl-band[data-i="1"]');

  console.log('   F brings the view back to the piece being timed');
  await page.click('[data-x="all"]');
  const wide = parseFloat(await page.evaluate(() => document.querySelector('.tl-span').textContent));
  await page.keyboard.press('f');
  const fitted = parseFloat(await page.evaluate(() => document.querySelector('.tl-span').textContent));
  assert(fitted < wide, `F fits it: ${wide} s across -> ${fitted} s across`);
  const byBtn = await (async () => {
    await page.click('[data-x="all"]');
    await page.click('[data-x="fit"]');
    return parseFloat(await page.evaluate(() => document.querySelector('.tl-span').textContent));
  })();
  assert(Math.abs(byBtn - fitted) < 0.01, 'and fits it to exactly what the button does: ' + byBtn);
  assert(/\(F\)/.test(await page.evaluate(() => document.querySelector('[data-x="fit"]').title)),
         'the button says its key, as the cut editor\'s buttons do');

  console.log('   and none of them fire while a time is being typed');
  const wasHere = await here();
  await page.click('.tl-at');
  await page.keyboard.press('.');
  await page.keyboard.press(',');
  await page.keyboard.press('f');
  eq(await here(), wasHere, 'typing into a time box does not step anywhere');
  assert(await page.evaluate(() => document.activeElement.classList.contains('tl-at')),
         'and the box still has the focus');
  await page.click('.tl-band[data-i="1"]');
  // Ctrl+F is the browser's, and stays the browser's
  await page.click('[data-x="all"]');
  const before = await page.evaluate(() => document.querySelector('.tl-span').textContent);
  await page.keyboard.press('Control+f');
  eq(await page.evaluate(() => document.querySelector('.tl-span').textContent), before,
     'Ctrl+F is left to the browser and fits nothing');
  assert(await page.evaluate(() => [...document.querySelectorAll('.tl-hint')]
           .some(n => /take up the piece before and after/.test(n.textContent))),
         'and the hint says where all of this is, which is the whole of finding it');

  console.log('g) S drops the line being moved into the nearest quiet');
  // the harness sounds a tone from every whole second to .6 of it and is
  // silent until the next, so the gaps are [1.6,2), [2.6,3)... and their
  // middles are 1.8, 2.8, 3.8 -- which is what "the middle of the quiet"
  // has to mean, to a hundredth.  This boundary may be moved between 0.85
  // and 5.15 (a piece keeps a little of itself either side), so every time
  // asked for here is inside that.
  const box = w => `.tl-row[data-edge="${w}"] .tl-at`;
  const at = w => page.evaluate(sel => {
    const v = document.querySelector(sel).value;
    return v.split(':').reduce((x, y) => x * 60 + +y, 0);
  }, box(w));
  // fill leaves the focus IN the box, where s is a letter and not a
  // shortcut, so the focus is given up before any key is pressed
  const put = async (w, v) => {
    await page.fill(box(w), v);
    await page.keyboard.press('Enter');
    await page.evaluate(() => document.activeElement && document.activeElement.blur());
    await page.waitForTimeout(120);
  };
  const settles = async (w, was) => {
    await page.waitForFunction(o => {
      const v = document.querySelector(o.sel).value;
      return v.split(':').reduce((x, y) => x * 60 + +y, 0) !== o.was;
    }, {sel: box(w), was}, {timeout: 15000});
    return at(w);
  };
  await page.click('.tl-band[data-i="0"]');
  for (const [from, want] of [['0:03.40', 3.8], ['0:04.40', 4.8], ['0:02.20', 1.8]]) {
    await put('e', from);
    const was = await at('e');
    await page.keyboard.press('s');
    const got = await settles('e', was);
    assert(Math.abs(got - want) < 0.06,
           `from ${from} it lands in the middle of the gap at ${want}: ${got.toFixed(2)}`);
  }

  console.log('   the button does the same, and says what it is for');
  assert(/nearest stretch where the sound drops away/.test(
           await page.evaluate(() => document.querySelector('[data-x="quiet"]').title)),
         'the button says what it does, and names its key');
  await put('e', '0:03.15');
  const wasB = await at('e');
  await page.click('[data-x="quiet"]');
  const gotB = await settles('e', wasB);
  assert(Math.abs(gotB - 2.8) < 0.06, 'the button lands where the key does: ' + gotB.toFixed(2));

  console.log('   it moves the line the arrows would move, and not the other one');
  await put('e', '0:03.90');
  await put('s', '0:01.30');
  const endHeld = await at('e');
  await page.keyboard.press('s');
  const gotS = await settles('s', 1.3);
  assert(Math.abs(gotS - 1.8) < 0.06,
         'the START was the line in hand, so the start moved: ' + gotS.toFixed(2));
  assert(Math.abs(await at('e') - endHeld) < 0.001,
         'and the end stayed exactly where it was: ' + endHeld);

  console.log('   and it does not fire while a time is being typed');
  // the BOX shows what was typed; what must not have moved is the boundary,
  // which the line above the steps reads out of the marks themselves
  const modelEnd = () => page.evaluate(() => {
    const m = /to (\d+):(\d+\.\d+)/.exec(document.querySelector('.tl-what').textContent);
    return m ? +m[1] * 60 + +m[2] : null;
  });
  await put('e', '0:03.40');
  const held = await modelEnd();
  await page.click(box('e'));
  await page.keyboard.press('s');
  await page.waitForTimeout(700);
  // where in the text it lands is the caret's business, not ours
  assert(/s/.test(await page.evaluate(sel => document.querySelector(sel).value, box('e'))),
         'in a box, s is a letter and goes into the box');
  assert(Math.abs(await modelEnd() - held) < 0.001,
         'and the boundary did not move from ' + held);
  // and a time that will not parse is refused, the box going back to the mark
  await page.evaluate(() => document.activeElement && document.activeElement.blur());
  await page.waitForTimeout(150);
  assert(Math.abs(await at('e') - held) < 0.001,
         'a time that will not parse is refused and the box goes back to the '
         + 'boundary: ' + await at('e'));

  console.log('h) E lays a fresh guess over everything after the line in hand');
  // the whole point is the half it does NOT touch: a hand works left to
  // right, and what is behind it has been put right by hand already
  await page.click('[data-x="all"]');
  await page.click('.tl-band[data-i="1"]');
  await put('e', '0:04.00');            // the line in hand: the end of piece 1
  const kept0 = await nums(0), kept1 = await nums(1);
  const was2 = await nums(2), was3 = await nums(3);
  // reading them took the selection with it (nums clicks a block), so the
  // line in hand is put back where the hand actually left it
  await page.click('.tl-band[data-i="1"]');
  await put('e', '0:04.00');
  assert(await page.evaluate(() => !document.querySelector('[data-x="rest"]').disabled),
         'the button is live while there is something after this one');
  await page.keyboard.press('e');
  await page.waitForTimeout(300);
  const got0 = await nums(0), got1 = await nums(1);
  const got2 = await nums(2), got3 = await nums(3);
  assert(JSON.stringify(got0) === JSON.stringify(kept0),
         'not one number of the piece before it moved: ' + JSON.stringify([kept0, got0]));
  assert(JSON.stringify(got1) === JSON.stringify(kept1),
         'nor of the piece the line belongs to, whose end IS the line: '
         + JSON.stringify([kept1, got1]));
  assert(JSON.stringify(got2) !== JSON.stringify(was2)
         || JSON.stringify(got3) !== JSON.stringify(was3),
         'and everything after it was re-timed: ' + JSON.stringify([was2, got2, was3, got3]));
  assert(Math.abs(got2[0] - kept1[1]) < 0.001,
         'the first of them starts exactly at the line: ' + got2[0] + ' vs ' + kept1[1]);
  assert(Math.abs(got3[1] - was3[1]) < 0.001,
         'and the last end is still the end of what the recording covers: ' + got3[1]);
  assert(Math.abs(got2[1] - got3[0]) < 0.001,
         'the pieces it laid meet one another: ' + JSON.stringify([got2, got3]));
  assert(got2[1] - got2[0] >= 0.39 && got3[1] - got3[0] >= 0.39,
         'and none is shorter than the floor: '
         + JSON.stringify([+(got2[1] - got2[0]).toFixed(2), +(got3[1] - got3[0]).toFixed(2)]));
  // the longer text gets the longer slice, which is the whole measure
  const share = await page.evaluate(() => {
    const t = i => (document.querySelector(`.tl-band[data-i="${i}"]`) || {}).title || '';
    return [t(2), t(3)];
  });
  console.log('      slices:', JSON.stringify([+(got2[1] - got2[0]).toFixed(2),
                                               +(got3[1] - got3[0]).toFixed(2)]));

  console.log('   on the very last piece there is nothing after it to estimate');
  await page.click('.tl-band[data-i="3"]');
  await page.click('.tl-row[data-edge="e"] [data-e="e+"]');   // the END of the last one
  await page.waitForTimeout(150);
  assert(await page.evaluate(() => document.querySelector('[data-x="rest"]').disabled),
         'so the button is grey');
  await page.click('.tl-row[data-edge="s"] [data-e="s+"]');   // its START: there IS one after
  await page.waitForTimeout(150);
  assert(!await page.evaluate(() => document.querySelector('[data-x="rest"]').disabled),
         'and live again on its start, which has the last piece after it');

  console.log('e) it saves by the door `save times` has always used');
  const willSave = (await nums(0))[1];
  await page.click('[data-x="save"]');
  await page.waitForFunction(() => !document.querySelector('.tl-root'), null, {timeout: 25000});
  assert(posted.length === 1, 'one POST to __save/subtimes.json: ' + posted.length);
  const keys = posted.length ? Object.keys(posted[0]) : [];
  assert(keys.length >= 2 && keys.every(k => /-[0-9a-f]{6,}$/.test(k)),
         'keyed by subkey, as that door has always been: ' + JSON.stringify(keys));
  const onPage = await page.evaluate(() => SUBS.map(s => [s[0], s[1]]));
  assert(Math.abs(onPage[0][1] - willSave) < 0.02 && Math.abs(onPage[1][0] - willSave) < 0.02,
         'the page agrees without being rebuilt under it: '
         + JSON.stringify([onPage[0][1], onPage[1][0]]));
  const disk = await (await fetch(`${BASE}/books/english/mini-en/timings.json`)).json();
  const vals = Object.values(disk.subs).sort((a, b) => a.t0 - b.t0);
  assert(Math.abs(vals[0].t1 - willSave) < 0.02 && Math.abs(vals[1].t0 - willSave) < 0.02,
         'and so does timings.json on disk: ' + JSON.stringify([vals[0].t1, vals[1].t0]));
  eq([vals[0].src, vals[0].conf], ['manual', 1], 'written as fixed by hand');
  await page.close();


  /* ======= i) estimate the rest: by the text, or by the sound ======= */
  // The choice beside "estimate the rest", and what "by the sound" does with
  // the server's answer.  The answer is ROUTED here -- made up, its numbers
  // chosen from the question so that what the page lays can be checked to
  // the hundredth -- because what is tested is the page: one request, the
  // numbers laid after the line and none before it, a split where the answer
  // leaves a pause, the busy spell, a failure that changes nothing, a sheet
  // shut while it waits.  The real answer (lib/wavealign.py behind serve.py)
  // is asked for at the end, wherever that file imports.
  const bp = await browser.newPage({viewport: {width: 1100, height: 850}});
  bp.on('pageerror', e => errors.push('by the sound: ' + e.message));
  const asked = [];
  let answer = null;          // question -> {status, json, delay}; null asks the hub
  await bp.route('**/__clip/estimate', async r => {
    const body = JSON.parse(r.request().postData() || '{}');
    asked.push(body);
    if (!answer) return r.continue();
    const a = answer(body);
    if (a.delay) await new Promise(ok => setTimeout(ok, a.delay));
    try {
      await r.fulfill({status: a.status || 200, contentType: 'application/json',
                       body: JSON.stringify(a.json)});
    } catch (_) { /* the page may have gone meanwhile */ }
  });
  // SAVING (e, above) REBUILT THE READER, and a reader built in a temporary
  // tree climbs to lib/ by a path the hub does not serve: cardkit_harness.py
  // writes that climb as the hub's own /lib/ when it builds the book, and
  // the one the server has just rebuilt needs the same
  const relinked = new Deno.Command(PY, {args: ['-c', `
import os, sys
out = sys.argv[1]
climb = os.path.relpath(os.getcwd(), out).replace(os.sep, "/") + "/"
for name in os.listdir(out):
    if name.endswith(".html"):
        p = os.path.join(out, name)
        text = open(p, encoding="utf-8").read()
        open(p, "w", encoding="utf-8").write(text.replace(climb, "/"))
`, `${TMP}/root/books/english/mini-en/reader`]}).outputSync();
  if (relinked.code) throw new Error(new TextDecoder().decode(relinked.stderr));
  await bp.goto(`${BASE}/books/english/mini-en/reader/`);
  await bp.waitForFunction(() => typeof SUBS !== 'undefined' && document.querySelector('.sub'));
  const byEar = async () => {
    const listed = await bp.evaluate(() => {
      const l = document.querySelector('#nlist');
      return !!l && !l.hidden && !!l.offsetParent;
    });
    if (!listed) {
      await bp.click('#narr');
      await bp.waitForSelector('#nlist:not([hidden])');
    }
    await bp.click('#nlist .nitem [data-x="byear"]');
    await bp.waitForSelector('.tl-root');
    await bp.waitForFunction(() => document.querySelectorAll('.tl-band').length > 0);
    await bp.click('[data-x="all"]');
  };
  const shut = async () => {
    await bp.keyboard.press('Escape');
    await bp.waitForFunction(() => !document.querySelector('.tl-root'));
  };
  // a made-up answer in the server's shape: the first piece to 30% of the
  // stretch, a pause the sound left, the second from 40% to 65%, the third
  // joined to it and ending short of the end -- a trailing silence
  const made = body => {
    const S = body.start, E = body.end, at = f => S + (E - S) * f;
    return {ok: true, method: 'wavealign', confidence: 0.7, anchored: 1, boundaries: 2, words: 12,
            pieces: [{t0: S, t1: at(0.3), confidence: 1, t0_min: S, t0_max: S},
                     {t0: at(0.4), t1: at(0.65), confidence: 0.8, t0_min: at(0.38), t0_max: at(0.42)},
                     {t0: at(0.65), t1: at(0.95), confidence: 0.4, t0_min: at(0.6), t0_max: at(0.7)}]};
  };

  // SIX PIECES WHOSE EVERY NUMBER IS KNOWN, on a sheet opened straight from
  // the page's own ParsehTimeline: the stretch the box picks can then be
  // checked to the hundredth on both kinds (a book's two numbers a piece, a
  // video's one) and both ways.  Their texts have 4, 8, 4, 12, 2 and 12
  // letters -- all that by the text looks at -- and the estimate is answered
  // in the page, in the server's shape, by what it was asked: 'even' shares
  // the stretch out equally and ends at its end, 'tail' leaves the last 20%
  // of it to nobody (the pause the sound showed), 'over' ends the last piece
  // past the end, which no server does.  With the line at the START of the
  // second piece (3 s) the cuts after it are 6, 8, 12, 13 and the end, 20.
  const SIX = {texts: ['zero', 'aaaaaaaa', 'bbbb', 'cccccccccccc', 'dd', 'eeeeeeeeeeee'],
               t0: [0.5, 3, 6, 8, 12, 13], t1: [3, 6, 8, 12, 13, 20], dur: 20};
  // (`set` puts other pieces in their place: the same shape as SIX)
  const sixSheet = async (pg, o) => {
    await pg.evaluate(o => {
      try { localStorage.setItem('tl_estimate_by', o.by); } catch (_) {}
      window.__asked = []; window.__saved = 0;
      const S6 = o.six;
      const marks = S6.texts.map((t, i) => ({key: 'k' + i, label: 'p' + i, text: t, t0: S6.t0[i],
                                             t1: o.kind === 'point' ? null : S6.t1[i]}));
      const draw = (a, b, n) => Promise.resolve({ok: true, peaks: new Array(n).fill(0.4), start: a, end: b});
      const answer = req => {
        const S = req.start, E = req.end, n = req.texts.length;
        const T = o.shape === 'tail' ? S + (E - S) * 0.8 : E;
        const at = k => S + (T - S) * k / n;
        return {ok: true, method: 'wavealign', confidence: 0.5, anchored: 1, boundaries: n - 1,
                words: n, pieces: req.texts.map((_, k) => ({t0: at(k),
                  t1: o.shape === 'over' && k === n - 1 ? E + 0.7 : at(k + 1), confidence: 0.5}))};
      };
      ParsehTimeline.open({title: 'six pieces', kind: o.kind, duration: S6.dur, marks: marks, peaks: draw,
        estimate: o.estimate === false ? undefined : req => {
          window.__asked.push(req);
          return new Promise(ok => setTimeout(() => ok(answer(req)), o.delay || 0));
        },
        save: () => { window.__saved++; return Promise.resolve(); },
        play: () => {}, stop: () => {}, now: () => null});
    }, {...o, six: o.set || SIX});
    await pg.waitForSelector('.tl-root');
    await pg.waitForFunction(() => document.querySelector('.tl-strip.tl-drawn'));
    await pg.click('[data-x="all"]');
  };
  // the box, filled the way a hand does; false when there is no box to fill --
  // and then every later touch of it is refused at once, so that a sheet
  // without one fails these checks one by one instead of waiting on each
  let boxGone = false;
  const boxIn = async (pg, v) => {
    if (boxGone) return false;
    const ok = await pg.fill('.tl-nx-in', v, {timeout: 3000}).then(() => true, () => false);
    if (!ok) boxGone = true;
    return ok;
  };
  const boxDo = async (pg, key) => {                 // a key pressed in the box; a click when key is null
    if (boxGone) return;
    await (key ? pg.press('.tl-nx-in', key, {timeout: 3000}) : pg.click('.tl-nx-in', {timeout: 3000}))
      .catch(() => { boxGone = true; });
  };
  const boxOf = (pg, what) => pg.evaluate(w => {     // what the box holds or says: null with no box
    const b = document.querySelector('.tl-nx-in');
    if (!b) return null;
    return w === 'value' ? b.value : w === 'readOnly' ? b.readOnly : w === 'focused' ? document.activeElement === b
         : b.getAttribute(w);
  }, what);
  const restLabel = pg => pg.evaluate(() => document.querySelector('[data-x="rest"]').textContent);
  // ONE ESTIMATE OVER THE SIX: the sheet opened, the piece taken up (its END
  // in hand when `edge` is 'e'), the number typed and taken with Enter --
  // which gives the sheet its keys back -- and E pressed.  What comes back is
  // the button's own words, the questions the server was asked, the numbers
  // on the strip and the status line.
  const runStretch = async (pg, o) => {
    await sixSheet(pg, o);
    // a piece too narrow to click on, under its own two lines, is taken up with the key
    if (o.keys) for (let i = 0; i < (o.sel || 1); i++) await pg.keyboard.press('.');
    else await pg.click(`.tl-band[data-i="${o.sel || 1}"]`);
    if (o.edge === 'e') {                              // nudged away and back
      await pg.click('.tl-row[data-edge="e"] [data-e="e+1"]');
      await pg.click('.tl-row[data-edge="e"] [data-e="e-1"]');
    }
    const was = await linesOf(pg);
    if (o.n != null) {
      await boxIn(pg, String(o.n));
      await boxDo(pg, 'Enter');
    }
    const label = await restLabel(pg);
    if (o.via === 'click') await pg.click('[data-x="rest"]');
    else await pg.keyboard.press('e');
    if (o.by === 'sound' && o.estimate !== false) await settled(pg, 15000);
    else await pg.waitForTimeout(200);
    const after = {label: await restLabel(pg), readOnly: await boxOf(pg, 'readOnly')};
    return {was, label, after, lines: await linesOf(pg), status: await statOf(pg),
            asked: await pg.evaluate(() => window.__asked || []),
            saved: await pg.evaluate(() => window.__saved)};
  };

  console.log('i) "estimate the rest" goes by the text, or by the sound');
  await byEar();
  const look = await bp.evaluate(() => {
    const t = document.querySelector('[data-x="by-text"]');
    const s = document.querySelector('[data-x="by-sound"]');
    const rest = document.querySelector('[data-x="rest"]');
    // on the screen, and the thing a finger lands on at its middle
    const seen = b => {
      const r = b.getBoundingClientRect();
      const hit = document.elementFromPoint((r.left + r.right) / 2, (r.top + r.bottom) / 2);
      return r.width > 0 && r.height > 0 && r.top >= 0 && r.bottom <= innerHeight
        && r.left >= 0 && r.right <= innerWidth && (hit === b || b.contains(hit));
    };
    return {words: t && s ? [t.textContent, s.textContent] : null,
            together: !!t && !!rest.closest('.tl-est') && t.closest('.tl-est') === rest.closest('.tl-est'),
            group: t && t.parentElement.getAttribute('role'),
            seen: !!t && seen(t) && seen(s) && seen(rest),
            pressed: t && [t.getAttribute('aria-pressed'), s.getAttribute('aria-pressed')]};
  });
  eq(look.words, ['by the text', 'by the sound'], 'the two ways are there, in words');
  assert(look.together && look.group === 'group', 'beside "estimate the rest", as one switch');
  assert(look.seen, 'and on the screen, where a hand can press them');
  eq(look.pressed, ['true', 'false'], 'by the text is the one in force until the other is chosen');
  assert(await soundLive(bp), 'by the sound is live on a book whose sound the server draws');
  assert(/picture of the sound/.test(await bp.evaluate(() =>
           document.querySelector('[data-x="by-sound"]').title)),
         'and its button says what it does');
  assert(await bp.evaluate(() => /by the text or by the sound/.test(
           document.querySelector('.tl-hint').textContent)),
         'the hint says E goes whichever way is pressed');

  console.log('   the choice is kept on this device');
  await bp.click('[data-x="by-sound"]');
  eq(await pressedOn(bp), ['false', 'true'], 'pressed, by the sound is the one in force');
  const restSays = await bp.evaluate(() => document.querySelector('[data-x="rest"]').title);
  assert(/from the picture of the sound/.test(restSays) && /\(E\)/.test(restSays),
         '"estimate the rest" says which way it goes now, and its key');
  eq(await bp.evaluate(() => localStorage.getItem('tl_estimate_by')), 'sound', 'kept on this device');
  await shut();
  await byEar();
  assert(await soundLive(bp), 'by the sound is live again on the sheet opened again');
  eq(await pressedOn(bp), ['false', 'true'], 'and it is still the one chosen');

  console.log('   E by the sound: one question, and the answer laid after the line');
  const was = await linesOf(bp);
  await bp.click('.tl-band[data-i="1"]');          // its START is the line in hand
  assert(await bp.evaluate(() => !!document.querySelector('.tl-row.tl-on[data-edge="s"]')),
         'the line in hand is the start of the second piece');
  let laid = null;
  answer = body => { laid = made(body); return {json: laid}; };
  const n0 = asked.length;
  await bp.keyboard.press('e');
  assert(await settled(bp, 15000), 'the sheet says it is done');
  const got = await linesOf(bp);
  eq(asked.length - n0, 1, 'one request to __clip/estimate');
  const q = asked[asked.length - 1] || {};
  eq([q.narration, q.kind, (q.texts || []).length], ['n1', 'span', 3],
     'asked about this recording, as a book (two numbers a piece), with the three pieces after the line');
  assert((q.texts || []).every(t => typeof t === 'string' && t.trim().length > 3),
         'each piece sent with its words');
  assert(Math.abs(q.start - was.t0[1]) < 0.006 && Math.abs(q.end - was.t1[3]) < 0.006,
         'over the stretch from the line to the last end: ' + JSON.stringify([q.start, q.end]));
  eq([got.t0[0], got.t1[0]], [was.t0[0], was.t1[0]], 'not one number of the piece before the line moved');
  eq(got.t0[1], was.t0[1], 'and the piece at the line keeps its start');
  if (laid) {
    const p = laid.pieces;
    eq([got.t1[1], got.t0[2], got.t1[2], got.t0[3], got.t1[3]],
       [r2(p[0].t1), r2(p[1].t0), r2(p[1].t1), r2(p[2].t0), r2(p[2].t1)],
       'every number after it is the answer\'s, to the hundredth');
  }
  eq(got.gaps, 1, 'the pause the answer left between two pieces is drawn, said by neither');
  assert(got.t1[1] < got.t0[2] && got.t1[2] === got.t0[3],
         'split there, and joined where the answer joins them');
  const told = await statOf(bp);
  eq(told, {text: '3 pieces after this estimated from the sound — 1 of the 2 boundaries sits '
                  + 'in a pause it heard; nothing to the left of it moved', bad: false},
     'the status says what it did, and what it heard');
  assert(await bp.evaluate(() => /\(\d+\)/.test(document.querySelector('[data-x="save"]').textContent)),
         'and nothing is saved until "save the timings"');
  await shut();

  console.log('   while the sound is being read, the sheet holds still');
  await byEar();
  await soundLive(bp);
  const still = await linesOf(bp);
  await bp.click('.tl-band[data-i="1"]');
  answer = body => ({delay: 1500, json: made(body)});
  const n1 = asked.length;
  await bp.keyboard.press('e');
  await bp.waitForTimeout(250);
  const busy = await bp.evaluate(() => ({
    said: document.querySelector('.tl-stat').textContent,
    off: ['by-text', 'by-sound', 'quiet', 'split', 'save'].map(x =>
      document.querySelector(`[data-x="${x}"]`).disabled),
    stop: (b => [b.disabled, b.textContent])(document.querySelector('[data-x="rest"]')),
    steps: [...document.querySelectorAll('.tl-step')].every(b => b.disabled),
    boxes: [...document.querySelectorAll('.tl-at')].every(b => b.readOnly)}));
  eq(busy.said, 'estimating from the sound…', 'it says it is listening');
  eq(busy.off, [true, true, true, true, true], 'the choice, quiet, split and save are grey');
  eq(busy.stop, [false, 'stop estimating'], 'and "estimate the rest" is the way to stop it');
  assert(busy.steps && busy.boxes, 'and so are the steps and the time boxes');
  await bp.keyboard.press('ArrowRight');           // a nudge meanwhile moves nothing
  await bp.keyboard.press('e');                    // and E again asks nothing more
  const mid = await linesOf(bp);
  eq([mid.t0, mid.t1], [still.t0, still.t1], 'an arrow pressed while waiting moved nothing');
  assert(await settled(bp, 15000), 'the answer comes');
  eq(asked.length - n1, 1, 'and it was asked for once, however often E was pressed');
  const heldAfter = await linesOf(bp);
  eq([heldAfter.t0[0], heldAfter.t1[0], heldAfter.t0[1]], [still.t0[0], still.t1[0], still.t0[1]],
     'laid after the line, as before');
  assert(!await bp.evaluate(() => document.querySelector('[data-x="by-text"]').disabled),
         'and the sheet is live again');
  await shut();

  console.log('   a failure changes nothing, and says the server\'s own words');
  await byEar();
  await soundLive(bp);
  const firm = await linesOf(bp);
  await bp.click('.tl-band[data-i="1"]');
  const refusal = 'there is no picture of the sound to estimate from: ffmpeg, which reads the '
    + 'recording, is not installed on this computer';
  answer = () => ({status: 409, json: {ok: false, error: refusal}});
  await bp.keyboard.press('e');
  assert(await settled(bp, 15000), 'the sheet says it is done');
  eq(await statOf(bp), {text: refusal, bad: true}, 'the refusal is said in its own words, as a fault');
  const left = await linesOf(bp);
  eq([left.t0, left.t1, left.gaps], [firm.t0, firm.t1, firm.gaps], 'and not one number moved');
  assert(await bp.evaluate(() => document.querySelector('[data-x="save"]').disabled),
         'so there is nothing to save');
  assert(!await bp.evaluate(() => document.querySelector('[data-x="rest"]').disabled),
         'and it may be asked again');
  await shut();

  console.log('   the wait can be given up, and what the hand moved stays');
  // An hour of sound is read for a minute or two, and until the answer
  // comes the sheet holds still, save and all.  Escape and the button
  // itself give the wait up -- the sheet stays, with every change the hand
  // made, and the answer, when it comes, is dropped.
  await byEar();
  await soundLive(bp);
  await bp.click('.tl-band[data-i="0"]');
  await bp.click('.tl-row[data-edge="e"] [data-e="e+"]');   // a change by hand, not saved
  const handMoved = await linesOf(bp);
  await bp.click('.tl-band[data-i="1"]');
  answer = body => ({delay: 1500, json: made(body)});
  const n5 = asked.length;
  await bp.keyboard.press('e');
  await bp.waitForTimeout(250);
  const stopper = await bp.evaluate(() => {
    const b = document.querySelector('[data-x="rest"]');
    return {off: b.disabled, words: b.textContent, why: b.title};
  });
  assert(!stopper.off && stopper.words === 'stop estimating' && /Escape/.test(stopper.why),
         'while it waits, the button is a stop, and says Escape is one too: ' + JSON.stringify(stopper));
  await bp.keyboard.press('Escape');
  eq(await statOf(bp), {text: 'stopped: nothing was estimated, and nothing moved', bad: false},
     'Escape gives the wait up, and says so');
  assert(await bp.evaluate(() => !!document.querySelector('.tl-root')), 'and the sheet stays open');
  assert(!await bp.evaluate(() => document.querySelector('[data-x="by-text"]').disabled),
         'live again at once');
  eq(await bp.evaluate(() => document.querySelector('[data-x="rest"]').textContent), 'estimate the rest',
     'the button is itself again');
  await bp.waitForTimeout(1800);                   // the answer comes, to a question given up
  const keptHand = await linesOf(bp);
  eq([keptHand.t0, keptHand.t1], [handMoved.t0, handMoved.t1],
     'nothing was laid, and the change made by hand is still there');
  assert(await bp.evaluate(() => {
    const b = document.querySelector('[data-x="save"]');
    return !b.disabled && /\(\d+\)/.test(b.textContent);
  }), 'still there to be saved');
  await bp.keyboard.press('e');
  await bp.waitForTimeout(250);
  await bp.click('[data-x="rest"]');
  eq((await statOf(bp)).text, 'stopped: nothing was estimated, and nothing moved',
     'and the button gives it up just the same');
  await bp.waitForTimeout(1800);
  eq(asked.length - n5, 2, 'each question had gone out once');
  const keptHand2 = await linesOf(bp);
  eq([keptHand2.t0, keptHand2.t1], [handMoved.t0, handMoved.t1], 'and its late answer laid nothing either');
  await shut();

  console.log('   the end of a split boundary in hand: the stretch starts at that end');
  // By the text lays the rest from the line in hand, whichever edge it is;
  // with the END of a split boundary in hand, the next piece's start moves
  // to it.  By the sound must ask from there too -- not from the next
  // piece's old start, which would leave the sound between them to nobody.
  const even = body => {
    const S = body.start, E = body.end, n = body.texts.length, at = k => S + (E - S) * k / n;
    return {ok: true, method: 'wavealign', confidence: 0.5, anchored: 0, boundaries: n - 1,
            words: n, pieces: body.texts.map((_, k) => ({t0: at(k), t1: at(k + 1),
                                                          confidence: k ? 0.5 : 1,
                                                          t0_min: at(k), t0_max: at(k)}))};
  };
  await byEar();
  await soundLive(bp);
  await bp.click('.tl-band[data-i="1"]');
  if (/^split/.test(await bp.evaluate(() => document.querySelector('[data-x="split"]').textContent)))
    await bp.click('[data-x="split"]');
  await bp.click('.tl-row[data-edge="e"] [data-e="e-5"]');
  const endIn = await linesOf(bp);
  assert(endIn.t1[1] < endIn.t0[2] - 0.3,
         'the end in hand stands well before the next start: ' + JSON.stringify(endIn));
  assert(await bp.evaluate(() => !!document.querySelector('.tl-row.tl-on[data-edge="e"]')),
         'and it is the end that is the line in hand');
  answer = body => ({json: even(body)});
  const n4 = asked.length;
  await bp.keyboard.press('e');
  assert(await settled(bp, 15000), 'the sheet says it is done');
  eq(asked.length - n4, 1, 'one request');
  const qe = asked[asked.length - 1] || {};
  assert(Math.abs(qe.start - endIn.t1[1]) < 0.006,
         'asked from the end in hand, not from the next piece\'s old start: '
         + JSON.stringify([qe.start, endIn.t1[1], endIn.t0[2]]));
  eq((qe.texts || []).length, 2, 'about the pieces after it');
  const afterE = await linesOf(bp);
  eq([afterE.t0[1], afterE.t1[1]], [endIn.t0[1], endIn.t1[1]], 'the piece in hand kept both its numbers');
  eq(afterE.t0[2], endIn.t1[1], 'and the next starts at the line, as by the text would start it');
  await shut();

  console.log('   a sheet shut while it waits drops the late answer');
  await byEar();
  await soundLive(bp);
  const unshut = await linesOf(bp);
  await bp.click('.tl-band[data-i="1"]');
  answer = body => ({delay: 1200, json: made(body)});
  const n2 = asked.length;
  await bp.keyboard.press('e');
  await bp.waitForTimeout(200);
  // (Escape now gives the wait up: leaving is the ✕)
  await bp.click('[data-x="cancel"]');
  await bp.waitForFunction(() => !document.querySelector('.tl-root'));
  await bp.waitForTimeout(1800);                   // the answer has come, to nobody
  eq(asked.length - n2, 1, 'the question had gone out');
  assert(!await bp.evaluate(() => !!document.querySelector('.tl-root')),
         'and its answer opened nothing');
  await byEar();
  const reopened = await linesOf(bp);
  eq([reopened.t0, reopened.t1], [unshut.t0, unshut.t1], 'and laid nothing anywhere');
  await shut();

  console.log('   where it cannot go by the sound, it says why, and goes by the text');
  // three sheets opened straight from the page's own ParsehTimeline, each
  // with what one kind of caller gives: a reader built before this (no
  // estimate), a machine with no picture to be had (peaks answer nothing),
  // and a video not drawn yet, which then is
  const sheetFor = async opts => {
    await bp.evaluate(o => {
      const marks = [{key: 'a', label: '1', text: 'One two three.', t0: 0.5, t1: 3},
                     {key: 'b', label: '2', text: 'Four five.', t0: 3, t1: 6},
                     {key: 'c', label: '3', text: 'Six.', t0: 6, t1: 9}];
      window.__drawn = false;
      const draw = (a, b, n) => Promise.resolve({ok: true, peaks: new Array(n).fill(0.4), start: a, end: b});
      ParsehTimeline.open({
        title: o.title, kind: o.kind, duration: 10, marks: marks,
        peaks: o.peaks === 'drawn' ? draw
             : o.peaks === 'none' ? () => Promise.resolve(null)
             : (a, b, n) => window.__drawn ? draw(a, b, n) : Promise.resolve(null),
        estimate: o.estimate ? req => Promise.resolve({ok: true, anchored: 0, boundaries: req.texts.length - 1,
          pieces: req.texts.map((_, k) => ({t0: req.start + k, t1: req.start + k + 1}))}) : undefined,
        wave: o.wave ? {why: '', run: () => { window.__drawn = true;
                                              return Promise.resolve({rate: 20, peaks: [0.4, 0.4]}); }}
                     : null,
        play: () => {}, stop: () => {}, now: () => null});
    }, opts);
    await bp.waitForSelector('.tl-root');
    await bp.waitForFunction(() => document.querySelector('.tl-strip.tl-drawn, .tl-strip.tl-plain'));
    await bp.waitForTimeout(100);
    return bp.evaluate(() => {
      const s = document.querySelector('[data-x="by-sound"]');
      return {off: s.disabled, why: s.title,
              pressed: ['by-text', 'by-sound'].map(x =>
                document.querySelector(`[data-x="${x}"]`).getAttribute('aria-pressed'))};
    });
  };
  const old = await sheetFor({title: 'a reader built before this', kind: 'span', peaks: 'drawn'});
  assert(old.off && /rebuild the reader/.test(old.why),
         'a reader built before this: grey, and the rebuild that brings it is named -- ' + old.why);
  eq(old.pressed, ['true', 'false'],
     'by the text is shown in force meanwhile, though by the sound is the one kept');
  await bp.click('.tl-band[data-i="0"]');
  await bp.click('.tl-row[data-edge="e"] [data-e="e+"]');
  await bp.click('.tl-row[data-edge="e"] [data-e="e-"]');
  await bp.keyboard.press('e');
  assert(/estimated afresh by the text/.test((await statOf(bp)).text), 'and E goes by the text');
  eq(await bp.evaluate(() => localStorage.getItem('tl_estimate_by')), 'sound',
     'without forgetting the choice kept');
  await shut();
  const bare = await sheetFor({title: 'no ffmpeg', kind: 'span', peaks: 'none', estimate: true});
  assert(bare.off && /no picture of the sound here/.test(bare.why) && /ffmpeg/.test(bare.why),
         'no picture to be had: grey, and says what draws one -- ' + bare.why);
  await shut();
  const undrawn = await sheetFor({title: 'not drawn yet', kind: 'point', peaks: 'later',
                              estimate: true, wave: true});
  assert(undrawn.off && /draw the sound first/.test(undrawn.why),
         'a video not drawn yet: grey, and says to draw the sound first -- ' + undrawn.why);
  eq(undrawn.pressed, ['true', 'false'], 'by the text in force until then');
  await bp.click('[data-x="wave"]');
  assert(await soundLive(bp, 5000), 'drawn, by the sound is live at once');
  eq(await pressedOn(bp), ['false', 'true'], 'and the choice kept is back in force');
  await shut();

  console.log('   "all" before the first picture, on a recording longer than one picture may be');
  // THE SERVER DRAWS AT MOST FIVE MINUTES AT A TIME (clips.MAX_SECONDS), so
  // "all" over a longer narration is refused on a computer whose ffmpeg
  // draws every shorter window.  Pressed before the strip's first picture
  // had come, that refusal once read as "no picture of the sound here":
  // by the sound went grey blaming ffmpeg, and E went by the text.  Here
  // the limit is scaled to this eight-second recording -- a window longer
  // than seven seconds is refused as the server refuses one over three
  // hundred -- and every picture is held back a little, so that "all" is
  // surely pressed before the first one has come.  Then the same door
  // refusing everything, which is what a computer without ffmpeg does.
  const LIMIT = 7;
  let peaksRule = null;     // null: the hub answers; 'limit' or 'none': refused here
  const peaksAsked = [];
  await bp.route('**/__clip/peaks', async r => {
    if (!peaksRule) return r.continue();
    const body = JSON.parse(r.request().postData() || '{}');
    const refused = peaksRule === 'none' || !(body.end - body.start <= LIMIT);
    peaksAsked.push({start: body.start, end: body.end, refused});
    await new Promise(ok => setTimeout(ok, 400));
    try {
      if (!refused) await r.continue();
      else if (peaksRule === 'none')
        await r.fulfill({status: 409, contentType: 'application/json',
                         body: JSON.stringify({ok: false, error: 'ffmpeg is not installed', record: true})});
      else
        await r.fulfill({status: 400, contentType: 'application/json',
                         body: JSON.stringify({ok: false, error: `a clip is at most ${LIMIT} seconds long`})});
    } catch (_) { /* the sheet may have gone meanwhile */ }
  });
  const soundState = () => bp.evaluate(() => {
    const s = document.querySelector('[data-x="by-sound"]');
    return {off: s.disabled, why: s.title,
            plain: !!document.querySelector('.tl-strip.tl-plain'),
            pressed: ['by-text', 'by-sound'].map(x =>
              document.querySelector(`[data-x="${x}"]`).getAttribute('aria-pressed'))};
  });
  peaksRule = 'limit';
  await byEar();                                   // "all" the moment the blocks are there
  assert(!await bp.evaluate(() => !!document.querySelector('.tl-strip.tl-drawn')),
         'no picture had come when "all" was pressed');
  const liveAfterAll = await soundLive(bp);
  await bp.waitForTimeout(800);                    // and nothing still on its way takes it back
  const afterAll = await soundState();
  const allRefused = peaksAsked.findIndex(p => p.refused && p.start === 0 && p.end >= 7.9);
  assert(allRefused >= 0, 'the picture of all of it was refused, as the server refuses more '
         + 'than five minutes: ' + JSON.stringify(peaksAsked));
  assert(afterAll.plain, 'so the strip over all of it has no picture');
  assert(liveAfterAll && !afterAll.off,
         'yet by the sound stays live: the sound can be drawn here, just not all at once -- '
         + JSON.stringify(afterAll));
  assert(!/ffmpeg/.test(afterAll.why) && /picture of the sound/.test(afterAll.why),
         'and its button says what it does, blaming nothing: ' + afterAll.why);
  eq(afterAll.pressed, ['false', 'true'], 'the choice kept is the one in force');
  eq(peaksAsked.slice(allRefused + 1).map(p => [p.refused, +(p.end - p.start).toFixed(2) <= 2]),
     [[false, true]], 'it asked once more, for a short stretch, and was drawn one');
  await bp.click('.tl-band[data-i="1"]');          // in view already: nothing more is asked
  answer = body => ({json: made(body)});
  const n6 = asked.length;
  await bp.keyboard.press('e');
  assert(await settled(bp, 15000), 'E goes by the sound: ' + JSON.stringify(await statOf(bp)));
  eq(asked.length - n6, 1, 'one request to __clip/estimate');
  await shut();

  peaksRule = 'none';
  peaksAsked.length = 0;
  await byEar();
  const noneWhy = await bp.waitForFunction(() =>
    /ffmpeg/.test(document.querySelector('[data-x="by-sound"]').title), null, {timeout: 15000})
    .then(() => true, () => false);
  await bp.waitForTimeout(800);
  const noFF = await soundState();
  assert(peaksAsked.length > 0 && peaksAsked.every(p => p.refused),
         'with every picture refused, as a computer without ffmpeg refuses it: ' + peaksAsked.length);
  assert(noneWhy && noFF.off && /no picture of the sound here/.test(noFF.why) && /ffmpeg/.test(noFF.why),
         'by the sound is grey, and says what draws one -- ' + noFF.why);
  eq(noFF.pressed, ['true', 'false'], 'by the text is shown in force');
  await bp.click('.tl-band[data-i="1"]');
  const n7 = asked.length;
  await bp.keyboard.press('e');
  await bp.waitForTimeout(400);
  assert(/estimated afresh by the text/.test((await statOf(bp)).text),
         'and E goes by the text: ' + (await statOf(bp)).text);
  eq(asked.length - n7, 0, 'asking the server nothing');
  await shut();
  peaksRule = null;
  await bp.unroute('**/__clip/peaks');

  /* ---- the next N seconds: a stretch of the rest, by the same two ways ---- */
  // THE OWNER'S WORDS (2026-09-25): a box for a number of seconds beside
  // "estimate the rest" and its switch; filled, the button reads "estimate
  // the next <N> seconds" and does the same act over a shorter stretch --
  // from the line in hand to the existing boundary closest to <N> seconds
  // after it, which stays where it is.  The algorithms are the same two, and
  // nothing outside the stretch moves.  The number is NOT kept: every sheet
  // opens on "estimate the rest".
  console.log('i) estimate the next N seconds: the box, beside "estimate the rest" and its switch');
  answer = null;
  await byEar();
  const nx = await bp.evaluate(() => {
    const b = document.querySelector('.tl-nx-in');
    if (!b) return null;
    const rest = document.querySelector('[data-x="rest"]'), by = document.querySelector('[data-x="by-text"]');
    const r = b.getBoundingClientRect();
    const hit = document.elementFromPoint((r.left + r.right) / 2, (r.top + r.bottom) / 2);
    return {group: b.closest('.tl-est') === rest.closest('.tl-est') && b.closest('.tl-est') === by.closest('.tl-est'),
            empty: b.value === '', label: rest.textContent, words: b.getAttribute('aria-label') || '',
            seen: r.width > 0 && r.height > 0 && r.top >= 0 && r.bottom <= innerHeight
              && r.left >= 0 && r.right <= innerWidth && hit === b};
  }) || {};
  assert(nx.group, 'the box is in the same group as "estimate the rest" and its switch');
  assert(nx.seen, 'and on the screen, where a hand can type in it');
  assert(nx.empty && nx.label === 'estimate the rest',
         'empty, the button says "estimate the rest", as ever: ' + JSON.stringify(nx.label));
  assert(/seconds/.test(nx.words), 'and the box says in words what it wants: ' + JSON.stringify(nx.words));
  const keysBefore = await bp.evaluate(() => JSON.stringify(Object.keys(localStorage).sort()));

  console.log('   the button says what it will do, in the number as typed');
  for (const [typed, want] of [['30', 'estimate the next 30 seconds'], ['1', 'estimate the next 1 second'],
      ['1.0', 'estimate the next 1 second'], ['1:30', 'estimate the next 90 seconds'],
      ['1,5', 'estimate the next 1.5 seconds'], ['0.25', 'estimate the next 0.25 seconds'],
      ['0.005', 'estimate the next 0.01 seconds'],
      ['', 'estimate the rest']]) {
    await boxIn(bp, typed);
    eq(await restLabel(bp), want, `${JSON.stringify(typed)} in the box`);
  }
  await boxIn(bp, '30');
  const nxTitle = await bp.evaluate(() => document.querySelector('[data-x="rest"]').title);
  assert(/in the next 30 seconds/.test(nxTitle) && /boundary closest/.test(nxTitle)
           && /Nothing outside that stretch/.test(nxTitle) && /\(E\)/.test(nxTitle),
         'its title says what it does, and its key: ' + nxTitle);
  assert(await bp.evaluate(() => /in the next 30 seconds, up to the boundary closest to them/
           .test(document.querySelector('.tl-hint').textContent)
           && /by the text or by the sound/.test(document.querySelector('.tl-hint').textContent)),
         'and so does the hint under the strip, which still says E goes whichever way is pressed');
  eq(await bp.evaluate(() => JSON.stringify(Object.keys(localStorage).sort())), keysBefore,
     'the number is written nowhere: this device keeps nothing new');
  for (const [typed, button] of [['30', 'estimate the next 30 seconds'], ['', 'estimate the rest']]) {
    await boxIn(bp, typed);
    await bp.click('[data-x="by-text"]');
    eq((await statOf(bp)).text, `\u201c${button}\u201d now goes by the text`,
       `pressing the switch names the button as it reads: ${JSON.stringify(button)}`);
    await bp.click('[data-x="by-sound"]');
    eq((await statOf(bp)).text, `\u201c${button}\u201d now goes by the sound`, 'and the other way');
  }
  console.log('   what is not a number of seconds is refused in words, and nothing is estimated');
  const REFUSE_BAD = 'the box must hold seconds (90 or 1:30) or be empty; nothing was estimated';
  const REFUSE_ZERO = 'the seconds in the box must be above zero, or the box empty; nothing was estimated';
  await soundLive(bp);
  await bp.click('.tl-band[data-i="1"]');
  const refusedFrom = await linesOf(bp);
  const nAsk = asked.length;
  for (const [typed, words] of [['abc', REFUSE_BAD], ['30 s', REFUSE_BAD], ['-3', REFUSE_BAD],
                                ['1:2:3:4', REFUSE_BAD], ['0', REFUSE_ZERO], ['0.00', REFUSE_ZERO],
                                ['0.004', REFUSE_ZERO]]) {
    await boxIn(bp, typed);
    await boxDo(bp, 'Enter');
    eq(await restLabel(bp), 'estimate the rest', `${JSON.stringify(typed)}: the button stays "estimate the rest"`);
    assert(await boxOf(bp, 'aria-invalid') === 'true',
           `${JSON.stringify(typed)}: and the box says it is not a number`);
    await bp.keyboard.press('e');
    await bp.waitForTimeout(150);
    eq(await statOf(bp), {text: words, bad: true}, `${JSON.stringify(typed)}: E is refused in words`);
    const still = await linesOf(bp);
    eq([still.t0, still.t1], [refusedFrom.t0, refusedFrom.t1], `${JSON.stringify(typed)}: and not one number moved`);
  }
  await bp.click('[data-x="rest"]');
  await bp.waitForTimeout(150);
  eq(asked.length - nAsk, 0, 'the button is refused the same: no question went to the server');
  await boxIn(bp, '');
  assert([null, 'false'].includes(await boxOf(bp, 'aria-invalid')) && !boxGone,
         'emptied, the box is no longer called wrong');
  await shut();

  console.log('   the keys typed in the box are the box\'s: the sheet is not stepped or saved from it');
  await sixSheet(bp, {kind: 'span', by: 'text'});
  await bp.click('.tl-band[data-i="1"]');
  const inHand = () => bp.evaluate(() => document.querySelector('.tl-now .tl-say').textContent.slice(0, 2));
  eq(await inHand(), 'p1', 'the second piece is in hand');
  await boxDo(bp, null);
  await bp.keyboard.type('1.5,');
  eq([await inHand(), await boxOf(bp, 'value')], ['p1', '1.5,'],
     'a full stop and a comma typed in the box do not take up the next piece');
  await boxIn(bp, '5');
  await bp.keyboard.press('Enter');
  assert(!boxGone && await boxOf(bp, 'focused') === false,
         'Enter takes the number, and the keys are the sheet\'s again');
  await bp.keyboard.press('e');
  await bp.waitForTimeout(200);
  assert(await bp.evaluate(() => /\(\d+\)/.test(document.querySelector('[data-x="save"]').textContent)),
         'E has moved something, so there is something to save');
  await boxDo(bp, null);
  await bp.keyboard.press('Enter');
  eq([await bp.evaluate(() => window.__saved), await bp.evaluate(() => !!document.querySelector('.tl-root'))],
     [0, true], 'and Enter in the box saves nothing and leaves nothing: it only takes the number');
  // the key held down on: Enter has just handed the focus to the sheet, where Enter saves --
  // and a repeat of it must not
  await boxDo(bp, null);
  await bp.keyboard.down('Enter');
  await bp.keyboard.down('Enter');
  await bp.keyboard.up('Enter');
  eq([await bp.evaluate(() => window.__saved), await bp.evaluate(() => !!document.querySelector('.tl-root'))],
     [0, true], 'a held Enter in the box saves nothing either: the repeat of it lands on the sheet, and is not a save');
  await shut();

  console.log('   a sheet with nothing to time: E says so as it always did, and nothing throws');
  await bp.evaluate(() => {
    try { localStorage.setItem('tl_estimate_by', 'text'); } catch (_) {}
    ParsehTimeline.open({title: 'nothing', kind: 'span', duration: 5, marks: [],
      peaks: () => Promise.resolve(null), play: () => {}, stop: () => {}, now: () => null});
  });
  await bp.waitForSelector('.tl-root');
  await bp.keyboard.press('e');
  await bp.waitForTimeout(150);
  eq(await statOf(bp), {text: 'there is nothing after this one to estimate', bad: true}, 'E on an empty sheet');
  await shut();

  console.log('   the stretch: from the line to the cut closest to it, on either side, a tie to the earlier');
  // the line at 3 s; the cuts after it are the starts of the pieces (6, 8,
  // 12 and 13) and the end of the last (20).  a + n is where the number
  // points; the cut nearest it is where the stretch ends, and the pieces
  // asked about are the ones between.
  const ROUNDS = [[4, 6, 'a tie (6 and 8 are as far from 7): the earlier'], [5, 8, 'exactly on a cut'],
    [5.4, 8, 'between two, the nearer below'], [7, 8, 'a tie again (8 and 12 from 10)'],
    [7.1, 12, 'a hair past the middle: the nearer cut, though beyond it'],
    [8.5, 12, 'beyond, and nearer than the last cut not beyond it'],
    [1, 6, 'shorter than the first piece: still one piece'], [0.5, 6, 'so is half a second'],
    [10, 13, 'on a cut, the one before the end'],
    [16, 20, 'nearer the end than the last start: the whole rest'], [500, 20, 'past the end: the whole rest']];
  for (const kind of ['span', 'point']) {
    for (const [n, cut, why] of ROUNDS) {
      const r = await runStretch(bp, {kind, by: 'sound', n});
      const to = cut === 20 ? 5 : SIX.t0.indexOf(cut) - 1;
      const rq = r.asked[0] || {};
      eq([r.asked.length, rq.start, rq.end, rq.kind, rq.texts],
         [1, 3, cut, kind, SIX.texts.slice(1, to + 1)],
         `${kind}: ${n} s from 3 asks for 3 to ${cut} (${why}), about the pieces inside it only`);
    }
  }
  await shut();

  // A TIE IS A TIE IN DECIMALS, NOT IN DOUBLES: with the line at 3.9 the cuts
  // are 5.2, 6.5 and 7.8.  3.9 + 1.95 = 5.85 and 3.9 + 3.25 = 7.15 are exactly
  // between two of them, and in doubles 7.15 is nearer 7.8 than 6.5 by 1e-15:
  // a plain comparison takes the later, which here is the end and so the
  // whole rest.  The earlier is the answer, always.
  const FLT = {texts: ['zero', 'aaaaaaaa', 'bbbb', 'cccc'], t0: [0.8, 3.9, 5.2, 6.5],
               t1: [3.9, 5.2, 6.5, 7.8], dur: 8};
  for (const [n, cut, count] of [[1.95, 5.2, 1], [3.25, 6.5, 2]]) {
    const r = await runStretch(bp, {kind: 'span', by: 'sound', n, set: FLT});
    const rq = r.asked[0] || {};
    eq([rq.start, rq.end, (rq.texts || []).length], [3.9, cut, count],
       `a tie (3.9 + ${n} is halfway between two cuts) goes to the earlier cut, ${cut}`);
  }

  console.log('   a cut too near the line to hold a piece is passed over for the next');
  {
    // the second piece is 0.3 s long: 3.3 is the closest cut to 3 + 0.2, and no piece fits before it
    const SLIV = {texts: SIX.texts, t0: [0.5, 3, 3.3, 6, 12, 13], t1: [3, 3.3, 6, 12, 13, 20], dur: 20};
    for (const kind of ['span', 'point']) {
      const r = await runStretch(bp, {kind, by: 'sound', n: 0.2, set: SLIV, keys: true});
      const rq = r.asked[0] || {};
      eq([r.asked.length, rq.start, rq.end, rq.texts], [1, 3, 6, ['aaaaaaaa', 'bbbb']],
         `${kind}: 0.2 s from 3 would end at 3.3, 0.3 s on, too near to hold a piece: the next cut, 6`);
    }
    const t = await runStretch(bp, {kind: 'span', by: 'text', n: 0.2, set: SLIV, keys: true});
    eq([t.lines.t0, t.lines.t1], [[0.5, 3, 5, 6, 12, 13], [3, 5, 6, 12, 13, 20]],
       'and by the text the two pieces share 3 to 6 in proportion to their words');
  }

  console.log('   a cut exactly the floor away is decided in decimals, whichever way the doubles fall');
  for (const [a, cut] of [[42.55, 42.95], [42.6, 43]]) {
    // 42.55 + 0.4 is 42.949999999999996 in doubles, 42.6 + 0.4 is exactly 43: in both the cut is
    // 0.4 s from the line, no piece fits between, and the stretch goes on to the next
    const FLOOR = {texts: SIX.texts, t0: [0.5, a, cut, cut + 9.9, cut + 15, cut + 16],
                   t1: [a, cut, cut + 9.9, cut + 15, cut + 16, cut + 30], dur: cut + 30};
    const r = await runStretch(bp, {kind: 'span', by: 'sound', n: 2.21, set: FLOOR, keys: true});
    const rq = r.asked[0] || {};
    eq([rq.start, rq.end, rq.texts], [a, cut + 9.9, [SIX.texts[1], SIX.texts[2]]],
       `the line at ${a}: a cut at ${cut}, 0.4 s on, is passed over for the next`);
  }
  console.log('   the END of a split boundary in hand, with a number: the stretch starts at that end');
  {
    const SPLE = {texts: SIX.texts, t0: SIX.t0, t1: [3, 5, 8, 12, 13, 20], dur: 20};      // 5 | 6 pulled apart
    const r = await runStretch(bp, {kind: 'span', by: 'sound', n: 7, edge: 'e', set: SPLE, shape: 'even'});
    const rq = r.asked[0] || {};
    eq([r.was.gaps, rq.start, rq.end, rq.texts], [1, 5, 12, ['bbbb', 'cccccccccccc']],
       'from the end at 5, not the next piece\'s old start at 6, to the cut at 12');
    // (the boundary at the line itself stays flagged split, with two equal numbers, as it does at
    // every estimate that starts from the end of one: nothing outside the stretch is touched)
    eq([r.lines.t0, r.lines.t1], [[0.5, 3, 5, 8.5, 12, 13], [3, 5, 8.5, 12, 13, 20]],
       'the piece in hand keeps both its numbers, and the next starts at the line, as by the text would start it');
  }
  console.log('   no room for a piece between the line and the end: refused as before, over any number');
  {
    const NR = {texts: SIX.texts, t0: [0.5, 3, 6, 8, 12, 19.7], t1: [3, 6, 8, 12, 19.7, 20], dur: 20};
    for (const by of ['text', 'sound']) {
      const r = await runStretch(bp, {kind: 'span', by, n: 5, set: NR, sel: 5, keys: true});
      eq([r.status, r.asked.length, r.lines.t0, r.lines.t1], [{text: 'there is no room between this line and the end', bad: true}, 0, NR.t0, NR.t1],
         `by the ${by}: the last piece is 0.3 s long: no room, nothing asked, nothing moved`);
    }
  }

  console.log('   by the text, over the stretch: every number to the hundredth, nothing outside it moved');
  for (const kind of ['span', 'point']) {
    for (const [n, t0, t1, said] of [
        [5, [0.5, 3, 6.33, 8, 12, 13], [3, 6.33, 8, 12, 13, 20],
         '2 pieces in the next 5 s (to 0:08.00) estimated afresh by the text; nothing outside that stretch moved'],
        [7.1, [0.5, 3, 6, 7.5, 12, 13], [3, 6, 7.5, 12, 13, 20],
         '3 pieces in the next 9 s (to 0:12.00) estimated afresh by the text; nothing outside that stretch moved'],
        [4, SIX.t0, SIX.t1,
         'the one piece in the next 3 s (to 0:06.00) estimated afresh by the text; nothing outside that stretch moved']]) {
      const r = await runStretch(bp, {kind, by: 'text', n});
      eq([r.lines.t0, r.lines.t1, r.lines.gaps], [t0, t1, 0], `${kind}: ${n} s -> the numbers, joined`);
      eq(r.status, {text: said, bad: false}, `${kind}: and the status names the stretch as laid`);
    }
  }
  {
    const rest = await runStretch(bp, {kind: 'span', by: 'text'});
    const wide = await runStretch(bp, {kind: 'span', by: 'text', n: 16});
    eq([wide.lines.t0, wide.lines.t1], [rest.lines.t0, rest.lines.t1],
       'a number that reaches the end is exactly "estimate the rest": the same numbers');
    eq(wide.status.text, rest.status.text.replace('; nothing to the left of it moved',
         '; nothing to the left of it moved (the closest boundary to the next 16 seconds is the end, so this is the whole rest)'),
       'and the status says so');
    const via = await runStretch(bp, {kind: 'span', by: 'text', n: 5, via: 'click'});
    eq([via.lines.t0, via.lines.t1], [[0.5, 3, 6.33, 8, 12, 13], [3, 6.33, 8, 12, 13, 20]],
       'pressing the button is the same act as E');
  }
  {
    const off = await runStretch(bp, {kind: 'span', by: 'text', n: 'abc'});
    eq([off.lines.t0, off.lines.t1, off.status.bad], [off.was.t0, off.was.t1, true],
       'by the text, a box that is not a number refuses too, and moves nothing');
  }

  console.log('   by the sound, over the stretch: the answer laid inside it, the cut where it was');
  for (const kind of ['span', 'point']) {
    const even5 = await runStretch(bp, {kind, by: 'sound', n: 5, shape: 'even'});
    eq([even5.lines.t0, even5.lines.t1, even5.lines.gaps],
       [[0.5, 3, 5.5, 8, 12, 13], [3, 5.5, 8, 12, 13, 20], 0], `${kind}: the answer's numbers, to the hundredth`);
    eq(even5.after, {label: 'estimate the next 5 seconds', readOnly: false},
       `${kind}: and the sheet is live again: the button says it, and the box takes a number`);
    eq(even5.status, {text: '2 pieces in the next 5 s (to 0:08.00) estimated from the sound — the boundary '
                            + 'between them sits in a pause it heard; nothing outside that stretch moved', bad: false},
       `${kind}: and the status names the stretch, and what it heard`);
    // the last 20% of the stretch left to nobody: a book's last piece ends
    // there and the boundary at the cut is split, the next piece keeping its
    // start; a video's caption runs on until the cut
    const tail = await runStretch(bp, {kind, by: 'sound', n: 5, shape: 'tail'});
    if (kind === 'span')
      eq([tail.lines.t0, tail.lines.t1, tail.lines.gaps],
         [[0.5, 3, 5, 8, 12, 13], [3, 5, 7, 12, 13, 20], 1],
         'span: a pause left before the cut splits the boundary there; the piece after it keeps its start');
    else
      eq([tail.lines.t0, tail.lines.t1, tail.lines.gaps],
         [[0.5, 3, 5, 8, 12, 13], [3, 5, 8, 12, 13, 20], 0],
         'point: the last caption of the stretch runs until the cut, as the rest\'s runs until the end');
    const over = await runStretch(bp, {kind, by: 'sound', n: 5, shape: 'over'});
    eq([over.lines.t0, over.lines.t1, over.lines.gaps],
       [[0.5, 3, 5.5, 8, 12, 13], [3, 5.5, 8, 12, 13, 20], 0],
       `${kind}: an answer that ends past the cut is laid ending AT it, never beyond`);
    const whole = await runStretch(bp, {kind, by: 'sound', n: 500});
    const plain = await runStretch(bp, {kind, by: 'sound'});
    eq([whole.lines.t0, whole.lines.t1, whole.asked], [plain.lines.t0, plain.lines.t1, plain.asked],
       `${kind}: past the end it is "estimate the rest": the same question, the same numbers`);
    const past = await runStretch(bp, {kind, by: 'sound', n: 500, shape: 'over'});
    eq([past.lines.t0, past.lines.t1], [plain.lines.t0, plain.lines.t1],
       `${kind}: and an answer that ends past the end of the recording is laid ending AT it`);
  }
  console.log('   a boundary split beforehand: at the cut it is the stretch\'s to decide; beyond the cut it stays');
  {
    // the boundary at the cut (7.5 | 8) and the one just beyond it (11 | 12) are both pulled apart
    const SPLT = {texts: SIX.texts, t0: SIX.t0, t1: [3, 6, 7.5, 11, 13, 20], dur: 20};
    const r = await runStretch(bp, {kind: 'span', by: 'text', n: 5, set: SPLT});
    eq([r.was.t0, r.was.t1, r.was.gaps], [SIX.t0, [3, 6, 7.5, 11, 13, 20], 2],
       'two boundaries are split to begin with: the one at the cut and the one beyond it');
    eq([r.lines.t0, r.lines.t1, r.lines.gaps], [[0.5, 3, 6.33, 8, 12, 13], [3, 6.33, 8, 11, 13, 20], 1],
       'by the text the stretch ends AT the cut, joined; the split beyond it is as it was');
    const t = await runStretch(bp, {kind: 'span', by: 'sound', n: 5, set: SPLT, shape: 'tail'});
    eq([t.lines.t0, t.lines.t1, t.lines.gaps], [[0.5, 3, 5, 8, 12, 13], [3, 5, 7, 11, 13, 20], 2],
       'by the sound, a pause before the cut splits it there, and the one beyond it is as it was');
    const e = await runStretch(bp, {kind: 'span', by: 'sound', n: 5, set: SPLT, shape: 'even'});
    eq([e.lines.t0, e.lines.t1, e.lines.gaps], [[0.5, 3, 5.5, 8, 12, 13], [3, 5.5, 8, 11, 13, 20], 1],
       'and an answer that ends at the cut joins it, leaving the one beyond as it was');
  }
  console.log('   the END of a boundary in hand starts the stretch, the piece in hand keeping both its numbers');
  {
    const r = await runStretch(bp, {kind: 'span', by: 'sound', n: 4, edge: 'e'});
    const rq = r.asked[0] || {};
    eq([rq.start, rq.end, rq.texts], [6, 8, ['bbbb']], 'from the end at 6 to the cut at 8, about the one piece between');
    eq([r.lines.t0.slice(0, 3), r.lines.t1.slice(0, 2)], [[0.5, 3, 6], [3, 6]],
       'the piece in hand keeps its start and its end, and the ones before it are as they were');
    eq([r.lines.t0.slice(3), r.lines.t1.slice(3)], [[8, 12, 13], [12, 13, 20]], 'and from the cut on, too');
  }
  console.log('   a reader built before this has no picture to go by, and the box still works, by the text');
  {
    const r = await runStretch(bp, {kind: 'span', by: 'sound', n: 5, estimate: false});
    eq([r.lines.t0, r.lines.t1, r.status.text],
       [[0.5, 3, 6.33, 8, 12, 13], [3, 6.33, 8, 12, 13, 20],
        '2 pieces in the next 5 s (to 0:08.00) estimated afresh by the text; nothing outside that stretch moved'],
       'E goes by the text over the stretch, asking nothing');
  }
  console.log('   while the sound is read, and what moves under it');
  {
    await sixSheet(bp, {kind: 'span', by: 'sound', delay: 1200});
    await boxIn(bp, '5');
    await boxDo(bp, 'Enter');
    await bp.click('.tl-band[data-i="1"]');
    const held0 = await linesOf(bp);
    await bp.keyboard.press('e');
    await bp.waitForTimeout(250);
    const waiting = await bp.evaluate(() => ({
      said: document.querySelector('.tl-stat').textContent,
      stop: document.querySelector('[data-x="rest"]').textContent}));
    waiting.box = await boxOf(bp, 'readOnly'); waiting.val = await boxOf(bp, 'value');
    eq(waiting.said, 'estimating the next 5 s from the sound…', 'the status says which stretch is being read');
    eq([waiting.stop, waiting.box, waiting.val], ['stop estimating', true, '5'],
       'the button is the stop, and the box is held still with what it held');
    await bp.keyboard.press('Escape');
    eq(await statOf(bp), {text: 'stopped: nothing was estimated, and nothing moved', bad: false},
       'Escape gives the wait up');
    eq(await restLabel(bp), 'estimate the next 5 seconds', 'and the button is itself again, with the number still in the box');
    await bp.waitForTimeout(1300);                   // the answer comes, to a question given up
    const dropped = await linesOf(bp);
    eq([dropped.t0, dropped.t1], [held0.t0, held0.t1], 'its late answer laid nothing');
    await bp.keyboard.press('e');
    await bp.waitForTimeout(250);
    await bp.click('[data-x="rest"]');
    eq((await statOf(bp)).text, 'stopped: nothing was estimated, and nothing moved', 'the button gives it up just the same');
    await bp.waitForTimeout(1300);
    eq(await bp.evaluate(() => window.__asked.map(x => [x.start, x.end, x.texts.length])), [[3, 8, 2], [3, 8, 2]],
       'each question had gone out once, about the stretch from 3 to 8');
    const dropped2 = await linesOf(bp);
    eq([dropped2.t0, dropped2.t1], [held0.t0, held0.t1], 'and laid nothing either');
    // the timings that move under the question: a line dragged while the
    // sound is read (the drag began before E was pressed, which is the one
    // way to move them meanwhile) -- so the answer, laid over numbers it was
    // not asked about, is refused whole
    const line = await bp.locator('.tl-edge[data-i="0"][data-who="e"]').boundingBox();
    const cx = line.x + line.width / 2, cy = line.y + line.height / 2;
    await bp.mouse.move(cx, cy);
    await bp.mouse.down();
    await bp.keyboard.press('e');
    await bp.waitForTimeout(150);
    await bp.mouse.move(cx + 30, cy, {steps: 6});
    await bp.mouse.up();
    await bp.waitForFunction(() => /so nothing was laid/.test(document.querySelector('.tl-stat').textContent),
                             null, {timeout: 6000}).catch(() => {});
    eq(await statOf(bp), {text: 'the timings moved while the sound was being read, so nothing was laid', bad: true},
       'a line dragged meanwhile: the answer is refused whole');
    const meanwhile = await linesOf(bp);
    eq([meanwhile.t0.slice(2), meanwhile.t1.slice(2)], [held0.t0.slice(2), held0.t1.slice(2)],
       'nothing was laid over the stretch');
    assert(meanwhile.t0[1] > held0.t0[1] + 0.05, 'and the hand\'s own move is still there: ' + meanwhile.t0[1]);
    eq(await bp.evaluate(() => window.__asked.map(x => [x.start, x.end, x.texts.length]).slice(2)), [[3, 8, 2]],
       'the third question was about the same stretch');
    // the sheet is live again after a refusal: the box takes a number and the button says it
    await boxIn(bp, '7');
    eq([await restLabel(bp), await boxOf(bp, 'readOnly')], ['estimate the next 7 seconds', false],
       'after a refused answer the button says the number, and the box is the hand\'s');
    await shut();
    // the same, with the line dragged lying OUTSIDE the stretch: the end of a split boundary moves
    // only the piece before the line, and held() watches every mark, not only the stretch's
    await sixSheet(bp, {kind: 'span', by: 'sound', delay: 900,
                        set: {texts: SIX.texts, t0: SIX.t0, t1: [2.5, 6, 8, 12, 13, 20], dur: 20}});
    await boxIn(bp, '5');
    await boxDo(bp, 'Enter');
    const before = await linesOf(bp);
    const gate = await bp.locator('.tl-edge[data-i="0"][data-who="e"]').boundingBox();
    const gx = gate.x + gate.width / 2, gy = gate.y + gate.height / 2;
    await bp.mouse.move(gx, gy);
    await bp.mouse.down();
    await bp.keyboard.press('e');
    await bp.waitForTimeout(150);
    await bp.mouse.move(gx + 30, gy, {steps: 6});
    await bp.mouse.up();
    await bp.waitForFunction(() => /so nothing was laid/.test(document.querySelector('.tl-stat').textContent),
                             null, {timeout: 6000}).catch(() => {});
    eq(await statOf(bp), {text: 'the timings moved while the sound was being read, so nothing was laid', bad: true},
       'a line before the stretch dragged meanwhile: the answer is refused whole');
    const outside = await linesOf(bp);
    eq([outside.t0.slice(1), outside.t1.slice(1)], [before.t0.slice(1), before.t1.slice(1)],
       'and nothing was laid');
    assert(outside.t1[0] > before.t1[0] + 0.05, 'while the piece before the line kept the hand\'s move: ' + outside.t1[0]);
    await shut();
  }
  await bp.evaluate(() => { try { localStorage.setItem('tl_estimate_by', 'sound'); } catch (_) {} });

  console.log('   on the real book: what the reader asks, and where the numbers land');
  // The pieces are whatever the book's timings are by now (the saves above
  // moved some), read off the strip: the line at the start of the second
  // piece, and the cuts after it the starts of the third and fourth and the
  // end of the last.  The answer is skewed so that a moved boundary shows.
  const fullTexts = q.texts;                         // the three pieces after the line, from the first E above
  const skew = body => {
    const S = body.start, E = body.end, n = body.texts.length, at = k => S + (E - S) * Math.pow(k / n, 1.5);
    return {ok: true, method: 'wavealign', confidence: 0.6, anchored: 1, boundaries: n - 1, words: n,
            pieces: body.texts.map((_, k) => ({t0: at(k), t1: at(k + 1), confidence: 0.6}))};
  };
  answer = body => ({json: skew(body)});
  const stretchOnce = async n => {
    await byEar();
    await soundLive(bp);
    const b0 = await linesOf(bp);
    await bp.click('.tl-band[data-i="1"]');
    await boxIn(bp, n);
    await boxDo(bp, 'Enter');
    const label = await restLabel(bp);
    const k0 = asked.length;
    await bp.keyboard.press('e');
    const ok = await settled(bp, 15000);
    return {b0, label, ok, asked: asked.slice(k0), got: await linesOf(bp), said: await statOf(bp)};
  };
  {
    const r = await stretchOnce('2.5');
    const a = r.b0.t0[1], cut = r.b0.t0[3];
    // 2.5 s after the line points at a + 2.5, and the fourth piece's start is the cut nearest it
    assert(Math.abs((a + 2.5) - cut) < Math.min(Math.abs((a + 2.5) - r.b0.t0[2]), Math.abs((a + 2.5) - r.b0.t1[3])),
           'the book\'s numbers are what this check counts on: ' + JSON.stringify(r.b0));
    eq(r.label, 'estimate the next 2.5 seconds', 'the button says it');
    assert(r.ok, 'the sheet says it is done');
    const rq = r.asked[0] || {};
    eq([r.asked.length, rq.narration, rq.kind, rq.texts], [1, 'n1', 'span', fullTexts.slice(0, 2)],
       'one request, about this recording, with the two pieces inside the stretch and no more');
    assert(Math.abs(rq.start - a) < 0.006 && Math.abs(rq.end - cut) < 0.006,
           'from the line to the start of the fourth piece, the cut closest to the line + 2.5: '
           + JSON.stringify([rq.start, rq.end]));
    const mid = r2(a + (cut - a) * Math.pow(0.5, 1.5));
    eq([r.got.t0[0], r.got.t1[0]], [r.b0.t0[0], r.b0.t1[0]], 'nothing to the left of the line moved');
    eq([r.got.t0[1], r.got.t1[1], r.got.t0[2], r.got.t1[2]], [a, mid, mid, cut],
       'the two pieces are the answer\'s, to the hundredth, the second ending AT the cut');
    eq([r.got.t0[3], r.got.t1[3], r.got.gaps], [r.b0.t0[3], r.b0.t1[3], 0],
       'and the piece at the cut, and everything after it, is exactly as it was: same start, same end');
    eq(r.said, {text: `2 pieces in the next ${tenth(cut - a)} s (to ${clock(cut)}) estimated from the sound — the boundary `
                      + 'between them sits in a pause it heard; nothing outside that stretch moved', bad: false},
       'the status names the stretch as laid: the seconds are the real ones after rounding');
    await shut();
  }
  {
    const r = await stretchOnce('1');
    const rq = r.asked[0] || {};
    const a = r.b0.t0[1], cut = r.b0.t0[2];
    eq([rq.texts, r.label], [fullTexts.slice(0, 1), 'estimate the next 1 second'],
       'a number shorter than the first piece still lays one piece');
    assert(Math.abs(rq.end - cut) < 0.006, 'up to where the next begins: ' + rq.end);
    eq(r.said.text, `the one piece in the next ${tenth(cut - a)} s (to ${clock(cut)}) estimated from the sound; `
                    + 'nothing outside that stretch moved', 'and says so, in the singular');
    await shut();
  }
  {
    const r = await stretchOnce('50');
    const rq = r.asked[0] || {};
    eq([rq.texts, Math.abs(rq.end - r.b0.t1[3]) < 0.006], [fullTexts, true],
       'a number past the end asks exactly what "estimate the rest" asks');
    assert(/^3 pieces after this estimated from the sound — .*; nothing to the left of it moved \(the closest boundary to the next 50 seconds is the end, so this is the whole rest\)$/
             .test(r.said.text), 'and the status says it was the rest: ' + r.said.text);
    await shut();
  }

  console.log('   the number is not kept: a sheet opens on "estimate the rest"');
  await byEar();
  eq([await restLabel(bp), await boxOf(bp, 'value')],
     ['estimate the rest', ''], 'reopened, the box is empty and the button says the rest');
  eq(await bp.evaluate(() => JSON.stringify(Object.keys(localStorage).sort())), keysBefore,
     'and nothing about it is on this device');
  await shut();
  answer = null;

  if (REAL) {
    console.log('   and the real answer, from lib/wavealign.py through serve.py');
    answer = null;
    await byEar();
    assert(await soundLive(bp), 'by the sound is live');
    const real0 = await linesOf(bp);
    await bp.click('.tl-band[data-i="1"]');
    const n3 = asked.length;
    const resp = bp.waitForResponse(r => r.url().includes('__clip/estimate'), {timeout: 60000})
      .then(r => r.json(), () => null);
    await bp.keyboard.press('e');
    const ok = await settled(bp, 60000);
    const real = await resp;
    const realSaid = await statOf(bp);
    assert(ok && real && real.ok && !realSaid.bad,
           'the hub answers: ' + JSON.stringify(realSaid) + ' ' + JSON.stringify(real).slice(0, 200));
    eq(asked.length - n3, 1, 'one request');
    const r1 = await linesOf(bp);
    eq([r1.t0[0], r1.t1[0], r1.t0[1]], [real0.t0[0], real0.t1[0], real0.t0[1]],
       'nothing to the left of the line moved, and the piece at it kept its start');
    let inOrder = true;
    for (let i = 1; i < r1.t0.length; i++) {
      if (!(r1.t0[i] < r1.t1[i]) || (i + 1 < r1.t0.length && r1.t1[i] > r1.t0[i + 1])) inOrder = false;
    }
    assert(inOrder && r1.t1[3] <= real0.t1[3] + 0.001,
           'the pieces it laid are in order, inside the stretch: ' + JSON.stringify(r1));
    assert(/pieces after this estimated from the sound/.test(realSaid.text), 'and it says so: ' + realSaid.text);
    await shut();

    console.log('   and over a stretch, from lib/wavealign.py through serve.py: nothing outside it moves');
    await byEar();
    assert(await soundLive(bp), 'by the sound is live');
    const real2 = await linesOf(bp);
    await bp.click('.tl-band[data-i="1"]');
    await boxIn(bp, '2.5');
    await boxDo(bp, 'Enter');
    const n8 = asked.length;
    const resp2 = bp.waitForResponse(r => r.url().includes('__clip/estimate'), {timeout: 60000})
      .then(r => r.json(), () => null);
    await bp.keyboard.press('e');
    const ok2 = await settled(bp, 60000);
    const rr = await resp2;
    const said2 = await statOf(bp);
    assert(ok2 && rr && rr.ok && !said2.bad,
           'the hub answers: ' + JSON.stringify(said2) + ' ' + JSON.stringify(rr).slice(0, 200));
    eq(asked.length - n8, 1, 'one request');
    const q8 = asked[asked.length - 1] || {};
    assert(Math.abs(q8.start - real2.t0[1]) < 0.006 && Math.abs(q8.end - real2.t0[3]) < 0.006
             && (q8.texts || []).length === 2,
           'about the two pieces up to the cut at the start of the third: ' + JSON.stringify([q8.start, q8.end]));
    const r4 = await linesOf(bp);
    eq([r4.t0[0], r4.t1[0], r4.t0[1]], [real2.t0[0], real2.t1[0], real2.t0[1]],
       'nothing to the left of the line moved, and the piece at it kept its start');
    eq([r4.t0[3], r4.t1[3]], [real2.t0[3], real2.t1[3]],
       'and the piece at the cut, with everything after it, is exactly as it was');
    assert(r4.t0[1] < r4.t1[1] && r4.t0[2] < r4.t1[2] && r4.t1[1] <= r4.t0[2] + 0.001
             && r4.t1[2] <= real2.t0[3] + 0.001,
           'the two pieces it laid are in order, inside the stretch: ' + JSON.stringify(r4));
    assert(said2.text.startsWith(`2 pieces in the next ${tenth(real2.t0[3] - real2.t0[1])} s (to ${clock(real2.t0[3])}) `
                                 + 'estimated from the sound') && /; nothing outside that stretch moved$/.test(said2.text),
           'and it names the stretch: ' + said2.text);
    await shut();
  } else {
    console.log('   (the real answer is not asked for: lib/wavealign.py does not import here)');
  }
  await bp.close();

  /* ============ c) a video: one number per boundary, and no split ========= */
  const vp = await browser.newPage({viewport: {width: 1200, height: 900}});
  vp.on('pageerror', e => errors.push('film: ' + e.message));
  await vp.route('https://www.youtube.com/**', r => r.abort());
  await vp.goto(`${BASE}/youtube/v/${VIDEO}/`);
  await vp.waitForFunction(() => document.querySelectorAll('.seg').length > 0, null, {timeout: 25000});
  const labs = () => vp.evaluate(() => [...document.querySelectorAll('.seg .lab')]
    .map(b => b.textContent.trim().split(':').reduce((a, c) => a * 60 + +c, 0)));

  console.log('c) a film on this machine: the button, and what it opens');
  const hdr = await vp.evaluate(() => {
    const b = document.getElementById('captimes');
    return {text: b.textContent, off: b.disabled,
            after: b.previousElementSibling && b.previousElementSibling.id};
  });
  assert(hdr.text === 'the timings' && hdr.after === 'vidinfo',
         'it sits in the player header beside video info: ' + JSON.stringify(hdr.text));
  await vp.waitForFunction(() => {
    const f = document.querySelector('#film');
    return f && f.readyState >= 1;
  }, null, {timeout: 25000});
  const starts0 = await labs();
  await openSheet(vp, '#captimes');
  await vp.click('[data-x="all"]');
  assert(await vp.evaluate(() => document.querySelectorAll('.tl-band').length) === starts0.length,
         'one block per caption');
  assert(!await vp.evaluate(() => !!document.querySelector('[data-x="split"]')),
         'and NO split button: a caption has a start and nothing to split from');
  await vp.waitForFunction(() => document.querySelector('.tl-strip.tl-drawn'), null, {timeout: 25000});
  assert(await vp.evaluate(() => {
    const c = document.querySelector('.tl-wave'), g = c.getContext('2d');
    let lit = 0;
    const d = g.getImageData(0, 0, c.width, c.height).data;
    for (let k = 3; k < d.length; k += 4) if (d[k] > 0) lit++;
    return lit;
  }) > 500, 'the film\'s own sound is drawn, read by the server with ffmpeg');

  const vnums = async i => {
    await vp.click(`.tl-band[data-i="${i}"]`);
    return await vp.evaluate(() => [...document.querySelectorAll('.tl-at')]
      .map(n => n.value.split(':').reduce((a, b) => a * 60 + +b, 0)));
  };
  const v1was = await vnums(1), v0was = await vnums(0);
  assert(Math.abs(v0was[1] - v1was[0]) < 0.001,
         'the one before ends exactly where this starts, because that is what it means');
  await vp.click('.tl-band[data-i="1"]');
  await vp.click('.tl-row[data-edge="s"] [data-e="s+1"]');
  const v1now = await vnums(1), v0now = await vnums(0);
  assert(Math.abs(v1now[0] - (v1was[0] + 1)) < 0.02, 'a step of +1 moves it: ' + v1now[0]);
  assert(Math.abs(v0now[1] - v1now[0]) < 0.001,
         'and the one before follows, with no second number that could disagree');
  eq(await vp.evaluate(() => document.querySelectorAll('.tl-gap').length), 0,
     'no silence can be opened between two captions at all');

  console.log('f) and the same keys, because it is the same editor');
  const vhere = () => vp.evaluate(() =>
    document.querySelector('.tl-now .tl-say').textContent.slice(0, 4).trim());
  await vp.click('.tl-band[data-i="0"]');
  const v0 = await vhere();
  await vp.keyboard.press('.');
  const v1 = await vhere();
  await vp.keyboard.press(',');
  assert(v1 !== v0 && (await vhere()) === v0,
         'a video steps between captions with the same two keys: '
         + JSON.stringify([v0, v1]));
  // this film is 8 s long with three captions, so "fit" and "all" are the
  // same window on it; what is checked is that F does what the button does,
  // which holds whatever the recording's length
  const vspan = () => vp.evaluate(() => document.querySelector('.tl-span').textContent);
  await vp.click('.tl-band[data-i="1"]');
  await vp.click('[data-x="in"]');
  await vp.click('[data-x="in"]');
  const vnarrow = await vspan();
  await vp.keyboard.press('f');
  const vbyKey = await vspan();
  await vp.click('[data-x="in"]');
  await vp.click('[data-x="in"]');
  await vp.click('[data-x="fit"]');
  assert(vbyKey !== vnarrow && vbyKey === await vspan(),
         `and F opens the view back to exactly what fit does: ${vnarrow} -> ${vbyKey}`);

  console.log('e) and it saves through /youtube/api/times');
  let said = null;
  vp.on('response', async r => {
    if (r.url().includes('/api/times')) { try { said = JSON.parse(await r.text()); } catch (_) {} }
  });
  const vwant = v1now[0];
  await vp.click('[data-x="save"]');
  await vp.waitForFunction(() => !document.querySelector('.tl-root'), null, {timeout: 25000});
  assert(said && said.ok && said.moved === 1,
         'ONE caption moved, not the one before it as well: ' + JSON.stringify(said));
  const after = await labs();
  assert(Math.abs(after[1] - vwant) < 0.6, 'the caption list was redrawn with it: ' + after[1]);
  const ann = await (await fetch(`${BASE}/youtube/videos/english/${VIDEO}/annotations.json`)).json();
  assert(Math.abs(ann.segments[1].start - vwant) < 0.02,
         'and annotations.json on disk agrees: ' + ann.segments[1].start);
  console.log('   and the same on a video, where a piece has one number');
  // after the save, on a freshly opened sheet: this moves SEVERAL captions
  // and the checks above are about one
  await openSheet(vp, '#captimes');
  const vall = async () => {
    const out = [];
    for (let i = 0; i < 3; i++) out.push(await vnums(i));
    return out;
  };
  await vp.click('[data-x="all"]');
  const vwas = await vall();
  await vp.click('.tl-band[data-i="0"]');
  await vp.click('.tl-row[data-edge="e"] [data-e="e+"]');     // the line after caption 0
  await vp.waitForTimeout(150);
  const vanchor = (await vnums(0))[1];
  await vp.click('.tl-band[data-i="0"]');
  await vp.click('.tl-row[data-edge="e"] [data-e="e+"]');
  await vp.click('.tl-row[data-edge="e"] [data-e="e-"]');     // back, to leave edge on the end
  await vp.waitForTimeout(150);
  await vp.keyboard.press('e');
  await vp.waitForTimeout(300);
  const vnow = await vall();
  assert(Math.abs(vnow[0][0] - vwas[0][0]) < 0.001,
         'the caption before the line keeps its start: ' + JSON.stringify([vwas[0], vnow[0]]));
  assert(Math.abs(vnow[1][0] - vnow[0][1]) < 0.001,
         'and the one after starts exactly where that one ends, as a caption always does: '
         + JSON.stringify([vnow[0], vnow[1]]));
  assert(await vp.evaluate(() => document.querySelectorAll('.tl-gap').length) === 0,
         'no silence was opened: a caption has one number and there is nothing to split');
  await vp.keyboard.press('Escape');

  console.log('i) a film estimates by the sound too, its captions one number each');
  // the answer is routed and made up, as for the book: what is tested is
  // what the player asks and what the sheet does with the answer
  const vasked = [];
  await vp.route('**/youtube/api/estimate', async r => {
    const body = JSON.parse(r.request().postData() || '{}');
    vasked.push(body);
    const S = body.start, E = body.end, at = f => S + (E - S) * f;
    await r.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify({
      ok: true, method: 'wavealign', confidence: 0.6, anchored: 1, boundaries: 1, words: 7,
      pieces: [{t0: S, t1: at(0.45), confidence: 1, t0_min: S, t0_max: S},
               {t0: at(0.45), t1: E, confidence: 0.7, t0_min: at(0.4), t0_max: at(0.5)}]})});
  });
  await openSheet(vp, '#captimes');
  await vp.click('[data-x="all"]');
  assert(await soundLive(vp), 'by the sound is live on a film: the server draws its sound');
  await vp.click('[data-x="by-sound"]');
  const fwas = await linesOf(vp);
  await vp.click('.tl-band[data-i="1"]');
  await vp.keyboard.press('e');
  assert(await settled(vp, 15000), 'the sheet says it is done');
  const fq = vasked[vasked.length - 1] || {};
  eq([vasked.length, fq.video, fq.kind, (fq.texts || []).length, 'wave' in fq],
     [1, VIDEO, 'point', 2, false],
     'one request, about this film, as captions (one number a piece), with no picture sent: '
     + 'the server reads the film itself');
  const fgot = await linesOf(vp);
  const fS = fq.start, fE = fq.end;
  assert(Math.abs(fS - fwas.t0[1]) < 0.006, 'asked from the line in hand: ' + fS);
  eq([fgot.t0[0], fgot.t0[1]], [fwas.t0[0], fwas.t0[1]],
     'the caption before the line, and the one at it, keep their starts');
  eq(fgot.t0[2], r2(fS + (fE - fS) * 0.45), 'the next starts where the answer says');
  eq([fgot.t1[1], fgot.gaps], [fgot.t0[2], 0], 'and the one before runs until it, with no gap');
  eq(await statOf(vp), {text: '2 pieces after this estimated from the sound — the boundary '
                              + 'between them sits in a pause it heard; nothing to the left of '
                              + 'it moved', bad: false}, 'the status says so');
  await vp.keyboard.press('Escape');

  console.log('i) a film over a stretch: the next N seconds, from the caption in hand to the closest start');
  // the captions start at 0, 3 and 5 and the film ends at 8: the line at 3,
  // the cuts 5 and 8.  The answer is skewed (as on the book) by what it was
  // asked, so that a caption that moved shows.
  const fasked = [];
  await vp.route('**/youtube/api/estimate', async r => {
    const body = JSON.parse(r.request().postData() || '{}');
    fasked.push(body);
    await r.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(skew(body))});
  });
  const filmSheet = async n => {
    await openSheet(vp, '#captimes');
    await vp.click('[data-x="all"]');
    await soundLive(vp);
    const at = await linesOf(vp);
    await vp.click('.tl-band[data-i="1"]');
    const filled = await boxIn(vp, n);
    await boxDo(vp, 'Enter');
    const label = await restLabel(vp);
    const k0 = fasked.length;
    await vp.keyboard.press('e');
    const ok = await settled(vp, 15000);
    return {at, filled, label, ok, asked: fasked.slice(k0), got: await linesOf(vp), said: await statOf(vp)};
  };
  {
    const f = await filmSheet('1');
    assert(f.filled, 'the box is there on the player\'s sheet too');
    eq([f.at.t0[1], f.at.t0[2]], [3, 5], 'the captions the film has, as this test counts on them');
    eq(f.label, 'estimate the next 1 second', 'the button says it');
    const fq3 = f.asked[0] || {};
    eq([f.asked.length, fq3.video, fq3.kind, (fq3.texts || []).length, fq3.start, fq3.end],
       [1, VIDEO, 'point', 1, 3, 5],
       'one request, as captions: the one caption inside the stretch, from the line to the next start');
    eq([f.got.t0, f.got.gaps], [f.at.t0, 0], 'a shorter number than the first caption still lays one: nothing moved');
    eq(f.said.text, 'the one piece in the next 2 s (to 0:05.00) estimated from the sound; nothing outside that stretch moved',
       'and it says so');
    await vp.keyboard.press('Escape');
    const g = await filmSheet('100');
    const fq4 = g.asked[0] || {};
    eq([(fq4.texts || []).length, fq4.start, Math.abs(fq4.end - g.at.t1[2]) < 0.006], [2, 3, true],
       'a number past the end is the rest: both captions after the line, to the end of the film');
    eq([g.got.t0[0], g.got.t0[1], g.got.t0[2]],
       [g.at.t0[0], g.at.t0[1], r2(3 + (g.at.t1[2] - 3) * Math.pow(0.5, 1.5))],
       'the caption before the line, and the one at it, keep their starts; the next is the answer\'s');
    assert(/^2 pieces after this estimated from the sound — .*; nothing to the left of it moved \(the closest boundary to the next 100 seconds is the end, so this is the whole rest\)$/
             .test(g.said.text), 'and the status says it was the rest: ' + g.said.text);
    await vp.keyboard.press('Escape');
  }

  await vp.close();

  /* ==== d) a YouTube video: no sound any script here can reach ==== */
  const yp = await browser.newPage({viewport: {width: 1200, height: 900}});
  yp.on('pageerror', e => errors.push('youtube: ' + e.message));
  await yp.route('https://www.youtube.com/**', r => r.abort());
  // only YouTube is faked, and only the six methods the page may ask of it
  await yp.route('https://www.youtube.com/iframe_api', r => r.fulfill({
    contentType: 'text/javascript',
    body: `window.YT = {Player: function (el, o) {
      var t = 0, going = false, self = this;
      this.getCurrentTime = function () { return t; };
      this.getDuration = function () { return 40; };
      this.seekTo = function (s) { t = +s || 0; };
      this.playVideo = function () { going = true; };
      this.pauseVideo = function () { going = false; };
      this.getPlayerState = function () { return going ? 1 : 2; };
      this.getPlaybackRate = function () { return 1; };
      this.setPlaybackRate = function () {};
      this.mute = function () {}; this.unMute = function () {};
      this.isMuted = function () { return false; };
      setInterval(function () { if (going) t += 0.05; }, 50);
      setTimeout(function () { if (o.events && o.events.onReady) o.events.onReady({target: self}); }, 20);
    }};
    if (window.onYouTubeIframeAPIReady) window.onYouTubeIframeAPIReady();`,
  }));
  const yasked = [];
  await yp.route('**/youtube/api/estimate', async r => {
    const body = JSON.parse(r.request().postData() || '{}');
    yasked.push(body);
    const S = body.start, E = body.end, n = (body.texts || []).length;
    await r.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify({
      ok: true, method: 'wavealign', confidence: 0.5, anchored: 2, boundaries: n - 1, words: 20,
      pieces: body.texts.map((_, k) => ({t0: S + (E - S) * k / n, t1: S + (E - S) * (k + 1) / n,
                                         confidence: k ? 0.5 : 1}))})});
  });
  // the choice is kept on this device: by the sound is the one wanted here
  await yp.addInitScript(() => { try { localStorage.setItem('tl_estimate_by', 'sound'); } catch (_) {} });
  await yp.goto(`${BASE}/youtube/v/${YT}/`);

  console.log('d) a YouTube video is offered a waveform, and works without one');
  await openSheet(yp, '#captimes');
  const offer = await yp.evaluate(() => {
    const b = document.querySelector('[data-x="wave"]');
    return {there: !!b, hidden: b && b.hidden, off: b && b.disabled, why: b && b.title};
  });
  assert(offer.there && !offer.hidden, 'the offer to draw the sound is there');
  assert(!offer.off && /takes as long as the recording does/.test(offer.why),
         'live on a browser that can record a tab, and saying what it costs first');
  assert(await yp.evaluate(() => !!document.querySelector('.tl-strip.tl-plain')),
         'the strip says it has no waveform rather than pretending to one');
  const undrawnYT = await yp.evaluate(() => {
    const s = document.querySelector('[data-x="by-sound"]');
    return {off: s.disabled, why: s.title,
            pressed: ['by-text', 'by-sound'].map(x =>
              document.querySelector(`[data-x="${x}"]`).getAttribute('aria-pressed'))};
  });
  assert(undrawnYT.off && /draw the sound first/.test(undrawnYT.why),
         'i) by the sound is grey on a video not drawn yet, and says to draw it first -- '
         + undrawnYT.why);
  eq(undrawnYT.pressed, ['true', 'false'], 'so E goes by the text, though by the sound is the one kept');
  // a view that comes back with no picture is followed by one question for
  // a short stretch, in case the sound CAN be drawn here and only that view
  // could not: on a video never drawn that finds nothing either, and it
  // stays grey, saying the same
  await yp.click('[data-x="all"]');
  await yp.waitForTimeout(800);
  const allYT = await yp.evaluate(() => {
    const s = document.querySelector('[data-x="by-sound"]');
    return {off: s.disabled, why: s.title};
  });
  assert(allYT.off && /draw the sound first/.test(allYT.why),
         'with "all" pressed and the question for a short stretch answered, still grey, '
         + 'and still says to draw the sound first -- ' + allYT.why);
  await yp.click('.tl-band[data-i="1"]');
  await yp.click('.tl-row[data-edge="s"] [data-e="s+1"]');
  eq(await yp.evaluate(() => document.querySelectorAll('.tl-at')[0].value), '0:07.00',
     'and a caption still moves by its steps with no picture at all');
  await yp.keyboard.press('e');
  await yp.waitForTimeout(300);
  assert(/estimated afresh by the text/.test((await statOf(yp)).text),
         'E goes by the text: ' + (await statOf(yp)).text);
  eq(yasked.length, 0, 'asking the server nothing');
  await yp.keyboard.press('Escape');

  // the card kit reads navigator.userAgentData.brands and never a UA string
  await yp.evaluate(() => Object.defineProperty(navigator, 'userAgentData',
    {value: undefined, configurable: true}));
  await openSheet(yp, '#captimes');
  const grey = await yp.evaluate(() => {
    const b = document.querySelector('[data-x="wave"]');
    return {off: b.disabled, why: b.title};
  });
  assert(grey.off && /only Chrome and Edge/.test(grey.why),
         'on a browser that cannot record a tab it is grey, in the card kit\'s own words');
  await yp.keyboard.press('Escape');

  console.log('   a waveform recorded once is kept, and drawn on every later visit');
  const peaks = [];
  for (let k = 0; k < 40 * 20; k++) peaks.push(k >= 10 * 20 && k < 12 * 20 ? 1 : 0);
  const kept = await (await fetch(`${BASE}/youtube/api/waveform`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({video: YT, rate: 20, peaks})})).json();
  assert(kept.ok && kept.buckets === 800, 'it is kept: ' + JSON.stringify(kept));
  for (const [body, want, what] of [
      [{video: YT, rate: 9000, peaks: [1]}, 400, 'a rate nobody could have recorded'],
      [{video: 'nope', rate: 20, peaks: [1]}, 404, 'a video that is not there'],
      [{video: YT, rate: 20, peaks: []}, 400, 'a waveform with nothing in it']]) {
    const r = await fetch(`${BASE}/youtube/api/waveform`, {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    assert(r.status === want, what + ' is refused: ' + r.status);
  }
  await yp.goto(`${BASE}/youtube/v/${YT}/`);
  await openSheet(yp, '#captimes');
  await yp.click('[data-x="all"]');
  await yp.waitForFunction(() => document.querySelector('.tl-strip.tl-drawn'), null, {timeout: 20000});
  assert(await yp.evaluate(() => {
    const b = document.querySelector('[data-x="wave"]');
    return !b || b.hidden;
  }), 'it no longer offers to draw what is already drawn');
  const shape = await yp.evaluate(() => {
    const c = document.querySelector('.tl-wave'), g = c.getContext('2d');
    const w = c.width, h = c.height;
    const t = [...document.querySelectorAll('.tl-t')].map(n =>
      n.textContent.split(':').reduce((a, b) => a * 60 + +b, 0));
    const at = s => Math.round((s - t[0]) / (t[1] - t[0]) * w);
    const col = x => { let n = 0;
      const d = g.getImageData(Math.max(0, Math.min(w - 1, x)), 0, 1, h).data;
      for (let y = 0; y < h; y++) if (d[y * 4 + 3] > 0) n++; return n; };
    return {loud: col(at(11)), quiet: col(at(30))};
  });
  assert(shape.loud > 20, 'what the recording heard at 11 s is drawn tall: ' + shape.loud);
  assert(shape.quiet < shape.loud / 3, 'and the silence at 30 s is flat: ' + shape.quiet);

  console.log('i) drawn, the same video estimates by the sound, sending what it recorded');
  assert(await soundLive(yp), 'by the sound is live now that there is a picture');
  eq(await pressedOn(yp), ['false', 'true'], 'and the choice kept is the one in force');
  const ywas = await linesOf(yp);
  await yp.click('.tl-band[data-i="1"]');
  await yp.keyboard.press('e');
  assert(await settled(yp, 15000), 'the sheet says it is done');
  const yq = yasked[yasked.length - 1] || {};
  eq([yasked.length, yq.video, yq.kind, (yq.texts || []).length], [1, YT, 'point', 5],
     'one request, about this video, with the five captions after the line');
  const w = yq.wave || {};
  // caption 1 starts at 6 s and the stretch runs to the end of the video (40
  // s): the numbers kept are one every 50 ms, the 120th heard at 6 s
  eq([yq.start, yq.end, w.rate, w.start, (w.peaks || []).length], [6, 40, 20, 6, 680],
     'and the picture of the stretch it recorded sent with it, at its own rate, from 6 s');
  assert(JSON.stringify(w.peaks) === JSON.stringify(peaks.slice(120, 800)),
         'the numbers as they were kept, untouched: the loud stretch at '
         + JSON.stringify([(w.peaks || []).indexOf(1), (w.peaks || []).lastIndexOf(1)]));
  const ygot = await linesOf(yp);
  eq([ygot.t0[0], ygot.t0[1]], [ywas.t0[0], ywas.t0[1]],
     'nothing to the left of the line moved, nor the start of the caption at it');
  eq(ygot.t0.slice(2), [12.8, 19.6, 26.4, 33.2], 'and the rest start where the answer says');
  assert(/^5 pieces after this estimated from the sound — 2 of the 4 boundaries sit in a pause/
           .test((await statOf(yp)).text), 'the status says so: ' + (await statOf(yp)).text);
  await yp.keyboard.press('Escape');

  console.log('i) the same video over a stretch: the picture sent is the stretch\'s, and the cut stays');
  const y2 = [];
  await yp.route('**/youtube/api/estimate', async r => {
    const body = JSON.parse(r.request().postData() || '{}');
    y2.push(body);
    await r.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(skew(body))});
  });
  await openSheet(yp, '#captimes');
  await yp.click('[data-x="all"]');
  assert(await soundLive(yp), 'by the sound is live');
  const y0 = await linesOf(yp);
  eq(y0.t0, [0, 6, 12, 18, 24, 30], 'the captions the video has, as this test counts on them');
  await yp.click('.tl-band[data-i="1"]');
  assert(await boxIn(yp, '10'), 'the box is there');
  await boxDo(yp, 'Enter');
  eq(await restLabel(yp), 'estimate the next 10 seconds', 'the button says it');
  await yp.keyboard.press('e');
  assert(await settled(yp, 15000), 'the sheet says it is done');
  const yq2 = y2[y2.length - 1] || {};
  const yw2 = yq2.wave || {};
  // the line at 6 s; the cuts are 12, 18, 24, 30 and 40; 6 + 10 = 16 is
  // nearer 18 than 12, so the stretch is the two captions between
  eq([y2.length, yq2.video, yq2.kind, (yq2.texts || []).length, yq2.start, yq2.end],
     [1, YT, 'point', 2, 6, 18], 'one request: the two captions inside the stretch, from 6 s to 18 s');
  eq([yw2.rate, yw2.start, (yw2.peaks || []).length], [20, 6, 241],
     'and the picture sent is the stretch\'s only: one number every 50 ms, from 6 s to 18 s and the one after');
  assert(JSON.stringify(yw2.peaks) === JSON.stringify(peaks.slice(120, 361)),
         'the numbers as they were kept, untouched');
  const y1 = await linesOf(yp);
  eq(y1.t0, [0, 6, r2(6 + 12 * Math.pow(0.5, 1.5)), 18, 24, 30],
     'the caption at the cut, and every one after it, start exactly where they did');
  eq((await statOf(yp)).text, '2 pieces in the next 12 s (to 0:18.00) estimated from the sound — the boundary '
       + 'between them sits in a pause it heard; nothing outside that stretch moved', 'the status says so');
  await yp.keyboard.press('Escape');
  await yp.close();

  assert(errors.length === 0, 'no page threw anything: ' + JSON.stringify(errors));
  console.log(`\ntimings: ${passed} checks passed`);
  if (failed) throw Error(failed + ' failed');
} finally {
  await browser.close();
  try { hub.kill(); } catch (_) {}
  await hub.status;
  await Deno.remove(TMP, {recursive: true});
}
Deno.exit(failed ? 1 : 0);
