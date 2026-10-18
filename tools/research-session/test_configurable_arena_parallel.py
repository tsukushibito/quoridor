"""Only new configurable count/alternating-core/pool guards; metadata and mocks."""

import copy
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SOURCE = Path(
    os.environ.get(
        "ARENA_PARALLEL_LIFECYCLE",
        Path(__file__).resolve().parents[2] / "scripts/dev/research-lifecycle.py",
    )
)
spec = importlib.util.spec_from_file_location("configured_arena_target", SOURCE)
lc = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = lc
spec.loader.exec_module(lc)


def configuration(count):
    return dict(
        parallel_games=count,
        physical_cpu_pool=list(range(0, 20, 2)),
        operation_ids=[10 + 7 * i for i in range(32)],
        lane_family_B=512 * 1024**2,
        common_family_B=256 * 1024**2,
        lane_storage_B=20 * 1024**2,
        shared_storage_B=8 * 1024**2,
    )


def cohort(count):
    config = configuration(count)
    resolved = lc.resolve_arena_parallel(config)
    return dict(
        parallel=config,
        members=resolved["members"],
        global_controller_cpu=resolved["global_controller_cpu"],
        global_controller_B=resolved["global_controller_B"],
        management_cpu_pool=resolved["management_cpu_pool"],
        shared_storage_B=resolved["shared_storage_B"],
        artifact=dict(path="/synthetic/runner"),
    )


class ConfigurableArenaParallel(unittest.TestCase):
    def test_one_config_resolves_1_3_8_counts_operations_and_budgets(self):
        for count in [1, 3, 8]:
            config = configuration(count)
            value = lc.resolve_arena_parallel(config)
            self.assertEqual(value["CPU"], count + 2)
            self.assertEqual(
                value["family_RAM_B"], count * config["lane_family_B"] + config["common_family_B"]
            )
            self.assertEqual(
                value["whole_B"], count * config["lane_storage_B"] + config["shared_storage_B"]
            )
            self.assertEqual(len(value["members"]), count)
            by_order = []
            for lane, member in enumerate(value["members"]):
                self.assertEqual(member["AI_workers"], [4 + 2 * lane] * 2)
                self.assertEqual(member["main_cpu"], [0, 2][lane % 2])
                self.assertEqual(member["operation_ids"], config["operation_ids"][lane::count])
                self.assertEqual(member["worker_B"] + member["controller_B"], member["family_B"])
                by_order.extend(member["operation_ids"])
            self.assertCountEqual(by_order, config["operation_ids"])
            self.assertEqual(len(lc.arena_cohort_cpus(cohort(count))), count + 2)
        for field, value in [
            ("parallel_games", True),
            ("parallel_games", 9),
            ("operation_ids", [1, 1]),
            ("lane_family_B", 64 * 1024**2),
            ("physical_cpu_pool", [0, 2, 4, 4]),
        ]:
            bad = configuration(3)
            bad[field] = value
            with self.assertRaises(lc.Refused):
                lc.resolve_arena_parallel(bad)

    def test_only_same_game_ai_and_declared_management_can_overlap(self):
        good = cohort(8)
        self.assertEqual(lc.arena_cohort_cpus(good), list(range(0, 20, 2)))
        for case in range(4):
            bad = copy.deepcopy(good)
            if case == 0:
                bad["members"][1]["AI_workers"] = bad["members"][0]["AI_workers"]
            elif case == 1:
                bad["members"][0]["AI_workers"] = [0, 0]
            elif case == 2:
                bad["management_cpu_pool"] = [0, 0]
            else:
                bad["members"][0]["main_cpu"] = 18
            with self.assertRaises(lc.Refused):
                lc.arena_cohort_cpus(bad)
        # Explicit separate A/B roles remain supported; no historical-mode shim.
        explicit = dict(
            members=[dict(lane=0, AI_workers=[4, 6], main_cpu=2)], global_controller_cpu=0
        )
        self.assertEqual(lc.arena_cohort_cpus(explicit), [0, 2, 4, 6])

    def test_actual_physical_and_ram_guard_still_rejects_siblings_and_shortage(self):
        value = cohort(8)
        member = value["members"][0]
        spec = dict(
            kind="run",
            experiment={},
            child_cpu_cores=[0, 4],
            limits=dict(
                worker_cpu=4, guardian_cpu=0, family_B=512 * 1024**2, host_reserve_B=4 * 1024**3
            ),
        )
        original = Path.read_text

        def metadata(path, *args, **kwargs):
            text = str(path)
            if text.startswith("/sys/devices/system/cpu/cpu"):
                cpu = int(text.split("/cpu")[-1].split("/")[0])
                return (
                    "0"
                    if text.endswith("physical_package_id")
                    else str((4 if cpu == 6 else cpu) // 2)
                )
            return original(path, *args, **kwargs)

        with (
            patch.object(lc, "arena_cohort", return_value=(value, member)),
            patch.object(lc, "document", return_value={"phase": "arena"}),
            patch.object(lc, "arena_cpu_cores", return_value=[0, 4]),
            patch.object(lc.process, "available_memory", return_value=20 * 1024**3),
            patch.object(lc.os, "sched_getaffinity", return_value={0}),
            patch.object(Path, "read_text", metadata),
        ):
            with self.assertRaisesRegex(lc.Refused, "distinct physical cores"):
                lc.physical_and_quiet(spec)
        with (
            patch.object(lc, "arena_cohort", return_value=(value, member)),
            patch.object(lc.process, "available_memory", return_value=4 * 1024**3),
        ):
            with self.assertRaisesRegex(lc.Refused, "physical RAM admission"):
                lc.physical_and_quiet(spec)


if __name__ == "__main__":
    unittest.main()
