'use strict';
const {spawn}=require('child_process'),readline=require('readline');
// FIFO serialization is required by the original native Rust bridge, which has no request ID.
class Pipe{
 constructor(cmd,args=[],{timeoutMs=1000}={}){this.child=spawn(cmd,args,{stdio:['pipe','pipe','pipe']});this.queue=[];this.active=null;this.dead=null;this.timeoutMs=timeoutMs;this.calls=0;this.requestBytes=0;this.responseBytes=0;this.stderr='';this.timings={serialize_ms:0,parse_ms:0,write_callback_ms:0};this.child.stderr.on('data',b=>{this.stderr=(this.stderr+b).slice(-2048)});this.child.once('error',e=>this.fail(e));this.exit=new Promise(resolve=>this.child.once('exit',(code,signal)=>{this.fail(Error('PIPE_EXIT'));resolve({code,signal,pid:this.child.pid})}));readline.createInterface({input:this.child.stdout}).on('line',s=>{this.responseBytes+=Buffer.byteLength(s)+1;const a=this.active;if(!a)return this.fail(Error('UNSOLICITED_PIPE_REPLY'));let x;try{const t=performance.now();x=JSON.parse(s);this.timings.parse_ms+=performance.now()-t}catch(e){return this.fail(Error('PIPE_JSON'))}clearTimeout(a.timer);this.active=null;a.resolve(x);this.next();});}
 ask(x){return new Promise((resolve,reject)=>{if(this.dead)return reject(this.dead);this.queue.push({x,resolve,reject});this.next();});}
 next(){if(this.dead||this.active||!this.queue.length)return;const a=this.active=this.queue.shift();const t=performance.now();const s=JSON.stringify(a.x)+'\n';this.timings.serialize_ms+=performance.now()-t;this.calls++;this.requestBytes+=Buffer.byteLength(s);a.timer=setTimeout(()=>this.fail(Error('PIPE_TIMEOUT')),this.timeoutMs);const wt=performance.now();this.child.stdin.write(s,e=>{this.timings.write_callback_ms+=performance.now()-wt;if(e)this.fail(e)});}
 fail(e){if(this.dead)return;this.dead=e;if(this.active){clearTimeout(this.active.timer);this.active.reject(e);this.active=null;}for(const a of this.queue.splice(0))a.reject(e);}
 async close(){this.child.stdin.end();const done=await Promise.race([this.exit,new Promise(resolve=>{const t=setTimeout(()=>{this.child.kill('SIGTERM');resolve(null)},250);t.unref()})]);if(done)return done;return this.exit;}
}
module.exports={Pipe};
