// Root-only changed-pattern qualification. Requires real same-source native/Wasm
// and the prepared Python interpreter; no silently skipped parity leg.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { initSync, PatternModel, search_json } from '../wasm/othello.js';

initSync({ module: readFileSync(new URL('../wasm/othello_bg.wasm', import.meta.url)) });
const repository = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..');
const swap = (code) => {
  let result = 0;
  for (let j = 0; j < 6; j++) {
    const digit = code % 3;
    result += (digit ? 3 - digit : 0) * 3 ** j;
    code = Math.floor(code / 3);
  }
  return result;
};

function fixtureModel() {
  return {
    version: 1,
    shapes: [
      [0, 1, 2, 8, 9, 10],
      [1, 2, 3, 4, 5, 6],
    ],
    cellOrder: 'shape-list-lsb-ternary',
    encoding: 'empty0-stm1-opponent2',
    transforms: 'mirror-then-clockwise-rotations-0-1-2-3',
    phase: 'min(3,clamp(occupied-4,0,60)//15)',
    score: 'stm-centidiscs',
    quantization: { scale: 1, rounding: 'nearest-ties-even', minimum: -32767, maximum: 32767 },
    weights: Array.from({ length: 4 }, (_, phase) =>
      Array.from({ length: 2 }, (_, shape) =>
        Array.from({ length: 729 }, (_, code) => {
          const other = swap(code);
          const weight = ((Math.min(code, other) % 23) - 11) * (phase + 1) * (shape + 1);
          return code === other ? 0 : code < other ? weight : -weight;
        }),
      ),
    ),
  };
}

function positions() {
  const board = Array(64).fill(0);
  for (const i of [0, 1, 2, 8, 10, 18, 31, 37]) board[i] = 1;
  for (const i of [3, 9, 27, 36]) board[i] = 2;
  const forced = Array(64).fill(0);
  forced[0] = 1;
  forced[1] = 2;
  return [
    { version: 1, board, toMove: 1 },
    { version: 1, board, toMove: 2 },
    { version: 1, board: forced, toMove: 2 },
    { version: 1, board: [1, ...Array(63).fill(0)], toMove: 1 },
  ];
}

test('pattern objects reject invalid models and do not mutate baseline search selection', () => {
  const input = fixtureModel();
  const first = new PatternModel(JSON.stringify(input));
  const second = new PatternModel(
    JSON.stringify({
      ...input,
      weights: Array.from({ length: 4 }, () => Array.from({ length: 2 }, () => Array(729).fill(0))),
    }),
  );
  const state = JSON.stringify(positions()[0]);
  const options = '{"timeMs":0,"ttMiB":0}';
  try {
    const before = JSON.parse(search_json(state, options));
    assert.equal(JSON.parse(second.evaluate_json(state)).score, 0);
    const a = JSON.parse(first.evaluate_json(state));
    assert.equal(a.score, -JSON.parse(first.evaluate_json(JSON.stringify(positions()[1]))).score);
    assert.equal(JSON.parse(search_json(state, options)).score, before.score);
    assert.equal(JSON.parse(first.search_json(state, options)).score, a.score);
    assert.throws(() => new PatternModel('{}'));
    const invalid = fixtureModel();
    invalid.weights[0][0][0] = 1;
    assert.throws(() => new PatternModel(JSON.stringify(invalid)));
  } finally {
    first.free();
    second.free();
  }
});

test('pattern raw scores and search match Python/native/Wasm with exact mode independent', () => {
  assert.ok(process.env.OTHELLO_NATIVE_ENGINE, 'OTHELLO_NATIVE_ENGINE required');
  assert.ok(process.env.OTHELLO_PATTERN_PYTHON, 'OTHELLO_PATTERN_PYTHON required');
  const supplied = process.env.OTHELLO_PATTERN_WEIGHTS;
  const input = supplied ? readFileSync(supplied, 'utf8') : JSON.stringify(fixtureModel());
  const temporary = mkdtempSync(join(tmpdir(), 'othello-pattern-parity-'));
  const path = join(temporary, 'pattern-fixture.json');
  const hash = createHash('sha256').update(input).digest('hex');
  let model;
  const states = positions();
  const options = { timeMs: 1000, ttMiB: 0, maxDepth: 2, exactEmpties: 64 };
  // Early artificial positions have many empties; disable exact on the first2.
  const requests = states.flatMap((state, index) => [
    { op: 'evaluate', state },
    { op: 'search', state, ...options, exactEmpties: index < 2 ? 0 : 64 },
  ]);
  try {
    writeFileSync(path, input);
    model = new PatternModel(input);
    const native = spawnSync(
      process.env.OTHELLO_NATIVE_ENGINE,
      ['--pattern', path, '--model-id', `sha256:${hash}`],
      {
        input: requests.map(JSON.stringify).join('\n') + '\n',
        encoding: 'utf8',
        timeout: 10000,
        maxBuffer: 1024 * 1024,
      },
    );
    assert.ifError(native.error);
    assert.equal(native.status, 0, native.stderr);
    const responses = native.stdout.trim().split('\n').map(JSON.parse);
    assert.equal(responses.length, requests.length);
    const python = spawnSync(
      process.env.OTHELLO_PATTERN_PYTHON,
      ['-B', '-m', 'othello_training.parity', '--model', path],
      {
        input: states.map(JSON.stringify).join('\n') + '\n',
        encoding: 'utf8',
        timeout: 10000,
        maxBuffer: 1024 * 1024,
        env: { ...process.env, PYTHONPATH: join(repository, 'games/othello/python') },
      },
    );
    assert.ifError(python.error);
    assert.equal(python.status, 0, python.stderr);
    const expected = python.stdout.trim().split('\n').map(JSON.parse);
    for (const [index, state] of states.entries()) {
      const evaluated = JSON.parse(model.evaluate_json(JSON.stringify(state)));
      assert.deepEqual(evaluated, expected[index]);
      assert.equal(responses[index * 2].ok, true);
      for (const key of ['score', 'scoreKind', 'proven'])
        assert.equal(responses[index * 2][key], evaluated[key]);
      const result = JSON.parse(
        model.search_json(
          JSON.stringify(state),
          JSON.stringify({ ...options, exactEmpties: index < 2 ? 0 : 64 }),
        ),
      );
      const actual = responses[index * 2 + 1];
      assert.equal(actual.ok, true);
      assert.equal(actual.evaluation.modelId, `sha256:${hash}`);
      assert.equal(actual.evaluation.modelBytes, Buffer.byteLength(input));
      for (const key of [
        'move',
        'score',
        'scoreKind',
        'completedDepth',
        'nodes',
        'timedOut',
        'cancelled',
        'proven',
      ])
        assert.equal(actual[key], result[key], `case${index} ${key}`);
      if (index >= 2) {
        const baseline = JSON.parse(search_json(JSON.stringify(state), JSON.stringify(options)));
        assert.equal(result.score, baseline.score);
        assert.equal(result.proven, true);
        assert.equal(result.scoreKind, 'discDifference');
      }
    }
  } finally {
    model?.free();
    rmSync(temporary, { recursive: true, force: true });
  }
});
