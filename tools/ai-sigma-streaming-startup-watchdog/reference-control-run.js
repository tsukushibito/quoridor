async function runMCTSControl(state,numSims,evaluator,cancelToken,onProgress=null){
 const c=clockContext,root=new MCTSNode(state);let checkpoint=null;
 function commit(){const finishStart=stamp();check(c);const p=pickFromVisits(root.children,0);if(p)checkpoint={action:p.action,at:stamp(),rootVisits:root.visitCount,simulations:c.simulations};check(c);c.checkpoint=checkpoint;c.spans.push({kind:'finish',start:finishStart,end:stamp()});}
 try{check(c,true);const initVal=await expandNode(root,evaluator);check(c);backup(root,initVal);commit();c.rootFinished=stamp();await new Promise(r=>setTimeout(r,0));
  for(let i=0;i<numSims;i++){check(c,true);const begin=stamp(),leaf=selectLeaf(root);leaf.ensureState();check(c);let value;
   const t=terminalResult(leaf.state);if(t)value=t.value;else value=await expandNode(leaf,evaluator);
   check(c);backup(leaf,value);check(c);c.simulations++;commit();c.steps.push(stamp()-begin);await new Promise(r=>setTimeout(r,0));
  }
 }catch(e){if(e.message!=='guard')throw e;c.stopped='guard';}
 check(c);return root;
}

