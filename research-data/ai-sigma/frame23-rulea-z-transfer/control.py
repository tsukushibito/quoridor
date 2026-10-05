"""Reuse the stopped guardian and include current saved-score/parity CPU tools."""

import importlib.util
from pathlib import Path

SOURCE = Path(
    "/workspaces/quoridor/research-data/ai-sigma/frame23-independent-teachers/control-v1.py"
)
SPEC = importlib.util.spec_from_file_location("stopped_producer_guard", SOURCE)
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)
ORIGINAL_SCIENCE = GUARD.science


def science(process):
    if ORIGINAL_SCIENCE(process):
        return True
    argv = process["argv"]
    if not argv or not Path(argv[0]).name.startswith(("python", "node")):
        return False
    script = next((part for part in argv[1:] if not part.startswith("-")), "")
    return "/research-data/ai-sigma/" in script and any(
        term in Path(script).name for term in ("score", "arithmetic", "parity", "exposure")
    )


if __name__ == "__main__":
    GUARD.science = science
    GUARD.main()
