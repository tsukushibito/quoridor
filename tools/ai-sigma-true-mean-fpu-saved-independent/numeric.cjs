'use strict';
const fs=require('fs'),vm=require('vm'),path=require('path'),cp=require('child_process'),crypto=require('crypto');
const root=path.resolve(__dirname,'../..'),base=root+'/research-data/ai-sigma/140-candidate-true-mean-fpu/';
const fixtures=JSON.parse(fs.readFileSync(base+'fixed-inputs.json')).fixtures;
const data=JSON.parse(cp.execFileSync('tar',['-xOf',base+'all-runs-failures.tar.gz','runs/fpu140-mechanism-r1/browser-result.json'],{maxBuffer:12*1024*1024,encoding:'utf8'}));
const box=vm.createContext({fixtures,data,output:null}),source=['tools/ai-sigma-actual-boundary-repair/game.js','tools/ai-sigma-actual-boundary-repair/context.js'];
for(const p of source)vm.runInContext(fs.readFileSync(root+'/'+p,'utf8'),box,{filename:p,timeout:1000});
vm.runInContext(`
const checks=[],eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b),sort=h=>[...h].sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0);
function must(v,m){checks.push(m);if(!v)throw Error(m);}
const rows=[];let maxPrior=0;
function inspect(s,n,edges){
 const bits=Array.from(new Uint32Array(s.toNNInput().buffer));
 must(eq(bits,n.features_bits),'FEATURE648');must(n.policy_logits.length===136&&n.policy_logits.every(Number.isFinite)&&Number.isFinite(n.value)&&n.value>=-1&&n.value<=1,'FINITE137_STRICT');
 must(s._positionKey()===n.key&&eq(sort(s.position_history),sort(n.history))&&s.depth===n.ply&&s.getCurrentPlayer()-1===n.turn,'KEY_HISTORY_SIDE_PLY');
 const actions=s.getLegalActions(),map=new Map(actions.map(a=>[rustAction(s,a),a])),ids=[...map.keys()].sort((a,b)=>a-b);
 must(eq(ids,n.legal)&&eq(ids,edges.map(e=>e[0])),'CANDIDATE_SORTED_LEGAL_ORDER');
 const indices=ids.map(id=>{let a=map.get(id);if(!s.isPlayer1Turn())a=a.type==='pawn'?{type:'pawn',direction:[a.direction[0],-a.direction[1]]}:{...a,y:7-a.y};return actionToIndex(a,9);});
 const mx=Math.max(...indices.map(i=>n.policy_logits[i])),w=indices.map(i=>Math.exp(n.policy_logits[i]-mx)),total=w.reduce((a,b)=>a+b,0);
 edges.forEach((e,i)=>{const want=w[i]/total,delta=Math.abs(e[1]-want);must(delta<=1e-4+1e-4*Math.abs(want),'P2_ACTION_PRIOR');maxPrior=Math.max(maxPrior,delta);});
 return {ply:s.depth,side:s.getCurrentPlayer(),legal_count:ids.length,walls:[s.walls_p1,s.walls_p2]};
}
for(const r of data.mean_results){
 const fixture=fixtures.find(f=>f.id===r.fixture_id),s=fromPrefix(fixture.legal_prefix),n=r.numeric[0];
 must(s.depth===fixture.board.total_ply&&s.getCurrentPlayer()===2,'FIXED_P2_INPUT');must(eq(Array.from(new Uint32Array(s.toNNInput().buffer)),fixture.features_bits),'FIXED_FEATURES');
 const root=inspect(s,n,r.cp.root_edges);must(r.cp.root_edges.some(e=>e[0]===r.cp.action),'ROOT_ACTION_LEGAL');
 let selected=0;
 if(r.trace)for(const leaf of r.trace.nodes){
  let state=s;
  for(const p of leaf.pre.path){const act=state.getLegalActions().find(a=>rustAction(state,a)===p.Action);must(!!act,'TRACE_PATH_LEGAL');state=state.next(act);}
  const tree=r.cp.tree[leaf.node_index],buf=new ArrayBuffer(4),u=new Uint32Array(buf),v=new Float32Array(buf),decode=b=>{u[0]=b;return v[0];};
  inspect(state,leaf.numeric,tree.edges.map(e=>[e[0],decode(e[1]),e[2],decode(e[3])]));must(eq(sort(state.position_history),sort(leaf.history))&&state._positionKey()===leaf.key,'SELECTED_LEAF_HISTORY');selected++;
 }
 rows.push({fixture:r.fixture_id,variant:r.variant,root,selected_nodes:selected,fixed_golden:false});
}
output={checks:checks.length,rows,maxPrior,shared_RuleA_independence_limit:true,new_NN_Chrome_Wasm:0};
`,box,{timeout:15000});
box.output.source=source.map(p=>({path:p,SHA256:crypto.createHash('sha256').update(fs.readFileSync(root+'/'+p)).digest('hex')}));
fs.writeFileSync(root+'/research-data/ai-sigma/141-true-mean-fpu-saved-independent/independent-numeric.json',JSON.stringify(box.output,null,2)+'\n');console.log(JSON.stringify(box.output));
