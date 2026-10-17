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


def training_view_indices(ref, cache_manifest_sha256, candidates):
    """A bound subset of the existing T-only capped view, never a new split."""
    if ref is None:
        return candidates
    view = json.loads(bound_file_bytes(ref, 4 * 1024**2))
    if (
        not isinstance(view, dict)
        or set(view) != {"cache_manifest_sha256", "indices"}
        or view["cache_manifest_sha256"] != cache_manifest_sha256
    ):
        raise ValueError("training view must bind the actual compact cache")
    indices = view["indices"]
    if (
        not isinstance(indices, list)
        or not indices
        or any(type(i) is not int for i in indices)
        or indices != sorted(set(indices))
        or not set(indices) <= set(map(int, candidates))
    ):
        raise ValueError("nonempty unique chronological subset of configured eligible T required")
    return indices


def mixed_batch(
    added,
    public,
    added_indices,
    public_indices,
    reflection_mask,
    *,
    target_column,
    teacher_values=None,
):
    """One FP32 STM stream; validate source/split isolation before model input."""
    import numpy as np

    ai, pi, mask = map(np.asarray, (added_indices, public_indices, reflection_mask))
    count = len(ai) + len(pi)
    if (
        ai.ndim != 1
        or pi.ndim != 1
        or ai.dtype.kind not in "iu"
        or pi.dtype.kind not in "iu"
        or not count
        or mask.dtype != np.dtype(bool)
        or mask.shape != (count,)
        or np.any(ai < 0)
        or np.any(ai >= added.row_count)
    ):
        raise ValueError("nonempty configured added rows and source reflection masks required")
    if np.any(added.splits[ai] != 0) or not added.eligible[ai].all():
        raise ValueError("added training excludes V and ineligible outcomes")
    if len(ai):
        x, d, targets = added.batch(ai, mask[: len(ai)])
        y = (
            targets[:, target_column]
            if teacher_values is None
            else teacher_values.take(ai, mask[: len(ai)])
        )
    else:
        x = np.empty((0, 2, 312), dtype=np.float32)
        d = np.empty((0, 2), dtype=np.float32)
        y = np.empty((0,), dtype=np.float32)
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
        or (not np.isin(y, (-1, 0, 1)).all() if teacher_values is None else np.any(np.abs(y) > 1))
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


def public_observation_policy(mixture):
    return mixture.get("public_evaluation") or {
        "validation": "checkpoints",
        "train_diagnostic": True,
    }


def initial_observation_scopes(saved, binding):
    """Reuse only requested scopes from an actual identity-bound INITIAL bank."""
    if not isinstance(saved, dict) or not isinstance(saved.get("binding"), dict):
        raise ValueError("bound actual shared INITIAL bank required")
    observed = saved.get("binding", {})
    fixed = {k: v for k, v in binding.items() if k not in ("scopes", "constants")}
    if fixed != {k: v for k, v in observed.items() if k not in ("scopes", "constants")}:
        raise ValueError("shared INITIAL model/scale/cache/public/scope correspondence")
    for name, expected in binding["scopes"].items():
        source = name.split("_")[0]
        if (
            observed.get("scopes", {}).get(name) != expected
            or observed.get("constants", {}).get(source) != binding["constants"][source]
            or name not in saved.get("scopes", {})
        ):
            raise ValueError("shared INITIAL exact requested rows/constants")
    return {name: saved["scopes"][name] for name in binding["scopes"]}


def planned_work(config, train_rows, validation_rows, public_rows, *, reuse_initial=False):
    """Result-blind full-batch exposure and full-selector forward upper bound."""
    m, t, e = config["mixture"], config["training"], config["evaluation"]
    public_policy = public_observation_policy(m)
    if (
        train_rows <= 0
        or validation_rows <= 0
        or any(public_rows[s] <= 0 for s in ("train", "validation"))
    ):
        raise ValueError("nonempty added/public T and V required")
    steps = (
        min(t["steps"], math.ceil(m["added_exposures"] * train_rows / m["added_rows"]))
        if m["added_rows"]
        else t["steps"]
    )
    training_rows = m.get("training_rows")
    if training_rows is not None:
        steps = math.ceil(training_rows / t["batch_size"])
        if steps != t["steps"] or (
            training_rows % t["batch_size"] and m["added_rows"] and m["public_rows"]
        ):
            raise ValueError("exact training rows/update count and source-specific tail")
        added_rows = training_rows if not m["public_rows"] else steps * m["added_rows"]
        if added_rows > m["added_exposures"] * train_rows:
            raise ValueError("requested actual added-row exposure exceeds configured limit")
    else:
        training_rows = steps * t["batch_size"]
        added_rows = steps * m["added_rows"]
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
            names.append("added_validation")
            if public_policy["validation"] == "checkpoints":
                names.append("public_validation")
        if point in diagnostics:
            names.append("added_train")
            if public_policy["train_diagnostic"]:
                names.append("public_train")
        if point in full_train:
            names.append("added_full_train")
            if public_policy["train_diagnostic"]:
                names.append("public_full_train")
        scopes_by_step[point] = names
    measurement_rows = {
        point: sum(scope_rows[n] for n in names) for point, names in scopes_by_step.items()
    }
    if reuse_initial:
        measurement_rows[0] = 0
    measurements = sum(measurement_rows.values())
    frozen_best_rows = public_rows["validation"] if public_policy["validation"] == "best" else 0
    last_rows = public_rows["validation"] if public_policy["validation"] == "last" else 0
    return {
        "updates": steps,
        "observation_steps": list(scopes_by_step),
        "selector_steps": sorted(selectors),
        "diagnostic_steps": sorted(diagnostics),
        "full_train_steps": sorted(full_train),
        "scopes_by_step": scopes_by_step,
        "added_rows": added_rows,
        "public_rows": training_rows - added_rows,
        "training_forwards": training_rows,
        "measurement_forwards": measurements + frozen_best_rows + last_rows,
        "frozen_best_public_validation_rows": frozen_best_rows,
        "last_public_validation_rows": last_rows,
        "reused_initial": reuse_initial,
        "forward_upper": training_rows + measurements + frozen_best_rows + last_rows,
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
        if not math.isfinite(added) or (
            (self.gate or public is not None) and (public is None or not math.isfinite(public))
        ):
            raise ValueError("finite full validation selector metrics")
        if self.initial_added is None:
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
    model_inputs = warmstart_model_inputs(cfg)
    warm = model_inputs["warm_start"]
    extra = {}
    if input_binding is not None:
        extra = json.loads(Path(input_binding).read_bytes())
        if warm["weights"] is None:
            files = extra.get("files", {})
            if (
                not isinstance(files, dict)
                or set(files) - {"cache_manifest", "descriptor"}
                or ("descriptor" in files and files["descriptor"] != warm["descriptor"])
                or (
                    "cache_manifest" in files
                    and (
                        files["cache_manifest"].get("path") != str(path)
                        or files["cache_manifest"].get("sha256")
                        != hashlib.sha256(path.read_bytes()).hexdigest()
                    )
                )
            ):
                raise ValueError(
                    "fresh initialization binds only actual cache and normalization metadata"
                )
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
    expected_authority = (
        model_inputs["scale_authority"]
        if warm["weights"] is None
        else {
            "starting_weights_sha256": warm["weights"]["sha256"],
            "descriptor_sha256": warm["descriptor"]["sha256"],
            "evaluator_sha256": warm["evaluator_sha256"],
            "scale_policy": "incumbent_descriptor_T_only",
        }
    )
    authorities = []
    if "model_scale_authority" in manifest:
        authorities.append(manifest["model_scale_authority"])
    if "model_scale_authority" in extra:
        files = extra.get("files", {})
        cache_ref = files.get("cache_manifest", {})
        if (
            extra.get("cache_manifest_sha256") != hashlib.sha256(path.read_bytes()).hexdigest()
            or cache_ref.get("path") != str(path)
            or cache_ref.get("sha256") != extra["cache_manifest_sha256"]
            or files.get("descriptor") != warm["descriptor"]
            or (warm["weights"] is not None and files.get("weights") != warm["weights"])
            or (warm["weights"] is None and "weights" in files)
        ):
            raise ValueError(
                "external initializer/scale authority must bind actual cache/model refs"
            )
        authorities.append(extra["model_scale_authority"])
    if not authorities or any(authority != expected_authority for authority in authorities):
        raise ValueError("actual cache/initializer/frozen-scale correspondence")
    if warm["weights"] is None and extra.get("files", {}).get("initial_observation") is not None:
        raise ValueError("fresh initialization requires its own actual INITIAL observation")
    return manifest, acceptance, counts, model_inputs


def _add_outcome_slice(bank, predictions, outcomes, groups=None):
    """Accumulate observation-only z/saturation/family counts from existing outputs."""
    import numpy as np

    p, z = (
        np.asarray(predictions, dtype=np.float64),
        np.asarray(outcomes, dtype=np.float64),
    )
    if (
        p.ndim != 1
        or z.shape != p.shape
        or not np.isfinite(p).all()
        or not np.isin(z, (-1, 0, 1)).all()
        or (groups is not None and np.asarray(groups).shape != p.shape)
    ):
        raise ValueError(
            "finite observation predictions and corresponding literal z/groups required"
        )
    if not bank:
        bank.update(
            rows=0,
            z_sse=0.0,
            family_bound=groups is not None,
            families={},
            by_z={
                str(k): dict(
                    rows=0,
                    z_sse=0.0,
                    absolute_post_sum=0.0,
                    prediction_negative_rows=0,
                    prediction_zero_rows=0,
                    prediction_positive_rows=0,
                    saturated_90_rows=0,
                    saturated_99_rows=0,
                )
                for k in (-1, 0, 1)
            },
        )
    if bank["family_bound"] != (groups is not None):
        raise ValueError("observation family qualification changed between batches")
    error = (p - z) ** 2
    bank["rows"] += len(p)
    bank["z_sse"] += float(error.sum())
    for outcome in (-1, 0, 1):
        take = z == outcome
        values = p[take]
        counts = bank["by_z"][str(outcome)]
        counts["rows"] += int(take.sum())
        counts["z_sse"] += float(error[take].sum())
        counts["absolute_post_sum"] += float(np.abs(values).sum())
        counts["prediction_negative_rows"] += int((values < 0).sum())
        counts["prediction_zero_rows"] += int((values == 0).sum())
        counts["prediction_positive_rows"] += int((values > 0).sum())
        counts["saturated_90_rows"] += int((np.abs(values) >= 0.9).sum())
        counts["saturated_99_rows"] += int((np.abs(values) >= 0.99).sum())
    if groups is not None:
        groups = np.asarray(groups)
        for group in np.unique(groups):
            take = groups == group
            family = bank["families"].setdefault(int(group), [0, 0.0])
            family[0] += int(take.sum())
            family[1] += float(error[take].sum())


def _outcome_slice_result(bank):
    """Publish explicit row/family denominators; zero-z remains its own category."""
    n = bank["rows"]
    families = bank["families"]
    saturated = {
        threshold: sum(c["saturated_" + threshold + "_rows"] for c in bank["by_z"].values())
        for threshold in ("90", "99")
    }
    return {
        "rows": n,
        "z_sse": bank["z_sse"],
        "row_z_mse": bank["z_sse"] / n if n else None,
        "canonical_family_count": len(families) if bank["family_bound"] else None,
        "canonical_family_z_mse": sum(v[1] / v[0] for v in families.values()) / len(families)
        if families
        else None,
        "z_sign": {
            key: {
                **counts,
                "mean_abs_post": counts["absolute_post_sum"] / counts["rows"]
                if counts["rows"]
                else None,
            }
            for key, counts in bank["by_z"].items()
        },
        "decisive_rows": bank["by_z"]["-1"]["rows"] + bank["by_z"]["1"]["rows"],
        "decisive_correct_sign_rows": bank["by_z"]["-1"]["prediction_negative_rows"]
        + bank["by_z"]["1"]["prediction_positive_rows"],
        "decisive_prediction_zero_rows": bank["by_z"]["-1"]["prediction_zero_rows"]
        + bank["by_z"]["1"]["prediction_zero_rows"],
        "draw_rows": bank["by_z"]["0"]["rows"],
        "draw_mean_abs_post": bank["by_z"]["0"]["absolute_post_sum"] / bank["by_z"]["0"]["rows"]
        if bank["by_z"]["0"]["rows"]
        else None,
        **{"saturated_" + k + "_rows": v for k, v in saturated.items()},
        **{"saturation_" + k + "_fraction": v / n if n else None for k, v in saturated.items()},
    }


def train_mixture(cache, output, config_path, input_binding, cfg):
    manifest, acceptance, counts, model_inputs = admit(cache, config_path, input_binding, cfg)
    import numpy as np
    import torch
    from .compact_cache import IndexedPublicCorpus
    from .terminal_cache import TerminalCorpus
    from .sampling import (
        FullBatchSampler,
        family_training_view,
        diagnostic_indices,
        indexed_public_sample,
    )
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
    public_policy = public_observation_policy(m)
    added = public = model = optimizer = teacher_values = None
    outcome_column = None
    attempted_stream = hashlib.sha256()
    completed_stream = hashlib.sha256()
    stream_rows = stream_updates = 0
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
    initial_observation = None
    public_selection_candidates = 0
    public_selected_by_file = public_completed_by_file = None
    public_selection_state = "NOT_ENTERED"

    def facts():
        return {
            "teacher_values": teacher_values.binding if teacher_values is not None else None,
            "stream_identity": {
                "attempted_sha256": attempted_stream.hexdigest(),
                "completed_sha256": completed_stream.hexdigest(),
                "completed_rows": stream_rows,
                "completed_updates": stream_updates,
                "encoding": "per-update LE-i64 [update,nAdded,nPublic], added IDs, public IDs, uint8 added/public LR masks",
                "numpy_version": np.__version__,
                "torch_version": torch.__version__,
                "added_rng": "numpy.default_rng/PCG64",
            },
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
            "public_selection_candidate_rows": public_selection_candidates,
            "public_selected_by_file": public_selected_by_file,
            "public_completed_by_file": public_completed_by_file,
            "public_selection_state": public_selection_state,
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
            "z_error": 0.0,
            "z_sign_rows": 0,
            "z_correct": 0,
            "sign_rows": 0,
            "correct": 0,
            "saturated": 0,
            "constant": 0.0,
            "distance": 0.0,
            "draw_rows": 0,
            "draw_absolute_value": 0.0,
        }
        families, strata, games = {}, {}, {}
        outcome_slices = {}
        calibration = [[0, 0.0, 0.0, 0.0, 0.0] for _ in range(10)]
        reference_totals = {}
        model.eval()
        with torch.no_grad():
            for first in range(0, len(indices), e["batch_size"]):
                sub = indices[first : first + e["batch_size"]]
                if name.startswith("added_"):
                    x, d, targets = added.batch(sub)
                    z = targets[:, outcome_column]
                    y = z if teacher_values is None else teacher_values.take(sub)
                else:
                    x, d, y = public.batch(
                        "train" if name in ("public_train", "public_full_train") else "validation",
                        sub,
                    )
                    z = y
                p = forward(x, d).detach().cpu().numpy().astype(np.float64)
                yf = y.astype(np.float64)
                continuous_target = (
                    name.startswith("added_")
                    and teacher_values is not None
                    and teacher_values.metadata[teacher_values.objective]["source"] == "sidecar"
                )
                if (
                    not np.isfinite(yf).all()
                    or np.any(np.abs(yf) > 1)
                    or (not continuous_target and not np.isin(y, (-1, 0, 1)).all())
                ):
                    raise ValueError("finite local STM target in [-1,1]")
                zd = z.astype(np.float64)
                _add_outcome_slice(
                    outcome_slices.setdefault("all", {}),
                    p,
                    zd,
                    added.groups[sub] if name.startswith("added_") else None,
                )
                z_decisive = zd != 0
                totals["z_error"] += float(((p - zd) ** 2).sum())
                totals["z_sign_rows"] += int(z_decisive.sum())
                totals["z_correct"] += int((p[z_decisive] * zd[z_decisive] > 0).sum())
                outcome_name = (
                    teacher_values.outcome_name
                    if name.startswith("added_") and teacher_values is not None
                    else t["target"]
                )
                references = {outcome_name: zd}
                if name.startswith("added_") and teacher_values is not None:
                    references.update(
                        {
                            target: teacher_values.take(sub, target=target).astype(np.float64)
                            for target in teacher_values.values
                        }
                    )
                bins = np.minimum(9, np.maximum(0, ((p + 1) * 5).astype(np.int64)))
                for target, reference in references.items():
                    bank = reference_totals.setdefault(
                        target,
                        {
                            "rows": 0,
                            "sse": 0.0,
                            "sign_rows": 0,
                            "sign_agree": 0,
                            "target_sum": 0.0,
                            "bins": [[0, 0.0, 0.0] for _ in range(10)],
                        },
                    )
                    decisive_reference = reference != 0
                    bank["rows"] += len(reference)
                    bank["sse"] += float(((p - reference) ** 2).sum())
                    bank["sign_rows"] += int(decisive_reference.sum())
                    bank["sign_agree"] += int(
                        (p[decisive_reference] * reference[decisive_reference] > 0).sum()
                    )
                    bank["target_sum"] += float(reference.sum())
                    for j in range(10):
                        take = bins == j
                        bank["bins"][j][0] += int(take.sum())
                        bank["bins"][j][1] += float(p[take].sum())
                        bank["bins"][j][2] += float(reference[take].sum())
                error = (p - yf) ** 2
                for j in range(10):
                    bins = np.minimum(9, np.maximum(0, ((p + 1) * 5).astype(np.int64)))
                    take = bins == j
                    calibration[j][0] += int(take.sum())
                    calibration[j][1] += float(((p[take] + 1) / 2).sum())
                    calibration[j][2] += float(((yf[take] + 1) / 2).sum())
                    calibration[j][3] += float(p[take].sum())
                    calibration[j][4] += float(yf[take].sum())
                decisive = yf != 0
                totals["draw_rows"] += int((~decisive).sum())
                totals["draw_absolute_value"] += float(np.abs(p[~decisive]).sum())
                totals["rows"] += len(y)
                totals["error"] += float(error.sum())
                totals["sign_rows"] += int(decisive.sum())
                totals["correct"] += int((p[decisive] * yf[decisive] > 0).sum())
                totals["saturated"] += int((np.abs(p) >= 0.9).sum())
                if constant is not None:
                    totals["constant"] += float(((constant - yf) ** 2).sum())
                analytic = np.tanh(np.float32(8) * (d[:, 1] - d[:, 0]))
                totals["distance"] += float(((analytic.astype(np.float64) - yf) ** 2).sum())
                if name.startswith("added_"):
                    groups = added.groups[sub]
                    for g in np.unique(groups):
                        bank = families.setdefault(added.families[int(g)], [0, 0.0, 0, 0, 0.0, 0.0])
                        take = groups == g
                        bank[0] += int(take.sum())
                        bank[1] += float(error[take].sum())
                        bank[2] += int((take & decisive).sum())
                        bank[3] += int((take & decisive & (p * yf > 0)).sum())
                        bank[4] += float(p[take].sum())
                        bank[5] += float(yf[take].sum())
                    if hasattr(added, "row_game_codes"):
                        game_codes = added.row_game_codes[sub]
                        for code in np.unique(game_codes):
                            take = game_codes == code
                            bank = games.setdefault(str(int(code)), [0, 0.0, 0, 0, 0.0, 0.0])
                            bank[0] += int(take.sum())
                            bank[1] += float(error[take].sum())
                            bank[2] += int((take & decisive).sum())
                            bank[3] += int((take & decisive & (p * yf > 0)).sum())
                            bank[4] += float(p[take].sum())
                            bank[5] += float(yf[take].sum())
                    stock = (
                        added.maps[0]["geometry"]["stocks"][sub].sum(axis=1)
                        if m["train_stock_strata"] is not None
                        else None
                    )
                    for band in m["train_stock_strata"] or []:
                        take = (stock >= band["min"]) & (stock <= band["max"])
                        label = f"{band['min']}..{band['max']}"
                        _add_outcome_slice(
                            outcome_slices.setdefault(label, {}), p[take], zd[take], groups[take]
                        )
                        bank = strata.setdefault(label, [0, 0.0, 0, 0, 0.0, 0.0])
                        bank[0] += int(take.sum())
                        bank[1] += float(error[take].sum())
                        bank[2] += int((take & decisive).sum())
                        bank[3] += int((take & decisive & (p * yf > 0)).sum())
                        bank[4] += float(p[take].sum())
                        bank[5] += float(yf[take].sum())
        n = totals["rows"]
        if not n:
            raise ValueError("empty observation scope")
        return {
            "rows": n,
            "outcome_slices": {
                label: _outcome_slice_result(bank) for label, bank in outcome_slices.items()
            },
            "reference_targets": {
                target: {
                    "rows": bank["rows"],
                    "mse": bank["sse"] / bank["rows"],
                    "sign_agreement": bank["sign_agree"] / bank["sign_rows"]
                    if bank["sign_rows"]
                    else None,
                    "sign_rows": bank["sign_rows"],
                    "mean_target": bank["target_sum"] / bank["rows"],
                    "numeric_calibration_bins": bank["bins"],
                    "display_name": teacher_values.metadata[target]["display_name"]
                    if name.startswith("added_") and teacher_values is not None
                    else target,
                    "semantics": teacher_values.metadata[target]["value_semantics"]
                    if name.startswith("added_") and teacher_values is not None
                    else "literal-stm-outcome",
                }
                for target, bank in reference_totals.items()
            },
            "reference_teacher_availability": "fixed common T/V only; external public scopes have original z only",
            "mse": totals["error"] / n,
            "target_semantics": "raw teacher value/sign agreement; zero is not certified draw"
            if name.startswith("added_")
            and teacher_values is not None
            and teacher_values.metadata[teacher_values.objective]["source"] != "cache"
            else "literal terminal z",
            "calibration_semantics": "numeric target-bin means; teacher values are not calibrated WDL"
            if name.startswith("added_")
            and teacher_values is not None
            and teacher_values.metadata[teacher_values.objective]["source"] != "cache"
            else "literal z outcome-bin means",
            "z_mse": totals["z_error"] / n,
            "z_sign_rows": totals["z_sign_rows"],
            "z_sign_accuracy": totals["z_correct"] / totals["z_sign_rows"]
            if totals["z_sign_rows"]
            else None,
            "sign_rows": totals["sign_rows"],
            "draw_rows": totals["draw_rows"],
            "draw_mean_absolute_value": totals["draw_absolute_value"] / totals["draw_rows"]
            if totals["draw_rows"]
            else None,
            "sign_accuracy": totals["correct"] / totals["sign_rows"]
            if totals["sign_rows"]
            else None,
            "saturation_fraction": totals["saturated"] / n,
            "constant_mse": totals["constant"] / n if constant is not None else None,
            "analytic_D_mse": totals["distance"] / n,
            "families": {
                k: {
                    "rows": v[0],
                    "mse": v[1] / v[0],
                    "sign_rows": v[2],
                    "sign_accuracy": v[3] / v[2] if v[2] else None,
                    "mean_prediction": v[4] / v[0],
                    "mean_target": v[5] / v[0],
                }
                for k, v in families.items()
            },
            "family_mse": sum(v[1] / v[0] for v in families.values()) / len(families)
            if families
            else None,
            "games": {
                k: {
                    "rows": v[0],
                    "sse": v[1],
                    "mse": v[1] / v[0],
                    "sign_rows": v[2],
                    "correct_sign_rows": v[3],
                    "prediction_sum": v[4],
                    "target_sum": v[5],
                }
                for k, v in games.items()
            },
            "game_key_kind": "TerminalCorpus.row_game_codes",
            "stock_strata": {
                k: {
                    "rows": v[0],
                    "mse": v[1] / v[0] if v[0] else None,
                    "sign_rows": v[2],
                    "sign_accuracy": v[3] / v[2] if v[2] else None,
                    "mean_prediction": v[4] / v[0] if v[0] else None,
                    "mean_target": v[5] / v[0] if v[0] else None,
                }
                for k, v in strata.items()
            },
            "calibration": [
                {
                    "lower": j / 10,
                    "upper": (j + 1) / 10,
                    "rows": v[0],
                    "mean_probability": v[1] / v[0] if v[0] else None,
                    "mean_outcome_probability": v[2] / v[0] if v[0] else None,
                    "lower_value": -1 + j / 5,
                    "upper_value": -1 + (j + 1) / 5,
                    "mean_value": v[3] / v[0] if v[0] else None,
                    "mean_z": v[4] / v[0] if v[0] else None,
                }
                for j, v in enumerate(calibration)
            ],
        }

    def observe():
        reused = initial_observation if step == 0 else None
        record = {
            "step": step,
            "scopes": reused["scopes"]
            if reused is not None
            else {
                name: evaluate(name, indices, constants[name.split("_")[0]])
                for name in plan["scopes_by_step"][step]
                for indices in (scopes[name],)
            },
            **facts(),
        }
        if reused is not None:
            record["reused_initial_observation"] = initial_observation_ref
        elif step == 0:
            write(
                output / "initial-observation.json",
                {"binding": observation_binding, "scopes": record["scopes"]},
            )
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
                record["scopes"]["added_validation"][m["selector"]["added_metric"]],
                record["scopes"].get("public_validation", {}).get("mse"),
            )
        if improved:
            result["best_descriptor"] = save_checkpoint("best")
            result["best_step"] = step
        budget.check()
        return stop

    try:
        with cancellation_signals():
            added = TerminalCorpus(cache)
            outcome_column = added.manifest["label_columns"].index(t["target"])
            public = IndexedPublicCorpus(m["public_membership"], acceptance)
            train_rows = family_training_view(
                added.groups,
                added.splits,
                added.eligible,
                m["train_family_row_cap"],
                games=added.row_game_codes if m["train_stock_strata"] is not None else None,
                stock=added.maps[0]["geometry"]["stocks"].sum(axis=1)
                if m["train_stock_strata"] is not None
                else None,
                strata=m["train_stock_strata"],
            )
            train_rows = np.asarray(
                training_view_indices(m.get("training_view"), added.manifest_sha, train_rows),
                dtype=np.int64,
            )
            validation_rows = np.flatnonzero(added.eligible & (added.splits == 1))
            if m.get("teacher_values") is not None:
                from .teacher_values import TeacherValues

                teacher_values = TeacherValues(
                    m["teacher_values"], added, train_rows, validation_rows
                )
                if teacher_values.outcome_column != outcome_column:
                    raise ValueError(
                        "configured original outcome provenance differs from label manifest"
                    )
            initial_observation_ref = (
                json.loads(Path(input_binding).read_bytes())
                .get("files", {})
                .get("initial_observation")
                if input_binding is not None
                else None
            )
            plan = planned_work(
                cfg,
                len(train_rows),
                len(validation_rows),
                counts,
                reuse_initial=initial_observation_ref is not None,
            )
            if plan["forward_upper"] > cfg["limits"]["samples"]:
                raise ValueError("configured complete-work forward upper exceeds samples")
            scopes = {
                "added_train": diagnostic_indices(
                    added.rows, train_rows, e["diagnostic_rows"], m["diagnostic_seed"]
                ),
                "added_validation": validation_rows,
                "public_train": random.Random(m["diagnostic_seed"]).sample(
                    range(counts["train"]), min(e["diagnostic_rows"], counts["train"])
                )
                if public_policy["train_diagnostic"]
                else [],
                "public_validation": range(counts["validation"]),
                "added_full_train": train_rows,
                "public_full_train": range(counts["train"]),
            }
            # Public constant is derived only from the configured T diagnostic,
            # not the entire public T or any V labels. Its scope is recorded.
            constants = {
                "added": float(
                    np.mean(
                        (
                            added.labels[train_rows, outcome_column]
                            if teacher_values is None
                            else teacher_values.take(train_rows)
                        ).astype(np.float64)
                    )
                ),
                "public": None,
            }
            public_sum = 0.0
            for first in range(0, len(scopes["public_train"]), e["batch_size"]):
                _, _, y = public.batch(
                    "train", scopes["public_train"][first : first + e["batch_size"]]
                )
                public_sum += float(y.astype(np.float64).sum())
            if scopes["public_train"]:
                constants["public"] = public_sum / len(scopes["public_train"])
            selector = Selector(
                m["selector"]["public_non_regression"],
                e["early_stopping_patience"],
                e["min_delta"],
                e["min_delta_relative"],
            )
            observation_binding = {
                **(
                    {"teacher_values": teacher_values.binding} if teacher_values is not None else {}
                ),
                "warm_start": initial,
                "statistics": model_inputs["statistics"],
                "cache_manifest_sha256": added.manifest_sha,
                "public_membership": m["public_membership"],
                "evaluation_batch_size": e["batch_size"],
                "stock_strata": m["train_stock_strata"],
                "scopes": {
                    name: {
                        "rows": len(indices),
                        "index_sha256": hashlib.sha256(
                            np.asarray(indices, dtype="<i8").tobytes()
                        ).hexdigest(),
                    }
                    for name, indices in scopes.items()
                    if name in plan["scopes_by_step"][0]
                },
                "constants": constants,
            }
            if initial_observation_ref is not None:
                initial_observation = json.loads(
                    bound_file_bytes(initial_observation_ref, 16 * 1024**2)
                )
                initial_observation["scopes"] = initial_observation_scopes(
                    initial_observation, observation_binding
                )
                for name, value in initial_observation["scopes"].items():
                    if (
                        value["rows"] != observation_binding["scopes"][name]["rows"]
                        or not math.isfinite(value["mse"])
                        or (
                            name == "added_validation"
                            and not math.isfinite(value[m["selector"]["added_metric"]])
                        )
                    ):
                        raise ValueError("shared INITIAL finite scope denominator")
            sampler = FullBatchSampler(
                train_rows, max(1, m["added_rows"]), m["added_sampling_seed"]
            )
            public_rng = np.random.default_rng(m["public_sampling_seed"])
            acceptance_rng = (
                np.random.default_rng(m["public_acceptance_seed"])
                if m.get("public_file_decay") is not None
                else None
            )
            added_rng, public_reflection_rng = reflection_generators(m)
            write(
                output / "training-view.json",
                {
                    "cache_manifest_sha256": added.manifest_sha,
                    "indices": train_rows.tolist(),
                    **(
                        {"training_view": m["training_view"]}
                        if m.get("training_view") is not None
                        else {}
                    ),
                    "train_family_row_cap": m["train_family_row_cap"],
                    "stock_strata": m["train_stock_strata"],
                    "validation_rows": len(validation_rows),
                },
            )
            visits = np.zeros(added.row_count, dtype=np.uint64)
            public_visits = {}
            reflected = {"added": 0, "public": 0}
            model = build_model(cfg["model"], model_inputs["statistics"]).to(device)
            if initial["weights"] is not None:
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
                best_descriptor=initial["descriptor"]
                if initial["weights"] is not None
                else save_checkpoint("initial"),
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
                batch_rows = min(
                    t["batch_size"], plan["training_forwards"] - step * t["batch_size"]
                )
                added_count = (
                    m["added_rows"]
                    if batch_rows == t["batch_size"]
                    else (batch_rows if not m["public_rows"] else 0)
                )
                public_count = batch_rows - added_count
                ai = sampler.take(added_count) if added_count else np.asarray([], dtype=np.int64)
                public_selection_state = "IN_PROGRESS_UNKNOWN"
                pi, selection = indexed_public_sample(
                    public,
                    public_rng,
                    public_count,
                    counts["train"],
                    m.get("public_file_decay"),
                    budget.check,
                    acceptance_rng=acceptance_rng,
                )
                public_selection_state = "RETURNED_INDEXED_SELECTION"
                public_selection_candidates += selection["candidate_rows"]
                if "accepted_by_file" in selection:
                    if public_selected_by_file is None:
                        public_selected_by_file = [0] * len(selection["accepted_by_file"])
                        public_completed_by_file = [0] * len(selection["accepted_by_file"])
                    public_selected_by_file = [
                        a + b
                        for a, b in zip(public_selected_by_file, selection["accepted_by_file"])
                    ]
                am = added_rng.random(len(ai)) < m["added_reflection_probability"]
                pm = public_reflection_rng.random(len(pi)) < m["public_reflection_probability"]
                attempted_added += len(ai)
                attempted_public += len(pi)
                stream_parts = (
                    np.asarray([update, len(ai), len(pi)], dtype="<i8").tobytes(),
                    np.asarray(ai, dtype="<i8").tobytes(),
                    np.asarray(pi, dtype="<i8").tobytes(),
                    am.astype("u1").tobytes(),
                    pm.astype("u1").tobytes(),
                )
                for part in stream_parts:
                    attempted_stream.update(part)
                x, d, y = mixed_batch(
                    added,
                    public,
                    ai,
                    pi,
                    np.concatenate((am, pm)),
                    target_column=outcome_column,
                    teacher_values=teacher_values,
                )
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
                for part in stream_parts:
                    completed_stream.update(part)
                stream_rows += len(ai) + len(pi)
                stream_updates += 1
                step = update
                current_update_state = "VERIFIED_COMPLETED_UPDATE"
                rates.append(rate)
                seen_added += len(ai)
                seen_public += len(pi)
                if "accepted_by_file" in selection:
                    public_completed_by_file = [
                        a + b
                        for a, b in zip(public_completed_by_file, selection["accepted_by_file"])
                    ]
                np.add.at(visits, ai, 1)
                for i in pi:
                    public_visits[int(i)] = public_visits.get(int(i), 0) + 1
                reflected["added"] += int(am.sum())
                reflected["public"] += int(pm.sum())
                if step in plan["observation_steps"] and observe():
                    result["stop_reason"] = "early_stopping"
                    break
            if public_policy["validation"] == "last":
                result["frozen_last_public_validation"] = {
                    "checkpoint_step": step,
                    "endpoint": "LAST",
                    "metrics": evaluate("public_validation", scopes["public_validation"], None),
                }
            if public_policy["validation"] == "best":
                # Observe the frozen BEST without mutating the live LAST model or
                # optimizer. Reuse the same maintained model builder and loader.
                best_model = build_model(cfg["model"], model_inputs["statistics"]).to(device)
                if result["best_step"] == 0 and initial["weights"] is not None:
                    best_weights = initial["weights"]
                else:
                    descriptor_path = Path(result["best_descriptor"])
                    descriptor = json.loads(descriptor_path.read_bytes())
                    weights_path = descriptor_path.parent / descriptor["weights"]
                    best_weights = {
                        "path": str(weights_path),
                        "sha256": descriptor["weights_SHA"],
                        "bytes": descriptor["weights_B"],
                        "mode": f"{weights_path.stat().st_mode & 0o7777:04o}",
                    }
                restore_warmstart_parameters(best_model, best_weights)
                live_model = model
                try:
                    model = best_model
                    result["frozen_best_public_validation"] = {
                        "checkpoint_step": result["best_step"],
                        "descriptor": result["best_descriptor"],
                        "metrics": evaluate("public_validation", scopes["public_validation"], None),
                    }
                finally:
                    model = live_model
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
                public_file_decay=m.get("public_file_decay"),
                public_selection_candidate_rows=public_selection_candidates,
                selection={
                    "public_non_regression": selector.gate,
                    "added_metric": m["selector"]["added_metric"],
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
        if visits is not None and public_visits is not None:

            def save_exposure():
                np.savez_compressed(
                    output / "exposure.npz",
                    added_visits=visits,
                    public_indices=np.asarray(list(public_visits), dtype=np.int64),
                    public_visits=np.asarray(list(public_visits.values()), dtype=np.uint64),
                )

            actions.append(("completed_update_exposure", save_exposure))
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
