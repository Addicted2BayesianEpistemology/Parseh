// SPDX-License-Identifier: GPL-3.0-or-later
// Real Parseh pages + real catalogue on an isolated server, with fake installed
// states. No weights, installation, transcription or existing-server requests.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,mkdtemp,symlink,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {spawn} from 'node:child_process';
import {createServer} from 'node:net';
const {chromium}=await import(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const root=resolve('.'),temporary=await mkdtemp(join(tmpdir(),'parseh-catalogue-visual-'));
const tree=join(temporary,'tree'),install=join(tree,'root');
const python=process.env.PARSEH_PYTHON || 'python3';
for(const folder of ['config','library','tray','exercises','anki','nodict','nocorpus','nomt','root/youtube/videos'])await mkdir(join(tree,folder),{recursive:true});
await symlink(join(root,'lib'),join(install,'lib'));await symlink(join(root,'youtube/lib'),join(install,'youtube/lib'));
const socket=createServer();await new Promise(r=>socket.listen(0,'127.0.0.1',r));const port=socket.address().port;await new Promise(r=>socket.close(r));
const base='http://127.0.0.1:'+port;
let boot=(await readFile('tests/add_stt.mjs','utf8')).match(/const BOOT = String.raw`([\s\S]*?)`;/)[1];
boot=boot.replace("import addstt_fakes\nsys.modules['getstt'] = addstt_fakes.make(str(tmp.parent / 'fake'))",String.raw`
import getstt, speechpackages, copy
getstt.STT_DIR=str(tmp/'stt')
speechpackages.PREPARED_ROOT=tmp/'no-prepared-weights'
ready={'large-v3-turbo','fa-fast','fa-accuracy','hi-accuracy','it-turbo'}
getstt.runtime=lambda:{'state':'ready','ready':True,'have':True,'version':'1.2.1','ctranslate2':'4.8.2','python':'cp312','size':431000000,'why':''}
getstt.runtime_ready=lambda:True
getstt.model_info=lambda model:{'state':'ready' if model in ready else 'absent','ready':model in ready,'have':model in ready,'size':getstt.MEASURED.get(model,0) if model in ready else 0,'built':'2026-10-04','why':''}
getstt.MODEL_INFO=copy.deepcopy(getstt.MODEL_INFO)
getstt.MODEL_INFO['it-turbo']['hint']='Words <img src=x onerror=window.badEscape=true> remain text.'
getstt._run_probe=lambda timeout=30:{'ct2':'4.8.2','cuda_devices':0,'cuda_types':[],'cpu_types':['int8'],'cublas':{'loads':False},'smi':None}
`);
boot=boot.replace("speechconfig.CONFIG = tmp / 'config/speech.json'", "speechconfig.CONFIG = tmp / 'config/speech.json'\nspeechconfig.select('fa','fa-fast')\nspeechconfig.select('hi','hi-accuracy')");
let server,browser,logs='',checks=0;
const ok=(condition,message)=>{assert.ok(condition,message);checks++;};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
try{
 server=spawn(python,['-c',boot,tree,String(port)],{cwd:root,stdio:['ignore','pipe','pipe']});
 server.stdout.on('data',b=>logs+=b);server.stderr.on('data',b=>logs+=b);
 for(let i=0;i<120;i++){try{const response=await fetch(base+'/lookup/api/speech',{method:'POST',body:'{}'});if(response.ok)break;}catch{}if(i===119)throw Error('Temporary server did not start: '+logs);await sleep(100);}
 browser=await chromium.launch({executablePath:process.env.CHROME_BIN || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1280,height:960}});
 await context.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/,route=>route.abort());
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/settings/speech/');await page.waitForSelector('#sp_language');
 const state=await page.locator('#sp-state').textContent();const models=JSON.parse(state).speech.models;
 ok(Object.keys(models).length===15,'real shared catalogue contains15 entries');
 ok(Object.values(models).every(model=>model.available===true),'all real catalogue packages are pinned');
 ok((await page.locator('#sp .it').count())>=16,'real page renders models and independent optional parts');
 ok(await page.locator('#sp img[src=x]').count()===0,'real model hints are escaped');
 ok(!(await page.evaluate(()=>window.badEscape)),'escaped catalogue text cannot run script');
 ok(await page.locator('[data-row="ar-dialectal"] [data-get]').count()===1,'published Arabic package has a direct verified install control');
 ok(await page.locator('[data-row="de-turbo"] [data-get]').count()===1,'direct pinned package has ordinary install action');
 await page.selectOption('#sp_language','fa');
 ok(await page.locator('[data-row="hi-accuracy"]').count()===0,'real catalogue language filtering excludes Hindi in Persian settings');
 ok(await page.inputValue('#sp_preferred_model')==='fa-fast','saved Persian preference appears in settings');
 await page.selectOption('#sp_preferred_model','fa-accuracy');
 await page.waitForFunction(()=>document.getElementById('sp_model_preference_status').textContent.startsWith('Saved'));
 await page.locator('#sp_installed_only').check();
 ok(await page.locator('[data-row="large-v3"]').count()===0,'missing standard model is hidden only by Installed only');
 ok(await page.locator('[data-row="fa-accuracy"]').count()===1,'installed language model remains visible');
 await page.locator('[data-row="fa-fast"] details.tech summary').click();
 ok((await page.locator('[data-row="fa-fast"] details.tech').textContent()).includes(models['fa-fast'].source),'source checkpoint is displayed for the real manifest shape');
 ok((await page.locator('[data-row="fa-fast"] details.tech').textContent()).includes(models['fa-fast'].revision),'pinned source revision is displayed for the real manifest shape');
 await page.locator('#sp_language').evaluate(element=>element.closest('section').scrollIntoView({block:'start'}));
 await page.screenshot({path:'/tmp/parseh-speech-catalogue-desktop.png',fullPage:false});
 await page.setViewportSize({width:390,height:850});
 ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'real narrow settings page has no horizontal overflow');
 await page.locator('#sp_language').evaluate(element=>element.closest('section').scrollIntoView({block:'start'}));
 await page.screenshot({path:'/tmp/parseh-speech-catalogue-narrow.png',fullPage:false});
 await page.setViewportSize({width:1280,height:960});
 await page.goto(base+'/youtube/add/?src=film&by=empty');
 await page.waitForSelector('#transcript',{state:'attached'});await page.selectOption('#lang','fa');await page.fill('#path','/tmp/fake-local-video.mp4');
 await page.waitForFunction(()=>document.querySelector('#stt_model').options.length===3);
 ok(await page.inputValue('#stt_model')==='fa-accuracy','Add Video uses the preference saved by the real settings API');
 ok(await page.locator('#stt_model option[value="hi-accuracy"]').count()===0,'Add Video excludes installed model for another language');
 await page.selectOption('#lang','hi');
 ok(await page.inputValue('#stt_model')==='hi-accuracy','Hindi retains its independent preferred model');
 ok(await page.locator('#stt_model option[value="fa-accuracy"]').count()===0,'language change refreshes the real installed selector');
 ok(await page.locator('#stt_review').getAttribute('data-layout')==='browser','correction workspace stays explicitly browser-only');
 ok(errors.length===0,'real catalogue settings and Add Video have no script errors');
 console.log(`${checks} real catalogue visual/browser checks passed`);
}finally{
 if(browser)await browser.close();
 if(server && server.exitCode===null){const stopped=new Promise(r=>server.once('exit',r));server.kill('SIGTERM');await stopped;}
 await rm(temporary,{recursive:true,force:true});
}
