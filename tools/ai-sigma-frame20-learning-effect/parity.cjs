'use strict';
const fs=require('fs'),assert=require('assert'),n=require('../ai-sigma-frame18-native-connection/native.cjs'),{q}=n;
const{w,m}=n.load(process.argv[2]),expected=new Map(JSON.parse(fs.readFileSync(process.argv[3])).map(r=>[r.id,r.value]));
let NN=0,maxTorch=0,maxDelta=0,cases=0;const roots=[],rows=[],kinds=new Set(),clock=()=>Number(process.hrtime.bigint())/1e6;let fullms=0,deltams=0;
function evaluate(s,a){const t=q.r.terminalResult(s);if(t)return t.value;NN++;assert(NN<=2000);return n.valueScaled(a,w,m)}
function close(x,y,label){assert(Number.isFinite(x)&&Number.isFinite(y));const err=Math.abs(x-y);assert(err<=1e-5+1e-4*Math.abs(y),label);return err}
for(const f of q.fixtures()){
 const s=f.state,a=q.full(s,w),bytes=a.a.map(v=>Buffer.from(v.buffer).toString('hex')),key=s._positionKey(),hist=n.history(s);
 const v=evaluate(s,a);maxTorch=Math.max(maxTorch,close(v,expected.get(f.id),'TORCH_NATIVE_ROOT'));roots.push({id:f.id,value:v});
 const legal=s.getLegalActions(),selected=legal.filter(x=>x.type==='pawn').concat(['h','v'].flatMap(o=>{const x=legal.find(x=>x.type==='wall'&&x.orientation===o);return x?[x]:[]}));
 for(let i=0;i<selected.length;i++){const child=s.next(selected[i]),v=evaluate(child,q.full(child,w)),tv=expected.get(f.id+'/child'+i);maxTorch=Math.max(maxTorch,close(v,tv,'TORCH_NATIVE_SELECTED'));rows.push({id:f.id+'/child'+i,native:v,torch:tv})}
 for(const action of legal){const child=s.next(action);let st=clock();const fa=q.full(child,w),fv=evaluate(child,fa);fullms+=clock()-st;st=clock();const da=q.delta(a,child,w),dv=evaluate(child,da);deltams+=clock()-st;maxDelta=Math.max(maxDelta,close(dv,fv,'FULL_DELTA'));assert.deepStrictEqual(fa.ids,da.ids);assert.deepStrictEqual(a.a.map(v=>Buffer.from(v.buffer).toString('hex')),bytes);assert.equal(s._positionKey(),key);assert.equal(n.history(s),hist);cases++;
  if(action.type==='wall')kinds.add(action.orientation);else{const p=s.getCurrentPlayer()===1?'player1pos':'player2pos',dx=Math.abs(s[p][0]-child[p][0]),dy=Math.abs(s[p][1]-child[p][1]);kinds.add(dx&&dy?'diagonal':dx+dy===2?'jump':'pawn')}
 }
}
assert.equal(expected.size,27);assert(['pawn','jump','diagonal','h','v'].every(k=>kinds.has(k)));
const before=NN,term=q.r.fromPrefix([]).copy();term.player1pos=[4,8];term.player2pos=[0,1];term.depth=1;assert.equal(evaluate(term,null),-1);const draw=q.r.fromPrefix([]).copy();draw.depth=200;assert.equal(evaluate(draw,null),0);assert.equal(NN,before);
const result={PASS:true,implementation:'Node native-hosted scalar f32; not Rust/Wasm',samples:NN,Torch27:true,max_torch_abs:maxTorch,max_full_delta_abs:maxDelta,tol:{abs:1e-5,rtol:1e-4},all_legal_children:cases,kinds:[...kinds],roots,selected:rows,parent_copy_buffer_key_history_unchanged:true,mutable_undo_guarantee:false,terminal_beforeNN:true,terminal_NN:0,full_including_input_ms:fullms,delta_including_input_ms:deltams,map:q.stats(),samewall_speed_claim:false};
fs.writeFileSync(process.argv[4],JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({PASS:true,samples:NN,cases,maxTorch,maxDelta}));
