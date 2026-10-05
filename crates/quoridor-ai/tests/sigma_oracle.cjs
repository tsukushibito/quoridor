'use strict';
// Independent JavaScript oracle, used only by Rust compatibility tests.
const {createReference}=require('../../../tools/ai-sigma-native/reference.cjs');
(async()=>{
  const results=[];
  for(const prefix of [[],[{type:'pawn',direction:[0,1]}],[{type:'wall',orientation:'h',x:2,y:3}]]){
    for(const K of [32,64,800]){
      const {r}=createReference();r.reset(false);
      r.setClock({spans:[],steps:[],simulations:0});
      let nn=0;
      const evaluator=async(state,legal)=>{
        nn++;
        const f=Float32Array.from(state.toNNInput());
        const bits=new Uint32Array(f.buffer);
        let hash=0;for(const v of bits)hash=(hash+v)>>>0;
        const value=Math.fround(((hash%201)-100)/128);
        const perm=r.vertPolicyPermutation(9);
        const logits=legal.map(a=>{let i=r.actionToIndex(a,9);if(state.getCurrentPlayer()===2)i=perm[i];return Math.fround((i-68)/512)});
        const max=Math.max(...logits),ex=logits.map(x=>Math.exp(x-max)),sum=ex.reduce((a,b)=>a+b,0);
        return [ex.map(x=>x/sum),value];
      };
      const root=await r.runMCTS(r.fromPrefix(prefix),K-1,evaluator,{});
      results.push({K,prefix,nn,cp:r.CP(root,1)});
    }
  }
  process.stdout.write(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exitCode=1});
