'use strict';
const {spawn}=require('child_process'),readline=require('readline'),{now}=require('../ai-sigma-native-baseline/common.cjs');
class Engine{
 constructor(name,core){this.name=name;this.seq=0;this.pending=new Map();this.err='';const file=name==='candidate'?__dirname+'/candidate-engine.cjs':__dirname+'/../ai-sigma-native-ni-arena/load-engine.cjs';this.child=spawn('taskset',['-c',String(core),process.execPath,'--max-old-space-size=512',file,name],{stdio:['pipe','pipe','pipe']});this.child.stderr.on('data',b=>{this.err=(this.err+b).slice(-8192);});this.exit=new Promise(resolve=>this.child.on('exit',(code,signal)=>{for(const p of this.pending.values())p.reject(Error('ENGINE_EXIT '+code+' '+signal+' '+this.err));this.pending.clear();resolve({code,signal});}));readline.createInterface({input:this.child.stdout}).on('line',line=>{let x;try{x=JSON.parse(line);}catch(e){for(const p of this.pending.values())p.reject(Error('ENGINE_JSON'));return;}const p=this.pending.get(x.id);if(!p)return;if(x.kind==='cp'){p.onCP?.(x,now());return;}this.pending.delete(x.id);x.error?p.reject(Error(x.error)):p.resolve({...x,receive:now()});});}
 request(v,onCP){const id=++this.seq;return new Promise((resolve,reject)=>{this.pending.set(id,{resolve,reject,onCP});this.child.stdin.write(JSON.stringify({...v,id})+'\n');});}
 stop(){for(const id of this.pending.keys())this.child.stdin.write(JSON.stringify({op:'stop',id})+'\n');}
 async init(mock=false){return(await this.request({op:'init',mock})).data;}
 async close(){this.stop();const x=await this.request({op:'close'});this.child.stdin.end();return{receipt:x.data,exit:await this.exit,stderr:this.err};}
}
module.exports={Engine};
