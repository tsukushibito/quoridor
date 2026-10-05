'use strict';
const fs=require('fs'), assert=require('assert/strict'), crypto=require('crypto');
const A='.artifacts/ai-sigma/continuation-20261001/SIGMA-REMAINING-EVIDENCE-PLAN';
const p=JSON.parse(fs.readFileSync(A+'/evidence-choice-plan.json','utf8'));
assert.equal(p.m8_adopted,false);assert.equal(p.actual_go,false);assert.equal(p.new_prefix_selection,false);
const reasonTable={candidate_NN:'candidate_loss',candidate_model:'candidate_loss',candidate_fallback:'candidate_loss',reference_NN:'invalid_pair',reference_model:'invalid_pair',reference_fallback:'invalid_pair',shared_identity:'invalid_pair',shared_referee:'invalid_pair',candidate_timeout:'candidate_loss',candidate_late:'candidate_loss',candidate_crash:'candidate_loss',candidate_noCP:'candidate_loss',candidate_noresponse:'candidate_loss',reference_timeout:'reference_loss',reference_late:'reference_loss',reference_crash:'reference_loss',reference_noCP:'reference_loss',reference_noresponse:'reference_loss'};
// These are given control symbols, NOT observations of a real failure classifier or actual games.
function scenario(kind){const attempts=[],pairs=[];let retries=0,stop=null;for(let i=0;i<8;i++){
 if(['pause','deadline','signal','guard'].includes(kind)&&i===3){stop=kind.toUpperCase();break;}
 let completed=false;
 for(let a=0;a<2;a++){
  const invalid=(kind==='one_invalid'&&i===0&&a===0)||(kind==='pair_exhausted'&&i===0)||(kind==='global_exhausted'&&i<3&&a===0);
  attempts.push({synthetic_pair:i,attempt:a,invalid,control_symbol:invalid?'invalid_pair':'two_scores',prefix:null});
  if(invalid){if(a===1){stop='PAIR_RETRY_EXHAUSTED';break;}if(retries===2){stop='GLOBAL_RETRY_EXHAUSTED';break;}retries++;continue;}
  const scores=kind==='candidate_loss'?[0,0]:kind==='reference_loss'?[1,1]:kind==='mixed'?[[1,.5],[0,.5],[1,0],[.5,.5]][i%4]:[.5,.5];
  pairs.push({synthetic_pair:i,scores,Xi:(scores[0]+scores[1])/2});completed=true;break;
 }
 if(!completed)break;
 }
 const completed=pairs.length,mean=completed?pairs.reduce((s,x)=>s+x.Xi,0)/completed:null;
 return {kind,attempts,pairs,retries,completed,planned:8,complete:completed===8,mean,L:completed===8?Math.max(0,mean-Math.sqrt(Math.log(20)/16)):null,stop,synthetic:true,actual_games:0};
}
const scenarios=['all_draw','candidate_loss','reference_loss','mixed','one_invalid','pair_exhausted','global_exhausted','pause','deadline','signal','guard'].map(scenario);
const stop=Date.parse('2026-10-02T00:30:00Z'),budget=16*200*.5+400+1200+600,reserve=1.5,latest=stop-(budget+reserve)*1000;
assert.equal(budget,3800);assert.equal(new Date(latest).toISOString(),'2026-10-01T23:26:38.500Z');
const width=Math.sqrt(Math.log(20)/16),interval={m:8,one_sided95_each_width:width,L_at_half:Math.max(0,.5-width),U_at_half:Math.min(1,.5+width),two_separate_one_sided_bounds_not_joint95:true,joint95_width_Bonferroni:Math.sqrt(Math.log(40)/16),threshold:.45,mean_required:.45+width,near_half_formal_NI:false};
const nPrecision=Math.ceil(Math.log(20)/(2*.05**2)),nPower=Math.ceil((Math.sqrt(Math.log(20))+Math.sqrt(Math.log(5)))**2/(2*.05**2));
assert.equal(nPrecision,600);assert.equal(nPower,1800);
const result={plan_sha256:crypto.createHash('sha256').update(fs.readFileSync(A+'/evidence-choice-plan.json')).digest('hex'),interval,budget:{think:1600,startup:400,retry:1200,save:600,total:budget,reserve,latest:new Date(latest).toISOString(),at_latest_eligible_arithmetic:stop-latest>=(budget+reserve)*1000,plus1ms_eligible_arithmetic:stop-(latest+1)>=(budget+reserve)*1000,gate_required:true,completion_guarantee:false},future:{precision_pairs:nPrecision,power_sufficient_pairs:nPower,precision_think_s:nPrecision*2*200*.5,power_think_s:nPower*2*200*.5,not_minimal_power:true,formal_assumptions_unadjudicated:true},reasonTable,scenarios,actual_go:false,NN:0,PRNG_executed:false,holdout_sends:0,real_classifier_tested:false};
assert(result.budget.at_latest_eligible_arithmetic&&!result.budget.plus1ms_eligible_arithmetic);assert(scenarios.filter(x=>!x.complete).every(x=>x.L===null));
fs.writeFileSync(A+'/node-static-check.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({all_static_assertions_passed:true,scenarios:scenarios.length,width,budget:result.budget,NN:0,actual_go:false}));
