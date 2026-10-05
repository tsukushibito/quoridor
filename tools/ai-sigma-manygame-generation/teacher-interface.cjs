'use strict';
// Compatibility default preserves the old diagnostic source label; no training eligibility.
const {record: sharedRecord}=require('../ai-sigma-common/generation/diagnostic-record.cjs');
function record(result, options={}) {return sharedRecord(result,{source:'185-NN0',...options});}
module.exports={record};
