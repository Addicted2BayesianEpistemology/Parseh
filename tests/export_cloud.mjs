// SPDX-License-Identifier: GPL-3.0-or-later
// Browser test of the transliteration cloud on an EXPORTED page (TO-DO §8.38,
// a0.4.0: "the cloud works on an exported page, changing that open page
// only"), against the real studio routes on a temporary library:
//   * a Persian starter is exported ("HTML page, for a website") and the file
//     opened from file://, as a student who has no Parseh would open it
//   * pointing at a word of the target language opens the cloud, and the
//     cloud SAYS it changes this page only
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
  const note = (await page.locator('.fapal .fapal-here').textContent()).trim();
  assert(/this page only/i.test(note) && /nothing is saved/i.test(note), `and it says so: "${note}"`);
  if (SHOTS) await page.screenshot({path: `${SHOTS}/export-cloud.png`});

  await page.locator('.fapal button[data-color]').first().click();
  await page.waitForFunction(() => document.querySelector('.fa[data-fa]').parentElement.classList.contains('fac'),
                             null, {timeout: 3000});
  assert(true, 'a colour chosen in it colours the word on the open page');

  await word.hover();
  await page.locator('.fapal .tr-add').first().click();
  await page.locator('.fapal .tr-in').first().fill('salaam');
  await page.locator('.fapal .tr-in').first().press('Enter');
  await page.waitForFunction(() => document.querySelector('.fa[data-fa]').dataset.translit === 'salaam',
                             null, {timeout: 3000});
  assert(true, 'a transliteration typed in it is written on the open page');

  assert(asked.length === 0, 'nothing was asked of any server: ' + JSON.stringify(asked.slice(0, 3)));
  const keys = await page.evaluate(() => [...Object.keys(localStorage), ...Object.keys(sessionStorage)]);
  assert(keys.length === 0, 'nothing was stored in the browser: ' + JSON.stringify(keys));

  await page.reload();
  await page.waitForSelector('.fa[data-fa]');
  const after = await state(page.locator('.fa[data-fa]').first());
  assert(JSON.stringify(after) === JSON.stringify(before) && (await page.locator('.fac').count()) === facBefore,
         'a reload forgets both changes: the page is as it was exported');
  assert(errors.length === 0, 'no script error: ' + errors.join(' | '));
  console.log(`Exported cloud passed (${passed} checks)`);
} finally {
  if (browser) await browser.close();
  proc.kill('SIGTERM');
  await proc.status.catch(() => {});
  await Deno.remove(tmp, {recursive: true}).catch(() => {});
}
