// SPDX-License-Identifier: GPL-3.0-or-later
// Browser test of ⤢ Enlarge (app.js openCardZoom): the enlarged flashcard is
// the card on the page, only bigger.  Against the REAL routes
// (markdown/app/server.py, htmlgen) on a temporary library and exercises
// store (tests/decks_harness.py, studio mode), documents written through
// POST /api/docs: Persian (a vocabulary card, a picture card, an opposites
// card, a jolly card whose fields are several lines of [ … ]{tl} and of
// [ … ]{la}, one of them long enough to be taller than the window, a card
// with a large photograph), English (a Latin block justified and one set on
// the right, a table, a Jolly card with a picture 40% of its field wide and
// a recording), Japanese, and cards with footnotes.
//   a) every card, on each of its faces, on a desktop (1400x900) and on a
//      phone (390x844): each field, each paragraph and each line of text is
//      measured where it is drawn, relative to the card's own box, on the
//      page and enlarged -- its text-align, its direction, its box, how many
//      lines it breaks into and where each line starts and ends -- and the
//      two must be the same; the enlarged card is larger (half as large again
//      on the desktop) and inside the window; a card taller than the window
//      opens at its top and scrolls to its end.  On the phone a card that
//      fits is laid out narrower than on the page and magnified to the
//      window's width: it is compared with the card on the page laid out at
//      that same width, it is a tenth larger at least than the card
//      magnified whole would be, and it takes the window's height (or is
//      twice as large, or any narrower a line that is whole on the page
//      would break, or something in it -- the table -- would be wider than
//      its box, or a picture or player narrower than on the page); its
//      photograph is drawn half as large again at least.  One too tall even
//      so, or that could be only a little larger, is magnified whole to the
//      window's width.  On the phone every stretch of text that is one line
//      on the page -- a field, a paragraph, a line of a Jolly field up to
//      its ⏎ -- is one line enlarged.  Every picture and player is drawn as
//      many times its size on the page as the text is, at least: the 40%
//      picture and the recording beside them as on the page.  Nowhere is
//      anything in an enlarged card wider than its box that is not on the
//      page.
//   b) turning the enlarged card turns the one on the page and keeps its size
//   c) the page's typography followed: "justify" turned off and a larger
//      text size, a Latin block is not justified on the page, nor enlarged
//   d) the editor's preview, both sides shown at once, enlarged the same
//   e) the window resized with the card open: it is measured again, at the
//      width the card on the page has now; in that narrow window a card
//      taller than it fills its width and scrolls down, never sideways
//   f) a card with footnotes, on the desktop and on the phone: nothing
//      scrolls sideways with every cloud hidden, and each cloud, shown by
//      hovering its mark, is inside the window with its tail on its mark --
//      one at the right end of a line, one at the start of a line set on
//      the left
//   CHROME_BIN=... PARSEH_PYTHON=python3 deno run --allow-all tests/card_zoom.mjs
//   SHOTS=<dir> saves every card on the page and enlarged
import {chromium} from 'npm:playwright-core@1.52.0';
import {Buffer} from 'node:buffer';

const root = await Deno.realPath(new URL('..', import.meta.url));
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';
const SHOTS = Deno.env.get('SHOTS') || '';
let passed = 0;
const assert = (v, m) => { if (!v) throw Error('FAIL: ' + m); passed++; console.log('  ok', m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

// a 60x40 picture: small enough to be drawn at its own size on the card
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAADwAAAAoCAIAAAAt2Q6oAAAAO0lEQVR42u3OQQkAAAgEsItjOjMZ1RQ+hMECLNXzTqSlpaWlpaWlpaWlpaWlpaWlpaWlpaWlpaWlpS8tUIta5t7QVXgAAAAASUVORK5CYII=', 'base64');

const PERSIAN = `---
title: Cards in Persian
target: fa
lang: en
---

:::exercise flashcard
card-type: vocab
target: [خداحافظ]{tl}
transliteration: xodâhâfez
meaning: goodbye
context: said on leaving, to anyone, at any hour of the day or of the night
:::

:::exercise flashcard
card-type: jolly
front-primary: [سلام]{tl}
front-secondary: |
  [
    مریم: آیپدِ جدید خریدی؟⏎
    لیلا: آره.⏎
    مریم: مبارکه. چطوره؟⏎
    لیلا: خیلی خوبه. کار کردن باهاش آسونه و سُرعَتِشَم خیلی بالاست، مثلِ آیفونه.
    ]{tl}
back-secondary: |
  [
    Maryam: Did you buy the new iPad?⏎
    Leila: Yeah.⏎
    Maryam: Congratulations. How is it?⏎
    Leila: It is really good. It is easy to work with and it is really fast too, just like the iPhone.
    ]{la}
front-secondary-size: 175
front-secondary-shade: primary
:::

:::exercise flashcard
card-type: vocab
front-image: images/swatch.png
target: [آبی]{tl}
transliteration: âbi
meaning: blue, the colour of the sky and of the sea on a clear day
:::

:::exercise flashcard
card-type: opposites
target: [بزرگ]{tl}
transliteration: bozorg
opposite: [کوچک]{tl}
opposite-transliteration: kuchak
notes: big and small, said of things and of people
:::

:::exercise flashcard
card-type: jolly
front-secondary: |
  [
    لیلا شانزده ساله است. وقتی به دبیرستان می رود، آیفون و آیپدش را با خود می برد. لیلا در طولِ راه از همه چیز عکس می گیرد، ایمیل هایش را می خواند و به موسیقی گوش می دهد.⏎
    بر خلافِ پدرش، او وسایل و تکنولوژی های جدید را خیلی دوست دارد و کارکردن با آنها برایش آسان است. گاهی به والدینش استفاده از فناوریِ های جدید را یاد می دهد و حتّی بیشتر و بهتر از معلّم هایش دربارۀ استفاده از این ابزارها می داند! به نظرِ لیلا، کلاسِ بدونِ کامپیوتر و تکنولوژی کسل کننده است، امّا به نظرِ بعضی از معلّم هایش، استفادۀ زیاد از این نوع فناوری ها در کلاس و به ویژه بازی هایِ کامپیوتری اتلافِ وقت است.⏎
    لیلا و همکلاسی هایش به راحتی اطّلاعات را از وبسایت ها پیدا می کنند و حتّی تمرین هایشان را آنلاین انجام می دهند.⏎
    آنها روزها و ماه ها منتظرِ ابزارهایِ جدید می مانند. وقتی مدلِ جدیدی می آید، به فروشگاه هایِ بزرگ مانند اپل می روند، ساعت ها در صف می ایستند و در همان روزِ اوّل، وسیلۀ دوست داشتنیِ جدیدشان را می خرند.
    ]{tl}
back-secondary: |
  [
    Leyla is sixteen years old. When she goes to school, she takes her iPhone and iPad with her. All along the way Leyla takes photos of everything, reads her e-mails and listens to music.
    ]{la}
front-secondary-size: 175
front-secondary-shade: primary
:::

:::exercise flashcard
card-type: vocab
front-image: images/photo.png
target: [عکس]{tl}
transliteration: aks
meaning: a photograph
:::
`;

const ENGLISH = `---
title: Cards in English
target: en
lang: it
---

:::exercise flashcard
card-type: vocab
target: [to take off]{tl}
transliteration: tu teɪk ɒf
meaning: decollare, togliersi (un vestito)
context: The plane took off at six; he took off his coat as soon as he came in.
:::

:::exercise flashcard
card-type: jolly
front-primary: [to look forward to]{tl}
back-primary: |
  [
    Right-aligned block, a second line of it.
    ]{la align=right}
back-secondary: |
  [
    Aspettare qualcosa con piacere: si usa con il gerundio o con un nome, mai con l'infinito, e di solito al presente progressivo nelle lettere.⏎
    I'm looking forward to seeing you.
    ]{la}
:::

:::exercise flashcard
card-type: vocab
target: [Carbonic acid (H2CO3)]{tl}
meaning: acido carbonico, in acqua
context: The plane took off at six.
:::

:::exercise flashcard
card-type: jolly
front-primary: [a table]{tl}
back-secondary: |
  | single | plural | article |
  |---|---|---|
  | child | kids | the |
  | mouse | mice | a |
:::

:::exercise flashcard
card-type: jolly
front-primary: |
  ![An apple](images/starter-apple.svg){width=40 align=center}
front-secondary: What is it? Say it aloud, with its article.
back-primary: [an apple]{tl}
back-secondary: |
  ![A chime for a right answer](audio/starter-chime.mp3)
:::
`;

const JAPANESE = `---
title: Cards in Japanese
target: ja
lang: en
---

:::exercise flashcard
card-type: vocab
target: [速い]{kana:はやい translit:hayai}
reading: はやい
transliteration: hayai
meaning: fast, quick
context: of motion; not 早い, which is early
:::

:::exercise flashcard
card-type: jolly
front-primary: [足が速い]{tl}
front-secondary: |
  [
    古池や⏎
    蛙飛び込む⏎
    水の音、これは新しいノートで、まだ何も書いてありません。長い行が折り返すかどうかを見るための文です。
    ]{tl}
back-secondary: |
  [
    The old pond; a frog jumps in; the sound of the water. A long line to see whether it wraps on the card.
    ]{la}
:::
`;

async function startHarness() {
  const proc = new Deno.Command(python, {args: [root + '/tests/decks_harness.py', 'studio'], cwd: root,
                                         stdout: 'piped', stderr: 'inherit'}).spawn();
  const reader = proc.stdout.pipeThrough(new TextDecoderStream()).getReader();
  let buf = '', info = null;
  while (!info) {
    const {value, done} = await reader.read();
    if (done) throw Error('harness exited before READY:\n' + buf);
    buf += value;
    const m = buf.match(/READY (\{.*\})\n/);
    if (m) info = JSON.parse(m[1]);
  }
  (async () => { for (;;) { const r = await reader.read(); if (r.done) break; } })();
  return {proc, info};
}

/* A card as it is drawn: every field, paragraph, picture and player in it,
   and every line of its text, as fractions of the card's own width measured
   from its left edge (and its top), with the text-align and direction each
   one has.  Relative to the card, so a card drawn larger reads the same. */
function drawnCard(card) {
  const R = card.getBoundingClientRect();
  const x = v => (v - R.left) / R.width, y = v => (v - R.top) / R.width;
  const TEXT = '.fa-par, .la-par, .fa-display, .ex-target-block, .ex-field-line, .ex-card-blocks > p';
  const items = [];
  for (const el of card.querySelectorAll('.ex-card-field, ' + TEXT + ', figure, img, audio, .ex-card-play, .ex-card-hint')) {
    if (el.closest('[hidden]')) continue;
    const r = el.getBoundingClientRect();
    if (!r.width) continue;
    const cs = getComputedStyle(el);
    const lines = [];
    // the lines of a paragraph, or of a field that is one line of words
    // (a footnote's cloud is no line of it: hidden on the page, and out of
    // the layout until it is shown enlarged)
    if (el.matches(TEXT) || (el.matches('.ex-card-field') && !el.querySelector(TEXT + ', figure, img'))) {
      const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      const range = document.createRange();
      for (let t; (t = walk.nextNode());) {
        if (t.parentElement.closest('.fncloud')) continue;
        range.selectNodeContents(t);
        for (const q of range.getClientRects()) {
          if (!q.width) continue;
          const line = lines.find(l => Math.abs(l.t - q.top) < q.height / 2);
          if (line) { line.l = Math.min(line.l, q.left); line.r = Math.max(line.r, q.right); }
          else lines.push({t: q.top, l: q.left, r: q.right});
        }
      }
    }
    items.push({what: (el.className && String(el.className).split(' ')[0]) || el.tagName.toLowerCase(),
                align: cs.textAlign, dir: cs.direction, l: x(r.left), r: x(r.right), t: y(r.top), b: y(r.bottom),
                lines: lines.map(l => [x(l.l), x(l.r), y(l.t)])});
  }
  return {w: R.width, h: R.height, l: R.left, r: R.right, t: R.top, b: R.bottom, items};
}

/* The page's card against the enlarged one: nothing may differ but the size.
   A line starts and ends where it did to within half a percent of the
   card's width (two pixels of a card as wide as a desktop window). */
const NEAR = 0.005;
function sameCard(page, zoom, where) {
  const bad = [];
  if (page.items.length !== zoom.items.length)
    bad.push(`${page.items.length} things drawn on the page, ${zoom.items.length} enlarged`);
  page.items.forEach((a, i) => {
    const b = zoom.items[i];
    if (!b) return;
    if (a.what !== b.what) { bad.push(`#${i}: ${a.what} on the page, ${b.what} enlarged`); return; }
    if (a.align !== b.align) bad.push(`${a.what}: text-align ${a.align} on the page, ${b.align} enlarged`);
    if (a.dir !== b.dir) bad.push(`${a.what}: direction ${a.dir} on the page, ${b.dir} enlarged`);
    for (const k of ['l', 'r', 't', 'b'])
      if (Math.abs(a[k] - b[k]) > NEAR) bad.push(`${a.what}: box ${k} ${a[k].toFixed(3)} on the page, ${b[k].toFixed(3)} enlarged`);
    if (a.lines.length !== b.lines.length) bad.push(`${a.what}: ${a.lines.length} lines on the page, ${b.lines.length} enlarged`);
    else a.lines.forEach((la, j) => {
      const lb = b.lines[j];
      if (la.some((v, k) => Math.abs(v - lb[k]) > NEAR))
        bad.push(`${a.what} line ${j + 1}: ${la.map(v => v.toFixed(3))} on the page, ${lb.map(v => v.toFixed(3))} enlarged`);
    });
  });
  const lines = page.items.reduce((n, it) => n + it.lines.length, 0);
  assert(!bad.length, `${where}: every field and each of its ${lines} lines drawn as on the page` +
         (bad.length ? ':\n      ' + bad.slice(0, 12).join('\n      ') : ''));
}

/* The enlarged card against the card on the page.  Magnified whole at the
   page card's width, it must be the page's card as it is; laid out narrower
   (a phone), the page's card laid out at that same width -- set on it for
   the measure and taken off again -- which is what the copy is at the
   page's size, before it is magnified.  Returns how it was laid out. */
async function sameAsPage(page, card, onPage, where) {
  const big = await page.locator(ZOOMED).evaluate(drawnCard);
  const width = await page.locator(ZOOMED).evaluate(c => c.style.width);
  const pageWidth = await card.evaluate(c => getComputedStyle(c).width);
  if (width === pageWidth) { sameCard(onPage, big, where); return {relaid: false}; }
  await card.evaluate((c, w) => { c.style.width = w; }, width);
  const narrower = await card.evaluate(drawnCard);
  await card.evaluate(c => { c.style.width = ''; });
  sameCard(narrower, big, `${where}, laid out ${parseFloat(width).toFixed(1)} px wide (the card on the page ${pageWidth})`);
  return {relaid: true};
}

const FOOTNOTES = `---
title: Cards with footnotes
target: fa
lang: en
---

:::exercise flashcard
card-type: vocab
target: [سلام]{tl}
meaning: hello, the everyday greeting said at any hour of the day or night[^a]
context: a long line of context so that the footnote mark sits close to the right edge of the card here[^b]
:::

:::exercise flashcard
card-type: jolly
front-primary: [خداحافظ]{tl}
back-secondary: |
  [
    A[^c] block set on the left, its mark at the very start of its first line, by the card's left edge.
    ]{la align=left}
:::

[^a]: A long footnote about greetings in Persian, which goes on and on so that its cloud is as wide as a cloud may be, thirty ems or so, and wraps.
[^b]: Another long footnote, placed at the right edge of the card, whose cloud would stick out past the card's edge when it is centred on its mark.
[^c]: A footnote at the start of a line set on the left, whose cloud would stick out past the left edge of the window when it is centred on its mark.
`;

const {proc, info} = await startHarness();
const B = `http://127.0.0.1:${info.port}`;
async function send(method, path, body, type = 'application/json') {
  const r = await fetch(B + path, {method, headers: {'Content-Type': type}, body});
  const data = await r.json();
  if (!r.ok) throw Error(`${method} ${path}: ${r.status} ${JSON.stringify(data)}`);
  return data;
}
const docs = {};
for (const [name, md] of [['Persian', PERSIAN], ['English', ENGLISH], ['Japanese', JAPANESE], ['Footnotes', FOOTNOTES]])
  docs[name] = (await send('POST', '/api/docs', JSON.stringify({markdown: md}))).meta.id;
await send('POST', `/api/docs/${docs.Persian}/images?name=swatch.png`, PNG, 'image/png');

const browser = await chromium.launch({executablePath: Deno.env.get('CHROME_BIN') || undefined, headless: true});
const pageErrors = [];
{
  // a photograph as a camera takes it, 1600x1200: shrunk on the card
  const page = await browser.newPage();
  const b64 = await page.evaluate(() => {
    const c = document.createElement('canvas');
    c.width = 1600; c.height = 1200;
    const g = c.getContext('2d');
    g.fillStyle = '#4a7'; g.fillRect(0, 0, 1600, 1200);
    g.fillStyle = '#fff'; g.fillRect(200, 200, 1200, 800);
    return c.toDataURL('image/png').split(',')[1];
  });
  await send('POST', `/api/docs/${docs.Persian}/images?name=photo.png`, Buffer.from(b64, 'base64'), 'image/png');
  await page.close();
}
const ready = async page => {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => [...document.querySelectorAll('#sheet img')].every(i => i.complete));
};
const cardAt = (page, i) => page.locator('#sheet .ex-flashcard').nth(i);
const ZOOMED = '.ex-zoom-overlay .ex-zoom-stage .ex-flashcard';
async function enlarge(page, i) {
  await page.locator('#sheet .exercise:has(.ex-flashcard)').nth(i).locator('.ex-card-zoom').click();
  await page.waitForSelector(ZOOMED);
  await page.evaluate(() => document.fonts.ready);
  await sleep(150);                       // a ResizeObserver's second look
}
async function closeZoom(page) {
  await page.keyboard.press('Escape');
  await page.waitForSelector('.ex-zoom-overlay', {state: 'detached'});
}
/* Where the enlarged card is against the window, and how much larger it is:
   `times` as wide as on the page, magnified `zoom` times (laid out narrower,
   a card is magnified more than it is widened), its taller side `tallest`
   high against the `room` the window has for it, across and down. */
const placement = (page, onPage) => page.evaluate(([sel, w]) => {
  const copy = document.querySelector(sel), c = copy.getBoundingClientRect();
  const s = document.querySelector('.ex-zoom-stage'), sr = s.getBoundingClientRect(), ss = getComputedStyle(s);
  const zoom = new DOMMatrix(getComputedStyle(document.querySelector('.ex-zoom-scale')).transform).a;
  const front = copy.querySelector(':scope > .ex-card-front'), back = copy.querySelector(':scope > .ex-card-back');
  let tallest = c.height;
  if (front.hidden !== back.hidden) {
    front.hidden = !front.hidden; back.hidden = !back.hidden;
    tallest = Math.max(tallest, copy.getBoundingClientRect().height);
    front.hidden = !front.hidden; back.hidden = !back.hidden;
  }
  return {times: c.width / w, zoom, tallest, l: c.left, r: c.right, t: c.top, b: c.bottom, vw: innerWidth, vh: innerHeight,
          roomX: s.clientWidth - parseFloat(ss.paddingLeft) - parseFloat(ss.paddingRight),
          roomY: s.clientHeight - parseFloat(ss.paddingTop) - parseFloat(ss.paddingBottom),
          stageTop: sr.top, stageBottom: sr.bottom, scrolls: s.scrollHeight > s.clientHeight + 1, scrollTop: s.scrollTop,
          sideways: s.scrollWidth > s.clientWidth + 1};
}, [ZOOMED, onPage.w]);
/* The card on the page laid out at a width (null: its own) and measured on
   both its sides: its taller side, how many things in it are wider than
   their box (a table its wrapper scrolls, a word sticking out of the card),
   the lines of each stretch of its text (stretchLines) and how wide each of
   its pictures and players is laid out. */
const narrowed = (card, width) => card.evaluate((c, w) => {
  if (w) c.style.width = w + 'px';
  const f = c.querySelector(':scope > .ex-card-front'), b = c.querySelector(':scope > .ex-card-back');
  const wider = () => [c, ...c.querySelectorAll('*')]
    .filter(e => !e.closest('[hidden]') && e.scrollWidth > e.clientWidth + 1).length;
  const media = () => [...c.querySelectorAll('img, audio, video, iframe')]
    .filter(e => e.getClientRects().length).map(e => parseFloat(getComputedStyle(e).width));
  let high = c.offsetHeight, n = wider(), stretches = window.stretchLines(c), widths = media();
  if (f.hidden !== b.hidden) {
    f.hidden = !f.hidden; b.hidden = !b.hidden;
    high = Math.max(high, c.offsetHeight);
    n += wider();
    stretches = stretches.concat(window.stretchLines(c));
    widths = widths.concat(media());
    f.hidden = !f.hidden; b.hidden = !b.hidden;
  }
  c.style.width = '';
  return {high, wider: n, stretches, widths};
}, width);
/* How many lines each stretch of a card's text is drawn in: a stretch is
   what only wrapping breaks -- a field, a paragraph, a cell, a line of a
   Jolly field up to its ⏎ (a <br>) -- and its lines are its text's boxes
   grouped by where they sit down the card (across it, in vertical text).
   A ruby's reading, a footnote's cloud and a hidden side are none of it.
   Returns [lines, text] for each, in the order they come, which is the
   same at any width.  Put on the pages of a) as window.stretchLines. */
function stretchLines(el) {
  const blocks = new Map();
  const inline = b => /^(inline|contents|ruby)$|^ruby-/.test(getComputedStyle(b).display);
  const of = node => {
    let b = node.parentElement;
    while (b !== el && inline(b)) b = b.parentElement;
    if (!blocks.has(b)) blocks.set(b, [{lines: [], text: ''}]);
    return blocks.get(b);
  };
  const walk = document.createTreeWalker(el, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
    acceptNode: n => n.nodeType === 1 && n.matches('rt, rp, .fncloud, [hidden]')
      ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT});
  const range = document.createRange();
  for (let n = walk.nextNode(); n; n = walk.nextNode()) {
    if (n.nodeType === 1) { if (n.localName === 'br') of(n).push({lines: [], text: ''}); continue; }
    if (!/\S/.test(n.data)) continue;
    const all = of(n), s = all[all.length - 1];
    s.text += n.data;
    const vertical = /^(vertical|sideways)/.test(getComputedStyle(n.parentElement).writingMode);
    range.selectNodeContents(n);
    for (const q of range.getClientRects()) {
      if (!q.width || !q.height) continue;
      const [a, b] = vertical ? [q.left, q.right] : [q.top, q.bottom];
      const line = s.lines.find(([c, d]) => Math.min(b, d) - Math.max(a, c) > Math.min(b - a, d - c) / 2);
      if (line) { line[0] = Math.min(line[0], a); line[1] = Math.max(line[1], b); }
      else s.lines.push([a, b]);
    }
  }
  return [...blocks.values()].flat().map(s => [s.lines.length, s.text.trim().replace(/\s+/g, ' ')]);
}
/* The stretches of one line in `was` that are more in `now`. */
const broken = (was, now) => was.flatMap(([n, text], i) => n === 1 && now[i] && now[i][0] > 1 ? [`"${text}" ${now[i][0]} lines`] : []);
/* How wide the pictures a card shows are drawn. */
const pictures = card => card.evaluate(c => [...c.querySelectorAll('img')]
  .filter(i => !i.closest('[hidden]')).map(i => i.getBoundingClientRect().width));
/* How wide its pictures and players -- a figure's picture, a card's picture,
   a recording's player, a video -- are drawn. */
const drawnMedia = card => card.evaluate(c => [...c.querySelectorAll('img, audio, video, iframe')]
  .filter(e => e.getClientRects().length).map(e => e.getBoundingClientRect().width));
/* The pictures and players laid out in `now` narrower than in `was`. */
const narrowedMedia = (was, now) => was.flatMap((w, i) => now[i] < w - 0.5 ? [`${Math.round(w)} -> ${Math.round(now[i])} px`] : []);

try {
  // ------------------------------------------------ a) every card, both faces
  console.log('a) every card enlarged is the card on the page, only bigger');
  for (const [vw, vh, phone] of [[1400, 900, false], [390, 844, true]]) {
    const ctx = await browser.newContext({viewport: {width: vw, height: vh}, isMobile: phone, hasTouch: phone});
    await ctx.addInitScript({content: `window.stretchLines = ${stretchLines};`});
    const page = await ctx.newPage();
    page.on('pageerror', e => pageErrors.push(e.message));
    for (const [name, id] of Object.entries(docs)) {
      await page.goto(`${B}/doc/${id}`);
      await ready(page);
      const n = await page.locator('#sheet .ex-flashcard').count();
      for (let i = 0; i < n; i++) {
        for (const face of ['front', 'back']) {
          const card = cardAt(page, i);
          await card.scrollIntoViewIfNeeded();
          // turned from the keyboard: a card taller than the window has no
          // corner a click is sure to reach
          if ((face === 'back') !== await card.evaluate(c => c.classList.contains('flipped'))) {
            await card.focus();
            await page.keyboard.press('Enter');
          }
          const type = await card.getAttribute('data-card-type');
          const where = `${vw}x${vh} ${name} card ${i + 1} (${type}), ${face}`;
          const onPage = await card.evaluate(drawnCard);
          const pageLines = await card.evaluate(c => window.stretchLines(c));
          const photos = await pictures(card), media = await drawnMedia(card);
          if (SHOTS) await card.screenshot({path: `${SHOTS}/${vw}-${name}-${i + 1}-${face}-page.png`});
          await enlarge(page, i);
          if (SHOTS) await page.screenshot({path: `${SHOTS}/${vw}-${name}-${i + 1}-${face}-enlarged.png`});
          const how = await sameAsPage(page, card, onPage, where);
          const at = await placement(page, onPage);
          // laid out narrower, a card is drawn as wide as the window, which
          // is `times` as wide as the card on the page: magnified whole, it
          // would be that much larger
          assert(!phone ? at.zoom >= 1.49 && !how.relaid : how.relaid ? at.zoom >= at.times * 1.1 - 0.005 : at.times >= 1.25 && at.r - at.l >= at.roomX - 1,
                 `${where}: magnified ${at.zoom.toFixed(2)} times` + (how.relaid ? ', laid out narrower' : ', whole')
                 + `, ${at.times.toFixed(2)} times as wide, and inside the window across (${Math.round(at.l)}–${Math.round(at.r)} of ${at.vw})`);
          if (phone) {
            // the card on the page, only bigger: a line may wrap at other
            // words only where it wraps on the page
            const bigLines = await page.locator(ZOOMED).evaluate(c => window.stretchLines(c));
            const rebroken = broken(pageLines, bigLines);
            assert(bigLines.length === pageLines.length && !rebroken.length,
                   `${where}: each of its ${pageLines.filter(([n]) => n === 1).length} stretches of text that are one line on the page is one line enlarged`
                   + (rebroken.length ? ': ' + rebroken.join('; ') : ''));
          }
          if (media.length) {
            // beside the words as on the page: every picture and player
            // magnified as much as the text is, never laid out narrower
            // (a figure is a share of its field's width, a recording as
            // wide as its field narrows with it)
            const big = await drawnMedia(page.locator(ZOOMED));
            const smaller = media.flatMap((w, k) => big[k] >= w * at.zoom - 1 ? [] : [`${Math.round(w)} -> ${Math.round(big[k])} px`]);
            assert(big.length === media.length && !smaller.length,
                   `${where}: each of its ${media.length} pictures and players is drawn at least ${at.zoom.toFixed(2)} times its size on the page, as its text is`
                   + (smaller.length ? ': ' + smaller.join('; ') : ''));
          }
          assert(at.l >= -0.5 && at.r <= at.vw + 0.5 && !at.sideways, `${where}: nothing of it scrolls sideways`);
          // (a table its wrapper scrolls, a word sticking out of its box)
          const wider = sel => page.locator(sel).evaluate(c => [c, ...c.querySelectorAll('*')]
            .filter(b => !b.closest('[hidden]') && b.scrollWidth > b.clientWidth + 1).length);
          const [was, now] = [await wider('#sheet .ex-flashcard >> nth=' + i), await wider(ZOOMED)];
          assert(now <= was, `${where}: nothing in it is wider than its box that is not on the page (${now} enlarged, ${was} on the page)`);
          const onPageAt = await narrowed(card, null);
          if (how.relaid) {
            // as large as the window holds: its height, twice as large, or
            // any narrower, a line that is whole on the page would break,
            // something in it would be wider than its box or a picture or
            // player narrower than on the page
            const more = at.zoom >= 1.99 || at.tallest >= at.roomY * 0.95 ? null
              : await narrowed(card, at.roomX / (at.zoom * 1.05));
            const breaks = more ? broken(onPageAt.stretches, more.stretches) : [];
            const shrunk = more ? narrowedMedia(onPageAt.widths, more.widths) : [];
            assert(!at.scrolls && (!more || more.wider > onPageAt.wider || breaks.length || shrunk.length),
                   `${where}: laid out narrower, it takes the window: its taller side ${Math.round(at.tallest)} px of ${Math.round(at.roomY)}, or twice as large`
                   + (more ? `, or any narrower ${more.wider} things in it would be wider than their box (${onPageAt.wider} on the page),`
                     + ` ${breaks.length} lines whole on the page would break (${breaks.join('; ')})`
                     + ` and ${shrunk.length} pictures or players would be narrower (${shrunk.join('; ')})` : ''));
          } else if (phone) {
            // magnified whole only where a tenth larger than that (and a
            // hair, for the halving that finds it) could not fit however it
            // was laid out: the page's card at the width that would take,
            // too high for the window, with a line whole on the page broken,
            // with something in it wider than its box, or with a picture or
            // player narrower than on the page
            const m = at.zoom * 1.1 + 0.01, then = await narrowed(card, at.roomX / m);
            const breaks = broken(onPageAt.stretches, then.stretches);
            const shrunk = narrowedMedia(onPageAt.widths, then.widths);
            assert(then.high * m > at.roomY || then.wider > onPageAt.wider || breaks.length || shrunk.length,
                   `${where}: magnified whole since, laid out narrower, ${m.toFixed(2)} times as large it would be ${Math.round(then.high * m)} px high, the window ${Math.round(at.roomY)}, with ${then.wider} things wider than their box (${onPageAt.wider} on the page), ${breaks.length} lines whole on the page broken (${breaks.join('; ')}) and ${shrunk.length} pictures or players narrower (${shrunk.join('; ')})`);
          }
          if (name === 'Persian' && i === 5 && face === 'front') {
            const [was] = photos, [now] = await pictures(page.locator(ZOOMED));
            assert(now >= was * 1.49, `${where}: its photograph is drawn ${Math.round(now)} px wide, ${(now / was).toFixed(2)} times its ${Math.round(was)} px on the page`);
          }
          if (at.scrolls) {
            // taller than the window: it opens at its top, and scrolls to its end
            assert(at.scrollTop === 0 && at.t >= at.stageTop - 0.5,
                   `${where}: taller than the window, it opens at its top (${Math.round(at.t)} under the window's ${Math.round(at.stageTop)})`);
            await page.locator('.ex-zoom-stage').evaluate(s => { s.scrollTop = s.scrollHeight; });
            const end = await placement(page, onPage);
            assert(end.b <= end.stageBottom + 0.5 && end.b >= end.stageBottom - 12,
                   `${where}: and its end is reached by scrolling (${Math.round(end.b)} at the window's ${Math.round(end.stageBottom)})`);
          } else {
            assert(at.t >= -0.5 && at.b <= at.vh + 0.5, `${where}: the whole card is in the window (${Math.round(at.t)}–${Math.round(at.b)} of ${at.vh})`);
          }
          await closeZoom(page);
        }
      }
    }
    await ctx.close();
  }

  // ------------------------------------------------ b) turned while enlarged
  console.log('b) turning the enlarged card');
  {
    const page = await browser.newPage({viewport: {width: 1400, height: 900}});
    page.on('pageerror', e => pageErrors.push(e.message));
    await page.goto(`${B}/doc/${docs.Persian}`);
    await ready(page);
    const card = cardAt(page, 1);
    await enlarge(page, 1);
    const before = await page.locator(ZOOMED).boundingBox();
    await page.locator(ZOOMED).click({position: {x: 10, y: 10}});
    const turned = await page.evaluate(sel => document.querySelector(sel).classList.contains('flipped'), ZOOMED);
    assert(turned && await card.evaluate(c => c.classList.contains('flipped')),
           'a click on the enlarged card turns it, and the card on the page with it');
    const after = await page.locator(ZOOMED).boundingBox();
    assert(Math.abs(after.width - before.width) < 0.5,
           `turned, it keeps its size: ${before.width.toFixed(1)} px wide before, ${after.width.toFixed(1)} after`);
    sameCard(await card.evaluate(drawnCard), await page.locator(ZOOMED).evaluate(drawnCard), 'turned while enlarged, its back');
    await page.keyboard.press(' ');
    assert(!await card.evaluate(c => c.classList.contains('flipped')), 'Space turns it back');
    sameCard(await card.evaluate(drawnCard), await page.locator(ZOOMED).evaluate(drawnCard), 'turned back with Space, its front');
    await closeZoom(page);
    await page.close();
  }

  // ------------------------------------------------ c) justify off
  console.log('c) the page\'s own typography');
  {
    const page = await browser.newPage({viewport: {width: 1400, height: 900}});
    page.on('pageerror', e => pageErrors.push(e.message));
    await page.goto(`${B}/doc/${docs.English}`);
    await page.evaluate(() => localStorage.setItem('exlex-typo:global', JSON.stringify({justify: false, base: 20})));
    await page.reload();
    await ready(page);
    const card = cardAt(page, 1);
    await card.focus();
    await page.keyboard.press('Enter');
    const onPage = await card.evaluate(drawnCard);
    const ragged = onPage.items.filter(it => it.what === 'la-par').map(it => it.align);
    assert(ragged.length === 2 && !ragged.includes('justify'),
           `with "justify" off the page justifies neither Latin block (${ragged.join(', ')})`);
    await enlarge(page, 1);
    sameCard(onPage, await page.locator(ZOOMED).evaluate(drawnCard), 'justify off and a larger text size, the back');
    await closeZoom(page);
    await page.evaluate(() => localStorage.removeItem('exlex-typo:global'));
    await page.close();
  }

  // ------------------------------------------------ d) the editor's preview
  console.log('d) the editor\'s preview');
  {
    const page = await browser.newPage({viewport: {width: 1400, height: 900}});
    page.on('pageerror', e => pageErrors.push(e.message));
    await page.goto(`${B}/doc/${docs.Persian}/edit`);
    await page.waitForFunction(() => /rendered/.test(document.querySelector('#pv-status')?.textContent || ''), null, {timeout: 15000});
    await ready(page);
    for (const i of [0, 1, 2]) {
      const card = cardAt(page, i);
      await card.scrollIntoViewIfNeeded();
      const both = await card.evaluate(c => !c.querySelector('.ex-card-front').hidden && !c.querySelector('.ex-card-back').hidden);
      const onPage = await card.evaluate(drawnCard);
      await enlarge(page, i);
      if (SHOTS) await page.screenshot({path: `${SHOTS}/editor-${i + 1}-enlarged.png`});
      sameCard(onPage, await page.locator(ZOOMED).evaluate(drawnCard), `the editor's preview, card ${i + 1}, both sides shown (${both})`);
      await closeZoom(page);
    }
    await page.close();
  }

  // ------------------------------------------------ e) resized while open
  console.log('e) the window resized with the card enlarged');
  {
    const page = await browser.newPage({viewport: {width: 1400, height: 900}});
    page.on('pageerror', e => pageErrors.push(e.message));
    await page.goto(`${B}/doc/${docs.Persian}`);
    await ready(page);
    const card = cardAt(page, 1);
    await enlarge(page, 1);
    const wide = (await card.boundingBox()).width;
    await page.setViewportSize({width: 480, height: 800});
    await sleep(500);
    const narrow = (await card.boundingBox()).width;
    const onPage = await card.evaluate(drawnCard);
    const at = await placement(page, onPage);
    assert(narrow < wide - 50 && at.l >= -0.5 && at.r <= at.vw + 0.5,
           `narrowed from 1400 to 480 px, the enlarged card is inside the window again (${Math.round(at.l)}–${Math.round(at.r)} of ${at.vw})`);
    await sameAsPage(page, card, onPage, `measured again at the page card's new width (${Math.round(wide)} → ${Math.round(narrow)} px)`);
    await closeZoom(page);
    // and in a window that narrow, the card taller than it: as wide as the
    // window lets it be, and the scrollbar it brings pushes nothing sideways
    await enlarge(page, 4);
    const tall = await cardAt(page, 4).evaluate(drawnCard);
    const up = await placement(page, tall);
    assert(up.scrolls && !up.sideways && up.times > 1 && up.l >= -0.5 && up.r <= up.vw + 0.5,
           `a card taller than a narrow window scrolls down only (${up.times.toFixed(2)} times as large, ${Math.round(up.l)}–${Math.round(up.r)} of ${up.vw})`);
    await sameAsPage(page, cardAt(page, 4), tall, 'the tall card in a narrow window');
    await closeZoom(page);
    await page.close();
  }

  // ------------------------------------------------ f) footnotes
  console.log('f) a footnote\'s cloud on the enlarged card');
  for (const [vw, vh, phone] of [[1400, 900, false], [1280, 800, false], [390, 844, true]]) {
    const ctx = await browser.newContext({viewport: {width: vw, height: vh}, isMobile: phone, hasTouch: phone});
    const page = await ctx.newPage();
    page.on('pageerror', e => pageErrors.push(e.message));
    await page.goto(`${B}/doc/${docs.Footnotes}`);
    await ready(page);
    let marks = 0;
    for (const i of [0, 1]) for (const face of ['front', 'back']) {
      const where = `${vw}x${vh} footnotes card ${i + 1}, ${face}`;
      const card = cardAt(page, i);
      await card.scrollIntoViewIfNeeded();
      if ((face === 'back') !== await card.evaluate(c => c.classList.contains('flipped'))) {
        await card.focus();
        await page.keyboard.press('Enter');
      }
      await enlarge(page, i);
      const at = await placement(page, await card.evaluate(drawnCard));
      assert(!at.sideways && at.l >= -0.5 && at.r <= at.vw + 0.5,
             `${where}: every cloud hidden, nothing scrolls sideways (${Math.round(at.l)}–${Math.round(at.r)} of ${at.vw})`);
      const refs = page.locator(`.ex-zoom-overlay .ex-card-${face} .fnref`);
      for (let j = 0; j < await refs.count(); j++, marks++) {
        const ref = refs.nth(j);
        await ref.hover();
        await sleep(250);
        const c = await ref.evaluate(r => {
          const cloud = r.parentElement.querySelector('.fncloud'), q = cloud.getBoundingClientRect();
          const s = document.querySelector('.ex-zoom-stage'), sr = s.getBoundingClientRect(), gutter = (sr.width - s.clientWidth) / 2;
          const zoom = new DOMMatrix(getComputedStyle(document.querySelector('.ex-zoom-scale')).transform).a;
          const tail = getComputedStyle(cloud, '::after'), m = r.getBoundingClientRect();
          return {shown: getComputedStyle(cloud).visibility === 'visible' && q.width > 0, l: q.left, r: q.right, t: q.top, b: q.bottom,
                  left: sr.left + gutter, right: sr.right - gutter, top: sr.top, bottom: sr.bottom,
                  tail: q.left + (q.width / zoom / 2 + parseFloat(tail.marginLeft) + parseFloat(tail.borderLeftWidth)) * zoom,
                  mark: (m.left + m.right) / 2,
                  sideways: s.scrollWidth > s.clientWidth + 1};
        });
        assert(c.shown && c.l >= c.left - 0.5 && c.r <= c.right + 0.5 && c.t >= c.top - 0.5 && c.b <= c.bottom + 0.5 && !c.sideways,
               `${where}, mark ${j + 1}: its cloud is shown inside the window (${Math.round(c.l)}–${Math.round(c.r)} of ${Math.round(c.left)}–${Math.round(c.right)}, ${Math.round(c.t)}–${Math.round(c.b)} of ${Math.round(c.top)}–${Math.round(c.bottom)})`);
        assert(Math.abs(c.tail - c.mark) < 3, `${where}, mark ${j + 1}: and its tail is on its mark (${Math.round(c.tail)}, the mark at ${Math.round(c.mark)})`);
        if (SHOTS) await page.screenshot({path: `${SHOTS}/footnote-${vw}-${i + 1}-${face}-${j + 1}.png`});
      }
      await page.mouse.move(1, 1);
      await closeZoom(page);
    }
    assert(marks === 3, `${vw}x${vh}: the three marks were each hovered`);
    await ctx.close();
  }

  assert(!pageErrors.length, 'no page errors' + (pageErrors.length ? ': ' + pageErrors.join('; ') : ''));
  console.log(`card zoom passed (${passed} checks)`);
} finally {
  await browser.close();
  proc.kill('SIGTERM');
  await proc.status;
}
