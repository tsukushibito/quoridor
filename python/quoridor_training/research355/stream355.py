"""Bounded saved analysis child of the single maintained research lifecycle."""

import argparse
import json
from pathlib import Path
import sys

import io355 as io
import lifecycle355 as life
import observations355 as observations
import producer355 as producer
import strength355 as s


class Inputs:
    def __init__(self, index):
        s.require(
            index["schema"] == "quoridor.strength355.stopped-input-index.v1"
            and index["plan_SHA256"] == s.PLAN_SHA
            and index["provenance"] == "ACTUAL_GENERATED",
            "stopped input index",
        )
        refs = index["files"]
        s.require(type(refs) is dict and len(refs) <= 512, "finite named input map")
        self.refs, self.seen = refs, {}
        self.progress = {"rows_read": 0, "files_returned": [], "available_sections": []}
        total = 0
        paths = set()
        for name, ref in refs.items():
            path = Path(ref["path"])
            s.require(
                path.is_absolute()
                and str(path) == str(path.resolve())
                and not path.is_symlink()
                and str(path) not in paths,
                "exclusive canonical named files, no aliases",
            )
            paths.add(str(path))
            s.sha(ref["SHA256"])
            total += s.integer(ref["bytes"], 0, io.MAX_INPUT_TOTAL)
            s.require(ref["mode"] in ("0600", "0644"), "exact supported file mode")
        s.require(total <= io.MAX_INPUT_TOTAL, "whole named input read envelope")
        self.total = total

    def get(self, name, maximum=131072):
        ref = self.refs[name]
        self.progress["last_attempted_file"] = ref
        value = io.read_bound(
            Path(ref["path"]), {k: ref[k] for k in ("SHA256", "bytes", "mode")}, maximum
        )
        self.seen[name] = ref
        self.progress["files_returned"].append(name)
        return value

    def lines(self, name):
        ref = self.refs[name]
        self.progress["last_attempted_file"] = ref
        expected = {k: ref[k] for k in ("SHA256", "bytes", "mode")}
        yield from io.read_jsonl(Path(ref["path"]), expected, 630784, 32, self.progress)
        self.seen[name] = ref
        self.progress["files_returned"].append(name)

    def after(self):
        for ref in self.seen.values():
            s.require(
                io.identity(Path(ref["path"])) == {k: ref[k] for k in ("SHA256", "bytes", "mode")},
                "source-after input drift",
            )


def scientific_inputs(index, inputs, metadata, build_ref, build, analysis_experiment):
    """Validate all manifest/config/clock/source joins before reading outcomes."""
    actual_files = [
        {"path": r["path"], "sha256": r["SHA256"], "bytes": r["bytes"], "mode": r["mode"]}
        for r in inputs.refs.values()
    ]
    s.require(
        sorted(actual_files, key=lambda r: r["path"])
        == sorted(analysis_experiment["inputs"], key=lambda r: r["path"]),
        "exact selected analysis input envelope",
    )
    s.require(index["build_manifest"] == build_ref, "analysis-config current accepted build")
    available = {}
    contexts = {}
    provenance = metadata.progress.setdefault("operation_provenance", [])
    s.require(
        type(index["producer_completions"]) is list and len(index["producer_completions"]) <= 20,
        "bounded generation/materialization/compare/sixteen arena completions",
    )
    for ref in index["producer_completions"]:
        completed, experiment = life.finalized_input(metadata, ref, build_ref)
        provenance.append(
            {
                "completion": ref,
                "status": completed["status"],
                "cleanup_complete": completed["cleanup_complete"],
                "remaining": completed["remaining"],
                "primary": completed["primary"],
                "secondary": completed["secondary"],
                "checks": completed["checks"],
                "data_errors": completed["data"]["errors"],
                "owed": completed["owed_finalizers"],
                "generation": completed["data"].get("generation"),
                "returned_guardian_facts": [
                    check.get("guardian_return", "UNKNOWN_NOT_RETURNED")
                    for check in completed["checks"]
                ],
            }
        )
        life.numerical(metadata, experiment, build)
        inventory = list(completed["data"]["files"])
        for obligation in completed["owed_finalizers"]:
            receipt_ref = obligation.get("actual_receipt")
            s.require(
                receipt_ref is not None and receipt_ref["path"] == obligation["path"],
                "bound declared actual receipt inventory",
            )
            receipt = metadata.read(receipt_ref, min(obligation["limit_B"], io.MAX_INDEX_BYTES))
            s.require(type(receipt["files"]) is list, "typed actual receipt file inventory")
            inventory.extend(receipt["files"])
        for file in inventory:
            name = life.index_ref(inputs, file)
            s.require(
                name not in available or available[name][0] is completed,
                "one actual producer for each durable output",
            )
            available[name] = (completed, experiment)
        contexts[ref["sha256"]] = (completed, experiment)
    compare_binding(
        index, inputs, available, {"source_book_SHA256": inputs.refs[index["book"]]["SHA256"]}
    )
    raw_book = inputs.get(index["book"], 1048576)
    book = s.adapt_generated_book(
        raw_book, inputs.refs[index["book"]]["SHA256"], "ACTUAL_GENERATED"
    )
    schedule = s.adapt_schedule(
        inputs.get(index["schedule"]), book, inputs.refs[index["schedule"]]["SHA256"]
    )
    schedule_ref = {
        "path": inputs.refs[index["schedule"]]["path"],
        "sha256": inputs.refs[index["schedule"]]["SHA256"],
        "bytes": inputs.refs[index["schedule"]]["bytes"],
        "mode": inputs.refs[index["schedule"]]["mode"],
    }
    s.require(analysis_experiment["schedule"] == schedule_ref, "same full512 schedule")
    used = [index["book"], index["schedule"]] + list(index["matched_rows"]) + list(index["trees"])
    used += [d["file"] for d in index["stronger_rows"]]
    used += [
        index[k] for k in ("selection", "engineering_footer", "engineering_failure") if index.get(k)
    ]
    if index.get("engineering_intent"):
        used.append(index["engineering_intent"])
    for batch in index["batches"]:
        used.extend(batch[k] for k in ("completed", "result"))
        s.require(batch["completed"] in available, "finalized native journal")
        completed, arena = available[batch["completed"]]
        s.require(
            batch["result"] in available and available[batch["result"]][0] is completed,
            "journal and result belong to the same finalized operation",
        )
        s.require(
            arena["phase"] == "arena"
            and arena["batch"] == batch["batch"]
            and arena["schedule"] == schedule_ref,
            "actual batch/global512 experiment join",
        )
        config = inputs.get(batch["config"])
        s.require(life.index_ref(inputs, arena["config"]) == batch["config"], "actual arena config")
        life.arena_clock(config)
        life.arena_conditions(config, arena)
        slots = [slot for slot in schedule["slots"] if slot["batch_id"] == batch["batch"]]
        s.require(
            len(slots) == 32
            and sorted(slot["local_game"] for slot in slots) == list(range(32))
            and config["games"] == 32
            and type(config["run_id"]) is str
            and bool(config["run_id"])
            and len(config["arena"]["book"]["openings"]) == 16
            and len(config["arena"]["first_candidate_colors"]) == 16,
            "bound full batch context",
        )
        for slot in slots:
            local_family = slot["local_game"] // 2
            opening = config["arena"]["book"]["openings"][local_family]
            s.require(
                opening["reference"]["settings"]["family_id"] == slot["family_id"]
                and opening["prefix"] == book["families"][slot["family_id"]]["prefix"]
                and type(config["arena"]["first_candidate_colors"][local_family]) is int
                and config["arena"]["first_candidate_colors"][local_family] in (0, 1)
                and config["arena"]["first_candidate_colors"][local_family]
                ^ (slot["local_game"] % 2)
                == slot["candidate_colour"],
                "config opening/global family/colour agrees with full512 schedule",
            )
        expected_model = life.MODELS[(batch["batch"] // 2 + batch["batch"] % 2) % 2]
        s.require(
            arena["models"][0]["descriptor"]["sha256"] == expected_model[0],
            "batch model and shared schedule matchup",
        )
    s.require(
        all(name in available for name in used),
        "every scientific output is finalized durable evidence",
    )
    return book, schedule, available, contexts, provenance


def compare_binding(index, inputs, available, book):
    """Validate explicit versioned config/experiment bindings before outcomes."""
    if index.get("engineering_footer") is None:
        return
    completed, experiment = available[index["engineering_footer"]]
    s.require(experiment["phase"] == "compare", "actual compare result provenance")
    intent = inputs.get(index["engineering_intent"])
    config = inputs.get(index["engineering_plan"])
    footer = inputs.get(index["engineering_footer"])
    s.require(
        config["schema"] == "quoridor.value-search-strength.compare.v2"
        and "qualification" not in config
        and config["canonical_plan"]["sha256"] == s.PLAN_SHA
        and config["book"]["sha256"] == book["source_book_SHA256"],
        "current compare Planv2",
    )
    s.require(
        life.index_ref(inputs, experiment["config"]) == index["engineering_plan"]
        and intent["schema"] == "quoridor.value-search-strength.compare-intent.v2"
        and intent["experiment_sha256"] == completed["experiment"]["sha256"]
        and intent["config_sha256"] == experiment["config"]["sha256"]
        and intent["build_manifest"] == completed["build_manifest"],
        "explicit current header experiment/config bindings",
    )
    s.require(
        "plan_sha256" not in intent and "plan_sha256" not in footer,
        "retired ambiguous hash field refuses",
    )
    s.require(
        footer["schema"] == "quoridor.value-search-strength.compare-result.v2"
        and footer["experiment_sha256"] == intent["experiment_sha256"]
        and footer["config_sha256"] == intent["config_sha256"]
        and footer["book_sha256"] == book["source_book_SHA256"],
        "explicit current result experiment/config bindings",
    )
    s.require(
        footer["fixed_denominator"]
        == {"matched_positions": 32, "natural4": 96, "common_trees": 8, "stronger_max_cases": 16},
        "scientific footer denominator",
    )
    for ref in footer["outputs"]:
        matches = [
            name
            for name, actual in inputs.refs.items()
            if actual["path"] == ref["path"]
            and actual["SHA256"] == ref["sha256"]
            and actual["bytes"] == ref["bytes"]
        ]
        s.require(len(matches) == 1 and matches[0] in available, "footer durable output ownership")
    return intent, footer


def compare_footer(index, inputs, metadata, available, book, summary):
    if index.get("engineering_footer") is None:
        return
    intent, footer = compare_binding(index, inputs, available, book)
    matched = summary["matched_available_rows"]
    stronger = summary["stronger_available_rows"]
    summary["engineering_census"] = {
        "matched": producer.census(footer["matched_census"], matched, 96, 192000000),
        "stronger": producer.census(footer["stronger_census"], stronger, 192, 1536000000),
        "whole_phase_until_footer_seconds": s.finite(footer["whole_phase_until_footer_seconds"]),
        "external_worker_controller_whole_seconds": "SEPARATE_AUTHORITATIVE_OPERATION_DOMAIN",
        "experiment_SHA256": intent["experiment_sha256"],
        "config_SHA256": intent["config_sha256"],
    }


def write_data(intent, files):
    """Only owed data files; no candidate/manifest/INCOMPLETE publication."""
    root = Path(intent["data_root"])
    s.require(
        root.is_absolute() and str(root) == str(root.resolve()) and not root.is_symlink(),
        "owned data root",
    )
    if not root.exists():
        root.mkdir(exist_ok=False)
    declarations = {d["name"]: d for d in intent["data"]}
    s.require(len(declarations) == len(intent["data"]), "exclusive declared data names")
    for name, raw in files.items():
        declaration = declarations[name]
        path = Path(declaration["path"])
        s.require(
            path.parent == root
            and path.name
            == {"summary": "summary.json", "report": "report.md", "failure": "failure.json"}[name]
            and not path.is_symlink(),
            "only declared scientific report files",
        )
        s.integer(declaration["limit_B"], 1, io.MAX_OUTPUT)
        s.require(
            len(raw) <= declaration["limit_B"] and len(raw) <= io.MAX_OUTPUT, "bounded owed data"
        )
        with path.open("xb") as output:
            output.write(raw)
            output.flush()
    # The parent owns sync/close/cleanup, outer completion and final marker unlink.


def child_entry(experiment_path, experiment_sha256, intent_path):
    """Same guardian child; standalone/mismatched context refuses before data."""
    metadata = life.Metadata()
    partial = {}
    inputs = None
    intent = None
    secondary = []
    try:
        intent, _ = life.child_context(intent_path, metadata)
        experiment_ref = intent["experiment"]
        s.require(
            experiment_ref["path"] == str(Path(experiment_path))
            and experiment_ref["sha256"] == s.sha(experiment_sha256),
            "exact caller experiment",
        )
        experiment = metadata.read(experiment_ref)
        build_ref = experiment["build_manifest"]
        metadata.add(build_ref)
        build = life.authoritative(metadata, build_ref, "build-manifest", "build")
        life.analysis_source(
            intent,
            (
                __file__,
                life.__file__,
                io.__file__,
                s.__file__,
                observations.__file__,
                producer.__file__,
            ),
        )
        s.require(intent["artifact"] == build["artifact"], "same actually qualified artifact")
        experiment = life.experiment(metadata, experiment_ref, build_ref, "analysis")
        life.numerical(metadata, experiment, build)
        index = metadata.read(experiment["config"], io.MAX_INDEX_BYTES)
        inputs = Inputs(index)
        book, schedule, available, _, provenance = scientific_inputs(
            index, inputs, metadata, build_ref, build, experiment
        )
        partial["operation_provenance"] = provenance
        if index.get("engineering_failure"):
            # Current failure envelope is data, not a recursive admission chain.
            partial["engineering_failure_raw"] = inputs.get(index["engineering_failure"], 1048576)
        summary = observations.aggregate_observations(
            index,
            inputs,
            partial,
            book,
            schedule,
            {"build_manifest": build_ref, "analysis_experiment": experiment_ref},
        )
        compare_footer(index, inputs, metadata, available, book, summary)
        inputs.after()
        metadata.after()
        raw = json.dumps(summary, allow_nan=False, indent=2).encode()
        report = s.report(summary).encode()
        s.require(len(raw) + len(report) <= io.MAX_OUTPUT, "whole joint report bound")
        write_data(intent, {"summary": raw, "report": report})
        return summary
    except BaseException as primary:
        inherited_secondary = getattr(primary, "strength355_secondary_errors", [])
        secondary = [*inherited_secondary, *secondary]
        primary.strength355_available_evidence = partial
        primary.strength355_input_progress = {} if inputs is None else inputs.progress
        primary.strength355_metadata_progress = metadata.progress
        primary.strength355_secondary_errors = secondary
        if intent is not None and any(d["name"] == "failure" for d in intent["data"]):
            try:
                failed = {
                    "primary": repr(primary),
                    "primary_cause": None if primary.__cause__ is None else repr(primary.__cause__),
                    "primary_notes": list(getattr(primary, "__notes__", [])),
                    "secondary": [
                        {
                            "type": type(error).__name__,
                            "message": str(error),
                            "notes": list(getattr(error, "__notes__", [])),
                        }
                        for error in secondary
                    ],
                    "available": partial,
                    "progress": primary.strength355_input_progress,
                    "metadata_progress": metadata.progress,
                    "authoritative": False,
                }
                write_data(intent, {"failure": json.dumps(failed, allow_nan=False).encode()})
            except BaseException as error:
                secondary.append(error)
                primary.add_note("independent data publication failure: " + repr(error))
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--experiment-sha256", required=True)
    parser.add_argument("--intent", required=True)
    args = parser.parse_args()
    child_entry(args.experiment, args.experiment_sha256, args.intent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
