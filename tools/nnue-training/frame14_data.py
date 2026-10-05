"""Frozen frame14 policy and compatibility imports.

New reusable code imports dataset/qf1/exposure directly. Existing frame14 and
later frozen commands may keep this compatibility entry; remove it only when
those recipes are no longer invoked from the live tree (old Git stays valid).
"""

from dataset import bound_path, digest, load_stage, read_rows, sha
from exposure import make_exposure_mask, signatures
from qf1 import canonical_model_input, feature_signature

__all__ = [
    "bound_path", "digest", "load_stage", "read_rows", "sha", "signatures",
    "canonical_model_input", "feature_signature", "make_mask",
]


def make_mask(rows):
    return make_exposure_mask(
        rows,
        rule="state OR history OR STM-QF1 input sharing; max-train96 fixed before selection",
    )
