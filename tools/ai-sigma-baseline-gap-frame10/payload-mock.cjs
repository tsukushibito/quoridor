'use strict';const fs=require('fs'),path=require('path'),crypto=require('crypto');
const out=path.resolve(__dirname,'../../.artifacts/ai-sigma/resume-20261003/BASELINE-GAP/runs');
let peak=0,total=0;const cases=[];
for(let index=0;index<4;index++){
 const game={id:'mock-'+index,status:'terminal',winner:1,reason:'artificial fixture only'};
 const data={game,rows:Array.from({length:32},(_,i)=>({spec:{engine:i%2?'reference':'candidate',turn:i},numeric:{features_bits:Array(648).fill(0),policy_logits:Array(136).fill(0),value:0},firstCP:{sequence:1,completed_backup:1,completed_NN:1},adoptedCP:{sequence:8,completed_backup:8,completed_NN:8},artificial_payload:'x'.repeat(262144)}))};
 const body=JSON.stringify(data),p=out+'/payload-mock-'+index+'.tmp';fs.writeFileSync(p,body);const restored=JSON.parse(fs.readFileSync(p,'utf8'));if(restored.rows.length!==32||restored.game.id!==game.id)throw Error('POSTGAME_PAYLOAD_RESTORE');
 peak=Math.max(peak,process.memoryUsage().rss);if(peak>=896*1024*1024)throw Error('STATIC_RSS_GUARD');total+=Buffer.byteLength(body);cases.push({id:game.id,bytes:Buffer.byteLength(body),SHA256:crypto.createHash('sha256').update(body).digest('hex')});fs.unlinkSync(p);
}
const record={NN:0,Chrome:0,artificial:true,sequential_game_save:cases,total_bytes:total,sampled_current_RSS_peak:peak,terminal_or_model_behavior_not_tested:true,Node_heap_MiB:768};fs.writeFileSync(out+'/payload-mock-result.json',JSON.stringify(record,null,2)+'\n');console.log(JSON.stringify(record));
