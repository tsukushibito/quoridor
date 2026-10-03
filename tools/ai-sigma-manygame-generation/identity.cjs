'use strict';
const fields=['run_id','worker_id','game_id','generation','handle','token','request_id'];
function validate(x){if(!x||fields.some(k=>x[k]===undefined))throw Error('IDENTITY_SCHEMA');for(const k of ['run_id','worker_id','game_id','request_id'])if(typeof x[k]!=='string'||!x[k]||x[k].length>128)throw Error('IDENTITY_SCHEMA');for(const k of ['generation','handle','token'])if(!Number.isSafeInteger(x[k])||x[k]<0)throw Error('IDENTITY_SCHEMA');return Object.freeze(Object.fromEntries(fields.map(k=>[k,x[k]])));}
const key=x=>JSON.stringify(fields.map(k=>x[k]));
const owner=x=>JSON.stringify([x.run_id,x.worker_id,x.game_id]);
function features(bits){if(!Array.isArray(bits)||bits.length!==648||bits.some(v=>!Number.isInteger(v)||v<0||v>0xffffffff||(v&0x7f800000)===0x7f800000))throw Error('FEATURE_SCHEMA');return bits;}
module.exports={fields,validate,key,owner,features};
