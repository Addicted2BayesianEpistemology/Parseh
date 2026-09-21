import { chromium } from 'npm:playwright-core@1.52.0';
// Sections: a chapter's name and the places inside it, in the reader.
//
// Run: CHROME_BIN=/path/to/chrome deno run --allow-all tests/sections.mjs
//
//  a) IN THE TEXT.  A chapter says which chapter it is, with its name under
//     the number; a section says its name, in a smaller hand, and stands
//     OUTSIDE the .para -- folding a run of paragraphs away must never take
//     the mark of a section with it.
//  b) THE CONTENTS IS A TREE.  Chapter -> section -> paragraph, each foldable
//     on its own, with fold-all and open-all.  Nothing is folded to begin
//     with, so the panel opens as the flat list it has always been.
//  c) A SEARCH OPENS WHAT IT SEARCHES.  Filtering with a chapter folded away
//     would otherwise find an entry and show nothing.
//  d) THE SHEET IS REALLY ON SCREEN.  Asserted the way the fold sheet has to
//     be: computed position, a rect inside the viewport, and the element the
//     browser finds at its own centre -- `hidden` being false proves nothing,
//     since a sheet with no CSS opens in the normal flow at the foot of the
//     body, where nobody is looking.
//  e) THE BOUNDARY the player stops at is the one the build counted.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const TMP = await Deno.makeTempDir({prefix: 'parseh-sections-'});
const td = new TextDecoder();
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
async function py(code, ...args) {
  const o = await new Deno.Command(PY, {args: ['-c', code, ...args], stdout: 'piped', stderr: 'piped'}).output();
  if (!o.success) throw Error(td.decode(o.stderr) || td.decode(o.stdout));
  return td.decode(o.stdout);
}

/* ---------------- a book with a named chapter and two sections ------------ */
const BOOK = `${TMP}/books/english/mini-en`;
await py(`
import os, shutil, sys
d = sys.argv[1]
os.makedirs(os.path.dirname(d), exist_ok=True)
shutil.copytree('tests/fixtures/books/english/mini-en', d, ignore=shutil.ignore_patterns('reader'))
`, BOOK);

// the shape before anything: what must not move
const before = JSON.parse(await py(`
import json, sys
sys.path.insert(0, 'lib')
import texparse as T
ch = T.parse_chapter(sys.argv[1] + '/ch1.tex')
print(json.dumps({"paras": [p.no for p in ch.paragraphs],
                  "subs": [s.label for s in ch.subs],
                  "chunks": len(T.all_chunks([ch]))}))
`, BOOK));

await py(`
import sys
sys.path.insert(0, 'lib')
import structure as S
d = sys.argv[1]
S.set_chapter_name(d, 1, 'Water & Waste')
S.set_section(d, 1, 2, 'The Spillway')
`, BOOK);

const after = JSON.parse(await py(`
import json, sys
sys.path.insert(0, 'lib')
import texparse as T
ch = T.parse_chapter(sys.argv[1] + '/ch1.tex')
print(json.dumps({"paras": [p.no for p in ch.paragraphs],
                  "subs": [s.label for s in ch.subs],
                  "chunks": len(T.all_chunks([ch])),
                  "name": ch.name,
                  "secs": {str(p.no): p.section for p in ch.paragraphs if p.section}}))
`, BOOK));

assert(JSON.stringify(after.paras) === JSON.stringify(before.paras) &&
       JSON.stringify(after.subs) === JSON.stringify(before.subs) &&
       after.chunks === before.chunks,
       'naming a chapter and opening a section moves no paragraph, no subparagraph and no chunk');
assert(after.secs['2'] && !after.secs['1'],
       'the section opens at the paragraph it was asked for, not the one before it');

await py(`
import subprocess, sys
subprocess.run([sys.executable, 'lib/tex2html.py', '--book', sys.argv[1]], check=True,
               stdout=subprocess.DEVNULL)
`, BOOK);

/* ---------------- served the way serve.py serves it ---------------------- */
const server = Deno.serve({port: 0, onListen: () => {}}, async req => {
  const p = decodeURIComponent(new URL(req.url).pathname);
  // '' last, and it is the one that matters: the reader links parseh.js by a
  // path relative to ITS OWN directory, and a reader built in a temp tree
  // resolves that to the repo's real lib/ -- an absolute path, which neither
  // of the other two bases can serve.  Without it the page loads with no
  // Parseh, throws on the first use of it, and assigns none of its handlers;
  // every later step then times out waiting for something to open.
  for (const base of [TMP, root, '']) {
    try {
      const f = await Deno.readFile(base + p);
      const type = p.endsWith('.css') ? 'text/css'
        : p.endsWith('.js') ? 'text/javascript'
        : p.endsWith('.json') ? 'application/json' : 'text/html; charset=utf-8';
      return new Response(f, {headers: {'content-type': type}});
    } catch (_) { /* try the next base */ }
  }
  return new Response('not found', {status: 404});
});
const PORT = server.addr.port;
const READER = `http://127.0.0.1:${PORT}/books/english/mini-en/reader/index.html`;

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
const errors = [];
try {
  const page = await browser.newPage();
  // said at once, not only in the assertion at the foot: a script that throws
  // on load assigns none of its handlers, and every later step then fails as
  // a timeout waiting for something to open -- which names the symptom and
  // hides the cause
  page.on('pageerror', e => {
    errors.push(String(e.message || e));
    console.log('  PAGE ERROR', e.message || e);
  });
  await page.goto(READER, {waitUntil: 'domcontentloaded'});
  await page.waitForSelector('.para');

  // (a) in the text
  const text = await page.evaluate(() => {
    const head = document.querySelector('.chhead');
    const sec = document.querySelector('.sechead');
    return {
      chnum: head && head.querySelector('.chnum') ? head.querySelector('.chnum').textContent.trim() : '',
      chname: head && head.querySelector('.chname') ? head.querySelector('.chname').textContent.trim() : '',
      sec: sec ? sec.textContent.trim() : '',
      secInsidePara: !!(sec && sec.closest('.para')),
      secFont: sec ? parseFloat(getComputedStyle(sec).fontSize) : 0,
      chFont: head && head.querySelector('.chnum')
        ? parseFloat(getComputedStyle(head.querySelector('.chnum')).fontSize) : 0,
    };
  });
  assert(text.chnum === '1', 'the chapter says which chapter it is, in the text');
  assert(text.chname === 'Water & Waste', "and its name, with the & it was typed with");
  assert(text.sec === 'The Spillway', 'the section says its name in the text');
  assert(!text.secInsidePara,
         'and stands outside the .para, so folding a run cannot take it away');
  assert(text.secFont < text.chFont,
         `a section is set smaller than a chapter (${text.secFont} < ${text.chFont})`);

  // (b) the contents is a tree
  await page.click('#toc');
  await page.waitForSelector('#tocpanel');
  const tree = await page.evaluate(() => ({
    groups: document.querySelectorAll('#toclist .tocgrp').length,
    sgroups: document.querySelectorAll('#toclist .tocsgrp').length,
    nested: document.querySelectorAll('#toclist .tocgrp > .tocbody > .tocsgrp > .tocbody > a.toce').length,
    closedAtFirst: document.querySelectorAll('#toclist .closed').length,
    secName: (document.querySelector('#toclist .tocsecn') || {}).textContent || '',
    chName: (document.querySelector('#toclist .tocchn') || {}).textContent || '',
  }));
  assert(tree.groups === 1 && tree.sgroups === 1, 'one chapter and one section in the panel');
  assert(tree.nested === 1, "the section's paragraph sits inside the section, inside the chapter");
  assert(tree.closedAtFirst === 0, 'nothing is folded when the panel opens');
  assert(tree.secName.trim() === 'The Spillway' && tree.chName.trim() === 'Water & Waste',
         'the panel names the chapter and the section');

  // each folds on its own
  await page.click('#toclist .tocgrp > .tocch > .tocfold');
  const folded = await page.evaluate(() => {
    const g = document.querySelector('#toclist .tocgrp');
    const body = g.querySelector(':scope > .tocbody');
    return {closed: g.classList.contains('closed'),
            shown: body.getClientRects().length > 0,
            head: g.querySelector(':scope > .tocch').getClientRects().length > 0};
  });
  assert(folded.closed && !folded.shown && folded.head,
         'folding a chapter hides what is under it and leaves its own row');

  await page.click('#tocopenall');
  const opened = await page.evaluate(() => document.querySelectorAll('#toclist .closed').length);
  assert(opened === 0, 'open all opens every chapter and every section');
  await page.click('#tocfoldall');
  const allShut = await page.evaluate(() => ({
    closed: document.querySelectorAll('#toclist .closed').length,
    groups: document.querySelectorAll('#toclist .tocgrp, #toclist .tocsgrp').length,
  }));
  assert(allShut.closed === allShut.groups, 'fold all folds every one of them');

  // (c) a search opens what it searches
  await page.fill('#tocq', 'child');
  const found = await page.evaluate(() => {
    const vis = [...document.querySelectorAll('#toclist a.toce')].filter(a => !a.hidden);
    return {n: vis.length, onScreen: vis.length ? vis[0].getClientRects().length > 0 : false};
  });
  assert(found.n >= 1 && found.onScreen,
         'a match is shown even though everything had been folded away');
  await page.fill('#tocq', '');

  // (d) the sheet is really on screen
  await page.click('#tocsecs');
  const sheet = await page.evaluate(() => {
    const box = document.getElementById('secbox');
    const r = box.getBoundingClientRect();
    const cs = getComputedStyle(box);
    const mid = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return {
      hidden: box.hidden, position: cs.position,
      inView: r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight && r.right <= innerWidth,
      hit: !!(mid && box.contains(mid)),
      backdrop: !document.getElementById('secback').hidden,
      chapters: document.querySelectorAll('#secch option').length,
      paras: document.querySelectorAll('#secpara option').length,
      listed: (document.getElementById('seclist').textContent || '').includes('The Spillway'),
      doLabel: document.getElementById('secdo').textContent,
    };
  });
  assert(!sheet.hidden && sheet.position === 'fixed' && sheet.inView && sheet.hit && sheet.backdrop,
         'the sections sheet is a sheet on screen, not a block at the foot of the body');
  assert(sheet.chapters === 1 && sheet.paras === 2,
         'it offers the chapters and the paragraphs the book actually has');
  assert(sheet.listed, 'and lists the section that exists, to remove it');

  // picking the paragraph that already opens one offers a rename, not a second
  await page.selectOption('#secpara', '1:2');
  const onExisting = await page.evaluate(() => ({
    label: document.getElementById('secdo').textContent,
    name: document.getElementById('secname').value,
  }));
  assert(/rename/.test(onExisting.label) && onExisting.name === 'The Spillway',
         'picking a paragraph that already starts a section offers to rename it');

  await page.keyboard.press('Escape');
  const shut = await page.evaluate(() => document.getElementById('secbox').hidden);
  assert(shut, 'Escape closes the sheet');

  // (e) the boundary the player would stop at
  const bounds = await page.evaluate(() => ({
    list: typeof BOUNDS === 'undefined' ? null : BOUNDS.slice(),
    crossesIntoSection: crossesBound(1, 2),
    staysInside: crossesBound(2, 3),
    button: !!document.getElementById('stopbnd'),
    offAtFirst: !document.getElementById('stopbnd').classList.contains('on'),
  }));
  assert(Array.isArray(bounds.list) && bounds.list.length === 2,
         `the build counted the chapter and the section as boundaries (${JSON.stringify(bounds.list)})`);
  assert(bounds.crossesIntoSection && !bounds.staysInside,
         'stepping into the section crosses a boundary; stepping along inside it does not');
  assert(bounds.button && bounds.offAtFirst,
         'the stop-at-a-change button is there and is off by default, so a book plays through');

  assert(errors.length === 0, 'the page threw nothing: ' + errors.join(' | '));
  await page.close();
} finally {
  await browser.close();
  await server.shutdown();
}
console.log(`\nsections: ${passed} checks passed`);
