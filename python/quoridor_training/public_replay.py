"""Configured outcome mixture using the maintained model, codec and GPU entry.

Public T is indexed with replacement; public V is observation-only. The added
stream cycles whole-family T rows and keeps V uncapped. Detailed source histories
remain at publication, outside this consumer.
"""

import csv
import hashlib
import json
import math
from pathlib import Path
import random
import time

from .common import bound_file_bytes, common_cache_config, warmstart_model_inputs

STUDY = "mixed-outcome"


def mixed_batch(added, public, added_indices, public_indices, reflection_mask):
    """One FP32 STM stream; validate source/split isolation before model input."""
    import numpy as np

    ai, pi, mask = map(np.asarray, (added_indices, public_indices, reflection_mask))
    count = len(ai) + len(pi)
    if (
        ai.ndim != 1
        or pi.ndim != 1
        or ai.dtype.kind not in "iu"
        or pi.dtype.kind not in "iu"
        or not len(ai)
        or mask.dtype != np.dtype(bool)
        or mask.shape != (count,)
        or np.any(ai < 0)
        or np.any(ai >= added.row_count)
    ):
        raise ValueError("nonempty configured added rows and source reflection masks required")
    if np.any(added.splits[ai] != 0) or not added.eligible[ai].all():
        raise ValueError("added training excludes V and ineligible outcomes")
    x, d, targets = added.batch(ai, mask[: len(ai)])
    y = targets[:, 1]
    if len(pi):
        px, pd, py = public.batch("train", pi, mask[len(ai) :], training=True)
        x, d, y = (
            np.concatenate((x, px)),
            np.concatenate((d, pd)),
            np.concatenate((y, py)),
        )
    if (
        x.shape != (count, 2, 312)
        or d.shape != (count, 2)
        or y.shape != (count,)
        or any(v.dtype != np.float32 or not np.isfinite(v).all() for v in (x, d, y))
        or not np.isin(y, (-1, 0, 1)).all()
    ):
        raise ValueError("finite configured QF1/STM/outcome batch required")
    return x, d, y


def mixed_row_loss(predictions, targets):
    """Average every configured source row loss exactly once."""
    import torch

    if (
        predictions.ndim != 1
        or predictions.shape != targets.shape
        or not len(targets)
        or predictions.dtype != torch.float32
        or targets.dtype != torch.float32
    ):
        raise ValueError("one nonempty FP32 row prediction/target objective required")
    return torch.mean((predictions - targets) ** 2)


def reflection_generators(settings):
    """Independent source streams; public keeps the maintained PCG64 jump domain."""
    import numpy as np

    return (
        np.random.default_rng(settings["added_reflection_seed"]),
        np.random.Generator(np.random.PCG64(settings["public_reflection_seed"]).jumped()),
    )


def planned_work(config, train_rows, validation_rows, public_rows):
    """Result-blind full-batch exposure and full-selector forward upper bound."""
    m, t, e = config["mixture"], config["training"], config["evaluation"]
    if (
        train_rows <= 0
        or validation_rows <= 0
        or any(public_rows[s] <= 0 for s in ("train", "validation"))
    ):
        raise ValueError("nonempty added/public T and V required")
    steps = min(t["steps"], math.ceil(m["added_exposures"] * train_rows / m["added_rows"]))
    selectors = set(
        e["checkpoints"] if e["checkpoints"] is not None else range(0, steps + 1, e["interval"])
    )
    selectors = {0, steps, *(p for p in selectors if p <= steps)}
    diagnostics = (
        selectors
        if e["diagnostic_checkpoints"] is None
        else {p for p in e["diagnostic_checkpoints"] if p <= steps}
    )
    full_train = {p for p in e["full_train_checkpoints"] if p <= steps}
    if e["full_train"]:
        full_train |= selectors
    # The same named scopes drive both the finite bound and actual observations.
    scope_rows = {
        "added_validation": validation_rows,
        "public_validation": public_rows["validation"],
        "added_train": min(train_rows, e["diagnostic_rows"]),
        "public_train": min(public_rows["train"], e["diagnostic_rows"]),
        "added_full_train": train_rows,
        "public_full_train": public_rows["train"],
    }
    scopes_by_step = {}
    for point in sorted(selectors | diagnostics | full_train):
        names = []
        if point in selectors:
            names.extend(("added_validation", "public_validation"))
        if point in diagnostics:
            names.extend(("added_train", "public_train"))
        if point in full_train:
            names.extend(("added_full_train", "public_full_train"))
        scopes_by_step[point] = names
    measurement_rows = {
        point: sum(scope_rows[n] for n in names) for point, names in scopes_by_step.items()
    }
    measurements = sum(measurement_rows.values())
    return {
        "updates": steps,
        "observation_steps": list(scopes_by_step),
        "selector_steps": sorted(selectors),
        "diagnostic_steps": sorted(diagnostics),
        "full_train_steps": sorted(full_train),
        "scopes_by_step": scopes_by_step,
        "added_rows": steps * m["added_rows"],
        "public_rows": steps * m["public_rows"],
        "training_forwards": steps * t["batch_size"],
        "measurement_forwards": measurements,
        "forward_upper": steps * t["batch_size"] + measurements,
        "measurement_rows_by_step": measurement_rows,
    }


class Selector:
    """Strict new-V improvement, with an explicitly optional public-V gate."""

    def __init__(self, public_non_regression, patience, min_delta, relative_delta):
        from .sampling import EarlyStopping

        if type(public_non_regression) is not bool:
            raise ValueError("explicit public_non_regression boolean required")
        self.gate = public_non_regression
        self.stopping = EarlyStopping(patience, min_delta, relative_delta)
        self.initial_public = self.initial_added = self.best = None
        self.best_step = 0

    def observe(self, step, added, public):
        if not math.isfinite(added) or not math.isfinite(public):
            raise ValueError("finite full validation selector metrics")
        if self.initial_public is None:
            if step != 0:
                raise ValueError("INITIAL selector observation required")
            self.initial_public, self.initial_added, self.best = public, added, added
        _, stop = self.stopping.observe(added)
        improved = added < self.best and (not self.gate or public <= self.initial_public)
        if improved:
            self.best, self.best_step = added, step
        return improved, stop


class WorkBudget:
    """Count every attempted model row before its forward; preserve partial facts."""

    def __init__(self, samples, seconds, output, output_limit_bytes):
        self.limit, self.seconds, self.output, self.output_limit = (
            samples,
            seconds,
            Path(output),
            output_limit_bytes,
        )
        self.start, self.training, self.measurement = time.monotonic(), 0, 0
        self.returned_training = self.returned_measurement = 0

    def check(self):
        from .cycle_process import CycleStopped, directory_bytes

        if self.seconds is not None and time.monotonic() - self.start >= self.seconds:
            raise CycleStopped("configured fit time limit")
        if directory_bytes(self.output) > self.output_limit:
            raise CycleStopped("configured whole fit output limit")

    def charge(self, count, *, training=False):
        if type(count) is not int or count <= 0:
            raise ValueError("positive forward row count")
        self.check()
        if self.training + self.measurement + count > self.limit:
            raise ValueError("all-work forward limit exceeded before forward")
        if training:
            self.training += count
        else:
            self.measurement += count


def admit(cache, config_path, input_binding, cfg):
    """Actual cache/model/public refs; scientific permission stays in normal RUN."""
    if config_path is None:
        raise ValueError("explicit configured mixture recipe required")
    from .common import resolve_config
    from .distance_steps import require_completed_stream_cache

    if resolve_config(config_path) != cfg:
        raise ValueError("normalized config/path correspondence")
    path = Path(cache) / "cache.json"
    manifest = json.loads(path.read_bytes())
    require_completed_stream_cache(cache, manifest)
    common_cache_config(manifest)
    # This mode must never reinterpret a historical raw-range common mask as
    # outcome-only eligibility, or silently alter producer eligibility.
    if manifest["common_corpus"]["config"]["root_value_policy"] != "outcome_only":
        raise ValueError("outcome-only producer eligibility required")
    if input_binding is not None:
        extra = json.loads(Path(input_binding).read_bytes())
        for name, ref in extra.get("files", {}).items():
            bound_file_bytes(ref, max(1024**2, ref["bytes"]))
        if (
            extra.get("cache_manifest_sha256", hashlib.sha256(path.read_bytes()).hexdigest())
            != hashlib.sha256(path.read_bytes()).hexdigest()
        ):
            raise ValueError("bound current compact cache manifest")
    m = cfg["mixture"]
    public = json.loads(bound_file_bytes(m["public_membership"], 1024**2))
    acceptance = json.loads(bound_file_bytes(m["public_acceptance"], 1024**2))
    if acceptance["public_membership"] != m["public_membership"]:
        raise ValueError("owning public accepted membership")
    counts = {}
    for split in ("train", "validation"):
        parts = [p for p in public["partitions"] if p["name"] == split]
        if len(parts) != 1 or type(parts[0]["rows"]) is not int or parts[0]["rows"] <= 0:
            raise ValueError("nonempty opened public T/V membership")
        counts[split] = parts[0]["rows"]
    model_inputs = warmstart_model_inputs(cfg)
    warm = model_inputs["warm_start"]
    if manifest["model_scale_authority"] != {
        "starting_weights_sha256": warm["weights"]["sha256"],
        "descriptor_sha256": warm["descriptor"]["sha256"],
        "evaluator_sha256": warm["evaluator_sha256"],
        "scale_policy": "incumbent_descriptor_T_only",
    }:
        raise ValueError("actual cache/initializer/frozen-scale correspondence")
    return manifest, acceptance, counts, model_inputs


def train_mixture(cache, output, config_path, input_binding, cfg):
    manifest, acceptance, counts, model_inputs = admit(cache, config_path, input_binding, cfg)
    import numpy as np
    import torch
    from .compact_cache import IndexedPublicCorpus
    from .terminal_cache import TerminalCorpus
    from .sampling import FullBatchSampler, family_training_view, diagnostic_indices
    from .train import (
        build_model,
        configure_framework,
        outcome_inputs,
        export,
        restore_warmstart_parameters,
        verify_native_parameters,
        write,
        _finalize_training,
        append_curve_record,
        _exception_record,
    )
    from .cycle_process import cancellation_signals

    device = configure_framework(cfg)
    output = Path(output)
    output.mkdir(exist_ok=False)
    marker = output / "INCOMPLETE"
    marker.write_text("normal parent finalization owns authoritative completion\n")
    budget = WorkBudget(
        cfg["limits"]["samples"],
        cfg["limits"]["seconds"],
        output,
        cfg["mixture"]["output_limit_bytes"],
    )
    m, t, e = cfg["mixture"], cfg["training"], cfg["evaluation"]
    added = public = model = optimizer = None
    step = seen_added = seen_public = attempted_added = attempted_public = 0
    attempted_update = 0
    current_update_state = "NOT_INITIALIZED"
    curves, rates = [], []
    result = {
        "status": "FAILED",
        "stop_reason": None,
        "best_step": 0,
        "last_checkpoint_state": "UNKNOWN",
        "last_checkpoint_step": None,
    }
    primary = None
    initial = model_inputs["warm_start"]
    write(output / "config.json", cfg)
    write(output / "scale.json", model_inputs["statistics"])
    visits = public_visits = None
    plan = None

    def facts():
        return {
            "step": step,
            "attempted_update": attempted_update,
            "current_update_state": current_update_state,
            "added_seen": seen_added,
            "public_seen": seen_public,
            "attempted_added": attempted_added,
            "attempted_public": attempted_public,
            "training_forwards": budget.training,
            "measurement_forwards": budget.measurement,
            "forward_rows": budget.training + budget.measurement,
            "returned_finite_training_rows": budget.returned_training,
            "returned_finite_measurement_rows": budget.returned_measurement,
            "forward_count_semantics": "forward_rows charges attempted rows before placement/model call; returned_finite rows require completed finite output; failure's intervening actual calls UNKNOWN",
            "wall_seconds": time.monotonic() - budget.start,
        }

    def save_checkpoint(name):
        if current_update_state != "VERIFIED_COMPLETED_UPDATE":
            raise ValueError("current model/optimizer state is UNKNOWN; no completed checkpoint")
        budget.check()
        descriptor = export(
            model,
            cfg,
            model_inputs["statistics"],
            {"a": 0, "b": 0},
            output / (name + "-model"),
        )
        torch.save(
            {
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "config": cfg,
                "step": step,
                "attempted_update": attempted_update,
                "current_update_state": current_update_state,
                "initial_reference": initial,
            },
            output / (name + ".pt"),
        )
        budget.check()
        return str(descriptor)

    def forward(x, d, *, training=False):
        budget.charge(len(x), training=training)
        values = model(*outcome_inputs(x, d, device))
        if values.shape not in ((len(x),), (len(x), 1)) or not torch.isfinite(values).all():
            raise ValueError("finite model output shape")
        if training:
            budget.returned_training += len(x)
        else:
            budget.returned_measurement += len(x)
        return values.reshape(-1)

    def evaluate(name, indices, constant):
        totals = {
            "rows": 0,
            "error": 0.0,
            "sign_rows": 0,
            "correct": 0,
            "saturated": 0,
            "constant": 0.0,
            "distance": 0.0,
        }
        families = {}
        model.eval()
        with torch.no_grad():
            for first in range(0, len(indices), e["batch_size"]):
                sub = indices[first : first + e["batch_size"]]
                if name.startswith("added_"):
                    x, d, targets = added.batch(sub)
                    y = targets[:, 1]
                else:
                    x, d, y = public.batch(
                        "train" if name in ("public_train", "public_full_train") else "validation",
                        sub,
                    )
                p = forward(x, d).detach().cpu().numpy().astype(np.float64)
                yf = y.astype(np.float64)
                if not np.isfinite(yf).all() or not np.isin(y, (-1, 0, 1)).all():
                    raise ValueError("finite literal outcome labels")
                error = (p - yf) ** 2
                decisive = yf != 0
                totals["rows"] += len(y)
                totals["error"] += float(error.sum())
                totals["sign_rows"] += int(decisive.sum())
                totals["correct"] += int((p[decisive] * yf[decisive] > 0).sum())
                totals["saturated"] += int((np.abs(p) >= 0.9).sum())
                totals["constant"] += float(((constant - yf) ** 2).sum())
                analytic = np.tanh(np.float32(8) * (d[:, 1] - d[:, 0]))
                totals["distance"] += float(((analytic.astype(np.float64) - yf) ** 2).sum())
                if name.startswith("added_"):
                    groups = added.groups[sub]
                    for g in np.unique(groups):
                        bank = families.setdefault(added.families[int(g)], [0, 0.0])
                        bank[0] += int((groups == g).sum())
                        bank[1] += float(error[groups == g].sum())
        n = totals["rows"]
        if not n:
            raise ValueError("empty observation scope")
        return {
            "rows": n,
            "mse": totals["error"] / n,
            "sign_rows": totals["sign_rows"],
            "sign_accuracy": totals["correct"] / totals["sign_rows"]
            if totals["sign_rows"]
            else None,
            "saturation_fraction": totals["saturated"] / n,
            "constant_mse": totals["constant"] / n,
            "analytic_D_mse": totals["distance"] / n,
            "families": {k: {"rows": v[0], "mse": v[1] / v[0]} for k, v in families.items()},
        }

    def observe():
        record = {
            "step": step,
            "scopes": {
                name: evaluate(name, indices, constants[name.split("_")[0]])
                for name in plan["scopes_by_step"][step]
                for indices in (scopes[name],)
            },
            **facts(),
        }
        append_curve_record(output / "curves.jsonl.gz", record)
        with (output / "curves.csv").open("a", newline="") as stream:
            fields = [
                "step",
                "scope",
                "rows",
                "mse",
                "sign_rows",
                "sign_accuracy",
                "saturation_fraction",
                "constant_mse",
                "analytic_D_mse",
            ]
            writer = csv.DictWriter(stream, fieldnames=fields)
            if not curves:
                writer.writeheader()
            for name, value in record["scopes"].items():
                writer.writerow(
                    {
                        "step": step,
                        "scope": name,
                        **{k: value[k] for k in fields if k in value},
                    }
                )
        curves.append(record)
        improved, stop = (False, False)
        if step in plan["selector_steps"]:
            improved, stop = selector.observe(
                step,
                record["scopes"]["added_validation"]["mse"],
                record["scopes"]["public_validation"]["mse"],
            )
        if improved:
            result["best_descriptor"] = save_checkpoint("best")
            result["best_step"] = step
        budget.check()
        return stop

    try:
        with cancellation_signals():
            added = TerminalCorpus(cache)
            public = IndexedPublicCorpus(m["public_membership"], acceptance)
            train_rows = family_training_view(
                added.groups, added.splits, added.eligible, m["train_family_row_cap"]
            )
            validation_rows = np.flatnonzero(added.eligible & (added.splits == 1))
            plan = planned_work(cfg, len(train_rows), len(validation_rows), counts)
            if plan["forward_upper"] > cfg["limits"]["samples"]:
                raise ValueError("configured complete-work forward upper exceeds samples")
            scopes = {
                "added_train": diagnostic_indices(
                    added.rows, train_rows, e["diagnostic_rows"], m["diagnostic_seed"]
                ),
                "added_validation": validation_rows,
                "public_train": random.Random(m["diagnostic_seed"]).sample(
                    range(counts["train"]), min(e["diagnostic_rows"], counts["train"])
                ),
                "public_validation": range(counts["validation"]),
                "added_full_train": train_rows,
                "public_full_train": range(counts["train"]),
            }
            # Public constant is derived only from the configured T diagnostic,
            # not the entire public T or any V labels. Its scope is recorded.
            constants = {
                "added": float(np.mean(added.labels[train_rows, 1].astype(np.float64))),
                "public": 0.0,
            }
            public_sum = 0.0
            for first in range(0, len(scopes["public_train"]), e["batch_size"]):
                _, _, y = public.batch(
                    "train", scopes["public_train"][first : first + e["batch_size"]]
                )
                public_sum += float(y.astype(np.float64).sum())
            constants["public"] = public_sum / len(scopes["public_train"])
            selector = Selector(
                m["selector"]["public_non_regression"],
                e["early_stopping_patience"],
                e["min_delta"],
                e["min_delta_relative"],
            )
            sampler = FullBatchSampler(train_rows, m["added_rows"], t["seed"])
            public_rng = np.random.default_rng(m["public_sampling_seed"])
            added_rng, public_reflection_rng = reflection_generators(m)
            visits = np.zeros(added.row_count, dtype=np.uint64)
            public_visits = {}
            reflected = {"added": 0, "public": 0}
            model = build_model(cfg["model"], model_inputs["statistics"]).to(device)
            restore_warmstart_parameters(model, initial["weights"])
            verify_native_parameters(initial["weights"]["path"], model.state_dict())
            optimizer = torch.optim.Adam(
                model.parameters(),
                lr=cfg["optimizer"]["lr"],
                betas=tuple(cfg["optimizer"]["betas"]),
                eps=cfg["optimizer"]["eps"],
                weight_decay=cfg["optimizer"]["weight_decay"],
            )
            current_update_state = "VERIFIED_COMPLETED_UPDATE"
            result.update(
                initial_reference=initial,
                best_descriptor=initial["descriptor"],
                best_step=0,
                plan={
                    **plan,
                    "scopes_by_step": {str(k): v for k, v in plan["scopes_by_step"].items()},
                    "measurement_rows_by_step": {
                        str(k): v for k, v in plan["measurement_rows_by_step"].items()
                    },
                },
                constants={
                    "added_T_view": constants["added"],
                    "public_T_diagnostic": constants["public"],
                },
            )
            observe()
            for update in range(1, plan["updates"] + 1):
                budget.check()
                attempted_update = update
                ai = sampler.take(m["added_rows"])
                pi = public_rng.integers(counts["train"], size=m["public_rows"])
                am = added_rng.random(len(ai)) < m["added_reflection_probability"]
                pm = public_reflection_rng.random(len(pi)) < m["public_reflection_probability"]
                attempted_added += len(ai)
                attempted_public += len(pi)
                x, d, y = mixed_batch(added, public, ai, pi, np.concatenate((am, pm)))
                model.train()
                current_update_state = "UPDATE_IN_PROGRESS_UNKNOWN"
                optimizer.zero_grad(set_to_none=True)
                values = forward(x, d, training=True)
                loss = mixed_row_loss(values, torch.from_numpy(y).to(device))
                if not torch.isfinite(loss):
                    raise ValueError("nonfinite row-mean outcome loss")
                loss.backward()
                if any(
                    p.grad is not None and not torch.isfinite(p.grad).all()
                    for p in model.parameters()
                ):
                    raise ValueError("nonfinite training gradient")
                rate = cfg["optimizer"]["lr"] * (
                    min(1.0, update / t["warmup_steps"]) if t["warmup_steps"] else 1.0
                )
                for group in optimizer.param_groups:
                    group["lr"] = rate
                optimizer.step()
                if any(not torch.isfinite(p).all() for p in model.parameters()):
                    raise ValueError("nonfinite updated parameters")
                step = update
                current_update_state = "VERIFIED_COMPLETED_UPDATE"
                rates.append(rate)
                seen_added += len(ai)
                seen_public += len(pi)
                np.add.at(visits, ai, 1)
                for i in pi:
                    public_visits[int(i)] = public_visits.get(int(i), 0) + 1
                reflected["added"] += int(am.sum())
                reflected["public"] += int(pm.sum())
                if step in plan["observation_steps"] and observe():
                    result["stop_reason"] = "early_stopping"
                    break
            np.savez_compressed(
                output / "exposure.npz",
                added_visits=visits,
                public_indices=np.asarray(list(public_visits), dtype=np.int64),
                public_visits=np.asarray(list(public_visits.values()), dtype=np.uint64),
            )
            result["status"] = "COMPLETE"
            result["stop_reason"] = result["stop_reason"] or "configured_horizon"
            result.update(
                reflected_rows=reflected,
                reflection_streams={
                    "added": "default_rng configured added seed",
                    "public": "PCG64 configured public seed, jumped independent stream",
                },
                learning_rates=rates,
                training_view_rows=len(train_rows),
                validation_rows=len(validation_rows),
                added_distinct=int(np.count_nonzero(visits)),
                public_distinct=len(public_visits),
                added_repeats=seen_added - int(np.count_nonzero(visits)),
                public_repeats=seen_public - len(public_visits),
                selection={
                    "public_non_regression": selector.gate,
                    "best_step": selector.best_step,
                },
                curves=curves,
                cache_manifest_sha256=added.manifest_sha,
                fit_config_sha256=hashlib.sha256(Path(config_path).read_bytes()).hexdigest(),
            )
    except BaseException as error:
        primary = error
        result.update(status="FAILED", primary=_exception_record(error))
        raise
    finally:
        # Independent saves/identity/close all attempted; errors remain FAILED.
        actions = []
        if (
            model is not None
            and optimizer is not None
            and current_update_state == "VERIFIED_COMPLETED_UPDATE"
        ):

            def save_last():
                result["last_descriptor"] = save_checkpoint("last")
                result["last_checkpoint_state"] = "VERIFIED_COMPLETED_UPDATE"
                result["last_checkpoint_step"] = step

            actions.append(("LAST_checkpoint", save_last))
        # In-progress/failed mutations are not relabelled as the previous step.
        # Metadata remains UNKNOWN; no rollback, rescue or extra model call.
        actions.append(
            (
                "training_result",
                lambda: write(output / "training.json", {**result, **facts()}),
            )
        )
        if added is not None:
            actions.append(("added_cache_identity_after", added.verify_binding))
        if public is not None:
            actions.extend(
                (
                    ("public_identity_after", public.verify_binding),
                    ("public_close", public.close),
                )
            )
        _finalize_training(output, actions, primary, facts)
    marker.unlink()
    return {**result, **facts()}
