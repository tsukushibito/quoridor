'use strict';
const fs=require('fs');const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function table(){const m=new Map();for(const n of fs.readdirSync('/proc'))if(/^\d+$/.test(n)){try{const s=fs.readFileSync('/proc/'+n+'/stat','utf8').split(')').slice(1).join(')').trim().split(/\s+/);m.set(+n,{pid:+n,ppid:+s[1],starttick:+s[19],state:s[0]})}catch{}}return m}
class OwnedProcesses{
 constructor(){this.root=process.pid;this.ids=new Map();this.children=new Map();this.timer=setInterval(()=>this.scan(),10)}
 register(child){const p=table().get(child.pid);if(p)this.ids.set(p.pid,p.starttick);this.children.set(child.pid,child);this.scan();return child}
 scan(includeZombies=false){const all=table();let known=new Set([this.root]);for(const [p,t]of this.ids)if(all.get(p)?.starttick===t)known.add(p);let more=true;while(more){more=false;for(const p of all.values())if(known.has(p.ppid)&&!known.has(p.pid)){known.add(p.pid);more=true}}for(const p of known)if(p!==this.root&&all.has(p))this.ids.set(p,all.get(p).starttick);return [...this.ids].filter(([p,t])=>all.get(p)?.starttick===t&&(includeZombies||all.get(p)?.state!=='Z')).map(([pid,starttick])=>({pid,starttick}))}
 signal(sig){for(const p of this.scan()){if(p.pid===process.pid)throw Error('PARENT_KILL_FORBIDDEN');try{const q=table().get(p.pid);if(q?.starttick===p.starttick)process.kill(p.pid,sig)}catch(e){if(e.code!=='ESRCH')throw e}}}
 async drain(){for(const c of this.children.values())if(c.exitCode===null&&c.signalCode===null)await Promise.race([new Promise(r=>c.once('exit',r)),sleep(100)]);}
 finish(){clearInterval(this.timer)}
}
const stopped=new WeakMap();
function boundedStop(backend){if(stopped.has(backend))return stopped.get(backend);const p=(async()=>{let graceful;try{graceful=Promise.resolve(backend.stop())}catch(e){graceful=Promise.reject(e)}const first=await Promise.race([graceful.then(proof=>({proof}),error=>({error:error.message})),sleep(120).then(()=>({pending:true}))]);const owner=backend.owner;
 if(!owner){if(!first.proof||first.proof.remaining_pids!==0)throw Error('BOUNDED_CLEANUP_NO_OWNERSHIP_PROOF');return first.proof}
 try{if(first.pending||first.error||owner.scan().length){owner.signal('SIGTERM');await sleep(80);if(owner.scan().length){owner.signal('SIGKILL');await sleep(80)}}await owner.drain();const waitUntil=Date.now()+1000;while(owner.scan(true).length&&Date.now()<waitUntil)await sleep(10);const remaining=owner.scan(true);if(remaining.length)throw Error('OWN_CLEANUP_FAILED');return {remaining_pids:0,tracked:[...owner.ids].map(([pid,starttick])=>({pid,starttick})),forced:!!(first.pending||first.error),graceful_error:first.error??null,waited:true,zombie_identities_absent:true}}finally{owner.finish()}})();stopped.set(backend,p);return p}
module.exports={OwnedProcesses,boundedStop};
