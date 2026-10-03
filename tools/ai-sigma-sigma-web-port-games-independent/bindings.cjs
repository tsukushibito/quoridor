const fs=require('fs'),crypto=require('crypto'),path=require('path');
const a=require('../ai-sigma-sigma-web-port/adapters.cjs'),D='research-data/ai-sigma/155-sigma-web-port-games-independent/',P='.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT/runs/';
const routes={'/early-page.js':'main','/early-worker.js':'worker','/original-worker.js':'producer','/checkpoint.js':'checkpoint','/snapshot-cache.js':'cache','/reference-core.js':'reference','/player-base.js':'base-worker'};
let out=[];
for(let i=1;i<=4;i++){
 const p=P+`port151-stageB-group${i}-r1/`,saved=JSON.parse(fs.readFileSync(p+'actual-served-source.json','utf8')),binding=JSON.parse(fs.readFileSync(p+'source-bindings.json','utf8'));let rows=[];
 for(const [route,s]of Object.entries(saved)){
 let b=routes[route]?Buffer.from(a.script(routes[route])):fs.readFileSync(s.path);
 if(route==='/numeric-browser.js')b=Buffer.from(b.toString().replace('V.equal(ids,e[engine])','V.equal(ids,e.reference)'));
 const digest=crypto.createHash('sha256').update(b).digest('hex');if(digest!==s.SHA256||b.length!==s.bytes)throw Error('served mismatch '+route);
 rows.push({route,bytes:b.length,SHA256:digest,generated:!!routes[route]||route==='/numeric-browser.js'});
 }
 for(const [name,digest]of Object.entries(binding.local)){if(crypto.createHash('sha256').update(fs.readFileSync(path.resolve('tools/ai-sigma-sigma-web-port',name))).digest('hex')!==digest)throw Error('local binding');}
 const sources=JSON.parse(fs.readFileSync(P+`port151-stageB-group${i}-r1.inputs.json`,'utf8'));for(const n of ['adapters.cjs','port-main.js','port-worker.js']){const file=path.resolve('tools/ai-sigma-sigma-web-port',n);if(crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')!==sources.source[file])throw Error('launch source');}
 out.push({group:i,route_count:rows.length,rows,local:binding.local,launch_git:sources.git_commit,current_bytes_finitely_bound:true,full_build_period_dependency_reads:false,browser_independent_fetch_digest:false});
}
fs.writeFileSync(D+'served-binding-result.json',JSON.stringify(out,null,2));console.log(JSON.stringify(out.map(x=>({group:x.group,route_count:x.route_count,local:x.local}))));
