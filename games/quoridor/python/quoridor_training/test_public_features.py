"""Independent scalar coordinate/QF1 reference for lossless online reflection."""

import unittest

import numpy as np

from .public_features import (
    GEOMETRY,
    RECORD,
    features,
    geometry_from_native,
    model_keys,
    reflect,
)


def scalar_reference(position):
    result = np.zeros((2, 312), dtype=np.float32)
    for player in (0, 1):

        def square(cell):
            y, x = divmod(int(cell), 9)
            return (8 - y) * 9 + 8 - x if player else y * 9 + x

        result[player, square(position["pawns"][player])] = 1
        result[player, 81 + square(position["pawns"][1 - player])] = 1
        result[player, 290 + int(position["stocks"][player])] = 1
        result[player, 301 + int(position["stocks"][1 - player])] = 1
        for name, offset in (("horizontal", 162), ("vertical", 226)):
            for y in range(8):
                for x in range(8):
                    if int(position[name]) & (1 << (y * 8 + x)):
                        anchor = (7 - y) * 8 + 7 - x if player else y * 8 + x
                        result[player, offset + anchor] = 1
    return result


def scalar_reflection(position):
    out = position.copy()
    for player in (0, 1):
        y, x = divmod(int(position["pawns"][player]), 9)
        out["pawns"][player] = y * 9 + 8 - x
    for name in ("horizontal", "vertical"):
        value = 0
        for y in range(8):
            for x in range(8):
                if int(position[name]) & (1 << (y * 8 + x)):
                    value |= 1 << (y * 8 + 7 - x)
        out[name] = value
    return out


class PublicGeometryTests(unittest.TestCase):
    def geometry(self):
        out = np.zeros(4, dtype=GEOMETRY)
        out["pawns"] = [[4, 76], [0, 80], [27, 39], [8, 73]]
        out["stocks"] = [[10, 10], [9, 9], [8, 9], [0, 4]]
        out["horizontal"] = [0, 1 << 7, (1 << 3) | (1 << 63), 1 << 48]
        out["vertical"] = [0, 1 << 16, 1 << 21, 1 << 55]
        return out

    def test_native_layout_two_views_and_roundtrip(self):
        geometry = self.geometry()
        reference = np.stack([scalar_reference(p) for p in geometry])
        np.testing.assert_array_equal(features(geometry), reference)
        native_bytes = np.packbits(
            reference.astype(np.uint8).reshape(-1, 624), axis=1, bitorder="little"
        )
        np.testing.assert_array_equal(geometry_from_native(native_bytes), geometry)
        self.assertEqual(RECORD.itemsize, 66)
        native_bytes[0, 77] ^= 1 << 6
        with self.assertRaisesRegex(ValueError, "both native"):
            geometry_from_native(native_bytes)

    def test_true_wall_anchor_reflection_and_involution(self):
        original = self.geometry()
        mirrored = reflect(original)
        np.testing.assert_array_equal(
            mirrored, np.asarray([scalar_reflection(p) for p in original])
        )
        np.testing.assert_array_equal(reflect(mirrored), original)
        np.testing.assert_array_equal(mirrored["stocks"], original["stocks"])
        # The native 8-wide anchor x=0 becomes x=7, never the plane-padding x=8.
        self.assertEqual(int(mirrored["vertical"][1]), 1 << 23)
        self.assertEqual(int(mirrored["horizontal"][1]), 1 << 0)
        np.testing.assert_array_equal(
            features(mirrored), np.stack([scalar_reference(p) for p in mirrored])
        )

    def test_model_identity_excludes_source_observation_target_and_raw_SHA(self):
        records = np.zeros(3, dtype=RECORD)
        records["geometry"] = self.geometry()[0]
        records["distance"] = [0.1, 0.1]
        records["z"] = [-1, 1, -1]
        records["shard"] = [0, 0, 1]
        records["row"] = [3, 4, 5]
        records["input_sha"][1] = 255
        self.assertEqual(len(np.unique(model_keys(records))), 1)
        records["distance"][2, 0] = np.nextafter(np.float32(0.1), np.float32(1))
        self.assertEqual(len(np.unique(model_keys(records))), 2)

    def test_invalid_bounds_are_not_silently_normalized(self):
        geometry = self.geometry()
        geometry["stocks"][0, 1] = 11
        with self.assertRaisesRegex(ValueError, "bounds"):
            reflect(geometry)


if __name__ == "__main__":
    unittest.main()
