"""Manifest-bound scalar label views on an unchanged common corpus.

The existing LR mask selects the actually evaluated reflected board/history.
No neural reflection invariance or calibration as WDL is assumed.
"""

import hashlib
import json

from .common import bound_file_bytes


class TeacherValues:
    """A scalar sidecar reader; model adapters and scientific choices live outside."""

    def __init__(self, selection, corpus, train_rows, validation_rows):
        import numpy as np

        if (
            not isinstance(selection, dict)
            or set(selection) != {"manifest", "objective"}
            or not isinstance(selection["objective"], str)
            or not selection["objective"]
        ):
            raise ValueError("bound label manifest and explicit objective key required")
        manifest = json.loads(bound_file_bytes(selection["manifest"], 1024**2))
        required = {
            "schema",
            "cache_manifest_sha256",
            "indices",
            "rows",
            "row_ids_sha256",
            "train_indices_sha256",
            "validation_indices_sha256",
            "canonical_input_identities",
            "reflected_train_input_identities",
            "source_projection",
            "reflection_semantics",
            "targets",
            "outcome_target",
        }
        if (
            not isinstance(manifest, dict)
            or set(manifest) != required
            or manifest["schema"] != "quoridor-static-teacher-values-v1"
            or manifest["cache_manifest_sha256"] != corpus.manifest_sha
            or manifest["reflection_semantics"] != "evaluated-reflected-board-and-fullhistory"
            or not isinstance(manifest["targets"], dict)
            or not manifest["targets"]
        ):
            raise ValueError(
                "bound existing cache and actual canonical/reflected label views required"
            )
        self.indices = np.frombuffer(bound_file_bytes(manifest["indices"], 1024**2), dtype="<i8")
        self.train = np.asarray(train_rows, dtype="<i8")
        validation = np.asarray(validation_rows, dtype="<i8")
        expected = np.sort(np.concatenate((self.train, validation)))
        if (
            type(manifest["rows"]) is not int
            or manifest["rows"] != len(expected)
            or not len(expected)
            or not np.array_equal(self.indices, expected)
            or np.any(np.diff(self.indices) <= 0)
            or np.any(np.diff(self.train) <= 0)
            or self.indices[0] < 0
            or self.indices[-1] >= corpus.row_count
            or np.any(corpus.splits[self.train] != 0)
            or np.any(corpus.splits[validation] != 1)
            or not corpus.eligible[expected].all()
            or manifest["train_indices_sha256"] != hashlib.sha256(self.train.tobytes()).hexdigest()
            or manifest["validation_indices_sha256"]
            != hashlib.sha256(validation.tobytes()).hexdigest()
        ):
            raise ValueError("exact configured T/full V membership required")
        row_ids = [corpus.manifest["sampling"]["row_ids"][int(i)] for i in self.indices]
        digest = hashlib.sha256(
            json.dumps(row_ids, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
        if manifest["row_ids_sha256"] != digest:
            raise ValueError("original cache row identity correspondence")
        # Per row: prefix SHA, full-state SHA, full-history digest, native input SHA.
        for key, count in (
            ("canonical_input_identities", len(expected)),
            ("reflected_train_input_identities", len(self.train)),
        ):
            if len(bound_file_bytes(manifest[key], 4 * 1024**2)) != count * 128:
                raise ValueError("complete per-row canonical/reflected input identities")
        bound_file_bytes(manifest["source_projection"], 1024**2)
        self.values, self.metadata = {}, manifest["targets"]
        for name, item in self.metadata.items():
            if (
                not isinstance(name, str)
                or not name
                or not isinstance(item, dict)
                or not isinstance(item.get("display_name"), str)
                or not item["display_name"]
            ):
                raise ValueError("target keys/display names come from the resolved manifest")
            if item.get("source") == "cache":
                if (
                    set(item) != {"source", "display_name", "column", "value_semantics"}
                    or item["value_semantics"] != "literal-stm-outcome"
                    or item["column"] not in corpus.manifest["label_columns"]
                ):
                    raise ValueError("declared original cache outcome column required")
                column = corpus.manifest["label_columns"].index(item["column"])
                if column >= corpus.labels.shape[1]:
                    raise ValueError("declared cache target column unavailable")
                self.values[name] = column
            elif item.get("source") == "sidecar":
                if (
                    set(item)
                    != {
                        "source",
                        "display_name",
                        "identity",
                        "value_semantics",
                        "canonical",
                        "reflected_train",
                    }
                    or item["value_semantics"] != "raw-local-stm-single-network-post-tanh"
                    or not isinstance(item["identity"], dict)
                    or not item["identity"]
                ):
                    raise ValueError("actual teacher identity and raw local STM semantics required")
                canonical = np.frombuffer(bound_file_bytes(item["canonical"], 1024**2), dtype="<f4")
                reflected = np.frombuffer(
                    bound_file_bytes(item["reflected_train"], 1024**2), dtype="<f4"
                )
                if (
                    canonical.shape != (len(expected),)
                    or reflected.shape != (len(self.train),)
                    or any(
                        not np.isfinite(x).all() or np.any(np.abs(x) > 1)
                        for x in (canonical, reflected)
                    )
                ):
                    raise ValueError(
                        "finite FP32 canonical T/V and actually reflected T labels required"
                    )
                self.values[name] = canonical, reflected
            else:
                raise ValueError("label source must be an existing cache column or scalar sidecar")
        self.corpus = corpus
        self.objective = selection["objective"]
        self.outcome_name = manifest["outcome_target"]
        if (
            self.objective not in self.values
            or self.outcome_name not in self.values
            or type(self.values[self.outcome_name]) is not int
        ):
            raise ValueError("selected objective and unchanged cache outcome provenance required")
        self.outcome_column = self.values[self.outcome_name]
        self.binding = {
            "manifest": selection["manifest"],
            "objective": self.objective,
            "reflection_semantics": manifest["reflection_semantics"],
        }

    def take(self, indices, reflection_mask=None, *, target=None):
        import numpy as np

        rows = np.asarray(indices)
        if rows.ndim != 1 or rows.dtype.kind not in "iu":
            raise ValueError("integer row indices required")
        offsets = np.searchsorted(self.indices, rows)
        if np.any(offsets >= len(self.indices)) or not np.array_equal(self.indices[offsets], rows):
            raise ValueError("row outside bound original T/V membership")
        mask = (
            np.zeros(len(rows), dtype=bool)
            if reflection_mask is None
            else np.asarray(reflection_mask)
        )
        if mask.dtype != np.dtype(bool) or mask.shape != rows.shape:
            raise ValueError("actual existing source LR mask required")
        positions = np.searchsorted(self.train, rows[mask])
        if np.any(positions >= len(self.train)) or not np.array_equal(
            self.train[positions], rows[mask]
        ):
            raise ValueError("reflected V or non-T labels are not part of this sidecar")
        name = self.objective if target is None else target
        if name not in self.values:
            raise ValueError("target is absent from the resolved label manifest")
        source = self.values[name]
        if type(source) is int:
            values = self.corpus.labels[rows, source]
            if not np.isfinite(values).all() or not np.isin(values, (-1, 0, 1)).all():
                raise ValueError("original outcome provenance is not finite literal z")
            return values
        canonical, reflected = source
        values = canonical[offsets]
        values[mask] = reflected[positions]
        return values
