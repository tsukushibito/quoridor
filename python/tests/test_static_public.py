"""Maintain the original-half/old-label boundary; pair codec tests own class storage."""

import unittest

import numpy as np


class StaticPublicTests(unittest.TestCase):
    def test_original_half_decoder_never_opens_labels_or_naive_lr(self):
        import io
        import tempfile
        import zipfile
        from pathlib import Path

        from quoridor_training.public_sigma import original_plane_chunks

        source = np.zeros((4, 8, 9, 9), dtype="<f4")
        source[0].fill(1)
        source[1].fill(2)
        source[2:].fill(99)  # old incorrect reflected half must never be yielded
        body = io.BytesIO()
        np.save(body, source)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.npz"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("states.npy", body.getvalue())
                # No values.npy at all: new static ingress cannot touch labels.
            batches = list(original_plane_chunks(path, {"rows": 4}, with_values=False))
            self.assertEqual(len(batches), 1)
            ids, planes, labels = batches[0]
            np.testing.assert_array_equal(ids, np.array([0, 1], dtype="<u4"))
            np.testing.assert_array_equal(planes[:, 0, 0, 0], [1, 2])
            self.assertIsNone(labels)
            with self.assertRaises(KeyError):
                list(original_plane_chunks(path, {"rows": 4}, with_values=True))


if __name__ == "__main__":
    unittest.main()
