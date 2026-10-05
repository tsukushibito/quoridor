'use strict';

const { spawn } = require('child_process');
const readline = require('readline');

// FIFO is intentional: the native bridge replies without a transport request ID.
// A timeout or malformed/unsolicited response quarantines the entire pipe.
class Pipe {
  constructor(
    command,
    args = [],
    { timeoutMs = 1000, closeGraceMs = 250, killGraceMs = 250 } = {},
  ) {
    if (
      !Number.isFinite(timeoutMs) ||
      timeoutMs <= 0 ||
      !Number.isFinite(closeGraceMs) ||
      closeGraceMs < 0 ||
      !Number.isFinite(killGraceMs) ||
      killGraceMs < 0
    ) {
      throw Error('PIPE_CONFIG');
    }
    this.child = spawn(command, args, { stdio: ['pipe', 'pipe', 'pipe'] });
    this.queue = [];
    this.active = null;
    this.dead = null;
    this.closing = false;
    this.timeoutMs = timeoutMs;
    this.closeGraceMs = closeGraceMs;
    this.killGraceMs = killGraceMs;
    this.calls = 0;
    this.requestBytes = 0;
    this.responseBytes = 0;
    this.stderr = '';
    this.child.stderr.on('data', (buffer) => {
      this.stderr = (this.stderr + buffer).slice(-2048);
    });
    this.child.once('error', (error) => this.fail(error));
    this.child.stdin.on('error', (error) => this.fail(error));
    this.exit = new Promise((resolve) => {
      // 'close' includes stdio closure; spawn failures do not emit 'exit'.
      this.child.once('close', (code, signal) => {
        this.fail(Error('PIPE_EXIT'));
        resolve({ code, signal, pid: this.child.pid });
      });
    });
    this.reader = readline.createInterface({ input: this.child.stdout });
    this.reader.on('line', (line) => this.receive(line));
  }

  ask(request) {
    return new Promise((resolve, reject) => {
      if (this.dead || this.closing) return reject(this.dead ?? Error('PIPE_CLOSED'));
      this.queue.push({ request, resolve, reject });
      this.next();
    });
  }

  next() {
    if (this.dead || this.active || !this.queue.length) return;
    const active = (this.active = this.queue.shift());
    let line;
    try {
      line = JSON.stringify(active.request) + '\n';
    } catch (error) {
      this.fail(error);
      return;
    }
    this.calls++;
    this.requestBytes += Buffer.byteLength(line);
    active.timer = setTimeout(() => this.fail(Error('PIPE_TIMEOUT')), this.timeoutMs);
    this.child.stdin.write(line, (error) => {
      if (error) this.fail(error);
    });
  }

  receive(line) {
    this.responseBytes += Buffer.byteLength(line) + 1;
    if (this.dead) return;
    const active = this.active;
    if (!active) return this.fail(Error('UNSOLICITED_PIPE_REPLY'));
    let response;
    try {
      response = JSON.parse(line);
    } catch (_) {
      return this.fail(Error('PIPE_JSON'));
    }
    clearTimeout(active.timer);
    this.active = null;
    active.resolve(response);
    this.next();
  }

  fail(error) {
    if (this.dead) return;
    this.dead = error;
    if (this.active) {
      clearTimeout(this.active.timer);
      this.active.reject(error);
      this.active = null;
    }
    for (const queued of this.queue.splice(0)) queued.reject(error);
  }

  close() {
    if (this.closePromise) return this.closePromise;
    this.closing = true;
    this.closePromise = this.closeOwnedChild();
    return this.closePromise;
  }

  async closeOwnedChild() {
    // close is a stop operation, never a claim that unfinished requests succeeded.
    this.fail(Error('PIPE_CLOSED'));
    this.child.stdin.end();
    let timer;
    const grace = new Promise((resolve) => {
      timer = setTimeout(() => {
        this.child.kill('SIGTERM');
        resolve(null);
      }, this.closeGraceMs);
    });
    const exit = await Promise.race([this.exit, grace]);
    clearTimeout(timer);
    if (exit) return exit;
    // A child ignoring SIGTERM must not keep shutdown waiting forever.
    const killTimer = setTimeout(() => this.child.kill('SIGKILL'), this.killGraceMs);
    try {
      // Wait for actual stdio/process closure, not signal delivery.
      return await this.exit;
    } finally {
      clearTimeout(killTimer);
    }
  }
}

module.exports = { Pipe };
