"use strict";
// Read-only adapter from existing native teacher files. Does not change old runs/splits.
const fs = require("fs"), path = require("path"), zlib = require("zlib"), crypto = require("crypto"), assert = require("assert");
const {r, input} = require("../ai-sigma-nnue-qf1-prototype/qf1.cjs");
const args = process.argv.slice(2);
const output = args.shift();
if (!output || !args.length) throw new Error("usage: node export_qf1.cjs OUTPUT.jsonl.gz DATASET_DIR [DATASET_DIR...]");
if (fs.existsSync(output) || fs.existsSync(output + ".manifest.json")) throw new Error("output exists; use a new export path");
const samples = [], sources = [];
for (const dir of args) {
  if (path.basename(dir).includes("173-native-ni-arena")) throw new Error("formal 173 holdout must not be exported for training");
  const openingFile = path.join(dir, "openings.json"), rowFile = path.join(dir, "teacher-rows.jsonl.gz");
  const openingBytes = fs.readFileSync(openingFile), rowBytes = fs.readFileSync(rowFile);
  const games = JSON.parse(openingBytes).games;
  const states = new Map(games.filter(g => g.generated).map(g => [g.game_id, r.fromPrefix(g.opening.legal_prefix)]));
  for (const line of zlib.gunzipSync(rowBytes).toString().trim().split("\n")) {
    const row = JSON.parse(line), state = states.get(row.game_id);
    assert(state, "missing game opening");
    assert.equal(state._positionKey(), row.state_key);
    assert.equal(state.depth, row.ply);
    assert.equal(state.getCurrentPlayer(), row.side);
    const canonical = counts => counts.slice().sort((a,b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0);
    // Reference arrays belong to a VM realm; compare canonical content, not prototypes.
    assert.equal(JSON.stringify(canonical([...state.position_history])), JSON.stringify(canonical(row.history_counts)));
    const f = state.toNNInput();
    assert.deepStrictEqual(Array.from(new Uint32Array(f.buffer, f.byteOffset, f.length)), row.features648_bits);
    assert.equal(row.rootmean_view, "root side-to-move");
    const q = input(state);
    const historyKey = crypto.createHash("sha256").update(JSON.stringify([row.state_key, canonical(row.history_counts)])).digest("hex");
    samples.push({id: row.row_id, group: row.family || row.lineage, split: row.split, cohort: path.basename(dir), state_key: row.state_key, history_key: historyKey, side: row.side, ids: q.ids, distance: q.distance, rootmean: row.rootmean, z: row.value_eligible ? row.z_stm : null});
    const action = state.getLegalActions().find(a => JSON.stringify(a) === JSON.stringify(row.action));
    assert(action, "saved action illegal");
    assert.equal(r.rustAction(state, action), row.action209);
    states.set(row.game_id, state.next(action));
  }
  sources.push({directory: path.resolve(dir), openings_sha256: crypto.createHash("sha256").update(openingBytes).digest("hex"), rows_sha256: crypto.createHash("sha256").update(rowBytes).digest("hex")});
}
fs.mkdirSync(path.dirname(output), {recursive: true});
fs.writeFileSync(output, zlib.gzipSync(samples.map(x => JSON.stringify(x)).join("\n") + "\n"));
fs.writeFileSync(output + ".manifest.json", JSON.stringify({feature_version: "QF1", sources, rows: samples.length, source_split_preserved: true, sha256: crypto.createHash("sha256").update(fs.readFileSync(output)).digest("hex")}, null, 2) + "\n");
console.log(JSON.stringify({rows: samples.length, output}));
