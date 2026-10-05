importScripts('/shared-best-action.js');
let producer;
onmessage=({data})=>{
  try {
    if(data.kind==='attach') {
      producer=SharedBestAction.bind(data.memory,data.context,data.expected);
      postMessage({kind:'attached',isolated:crossOriginIsolated,secure:isSecureContext});
    } else if(data.kind==='publish') {
      const accepted=producer.publish(data.cp);
      postMessage({kind:'published',accepted});
    } else if(data.kind==='stop') {
      producer.stop(data.reason);
      postMessage({kind:'stopped',reason:data.reason});
    }
  } catch(error) { postMessage({kind:'rejected',error:error.message}); }
};
