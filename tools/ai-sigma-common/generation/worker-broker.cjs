'use strict';

const identity = require('./identity.cjs');

// Worker side of the infer/cancel/drain IPC protocol; no backend or model imports.
class WorkerBroker {
  constructor(send, { identityError = 'REPLY_IDENTITY' } = {}) {
    this.send = send;
    this.identityError = identityError;
    this.pending = new Map();
    this.waits = new Map();
    this.waitId = 0;
  }

  infer(id, features_bits648) {
    return new Promise((resolve, reject) => {
      if (this.pending.has(id.request_id)) return reject(Error('DUPLICATE_REQUEST_ID'));
      this.pending.set(id.request_id, { identity: id, resolve, reject });
      try {
        this.send({ kind: 'infer', identity: id, features_bits648 });
      } catch (error) {
        this.pending.delete(id.request_id);
        reject(error);
      }
    });
  }

  cancel(worker, game, generation, run) {
    this.send({ kind: 'cancel', worker, game, generation, run });
    return { pending: true };
  }

  quiescentGame(worker, game, run) {
    return new Promise((resolve, reject) => {
      const id = 'drain.' + ++this.waitId;
      this.waits.set(id, resolve);
      try {
        this.send({ kind: 'wait_game', worker, game, run, id });
      } catch (error) {
        this.waits.delete(id);
        reject(error);
      }
    });
  }

  handle(message) {
    if (message.kind === 'reply') {
      const pending = this.pending.get(message.request_id);
      if (!pending) return true;
      this.pending.delete(message.request_id);
      if (message.error) pending.reject(Error(message.error));
      else if (
        !message.data?.identity ||
        identity.key(message.data.identity) !== identity.key(pending.identity)
      ) {
        pending.reject(Error(this.identityError));
      } else pending.resolve(message.data);
      return true;
    }
    if (message.kind === 'drained') {
      this.waits.get(message.id)?.();
      this.waits.delete(message.id);
      return true;
    }
    return false;
  }
}

module.exports = { WorkerBroker };
