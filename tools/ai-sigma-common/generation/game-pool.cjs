'use strict';

const identity = require('./identity.cjs');

// Each game owns one backend tree; backend and provider implementations are injected.
class GamePool {
  constructor(worker, backend, broker, { run, maxHandles = 8 } = {}) {
    if (typeof run !== 'string' || !run || !Number.isSafeInteger(maxHandles) || maxHandles < 1) {
      throw Error('POOL_CONFIG');
    }
    Object.assign(this, { worker, backend, broker, run, maxHandles });
    this.games = new Map();
    this.seq = 0;
    this.stopped = false;
  }

  async search(game, { K = 4, generation = 1, fixture = {} } = {}) {
    if (this.stopped) throw Error('POOL_STOPPED');
    if (this.games.has(game)) throw Error('ACTIVE_GAME');
    if (this.games.size >= this.maxHandles) throw Error('HANDLE_CAP');
    const state = {
      game,
      generation,
      handle: null,
      pending: null,
      cancelled: false,
      NN_started: 0,
      NN_returned: 0,
      NN_discarded: 0,
      completed: 0,
    };
    this.games.set(game, state);
    const result = { cp: null, typed: null, firstNN: null, lastLeafNN: null, firstPending: null };
    try {
      state.handle = await this.backend.new(fixture, generation, K);
      while (!state.cancelled) {
        const step = await this.backend.begin(state.handle, generation);
        let done = !!step.done;
        if (step.pending) done = await this.resumePending(state, step, result);
        // Give message-based cancellation a chance even when backend work is synchronous.
        await new Promise((resolve) => setImmediate(resolve));
        if (done && !state.cancelled) {
          result.cp = await this.backend.checkpoint(state.handle, generation);
          state.completed = result.cp.simulations;
          break;
        }
      }
      if (state.cancelled) result.typed = 'CANCELLED';
    } catch (error) {
      result.typed = error.message;
    } finally {
      try {
        await this.releaseTree(state);
      } finally {
        this.games.delete(game);
      }
    }
    return {
      first_NN: result.firstNN,
      firstPending: result.firstPending,
      last_leafNN: result.lastLeafNN,
      game_id: game,
      generation,
      cp: result.cp,
      typed: result.typed,
      status: result.typed
        ? 'CONTROL_OR_MOCK_UNKNOWN'
        : result.cp?.root_visits === K
          ? 'MOCK_OR_TAPE_COMPLETE'
          : 'TERMINAL_OR_INCOMPLETE',
      counters: {
        started: state.NN_started,
        returned: state.NN_returned,
        discarded: state.NN_discarded,
        completed: state.completed,
      },
      zero: { pending: 0, handle: 0 },
      mock_or_tape: false,
      model_forward: state.NN_started,
    };
  }

  async resumePending(state, step, result) {
    if (state.pending) throw Error('ONE_PENDING_PER_GAME');
    const id = identity.validate({
      run_id: this.run,
      worker_id: this.worker,
      game_id: state.game,
      generation: state.generation,
      handle: state.handle,
      token: step.token,
      request_id: this.worker + ':' + ++this.seq,
    });
    state.pending = id;
    state.NN_started++;
    let row;
    try {
      row = await this.broker.infer(id, step.features_bits);
      state.NN_returned++;
      if (result.firstNN === null) {
        result.firstPending = step;
        result.firstNN = {
          features_bits: step.features_bits,
          NN_bits: row.NN.f32bits137,
          policy_logits: row.NN.logits,
          value: row.NN.value,
        };
      }
      result.lastLeafNN = {
        value: row.NN.value,
        side: step.turn + 1,
        ply: step.ply,
        view: 'last expanded NN leaf side-to-move',
      };
    } catch (error) {
      if (error.message === 'CANCEL_RETURN_DISCARDED') {
        state.NN_returned++;
        state.NN_discarded++;
      }
      throw error;
    }
    if (identity.key(row.identity) !== identity.key(id)) {
      throw Error('GENERATION_HANDLE_TOKEN_ATTRIBUTION');
    }
    if (state.cancelled) {
      state.NN_discarded++;
      throw Error('CANCEL_RETURN_DISCARDED');
    }
    state.pending = null;
    const resumed = await this.backend.resume(state.handle, state.generation, step.token, row.NN);
    state.completed = resumed.simulations;
    return !!resumed.done;
  }

  async releaseTree(state) {
    if (state.pending) {
      this.broker.cancel(this.worker, state.game, state.generation, this.run);
      await this.broker.quiescentGame(this.worker, state.game, this.run);
      state.pending = null;
    }
    if (state.handle !== null) {
      // A failed cancel must not prevent an attempted exact-handle release.
      try {
        await this.backend.cancel(state.handle, state.generation);
      } finally {
        await this.backend.free(state.handle);
      }
    }
  }

  cancel(game, generation) {
    const state = this.games.get(game);
    if (!state) return { active: false };
    if (state.generation !== generation) {
      return { active: true, error: 'STALE_CANCEL_GENERATION' };
    }
    state.cancelled = true;
    return this.broker.cancel(this.worker, game, generation, this.run);
  }

  stop() {
    this.stopped = true;
    for (const state of this.games.values()) this.cancel(state.game, state.generation);
  }
}

module.exports = { GamePool };
