import { chromium } from 'npm:playwright-core@1.52.0';
// Run: CHROME_BIN=/path/to/chrome deno run --allow-all tests/readings.mjs
// Uses the existing book/video fixtures; all browser requests are intercepted.
const root = await Deno.realPath(new URL('..', import.meta.url));
Deno.chdir(root);
const build = await new Deno.Command(Deno.env.get('PARSEH_PYTHON') || 'python3', {
  args:['lib/tex2html.py','--book','tests/fixtures/books/japanese/mini-ja'],
  stdout:'null', stderr:'piped'
}).output();
if (!build.success) throw Error(new TextDecoder().decode(build.stderr));
const browser = await chromium.launch({executablePath:Deno.env.get('CHROME_BIN'),headless:true});
try {
const page = await browser.newPage();
await page.route('http://parseh.test/**', route => route.fulfill({body:'<!doctype html><html data-lang="ja"><body><button id="typo">Aa</button><div class="p1" id="text"></div><div id="cloud"></div></body></html>',contentType:'text/html'}));
await page.goto('http://parseh.test/');
await page.addScriptTag({path: Deno.cwd()+'/lib/parseh.js'});
await page.addScriptTag({path: Deno.cwd()+'/lib/llm.js'});
await page.addScriptTag({path: Deno.cwd()+'/lib/mt.js'});
await page.addStyleTag({path: Deno.cwd()+'/lib/parseh.css'});
console.log(await page.evaluate(async () => {
 const assert=(v,m)=>{if(!v)throw Error(m)};
 const text=document.querySelector('#text'),cloud=document.querySelector('#cloud');
 const r=Parseh.readings({scope:'book:ja:test',kind:'book',selector:'.p1'});
 r.render(text,'私は本を読む','わたしはほんをよむ');
 assert(text.querySelectorAll('ruby').length===3,'anchored single kanji readings');
 assert(Parseh.baseText(text)==='私は本を読む','base text preserved');
 r.controls(cloud,'私は本を読む');
 cloud.querySelector('[data-known-kanji="本"]').click();
 assert(text.querySelector('.reading-known').textContent==='本ほん','hide only known kanji');
 assert(getComputedStyle(text.querySelector('.reading-known rt')).visibility==='hidden','hidden css');
 r.render(text,'本を読む本','ほんをよむほん');
 assert(text.querySelectorAll('.reading-known').length===2,'every occurrence');
 const again=Parseh.readings({scope:'book:ja:test',kind:'book',selector:'.p1'});
 again.render(text,'本','ほん');
 assert(text.querySelector('.reading-known'),'persistence');
 const other=Parseh.readings({scope:'book:ja:other',kind:'book',selector:'.other'});
 const el=document.createElement('div'); other.render(el,'本','ほん');
 assert(!el.querySelector('.reading-known'),'scope isolation');
 cloud.querySelector('[data-known-kanji="本"]').click();
 assert(!text.querySelector('.reading-known'),'restore');
 r.render(text,'山へ柴刈りに、','やまへしばかりに');
 assert(text.querySelectorAll('ruby').length===2,'punctuation omitted in reading still aligns');
 assert(Parseh.baseText(text)==='山へ柴刈りに、','source punctuation preserved');
 r.render(text,'今日','きょう');
 assert(text.querySelectorAll('ruby').length===1,'irregular compounds remain intact');
 const fields=Parseh.readingFields('ja');
 assert(fields.length===3 && Parseh.readingFields('zh').length===1 && !Parseh.readingFields('en').length,'language settings');
 const typo=Parseh.typo({key:'test_typo',button:document.querySelector('#typo'),fields});
 typo.set('kanaSize',200); typo.set('cjkSpace',0.25); typo.set('kanaContrast',100);
 assert(getComputedStyle(text).letterSpacing==='4px','spacing applied');
 assert(getComputedStyle(text.querySelector('rt')).fontSize==='32px','200% relative size');
 typo.set('kanaSize',250);
 assert(typo.get().kanaSize===200,'size cap');
 const chinese=Parseh.typo({key:'test_typo',fields:Parseh.readingFields('zh')});
 chinese.set('cjkSpace',0.5);
 assert(JSON.parse(localStorage.getItem('test_typo')).kanaSize===200,'other languages preserve kana preferences');
 typo.reset();
 assert(document.documentElement.style.getPropertyValue('--kana-size')==='50%','default size');
 const result={words:[{word:'本',hits:[{headword:'本',senses:['book']}]}]};
 const p=Parseh.pairMarkup({src:'本を読む本',dst:'I read books.',matched:['本']},result,{code:'ja',word_sep:''},{code:'en'});
 assert((p.src.match(/<mark/g)||[]).length===2,'source repeated matches');
 assert(p.dst.includes('>books</mark>'),'translation equivalent inflection: '+p.dst);
 const latin=Parseh.pairMarkup({src:'Art is not a cart. ART!',dst:'<b>art</b>',matched:['art']},{words:[]},{code:'en',word_sep:' '},{code:'en'});
 assert((latin.src.match(/<mark/g)||[]).length===2,'word boundaries and case');
 assert(latin.dst==='&lt;b&gt;art&lt;/b&gt;','HTML escaped');
 const evidence={pairs:[{src:'本です。',dst:'It is a book.'}],pairs_more:true,pairs_offset:0};
 const all=await ParsehLLM.collectPairs(evidence,offset=>Promise.resolve({pairs:[{src:'本を読む。',dst:'I read a book.'}],pairs_more:false}));
 const prompt=ParsehLLM.prompt({sourceName:'Japanese',targetName:'English',sentence:'今日は本を読む。',
   before:['昨日、本を買った。'],after:['明日、返す。'],
   words:[{word:'本',hits:[{headword:'本',translit:'hon',pos:'noun',senses:['book']}]}],pairs:all});
 assert(prompt.includes('Return ONLY the translation'),'translation-only instruction');
 assert(prompt.includes('昨日、本を買った。')&&prompt.includes('明日、返す。'),'surrounding context');
 assert(prompt.includes('本: hon | noun | book'),'visible dictionary results');
 assert(prompt.includes('本です。')&&prompt.includes('本を読む。'),'all Tatoeba pages');
 assert(!prompt.toLowerCase().includes('bergamot'),'Bergamot omitted');
 return 'Reading, typography, highlighting and shared external-chatbot prompt: passed';
}));
await page.unroute('http://parseh.test/**');
let videoHTML;
const errors=[]; page.on('pageerror', e=>{errors.push(e.message);console.log('PAGE ERROR',e.message);});
await page.route('**/*', async route => {
  const url=new URL(route.request().url());
  if (url.hostname!=='parseh.test') return route.abort();
  if (url.pathname==='/video') return route.fulfill({body:videoHTML,contentType:'text/html'});
  if (url.pathname==='/anki/decks') return route.fulfill({json:[]});
  if (url.pathname.endsWith('/reader/__lookup')) {
    const body=route.request().postDataJSON();
    const examples=Array.from({length:10},(_,i)=>({src:`本の例 ${i+1}`,dst:`Book example ${i+1}.`,matched:['本']}));
    if(body.corpus_only){
      const start=body.corpus_offset||0, limit=body.corpus_limit||3;
      return route.fulfill({json:{ok:true,pairs:examples.slice(start,start+limit),
        pairs_more:start+limit<examples.length,pairs_offset:start}});
    }
    return route.fulfill({json:{ok:true,
      words:[{word:'本',hits:[{headword:'本',translit:'hon',pos:'noun',senses:['book']}]}],
      pairs:examples.slice(0,3),pairs_more:true,pairs_offset:0,corpus:{source:'Tatoeba'}}});
  }
  if (url.pathname==='/youtube/api/lookup') {
    const body=route.request().postDataJSON();
    if(body.about)return route.fulfill({json:{ok:true,help:true,available:false,corpus_available:true,corpus:{source:'Tatoeba'}}});
    const examples=Array.from({length:10},(_,i)=>({src:`今日は本を読む ${i+1}`,dst:`I read a book today ${i+1}.`,matched:['本']}));
    if(body.corpus_only){
      const start=body.corpus_offset||0, limit=body.corpus_limit||3;
      return route.fulfill({json:{ok:true,pairs:examples.slice(start,start+limit),
        pairs_more:start+limit<examples.length,pairs_offset:start}});
    }
    return route.fulfill({json:{ok:true,
      words:[{word:'本',hits:[{headword:'本',translit:'hon',pos:'noun',senses:['book']}]}],
      pairs:examples.slice(0,3),pairs_more:true,pairs_offset:0,corpus:{source:'Tatoeba'}}});
  }
  try {
    const path=Deno.cwd()+decodeURIComponent(url.pathname);
    let body=await Deno.readTextFile(path);
    if(url.pathname.endsWith('/tests/fixtures/videos/japanese/aB3dE5fG7hI/annotations.json')){
      const data=JSON.parse(body); data.segments[2].chunks[0].voc=''; body=JSON.stringify(data);
    }
    const ext=path.split('.').pop();
    const mime={html:'text/html',js:'text/javascript',css:'text/css',json:'application/json',woff2:'font/woff2'}[ext] || 'application/octet-stream';
    return route.fulfill({body,contentType:mime});
  } catch (_) { return route.fulfill({body:'{}',contentType:'application/json'}); }
});
await page.goto('http://parseh.test/tests/fixtures/books/japanese/mini-ja/reader/index.html', {waitUntil:'domcontentloaded'});
console.log('book loaded');
await page.waitForSelector('.p1 ruby');
await page.evaluate(()=>setHover(true));
await page.locator('.p1 ruby').filter({hasText:/\p{Script=Han}/u}).first().hover();
await page.waitForSelector('#cloud .reading-controls button');
const bookCheck=await page.evaluate(async()=>{
 const b=document.querySelector('#cloud [data-known-kanji]'),c=b.dataset.knownKanji;
 const kana=document.querySelector('#cloud .kana').textContent;
 b.click();
 if(document.querySelector('#cloud .kana').textContent!==kana)throw Error('cloud reading changed');
 const stored=JSON.parse(localStorage.getItem('parseh_known_kanji:book:ja:mini-ja'));
 if(!stored.includes(c))throw Error('book scope not saved');
 b.click();
 const examples=Array.from({length:10},(_,i)=>({src:`本を読む ${i+1}`,dst:`I read a book ${i+1}.`,matched:['本']}));
 const j={pairs:examples.slice(0,3),pairs_more:true,text:'本',sentence:'本を読む',
          words:[{word:'本',hits:[{headword:'本',senses:['book']}]}]};
 const oldFetch=window.fetch; let request=0;
 window.fetch=async(_url,opts)=>{
   const body=JSON.parse(opts.body);
   if(body.corpus_limit!==5||!body.corpus_only)throw Error('load-more request is not corpus-only five');
   if(body.corpus_offset!==(request?8:3))throw Error('wrong corpus offset '+body.corpus_offset);
   const pairs=request++ ? examples.slice(8) : examples.slice(3,8);
   return {json:async()=>({ok:true,pairs,pairs_more:request===1})};
 };
 const box=document.createElement('div'); box.className='dict'; document.body.appendChild(box); pairsInto(box,j);
 if(box.querySelectorAll('.dpair').length!==3||!box.querySelector('.dmore'))throw Error('book starts with three and Load more');
 box.querySelector('.dmore').click(); await new Promise(r=>setTimeout(r,0));
 if(box.querySelectorAll('.dpair').length!==8||!box.querySelector('.dmore'))throw Error('book did not append five and keep Load more');
 box.querySelector('.dmore').click(); await new Promise(r=>setTimeout(r,0));
 if(box.querySelectorAll('.dpair').length!==10||box.querySelector('.dmore'))throw Error('book did not append final page and remove button');
 if(box.querySelectorAll('.pair-match').length!==20)throw Error('book cloud pair highlighting');
 window.fetch=oldFetch;
 const side=document.createElement('div'); sidePairs(side,{pairs:[examples[0]],words:j.words});
 if(side.querySelectorAll('.pair-match').length!==2)throw Error('book editor pair highlighting');
 return 'Book hover, persisted controls, full cloud reading, progressive Tatoeba and both highlights: passed';
}); console.log(bookCheck);
console.log(await page.evaluate(async()=>{
 const assert=(v,m)=>{if(!v)throw Error(m)};
 const sub=[...document.querySelectorAll('.sub')].find((s,i)=>i>0&&i<document.querySelectorAll('.sub').length-1&&s.querySelectorAll('.pass.p2 .row').length>1);
 const rows=[...sub.querySelectorAll('.pass.p2 .row')];
 openChunk(+rows[0].dataset.c,rows[0]); sideShow(true);
 for(let i=0;i<100&&(!document.querySelector('#chside .sllmactions')||document.querySelector('#chside .sllmactions button').disabled);i++)await new Promise(r=>setTimeout(r,20));
 assert([...document.querySelectorAll('#chsrcbody h4')].map(x=>x.textContent).join('|')==='dictionary|a machine’s reading|sentences somebody translated|external chatbot','book source order');
 let copied=''; ParsehLLM.copy=async p=>(copied=p,true);
 document.querySelector('#chside .sllmactions button').click();
 for(let i=0;i<50&&!/Prompt copied/.test(document.querySelector('#chside .sllmstat').textContent);i++)await new Promise(r=>setTimeout(r,20));
 assert(copied.includes('TARGET SENTENCE:')&&copied.includes(chunkCtx(+rows[0].dataset.c).sentence),'book prompt target sentence');
 assert(copied.includes('SENTENCES BEFORE:')&&copied.includes('SENTENCES AFTER:'),'book prompt context');
 assert(copied.includes('本: hon | noun | book')&&copied.includes('本の例 10'),'book prompt has dictionary and all Tatoeba');
 const area=document.querySelector('#chside .sllmctl textarea'); area.value='This book is useful.';
 document.querySelectorAll('#chside .sllmactions button')[1].click();
 assert(document.querySelector('#chside .sllmout .shere'),'book pasted translation is highlighted');
 const whole=[...document.querySelectorAll('#chside .sllmout .sput button')].find(b=>/whole sentence/.test(b.textContent));
 assert(whole,'book pasted translation has the machine-reading buttons'); whole.click();
 assert(document.querySelector('#chen').value.includes('This book is useful.'),'book translation enters meaning');
 closeChunk(); openChunk(+rows[1].dataset.c,rows[1]);
 for(let i=0;i<50&&!document.querySelector('#chside .sllmctl textarea');i++)await new Promise(r=>setTimeout(r,20));
 assert(document.querySelector('#chside .sllmctl textarea').value==='This book is useful.','book sentence cache reused by another chunk');
 closeChunk();
 return 'Book Ask LLM prompt, paste, highlighting, insertion and sentence cache: passed';
}));
const cfg = await page.evaluate(()=>({id:'aB3dE5fG7hI',
 ann:'/tests/fixtures/videos/japanese/aB3dE5fG7hI/annotations.json',
 lang:LANG,gloss:GLOSS,local:true,notes:'/notes',editable:{}}));
videoHTML = (await Deno.readTextFile('youtube/lib/player.html'))
 .replace('__YTFRANK__',JSON.stringify(cfg)).replaceAll('__BASE__','/youtube')
 .replaceAll('__LANG__','ja').replaceAll('__LANG_DIR__','ltr');
await page.evaluate(()=>localStorage.setItem('yt_dict','1'));
await page.goto('http://parseh.test/video');
await page.waitForSelector('.seg .fa ruby');
await page.locator('.seg .fa ruby').first().hover();
await page.waitForSelector('#cloud .reading-controls button');
console.log(await page.evaluate(()=>{
 const b=document.querySelector('#cloud [data-known-kanji]'), c=b.dataset.knownKanji;
 const kana=document.querySelector('#cloud .kana').textContent; b.click();
 if(document.querySelector('#cloud .kana').textContent!==kana)throw Error('video cloud reading changed');
 if(!JSON.parse(localStorage.getItem('parseh_known_kanji:video:ja:aB3dE5fG7hI')).includes(c))throw Error('video scope');
 b.click();
 let copied; Parseh.copy=s=>{copied=s;};
 const rt=document.querySelector('.seg .fa rt'), w=rt.closest('.w');
 rt.dispatchEvent(new MouseEvent('click',{bubbles:true,shiftKey:true}));
 if(copied!==Parseh.baseText(w))throw Error('video copy contains reading');
 rt.dispatchEvent(new MouseEvent('click',{bubbles:true,ctrlKey:true}));
 if(document.querySelector('#afa').value!==Parseh.baseText(w))throw Error('video Anki includes reading');
 document.querySelector('#acancel').click();
 return 'Video hover, persisted controls, full cloud reading, copy and Anki: passed';
}));
await page.mouse.move(1,1);
await page.locator('.seg .fa ruby').first().hover();
await page.waitForSelector('#cloud .dict .dmore');
if(await page.locator('#cloud .dict .dpair').count()!==3)throw Error('video cloud does not start with three examples');
await page.locator('#cloud .dict .dmore').click();
await page.waitForFunction(()=>document.querySelectorAll('#cloud .dict .dpair').length===8);
if(!await page.locator('#cloud .dict .dmore').count())throw Error('video Load more disappeared before the final page');
await page.locator('#cloud .dict .dmore').click();
await page.waitForFunction(()=>document.querySelectorAll('#cloud .dict .dpair').length===10);
if(await page.locator('#cloud .dict .dmore').count())throw Error('video Load more remained after the final page');
console.log('Video Tatoeba progressive loading: passed');
await page.locator('#cloud .mkedit').click();
await page.locator('#cloud .esrc').click();
await page.waitForSelector('#cloud .sllmactions');
await page.evaluate(()=>{window.__llmPrompt='';ParsehLLM.copy=async p=>(window.__llmPrompt=p,true);});
await page.locator('#cloud .sllmactions button').first().click();
await page.waitForFunction(()=>/Prompt copied/.test(document.querySelector('#cloud .sllmstat').textContent));
const videoPrompt=await page.evaluate(()=>window.__llmPrompt);
if(!videoPrompt.includes('TARGET SENTENCE:')||!videoPrompt.includes('SENTENCES BEFORE:')||
   !videoPrompt.includes('SENTENCES AFTER:')||!videoPrompt.includes('本: hon | noun | book')||
   !videoPrompt.includes('今日は本を読む 10'))throw Error('video external-chatbot prompt lacks its evidence');
await page.locator('#cloud .sllmctl textarea').fill('I read this useful book today.');
await page.locator('#cloud .sllmactions button').nth(1).click();
if(!await page.locator('#cloud .sllmout .shere').count())throw Error('video pasted translation was not dictionary-highlighted');
if(!await page.locator('#cloud .sllmout .sput button').count())throw Error('video pasted translation lacks insertion buttons');
const editedAt=await page.locator('#cloud .ewhere').textContent();
const foundAt=/segment (\d+) chunk (\d+)/.exec(editedAt||'');
if(!foundAt)throw Error('video editor did not identify its phrase');
const sameCaption=page.locator(`.seg[data-i="${foundAt[1]}"] .w`);
if(await sameCaption.count()<2)throw Error('video cache fixture has no second phrase in the caption');
const other=Number(foundAt[2])===0?1:0;
await page.locator('#cloud .ecancel').click();
await page.mouse.move(1,1);
await sameCaption.nth(other).hover();
await page.waitForSelector('#cloud .mkedit');
await page.locator('#cloud .mkedit').click();
await page.waitForSelector('#cloud .sllmctl textarea');
if(await page.locator('#cloud .sllmctl textarea').inputValue()!=='I read this useful book today.')
  throw Error('video sentence cache was not reused by another phrase');
console.log('Video Ask LLM prompt, paste, highlighting, insertion and caption cache: passed');
if(errors.length)throw Error(errors.join('\n'));
} finally { await browser.close(); }
