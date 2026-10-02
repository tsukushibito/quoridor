 'use strict';
importScripts('/count-base.js');
const countHandler=onmessage, countSend=send;
let countChannel=null,countControl=null;
send=function(row){
 if(row.kind==='deep_result'&&countChannel){
  if(!row.primary&&row.cp?.action!==null){const visits=boundEngine==='candidate'?row.cp.simulations:row.cp.root_visits;countChannel.publish({completed:true,sequence:visits,action:row.cp.action,value:row.numeric[0].value,visits});}
  row.shared_publication=countChannel.status();row.control=countControl.status();row.ACK_ms=epoch();
 }
 countSend(row);
};
onmessage=async e=>{
 if(e.data.kind!=='deep_search')return countHandler(e);
 const d=e.data,s=walllessCheck(d.fixture);
 countChannel=SharedBestAction.bind(d.shared,d.shared_context,d.shared_context);
 countControl=PlayerControl.bind(d.control,d.generation);requestControl=countControl;requestIdentity={generation:d.generation,request_id:d.id};
 try{await countHandler(e);}finally{requestControl=null;requestIdentity=null;countChannel=null;countControl=null;}
};
