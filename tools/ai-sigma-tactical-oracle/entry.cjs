'use strict';
const fs=require('fs'),path=require('path'),CP=require('child_process');
const {createRequire}=require('module');
const {OwnedProcesses,boundedStop}=require('../ai-sigma-actual-boundary-repair/cleanup.cjs');
const {createMonitor}=require('../ai-sigma-actual-boundary-repair/pause-check.cjs');
const ROOT=path.resolve(__dirname,'../..'),OUT=ROOT+'/.artifacts/ai-sigma/resume-20261002/TACTICAL-ORACLE/runs/'+process.argv[2];
async function main(){
 const admission=JSON.parse(fs.readFileSync(ROOT+'/research-data/ai-sigma/127-tactical-oracle/prelaunch.json'));if(!admission.launch_admitted||Date.now()-Date.parse(admission.UTC)>30000)throw Error('ADMISSION_REFUSED_OR_STALE');
 fs.mkdirSync(OUT,{recursive:true});const save=(n,d)=>fs.writeFileSync(OUT+'/'+n+'.json',JSON.stringify(d,null,2)+'\n');
 const monitor=createMonitor({out:OUT,subjectIssue:'quoridor-4lc.127',deadlineUTC:'2026-10-02T14:05:49Z',windowEndUTC:'2026-10-02T14:05:49Z'});
 let browser=null,page=null,primary=null,stop=null;const owner=new OwnedProcesses({tracePath:OUT+'/cleanup.jsonl'});
 try{
  await monitor.start();monitor.check();
  const {chromium}=createRequire('/workspaces/quoridor/package.json')('playwright'),original=CP.spawn;CP.spawn=(...a)=>owner.observeChild(original(...a));
  try{browser=await chromium.launch({headless:true,executablePath:'/workspaces/quoridor/artifacts/playwright/chromium-1243/chrome-linux64/chrome',args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--disable-software-rasterizer','--use-gl=disabled','--renderer-process-limit=1']});}finally{CP.spawn=original;}
  page=await browser.newPage();await page.route('**/*',r=>r.abort());
  for(const f of ['tools/ai-sigma-actual-boundary-repair/game.js','tools/ai-sigma-actual-boundary-repair/context.js','tools/ai-sigma-tactical-oracle/checker.js'])await page.addScriptTag({content:fs.readFileSync(ROOT+'/'+f,'utf8')});
  const reg=JSON.parse(fs.readFileSync(ROOT+'/research-data/ai-sigma/127-tactical-oracle/preregister.json'));
  monitor.check();save('result',await page.evaluate(reg=>oracleRun(reg),reg));monitor.check();save('browser-timers',{timers:0,model_loads:0,Workers:0});
 }catch(e){primary={name:e.name,message:e.message,stack:e.stack};save('primary',primary);}
 finally{
  await monitor.stop();
  const backend={owner,stop:async()=>{if(browser)await browser.close();return{remaining_pids:0};}};
  stop=await boundedStop(backend);save('controlled-stop',stop);
 }
 save('summary',{NN:0,games:0,primary,stop});if(primary)process.exitCode=1;
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
