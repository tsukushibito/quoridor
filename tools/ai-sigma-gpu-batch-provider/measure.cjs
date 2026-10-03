// One resident child, sequential complete batches; JSON and real pipe timing.
const fs=require('fs'),path=require('path'),zlib=require('zlib'),{spawn}=require('child_process'),readline=require('readline'),{performance}=require('perf_hooks');
const ROOT=path.resolve(__dirname,'../..'),D=path.join(ROOT,'research-data/ai-sigma/177-gpu-batch-provider');
const reg=JSON.parse(fs.readFileSync(path.join(D,'preregister.json'))),fixtures=JSON.parse(fs.readFileSync(path.join(ROOT,'research-data/ai-sigma/174-gpu-inference/inputs.json'))).inputs;
const saved=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(D,'saved174-outputs.json.gz'))));
const raw=zlib.createGzip({level:9}),sink=fs.createWriteStream(path.join(D,'requests.jsonl.gz'));raw.pipe(sink);
let child,pending=null,seq=0,stdio='',exitPromise;
const result={run:'batch-provider-r1',status:'STARTED',parity:[],timing:{},planned_single_sample_equivalent:305};
function save(){fs.writeFileSync(path.join(D,'results.json'),JSON.stringify(result,null,2)+'\n');}
function decode(bits){const b=Buffer.alloc(bits.length*4);bits.forEach((x,i)=>b.writeUInt32LE(x,i*4));return bits.map((_,i)=>b.readFloatLE(i*4));}
function compare(actual,expected){if(actual.length!==expected.length)throw Error('OUTPUT_LENGTH');let max=0;actual.forEach((x,i)=>{const d=Math.abs(x-expected[i]);max=Math.max(max,d);if(!Number.isFinite(x)||d>reg.abs_tol+reg.rel_tol*Math.abs(expected[i]))throw Error('PARITY_DIFF '+d);});return max;}
function items(indices,label){return indices.map((i,j)=>({id:label+':'+j+':fixture'+i,features_bits648:fixtures[i].features_bits}));}
function request(op,more={}){return new Promise((resolve,reject)=>{if(pending)throw Error('MULTIPLE_PENDING');const req={op,request_id:String(++seq),...more},start=performance.now();pending={resolve,reject,req,start};child.stdin.write(JSON.stringify(req)+'\n');});}
async function checked(reqItems,backend,label,expected){const {response,total_ms}=await request('infer_batch',{items:reqItems,backend});const r=response.result;let max=0;if(r.items.length!==reqItems.length)throw Error('ID_COUNT');r.items.forEach((row,i)=>{if(row.id!==reqItems[i].id)throw Error('ID_ATTRIBUTION');const values=decode(row.f32bits137);if(values.length!==137||Math.abs(values[136])>1)throw Error('FINITE_VALUE');compare(values,row.logits.concat([row.value]));if(expected)max=Math.max(max,compare(values,expected[i]));});return {label,backend,B:reqItems.length,total_ms,server:r.batchcost,max_abs:max,outputs:r.items.map(x=>decode(x.f32bits137))};}
(async()=>{save();try{
 const cold=performance.now();child=spawn('/home/vscode/.cache/inference/envs/quoridor-training/bin/python',['-B',path.join(__dirname,'provider.py')],{cwd:ROOT,env:process.env,stdio:['pipe','pipe','pipe']});exitPromise=new Promise(resolve=>child.once('exit',(code,signal)=>resolve({code,signal})));fs.writeFileSync(path.join(D,'provider-owned.json'),JSON.stringify({pid:child.pid,starttick:fs.readFileSync('/proc/'+child.pid+'/stat','utf8').split(')')[1].trim().split(/\s+/)[19],boot:fs.readFileSync('/proc/sys/kernel/random/boot_id','utf8').trim()}));child.stderr.on('data',b=>{stdio+=b;fs.appendFileSync(path.join(D,'provider.stderr'),b);});
 readline.createInterface({input:child.stdout}).on('line',line=>{try{const response=JSON.parse(line),p=pending;if(!p||p.req.request_id!==response.request_id)throw Error('REQUEST_ID_MISMATCH');pending=null;const total_ms=performance.now()-p.start;raw.write(JSON.stringify({request:p.req,response,total_ms})+'\n');if(!response.ok)p.reject(Error(JSON.stringify(response.error)));else p.resolve({response,total_ms});}catch(e){if(pending){pending.reject(e);pending=null;}}});
 child.once('exit',(c,s)=>{if(pending){pending.reject(Error('PROVIDER_EXIT '+c+' '+s));pending=null;}});
 result.info=(await request('info')).response.result;result.cold_startup_to_info_ms=performance.now()-cold;save();
 // Five new batch1 CUDA baselines compare to saved CPUORT and saved CUDA, not new CPU NN.
 const baseline=[];
 for(let i=0;i<5;i++){const r=await checked(items([i],'baseline'+i),'cuda','batch1-fixture'+i,[saved[i].CPUORT]);compare(r.outputs[0],saved[i].torchCUDA);baseline.push(r.outputs[0]);result.parity.push({...r,outputs:undefined});save();}
 const layouts={2:[0,1],4:[1,2,3,4],8:[0,1,2,3,4,2,0,4]};
 for(const B of [2,4,8]){const ix=layouts[B],r=await checked(items(ix,'B'+B),'cuda','heterogeneous-B'+B,ix.map(i=>baseline[i]));result.parity.push({...r,outputs:undefined});save();}
 const ix=layouts[8],reversed=ix.slice().reverse(),changed=ix.slice();changed[3]=0;
 for(const [label,indices] of [['permuted8',reversed],['one-row-replaced8',changed]]){const r=await checked(items(indices,label),'cuda',label,indices.map(i=>baseline[i]));result.parity.push({...r,outputs:undefined});save();}
 result.parity_pass=true;save();
 for(const B of [1,2,4,8]){const ix=B===1?[0]:layouts[B];result.timing[B]={};for(const backend of ['cpuort','cuda']){const warm=await checked(items(ix,'warm'+B+backend),backend,'warm1',ix.map(i=>baseline[i]));const steady=[];for(let j=0;j<8;j++){const r=await checked(items(ix,'steady'+B+backend+j),backend,'steady'+j,ix.map(i=>baseline[i]));steady.push({...r,outputs:undefined});}result.timing[B][backend]={warm:{...warm,outputs:undefined},steady,actual_GPU_batch:backend==='cuda'?B:1,CPUORT_serial_rows:backend==='cpuort'?B:0};save();}}
 result.final_info=(await request('stop')).response.result;child.stdin.end();result.provider_exit=await exitPromise;result.status='COMPLETED';
 }catch(e){result.status='TYPED_FAILURE';result.failure={message:e.message,stack:e.stack,stderr:stdio};if(child){child.kill('SIGTERM');result.provider_exit=await exitPromise;}}finally{raw.end();await new Promise(resolve=>sink.on('finish',resolve));save();console.log(JSON.stringify({status:result.status,parity_pass:result.parity_pass,counters:result.final_info&&result.final_info.single_sample_equivalent}));}
})();
