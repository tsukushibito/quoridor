"""One bounded invocation of the maintained trainer, not an alternate learner."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

os.environ["ORT_DISABLE_TELEMETRY"] = "1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", required=True)
    path = Path(parser.parse_args().registration)
    reg = json.loads(path.read_text())
    if reg["task"] != "native-outcome-z-fit-298-v1":
        raise ValueError("unregistered fit task")
    for source, digest in reg["input_SHA"].items():
        if sha(source) != digest:
            raise ValueError("registered source/input changed: " + source)
    output = Path(reg["checkpoint_output"])
    if output.exists() or not output.parent.is_dir():
        raise ValueError("output parent/collision preflight before framework import")
    from quoridor_training.common import resolve_config
    from quoridor_training.train import train

    cfg = resolve_config(reg["config"])
    if (
        cfg["model"]["architecture"] != "distance_residual"
        or cfg["training"]["target"] != "z"
        or cfg["training"]["sampling"] != "game"
        or cfg["artifacts"]["mode"] != "native"
        or cfg["evaluation"]["checkpoints"] != reg["points"]
    ):
        raise ValueError("registered target/model/sampler/artifact/schedule")
    freeze = train(reg["cache"], output, reg["config"], scale_path=reg["scale"])
    curve = json.loads((output / "curves.json").read_text())
    if freeze["samples"] != reg["sample_upper"] or [r["step"] for r in curve] != reg["points"]:
        raise ValueError("actual fit/evaluation sample or step denominator differs")
    if freeze["initial_weights_sha"] != reg["common_initial_SHA"]:
        raise ValueError("fixed common zerohead initial tensor SHA differs")
    sample = json.loads((output / "sampling.json").read_text())
    if sample["seen"] != 1000064 or sum(sample["family_counts"].values()) != 1000064:
        raise ValueError("actual family sampling ledger differs")
    result = {
        "task": reg["task"],
        "schema": "native-z-fit-result-v1",
        "status": "FINITE_FIT_COMPLETED",
        "UTC": datetime.now(timezone.utc).isoformat(),
        "registration_SHA": sha(path),
        "total_NN": freeze["samples"],
        "processed": freeze["samples"] + 2 * reg["raw_rows"],
        "training_seen": sample["seen"],
        "freeze": freeze,
        "checkpoint_root": str(output),
        "old_corpus_selection_not_blind": True,
        "new_future_labels_opened": False,
        "ONNX_forward": 0,
        "extra_model_forward": 0,
        "sameforward_scalars_and_scheduledweights": True,
    }
    Path(reg["expected_output"]).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"task": reg["task"], "status": result["status"], "NN": result["total_NN"]}))


if __name__ == "__main__":
    main()
