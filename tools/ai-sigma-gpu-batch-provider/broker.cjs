// Generator owner supplies askBatch(items); no child spawning or teacher policy here.
// At most one pending request per independent search; bounded microbatch delay.
class Broker {
 constructor(askBatch,{maxBatch=2,flushMs=.25}={}){if(![1,2,4,8].includes(maxBatch)||flushMs<0||flushMs>1)throw Error('BROKER_CONFIG');this.askBatch=askBatch;this.maxBatch=maxBatch;this.flushMs=flushMs;this.queue=[];this.owners=new Set;this.timer=null;this.busy=false;this.stopped=false;this.next=0;}
 infer(searchId,features_bits648){return new Promise((resolve,reject)=>{if(this.stopped)return reject(Error('STOPPED'));if(this.owners.has(searchId))return reject(Error('ONE_PENDING_PER_SEARCH'));this.owners.add(searchId);const id=String(++this.next)+':'+searchId;this.queue.push({id,searchId,features_bits648,resolve,reject});this.schedule();});}
 schedule(){if(this.busy||this.stopped||!this.queue.length)return;if(this.queue.length>=this.maxBatch){if(this.timer)clearTimeout(this.timer);this.timer=null;void this.flush();}else if(!this.timer)this.timer=setTimeout(()=>{this.timer=null;void this.flush();},this.flushMs);}
 async flush(){if(this.busy||this.stopped)return;this.busy=true;const batch=this.queue.splice(0,this.maxBatch);try{const rows=await this.askBatch(batch.map(({id,features_bits648})=>({id,features_bits648})));if(rows.length!==batch.length||rows.some((r,i)=>r.id!==batch[i].id))throw Error('BROKER_ID_ATTRIBUTION');batch.forEach((b,i)=>b.resolve(rows[i]));}catch(e){batch.forEach(b=>b.reject(e));}finally{batch.forEach(b=>this.owners.delete(b.searchId));this.busy=false;this.schedule();}}
 stop(){this.stopped=true;if(this.timer)clearTimeout(this.timer);this.timer=null;for(const b of this.queue.splice(0)){this.owners.delete(b.searchId);b.reject(Error('STOPPED'));}return {in_flight:this.busy,pending_searches:this.owners.size};}
}
module.exports={Broker};
