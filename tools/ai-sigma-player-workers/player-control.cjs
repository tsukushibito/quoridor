'use strict';
// User's player-specific Worker policy: close a generation without waiting for
// an event-loop message or interrupting a model.run already in progress.
const PlayerControl = (() => {
  const STATE = { ACTIVE: 1, ADOPTED: 2, CANCELLED: 3, ABORTED: 4 };
  function create(generation) {
    if (!Number.isInteger(generation) || generation <= 0) throw Error('CONTROL_GENERATION');
    const memory = new SharedArrayBuffer(16);
    const words = new Int32Array(memory);
    Atomics.store(words, 0, generation);
    Atomics.store(words, 1, STATE.ACTIVE);
    return memory;
  }
  function bind(memory, generation) {
    if (!(memory instanceof SharedArrayBuffer) || memory.byteLength !== 16) throw Error('CONTROL_SCHEMA');
    const words = new Int32Array(memory);
    if (Atomics.load(words, 0) !== generation) throw Error('CONTROL_GENERATION');
    function active() { return Atomics.load(words, 0) === generation && Atomics.load(words, 1) === STATE.ACTIVE; }
    function close(reason) {
      const state = reason === 'adopt' ? STATE.ADOPTED : reason === 'cancel' ? STATE.CANCELLED : STATE.ABORTED;
      Atomics.compareExchange(words, 1, STATE.ACTIVE, state);
      return status();
    }
    function status() { return { generation: Atomics.load(words, 0), state: Atomics.load(words, 1), NN_started: Atomics.load(words, 2), NN_returned: Atomics.load(words, 3) }; }
    return { active, close, status, words };
  }
  return { create, bind, STATE };
})();
globalThis.PlayerControl = PlayerControl;
if (typeof module !== 'undefined') module.exports = PlayerControl;
