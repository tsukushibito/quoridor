'use strict';
const fs=require('fs'),{performance}=require('perf_hooks');
const boot=()=>fs.readFileSync('/proc/sys/kernel/random/boot_id','utf8').trim();
const key=p=>`${p.pid}:${p.starttick}`;
class Ledger {
 constructor(root){this.root=root;this.boot=boot();this.records=new Map();this.file=process.env.SIGMA_OWNED_LEDGER;this.ack=process.env.SIGMA_OWNED_ACK;if(!this.file||!this.ack)throw Error('OWNED_LEDGER_REQUIRED');}
 add(p,parent){if(this.records.has(key(p)))return;if(!parent)throw Error('OWNED_PARENT_PROOF_MISSING');const r={boot_id:this.boot,root:this.root,identity:p,parent,UTC:new Date().toISOString(),monotonic_ms:performance.now()};this.records.set(key(p),r);fs.appendFileSync(this.file,JSON.stringify(r)+'\n');}
 state(){try{const a=JSON.parse(fs.readFileSync(this.ack));if(a.boot_id!==this.boot)throw Error('OWNED_BOOT_MISMATCH');if(!a.kernel_boundary?.valid||!a.kernel_boundary.sole_explicit_root||a.kernel_boundary.spawn_count!==1||a.kernel_boundary.root?.pid!==this.root.pid||a.kernel_boundary.root?.start_ticks!==this.root.starttick)throw Error('KERNEL_OWNERSHIP_BOUNDARY_INVALID');if(a.unknown_adopted?.length)throw Error('UNKNOWN_ADOPTED_OWNERSHIP_REFUSED');for(const k of this.records.keys()){if(a.rejected?.[k])throw Error('OWNED_REGISTRATION_REJECTED:'+a.rejected[k]);if(!a.accepted?.[k])return false;}return true}catch(e){if(e.code==='ENOENT')return false;throw e}}
 kernelIdentities(){try{const a=JSON.parse(fs.readFileSync(this.ack));if(a.boot_id!==this.boot||!a.kernel_boundary?.valid||a.kernel_boundary.root?.pid!==this.root.pid||a.kernel_boundary.root?.start_ticks!==this.root.starttick)return [];return a.kernel_owned??[]}catch(e){if(e.code==='ENOENT')return [];throw e}}
 async receipt(){const until=performance.now()+100;while(!this.state()&&performance.now()<until)await new Promise(r=>setTimeout(r,5));if(!this.state())throw Error('OWNED_REGISTRATION_TIMEOUT');return {registered:this.records.size,ack:true};}
}
module.exports={Ledger,key};
