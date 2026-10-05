const fs=require('fs'),readline=require('readline'),path=require('path'),{spawn}=require('child_process');const RUN=__dirname;
function pipe(cmd,args,log){const child=spawn(cmd,args,{stdio:['pipe','pipe',fs.openSync(path.isAbsolute(log)?log:RUN+'/'+log,'w')]});const queue=[],lines=[];let failure,closePromise,abortPromise;
 const exited=()=>child.exitCode!==null||child.signalCode!==null;
 const fail=e=>{failure=e;while(queue.length)queue.shift().reject(e)};
 const wait=()=>exited()?Promise.resolve():new Promise(resolve=>{child.once('exit',resolve);if(exited()){child.removeListener('exit',resolve);resolve();}});
 readline.createInterface({input:child.stdout}).on('line',l=>{let v;try{v=JSON.parse(l)}catch(e){fail(Error('PIPE_PARSE'));return;}const r=queue.shift();if(r)r.resolve(v);else lines.push(v)});
 child.on('error',fail);child.on('exit',(code,signal)=>fail(Object.assign(Error('BACKEND_EXIT'),{code,signal})));child.stdin.on('error',fail);
 return {child,next:()=>{if(failure)return Promise.reject(failure);if(lines.length)return Promise.resolve(lines.shift());return new Promise((resolve,reject)=>queue.push({resolve,reject}));},send:v=>child.stdin.write(JSON.stringify(v)+'\n'),
 close:()=>{if(closePromise)return closePromise;if(exited())return Promise.resolve();closePromise=wait();child.stdin.end();return closePromise;},
 abort:()=>{if(abortPromise)return abortPromise;if(exited())return Promise.resolve();abortPromise=wait();child.kill('SIGTERM');const timer=setTimeout(()=>{if(!exited())child.kill('SIGKILL')},1000);abortPromise.finally(()=>clearTimeout(timer));return abortPromise;}};
}

module.exports={pipe};
