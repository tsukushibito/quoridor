"""Alternating held-process CPU comparison; leaves production/source assets intact."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Held:
    def __init__(self, command, log):
        self.log = log.open("w")
        self.p = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log, text=True
        )
        self.ready = self.read()
        if not self.ready.get("ready"):
            raise RuntimeError("missing readiness receipt")

    def read(self):
        if not select.select([self.p.stdout], [], [], 90)[0]:
            raise TimeoutError("benchmark reply deadline")
        line = self.p.stdout.readline()
        if not line:
            raise RuntimeError(f"benchmark process exited: {self.p.poll()}")
        return json.loads(line)

    def ask(self, request):
        self.p.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        self.p.stdin.flush()
        return self.read()

    def close(self):
        self.p.stdin.close()
        try:
            code = self.p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.p.terminate()
            code = self.p.wait(timeout=5)
        self.log.close()
        return code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    model = (
        ROOT
        / ".artifacts/rust-migration/data-runner/gpu-cycle-r2/learning/best-model/manifest.json"
    )
    old_config = json.loads(
        (ROOT / ".artifacts/rust-migration/data-runner/mcts-ort-r1/config.json").read_text()
    )
    inf = old_config["inference"]
    python = "/home/vscode/.cache/inference/envs/quoridor-training/bin/python"
    binary = ROOT / ".artifacts/rust-migration/target/release/examples/node_comparison"
    node_source = ROOT / "tools/ai-native-node-benchmark/node.cjs"
    weights = model.parent / json.loads(model.read_text())["weights"]
    plan = {
        "schema": "native-node-cpu-benchmark-v1",
        "fixtures": [[], [13], [107]],
        "fixture_names": ["initial-p1", "pawn-step-p2", "horizontal-wall-p2"],
        "nnue_iterations": 5000,
        "nnue_depth": 2,
        "nnue_warm": 1,
        "nnue_steady": 5,
        "mcts_k": 800,
        "mcts_warm": 1,
        "mcts_steady": 3,
        "core": 2,
        "sequential_engines": True,
        "order": "alternates each round, rotates scalar/SIMD/Node within NNUE rounds",
        "model": str(model),
        "model_manifest_sha": sha(model),
        "weights_sha": sha(weights),
        "inference": inf,
        "binary_sha": sha(binary),
        "node_source_sha": sha(node_source),
        "node_version": subprocess.check_output(["node", "--version"], text=True).strip(),
        "host_affinity": sorted(os.sched_getaffinity(0)),
        "start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (out / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    held = {}
    raw = []
    codes = {}
    began = time.monotonic()
    try:
        held["rust"] = Held(
            [str(binary), str(model), inf["model"], inf["library"], inf["model_sha"]],
            out / "rust-stderr.log",
        )
        held["node"] = Held(
            ["taskset", "-c", "2", "node", str(node_source), str(model), inf["model"], python],
            out / "node-stderr.log",
        )
        (out / "readiness.json").write_text(
            json.dumps({k: v.ready for k, v in held.items()}, indent=2) + "\n"
        )
        with (out / "raw.jsonl").open("w") as journal:
            for operation in ["eval", "search", "mcts"]:
                for fixture, prefix in enumerate(plan["fixtures"]):
                    repeats = 4 if operation == "mcts" else 6
                    variants = (
                        ["node", "rust-scalar"]
                        if operation == "mcts"
                        else ["node", "rust-scalar", "rust-simd"]
                    )
                    for repeat in range(repeats):
                        order = (
                            variants[repeat % len(variants) :] + variants[: repeat % len(variants)]
                        )
                        for variant in order:
                            request = {
                                "op": operation,
                                "prefix": prefix,
                                "iterations": 5000,
                                "depth": 2,
                                "k": 800,
                                "simd": variant == "rust-simd",
                            }
                            target = "node" if variant == "node" else "rust"
                            measured = held[target].ask(request)
                            record = {
                                "operation": operation,
                                "fixture": fixture,
                                "variant": variant,
                                "repeat": repeat,
                                "warm": repeat == 0,
                                **measured,
                            }
                            raw.append(record)
                            journal.write(json.dumps(record, separators=(",", ":")) + "\n")
                            journal.flush()
                        print(f"{operation} fixture={fixture} repeat={repeat} complete", flush=True)
                        if time.monotonic() - began > 600:
                            raise TimeoutError("whole benchmark exceeded 600 seconds")
    finally:
        for k, p in held.items():
            codes[k] = p.close()
        (out / "stop.json").write_text(
            json.dumps(
                {
                    "exit_codes": codes,
                    "all_children_waited": True,
                    "wall_seconds": time.monotonic() - began,
                },
                indent=2,
            )
            + "\n"
        )
    if any(codes.values()):
        raise RuntimeError("benchmark subprocess exit failure")
    summary = []
    parity = []
    for op in ["eval", "search", "mcts"]:
        for f in range(3):
            records = [x for x in raw if x["operation"] == op and x["fixture"] == f]
            node = [x for x in records if x["variant"] == "node"]
            for variant in sorted({x["variant"] for x in records} - {"node"}):
                native = [x for x in records if x["variant"] == variant]
                ns = [x["seconds"] for x in node if not x["warm"]]
                rs = [x["seconds"] for x in native if not x["warm"]]
                a, b = node[-1], native[-1]
                check = {
                    "op": op,
                    "fixture": f,
                    "variant": variant,
                    "value_max_abs": max(abs(x["value"] - a["value"]) for x in native),
                }
                if op != "eval":
                    check["action_equal"] = all(x["action"] == a["action"] for x in native)
                    check["action_node"] = a["action"]
                    check["action_rust"] = b["action"]
                if op == "mcts":
                    check["root_visits_equal"] = a["root_visits"] == b["root_visits"] == 800
                    check["nn_calls_equal"] = a["nn_calls"] == b["nn_calls"]
                    check["edge_visits_equal"] = [x[:2] for x in a["edges"]] == [
                        x[:2] for x in b["edges"]
                    ]
                    check["edge_value_max_abs"] = max(
                        abs(x[2] - y[2]) for x, y in zip(a["edges"], b["edges"], strict=True)
                    )
                parity.append(check)
                summary.append(
                    {
                        "operation": op,
                        "fixture": plan["fixture_names"][f],
                        "variant": variant,
                        "node_median_seconds": statistics.median(ns),
                        "rust_median_seconds": statistics.median(rs),
                        "node_min_max": [min(ns), max(ns)],
                        "rust_min_max": [min(rs), max(rs)],
                        "node_over_rust_ratio": statistics.median(ns) / statistics.median(rs),
                        "node_nodes": a.get("nodes"),
                        "rust_nodes": b.get("nodes"),
                        "node_evaluations": a.get("evaluations"),
                        "rust_evaluations": b.get("evaluations"),
                    }
                )
    (out / "summary.json").write_text(
        json.dumps({"summaries": summary, "parity": parity}, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
