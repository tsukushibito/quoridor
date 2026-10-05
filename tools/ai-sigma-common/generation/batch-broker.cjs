'use strict';

const { performance } = require('perf_hooks');
const identity = require('./identity.cjs');

function validateOutput(row) {
  if (
    !Array.isArray(row.f32bits137) ||
    row.f32bits137.length !== 137 ||
    !Array.isArray(row.logits) ||
    row.logits.length !== 136 ||
    !row.logits.every(Number.isFinite) ||
    !Number.isFinite(row.value) ||
    Math.abs(row.value) > 1
  )
    throw Error('OUTPUT_SCHEMA');
  const values = new Float32Array([...row.logits, row.value]);
  const bits = Array.from(new Uint32Array(values.buffer));
  if (JSON.stringify(bits) !== JSON.stringify(row.f32bits137)) throw Error('F32_WIRE');
}

// Provider-neutral batching. Scientific run settings are supplied by the caller.
// An in-flight cancellation holds its game owner until the physical reply returns.
class Broker {
  constructor(
    askBatch,
    { maxBatch = 8, maxPendingGames = 24, flushMs = 0.25, replyCap = 512 } = {},
  ) {
    if (
      typeof askBatch !== 'function' ||
      !Number.isSafeInteger(maxBatch) ||
      maxBatch < 1 ||
      !Number.isSafeInteger(maxPendingGames) ||
      maxPendingGames < maxBatch ||
      !Number.isFinite(flushMs) ||
      flushMs < 0 ||
      flushMs > 1 ||
      !Number.isSafeInteger(replyCap) ||
      replyCap < 1
    ) {
      throw Error('BROKER_CONFIG');
    }
    Object.assign(this, { askBatch, maxBatch, maxPendingGames, flushMs, replyCap });
    this.queue = [];
    this.owners = new Map();
    this.timer = null;
    this.inflight = null;
    this.next = 0;
    this.stopped = false;
    this.fault = null;
    this.waiters = [];
    this.stats = {
      started: 0,
      returned: 0,
      resumed: 0,
      discarded: 0,
      rejected_queued: 0,
      batches: [],
      receipts: [],
      max_pending_games: 0,
      batch_histogram: Array(maxBatch + 1).fill(0),
      queue_ms_sum: 0,
      queue_ms_max: 0,
      provider_pipe_ms: 0,
    };
  }

  infer(rawIdentity, bits) {
    let id;
    try {
      id = identity.validate(rawIdentity);
      identity.features(bits);
    } catch (error) {
      return Promise.reject(error);
    }
    const owner = identity.owner(id);
    return new Promise((resolve, reject) => {
      if (this.stopped) return reject(Error(this.fault ?? 'STOPPED'));
      if (this.owners.has(owner)) return reject(Error('ONE_PENDING_PER_GAME'));
      if (this.owners.size >= this.maxPendingGames) return reject(Error('GAME_PENDING_CAP'));
      const entry = {
        identity: id,
        wire_id: 'nn0.' + ++this.next,
        bits,
        resolve,
        reject,
        cancelled: false,
        queued: performance.now(),
        sent: null,
      };
      this.owners.set(owner, entry);
      this.queue.push(entry);
      this.stats.max_pending_games = Math.max(this.stats.max_pending_games, this.owners.size);
      this.schedule();
    });
  }

  schedule() {
    if (this.stopped || this.inflight || !this.queue.length) return;
    if (this.queue.length >= this.maxBatch) {
      if (this.timer) clearTimeout(this.timer);
      this.timer = null;
      void this.flush();
    } else if (!this.timer) {
      this.timer = setTimeout(() => {
        this.timer = null;
        void this.flush();
      }, this.flushMs);
    }
  }

  async flush() {
    if (this.stopped || this.inflight || !this.queue.length) return;
    const batch = this.queue.splice(0, this.maxBatch);
    this.inflight = batch;
    const sent = performance.now();
    for (const entry of batch) entry.sent = sent;
    // Refuse before provider dispatch: started records physical requests, not a rejected forecast.
    if (this.stats.started + batch.length > this.replyCap) {
      this.fail('SAMPLE_CAP');
      for (const entry of batch) this.release(entry);
      this.inflight = null;
      this.notify();
      return;
    }
    this.stats.started += batch.length;
    try {
      const rows = await this.askBatch(
        batch.map((entry) => ({
          id: entry.wire_id,
          features_bits648: entry.bits,
        })),
      );
      this.stats.returned += Array.isArray(rows) ? rows.length : 0;
      if (
        !Array.isArray(rows) ||
        rows.length !== batch.length ||
        rows.some((row, index) => !row || row.id !== batch[index].wire_id)
      ) {
        throw Error('BROKER_ID_ATTRIBUTION');
      }
      for (const row of rows) validateOutput(row);
      const received = performance.now();
      this.recordBatch(batch, sent, received);
      batch.forEach((entry, index) => {
        if (this.replyCap <= 512 || this.stats.receipts.length < 16) {
          this.stats.receipts.push({
            identity: entry.identity,
            wire_id: entry.wire_id,
            started_ms: entry.sent,
            returned_ms: received,
            discarded: entry.cancelled,
          });
        }
        if (entry.cancelled) {
          this.stats.discarded++;
          entry.reject(Error('CANCEL_RETURN_DISCARDED'));
        } else {
          this.stats.resumed++;
          entry.resolve({ identity: entry.identity, NN: rows[index] });
        }
      });
    } catch (error) {
      this.fail(error.message);
    } finally {
      for (const entry of batch) this.release(entry);
      this.inflight = null;
      this.notify();
      this.schedule();
    }
  }

  recordBatch(batch, sent, received) {
    this.stats.batch_histogram[batch.length]++;
    this.stats.provider_pipe_ms += received - sent;
    for (const entry of batch) {
      this.stats.queue_ms_sum += sent - entry.queued;
      this.stats.queue_ms_max = Math.max(this.stats.queue_ms_max, sent - entry.queued);
    }
    if (this.replyCap <= 512 || this.stats.batches.length < 16) {
      this.stats.batches.push({
        size: batch.length,
        sent_ms: sent,
        received_ms: received,
        queue_ms: batch.map((entry) => sent - entry.queued),
      });
    }
  }

  release(entry) {
    const owner = identity.owner(entry.identity);
    if (this.owners.get(owner) === entry) this.owners.delete(owner);
    for (const resolve of entry.drainWaiters ?? []) resolve();
  }

  cancel(worker, game, generation, run) {
    const entry = this.owners.get(JSON.stringify([run, worker, game]));
    if (!entry) return { pending: false };
    if (entry.identity.generation !== generation) {
      return { pending: true, error: 'STALE_CANCEL_GENERATION' };
    }
    entry.cancelled = true;
    if (entry.sent === null) {
      this.queue = this.queue.filter((candidate) => candidate !== entry);
      this.stats.rejected_queued++;
      entry.reject(Error('CANCEL_QUEUED'));
      this.release(entry);
      this.notify();
    }
    return { pending: entry.sent !== null, inflight: entry.sent !== null };
  }

  fail(reason) {
    this.fault = reason;
    this.stopped = true;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    for (const entry of this.queue.splice(0)) {
      entry.cancelled = true;
      entry.reject(Error('PROVIDER_OR_CONTROL_UNKNOWN:' + reason));
      this.release(entry);
    }
    for (const entry of this.inflight ?? []) {
      entry.cancelled = true;
      entry.reject(Error('PROVIDER_OR_CONTROL_UNKNOWN:' + reason));
    }
    this.notify();
  }

  stop() {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    this.stopped = true;
    for (const entry of this.queue.splice(0)) {
      this.stats.rejected_queued++;
      entry.cancelled = true;
      entry.reject(Error('STOPPED_QUEUED'));
      this.release(entry);
    }
    for (const entry of this.inflight ?? []) entry.cancelled = true;
    this.notify();
    return this.zero();
  }

  zero() {
    return {
      pending_games: this.owners.size,
      inflight_batches: this.inflight ? 1 : 0,
      queued: this.queue.length,
      timer: this.timer !== null,
      started: this.stats.started,
      returned: this.stats.returned,
    };
  }

  notify() {
    if (!this.owners.size && !this.inflight) {
      for (const resolve of this.waiters.splice(0)) resolve();
    }
  }

  async quiescent() {
    if (!this.owners.size && !this.inflight) return;
    await new Promise((resolve) => this.waiters.push(resolve));
  }

  async quiescentGame(worker, game, run) {
    const entry = this.owners.get(JSON.stringify([run, worker, game]));
    if (!entry) return;
    await new Promise((resolve) => (entry.drainWaiters ??= []).push(resolve));
  }
}

module.exports = { Broker, validateOutput };
