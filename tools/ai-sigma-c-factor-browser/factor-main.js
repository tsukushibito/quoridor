const countResults=[];
const inheritedMessageHandler=()=>explorationWorker.onmessage;
function installCountMessages() {
  const prior=explorationWorker.onmessage;
  explorationWorker.onmessage=event=>event.data.kind==='count_result'?resolveMessage('count-'+event.data.id,event.data):prior(event);
}
async function calibrateFactorClock() {
  const samples=[];
  for(let i=0;i<8;i++){const start=epochMain(),reply=await pingEarly(),end=epochMain();samples.push({start_ms:start,end_ms:end,worker_ms:reply.at_ms});}
  const lo=Math.max(...samples.map(x=>x.worker_ms-x.end_ms-.1));
  const hi=Math.min(...samples.map(x=>x.worker_ms-x.start_ms+.1));
  if(lo>hi)throw Error('CLOCK_DISJOINT');
  return {lo_ms:lo,hi_ms:hi,mid_ms:(lo+hi)/2,error_ms:(hi-lo)/2+.1,samples};
}
function classificationFactorMock() {
  const FAULT=SharedBestAction.STATE.FAULT;
  const cases=[
    [{late:true,shared_state:FAULT},{error:'NN_FAIL'},'browser_deadline_processing_late'],
    [{judge_error:'read failed',shared_state:FAULT},{error:'NN_FAIL'},'browser_judge_failure'],
    [{cancelled:true,shared_state:FAULT},{error:'NN_FAIL'},'cancel_null'],
    [{external_abort:{code:'BEADS_READ_ERROR'},shared_state:FAULT},{error:'NN_FAIL'},'external_automation_failure'],
    [{shared_state:FAULT},null,'ambiguous_shared_fault'],
    [{shared_state:FAULT},{error:'NN_FAIL'},'engine_fault'],
    [{completed:false},null,'initial_no_completed_cp'],
    [{completed:true},null,'completed_legal']
  ];
  return cases.map(([body,fault,expected])=>{const actual=classifyResponse(body,fault);if(actual!==expected)throw Error('CLASSIFICATION_MOCK_'+actual);return {body,fault,expected,actual,causes:responseCauses(body,fault),game_result:gameFailureResult(actual,1,'candidate')};});
}
async function runCountSearches(config,fixtures,references) {
  installCountMessages();
  for(const spec of config.count_searches) {
    const fixture=fixtures.find(x=>x.id===spec.fixture_id),id=config.run_id+'-'+(countResults.length+1),generation=++generationCounter;
    const resultPromise=waitingMessage('count-'+id,config.count_timeout_ms+5000);
    explorationWorker.postMessage({kind:'count_search',id,generation,fixture,K:spec.K,timeout_ms:config.count_timeout_ms});
    const result=await resultPromise;countResults.push(result);
    if(result.primary)throw Error(result.primary.message);
    if(result.zero.handles||result.zero.activeNN||result.zero.active)throw Error('COUNT_ZERO_ACK');
    result.gate=BrowserNumeric.check({engine:'candidate',state:referenceState(fixture),numeric:result.numeric[0],cp:result.cp,reference:references.find(x=>x.id===fixture.id)});
    const edges=result.cp.root_edges;
    result.edge_sum=edges.reduce((sum,e)=>sum+e[2],0);
    result.observed_root_N=result.cp.tree[0].visits;
    if(result.cp.simulations!==spec.K||result.edge_sum!==spec.K-1||result.observed_root_N!==spec.K)throw Error('COUNT_VISIT_CONVENTION');
    result.entropy=edges.reduce((sum,e)=>e[2]===0?sum:sum-(e[2]/result.edge_sum)*Math.log(e[2]/result.edge_sum),0);
  }
  return {count_results:countResults,completed:countResults.length,games_started:0,clock_end:await calibrateFactorClock()};
}
