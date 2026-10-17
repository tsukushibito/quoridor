"""Finite static-teacher recipe and weighted metrics for the maintained trainer.

This module does not contain another optimizer/fit loop or source classifier.
"""

import copy
import math
import sys

import numpy as np


def recipe(train_rows, validation_rows, *, device, threads):
    """Materialize once from actual retained multiplicities, before fit outcomes."""
    from .common import DEFAULTS

    if any(type(n) is not int or n <= 0 for n in (train_rows, validation_rows)):
        raise ValueError("actual nonempty retained original T/V multiplicities required")
    cfg = copy.deepcopy(DEFAULTS)
    r, v = train_rows, validation_rows
    steps = math.ceil(32 * r / 4096)
    points = sorted({0, *[math.ceil(k * r / 4096) for k in range(1, 33)]})
    cfg["model"].update(
        architecture="distance_residual",
        distance_a=0.0,
        distance_b=0.0,
        transformer_width=32,
        hidden_width=32,
        dropout=0.0,
    )
    cfg["optimizer"].update(
        name="adam", lr=0.0003, weight_decay=0.0, momentum=0.0, betas=[0.9, 0.999], eps=1e-8
    )
    cfg["training"].update(
        steps=steps,
        batch_size=4096,
        seed=32442026101703,
        target="static_teacher",
        sampling="row",
        loss_weighting="row",
        scheduler="none",
        warmup_steps=min(1000, max(1, math.ceil(0.02 * steps))),
        reflection_probability=0.5,
        reflection_seed=32442026101704,
        supply_workers=0,
        device=device,
        threads=threads,
    )
    cfg["evaluation"].update(
        checkpoints=points,
        batch_size=4096,
        monitor="row",
        early_stopping_patience=4,
        early_stopping_unit="observation",
        min_delta=0.0001,
        min_delta_relative=0.001,
        diagnostic_rows=min(65536, r),
        diagnostic_checkpoints=[],
        full_train=False,
        full_train_checkpoints=[],
    )
    cfg["limits"].update(seconds=None, samples=32 * r + 33 * (2 * v + 2 * min(65536, r)))
    cfg["artifacts"].update(mode="native", save_scheduled=False, checkpoint_steps=[])
    return cfg


def validate_recipe(cfg, train_rows, validation_rows):
    expected = recipe(
        train_rows,
        validation_rows,
        device=cfg["training"]["device"],
        threads=cfg["training"]["threads"],
    )
    if cfg != expected:
        raise ValueError("static-teacher recipe differs from fixed real-R/V recipe")


def adequate_learning(initial_panel, observed_panel, parameter_changed):
    return bool(
        parameter_changed and initial_panel - observed_panel >= max(0.0001, 0.01 * initial_panel)
    )


class StaticMeasurements:
    """Same predictions produce row/class/stock/sign/zero/saturation statistics."""

    def __init__(self, pairs):
        self.pairs = pairs
        self.group_error = np.zeros(len(pairs), dtype=np.float64)
        self.group_weight = np.zeros(len(pairs), dtype=np.float64)
        self.stats = {}

    def add(self, pair, prediction, target, weight, stock):
        prediction = np.asarray(prediction, dtype=np.float32)
        target = np.asarray(target, dtype=np.float32)
        weight = np.asarray(weight, dtype=np.float64)
        if (
            prediction.shape != target.shape
            or weight.shape != target.shape
            or not np.isfinite(prediction).all()
            or not np.isfinite(target).all()
            or not np.isfinite(weight).all()
            or np.any(weight <= 0)
        ):
            raise ValueError("finite actual static prediction/target and positive weights")
        error = prediction.astype(np.float64) - target.astype(np.float64)
        np.add.at(self.group_error, pair, weight * error**2)
        np.add.at(self.group_weight, pair, weight)
        for name, mask in [
            ("all", np.ones(len(pair), dtype=bool)),
            ("stock16..20", (stock >= 16) & (stock <= 20)),
            ("stock8..15", (stock >= 8) & (stock <= 15)),
            ("stock1..7", (stock >= 1) & (stock <= 7)),
            ("stock0", stock == 0),
        ]:
            w = weight[mask]
            y = target[mask]
            p = prediction[mask]
            e = error[mask]
            s = self.stats.setdefault(
                name,
                dict(
                    rows=0.0,
                    sse=0.0,
                    absolute=0.0,
                    bias=0.0,
                    target_sum=0.0,
                    target_square_sum=0.0,
                    target_histogram10=[0.0] * 10,
                    sign_rows=0.0,
                    sign_correct=0.0,
                    target_zero_rows=0.0,
                    target_zero_abs=0.0,
                    target_saturated90=0.0,
                    target_saturated99=0.0,
                    predicted_saturated90=0.0,
                    predicted_saturated99=0.0,
                ),
            )
            for field, value in dict(
                rows=w.sum(),
                sse=np.dot(w, e**2),
                absolute=np.dot(w, abs(e)),
                bias=np.dot(w, e),
                target_sum=np.dot(w, y),
                target_square_sum=np.dot(w, y.astype(np.float64) ** 2),
                sign_rows=w[y != 0].sum(),
                sign_correct=w[p * y > 0].sum(),
                target_zero_rows=w[y == 0].sum(),
                target_zero_abs=np.dot(w[y == 0], abs(p[y == 0])),
                target_saturated90=w[abs(y) >= 0.9].sum(),
                target_saturated99=w[abs(y) >= 0.99].sum(),
                predicted_saturated90=w[abs(p) >= 0.9].sum(),
                predicted_saturated99=w[abs(p) >= 0.99].sum(),
            ).items():
                s[field] += float(value)
            histogram, _ = np.histogram(y, bins=np.linspace(-1.0, 1.0, 11), weights=w)
            s["target_histogram10"] = [
                previous + float(value)
                for previous, value in zip(s["target_histogram10"], histogram)
            ]

    def result(self):
        from .public_features import input_records

        stock = input_records(self.pairs["key"])["geometry"]["stocks"].sum(axis=1)
        out = {}
        for name, s in self.stats.items():
            n = s["rows"]
            selected = self.group_weight > 0
            if name != "all":
                lo, hi = {
                    "stock16..20": (16, 20),
                    "stock8..15": (8, 15),
                    "stock1..7": (1, 7),
                    "stock0": (0, 0),
                }[name]
                selected &= (stock >= lo) & (stock <= hi)
            report = {
                **s,
                "target_mse": s["sse"] / n if n else None,
                "target_mae": s["absolute"] / n if n else None,
                "target_mean": s["target_sum"] / n if n else None,
                "target_second_moment": s["target_square_sum"] / n if n else None,
                "target_histogram_edges": np.linspace(-1.0, 1.0, 11).tolist(),
                "input_classes": int(selected.sum()),
                "class_macro_mse": float(
                    np.mean(self.group_error[selected] / self.group_weight[selected])
                )
                if selected.any()
                else None,
                "decisive_sign_accuracy": s["sign_correct"] / s["sign_rows"]
                if s["sign_rows"]
                else None,
                "target_zero_mean_absolute_prediction": s["target_zero_abs"] / s["target_zero_rows"]
                if s["target_zero_rows"]
                else None,
            }
            for key in [
                "target_saturated90",
                "target_saturated99",
                "predicted_saturated90",
                "predicted_saturated99",
            ]:
                report[key + "_fraction"] = s[key] / n if n else None
            out[name] = report
        result = out.pop("all")
        result.update(
            stock_strata=out,
            weighting="original observation multiplicity, equal actual canonical/trueLR orientations",
            teacher_zero="static scalar zero; never a Draw0 outcome",
            independent_games="UNKNOWN",
            group_kind="exact trueLR input class",
        )
        return result


def prepare_common(cache, output, config_path):
    """One actual constructor/export, no forward; caller owns normal resources."""
    from pathlib import Path
    from .train import configure_framework, build_model, export, write, sha
    from .cache import load
    from .common import resolve_config

    cfg = resolve_config(config_path)
    corpus = load(cache)
    try:
        validate_recipe(cfg, corpus.counts["train"], corpus.counts["validation"])
        statistics = corpus.statistics()
        init = copy.deepcopy(cfg)
        init["training"].update(seed=32442026101701, device="cpu")
        configure_framework(init)
        model = build_model(init["model"], statistics)
        output = Path(output)
        output.mkdir(exist_ok=False)
        export(model, init, statistics, {"a": 0.0, "b": 0.0}, output / "initial-model")
        write(output / "scale.json", statistics)
        corpus.verify_binding()
        from .public_static_prepare import file_ref

        result = dict(
            schema="quoridor-static-common-initial-v1",
            initial_weights=file_ref(output / "initial-model/weights.f32"),
            input_classes=corpus.input_ref,
            initial_weights_sha=sha(output / "initial-model/weights.f32"),
            initializer_seed=32442026101701,
            model_forwards=0,
            scale=dict(
                path=str((output / "scale.json").resolve()), sha256=sha(output / "scale.json")
            ),
            initializer=init,
            normalizer="T-only original multiplicity, correctLR distance invariant",
        )
        write(output / "result.json", result)
        return result
    finally:
        corpus.close(primary_error=sys.exception())


def prepare_fits(config):
    """Bind actual completed labels and one fresh initializer to normal train."""
    import json
    from pathlib import Path
    from .common import bound_file_bytes
    from .cache import load
    from .public_static_prepare import file_ref
    from .snapshot import write_json

    bank_ref = config["teacher_values"]
    bank = json.loads(bound_file_bytes(bank_ref, 131072))
    if bank["schema"] != "quoridor-public-static-teacher-values-v1" or bank["status"] != "COMPLETE":
        raise ValueError("actual completed two-teacher bank required")
    input_ref = bank["input_classes"]
    inputs = json.loads(bound_file_bytes(input_ref, 131072))
    if inputs["status"] != "COMPLETE":
        raise ValueError("actual complete same input bank required")
    r, v = inputs["counts"]["train"], inputs["counts"]["validation"]
    output = Path(config["output"])
    output.mkdir(exist_ok=False)
    marker = output / "INCOMPLETE"
    marker.write_text("fit preparation owns partial controls; no implicit retry\n")
    cfg = recipe(r, v, device=config["device"], threads=config["threads"])
    fit_config = output / "fit-config.json"
    write_json(fit_config, cfg)
    caches = {}
    for teacher in ("S", "C"):
        cache = output / ("cache-" + teacher)
        cache.mkdir()
        write_json(
            cache / "cache.json",
            dict(
                schema="quoridor-public-static-teacher-v1",
                input_classes=input_ref,
                teacher_values=bank_ref,
                teacher=teacher,
            ),
        )
        caches[teacher] = cache
    common_directory = output / "common-initial"
    common = prepare_common(caches["S"], common_directory, fit_config)
    common_ref = file_ref(common_directory / "result.json")
    arms = {}
    for teacher in ("S", "C"):
        corpus = load(caches[teacher])
        try:
            if corpus.input_ref != input_ref or corpus.counts != {"train": r, "validation": v}:
                raise ValueError("same retained multiplicity and shared partition")
            # This is a descriptive T-only constant. It is not a target transform.
            indices = np.arange(r, dtype=np.int64)
            constant = float(np.mean(corpus.labels[indices, 0], dtype=np.float64))
            statistics = corpus.statistics()
            scale = json.loads(bound_file_bytes(file_ref(common["scale"]["path"]), 65536))
            if statistics != scale:
                raise ValueError("teacher-independent T-only scale differs")
            constant_path = output / ("constant-" + teacher + ".json")
            write_json(
                constant_path,
                dict(
                    row_mean_constant=constant,
                    partition="train",
                    teacher=teacher,
                    original_observations=r,
                ),
            )
            binding = dict(
                cache_manifest_sha=corpus.binding["dataset_sha"],
                scale_artifact=common["scale"]["path"],
                scale_artifact_sha=common["scale"]["sha256"],
                constant_artifact=str(constant_path),
                constant_artifact_sha=file_ref(constant_path)["sha256"],
                fit_config_sha=file_ref(fit_config)["sha256"],
                common_initial=common_ref,
                initial_weights=common["initial_weights"],
                initial_weights_sha=common["initial_weights_sha"],
            )
            path = output / ("input-binding-" + teacher + ".json")
            write_json(path, binding)
            corpus.verify_binding()
            arms[teacher] = dict(
                cache=str(caches[teacher]),
                input_binding=file_ref(path),
                config=file_ref(fit_config),
                original_train=r,
                original_validation=v,
                fit_not_entered=True,
            )
        finally:
            corpus.close(primary_error=sys.exception())
    bound_file_bytes(bank_ref, 131072)
    bound_file_bytes(input_ref, 131072)
    result = dict(
        schema="quoridor-static-paired-fit-controls-v1",
        input_classes=input_ref,
        teacher_values=bank_ref,
        common_initial=common_ref,
        arms=arms,
        prepare_head_rows=0,
        initial_model_reused=True,
        scope="normal train controls only; no fit/numerical success inferred",
    )
    write_json(output / "result.json", result)
    marker.unlink()
    return dict(result=file_ref(output / "result.json"), fit_entered=False)


def main():
    import argparse
    import json
    from pathlib import Path
    from .cycle_process import cancellation_signals

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with cancellation_signals():
        result = prepare_fits(json.loads(Path(args.config).read_bytes()))
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
