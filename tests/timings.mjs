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
  await yp.click('.tl-band[data-i="1"]');
  await yp.click('.tl-row[data-edge="s"] [data-e="s+1"]');
  eq(await yp.evaluate(() => document.querySelectorAll('.tl-at')[0].value), '0:07.00',
     'and a caption still moves by its steps with no picture at all');
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
