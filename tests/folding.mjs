import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome PARSEH_PYTHON=python3 deno run --allow-all tests/folding.mjs
//
// A run of paragraphs folded away (lib/reading.py, written into reading.json
// beside the book).  What has to hold, and is covered nowhere else:
//
//   * the BUILD knows nothing about it -- it emits every paragraph as it
//     always did and hands the page two tables, PARAS and FOLDED -- so what
//     is folded is folded at runtime, which is what lets a chapter fetched
//     later be folded by the same call;
//   * the text of a folded run is not shown, and ONE bar stands in its place,
//     which opens the run on the page without unfolding it in the book;
//   * READING WALKS PAST IT WITH NO AUDIO AT ALL.  The fixture has no
//     recording, so nextWithAudio has nothing to offer and the arrows are
//     walking the text: that is the path this file exists to hold, because
//     the other one (a narration, the playhead jumping the run) is the one
//     anybody would think to try.
//
// The book is built for real and served off disk; the two doors are answered
// here, since what they do to reading.json is tests/test_reading.py's affair.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const TMP = await Deno.makeTempDir({prefix: 'parseh-folding-'});
const td = new TextDecoder();
const assert = (v, m) => { if (!v) throw Error(m); };
const eq = (got, want, m) => {
  if (JSON.stringify(got) !== JSON.stringify(want))
    throw Error(m + ': got ' + JSON.stringify(got) + ' want ' + JSON.stringify(want));
};
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function py(code, ...args) {
  const o = await new Deno.Command(PY, {args: ['-c', code, ...args],
                                        stdout: 'piped', stderr: 'piped'}).output();
  if (!o.success) throw Error(td.decode(o.stderr) || td.decode(o.stdout));
  return td.decode(o.stdout);
}

// ---- a real book, with paragraph 1 of chapter 1 folded away ---------------
const BOOK = TMP + '/books/english/mini-en';
await py([
  'import os, shutil, sys',
  'sys.path.insert(0, "lib")',
  'import reading',
  'dest = sys.argv[1]',
  'os.makedirs(os.path.dirname(dest), exist_ok=True)',
  'shutil.copytree("tests/fixtures/books/english/mini-en", dest,',
  '                ignore=shutil.ignore_patterns("reader"))',
  'reading.collapse(dest, "1:1", "1:1", True)',
  'print(reading.load(dest))',
].join('\n'), BOOK);
{
  const o = await new Deno.Command(PY, {args: ['lib/tex2html.py', '--book', BOOK],
                                        stdout: 'piped', stderr: 'piped'}).output();
  if (!o.success) throw Error('the book did not build: ' + td.decode(o.stderr));
}

// ---- the doors, answered here --------------------------------------------
// what reading.json would hold; the page is told and folds without a reload
let DOC = {free: [], collapsed: [['1:1', '1:1']]};
const posted = [];

const MIME = {html: 'text/html', js: 'text/javascript', css: 'text/css',
              json: 'application/json'};
async function file(route, path) {
  let body;
  try { body = await Deno.readTextFile(path); }
  catch (_) { return route.fulfill({status: 404, body: 'no such file'}); }
  return route.fulfill({body, contentType: MIME[path.split('.').pop()]
                                           || 'application/octet-stream'});
}

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN')});
const page = await browser.newPage();
page.on('pageerror', e => { throw Error('the page threw: ' + e.message); });
await page.route('**/*', async route => {
  const url = new URL(route.request().url());
  const p = url.pathname;
  if (route.request().method() === 'POST' && p.includes('__reading/')) {
    const body = JSON.parse(route.request().postData() || '{}');
    posted.push([p.endsWith('fold') ? 'fold' : 'free', body]);
    if (p.endsWith('fold')) {
      const a = body.from, b = body.to || body.from;
      DOC = {...DOC, collapsed: body.on === false
        ? DOC.collapsed.filter(r => !(r[0] <= a && a <= r[1]))
        : [...DOC.collapsed, [a, b]].sort()};
    } else {
      const free = new Set(DOC.free);
      if (body.on) free.add(body.para); else free.delete(body.para);
      DOC = {...DOC, free: [...free].sort()};
    }
    return route.fulfill({contentType: 'application/json',
      body: JSON.stringify({ok: true, reading: DOC, reader: {ok: true}})});
  }
  // the lib/ scripts are reached from the reader by a long relative path
  const lib = p.match(/\/lib\/([^/]+)$/);
  if (lib) return file(route, root + '/lib/' + lib[1]);
  const inBook = p.replace(/^.*\/reader\//, '');
  return file(route, BOOK + '/reader/' + (inBook || 'index.html'));
});
await page.goto('https://parseh.test/books/english/mini-en/reader/');
await page.waitForFunction(() => typeof PARAS !== 'undefined');

// ---- the build stayed out of it ------------------------------------------
const built = await page.evaluate(() => ({
  paras: PARAS, folded: FOLDED,
  divs: [...document.querySelectorAll('.para[data-p]')].map(e => e.dataset.p),
}));
eq(built.paras, [['1:1', 0, 1], ['1:2', 2, 3]],
   'the build names every paragraph and the subparagraphs it holds');
eq(built.folded, [['1:1', '1:1']], 'and hands the page the runs, unapplied');
eq(built.divs, ['1:1', '1:2'],
   'every paragraph is in the page -- a folded one is hidden, never left out');

// ---- what the reader shows -----------------------------------------------
const shown = await page.evaluate(() => {
  const el = k => document.querySelector('.para[data-p="' + k + '"]');
  const bars = [...document.querySelectorAll('.foldbar')];
  return {
    foldedClass: el('1:1').classList.contains('folded'),
    hidden: el('1:1').offsetParent === null,
    otherShown: el('1:2').offsetParent !== null,
    bars: bars.length,
    runs: bars.map(b => b.dataset.run),
    says: bars.map(b => b.querySelector('button').textContent),
  };
});
assert(shown.foldedClass, 'the folded paragraph carries the class');
assert(shown.hidden, 'and its text is not shown');
assert(shown.otherShown, 'while the paragraph that is not folded still is');
eq(shown.bars, 1, 'one bar stands in the run\'s place');
eq(shown.runs, ['1:1|1:1'], 'and it says which run it is for');
eq(shown.says, ['1 paragraph folded away'], 'counted, and in the singular');

// ---- THE WALK, with no audio at all --------------------------------------
const walk = await page.evaluate(() => ({
  anyAudio: SUBS.some(s => s[0] != null),
  inFolded: [inFolded(0), inFolded(1), inFolded(2), inFolded(3)],
  withAudio: nextWithAudio(0, 1),
  forward: nextStop(0, 1),
  back: nextStop(3, -1),
}));
assert(!walk.anyAudio, 'the fixture has no recording -- that is the point here');
eq(walk.inFolded, [true, true, false, false],
   'the run covers the subparagraphs of paragraph 1 and no others');
eq(walk.withAudio, -1, 'nothing has a time, so the audio walk offers nothing');
eq(walk.forward, 2, 'and the text walk steps over the folded run, not into it');
eq(walk.back, 3, 'backwards from the end stands on the last unfolded one');

// the arrows themselves, not only the function behind them
await page.keyboard.press('ArrowRight');
await page.waitForFunction(() => cur >= 0, null, {timeout: 5000});
eq(await page.evaluate(() => cur), 2,
   'ArrowRight from the top of a book whose first paragraph is folded lands '
   + 'past the run');

// ---- the bar opens the run without unfolding it in the book ---------------
await page.click('.foldbar button');
const opened = await page.evaluate(() => {
  const el = document.querySelector('.para[data-p="1:1"]');
  return {opened: el.classList.contains('opened'),
          visible: el.offsetParent !== null,
          stillFolded: el.classList.contains('folded'),
          says: document.querySelector('.foldbar button').textContent,
          walk: nextStop(0, 1)};
});
assert(opened.opened && opened.visible, 'the bar shows the run on the page');
assert(opened.stillFolded, 'which is a look, not an unfolding');
eq(opened.says, 'fold them away again', 'and the bar says how to put it back');
eq(opened.walk, 2, 'reading still walks past it -- the book is still folded');
await page.click('.foldbar button');
assert(await page.evaluate(() =>
  !document.querySelector('.para[data-p="1:1"]').classList.contains('opened')),
  'and it folds away again');

// A FOLD THAT MERGES INTO A RUN SOMEBODY HAS OPEN LEAVES IT OPEN.  Folding an
// adjacent run joins the two, which gives the run new ends -- and the open
// state used to be kept on the bar under an id made of those ends, so the
// text shut under the reader who was in the middle of it.
const kept = await page.evaluate(() => {
  folded = [['1:1', '1:1']]; foldRanges(); applyFold();
  openRun(foldedRun('1:1'), true);
  const before = document.querySelector('.para[data-p="1:1"]').classList.contains('opened');
  folded = [['1:1', '1:2']]; foldRanges(); applyFold();   // a fold merges in
  const el = document.querySelector('.para[data-p="1:1"]');
  const bar = document.querySelector('.foldbar');
  return {before: before, after: el.classList.contains('opened'),
          barOpen: !!bar && bar.classList.contains('open')};
});
assert(kept.before, 'the run opens when the bar is pressed');
assert(kept.after, 'and a fold merging into it does not shut it under the reader');
assert(kept.barOpen, 'the bar for the bigger run says so too');
// and an unfolded run does not spring open if it is ever folded again
const sprang = await page.evaluate(() => {
  openRun(foldedRun('1:1'), false);
  folded = []; foldRanges(); applyFold();
  folded = [['1:1', '1:1']]; foldRanges(); applyFold();
  return document.querySelector('.para[data-p="1:1"]').classList.contains('opened');
});
assert(!sprang, 'a run folded a second time comes back folded, not open');
// put the book back as the rest of this file expects it
await page.evaluate(() => { folded = [['1:1', '1:1']]; foldRanges(); applyFold(); });

// ---- the sheet ------------------------------------------------------------
await page.click('#fold');
assert(await page.evaluate(() => !$('#fdbox').hidden), 'fold opens the sheet');

// AND A PERSON CAN SEE IT.  Every one of these questions is here because the
// first version of this file did not ask it: the sheet had no CSS at all, so
// it opened as a plain block in the normal flow at the foot of the body --
// !hidden was perfectly true, and Playwright scrolls an element into view
// before acting on it, so selecting and clicking inside it worked too.  The
// button looked dead to the person using it and the test was green.
const seen = await page.evaluate(() => {
  const box = $('#fdbox'), back = $('#fdback');
  const r = box.getBoundingClientRect();
  const cs = getComputedStyle(box);
  const hit = document.elementFromPoint(Math.round(r.left + r.width / 2),
                                        Math.round(r.top + r.height / 2));
  return {
    position: cs.position,
    zIndex: +cs.zIndex || 0,
    inView: r.top >= 0 && r.left >= 0
            && r.bottom <= innerHeight + 1 && r.right <= innerWidth + 1,
    sized: r.width > 200 && r.height > 80,
    onTop: !!hit && (hit === box || box.contains(hit)),
    backdrop: getComputedStyle(back).position === 'fixed'
              && back.getBoundingClientRect().width >= innerWidth,
    listLaidOut: getComputedStyle($('#fdlist')).display === 'flex',
  };
});
eq(seen.position, 'fixed', 'it is a sheet, not a block at the foot of the page');
assert(seen.inView, 'it is inside the viewport, where the reader is looking');
assert(seen.sized, 'and it has a size');
assert(seen.onTop, 'and the point at the middle of it hits the sheet itself');
assert(seen.zIndex >= 80, 'it stands above the text and the gloss cloud');
assert(seen.backdrop, 'its backdrop covers the page, as every other sheet does');
assert(seen.listLaidOut, '.nrow is scoped to #narrbox, so this sheet needs a rule '
                         + 'of its own or its rows are never laid out');

// AND IT STAYS ON SCREEN WHEREVER YOU ARE IN THE BOOK.  This is what `fixed`
// means to the person reading: a sheet in the normal flow sits at the foot of
// the body, which in a two-paragraph fixture is still in view -- so the rect
// check above passes for a short book even when the sheet is broken, and only
// this one holds for the long book somebody actually reads.
await page.evaluate(() => scrollTo(0, document.body.scrollHeight));
await sleep(80);
const afterScroll = await page.evaluate(() => {
  const r = $('#fdbox').getBoundingClientRect();
  return {inView: r.top >= 0 && r.bottom <= innerHeight + 1, top: Math.round(r.top)};
});
assert(afterScroll.inView,
       'the sheet is still on screen after scrolling the book (top=' + afterScroll.top + ')');
await page.evaluate(() => scrollTo(0, 0));
eq(await page.evaluate(() => $('#fdfrom').options.length), 2,
   'both paragraphs of the book are offered');
eq(await page.evaluate(() => $('#fdlist').querySelectorAll('button').length), 1,
   'and the run already folded is listed, with its own unfold');
await page.selectOption('#fdfrom', '1:2');
await page.selectOption('#fdto', '1:2');
await page.click('#fddo');
await page.waitForFunction(() =>
  document.querySelectorAll('.foldbar').length === 2, null, {timeout: 5000});
eq(posted.at(-1), ['fold', {from: '1:2', to: '1:2', on: true}],
   'the sheet asks the server, which is where the decision is kept');
eq(await page.evaluate(() => nextStop(0, 1)), -1,
   'with every paragraph folded there is nowhere left to stand');

// and unfolding from the sheet's own list puts one back
await page.click('#fdlist button');
await page.waitForFunction(() =>
  document.querySelectorAll('.foldbar').length === 1, null, {timeout: 5000});
eq(await page.evaluate(() =>
  document.querySelector('.para[data-p="1:1"]').classList.contains('folded')),
  false, 'the run named by the list is shown again');

// ---- it behaves like a sheet, not like markup that happens to be visible --
// Escape, which the x button's own tooltip promises; the book underneath held
// still while it is up; and Enter that does not submit the form and reload
// the reader out from under the reading place.
await page.keyboard.press('Escape');
assert(await page.evaluate(() => $('#fdbox').hidden), 'Escape closes the sheet');
assert(await page.evaluate(() => $('#fdback').hidden), 'and takes its backdrop with it');

await page.click('#fold');
await page.evaluate(() => document.activeElement && document.activeElement.blur());
const stood = await page.evaluate(() => cur);
await page.keyboard.press('ArrowRight');
await page.keyboard.press(' ');
eq(await page.evaluate(() => cur), stood,
   'the arrows and space belong to the sheet while it is over the page');
assert(await page.evaluate(() => !$('#fdbox').hidden),
       'and space did not close it or start the recording underneath');

const wasAt = page.url();
await page.focus('#fdfrom');
await page.keyboard.press('Enter');
await sleep(200);
eq(page.url(), wasAt, 'Enter does not submit the form and reload the book');
assert(await page.evaluate(() => typeof PARAS !== 'undefined'),
       'and the page is still the page it was');
await page.keyboard.press('Escape');

// ---- the chunk sheet's own checkbox ---------------------------------------
await page.evaluate(() => { fdOpen(false); openChunk(0); });
const sheet = await page.evaluate(() => ({
  rowShown: !$('#chfreerow').hidden,
  checked: $('#chfree').checked,
  para: paraOfChunk(0),
}));
assert(sheet.rowShown, 'a chunk that sits in a paragraph is offered the mark');
eq(sheet.para, '1:1', 'the paragraph the build named on the .para');
assert(!sheet.checked, 'and nothing is marked in this book yet');

// and it LOOKS like a checkbox: #chbox styles every input in the sheet to
// width:100% with a border and padding, which turned this one into a wide
// empty box that did not read as a tick at all
const tick = await page.evaluate(() => {
  const r = $('#chfree').getBoundingClientRect();
  return {w: Math.round(r.width), h: Math.round(r.height)};
});
assert(tick.w > 0 && tick.w < 40 && tick.h < 40,
       'the exemption control is a checkbox, not a full-width bordered box ('
       + tick.w + '×' + tick.h + ')');

// ---- a jump into a folded run has to land somewhere -----------------------
// .para.folded is display:none and so has no box at all, and scrollIntoView
// on a boxless element does nothing: the contents entry for a folded
// paragraph was a control that visibly did nothing when pressed.
await page.evaluate(() => { if (typeof closeChunk === 'function') closeChunk(); });
await page.click('#toc');
await page.click('#toclist a.toce[href="#par-1-2"]');
const jumped = await page.evaluate(() => {
  const el = document.querySelector('.para[data-p="1:2"]');
  const bar = document.querySelector('.foldbar[data-run="1:2|1:2"]');
  return {opened: el.classList.contains('opened'),
          visible: el.offsetParent !== null,
          stillFolded: el.classList.contains('folded'),
          says: bar && bar.querySelector('button').textContent};
});
assert(jumped.opened && jumped.visible,
       'jumping to a folded paragraph from the contents shows it');
assert(jumped.stillFolded, 'and shows it without unfolding it in the book');
eq(jumped.says, 'fold them away again', 'the bar agrees that it stands open');

// ---- how an old book gains any of this ------------------------------------
// Everything here is written into the page at build time, so a book built
// before the feature has none of it until its reader is written again -- and
// asking for the PDF to get it wants LaTeX and two lualatex passes.
assert(await page.evaluate(() => !!document.getElementById('buildhtml')),
       'the reader can be rebuilt on its own from the page');
const asked = await page.evaluate(() => new Promise(res => {
  const real = Parseh.buildBook;
  Parseh.buildBook = (url, what, opts) => {
    Parseh.buildBook = real;
    res({url: url, what: what, kind: opts && opts.what});
  };
  document.getElementById('buildhtml').click();
}));
eq(asked.kind, 'html', 'and it asks for the reader alone, not for a LaTeX build');
eq(asked.url, '__build', 'through the door bookbuild already had');

// ---- the place does not stay inside a run folded under it -----------------
// Folding is a decision made about what you are reading, so the run being
// read is the ordinary one to fold.  The mark has to walk out of it -- and
// walk BACKWARDS when the run reaches the end of the book, which a
// forward-only walk left sitting inside the fold, to be saved there and read
// back on the next open.
const walked = await page.evaluate(() => {
  const out = {};
  playSub(PARAT['1:2'][0], false);          // stand in the last paragraph
  out.stood = cur;
  folded = [['1:2', '1:2']]; foldRanges(); applyFold();
  fdOpen(true); fdOpen(false);              // fold it under yourself
  out.after = cur;
  out.stillInside = cur >= 0 && inFolded(cur);
  folded = [['1:1', '1:2']]; foldRanges(); applyFold();
  playSub(0, false);
  fdOpen(true); fdOpen(false);              // now fold the whole book
  out.whenNothingIsLeft = cur;
  return out;
});
assert(!walked.stillInside,
       'closing the sheet leaves the place outside the run just folded (stood '
       + walked.stood + ', ended ' + walked.after + ')');
eq(walked.whenNothingIsLeft, -1,
   'and with every paragraph folded it stands nowhere rather than inside a fold');
// put the book back as the rest of this file expects it
await page.evaluate(() => {
  folded = [['1:2', '1:2']]; foldRanges(); applyFold();
});

// ---- an old book's shape: a paragraph written in two files ----------------
// ch1.tex and ch1b.tex are BOTH chapter 1 -- verify_book.py says so and
// texwrite agrees -- so a paragraph continued in the second file is emitted
// as one .para per piece, each carrying the same key.  The page has to put
// the pieces back together: keeping only the last entry would hide the text
// of both halves and walk past only the tail of it, which is the shape an
// old edition is most likely to have and the fixture cannot show.
const BOOK2 = TMP + '/books/english/cont';
await py('import shutil, sys; shutil.copytree(sys.argv[1], sys.argv[2],'
         + ' ignore=shutil.ignore_patterns("reader"))',
         'tests/fixtures/books/english/mini-en', BOOK2);
await Deno.writeTextFile(BOOK2 + '/ch1b.tex',
  '\\parnum{2.3}\n\\begin{frank}\n'
  + '\\ch{}{and went home.}{\u0259n w\u025bnt ho\u028am}{}{and went home.}\n'
  + '\\end{frank}\n\\parend\n');
{
  const mp = BOOK2 + '/main.tex';
  const s = await Deno.readTextFile(mp);
  assert(s.includes('\\input{ch1.tex}'), 'main.tex names its chapters by \\input');
  await Deno.writeTextFile(mp, s.replace('\\input{ch1.tex}',
                                         '\\input{ch1.tex}\n\\input{ch1b.tex}'));
  // the decision is the book's, so it is on disk before the build
  await Deno.writeTextFile(BOOK2 + '/reading.json',
    JSON.stringify({free: [], collapsed: [['1:2', '1:2']]}));
  const o = await new Deno.Command(PY, {args: ['lib/tex2html.py', '--book', BOOK2],
                                        stdout: 'piped', stderr: 'piped'}).output();
  if (!o.success) throw Error('the split book did not build: ' + td.decode(o.stderr));
}
const page2 = await browser.newPage();
page2.on('pageerror', e => { throw Error('the split book threw: ' + e.message); });
await page2.route('**/*', async route => {
  const p = new URL(route.request().url()).pathname;
  const lib = p.match(/\/lib\/([^/]+)$/);
  if (lib) return file(route, root + '/lib/' + lib[1]);
  return file(route, BOOK2 + '/reader/' + (p.replace(/^.*\/reader\//, '') || 'index.html'));
});
await page2.goto('https://parseh.test/books/english/cont/reader/');
await page2.waitForFunction(() => typeof PARAS !== 'undefined');
const split = await page2.evaluate(() => ({
  paras: PARAS,
  stretch: PARAT['1:2'],
  inFolded: [0, 1, 2, 3, 4].map(i => inFolded(i)),
  forward: nextStop(0, 1),
  afterIt: nextStop(2, 1),
}));
eq(split.paras, [['1:1', 0, 1], ['1:2', 2, 3], ['1:2', 4, 4]],
   'the build writes one entry per piece, both under the one name');
eq(split.stretch, [2, 4],
   'and the page merges them into the whole stretch the paragraph covers');
eq(split.inFolded, [false, false, true, true, true],
   'so folding it covers every subparagraph of both pieces, not just the last');
eq(split.forward, 0, 'the paragraph before it is still a place to stand');
eq(split.afterIt, -1, 'and there is nothing after it that is not folded');

// AND THE TAIL OF THE RUN ARRIVES IN A FILE OF ITS OWN.  ch1b.tex is a second
// chapter object under label 1, so the build leaves it in ch-1.html and the
// page fetches it: this run has half its paragraphs in the page at load and
// half in a part that lands later, and applyFold runs again with that section
// as its scope.  ONE BAR, not two -- the bar for this run stands outside that
// scope, so it is not removed and must not be drawn a second time, which is
// what the question asked of the document rather than of the scope is for --
// and the half that has just arrived comes in folded rather than open.
await page2.waitForFunction(
  () => document.querySelectorAll('.para[data-p="1:2"]').length === 2,
  null, {timeout: 10000});
const landed = await page2.evaluate(() => {
  const pieces = [...document.querySelectorAll('.para[data-p="1:2"]')];
  return {
    pieces: pieces.length,
    allFolded: pieces.every(el => el.classList.contains('folded')),
    bars: document.querySelectorAll('.foldbar').length,
    mine: document.querySelectorAll('.foldbar[data-run="1:2|1:2"]').length,
  };
});
eq(landed.pieces, 2, 'both pieces of the paragraph are in the page once the part lands');
assert(landed.allFolded, 'and both are folded, the piece that arrived late included');
eq(landed.bars, 1, 'one bar in the whole document, not one per piece');
eq(landed.mine, 1, 'and it is the bar for this run');

// ---- a paragraph the build could not name, inside a folded run ------------
// A .tex whose NAME carries no chapter number names no paragraph, so the build
// gives it no key and no data-p: it cannot be folded, and nothing hides it.
// Put one BETWEEN two files of the same chapter and fold across it, and the
// run's first and last subparagraph numbers now straddle a paragraph that is
// still on the page.  Reading must not step over it.
const BOOK3 = TMP + '/books/english/aside';
await py('import shutil, sys; shutil.copytree(sys.argv[1], sys.argv[2],'
         + ' ignore=shutil.ignore_patterns("reader"))',
         'tests/fixtures/books/english/mini-en', BOOK3);
await Deno.writeTextFile(BOOK3 + '/characters.tex',
  '\\parstart{9.1}{The names in this book}\n\\parnum{9.1}\n\\begin{frank}\n'
  + '\\ch{}{The names in this book}{\u00f0\u0259 ne\u026amz}{}{the names in this book}\n'
  + '\\end{frank}\n\\parend\n');
await Deno.writeTextFile(BOOK3 + '/ch1b.tex',
  '\\parnum{3.1}\n\\begin{frank}\n'
  + '\\ch{}{and went home.}{\u0259n w\u025bnt ho\u028am}{}{and went home.}\n'
  + '\\end{frank}\n\\parend\n');
{
  const mp = BOOK3 + '/main.tex';
  const s = await Deno.readTextFile(mp);
  await Deno.writeTextFile(mp, s.replace('\\input{ch1.tex}',
    '\\input{ch1.tex}\n\\input{characters.tex}\n\\input{ch1b.tex}'));
  await Deno.writeTextFile(BOOK3 + '/reading.json',
    JSON.stringify({free: [], collapsed: [['1:1', '1:3']]}));
  const o = await new Deno.Command(PY, {args: ['lib/tex2html.py', '--book', BOOK3],
                                        stdout: 'piped', stderr: 'piped'}).output();
  if (!o.success) throw Error('the aside book did not build: ' + td.decode(o.stderr));
}
const page3 = await browser.newPage();
page3.on('pageerror', e => { throw Error('the aside book threw: ' + e.message); });
await page3.route('**/*', async route => {
  const p = new URL(route.request().url()).pathname;
  const lib = p.match(/\/lib\/([^/]+)$/);
  if (lib) return file(route, root + '/lib/' + lib[1]);
  return file(route, BOOK3 + '/reader/' + (p.replace(/^.*\/reader\//, '') || 'index.html'));
});
await page3.goto('https://parseh.test/books/english/aside/reader/');
await page3.waitForFunction(() => typeof PARAS !== 'undefined');
const aside = await page3.evaluate(() => ({
  paras: PARAS,
  inFolded: [0, 1, 2, 3, 4, 5].map(i => inFolded(i)),
  stand: nextStop(4, 1),
}));
eq(aside.paras, [['1:1', 0, 1], ['1:2', 2, 3], ['1:3', 5, 5]],
   'the file that is not a chapter is given no key, so its paragraph is not '
   + 'in the table at all -- and the run\'s numbers straddle it');
eq(aside.inFolded, [true, true, true, true, false, true],
   'the paragraph nothing hides is NOT walked over, though its subparagraph '
   + 'lies between the first and the last of the folded run');
eq(aside.stand, 4, 'and it is a place to stand');

await browser.close();
await Deno.remove(TMP, {recursive: true});
console.log('folding.mjs: all good');
