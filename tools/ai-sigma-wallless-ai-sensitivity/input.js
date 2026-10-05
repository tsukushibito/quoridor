 'use strict';
function walllessCheck(x){
 const s=fromPrefix(x.prefix),f=s.toNNInput(),bits=Array.from(new Uint32Array(f.buffer,f.byteOffset,f.length));
 const checks={key:s._positionKey(),side:s.getCurrentPlayer(),pawns:[s.player1pos,s.player2pos],walls:[s.walls_p1,s.walls_p2],depth:s.depth,history:Array.from(s.position_history),featuresbits:bits,root_legal:s.getLegalActions()};
 for(const [k,v]of Object.entries(checks))if(JSON.stringify(v)!==JSON.stringify(x[k]))throw Error('WALLLESS_INPUT_'+k);
 if(terminalResult(s)||s.walls_p1||s.walls_p2||bits.length!==648)throw Error('WALLLESS_INPUT_SHAPE');return s;
}
function deepCheckedState(x){return walllessCheck(x);}
function deepRustPrefix(prefix){let s=fromPrefix([]);return prefix.map(a=>{const id=rustAction(s,a);s=s.next(a);return id;});}
function actionBindings(s){return s.getLegalActions().map(a=>({action:a,label_index:actionToIndex(a,9),rust_id:rustAction(s,a),canonical_NN_index:BrowserNumeric.canonical(actionToIndex(a,9),s.isPlayer1Turn()),side:s.getCurrentPlayer(),from:s.isPlayer1Turn()?s.player1pos:s.player2pos,to:s.isPlayer1Turn()?s.next(a).player1pos:s.next(a).player2pos}));}
