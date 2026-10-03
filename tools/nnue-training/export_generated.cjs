'use strict';
// NN0 replay adapter. The generation owner alone invokes this on sealed test rows.
// Output label-free metadata + explicitly separate labels; no model/import/session.
const fs=require('fs'),zlib=require('zlib'),crypto=require('crypto'),assert=require('assert');
const {r,input}=require('../ai-sigma-nnue-qf1-prototype/qf1.cjs');
const [openingsPath,rowsPath,metadataPath,labelsPath]=process.argv.slice(2);
if(!labelsPath)throw Error('usage: node export_generated.cjs OPENINGS ROWS METADATA.gz LABELS.gz');
for(const p of [metadataPath,labelsPath])assert(!fs.existsSync(p),'output exists');
const spec=JSON.parse(fs.readFileSync(openingsPath)).games;
const states=new Map(spec.filter(g=>g.generated!==false).map(g=>[g.game_id,r.fromPrefix(g.opening.legal_prefix)]));
const canon=x=>x.slice().sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0);
const hash=x=>crypto.createHash('sha256').update(JSON.stringify(x)).digest('hex');
const metadata=[],labels=[];
const raw=fs.readFileSync(rowsPath),text=rowsPath.endsWith('.gz')?zlib.gunzipSync(raw).toString():raw.toString();
for(const line of text.split('\n').filter(Boolean)){
 const row=JSON.parse(line),g=spec.find(g=>g.game_id===row.game_id),state=states.get(row.game_id);
 assert(g&&state,'opening missing');assert(['train','validation','test'].includes(g.split));
 const declaredSplit=g.split==='test'&&row.split==='evaluation'?'test':row.split;
 assert.equal(g.split,declaredSplit);assert.equal(g.family,row.family);assert.equal(row.state_key,state._positionKey());
 assert.equal(row.ply,state.depth);assert.equal(row.side,state.getCurrentPlayer());
 assert.equal(JSON.stringify(canon([...state.position_history])),JSON.stringify(canon(row.history_counts)));
 const f=state.toNNInput();assert.equal(JSON.stringify(Array.from(new Uint32Array(f.buffer,f.byteOffset,f.length))),JSON.stringify(row.features648_bits));
 const q=input(state),history=hash(['RuleA-state-history-v1',row.state_key,row.side,canon(row.history_counts)]);
 const trainSlot=g.train_slot??g.partition_slot??g.slot;
 const meta={id:row.row_id,game_id:row.game_id,group:row.family,split:g.split,train_slot:g.split==='train'?trainSlot:null,
  cohort:'opening-'+g.opening.legal_prefix.length,opening_ply:g.opening.legal_prefix.length,ply:row.ply,
  state_key:row.state_key,history_key:history,side:row.side,ids:q.ids,distance:q.distance};
 metadata.push(meta);
 assert.equal(row.rootmean_view,'root side-to-move');assert(Number.isFinite(row.rootmean)&&Math.abs(row.rootmean)<=1);
 labels.push({id:row.row_id,split:g.split,rootmean:row.rootmean,z:row.value_eligible?row.z_stm:null});
 const action=state.getLegalActions().find(a=>r.rustAction(state,a)===row.action209);assert(action,'illegal action');
 states.set(row.game_id,state.next(action));
}
for(const [p,a]of[[metadataPath,metadata],[labelsPath,labels]])fs.writeFileSync(p,zlib.gzipSync(a.map(x=>JSON.stringify(x)).join('\n')+'\n'));
console.log(JSON.stringify({rows:metadata.length,metadata_sha256:crypto.createHash('sha256').update(fs.readFileSync(metadataPath)).digest('hex'),
 labels_sha256:crypto.createHash('sha256').update(fs.readFileSync(labelsPath)).digest('hex'),test_labels_remain_generation_owner_only:true,
 canonical_signature_command:'python3 -B tools/nnue-training/frame14.py canonicalize --metadata INPUT.gz --output OUTPUT.gz'}));
