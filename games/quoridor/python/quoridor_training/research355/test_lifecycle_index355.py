"""Only the stopped index's root file map gets its existing 512-name bound."""

import copy
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

import lifecycle355 as life
import stream355 as stream
import strength355 as s


class IndexDecoderBoundary(unittest.TestCase):
    def test_original_bound_index_and_context_specific_file_map(self):
        phase = Path(__file__).resolve().parents[5] / (
            ".artifacts/value-search-strength355-analysis-v1/index-decoder-repair-v21"
        )
        tmp = phase / "TMP"
        tmp.mkdir(exist_ok=True)
        original = phase.parent / "joint-analysis-entry-v1/analysis-config.json"
        original_ref = {
            "path": str(original),
            "sha256": "56fbb4794e25eef63c5be646d20929a1c92a21f35aecb619a54a20367db8c686",
            "bytes": 122582,
            "mode": "0644",
        }
        allowed_reads = {str(original)}
        with mock.patch.object(life.io355, "identity", wraps=life.io355.identity) as identities:
            metadata = life.Metadata()
            actual = metadata.read(original_ref, life.io355.MAX_INDEX_BYTES)
            self.assertEqual(len(actual["files"]), 272)
            self.assertEqual(
                hashlib.sha256(original.read_bytes()).hexdigest(), original_ref["sha256"]
            )
            self.assertEqual(stream.Inputs(actual).total, 119379184)
            metadata.after()
            # No Inputs.get/lines/after or producer/scientific function executes.
            with tempfile.TemporaryDirectory(dir=tmp) as directory:
                path = Path(directory) / "metadata.json"
                allowed_reads.add(str(path))

                def decode(value, *, raw=None, drift=False):
                    raw = json.dumps(value, allow_nan=False).encode() if raw is None else raw
                    self.assertLessEqual(len(raw), 524288)
                    path.write_bytes(raw)
                    ref = {
                        "path": str(path),
                        "sha256": "f" * 64 if drift else hashlib.sha256(raw).hexdigest(),
                        "bytes": len(raw),
                        "mode": format(stat.S_IMODE(path.stat().st_mode), "04o"),
                    }
                    return life.Metadata().read(ref, life.io355.MAX_INDEX_BYTES)

                expanded = copy.deepcopy(actual)
                exemplar = next(iter(actual["files"].values()))
                for number in range(272, 512):
                    expanded["files"][str(number)] = {
                        **exemplar,
                        "path": str(Path(directory) / f"unread-input-{number}"),
                        "bytes": 0,
                    }
                with self.subTest(case="512_exact_typed_file_map"):
                    accepted = decode(expanded)
                    self.assertEqual(len(accepted["files"]), 512)
                    view = stream.Inputs(accepted)
                    self.assertEqual(view.total, 119379184)
                    self.assertEqual(view.progress["rows_read"], 0)

                invalid = []
                oversized = copy.deepcopy(expanded)
                oversized["files"]["512"] = exemplar
                invalid.append(("513", oversized, None, "object field cap"))
                invalid.append(
                    ("generic257", {str(i): i for i in range(257)}, None, "object field cap")
                )
                wrong = copy.deepcopy(expanded)
                wrong["schema"] = "quoridor.strength355.not-an-index.v1"
                invalid.append(("wrong_schema", wrong, None, "object field cap"))
                nested = {
                    "schema": actual["schema"],
                    "files": {"0": {str(i): i for i in range(257)}},
                }
                invalid.append(("nested_FileRef257", nested, None, "object field cap"))
                invalid.append(("nested_index", {"nested": expanded}, None, "object field cap"))
                invalid.append(
                    (
                        "sibling257",
                        {"schema": actual["schema"], "other": {str(i): i for i in range(257)}},
                        None,
                        "object field cap",
                    )
                )
                root = {"schema": actual["schema"], **{str(i): i for i in range(256)}}
                invalid.append(("root257", root, None, "object field cap"))
                invalid.append(("NaN", None, b'{"n":NaN}', "nonfinite JSON constant"))
                invalid.append(("overflow", None, b'{"n":1e309}', "finite numeric domain"))
                duplicate = (
                    '{"schema":' + json.dumps(actual["schema"]) + ',"files":{"a":{},"a":{}}}'
                ).encode()
                invalid.append(("duplicate_key", None, duplicate, "duplicate JSON key"))
                invalid.append(("string", {"n": "x" * (s.MAX_STRING + 1)}, None, "string cap"))
                invalid.append(("array", {"n": [0] * 1025}, None, "array cap"))
                deep = 0
                for _ in range(25):
                    deep = [deep]
                invalid.append(("depth", deep, None, "JSON nesting cap"))
                for name, value, raw, reason in invalid:
                    with self.subTest(case=name), self.assertRaisesRegex(ValueError, reason):
                        decode(value, raw=raw)
                with self.subTest(case="bound_metadata_hash_drift"):
                    with self.assertRaisesRegex(ValueError, "input SHA-size-mode drift"):
                        decode(expanded, drift=True)
                with self.subTest(case="index_byte_limit"):
                    with self.assertRaisesRegex(ValueError, "UTF8 record cap"):
                        s.strict_json(
                            b" " * (life.io355.MAX_INDEX_BYTES + 1), life.io355.MAX_INDEX_BYTES
                        )
                with self.subTest(case="FileRef_semantics_unchanged"):
                    bad = copy.deepcopy(expanded)
                    bad["files"]["0"]["SHA256"] = "not-a-hash"
                    with self.assertRaisesRegex(ValueError, "SHA256 domain"):
                        stream.Inputs(decode(bad))
            self.assertTrue(
                all(str(call.args[0]) in allowed_reads for call in identities.call_args_list)
            )
        self.assertEqual(list(tmp.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
