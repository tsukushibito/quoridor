'use strict';

const fs = require('node:fs');
const { OwnedTree } = require('../ai-sigma-common/process/owned-tree.cjs');
const { procIdentity } = require('../ai-sigma-common/process/worker-client.cjs');

function identity(pid) {
  const fields = fs.readFileSync(`/proc/${pid}/stat`, 'utf8').split(')').at(-1).trim().split(/\s+/);
  return {
    pid,
    start_ticks: Number(fields[19]),
    ppid: Number(fields[1]),
    boot_id: fs.readFileSync('/proc/sys/kernel/random/boot_id', 'utf8').trim(),
  };
}

function normalized(row) {
  if (!row || !Number.isSafeInteger(row.pid) || row.pid < 1) throw Error('PROCESS_IDENTITY_SCHEMA');
  const starttick = String(row.starttick ?? row.start_ticks);
  const boot = row.boot ?? row.boot_id;
  if (!/^\d+$/.test(starttick) || typeof boot !== 'string' || !boot)
    throw Error('PROCESS_IDENTITY_SCHEMA');
  return { pid: row.pid, starttick, boot };
}

function matches(left, right) {
  return left.pid === right.pid && left.starttick === right.starttick && left.boot === right.boot;
}

class OwnedProcesses {
  constructor(root) {
    this.root = normalized(root);
    this.tree = new OwnedTree();
    this.tree.add(this.root);
    this.declarations = [];
    this.unresolved = [];
  }

  sample() {
    return this.tree.sample();
  }

  declare(childRow, parentRow) {
    const child = normalized(childRow),
      parent = normalized(parentRow);
    const expected = this.tree.owned.get(parent.pid);
    if (!expected || !matches(parent, expected)) throw Error('PROCESS_OWNER_UNKNOWN');
    const current = procIdentity(child.pid);
    if (!current || !matches(child, current)) throw Error('PROCESS_IDENTITY_CHANGED');
    const currentParent = procIdentity(parent.pid);
    const observed = identity(child.pid);
    if (currentParent && matches(currentParent, parent) && observed.ppid !== parent.pid) {
      throw Error('PROCESS_PARENT_CURRENT_MISMATCH');
    }
    if (!currentParent || !matches(currentParent, parent)) {
      const recorded = this.tree.owned.get(child.pid);
      if (!recorded || !matches(recorded, child)) {
        this.unresolved.push({ child, parent, observed_ppid: observed.ppid });
        throw Error('PROCESS_OWNER_NOT_OBSERVED');
      }
    }
    // Record ancestry while the parent is live, or retain an already observed
    // exact descendant after reparenting. An unproven late claim is not kill authority.
    if (childRow.ppid !== parent.pid) throw Error('PROCESS_PARENT_WITNESS');
    this.tree.add(child);
    this.declarations.push({ child, parent, observed_ppid: observed.ppid });
  }

  async waitEmpty(milliseconds) {
    const end = Date.now() + milliseconds;
    while (this.sample().length && Date.now() < end) {
      await new Promise((resolve) => setTimeout(resolve, 10));
    }
    return this.sample();
  }

  async recover(graceMs) {
    let remaining = await this.waitEmpty(graceMs);
    if (remaining.length) {
      this.tree.signal('SIGTERM');
      remaining = await this.waitEmpty(graceMs);
    }
    if (remaining.length) {
      this.tree.signal('SIGKILL');
      remaining = await this.waitEmpty(graceMs);
    }
    return {
      owned: [...this.tree.owned.values()],
      declarations: this.declarations,
      unresolved: this.unresolved,
      remaining,
    };
  }
}

module.exports = { identity, normalized, OwnedProcesses };
