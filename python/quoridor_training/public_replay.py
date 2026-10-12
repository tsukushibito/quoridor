"""Outcome replay through maintained model, compact codec and export primitives.

This module is selected by the normal trainer fit entry. It owns full batches,
source shares and preselected LAST measurements; it does not qualify models or
open detailed histories, sealed data, a new environment or a second job lease.
"""

import copy
import csv
import hashlib
import json
from pathlib import Path
import random
import time

from .common import (
    BEST43_WEIGHTS,
    bound_file_bytes,
    common_cache_config,
    resolve_config,
    warmstart_model_inputs,
)

STUDY = "public-replay-v1"
POINTS = list(range(0, 201, 20))
PUBLIC_ROWS = {"train": 8413949, "validation": 419150}
INDEX_SEEDS = {"train": 37120261013, "validation": 37120261014}
PUBLIC_SEED = 37120261012
FORWARD_LIMIT = 2000000
PLANNED_PAIR_FORWARDS = 1649944


def mixed_batch(added, public, added_indices, public_indices, reflection_mask):
    """One STM input/label stream, with split isolation before any model call."""
    import numpy as np

    ai, pi = np.asarray(added_indices), np.asarray(public_indices)
    mask = np.asarray(reflection_mask)
    if (
        ai.ndim != 1
        or pi.ndim != 1
        or ai.dtype.kind not in "iu"
        or pi.dtype.kind not in "iu"
        or len(ai) not in (32, 64)
        or len(ai) + len(pi) != 64
        or mask.dtype != np.dtype(bool)
        or mask.shape != (64,)
        or np.any(ai < 0)
        or np.any(ai >= added.row_count)
    ):
        raise ValueError("selected full batch64 source shares/reflection mask required")
    if np.any(added.splits[ai] != 0) or not added.eligible[ai].all():
        raise ValueError("added training excludes V and ineligible rows")
    x, d, targets = added.batch(ai, mask[: len(ai)])
    y = targets[:, 1]
    if len(pi):
        px, pd, py = public.batch("train", pi, mask[len(ai) :], training=True)
        x, d, y = np.concatenate((x, px)), np.concatenate((d, pd)), np.concatenate((y, py))
    if (
        x.shape != (64, 2, 312)
        or d.shape != (64, 2)
        or y.shape != (64,)
        or x.dtype != np.float32
        or d.dtype != np.float32
        or y.dtype != np.float32
        or not np.isfinite(x).all()
        or not np.isfinite(d).all()
        or not np.isfinite(y).all()
        or not np.isin(y, (-1, 0, 1)).all()
    ):
        raise ValueError("finite full mixed QF1/STM/outcome batch64 required")
    return x, d, y


def mixed_row_loss(predictions, targets):
    """Average all 64 outcome losses once, regardless of source membership."""
    import torch

    if (
        predictions.shape != (64,)
        or targets.shape != (64,)
        or (predictions.dtype != torch.float32 or targets.dtype != torch.float32)
    ):
        raise ValueError("one FP32 64-row prediction/target objective required")
    return torch.mean((predictions - targets) ** 2)


def frozen_diagnostics():
    """Indices only: no corpus, label, framework or model is consulted."""
    return {
        "schema": "quoridor-public-replay-diagnostics-v1",
        "population": PUBLIC_ROWS,
        "seeds": INDEX_SEEDS,
        "algorithm": "Python random.Random.sample, without replacement",
        "indices": {
            name: random.Random(INDEX_SEEDS[name]).sample(range(count), 8192)
            for name, count in PUBLIC_ROWS.items()
        },
    }


def admit(cache, config_path, input_binding, cfg):
    """Join current selected plan/configs before frameworks, arrays or outputs."""
    if config_path is None or input_binding is None:
        raise ValueError("public replay needs the normal selected fit binding")
    expected = json.loads(Path(input_binding).read_bytes())
    plan = json.loads(bound_file_bytes(expected["selected_plan"], 131072))
    study = plan["public_replay_study"]
    if study["issue"] != "quoridor-4lc.371" or study["scientific_entry"] is not True:
        raise ValueError("current human-selected public replay plan required")
    if resolve_config(config_path) != cfg:
        raise ValueError("current normalized fit config/path correspondence")
    normalized = copy.deepcopy(cfg)
    arm = normalized["experiment"]["condition"]
    normalized["experiment"]["condition"] = None
    if (
        arm not in ("added_only", "replay")
        or normalized != study["common_learner_settings"]
        or cfg["experiment"]["study"] != STUDY
        or cfg["training"]["target"] != "z"
        or cfg["training"]["steps"] != 200
        or cfg["training"]["batch_size"] != 64
        or cfg["training"]["seed"] != 36220261011
        or cfg["training"]["reflection_seed"] != 36220261012
        or cfg["training"]["reflection_probability"] != 0.5
        or cfg["training"]["warmup_steps"] != 20
        or cfg["training"]["threads"] != 1
        or cfg["training"]["device"] != "cpu"
        or cfg["training"]["supply_workers"] != 0
        or cfg["optimizer"]
        != {
            "name": "adam",
            "lr": 0.001,
            "weight_decay": 0.0,
            "momentum": 0.0,
            "betas": [0.9, 0.999],
            "eps": 1e-8,
        }
        or cfg["evaluation"]["checkpoints"] != POINTS
        or cfg["evaluation"]["early_stopping_patience"] != 0
        or cfg["limits"]["samples"] != FORWARD_LIMIT
        or cfg["limits"]["seconds"] is not None
        or study["public_sampling_seed"] != PUBLIC_SEED
        or study["logical_forward_upper"] != FORWARD_LIMIT
        or study["planned_pair_forwards"] != PLANNED_PAIR_FORWARDS
        or study["comparison_checkpoint"] != "LAST200"
        or study["full_opened_validation"] != {"initial": "once_added_only", "last": "each"}
    ):
        raise ValueError("selected public replay recipe/counts differ")
    refs = expected["paired_fit_configs"]
    if refs != study["paired_fit_configs"] or len(refs) != 2:
        raise ValueError("selected paired fit configs differ")
    selected = hashlib.sha256(Path(config_path).read_bytes()).hexdigest()
    arms = []
    for ref in refs:
        recipe = resolve_config(json.loads(bound_file_bytes(ref, 16384)))
        arms.append(recipe["experiment"].pop("condition"))
        common = copy.deepcopy(normalized)
        common["experiment"].pop("condition")
        if recipe != common:
            raise ValueError("both normalized fit recipes must match selected settings")
    if arms != ["added_only", "replay"] or selected not in {r["sha256"] for r in refs}:
        raise ValueError("exact current added-only/replay selected config required")
    for field in (
        "public_membership",
        "public_acceptance",
        "added_membership",
        "diagnostic_indices",
    ):
        if expected[field] != study[field]:
            raise ValueError("selected input membership differs: " + field)
    public = json.loads(bound_file_bytes(expected["public_membership"], 65536))
    acceptance = json.loads(bound_file_bytes(expected["public_acceptance"], 16384))
    if (
        acceptance["issue"] != "quoridor-4lc.370"
        or acceptance["status"] != "ACCEPTED_FINITE_SAVED_PUBLIC_CORRESPONDENCE"
        or acceptance["accepted_observations"]["sealed_files_opened"] != []
        or acceptance["public_membership"] != expected["public_membership"]
        or acceptance["query_membership"] != expected["added_membership"]
    ):
        raise ValueError("accepted public/added lineage differs")
    for name, count in PUBLIC_ROWS.items():
        descriptors = [p for p in public["partitions"] if p["name"] == name]
        if len(descriptors) != 1 or descriptors[0]["rows"] != count:
            raise ValueError("selected public T/opened-V population")
    diagnostics = json.loads(bound_file_bytes(expected["diagnostic_indices"], 262144))
    if diagnostics != frozen_diagnostics():
        raise ValueError("diagnostic indices must be selected without outcomes")
    added = json.loads(bound_file_bytes(expected["added_membership"], 65536))
    if Path(expected["added_membership"]["path"]) != Path(cache) / "cache.json":
        raise ValueError("same selected added compact cache path required")
    common_cache_config(added, cfg["experiment"], plan=plan)
    if added["rows"] != 341 or added["common_corpus"]["common_eligible_by_split"] != {
        "train": 217,
        "validation": 76,
    }:
        raise ValueError("same literal common eligibility and partition required")
    prior = expected["qualification_forward_rows"]
    if type(prior) is not int or not 0 <= prior <= FORWARD_LIMIT - PLANNED_PAIR_FORWARDS:
        raise ValueError("aggregate affected qualification forward budget")
    initial = None
    if arm == "replay":
        manifest_ref = expected["prior_fit_manifest"]
        manifest = json.loads(bound_file_bytes(manifest_ref, 1048576))
        if (
            Path(manifest_ref["path"]).with_name("INCOMPLETE").exists()
            or manifest["status"] != "PASS"
            or manifest["cleanup_complete"] is not True
            or manifest["remaining"] != []
            or manifest["primary"] is not None
            or manifest["secondary"] != []
            or expected["prior_fit_result"] not in manifest["data"]["files"]
        ):
            raise ValueError("first arm actual authoritative STOP/cleanup required")
        prior_experiment = json.loads(bound_file_bytes(manifest["experiment"], 1048576))
        if (
            prior_experiment["phase"] != "fit"
            or prior_experiment["config"] != refs[0]
            or prior_experiment["canonical_plan_sha256"] != expected["selected_plan"]["sha256"]
            or manifest["data"]["public_replay"]["arm"] != "added_only"
            or manifest["data"]["public_replay"]["forward_rows"] != 1034547
        ):
            raise ValueError("actual original selected first arm Experiment/result required")
        initial = json.loads(bound_file_bytes(expected["prior_fit_result"], 1048576))
        if (
            initial["status"] != "COMPLETE"
            or initial["arm"] != "added_only"
            or initial["initial_weights_sha"] != BEST43_WEIGHTS
            or initial["selected_plan"] != expected["selected_plan"]
            or initial["input_membership"]
            != {
                k: expected[k]
                for k in ("public_membership", "added_membership", "diagnostic_indices")
            }
            or initial["prior_forward_rows"] != prior
            or initial["forward_rows"] != 1034547
        ):
            raise ValueError("shared INITIAL/current paired input/forward correspondence")
        prior += initial["forward_rows"]
    model_inputs = warmstart_model_inputs(cfg)
    return expected, acceptance, diagnostics, model_inputs, prior, initial


def train_arm(cache, output, config_path, input_binding, cfg):
    started = time.monotonic()
    expected, acceptance, diagnostic, model_inputs, prior, initial = admit(
        cache, config_path, input_binding, cfg
    )
    import numpy as np
    import torch
    from .compact_cache import IndexedPublicCorpus
    from .terminal_cache import TerminalCorpus
    from .sampling import FullBatchSampler
    from .train import (
        build_model,
        export,
        restore_warmstart_parameters,
        verify_initial_binding,
        verify_native_parameters,
        write,
        _finalize_training,
    )

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(cfg["training"]["seed"])
    output = Path(output)
    output.mkdir(exist_ok=False)
    marker = output / "INCOMPLETE"
    marker.write_text("normal parent finalization owns authoritative completion\n")
    added = public = None
    curves, lr_history = [], []
    forward_rows, seen_added, seen_public, step = 0, 0, 0, 0
    primary = None
    result = {"status": "FAILED", "arm": cfg["experiment"]["condition"]}

    def charge(count):
        nonlocal forward_rows
        if prior + forward_rows + count > FORWARD_LIMIT:
            raise ValueError("aggregate all-work forward ceiling exceeded before forward")
        forward_rows += count

    def metrics(values, labels):
        y = np.asarray(labels, dtype=np.float64)
        p = np.asarray(values, dtype=np.float64)
        if p.shape != y.shape or not len(y) or not np.isfinite(p).all() or not np.isfinite(y).all():
            raise ValueError("finite prediction/label shape required")
        decisive = y != 0
        return {
            "rows": len(y),
            "mse": float(np.mean((p - y) ** 2)),
            "sign_rows": int(decisive.sum()),
            "sign_accuracy": float(np.mean(p[decisive] * y[decisive] > 0))
            if decisive.any()
            else None,
            "saturation_fraction": float(np.mean(np.abs(p) >= 0.9)),
        }

    def forward(x, distances):
        charge(len(x))
        values = model(
            torch.from_numpy(x), torch.from_numpy(distances), torch.ones(len(x), dtype=torch.int64)
        )
        if values.shape not in ((len(x),), (len(x), 1)) or not torch.isfinite(values).all():
            raise ValueError("finite model output shape")
        return values.reshape(-1)

    def evaluate(name, indices):
        predictions, labels = [], []
        model.eval()
        with torch.no_grad():
            for start in range(0, len(indices), cfg["evaluation"]["batch_size"]):
                sub = indices[start : start + cfg["evaluation"]["batch_size"]]
                if name.startswith("added_"):
                    x, d, targets = added.batch(sub)
                    y = targets[:, 1]
                else:
                    split = "train" if name == "public_train" else "validation"
                    x, d, y = public.batch(split, sub)
                predictions.append(forward(x, d).cpu().numpy())
                labels.append(y)
        p, y = np.concatenate(predictions), np.concatenate(labels)
        summary = metrics(p, y)
        if name.startswith("added_"):
            summary["families"] = {
                added.families[int(group)]: metrics(
                    p[added.groups[indices] == group], y[added.groups[indices] == group]
                )
                for group in np.unique(added.groups[indices])
            }
        return summary

    def observe():
        record = {
            "step": step,
            "training_seen": seen_added + seen_public,
            "added_seen": seen_added,
            "public_seen": seen_public,
            "learning_rate": cfg["optimizer"]["lr"] * min(1, step / 20),
            "scopes": {name: evaluate(name, indices) for name, indices in scopes.items()},
        }
        curves.append(record)
        write(output / "curves.json", curves)

    def facts():
        return {
            "step": step,
            "added_seen": seen_added,
            "public_seen": seen_public,
            "forward_rows": forward_rows,
            "prior_forward_rows": prior,
            "wall_seconds": time.monotonic() - started,
            "result": result,
        }

    try:
        # Frozen public index metadata has been verified before opening any outcome.
        added = TerminalCorpus(cache)
        public = IndexedPublicCorpus(expected["public_membership"], acceptance)
        train_rows = np.flatnonzero(added.eligible & (added.splits == 0))
        validation_rows = np.flatnonzero(added.eligible & (added.splits == 1))
        if len(train_rows) != 217 or len(validation_rows) != 76:
            raise ValueError("unchanged common added T/V required")
        scopes = {
            "added_train": train_rows,
            "added_validation": validation_rows,
            "public_train": np.asarray(diagnostic["indices"]["train"], dtype=np.int64),
            "public_validation": np.asarray(diagnostic["indices"]["validation"], dtype=np.int64),
        }
        sampler = FullBatchSampler(train_rows, 64, cfg["training"]["seed"])
        public_rng = np.random.default_rng(PUBLIC_SEED)
        reflection_rng = np.random.default_rng(cfg["training"]["reflection_seed"])
        public_reflection_rng = np.random.Generator(
            np.random.PCG64(cfg["training"]["reflection_seed"]).jumped()
        )
        visits = np.zeros(added.row_count, dtype=np.uint32)
        public_visits = {}
        added_order, added_reflections = [], []
        reflected = 0
        model = build_model(cfg["model"], model_inputs["statistics"])
        restore_warmstart_parameters(model, model_inputs["warm_start"]["weights"])
        # Match loaded parameters to the existing immutable native weights in place.
        weights_path = model_inputs["warm_start"]["weights"]["path"]
        verify_initial_binding({"initial_weights_sha": BEST43_WEIGHTS}, weights_path)
        verify_native_parameters(weights_path, model.state_dict())
        initial_export = model_inputs["warm_start"]
        optimizer = torch.optim.Adam(
            model.parameters(),
            lr=cfg["optimizer"]["lr"],
            betas=tuple(cfg["optimizer"]["betas"]),
            eps=cfg["optimizer"]["eps"],
            weight_decay=0,
        )
        initial_full = (
            initial["full_opened_validation"]["initial"]
            if initial
            else evaluate("full_public_validation", range(PUBLIC_ROWS["validation"]))
        )
        observe()
        if initial and curves[0]["scopes"] != initial["curves"][0]["scopes"]:
            raise ValueError("same initial model/input/environment prediction correspondence")
        for update in range(1, 201):
            n_added = 64 if cfg["experiment"]["condition"] == "added_only" else 32
            ai = sampler.take(n_added)
            pi = public_rng.integers(PUBLIC_ROWS["train"], size=64 - n_added)
            added_mask = reflection_rng.random(n_added) < 0.5
            public_mask = public_reflection_rng.random(len(pi)) < 0.5
            mask = np.concatenate((added_mask, public_mask))
            x, d, y = mixed_batch(added, public, ai, pi, mask)
            model.train()
            optimizer.zero_grad(set_to_none=True)
            values = forward(x, d)
            loss = mixed_row_loss(values, torch.from_numpy(y))
            if not torch.isfinite(loss):
                raise ValueError("nonfinite single row-mean mixed loss")
            loss.backward()
            if any(
                p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()
            ):
                raise ValueError("nonfinite training gradient")
            rate = cfg["optimizer"]["lr"] * min(1, update / 20)
            for group in optimizer.param_groups:
                group["lr"] = rate
            optimizer.step()
            if any(not torch.isfinite(p).all() for p in model.parameters()):
                raise ValueError("nonfinite updated parameters")
            step = update
            lr_history.append(rate)
            seen_added += len(ai)
            seen_public += len(pi)
            reflected += int(mask.sum())
            np.add.at(visits, ai, 1)
            added_order.extend(int(i) for i in ai)
            added_reflections.extend(bool(v) for v in added_mask)
            for index in pi:
                public_visits[int(index)] = public_visits.get(int(index), 0) + 1
            if step in POINTS:
                observe()
        last_full = evaluate("full_public_validation", range(PUBLIC_ROWS["validation"]))
        last = export(
            model, cfg, model_inputs["statistics"], {"a": 0, "b": 0}, output / "last-model"
        )
        torch.save({"model": model.state_dict(), "config": cfg, "step": step}, output / "last.pt")
        np.savez_compressed(
            output / "exposure.npz",
            added_indices=np.asarray(added_order, dtype=np.int64),
            added_visits=visits,
            added_reflections=np.asarray(added_reflections, dtype=bool),
            public_indices=np.asarray(list(public_visits), dtype=np.int64),
            public_visits=np.asarray(list(public_visits.values()), dtype=np.uint32),
        )
        result = {
            "status": "COMPLETE",
            "arm": cfg["experiment"]["condition"],
            "step": step,
            "initial_weights_sha": BEST43_WEIGHTS,
            "initial_reference": initial_export,
            "last_weights_sha": json.loads(last.read_bytes())["weights_SHA"],
            "selected_plan": expected["selected_plan"],
            "fit_config_sha": expected["fit_config_sha"],
            "input_membership": {
                k: expected[k]
                for k in ("public_membership", "added_membership", "diagnostic_indices")
            },
            "prior_forward_rows": prior,
            "forward_rows": forward_rows,
            "aggregate_forward_rows": prior + forward_rows,
            "added_seen": seen_added,
            "public_seen": seen_public,
            "added_distinct": int(np.count_nonzero(visits)),
            "public_distinct": len(public_visits),
            "added_repeats": seen_added - int(np.count_nonzero(visits)),
            "public_repeats": seen_public - len(public_visits),
            "added_stream_SHA256": hashlib.sha256(
                np.asarray(added_order, dtype="<u4").tobytes()
            ).hexdigest(),
            "added_first6400_SHA256": hashlib.sha256(
                np.asarray(added_order[:6400], dtype="<u4").tobytes()
            ).hexdigest(),
            "added_reflection_SHA256": hashlib.sha256(bytes(added_reflections)).hexdigest(),
            "added_first6400_reflection_SHA256": hashlib.sha256(
                bytes(added_reflections[:6400])
            ).hexdigest(),
            "reflection_rng": "added default_rng approved seed; public PCG64(approved seed).jumped() separate stream",
            "reflected_rows": reflected,
            "learning_rates": lr_history,
            "full_opened_validation": {"initial": initial_full, "last": last_full},
            "curves": curves,
            "wall_seconds": time.monotonic() - started,
            "completed_epochs": None,
            "selection": "LAST200; no validation-selected model",
            "continuous_peak": "UNKNOWN",
        }
        expected_forwards = 1034547 if result["arm"] == "added_only" else 615397
        if (
            forward_rows != expected_forwards
            or len(curves) != 11
            or seen_added + seen_public != 12800
        ):
            raise ValueError("fixed full-batch/evaluation/forward census incomplete")
        if initial and (
            result["added_stream_SHA256"] != initial["added_first6400_SHA256"]
            or result["added_reflection_SHA256"] != initial["added_first6400_reflection_SHA256"]
        ):
            raise ValueError("replay must consume exactly the same added-stream prefix")
        with (output / "curves.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=(
                    "arm",
                    "step",
                    "scope",
                    "rows",
                    "mse",
                    "sign_rows",
                    "sign_accuracy",
                    "saturation_fraction",
                ),
            )
            writer.writeheader()
            for point in curves:
                for scope, value in point["scopes"].items():
                    writer.writerow(
                        {
                            "arm": result["arm"],
                            "step": point["step"],
                            "scope": scope,
                            **{k: value[k] for k in writer.fieldnames if k in value},
                        }
                    )
    except BaseException as error:
        primary = error
        result["status"] = "FAILED"
        raise
    finally:
        actions = [
            (
                "training_result",
                lambda: write(
                    output / "training.json",
                    {**result, **{k: v for k, v in facts().items() if k != "result"}},
                ),
            )
        ]
        if added is not None:
            actions.append(("added_cache_identity_after", added.verify_binding))
        if public is not None:
            actions.extend(
                (("public_identity_after", public.verify_binding), ("public_close", public.close))
            )
        _finalize_training(output, actions, primary, facts)
    # The authoritative normal parent FINALIZE still verifies data/source/cleanup.
    marker.unlink()
    return result
