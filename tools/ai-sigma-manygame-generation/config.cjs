'use strict';

const path = require('path');

function requireString(value, name) {
  if (typeof value !== 'string' || !value || value.length > 1024) throw Error('CONFIG_' + name);
  return value;
}

function positiveInteger(value, name, maximum = Number.MAX_SAFE_INTEGER) {
  if (!Number.isSafeInteger(value) || value < 1 || value > maximum) throw Error('CONFIG_' + name);
  return value;
}

function absolutePath(value, name) {
  requireString(value, name);
  if (!path.isAbsolute(value)) throw Error('CONFIG_' + name + '_ABSOLUTE_PATH');
  return value;
}

function timestamp(value, name) {
  requireString(value, name);
  const time = Date.parse(value);
  if (!Number.isFinite(time)) throw Error('CONFIG_' + name);
  return time;
}

function validateWorkerSettings(settings, mode) {
  if (!['CPUJS', 'RustCPU', 'GPU'].includes(mode)) throw Error('CONFIG_MODE');
  if (!settings || typeof settings !== 'object') throw Error('CONFIG_WORKER_SETTINGS');
  const { runtime, teacher } = settings;
  if (!runtime || !teacher) throw Error('CONFIG_RUNTIME_TEACHER_REQUIRED');
  absolutePath(runtime.python, 'PYTHON');
  absolutePath(runtime.model, 'MODEL');
  positiveInteger(runtime.pipeTimeoutMs, 'PIPE_TIMEOUT_MS');
  requireString(runtime.expectedORTVersion, 'ORT_VERSION');
  if (mode !== 'CPUJS') absolutePath(runtime.nativeBridge, 'NATIVE_BRIDGE');
  if (mode === 'RustCPU') absolutePath(runtime.ortScript, 'ORT_SCRIPT');
  if (!Number.isSafeInteger(teacher.K) || teacher.K < 2) throw Error('CONFIG_TEACHER_K');
  positiveInteger(teacher.sampleCap, 'SAMPLE_CAP');
  positiveInteger(teacher.maxNewPlies, 'NEW_PLY_CAP');
  if (!Number.isSafeInteger(teacher.temperaturePlies) || teacher.temperaturePlies < 0) {
    throw Error('CONFIG_TEMPERATURE_PLIES');
  }
  if (!/^[0-9a-f]{64}$/.test(teacher.modelSHA256)) throw Error('CONFIG_MODEL_SHA');
  requireString(teacher.providerLabel, 'PROVIDER_LABEL');
  requireString(teacher.searchLabel, 'SEARCH_LABEL');
  requireString(settings.run, 'RUN');
  return settings;
}

function validateConfig(raw) {
  if (!raw || typeof raw !== 'object') throw Error('CONFIG_OBJECT');
  const config = structuredClone(raw);
  if (!['CPUJS', 'RustCPU', 'GPU'].includes(config.mode)) throw Error('CONFIG_MODE');
  requireString(config.run_id, 'RUN_ID');
  requireString(config.issue, 'ISSUE');
  requireString(config.owner, 'OWNER');
  requireString(config.goal_issue, 'GOAL_ISSUE');
  absolutePath(config.openings_path, 'OPENINGS');
  absolutePath(config.job_out, 'JOB_OUT');
  absolutePath(config.beads_wrapper, 'BEADS_WRAPPER');
  const cutoff = timestamp(config.heavy_start_cutoff_utc, 'HEAVY_CUTOFF');
  const deadline = timestamp(config.science_deadline, 'SCIENCE_DEADLINE');
  const windowEnd = timestamp(config.window_end_utc, 'WINDOW_END');
  if (!(cutoff <= deadline && deadline <= windowEnd)) throw Error('CONFIG_DEADLINE_ORDER');
  positiveInteger(config.job_seconds, 'JOB_SECONDS');
  positiveInteger(config.cleanup_seconds, 'CLEANUP_SECONDS');
  if (config.cleanup_seconds >= config.job_seconds) throw Error('CONFIG_CLEANUP_BUDGET');
  positiveInteger(config.active_per_worker, 'ACTIVE_PER_WORKER');
  if (!Array.isArray(config.workers) || !config.workers.length) throw Error('CONFIG_WORKERS');
  const cpus = new Set();
  const workerIds = new Set();
  const gameIds = new Set();
  for (const worker of config.workers) {
    if (!Number.isSafeInteger(worker.cpu) || worker.cpu < 0 || cpus.has(worker.cpu)) {
      throw Error('CONFIG_CPU_ASSIGNMENT');
    }
    cpus.add(worker.cpu);
    requireString(worker.worker_id, 'WORKER_ID');
    if (workerIds.has(worker.worker_id)) throw Error('CONFIG_WORKER_ID_DUPLICATE');
    workerIds.add(worker.worker_id);
    if (!Array.isArray(worker.game_ids)) throw Error('CONFIG_GAME_IDS');
    for (const game of worker.game_ids) {
      requireString(game, 'GAME_ID');
      if (gameIds.has(game)) throw Error('CONFIG_GAME_ASSIGNMENT_DUPLICATE');
      gameIds.add(game);
    }
  }
  validateWorkerSettings({ ...config, run: config.run_id }, config.mode);
  if (!config.resources) throw Error('CONFIG_RESOURCES');
  positiveInteger(config.resources.ram_guard_bytes, 'RAM_GUARD');
  positiveInteger(config.resources.output_cap_bytes, 'OUTPUT_CAP');
  positiveInteger(config.resources.management_cpu_count, 'MANAGEMENT_CPU_COUNT');
  positiveInteger(config.resources.logical_cpu_limit, 'LOGICAL_CPU_LIMIT');
  if (config.resources.management_cpu_count !== 1) throw Error('CONFIG_MANAGEMENT_CPU_SINGLE');
  if (
    !Number.isSafeInteger(config.resources.management_cpu) ||
    config.resources.management_cpu < 0
  ) {
    throw Error('CONFIG_MANAGEMENT_CPU');
  }
  cpus.add(config.resources.management_cpu);
  if (cpus.size > config.resources.logical_cpu_limit) throw Error('CONFIG_CPU_BUDGET');
  if (!config.broker) throw Error('CONFIG_BROKER');
  positiveInteger(config.broker.maxBatch, 'BATCH_MAX');
  positiveInteger(config.broker.maxPendingGames, 'PENDING_MAX');
  positiveInteger(config.broker.replyCap, 'REPLY_CAP');
  if (
    !Number.isFinite(config.broker.flushMs) ||
    config.broker.flushMs < 0 ||
    config.broker.flushMs > 1 ||
    config.broker.maxPendingGames < config.broker.maxBatch
  )
    throw Error('CONFIG_BROKER');
  if (config.mode === 'GPU') {
    if (!config.provider) throw Error('CONFIG_PROVIDER');
    positiveInteger(config.resources.gpu_vram_guard_bytes, 'GPU_VRAM_GUARD');
    requireString(config.resources.gpu_id, 'GPU_ID');
    absolutePath(config.provider.command, 'PROVIDER_COMMAND');
    if (
      !Array.isArray(config.provider.args) ||
      !config.provider.args.every((value) => typeof value === 'string')
    ) {
      throw Error('CONFIG_PROVIDER_ARGS');
    }
    positiveInteger(config.provider.timeoutMs, 'PROVIDER_TIMEOUT');
  }
  return config;
}

function checkStart(config, now = Date.now()) {
  if (now >= Date.parse(config.heavy_start_cutoff_utc)) throw Error('NEWHEAVY_CUTOFF');
  if (now + config.job_seconds * 1000 > Date.parse(config.science_deadline)) {
    throw Error('JOB_DOES_NOT_FIT_DEADLINE');
  }
}

module.exports = { validateConfig, validateWorkerSettings, checkStart };
