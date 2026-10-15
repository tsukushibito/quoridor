"""Finalize the actual successful build and verify its original process cleanup."""

import importlib.util
from pathlib import Path
import re
import sys

ROOT = Path("/workspaces/quoridor")
BASE = Path(__file__).resolve().parent
OUT = BASE / "compatible-build-v1"
loader = importlib.util.spec_from_file_location(
    "lc", ROOT / "scripts/dev/research-lifecycle.py"
)
lc = importlib.util.module_from_spec(loader)
sys.modules["lc"] = lc
loader.loader.exec_module(lc)


def main():
    outer_ref = lc.artifact_ref(OUT / "job/result.json")
    outer = lc.document(outer_ref)
    assert (
        outer["exit_code"] == 0
        and outer["cleanup_complete"]
        and outer["direct_child_reaped"]
        and not outer["remaining"]
        and not outer["cleanup_errors"]
    )
    candidate_ref = lc.artifact_ref(OUT / "operation-v1/candidate.json")
    candidate = lc.document(candidate_ref)
    assert (
        candidate["status"] == "PENDING_FINALIZATION"
        and candidate["primary"] is None
        and candidate["cleanup_complete"]
        and not candidate["remaining"]
    )
    assert all(c["status"] == "PASS" for c in candidate["checks"])
    expected = lc.document(lc.artifact_ref(OUT / "prepared.json"))["test_filters"]
    actual_test_counts = []
    identities = []
    for c in candidate["checks"]:
        r = lc.document(c["persisted_process_receipt"])
        assert (
            r["direct_child_reaped"]
            and r["process_cleanup_complete"]
            and r["handle_closes_complete"]
            and not r["remaining"]
        )
        now = lc.process.identity(lc.process.process_info(r["child"]["pid"]))
        assert now != r["child"]
        identities.append(
            dict(
                original=r["child"],
                current=now,
                returned=c["guardian_return"] is not None,
                persisted_mask=r.get("signal_mask_restoration"),
                persisted_finalization=r.get("final_record_persist"),
            )
        )
        raw = lc.read_ref(c["full_log"], c["full_log"]["bytes"]).decode()
        if c["role"] == "test" and "--no-run" not in c["argv"]:
            matches = re.findall(r"test result: ok\. (\d+) passed; 0 failed;", raw)
            assert len(matches) == 1
            selector = c["argv"][c["argv"].index("--") - 1]
            target = next(t for t in expected if t["filter"] == selector)
            assert int(matches[0]) == target["expected"]
            actual_test_counts.append(dict(filter=selector, passed=int(matches[0])))
    spec = lc.document(lc.artifact_ref(OUT / "intent.json"))
    assert not Path(spec["TMP"]).exists()
    state = lc.document(lc.artifact_ref(OUT / "job/state.json"))
    now = lc.process.identity(lc.process.process_info(state["child"]["pid"]))
    assert now != state["child"]
    # The maintained finalizer binds the real originating job; no engine/model call.
    result = lc.finalize(OUT / "operation-v1", outer_ref)
    assert result["status"] == "PASS"
    manifest_ref = lc.artifact_ref(OUT / "operation-v1/manifest.json")
    manifest = lc.accepted_build(manifest_ref)
    assert lc.artifact_ref(candidate["artifact"]["path"]) == candidate["artifact"]
    lc.new_json(
        OUT / "STOP.json",
        dict(
            at=lc.stamp(),
            outer=outer_ref,
            candidate=candidate_ref,
            manifest=manifest_ref,
            artifact=manifest["artifact"],
            original_candidate_finished=candidate["finished_at"],
            identities=identities,
            outer_child=dict(original=state["child"], current=now),
            TMP_absent=True,
            original_masks_preserved=True,
            outer_seconds=outer["wall_seconds"],
            actual_selected_test_counts=actual_test_counts,
            old_successful_suites_replayed=False,
            new_AI4_runner1_affected2_PASS=True,
            config_NN0=lc.artifact_ref(BASE / "Python-NN0-v1/returned-receipt.json"),
            source_composition=lc.artifact_ref(
                BASE / "source-composition-v1/result.json"
            ),
            fixture_repair=lc.artifact_ref(BASE / "fixture-default-repair.json"),
            comparison_image_frozen=False,
            scientific_entry=False,
            owned_readers_writers_children_jobs_handles_TMP_leases=[],
        ),
    )
    print(manifest_ref)


if __name__ == "__main__":
    main()
