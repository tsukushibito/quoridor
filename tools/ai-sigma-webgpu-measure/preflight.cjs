'use strict';
const fs = require('fs');
const path = require('path');
const CP = require('child_process');
const {createRequire} = require('module');
const {OwnedProcesses,boundedStop} = require('../ai-sigma-actual-boundary-repair/cleanup.cjs');
const {createMonitor} = require('../ai-sigma-actual-boundary-repair/pause-check.cjs');
const ROOT = path.resolve(__dirname, '../..');
const {chromium} = createRequire('/workspaces/quoridor/package.json')('playwright');
const config = JSON.parse(fs.readFileSync(process.argv[3]));
if(process.argv[2] !== '--config' || config.issue !== 'quoridor-4lc.115' || config.frame !== 8) throw Error('CONFIG_BINDING');
const out = ROOT+'/.artifacts/ai-sigma/resume-20261002/WEBGPU-MEASURE/runs/'+config.run_id;
fs.mkdirSync(out);
const save=(name,data)=>fs.writeFileSync(out+'/'+name+'.json',JSON.stringify(data,null,2)+'\n');
const headers={'Cross-Origin-Opener-Policy':'same-origin','Cross-Origin-Embedder-Policy':'require-corp','Cross-Origin-Resource-Policy':'same-origin'};
async function main() {
  const owner=new OwnedProcesses({tracePath:out+'/cleanup.jsonl'});
  const monitor=createMonitor({out,subjectIssue:config.issue,deadlineUTC:config.processing_deadline,windowEndUTC:'2026-10-02T14:05:49Z'});
  let browser=null,primary=null,timer=null,query=null;
  const secondary=[], vram=[], consoleRows=[];
  const original=CP.spawn;
  const queryGPU=()=>new Promise((resolve,reject)=>{
    const child=owner.observeChild(original('nvidia-smi',['--query-gpu=index,name,uuid,memory.total,memory.used,utilization.gpu','--format=csv,noheader,nounits'],{stdio:['ignore','pipe','pipe']}));
    let text='',error='';child.stdout.on('data',b=>text+=b);child.stderr.on('data',b=>error+=b);
    child.once('close',code=>{
      const row={UTC:new Date().toISOString(),PID:child.pid,code,text,error};vram.push(row);
      if(code!==0)return reject(Error('VRAM_READ_ERROR'));
      const used=text.trim().split('\n').map(line=>Number(line.split(',').at(-2).trim()));
      if(!used.length||used.some(n=>!Number.isFinite(n)))return reject(Error('VRAM_SCHEMA_ERROR'));
      if(used.some(n=>n*1048576>=5905580032))return reject(Error('VRAM_GUARD'));
      resolve(row);
    });
  });
  const backend={owner,stop:async()=>{if(browser)await browser.close();return {remaining_pids:0}}};
  try {
    await monitor.start();monitor.check();await queryGPU();
    CP.spawn=(...args)=>owner.observeChild(original(...args));
    try {
      const env={...process.env,LIBGL_ALWAYS_SOFTWARE:'0'};
      browser=await chromium.launch({headless:true,executablePath:'/workspaces/quoridor/artifacts/playwright/chromium-1243/chrome-linux64/chrome',args:config.flags,env});
    } finally {CP.spawn=original;}
    timer=setInterval(()=>{if(query)return;query=queryGPU().catch(error=>{primary??={name:error.name,message:error.message};void browser.close();}).finally(()=>query=null);},1000);
    const ctx=await browser.newContext();
    await ctx.route('**/*',r=>r.request().url()==='http://localhost:5196/'?r.fulfill({headers,contentType:'text/html',body:'<!doctype html><title>115 actual WebGPU preflight</title>'}):r.abort());
    const page=await ctx.newPage();
    page.on('console',msg=>consoleRows.push({type:msg.type(),text:msg.text()}));
    await page.goto('http://localhost:5196/');
    save('preflight',await page.evaluate(async()=>{
      const result={secure:isSecureContext,isolated:crossOriginIsolated,SAB:typeof SharedArrayBuffer,Atomics:typeof Atomics,gpu:!!navigator.gpu,model_NN:0};
      if(!result.gpu)return result;
      let adapter=null,device=null,buffers=[];
      try {
        adapter=await Promise.race([navigator.gpu.requestAdapter({powerPreference:'high-performance',forceFallbackAdapter:false}),new Promise((_,reject)=>setTimeout(()=>reject(Error('ADAPTER_TIMEOUT')),5000))]);
        if(!adapter){result.adapter=null;return result;}
        const info=adapter.info??await adapter.requestAdapterInfo();
        result.adapter={vendor:info.vendor,architecture:info.architecture,device:info.device,description:info.description,isFallbackAdapter:info.isFallbackAdapter??adapter.isFallbackAdapter??null,features:[...adapter.features]};
        device=await adapter.requestDevice();
        device.addEventListener('uncapturederror',e=>{result.uncaptured_errors??=[];result.uncaptured_errors.push(e.error.message);});
        const input=new Uint32Array([3,5,11,17]);
        const data=device.createBuffer({size:16,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_SRC|GPUBufferUsage.COPY_DST});
        const read=device.createBuffer({size:16,usage:GPUBufferUsage.MAP_READ|GPUBufferUsage.COPY_DST});buffers=[data,read];
        device.queue.writeBuffer(data,0,input);
        const shader=device.createShaderModule({code:'@group(0) @binding(0) var<storage,read_write> data: array<u32>; @compute @workgroup_size(1) fn main(@builtin(global_invocation_id) id: vec3<u32>) { data[id.x] = data[id.x] * 2u + 1u; }'});
        const pipeline=await device.createComputePipelineAsync({layout:'auto',compute:{module:shader,entryPoint:'main'}});
        const bind=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:data}}]});
        const start=performance.now(),encoder=device.createCommandEncoder(),pass=encoder.beginComputePass();
        pass.setPipeline(pipeline);pass.setBindGroup(0,bind);pass.dispatchWorkgroups(4);pass.end();encoder.copyBufferToBuffer(data,0,read,0,16);device.queue.submit([encoder.finish()]);
        await device.queue.onSubmittedWorkDone();await read.mapAsync(GPUMapMode.READ);
        result.sentinel={input:[...input],output:[...new Uint32Array(read.getMappedRange())],queue_and_readback_ms:performance.now()-start,expected:[7,11,23,35],NN:0};
        read.unmap();
        result.sentinel.passed=JSON.stringify(result.sentinel.output)===JSON.stringify(result.sentinel.expected);
      } catch(error){result.error={name:error.name,message:error.message};}
      finally {for(const b of buffers)b.destroy();if(device){device.destroy();result.device_destroyed=true;}result.buffers_destroyed=buffers.length;}
      return result;
    }));
    const session=await browser.newBrowserCDPSession();save('cdp-system-info',await session.send('SystemInfo.getInfo'));await session.detach();
    const gpuPage=await ctx.newPage();await gpuPage.goto('chrome://gpu');await gpuPage.waitForTimeout(400);save('chrome-gpu',{text:await gpuPage.locator('body').innerText()});
    save('browser',{version:browser.version(),flags:config.flags,env_override:{LIBGL_ALWAYS_SOFTWARE:'0'},console:consoleRows});
    monitor.check();await queryGPU();
  } catch(error){primary??={name:error.name,message:error.message,stack:error.stack};}
  finally {
    CP.spawn=original;if(timer)clearInterval(timer);if(query)await query;
    try{await monitor.stop();}catch(error){secondary.push({stage:'monitor',message:error.message});}
    try{save('controlled-stop',await boundedStop(backend));}catch(error){secondary.push({stage:'browser-stop',message:error.message});}
    save('vram-monitor',vram);save('summary',{primary,secondary,model_NN:0,compute_only:true,actual_go:false});
  }
  console.log(JSON.stringify({out,primary,secondary}));if(primary||secondary.length)process.exitCode=1;
}
main().catch(error=>{console.error(error.stack);process.exitCode=1;});
