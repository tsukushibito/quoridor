'use strict';

const { spawn } = require('node:child_process');
const readline = require('node:readline');
const { now } = require('./control.cjs');
const { OwnedProcesses, identity } = require('./process.cjs');

class Engine {
  constructor(engine, model = null, config = {}) {
    this.timeout = config.pipeTimeoutMs;
    if (!Number.isFinite(this.timeout) || this.timeout <= 0)
      throw Error('RUNTIME_CONFIG_pipeTimeoutMs');
    this.seq = 0;
    this.pending = new Map();
    this.err = '';
    this.closed = false;
    this.closing = false;
    this.child = spawn(
      process.execPath,
      [
        '--max-old-space-size=' + (config.maxOldSpaceMb ?? 192),
        config.workerScript ?? __dirname + '/mcts-worker.cjs',
        engine,
      ],
      {
        stdio: ['pipe', 'pipe', 'pipe'],
        env: {
          ...process.env,
          SIGMA_RUNTIME_CONFIG: JSON.stringify({ ...config, ...(model ? { model } : {}) }),
        },
      },
    );
    this.owned = new OwnedProcesses(identity(this.child.pid));
    this.observer = setInterval(
      () => {
        try {
          this.owned.sample();
        } catch (error) {
          this.fail(error);
        }
      },
      Math.max(1, Math.min(50, this.timeout / 4)),
    );
    this.observer.unref();
    this.child.stderr.on('data', (buffer) => {
      this.err = (this.err + buffer).slice(-16384);
    });
    this.child.on('error', (error) => this.fail(error));
    this.child.stdin.on('error', (error) => this.fail(error));
    this.exit = new Promise((resolve) => {
      this.child.once('close', (code, signal) => {
        this.closed = true;
        if (!this.closing || this.pending.size)
          this.fail(Error('ENGINE_EXIT ' + code + ' ' + signal + ' ' + this.err));
        resolve({ code, signal });
      });
    });
    readline.createInterface({ input: this.child.stdout }).on('line', (line) => this.receive(line));
  }

  receive(line) {
    try {
      const message = JSON.parse(line);
      if (message.kind === 'owned') {
        this.owned.declare(message.child, message.parent);
        return;
      }
      if (message.kind === 'fatal') throw Error(message.error ?? 'ENGINE_FATAL');
      // A quarantined transport's late response cannot revive rejected work.
      if (this.fault) return;
      const pending = this.pending.get(message.id);
      if (!pending) throw Error('UNKNOWN_ENGINE_REPLY');
      if (message.kind === 'cp') {
        pending.cp?.(message, now());
        return;
      }
      clearTimeout(pending.timer);
      this.pending.delete(message.id);
      if (message.error) pending.reject(Error(message.error));
      else pending.resolve({ ...message, controller_receive_ms: now() });
    } catch (error) {
      this.fail(error);
    }
  }

  fail(error) {
    if (this.fault) return;
    this.fault = error;
    this.stopCurrent();
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
    // Give the worker's EOF shutdown a chance to cancel and close its child pipes.
    if (!this.child.stdin.destroyed) this.child.stdin.end();
    this.recoveryPromise = this.owned
      .recover(this.timeout)
      .finally(() => clearInterval(this.observer));
  }

  request(request, onCP) {
    if (this.closed || this.fault || (this.closing && request.op !== 'close')) {
      return Promise.reject(this.fault ?? Error('ENGINE_CLOSED'));
    }
    const id = ++this.seq;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => this.fail(Error('ENGINE_REPLY_TIMEOUT')), this.timeout);
      this.pending.set(id, { resolve, reject, cp: onCP, timer });
      try {
        this.child.stdin.write(JSON.stringify({ ...request, id }) + '\n', (error) => {
          if (error) this.fail(error);
        });
      } catch (error) {
        this.fail(error);
      }
    });
  }

  stopCurrent() {
    if (this.child.stdin.destroyed) return;
    for (const id of this.pending.keys()) {
      try {
        this.child.stdin.write(JSON.stringify({ op: 'stop', id }) + '\n', (error) => {
          // Recovery/EOF is already responsible for a broken pipe; do not recurse.
          if (error && !this.fault) this.fail(error);
        });
      } catch (error) {
        if (!this.fault) this.fail(error);
      }
    }
  }

  async init(mock = false) {
    const result = await this.request({ op: 'init', mock });
    this.info = result.data;
    return result.data;
  }

  close() {
    if (!this.closePromise) this.closePromise = this.closeOwned();
    return this.closePromise;
  }

  async closeOwned() {
    this.closing = true;
    let receipt = null,
      error = null;
    try {
      if (!this.closed && !this.fault) receipt = (await this.request({ op: 'close' })).data;
    } catch (failure) {
      error = String(failure);
    } finally {
      if (!this.child.stdin.destroyed) this.child.stdin.end();
    }
    const ownership = await (this.recoveryPromise ?? this.owned.recover(this.timeout));
    const exit = await new Promise((resolve) => {
      const timer = setTimeout(() => resolve(null), this.timeout);
      this.exit.then((value) => {
        clearTimeout(timer);
        resolve(value);
      });
    });
    if (!exit) error ??= 'STDIO_COLLECTION_TIMEOUT';
    clearInterval(this.observer);
    return { receipt, error, exit, ownership, stdio_collected: exit !== null, stderr: this.err };
  }
}

module.exports = { Engine };
