"""One bounded native generation→train→freeze→test→native arena cycle."""

import argparse
import json
import math
import os
import signal
import subprocess
import time
from pathlib import Path


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def execute(command, log, deadline, cpu_core=None):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise RuntimeError("cycle deadline before child launch")
    with Path(log).open("x") as stream:
        child = subprocess.Popen(
            command,
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            preexec_fn=(lambda: os.sched_setaffinity(0, {cpu_core}))
            if cpu_core is not None
            else None,
        )
        try:
            code = child.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            raise RuntimeError("cycle child deadline: " + command[0])
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=3)
    if code != 0:
        raise RuntimeError("cycle child failed: " + str(command) + ": " + str(code))


def cycle(config_path, runner):
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text())
    settings = config.get("cycle")
    if not settings:
        raise ValueError("cycle settings required")
    output = Path(config["output"]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write(output / "cycle-config.json", config)
    deadline = time.monotonic() + config.get("wall_seconds", 300)
    unix_deadline = config.get("deadline_unix_ms", 0)
    if unix_deadline:
        deadline = min(deadline, time.monotonic() + unix_deadline / 1000 - time.time())
    state = {
        "schema": "quoridor-cycle-v1",
        "status": "running",
        "stages": [],
        "adopted": False,
    }
    write(output / "cycle-state.json", state)
    environment_python = os.path.abspath(settings["python"])
    try:
        generation = {**config, "output": str(output / "generation"), "cycle": None}
        gen_path = output / "generation-config.json"
        write(gen_path, generation)
        execute(
            [str(runner), "selfplay", "--config", str(gen_path)],
            output / "generation.log",
            deadline,
        )
        generated = json.loads((output / "generation" / "result.json").read_text())
        state["stages"].append(
            {
                "name": "generation",
                "rows": generated["rows"],
                "wall_seconds": generated["wall_seconds"],
            }
        )
        if not generated["rows"] or any(o["status"] == "unknown" for o in generated["outcomes"]):
            raise RuntimeError("generation must have terminal-qualified data")
        dataset = output / "generation" / "dataset"
        cache = output / "train-cache"
        execute(
            [
                str(runner),
                "dataset",
                "cache",
                "--input",
                str(dataset),
                "--output",
                str(cache),
            ],
            output / "train-cache.log",
            deadline,
        )
        train_command = [
            environment_python,
            "-m",
            "quoridor_training.train",
            "train",
            "--cache",
            str(cache),
            "--output",
            str(output / "learning"),
        ]
        if settings.get("training_config"):
            train_command += [
                "--config",
                str(Path(settings["training_config"]).resolve()),
            ]
        if settings.get("steps"):
            train_command += ["--steps", str(settings["steps"])]
        execute(
            train_command,
            output / "train.log",
            deadline,
            (config.get("cpu_cores") or sorted(os.sched_getaffinity(0)))[0],
        )
        freeze = json.loads((output / "learning" / "freeze.json").read_text())
        state["stages"].append({"name": "training", **freeze})
        write(output / "cycle-state.json", state)
        test_cache = output / "test-cache"
        execute(
            [
                str(runner),
                "dataset",
                "cache",
                "--input",
                str(dataset),
                "--output",
                str(test_cache),
                "--allow-test",
            ],
            output / "test-cache.log",
            deadline,
        )
        execute(
            [
                environment_python,
                "-m",
                "quoridor_training.train",
                "test",
                "--cache",
                str(test_cache),
                "--training",
                str(output / "learning"),
                "--output",
                str(output / "test"),
            ],
            output / "test.log",
            deadline,
            (config.get("cpu_cores") or sorted(os.sched_getaffinity(0)))[0],
        )
        state["stages"].append({"name": "test", "result": "test/result.json"})
        model_path = output / "learning" / "best-model" / "manifest.json"
        fit = json.loads((output / "learning" / "data.json").read_text())["distance_fit"]
        engines = [
            {
                "kind": "nnue",
                "model": str(model_path),
                "depth": 64,
                "max_nodes": 1_000_000,
                "time_ms": settings.get("arena_time_ms") or 100,
                "simd": True,
            },
            {
                "kind": "distance",
                "distance_a": fit["a"],
                "distance_b": fit["b"],
                "depth": 64,
                "max_nodes": 1_000_000,
                "time_ms": settings.get("arena_time_ms") or 100,
                "simd": True,
            },
        ]
        arena = {
            **config,
            "run_id": config["run_id"] + "-arena",
            "output": str(output / "arena"),
            "games": settings.get("arena_games") or 4,
            "engines": engines,
            "cycle": None,
            "inference": None,
            "seed": config.get("seed", 19080311) + 1,
            "train_games": 0,
            "validation_games": 0,
            "openings": [],
            "wall_seconds": max(1.0, deadline - time.monotonic()),
        }
        if arena["games"] % 2:
            raise ValueError("arena game count must be even")
        arena_path = output / "arena-config.json"
        write(arena_path, arena)
        execute(
            [str(runner), "arena", "--config", str(arena_path)],
            output / "arena.log",
            deadline,
        )
        result = json.loads((output / "arena" / "result.json").read_text())
        state["stages"].append(
            {"name": "arena", "score": result["score"], "games": result["planned"]}
        )
        # Fixed paired Hoeffding bound. A tiny connection diagnostic can never
        # silently promote a model merely because it happened to win two games.
        outcomes = result["outcomes"]
        unknown = sum(o["status"] == "unknown" for o in outcomes)
        pairs = len(outcomes) // 2
        lower = (
            None
            if not pairs or unknown
            else result["score"] - math.sqrt(math.log(20) / (2 * pairs))
        )
        state["adopted"] = lower is not None and lower > 0.5 + settings.get("adoption_margin", 0)
        state["adoption"] = {
            "rule": "fixed-pair one-sided95 Hoeffding",
            "lower": lower,
            "threshold": 0.5 + settings.get("adoption_margin", 0),
            "unknown": unknown,
            "default_weights_changed": False,
        }
        state["status"] = "complete"
    except BaseException as error:
        state["status"] = "failed"
        state["error"] = str(error)
        write(output / "cycle-state.json", state)
        raise
    write(output / "cycle-state.json", state)
    return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--runner", required=True)
    args = parser.parse_args()
    print(json.dumps(cycle(args.config, Path(args.runner).resolve())))


if __name__ == "__main__":
    main()
