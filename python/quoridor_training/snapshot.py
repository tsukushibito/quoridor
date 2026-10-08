"""Owned atomic publication of replaceable small text snapshots."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import tempfile


@contextmanager
def atomic_text(path):
    """Keep the previous snapshot until serialization and replacement succeed.

    The caller must forecast overlap with one complete sibling temporary per writer.
    This does not change append-only observations or scientific payload publication.
    """
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w") as stream:
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        primary = sys.exception()
        try:
            temporary.unlink(missing_ok=True)
        except BaseException as error:
            if primary is None:
                raise
            primary.add_note("snapshot temporary cleanup failed: " + repr(error))


def write_json(path, value):
    with atomic_text(path) as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
