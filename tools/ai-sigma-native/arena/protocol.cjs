'use strict';
const { spawn } = require('node:child_process');
const now = () => Number(process.hrtime.bigint()) / 1e6;

const DEFAULTS = {
  maxQueueMessages: 32,
  maxQueueBytes: 1024 * 1024,
  maxReplyBytes: 1024 * 1024,
  maxRequestBytes: 1024 * 1024,
  maxStderrBytes: 8192,
  stopTimeoutMs: 2000,
  closeGraceMs: 2000,
  killGraceMs: 1000,
};

class Worker {
  constructor(manifest, script = __dirname + '/worker.cjs', extra = [], options = {}) {
    this.options = { ...DEFAULTS, ...options };
    for (const name of Object.keys(DEFAULTS)) {
      const value = this.options[name];
      if (!Number.isSafeInteger(value) || value <= 0 || value > 0x7fffffff)
        throw Error('TRANSPORT_OPTION_' + name);
    }
    if (
      options.affinity !== undefined &&
      (!Array.isArray(options.affinity) ||
        !options.affinity.length ||
        options.affinity.some((cpu) => !Number.isSafeInteger(cpu) || cpu < 0) ||
        new Set(options.affinity).size !== options.affinity.length)
    )
      throw Error('TRANSPORT_AFFINITY');
    if (
      options.spawnArgs !== undefined &&
      (!Array.isArray(options.spawnArgs) ||
        options.spawnArgs.some((arg) => typeof arg !== 'string'))
    )
      throw Error('TRANSPORT_SPAWN_ARGS');
    this.queue = [];
    this.queueSizes = [];
    this.queueBytes = 0;
    this.pending = Buffer.alloc(0);
    this.waiter = null;
    this.operation = null;
    this.exit = null;
    this.closed = null;
    this.failure = null;
    this.closing = false;
    this.stderr = '';
    this.stderrBytes = Buffer.alloc(0);
    this.signals = [];
    this.spawned = false;
    this.closePromise = null;
    this.closedPromise = new Promise((resolve) => {
      this.resolveClosed = resolve;
    });
    const executable = options.executable ?? process.execPath;
    const args = [...(options.spawnArgs ?? []), script, manifest, ...extra];
    this.p = spawn(
      options.affinity ? 'taskset' : executable,
      options.affinity ? ['-c', options.affinity.join(','), executable, ...args] : args,
      {
        stdio: ['pipe', 'pipe', 'pipe'],
      },
    );
    this.p.on('spawn', () => {
      this.spawned = true;
      if (this.failure) this.signal('SIGTERM');
    });
    this.p.on('error', (error) => this.fail('PROCESS_ERROR', String(error)));
    this.p.on('exit', (code, signal) => {
      this.exit = { code, signal };
    });
    // exit does not imply that inherited stdout/stderr have closed. Only close
    // establishes collection; late complete lines can still arrive after exit.
    this.p.on('close', (code, signal) => {
      this.closed = { code, signal };
      this.resolveClosed(this.closed);
      this.push({ type: 'EOF', code, signal });
    });
    this.p.stdin.on('error', (error) => {
      if (!this.closing) this.fail('STDIN_ERROR', String(error));
    });
    this.p.stdout.on('error', (error) => this.fail('STDOUT_ERROR', String(error)));
    this.p.stderr.on('error', (error) => this.fail('STDERR_ERROR', String(error)));
    this.p.stderr.on('data', (bytes) => {
      this.stderrBytes = Buffer.concat([this.stderrBytes, bytes]).subarray(
        -this.options.maxStderrBytes,
      );
      this.stderr = this.stderrBytes.toString();
    });
    this.p.stdout.on('data', (bytes) => this.read(bytes));
    this.p.stdout.on('end', () => {
      if (this.pending.length && !this.closing && !this.failure)
        this.fail('SCHEMA_ERROR', 'UNTERMINATED_REPLY');
    });
  }

  read(bytes) {
    let offset = 0;
    while (offset < bytes.length && !this.failure && !this.closing) {
      const newline = bytes.indexOf(10, offset);
      const end = newline < 0 ? bytes.length : newline;
      const part = bytes.subarray(offset, end);
      if (this.pending.length + part.length > this.options.maxReplyBytes) {
        this.fail('REPLY_CAP', 'JSON line exceeds maxReplyBytes');
        return;
      }
      const line = this.pending.length ? Buffer.concat([this.pending, part]) : part;
      if (newline < 0) {
        this.pending = Buffer.from(line);
        return;
      }
      this.pending = Buffer.alloc(0);
      offset = newline + 1;
      try {
        const message = JSON.parse(line.toString());
        if (!message || typeof message !== 'object' || typeof message.type !== 'string')
          throw Error('REPLY_OBJECT_TYPE');
        this.push(message, line.length + 1);
      } catch (error) {
        this.fail('SCHEMA_ERROR', String(error));
      }
    }
  }

  fail(type, reason) {
    if (this.failure || this.closed) return;
    this.failure = { type, reason };
    this.queue.length = 0;
    this.queueSizes.length = 0;
    this.queueBytes = 0;
    this.pending = Buffer.alloc(0);
    this.deliver(this.failure);
    // Capacity/write/spawn faults stop the owned child immediately; no retry.
    void this.beginClose(true);
  }

  deliver(message) {
    if (!this.waiter) return false;
    const waiter = this.waiter;
    this.waiter = null;
    waiter(message);
    return true;
  }

  push(message, bytes = Buffer.byteLength(JSON.stringify(message))) {
    if (this.failure || this.closing) return;
    if (this.deliver(message)) return;
    if (
      this.queue.length >= this.options.maxQueueMessages ||
      this.queueBytes + bytes > this.options.maxQueueBytes
    ) {
      this.fail('QUEUE_CAP', 'Reply queue exceeds message/byte capacity');
      return;
    }
    this.queue.push(message);
    this.queueSizes.push(bytes);
    this.queueBytes += bytes;
  }

  async take(ms) {
    if (this.operation) throw Error('WAITER_CONCURRENCY');
    return this.takeOwned(ms);
  }

  async takeOwned(ms) {
    if (!Number.isFinite(ms) || ms < 0 || ms > 0x7fffffff) throw Error('WAIT_BUDGET');
    if (this.waiter) throw Error('WAITER_CONCURRENCY');
    if (this.failure) return this.failure;
    if (this.queue.length) {
      this.queueBytes -= this.queueSizes.shift();
      return this.queue.shift();
    }
    if (this.closed) return { type: 'EOF', ...this.closed };
    if (this.closing) return { type: 'CLOSING' };
    return new Promise((resolve) => {
      const timer = setTimeout(
        () => {
          if (this.waiter === accept) this.waiter = null;
          resolve({ type: 'WAIT_TIMEOUT', timer_fired_ms: now() });
        },
        Math.max(0, ms),
      );
      const accept = (message) => {
        clearTimeout(timer);
        resolve(message);
      };
      this.waiter = accept;
    });
  }

  send(message, closing = false) {
    if (this.closed || this.exit || this.failure || (this.closing && !closing)) return false;
    if (this.p.stdin.destroyed || !this.p.stdin.writable) {
      if (!closing) this.fail('STDIN_ERROR', 'Input pipe is not writable');
      return false;
    }
    try {
      const encoded = JSON.stringify(message) + '\n';
      if (Buffer.byteLength(encoded) > this.options.maxRequestBytes) {
        this.fail('REQUEST_CAP', 'Request exceeds maxRequestBytes');
        return false;
      }
      this.p.stdin.write(encoded, (error) => {
        if (error && !this.closing) this.fail('STDIN_ERROR', String(error));
      });
      return true;
    } catch (error) {
      this.fail('STDIN_ERROR', String(error));
      return false;
    }
  }

  async request(command, budget, validate = null, inputReady = null, margin = 10) {
    if (
      !Number.isFinite(budget) ||
      budget <= 0 ||
      budget > 0x7fffffff ||
      !Number.isFinite(margin) ||
      margin < 0 ||
      margin >= budget
    )
      throw Error('REQUEST_BUDGET');
    const t0 = inputReady ?? now();
    if (!Number.isFinite(t0)) throw Error('INPUT_READY_CLOCK');
    if (this.operation || this.waiter) throw Error('REQUEST_CONCURRENCY');
    this.operation = 'request';
    const obsolete = [];
    let obsoleteBytes = 0;
    let timerFired = null,
      response = null;
    try {
      if (now() - t0 < budget) this.send({ ...command, deadline_ms: t0 + budget - margin });
      while (now() - t0 < budget) {
        const message = await this.takeOwned(Math.max(0, budget - (now() - t0)));
        if (message.type === 'WAIT_TIMEOUT') {
          timerFired = message.timer_fired_ms;
          if (now() < t0 + budget) continue;
          break;
        }
        if (
          message.type === 'RESULT' &&
          (message.id !== command.id ||
            message.generation !== command.generation ||
            message.key !== command.key ||
            message.history !== command.history)
        ) {
          const record = { type: message.type, id: message.id, reason: 'STALE_IDENTITY_DISCARD' };
          const bytes = Buffer.byteLength(JSON.stringify(record));
          if (
            obsolete.length >= this.options.maxQueueMessages ||
            obsoleteBytes + bytes > this.options.maxQueueBytes
          ) {
            this.fail('QUEUE_CAP', 'Stale response record exceeds bounded capacity');
            response = this.failure;
            break;
          }
          obsolete.push(record);
          obsoleteBytes += bytes;
          continue;
        }
        response = message;
        if (message.type === 'RESULT' && validate) {
          try {
            message.validation = validate(message);
          } catch (error) {
            message.validation = { valid: false, reason: String(error) };
          }
        }
        break;
      }
      // t1 is after complete parse, identity discard and caller validation.
      const received = now(),
        elapsed = received - t0;
      return {
        t0_ms: t0,
        received_ms: received,
        elapsed_ms: elapsed,
        budget_ms: budget,
        margin_ms: margin,
        timer_fired_ms: timerFired,
        timer_callback_delay_ms:
          timerFired === null ? null : Math.max(0, timerFired - (t0 + budget)),
        overshoot_ms: Math.max(0, elapsed - budget),
        t1_definition: 'complete parse+generation/key/history+legal completed Action validation',
        obsolete,
        response,
        status:
          !response || elapsed > budget
            ? 'OUTER_DEADLINE'
            : response.type === 'RESULT'
              ? 'RECEIVED'
              : response.type,
      };
    } finally {
      this.operation = null;
    }
  }

  async stop(id) {
    if (this.operation || this.waiter) throw Error('REQUEST_CONCURRENCY');
    if (this.failure) return { status: this.failure.type, cleanup: await this.close() };
    if (this.closed) return { status: 'ALREADY_EXITED', ...this.closed };
    this.operation = 'stop';
    const start = now(),
      discarded = [];
    let discardedBytes = 0;
    try {
      this.send({ kind: 'STOP', id });
      while (now() - start < this.options.stopTimeoutMs) {
        const message = await this.takeOwned(
          Math.max(0, this.options.stopTimeoutMs - (now() - start)),
        );
        if (message.type === 'STOP_ACK' && message.id === id)
          return {
            status: 'STOP_ACK',
            allNN: message.allNN,
            wall_ms: now() - start,
            discarded_late_responses: discarded,
          };
        if (message.type === 'EOF' || this.failure)
          return {
            status: message.type,
            ...message,
            discarded_late_responses: discarded,
            cleanup: await this.close(),
          };
        if (message.type === 'WAIT_TIMEOUT') continue;
        const record = {
          received_ms: now(),
          type: message.type,
          id: message.id,
          generation: message.generation,
          allNN: message.allNN,
          adopted: false,
          reason: 'AFTER_DEADLINE_OR_STOP_DISCARD',
        };
        const bytes = Buffer.byteLength(JSON.stringify(record));
        if (
          discarded.length >= this.options.maxQueueMessages ||
          discardedBytes + bytes > this.options.maxQueueBytes
        ) {
          this.fail('QUEUE_CAP', 'Stop discard record exceeds bounded capacity');
          return {
            status: 'QUEUE_CAP',
            discarded_late_responses: discarded,
            cleanup: await this.close(),
          };
        }
        discarded.push(record);
        discardedBytes += bytes;
      }
      this.fail('STOP_TIMEOUT', 'Owned child did not acknowledge stop');
      return {
        status: 'STOP_TIMEOUT_KILLED',
        discarded_late_responses: discarded,
        cleanup: await this.close(),
      };
    } finally {
      this.operation = null;
    }
  }

  signal(signal) {
    if (
      !this.spawned ||
      this.exit ||
      this.closed ||
      !Number.isInteger(this.p.pid) ||
      this.signals.some((item) => item.signal === signal)
    )
      return false;
    try {
      if (!this.p.kill(signal)) return false;
    } catch (error) {
      this.signalError = { type: 'SIGNAL_ERROR', signal, reason: String(error) };
      return false;
    }
    this.signals.push({ pid: this.p.pid, signal, at_ms: now() });
    return true;
  }

  async waitClosed(ms) {
    if (this.closed) return true;
    return new Promise((resolve) => {
      const timer = setTimeout(() => resolve(false), ms);
      this.closedPromise.then(() => {
        clearTimeout(timer);
        resolve(true);
      });
    });
  }

  beginClose(force = false) {
    if (this.closePromise) return this.closePromise;
    this.closing = true;
    this.deliver(this.failure ?? { type: 'CLOSING' });
    this.queue.length = 0;
    this.queueSizes.length = 0;
    this.queueBytes = 0;
    this.pending = Buffer.alloc(0);
    this.closePromise = Promise.resolve().then(async () => {
      const start = now();
      if (force) this.signal('SIGTERM');
      else this.send({ kind: 'CLOSE' }, true);
      let collected = await this.waitClosed(
        force ? this.options.killGraceMs : this.options.closeGraceMs,
      );
      if (!collected && !force) {
        this.signal('SIGTERM');
        collected = await this.waitClosed(this.options.killGraceMs);
      }
      if (!collected) {
        this.signal('SIGKILL');
        await this.waitClosed(this.options.killGraceMs);
      }
      return {
        exit: this.exit,
        close: this.closed,
        wall_ms: now() - start,
        stderr: this.stderr,
        waited: !!this.closed,
        owned_pid: this.p.pid ?? null,
        spawned: this.spawned,
        signals: this.signals.slice(),
        failure: this.failure,
        signal_error: this.signalError ?? null,
      };
    });
    return this.closePromise;
  }

  async close() {
    const receipt = await this.beginClose();
    // A delayed inherited stdio close may arrive after a bounded first receipt.
    // Refresh facts without repeating signals or inventing prior collection.
    return { ...receipt, exit: this.exit, close: this.closed, waited: !!this.closed };
  }
}

module.exports = { Worker };
