"""Quality command routing without formatters, frameworks, or model jobs."""

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "quality_entrypoints", ROOT / "scripts/dev/check-research.py"
)
QUALITY = importlib.util.module_from_spec(spec)
spec.loader.exec_module(QUALITY)


class QualityEntryPointContracts(unittest.TestCase):
    def test_nn0_runs_all_named_contracts_even_when_live_environment_is_set(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename in (
                "tools/research-quality/node_modules/.bin/prettier",
                "project/bin/ruff",
                "project/bin/python",
            ):
                file = root / filename
                file.parent.mkdir(parents=True, exist_ok=True)
                file.touch()
            (root / "research-paths.json").write_text(
                json.dumps(
                    {
                        "environments": {
                            "project": str(root / "project"),
                        }
                    }
                )
            )
            with (
                patch.object(QUALITY, "ROOT", root),
                patch.object(QUALITY, "sources", return_value=([], [])),
                patch.object(QUALITY.subprocess, "run") as execute,
                patch.dict(os.environ, {"QUORIDOR_OBSERVATION_LIVE_TESTS": "1"}, clear=True),
                patch("sys.argv", ["check-research.py"]),
            ):
                QUALITY.main()
            storage_calls = [
                call
                for call in execute.call_args_list
                if "scripts/dev/test_research_storage.py" in call.args[0]
            ]
            self.assertEqual(len(storage_calls), 1)
            self.assertIn("scripts/dev/test_research_storage.py", QUALITY.PY_FILES)
            training_call = next(
                call
                for call in execute.call_args_list
                if call.args[0][0] == str(root / "project/bin/python")
            )
            modules = training_call.args[0][4:]
            self.assertEqual(tuple(modules), QUALITY.NN0_TESTS)
            self.assertIn("quoridor_training.test_sampling", modules)
            self.assertIn("quoridor_training.test_selected_target", modules)
            self.assertIn("quoridor_training.test_sharded_cache", modules)
            self.assertIn("quoridor_training.test_observation.ObservationContracts", modules)
            self.assertFalse(set(QUALITY.MODEL_TESTS) & set(modules))

    def test_model_gate_requires_explicit_admission_before_running_any_command(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("sys.argv", ["check-research.py", "--model-tests"]),
            patch.object(QUALITY.subprocess, "run") as execute,
        ):
            with self.assertRaises(SystemExit) as error:
                QUALITY.main()
            self.assertEqual(error.exception.code, 2)
            execute.assert_not_called()

    def test_model_gate_requires_an_existing_owned_fixture_directory(self):
        with (
            patch.dict(os.environ, {"QUORIDOR_OBSERVATION_LIVE_TESTS": "1"}, clear=True),
            patch("sys.argv", ["check-research.py", "--model-tests"]),
            patch.object(QUALITY.subprocess, "run") as execute,
        ):
            with self.assertRaises(SystemExit) as error:
                QUALITY.main()
            self.assertEqual(error.exception.code, 2)
            execute.assert_not_called()

    def test_normal_gate_keeps_one_project_interpreter_across_all_test_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environments = [root / "first", root / "replacement"]
            for environment in environments:
                for binary in ("ruff", "python"):
                    file = environment / "bin" / binary
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.touch()
            prettier = root / "tools/research-quality/node_modules/.bin/prettier"
            prettier.parent.mkdir(parents=True)
            prettier.touch()
            layout = root / "research-paths.json"
            layout.write_text(json.dumps({"environments": {"project": str(environments[0])}}))

            def replace_layout_after_first_command(*args, **kwargs):
                layout.write_text(json.dumps({"environments": {"project": str(environments[1])}}))

            with (
                patch.object(QUALITY, "ROOT", root),
                patch.object(QUALITY, "sources", return_value=([], [])),
                patch.object(
                    QUALITY.subprocess, "run", side_effect=replace_layout_after_first_command
                ) as execute,
                patch.dict(os.environ, {}, clear=True),
                patch("sys.argv", ["check-research.py"]),
            ):
                QUALITY.main()
            interpreters = {str(environment / "bin/python") for environment in environments}
            selected = [
                call.args[0][0]
                for call in execute.call_args_list
                if call.args[0][0] in interpreters
            ]
            self.assertEqual(selected, [str(environments[0] / "bin/python")] * 2)
            self.assertEqual(
                json.loads(layout.read_text())["environments"]["project"], str(environments[1])
            )


if __name__ == "__main__":
    unittest.main()
