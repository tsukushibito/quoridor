// Search and cooperative clock remain in the stopped 97 Worker.
importScripts('/frame-codec.js');
const rawPost=postMessage.bind(globalThis);
let encoder=new CPFrame.Encoder();
let frameCondition='original';
globalThis.postMessage=function(message) {
 const begin=performance.timeOrigin+performance.now();
 const originalBytes=new TextEncoder().encode(JSON.stringify(message)).length;
 let wire=message;
 if(message.kind==='snapshot'&&frameCondition==='frame')wire=encoder.pack(message);
 const wireBytes=new TextEncoder().encode(JSON.stringify(wire)).length;
 wire.frame_measure={original_payload_bytes:originalBytes,wire_payload_bytes:wireBytes,pack_and_size_ms:performance.timeOrigin+performance.now()-begin};
 rawPost(wire);
 if(message.kind==='stopped'&&message.identity)encoder.drop(message.identity);
};
importScripts('/original-worker.js');
const originalMessage=onmessage;
onmessage=async function(event) {
 if(['request','direct','mock'].includes(event.data.kind)) {
  frameCondition=event.data.frame_condition??'original';
  encoder=new CPFrame.Encoder();
 }
 return originalMessage(event);
};
