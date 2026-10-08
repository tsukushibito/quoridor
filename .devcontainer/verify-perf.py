#!/usr/bin/env python3
"""Explicit post-recreation check; event openings require --probe."""

import argparse
import grp
import json
import os
from pathlib import Path
import platform
import pwd
import re
import subprocess
import time


PERFMON = 1 << 38


def command(argv):
    start = time.monotonic()
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=5,
            env={**os.environ, "LC_ALL": "C"},
            check=False,
        )
        return {
            "argv": argv,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "whole_seconds": time.monotonic() - start,
            "direct_child_waited": True,
        }
    except (OSError, subprocess.TimeoutExpired) as error:

        def captured(value):
            if isinstance(value, bytes):
                return value.decode(errors="replace")
            return value or ""

        return {
            "argv": argv,
            "error": str(error),
            "stdout": captured(getattr(error, "stdout", None)),
            "stderr": captured(getattr(error, "stderr", None)),
            "whole_seconds": time.monotonic() - start,
            "direct_child_waited": isinstance(error, subprocess.TimeoutExpired),
        }


def usable_counter(result, event):
    if result.get("returncode") != 0:
        return False
    for line in result["stderr"].splitlines():
        fields = line.split("\t")
        if len(fields) >= 3 and fields[2].strip() == event:
            return re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", fields[0].strip()) is not None
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    report = {"kernel": platform.release(), "uid": os.geteuid(), "errors": []}
    report["user"] = pwd.getpwuid(os.geteuid()).pw_name
    try:
        binary = Path("/usr/bin/perf").resolve(strict=True)
        info = binary.stat()
        group = grp.getgrnam("perf_users")
        status = dict(
            line.split(":", 1)
            for line in Path("/proc/self/status").read_text().splitlines()
            if ":" in line
        )
        with binary.open("rb") as stream:
            elf = stream.read(4) == b"\x7fELF"
        capability = command(["/usr/sbin/getcap", str(binary)])
        report.update(
            {
                "binary": str(binary),
                "file_capability": capability,
                "shell_CapEff": status["CapEff"].strip(),
                "CapBnd": status["CapBnd"].strip(),
                "NoNewPrivs": status["NoNewPrivs"].strip(),
                "Seccomp": status["Seccomp"].strip(),
                "perf_event_paranoid": Path("/proc/sys/kernel/perf_event_paranoid")
                .read_text()
                .strip(),
                "kptr_restrict": Path("/proc/sys/kernel/kptr_restrict")
                .read_text()
                .strip(),
            }
        )
        checks = {
            "remote_user_vscode": report["user"] == "vscode" and os.geteuid() != 0,
            "root_owned_ELF": info.st_uid == 0 and elf,
            "restricted_perf_group": info.st_gid == group.gr_gid
            and info.st_mode & 0o777 == 0o750
            and group.gr_gid in {os.getegid(), *os.getgroups()},
            "only_perfmon_file_capability": capability.get("returncode") == 0
            and capability["stdout"].strip() == f"{binary} cap_perfmon=ep",
            "perfmon_in_bounding_set": bool(int(status["CapBnd"], 16) & PERFMON),
            "file_capability_elevation_allowed": status["NoNewPrivs"].strip() == "0",
        }
        report["checks"] = checks
        report["errors"].extend(name for name, passed in checks.items() if not passed)
    except (OSError, KeyError, ValueError) as error:
        report["errors"].append(str(error))

    report["packages"] = command(
        ["dpkg-query", "-W", "-f=${Package}\t${Version}\n", "linux-perf", "libcap2-bin"]
    )
    if report["packages"].get("returncode") != 0:
        report["errors"].append("package_metadata_failed")
    if not report["errors"]:
        report["perf_version"] = command([str(binary), "--version"])
        if report["perf_version"].get("returncode") != 0:
            report["errors"].append("perf_version_failed")
    report["event_probe"] = "NOT_RUN"
    if args.probe and not report["errors"]:
        probes = []
        for event in ("cycles:u", "cpu-clock:u"):
            result = command(
                [str(binary), "stat", "-x", "\t", "-e", event, "--", "/bin/true"]
            )
            result["event"] = event
            result["usable_counter"] = usable_counter(result, event)
            probes.append(result)
            if result["usable_counter"]:
                break
        report["event_probe"] = probes
        if not any(probe["usable_counter"] for probe in probes):
            report["errors"].append("hardware_and_software_events_unavailable")
    print(json.dumps(report, indent=2))
    return bool(report["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
