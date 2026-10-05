'use strict';

const fs = require('fs');
const { execFile } = require('child_process');

// Read only through the project's Beads wrapper; no DB access or research dispatch.
class RunControl {
  constructor({ wrapper, goalIssue, issue, owner, deadline, pausePath, onFailure }) {
    Object.assign(this, { wrapper, goalIssue, issue, owner, deadline, pausePath, onFailure });
    this.closed = false;
    this.failure = null;
    this.inflight = null;
    this.receipts = [];
  }

  check() {
    if (this.failure) throw this.failure;
    if (Date.now() >= this.deadline) throw Error('PROCESSING_DEADLINE');
    if (fs.existsSync(this.pausePath)) throw Error('PAUSED');
  }

  readIssue(id) {
    this.check();
    return new Promise((resolve, reject) => {
      execFile(
        'bash',
        [this.wrapper, 'show', id, '--json'],
        {
          encoding: 'utf8',
          timeout: Math.max(1, Math.min(10000, this.deadline - Date.now())),
          maxBuffer: 2 * 1024 * 1024,
          env: { ...process.env, UV_NO_SYNC: '1', UV_OFFLINE: '1', PYTHONDONTWRITEBYTECODE: '1' },
        },
        (error, stdout) => {
          if (error) return reject(Error('BEADS_READ_UNKNOWN:' + error.message));
          try {
            const row = JSON.parse(stdout)[0];
            if (!row || row.id !== id) throw Error('BEADS_SCHEMA_UNKNOWN');
            if (row.status !== 'in_progress' || row.labels?.includes('paused-by-user')) {
              throw Error('PAUSED_OR_UNASSIGNED');
            }
            if (id === this.issue && row.assignee !== this.owner) throw Error('OWNER_CHANGED');
            const selected = { id, status: row.status, assignee: row.assignee, labels: row.labels };
            this.receipts.push({ ...selected, at: new Date().toISOString() });
            // Bounded runtime receipts; stopped job's final receipt retains the latest state.
            if (this.receipts.length > 32) this.receipts.shift();
            resolve(selected);
          } catch (failure) {
            reject(failure);
          }
        },
      );
    });
  }

  async poll() {
    if (this.closed || this.inflight) return;
    this.inflight = (async () => {
      try {
        this.check();
        await this.readIssue(this.goalIssue);
        await this.readIssue(this.issue);
        this.check();
      } catch (error) {
        this.failure = error;
        this.onFailure(error);
      }
    })();
    try {
      await this.inflight;
    } finally {
      this.inflight = null;
    }
  }

  async start() {
    await this.poll();
    this.check();
    this.timer = setInterval(() => {
      void this.poll();
    }, 5000);
  }

  async stop() {
    this.closed = true;
    clearInterval(this.timer);
    if (this.inflight) await this.inflight;
  }
}

module.exports = { RunControl };
