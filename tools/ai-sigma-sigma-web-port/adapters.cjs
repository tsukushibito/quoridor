'use strict';
const fs=require('fs'),crypto=require('crypto'),path=require('path'),base=require('../ai-sigma-baseline-gap-frame10/adapters.cjs');
const root=path.resolve(__dirname,'../..');
function script(name){
 if(name==='base-worker')return base.script('worker');
 if(name==='worker')return fs.readFileSync(__dirname+'/port-worker.js','utf8');
 let s=base.script(name);
 // Wire identity now states the private refusal guards; shared originals remain read-only.
 s=s.replace(/max_nodes:512/g,'max_nodes:200000').replace(/max_depth:24/g,'max_depth:200').replace(/max_nodes!==512/g,'max_nodes!==200000').replace(/max_depth!==24/g,'max_depth!==200');
 if(name==='main')s=s.replace("max_nodes:spec.engine==='reference'?null:512","max_nodes:spec.engine==='reference'?null:200000").replace("max_depth:spec.engine==='reference'?null:24","max_depth:spec.engine==='reference'?null:200")+'\n'+fs.readFileSync(__dirname+'/port-main.js','utf8');
 return s;
}
function bindings(){return {policy:'faithful fixed Sigma-Web f64 bundle; research CP/SAB/clock/strictfault adapter distinct',old_base_readonly:base.bindings(),local:Object.fromEntries(['adapters.cjs','port-worker.js','port-main.js'].map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(__dirname+'/'+n)).digest('hex')])),served:Object.fromEntries(['main','worker','producer','checkpoint','cache','reference'].map(n=>[n,crypto.createHash('sha256').update(script(n)).digest('hex')]))};}
module.exports={script,bindings};
