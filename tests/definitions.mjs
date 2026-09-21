import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome deno run --allow-all tests/definitions.mjs
// English explained in English, in both readers: the "definitions" switch and
// the switch that translates them.  A copy of the English fixture book,
// glossed in Italian with its first chunk left unglossed, is built with
// lib/tex2html.py; the player is drawn over the English fixture video, glossed
// in Italian.  Every request either page makes is answered here -- the
// dictionary's by a stand-in that defines each word the way Wiktionary
// defines `run`, the translation model's by a stand-in that writes "IT: "
// before whatever it is given.  A dictionary that translates rather than
// defines is the one tests/book_words.mjs and tests/player_words.mjs drive,
// and it is asked for once more here: the switches must not appear for it.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const PY = Deno.env.get('PARSEH_PYTHON') || 'python3';
const TMP = await Deno.makeTempDir({prefix: 'parseh-definitions-'});
const td = new TextDecoder();
async function py(code, ...args) {
  const o = await new Deno.Command(PY, {args: ['-c', code, ...args], stdout: 'piped', stderr: 'piped'}).output();
  if (!o.success) throw Error(td.decode(o.stderr) || td.decode(o.stdout));
  return td.decode(o.stdout);
}
const assert = (v, m) => { if (!v) throw Error(m); };
const eq = (got, want, m) => {
  if (JSON.stringify(got) !== JSON.stringify(want))
    throw Error(m + ': got ' + JSON.stringify(got) + ' want ' + JSON.stringify(want));
};
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, what, ms = 15000) {
  const t = Date.now();
  for (;;) {
    const v = await fn();
    if (v) return v;
    if (Date.now() - t > ms) throw Error('timed out: ' + what);
    await sleep(50);
  }
}

// the English book glossed in Italian, its first chunk nobody has glossed
const SETUP = String.raw`
import json, os, shutil, subprocess, sys
sys.path.insert(0, 'lib')
import languages
d = os.path.join(sys.argv[1], 'mini-en')
shutil.copytree('tests/fixtures/books/english/mini-en', d,
                ignore=shutil.ignore_patterns('reader', '.reader-key'))
b = json.load(open(os.path.join(d, 'book.json'), encoding='utf-8'))
b['gloss'] = 'it'
json.dump(b, open(os.path.join(d, 'book.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
ch = os.path.join(d, 'ch1.tex')
t = open(ch, encoding='utf-8').read()
old = r'\ch{}{The old man}{ðə oʊld mæn}{\dw{old}{oʊld} having lived a long time}{the old man}'
assert old in t
open(ch, 'w', encoding='utf-8').write(t.replace(old, r'\ch{}{The old man}{}{}{}'))
subprocess.run([sys.executable, 'lib/tex2html.py', '--book', d], check=True, capture_output=True)
print(json.dumps({'en': languages.LANGS['en'].as_json(),
                  'it': languages.gloss_or_default('it').as_json()}))
`;
const REG = JSON.parse(await py(SETUP, TMP));

// Wiktionary's `run`, cut down: the three senses a hit carries, and the rest
const SENSES = ['To move swiftly.', 'To go at a fast pace.', 'To cover a distance by running.'];
const MARKS = ['intransitive', 'intransitive', 'transitive'];
const MORE = ['To compete in a race.', 'To manage a business.', 'To flee.'];
// the first as a verb's senses can carry them: its part of speech and the
// person and number of the form it was written under are no labels
const MORE_MARKS = ['intransitive,transitive,verb,third-person,singular', 'obj:acc', 'obsolete'];
const SHOWN = ['(intransitive) To move swiftly.', '(intransitive) To go at a fast pace.',
               '(transitive) To cover a distance by running.'];
const REST = ['(intransitive, transitive) To compete in a race.', 'To manage a business.',
              '(obsolete) To flee.'];
let DEFINES = true;
// A COMPOUND'S VERB ENTRY, as lib/verbs builds one: the light verb's own
// entry with no meaning, the \bw it still wants named in `missing`, and the
// whole compound in `compound` -- ONE entry, the \vb and the \bw run
// together with nothing between them.  Turned on for one check and off
// again, so every other hit here stays what it was.
let COMPOUND = false;
const VB = {lemma: 'zadan', here: 'ZADAN (zadan)', tex: '\\vb{zadan}{}{zan}{}{zad}{}{}',
            plain: 'zadan · pres. zan · past zad', line: 'pres. zan · past zad',
            complete: false, missing: ['bw for labxand after it: to smile'],
            compound: {name: 'compound verb', whole: 'labxand zadan', sound: '',
                       mean: 'to smile', word: 'labxand',
                       bw: '\\bw{labxand}{}{to smile}',
                       tex: '\\vb{zadan}{}{zan}{}{zad}{}{}\\bw{labxand}{}{to smile}',
                       plain: 'labxand zadan to smile (zadan · pres. zan · past zad)',
                       complete: true, missing: []}};
function answer(body, seen) {
  seen.push(body);
  if (body.about) return {ok: true, help: true, available: true, corpus_available: false,
                          definitions: DEFINES, source: {source: 'Wiktionary', licence: 'CC BY-SA 4.0'}};
  const hit = {entry: 1, headword: 'run', translit: 'rʌn', pos: 'verb', senses: SENSES, marks: MARKS, buried: 3};
  if (COMPOUND) hit.vb = VB;
  if (body.senses === 'all') Object.assign(hit, {more: MORE, more_marks: MORE_MARKS});
  return {ok: true, words: [{word: 'run', hits: [hit], tried: ['run']}], pairs: [], pairs_more: false};
}
const FAKE_MT = `window.MTCALLS = [];
window.ParsehMT = {
  has: (a, b) => Promise.resolve(a === 'en' && b === 'it' ? {source: 'a test model', engine: 'none'} : null),
  translate: (a, b, t) => {
    MTCALLS.push(t);
    const one = s => 'IT: ' + s;
    return Promise.resolve(Array.isArray(t) ? t.map(one) : one(t));
  },
  align: () => null, marked: out => [{text: out, here: false}], why: () => ''
};`;
const asked = (calls, list) => calls.some(c => Array.isArray(c) && JSON.stringify(c) === JSON.stringify(list));

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN'), headless: true});
const errors = [];
try {
// ======== the book reader ========
{
  const page = await browser.newPage();
  page.on('pageerror', e => { errors.push('book: ' + e.message); console.log('PAGE ERROR', e.message); });
  const seen = [];
  const MIME = {html: 'text/html', js: 'text/javascript', css: 'text/css', json: 'application/json'};
  await page.route('**/*', async route => {
    const req = route.request(), url = new URL(req.url());
    if (url.hostname !== 'parseh.test') return route.abort();
    const path = decodeURIComponent(url.pathname);
    if (path.endsWith('/reader/__lookup')) return route.fulfill({json: answer(req.postDataJSON(), seen)});
    if (path.endsWith('/lib/mt.js')) return route.fulfill({body: FAKE_MT, contentType: 'text/javascript'});
    if (path === '/anki/decks') return route.fulfill({json: []});
    try {
      return route.fulfill({body: await Deno.readTextFile(path),
                            contentType: MIME[path.split('.').pop()] || 'application/octet-stream'});
    } catch (_) { return route.fulfill({body: '{}', contentType: 'application/json'}); }
  });
  const hover = async () => {
    await page.mouse.move(1, 1);
    await page.locator('.p1 [data-c="0"]').hover();
    await page.waitForFunction(() => cloudC === 0 && !document.querySelector('#cloud').hidden);
    await page.waitForSelector('#cloud .dict .dhead2');
  };
  const shownDefs = () => page.evaluate(() =>
    [...document.querySelectorAll('#cloud .ddef')].filter(d => !d.hidden)
      .map(d => [...d.childNodes].filter(n => !(n.classList && n.classList.contains('dtr'))).map(n => n.textContent).join('')));
  await page.goto(`http://parseh.test${TMP}/mini-en/reader/index.html`, {waitUntil: 'load'});
  await page.waitForFunction(() => DICT.ready && MT.ready);
  eq(await page.evaluate(() => [defBtn.hidden, defBtn.disabled, defBtn.classList.contains('on'),
                                defMtBtn.hidden, defMtBtn.disabled, defMtBtn.textContent]),
     [false, true, false, false, true, 'in italian'],
     'English glossed in Italian: both switches offered, off, and greyed while the dictionary is off');
  // as dict/en.db has them: `thee`, a pronoun of Multicultural London English, `old` as a noun
  eq(await page.evaluate(() => [
       Parseh.senseLabels('archaic,literary,objective,second-person,singular', 'pron'),
       Parseh.senseLabels('Multicultural-London-English,personal,pronoun,slang', 'pron'),
       Parseh.senseLabels('countable,invariable,plural,plural-only,uncountable,obj:dat', 'noun'),
       Parseh.senseLabels('', 'verb')]),
     [['archaic', 'literary'], ['Multicultural London English', 'slang'],
      ['countable', 'plural only', 'uncountable'], []],
     'a sense\'s labels, less the form a table lends it, its part of speech and lookup\'s own notation');
  await page.evaluate(() => { setHover(true); dictSwitch(DICT, dictBtn, 'dict', true); });
  eq(await page.evaluate(() => [defBtn.disabled, defMtBtn.disabled]), [false, true],
     'the dictionary on: the definitions can be turned on, their translation not yet');

  await hover();
  let r = await page.evaluate(() => ({
    senses: document.querySelectorAll('#cloud .dict .dsense').length,
    head: document.querySelector('#cloud .dict .dhead2').textContent,
    notes: [...document.querySelectorAll('#cloud .dict .ddict .dnone')].map(n => n.textContent)}));
  eq([r.senses, r.head], [0, 'run rʌn'], 'the definitions off: the entry without its senses, and with its head');
  assert(r.notes.some(t => t.includes('explains these words in English') && t.includes('definitions')),
         'and a word on where the definitions are: ' + JSON.stringify(r.notes));
  assert(seen.filter(b => !b.about).length && seen.filter(b => !b.about).every(b => !('senses' in b)),
         'nothing past the first three is asked for');

  await page.evaluate(() => defBtn.click());
  await hover();
  await page.waitForSelector('#cloud .ddef');
  eq(await shownDefs(), SHOWN, 'on: the first three definitions, each with its labels');
  r = await page.evaluate(() => ({
    hidden: [...document.querySelectorAll('#cloud .ddef')].filter(d => d.hidden).length,
    lang: document.querySelector('#cloud .ddef').getAttribute('lang'),
    more: document.querySelector('#cloud .ddefmore').textContent,
    notes: document.querySelectorAll('#cloud .dict .ddict .dnone').length,
    kept: DICT.cache.has('0\n\nall'), mt: defMtBtn.disabled, on: defBtn.classList.contains('on')}));
  eq(r, {hidden: 3, lang: 'en', more: '3 more definitions', notes: 0, kept: true, mt: false, on: true},
     'the rest one click away, the whole entry kept apart, the translation now possible');
  assert(seen.some(b => b.senses === 'all' && b.text === 'The old man'), 'the whole entry is asked for');

  await page.evaluate(() => document.querySelector('#cloud .ddefmore').click());
  eq((await shownDefs()).slice(3), REST, 'a click: the rest, in order, a tag with a colon no label');
  eq(await page.evaluate(() => [document.querySelector('#cloud .ddefmore').hidden,
                                !document.querySelector('#cloud').hidden && cloudC === 0]),
     [true, true], 'the button gone, and the cloud still open');

  await page.evaluate(() => defMtBtn.click());
  await hover();
  await until(() => page.evaluate(() => {
    const t = [...document.querySelectorAll('#cloud .ddef .dtr')];
    return t.length === 3 && t.every(x => !x.classList.contains('dwaiting'));
  }), 'the definitions translated');
  r = await page.evaluate(() => ({
    tr: [...document.querySelectorAll('#cloud .ddef .dtr')].map(t => [t.textContent, t.getAttribute('lang')]),
    src: document.querySelector('#cloud .ddict .dsrc').textContent, calls: MTCALLS}));
  eq(r.tr, SENSES.map(s => ['IT: ' + s, 'it']), 'each definition that shows, in Italian, under it');
  assert(r.src.includes('the definitions put into Italian by a test model'), 'and the source line says by what: ' + r.src);
  assert(asked(r.calls, SENSES), 'the three read in one call: ' + JSON.stringify(r.calls));
  await page.evaluate(() => document.querySelector('#cloud .ddefmore').click());
  await until(() => page.evaluate(() => {
    const t = [...document.querySelectorAll('#cloud .ddef .dtr')];
    return t.length === 6 && t.every(x => !x.classList.contains('dwaiting'));
  }), 'the rest translated as they show');
  eq(await page.evaluate(() => MTCALLS[MTCALLS.length - 1]), MORE, 'and only the rest read for them');

  r = await page.evaluate(async () => {
    DEFT.clear(); DEFT_FAILED = false;
    const p = preDefinitions();
    if (!p) return 'nothing to read';
    await p;
    return [...DEFT.entries()];
  });
  eq(r, SENSES.map(s => [s, 'IT: ' + s]), 'the look-ahead reads the first three of the entries ahead, in one call');

  await page.evaluate(() => defBtn.click());
  await hover();
  eq(await page.evaluate(() => [document.querySelectorAll('#cloud .ddef, #cloud .dsense, #cloud .dtr').length,
                                defMtBtn.disabled, defMtBtn.classList.contains('on')]),
     [0, true, true], 'off again: no definitions, their translation greyed and still remembered');
  await page.reload({waitUntil: 'load'});
  await page.waitForFunction(() => DICT.ready && MT.ready);
  eq(await page.evaluate(() => [DICT.on, DICT.defs, DICT.defsMt, defBtn.classList.contains('on'),
                                defMtBtn.classList.contains('on')]),
     [true, false, true, false, true], 'all three remembered for the book');

  // THE SHEET'S SOURCES: a switch of their own over the dictionary's rows --
  // the sheet lies over the header -- a row's sense read in Italian under it,
  // and the buttons that put that
  r = await page.evaluate(async () => {
    const until = async (f, m) => {
      for (let i = 0; i < 300; i++) { if (f()) return; await new Promise(res => setTimeout(res, 20)); }
      throw Error('timed out: ' + m);
    };
    openChunk(0, document.querySelector('.row[data-c="0"]')); sideShow(true);
    await until(() => { const t = document.querySelector('#chsrcbody .sdef .dtr');
                        return t && !t.classList.contains('dwaiting'); }, 'the sense in Italian');
    const sw = document.querySelector('#chsrcbody .sdefbar .sdefmt');
    const out = {sw: [sw.textContent, sw.classList.contains('on')],
                 tr: [...document.querySelectorAll('#chsrcbody .sdef .dtr')].map(t => [t.textContent, t.getAttribute('lang')]),
                 btns: [...document.querySelectorAll('#chsrcbody .sdef .sput button')].map(b => b.textContent)};
    CH.en.value = ''; CH.voc.value = '';
    for (const b of document.querySelectorAll('#chsrcbody .sdef .sput button')) b.click();
    out.put = [CH.voc.value, CH.en.value];
    sw.click();
    out.off = [DICT.defsMt, sw.classList.contains('on'), document.querySelector('#chsrcbody .sdef').hidden,
               defMtBtn.classList.contains('on')];
    sw.click();
    out.on = [DICT.defsMt, document.querySelector('#chsrcbody .sdef').hidden];
    closeChunk();
    return out;
  });
  eq(r.sw, ['in italian', true], 'the sheet has the switch over the dictionary\'s rows, on as remembered');
  eq(r.tr, [['IT: ' + SENSES[0], 'it']], 'the row\'s sense read in Italian under it');
  eq(r.btns, ['\\dw → vocabulary', 'meaning →'], 'with the buttons that put the translation');
  eq(r.put, ['\\dw{run}{rʌn} IT: ' + SENSES[0], 'IT: ' + SENSES[0]], 'and they put it');
  eq(r.off, [false, false, true, false], 'the sheet\'s switch turns it off everywhere');
  eq(r.on, [true, false], 'and on again');

  // A VERB THAT IS MORE THAN ONE WORD HAS ITS OWN BUTTON.  The light verb
  // and the word it carries are ONE entry, not two: the \bw runs straight
  // onto the \vb.  The plain button is untouched -- it still puts the light
  // verb alone, dashed, for whoever wants exactly that.
  COMPOUND = true;
  await page.reload({waitUntil: 'load'});
  await page.waitForFunction(() => DICT.ready && MT.ready);
  const cmp = await page.evaluate(async () => {
    const until = async (f, m) => {
      for (let i = 0; i < 300; i++) { if (f()) return; await new Promise(res => setTimeout(res, 20)); }
      throw Error('timed out: ' + m);
    };
    openChunk(0, document.querySelector('.row[data-c="0"]')); sideShow(true);
    await until(() => [...document.querySelectorAll('#chsrcbody .sput button')]
                      .some(b => b.textContent.includes('vocabulary')), 'the verb button');
    const all = [...document.querySelectorAll('#chsrcbody .sput button')];
    const one = t => all.find(e => e.textContent.includes(t));
    const v = document.querySelector('#chvoc');
    const press = b => {
      v.value = ''; v.dispatchEvent(new Event('input', {bubbles: true}));
      b.click();
      return {label: b.textContent, title: b.title,
              dashed: b.classList.contains('sgap'), value: v.value};
    };
    return {comp: press(one('compound verb')), vb: press(one('\\vb →')),
            labels: all.map(b => b.textContent),
            says: /to fill in/.test(document.querySelector('#chsrcbody').textContent)};
  });
  assert(cmp.labels.indexOf('compound verb → vocabulary') >= 0 &&
         cmp.labels.indexOf('compound verb → vocabulary') <
         cmp.labels.indexOf('\\vb → vocabulary'),
     'a compound gets a button of its own, before the plain one: ' + cmp.labels.join(' | '));
  eq(cmp.comp.value, '\\vb{zadan}{}{zan}{}{zad}{}{}\\bw{labxand}{}{to smile}',
     'it puts the whole compound in as ONE entry, the \\bw run onto the \\vb');
  assert(/is one verb written in two words, not two vocabulary entries/.test(cmp.comp.title) &&
         cmp.comp.title.includes('labxand zadan'),
     'and says in so many words what the pair is: ' + cmp.comp.title);
  eq(cmp.comp.dashed, false, 'nothing is left to fill in, so it is not drawn unfinished');
  eq(cmp.vb.value, '\\vb{zadan}{}{zan}{}{zad}{}{}',
     'the plain button is untouched: the light verb alone');
  eq([cmp.vb.dashed, cmp.says], [true, true],
     'still dashed, and the row still names the \bw under "to fill in"');
  COMPOUND = false;

  DEFINES = false;
  await page.reload({waitUntil: 'load'});
  await page.waitForFunction(() => DICT.ready && MT.ready);
  await page.evaluate(() => { setHover(true); defsSwitch('defs', true); });
  await hover();
  eq(await page.evaluate(() => [defBtn.hidden, defMtBtn.hidden, document.querySelectorAll('#cloud .dsense').length,
                                document.querySelectorAll('#cloud .ddef, #cloud .dtr').length]),
     [true, true, 3, 0], 'a dictionary that translates: no switches, and its senses as they always were, whatever is remembered');
  DEFINES = true;
  await page.close();
  console.log('Book reader: offered for English only, off and greyed; the entry without its senses; the definitions ' +
              'with their labels and the rest on a click; translated where they show; the look-ahead; remembered: passed');
}

// ======== the player ========
{
  const context = await browser.newContext({viewport: {width: 1280, height: 900}});
  const page = await context.newPage();
  page.on('pageerror', e => { errors.push('player: ' + e.message); console.log('PAGE ERROR', e.message); });
  const FIXV = 'tests/fixtures/videos/english/eN5wX7zA9bC';
  const ann = JSON.parse(await Deno.readTextFile(FIXV + '/annotations.json'));
  const cfg = {id: 'eN5wX7zA9bC', ann: '/fixture/en/annotations.json', lang: REG.en, gloss: REG.it,
               local: true, notes: '', editable: {}};
  const html = (await Deno.readTextFile('youtube/lib/player.html')).replace('__YTFRANK__', JSON.stringify(cfg))
    .replaceAll('__BASE__', '/youtube').replaceAll('__LANG__', 'en').replaceAll('__LANG_DIR__', 'ltr');
  const seen = [];
  await page.route('**/*', async route => {
    const req = route.request(), url = new URL(req.url()), p = url.pathname;
    if (url.hostname !== 'parseh.test') return route.abort();
    const json = j => route.fulfill({json: j});
    if (p === '/blank') return route.fulfill({body: '<!doctype html><title>blank</title>', contentType: 'text/html'});
    if (p === '/video') return route.fulfill({body: html, contentType: 'text/html'});
    if (p === cfg.ann) return json(ann);
    if (p === cfg.ann.replace('annotations.json', 'video.json'))
      return route.fulfill({body: await Deno.readTextFile(FIXV + '/video.json'), contentType: 'application/json'});
    if (p.endsWith('/lib/mt.js')) return route.fulfill({body: FAKE_MT, contentType: 'text/javascript'});
    if (p.startsWith('/mt/')) return route.fulfill({status: 404, body: 'no model'});
    if (p === '/anki/decks') return json([]);
    if (p === '/lookup/api/decompositions') return json({ok: true, packs: []});
    if (p === '/youtube/api/lookup') return json(answer(req.postDataJSON(), seen));
    try {
      const path = root + decodeURIComponent(p), ext = path.split('.').pop();
      const mime = {html: 'text/html', js: 'text/javascript', css: 'text/css', json: 'application/json'}[ext] ||
                   'application/octet-stream';
      return route.fulfill({body: await Deno.readTextFile(path), contentType: mime});
    } catch (_) { return route.fulfill({body: '{}', contentType: 'application/json'}); }
  });
  const buttons = () => page.evaluate(() => ['#defmode', '#defmt'].map(s => {
    const b = document.querySelector(s);
    return [b.hidden, b.disabled, b.classList.contains('on'), b.textContent];
  }));
  // caption 2's second phrase, "or three for five", has nobody's vocabulary
  const hover = async () => {
    await page.mouse.move(1, 1);
    await page.waitForFunction(() => document.querySelector('#cloud').hidden);
    await page.locator('.seg[data-i="2"] .w[data-j="1"]').hover();
    await page.waitForFunction(() => !document.querySelector('#cloud').hidden);
    await page.waitForSelector('#cloud .dict .dhead2');
  };
  const shownDefs = () => page.evaluate(() =>
    [...document.querySelectorAll('#cloud .ddef')].filter(d => !d.hidden)
      .map(d => [...d.childNodes].filter(n => !(n.classList && n.classList.contains('dtr'))).map(n => n.textContent).join('')));
  const click = sel => page.evaluate(sel => document.querySelector(sel).click(), sel);
  const load = async () => {
    await page.goto('http://parseh.test/video');
    await page.waitForSelector('.seg .fa .w');
    await page.waitForFunction(() => !document.querySelector('#dictmode').hidden && !document.querySelector('#defmt').hidden);
  };
  await page.goto('http://parseh.test/blank');
  await page.evaluate(() => localStorage.clear());
  await load();
  eq(await buttons(), [[false, true, false, 'definitions'], [false, true, false, 'in italian']],
     'the player offers both for English, off, and greyed while the dictionary is off');
  await click('#dictmode');
  eq((await buttons()).map(b => b[1]), [false, true], 'the dictionary on: the definitions can be turned on');

  await hover();
  let r = await page.evaluate(() => ({
    senses: document.querySelectorAll('#cloud .dict .dsense').length,
    head: document.querySelector('#cloud .dict .dhead2').textContent,
    notes: [...document.querySelectorAll('#cloud .dict .ddict .dnone')].map(n => n.textContent)}));
  eq([r.senses, r.head], [0, 'run rʌn'], 'the definitions off: the entry without its senses');
  assert(r.notes.some(t => t.includes('explains these words in English')), 'and a word on where they are: ' + JSON.stringify(r.notes));
  assert(seen.filter(b => !b.about).every(b => !('senses' in b)), 'nothing past the first three asked for');

  await click('#defmode');
  await hover();
  await page.waitForSelector('#cloud .ddef');
  eq(await shownDefs(), SHOWN, 'on: the first three definitions with their labels');
  eq(await page.evaluate(() => [[...document.querySelectorAll('#cloud .ddef')].filter(d => d.hidden).length,
                                document.querySelector('#cloud .ddef').getAttribute('lang'),
                                document.querySelector('#cloud .ddefmore').textContent]),
     [3, 'en', '3 more definitions'], 'the rest one click away');
  assert(seen.some(b => b.senses === 'all' && b.text === 'or three for five'), 'the whole entry is asked for');
  await click('#cloud .ddefmore');
  eq((await shownDefs()).slice(3), REST, 'a click: the rest, in order');
  eq(await page.evaluate(() => [document.querySelector('#cloud .ddefmore').hidden, !document.querySelector('#cloud').hidden]),
     [true, true], 'the button gone and the cloud still open: the click was inside it');

  await click('#defmt');
  await hover();
  await until(() => page.evaluate(() => {
    const t = [...document.querySelectorAll('#cloud .ddef .dtr')];
    return t.length === 3 && t.every(x => !x.classList.contains('dwaiting'));
  }), 'the definitions translated');
  r = await page.evaluate(() => ({
    tr: [...document.querySelectorAll('#cloud .ddef .dtr')].map(t => [t.textContent, t.getAttribute('lang')]),
    src: document.querySelector('#cloud .ddict .dsrc').textContent}));
  eq(r.tr, SENSES.map(s => ['IT: ' + s, 'it']), 'each definition that shows, in Italian, under it');
  assert(r.src.includes('the definitions put into Italian by a test model'), 'and said by what: ' + r.src);
  await click('#cloud .ddefmore');
  await until(() => page.evaluate(() => {
    const t = [...document.querySelectorAll('#cloud .ddef .dtr')];
    return t.length === 6 && t.every(x => !x.classList.contains('dwaiting'));
  }), 'the rest translated as they show');
  eq(await page.evaluate(() => MTCALLS[MTCALLS.length - 1]), MORE, 'only the rest read for them');

  // remembered, and read ahead with no panel open
  await page.mouse.move(1, 1);
  await load();
  eq(await buttons(), [[false, false, true, 'definitions'], [false, false, true, 'in italian']],
     'both remembered for every video');
  await until(() => page.evaluate(SENSES => MTCALLS.some(c => Array.isArray(c) && SENSES.every(s => c.includes(s))), SENSES),
              'the look-ahead reading the definitions ahead');

  // THE EDITOR'S SOURCES: the switch over the dictionary's rows, the sense in
  // Italian under its row, and the buttons that put that
  await hover();
  await click('#cloud .mkedit');
  await page.waitForSelector('#cloud .eside', {state: 'attached'});
  if (await page.evaluate(() => document.querySelector('#cloud .eside').hidden)) await click('#cloud .esrc');
  await until(() => page.evaluate(() => {
    const t = document.querySelector('#cloud .esrcbody .sdef .dtr');
    return t && !t.classList.contains('dwaiting');
  }), 'the editor\'s sense in Italian');
  r = await page.evaluate(() => {
    const sw = document.querySelector('#cloud .esrcbody .sdefbar .sdefmt');
    const out = {sw: [sw.textContent, sw.classList.contains('on')],
      tr: [...document.querySelectorAll('#cloud .esrcbody .sdef .dtr')].map(t => [t.textContent, t.getAttribute('lang')]),
      btns: [...document.querySelectorAll('#cloud .esrcbody .sdef .sput button')].map(b => b.textContent)};
    const en = document.querySelector('#cloud .ef[data-f="en"]'), voc = document.querySelector('#cloud .ef[data-f="voc"]');
    en.value = ''; voc.value = '';
    for (const b of document.querySelectorAll('#cloud .esrcbody .sdef .sput button')) b.click();
    out.put = [voc.value, en.value];
    sw.click();
    out.off = [sw.classList.contains('on'), document.querySelector('#cloud .esrcbody .sdef').hidden,
               document.querySelector('#defmt').classList.contains('on'), !document.querySelector('#cloud').hidden];
    sw.click();
    out.on = [sw.classList.contains('on'), document.querySelector('#cloud .esrcbody .sdef').hidden];
    return out;
  });
  eq(r.sw, ['in italian', true], 'the editor has the switch over the dictionary\'s rows, on as remembered');
  eq(r.tr, [['IT: ' + SENSES[0], 'it']], 'the row\'s sense read in Italian under it');
  eq(r.btns, ['→ vocabulary', 'meaning →'], 'with the buttons that put the translation');
  eq(r.put, ['run rʌn IT: ' + SENSES[0], 'IT: ' + SENSES[0]], 'and they put it');
  eq(r.off, [false, true, false, true], 'the editor\'s switch turns it off everywhere, and the editor stays open');
  eq(r.on, [true, false], 'and on again');
  await click('#cloud .ecancel');

  await click('#defmode');
  await hover();
  eq(await page.evaluate(() => document.querySelectorAll('#cloud .ddef, #cloud .dsense, #cloud .dtr').length), 0,
     'off again: no definitions');
  eq((await buttons()).map(b => [b[1], b[2]]), [[false, false], [true, true]], 'their translation greyed, and remembered');

  DEFINES = false;
  await click('#defmode');
  await load().catch(() => {});
  await page.waitForFunction(() => !document.querySelector('#dictmode').hidden);
  await hover();
  eq(await page.evaluate(() => [document.querySelector('#defmode').hidden, document.querySelector('#defmt').hidden,
                                document.querySelectorAll('#cloud .dsense').length,
                                document.querySelectorAll('#cloud .ddef, #cloud .dtr').length]),
     [true, true, 3, 0], 'a dictionary that translates: no switches, and its senses as they always were');
  await context.close();
  console.log('Player: offered for English only, off and greyed; the entry without its senses; the definitions with ' +
              'their labels and the rest on a click; translated where they show; read ahead; remembered: passed');
}
assert(!errors.length, 'page errors: ' + errors.join('; '));
} finally {
  await browser.close();
  await Deno.remove(TMP, {recursive: true}).catch(() => {});
}
