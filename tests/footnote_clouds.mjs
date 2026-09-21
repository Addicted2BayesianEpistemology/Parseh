// Browser test of the studio's footnote clouds on a phone, against the REAL
// routes on a temporary library (tests/studio_harness.py).  A note's cloud is
// laid out only while it is shown: hidden but laid out, a cloud near the right
// edge of a 390 px screen widened the page, and the whole reading view could
// be pushed sideways.  Driven here, for a document made from each of the
// eleven starter pages (every one of them has notes):
//   a) at 390x844 with touch, the page is no wider than the screen
//   b) a tap on each note's mark opens its cloud, inside the screen at both
//      sides, with its tail still on the mark
//   c) at 1400x900 a hover opens it, above or below its line, inside the window
//   CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/footnote_clouds.mjs
import {chromium} from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };

async function startHarness() {
  const proc = new Deno.Command(python, {args: [root + '/tests/studio_harness.py', 'studio'], cwd: root,
                                         stdout: 'piped', stderr: 'piped'}).spawn();
  const log = [];
  (async () => {
    const r = proc.stderr.pipeThrough(new TextDecoderStream()).getReader();
    for (;;) { const {value, done} = await r.read(); if (done) break; log.push(value); }
  })();
  const reader = proc.stdout.pipeThrough(new TextDecoderStream()).getReader();
  let buf = '', info = null;
  while (!info) {
    const {value, done} = await reader.read();
    if (done) throw Error('harness exited before READY:\n' + buf + log.join(''));
    buf += value;
    const m = buf.match(/READY (\{.*\})\n/);
    if (m) info = JSON.parse(m[1]);
  }
  (async () => { for (;;) { const r = await reader.read(); if (r.done) break; } })();
  return {proc, info, log};
}

const CODES = ['ar', 'de', 'en', 'es', 'fa', 'fr', 'hi', 'it', 'ja', 'tr', 'zh'];
const {proc, info} = await startHarness();
const origin = `http://127.0.0.1:${info.port}`, base = info.studio;
const url = p => origin + base + p;
const create = async md => {
  const r = await fetch(url('/api/docs'), {method: 'POST', headers: {'Content-Type': 'application/json'},
                                           body: JSON.stringify({markdown: md})});
  const j = await r.json();
  if (r.status !== 201) throw Error('create: ' + JSON.stringify(j));
  return j.meta.id;
};

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
try {
  const docs = {};
  for (const code of CODES)
    docs[code] = await create(await Deno.readTextFile(`${root}/markdown/exlex/starters/${code}.md`));

  // where a note's cloud is, shown, against the screen and its mark
  const clouds = page => page.evaluate(() => [...document.querySelectorAll('#sheet .fn')].map(fn => {
    const c = fn.querySelector('.fncloud'), m = fn.querySelector('.fnref');
    return {cloud: c.getBoundingClientRect().toJSON(), mark: m.getBoundingClientRect().toJSON(),
            shown: getComputedStyle(c).display !== 'none', width: document.documentElement.clientWidth};
  }));

  const phone = await browser.newContext({viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true});
  const pp = await phone.newPage();
  const errors = [];
  pp.on('pageerror', e => errors.push(e.message));
  for (const code of CODES) {
    await pp.goto(url(`/doc/${docs[code]}`));
    await pp.waitForSelector('#sheet .fn');
    const wide = await pp.evaluate(() => ({doc: document.documentElement.scrollWidth, body: document.body.scrollWidth,
                                           screen: innerWidth}));
    assert(wide.doc <= wide.screen && wide.body <= wide.screen,
           `${code}: on a 390 px phone the reading view is no wider than the screen ${JSON.stringify(wide)}`);
    const n = await pp.locator('#sheet .fnref').count();
    for (let i = 0; i < n; i++) {
      const mark = pp.locator('#sheet .fnref').nth(i);
      await mark.scrollIntoViewIfNeeded();
      await mark.tap();
      const got = (await clouds(pp))[i];
      const inside = got.cloud.left >= 0 && got.cloud.right <= got.width;
      const onMark = got.mark.left - 8 <= got.cloud.right && got.mark.right + 8 >= got.cloud.left;
      assert(got.shown && inside && onMark,
             `${code}: a tap on note ${i + 1} opens its cloud inside the screen, over its mark ${JSON.stringify(got)}`);
      await pp.evaluate(() => document.activeElement && document.activeElement.blur());
    }
    const after = await pp.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
    assert(after, `${code}: and the page is still no wider than the screen after the notes were opened`);
  }
  assert(!errors.length, 'no page errors on the phone: ' + errors.join(' | '));

  const desk = await browser.newContext({viewport: {width: 1400, height: 900}});
  const dp = await desk.newPage();
  for (const code of ['fa', 'de', 'ja']) {
    await dp.goto(url(`/doc/${docs[code]}`));
    await dp.waitForSelector('#sheet .fn');
    const mark = dp.locator('#sheet .fnref').first();
    await mark.scrollIntoViewIfNeeded();
    await mark.hover();
    const got = (await clouds(dp))[0];
    assert(got.shown && got.cloud.left >= 0 && got.cloud.right <= got.width && got.cloud.top >= 0,
           `${code}: at 1400 px a hover opens the first note inside the window ${JSON.stringify(got)}`);
  }
  console.log(`\nfootnote_clouds: ${passed} checks passed`);
} finally {
  await browser.close();
  try { proc.kill('SIGTERM'); } catch (_) { /* gone */ }
}
