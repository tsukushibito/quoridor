'use strict';
const now=()=>Number(process.hrtime.bigint())/1e6;
function detail(e,stage,state={}){return {UTC:new Date().toISOString(),monotonic_ms:now(),stage,name:e?.name??null,message:e?.message??String(e),code:e?.code??null,stack:e?.stack??null,remote_exception:e?.source_error??null,state};}
async function preserveAndClean(save,stage,primary,cleanup,state={}){save('primary-exception-'+stage,detail(primary,stage,state));try{const proof=await cleanup();save('cleanup-after-'+stage,{UTC:new Date().toISOString(),proof});}catch(secondary){save('secondary-cleanup-'+stage,detail(secondary,stage,state));primary.cleanup_failure=secondary.message;}throw primary;}
module.exports={detail,preserveAndClean};
