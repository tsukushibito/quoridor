'use strict';const {spawn}=require('child_process'),readline=require('readline'),{now,identity}=require('./common.cjs');
class Engine {
 constructor(engine){this.engine=engine;this.child=spawn(process.execPath,['--max-old-space-size=192',__dirname+'/engine.cjs',engine],{stdio:['pipe','pipe','pipe']});this.seq=0;this.pending=new Map();this.err='';this.child.stderr.on('data',b=>{this.err=(this.err+b).slice(-16384)});this.exit=new Promise(resolve=>this.child.on('exit',(code,signal)=>{for(const p of this.pending.values())p.reject(Error('ENGINE_EXIT '+code+' '+signal+' '+this.err));resolve({code,signal})}));readline.createInterface({input:this.child.stdout}).on('line',line=>{const receive=now();let x;try{x=JSON.parse(line)}catch(e){throw Error('ENGINE_JSON '+line.slice(0,100))}const p=this.pending.get(x.id);if(!p)throw Error('UNKNOWN_ENGINE_REPLY');if(x.kind==='cp'){p.cp?.(x,receive);return}this.pending.delete(x.id);if(x.error)p.reject(Error(x.error));else p.resolve({...x,controller_receive_ms:receive})});}
 request(q,onCP){const id=++this.seq;return new Promise((resolve,reject)=>{this.pending.set(id,{resolve,reject,cp:onCP});this.child.stdin.write(JSON.stringify({...q,id})+'\n')});}
 stopCurrent(){for(const id of this.pending.keys())this.child.stdin.write(JSON.stringify({op:'stop',id})+'\n')}
 async init(mock=false){const x=await this.request({op:'init',mock});this.info=x.data;return x.data;}
 async close(){const x=await this.request({op:'close'});this.child.stdin.end();return{receipt:x.data,exit:await this.exit,stderr:this.err};}
}
module.exports={Engine};
