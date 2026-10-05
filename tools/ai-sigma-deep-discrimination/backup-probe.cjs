const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const source=fs.readFileSync('tools/ai-sigma-actual-boundary-repair/reference-core.js','utf8');
const context={};vm.runInNewContext(source+'\nthis.probe={MCTSNode,backup,pickFromVisits};',context);
const {MCTSNode,backup,pickFromVisits}=context.probe;let out=[];
for(const depth of [1,2,3,4])for(const value of [-.75,.25]){
 let root=new MCTSNode({}),leaf=root,nodes=[root];
 for(let i=0;i<depth;i++){leaf=new MCTSNode({},leaf,i,.5);nodes.push(leaf);}
 backup(leaf,value);
 // Mechanical edge backup from candidate source: negate child-side value per parent.
 let v=value,edgeValues=[];for(let i=depth-1;i>=0;i--){v=-v;edgeValues.unshift(v);}
 for(let i=0;i<depth;i++)assert.equal(edgeValues[i],-nodes[i+1].qValue);
 assert.equal(root.qValue,value*(depth%2?-1:1));
 out.push({artificial:true,depth,leaf_value:value,root_q:root.qValue,edge_parent_values:edgeValues});
}
const first=new MCTSNode({},null,3,.1),second=new MCTSNode({},null,5,.9);
assert.equal(pickFromVisits([first,second],0).action,3);
const finish={artificial:true,all_child_visits:0,reference_first_action:3,candidate_unique_max_prior_action:5,root_terminal_children_tested:false};
const result={issue:'quoridor-4lc.130',run:'backup130-r1',source_SHA:crypto.createHash('sha256').update(source).digest('hex'),probe:out,finish,NN:0,games:0,limits:'Reference backup/pickFromVisits are actual saved source. Candidate negation is std arithmetic transcription, not Rust/Wasm runtime or real deep trace.'};
fs.writeFileSync('research-data/ai-sigma/130-deep-discrimination/backup-probe.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
