function sameAction(a,b){return a?.type===b?.type&&(a.type==='pawn'?a.direction[0]===b.direction[0]&&a.direction[1]===b.direction[1]:a.orientation===b.orientation&&a.x===b.x&&a.y===b.y);}
function fromPrefix(prefix){let s=new State({boardsize:9,walls_p1:10,walls_p2:10,walls_initial:10});for(const a of prefix){if(terminalResult(s)||!s.getLegalActions().some(x=>sameAction(x,a)))throw Error('invalid-prefix');s=s.next(a);}return s;}
function requestState(d){if(d.fixture)return referenceState(d.fixture);if(Array.isArray(d.legal_prefix))return fromPrefix(d.legal_prefix);throw Error('prefix_required');}
function referenceState(f) {
 let s=new State({boardsize:9,walls_p1:10,walls_p2:10,walls_initial:10});
 if(f.classification==='legal-replay') {
  for(const a of f.legal_prefix){if(s.isFinished()||!s.getLegalActions().some(x=>sameAction(x,a)))throw Error('invalid-prefix '+f.id);s=s.next(a);}
 } else {
  const b=f.board;s=new State({boardsize:9,depth:b.total_ply,player1pos:b.pawns[0],player2pos:b.pawns[1],hwalls:new Uint8Array(b.h_segments),vwalls:new Uint8Array(b.v_segments),walls_p1:b.walls_remaining[0],walls_p2:b.walls_remaining[1],walls_initial:10,hwall_anchors:new Set(b.h_anchors),vwall_anchors:new Set(b.v_anchors),position_history:new Map(f.history_counts)});
 }
 const h=Array.from(s.position_history).sort((a,b)=>a[0].localeCompare(b[0]));
 if(s._positionKey()!==f.history_count_key||s.depth!==f.board.total_ply||JSON.stringify(h)!==JSON.stringify([...f.history_counts].sort((a,b)=>a[0].localeCompare(b[0]))))throw Error('context mismatch '+f.id);
 const v=Array.from(s.toNNInput());if(v.some((x,i)=>x!==f.raw_features_float32[i]))throw Error('feature mismatch '+f.id);
 const legal=s.getLegalActions().map(a=>actionToIndex(a,9));if(JSON.stringify(legal)!==JSON.stringify(f.legal_actions.map(a=>a.sigma136)))throw Error('legal/order mismatch '+f.id);
 return s;
}
function terminalResult(s){const w=s.winner();if(w)return {winner:w,value:w===s.getCurrentPlayer()?1:-1};if(s.depth>=200||s.getLegalActions().length===0)return {winner:0,value:0};return null;}
function rustAction(s,a){if(a.type==='wall')return (a.orientation==='h'?81:145)+a.y*8+a.x;let n=s.next(a),p=s.isPlayer1Turn()?n.player1pos:n.player2pos;return p[1]*9+p[0];}
