// CHROME_BIN=/path/to/chrome PARSEH_PYTHON=python3 deno run --allow-all tests/decomposition.mjs
import { chromium } from 'npm:playwright-core@1.52.0';
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const python = Deno.env.get('PARSEH_PYTHON') || 'python3';
for (const [folder,slug] of [['japanese','mini-ja'],['chinese','mini-zh'],['english','mini-en']]) {
  const result = await new Deno.Command(python,{args:['lib/tex2html.py','--book',`tests/fixtures/books/${folder}/${slug}`],stdout:'null',stderr:'piped'}).output();
  if (!result.success) throw Error(new TextDecoder().decode(result.stderr));
}
const setupResult = await new Deno.Command(python,{args:['-c',"import sys;sys.path.insert(0,'lib');import lookuppage;print(lookuppage.page())"],stdout:'piped'}).output();
const setupHTML = new TextDecoder().decode(setupResult.stdout);
const browser = await chromium.launch({executablePath:Deno.env.get('CHROME_BIN'),headless:true});
const artifacts = Deno.env.get('PARSEH_TEST_ARTIFACTS') || await Deno.makeTempDir({prefix:'parseh-decomposition-'});
await Deno.mkdir(artifacts,{recursive:true});
const errors = [];
const assert = (condition, message) => {if (!condition) throw Error(message);};
const leaf = character => ({character,source:'kanjivg'});
const tree = {character:'想',source:'kanjivg',operator:'⿱',children:[{character:'相',source:'kanjivg',operator:'⿰',children:[leaf('木'),leaf('目')]},leaf('心')]};
let installed = true, failure = false, selectedRequests = 0, installs = 0, drops = 0;
const packs = () => ['kanjivg','makemeahanzi','cjkvi'].map(source => ({source,name:source,have:installed,languages:source==='kanjivg'?['ja']:source==='makemeahanzi'?['zh']:['ja','zh'],licence:'Fixture licence',entries:3,size:1000,url:'https://example.test/source'}));
async function wire(page) {
  page.setDefaultTimeout(7000);
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.hostname !== 'parseh.test') return route.abort();
    if (url.pathname === '/setup') return route.fulfill({body:setupHTML,contentType:'text/html'});
    if (url.pathname.startsWith('/lookup/api/')) {
      const what = url.pathname.split('/').pop(), body = route.request().postDataJSON() || {};
      let payload = {ok:true};
      if (what === 'decompositions') payload = {ok:true,packs:packs(),jobs:{}};
      else if (what === 'getdecomposition') {installed=true;installs++;}
      else if (what === 'dropdecomposition') {installed=false;drops++;}
      else if (what === 'decompose') {
        selectedRequests++;
        if (failure) return route.fulfill({status:500,json:{ok:false,error:'Fixture read failure'}});
        const character = body.character;
        const chosen = character === '想' ? tree : character === '相' ? tree.children[0] : leaf(character);
        payload = {ok:true,character,lang:body.code,status:character==='𠮷'?'missing':chosen.children?'available':'atomic',tree:chosen,
          meanings:{想:'thought',相:'appearance',木:'tree; wood',目:'eye',心:'heart'},dictionary:{source:'Existing dictionary'},
          sources:[{source:'kanjivg',name:'KanjiVG',licence:'CC BY-SA 3.0',url:'https://kanjivg.tagaini.net/',attribution:'Ulrich Apel and contributors'}]};
      } else if (what === 'dicts') payload = {ok:true,dicts:[],jobs:{}};
      else if (what === 'corpora') payload = {ok:true,corpora:[],jobs:{}};
      else if (what === 'models') payload = {ok:true,models:[],jobs:{}};
      else if (what === 'syn') payload = {ok:true,syn:{have:false},job:{}};
      return route.fulfill({json:payload});
    }
    try {
      const path = root + decodeURIComponent(url.pathname);
      const body = await Deno.readTextFile(path);
      const mime = {html:'text/html',js:'text/javascript',css:'text/css',json:'application/json'}[path.split('.').pop()];
      return route.fulfill({body,contentType:mime || 'text/plain'});
    } catch (_) { return route.fulfill({json:{}}); }
  });
}
async function extra(page, selector) {
  await page.evaluate(selector => {
    const span=document.createElement('span');span.className='test-extra';span.textContent='想かな A𠮷想\u{E0100}';
    document.querySelector(selector).append(span);
    window.readerClicks=0;window.readerKeys=0;
    document.addEventListener('click',()=>window.readerClicks++);
    document.addEventListener('keydown',()=>window.readerKeys++);
  }, selector);
}
try {
  const page = await browser.newPage(); await wire(page);
  await page.goto('http://parseh.test/tests/fixtures/books/japanese/mini-ja/reader/index.html',{waitUntil:'domcontentloaded'});
  await extra(page,'.p1');
  const before = await page.locator('.p1').first().innerText();
  assert(await page.locator('.cd-char').count()===0,'no permanent character targets');
  await page.getByRole('button',{name:'Decompose Kanji',exact:true}).click();
  await page.waitForSelector('body.cd-mode');
  assert(await page.locator('rt .cd-char').count()===0,'furigana excluded');
  assert(await page.locator('.test-extra .cd-char').count()===3,'Han Unicode/variation selection only');
  await page.evaluate(()=>window.readerClicks=0);
  await page.locator('.test-extra [data-character="想"]').click({modifiers:['Control']});
  await page.waitForSelector('.cd-root > .cd-node > .cd-glyph');
  assert(await page.locator('.cd-root > .cd-node > .cd-glyph').innerText()==='想','selected character root');
  assert(await page.locator('.cd-tree .cd-node').count()===5,'full recursive tree');
  assert(await page.locator('.cd-tree').innerText().then(t=>t.includes('tree; wood')&&t.includes('heart')),'component meanings');
  assert(await page.evaluate(()=>window.readerClicks)===0,'decomposition suppresses normal click/card actions');
  await page.getByRole('button',{name:'Explore components of 相',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.cd-root > .cd-node > .cd-glyph')?.textContent==='相');
  await page.getByRole('button',{name:'Return to 想',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.cd-root > .cd-node > .cd-glyph')?.textContent==='想');
  await page.locator('.cd-tree-viewport').focus(); await page.evaluate(()=>window.readerKeys=0); await page.keyboard.press('Space');
  assert(await page.evaluate(()=>window.readerKeys)===0,'modal blocks underlying keyboard shortcuts');
  await page.screenshot({path:artifacts+'/desktop.png'});
  await page.keyboard.press('Escape');
  assert(await page.locator('body.cd-mode').count()===1,'Escape closes modal and keeps mode');
  await page.keyboard.press('Escape');
  assert(await page.locator('.cd-char').count()===0,'second Escape leaves mode');
  assert(await page.locator('.p1').first().innerText()===before,'text/ruby content restored');
  await page.getByRole('button',{name:'Decompose Kanji',exact:true}).click();
  await page.locator('.test-extra [data-character="𠮷"]').focus(); await page.keyboard.press('Enter');
  await page.getByText('No component decomposition is available for this character.',{exact:true}).waitFor();
  assert(await page.locator('.cd-nav button').count()===0,'a new inspection starts its own navigation history');
  await page.keyboard.press('Escape'); await page.keyboard.press('Escape');
  failure=true;
  await page.getByRole('button',{name:'Decompose Kanji',exact:true}).click();
  await page.locator('.test-extra [data-character="想"]').click();
  await page.getByText('Fixture read failure',{exact:true}).waitFor();
  failure=false; await page.getByRole('button',{name:'Try again',exact:true}).click();
  await page.waitForSelector('.cd-root > .cd-node > .cd-glyph');
  await page.keyboard.press('Escape'); await page.keyboard.press('Escape');
  const cfg = await page.evaluate(()=>({id:'aB3dE5fG7hI',ann:'/tests/fixtures/videos/japanese/aB3dE5fG7hI/annotations.json',lang:LANG,gloss:GLOSS,local:true,notes:'/notes',editable:{}}));
  const videoHTML=(await Deno.readTextFile('youtube/lib/player.html')).replace('__YTFRANK__',JSON.stringify(cfg)).replaceAll('__BASE__','/youtube');
  await page.route('http://parseh.test/video',route=>route.fulfill({body:videoHTML,contentType:'text/html'}));
  await page.goto('http://parseh.test/video');await page.waitForSelector('#segs .fa');await extra(page,'#segs .fa');
  await page.getByRole('button',{name:'Decompose Kanji',exact:true}).click();
  await page.evaluate(()=>window.readerClicks=0);await page.locator('.test-extra [data-character="想"]').click({modifiers:['Shift']});
  await page.waitForSelector('.cd-root > .cd-node > .cd-glyph');
  assert(await page.evaluate(()=>window.readerClicks)===0,'video seek/copy suppressed');
  await page.keyboard.press('Escape');await page.keyboard.press('Escape');
  // Live rerenders while the mode is active get temporary targets too.
  await page.getByRole('button',{name:'Decompose Kanji',exact:true}).click();
  await page.evaluate(()=>{const span=document.createElement('span');span.className='dynamic-test';span.textContent='想';document.querySelector('#segs .fa').append(span);});
  await page.waitForSelector('.dynamic-test .cd-char');await page.getByRole('button',{name:'Done',exact:true}).click();
  assert(await page.locator('.cd-char').count()===0,'dynamic targets removed');
  console.log('Book/video mode, Unicode, ruby preservation, modal navigation, errors, keyboard, and action isolation passed');

  const mobile=await browser.newPage({viewport:{width:390,height:844},hasTouch:true,isMobile:true});await wire(mobile);
  await mobile.goto('http://parseh.test/tests/fixtures/books/chinese/mini-zh/reader/index.html',{waitUntil:'domcontentloaded'});await extra(mobile,'.p1');
  await mobile.getByRole('button',{name:'Decompose Hanzi',exact:true}).tap();await mobile.locator('.test-extra [data-character="想"]').tap();
  await mobile.waitForSelector('.cd-root > .cd-node > .cd-glyph');
  assert(await mobile.evaluate(()=>document.querySelector('.cd-dialog').getBoundingClientRect().width<=innerWidth),'mobile modal fits viewport');
  await mobile.screenshot({path:artifacts+'/mobile.png'});
  await mobile.getByRole('button',{name:'Close decomposition',exact:true}).tap();await mobile.getByRole('button',{name:'Done',exact:true}).tap();
  installed=false;
  await mobile.getByRole('button',{name:'Decompose Hanzi',exact:true}).tap();await mobile.getByText('Install character components',{exact:true}).waitFor();
  assert(await mobile.locator('body.cd-mode').count()===0,'uninstalled pack does not activate mode');
  await mobile.close();
  await page.goto('http://parseh.test/setup');
  await page.locator('[data-component-get="kanjivg"]').click();await page.waitForSelector('[data-component-drop="kanjivg"]');
  page.on('dialog',dialog=>dialog.accept());await page.locator('[data-component-drop="kanjivg"]').click();await page.waitForSelector('[data-component-get="kanjivg"].go');
  assert(installs===1&&drops===1,'optional installer/remove wiring');
  await page.goto('http://parseh.test/tests/fixtures/books/english/mini-en/reader/index.html',{waitUntil:'domcontentloaded'});
  assert(await page.locator('.cd-toggle').count()===0,'no control outside Japanese/Chinese');
  assert(errors.length===0,errors.join('\n'));assert(selectedRequests>0,'local decomposition endpoint used');
  console.log('Mobile Hanzi tapping, missing installation, setup install/remove, and language gating passed');
} finally { await browser.close(); }
