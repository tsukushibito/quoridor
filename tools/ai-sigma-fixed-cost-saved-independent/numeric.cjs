'use strict';
const fs=require('fs'),vm=require('vm'),path=require('path'),cp=require('child_process'),crypto=require('crypto');
const root=path.resolve(__dirname,'../..'),base=root+'/research-data/ai-sigma/137-fixed-policy-cost/';
const saved=JSON.parse(fs.readFileSync(base+'fixed-input.json'));
const text=cp.execFileSync('tar',['-xOf',base+'all-runs-failures.tar.gz','runs/cost137-r2/browser-result.json'],{maxBuffer:2*1024*1024,encoding:'utf8'});
const box=vm.createContext({saved,data:JSON.parse(text),output:null});
const source=['tools/ai-sigma-actual-boundary-repair/game.js','tools/ai-sigma-actual-boundary-repair/context.js'];
for(const p of source)vm.runInContext(fs.readFileSync(root+'/'+p,'utf8'),box,{filename:p,timeout:1000});
vm.runInContext(`
function must(v,m){if(!v)throw Error(m);}
const s=fromPrefix(saved.identity.legal_prefix),eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
must(s.depth===16&&s.getCurrentPlayer()===1&&s.walls_p1===5&&s.walls_p2===5,'P1_PREFIX16_WALLS');
must(s._positionKey()===saved.identity.key,'KEY');
const history=[...s.position_history].sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0);
must(eq(history,saved.identity.history),'HISTORY');
const input=s.toNNInput(),bits=Array.from(new Uint32Array(input.buffer,input.byteOffset,input.length));must(eq(bits,saved.numeric.features_bits),'FEATURE648');
const acts=s.getLegalActions(),ids=acts.map(a=>rustAction(s,a)),indices=acts.map(a=>actionToIndex(a,9));
let maxPrior=0;const rows=[];
for(const r of data.rows){
 must(acts.some(a=>sameAction(a,r.response.body.action)),'PUBLIC_LEGAL');
 must(eq(r.identity.history,history)&&eq(r.identity.legal_prefix,saved.identity.legal_prefix),'FRESH_SAME_INPUT');
 const n=r.diagnostic.numeric[0];must(eq(n.features_bits,bits)&&n.policy_logits.length===136&&n.policy_logits.every(Number.isFinite)&&Number.isFinite(n.value)&&n.value>=-1&&n.value<=1,'NUMERIC_SHAPE');
 const mx=Math.max(...indices.map(i=>n.policy_logits[i])),weights=indices.map(i=>Math.exp(n.policy_logits[i]-mx)),total=weights.reduce((a,b)=>a+b,0);
 for(const p of r.diagnostic.sab_publications){
  must(eq(p.root_edges.map(e=>e[0]),ids),'ORIGINAL_REFERENCE_LEGAL_ORDER');
  p.root_edges.forEach((e,i)=>{const want=weights[i]/total;must(Math.abs(e[1]-want)<=1e-4+1e-4*Math.abs(want),'PRIOR');maxPrior=Math.max(maxPrior,Math.abs(e[1]-want));must(e.every(Number.isFinite)&&Math.abs(e[3])<=e[2]+1e-5,'EDGE_VALUE');});
 }
 rows.push({request:r.identity.request_id,features:648,NN:137,side:1,Action:r.adopted_stats.action,legal_count:ids.length,actual_policy:'fixedSigma',fixed_golden:false});
}
output={shared_RuleA_independence_limit:true,P1:true,prefix16:true,wall_remaining:[5,5],rows,maxPrior,new_NN_Chrome:0};
`,box,{timeout:3000});
box.output.source=source.map(p=>({path:p,SHA256:crypto.createHash('sha256').update(fs.readFileSync(root+'/'+p)).digest('hex')}));
fs.writeFileSync(root+'/research-data/ai-sigma/138-fixed-cost-saved-independent/independent-numeric.json',JSON.stringify(box.output,null,2)+'\n');console.log(JSON.stringify(box.output));
