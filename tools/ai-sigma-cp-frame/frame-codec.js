(function(root) {
 'use strict';
 const clone = value => JSON.parse(JSON.stringify(value));
 const equal = (a,b) => JSON.stringify(a) === JSON.stringify(b);
 const fail = name => {throw Error(name);};
 function route(identity) {
  return {request_id:identity.request_id,engine:identity.engine,generation:identity.generation,epoch:identity.epoch};
 }
 function invariant(message) {
  const edges = message.owned?.cp?.root_edges;
  if(!Array.isArray(edges) || edges.some(edge=>!Array.isArray(edge)||edge.length!==4)) fail('FRAME_EDGE_SHAPE');
  return {identity:message.identity,producer_identity:message.producer_identity,owned_identity:message.owned.identity,edge_order_prior:edges.map(edge=>[edge[0],edge[1]])};
 }
 class Encoder {
  constructor() {this.frames=new Map();}
  pack(message) {
   if(message.kind!=='snapshot') return message;
   const content=invariant(message);
   const key=message.identity.request_id+':'+message.identity.generation;
   const existing=this.frames.get(key);
   if(existing&&!equal(existing,content)) fail('FRAME_INVARIANT_CHANGED');
   if(!existing)this.frames.set(key,clone(content));
   const {identity,producer_identity,owned,...dynamic}=message;
   const {identity:ownedIdentity,cp,...ownedDynamic}=owned;
   const {root_edges,...cpDynamic}=cp;
   return {...dynamic,identity:route(identity),frame_encoding:'cp-frame-v1',frame_ref:key,
    ...(!existing?{frame:content}:{}),owned:{...ownedDynamic,cp:cpDynamic},edge_stats:root_edges.map(edge=>[edge[2],edge[3]])};
  }
  drop(identity) {this.frames.delete(identity.request_id+':'+identity.generation);}
 }
 class Decoder {
  constructor() {this.frames=new Map();}
  restore(wire,expected) {
   if(wire.frame_encoding===undefined)return wire;
   if(wire.frame_encoding!=='cp-frame-v1'||wire.kind!=='snapshot') fail('FRAME_SCHEMA');
   const key=expected.request_id+':'+expected.generation;
   if(wire.frame_ref!==key||!equal(wire.identity,route(expected))) fail('FRAME_ROUTE');
   let frame=this.frames.get(key);
   if(wire.frame) {
    if(frame||wire.sequence!==1) fail('FRAME_REDEFINED');
    if(!equal(wire.frame.identity,expected)||!equal(wire.frame.producer_identity,expected)) fail('FRAME_CONTEXT');
    frame=clone(wire.frame);
    this.frames.set(key,frame);
   }
   if(!frame)fail('FRAME_MISSING');
   if(!Array.isArray(frame.edge_order_prior)||!Array.isArray(wire.edge_stats)||frame.edge_order_prior.length!==wire.edge_stats.length) fail('FRAME_EDGE_SHAPE');
   const edges=frame.edge_order_prior.map((edge,index)=>{
    const stats=wire.edge_stats[index];
    if(!Array.isArray(edge)||edge.length!==2||!Array.isArray(stats)||stats.length!==2)fail('FRAME_EDGE_SHAPE');
    return [edge[0],edge[1],stats[0],stats[1]];
   });
   const {frame_encoding,frame_ref,frame:unused,edge_stats,identity,owned,...dynamic}=wire;
   return {...dynamic,identity:clone(frame.identity),producer_identity:clone(frame.producer_identity),owned:{...owned,identity:clone(frame.owned_identity),cp:{...owned.cp,root_edges:edges}}};
  }
  drop(identity) {this.frames.delete(identity.request_id+':'+identity.generation);}
 }
 const api={Encoder,Decoder,invariant};
 Object.assign(root,{CPFrame:api});
 if(typeof module!=='undefined')module.exports=api;
})(globalThis);
