const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const src=fs.readFileSync('tools/ai-sigma-actual-boundary-repair/reference-core.js','utf8');let c={};vm.runInNewContext(src+'\nthis.M=MCTSNode',c);const M=c.M;
let rows=[];
for(const initial of [-1,1]){
 const r=new M({}),v=new M({},r,3,.9),u=new M({},r,5,.1);r.children=[v,u];v.visitCount=10;v.valueSum=2;r.visitCount=11;r.valueSum=initial-2;
 const visitedQ=-v.qValue;const visitedU=1.5*.9*Math.sqrt(11)/11, unseenU=1.5*.1*Math.sqrt(11);
 const baseline=(visitedQ+visitedU>unseenU)?3:5;assert.equal(baseline,5);
 const actual=r.bestChild(1.5,.2).action;assert.equal(actual,initial===-1?3:5);
 rows.push({artificial:true,initial_root_NN:initial,node_N:11,root_parentQ:r.qValue,visited_parentQ:visitedQ,unseen_Q0_pick:baseline,actual_reference_FPU_pick:actual,visited_prior_sum:.9,unseen_FPU:r.qValue-.2*Math.sqrt(.9),limits:'consistent synthetic node with10 child evaluations=.2; no real candidate parentQ filled'});
}
const result={issue:'quoridor-4lc.136',run:process.env.SIGMA_POLICY_RUN,actual_reference_source_SHA:crypto.createHash('sha256').update(src).digest('hex'),rows,limits:'NN0 reference bestChild direct; C1.5 override and artificial root values. Candidate uses sqrt(N+1)/f32, not executed here. No real FPU comparison/strength claim.',NN:0,games:0};fs.writeFileSync('research-data/ai-sigma/136-policy-factor-choice/artificial-FPU-probe.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
