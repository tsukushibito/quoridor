const fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto'),path=require('node:path');const scope=vm.createContext({console});vm.runInContext(fs.readFileSync(path.join(__dirname,'game.js'),'utf8')+'\n'+fs.readFileSync(path.join(__dirname,'context.js'),'utf8')+'\nglobalThis.api={State,fromPrefix,terminalResult,rustAction,sameAction,referenceState,actionToIndex};',scope);const A=scope.api;
function state(prefix){return A.fromPrefix(prefix)}
function encode(s,a){if(!s.getLegalActions().some(x=>A.sameAction(x,a)))throw Error('ILLEGAL_ACTION');return A.rustAction(s,a)}
function decode(s,id){if(!Number.isInteger(id))throw Error('ACTION_INTEGER');const a=s.getLegalActions().filter(x=>A.rustAction(s,x)===id);if(a.length!==1)throw Error('ACTION_INJECTIVITY_OR_ILLEGAL');return a[0]}
function ids(prefix){let s=state([]),out=[];for(const a of prefix){if(A.terminalResult(s))throw Error('TERMINAL_PREFIX_CONTINUED');out.push(encode(s,a));s=s.next(a)}return out}
function context(s){return {key:s._positionKey(),history:Array.from(s.position_history).sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0),turn:s.getCurrentPlayer(),total_ply:s.depth,remaining_total_ply:Math.max(0,200-s.depth),walls:[s.walls_p1,s.walls_p2],terminal:A.terminalResult(s)}}
function validate(prefix,id){const s=state(prefix);if(A.terminalResult(s))throw Error('TERMINAL_ACTION');const a=decode(s,id);if(encode(s,a)!==id)throw Error('ROUNDTRIP');return a}
function hash(x){return crypto.createHash('sha256').update(JSON.stringify(x)).digest('hex')}
module.exports={...A,state,ids,context,encode,decode,validate,hash};
