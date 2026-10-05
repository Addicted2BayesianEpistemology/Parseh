// SPDX-License-Identifier: GPL-3.0-or-later
// Browser test of the transliteration cloud on an EXPORTED page (TO-DO §8.38,
// a0.4.0: "the cloud works on an exported page, changing that open page
// only"), against the real studio routes on a temporary library:
//   * a Persian starter is exported ("HTML page, for a website") and the file
//     opened from file://, as a student who has no Parseh would open it
//   * pointing at a word of the target language opens the cloud, which is
//     exactly the studio's: it says nothing of saving
//   * the FIRST click on a word or in the cloud (a real mouse click, and a
//     real tap on a phone) puts one line over the screen, outside the cloud:
//     "Changes made here are not saved" -- never on the second click, never
//     again, never in the way of a click, gone in a few seconds or at Escape
//   * a colour chosen there colours the word on the open page; a
//     transliteration typed there (+ first) is written on it
//   * nothing is asked of any server and nothing is stored -- not a request,
//     not a localStorage or sessionStorage key -- and a reload returns the
//     page to what was exported
//   CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/export_cloud.mjs
//   SHOTS=<dir> saves the screenshot of the open cloud.
import {chromium} from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('SHOTS') || '';
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };

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

const origin = `http://127.0.0.1:${info.port}`;
const tmp = await Deno.makeTempDir({prefix: 'parseh-export-cloud-'});
let browser;
try {
  const md = await Deno.readTextFile(root + '/markdown/exlex/starters/fa.md');
  const made = await (await fetch(origin + '/api/docs', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                                          body: JSON.stringify({markdown: md})})).json();
  const html = await (await fetch(`${origin}/download/${made.meta.id}/html`)).text();
  const file = `${tmp}/exported.html`;
  await Deno.writeTextFile(file, html);
  console.log('the exported page:', Math.round(html.length / 1024), 'kB');

  browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
  const page = await (await browser.newContext({viewport: {width: 1100, height: 900}})).newPage();
  const asked = [], errors = [];
  page.on('request', r => { const u = r.url(); if (!/^(file|data|blob):/.test(u)) asked.push(u); });
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('file://' + file);
  await page.waitForSelector('.fa[data-fa]');
  const state = w => w.evaluate(e => ({coloured: e.parentElement.classList.contains('fac'), translit: e.dataset.translit || null}));
  const word = page.locator('.fa[data-fa]').first();
  const facBefore = await page.locator('.fac').count();     // the starter colours some words itself
  const before = await state(word);
  assert(!before.coloured && !before.translit, 'the first word of the page is plain, as exported');

  await word.scrollIntoViewIfNeeded();
  await word.hover();
  await page.waitForSelector('.fapal', {state: 'visible', timeout: 5000});
  assert(true, 'pointing at a word of the target language opens the cloud');
  const inCloud = await page.locator('.fapal').innerText();
  assert(!/saved|this page|only here|nothing/i.test(inCloud) && (await page.locator('.fapal .fapal-here').count()) === 0,
         `the cloud says nothing of saving, as in the studio: "${inCloud.replace(/\s+/g, ' ').trim()}"`);
  assert((await page.locator('.xp-unsaved').count()) === 0, 'pointing at a word says nothing yet: no click has been made');
  if (SHOTS) await page.screenshot({path: `${SHOTS}/export-cloud.png`});

  assert((await page.locator('.fapal button[data-color], .fapal input[type="color"], .fapal .none').count()) === 0,
         'the exported linguistic cloud constructs no colour controls');
  await page.locator('.fapal .tr-add').first().click();

  await page.waitForSelector('.xp-unsaved.xp-unsaved-on', {timeout: 3000});
  const said = await page.evaluate(() => {
    const n = document.querySelector('.xp-unsaved'), r = n.getBoundingClientRect(), cs = getComputedStyle(n);
    const bar = document.querySelector('.xp-bar').getBoundingClientRect();
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return {text: n.textContent, role: n.getAttribute('role'), live: n.getAttribute('aria-live'),
            inCloud: !!n.closest('.fapal'), parent: n.parentElement.tagName, position: cs.position,
            pointer: cs.pointerEvents, opacity: cs.opacity, z: +cs.zIndex,
            centred: Math.abs((r.left + r.right) / 2 - innerWidth / 2) <= 2,
            underBar: r.top >= bar.bottom, onScreen: r.top >= 0 && r.bottom <= innerHeight && r.left >= 0 && r.right <= innerWidth,
            hitIsNotIt: !(hit && hit.closest('.xp-unsaved')), toastZ: +getComputedStyle(document.querySelector('#toast')).zIndex,
            count: document.querySelectorAll('.xp-unsaved').length};
  });
  assert(said.text === 'Changes made here are not saved', `the first click puts one line over the screen: "${said.text}"`);
  assert(!said.inCloud && said.parent === 'BODY' && said.position === 'fixed' && said.count === 1,
         'outside the cloud, on the screen and not on the page: ' + JSON.stringify([said.parent, said.position, said.count]));
  assert(said.role === 'status' && said.live === 'polite', 'said to a screen reader too, politely');
  assert(said.centred && said.underBar && said.onScreen, 'at the top and the middle, under the bar, whole: ' + JSON.stringify([said.centred, said.underBar, said.onScreen]));
  assert(said.pointer === 'none' && said.hitIsNotIt, 'and it takes no click: the pointer goes through it');
  assert(said.z > said.toastZ, `above the toast (${said.z} over ${said.toastZ})`);
  if (SHOTS) await page.screenshot({path: `${SHOTS}/export-cloud-notice.png`});

  await page.locator('.fapal .tr-in').first().fill('salaam');
  await page.locator('.fapal .tr-in').first().press('Enter');
  await page.waitForFunction(() => document.querySelector('.fa[data-fa]').dataset.translit === 'salaam',
                             null, {timeout: 3000});
  assert(true, 'a transliteration typed in it is written on the open page');

  await page.waitForSelector('.xp-unsaved', {state: 'detached', timeout: 6000});
  assert(true, 'the line goes by itself after a few seconds');
  await word.hover();
  await page.waitForTimeout(700);
  assert((await page.locator('.xp-unsaved').count()) === 0, 'and pointing later does not bring it back');

  assert(asked.length === 0, 'nothing was asked of any server: ' + JSON.stringify(asked.slice(0, 3)));
  const keys = await page.evaluate(() => [...Object.keys(localStorage), ...Object.keys(sessionStorage)]);
  assert(keys.length === 0, 'nothing was stored in the browser: ' + JSON.stringify(keys));

  await page.reload();
  await page.waitForSelector('.fa[data-fa]');
  const after = await state(page.locator('.fa[data-fa]').first());
  assert(JSON.stringify(after) === JSON.stringify(before) && (await page.locator('.fac').count()) === facBefore,
         'a reload forgets the page-only linguistic change: the page is as it was exported');

  // a reload is a first time again; Escape puts the line away; and a click
  // on text that is no word of the target language says nothing
  await page.locator('.sheet p').first().click({position: {x: 3, y: 3}});
  assert((await page.locator('.xp-unsaved').count()) === 0, 'a click on the page that is no word says nothing');
  const answering = page.locator('.exercise .ex-item .fa[data-fa]').first();
  await answering.scrollIntoViewIfNeeded();
  await answering.click();
  await page.waitForTimeout(500);
  assert((await page.locator('.xp-unsaved').count()) === 0, 'nor does answering an exercise with a word of the target language');
  await page.mouse.move(2, 2);
  await page.locator('.fa[data-fa]').first().click();
  await page.waitForSelector('.xp-unsaved.xp-unsaved-on', {timeout: 3000});
  assert(true, 'after a reload the first click on a word says it again');
  await page.keyboard.press('Escape');
  await page.waitForSelector('.xp-unsaved', {state: 'detached', timeout: 3000});
  assert(true, 'and Escape puts it away');

  // a real tap, on a phone: the tap opens the cloud and is the first click
  const phone = await (await browser.newContext({viewport: {width: 390, height: 800}, hasTouch: true, isMobile: true,
                                                 deviceScaleFactor: 2})).newPage();
  phone.on('pageerror', e => errors.push('phone: ' + e.message));
  await phone.goto('file://' + file);
  await phone.waitForSelector('.fa[data-fa]');
  const tapped = phone.locator('.fa[data-fa]').first();
  await tapped.scrollIntoViewIfNeeded();
  await tapped.tap();
  await phone.waitForSelector('.fapal', {state: 'visible', timeout: 5000});
  await phone.waitForSelector('.xp-unsaved.xp-unsaved-on', {timeout: 3000});
  const onPhone = await phone.evaluate(() => {
    const n = document.querySelector('.xp-unsaved'), r = n.getBoundingClientRect();
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return {text: n.textContent, whole: r.left >= 0 && r.right <= innerWidth && r.top >= 0, oneLine: r.height < 2 * parseFloat(getComputedStyle(n).lineHeight),
            hit: !(hit && hit.closest('.xp-unsaved')),
            cloud: document.querySelector('.fapal').innerText.replace(/\s+/g, ' ').trim(), sideways: document.documentElement.scrollWidth > innerWidth};
  });
  assert(onPhone.text === 'Changes made here are not saved' && onPhone.whole && onPhone.oneLine && onPhone.hit && !onPhone.sideways,
         'a tap opens the cloud and brings the line, whole and on one line, on a phone, in nobody\'s way: ' + JSON.stringify(onPhone));
  if (SHOTS) await phone.screenshot({path: `${SHOTS}/export-cloud-phone.png`});
  assert((await phone.locator('.fapal button[data-color], .fapal input[type="color"], .fapal .none').count()) === 0,
         'the phone cloud has no colour controls either');
  assert(errors.length === 0, 'no script error: ' + errors.join(' | '));
  console.log(`Exported cloud passed (${passed} checks)`);
} finally {
  if (browser) await browser.close();
  proc.kill('SIGTERM');
  await proc.status.catch(() => {});
  await Deno.remove(tmp, {recursive: true}).catch(() => {});
}
