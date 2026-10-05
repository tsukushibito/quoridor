'use strict';

// Current configurable entry. The old generate.cjs/runner.py are frozen recipes.
const fs = require('fs');
const path = require('path');
const { performance } = require('perf_hooks');
const { validateConfig, checkStart } = require('./config.cjs');
const { Pipe } = require('../ai-sigma-common/process/json-line.cjs');
const { WorkerClient, procIdentity } = require('../ai-sigma-common/process/worker-client.cjs');
const { OwnedTree } = require('../ai-sigma-common/process/owned-tree.cjs');
const { RunControl } = require('../ai-sigma-common/process/run-control.cjs');
const { Broker } = require('../ai-sigma-common/generation/batch-broker.cjs');
const { checkUsage, readUsage } = require('../ai-sigma-common/process/gpu-guard.cjs');

function allocated(root) {
  let bytes = 0;
  const seen = new Set();
  const stack = [root];
  while (stack.length) {
    for (const entry of fs.readdirSync(stack.pop(), { withFileTypes: true })) {
      const file = path.join(entry.parentPath ?? entry.path, entry.name);
      if (entry.isDirectory()) stack.push(file);
      else if (entry.isFile()) {
        const stat = fs.statSync(file);
        const inode = stat.dev + ':' + stat.ino;
        if (!seen.has(inode)) bytes += stat.blocks * 512;
        seen.add(inode);
      }
    }
  }
  return bytes;
}

async function sha256File(file) {
  const hash = require('crypto').createHash('sha256');
  for await (const buffer of fs.createReadStream(file)) hash.update(buffer);
  return hash.digest('hex');
}

async function generate(rawConfig) {
  const config = validateConfig(rawConfig);
  checkStart(config);
  const affinity = fs
    .readFileSync('/proc/self/status', 'utf8')
    .split('\n')
    .find((line) => line.startsWith('Cpus_allowed_list:'))
    ?.split(':')[1]
    .trim();
  if (affinity !== String(config.resources.management_cpu)) throw Error('MANAGEMENT_CPU_AFFINITY');
  if (fs.existsSync(config.job_out)) throw Error('ATTEMPT_ALREADY_EXISTS');
  const specs = JSON.parse(fs.readFileSync(config.openings_path, 'utf8')).games;
  if (!Array.isArray(specs)) throw Error('OPENINGS_SCHEMA');
  const byId = new Map(specs.map((spec) => [spec.game_id, spec]));
  if (byId.size !== specs.length) throw Error('OPENINGS_DUPLICATE_GAME');
  for (const worker of config.workers) {
    if (worker.game_ids.some((id) => !byId.has(id))) throw Error('GAME_ASSIGNMENT_UNKNOWN');
  }
  const modelSHA = await sha256File(config.runtime.model);
  if (modelSHA !== config.teacher.modelSHA256) throw Error('MODEL_SHA_CHANGED');
  // New output only; no original scientific data, model or prior attempt is overwritten.
  fs.mkdirSync(config.job_out, { recursive: true });
  const save = (name, value) =>
    fs.writeFileSync(path.join(config.job_out, name), JSON.stringify(value, null, 2) + '\n');
  const started = performance.now();
  const deadline = Math.min(
    Date.now() + config.job_seconds * 1000,
    Date.parse(config.science_deadline),
  );
  const cleanupStart = deadline - config.cleanup_seconds * 1000;
  const tree = new OwnedTree();
  const workers = [];
  const closed = [];
  const results = [];
  let primary = null;
  let aborted = false;
  let broker;
  let provider;
  let providerStop;
  let providerSeq = 0;
  const providerCost = { batches: 0, server_before_JSON_ms: 0, stages: {} };
  const hardStopTimer = setTimeout(
    () => {
      aborted = true;
      tree.signal('SIGKILL');
    },
    Math.max(1, deadline - Date.now()),
  );

  function abort(reason) {
    if (aborted) return;
    aborted = true;
    save('abort.json', { reason, UTC: new Date().toISOString() });
    broker?.stop();
    for (const worker of workers) worker.client.abort();
  }

  const control = new RunControl({
    wrapper: config.beads_wrapper,
    goalIssue: config.goal_issue,
    issue: config.issue,
    owner: config.owner,
    deadline: cleanupStart,
    pausePath: path.join(config.job_out, 'PAUSE'),
    onFailure: (error) => abort(error.message),
  });
  let gpuRead = null;
  async function checkGPU() {
    const rows = await readUsage(config.resources.gpu_id);
    checkUsage(
      rows,
      new Set(tree.sample().map((row) => row.pid)),
      config.resources.gpu_vram_guard_bytes,
    );
  }
  const timer = setInterval(() => {
    try {
      control.check();
      const rss = tree.sample().reduce((sum, row) => sum + row.rss, process.memoryUsage().rss);
      if (rss >= config.resources.ram_guard_bytes) throw Error('RAM_GUARD');
      if (allocated(config.job_out) >= config.resources.output_cap_bytes) throw Error('OUTPUT_CAP');
      if (config.mode === 'GPU' && !gpuRead) {
        gpuRead = checkGPU()
          .catch((error) => abort(error.message))
          .finally(() => {
            gpuRead = null;
          });
      }
    } catch (error) {
      abort(error.message);
    }
  }, 100);

  function onMessage(message, client) {
    const send = (reply) => {
      if (client.child.connected) client.send(reply);
    };
    if (message.kind === 'infer') {
      if (aborted || !broker)
        send({ kind: 'reply', request_id: message.identity.request_id, error: 'CONTROL_ABORT' });
      else
        broker.infer(message.identity, message.features_bits648).then(
          (data) => send({ kind: 'reply', request_id: message.identity.request_id, data }),
          (error) => {
            send({ kind: 'reply', request_id: message.identity.request_id, error: error.message });
            abort(error.message);
          },
        );
      return true;
    }
    if (message.kind === 'cancel') {
      broker?.cancel(message.worker, message.game, message.generation, message.run);
      return true;
    }
    if (message.kind === 'wait_game') {
      void (
        broker?.quiescentGame(message.worker, message.game, message.run) ?? Promise.resolve()
      ).then(() => send({ kind: 'drained', id: message.id }));
      return true;
    }
    if (message.kind === 'fault') {
      abort(message.error);
      return true;
    }
    return false;
  }

  try {
    await control.start();
    save('run-config.json', config);
    save(
      'registered-games.json',
      config.workers.flatMap((worker) => worker.game_ids.map((id) => byId.get(id))),
    );
    if (config.mode === 'GPU') {
      await checkGPU();
      provider = new Pipe(config.provider.command, config.provider.args, {
        timeoutMs: config.provider.timeoutMs,
      });
      tree.add(procIdentity(provider.child.pid));
      const info = await provider.ask({ op: 'info', request_id: 'init' });
      if (!info.ok || info.request_id !== 'init') throw Error('PROVIDER_INIT');
      save('provider-init.json', info.result);
      broker = new Broker(async (items) => {
        const requestId = 'batch.' + ++providerSeq;
        const response = await provider.ask({
          op: 'infer_batch',
          request_id: requestId,
          backend: 'cuda',
          items,
        });
        if (!response.ok || response.request_id !== requestId) throw Error('PROVIDER_ID');
        providerCost.batches++;
        providerCost.server_before_JSON_ms += response.result.batchcost?.server_before_JSON_ms ?? 0;
        for (const [key, value] of Object.entries(response.result.batchcost?.stages ?? {})) {
          providerCost.stages[key] = (providerCost.stages[key] ?? 0) + value;
        }
        return response.result.items;
      }, config.broker);
    }
    for (const worker of config.workers) {
      const client = new WorkerClient({
        script: path.join(__dirname, 'worker.cjs'),
        cpu: worker.cpu,
        output: path.join(config.job_out, worker.worker_id),
        timeoutMs: Math.max(1, cleanupStart - Date.now()),
        onMessage,
      });
      tree.add(client.identity);
      workers.push({ ...worker, client });
    }
    await Promise.all(
      workers.map((worker) =>
        worker.client.ask('init', {
          mode: config.mode,
          run: config.run_id,
          datasetMode: config.dataset_mode ?? config.mode,
          worker_id: worker.worker_id,
          runtime: config.runtime,
          teacher: config.teacher,
          active_per_worker: config.active_per_worker,
          broker: config.broker,
        }),
      ),
    );
    control.check();
    if (aborted) throw Error('ABORT_BEFORE_GAMES');
    await Promise.all(
      workers.map(async (worker) => {
        const result = await worker.client.ask('games', {
          games: worker.game_ids.map((id) => byId.get(id)),
          active: config.active_per_worker,
        });
        results.push({ worker_id: worker.worker_id, ...result });
      }),
    );
    control.check();
  } catch (error) {
    primary = { error: error.stack };
    abort(error.message);
  } finally {
    clearInterval(timer);
    await control.stop();
    if (gpuRead) await gpuRead;
    // The stop of this driver never asserts that unknown or other owners' jobs stopped.
    for (const worker of workers) {
      worker.client.abort();
      try {
        const data = await worker.client.ask(
          'close',
          {},
          { timeoutMs: Math.max(1, deadline - Date.now()) },
        );
        closed.push({ worker_id: worker.worker_id, ...data, exit: await worker.client.exit });
      } catch (error) {
        closed.push({ worker_id: worker.worker_id, error: error.stack });
        tree.signal('SIGTERM');
        await worker.client.recover(Math.max(1, deadline - Date.now()));
      }
    }
    if (broker) {
      broker.stop();
      await broker.quiescent();
      save('broker.json', {
        stats: broker.stats,
        providerCost,
        zero: broker.zero(),
        fault: broker.fault,
      });
    }
    if (provider) {
      try {
        const response = await provider.ask({ op: 'stop', request_id: 'stop' });
        providerStop = response.result;
      } catch (error) {
        providerStop = { error: error.stack };
      }
      providerStop = { ...providerStop, exit: await provider.close() };
    }
  }
  const remaining = tree.sample();
  clearTimeout(hardStopTimer);
  const receipt = {
    issue: config.issue,
    run_id: config.run_id,
    mode: config.mode,
    results,
    closed,
    primary,
    aborted,
    providerStop,
    elapsed_ms: performance.now() - started,
    control_receipts: control.receipts,
    owned: [...tree.owned.values()],
    remaining,
    NN: closed.reduce((sum, worker) => sum + (worker.usedNN ?? 0), 0),
    startup_NN: closed.reduce((sum, worker) => sum + (worker.startup_NN ?? 0), 0),
  };
  save('result.json', receipt);
  if (primary || aborted || remaining.length) throw Error('GENERATION_INCOMPLETE');
  return receipt;
}

if (require.main === module) {
  const config = validateConfig(JSON.parse(fs.readFileSync(process.argv[2], 'utf8')));
  generate(config).catch((error) => {
    console.error(error.stack);
    process.exitCode = 1;
  });
}

module.exports = { generate, allocated };
