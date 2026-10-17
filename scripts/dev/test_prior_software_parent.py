"""Pure metadata qualification boundaries; no Cargo, native program or model calls."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

loader = importlib.util.spec_from_file_location(
    "prior_software_under_test", Path(__file__).with_name("research-lifecycle.py")
)
lc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(lc)


class PriorSoftwareParentTests(unittest.TestCase):
    def test_selected_pass_attributed_final_failure_and_clippy_forms(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def write(name, value):
                path = root / name
                path.write_text(json.dumps(value))
                return lc.artifact_ref(path)

            log = write("fake-log.json", {"fixture_only": "not qualification evidence"})
            argv = [
                "cargo",
                "clippy",
                "--offline",
                "--locked",
                "-j1",
                "--no-deps",
                "--",
                "-D",
                "warnings",
            ]
            good = {
                "name": "selected-lint",
                "status": "PASS",
                "capture_complete": True,
                "primary": None,
                "secondary": [],
                "argv": argv,
                "full_log": log,
                "guardian_return": {
                    "command": argv,
                    "exit_code": 0,
                    "direct_child_reaped": True,
                    "cleanup_complete": True,
                    "handle_closes_complete": True,
                    "remaining": [],
                },
            }
            error = {"type": "Refused", "message": "different final check", "notes": []}
            failed = {"name": "later-test", "status": "FAILED", "primary": error}
            receipt = {"checks": [good, failed], "primary": error}

            def evaluate(value, names=("selected-lint",)):
                ref = write("fake-receipt.json", value)
                adoption = {
                    "schema": "quoridor.research.source-adoption.v1",
                    "status": "ACCEPTED",
                    "prior_software": {
                        "subjects": [log],
                        "receipts": [{"file": ref, "name": name} for name in names],
                    },
                }
                return lc.prior_software_roles(write("fake-adoption.json", adoption))

            self.assertEqual(evaluate(receipt), {"lint"})
            plain = {"checks": [good], "primary": None}
            self.assertEqual(evaluate(plain), {"lint"})
            joined = copy.deepcopy(receipt)
            joined["checks"][0]["argv"][-2:] = ["-Dwarnings"]
            self.assertEqual(evaluate(joined), {"lint"})
            test = copy.deepcopy(receipt)
            test["checks"][0]["argv"][1] = "test"
            self.assertEqual(evaluate(test), {"test"})

            negatives = []
            no_failed = copy.deepcopy(receipt)
            no_failed["checks"].pop()
            negatives.append(no_failed)
            not_final = copy.deepcopy(receipt)
            not_final["checks"].reverse()
            negatives.append(not_final)
            mismatched = copy.deepcopy(receipt)
            mismatched["primary"] = {"message": "unaccounted parent error"}
            negatives.append(mismatched)
            multiple = copy.deepcopy(receipt)
            multiple["checks"].append(copy.deepcopy(failed))
            negatives.extend([multiple, {**multiple, "primary": None}])
            duplicate = copy.deepcopy(receipt)
            duplicate["checks"].insert(0, copy.deepcopy(good))
            negatives.append(duplicate)
            for field, value in [
                ("status", "PARTIAL"),
                ("capture_complete", False),
                ("primary", error),
                ("secondary", [error]),
            ]:
                bad = copy.deepcopy(receipt)
                bad["checks"][0][field] = value
                negatives.append(bad)
            for field, value in [
                ("command", ["substituted"]),
                ("exit_code", 1),
                ("direct_child_reaped", False),
                ("cleanup_complete", False),
                ("handle_closes_complete", False),
                ("remaining", [{"pid": 1}]),
            ]:
                bad = copy.deepcopy(receipt)
                bad["checks"][0]["guardian_return"][field] = value
                negatives.append(bad)
            for removed in ["--offline", "--locked", "-j1", "--no-deps", "warnings"]:
                bad = copy.deepcopy(receipt)
                bad["checks"][0]["argv"].remove(removed)
                negatives.append(bad)
            for added in ["-Aunused", "--allow=unused"]:
                bad = copy.deepcopy(receipt)
                bad["checks"][0]["argv"].append(added)
                negatives.append(bad)
            external_build = copy.deepcopy(receipt)
            external_build["checks"][0]["argv"][1] = "build"
            negatives.append(external_build)
            for index, bad in enumerate(negatives):
                with self.subTest(negative=index), self.assertRaises(lc.Refused):
                    evaluate(bad)
            for names in [("later-test",), ("selected-lint", "selected-lint")]:
                with self.subTest(selection=names), self.assertRaises(lc.Refused):
                    evaluate(receipt, names)
            (root / "fake-log.json").write_text("drift")
            with self.assertRaises(lc.Refused):
                evaluate(receipt)


if __name__ == "__main__":
    unittest.main()
