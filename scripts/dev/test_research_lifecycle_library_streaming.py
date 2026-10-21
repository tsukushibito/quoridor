"""Binary library identity must fit the normal management memory reservation."""

from contextlib import ExitStack
import hashlib
import importlib.util
import os
from pathlib import Path
import resource
import tempfile
import unittest
from unittest.mock import patch


class LibraryStreaming(unittest.TestCase):
    def test_large_library_preserves_identity_checks_with_64mib_address_space(self):
        loader = importlib.util.spec_from_file_location(
            "lc_library_streaming", Path(__file__).with_name("research-lifecycle.py")
        )
        lc = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(lc)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "large-library.so"
            size = 80 * 1024**2
            with library.open("wb") as stream:
                stream.truncate(size)
            library.chmod(0o644)
            digest = hashlib.sha256()
            chunk = bytes(1024**2)
            for _ in range(80):
                digest.update(chunk)
            del chunk
            library_ref = dict(
                path=str(library), sha256=digest.hexdigest(), bytes=size, mode="0644"
            )

            def save(name, value):
                path = root / name
                lc.new_json(path, value)
                return lc.bound(path)[0]

            config = save("config.json", {})
            schedule = save("schedule.json", [])
            plan = save("plan.json", {})
            artifact = dict(path=str(root / "unused-native"))
            build = dict(artifact=artifact)
            experiment = dict(
                schema=lc.EXPERIMENT_SCHEMA,
                phase="generation",
                build_manifest={},
                config=config,
                schedule=schedule,
                inputs=[],
                models=[],
                dynamic_libraries=[dict(file=library_ref, version="fixture")],
                planned_slots=0,
                argv=[artifact["path"], "generate"],
            )
            experiment_ref = save("experiment.json", experiment)
            data = root / "not-entered-data"
            spec = dict(
                kind="run",
                experiment=experiment_ref,
                artifact=artifact,
                approved_plan=plan,
                owner=tmp,
                output=str(root / "unused-operation"),
                data_root=str(data),
                data=[dict(name="fixture", path=str(data / "fixture.json"))],
                argv=experiment["argv"],
                finalizers=[],
            )
            # Other phase/source obligations are outside this synthetic binary-input test.
            # Actual read_ref/artifact_ref and their before/after identity checks stay live.
            with ExitStack() as stack:
                stack.enter_context(patch.object(lc, "experiment_phase_check"))
                stack.enter_context(patch.object(lc, "accepted_build", return_value=build))
                stack.enter_context(patch.object(lc, "caller_source_refs", return_value=[]))
                stack.enter_context(patch.object(lc, "approved_plan", return_value={}))
                stack.enter_context(patch.object(lc, "generation_check"))
                old_limit = resource.getrlimit(resource.RLIMIT_AS)
                resource.setrlimit(resource.RLIMIT_AS, (64 * 1024**2, old_limit[1]))
                try:
                    actual, _, refs = lc.experiment_check(spec)
                    self.assertEqual(actual, experiment)
                    self.assertIn(library_ref, refs)
                    library.chmod(0o600)
                    with self.assertRaisesRegex(ValueError, "actual streamed input identity"):
                        lc.experiment_check(spec)
                    library.chmod(0o644)
                    with library.open("r+b") as stream:
                        stream.write(b"x")
                    with self.assertRaisesRegex(ValueError, "actual streamed input identity"):
                        lc.experiment_check(spec)
                finally:
                    resource.setrlimit(resource.RLIMIT_AS, old_limit)
            self.assertFalse(data.exists())
            self.assertEqual(os.stat(library).st_size, size)


if __name__ == "__main__":
    unittest.main()
