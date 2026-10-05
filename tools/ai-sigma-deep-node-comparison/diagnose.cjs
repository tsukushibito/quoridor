'use strict';
const fs=require('fs');
const path=require('path');
const {boundedStop}=require('../ai-sigma-actual-boundary-repair/cleanup.cjs');
const ROOT=path.resolve(__dirname,'../..');
const OUT=ROOT+'/.artifacts/ai-sigma/resume-20261002/DEEP-NODE-COMPARISON';
async function main() {
  if(process.argv[2]!=='--config')throw Error('CONFIG_REQUIRED');
  const config=JSON.parse(fs.readFileSync(process.argv[3]));
  if(config.issue!=='quoridor-4lc.132'||config.frame!==9)throw Error('FRAME132_BINDING');
  if(config.seed!==1979)throw Error('REGISTERED_SEARCH_SEED');
  const mode=config.kind==='browser-prefix'?'prefix':config.kind==='browser-preflight'?'preflight':'NN';
  if(!['prefix','preflight','NN'].includes(mode))throw Error('MODE_REQUIRED');
  const run=config.run_id;
  const directory=OUT+'/runs/'+run;
  fs.mkdirSync(directory,{recursive:false});
  const save=(name,data)=>fs.writeFileSync(directory+'/'+name+'.json',JSON.stringify(data,null,2)+'\n');

  const fixtures=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json')).fixtures;
  const references=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json'));
  const monitor=require('../ai-sigma-actual-boundary-repair/pause-check.cjs').createMonitor({out:directory,subjectIssue:'quoridor-4lc.132',deadlineUTC:config.processing_deadline,windowEndUTC:'2026-10-02T23:10:59Z'});
  let browser=null,primary=null,secondary=[],rows=[],startup=null,gameResult=null,observerTimer=null;
  try {
    await monitor.start();monitor.check();
    browser=await require('./browser.cjs').open(directory,config);
    save('browser-preflight',await browser.page.evaluate(()=>browserPreflight()));
    let midFixtures;
    if(mode==='NN'){
      const input=JSON.parse(fs.readFileSync(config.input_prefixes));
      midFixtures=await browser.page.evaluate(input=>input.inputs.map(deepFixture),input);
      const inputBytes=Buffer.from(JSON.stringify({fixtures:midFixtures},null,2)+'\n');
      fs.writeFileSync(config.fixed_input_path,inputBytes);
      save('fixed-inputs',{fixtures:midFixtures,SHA256:require('crypto').createHash('sha256').update(inputBytes).digest('hex'),NN:0,models_loaded:0});
    }
    if(mode==='NN') {
      if(Date.now()>=Date.parse(config.newjob_deadline))throw Error('NEW_HEAVY_CUTOFF');
      monitor.check();save('config',config);
      let observerBusy=false;
      observerTimer=setInterval(async()=>{
        if(observerBusy)return;observerBusy=true;
        try{monitor.check();if(Date.now()>=Date.parse(config.processing_deadline))throw Error('PROCESSING_DEADLINE');}
        catch(error){
          clearInterval(observerTimer);observerTimer=null;
          try{save('external-abort',await browser.page.evaluate(reason=>browserAbort(reason),{code:error.message,scope:'external run monitor, not per-hand clock'}));}catch(failure){secondary.push({stage:'external-abort',message:failure.message});}
        }finally{observerBusy=false;}
      },250);
      await browser.load();
      startup=await browser.page.evaluate(({fixtures,references})=>browserStartup(fixtures,references),{fixtures,references});save('startup',startup);
      // One evaluate drives all requests in browser; Node never supplies per-hand clocks or judges.
      const result=await browser.page.evaluate(({config,references,fixtures})=>runDeepComparison(config,fixtures,references),{config,references,fixtures:midFixtures});
      gameResult=result;
      rows=result.rows??[];save('browser-result',result);save('rows-index',rows.map(row=>({request_id:row.identity.request_id,engine:row.spec.engine,classification:row.response.classification,public_elapsed_ms:row.response.public_elapsed_ms,hand_NN:row.hand_NN,stop_class:row.worker_stop_class}))); // Full rows preserved once in browser-result, no duplicate diagnostics.

      save('clock-end',await browser.page.evaluate(()=>calibratePlayerClocks()));

    }
  } catch(error) {
    primary={name:error.name,message:error.message,stack:error.stack};save('primary',primary);
    if(browser)try{const partial=await browser.page.evaluate(()=>({...collectBrowser(),deep_results:deepRows}));rows=partial.rows;gameResult=partial;save('partial-browser-result',partial);}catch(error){secondary.push({stage:'partial-collect',message:error.message});}
  } finally {
    if(observerTimer){clearInterval(observerTimer);observerTimer=null;}
    if(browser)try{save('main-timers-stop',await browser.page.evaluate(()=>abortBrowserTimers()));}catch(error){secondary.push({stage:'main-timers-stop',message:error.message});}
    if(browser&&browser.loadState.ready)try{save('finally-model-drop',await browser.page.evaluate(()=>dropEarly()));}catch(error){secondary.push({stage:'finally-drop',message:error.message});}
    // Freeze owned observer creation before taking the browser cleanup receipt.
    try{await monitor.stop();}catch(error){secondary.push({stage:'monitor-stop',message:error.message});}
    if(browser)try {save('outer-controlled-stop',await boundedStop(browser));}catch(error){secondary.push({stage:'browser-stop',message:error.message});}
  }
  const games=gameResult?.games??[];
  const pairing=config.kind==='browser-pair';
  const planned=(config.searches?.length??0)+(config.parity_searches?.length??0);
  const completed=(gameResult?.completed_primary??0)+(gameResult?.parity?.length??0)*2;
  const summary={issue:'quoridor-4lc.132',frame:9,Git:config.Git,mode,run,diagnostic:true,actual_go:false,
    games_started:gameResult?.started_games??0,games,holdout:0,planned,completed,missing:planned-completed,
    denominator:'K8 parity4 and K32 primary8 separate; no game or 500ms public gate',public_response_count:rows.length,
    game_unstarted:pairing?planned-(gameResult?.started_games??0):0,
    startup_NN:startup?.startup_NN??0,hand_NN:rows.reduce((n,row)=>n+row.hand_NN,0)+(gameResult?.deep_results??[]).reduce((n,row)=>n+row.NN_calls,0),
    public_classifications:rows.reduce((counts,row)=>(counts[row.response.classification]=(counts[row.response.classification]??0)+1,counts),{}),
    primary,secondary,count_failures:gameResult?.errors??[],started_search_requests:(gameResult?.started_parity??0)+(gameResult?.started_primary??0),browser_judgement:true,per_CP_Node_binding_calls:0,Node_per_hand_clock_calls:0};
  save('summary',summary);console.log(JSON.stringify(summary));
  if(primary||secondary.length||gameResult?.errors?.length)process.exitCode=1;
}
main().catch(error=>{console.error(error.stack);process.exitCode=1;});
