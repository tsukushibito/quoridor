"""Read-only reuse of the stopped producer guardian for a new bound task."""

import importlib.util
from pathlib import Path

SOURCE = Path(
    "/workspaces/quoridor/research-data/ai-sigma/frame23-rulea-z-transfer/control.py"
)
SPEC = importlib.util.spec_from_file_location("stopped_rulea_guard", SOURCE)
OLD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OLD)
if __name__ == "__main__":
    OLD.GUARD.science = OLD.science
    OLD.GUARD.main()
