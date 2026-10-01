'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert'),N=require('./numeric.cjs'),{makeWrapper}=require('./wrapper.cjs');
const ROOT=path.resolve(__dirname,'../..'),OUT=ROOT+'/.artifacts/ai-sigma/continuation-20261001/SIGMA-NN-SCHEMA-COST';
const fixtures=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json')).fixtures;
const refs=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json'));
let tick=0;const clock=()=>++tick,wrap=makeWrapper(N,clock),rows=[];
function raw(f,ref){
 return {features_bits:N.bits(f.raw_features_float32),raw_legal:N.expected(f),
  effective_legal:f.terminal.side_to_move_value===null?N.expected(f):[],
  terminal:f.terminal.side_to_move_value,turn:f.board.turn};
}
async function main(){
 for(const id of ['initial-p1','asym-hv-p2','straight-jump-p2','synthetic-total-ply-200','goal-win-legal-replay']){
  const f=fixtures.find(x=>x.id===id),ref=refs.find(x=>x.id===id);
  for(const side of ['A','B']){
   const count={A_attempt:0,A_complete:0,B_attempt:0,B_complete:0,raw_feature_calls:0,raw_policy_calls:0,search_calls:0};
   let aNN=0,bNN=0,bFeatures=0,bPolicy=0;
   const A={diagnose(g){aNN++;assert.equal(g.id,id);const r=raw(g,ref);
    delete r.turn;delete r.terminal;return {...r,id:g.id,classification:g.classification,policy_logits:ref.policy_logits.slice(),
     raw_prior:N.rawPriors(g,ref.policy_logits),value:ref.value,search:[]}}};
   const B={call(q){assert.equal(q.fixture.id,id);if(q.op==='raw'){bFeatures++;return raw(q.fixture,ref)}
    assert.equal(q.op,'raw_policy');bPolicy++;return {priors:N.rawPriors(q.fixture,q.logits)}},
    async infer(bits){bNN++;assert.deepEqual(bits,N.bits(f.raw_features_float32));const begin=clock();return {logits:ref.policy_logits.slice(),value:ref.value,nn_ms:1,spans:{run_start_ms:begin,run_end_ms:clock()}}}};
   const r=await wrap({side,fixture:f,reference:ref,A,B,count});
   assert.equal(aNN,side==='A'?1:0);assert.equal(bNN,side==='B'?1:0);
   assert.equal(bFeatures,side==='B'?1:0);assert.equal(bPolicy,side==='B'?1:0);
   assert.equal(count.raw_feature_calls,side==='B'?1:0);
   assert(r.spans.whole_start_ms<r.spans.input_clone_end_ms);
   assert(r.spans.validation_end_ms<r.spans.format_start_ms);
   assert(r.spans.format_encoding_end_ms<r.spans.whole_end_ms);
   if(side==='B')assert(r.spans.feature_only_start_ms<r.spans.B_infer.run_start_ms);
   const formatted=JSON.parse(r.formatted_json);assert.equal(formatted.id,id);
   assert.deepEqual(Object.keys(formatted),['schema','id','backend','features_bits','logits','value','raw_legal','raw_prior','effective_legal']);
   assert.equal(Buffer.byteLength(r.formatted_json),r.formatted_bytes);
   rows.push({id,side,kind:'NN0 stub wrapper, no actual inference',mock_counts:{aNN,bNN,bFeatures,bPolicy},count,spans:r.spans,
    whole_boundary:'before input clone to after mandatory validator + identical JSON/UTF8 shape',numeric_gate:r.numeric_gate});
  }
 }
 // A primary schema failure retains the returned raw output; cleanup belongs to driver finally.
 const f=fixtures[0],ref=refs[0],count={A_attempt:0,A_complete:0};
 try{await wrap({side:'A',fixture:f,reference:ref,A:{diagnose(){return {id:f.id}}},B:null,count});throw Error('FAILURE_NOT_REJECTED')}
 catch(e){assert(e.wrapper_evidence);assert.deepEqual(e.wrapper_evidence.raw_before_failure,{id:f.id,backend:'A'});rows.push({injection:'missing output fields',rejected:true,error:e.message,raw_before_failure_preserved:true})}
 fs.writeFileSync(OUT+'/wrapper-boundary-gates.json',JSON.stringify({pass:true,NN:0,Chromium:0,model_load:0,cases:rows,artificial_calls_are_not_NN_results:true},null,2)+'\n');
 console.log(JSON.stringify({pass:true,mock_normal_terminal_wrappers:10,failure_raw_preserved:1,NN:0}));
}
main().catch(e=>{console.error(e);process.exitCode=1});
