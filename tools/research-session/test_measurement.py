"""Owning metadata checks; no model, native operation or profiling execution."""

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(os.environ.get("RESEARCH_TEST_ROOT", Path(__file__).resolve().parents[2]))
SOURCE = Path(
    os.environ.get("RESEARCH_LIFECYCLE_SOURCE", ROOT / "scripts/dev/research-lifecycle.py")
)
loader = importlib.util.spec_from_file_location("measurement_lifecycle", SOURCE)
lc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(lc)


class MeasurementTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.settings = {
            "roots": [
                {
                    "input": 0,
                    "pointer": "/context",
                    "field": "prefix",
                    "label": "fixture",
                }
            ],
            "profile": "control",
            "tt_entries": 4096,
            "use_tt": True,
            "use_pvs": True,
            "namespace": {
                "evaluator": "fixture",
                "rules": "rules",
                "selectivity": "fullwidth",
            },
            "output_bytes": 65536,
            "record_bytes": 16384,
        }
        self.experiment = {
            "argv": ["/unused/native", "measure"],
            "inputs": [{}],
            "rules": "rules",
        }
        self.spec = {"owner": str(self.root), "data": [], "perf": None}

    def metadata(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value))
        return lc.bound(path)[0]

    def test_measurement_hardware_envelope_has_no_study_selector(self):
        declared = {
            "issue": "arbitrary-label",
            "resources": {"family_RAM_B": 3 * 1024**3},
        }
        self.assertEqual(lc.issued_family_upper({"kind": "run"}, declared), 3 * 1024**3)
        declared["issue"] = "another-label"
        self.assertEqual(lc.issued_family_upper({"kind": "run"}, declared), 3 * 1024**3)
        declared["resources"]["family_RAM_B"] = False
        with self.assertRaisesRegex(lc.Refused, "family RAM"):
            lc.issued_family_upper({"kind": "run"}, declared)
        # The normal measurement owner needs its actual settings and limits,
        # not another support/admission/approved-plan deliverable.
        spec = {
            "kind": "run",
            "owner": str(self.root),
            "output": str(self.root / "operation"),
            "data_root": str(self.root / "data"),
            "owned_outputs": [],
            "finalizers": [],
            "data": [],
            "experiment": self.metadata("execution.json", self.experiment),
            "limits": {
                "family_B": 536870912,
                "controller_B": 67108864,
                "host_reserve_B": 4294967296,
                "log_B": 2097152,
            },
        }
        resources = lc.Limits(spec)
        self.assertIsNone(resources.output_limit)
        self.assertIsNone(spec["limits"].get("owned_B"))

    def configure(self, names, sessions=None):
        sessions = sessions or ["shared"] * len(names)
        rows = [
            {"id": name, "session": session, "root": 0, "depth": 1, "node_cap": 3}
            for name, session in zip(names, sessions, strict=True)
        ]
        self.experiment["config"] = self.metadata("settings.json", self.settings)
        self.experiment["schedule"] = self.metadata("schedule.json", rows)
        return rows

    def test_measurement_two_counts_orders_and_configured_targets(self):
        for names, profile in [
            (["later", "earlier"], "control"),
            (["third", "first", "second"], "cheap"),
        ]:
            with self.subTest(names=names, profile=profile):
                self.settings["profile"] = profile
                self.configure(names)
                settings, rows = lc.measurement_config(self.experiment)
                self.assertEqual([row["id"] for row in rows], names)
                self.assertEqual(settings["profile"], profile)
        # The owning metadata port does not require a historical plan or Q record.
        lc.experiment_phase_check({**self.experiment, "phase": "compare", "models": [{}]})
        self.configure(["a", "b", "c"], ["cold", "warm", "cold"])
        with self.assertRaisesRegex(lc.Refused, "session reused"):
            lc.measurement_config(self.experiment)
        self.settings["tt_entries"] = False
        self.configure(["a"])
        with self.assertRaisesRegex(lc.Refused, "positive tt_entries"):
            lc.measurement_config(self.experiment)

    def test_measurement_partial_counts_errors_and_missing_counters_preserved(self):
        self.configure(["a", "b", "c", "d", "e"])
        rows = [
            {"status": "COMPLETE", "measurement": {"work": {"nodes": 12}}},
            {
                "status": "UNKNOWN",
                "measurement": {"returned": "Err", "error": "cancelled"},
            },
        ]
        result = {
            "planned": 5,
            "calls": 2,
            "complete": 1,
            "uncompleted": 4,
            "unperformed": 3,
            "measurements": rows,
            "errors": [{"stage": "cancel"}],
            "status": "PARTIAL",
        }
        values = {
            "settings": b"{}",
            "measurements": b"".join(json.dumps(row).encode() + b"\n" for row in rows),
            "result": json.dumps(result).encode(),
        }
        evidence = lc.measurement_evidence(self.spec, self.experiment, values)
        self.assertEqual(evidence["result"], result)
        self.assertEqual(evidence["journal_rows"], 2)
        self.assertNotIn(
            "evaluations", evidence["result"]["measurements"][0]["measurement"]["work"]
        )
        del values["result"]
        evidence = lc.measurement_evidence(self.spec, self.experiment, values)
        self.assertTrue(evidence["unreturned_tail"])
        self.assertIsNone(evidence["result"])
        self.assertEqual(evidence["recorded_prefix"], rows)
        torn = b'{"status":"COM'
        evidence = lc.measurement_evidence(
            self.spec,
            self.experiment,
            {**values, "measurements": values["measurements"] + torn},
        )
        self.assertEqual(evidence["recorded_prefix"], rows)
        self.assertEqual(evidence["journal_rows"], 2)
        self.assertEqual(evidence["observed_complete"], 1)
        self.assertTrue(evidence["unreturned_tail"])
        self.assertTrue(evidence["journal_partial_tail"])
        self.assertEqual(evidence["journal_tail_bytes"], len(torn))
        self.assertEqual(evidence["journal_tail_sha256"], lc.sha(torn))
        evidence = lc.measurement_evidence(
            self.spec, self.experiment, {**values, "measurements": b"{}"}
        )
        self.assertEqual(evidence["recorded_prefix"], [])
        self.assertEqual(evidence["observed_complete"], 0)
        self.assertEqual(evidence["journal_tail_bytes"], 2)

    def test_measurement_standard_perf_settings_identity_output_and_plain(self):
        tool = self.root / "perf"
        tool.write_bytes(b"synthetic executable identity only; never run")
        tool.chmod(0o755)
        output = str(self.root / "samples.data")
        native = ["/unused/native", "measure", "--experiment", "settings"]
        self.assertEqual(lc.measurement_argv(self.spec, self.experiment, native), native)
        for frequency, pages, graph in [(17, 8, "dwarf,4096"), (49, 64, "dwarf,8192")]:
            self.spec["perf"] = {
                "tool": lc.artifact_ref(tool),
                "output": output,
                "event": "cpu-clock:u",
                "frequency_hz": frequency,
                "call_graph": graph,
                "ring_pages": pages,
                "data_max_bytes": 12582912,
                "no_buildid_cache": True,
            }
            self.spec["data"] = [{"name": "perf_RAW", "path": output, "limit_B": 12582912}]
            argv = lc.measurement_argv(self.spec, self.experiment, native)
            self.assertEqual(argv[argv.index("-F") + 1], str(frequency))
            self.assertEqual(argv[argv.index("--call-graph") + 1], graph)
            self.assertEqual(argv[-len(native) :], native)
        tool.write_bytes(b"changed identity")
        with self.assertRaisesRegex(lc.Refused, "perf executable"):
            lc.measurement_argv(self.spec, self.experiment, native)
        self.spec["perf"]["tool"] = lc.artifact_ref(tool)
        Path(output).write_bytes(b"retained RAW")
        with self.assertRaisesRegex(lc.Refused, "exclusive"):
            lc.measurement_argv(self.spec, self.experiment, native)
        raw_ref = lc.bound(output)[0]
        result = {
            "planned": 2,
            "calls": 1,
            "complete": 1,
            "uncompleted": 1,
            "unperformed": 1,
            "measurements": [],
            "errors": [],
            "status": "PARTIAL",
        }
        evidence = lc.measurement_evidence(
            self.spec,
            self.experiment,
            {
                "settings": b"{}",
                "measurements": b"",
                "result": json.dumps(result).encode(),
            },
            files=[raw_ref],
        )
        self.assertEqual(evidence["result"]["perf_RAW"], [raw_ref])
        self.assertEqual(evidence["perf_RAW"], [raw_ref])


if __name__ == "__main__":
    unittest.main()
