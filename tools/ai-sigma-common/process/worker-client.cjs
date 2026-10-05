'use strict';

const { spawn } = require('child_process');
const fs = require('fs');

function procIdentity(pid) {
  try {
    const fields = fs
      .readFileSync('/proc/' + pid + '/stat', 'utf8')
      .split(')')
      .at(-1)
      .trim()
      .split(/\s+/);
    return {
      pid,
      starttick: fields[19],
      boot: fs.readFileSync('/proc/sys/kernel/random/boot_id', 'utf8').trim(),
    };
  } catch (_) {
    return null;
  }
}

function sameProcess(expected) {
  if (!expected) return false;
  const current = procIdentity(expected.pid);
  return !!current && current.starttick === expected.starttick && current.boot === expected.boot;
}

// One IPC worker, one owner. Caller supplies the scientific protocol message handler.
class WorkerClient {
  constructor({ script, cpu, output, timeoutMs, onMessage }) {
    this.pending = new Map();
    this.seq = 0;
    this.timeoutMs = timeoutMs;
    this.child = spawn(
      'taskset',
      [
        '-c',
        String(cpu),
        process.execPath,
        '--max-old-space-size=192',
        script,
        String(cpu),
        output,
      ],
      {
        stdio: ['ignore', 'inherit', 'inherit', 'ipc'],
      },
    );
    this.identity = procIdentity(this.child.pid);
    this.child.on('error', (error) => this.rejectPending(error));
    this.child.on('message', (message) => {
      if (onMessage(message, this)) return;
      const pending = this.pending.get(message.id);
      if (!pending) return;
      this.pending.delete(message.id);
      clearTimeout(pending.timer);
      if (message.error) pending.reject(Error(message.error));
      else pending.resolve(message.data);
    });
    this.exit = new Promise((resolve) => {
      this.child.once('close', (code, signal) => {
        this.rejectPending(Error('WORKER_EXIT'));
        resolve({ code, signal, identity: this.identity });
      });
    });
  }

  send(message) {
    if (!this.child.connected) throw Error('WORKER_DISCONNECTED');
    this.child.send(message);
  }

  ask(op, fields = {}, { timeoutMs = this.timeoutMs } = {}) {
    const id = ++this.seq;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(Error('WORKER_REQUEST_TIMEOUT'));
      }, timeoutMs);
      this.pending.set(id, { resolve, reject, timer });
      try {
        this.send({ id, op, ...fields });
      } catch (error) {
        clearTimeout(timer);
        this.pending.delete(id);
        reject(error);
      }
    });
  }

  rejectPending(error) {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
  }

  abort() {
    if (this.child.connected) this.send({ kind: 'abort' });
  }

  async recover(timeoutMs) {
    this.abort();
    let timer;
    const natural = await Promise.race([
      this.exit,
      new Promise((resolve) => {
        timer = setTimeout(() => resolve(null), timeoutMs);
      }),
    ]);
    clearTimeout(timer);
    if (natural) return natural;
    if (!sameProcess(this.identity)) throw Error('WORKER_IDENTITY_UNKNOWN');
    this.child.kill('SIGTERM');
    const killTimer = setTimeout(
      () => {
        if (sameProcess(this.identity)) this.child.kill('SIGKILL');
      },
      Math.max(1, timeoutMs),
    );
    try {
      return await this.exit;
    } finally {
      clearTimeout(killTimer);
    }
  }
}

module.exports = { WorkerClient, procIdentity, sameProcess };
