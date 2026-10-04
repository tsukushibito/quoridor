'use strict';
const q=require('../ai-sigma-nnue-qf1-prototype/qf1.cjs'),fs=require('fs'),assert=require('assert');
const add=(a,b)=>Math.fround(a+b),mul=(a,b)=>Math.fround(a*b);
function load(manifest){const m=JSON.parse(fs.readFileSync(manifest));assert.equal(m.feature,'QF1-f32-STM-scaled-v1');return{m,w:q.load(m.weights)}}
function valueScaled(a,w,m){const p=a.side-1,x=Array.from(a.a[p],v=>Math.max(0,v)).concat(Array.from(a.a[1-p],v=>Math.max(0,v)),a.distance.map((d,i)=>Math.fround(Math.fround(Math.fround(d)-m.mu_f32[i])/m.sigma_f32[i])));let out=w.ob;for(let j=0;j<32;j++){let h=w.hb[j];for(let k=0;k<66;k++)h=add(h,mul(w.H[j*66+k],x[k]));out=add(out,mul(w.O[j],Math.max(0,h)))}const v=Math.fround(Math.tanh(out));assert(Number.isFinite(v)&&Math.abs(v)<=1);return v}
function distance(s,m){const t=q.r.terminalResult(s);if(t)return t.value;const d=q.input(s).distance;return Math.max(-1,Math.min(1,add(Math.fround(m.distance_fit.a),mul(Math.fround(m.distance_fit.b),Math.fround(Math.fround(d[1])-Math.fround(d[0]))))))}
const history=s=>JSON.stringify([s._positionKey(),s.getCurrentPlayer(),[...s.position_history].sort(([a],[b])=>a<b?-1:a>b?1:0)]);
module.exports={q,load,valueScaled,distance,history};
