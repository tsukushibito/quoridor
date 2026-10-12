"""Raw-distance-step experiment contract; NN0 import, no implicit dataset/model job."""

import copy
import math
import json
import hashlib
from pathlib import Path

SCORE_SCHEMA = "quoridor-nnue-distance-step-v1"
CONDITIONS = {
    "A": ("outcome_steps", True, "F"),
    "B": ("terminal_margin", True, "F"),
    "C": ("outcome_steps", True, "raw"),
    "D": ("outcome_steps", False, "F"),
}
VIEWS = {
    "A-F": ("A", "F"),
    "A-raw": ("A", "raw"),
    "B-F": ("B", "F"),
    "C-raw": ("C", "raw"),
    "C-F": ("C", "F"),
    "D-F": ("D", "F"),
}


def recipe(condition, main_volume_N=None):
    if condition not in CONDITIONS:
        raise ValueError("explicit A/B/C/D condition required")
    target, bypass, transform = CONDITIONS[condition]
    return {
        "model": {
            "architecture": "distance_steps",
            "distance_bypass": bypass,
            "train_transform": transform,
            "deploy_transform": transform,
            "transformer_width": 32,
            "hidden_width": 32,
            "dropout": 0,
        },
        "optimizer": {"name": "adam", "lr": 0.01, "weight_decay": 0},
        "training": {
            "steps": None,
            "batch_size": 2048,
            "seed": 19080311,
            "target": target,
            "sampling": "epoch",
            "loss_weighting": "row",
            "scheduler": "plateau",
            "warmup_steps": 257,
            "lr_decay_factor": 0.5,
            "lr_decay_patience": 1,
            "min_lr": 1e-6,
            "reflection_probability": 0.5,
            "reflection_seed": 19080314,
            "supply_workers": 2,
        },
        "evaluation": {
            "monitor": "row",
            "early_stopping_patience": 8,
            "early_stopping_unit": "epoch",
            "min_delta": 1e-8,
            "min_delta_relative": 1e-4,
            "full_train": False,
        },
        "limits": {"seconds": None, "samples": None},
        "artifacts": {"mode": "native"},
        "experiment": {
            "condition": condition,
            "main_volume_N": main_volume_N,
            "main_volume_manifest": None,
            "main_volume_manifest_sha256": None,
        },
    }


def _sha256(value):
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("explicit SHA256 required")
    return value


def bound_json(path, digest):
    """Read a control record once; bind the exact bytes used for admission."""
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != _sha256(digest):
        raise ValueError("control record SHA256 mismatch: " + str(path))
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("control record object required")
    return result


def recipe_sha256(config):
    """Condition-specific resolved recipe, independent of permit path/quantity."""
    value = {k: v for k, v in config.items() if k != "experiment"}
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def require_main_volume(
    config,
    *,
    cache=None,
    config_path=None,
    input_binding=None,
    scale_path=None,
    supply_workers=None,
):
    """Bind N and common controls before frameworks, corpus, child or output."""
    if config["model"]["architecture"] != "distance_steps":
        return
    experiment = config["experiment"]
    if (
        type(experiment["main_volume_N"]) is not int
        or experiment["main_volume_N"] <= 0
        or not experiment["main_volume_manifest"]
    ):
        raise ValueError(
            "human full-generation N and frozen main-volume manifest are unset; four fits are not admitted"
        )
    if scale_path is not None or (
        supply_workers is not None and (type(supply_workers) is not int or supply_workers != 2)
    ):
        raise ValueError(
            "new fit requires common T-only scale and fixed supply workers2; overrides refused"
        )
    if cache is None or config_path is None or input_binding is None:
        raise ValueError("new fit requires actual cache/config and mandatory common input binding")
    permit_sha = _sha256(experiment.get("main_volume_manifest_sha256"))
    manifest = bound_json(experiment["main_volume_manifest"], permit_sha)
    if (
        manifest.get("scope") != "full-volume"
        or manifest.get("human_quantity_N") != experiment["main_volume_N"]
        or manifest.get("planned_games") != experiment["main_volume_N"]
    ):
        raise ValueError(
            "full-volume manifest must bind the explicit human N; pilot is not a fit corpus"
        )
    descriptor = manifest["common_input_freeze"]
    common = bound_json(descriptor["path"], descriptor["sha256"])
    input_binding_bytes = Path(input_binding).read_bytes()
    expected = json.loads(input_binding_bytes)
    if not isinstance(expected, dict):
        raise ValueError("common input binding object required")
    cache_path = Path(cache) / "cache.json"
    cache_manifest = bound_json(cache_path, common["cache_manifest_sha"])
    require_completed_stream_cache(cache, cache_manifest, full_volume=True)
    if cache_manifest["stream_intake"]["human_quantity_n"] != experiment["main_volume_N"]:
        raise ValueError("cache intake volume differs from accepted N")
    schedule = bound_json(common["schedule"]["path"], common["schedule"]["sha256"])
    initial = common["initialization"]
    condition = experiment["condition"]
    constant = common["constants"][condition]
    if (
        common.get("scope") != "full-volume"
        or common.get("human_quantity_N") != experiment["main_volume_N"]
        or schedule.get("planned_games") != experiment["main_volume_N"]
        or cache_manifest.get("schema") != "quoridor-terminal-geometry-v1"
        or cache_manifest.get("source_binding") != common["dataset"]
        or cache_manifest.get("schedule_sha256") != common["schedule"]["sha256"]
        or cache_manifest.get("family_partition_sha256")
        != _sha256(common["family_partition_sha256"])
        or schedule.get("family_partition_sha256") != common["family_partition_sha256"]
        or set(common["recipes_sha256"]) != set(CONDITIONS)
        or common["recipes_sha256"][condition] != recipe_sha256(config)
        or initial.get("seed") != config["training"]["seed"]
        or initial.get("zero_output_head") is not True
        or expected.get("initial_weights_sha") != _sha256(initial["ordered_parameters_sha256"])
        or expected.get("main_volume_manifest_sha256") != permit_sha
        or expected.get("common_input_freeze") != descriptor
        or expected.get("cache_manifest_sha") != common["cache_manifest_sha"]
        or expected.get("fit_config_sha")
        != hashlib.sha256(Path(config_path).read_bytes()).hexdigest()
        or expected.get("scale_artifact") != common["scale"]["path"]
        or expected.get("scale_artifact_sha") != common["scale"]["sha256"]
        or expected.get("constant_artifact") != constant["path"]
        or expected.get("constant_artifact_sha") != _sha256(constant["sha256"])
    ):
        raise ValueError(
            "main volume/cache/dataset/schedule/common recipe/initialization binding mismatch"
        )
    _sha256(common["dataset"]["sha256"])
    if not isinstance(common["dataset"].get("path"), str) or not common["dataset"]["path"]:
        raise ValueError("explicit dataset source path required")
    scale = bound_json(common["scale"]["path"], common["scale"]["sha256"])
    if (
        scale.get("fit_partition") != "train"
        or scale.get("target_independent") is not True
        or scale.get("original_before_reflection") is not True
        or scale.get("distance_input_units") != "canonical-integer-D/80"
    ):
        raise ValueError("common T-only statistics provenance required")
    return {
        "permit_sha256": permit_sha,
        "common_input_freeze": descriptor,
        "expected": expected,
        "statistics": scale,
        "cache_manifest_sha": common["cache_manifest_sha"],
        "input_binding_sha256": hashlib.sha256(input_binding_bytes).hexdigest(),
    }


def verify_main_statistics(admission, statistics):
    if admission is not None and statistics != admission["statistics"]:
        raise ValueError("actual eligible original T-only statistics differ from common freeze")


def require_completed_stream_cache(path, manifest, *, full_volume=False):
    """Pure control refusal before opening arrays, including finalization failure."""
    if any(
        ((Path(path) / name).exists() or (Path(path) / name).is_symlink())
        for name in ("intake-failure.json", "intake-incomplete.json", ".intake.partial")
    ):
        raise ValueError("failed/partial stream intake is not a cache")
    intake = manifest.get("stream_intake")
    if intake is None and not full_volume:
        return  # Existing non-stream caches keep their qualified entry.
    if not isinstance(intake, dict) or intake.get("status") != "complete":
        raise ValueError("complete authoritative stream cache required")
    if full_volume and (
        intake.get("scope") != "full-volume"
        or type(intake.get("human_quantity_n")) is not int
        or intake["human_quantity_n"] <= 0
    ):
        raise ValueError("human full N is unset; reference/fixture cache cannot fit")
    if intake.get("publication_protocol") != "incomplete-marker-last-v1":
        raise ValueError("completed stream publication protocol required")
    if manifest.get("schema") == "quoridor-common-corpus-terminal-geometry-v3":
        if intake.get("scope") != "common-corpus":
            raise ValueError("compressed common cache requires explicit common scope")
        phase = "common_corpus"  # Detailed source/config was joined once at publication.
    else:
        phase = intake.get("provenance", {}).get("header", {}).get("config", {}).get("phase")
    if intake.get("scope") != "synthetic-fixture":
        header = intake.get("provenance", {}).get("header", {})
        marker = header.get("resource_admission", {}).get("synthetic_fixture", False)
        if marker is not False or any(
            not isinstance(v, str) or "synthetic" in v or "fixture" in v
            for v in (header.get("generator_version"), phase)
        ):
            raise ValueError(
                "synthetic/missing provenance cannot be authoritative full volume/reference"
            )


def validate_condition(config):
    c = config["experiment"]["condition"]
    if c not in CONDITIONS:
        raise ValueError("distance-step condition A/B/C/D required")
    target, bypass, transform = CONDITIONS[c]
    if (
        config["training"]["target"],
        config["model"]["distance_bypass"],
        config["model"]["train_transform"],
    ) != (target, bypass, transform):
        raise ValueError("condition teacher/bypass/training transform mismatch")
    if type(config["model"]["distance_bypass"]) is not bool or config["model"][
        "deploy_transform"
    ] not in ("F", "raw"):
        raise ValueError("explicit score view")
    if (
        config["model"]["transformer_width"] != 32
        or config["model"]["hidden_width"] != 32
        or config["model"]["dropout"] != 0
    ):
        raise ValueError("distance-step contract requires FT32/H32/Zero4/dropout0")
    if config["artifacts"]["mode"] != "native":
        raise ValueError(
            "new experiment uses its explicit native score/view export, not an implicit ONNX path"
        )
    # Freeze method now; data/scale/recipe manifest is finalized only after N.
    expected = recipe(c)
    for section in ("optimizer", "training", "evaluation", "limits"):
        for key, value in expected[section].items():
            if section == "training" and key == "warmup_steps":
                if not 0 <= config[section][key] <= 257:
                    raise ValueError("warmup must be min(257, updates_per_epoch)")
                continue
            if config[section][key] != value:
                raise ValueError("common fixed recipe mismatch: " + section + "." + key)


def view_manifest(config, name):
    if name not in VIEWS or VIEWS[name][0] != config["experiment"]["condition"]:
        raise ValueError("view does not belong to this fit")
    result = copy.deepcopy(config)
    result["model"]["deploy_transform"] = VIEWS[name][1]
    return result


def significant_improvement(value, reference, absolute=1e-8, relative=1e-4):
    if not math.isfinite(value) or math.isnan(reference) or reference == -math.inf:
        raise ValueError("nonfinite selector metric")
    return reference == math.inf or value < reference - max(absolute, relative * abs(reference))


def transform_score(score, transform):
    if not math.isfinite(score) or transform not in ("F", "raw"):
        raise ValueError("finite score and explicit output transform required")
    return 80 * math.tanh(score / 80) if transform == "F" else score


def build_model(config, statistics, *, deployed=False):
    """One maintained residual head, fresh initialization; integer bypass is explicit."""
    import torch
    from .residual_model import DistanceResidualModel

    class DistanceStepModel(DistanceResidualModel):
        def forward(self, x, distance, side, integer_distance):
            if integer_distance.ndim != 2 or integer_distance.shape != distance.shape:
                raise ValueError("canonical integer STM/opponent distance shape")
            if (
                not torch.isfinite(integer_distance).all()
                or (integer_distance < 0).any()
                or (integer_distance > 80).any()
                or (integer_distance != integer_distance.round()).any()
            ):
                raise ValueError(
                    "canonical integer wall distance required; no rounded-feature reconstruction"
                )
            _, residual = self.residual_components(x, distance, side)
            score = residual
            if config["distance_bypass"]:
                score = integer_distance[:, 1] - integer_distance[:, 0] + score
            if config["deploy_transform" if deployed else "train_transform"] == "F":
                score = 80 * torch.tanh(score / 80)
            return score

    return DistanceStepModel(config, statistics, a=0, b=1)


def nonterminal_bound(arrays, statistics, bypass):
    """Native legal envelope, including at most200 general delta transitions.

    Positive norms advance outwards in FP64. Every FP32 operation is allowed
    full epsilon and minimum subnormal growth, then rounded up to FP32. Counts
    match native LegalEnvelope, including no-FMA head reductions. This is only
    serialization/range metadata; forward and training arithmetic are unchanged.
    """
    import numpy as np

    ft_w, ft_b, h_w, h_b, out_w, out_b = arrays
    if (
        ft_w.shape != (32, 312)
        or h_w.shape != (32, 70)
        or out_w.shape != (1, 32)
        or ft_b.shape != (32,)
        or h_b.shape != (32,)
        or out_b.shape != (1,)
    ):
        raise ValueError("score bound topology")
    if any(a.dtype != np.dtype("float32") or not np.isfinite(a).all() for a in arrays):
        raise ValueError("finite FP32 parameters required")
    if type(bypass) is not bool:
        raise ValueError("explicit distance bypass required")
    mu, sigma = statistics["mu_f32"], statistics["sigma_f32"]
    if (
        len(mu) != 2
        or len(sigma) != 2
        or not all(math.isfinite(float(v)) for v in (*mu, *sigma))
        or any(float(v) <= 0 for v in sigma)
        or any(float(np.float32(v)) != float(v) for v in (*mu, *sigma))
    ):
        raise ValueError("finite FP32 T-only scale required")

    def up(value):
        return value if value == 0 or not math.isfinite(value) else math.nextafter(value, math.inf)

    def add(a, b):
        return up(a + b)

    def mul(a, b):
        return up(a * b)

    growth_by_count = {}

    def rounded(norm, operations):
        if norm == 0:
            return 0.0
        if operations not in growth_by_count:
            growth = 1.0
            for _ in range(operations):
                growth = mul(growth, 1.0 + 2.0**-23)
            growth_by_count[operations] = growth
        underflow = mul(float(operations), 2.0**-149)
        upper = mul(add(norm, underflow), growth_by_count[operations])
        if not math.isfinite(upper) or upper < 0 or upper > float(np.finfo(np.float32).max) / 4:
            raise ValueError("unsafe/unrepresentable outward legal-input bound")
        result = np.float32(upper)
        if float(result) < upper:
            result = np.nextafter(result, np.float32(math.inf))
        value = float(result)
        if not math.isfinite(value) or value < 0 or value > float(np.finfo(np.float32).max) / 4:
            raise ValueError("unsafe/unrepresentable outward legal-input bound")
        return value

    additions = 24 + 48 * 200
    ft = [
        rounded(add(abs(float(b)), mul(float(additions), float(np.max(np.abs(w))))), additions)
        for w, b in zip(ft_w, ft_b, strict=True)
    ]
    dense = [
        rounded(up(rounded(add(1.0, abs(float(m))), 1) / float(s)), 1)
        for m, s in zip(mu, sigma, strict=True)
    ]
    inputs = ft + ft + dense + [0.0] * 4

    def norm(weights, bounds, bias):
        result = abs(float(bias))
        for weight, bound in zip(weights, bounds, strict=True):
            result = add(result, mul(abs(float(weight)), bound))
        return result

    hidden = [
        rounded(norm(w, inputs, b), 2 * len(inputs) + 16) for w, b in zip(h_w, h_b, strict=True)
    ]
    residual = rounded(norm(out_w[0], hidden, out_b[0]), 2 * len(hidden) + 16)
    return rounded(add(80.0, residual), 1) if bypass else residual
