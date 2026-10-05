"""Generic label-free QF1 metadata commands, independent of a frozen split."""

import argparse
import gzip
import json
from pathlib import Path

from dataset import read_rows, sha
from exposure import make_exposure_mask
from qf1 import feature_signature


def canonicalize(metadata, output):
    rows = read_rows(metadata)
    # Validate identities, label prohibition and partitions without imposing a
    # particular dataset size. The caller owns the frozen comparison universe.
    make_exposure_mask(rows)
    for row in rows:
        row["QF1_input_sha256"] = feature_signature(row)
    encoded = "\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n"
    with Path(output).open("xb") as stream:
        stream.write(gzip.compress(encoded.encode(), mtime=0))
    sources = {
        str(Path(__file__).with_name(name).resolve()): sha(Path(__file__).with_name(name))
        for name in ("metadata.py", "dataset.py", "exposure.py", "qf1.py")
    }
    return {
        "rows": len(rows),
        "sha256": sha(output),
        "labels_read": False,
        "source_sha256": sources,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    canonical = commands.add_parser("canonicalize")
    canonical.add_argument("--metadata", required=True)
    canonical.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(canonicalize(args.metadata, args.output)))


if __name__ == "__main__":
    main()
