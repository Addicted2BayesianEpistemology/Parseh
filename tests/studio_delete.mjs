// SPDX-License-Identifier: GPL-3.0-or-later
// Browser test of deleting a document, against the REAL routes on a temporary
// library, in both mounts (tests/studio_harness.py: `studio` is the studio's
// own server, `parseh` is Parseh's handler with the studio under /studio):
//   a) the library card's ✕ asks in the studio's own window (#modal-root
//      .modal, role=dialog) and never in the browser's: any native dialog
//      event fails the run.  Cancel, Escape and a click beside the box each
//      leave the document where it is and give the focus back to the ✕;
//      Delete document takes the card off the page at once -- before the
//      list has been asked for again -- and without a reload
//   b) a DELETE the server refuses (500) is said in a toast and the window
//      stays, both buttons free again; the list is still asked for again,
//      because the server may have done part of it.  A DELETE the server did
//      carry out but answered with a 500 (the bug that started this) takes
//      the card away on the re-list, and pressing Delete again meets "not
//      found", which is what was wanted: the window closes
//   c) the address of a deleted document, opened by a stale click, is the
//      studio's own 404 page (HTML, with the way back to the library), not
//      JSON; the API's own answers stay JSON
//   d) the document page's ⋯ > Delete document: the same window, the menu
//      shut behind it, Escape and a click beside cancel, a refusal keeps it,
//      Delete goes to the library; a document already deleted elsewhere goes
//      to the library too
//   CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/studio_delete.mjs
//   STUDIO_DELETE_MODES=studio (or parseh) runs one; SHOTS=<dir> saves the
//   window over the library and over a document, in paper, sepia and dark,
//   at 1280 and 390 px
import {chromium} from 'npm:playwright-core@1.52.0';

const root = await Deno.realPath(new URL('..', import.meta.url));
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';
const modes = (Deno.env.get('STUDIO_DELETE_MODES') || 'studio,parseh').split(',');
const SHOTS = Deno.env.get('SHOTS') || '';
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, what, ms = 8000) {
  const end = Date.now() + ms;
  for (;;) {
    let v;
    try { v = await fn(); } catch (_) { v = false; }
    if (v) return v;
    if (Date.now() > end) throw Error('FAIL: timed out: ' + what);
    await sleep(40);
  }
}

async function startHarness(mode) {
  const proc = new Deno.Command(python, {args: [root + '/tests/studio_harness.py', mode], cwd: root,
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
    if (done) throw Error(`harness (${mode}) exited before READY:\n` + buf + log.join(''));
    buf += value;
    const m = buf.match(/READY (\{.*\})\n/);
    if (m) info = JSON.parse(m[1]);
  }
  (async () => { for (;;) { const r = await reader.read(); if (r.done) break; } })();
  return {proc, info, log};
}

async function suite(mode) {
  console.log(`\n== ${mode} ==`);
  const {proc, info, log} = await startHarness(mode);
  const origin = `http://127.0.0.1:${info.port}`, base = info.studio;
  const url = p => origin + base + p;
  const call = async (method, path, body) => {
    const r = await fetch(url(path), {method, headers: body ? {'Content-Type': 'application/json'} : {},
                                      body: body ? JSON.stringify(body) : undefined});
    const text = await r.text();
    let data = null;
    try { data = JSON.parse(text); } catch (_) { /* a page */ }
    return {status: r.status, type: r.headers.get('content-type') || '', text, data};
  };
  const make = async title => (await call('POST', '/api/docs',
    {markdown: `---\ntitle: ${title}\ntarget: en\n---\n\nAbout ${title}.\n`})).data.meta.id;
  const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
  try {
    // a service worker would answer some of what the page asks before the
    // test's routes could see it
    const context = await browser.newContext({viewport: {width: 1280, height: 800}, serviceWorkers: 'block'});
    const page = await context.newPage();
    const errors = [], natives = [];
    page.on('pageerror', e => errors.push(e.message));
    // the run fails on any native dialog: a confirm() answered by a handler
    // that accepts it would look like a working delete
    page.on('dialog', d => { natives.push(d.type() + ': ' + d.message()); d.dismiss(); });

    const toast = () => page.evaluate(() => {
      const t = document.querySelector('#toast');
      return t && !t.hidden ? {text: t.textContent, err: t.classList.contains('err')} : null;
    });
    const modal = () => page.evaluate(() => {
      const m = document.querySelector('#modal-root .modal');
      if (!m) return null;
      const b = [...m.querySelectorAll('button')];
      return {title: m.querySelector('h3').textContent, hint: (m.querySelector('p') || {}).textContent || '',
              role: m.getAttribute('role'), modal: m.getAttribute('aria-modal'),
              buttons: b.map(x => ({text: x.textContent, cls: x.className, off: x.disabled})),
              focus: document.activeElement && document.activeElement.textContent,
              box: (r => ({x: r.left, r: r.right, y: r.top, b: r.bottom}))(m.getBoundingClientRect()),
              vw: innerWidth, vh: innerHeight};
    });
    const shut = what => until(async () => !(await modal()), what);
    const card = id => `#cards .card[data-id="${id}"]`;
    const listed = id => page.evaluate(sel => !!document.querySelector(sel), card(id));
    const gone = async id => (await call('GET', `/api/docs/${id}`)).status === 404;
    const lists = [];
    page.on('request', r => { if (r.method() === 'GET' && /\/api\/docs\?/.test(r.url())) lists.push(Date.now()); });
    // answers a DELETE of `id` with `status` (after really carrying it out, if
    // `alsoDelete`); what comes back puts the real thing back
    const refuse = async (id, status, alsoDelete) => {
      const match = u => u.pathname.endsWith('/api/docs/' + id);
      const handler = async route => {
        if (route.request().method() !== 'DELETE') return route.continue();
        if (alsoDelete) await route.fetch();
        return route.fulfill({status, contentType: 'application/json',
                              body: JSON.stringify({error: alsoDelete ? 'it broke after the delete' : 'disk is full'})});
      };
      await page.route(match, handler);
      return () => page.unroute(match, handler);
    };
    const library = async ids => {
      await page.goto(url('/'));
      await page.waitForFunction(n => document.querySelectorAll('#cards .card').length >= n, ids.length);
      await page.evaluate(() => { window.__stay = true; });
    };
    const askDelete = async id => {
      await page.hover(card(id));
      await page.click(card(id) + ' .card-del');
      await page.waitForSelector('#modal-root .modal');
    };

    /* ---------------- a) the card's ✕ ---------------- */
    console.log('a) the library card\'s ✕');
    const A = await make('Del A'), B = await make('Del B'), C = await make('Del C'), D = await make('Del D');
    await library([A, B, C, D]);
    await askDelete(A);
    let m = await modal();
    assert(m.role === 'dialog' && m.modal === 'true', 'the question is a dialog window over the page');
    assert(m.title === 'Delete “Del A”?' && /builds are deleted too/.test(m.hint) && /cannot be undone/.test(m.hint),
           `it names the document and says what goes with it (${m.title} / ${m.hint})`);
    assert(m.buttons.length === 2 && m.buttons[0].text === 'Cancel' && m.buttons[1].text === 'Delete document'
           && /\bdanger\b/.test(m.buttons[1].cls), 'Cancel, and a danger button that says what it does');
    assert(m.focus === 'Cancel', 'the focus starts on Cancel');
    assert(page.url() === url('/'), 'the ✕ did not open the document');
    assert(await listed(A), 'the document is still there while the question is open');
    await page.keyboard.press('Tab');
    assert((await modal()).focus === 'Delete document', 'Tab goes to the other button');
    await page.keyboard.press('Tab');
    assert((await modal()).focus === 'Cancel', 'and round again: the page beneath is out of reach');

    await page.keyboard.press('Escape');
    await shut('Escape closes the window');
    assert(await listed(A) && !(await gone(A)), 'Escape cancels: the document is kept');
    assert(await page.evaluate(id => document.activeElement === document.querySelector(`#cards .card[data-id="${id}"] .card-del`), A),
           'and the focus goes back to the ✕ that asked');

    await askDelete(A);
    await page.mouse.click(4, 4);
    await shut('a click beside the box closes the window');
    assert(await listed(A) && !(await gone(A)), 'a click beside the box cancels: the document is kept');

    await askDelete(A);
    await page.click('#modal-root [data-x="cancel"]');
    await shut('Cancel closes the window');
    assert(await listed(A) && !(await gone(A)), 'Cancel cancels: the document is kept');

    // the list is held back: the card must go without waiting for it
    await askDelete(D);
    let release;
    const held = new Promise(r => { release = r; });
    const isList = u => u.pathname === base + '/api/docs';
    const hold = async route => { await held; await route.continue(); };
    await page.route(isList, hold);
    const before = lists.length;
    await page.click('#modal-root .btn.danger');
    await until(async () => !(await listed(D)), 'the card goes at once, with the list still not answered', 1500);
    await until(async () => lists.length > before, 'the list was asked for again');
    assert(await gone(D), 'the document is deleted on the server');
    release();
    await page.unroute(isList, hold);
    await shut('the window closes');
    const t = await toast();
    assert(t && !t.err && t.text === 'Deleted Del D', `a toast says so (${t && t.text})`);
    assert(await page.evaluate(() => window.__stay === true), 'and the page was not reloaded');

    /* ---------------- b) a refusal ---------------- */
    console.log('b) a DELETE the server refuses');
    let mend = await refuse(B, 500);
    await askDelete(B);
    const n0 = lists.length;
    await page.click('#modal-root .btn.danger');
    await until(async () => (await toast() || {}).err, 'an error toast');
    m = await modal();
    assert(m && m.buttons.every(b => !b.off), 'the window stays, both buttons free again');
    assert((await toast()).text === 'Delete failed: disk is full', `the refusal is said as the server said it (${(await toast()).text})`);
    if (SHOTS) await page.screenshot({path: `${SHOTS}/${mode}-refused.png`});
    await until(async () => lists.length > n0, 'the list is asked for again after a refusal');
    assert(await listed(B) && !(await gone(B)), 'the document is still listed, and still there');
    await mend();
    await page.click('#modal-root .btn.danger');
    await shut('the second press goes through');
    assert(!(await listed(B)) && (await gone(B)), 'pressed again with the server well, it is deleted');

    mend = await refuse(C, 500, true);
    await askDelete(C);
    await page.click('#modal-root .btn.danger');
    await until(async () => (await toast() || {}).err, 'an error toast for the delete that did happen');
    assert(await modal(), 'it answered 500 after deleting: the window stays');
    await until(async () => !(await listed(C)), 'the list, asked again, no longer has it');
    assert(await gone(C), 'the server did delete it');
    await mend();
    await page.click('#modal-root .btn.danger');
    await shut('a document already gone is what was asked for: the window closes');
    assert((await toast()).text === 'Deleted Del C' && !(await toast()).err, 'and the toast says it is deleted');
    assert(await page.evaluate(() => window.__stay === true), 'still no reload');

    /* ---------------- c) the stale click ---------------- */
    console.log('c) the address of a deleted document');
    const stale = await call('GET', `/doc/${C}`);
    assert(stale.status === 404 && /text\/html/.test(stale.type) && !stale.data,
           `a page for a deleted document is HTML (${stale.status} ${stale.type})`);
    assert(/404/.test(stale.text) && stale.text.includes(`href="${base}/"`), 'the studio\'s own 404 page, with the way to the library');
    const edit = await call('GET', `/doc/${C}/edit`);
    assert(edit.status === 404 && /text\/html/.test(edit.type), 'so is its edit page');
    const json = await call('GET', `/api/docs/${C}`);
    assert(json.status === 404 && json.data && json.data.error === 'document not found', 'the API still answers JSON');
    const del2 = await call('DELETE', `/api/docs/${C}`);
    assert(del2.status === 404 && del2.data && del2.data.error === 'document not found', 'so does a second DELETE');
    const dl = await call('GET', `/download/${C}/md`);
    assert(dl.status === 404 && !/text\/html/.test(dl.type), 'and a download for a script');
    await page.goto(url(`/doc/${C}`));
    const shown = await page.evaluate(() => ({h1: (document.querySelector('h1') || {}).textContent,
                                              back: !!document.querySelector('main a[href$="/"]'),
                                              raw: document.body.innerText.includes('"error"')}));
    assert(shown.h1 === '404' && shown.back && !shown.raw, 'in the browser: a page with a way back, no raw JSON');
    if (SHOTS) await page.screenshot({path: `${SHOTS}/${mode}-404.png`});

    /* ---------------- d) the document page ---------------- */
    console.log('d) the document page\'s Delete document');
    const E = await make('Del E'), F = await make('Del F');
    const docPage = async id => {
      await page.goto(url(`/doc/${id}`));
      await page.waitForSelector('article.sheet');
      await page.evaluate(() => { window.__stay = true; });
    };
    const menuDelete = async () => {
      await page.click('header.topbar details.dropdown:has(#btn-delete) > summary');
      await page.click('#btn-delete');
      await page.waitForSelector('#modal-root .modal');
    };
    await docPage(E);
    await menuDelete();
    m = await modal();
    assert(m.role === 'dialog' && m.title === 'Delete “Del E”?' && m.buttons[1].text === 'Delete document'
           && /\bdanger\b/.test(m.buttons[1].cls) && m.focus === 'Cancel', 'the same window, on the document page');
    assert(!(await page.evaluate(() => document.querySelector('details.dropdown:has(#btn-delete)').open)),
           'the menu it came from is shut');
    await page.keyboard.press('Escape');
    await shut('Escape closes the window');
    assert(page.url() === url(`/doc/${E}`) && !(await gone(E)), 'Escape cancels: still on the page, still there');
    assert(await page.evaluate(() => document.activeElement === document.querySelector('details.dropdown:has(#btn-delete) > summary')),
           'the focus goes back to the ⋯ that opened it');
    await menuDelete();
    await page.mouse.click(4, 4);
    await shut('a click beside the box closes the window');
    assert(page.url() === url(`/doc/${E}`) && !(await gone(E)), 'a click beside the box cancels');
    await menuDelete();
    await page.click('#modal-root [data-x="cancel"]');
    await shut('Cancel closes the window');
    assert(!(await gone(E)), 'Cancel cancels');

    mend = await refuse(E, 500);
    await menuDelete();
    await page.click('#modal-root .btn.danger');
    await until(async () => (await toast() || {}).err, 'an error toast on the document page');
    m = await modal();
    assert(m && m.buttons.every(b => !b.off) && (await toast()).text === 'Delete failed: disk is full',
           'a refusal is said, and the window stays');
    assert(page.url() === url(`/doc/${E}`) && !(await gone(E)), 'still on the page, still there');
    await mend();
    await Promise.all([page.waitForURL(url('/')), page.click('#modal-root .btn.danger')]);
    assert(await gone(E), 'pressed again with the server well: deleted, and the library opens');
    await page.waitForFunction(() => document.querySelectorAll('#cards .card').length > 0);
    assert(!(await listed(E)), 'and the library does not list it');

    await docPage(F);
    await menuDelete();
    assert((await call('DELETE', `/api/docs/${F}`)).status === 200, 'the document is deleted elsewhere while the window is open');
    await Promise.all([page.waitForURL(url('/')), page.click('#modal-root .btn.danger')]);
    assert(page.url() === url('/') && (await gone(F)), 'pressing Delete on a document already gone takes the page to the library');

    /* ---------------- screenshots ---------------- */
    if (SHOTS) {
      const G = await make('Del G'), H = await make('Del H');
      for (const [vw, vh] of [[1280, 800], [390, 844]]) {
        await page.setViewportSize({width: vw, height: vh});
        for (const theme of ['light', 'sepia', 'dark']) {
          await page.goto(url('/'));
          await page.evaluate(t => { localStorage.setItem('parseh_theme', t); }, theme);
          await page.reload();
          await page.waitForSelector(card(G));
          await askDelete(G);
          await sleep(150);
          await page.screenshot({path: `${SHOTS}/${mode}-library-${theme}-${vw}.png`});
          const m2 = await modal();
          assert(m2.box.x >= 0 && m2.box.r <= m2.vw && m2.box.y >= 0 && m2.box.b <= m2.vh,
                 `${theme} ${vw}px: the window is whole on the screen`);
          await page.keyboard.press('Escape');
          await page.goto(url(`/doc/${H}`));
          await page.waitForSelector('article.sheet');
          await menuDelete();
          await sleep(150);
          await page.screenshot({path: `${SHOTS}/${mode}-doc-${theme}-${vw}.png`});
          await page.keyboard.press('Escape');
        }
      }
    }

    assert(natives.length === 0, `no native dialog was ever opened (${JSON.stringify(natives)})`);
    assert(errors.length === 0, `no page errors (${errors.join(' | ')})`);
  } finally {
    await browser.close();
    proc.kill('SIGTERM');
    await proc.status.catch(() => {});
    const err = log.join('');
    if (/Traceback/.test(err)) console.log('server said:\n' + err);
  }
}

for (const mode of modes) await suite(mode);
console.log(`\n${passed} checks passed`);
