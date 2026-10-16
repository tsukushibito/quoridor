"""Metadata-only coverage for the maintained native MCTS materialization boundary."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


def lifecycle():
    path = Path(__file__).with_name("research-lifecycle.py")
    loader = importlib.util.spec_from_file_location("lc_mcts_test", path)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


class MctsMaterialization(unittest.TestCase):
    def test_bound_config_list_and_manifest_directory_argv(self):
        lc = lifecycle()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()

            def save(name, value):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value))
                return lc.artifact_ref(path)

            streams = [save(f"dataset-{i}/manifest.json", {"fixture": i}) for i in range(2)]
            configs = [save(f"config-{i}.json", {"fixture_config": i}) for i in range(2)]
            bindings = [{k: r[k] for k in ("path", "sha256")} for r in configs]
            listed = save("config-list.json", bindings)
            request = dict(
                schema="quoridor.common-corpus-cache-materialization.v1",
                streams=streams,
                output=str(root / "cache"),
                mcts_configs=listed,
            )
            request_ref = save("request.json", request)
            manifest = {"artifact": {"path": "/actual/terminal-cache"}}
            argv = [manifest["artifact"]["path"]]
            for ref in streams:
                argv.extend(["--input", str(Path(ref["path"]).parent)])
            argv.extend(
                [
                    "--output",
                    request["output"],
                    "--mcts-configs",
                    listed["path"],
                    "--mcts-configs-sha256",
                    listed["sha256"],
                ]
            )
            experiment = dict(
                config=request_ref,
                inputs=[*streams, listed, *configs],
                models=[],
                planned_slots=0,
                batch=None,
                numerical_qualification=None,
                rules="research-standard-2p-threefold-goal-first-v1",
                distance_units="wall-distance/80",
                value_perspective="side-to-move",
                argv=argv,
            )
            spec = dict(
                data_root=request["output"],
                data=[{"name": n, "path": str(root / "cache" / n)} for n in lc.COMPACT_CACHE_WIDTHS]
                + [{"name": "cache_manifest", "path": str(root / "cache/cache.json")}],
            )
            lc.cache_materialize_check(spec, experiment, manifest)
            for mutation in ("missing_config", "file_argv", "list_hash"):
                bad = copy.deepcopy(experiment)
                if mutation == "missing_config":
                    bad["inputs"].remove(configs[0])
                elif mutation == "file_argv":
                    bad["argv"][2] = streams[0]["path"]
                else:
                    broken = dict(request, mcts_configs=dict(listed, sha256="0" * 64))
                    bad["config"] = save("bad-request.json", broken)
                    bad["inputs"][2] = broken["mcts_configs"]
                with self.subTest(mutation=mutation), self.assertRaises(lc.Refused):
                    lc.cache_materialize_check(spec, bad, manifest)
            alpha_request = {k: v for k, v in request.items() if k != "mcts_configs"}
            experiment["config"] = save("alpha-request.json", alpha_request)
            experiment["argv"] = [manifest["artifact"]["path"]]
            for ref in streams:
                experiment["argv"].extend(["--input", ref["path"]])
            experiment["argv"].extend(["--output", request["output"]])
            lc.cache_materialize_check(spec, experiment, manifest)

    def test_collection_keeps_native_manifest_lineage_and_actual_compact_hashes(self):
        lc = lifecycle()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            cache_dir = root / "cache"
            cache_dir.mkdir()

            def save(path, value):
                path.write_text(json.dumps(value))
                return lc.artifact_ref(path)

            stream = save(root / "manifest.json", {"fixture_manifest": True})
            listed = save(root / "config-list.json", [])
            request = dict(
                schema="quoridor.common-corpus-cache-materialization.v1",
                streams=[stream],
                output=str(cache_dir),
                mcts_configs=listed,
            )
            request_ref = save(root / "request.json", request)
            build = save(root / "build.json", {"artifact_target": "terminal-cache"})
            files = {}
            for name, width in lc.COMPACT_CACHE_WIDTHS.items():
                path = cache_dir / name
                path.write_bytes(bytes(width))
                files[name] = lc.artifact_ref(path)
            binding = {k: stream[k] for k in ("path", "sha256")}
            cache = dict(
                schema="quoridor-common-corpus-terminal-geometry-v3",
                rows=1,
                stream_intake=dict(status="complete", scope="common-corpus"),
                source_binding=[binding],
                source_content=[
                    dict(encoding="native-teacher-dataset-shards-v1", manifest=binding)
                ],
                mcts_native_configs={k: listed[k] for k in ("path", "sha256")},
                dataset_sha=listed["sha256"],
                common_corpus=dict(rootmean_is_raw=True),
                mcts_datasets=[dict(dataset=str(root), manifest_sha256=stream["sha256"], rows=1)],
                files={n: n for n in files},
                sha256={n: r["sha256"] for n, r in files.items()},
                file_bytes={n: r["bytes"] for n, r in files.items()},
            )
            cache_path = cache_dir / "cache.json"
            save(cache_path, cache)
            spec = dict(
                owner=str(root),
                data_root=str(cache_dir),
                data=[dict(name=n, path=str(cache_dir / n), limit_B=100000) for n in files]
                + [dict(name="cache_manifest", path=str(cache_path), limit_B=100000)],
            )
            experiment = dict(
                phase="materialize",
                argv=["unused", "--input"],
                planned_slots=0,
                config=request_ref,
                build_manifest=build,
            )
            result = lc.collect_data(spec, experiment)
            self.assertEqual(result["status"], "PASS", result["errors"])
            for mutation in ("gzip_claim", "list_sha", "raw_policy", "row_sum", "bytes"):
                bad = copy.deepcopy(cache)
                if mutation == "gzip_claim":
                    bad["source_content"][0] = dict(
                        encoding="gzip-single-member-v1", compressed=stream
                    )
                elif mutation == "list_sha":
                    bad["dataset_sha"] = "0" * 64
                elif mutation == "raw_policy":
                    bad["common_corpus"]["rootmean_is_raw"] = False
                elif mutation == "row_sum":
                    bad["mcts_datasets"][0]["rows"] = 2
                else:
                    bad["sha256"][next(iter(files))] = "0" * 64
                save(cache_path, bad)
                with self.subTest(mutation=mutation):
                    self.assertEqual(lc.collect_data(spec, experiment)["status"], "FAILED")
            alpha = copy.deepcopy(cache)
            alpha["source_content"] = [dict(encoding="gzip-single-member-v1", compressed=stream)]
            save(cache_path, alpha)
            request.pop("mcts_configs")
            experiment["config"] = save(root / "request-alpha.json", request)
            self.assertEqual(lc.collect_data(spec, experiment)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
