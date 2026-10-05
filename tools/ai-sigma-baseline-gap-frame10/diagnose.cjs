'use strict';
const fs=require('fs');
const path=require('path');
const {boundedStop}=require('../ai-sigma-actual-boundary-repair/cleanup.cjs');
const ROOT=path.resolve(__dirname,'../..');
const OUT=ROOT+'/.artifacts/ai-sigma/resume-20261003/BASELINE-GAP';
async function main() {
  if(process.argv[2]!=='--config')throw Error('CONFIG_REQUIRED');
  const config=JSON.parse(fs.readFileSync(process.argv[3]));
  if(config.issue!=='quoridor-4lc.149'||config.frame!==10)throw Error('FRAME149_BINDING');
  if(config.seed!==1979)throw Error('REGISTERED_SEARCH_SEED');
  const mode=config.generate_only?'prefix':config.kind==='ai'?'NN':'preflight';
  if(!['prefix','preflight','NN'].includes(mode))throw Error('MODE_REQUIRED');
  const run=config.run_id;
  const directory=OUT+'/runs/'+run;
  fs.mkdirSync(directory,{recursive:false});
  const save=(name,data)=>fs.writeFileSync(directory+'/'+name+'.json',JSON.stringify(data,null,2)+'\n');

  const fixtures=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json')).fixtures;
  const references=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json'));
  const monitor=require('../ai-sigma-actual-boundary-repair/pause-check.cjs').createMonitor({out:directory,subjectIssue:'quoridor-4lc.149',deadlineUTC:config.processing_deadline,windowEndUTC:'2026-10-03T04:15:21Z'});
  let browser=null,primary=null,secondary=[],rows=[],startup=null,gameResult=null,observerTimer=null,observerBusy=false,observerPromise=null;
  try {
    await monitor.start();monitor.check();
    browser=await require('./browser.cjs').open(directory,config);
    await browser.page.exposeFunction('saveFinishedGame',data=>{if(!config.games.some(g=>g.id===data.game.id))throw Error('UNREGISTERED_GAME_SAVE');save('completed-game-'+data.game.id,data);});
    save('browser-preflight',await browser.page.evaluate(()=>browserPreflight()));
    save('browser-rules-mock',await browser.page.evaluate(()=>browserRulesMock()));
    save('149-glue-mock',await browser.page.evaluate(({config,fixtures})=>gapMock(config,fixtures),{config,fixtures}));
    if(mode==='prefix'){
      const plan=JSON.parse(fs.readFileSync(config.seed_table)),old=JSON.parse(fs.readFileSync(config.old_document));
      for(const [p,h] of [[config.seed_table,config.seed_table_SHA256],[config.old_document,config.old_document_SHA256]])if(require('crypto').createHash('sha256').update(fs.readFileSync(p)).digest('hex')!==h)throw Error('GENERATION_INPUT_SHA');
      save('generated-prefixes',await browser.page.evaluate(({plan,old})=>generateDiversePrefixes(plan,old),{plan,old}));
    }
    if(mode==='NN'){
      const document=JSON.parse(fs.readFileSync(config.prefix_document));
      if(require('crypto').createHash('sha256').update(fs.readFileSync(config.prefix_document)).digest('hex')!==config.prefix_SHA256)throw Error('PREFIX_SHA');
      fixtures.push(...document.prefixes.filter(x=>x.accepted).map(x=>x.fixture));
      save('prefix-input-check',await browser.page.evaluate(document=>validateDiverseDocument(document),document));
    }
    if(mode==='NN') {
      if(Date.now()>=Date.parse(config.newjob_deadline))throw Error('NEW_HEAVY_CUTOFF');
      monitor.check();save('config',config);
      observerTimer=setInterval(()=>{
        if(observerBusy)return;observerBusy=true;
        observerPromise=(async()=>{
        try{monitor.check();if(Date.now()>=Date.parse(config.processing_deadline))throw Error('PROCESSING_DEADLINE');}
        catch(error){
          clearInterval(observerTimer);observerTimer=null;
          try{save('external-abort',await browser.page.evaluate(reason=>browserAbort(reason),{code:error.message,scope:'external run monitor, not per-hand clock'}));}catch(failure){secondary.push({stage:'external-abort',message:failure.message});}
        }finally{observerBusy=false;}
        })();
      },250);
      for(const [p,h] of [[ROOT+'/.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/final.wasm','1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01'],[ROOT+'/models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx','d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d']])if(require('crypto').createHash('sha256').update(fs.readFileSync(p)).digest('hex')!==h)throw Error('CURRENT_MODEL_BINARY_SHA');
      await browser.load();
      startup=await browser.page.evaluate(({fixtures,references})=>browserStartup(fixtures,references),{fixtures,references});save('startup',startup);
      // One evaluate drives all requests in browser; Node never supplies per-hand clocks or judges.
      const result=await browser.page.evaluate(({config,references,fixtures})=>runBrowserGames(config,fixtures,references),{config,references,fixtures});
      gameResult=result;
      rows=result.rows??[];save('browser-result',result);save('rows-index',rows.map(row=>({request_id:row.identity.request_id,engine:row.spec.engine,classification:row.response.classification,public_elapsed_ms:row.response.public_elapsed_ms,hand_NN:row.hand_NN,stop_class:row.worker_stop_class}))); // Full rows preserved once in browser-result, no duplicate diagnostics.

      save('clock-end',await browser.page.evaluate(()=>calibratePlayerClocks()));

    }
  } catch(error) {
    primary={name:error.name,message:error.message,stack:error.stack};save('primary',primary);
    if(browser)try{const partial=await browser.page.evaluate(()=>gapCollectForSave());rows=partial.rows;gameResult=partial;save('partial-browser-result',partial);}catch(error){secondary.push({stage:'partial-collect',message:error.message});}
  } finally {
    if(observerTimer){clearInterval(observerTimer);observerTimer=null;}
    if(observerPromise)await observerPromise;
    save('outer-main-observer-stop',{active_timer:!!observerTimer,inflight_callback:observerBusy,callbacks_awaited:!observerBusy});
    if(browser)try{save('main-timers-stop',await browser.page.evaluate(()=>abortBrowserTimers()));}catch(error){secondary.push({stage:'main-timers-stop',message:error.message});}
    if(browser&&browser.loadState.ready)try{save('finally-model-drop',await browser.page.evaluate(()=>dropEarly()));}catch(error){secondary.push({stage:'finally-drop',message:error.message});}
    // Freeze owned observer creation before taking the browser cleanup receipt.
    try{await monitor.stop();}catch(error){secondary.push({stage:'monitor-stop',message:error.message});}
    if(browser)try {save('outer-controlled-stop',await boundedStop(browser));}catch(error){secondary.push({stage:'browser-stop',message:error.message});}
  }
  const games=gameResult?.games??[];
  const pairing=config.kind==='ai'&&!config.generate_only;
  const planned=pairing?config.games.length:0;
  const completed=pairing?games.filter(game=>['terminal','responsibility_loss'].includes(game.status)).length:rows.length;
  const summary={issue:'quoridor-4lc.149',frame:10,Git:config.Git,mode,run,diagnostic:true,actual_go:false,
    games_started:gameResult?.started_games??0,games,holdout:0,planned,completed,missing:planned-completed,
    denominator:pairing?'game requirements; public count separate':'functional public requirements',public_response_count:rows.length,
    game_unstarted:pairing?planned-(gameResult?.started_games??0):0,
    startup_NN:startup?.startup_NN??0,hand_NN:rows.reduce((n,row)=>n+row.hand_NN,0)+(gameResult?.count_results??[]).reduce((n,row)=>n+row.NN_calls,0),
    public_classifications:rows.reduce((counts,row)=>(counts[row.response.classification]=(counts[row.response.classification]??0)+1,counts),{}),
    primary,secondary,browser_judgement:true,per_CP_Node_binding_calls:0,Node_per_hand_clock_calls:0};
  save('summary',summary);console.log(JSON.stringify({issue:summary.issue,run,planned,completed,primary,secondary,games:games.map(g=>({id:g.id,status:g.status,winner:g.winner,reason:g.reason,plies:g.actions.length}))}));
  if(primary||secondary.length)process.exitCode=1;
}
main().catch(error=>{console.error(error.stack);process.exitCode=1;});
