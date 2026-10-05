'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto');
const {r}=require('../ai-sigma-native-baseline/reference.cjs').createReference();
const D=path.resolve(__dirname,'../../research-data/ai-sigma/frame14-distance-test'),manifest=JSON.parse(fs.readFileSync(D+'/openings.json'));
assert.equal(manifest.games.length,24);assert.equal(new Set(manifest.games.map(g=>g.family)).size,24);
const lengths={};
for(const g of manifest.games){assert.equal(g.split,'test');assert(g.generated);const s=r.fromPrefix(g.opening.legal_prefix);assert(!r.terminalResult(s));assert.equal(s.depth,g.target_ply);assert.equal(s._positionKey(),g.opening.key);assert.equal(s.getCurrentPlayer(),g.opening.side);assert.equal(JSON.stringify(r.portState(s)),JSON.stringify(g.opening.root_state));assert.equal(g.opening.root_state.features_bits.length,648);lengths[g.target_ply]=(lengths[g.target_ply]??0)+1;}
for(const p of [8,12,16,20,24,28])assert.equal(lengths[p],4);
const previous=['frame14-teachers','frame14-l2-test'].flatMap(n=>JSON.parse(fs.readFileSync(path.resolve(D,'../'+n+'/openings.json'))).games);
assert(!manifest.games.some(g=>previous.some(p=>p.family===g.family||p.sampling_seed===g.sampling_seed)));
const out={issue:'quoridor-4lc.201',UTC:new Date().toISOString(),planned:24,alllegal_nonterminal:true,original_root_port_features648_order_history_exact:true,lengths,oldfamily_actionseed_shared:0,NN:0,GPU:0,oldtestlabels_read:false,openingSHA:crypto.createHash('sha256').update(fs.readFileSync(D+'/openings.json')).digest('hex')};fs.writeFileSync(D+'/opening-audit.json',JSON.stringify(out,null,2)+'\n');console.log(JSON.stringify(out));
