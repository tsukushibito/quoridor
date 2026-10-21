"""In-memory teacher contract/metadata tests only; no teacher, games or fit."""

import copy
from dataclasses import replace
import unittest
from unittest.mock import patch

from othello_training import data, pattern, train
from test_pattern_data import inputs, load


def teacher_inputs(train_count=16, validation_count=8, holdout_count=1):
    config, rows = inputs(train_count, validation_count, holdout_count)
    config.update(
        labelKind="teacherEstimate",
        labelSource="fixed-strong-teacher-estimate",
        teacher=dict(
            id="synthetic-fixed-teacher",
            source="git:synthetic-source",
            weights="sha256:synthetic-weights",
            adapter="sha256:synthetic-adapter",
            args=["--one-thread"],
        ),
    )
    for row in rows:
        row["labelKind"] = "teacherEstimate"
        row["teacher"] = dict(
            id=config["teacher"]["id"],
            rawSTMScore=2,
            scorePerspective="state.toMove",
            scoreUnits="engine-disc",
            scaleToCentidiscs=100,
            bound="UNKNOWN",
            proven=None,
        )
    return config, rows


class PatternTeacher(unittest.TestCase):
    def test_different_estimates_in_same_game_are_not_outcome_labels(self):
        config, rows = teacher_inputs()
        later = copy.deepcopy(rows[0])
        empty = [i for i, c in enumerate(later["state"]["board"]) if c == 0]
        for i in empty[:4]:
            later["state"]["board"][i] = 1
        later["state"]["toMove"] = 2
        later["teacher"]["rawSTMScore"] = -5.5
        later["targetCentidiscs"] = -550
        parsed = load(config, rows + [later])
        self.assertEqual(parsed.inferred_final_black_minus_white, {})
        self.assertEqual(parsed.train[-1].teacher["rawSTMScore"], -5.5)
        metadata = train.label_metadata(parsed, config)
        self.assertNotIn("inferredFinalBlackMinusWhite", metadata)
        self.assertNotIn("terminalVerification", metadata)
        self.assertEqual(
            metadata["labelProvenance"],
            dict(
                labelKind="teacherEstimate",
                labelSource=config["labelSource"],
                teacherId=config["teacher"]["id"],
            ),
        )

    def test_target_units_identity_orientation_finite_and_proof_reject(self):
        invalid = [
            ("id", "other"),
            ("scorePerspective", "black"),
            ("scoreUnits", "centidisc"),
            ("scaleToCentidiscs", 1),
            ("scaleToCentidiscs", 100.0),
            ("rawSTMScore", float("nan")),
            ("rawSTMScore", float("inf")),
            ("rawSTMScore", 65),
            ("rawSTMScore", True),
            ("bound", "unknown"),
            ("proven", 1),
            ("proven", "UNKNOWN"),
            ("completedDepth", 2.5),
            ("reportedProbability", 101),
            ("outerWallMs", -1),
            ("requestedTimeMs", True),
        ]
        for field, value in invalid:
            config, rows = teacher_inputs()
            rows[0]["teacher"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                load(config, rows)
        for target in [True, 2, 201, float("inf")]:
            config, rows = teacher_inputs()
            rows[0]["targetCentidiscs"] = target
            with self.subTest(target=target), self.assertRaises(ValueError):
                load(config, rows)
        for field in data.TEACHER_REQUIRED:
            config, rows = teacher_inputs()
            del rows[0]["teacher"][field]
            with self.subTest(missing=field), self.assertRaises(ValueError):
                load(config, rows)

    def test_reported_metrics_and_unknowns_never_fabricate_proven(self):
        config, rows = teacher_inputs()
        rows[0]["teacher"].update(
            rawSTMScore=1.25,
            completedDepth=64,
            reportedProbability=100,
            internalElapsedMs="UNKNOWN",
            outerWallMs=31.5,
            requestedTimeMs=25,
        )
        rows[0]["targetCentidiscs"] = 125
        parsed = load(config, rows)
        self.assertIsNone(parsed.train[0].teacher["proven"])
        self.assertEqual(parsed.train[0].teacher["bound"], "UNKNOWN")
        self.assertEqual(parsed.train[0].teacher["internalElapsedMs"], "UNKNOWN")
        self.assertIsNone(parsed.train[1].teacher["completedDepth"])
        counts = train.label_metadata(parsed, config)["teacherMetadataAvailability"]
        self.assertEqual(counts["outerWallMs"], dict(reported=1, unknown=23))

    def test_holdout_and_cross_split_rows_cannot_update_or_select(self):
        config, rows = teacher_inputs()
        forbidden = copy.deepcopy(rows[0])
        forbidden["openingFamily"] = config["holdoutFamilies"][0]
        with (
            patch.object(pattern, "features") as features,
            self.assertRaisesRegex(ValueError, "H/final"),
        ):
            load(config, [forbidden] + rows)
        features.assert_not_called()
        parsed = load(config, rows)
        bad = replace(
            parsed, train=(replace(parsed.train[0], family=config["holdoutFamilies"][0]),)
        )
        with self.assertRaisesRegex(ValueError, "split"):
            data.validate_fit_splits(bad, config)
        bad = replace(parsed, validation=(parsed.train[0],))
        with self.assertRaisesRegex(ValueError, "split"):
            data.validate_fit_splits(bad, config)

    def test_128_configured_openings_counts_bounds_and_exact_deficits(self):
        config, rows = teacher_inputs(96, 16, 16)
        config.update(samplePlacements=[8, 12, 20, 24, 36, 40, 48, 52], maxObservationsPerFamily=8)
        parsed = load(config, rows[:-1])
        self.assertEqual((len(parsed.train), len(parsed.validation)), (96, 15))
        self.assertEqual(
            parsed.coverage["validation"][config["validationFamilies"][-1]],
            dict(observed=0, unobservedCapacity=8),
        )
        self.assertEqual(
            sum(
                v["unobservedCapacity"]
                for split in parsed.coverage.values()
                for v in split.values()
            ),
            785,
        )
        self.assertNotIn("holdout", parsed.coverage)
        data.validate_fit_splits(parsed, config)
        bad = copy.deepcopy(config)
        bad["familyCounts"]["holdout"] = 15
        with self.assertRaises(ValueError):
            data.validate_config(bad)
        bad = copy.deepcopy(config)
        bad["maxFamilies"] = 127
        with self.assertRaises(ValueError):
            data.validate_config(bad)
        bad = copy.deepcopy(config)
        bad["openings"][-1]["state"] = bad["openings"][0]["state"]
        with self.assertRaisesRegex(ValueError, "deduplicated"):
            data.validate_config(bad)

    def test_declared_kind_and_source_control_metadata_without_experiment_branches(self):
        config, rows = inputs()
        config["labelSource"] = "explicit-outcome-source"
        metadata = train.label_metadata(load(config, rows), config)
        self.assertEqual(metadata["labelProvenance"]["labelSource"], "explicit-outcome-source")
        self.assertIn("inferredFinalBlackMinusWhite", metadata)
        self.assertNotIn("teacherVerification", metadata)
        config, rows = teacher_inputs()
        rows[0]["labelKind"] = "gameOutcome"
        with self.assertRaises(ValueError):
            load(config, rows)
        config, rows = teacher_inputs()
        config["teacher"]["weights"] = ""
        with self.assertRaises(ValueError):
            data.validate_config(config)
        config, rows = teacher_inputs()
        config["maxObservationsPerFamily"] = 1
        later = copy.deepcopy(rows[0])
        later["gameId"] = "second-game"
        with self.assertRaisesRegex(ValueError, "observation limit"):
            load(config, rows + [later])


if __name__ == "__main__":
    unittest.main()
