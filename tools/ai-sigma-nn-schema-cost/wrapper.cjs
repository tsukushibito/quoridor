'use strict';
function makeWrapper(N,clock){
 return async function evaluate({side,fixture,reference,A,B,count}){
  const spans={whole_start_ms:clock()};let r;
  try{
   const f=structuredClone(fixture);spans.input_clone_end_ms=clock();
   N.fixtureSchema(f);spans.input_validation_end_ms=clock();
   if(side==='A'){
    count.A_attempt++;spans.opaque_ABI_start_ms=clock();
    r=A.diagnose(f);count.A_complete++;
    spans.opaque_ABI_end_ms=clock();spans.A_kernel_span=null;
   }else if(side==='B'){
    spans.feature_only_start_ms=clock();
    const input=B.call({op:'raw',fixture:f});count.raw_feature_calls++;
    spans.feature_only_end_ms=clock();
    N.equal(input.features_bits,N.bits(f.raw_features_float32),'WHOLE_B_FEATURE_BITS');
    count.B_attempt++;const inference=await B.infer(input.features_bits);count.B_complete++;
    spans.B_infer=inference.spans;
    spans.policy_start_ms=clock();
    const policy=B.call({op:'raw_policy',fixture:f,logits:inference.logits});count.raw_policy_calls++;
    spans.policy_end_ms=clock();
    r={...input,...inference,raw_prior:policy.priors};
   }else throw Error('SELECTED_BACKEND');
   r.id=f.id;r.backend=side;
   spans.validation_start_ms=clock();
   const numeric_gate=N.validate(f,r,reference,side);
   spans.validation_end_ms=clock();
   const formatted={schema:'raw-evaluation-wrapper-v1',id:f.id,backend:side,
    features_bits:r.features_bits,logits:side==='A'?r.policy_logits:r.logits,
    value:r.value,raw_legal:r.raw_legal,raw_prior:r.raw_prior,effective_legal:r.effective_legal};
   spans.format_start_ms=clock();
   const formatted_json=JSON.stringify(formatted),encoded=new TextEncoder().encode(formatted_json);
   spans.format_encoding_end_ms=clock();spans.whole_end_ms=clock();
   return {...r,numeric_gate,spans,formatted_json,formatted_bytes:encoded.length,
    whole_call_ms:spans.whole_end_ms-spans.whole_start_ms,
    validation_start_ms:spans.validation_start_ms,validation_end_ms:spans.validation_end_ms};
  }catch(e){e.wrapper_evidence={side,id:fixture.id,spans,raw_before_failure:r??null,
    count:{...count},whole_failure_ms:clock()-spans.whole_start_ms};throw e}
 };
}
if(typeof module!=='undefined')module.exports={makeWrapper};
