"""Raw Python feature parity for an explicit model and stdin states; no games/fit."""

import argparse
import json
import sys

from . import data, pattern


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    args = parser.parse_args(argv)
    weights = pattern.from_json(data.bounded_bytes(args.model, pattern.MODEL_MAX_BYTES))
    for line in sys.stdin:
        if len(line.encode("utf-8")) > 4096:
            raise ValueError("parity state line exceeds4096 bytes")
        position = pattern.state(pattern.strict_json(line))
        print(
            json.dumps(
                dict(
                    score=pattern.evaluate(weights, position), scoreKind="heuristic", proven=False
                ),
                allow_nan=False,
            )
        )


if __name__ == "__main__":
    main()
