"""Deterministic normalized SGD on explicit outcome/teacher JSONL; no generation."""

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from . import data, pattern


def loss(parameters, rows):
    if not np.isfinite(parameters).all():
        raise ValueError("nonfinite loss parameter STOP")
    squared = [
        (
            max(-6400.0, min(6400.0, sum(parameters[i] * v for i, v in row.features.items())))
            - row.target
        )
        ** 2
        for row in rows
    ]
    result = float(np.mean(squared))
    if not np.isfinite(result):
        raise ValueError("nonfinite loss STOP")
    return result


def quantized_loss(model, rows):
    result = float(
        np.mean([(pattern.evaluate(model, row.state) - row.target) ** 2 for row in rows])
    )
    if not np.isfinite(result):
        raise ValueError("nonfinite quantized loss STOP")
    return result


def sgd_step(parameters, sparse, target, learning_rate=0.1, ridge=0.001):
    prediction = sum(parameters[i] * v for i, v in sparse.items())
    norm = max(1, sum(value * value for value in sparse.values()))
    step = learning_rate / norm
    parameters *= 1 - step * ridge
    error = target - prediction
    for index, value in sparse.items():
        parameters[index] += step * error * value
    if not np.isfinite(parameters).all():
        raise ValueError("nonfinite SGD parameter STOP")


def fit(dataset, config):
    """Validation selects best quantized/clamped loss; only train rows update."""
    data.validate_config(config)
    data.validate_fit_splits(dataset, config)
    deadline = time.monotonic() + config["maxTrainSeconds"]
    rng = np.random.Generator(np.random.PCG64(config["seed"]))
    parameters = np.zeros(pattern.PARAMETERS, dtype=np.float64)
    best = parameters.copy()
    best_model = pattern.quantize(best)
    best_loss = quantized_loss(best_model, dataset.validation)
    best_epoch, stale = 0, 0
    curves = [
        dict(
            epoch=0,
            trainMSE=loss(parameters, dataset.train),
            validationMSE=loss(parameters, dataset.validation),
            quantizedValidationMSE=best_loss,
        )
    ]
    stop = "maxEpochs"
    for epoch in range(1, config["maxEpochs"] + 1):
        for index in rng.permutation(len(dataset.train)):
            if time.monotonic() >= deadline:
                raise ValueError("configured training deadline STOP (no completed fit exported)")
            row = dataset.train[index]
            sgd_step(parameters, row.features, row.target, config["learningRate"], config["ridge"])
        model = pattern.quantize(parameters)
        validation = quantized_loss(model, dataset.validation)
        curves.append(
            dict(
                epoch=epoch,
                trainMSE=loss(parameters, dataset.train),
                validationMSE=loss(parameters, dataset.validation),
                quantizedValidationMSE=validation,
            )
        )
        if validation < best_loss - 1e-9:
            best, best_model, best_loss, best_epoch = parameters.copy(), model, validation, epoch
            stale = 0
        else:
            stale += 1
        if stale >= config["patience"]:
            stop = "validationPlateau"
            break
    return (
        best,
        best_model,
        curves,
        dict(
            bestEpoch=best_epoch,
            completedEpoch=curves[-1]["epoch"],
            stop=stop,
            bestQuantizedValidationMSE=best_loss,
        ),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    config_bytes = data.bounded_bytes(args.config, 256 * 1024)
    config = data.validate_config(pattern.strict_json(config_bytes))
    dataset = data.load_dataset(args.data, config)
    # An existing run is never overwritten; two checkpoints total, no epoch snapshots.
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        started = time.monotonic()
        best, model, curves, result = fit(dataset, config)
        fp_path = args.output / "best-fp.npy"
        np.save(fp_path, best, allow_pickle=False)
        model_path = args.output / "best-pattern.json"
        model_path.write_text(json.dumps(model, separators=(",", ":"), allow_nan=False) + "\n")
        (args.output / "curves.json").write_text(
            json.dumps(curves, indent=2, allow_nan=False) + "\n"
        )
        source = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__), Path(data.__file__), Path(pattern.__file__)]
        }
        metadata = dict(
            version=1,
            schema="pattern-v1",
            schemaSHA256=hashlib.sha256(
                json.dumps(
                    pattern.schema([]), sort_keys=True, separators=(",", ":"), allow_nan=False
                ).encode()
            ).hexdigest(),
            config=config,
            configSHA256=hashlib.sha256(config_bytes).hexdigest(),
            dataSHA256=dataset.sha256,
            sourceSHA256=source,
            numpyVersion=np.__version__,
            parameterCount=pattern.PARAMETERS,
            trainRows=len(dataset.train),
            validationRows=len(dataset.validation),
            **label_metadata(dataset, config),
            elapsedSeconds=time.monotonic() - started,
            checkpoints={
                p.name: dict(
                    bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()
                )
                for p in [fp_path, model_path]
            },
            **result,
        )
        (args.output / "metadata.json").write_text(
            json.dumps(metadata, indent=2, allow_nan=False) + "\n"
        )
        print(json.dumps(result, allow_nan=False))
    except Exception as error:
        (args.output / "failure.json").write_text(
            json.dumps(dict(error=str(error), type=type(error).__name__), indent=2) + "\n"
        )
        raise


def label_metadata(dataset, config):
    """Label meaning follows declared kind, never run ID, depth or probability."""
    result = dict(
        labelProvenance=dict(labelKind=config["labelKind"], labelSource=config["labelSource"]),
        familyCoverage=dataset.coverage,
    )
    if config["labelKind"] == "gameOutcome":
        result["inferredFinalBlackMinusWhite"] = dataset.inferred_final_black_minus_white
        result["terminalVerification"] = (
            "cross-row STM consistency only; actual rules/reached termination evidence belongs to generating Rust service"
        )
    else:
        result["labelProvenance"]["teacherId"] = config["teacher"]["id"]
        result["teacherVerification"] = (
            "caller-fixed source/weights/adapter/args in config; preserved reported bounds/bool-or-null proof; engine empty-award estimates are not our exact actual-disc solver truth"
        )
        rows = dataset.train + dataset.validation
        result["teacherMetadataAvailability"] = {
            key: dict(
                reported=sum(row.teacher[key] not in (None, "UNKNOWN") for row in rows),
                unknown=sum(row.teacher[key] in (None, "UNKNOWN") for row in rows),
            )
            for key in sorted(data.TEACHER_OPTIONAL)
        }
    return result


if __name__ == "__main__":
    main()
