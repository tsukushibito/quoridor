#!/usr/bin/env python3
"""One bounded read-only process-identity port in the existing session environment."""

import importlib.util
import json
from pathlib import Path
import sys


def main():
    root = Path(sys.argv[1])
    spec = importlib.util.spec_from_file_location(
        "dashboard_runtime", root / "scripts/dev/research-runtime.py"
    )
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    raw = sys.stdin.buffer.read(65537)
    if len(raw) > 65536:
        raise ValueError("Identity request too large")
    identities = json.loads(raw)
    if not isinstance(identities, list) or len(identities) > 128:
        raise ValueError("Invalid identity request")
    values = []
    for identity in identities:
        if (
            not isinstance(identity, dict)
            or set(identity) != {"pid", "start_ticks", "boot_id"}
            or type(identity["pid"]) is not int
            or identity["pid"] <= 0
            or not isinstance(identity["start_ticks"], str)
            or not identity["start_ticks"].isdigit()
            or not isinstance(identity["boot_id"], str)
            or len(identity["boot_id"]) > 64
        ):
            values.append(False)
        else:
            values.append(runtime.alive(identity))
    print(json.dumps(values))


if __name__ == "__main__":
    main()
