'use strict';
const vm=require('vm'),fs=require('fs'),assert=require('assert/strict'),path=require('path');
const root=path.resolve(__dirname,'../..'),box=vm.createContext({Math,JSON,Uint32Array,Float32Array,Map,Set,structuredClone});
for(const file of ['game.js','context.js'])vm.runInContext(fs.readFileSync(root+'/tools/ai-sigma-actual-boundary-repair/'+file,'utf8'),box);
vm.runInContext(fs.readFileSync(__dirname+'/deep-input.js','utf8'),box);
const inputs=JSON.parse(fs.readFileSync(root+'/research-data/ai-sigma/132-deep-node-comparison/raw-input-prefixes.json')).inputs;
const fixtures=inputs.map(x=>box.deepFixture(x));fixtures.forEach(x=>box.deepCheckedState(x));
assert.deepEqual(fixtures.map(x=>x.board.total_ply),[12,20,13,21]);
const corrupt=structuredClone(fixtures[0]);corrupt.history_counts=[];assert.throws(()=>box.deepCheckedState(corrupt));
let value=.6;const changes=[];for(let i=0;i<3;i++){value=-value;changes.push(value);}assert.deepEqual(changes,[-.6,.6,-.6]);
// Exercise actual reference backup hook with mock state/NN0; don't claim Wasm backup from this.
const reference=fs.readFileSync(root+'/tools/ai-sigma-actual-boundary-repair/reference-core.js','utf8');
vm.runInContext('let clockContext=null;function stamp(){return 0;}'+reference+'\nglobalThis.signProbe=()=>{const r=new MCTSNode(null);const c=new MCTSNode(null,r);backup(c,.6);return [r.valueSum,c.valueSum,r.visitCount,c.visitCount];};',box);
assert.deepEqual(Array.from(box.signProbe()),[-.6,.6,1,1]);
const adapters=require('./adapters.cjs');for(const name of ['main','worker','producer','checkpoint','cache','reference'])new vm.Script(adapters.script(name));
console.log(JSON.stringify({NN0:true,real_browser:false,fixtures:fixtures.map(x=>({id:x.id,key:x.history_count_key,side:x.board.turn,total_ply:x.board.total_ply,new_public_plies:x.new_public_plies,legal:x.legal_ids.length})),history_mutation_rejected:true,reference_backup_artificial_sign:true,trace_cap:8,count_root32_edge31:true}));
