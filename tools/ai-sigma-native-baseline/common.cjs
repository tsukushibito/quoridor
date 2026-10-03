'use strict';
const fs=require('fs'),path=require('path'),cp=require('child_process'),readline=require('readline');
const ROOT=path.resolve(__dirname,'../..'),A=ROOT+'/.artifacts/ai-sigma/resume-20261003/NATIVE-BASELINE',D=ROOT+'/research-data/ai-sigma/165-native-baseline';
const now=()=>Number(process.hrtime.bigint())/1e6;
class Pipe {
 constructor(command,args,env={}){this.child=cp.spawn(command,args,{stdio:['pipe','pipe','pipe'],env:{...process.env,...env}});this.waiting=[];this.errors='';this.child.stderr.on('data',b=>{this.errors=(this.errors+b).slice(-8192)});readline.createInterface({input:this.child.stdout}).on('line',line=>{const w=this.waiting.shift();if(!w)throw Error('UNEXPECTED_PIPE_REPLY');try{w.resolve(JSON.parse(line))}catch(e){w.reject(e)}});this.exit=new Promise(resolve=>this.child.on('exit',(code,signal)=>{this.closed=true;for(const w of this.waiting.splice(0))w.reject(Error('PIPE_EXIT '+code+' '+signal+' '+this.errors));resolve({code,signal})}));this.child.on('error',e=>{for(const w of this.waiting.splice(0))w.reject(e)});}
 ask(v){if(this.closed)return Promise.reject(Error('PIPE_CLOSED'));return new Promise((resolve,reject)=>{this.waiting.push({resolve,reject});this.child.stdin.write(JSON.stringify(v)+'\n')});}
 async stop(){this.child.stdin.end();return await this.exit;}
}
function identity(pid){const s=fs.readFileSync('/proc/'+pid+'/stat','utf8').split(')').at(-1).trim().split(/\s+/);return{pid,start_ticks:Number(s[19]),ppid:Number(s[1])};}
const save=(file,x)=>fs.writeFileSync(file,JSON.stringify(x,null,2)+'\n');
async function runControlled(config,fn){const {createMonitor}=require('./pause-monitor.cjs');fs.mkdirSync(config.job_out,{recursive:true});const monitor=createMonitor({out:config.job_out,subjectIssue:config.issue,deadlineUTC:config.processing_deadline,windowEndUTC:'2026-10-03T08:15:21Z'});let primary=null,control=null,result=null;try{await monitor.start(e=>{control={code:e.code,message:e.message}});result=await fn(()=>{monitor.check();if(control)throw Error(control.code)})}catch(e){primary={message:e.message,stack:e.stack}}finally{await monitor.stop();if(monitor.state!=='READY')control={code:monitor.state,late_observer:true};save(config.job_out+'/control-summary.json',{result,primary,control,monitor_state:monitor.state,UTC:new Date().toISOString()});}if(primary||control)throw Error(JSON.stringify({primary,control}));return result;}
module.exports={ROOT,A,D,now,Pipe,save,identity,runControlled};
