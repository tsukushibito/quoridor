'use strict';
function admitCP({cp,receive,validateEnd,t0,cutoff,generation,legal,finalized}){if(finalized)return{accepted:false,code:'AFTER_PUBLIC'};if(cp.generation!==generation)return{accepted:false,code:'STALE_GENERATION'};if(!Number.isFinite(receive)||!Number.isFinite(validateEnd)||receive<t0||validateEnd<receive)return{accepted:false,code:'CLOCK_UNKNOWN'};if(validateEnd>t0+cutoff)return{accepted:false,code:'LATE_CP'};if(!Number.isInteger(cp.action)||!legal.includes(cp.action)||!(cp.simulations>=1)||cp.root_visits!==cp.simulations)return{accepted:false,code:'ILLEGAL_OR_SCHEMA'};return{accepted:true,code:'ADMITTED'};}
// Synchronous transaction: validation and cloning, tentative assignment, actual
// completion clock, certify or rollback. No await/public callback within it.
function commitCP({slot,cp,receive,t0,cutoff,generation,legal,finalized,clock,clone=structuredClone}){
 const begin=clock(),v=admitCP({cp,receive,validateEnd:begin,t0,cutoff,generation,legal,finalized});
 if(!v.accepted)return{...v,actualEnd:null};
 const previous=slot.cache;let scratch;
 try{scratch={cp:clone(cp),receive_ms:receive-t0,admit_ms:null};}catch(e){return{accepted:false,code:'CLONE_UNKNOWN',actualEnd:null};}
 slot.cache=scratch;
 const actualEnd=clock();
 if(!Number.isFinite(actualEnd)||actualEnd<begin||actualEnd>t0+cutoff){slot.cache=previous;return{accepted:false,code:Number.isFinite(actualEnd)&&actualEnd>=begin?'LATE_CP':'CLOCK_UNKNOWN',actualEnd};}
 scratch.admit_ms=actualEnd-t0;
 return{accepted:true,code:'ADMITTED',actualEnd};
}
module.exports={admitCP,commitCP};
