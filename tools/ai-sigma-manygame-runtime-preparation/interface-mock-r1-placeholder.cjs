'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert'),{record}=require('./teacher-interface.cjs');
const D=path.resolve(__dirname,'../../research-data/ai-sigma/185-manygame-runtime-preparation'),out=process.argv[2];
const mock=JSON.parse(fs.readFileSync(D+'/runs/native185-mock-r1/result.json')),tape=JSON.parse(fs.readFileSync(D+'/runs/native185-tape-r1/result.json'));
const rows=[record(mock.cases[0].results[0],{lineage:'native185-mock-normal',rootNN:{value:.001,view:'synthetic'}})];
const terminal=mock.cases.find(x=>x.case==='K1_rootterminal_teacher_ineligible');for(const x of [terminal.K1,terminal.terminal])rows.push(record(x,{lineage:'native185-mock-'+x.game_id}));
for(const x of tape.results){const mapping=x.cp.root_edges.map((e,i)=>[e[0],i]),mask=Array(136).fill(0);for(const [,i]of mapping)mask[i]=1;rows.push(record(x,{lineage:'native185-saved-tape-'+x.game_id,mapping136:mapping,legal_mask136:mask,source:'FINITE_SCHEMA_ONLY_PLACEHOLDER_MAPPING_NOT_REAL_P2'}));}
for(const row of rows){assert.equal(row.z_stm,null);assert.equal(row.z_p1,null);assert.equal(row.value_loss_mask,0);assert(!row.policy_eligible&&!row.value_eligible&&!row.joint_eligible);if(row.pi136)assert(Math.abs(row.pi136.reduce((s,v)=>s+v,0)-1)<1e-12);else assert.equal(row.edgeSum,0);}
const missingMap=record(tape.results[0],{lineage:'native185-unknown-mapping'});assert.equal(missingMap.pi136,null);assert.equal(missingMap.edgeSum,31);
fs.writeFileSync(out+'/result.json',JSON.stringify({issue:'quoridor-4lc.185',NN:0,model_sessions:0,GPU:0,mock_reply_equivalents:0,rows,missing_map_record:missingMap,canonical_P2_production_mapping:'NOT_IMPLEMENTED_IN_THIS_PLACEHOLDER_SCHEMA_CHECK',teacher_training_rows:0},null,2)+'\n');console.log(JSON.stringify({rows:rows.length,passed:true,training_rows:0}));
