"""Joint-target admission and checkpoint helpers for the existing train loop.

No optimizer/update loop, teacher implementation, feature encoding or search
lives here. The normal trainer and StaticHead remain the sole execution owners.
"""

import ctypes
import hashlib
import io
import json
import math
from pathlib import Path

from .common import bound_file_bytes


def settings(cfg):
    options = cfg["policy_value"]
    if set(options) != {
        "value_weight",
        "policy_weight",
        "temperature",
        "initial_head",
        "freeze",
        "selector",
        "checkpoint_bytes",
    }:
        raise ValueError("explicit joint policy/value settings required")
    for name in ("value_weight", "policy_weight", "temperature"):
        v = options[name]
        if type(v) not in (int, float) or not math.isfinite(v) or v < 0:
            raise ValueError("finite nonnegative joint setting: " + name)
    if (
        options["temperature"] <= 0
        or options["value_weight"] + options["policy_weight"] <= 0
        or options["policy_weight"] <= 0
        or options["initial_head"] not in ("synthetic_untrained", "load")
        or options["freeze"] not in ("none", "shared", "value")
        or options["selector"] not in ("joint_loss", "value_mse")
        or type(options["checkpoint_bytes"]) is not int
        or not 0 < options["checkpoint_bytes"] <= 64 * 1024**2
        or cfg["training"]["target"] != "static_teacher"
        or cfg["training"]["supply_workers"] != 0
        or cfg["evaluation"]["diagnostic_checkpoints"] != []
        or cfg["artifacts"]["checkpoint_steps"]
        or cfg["static_teacher"]["state_checkpoint_steps"]
        or cfg["static_teacher"]["initializer_seed"] != cfg["training"]["seed"]
    ):
        raise ValueError("joint static single-loop/native checkpoint conditions")
    return options


def native_identity(library, descriptor, policy=None):
    """Normal Rust value/head loaders own both identities; actual head rows=0."""
    path = str(Path(descriptor).resolve()).encode()
    policy_path = None if policy is None else str(Path(policy).resolve()).encode()
    if not path or len(path) > 4096 or (policy_path is not None and len(policy_path) > 4096):
        raise ValueError("bounded native descriptor/policy path")
    native = ctypes.CDLL(str(library))
    function = native.quoridor_public_nnue_identity
    pointer = ctypes.POINTER(ctypes.c_uint8)
    function.argtypes = [pointer, ctypes.c_size_t, pointer, ctypes.c_size_t, pointer]
    function.restype = ctypes.c_int
    raw = (ctypes.c_uint8 * len(path)).from_buffer_copy(path)
    policy_raw = (
        None
        if policy_path is None
        else (ctypes.c_uint8 * len(policy_path)).from_buffer_copy(policy_path)
    )
    output = (ctypes.c_uint8 * 64)()
    if (
        function(
            raw,
            len(path),
            policy_raw,
            0 if policy_path is None else len(policy_path),
            output,
        )
        != 0
    ):
        raise ValueError("normal native shared/policy identity refused")
    return {
        "shared": bytes(output[:32]).hex(),
        "policy": None if policy_path is None else bytes(output[32:]).hex(),
    }


def initialization(cfg, expected, corpus):
    from .scaled_model import validate_statistics

    options = settings(cfg)
    binding = expected["policy_value"]
    if set(binding) != {"initial_model", "initial_policy", "core_library", "restart"}:
        raise ValueError("joint initializer/library/restart binding fields")
    if not getattr(corpus, "policy_value", False):
        raise ValueError("joint configuration requires same-forward joint target bank")
    if corpus.policy_temperature != options["temperature"]:
        raise ValueError("target temperature differs from admitted configuration")
    model = binding["initial_model"]
    if set(model) != {"descriptor", "weights"}:
        raise ValueError("exact native initializer descriptor/weights binding")
    descriptor = json.loads(bound_file_bytes(model["descriptor"], 65536))
    if (
        descriptor["schema"] != "quoridor-nnue-distance-residual-v3"
        or descriptor["feature"] != "QF1-route4-f32-STM-scaled-residual-v3"
        or descriptor["topology"] != {"ft_width": 32, "hidden_width": 32}
        or descriptor["route_mode"] != "zero4"
        or descriptor["distance_fit"] != {"a": 0, "b": 0}
        or descriptor["value_perspective"] != "side-to-move"
        or descriptor["weights_SHA"] != model["weights"]["sha256"]
        or descriptor["weights_B"] != 49284
        or descriptor["little_endian_f32"] != 12321
        or (Path(model["descriptor"]["path"]).parent / descriptor["weights"]).resolve()
        != Path(model["weights"]["path"]).resolve()
        or expected["initial_weights_sha"] != model["weights"]["sha256"]
        or expected["initial_weights"] != model["weights"]
    ):
        raise ValueError("joint initializer architecture/value/weights/scale mismatch")
    bound_file_bytes(model["weights"], 49284)
    bound_file_bytes(binding["core_library"], 16 * 1024**2)
    fingerprint = native_identity(binding["core_library"]["path"], model["descriptor"]["path"])[
        "shared"
    ]
    return {
        "binding": binding,
        "settings": options,
        "statistics": validate_statistics(descriptor),
        "initial_shared_fingerprint": fingerprint,
        "native_identity_constructors": 1,
        "native_identity_head_rows": 0,
    }


def attach(model, joint):
    from .residual_model import load_policy_head
    from .train import restore_warmstart_parameters

    binding, options = joint["binding"], joint["settings"]
    restore_warmstart_parameters(model, binding["initial_model"]["weights"])
    if options["initial_head"] == "synthetic_untrained":
        if binding["initial_policy"] is not None:
            raise ValueError("synthetic head must not silently load an artifact")
        model.enable_policy_head(evidence="synthetic_untrained")
    else:
        raw = bound_file_bytes(binding["initial_policy"], 65536)
        # Validate the exact bound file before the existing owning loader reads it.
        if not isinstance(json.loads(raw), dict):
            raise ValueError("bound policy manifest object")
        load_policy_head(
            model,
            binding["initial_policy"]["path"],
            shared_fingerprint=joint["initial_shared_fingerprint"],
        )
    for name, parameter in model.named_parameters():
        shared = name.startswith(("ft.", "h."))
        value = name.startswith("out.")
        freeze = options["freeze"]
        parameter.requires_grad_(
            not ((shared and freeze in ("shared", "value")) or (value and freeze == "value"))
        )


def checkpoint_identity(cfg, corpus, joint):
    return {
        "config_sha256": hashlib.sha256(
            json.dumps(cfg, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest(),
        "dataset": corpus.binding,
        "initializer": joint["binding"]["initial_model"],
        "initial_policy": joint["binding"]["initial_policy"],
        "shared_fingerprint": joint["initial_shared_fingerprint"],
    }


def read_restart(cfg, corpus, joint):
    reference = joint["binding"]["restart"]
    if reference is None:
        return None
    import torch

    if set(reference) != {"checkpoint", "run_status"}:
        raise ValueError("restart binds original checkpoint AND actual stopped run status")
    status = json.loads(bound_file_bytes(reference["run_status"], 1048576))
    runtime = status.get("joint_runtime") if isinstance(status, dict) else None
    if not isinstance(runtime, dict):
        raise ValueError("explicit actual prior/current/cumulative wall required")
    values = (
        status.get("wall_seconds"),
        runtime.get("prior_wall_seconds"),
        runtime.get("current_wall_seconds"),
        runtime.get("cumulative_wall_seconds"),
    )
    try:
        valid = all(
            type(value) in (int, float) and math.isfinite(value) and value >= 0 for value in values
        )
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError("finite nonnegative actual wall metadata required")
    wall_seconds, prior_wall, current_wall, prior_seconds = values
    # persist uses one current snapshot and this exact addition, also on restart.
    if current_wall != wall_seconds or prior_seconds != prior_wall + current_wall:
        raise ValueError("actual wall prefix differs from producer prior + current")
    raw = bound_file_bytes(reference["checkpoint"], joint["settings"]["checkpoint_bytes"])
    saved = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
    state = saved.get("policy_value")
    if (
        not isinstance(state, dict)
        or state["identity"] != checkpoint_identity(cfg, corpus, joint)
        or state["model_state_status"] != "LAST_COMPLETED_UPDATE"
        or state["observation"] is None
        or state["observation"]["step"] != saved["position"]["step"]
        or state["observation"]["training_seen"] != saved["position"]["training_seen"]
        or state["completed_step"] != saved["position"]["step"]
        or state["completed_step"] >= cfg["training"]["steps"]
        or status["model_state_status"] != "LAST_COMPLETED_UPDATE"
        or status["step"] != state["completed_step"]
        or status["attempted_step"] != state["completed_step"]
        or status["samples"] != state["samples"]
        or status["forward_rows_conservative"] != state["forward_rows"]
        or status["forward_rows_completed"] != state["completed_forward_rows"]
        or status["status"] in ("COMPLETED", "EARLY_STOPPED")
    ):
        raise ValueError("same-input/config observed verified joint checkpoint required")
    model_shapes = {
        "ft.weight": (32, 312),
        "ft.bias": (32,),
        "h.weight": (32, 70),
        "h.bias": (32,),
        "out.weight": (1, 32),
        "out.bias": (1,),
        "policy.weight": (209, 32),
        "policy.bias": (209,),
    }
    for tensors in (saved["model"], state["best_state"], state["initial_state"]):
        if set(tensors) != set(model_shapes):
            raise ValueError("joint restart exact shared/value/policy parameter set")
        for name, shape in model_shapes.items():
            value = tensors[name]
            if (
                tuple(value.shape) != shape
                or value.dtype != torch.float32
                or not torch.isfinite(value).all()
            ):
                raise ValueError("joint restart tensor shape/dtype/finite")
    if state["policy_evidence"] not in ("synthetic_untrained", "learned"):
        raise ValueError("joint checkpoint policy evidence")
    saved["_actual_previous_wall_seconds"] = prior_seconds
    return saved


def export_joint(model, cfg, statistics, distance_fit, path, joint, *, initial=False):
    """The existing value exporter and head exporter, joined by real Rust identity."""
    from .train import export, export_policy_head

    path = Path(path)
    descriptor = export(model, cfg, statistics, distance_fit, path)
    fingerprint = native_identity(joint["binding"]["core_library"]["path"], descriptor)["shared"]
    joint["native_identity_constructors"] += 1
    if initial and fingerprint != joint["initial_shared_fingerprint"]:
        raise ValueError("exported INITIAL is not the exact incumbent shared native identity")
    # The owning exporter creates a fresh directory. Replace only the new
    # policy export files beside this run's three maintained checkpoint names.
    import tempfile
    import os

    head = path / "policy-head"
    with tempfile.TemporaryDirectory(prefix="policy-export-", dir=path) as temporary:
        fresh = Path(temporary) / "head"
        export_policy_head(model, shared_fingerprint=fingerprint, path=fresh)
        identity = native_identity(
            joint["binding"]["core_library"]["path"],
            descriptor,
            fresh / "manifest.json",
        )
        joint["native_identity_constructors"] += 1
        if identity["shared"] != fingerprint:
            raise ValueError("shared native model changed during joint publication")
        head.mkdir(exist_ok=True)
        for name in ("policy.f32", "manifest.json"):
            os.replace(fresh / name, head / name)
    joint.setdefault("exported_identities", {})[str(path)] = identity
    return head / "manifest.json"
