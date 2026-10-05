class MCTSNode {
  constructor(state, parent = null, action = null, prior = 1.0, parentState = null) {
    this.state = state;
    this._parentState = parentState;
    this.parent = parent;
    this.action = action;
    this.prior = prior;
    this.basePrior = prior;
    this.children = [];
    this.visitCount = 0;
    this.valueSum = 0;
    this.isExpanded = false;
  }

  ensureState() {
    if (this.state === null) {
      this.state = this._parentState.next(this.action);
      this._parentState = null;
    }
  }

  get qValue() {
    return this.visitCount === 0 ? 0 : this.valueSum / this.visitCount;
  }

  bestChild(cPuct = 1.0, fpuReduction = 0.2) {
    const pq = this.qValue;
    const sqrtN = Math.sqrt(this.visitCount);
    let visitedPriorSum = 0;
    for (const c of this.children) if (c.visitCount > 0) visitedPriorSum += c.basePrior;
    let best = null,
      bestScore = -Infinity;
    for (const c of this.children) {
      const u = (cPuct * c.prior * sqrtN) / (1 + c.visitCount);
      const q = c.visitCount === 0 ? pq - fpuReduction * Math.sqrt(visitedPriorSum) : -c.qValue;
      const score = q + u;
      if (score > bestScore) {
        bestScore = score;
        best = c;
      }
    }
    return best;
  }
}

const C_PUCT = 1.0;
const FPU_REDUCTION = 0.2;

async function expandNode(node, evaluator) {
  const legalStart = stamp(),
    legal = node.state.getLegalActions();
  if (clockContext) clockContext.spans.push({ kind: 'legal', start: legalStart, end: stamp() });
  let priors, value;
  if (legal.length === 0) {
    priors = [];
    value = 0;
  } else {
    [priors, value] = await evaluator(node.state, legal);
  }
  for (let i = 0; i < legal.length; i++) {
    node.children.push(new MCTSNode(null, node, legal[i], priors[i], node.state));
  }
  node.isExpanded = true;
  return value;
}

function backup(node, value) {
  let n = node;
  while (n !== null) {
    n.visitCount++;
    n.valueSum += value;
    value = -value;
    n = n.parent;
  }
}

function selectLeaf(root) {
  let node = root;
  while (true) {
    node.ensureState();
    if (!node.isExpanded || node.state.isFinished()) break;
    node = node.bestChild(C_PUCT, FPU_REDUCTION);
  }
  return node;
}

async function runMCTS(state, numSims, evaluator, cancelToken, onProgress = null) {
  const c = clockContext,
    root = new MCTSNode(state);
  let checkpoint = null;
  function commit() {
    const finishStart = stamp();
    check(c);
    const p = pickFromVisits(root.children, 0);
    if (p)
      checkpoint = {
        action: p.action,
        at: stamp(),
        rootVisits: root.visitCount,
        simulations: c.simulations,
      };
    check(c);
    c.checkpoint = checkpoint;
    c.spans.push({ kind: 'finish', start: finishStart, end: stamp() });
    if (c.onComplete) c.onComplete(root);
  }
  try {
    check(c, true);
    const initVal = await expandNode(root, evaluator);
    check(c);
    backup(root, initVal);
    commit();
    c.rootFinished = stamp();
    await nativeControlDrain(); // common native IPC event drain; no artificial timer delay
    for (let i = 0; i < numSims; i++) {
      check(c, true);
      const begin = stamp(),
        leaf = selectLeaf(root);
      leaf.ensureState();
      check(c);
      let value;
      const t = terminalResult(leaf.state);
      if (t) value = t.value;
      else value = await expandNode(leaf, evaluator);
      check(c);
      backup(leaf, value);
      check(c);
      c.simulations++;
      commit();
      c.steps.push(stamp() - begin);
      await nativeControlDrain(); // common native IPC event drain; no artificial timer delay
    }
  } catch (e) {
    if (e.message !== 'guard') throw e;
    c.stopped = 'guard';
  }
  check(c);
  return root;
}

// Pick a child from the root's visit counts, matching Python
// MCTSAgent.get_policy + select_action (mcts.py): temperature 0 is argmax,
// above 0 samples proportional to visitCount^(1/T).
function pickFromVisits(children, temperature) {
  if (!children.length) return null;
  let best = children[0];
  for (const c of children) if (c.visitCount > best.visitCount) best = c;
  if (!(temperature > 0)) return best;
  const maxN = best.visitCount;
  if (maxN <= 0) return children[Math.floor(Math.random() * children.length)];

  // Dividing by maxN cancels in the normalisation below, but keeps
  // visitCount^(1/T) from overflowing to Infinity at low T (5000^100 does).
  const invT = 1 / temperature;
  const raw = children.map((c) => Math.pow(c.visitCount / maxN, invT));
  const total = raw.reduce((s, r) => s + r, 0);
  if (!(total > 0)) return best;
  let r = Math.random() * total;
  for (let i = 0; i < children.length; i++) {
    r -= raw[i];
    if (r <= 0) return children[i];
  }
  return best; // only reachable through float drift
}

async function selectAction(
  state,
  numSims,
  evaluator,
  cancelToken,
  onProgress = null,
  temperature = 0,
) {
  const root = await runMCTS(state, numSims, evaluator, cancelToken, onProgress);
  if (!root) return null;
  const pick = pickFromVisits(root.children, temperature);
  return pick ? pick.action : state.getLegalActions()[0] || null;
}

async function getPolicy(state, numSims, evaluator, cancelToken, onProgress = null) {
  const root = await runMCTS(state, numSims, evaluator, cancelToken, onProgress);
  if (!root) return null;
  const total = root.children.reduce((s, c) => s + c.visitCount, 0);
  const rootQ = root.qValue;
  const policy = root.children
    .map((c) => ({ action: c.action, prob: total > 0 ? c.visitCount / total : 0 }))
    .sort((a, b) => b.prob - a.prob);
  return { policy, rootQ };
}
