'use strict';
const fs=require('fs'),path=require('path'),CP=require('child_process'),crypto=require('crypto');
const {createRequire}=require('module');const {OwnedProcesses,boundedStop}=require('../ai-sigma-actual-boundary-repair/cleanup.cjs');const {createMonitor}=require('../ai-sigma-actual-boundary-repair/pause-check.cjs');
const ROOT=path.resolve(__dirname,'../..'),run=process.argv[2],OUT=ROOT+'/.artifacts/ai-sigma/resume-20261002/WALLLESS-ORACLE/runs/'+run,DATA=ROOT+'/research-data/ai-sigma/142-wallless-oracle';
async function main(){
 const cfg=JSON.parse(fs.readFileSync(DATA+'/oracle-config.json'));const admission=JSON.parse(fs.readFileSync(path.dirname(OUT)+'/'+run+'.admission.json'));
 if(admission.decision!=='launch_allowed'||admission.remaining_unknown!==0||!admission.ownership_confirmed||Date.now()-Date.parse(admission.UTC)>30000||Date.now()>=Date.parse(cfg.newjob_deadline))throw Error('ADMISSION_REFUSED_OR_STALE');
 fs.mkdirSync(OUT,{recursive:true});const save=(n,d)=>fs.writeFileSync(OUT+'/'+n+'.json',JSON.stringify(d)+'\n');
 const monitor=createMonitor({out:OUT,subjectIssue:'quoridor-4lc.142',deadlineUTC:cfg.processing_deadline,windowEndUTC:'2026-10-02T23:20:59Z'});let browser=null,page=null,primary=null,stop=null;const owner=new OwnedProcesses({tracePath:OUT+'/cleanup.jsonl'});
 try{
  await monitor.start();monitor.check();
  const {chromium}=createRequire('/workspaces/quoridor/package.json')('playwright'),original=CP.spawn;CP.spawn=(...a)=>owner.observeChild(original(...a));
  try{browser=await chromium.launch({headless:true,executablePath:'/workspaces/quoridor/artifacts/playwright/chromium-1243/chrome-linux64/chrome',args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--disable-software-rasterizer','--use-gl=disabled','--renderer-process-limit=1']});}finally{CP.spawn=original;}
  page=await browser.newPage();await page.route('**/*',r=>r.abort());
  await page.addScriptTag({content:"globalThis.oracleWorkers=0;globalThis.Worker=class {constructor(){oracleWorkers++;throw Error('WORKER_FORBIDDEN');}};"});
  const sources=[];
  for(const f of ['tools/ai-sigma-actual-boundary-repair/game.js','tools/ai-sigma-actual-boundary-repair/context.js','tools/ai-sigma-wallless-oracle/checker.js']){const text=fs.readFileSync(ROOT+'/'+f,'utf8');sources.push({path:f,sha256:crypto.createHash('sha256').update(text).digest('hex'),bytes:Buffer.byteLength(text)});await page.addScriptTag({content:text});}
  const provided=await page.evaluate(()=>Array.from(document.scripts).map(s=>s.textContent));save('actual-served-source',{sources,browser_script_sha256:provided.map(s=>crypto.createHash('sha256').update(s).digest('hex')),transport:'inline addScriptTag content echoed from document.scripts',independent_fetch:false});
  save('mocks',await page.evaluate(()=>browserMocks()));
  const reg=JSON.parse(fs.readFileSync(DATA+'/preregister.json'));
  for(let i=0;i<reg.cases.length;i++){
   monitor.check();const generated=await page.evaluate(({reg,i})=>walllessGenerate(reg,i),{reg,i});save('generation-'+i,generated);
   if(generated.adopted){monitor.check();const label=await page.evaluate(({input,reg})=>walllessCertify(input,reg),{input:generated.adopted,reg});save('label-'+i,label);save('certificate-check-'+i,await page.evaluate(({input,label,reg})=>verifyCertificate(input,label,reg),{input:generated.adopted,label,reg}));}
  }
  save('browser-status',await page.evaluate(()=>({workers_attempted:oracleWorkers,model_loads:0,NN:0,main_oracle_active:false,oracle_timer_callbacks:0})));monitor.check();
 }catch(e){primary={name:e.name,message:e.message,stack:e.stack};save('primary',primary);}
 finally{await monitor.stop();save('monitor-stop',{callback_stopped:true});stop=await boundedStop({owner,stop:async()=>{if(browser)await browser.close();return{remaining_pids:0};}});save('controlled-stop',stop);}
 save('summary',{NN:0,games:0,primary,stop});if(primary)process.exitCode=1;
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
