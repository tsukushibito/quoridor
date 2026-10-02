'use strict';
const fs=require('fs'),path=require('path');
const A=path.resolve(__dirname,'../../.artifacts/ai-sigma/continuation-20261001/SIGMA-ACTUAL-BOUNDARY-REPAIR'),GUARD=117440512;
function allocated(roots){let total=0;const seen=new Set();function walk(p){const s=fs.lstatSync(p);if(s.isSymbolicLink())return;const k=s.dev+':'+s.ino;if(seen.has(k))return;seen.add(k);total+=s.blocks*512;if(s.isDirectory())for(const n of fs.readdirSync(p))walk(path.join(p,n));}for(const p of roots)if(fs.existsSync(p))walk(p);return total;}
function gate(forecast){const before=allocated([__dirname,A]),reserved=Object.values(forecast).reduce((a,b)=>a+b,0);const proof={before,reserved,forecast,guard:GUARD,headroom:GUARD-before-reserved};if(!Number.isFinite(reserved)||reserved<0||proof.headroom<=0){const e=new Error('BUDGET_HEADROOM_REQUIRED');e.budget=proof;throw e;}return proof;}
module.exports={gate,allocated,GUARD,A};
