"""Typed documented lifecycle manifests, no historical certificate joins."""

import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

import io355
import strength355 as s

PREFIX = "quoridor.research."
COMPILED_KEYS = frozenset(
    [
        "Cargo.lock",
        "ai/alphabeta.rs",
        "ai/lib.rs",
        "ai/sigma_mcts.rs",
        "core/game.rs",
        "core/lib.rs",
        "core/position.rs",
        "core/research.rs",
        "data/lib.rs",
        "inference/cuda.rs",
        "inference/lib.rs",
        "inference/tensorrt.rs",
        "nnue/features.rs",
        "nnue/lib.rs",
        "nnue/quantized.rs",
        "nnue/residual.rs",
        "nnue/simd.rs",
        "runner/Cargo.toml",
        "runner/arena.rs",
        "runner/arena_book.rs",
        "runner/arena_clock.rs",
        "runner/arena_manifest.rs",
        "runner/arena_statistics.rs",
        "runner/config.rs",
        "runner/lib.rs",
        "runner/main.rs",
        "runner/native_input.rs",
        "runner/nnue-diagnose.rs",
        "runner/research_manifest.rs",
        "runner/resources.rs",
        "runner/runtime.rs",
        "runner/sigma_clock.rs",
        "runner/sigma_qualification.rs",
        "runner/value_search_compare.rs",
        "runner/value_search_strength.rs",
    ]
)
RULES = "research-standard-2p-threefold-goal-first-v1"
UNITS = "wall-distance/80"
PERSPECTIVE = "side-to-move"
MODELS = [
    (
        "c4712e0872b6831e33fcf59b99d9d7f774d18a3e8d5236d7923ba65e64aabc39",
        "9ca438e43b0c105ac5f802a302946f2ba71623ea2bc443b9c54cc9a8468b75b0",
        "519410ed5eb0b340d1d25df8626d67f508bee7706cbd4ba8a7175bf4e613e645",
    ),
    (
        "46ec2c4708f96dcf9fad579c2fb0d1299c6663df27412f0faac98267467715e1",
        "046fe926e56b955b0fb7de8f147a74ec33eace9cbc00a55c307f9b6541ab9841",
        "96a5f41f875022d1752b9c999595ad58bfb2d42687a8f06de08d42b1c4215875",
    ),
]


def descriptor(ref):
    s.require(
        type(ref) is dict and set(ref) == {"path", "sha256", "bytes", "mode"},
        "exact lifecycle descriptor",
    )
    path = Path(ref["path"])
    s.require(
        path.is_absolute() and str(path) == str(path.resolve()) and not path.is_symlink(),
        "canonical lifecycle path",
    )
    s.sha(ref["sha256"])
    s.integer(ref["bytes"], 0, io355.MAX_INPUT_TOTAL)
    s.require(
        type(ref["mode"]) is str and ref["mode"] in ("0600", "0644", "0755"),
        "actual lifecycle custody mode",
    )
    return ref


def index_ref(inputs, ref):
    descriptor(ref)
    expected = {
        "path": ref["path"],
        "SHA256": ref["sha256"],
        "bytes": ref["bytes"],
        "mode": ref["mode"],
    }
    matches = [name for name, actual in inputs.refs.items() if actual == expected]
    s.require(len(matches) == 1, "one exact lifecycle reference in named index")
    return matches[0]


def read_ref(inputs, ref, maximum=131072):
    return inputs.get(index_ref(inputs, ref), maximum)


def authoritative(inputs, ref, schema, kind, statuses=("PASS",)):
    descriptor(ref)
    path = Path(ref["path"])
    s.require(
        path.name == "manifest.json" and not (path.parent / "INCOMPLETE").exists(),
        "only finalized manifest, no candidate or marker",
    )
    value = read_ref(inputs, ref)
    s.require(
        value["schema"] == PREFIX + schema + ".v1"
        and value["kind"] == kind
        and value["status"] in statuses,
        "actual authoritative operation scope",
    )
    s.require(
        type(value["cleanup_complete"]) is bool and type(value["remaining"]) is list,
        "actual cleanup outcome and unavailable facts",
    )
    stamp = datetime.datetime.fromisoformat(
        value["authoritative_finished_at"].replace("Z", "+00:00")
    )
    s.require(stamp.tzinfo is not None, "actual authoritative completion time")
    if value["status"] == "PASS":
        s.require(
            value["primary"] is None
            and value["secondary"] == []
            and value["cleanup_complete"] is True
            and value["remaining"] == [],
            "successful finalized operation has no originating or owed errors",
        )
    # Cleanup and scientific outcome are independent facts. Frozen producerv1
    # emits false for FAILED; retain its actual value, never synthesize true.
    s.require(type(value["checks"]) is list and bool(value["checks"]), "actual returned checks")
    # The maintained finalizer owns checking its outer result and obligations.
    # These are bound facts, not recursive per-run certificate execution.
    descriptor(value["outer_job_result"])
    descriptor(value["intent"])
    if kind == "build":
        descriptor(value["artifact"])
        descriptor(value["source_adoption"])
        s.require(
            type(value["source"]) is dict and type(value["source"]["files"]) is list,
            "actual adopted build source",
        )
        compiled_digest(value["compiled_sources"])
        source_projection(value["source"], value["compiled_sources"])
        originating_build(value, inputs)
    s.require(type(value["owed_finalizers"]) is list, "typed owed finalizers")
    return value


def source_projection(source, compiled):
    """Exact adopted full source projection; no transitive header census."""
    workspace = Path(source["workspace"])
    s.require(
        workspace.is_absolute() and str(workspace) == str(workspace.resolve()),
        "adopted absolute source workspace",
    )
    descriptor(source["manifest"])
    descriptor(source["lock"])
    refs = source["compiled_sources"]
    s.require(
        type(refs) is dict and set(refs) == COMPILED_KEYS,
        "complete adopted source FileRef projection",
    )
    for key, file in refs.items():
        descriptor(file)
        s.require(file["sha256"] == compiled[key], "actual compiled source matches adoption")
    s.require(
        source["manifest"]["path"] == str(workspace / "Cargo.toml")
        and source["lock"]["path"] == str(workspace / "Cargo.lock")
        and refs["runner/Cargo.toml"]["path"]
        == str(workspace / "crates/quoridor-runner/Cargo.toml")
        and refs["Cargo.lock"] == source["lock"],
        "distinct workspace and runner manifests, same workspace lock",
    )
    s.require(type(source["files"]) is list, "adopted source file list")
    files = {file["path"]: descriptor(file) for file in source["files"]}
    s.require(
        len(files) == len(source["files"])
        and all(files.get(file["path"]) == file for file in refs.values())
        and files.get(source["manifest"]["path"]) == source["manifest"]
        and files.get(source["lock"]["path"]) == source["lock"],
        "compiled source descriptors belong to exact source files",
    )
    s.require(type(source["cargo_configs"]) is list, "direct Cargo configuration witnesses")
    seen = set()
    for witness in source["cargo_configs"]:
        path = Path(witness["path"])
        s.require(
            path.is_absolute() and str(path) == str(path.resolve()) and str(path) not in seen,
            "unique direct Cargo config witness",
        )
        seen.add(str(path))
        if witness["file"] is not None:
            descriptor(witness["file"])
            s.require(witness["file"]["path"] == str(path), "actual config witness identity")


def originating_build(value, metadata):
    """Retain new actual outer provenance and every command capture domain."""
    job = value["originating_job"]
    s.require(
        type(job) is dict
        and type(job["runtime"]) is str
        and Path(job["runtime"]).is_absolute()
        and type(job["job_id"]) is str
        and bool(job["job_id"]),
        "actual originating build job",
    )
    descriptor(job["config"])
    s.sha(job["config_sha256"])
    config = metadata.read(job["config"], 1048576)
    s.require(type(config) is dict, "actual originating job config object")
    normalized_sha = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    s.require(job["config_sha256"] == normalized_sha, "actual normalized job config fingerprint")
    for key in ("supervisor", "child"):
        identity = job[key]
        s.integer(identity["pid"], 1)
        s.require(
            type(identity["start_ticks"]) is str
            and identity["start_ticks"].isdigit()
            and type(identity["boot_id"]) is str
            and bool(identity["boot_id"]),
            "actual recorded process identity",
        )
    descriptor(value["outer_job_state"])
    s.require(type(value["process_cleanup_complete"]) is bool, "actual process cleanup domain")
    for check in value["checks"]:
        s.require(
            type(check["name"]) is str
            and bool(check["name"])
            and check["role"] in ("version", "test", "lint", "build", "bindings", "run")
            and type(check["argv"]) is list
            and bool(check["argv"])
            and all(type(arg) is str for arg in check["argv"])
            and type(check["status"]) is str
            and type(check["capture_complete"]) is bool
            and type(check["secondary"]) is list,
            "typed every attempted command ledger",
        )
        for key in ("full_log", "persisted_process_receipt"):
            if check[key] is not None:
                descriptor(check[key])
        s.require(
            check["guardian_return"] is None or type(check["guardian_return"]) is dict,
            "returned guardian separate from persisted process",
        )
        if value["status"] == "PASS":
            s.require(
                check["guardian_return"] is not None
                and check["full_log"] is not None
                and check["capture_complete"] is True
                and check["primary"] is None
                and check["secondary"] == [],
                "actual PASS build has complete returned command captures",
            )
    if value["status"] == "PASS":
        s.require(
            value["process_cleanup_complete"] is True, "accepted build actual process cleanup"
        )


def models(experiment):
    rows = experiment["models"]
    phase = experiment["phase"]
    if phase == "arena":
        batch = s.integer(experiment["batch"], 0, 15)
        expected = [MODELS[(batch // 2 + batch % 2) % 2]]
    elif phase == "generation" and rows == []:
        expected = []
    else:
        expected = MODELS
    s.require(type(rows) is list and len(rows) == len(expected), "fixed phase model identities")
    for row, (manifest, weights, evaluator) in zip(rows, expected):
        descriptor(row["descriptor"])
        descriptor(row["weights"])
        s.require(
            row["descriptor"]["sha256"] == manifest
            and row["weights"]["sha256"] == weights
            and row["evaluator_sha256"] == evaluator,
            "fixed models, scale and evaluator identities",
        )
        mode = "0644" if manifest == MODELS[0][0] else "0600"
        s.require(row["descriptor"]["mode"] == mode, "original model descriptor modes")


def experiment(inputs, ref, build_ref, phase):
    value = read_ref(inputs, ref)
    s.require(
        value["schema"] == PREFIX + "experiment.v1"
        and value["phase"] == phase
        and value["build_manifest"] == build_ref
        and value["canonical_plan_sha256"] == s.PLAN_SHA,
        "same accepted build, phase and frozen scientific plan",
    )
    s.integer(value["planned_slots"], 0, 512)
    if phase == "arena":
        s.require(value["planned_slots"] == 512, "arena full scientific denominator")
    if phase == "analysis":
        s.require(
            value["planned_slots"] == 0 and value["batch"] is None,
            "analysis is a non-game operation; scientific schedule remains512",
        )
    s.require(
        value["rules"] == RULES
        and value["distance_units"] == UNITS
        and value["value_perspective"] == PERSPECTIVE,
        "fixed rules, legacy D units and STM",
    )
    descriptor(value["config"])
    descriptor(value["schedule"])
    s.require(type(value["inputs"]) is list, "named experiment input envelope")
    for row in value["inputs"]:
        descriptor(row)
    models(value)
    descriptor(value["numerical_qualification"])
    s.require(type(value["dynamic_libraries"]) is list, "explicit actual dynamic dependencies")
    for library in value["dynamic_libraries"]:
        descriptor(library["file"])
        s.require(
            type(library["version"]) is str and bool(library["version"]), "actual library version"
        )
    return value


class Metadata:
    """Small direct manifests/configs tracked separately from science payloads."""

    def __init__(self):
        self.refs = {}
        self.seen = {}
        self.progress = {"files_returned": [], "last_attempted_file": None}

    def add(self, ref):
        descriptor(ref)
        name = ref["path"]
        value = {"path": name, "SHA256": ref["sha256"], "bytes": ref["bytes"], "mode": ref["mode"]}
        s.require(
            name not in self.refs or self.refs[name] == value, "no metadata identity substitution"
        )
        s.require(len(self.refs) < 128 or name in self.refs, "bounded manifest graph")
        self.refs[name] = value
        return name

    def get(self, name, maximum=131072):
        ref = self.refs[name]
        s.require(
            sum(r["bytes"] for r in self.refs.values()) <= 8388608, "bounded manifest metadata"
        )
        self.progress["last_attempted_file"] = ref
        value = io355.read_bound(
            Path(name), {k: ref[k] for k in ("SHA256", "bytes", "mode")}, maximum
        )
        self.seen[name] = ref
        self.progress["files_returned"].append(name)
        return value

    def read(self, ref, maximum=131072):
        return self.get(self.add(ref), maximum)

    def after(self):
        for name, ref in self.seen.items():
            s.require(
                io355.identity(Path(name)) == {k: ref[k] for k in ("SHA256", "bytes", "mode")},
                "metadata source-after drift",
            )


def compiled_digest(compiled):
    s.require(type(compiled) is dict and bool(compiled), "flat complete compiled sources")
    for name, digest in compiled.items():
        s.require(type(name) is str and name.isascii(), "actual named compiled source")
        s.sha(digest)
    s.require(set(compiled) == COMPILED_KEYS, "exact complete35 compiled source map")
    return hashlib.sha256(
        json.dumps(compiled, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def child_context(intent_path, metadata, environment=None, parent_pid=None, argv=None):
    """Validate passed raw intent SHA and immediate parent; no second lock."""
    environment = os.environ if environment is None else environment
    parent_pid = os.getppid() if parent_pid is None else parent_pid
    expected = s.sha(environment["QUORIDOR_LIFECYCLE_INTENT"])
    raw_parent = environment["QUORIDOR_LIFECYCLE_PARENT_PID"]
    s.require(
        type(raw_parent) is str and raw_parent == str(parent_pid) and parent_pid > 1,
        "actual immediate lifecycle parent",
    )
    path = Path(intent_path)
    s.require(
        path.is_absolute() and not path.is_symlink() and path.stat().st_size <= 1048576,
        "bound finite intent path",
    )
    ref = {"path": str(path), "sha256": expected, "bytes": path.stat().st_size, "mode": "0644"}
    intent = metadata.read(ref, 1048576)
    s.require(
        intent["schema"] == PREFIX + "lifecycle-intent.v1" and intent["kind"] == "run",
        "current run parent context",
    )
    digest = s.digest({k: v for k, v in intent.items() if k not in ("admission", "intent_sha256")})
    s.require(intent["intent_sha256"] == digest, "internal admission digest remains separate")
    actual_argv = (
        [os.fsdecode(x) for x in Path("/proc/self/cmdline").read_bytes().split(b"\0") if x]
        if argv is None
        else argv
    )
    s.require(intent["argv"] == actual_argv, "actual frozen analysis argv")
    operation = Path(intent["output"])
    s.require(
        operation.is_absolute()
        and (operation / "INCOMPLETE").is_file()
        and not (operation / "manifest.json").exists(),
        "active exclusive parent operation",
    )
    return intent, ref


def pinned_python_and_source(build, script, interpreter=None, version=None):
    python = build["tools"]["PYTHON"]
    descriptor(python["file"])
    interpreter = Path(sys.executable).resolve() if interpreter is None else Path(interpreter)
    version = "Python " + platform.python_version() if version is None else version
    s.require(
        str(interpreter) == python["file"]["path"]
        and python["version_args"] == ["--version"]
        and python["version"].strip() == version,
        "actual pinned Python",
    )
    s.require(
        io355.identity(interpreter)
        == {
            "SHA256": python["file"]["sha256"],
            "bytes": python["file"]["bytes"],
            "mode": python["file"]["mode"],
        },
        "Python file coupling",
    )
    files = build["source"]["files"]
    s.require(type(files) is list, "adopted source files")
    for path in [
        Path(script).resolve(),
        *[
            Path(__file__).parent / name
            for name in (
                "lifecycle355.py",
                "observations355.py",
                "io355.py",
                "strength355.py",
                "producer355.py",
            )
        ],
    ]:
        matches = [r for r in files if r["path"] == str(path)]
        s.require(len(matches) == 1, "analysis source present in adopted build")
        descriptor(matches[0])
        s.require(
            io355.identity(path)
            == {
                "SHA256": matches[0]["sha256"],
                "bytes": matches[0]["bytes"],
                "mode": matches[0]["mode"],
            },
            "current analysis source coupling",
        )


def arena_clock(config):
    s.require(
        config["arena"]["comparison"] == "evaluator_wall_time"
        and config["arena"]["clock_policy"] == "strict_unknown"
        and type(config["arena"]["return_reserve_ms"]) is int
        and config["arena"]["return_reserve_ms"] == 5,
        "actual fixed caller clock config",
    )
    s.require(
        len(config["engines"]) == 2
        and all(type(e["time_ms"]) is int and e["time_ms"] == 100 for e in config["engines"]),
        "both 100ms clocks",
    )


def arena_conditions(config, experiment_value):
    """Refuse scientific config drift before consuming any game outcomes."""
    s.require(
        config["ruleset"] == "standard_2p_threefold"
        and config["inference"] is None
        and config["inference_cpu_core"] is None,
        "pure maintained D/NN rules and backend",
    )
    s.require(
        type(config["arena"]["tt_entries"]) is int and config["arena"]["tt_entries"] == 4096,
        "fixed TT capacity",
    )
    for engine in config["engines"]:
        s.require(
            type(engine["depth"]) is int
            and engine["depth"] == 64
            and type(engine["max_nodes"]) is int
            and engine["max_nodes"] == 1000000,
            "fixed same-time search limits",
        )
    learned, baseline = config["engines"]
    s.require(
        baseline["kind"] == "distance"
        and baseline["distance_a"] == 0
        and baseline["distance_b"] == 8
        and baseline["model"] is None,
        "maintained fixedD Tanh0/8",
    )
    batch = s.integer(experiment_value["batch"], 0, 15)
    model = MODELS[(batch // 2 + batch % 2) % 2]
    s.require(
        learned["kind"] == "nnue"
        and learned["distance_a"] == 0
        and learned["distance_b"] == (8 if model == MODELS[0] else 0)
        and learned["model"] == experiment_value["models"][0]["descriptor"]["path"],
        "actual current NN descriptor and output-only condition",
    )


def numerical(metadata, experiment_value, build):
    """Ordered fingerprint arrays match their actual declared scientific inputs."""
    value = metadata.read(experiment_value["numerical_qualification"])
    required = {
        "schema": PREFIX + "numerical-qualification.v1",
        "status": "PASS",
        "phase": experiment_value["phase"],
        "artifact_sha256": build["artifact"]["sha256"],
        "compiled_sources_sha256": compiled_digest(build["compiled_sources"]),
        "config_sha256": experiment_value["config"]["sha256"],
        "schedule_sha256": experiment_value["schedule"]["sha256"],
        "input_sha256": [r["sha256"] for r in experiment_value["inputs"]],
        "descriptor_sha256": [r["descriptor"]["sha256"] for r in experiment_value["models"]],
        "weights_sha256": [r["weights"]["sha256"] for r in experiment_value["models"]],
        "evaluator_sha256": [r["evaluator_sha256"] for r in experiment_value["models"]],
        "rules": RULES,
        "distance_units": UNITS,
        "value_perspective": PERSPECTIVE,
        "remaining": [],
    }
    for key, expected in required.items():
        s.require(
            value[key] == expected and type(value[key]) is type(expected),
            "actual numerical coupling " + key,
        )
    return value


def finalized_input(metadata, completion_ref, build_ref):
    """FAILED inputs retain available evidence; no success or cleanup upgrade."""
    metadata.add(completion_ref)
    completed = authoritative(metadata, completion_ref, "completion", "run", ("PASS", "FAILED"))
    s.require(completed["build_manifest"] == build_ref, "producer same accepted current image")
    descriptor(completed["experiment"])
    phase_value = metadata.read(completed["experiment"])
    phase = phase_value["phase"]
    s.require(
        phase in ("generation", "materialize", "compare", "arena"), "actual scientific input phase"
    )
    metadata.add(build_ref)
    phase_value = experiment(metadata, completed["experiment"], build_ref, phase)
    data = completed["data"]
    s.require(
        type(data["files"]) is list and type(data["errors"]) is list, "typed durable/partial data"
    )
    for ref in data["files"]:
        descriptor(ref)
    return completed, phase_value


def owed_facts(metadata, manifest):
    """Attempt every bound receipt independently, retaining failed provenance."""
    facts, errors = [], []
    for obligation in manifest["owed_finalizers"]:
        fact = {
            "obligation": obligation,
            "validated_PASS": False,
            "operation_success": manifest["status"] == "PASS",
        }
        facts.append(fact)
        try:
            s.require(obligation["kind"] in ("data", "journal"), "known owed finalizer kind")
            s.integer(obligation["limit_B"], 1, 33554432)
            if "actual_receipt" not in obligation:
                fact["return"] = "UNKNOWN_UNBOUND"
                s.require(
                    manifest["status"] == "FAILED", "successful operation has an unbound receipt"
                )
                continue
            ref = descriptor(obligation["actual_receipt"])
            s.require(
                ref["path"] == obligation["path"], "actual receipt is the declared obligation"
            )
            result = metadata.read(ref, obligation["limit_B"])
            fact["available_receipt"] = result
            valid = (
                result.get("schema") == PREFIX + "data-finalizer.v1"
                and result.get("status") == "PASS"
                and result.get("remaining") == []
                and result.get("intent_sha256") == manifest["intent"]["sha256"]
            )
            s.require(type(result["files"]) is list, "actual receipt file array")
            for file in result["files"]:
                descriptor(file)
            if obligation["kind"] == "journal":
                valid = (
                    valid
                    and type(result.get("planned_slots")) is int
                    and result["planned_slots"] == 512
                )
                valid = valid and result.get("complete_planned_census") is True
            fact["validated_PASS"] = valid
            if manifest["status"] == "PASS":
                s.require(valid, "every successful operation obligation actually passed")
        except BaseException as error:
            fact["receipt_error"] = {"type": type(error).__name__, "message": str(error)}
            errors.append(error)
    if errors and manifest["status"] == "PASS":
        primary = errors[0]
        primary.strength355_owed_available = facts
        primary.strength355_secondary_errors = errors[1:]
        for error in errors[1:]:
            primary.add_note("later independent owed receipt: " + repr(error))
        raise primary
    return facts
