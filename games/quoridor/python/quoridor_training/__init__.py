"""Native-generated QF1 learning cycle; no Python search or feature rebuilding."""

import os

# Must precede framework imports: ORT's SDK writes :memory:.ses during import.
os.environ["ORT_DISABLE_TELEMETRY"] = "1"
