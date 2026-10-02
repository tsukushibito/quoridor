'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const base=require('../ai-sigma-diverse-prefix/adapters.cjs');
const root=path.resolve(__dirname,'../..');
function script(name){
  if(name==='main')return base.script('main')+'\n'+fs.readFileSync(__dirname+'/input.js','utf8')+'\n'+fs.readFileSync(__dirname+'/main.js','utf8');
  if(name==='reference')return fs.readFileSync(root+'/tools/ai-sigma-actual-boundary-repair/reference-core.js','utf8');
  if(name==='worker')return fs.readFileSync(__dirname+'/worker.js','utf8');
  return base.script(name);
}
function bindings(){return {...base.bindings(),reference_core:{path:'tools/ai-sigma-actual-boundary-repair/reference-core.js',original_SHA256:crypto.createHash('sha256').update(fs.readFileSync(root+'/tools/ai-sigma-actual-boundary-repair/reference-core.js')).digest('hex'),unchanged:true}};}
module.exports={script,bindings};
