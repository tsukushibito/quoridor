'use strict';
const readline=require('readline'),{search,q,history}=require('./alpha.cjs'),{identity}=require('../ai-sigma-native-baseline/common.cjs');let active=null,stopped=false;
const emit=x=>process.stdout.write(JSON.stringify(x)+'\n');
readline.createInterface({input:process.stdin}).on('line',line=>{let x;try{x=JSON.parse(line);}catch(e){emit({kind:'fatal',error:'JSON_INPUT'});return;}
 if(x.op==='stop'){if(active&&active.id===x.id)stopped=true;return;}
 if(x.op==='init'){emit({kind:'init',id:x.id,data:{schema:'distance-alpha-v1',NN:0,startup:{count:0},identity:identity(process.pid)}});return;}
 if(x.op==='close'){if(active){emit({kind:'closed',id:x.id,error:'CLOSE_ACTIVE'});return;}emit({kind:'closed',id:x.id,data:{NN_total:0,zero:true}});process.stdin.destroy();return;}
 if(x.op==='search'){if(active){emit({kind:'result',id:x.id,error:'ACTIVE_OLD'});return;}active=x;stopped=false;
  const s=q.r.fromPrefix(x.legal_prefix),root_state=q.r.portState(s),hist=history(s);
  void search(s,{generation:x.generation,deadline_ms:x.deadline_ms,maxdepth:4,node_cap:8192,stop:()=>stopped,onCP:cp=>emit({kind:'cp',id:x.id,cp})}).then(data=>{active=null;emit({kind:'result',id:x.id,data:{...data,root_state,root_history:hist}});}).catch(e=>{active=null;emit({kind:'result',id:x.id,error:e.stack});});
 }
});
