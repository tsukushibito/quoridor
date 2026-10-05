'use strict';
const fs = require('node:fs');
const assert = require('node:assert/strict');
const path = require('node:path');
const { q, n, now } = require('../search.cjs');
const { Worker } = require('./protocol.cjs');
const { validateConfig, validatePlan, checkStart, readJSON } = require('./config.cjs');
const { RunControl } = require('../../ai-sigma-common/process/run-control.cjs');
const { OwnedTree } = require('../../ai-sigma-common/process/owned-tree.cjs');

// An exclusive directory owns all new output. Existing evidence is never truncated.
class Records {
  constructor(c) {
    this.c = c;
    this.sizes = {};
    this.fds = {};
    const parent = fs.realpathSync(path.dirname(c.output_root));
    assert.equal(
      path.join(parent, path.basename(c.output_root)),
      path.resolve(c.output_root),
      'OUTPUT_SYMLINK_PARENT',
    );
    fs.mkdirSync(c.output_root); // EEXIST is a refusal, including symlinks.
    try {
      for (const key of ['hands', 'counter_file', 'output']) {
        this.fds[key] = fs.openSync(c[key], 'wx');
        this.sizes[key] = 0;
      }
    } catch (error) {
      this.close();
      throw error;
    }
  }
  write(key, value, append = false) {
    const bytes = Buffer.from(JSON.stringify(value) + '\n');
    if (key !== 'hands' && bytes.length > this.c.resources.max_snapshot_bytes)
      throw Error('SNAPSHOT_CAP');
    const size = append ? this.sizes[key] + bytes.length : bytes.length;
    const allocated = Object.entries(this.sizes).reduce(
      (sum, [name, n]) => sum + Math.ceil((name === key ? size : n) / 4096) * 4096,
      4096,
    );
    // Reserved snapshot replacement + terminal fault recording are charged before writes.
    if (
      allocated + 2 * this.c.resources.max_snapshot_bytes + 12288 >
      this.c.resources.output_cap_bytes
    )
      throw Error('OUTPUT_CAP');
    if (!append) fs.ftruncateSync(this.fds[key], 0);
    fs.writeSync(this.fds[key], bytes, 0, bytes.length, append ? this.sizes[key] : 0);
    this.sizes[key] = size;
  }
  close() {
    for (const fd of Object.values(this.fds)) fs.closeSync(fd);
    this.fds = {};
  }
}
async function run(raw, dependencies = {}) {
  const c = validateConfig(raw);
  checkStart(c);
  const { ledger, openings } = validatePlan(readJSON(c.openings), c);
  const records = new Records(c),
    begin = now(),
    deadline = Date.parse(c.end_utc) - c.cleanup_ms;
  let worker = null,
    control = null,
    timer = null,
    failure = null,
    cleanup = null,
    ready = null,
    NN = 0,
    generation = 0,
    hands = 0;
  const owned = new OwnedTree();
  const fail = (error) => {
    failure ??= error;
    if (worker)
      void worker.close().catch((e) => {
        failure ??= e;
      });
  };
  const signal = () => fail(Error('SIGNAL_STOP'));
  const check = () => {
    if (failure) throw failure;
    control.check();
    const rows = owned.sample();
    const selfRSS = process.memoryUsage().rss;
    if (rows.reduce((total, row) => total + row.rss, selfRSS) > c.resources.ram_guard_bytes)
      throw Error('RAM_GUARD');
  };
  const counter = () => records.write('counter_file', { all_samples: NN, hands });
  process.on('SIGTERM', signal);
  process.on('SIGINT', signal);
  try {
    control = dependencies.makeControl
      ? dependencies.makeControl(c, deadline, fail)
      : new RunControl({
          wrapper: c.beads_wrapper,
          goalIssue: c.goal_issue,
          issue: c.issue,
          owner: c.owner,
          deadline,
          pausePath: c.pause_path,
          onFailure: fail,
        });
    await control.start();
    check();
    counter();
    const Factory = dependencies.Worker ?? Worker;
    worker = new Factory(c.weight_manifest, path.join(__dirname, 'worker.cjs'), [], {
      ...c.transport,
      affinity: c.resources.affinity,
    });
    if (worker.p?.pid) {
      const stat = fs
        .readFileSync(`/proc/${worker.p.pid}/stat`, 'utf8')
        .split(')')
        .at(-1)
        .trim()
        .split(/\s+/);
      owned.add({ pid: worker.p.pid, starttick: stat[19], boot: owned.boot });
    }
    timer = setInterval(() => {
      try {
        check();
      } catch (error) {
        fail(error);
      }
    }, 100);
    const init = await worker.take(c.init_timeout_ms);
    assert.equal(init.type, 'READY', 'INIT_NOT_READY');
    ready = now();
    for (const slot of ledger) {
      check();
      const opening = openings.get(slot.opening);
      let prefix = structuredClone(opening.prefix),
        state = q.r.fromPrefix(prefix);
      slot.status = 'STARTED';
      slot.startUTC = new Date().toISOString();
      slot.hands = 0;
      while (true) {
        check();
        const terminal = q.r.terminalResult(state);
        if (terminal) {
          slot.status = 'TERMINAL';
          slot.winner = terminal.winner;
          slot.result_NNUE =
            terminal.winner === 0 ? 'D' : terminal.winner === slot.NNUE_side ? 'W' : 'L';
          break;
        }
        if (NN >= c.NNcap) throw Error('GLOBAL_NN_CAP');
        if (Date.now() + c.budget_ms + c.transport.stopTimeoutMs >= deadline)
          throw Error('PROCESSING_DEADLINE');
        const inputReady = now(),
          legal = state.getLegalActions(),
          engine = state.getCurrentPlayer() === slot.NNUE_side ? 'NNUE' : 'distance';
        const id = `${c.run}:${slot.slot}:${++generation}`;
        const request = {
          distance_mode: slot.distance_mode,
          leaf_package: true,
          kind: 'SEARCH',
          id,
          generation,
          engine,
          prefix,
          key: state._positionKey(),
          history: n.history(state),
          node_cap: c.node_cap,
          maxdepth: c.max_depth,
          ordering: c.ordering,
          NNcap: c.NNcap,
        };
        let selected = null;
        const clock = await worker.request(
          request,
          c.budget_ms,
          (x) => {
            const r = x.search,
              action = legal.find((a) => q.r.rustAction(state, a) === r.Action);
            const valid =
              x.distance_mode === slot.distance_mode &&
              r.distance_mode === slot.distance_mode &&
              x.leaf_package === true &&
              r.leaf_package === true &&
              r.status === 'COMPLETED_ACTION' &&
              Number.isInteger(r.completed_depth) &&
              r.completed_depth >= 1 &&
              Number.isFinite(r.value) &&
              r.last_completed_only === true &&
              !!action &&
              r.parent_copy_key_history_restored === true;
            selected = valid ? action : null;
            return {
              valid,
              completed_depth: r.completed_depth ?? null,
              legal: !!action,
              value_finite: Number.isFinite(r.value),
            };
          },
          inputReady,
          c.margin_ms,
        );
        if (clock.response) {
          assert(Number.isSafeInteger(clock.response.allNN), 'NN_COUNTER_REQUIRED');
          assert(clock.response.allNN >= NN && clock.response.allNN <= c.NNcap, 'NN_COUNTER');
          NN = clock.response.allNN;
        }
        hands++;
        slot.hands++;
        counter();
        records.write(
          'hands',
          {
            slot: slot.slot,
            distance_mode: slot.distance_mode,
            before_prefix: prefix,
            before_key: state._positionKey(),
            before_history: n.history(state),
            ply: state.depth,
            side: state.getCurrentPlayer(),
            engine,
            generation,
            id,
            clock,
          },
          true,
        );
        check();
        if (clock.status !== 'RECEIVED' || !clock.response?.validation?.valid) {
          slot.status = 'UNKNOWN';
          slot.fault = {
            type:
              clock.status === 'RECEIVED'
                ? (clock.response?.search?.status ?? 'INVALID_COMPLETED_ACTION')
                : clock.status,
            category: 'CLOCK_OR_ENGINE_UNKNOWN',
            cause_side: engine,
          };
          slot.stop = await worker.stop(`${id}:stop`);
          break;
        }
        assert(selected);
        prefix.push(structuredClone(selected));
        state = state.next(selected);
      }
      slot.final_ply = state.depth;
      slot.prefix = prefix;
      slot.endUTC = new Date().toISOString();
      records.write('output', { run: c.run, samples: NN, ledger, partial: true });
      if (slot.status === 'UNKNOWN' && (worker.exit || slot.stop?.status !== 'STOP_ACK'))
        throw Error('SHARED_HARNESS_STOPPED');
    }
  } catch (error) {
    failure ??= error;
  } finally {
    clearInterval(timer);
    process.off('SIGTERM', signal);
    process.off('SIGINT', signal);
    if (control) {
      try {
        await control.stop();
      } catch (error) {
        failure ??= error;
      }
    }
    if (worker) {
      try {
        cleanup = await worker.close();
        if (!cleanup.waited) failure ??= Error('CHILD_COLLECTION_UNKNOWN');
      } catch (error) {
        failure ??= error;
      }
    }
    // Any explicitly tracked descendants are collected too, even after reparenting.
    if (owned.sample().length) {
      owned.signal('SIGTERM');
      await new Promise((r) => setTimeout(r, Math.min(100, c.transport.closeGraceMs)));
      if (owned.sample().length) owned.signal('SIGKILL');
      await new Promise((r) => setTimeout(r, Math.min(100, c.transport.killGraceMs)));
      if (owned.sample().length) failure ??= Error('OWNED_COLLECTION_UNKNOWN');
    }
  }
  for (const slot of ledger)
    if (!['TERMINAL', 'UNKNOWN'].includes(slot.status)) {
      slot.status = 'NOT_COMPLETED';
      slot.reason = failure?.message ?? 'NOT_ATTEMPTED';
    }
  const result = {
    task: c.issue,
    schema: c.schema,
    run: c.run,
    UTC: new Date().toISOString(),
    samples: NN,
    planned_all_slots: c.slots.length,
    attempted_slots: ledger.filter((s) => s.startUTC).map((s) => s.slot),
    ledger,
    init_to_ready_ms: ready === null ? null : ready - begin,
    wholewall_ms: now() - begin,
    cleanup,
    control_receipts: control?.receipts ?? [],
    failure: failure?.message ?? null,
    clock_valid: !failure && ledger.every((s) => s.status === 'TERMINAL'),
    WDL: ledger.reduce(
      (a, s) => {
        if (s.result_NNUE) a[s.result_NNUE]++;
        else a.unknown++;
        return a;
      },
      { W: 0, D: 0, L: 0, unknown: 0 },
    ),
    strength_claim: false,
    formalNI: false,
    model_training: 0,
    GPU: 0,
  };
  try {
    counter();
    records.write('output', result);
  } finally {
    records.close();
  }
  return result;
}
if (require.main === module)
  run(readJSON(process.argv[2], 65536))
    .then((result) => {
      console.log(
        JSON.stringify({
          run: result.run,
          WDL: result.WDL,
          cleanup: result.cleanup,
          failure: result.failure,
        }),
      );
      if (result.failure) process.exitCode = 1;
    })
    .catch((error) => {
      console.error(error);
      process.exitCode = 1;
    });
module.exports = { run, Records };
