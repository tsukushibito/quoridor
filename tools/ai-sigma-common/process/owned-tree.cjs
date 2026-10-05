'use strict';

const fs = require('fs');

function processTable() {
  const table = new Map();
  for (const entry of fs.readdirSync('/proc')) {
    if (!/^\d+$/.test(entry)) continue;
    try {
      const fields = fs
        .readFileSync('/proc/' + entry + '/stat', 'utf8')
        .split(')')
        .at(-1)
        .trim()
        .split(/\s+/);
      table.set(Number(entry), {
        pid: Number(entry),
        ppid: Number(fields[1]),
        starttick: fields[19],
        state: fields[0],
        rss: Number(fields[21]) * 4096,
      });
    } catch (error) {
      if (!['ENOENT', 'ESRCH'].includes(error.code)) throw error;
    }
  }
  return table;
}

// Track only descendants of explicit child identities; keep identities after reparenting.
class OwnedTree {
  constructor() {
    this.boot = fs.readFileSync('/proc/sys/kernel/random/boot_id', 'utf8').trim();
    this.owned = new Map();
  }

  add(identity) {
    if (!identity || identity.boot !== this.boot) throw Error('PROCESS_IDENTITY_UNKNOWN');
    this.owned.set(identity.pid, identity);
  }

  sample() {
    if (fs.readFileSync('/proc/sys/kernel/random/boot_id', 'utf8').trim() !== this.boot) {
      throw Error('BOOT_CHANGED');
    }
    const table = processTable();
    const active = new Set(
      [...this.owned.values()]
        .filter((expected) => table.get(expected.pid)?.starttick === expected.starttick)
        .map((expected) => expected.pid),
    );
    let changed = true;
    while (changed) {
      changed = false;
      for (const current of table.values()) {
        if (active.has(current.ppid) && !active.has(current.pid)) {
          active.add(current.pid);
          this.owned.set(current.pid, {
            pid: current.pid,
            starttick: current.starttick,
            boot: this.boot,
          });
          changed = true;
        }
      }
    }
    return [...active].map((pid) => table.get(pid)).filter((row) => row.state !== 'Z');
  }

  signal(signal) {
    // A signal targets only a fresh matching identity, including known reparented children.
    const rows = this.sample().reverse();
    for (const expected of rows) {
      const current = processTable().get(expected.pid);
      if (current?.starttick !== expected.starttick || current.state === 'Z') continue;
      try {
        process.kill(expected.pid, signal);
      } catch (error) {
        if (error.code !== 'ESRCH') throw error;
      }
    }
  }
}

module.exports = { OwnedTree };
