"""New stream-to-fit/T-stat control ports; numerical imports must remain closed."""

import builtins
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from .distance_steps import require_completed_stream_cache


class StreamAdmission(unittest.TestCase):
    def test_partial_failed_reference_fixture_and_unknown_N_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for intake in (
                None,
                {"status": "STARTED"},
                {"status": "complete", "scope": "pilot-reference", "human_quantity_n": None},
                {"status": "complete", "scope": "synthetic-fixture", "human_quantity_n": None},
                {"status": "complete", "scope": "full-volume", "human_quantity_n": True},
            ):
                with self.subTest(intake=intake), self.assertRaises(ValueError):
                    require_completed_stream_cache(
                        path, {"stream_intake": intake}, full_volume=True
                    )
            manifest = {
                "stream_intake": {
                    "status": "complete",
                    "publication_protocol": "incomplete-marker-last-v1",
                    "provenance": {
                        "header": {
                            "generator_version": "fixed-d-dual-teacher-pilot-v1",
                            "config": {"phase": "full_volume"},
                            "compiled_sources": {"unexecuted-control-port": "b" * 64},
                            "resource_admission": {},
                        }
                    },
                    "scope": "full-volume",
                    "human_quantity_n": 1,
                }
            }
            require_completed_stream_cache(path, manifest, full_volume=True)
            (path / "intake-failure.json").write_text('{"admitted":false}')
            with self.assertRaisesRegex(ValueError, "failed/partial"):
                require_completed_stream_cache(path, manifest)

    def test_actual_statistics_refuses_N_before_arrays_corpus_or_output(self):
        original = builtins.__import__

        def closed(name, *args, **kwargs):
            if name.split(".")[0] in {"numpy", "torch", "onnxruntime", "ctypes"}:
                raise AssertionError("numerical import before volume admission")
            return original(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=closed):
            from . import train

            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                (path / "cache.json").write_text(
                    json.dumps(
                        {
                            "schema": "quoridor-terminal-geometry-v1",
                            "stream_intake": {
                                "status": "complete",
                                "scope": "pilot-reference",
                                "human_quantity_n": None,
                            },
                        }
                    )
                )
                with (
                    patch.object(train, "load", side_effect=AssertionError("corpus port")),
                    patch.object(train, "write", side_effect=AssertionError("output port")),
                    self.assertRaisesRegex(ValueError, "N is unset"),
                ):
                    train.prepare_statistics(path, path / "never-created")
                self.assertFalse((path / "never-created").exists())

    def test_actual_fit_admission_checks_added_cache_intake_N_and_failure(self):
        # Reuse control construction, never execute the previous seven tests.
        from .test_distance_steps_admission import FitAdmission, write_control

        case = FitAdmission()
        case.setUp()
        try:
            case.admit()
            (case.cache / "intake-failure.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "failed/partial"):
                case.admit()
            (case.cache / "intake-failure.json").unlink()
            manifest = json.loads((case.cache / "cache.json").read_text())
            manifest["stream_intake"]["human_quantity_n"] = 2
            descriptor = write_control(case.cache / "cache.json", manifest)
            case.common["cache_manifest_sha"] = descriptor["sha256"]
            case.expected["cache_manifest_sha"] = descriptor["sha256"]
            case.refreeze()
            with self.assertRaisesRegex(ValueError, "accepted N"):
                case.admit()
        finally:
            case.doCleanups()


class StreamRepair(unittest.TestCase):
    def manifest(self):
        # Pure control port, not a generated full corpus or minted human permit.
        return {
            "stream_intake": {
                "status": "complete",
                "publication_protocol": "incomplete-marker-last-v1",
                "scope": "full-volume",
                "human_quantity_n": 1,
                "provenance": {
                    "header": {
                        "generator_version": "fixed-d-dual-teacher-pilot-v1",
                        "config": {"phase": "full_volume"},
                        "compiled_sources": {"unexecuted-control-port": "b" * 64},
                        "resource_admission": {},
                    }
                },
            }
        }

    def test_stream_repair_synthetic_full_volume_refuses_before_data(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.manifest()
            header = manifest["stream_intake"]["provenance"]["header"]
            for port, key, value in [
                (header["resource_admission"], "synthetic_fixture", True),
                (header, "generator_version", "synthetic-fixture-v1"),
                (header["config"], "phase", "synthetic_fixture"),
            ]:
                old = port.get(key)
                port[key] = value
                with self.assertRaisesRegex(ValueError, "synthetic"):
                    require_completed_stream_cache(directory, manifest, full_volume=True)
                if old is None:
                    del port[key]
                else:
                    port[key] = old

    def test_stream_repair_incomplete_or_partial_refuses_without_failure_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            manifest = self.manifest()
            require_completed_stream_cache(path, manifest, full_volume=True)
            for name in ["intake-incomplete.json", ".intake.partial"]:
                item = path / name
                if name.startswith("."):
                    item.mkdir()
                else:
                    item.write_text('{"admitted":false}')
                self.assertFalse((path / "intake-failure.json").exists())
                with self.assertRaisesRegex(ValueError, "failed/partial"):
                    require_completed_stream_cache(path, manifest, full_volume=True)
                if item.is_dir():
                    item.rmdir()
                else:
                    item.unlink()


if __name__ == "__main__":
    unittest.main()
